"""[LEGACY] auto_agent.tools.crossref_lane → auto_agent.research.lanes.{crossref,openlibrary}로 이전.

Phase 5 cutover에서 thin re-export로 전환. 옛 import 경로가 깨지지 않도록 유지.
새 코드는 lane을 명시적으로 분리해서 import하세요:
  - from auto_agent.research.lanes.crossref import search_crossref
  - from auto_agent.research.lanes.openlibrary import search_openlibrary
"""
from __future__ import annotations

import warnings

from auto_agent.research.lanes.crossref import search_crossref
from auto_agent.research.lanes.openlibrary import search_openlibrary


def search_academic(query: str, *, limit: int = 5, papers_only: bool = False, books_only: bool = False) -> list[dict]:
    """옛 호환 — Crossref + OpenLibrary 통합 호출."""
    results: list[dict] = []
    if not books_only:
        results.extend(search_crossref(query, limit=limit))
    if not papers_only:
        results.extend(search_openlibrary(query, limit=limit))
    return results


warnings.warn(
    "auto_agent.tools.crossref_lane is deprecated. "
    "Use auto_agent.research.lanes.crossref / openlibrary directly.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["search_crossref", "search_openlibrary", "search_academic"]
