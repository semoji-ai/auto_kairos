"""[LEGACY] auto_agent.tools.wikipedia_lane → auto_agent.research.lanes.wikipedia로 이전.

Phase 5 cutover에서 thin re-export로 전환. 옛 import 경로(skeleton_from_vault 등)가 깨지지 않도록 유지.
새 코드는 `from auto_agent.research.lanes.wikipedia import ...`를 사용하세요.

이전 버전 (NAS lane 복사본, 한국 RSS 데드 URL 포함)은 git history에 있습니다.
auto_agent.research.lanes.wikipedia는 Phase 1 (commit 514a051)부터 운영 중.
"""
from __future__ import annotations

import warnings

from auto_agent.research.lanes.wikipedia import (
    fetch_wikipedia_article_content as fetch_article_content,
    search_wikipedia,
)

warnings.warn(
    "auto_agent.tools.wikipedia_lane is deprecated. "
    "Use auto_agent.research.lanes.wikipedia (search_wikipedia, fetch_wikipedia_article_content).",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["search_wikipedia", "fetch_article_content"]
