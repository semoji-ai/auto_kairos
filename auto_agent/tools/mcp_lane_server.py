"""
Lane Tools MCP 서버 — wikipedia / news_rss / crossref를 MCP 도구로 노출.

실행:
    python -m auto_agent.tools.mcp_lane_server

Claude Code settings.json 등록:
    "mcpServers": {
        "lane": {
            "command": "/path/to/.venv/bin/python",
            "args": ["-m", "auto_agent.tools.mcp_lane_server"]
        }
    }
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# 패키지 루트를 sys.path에 추가
_pkg_root = str(Path(__file__).parent.parent.parent)
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

from mcp.server.fastmcp import FastMCP

from auto_agent.tools.wikipedia_lane import search_wikipedia, fetch_article_content
from auto_agent.tools.news_rss_lane import search_news
from auto_agent.tools.crossref_lane import search_academic

mcp = FastMCP("lane-tools")


@mcp.tool()
def wikipedia_search(
    query: str,
    limit: int = 5,
    content: bool = False,
    images: bool = True,
) -> str:
    """Wikipedia에서 주제 개요·역사·인물 정보를 검색합니다.

    Args:
        query: 검색어 (한국어/영어 모두 가능)
        limit: 최대 결과 수 (기본 5)
        content: True면 첫 번째 결과의 본문 전문 포함 (개요·역사 조사 시 사용)
        images: True면 각 결과의 썸네일 URL 포함 (기본 True). image_url, image_source, image_license 필드 추가됨.
    """
    results = search_wikipedia(query, limit=limit, fetch_images=images)
    if content and results:
        first_url = results[0].get("url", "")
        if first_url:
            results[0]["full_content"] = fetch_article_content(first_url)
    return json.dumps(results, ensure_ascii=False, indent=2)


@mcp.tool()
def news_search(
    query: str,
    limit: int = 10,
    ko_only: bool = False,
    en_only: bool = False,
) -> str:
    """최신 뉴스를 RSS 피드(Google News + 한국 주요 언론)에서 수집합니다.

    Args:
        query: 검색어. 반드시 단일 키워드/고유명사로 분해해서 호출하세요.
               ❌ "다이소의 역사"  →  ✅ "다이소", "아성다이소 매출", "Daiso"
        limit: 소스당 최대 결과 수 (기본 10)
        ko_only: True면 한국 뉴스만
        en_only: True면 Google News(영문)만
    """
    results = search_news(query, limit=limit, ko_only=ko_only, en_only=en_only)
    # confidence=blocked 제외
    filtered = [r for r in results if r.get("confidence") != "blocked"]
    return json.dumps(filtered, ensure_ascii=False, indent=2)


@mcp.tool()
def academic_search(
    query: str,
    limit: int = 5,
    papers_only: bool = False,
    books_only: bool = False,
) -> str:
    """Crossref(학술 논문) + Open Library(도서)에서 학술 자료를 검색합니다.

    Args:
        query: 검색어 (영어 권장)
        limit: 소스당 최대 결과 수 (기본 5)
        papers_only: True면 Crossref 논문만
        books_only: True면 도서만
    """
    results = search_academic(query, limit=limit, papers_only=papers_only, books_only=books_only)
    return json.dumps(results, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
