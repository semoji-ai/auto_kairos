"""Research lanes — 외부 소스별 검색 모듈. 공통 결과 스키마(title/url/publisher/...)."""
from backend.research.lanes.wikipedia import search_wikipedia, fetch_wikipedia_article_content
from backend.research.lanes.news_rss import search_news
from backend.research.lanes.crossref import search_crossref
from backend.research.lanes.openlibrary import search_openlibrary

__all__ = [
    "search_wikipedia",
    "fetch_wikipedia_article_content",
    "search_news",
    "search_crossref",
    "search_openlibrary",
]
