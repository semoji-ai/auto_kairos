"""새 프로젝트 부트스트랩.

project_id 는 UUID(8자리 hex 단축)를 기본값으로 사용한다.
사람이 읽는 title은 plan.md / pd_notebook.md / projects/_index.md 에 보존.
"""
from __future__ import annotations
from datetime import date
from pathlib import Path
import uuid
from . import paths

ROOT = paths.ROOT
TEMPLATES = ROOT / "templates"


def new_project_id() -> str:
    return uuid.uuid4().hex[:8]


def _append_index(project_id: str, title: str) -> Path:
    idx = paths.projects_index()
    idx.parent.mkdir(parents=True, exist_ok=True)
    line = f"- `{project_id}` — {title} ({date.today().isoformat()})\n"
    if idx.exists():
        existing = idx.read_text(encoding="utf-8")
        if f"`{project_id}`" in existing:
            return idx
        idx.write_text(existing + line, encoding="utf-8")
    else:
        idx.write_text("# Projects Index\n\n" + line, encoding="utf-8")
    return idx


def init_project(title: str, *, project_id: str | None = None) -> dict[str, object]:
    """새 프로젝트를 생성한다.

    Returns: {'project_id', 'title', 'paths': {plan, pd_notebook, index?}}
    """
    pid = project_id or new_project_id()
    paths.project_dir(pid, create=True)
    created: dict[str, Path] = {}

    plan = paths.plan_md(pid)
    if not plan.exists():
        body = (TEMPLATES / "plan.md").read_text(encoding="utf-8")
        body = body.replace("{제목}", title).replace("{project_id}", pid)
        plan.write_text(body, encoding="utf-8")
        created["plan"] = plan

    notebook = paths.pd_notebook(pid)
    if not notebook.exists():
        body = (TEMPLATES / "pd_notebook.md").read_text(encoding="utf-8")
        body = body.replace("{project_id}", pid).replace("{제목}", title)
        notebook.write_text(body, encoding="utf-8")
        created["pd_notebook"] = notebook

    created["index"] = _append_index(pid, title)
    return {"project_id": pid, "title": title, "paths": {k: str(v) for k, v in created.items()}}
