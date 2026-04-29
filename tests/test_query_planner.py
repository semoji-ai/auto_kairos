"""query_planner 단위 테스트 — LLM은 mock으로 대체."""
from __future__ import annotations

import json

from auto_agent.research.query_planner import (
    _build_prompt,
    _fallback_queries,
    _parse_response,
    plan_queries,
)


def test_parse_response_extracts_queries():
    raw = """텍스트가 좀 있어도
{
  "queries": [
    {"query": "유한양행", "rationale": "회사", "lang": "ko"},
    {"query": "유일한 박사", "rationale": "창업자", "lang": "ko"}
  ]
}
또 텍스트
"""
    out = _parse_response(raw)
    assert len(out) == 2
    assert out[0]["query"] == "유한양행"
    assert out[1]["lang"] == "ko"


def test_parse_response_drops_long_queries():
    raw = json.dumps({"queries": [
        {"query": "유한양행", "lang": "ko"},
        {"query": "x" * 100, "lang": "ko"},  # 너무 김 — drop
        {"query": "  ", "lang": "ko"},  # 빈 문자열 — drop
    ]})
    out = _parse_response(raw)
    assert len(out) == 1
    assert out[0]["query"] == "유한양행"


def test_parse_response_raises_on_no_json():
    try:
        _parse_response("그냥 텍스트만 있고 JSON 없음")
        assert False, "should raise"
    except ValueError:
        pass


def test_parse_response_raises_on_empty_queries():
    try:
        _parse_response('{"queries": []}')
        assert False, "should raise"
    except ValueError:
        pass


def test_fallback_uses_real_topic_when_short():
    brief = {"real_topic": "유한양행 100주년"}
    out = _fallback_queries(brief)
    assert len(out) == 1
    assert out[0]["query"] == "유한양행 100주년"


def test_fallback_drops_long_real_topic():
    brief = {
        "real_topic": "유일한 박사와 유한양행이 남긴 100개의 숫자로 읽는 한국 기업 정신의 원형"
    }
    # 통문장 → drop, slug fallback 사용
    out = _fallback_queries(brief, project_slug="유한양행_100주년")
    assert len(out) == 1
    assert out[0]["query"] == "유한양행"  # 슬러그 첫 토큰


def test_plan_queries_with_mock_invoker():
    def mock_llm(prompt: str) -> str:
        # 프롬프트가 brief를 포함하는지 가볍게 검증
        assert "<brief>" in prompt
        return json.dumps({"queries": [
            {"query": "유한양행", "rationale": "회사", "lang": "ko"},
            {"query": "유일한 박사", "rationale": "창업자", "lang": "ko"},
            {"query": "안티푸라민 1933", "rationale": "1호 제품", "lang": "ko"},
        ]})

    out = plan_queries(
        {"real_topic": "유한양행 100주년"},
        invoker=mock_llm,
    )
    assert len(out) == 3
    assert out[2]["query"] == "안티푸라민 1933"


def test_plan_queries_falls_back_on_invoker_error():
    def boom(prompt: str) -> str:
        raise RuntimeError("CLI not found")

    out = plan_queries(
        {"real_topic": "유한양행 100주년"},
        invoker=boom,
    )
    # fallback 활성화
    assert len(out) == 1
    assert out[0]["rationale"].startswith("fallback")


def test_plan_queries_falls_back_on_malformed_json():
    def bad(prompt: str) -> str:
        return "이상한 응답"

    out = plan_queries(
        {"real_topic": "유한양행"},
        invoker=bad,
    )
    assert len(out) == 1
    assert "fallback" in out[0]["rationale"]


def test_build_prompt_includes_only_relevant_fields():
    brief = {
        "real_topic": "유한양행",
        "core_question": "100년 의미",
        "_meta": "drop me",
        "secret": "drop me too",
    }
    prompt = _build_prompt(brief)
    assert "real_topic" in prompt
    assert "core_question" in prompt
    assert "_meta" not in prompt
    assert "secret" not in prompt
