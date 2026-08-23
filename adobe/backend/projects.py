"""프로젝트 스토어 — projects/{id}/ 스캔/로드 (순수 로직)."""
from __future__ import annotations

import os
import uuid
from pathlib import Path

ARTIFACT_FILES = ["plan.md", "final_manuscript.md", "scenes.json", "pd_notebook.md"]

_VIEW_EXT = {".md", ".json", ".txt"}
_EXCLUDE_FILES = {
    "scenes.json", "layers.json", "references.json", "image_assets.json",
    ".imagegen_last.txt",
}
_FILE_GROUPS = [
    ("기획", ("plan", "strategy", "brief")),
    ("리서치", ("research", "facts", "claims", "deep", "targeted", "skeleton", "outline")),
    ("원고", ("draft", "manuscript", "final_manuscript", "questions", "script")),
]


def list_files(proj_dir: Path) -> list[dict]:
    """프로젝트 최상위 문서 파일(.md/.json/.txt)을 카테고리로 그룹핑.
    스토리보드/에셋/시스템 파일은 제외. 빈 그룹은 결과에서 생략."""
    if not proj_dir.is_dir():
        return []
    names = sorted(
        f.name for f in proj_dir.iterdir()
        if f.is_file() and f.suffix.lower() in _VIEW_EXT and f.name not in _EXCLUDE_FILES
    )
    buckets: dict[str, list[str]] = {label: [] for label, _ in _FILE_GROUPS}
    buckets["기타"] = []
    for n in names:
        low = n.lower()
        for label, keys in _FILE_GROUPS:
            if any(k in low for k in keys):
                buckets[label].append(n)
                break
        else:
            buckets["기타"].append(n)
    order = [label for label, _ in _FILE_GROUPS] + ["기타"]
    return [{"label": label, "files": buckets[label]} for label in order if buckets[label]]


def projects_root() -> Path:
    """프로젝트 저장소. **기본은 v3 의 `output/` 이다.**

    전에는 `adobe/projects/` 에 v3 프로젝트를 **통째로 복사**해 썼다. 그래서
    같은 편이 두 곳에 있었고, v3 에서 그림을 다시 뽑아도 패널에는 옛 그림이
    그대로였다 — 잔 모양을 고친 9씬이 그렇게 반영되지 않았고, 손으로 옮기다
    패널에서 안경을 지운 세 씬을 덮을 뻔했다.

    v3 폴더를 그대로 열면 사본이 생기지 않는다. 산출물(레이어·비디오·그림)이
    한 곳에 모이고, 리모션과 애프터이펙트가 **같은 것을 보고 렌더 단계에서만
    갈린다.**

    `AK_PROJECTS_ROOT` 로 덮을 수 있고, `output/` 이 없으면 옛 자리로 돌아간다.
    """
    env = os.environ.get("AK_PROJECTS_ROOT")
    if env:
        return Path(env)
    out = Path(__file__).resolve().parents[2] / "output"
    if out.is_dir():
        return out
    return Path(__file__).resolve().parents[1] / "projects"


def _title(proj_dir: Path) -> str:
    plan = proj_dir / "plan.md"
    if plan.exists():
        for line in plan.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    return proj_dir.name


def _artifacts(proj_dir: Path) -> dict:
    return {f: (proj_dir / f).exists() for f in ARTIFACT_FILES}


def _status(arts: dict) -> str:
    if arts.get("scenes.json"):
        return "decomposed"
    if arts.get("final_manuscript.md"):
        return "manuscript"
    if arts.get("plan.md"):
        return "planned"
    return "empty"


def _updated_at(proj_dir: Path) -> float:
    mtimes = [p.stat().st_mtime for p in proj_dir.glob("*") if p.is_file()]
    return max(mtimes) if mtimes else proj_dir.stat().st_mtime


def scan_projects(root: Path) -> list[dict]:
    if not root.exists():
        return []
    rows = []
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        # 목록에서 뺀 것을 담아 두는 곳. 파일은 남기되 목록에는 안 보인다.
        if d.name.startswith("_") or d.name.startswith("."):
            continue
        arts = _artifacts(d)
        if not (arts["final_manuscript.md"] or arts["plan.md"]):
            continue
        rows.append({
            "project_id": d.name,
            "title": _title(d),
            "status": _status(arts),
            "updated_at": _updated_at(d),
            "artifacts": arts,
        })
    return rows


def create_project(root: Path, title: str, *, channel: str = "semoji",
                   duration: str = "1분", tone: str = "흥미로운 다큐") -> dict:
    """projects/{id}/plan.md 생성. id=uuid8."""
    root.mkdir(parents=True, exist_ok=True)
    pid = uuid.uuid4().hex[:8]
    d = root / pid
    d.mkdir(parents=True, exist_ok=False)
    (d / "plan.md").write_text(
        f"# {title}\n\n채널: {channel}\n분량: {duration}\n톤: {tone}\n", encoding="utf-8")
    # 주: 에셋 폴더 NAS 심링크는 codex -s workspace-write 샌드박스가 NAS 쓰기를 막아
    # 이미지 생성이 실패하므로 비활성화(로컬 유지). 디스크는 codex 캐시 정리로 관리.
    return {"project_id": pid, "title": title, "status": "planned"}


def load_project(root: Path, project_id: str) -> dict:
    d = root / project_id
    if not d.is_dir():
        raise FileNotFoundError(f"project not found: {project_id}")
    arts = _artifacts(d)
    next_actions = []
    if arts["final_manuscript.md"] and not arts["scenes.json"]:
        next_actions.append("scene-decompose")
    return {
        "project_id": project_id,
        "title": _title(d),
        "status": _status(arts),
        "artifacts": arts,
        "next_actions": next_actions,
    }
