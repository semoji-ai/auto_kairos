"""프로젝트 폴더에서 기존 아티팩트를 발견하는 헬퍼.

스킬은 순서가 아니라 아티팩트 규약으로 연결되므로,
실행 시 자기가 필요한 입력이 디스크에 있는지 먼저 본다.
"""
from __future__ import annotations
from pathlib import Path
from . import paths


def list_research_reports(project_id: str) -> list[Path]:
    d = paths.project_dir(project_id) / "research_reports"
    return sorted(d.glob("*.md")) if d.exists() else []


def list_targeted(project_id: str) -> list[Path]:
    d = paths.project_dir(project_id) / "research_targeted"
    return sorted(d.glob("*.md")) if d.exists() else []


def list_wiki_sections(project_id: str) -> list[Path]:
    d = paths.project_dir(project_id) / "wiki"
    if not d.exists():
        return []
    return sorted(p for p in d.glob("*.md") if p.name != "index.md")


def latest_draft(project_id: str) -> Path | None:
    d = paths.project_dir(project_id) / "drafts"
    if not d.exists():
        return None
    items = []
    for p in d.glob("v*.md"):
        try:
            items.append((int(p.stem[1:]), p))
        except ValueError:
            continue
    return max(items)[1] if items else None


def has_final(project_id: str) -> bool:
    return paths.final_manuscript(project_id).exists()


def snapshot(project_id: str) -> dict:
    """현재 프로젝트가 보유한 아티팩트 요약. PD가 상태 파악할 때 쓴다."""
    return {
        "research_reports": [p.name for p in list_research_reports(project_id)],
        "targeted": [p.name for p in list_targeted(project_id)],
        "wiki_sections": [p.name for p in list_wiki_sections(project_id)],
        "latest_draft": (latest_draft(project_id) or Path("")).name or None,
        "has_final": has_final(project_id),
    }
