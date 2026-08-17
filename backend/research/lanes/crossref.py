"""Crossref lane — 학술 논문 검색."""
from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus

from backend.research.lanes._http import JsonFetcher, fetch_json
from backend.research.lanes._text import clean_crossref_abstract


def search_crossref(
    query: str,
    *,
    limit: int = 5,
    fetch_json_impl: JsonFetcher | None = None,
) -> list[dict[str, Any]]:
    json_fetcher = fetch_json_impl or fetch_json
    endpoint = f"https://api.crossref.org/works?query={quote_plus(query)}&rows={limit}"
    try:
        payload = json_fetcher(endpoint)
    except Exception as exc:
        return [{"error": str(exc), "lane": "crossref", "query": query}]

    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in (payload.get("message") or {}).get("items") or []:
        title = " ".join(item.get("title") or []).strip()
        url = str(item.get("URL") or "").strip()
        key = url or title
        if not key or key in seen:
            continue
        seen.add(key)
        date_parts = ((item.get("created") or {}).get("date-parts") or [[]])[0]
        results.append({
            "title": title,
            "url": url,
            "doi": str(item.get("DOI") or "").strip(),
            "author": ", ".join(
                f"{a.get('given', '')} {a.get('family', '')}".strip()
                for a in (item.get("author") or [])[:3]
            ),
            "publisher": str(item.get("publisher") or "").strip(),
            "published_at": "-".join(str(p) for p in date_parts if p),
            "snippet": clean_crossref_abstract(item.get("abstract")),
            "kind": "paper",
            "lane": "crossref",
            "tier_hint": "B",
            "query": query,
        })
        if len(results) >= limit:
            break
    return results
