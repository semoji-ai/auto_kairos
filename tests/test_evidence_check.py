"""evidence_check 단위 테스트."""
from __future__ import annotations

from auto_agent.research.evidence_check import (
    MAX_SPAN_LEN,
    MIN_SPAN_LEN,
    verify_evidence,
    verify_span_in_chunk,
)


# ─────────────────────────────────────────────
# verify_span_in_chunk 기본
# ─────────────────────────────────────────────

def test_exact_match():
    chunk = "1933년 12월, 자체 개발 진통소염제 안티푸라민을 출시했다. 국내 최초의 연고제이자 현재까지 판매 중인 장수 브랜드이다."
    span = "1933년 12월, 자체 개발 진통소염제 안티푸라민을 출시했다."
    ok, reason = verify_span_in_chunk(span, chunk)
    assert ok, f"실패: {reason}"


def test_whitespace_normalized():
    chunk = "유한양행은\n\n1926년에   설립되었습니다.   설립자는\t유일한이며 본사는 서울에 있습니다."
    span = "유한양행은 1926년에 설립되었습니다. 설립자는 유일한이며"
    ok, reason = verify_span_in_chunk(span, chunk)
    assert ok, f"실패: {reason}"


def test_curly_quote_normalized():
    chunk = '그는 "좋은 약을 만들자"는 신념으로 회사를 세웠다고 알려져 있습니다.'
    span = "그는 “좋은 약을 만들자”는 신념으로 회사를 세웠다고 알려져 있습니다."  # curly quotes
    ok, reason = verify_span_in_chunk(span, chunk)
    assert ok, f"실패: {reason}"


# ─────────────────────────────────────────────
# 길이 게이트
# ─────────────────────────────────────────────

def test_too_short_rejected():
    span = "안녕"  # 2자
    chunk = "안녕하세요. 이것은 충분히 긴 문장입니다."
    ok, reason = verify_span_in_chunk(span, chunk)
    assert not ok
    assert str(MIN_SPAN_LEN) in reason


def test_too_long_rejected():
    span = "x" * (MAX_SPAN_LEN + 10)
    chunk = span + " 추가"
    ok, reason = verify_span_in_chunk(span, chunk)
    assert not ok
    assert str(MAX_SPAN_LEN) in reason


def test_at_min_length_accepted():
    chunk = "1933년 12월에 안티푸라민을 출시한 유한양행은 한국 제약 산업의 대표 브랜드로 자리잡았다."
    span = chunk[:MIN_SPAN_LEN]
    ok, reason = verify_span_in_chunk(span, chunk)
    assert ok, f"실패: {reason}"


# ─────────────────────────────────────────────
# 거부 케이스
# ─────────────────────────────────────────────

def test_hallucinated_span_rejected():
    chunk = "유한양행은 1926년에 설립되었습니다. 진통제 안티푸라민이 대표 제품입니다."
    span = "유한양행 매출은 2025년 100조 원에 달했다고 발표했다고 합니다."
    ok, reason = verify_span_in_chunk(span, chunk)
    assert not ok
    assert "환각" in reason or "없음" in reason


def test_paraphrased_span_rejected():
    chunk = "1933년 12월, 자체 개발 진통소염제 안티푸라민을 출시했습니다. 매우 큰 의미가 있었죠."
    # 절반은 정확하지만 뒷부분이 paraphrase
    span = "1933년 12월, 자체 개발 진통소염제 안티푸라민을 만들었으며 한국 최초의 약품이었다."
    ok, reason = verify_span_in_chunk(span, chunk)
    assert not ok
    # paraphrase 진단 또는 단순 미매치 둘 중 하나
    assert reason


def test_empty_span_rejected():
    ok, reason = verify_span_in_chunk("", "충분히 긴 청크 텍스트가 여기에 있습니다.")
    assert not ok
    assert "비어" in reason


def test_empty_chunk_rejected():
    span = "유한양행은 1926년에 설립되었으며 한국 제약회사의 대표 브랜드입니다."
    ok, reason = verify_span_in_chunk(span, "")
    assert not ok
    assert "chunk_text" in reason


# ─────────────────────────────────────────────
# verify_evidence (래퍼)
# ─────────────────────────────────────────────

def test_verify_evidence_with_chunk_lookup():
    chunks = {
        "src_yuhan": "유한양행은 1926년에 설립되었습니다. 설립자는 유일한 박사로, 미국에서 귀국 후 회사를 세웠습니다.",
    }
    ev = {
        "source_id": "src_yuhan",
        "span": "유한양행은 1926년에 설립되었습니다. 설립자는 유일한 박사로",
    }
    ok, reason = verify_evidence(ev, lambda sid: chunks.get(sid))
    assert ok, f"실패: {reason}"


def test_verify_evidence_unknown_source():
    ev = {"source_id": "src_unknown", "span": "x" * 50}
    ok, reason = verify_evidence(ev, lambda sid: None)
    assert not ok
    assert "찾을 수 없" in reason


def test_verify_evidence_missing_source_id():
    ev = {"span": "x" * 50}
    ok, reason = verify_evidence(ev, lambda sid: "chunk text")
    assert not ok
    assert "source_id" in reason


def test_verify_evidence_not_dict():
    ok, reason = verify_evidence("string instead of dict", lambda sid: "x")
    assert not ok
