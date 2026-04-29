"""텍스트 유틸 — 도메인 추출, 한국어 감지, HTML 정리."""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse


def contains_korean(text: str) -> bool:
    return any("가" <= ch <= "힣" for ch in str(text or ""))


def wikipedia_languages_for_query(query: str) -> list[str]:
    return ["ko", "en"] if contains_korean(query) else ["en", "ko"]


def extract_domain(url: str) -> str:
    try:
        host = urlparse(str(url or "")).netloc.lower().strip()
    except Exception:
        return ""
    return host[4:] if host.startswith("www.") else host


def clean_html_fragment(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    return " ".join(text.split()).strip()


def clean_crossref_abstract(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    cleaned = re.sub(r"<[^>]+>", " ", text)
    return " ".join(cleaned.split()).strip()[:400]


def title_similar(first: str, second: str, threshold: float = 0.75) -> bool:
    pat = r"[A-Za-z0-9][A-Za-z0-9_-]+|[가-힣]{2,}"
    w1 = set(re.findall(pat, str(first or "").lower()))
    w2 = set(re.findall(pat, str(second or "").lower()))
    if len(w1) < 3 or len(w2) < 3:
        return False
    return (len(w1 & w2) / min(len(w1), len(w2))) >= threshold


def split_google_news_title(raw_title: str) -> tuple[str, str]:
    """Google News RSS 제목은 '<title> - <publisher>' 포맷."""
    title = str(raw_title or "").strip()
    if " - " not in title:
        return title, ""
    parts = [p.strip() for p in title.rsplit(" - ", 1)]
    return (parts[0], parts[1]) if len(parts) == 2 else (title, "")
