"""Wikipedia lane — ko/en wiki API."""
from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus

from auto_agent.research.lanes._http import JsonFetcher, TextFetcher, fetch_json, fetch_text
from auto_agent.research.lanes._text import clean_html_fragment, wikipedia_languages_for_query

JINA_READER_PREFIX = "https://r.jina.ai/"


def search_wikipedia(
    query: str,
    *,
    limit: int = 5,
    include_content: bool = False,
    char_limit: int = 8000,
    fetch_json_impl: JsonFetcher | None = None,
    fetch_text_impl: TextFetcher | None = None,
) -> list[dict[str, Any]]:
    json_fetcher = fetch_json_impl or fetch_json
    text_fetcher = fetch_text_impl or fetch_text
    results: list[dict[str, Any]] = []
    seen: set[str] = set()

    for lang in wikipedia_languages_for_query(query):
        if len(results) >= limit:
            break
        endpoint = (
            f"https://{lang}.wikipedia.org/w/api.php"
            f"?action=query&list=search&srsearch={quote_plus(query)}"
            f"&srlimit={limit}&format=json&utf8=1"
        )
        try:
            payload = json_fetcher(endpoint)
        except Exception as exc:
            results.append({"error": str(exc), "lang": lang, "query": query})
            continue
        for item in (payload.get("query") or {}).get("search") or []:
            title = str(item.get("title") or "").strip()
            url = (
                f"https://{lang}.wikipedia.org/wiki/{quote_plus(title.replace(' ', '_'))}"
                if title else ""
            )
            if not url or url in seen:
                continue
            seen.add(url)
            results.append({
                "title": title,
                "url": url,
                "lang": lang,
                "snippet": clean_html_fragment(str(item.get("snippet") or "")),
                "publisher": "Wikipedia",
                "kind": "reference",
                "lane": "wikipedia",
                "tier_hint": "A",
            })
            if len(results) >= limit:
                break

    if include_content and results and not results[0].get("error"):
        top_url = str(results[0].get("url") or "").strip()
        if top_url:
            results[0]["content"] = fetch_wikipedia_article_content(
                top_url,
                char_limit=char_limit,
                fetch_text_impl=text_fetcher,
            )
    return results


def fetch_wikipedia_article_content(
    url: str,
    *,
    char_limit: int = 8000,
    fetch_text_impl: TextFetcher | None = None,
) -> str:
    """Jina Reader로 Wikipedia 본문을 plain text로 가져옴."""
    text_fetcher = fetch_text_impl or fetch_text
    jina_url = JINA_READER_PREFIX + str(url or "").strip()
    try:
        return text_fetcher(jina_url)[:char_limit]
    except Exception as exc:
        return f"[content fetch failed: {exc}]"
