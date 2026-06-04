"""Kairos Vault 검색 헬퍼 (read-only).

Vault는 NAS 마운트 위에 있고 운영 매뉴얼은
`/Volumes/kairos/kairos_vault/kairos-vault/CLAUDE.md` 에 있다.
이 모듈은 그 매뉴얼 규약을 따라 검색만 수행한다. 쓰기는 별도 vault-absorb 스킬 책임.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import re

VAULT_ROOT = Path("/Volumes/kairos/kairos_vault/kairos-vault")

# Vault 매뉴얼이 정한 캐노니컬 검색 영역
SEARCH_AREAS = [
    "02-research/wiki",
    "02-research/topics",
    "02-research/raw",
    "01-patterns",
    "03-analysis/videos",
    "03-analysis/channels",
]


def is_available() -> bool:
    return VAULT_ROOT.exists() and (VAULT_ROOT / "CLAUDE.md").exists()


@dataclass
class VaultHit:
    path: str
    area: str
    title: str
    tags: list[str]
    snippet: str
    score: int

    def to_dict(self) -> dict:
        return asdict(self)


_FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    m = _FM_RE.match(text)
    if not m:
        return {}, text
    fm: dict = {}
    body = text[m.end():]
    current_list_key: str | None = None
    for raw in m.group(1).splitlines():
        if not raw.strip():
            current_list_key = None
            continue
        if raw.startswith("  - ") and current_list_key:
            fm.setdefault(current_list_key, []).append(raw[4:].strip().strip('"'))
            continue
        current_list_key = None
        if ":" in raw:
            k, _, v = raw.partition(":")
            k = k.strip()
            v = v.strip().strip('"')
            if v == "":
                current_list_key = k
                fm[k] = []
            else:
                fm[k] = v
    return fm, body


def _score(haystack: str, terms: list[str]) -> int:
    s = 0
    low = haystack.lower()
    for t in terms:
        if not t:
            continue
        s += low.count(t.lower())
    return s


def search(
    query: str,
    *,
    extra_terms: list[str] | None = None,
    areas: list[str] | None = None,
    limit: int = 20,
    snippet_chars: int = 200,
) -> list[VaultHit]:
    """키워드 기반 단순 검색. frontmatter title/tags + 본문 매칭 점수.

    실패는 빈 리스트 반환. 호출자(스킬)가 is_available()로 분기.
    """
    if not is_available():
        return []

    terms = [t for t in [query, *(extra_terms or [])] if t and t.strip()]
    if not terms:
        return []

    hits: list[VaultHit] = []
    target_areas = areas or SEARCH_AREAS

    for area in target_areas:
        base = VAULT_ROOT / area
        if not base.exists():
            continue
        for md in base.rglob("*.md"):
            try:
                text = md.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            fm, body = _parse_frontmatter(text)

            title_score = _score(str(fm.get("title", "")), terms) * 5
            tags_score = _score(" ".join(fm.get("tags", []) if isinstance(fm.get("tags"), list) else []), terms) * 3
            slug_score = _score(str(fm.get("topic_slug", "")), terms) * 3
            body_score = _score(body, terms)

            total = title_score + tags_score + slug_score + body_score
            if total <= 0:
                continue

            snippet = body.strip().replace("\n", " ")[:snippet_chars]
            hits.append(VaultHit(
                path=str(md),
                area=area,
                title=str(fm.get("title", md.stem)),
                tags=fm.get("tags", []) if isinstance(fm.get("tags"), list) else [],
                snippet=snippet,
                score=total,
            ))

    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:limit]
