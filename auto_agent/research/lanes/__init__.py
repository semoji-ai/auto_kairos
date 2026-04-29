"""Research lanes — 외부 소스별 검색/수집 모듈.

각 lane은 독립적으로 호출 가능하며, 공통 결과 스키마(title/url/publisher/...)를
반환합니다. fresh_collector_module이 lane들을 조합해 raw + manifests로 적재합니다.
"""

from auto_agent.research.lanes.wikipedia import search_wikipedia, fetch_wikipedia_article_content
from auto_agent.research.lanes.news_rss import search_news
from auto_agent.research.lanes.crossref import search_crossref
from auto_agent.research.lanes.openlibrary import search_openlibrary

__all__ = [
    "search_wikipedia",
    "fetch_wikipedia_article_content",
    "search_news",
    "search_crossref",
    "search_openlibrary",
]
