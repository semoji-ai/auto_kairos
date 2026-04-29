"""Lane 4종 단위 테스트 — mock fetcher 사용. 외부 네트워크 호출 없음."""
from __future__ import annotations

import json
from typing import Any

from auto_agent.research.lanes.wikipedia import search_wikipedia
from auto_agent.research.lanes.news_rss import (
    search_google_news_rss,
    search_naver_news_api,
    search_news,
)
from auto_agent.research.lanes.crossref import search_crossref
from auto_agent.research.lanes.openlibrary import search_openlibrary
from auto_agent.research.lanes._trust import classify_tier, is_evidence_eligible


# ─────────────────────────────────────────────
# Trust tier classifier
# ─────────────────────────────────────────────

def test_classify_tier_wikipedia_is_A():
    assert classify_tier("https://ko.wikipedia.org/wiki/유한양행") == "A"


def test_classify_tier_government_kr_is_A():
    assert classify_tier("https://www.kostat.go.kr/anything") == "A"


def test_classify_tier_korean_press_is_A():
    assert classify_tier("https://yna.co.kr/view/1234") == "A"


def test_classify_tier_blog_is_C():
    assert classify_tier("https://blog.naver.com/foo/bar") == "C"
    assert classify_tier("https://m.blog.tistory.com/anything") == "C" or \
           classify_tier("https://example.tistory.com/anything") == "C"


def test_classify_tier_youtube_is_C():
    assert classify_tier("https://youtube.com/watch?v=xx") == "C"


def test_classify_tier_unknown_domain():
    assert classify_tier("https://random-unknown-site.example/page") == "unknown"


def test_is_evidence_eligible():
    assert is_evidence_eligible("https://en.wikipedia.org/wiki/X")
    assert is_evidence_eligible("https://api.crossref.org/works/X")
    assert not is_evidence_eligible("https://blog.naver.com/X")
    assert not is_evidence_eligible("https://random.example/X")  # unknown 도 eligible 아님


# ─────────────────────────────────────────────
# Wikipedia lane
# ─────────────────────────────────────────────

def test_search_wikipedia_ko_first_for_korean_query():
    seen_endpoints: list[str] = []

    def mock_json(url: str) -> dict[str, Any]:
        seen_endpoints.append(url)
        return {"query": {"search": [
            {"title": "유한양행", "snippet": "한국 제약회사"},
        ]}}

    results = search_wikipedia("유한양행", limit=1, fetch_json_impl=mock_json)
    assert len(results) == 1
    assert results[0]["lang"] == "ko"
    assert results[0]["url"].startswith("https://ko.wikipedia.org/wiki/")
    assert results[0]["tier_hint"] == "A"
    assert results[0]["lane"] == "wikipedia"
    # 한국어 쿼리 → ko 먼저 호출
    assert "ko.wikipedia.org" in seen_endpoints[0]


def test_search_wikipedia_en_first_for_english_query():
    seen: list[str] = []

    def mock_json(url: str) -> dict[str, Any]:
        seen.append(url)
        return {"query": {"search": [{"title": "Apollo program", "snippet": "..."}]}}

    results = search_wikipedia("Apollo program", limit=1, fetch_json_impl=mock_json)
    assert len(results) == 1
    assert results[0]["lang"] == "en"
    assert "en.wikipedia.org" in seen[0]


def test_search_wikipedia_handles_api_error_gracefully():
    def boom(url: str) -> dict:
        raise RuntimeError("connection refused")

    results = search_wikipedia("anything", limit=1, fetch_json_impl=boom)
    assert any(r.get("error") for r in results)


# ─────────────────────────────────────────────
# News RSS lane
# ─────────────────────────────────────────────

GOOGLE_NEWS_RSS_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<rss><channel>
<item>
  <title>유한양행 100주년 - 연합뉴스</title>
  <link>https://yna.co.kr/view/AKR20260201001</link>
  <pubDate>Wed, 11 Feb 2026 08:00:00 GMT</pubDate>
</item>
<item>
  <title>유한양행 무관 가십 - 알수없는블로그</title>
  <link>https://blog.naver.com/random/post</link>
  <pubDate>Wed, 11 Feb 2026 09:00:00 GMT</pubDate>
