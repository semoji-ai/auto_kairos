"""
뉴스 RSS 수집 도구 — Google News + 한국 뉴스 (Naver, 연합뉴스).

에이전트가 Bash로 호출:
    python3 -m auto_agent.tools.news_rss_lane "query" [--limit 8] [--ko-only] [--en-only]

JSON 출력: 제목, URL, 발행일, 출판사, confidence(high/medium/blocked) 포함.

토큰 절약 전략:
  WebSearch("뉴스 ...") 대신 이 스크립트를 호출하면
  LLM 검색 토큰 없이 구조화된 최신 뉴스를 바로 받을 수 있습니다.

신뢰도 필터:
  confidence=blocked 항목은 결과에서 제외됩니다 (유튜브, 블로그, SNS 등).
  confidence=high: 주요 언론사 (연합뉴스, Reuters, AP 등)
  confidence=medium: 기타 뉴스 사이트
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Optional
from urllib.parse import quote_plus, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

# RSS media 네임스페이스
_MEDIA_NS = "http://search.yahoo.com/mrss/"
_CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"

_UA = "KairosAgent/3.1 (educational video production) Python/urllib"

# 신뢰 도메인 (confidence: high) — 주요 언론사 및 공식 기관
_TRUSTED_DOMAINS: frozenset[str] = frozenset({
    # 국내 주요 언론
    "yna.co.kr", "yonhapnews.co.kr",
    "chosun.com", "joongang.co.kr", "donga.com",
    "hani.co.kr", "hankookilbo.com",
    "mk.co.kr", "hankyung.com", "sedaily.com",
    "etnews.com", "zdnet.co.kr", "itchosun.com",
    "newsis.com", "newspim.com", "news1.kr",
    "ytn.co.kr", "sbs.co.kr", "kbs.co.kr", "mbc.co.kr",
    # 국제 주요 언론
    "reuters.com", "apnews.com",
    "bbc.com", "bbc.co.uk",
    "nytimes.com", "wsj.com", "ft.com",
    "economist.com", "bloomberg.com",
    "techcrunch.com", "wired.com",
    "theguardian.com", "washingtonpost.com",
    "cnn.com", "nbcnews.com", "forbes.com",
    # 공식/학술
    "wikipedia.org", "nature.com", "science.org",
    "ncbi.nlm.nih.gov", "who.int",
})

# 차단 도메인/패턴 (가짜뉴스·저신뢰 소스)
_BLOCKED_PATTERNS: tuple[str, ...] = (
    "youtube.com", "youtu.be",
    "tiktok.com", "instagram.com",
    "facebook.com", "twitter.com", "x.com",
    "blog.naver.com", "naver.com/blog",
    "tistory.com", "wordpress.com", "blogspot.com",
    "cafe.naver.com", "cafe.daum.net",
)


def _get_domain(url: str) -> str:
    """URL에서 도메인 추출 (www. 제거)."""
    try:
        return urlparse(url).netloc.lower().lstrip("www.")
    except Exception:
        return ""


def _get_confidence(url: str) -> str:
    """URL 기반 신뢰도 반환: 'high' | 'medium' | 'blocked'."""
    domain = _get_domain(url)
    url_lower = url.lower()
    for blocked in _BLOCKED_PATTERNS:
        if blocked in domain or blocked in url_lower:
            return "blocked"
    for trusted in _TRUSTED_DOMAINS:
        if domain == trusted or domain.endswith("." + trusted):
            return "high"
    return "medium"


def _title_similar(t1: str, t2: str, threshold: float = 0.75) -> bool:
    """토큰 겹침 기반 제목 유사도 — threshold 이상이면 중복으로 판정."""
    words1 = set(t1.lower().split())
    words2 = set(t2.lower().split())
    if len(words1) < 3 or len(words2) < 3:
        return False
    overlap = len(words1 & words2)
    return overlap / min(len(words1), len(words2)) >= threshold


_KOREAN_SOURCES = [
    {
        "name": "naver_news",
        "publisher": "Naver News",
        "url_template": "https://news.naver.com/rss/search.naver?query={query}",
    },
    {
        "name": "yonhap",
        "publisher": "연합뉴스",
        "url_template": "https://www.yna.co.kr/rss/search.nhn?query={query}",
    },
]


def _fetch_text(url: str) -> str:
    req = Request(url, headers={"User-Agent": _UA})
    with urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8")


def _extract_image_from_item(item: ET.Element) -> Optional[str]:
    """RSS <item>에서 이미지 URL 추출 (media:content > enclosure > og:image 순)."""
    # 1. media:content (Yahoo Media RSS)
    media_content = item.find(f"{{{_MEDIA_NS}}}content")
    if media_content is not None:
        url = media_content.get("url", "")
        medium = media_content.get("medium", "")
        if url and (medium == "image" or "image" in media_content.get("type", "")):
            return url
        if url and any(url.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp")):
            return url

    # 2. media:thumbnail
    media_thumb = item.find(f"{{{_MEDIA_NS}}}thumbnail")
    if media_thumb is not None:
        url = media_thumb.get("url", "")
        if url:
            return url

    # 3. enclosure (팟캐스트/일부 뉴스)
    enclosure = item.find("enclosure")
    if enclosure is not None:
        enc_type = enclosure.get("type", "")
        url = enclosure.get("url", "")
        if url and enc_type.startswith("image/"):
            return url

    # 4. description 내 <img src="..."> 파싱
    desc = item.findtext("description") or ""
    if desc:
        m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', desc, re.IGNORECASE)
        if m:
            return m.group(1)

    return None


def _split_google_title(raw: str) -> tuple[str, str]:
    """'기사 제목 - 언론사' 형식에서 제목과 언론사를 분리."""
    if " - " not in raw:
        return raw.strip(), ""
    parts = [p.strip() for p in raw.rsplit(" - ", 1)]
    return parts[0], parts[1] if len(parts) == 2 else ""


def search_google_news_rss(query: str, *, limit: int = 8) -> list[dict]:
    """Google News RSS에서 영어 뉴스 수집."""
    endpoint = (
        "https://news.google.com/rss/search"
        f"?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
    )
    results: list[dict] = []
    seen_urls: set[str] = set()
    seen_titles: list[str] = []
    try:
        xml_text = _fetch_text(endpoint)
        root = ET.fromstring(xml_text)
    except Exception as e:
        return [{"error": str(e), "source": "google_news_rss", "query": query}]

    for item in root.findall(".//item"):
        if len(results) >= limit:
            break
        raw_title = (item.findtext("title") or "").strip()
        title, publisher = _split_google_title(raw_title)
        url = (item.findtext("link") or "").strip()

        confidence = _get_confidence(url)
        if confidence == "blocked":
            continue

        key = url or title
        if not key or key in seen_urls:
            continue
        if any(_title_similar(title, t) for t in seen_titles):
            continue
        seen_urls.add(key)
        seen_titles.append(title)
        record: dict = {
            "title": title,
            "url": url,
            "published_at": (item.findtext("pubDate") or "").strip(),
            "publisher": publisher,
            "confidence": confidence,
            "kind": "news",
            "source": "google_news_rss",
            "query": query,
        }
        img_url = _extract_image_from_item(item)
        if img_url:
            record["image_url"] = img_url
            record["image_source"] = "news_rss"
        results.append(record)

    return results


def search_korean_news_rss(query: str, *, limit: int = 8) -> list[dict]:
    """Naver News + 연합뉴스 RSS에서 한국 뉴스 수집."""
    results: list[dict] = []
    seen_urls: set[str] = set()
    seen_titles: list[str] = []

    for source in _KOREAN_SOURCES:
        if len(results) >= limit:
            break
        endpoint = source["url_template"].format(query=quote_plus(query))
        try:
            xml_text = _fetch_text(endpoint)
            root = ET.fromstring(xml_text)
        except Exception as e:
            results.append({"error": str(e), "source": source["name"], "query": query})
            continue

        for item in root.findall(".//item"):
            if len(results) >= limit:
                break
            title = (item.findtext("title") or "").strip()
            url = (item.findtext("link") or "").strip()

            confidence = _get_confidence(url)
            if confidence == "blocked":
                continue

            key = url or title
            if not key or key in seen_urls:
                continue
            if any(_title_similar(title, t) for t in seen_titles):
                continue
            seen_urls.add(key)
            seen_titles.append(title)
            record: dict = {
                "title": title,
                "url": url,
                "published_at": (item.findtext("pubDate") or "").strip(),
                "snippet": (item.findtext("description") or "").strip()[:200],
                "publisher": source["publisher"],
                "confidence": confidence,
                "kind": "news",
                "source": source["name"],
                "query": query,
            }
            img_url = _extract_image_from_item(item)
            if img_url:
                record["image_url"] = img_url
                record["image_source"] = "news_rss"
            results.append(record)

    return results


def search_news(query: str, *, limit: int = 8, ko_only: bool = False, en_only: bool = False) -> list[dict]:
    """Google News + 한국 뉴스 통합 검색."""
    results: list[dict] = []

    if not ko_only:
        results.extend(search_google_news_rss(query, limit=limit))

    if not en_only:
        results.extend(search_korean_news_rss(query, limit=limit))

    # 중복 URL 제거 후 limit 적용
    seen: set[str] = set()
    deduped: list[dict] = []
    for item in results:
        key = str(item.get("url") or item.get("title") or "")
        if key and key not in seen:
            seen.add(key)
            deduped.append(item)

    return deduped[:limit * 2]  # Google + 한국 각각 limit개이므로 합산은 2배까지


def main() -> None:
    parser = argparse.ArgumentParser(
        description="뉴스 RSS 수집 도구 — 에이전트 WebSearch 토큰 절약용"
    )
    parser.add_argument("query", help="검색어 (한국어/영어 모두 가능)")
    parser.add_argument("--limit", type=int, default=8, help="소스당 최대 결과 수 (기본 8)")
    parser.add_argument("--ko-only", action="store_true", help="한국 뉴스만 수집")
    parser.add_argument("--en-only", action="store_true", help="Google News만 수집")
    args = parser.parse_args()

    results = search_news(args.query, limit=args.limit, ko_only=args.ko_only, en_only=args.en_only)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
