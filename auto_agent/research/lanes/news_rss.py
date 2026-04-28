"""News RSS lane — Google News + Naver Open API + (live) 한국 카테고리 RSS.

기존 ResearchAgent의 한국 검색 RSS URL 두 개(naver/yna)는 데드(404/400)라
다음으로 대체:
- Naver Open API (NAVER_API_CLIENT_ID/SECRET 환경변수 필요)
- Google News RSS (한국어 쿼리도 결과 반환)
"""
from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote_plus
from xml.etree import ElementTree as ET

from auto_agent.research.lanes._http import (
    DEFAULT_TIMEOUT,
    JsonFetcher,
    TextFetcher,
    fetch_json,
    fetch_text,
)
from auto_agent.research.lanes._text import (
    clean_html_fragment,
    split_google_news_title,
    title_similar,
)
from auto_agent.research.lanes._trust import classify_tier


def _confidence_from_tier(tier: str) -> str:
    return {"A": "high", "B": "high", "C": "blocked"}.get(tier, "medium")


def search_google_news_rss(
    query: str,
    *,
    limit: int = 8,
    fetch_text_impl: TextFetcher | None = None,
) -> list[dict[str, Any]]:
    text_fetcher = fetch_text_impl or fetch_text
    endpoint = (
        "https://news.google.com/rss/search"
        f"?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
    )
    results: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    seen_titles: list[str] = []
    try:
        xml_text = text_fetcher(endpoint)
        root = ET.fromstring(xml_text)
    except Exception as exc:
        return [{"error": str(exc), "lane": "google_news_rss", "query": query}]

    for item in root.findall(".//item"):
        if len(results) >= limit:
            break
        raw_title = (item.findtext("title") or "").strip()
        title, publisher = split_google_news_title(raw_title)
        url = (item.findtext("link") or "").strip()
        tier = classify_tier(url, publisher=publisher)
        confidence = _confidence_from_tier(tier)
        if confidence == "blocked":
            continue
        dedupe_key = url or title
        if not dedupe_key or dedupe_key in seen_urls:
            continue
        if any(title_similar(title, prev) for prev in seen_titles):
            continue
        seen_urls.add(dedupe_key)
        seen_titles.append(title)
        results.append({
            "title": title,
            "url": url,
            "published_at": (item.findtext("pubDate") or "").strip(),
            "publisher": publisher,
            "confidence": confidence,
            "tier_hint": tier,
            "kind": "news",
            "lane": "google_news_rss",
            "query": query,
        })
    return results


def search_naver_news_api(
    query: str,
    *,
    limit: int = 8,
    fetch_json_impl: JsonFetcher | None = None,
) -> list[dict[str, Any]]:
    """Naver Open API (한국어 뉴스). NAVER_API_CLIENT_ID/SECRET 환경변수 필수.

    환경변수 미설정 시 빈 리스트 반환 (silent skip).
    """
    client_id = os.environ.get("NAVER_API_CLIENT_ID", "").strip()
    client_secret = os.environ.get("NAVER_API_CLIENT_SECRET", "").strip()
    if not (client_id and client_secret):
        return []

    json_fetcher = fetch_json_impl or fetch_json
    endpoint = (
        f"https://openapi.naver.com/v1/search/news.json"
        f"?query={quote_plus(query)}&display={min(limit, 100)}&sort=sim"
    )
    try:
        payload = json_fetcher(endpoint, headers={  # type: ignore[call-arg]
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
        })
    except TypeError:
        # fetch_json_impl가 mock이라 headers kw 미지원인 경우
        try:
            payload = json_fetcher(endpoint)
        except Exception as exc:
            return [{"error": str(exc), "lane": "naver_news_api", "query": query}]
    except Exception as exc:
        return [{"error": str(exc), "lane": "naver_news_api", "query": query}]

    results: list[dict[str, Any]] = []
    for item in (payload.get("items") or [])[:limit]:
        title = clean_html_fragment(str(item.get("title") or ""))
        url = str(item.get("originallink") or item.get("link") or "").strip()
        if not url or not title:
            continue
        tier = classify_tier(url)
        confidence = _confidence_from_tier(tier)
        if confidence == "blocked":
            continue
        results.append({
            "title": title,
            "url": url,
            "published_at": str(item.get("pubDate") or "").strip(),
            "snippet": clean_html_fragment(str(item.get("description") or ""))[:200],
            "publisher": "",
            "confidence": confidence,
            "tier_hint": tier,
            "kind": "news",
            "lane": "naver_news_api",
            "query": query,
        })
    return results


def search_news(
    query: str,
    *,
    limit: int = 8,
    ko_only: bool = False,
    en_only: bool = False,
    fetch_text_impl: TextFetcher | None = None,
    fetch_json_impl: JsonFetcher | None = None,
) -> list[dict[str, Any]]:
    """Google News + Naver(키 있을 때) 통합. 결과 dedup."""
    results: list[dict[str, Any]] = []
    if not ko_only:
        results.extend(
            search_google_news_rss(query, limit=limit, fetch_text_impl=fetch_text_impl)
        )
    if not en_only:
        results.extend(
            search_naver_news_api(query, limit=limit, fetch_json_impl=fetch_json_impl)
        )

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    seen_titles: list[str] = []
    for item in results:
        if item.get("error"):
            deduped.append(item)
            continue
        title = str(item.get("title") or "").strip()
        key = str(item.get("url") or title).strip()
        if not key or key in seen:
            continue
        if any(title_similar(title, prev) for prev in seen_titles):
            continue
        seen.add(key)
        seen_titles.append(title)
        deduped.append(item)
    return deduped[: limit * 2]
