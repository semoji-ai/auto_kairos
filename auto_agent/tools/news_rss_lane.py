"""[LEGACY] auto_agent.tools.news_rss_lane → auto_agent.research.lanes.news_rss로 이전.

Phase 5 cutover에서 thin re-export로 전환. 옛 import 경로가 깨지지 않도록 유지.
새 코드는 `from auto_agent.research.lanes.news_rss import ...`를 사용하세요.

⚠ 이 옛 모듈에 데드 URL(naver/yna search RSS)이 박혀 있던 버그는 새 모듈에서
Naver Open API + Google News RSS로 대체됨 (commit 514a051).
"""
from __future__ import annotations

import warnings

from auto_agent.research.lanes.news_rss import (
    search_google_news_rss,
    search_naver_news_api,
    search_news,
)

# 옛 코드 호환 — search_korean_news_rss는 폐기됨 (데드 URL). search_naver_news_api로 대체.
search_korean_news_rss = search_naver_news_api

warnings.warn(
    "auto_agent.tools.news_rss_lane is deprecated. "
    "Use auto_agent.research.lanes.news_rss (search_news / search_google_news_rss / search_naver_news_api).",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["search_news", "search_google_news_rss", "search_korean_news_rss", "search_naver_news_api"]
