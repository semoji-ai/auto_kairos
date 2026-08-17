"""문서(기획/원고) 편집 저장 + 수정 내역(diff) 기록.

저장 시: 이전 버전을 _versions/ 에 백업(무삭제) + unified diff를 edits_log.jsonl에 적재.
LLM 오케스트레이터는 recent_edits_text()로 '사용자가 무엇을 고쳤는지'를 프롬프트에서 인지한다.
"""
from __future__ import annotations

import difflib
import json
from datetime import datetime
from pathlib import Path

EDIT_LOG = "edits_log.jsonl"
ALLOWED_EXT = {".md", ".txt"}
MAX_DIFF_CHARS = 4000           # 로그 한 건당 diff 상한(프롬프트 주입 고려)


def _safe_target(proj_dir: Path, name: str) -> Path | None:
    """프로젝트 내부 + 허용 확장자 검증. 불가하면 None."""
    if not name:
        return None
    fp = (proj_dir / name).resolve()
    if not fp.is_relative_to(Path(proj_dir).resolve()):
        return None
    if fp.suffix.lower() not in ALLOWED_EXT:
        return None
    return fp


def save_file(proj_dir: Path, name: str, content: str) -> dict:
    """파일 저장 + 이전본 백업 + diff 로그. 반환 {ok, changed} 또는 {error}."""
    proj_dir = Path(proj_dir)
    fp = _safe_target(proj_dir, name)
    if fp is None:
        return {"error": "잘못된 경로 또는 허용되지 않는 형식(.md/.txt만)"}
    old = fp.read_text(encoding="utf-8") if fp.is_file() else ""
    if old == content:
        return {"ok": True, "changed": 0, "note": "변경 없음"}

    # 이전본 백업(무삭제): _versions/{name}.v{n}
    if old:
        vdir = proj_dir / "_versions"
        vdir.mkdir(exist_ok=True)
        n = 1
        stem = name.replace("/", "_")
        while (vdir / f"{stem}.v{n}").exists():
            n += 1
        (vdir / f"{stem}.v{n}").write_text(old, encoding="utf-8")

    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(content, encoding="utf-8")

    diff_lines = list(difflib.unified_diff(
        old.splitlines(), content.splitlines(),
        fromfile=f"{name}(이전)", tofile=f"{name}(수정)", lineterm="", n=1))
    diff = "\n".join(diff_lines)[:MAX_DIFF_CHARS]
    changed = sum(1 for ln in diff_lines if ln[:1] in "+-" and ln[:3] not in ("+++", "---"))
    entry = {"ts": datetime.now().isoformat(timespec="seconds"),
             "file": name, "changed_lines": changed, "diff": diff}
    with (proj_dir / EDIT_LOG).open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return {"ok": True, "changed": changed}


def recent_edits(proj_dir: Path, limit: int = 5) -> list:
    """최근 수정 내역(최신순 limit개)."""
    log = Path(proj_dir) / EDIT_LOG
    if not log.is_file():
        return []
    entries = []
    for line in log.read_text(encoding="utf-8").splitlines():
        try:
            entries.append(json.loads(line))
        except Exception:
            continue
    return entries[-limit:][::-1]


def recent_edits_text(proj_dir: Path, limit: int = 3, max_chars: int = 3000) -> str:
    """오케스트레이터 프롬프트 주입용 텍스트. 수정 내역 없으면 ''."""
    items = recent_edits(proj_dir, limit=limit)
    if not items:
        return ""
    parts = ["## 최근 사용자 수정 내역(직접 고친 내용 — 반드시 존중하고 되돌리지 말 것)"]
    for e in items:
        parts.append(f"### {e.get('file')} ({e.get('ts')}, {e.get('changed_lines')}줄 변경)\n"
                     f"```diff\n{e.get('diff', '')}\n```")
    return "\n".join(parts)[:max_chars]
