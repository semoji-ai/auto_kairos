"""Evidence span 검증 — fact-retriever가 만든 인용이 실제 chunk에 들어있는지.

LLM이 가짜 인용(환각)을 만들지 못하게 강제. span은 chunk 원문에 substring으로
존재해야 채택. 한국어 띄어쓰기/구두점 변동은 normalize 후 비교.

spec: docs/superpowers/specs/2026-04-28-research-redesign.md (Phase 3)
"""
from __future__ import annotations

import re
from typing import Optional

MIN_SPAN_LEN = 30
MAX_SPAN_LEN = 300


def _normalize(text: str) -> str:
    """공백/제어문자 통합 + 일부 구두점 변동 흡수."""
    if not text:
        return ""
    # 모든 whitespace(공백/탭/줄바꿈/유니코드 공백)를 단일 스페이스로
    t = re.sub(r"\s+", " ", str(text))
    # 흔한 구두점 변동 정규화
    replacements = {
        "‘": "'", "’": "'", "“": '"', "”": '"',
        "–": "-", "—": "-", "…": "...",
    }
    for src, dst in replacements.items():
        t = t.replace(src, dst)
    return t.strip()


def verify_span_in_chunk(span: str, chunk_text: str) -> tuple[bool, Optional[str]]:
    """span이 chunk_text에 substring으로 들어있는지 검증.

    Returns:
        (ok, reason). ok=False일 때 reason은 거부 사유.

    규칙:
    - span 길이 30~300자 (normalize 전 기준)
    - normalize 후 chunk_text에 substring 매칭
    - 매칭 실패 시 부분 매치 진단 정보를 reason에 첨부
    """
    if not span or not span.strip():
        return False, "span 비어있음"

    raw_span = span.strip()
    if len(raw_span) < MIN_SPAN_LEN:
        return False, f"span 너무 짧음: {len(raw_span)}자 (최소 {MIN_SPAN_LEN}자)"
    if len(raw_span) > MAX_SPAN_LEN:
        return False, f"span 너무 김: {len(raw_span)}자 (최대 {MAX_SPAN_LEN}자)"

    if not chunk_text:
        return False, "chunk_text 비어있음 (검증 불가)"

    norm_span = _normalize(raw_span)
    norm_chunk = _normalize(chunk_text)

    if norm_span in norm_chunk:
        return True, None

    # 진단: 절반 매치되는지 (LLM이 살짝 paraphrase한 경우 식별)
    half = norm_span[: len(norm_span) // 2]
    if len(half) >= 15 and half in norm_chunk:
        return False, "span 일부만 chunk에 매치됨 (paraphrase 가능성). 원문 그대로 인용 필요."

    return False, "span이 chunk 원문에 없음 (환각 의심)"


def verify_evidence(evidence: dict, chunk_lookup) -> tuple[bool, Optional[str]]:
    """fact-retriever가 만든 evidence dict 검증.

    Args:
        evidence: {span, source_id, ...}
        chunk_lookup: callable(source_id) -> chunk_text 또는 None

    Returns:
        (ok, reason)
    """
    if not isinstance(evidence, dict):
        return False, "evidence가 dict가 아님"
    span = str(evidence.get("span") or "").strip()
    source_id = str(evidence.get("source_id") or "").strip()
    if not source_id:
        return False, "source_id 누락"
    chunk = chunk_lookup(source_id)
    if chunk is None:
        return False, f"source_id={source_id}에 해당하는 chunk를 찾을 수 없음"
    return verify_span_in_chunk(span, chunk)
