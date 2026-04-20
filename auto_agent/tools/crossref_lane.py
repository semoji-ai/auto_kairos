"""
학술 자료 검색 도구 — Crossref (논문) + Open Library (도서).

에이전트가 Bash로 호출:
    python3 -m auto_agent.tools.crossref_lane "query" [--limit 5] [--books-only] [--papers-only]

JSON 출력: 제목, URL, 저자, 발행일, 요약 포함.

토큰 절약 전략:
  WebSearch("academic paper ...") 대신 이 스크립트를 호출하면
  LLM 검색 토큰 없이 구조화된 학술 데이터를 바로 받을 수 있습니다.
"""
from __future__ import annotations

import argparse
import json
import re
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

_UA = "KairosAgent/3.1 (educational video production) Python/urllib"


def _fetch_json(url: str) -> dict:
    req = Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
    with urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _clean_abstract(text: str) -> str:
    """Crossref XML 태그 제거."""
    if not text:
        return ""
    cleaned = re.sub(r"<[^>]+>", " ", str(text))
    return " ".join(cleaned.split()).strip()[:400]


def search_crossref(query: str, *, limit: int = 5) -> list[dict]:
    """Crossref API로 학술 논문 검색."""
    endpoint = f"https://api.crossref.org/works?query={quote_plus(query)}&rows={limit}"
    try:
        payload = _fetch_json(endpoint)
    except Exception as e:
        return [{"error": str(e), "source": "crossref", "query": query}]

    results: list[dict] = []
    seen: set[str] = set()
    for item in (payload.get("message") or {}).get("items") or []:
        title = " ".join(item.get("title") or []).strip()
        url = str(item.get("URL") or "").strip()
        key = url or title
        if not key or key in seen:
            continue
        seen.add(key)

        date_parts = ((item.get("created") or {}).get("date-parts") or [[]])[0]
        published_at = "-".join(str(p) for p in date_parts if p)

        results.append({
            "title": title,
            "url": url,
            "doi": str(item.get("DOI") or "").strip(),
            "author": ", ".join(
                f"{a.get('given', '')} {a.get('family', '')}".strip()
                for a in (item.get("author") or [])[:3]
            ),
            "publisher": str(item.get("publisher") or "").strip(),
            "published_at": published_at,
            "snippet": _clean_abstract(item.get("abstract")),
            "kind": "paper",
            "source": "crossref",
            "query": query,
        })
        if len(results) >= limit:
            break

    return results


def search_openlibrary(query: str, *, limit: int = 5) -> list[dict]:
    """Open Library API로 도서 검색 (Google Books 폴백)."""
    endpoint = f"https://openlibrary.org/search.json?q={quote_plus(query)}&limit={limit}"
    try:
        payload = _fetch_json(endpoint)
        docs = payload.get("docs") or []
        if docs:
            results = []
            for item in docs[:limit]:
                results.append({
                    "title": str(item.get("title") or "").strip(),
                    "url": f"https://openlibrary.org{item['key']}" if item.get("key") else "",
                    "author": ", ".join((item.get("author_name") or [])[:2]),
                    "publisher": ", ".join((item.get("publisher") or [])[:2])[:120],
                    "published_at": str(item.get("first_publish_year") or ""),
                    "snippet": "",
                    "kind": "book",
                    "source": "openlibrary",
                    "query": query,
                })
            return results
    except Exception:
        pass

    # Google Books 폴백
    endpoint = f"https://www.googleapis.com/books/v1/volumes?q={quote_plus(query)}&maxResults={limit}"
    try:
        payload = _fetch_json(endpoint)
        results = []
        for item in (payload.get("items") or [])[:limit]:
            info = item.get("volumeInfo") or {}
            results.append({
                "title": str(info.get("title") or "").strip(),
                "url": str(info.get("infoLink") or "").strip(),
                "author": ", ".join((info.get("authors") or [])[:2]),
                "publisher": str(info.get("publisher") or "").strip(),
                "published_at": str(info.get("publishedDate") or "").strip(),
                "snippet": str((item.get("searchInfo") or {}).get("textSnippet") or info.get("description") or "").strip()[:300],
                "kind": "book",
                "source": "google_books",
                "query": query,
            })
        return results
    except Exception as e:
        return [{"error": str(e), "source": "openlibrary+google_books", "query": query}]


def search_academic(query: str, *, limit: int = 5, papers_only: bool = False, books_only: bool = False) -> list[dict]:
    """Crossref + Open Library 통합 학술 검색."""
    results: list[dict] = []

    if not books_only:
        results.extend(search_crossref(query, limit=limit))

    if not papers_only:
        results.extend(search_openlibrary(query, limit=limit))

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="학술 자료 검색 도구 — 에이전트 WebSearch 토큰 절약용"
    )
    parser.add_argument("query", help="검색어 (한국어/영어 모두 가능)")
    parser.add_argument("--limit", type=int, default=5, help="소스당 최대 결과 수 (기본 5)")
    parser.add_argument("--papers-only", action="store_true", help="Crossref 논문만")
    parser.add_argument("--books-only", action="store_true", help="도서만 (Open Library + Google Books)")
    args = parser.parse_args()

    results = search_academic(
        args.query,
        limit=args.limit,
        papers_only=args.papers_only,
        books_only=args.books_only,
    )
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
