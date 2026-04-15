"""
Wikipedia 검색 + 본문 추출 도구.

에이전트가 Bash로 호출:
    python3 -m auto_agent.tools.wikipedia_lane "query" [--limit 5] [--content]

JSON 출력: 제목, URL, 스니펫, 선택적으로 본문 텍스트 포함.

토큰 절약 전략:
  WebSearch("... wikipedia") 대신 이 스크립트를 호출하면
  LLM 검색 토큰 없이 구조화된 Wikipedia 데이터를 바로 받을 수 있습니다.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Optional
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

_UA = "KairosAgent/3.1 (educational video production) Python/urllib"
_JINA_PREFIX = "https://r.jina.ai/"


def _fetch_json(url: str) -> dict:
    req = Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
    with urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _fetch_text(url: str) -> str:
    req = Request(url, headers={"User-Agent": _UA})
    with urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8")


def _languages_for_query(query: str) -> list[str]:
    """한국어 포함 여부에 따라 언어 우선순위 결정."""
    has_korean = any("\uac00" <= c <= "\ud7a3" for c in query)
    return ["ko", "en"] if has_korean else ["en", "ko"]


def _fetch_page_thumbnail(lang: str, title: str) -> Optional[str]:
    """Wikipedia pageimages API로 썸네일 URL 반환 (실패 시 None)."""
    endpoint = (
        f"https://{lang}.wikipedia.org/w/api.php"
        f"?action=query&titles={quote_plus(title)}"
        f"&prop=pageimages&piprop=thumbnail&pithumbsize=600"
        f"&format=json&utf8=1"
    )
    try:
        payload = _fetch_json(endpoint)
        pages = (payload.get("query") or {}).get("pages") or {}
        for page in pages.values():
            thumb = (page.get("thumbnail") or {}).get("source")
            if thumb:
                return thumb
    except Exception:
        pass
    return None


def search_wikipedia(query: str, *, limit: int = 5, fetch_images: bool = True) -> list[dict]:
    """Wikipedia 검색 결과 반환 (ko + en 병행). fetch_images=True이면 썸네일 URL 포함."""
    results: list[dict] = []
    seen: set[str] = set()

    for lang in _languages_for_query(query):
        if len(results) >= limit:
            break
        endpoint = (
            f"https://{lang}.wikipedia.org/w/api.php"
            f"?action=query&list=search"
            f"&srsearch={quote_plus(query)}"
            f"&srlimit={limit}"
            f"&format=json&utf8=1"
        )
        try:
            payload = _fetch_json(endpoint)
        except Exception as e:
            results.append({"error": str(e), "lang": lang, "query": query})
            continue

        for item in (payload.get("query") or {}).get("search") or []:
            title = str(item.get("title") or "").strip()
            url = f"https://{lang}.wikipedia.org/wiki/{quote_plus(title.replace(' ', '_'))}" if title else ""
            if not url or url in seen:
                continue
            seen.add(url)
            record: dict = {
                "title": title,
                "url": url,
                "lang": lang,
                "snippet": str(item.get("snippet") or "").replace("<span class=\"searchmatch\">", "").replace("</span>", "").strip(),
                "publisher": "Wikipedia",
                "kind": "reference",
            }
            if fetch_images:
                thumb = _fetch_page_thumbnail(lang, title)
                if thumb:
                    record["image_url"] = thumb
                    record["image_source"] = "wikimedia"
                    record["image_license"] = "CC"  # Wikipedia 이미지는 대부분 CC 라이선스
            results.append(record)
            if len(results) >= limit:
                break

    return results


def fetch_article_content(url: str, *, char_limit: int = 8000) -> str:
    """Jina AI Reader를 통해 Wikipedia 본문 마크다운 추출."""
    jina_url = _JINA_PREFIX + url
    try:
        text = _fetch_text(jina_url)
        return text[:char_limit]
    except Exception as e:
        return f"[content fetch failed: {e}]"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Wikipedia 검색 도구 — 에이전트 WebSearch 토큰 절약용"
    )
    parser.add_argument("query", help="검색어 (한국어/영어 모두 가능)")
    parser.add_argument("--limit", type=int, default=5, help="최대 결과 수 (기본 5)")
    parser.add_argument(
        "--content",
        action="store_true",
        help="첫 번째 결과의 본문 텍스트도 함께 반환",
    )
    parser.add_argument(
        "--char-limit",
        type=int,
        default=8000,
        help="본문 최대 글자 수 (기본 8000)",
    )
    args = parser.parse_args()

    results = search_wikipedia(args.query, limit=args.limit)

    if args.content and results and not results[0].get("error"):
        top = results[0]
        top["content"] = fetch_article_content(top["url"], char_limit=args.char_limit)

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