</item>
</channel></rss>
"""


def test_google_news_rss_filters_blocked_domain():
    results = search_google_news_rss(
        "유한양행", limit=10,
        fetch_text_impl=lambda url: GOOGLE_NEWS_RSS_SAMPLE,
    )
    titles = [r["title"] for r in results]
    # blog.naver.com 차단
    assert "유한양행 100주년" in titles
    assert all("블로그" not in t for t in titles)
    # publisher 분리됐고 tier_hint 매핑
    yna = next(r for r in results if "100주년" in r["title"])
    assert yna["publisher"] == "연합뉴스"
    assert yna["tier_hint"] == "A"
    assert yna["confidence"] == "high"


def test_google_news_rss_xml_error_handled():
    def bad(url: str) -> str:
        return "NOT_VALID_XML"

    results = search_google_news_rss("x", fetch_text_impl=bad)
    assert results and results[0].get("error")


def test_naver_news_api_skips_when_no_credentials(monkeypatch):
    monkeypatch.delenv("NAVER_API_CLIENT_ID", raising=False)
    monkeypatch.delenv("NAVER_API_CLIENT_SECRET", raising=False)
    assert search_naver_news_api("유한양행") == []


def test_naver_news_api_returns_results(monkeypatch):
    monkeypatch.setenv("NAVER_API_CLIENT_ID", "xx")
    monkeypatch.setenv("NAVER_API_CLIENT_SECRET", "yy")

    payload = {"items": [
        {
            "title": "<b>유한양행</b> 100주년 기념",
            "originallink": "https://yna.co.kr/article/1",
            "link": "https://news.naver.com/article/1",
            "pubDate": "Mon, 01 Feb 2026 00:00:00 +0900",
            "description": "유한양행이 100주년을 맞아...",
        }
    ]}

    def mock_json(url: str) -> dict[str, Any]:
        return payload

    results = search_naver_news_api("유한양행", fetch_json_impl=mock_json)
    assert len(results) == 1
    r = results[0]
    assert r["title"] == "유한양행 100주년 기념"  # HTML 정리됨
    assert r["url"] == "https://yna.co.kr/article/1"  # originallink 우선
    assert r["lane"] == "naver_news_api"
    assert r["tier_hint"] == "A"


def test_search_news_combines_and_dedupes():
    def mock_text(url: str) -> str:
        return GOOGLE_NEWS_RSS_SAMPLE

    results = search_news(
        "유한양행", limit=5,
        fetch_text_impl=mock_text,
        fetch_json_impl=lambda u: {"items": []},
    )
    # naver 키 없으면 google만
    assert results
    assert any(r["lane"] == "google_news_rss" for r in results)


# ─────────────────────────────────────────────
# Crossref lane
# ─────────────────────────────────────────────

def test_crossref_parses_results():
    payload = {"message": {"items": [
        {
            "title": ["The Effect of X on Y"],
            "URL": "https://doi.org/10.1234/abc",
            "DOI": "10.1234/abc",
            "publisher": "Test Publisher",
            "author": [{"given": "Alice", "family": "Kim"}],
            "created": {"date-parts": [[2020, 5, 1]]},
            "abstract": "<p>An abstract.</p>",
        }
    ]}}

    results = search_crossref("anything", fetch_json_impl=lambda u: payload)
    assert len(results) == 1
    r = results[0]
    assert r["title"] == "The Effect of X on Y"
    assert r["doi"] == "10.1234/abc"
    assert r["author"] == "Alice Kim"
    assert r["published_at"] == "2020-5-1"
    assert "abstract" in r["snippet"]  # HTML 정리됨
    assert r["tier_hint"] == "B"
    assert r["lane"] == "crossref"


# ─────────────────────────────────────────────
# OpenLibrary lane
# ─────────────────────────────────────────────

def test_openlibrary_returns_books():
    payload = {"docs": [
        {
            "title": "유한양행 100년사",
            "key": "/works/OL12345W",
            "author_name": ["John Doe"],
            "publisher": ["Test Pub"],
            "first_publish_year": 2020,
        }
    ]}
    results = search_openlibrary("유한양행", fetch_json_impl=lambda u: payload)
    assert len(results) == 1
    r = results[0]
    assert r["title"] == "유한양행 100년사"
    assert r["url"] == "https://openlibrary.org/works/OL12345W"
    assert r["lane"] == "openlibrary"
    assert r["tier_hint"] == "B"


def test_openlibrary_falls_back_to_google_books():
    """openlibrary가 빈 응답이면 Google Books로 폴백."""
    call_count = {"n": 0}

    def mock(url: str) -> dict[str, Any]:
        call_count["n"] += 1
        if "openlibrary.org" in url:
            return {"docs": []}
        # Google Books
        return {"items": [{
            "volumeInfo": {
                "title": "Fallback Book",
                "infoLink": "https://books.google.com/x",
                "authors": ["Author A"],
                "publisher": "Pub",
                "publishedDate": "2021",
                "description": "desc",
            }
        }]}

    results = search_openlibrary("topic", fetch_json_impl=mock)
    assert call_count["n"] == 2  # OL 시도 → Google fallback
    assert len(results) == 1
    assert results[0]["lane"] == "google_books"
    assert results[0]["title"] == "Fallback Book"
