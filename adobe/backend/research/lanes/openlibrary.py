"""OpenLibrary lane — 도서. Open Library 우선, 실패 시 Google Books fallback."""
from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus

from backend.research.lanes._http import JsonFetcher, fetch_json


def search_openlibrary(
    query: str,
    *,
    limit: int = 5,
    fetch_json_impl: JsonFetcher | None = None,
) -> list[dict[str, Any]]:
    json_fetcher = fetch_json_impl or fetch_json
    endpoint = f"https://openlibrary.org/search.json?q={quote_plus(query)}&limit={limit}"
    try:
        payload = json_fetcher(endpoint)
        docs = payload.get("docs") or []
        if docs:
            return [
                {
                    "title": str(item.get("title") or "").strip(),
                    "url": f"https://openlibrary.org{item['key']}" if item.get("key") else "",
                    "author": ", ".join((item.get("author_name") or [])[:2]),
                    "publisher": ", ".join((item.get("publisher") or [])[:2])[:120],
                    "published_at": str(item.get("first_publish_year") or ""),
                    "snippet": "",
                    "kind": "book",
                    "lane": "openlibrary",
                    "tier_hint": "B",
                    "query": query,
                }
                for item in docs[:limit]
            ]
    except Exception:
        pass

    # fallback — Google Books
    endpoint = (
        f"https://www.googleapis.com/books/v1/volumes"
        f"?q={quote_plus(query)}&maxResults={limit}"
    )
    try:
        payload = json_fetcher(endpoint)
    except Exception as exc:
        return [{"error": str(exc), "lane": "openlibrary+google_books", "query": query}]

    results: list[dict[str, Any]] = []
    for item in (payload.get("items") or [])[:limit]:
        info = item.get("volumeInfo") or {}
        results.append({
            "title": str(info.get("title") or "").strip(),
            "url": str(info.get("infoLink") or "").strip(),
            "author": ", ".join((info.get("authors") or [])[:2]),
            "publisher": str(info.get("publisher") or "").strip(),
            "published_at": str(info.get("publishedDate") or "").strip(),
            "snippet": str(
                (item.get("searchInfo") or {}).get("textSnippet")
                or info.get("description") or ""
            ).strip()[:300],
            "kind": "book",
            "lane": "google_books",
            "tier_hint": "B",
            "query": query,
        })
    return results
