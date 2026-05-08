"""프로젝트 경로 규약 헬퍼.

모든 아티팩트 경로는 여기를 거쳐 만들어진다.
"""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROJECTS_DIR = ROOT / "projects"


def project_dir(project_id: str, *, create: bool = False) -> Path:
    p = PROJECTS_DIR / project_id
    if create:
        for sub in ("wiki", "research_reports", "research_targeted", "drafts", "strategy"):
            (p / sub).mkdir(parents=True, exist_ok=True)
    return p


def projects_index() -> Path:
    return PROJECTS_DIR / "_index.md"


def strategy_options(project_id: str, stamp: str) -> Path:
    return project_dir(project_id) / "strategy" / f"options-{stamp}.md"


def pd_notebook(project_id: str) -> Path:
    return project_dir(project_id) / "pd_notebook.md"


def plan_md(project_id: str) -> Path:
    return project_dir(project_id) / "plan.md"


def wiki_index(project_id: str) -> Path:
    return project_dir(project_id) / "wiki" / "index.md"


def wiki_section(project_id: str, slug: str) -> Path:
    return project_dir(project_id) / "wiki" / f"{slug}.md"


def research_report(project_id: str, slug: str) -> Path:
    return project_dir(project_id) / "research_reports" / f"{slug}.md"


def research_targeted(project_id: str, slug: str) -> Path:
    return project_dir(project_id) / "research_targeted" / f"{slug}.md"


def draft(project_id: str, version: int) -> Path:
    return project_dir(project_id) / "drafts" / f"v{version}.md"


def final_manuscript(project_id: str) -> Path:
    return project_dir(project_id) / "final_manuscript.md"
