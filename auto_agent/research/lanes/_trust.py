"""Tier 분류 — auto_agent/research/trust_tiers.json 기반."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from auto_agent.research.lanes._text import extract_domain


def _domain_match(domain: str, pattern: str) -> bool:
    domain = (domain or "").lower()
    pattern = (pattern or "").lower()
    if pattern.startswith("*."):
        suffix = pattern[1:]  # ".go.kr"
        return domain.endswith(suffix) or domain == suffix.lstrip(".")
    return domain == pattern or domain.endswith("." + pattern)


@lru_cache(maxsize=1)
def _load_tiers() -> dict:
    path = Path(__file__).resolve().parents[1] / "trust_tiers.json"
    if not path.exists():
        return {"A": {}, "B": {}, "C": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"A": {}, "B": {}, "C": {}}


def _flatten_domains(group: dict) -> list[str]:
    out: list[str] = []
    for k, v in (group or {}).items():
        if k.startswith("_"):
            continue
        if isinstance(v, list):
            out.extend(v)
    return out


def classify_tier(url: str, *, publisher: str = "") -> str:
    """url의 도메인 신뢰도 tier를 반환. 'A' | 'B' | 'C' | 'unknown'."""
    domain = extract_domain(url)
    if not domain:
        return "unknown"
    tiers = _load_tiers()
    for tier_label in ("C", "A", "B"):  # C 먼저 확인 (excluded 우선)
        for pattern in _flatten_domains(tiers.get(tier_label, {})):
            if _domain_match(domain, pattern):
                return tier_label
    return "unknown"


def is_evidence_eligible(url: str, *, publisher: str = "") -> bool:
    """이 source가 evidence로 채택 가능한지 (Tier A/B만)."""
    return classify_tier(url, publisher=publisher) in ("A", "B")
