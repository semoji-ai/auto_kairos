"""wiki/index.md 갱신 헬퍼.

인덱스 포맷:
    # Wiki Index

    - [slug](slug.md) — 한 줄 요약
"""
from __future__ import annotations
from pathlib import Path
from . import paths

HEADER = "# Wiki Index\n\n"


def _read(project_id: str) -> dict[str, str]:
    p = paths.wiki_index(project_id)
    if not p.exists():
        return {}
    entries: dict[str, str] = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.startswith("- ["):
            continue
        try:
            slug = line.split("](", 1)[0].removeprefix("- [")
            summary = line.split(") — ", 1)[1] if ") — " in line else ""
        except IndexError:
            continue
        entries[slug] = summary
    return entries


def _write(project_id: str, entries: dict[str, str]) -> Path:
    p = paths.wiki_index(project_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = [HEADER]
    for slug in sorted(entries):
        lines.append(f"- [{slug}]({slug}.md) — {entries[slug]}\n")
    p.write_text("".join(lines), encoding="utf-8")
    return p


def upsert(project_id: str, slug: str, summary: str) -> Path:
    """slug 항목을 추가 또는 갱신."""
    entries = _read(project_id)
    entries[slug] = summary.strip().replace("\n", " ")
    return _write(project_id, entries)


def remove(project_id: str, slug: str) -> Path:
    entries = _read(project_id)
    entries.pop(slug, None)
    return _write(project_id, entries)
