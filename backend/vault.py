"""프로젝트 볼트 — 작업·대화를 인덱싱해 세션이 바뀌어도 맥락을 복원.

- worklog.jsonl: 작업 이력(레이어 분리·TTS·모션·조립 등 — 패널 직접 실행 포함)
- context.md:    LLM이 대화·작업을 증류한 프로젝트 브리핑(새 세션의 출발 맥락)
- meta.json:     증류 진행 위치(대화 몇 턴까지 반영했는지 — 증분 증류)
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

DIRNAME = "vault"


def vault_dir(proj_dir: Path) -> Path:
    d = Path(proj_dir) / DIRNAME
    d.mkdir(exist_ok=True)
    return d


def log_work(proj_dir: Path, kind: str, summary: str) -> None:
    """작업 한 건 기록 — 어떤 작업이 언제 어떤 결과였는지."""
    try:
        with (vault_dir(proj_dir) / "worklog.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": datetime.now().isoformat(timespec="minutes"),
                                "kind": kind, "summary": (summary or "")[:300]},
                               ensure_ascii=False) + "\n")
    except Exception:
        pass


def worklog_text(proj_dir: Path, limit: int = 12) -> str:
    """최근 작업 이력 텍스트(프롬프트용). 없으면 ''."""
    fp = Path(proj_dir) / DIRNAME / "worklog.jsonl"
    if not fp.is_file():
        return ""
    rows = []
    for line in fp.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    rows = rows[-limit:]
    return "\n".join(f"- {r.get('ts')} [{r.get('kind')}] {r.get('summary')}" for r in rows)


def read_context(proj_dir: Path) -> str:
    fp = Path(proj_dir) / DIRNAME / "context.md"
    return fp.read_text(encoding="utf-8") if fp.is_file() else ""


def write_context(proj_dir: Path, text: str) -> None:
    (vault_dir(proj_dir) / "context.md").write_text(text or "", encoding="utf-8")


def _meta(proj_dir: Path) -> dict:
    fp = Path(proj_dir) / DIRNAME / "meta.json"
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_meta(proj_dir: Path, meta: dict) -> None:
    (vault_dir(proj_dir) / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False), encoding="utf-8")


def undistilled_turns(proj_dir: Path, chat_file: str = "assistant_chat.jsonl") -> list:
    """아직 context.md에 반영 안 된 대화 턴들(증분)."""
    fp = Path(proj_dir) / chat_file
    if not fp.is_file():
        return []
    turns = []
    for line in fp.read_text(encoding="utf-8").splitlines():
        try:
            turns.append(json.loads(line))
        except Exception:
            continue
    done = int(_meta(proj_dir).get("distilled_turns", 0))
    return turns[done:]


def mark_distilled(proj_dir: Path, total_turns: int) -> None:
    meta = _meta(proj_dir)
    meta["distilled_turns"] = int(total_turns)
    _save_meta(proj_dir, meta)


def total_turns(proj_dir: Path, chat_file: str = "assistant_chat.jsonl") -> int:
    fp = Path(proj_dir) / chat_file
    if not fp.is_file():
        return 0
    return sum(1 for ln in fp.read_text(encoding="utf-8").splitlines() if ln.strip())
