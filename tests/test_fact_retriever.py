"""fact_retriever subprocess 단위 테스트 — Claude CLI mock."""
from __future__ import annotations

import json
from pathlib import Path

from auto_agent.research.fact_retriever import (
    _build_prompt,
    _parse_response,
    _verify_evidence_against_chunk,
    fact_retrieve,
)


def test_parse_response_extracts_json():
    raw = """앞에 텍스트
{
  "found": true,
  "claim": "1898 펩시 창업",
  "evidence": {"span": "1898년에 창업", "source_id": "src_x", "anchor": "raw/x.md"},
  "tier": "A",
  "confidence": "high"
}
뒤에 텍스트
"""
    out = _parse_response(raw)
    assert out["found"] is True
    assert out["claim"] == "1898 펩시 창업"


def test_parse_response_with_code_fence():
    raw = '```json\n{"found": false, "reason": "not enough"}\n```'
    out = _parse_response(raw)
    assert out["found"] is False


def test_build_prompt_includes_skill_and_input():
    prompt = _build_prompt(
        query="펩시 1898 창업",
        entities=["Pepsi", "Caleb Bradham"],
        year=1898,
        claim_kind="fact:date_or_number",
        project_research_dir=Path("/tmp/x/research"),
    )
    assert "fact-retriever" in prompt
    assert "<input>" in prompt
    assert "1898" in prompt
    assert "Caleb Bradham" in prompt


def test_verify_evidence_against_chunk_ok(tmp_path: Path):
    research = tmp_path / "research"
    notes = research / "raw" / "topic" / "run" / "source_notes"
    notes.mkdir(parents=True)
    (notes / "src_x.md").write_text(
        "Pepsi was founded in 1898 by Caleb Bradham. The company started with a modest investment.",
        encoding="utf-8",
    )
    ev = {
        "span": "Pepsi was founded in 1898 by Caleb Bradham.",
        "source_id": "src_x",
        "anchor": "raw/topic/run/source_notes/src_x.md",
    }
    ok, reason = _verify_evidence_against_chunk(ev, research)
    assert ok, f"실패: {reason}"


def test_verify_evidence_rejects_hallucination(tmp_path: Path):
    research = tmp_path / "research"
    notes = research / "raw" / "topic" / "run" / "source_notes"
    notes.mkdir(parents=True)
    (notes / "src_x.md").write_text("Real content here is just plain text without claims.", encoding="utf-8")
    ev = {
        "span": "이것은 raw에 없는 환각 인용문이고 충분히 길어서 통과되면 안 됩니다 — 50자 이상.",
        "source_id": "src_x",
        "anchor": "raw/topic/run/source_notes/src_x.md",
    }
    ok, reason = _verify_evidence_against_chunk(ev, research)
    assert not ok
    assert reason


def test_verify_evidence_anchor_missing(tmp_path: Path):
    research = tmp_path / "research"
    research.mkdir()
    ev = {"span": "x" * 50, "source_id": "src_x", "anchor": "raw/nonexistent.md"}
    ok, reason = _verify_evidence_against_chunk(ev, research)
    assert not ok
    assert "없음" in reason


def test_fact_retrieve_with_mock_invoker(tmp_path: Path):
    research = tmp_path / "research"
    notes = research / "raw" / "x" / "run" / "source_notes"
    notes.mkdir(parents=True)
    (notes / "src_p.md").write_text(
        "1898년 캘럽 브래드햄이 노스캐롤라이나에서 펩시콜라를 창업했습니다.",
        encoding="utf-8",
    )

    def mock(prompt: str) -> str:
        assert "<input>" in prompt
        return json.dumps({
            "found": True,
            "claim": "1898 펩시 창업",
            "evidence": {
                "span": "1898년 캘럽 브래드햄이 노스캐롤라이나에서 펩시콜라를 창업했습니다.",
                "source_id": "src_p",
                "anchor": "raw/x/run/source_notes/src_p.md",
                "tier": "A",
            },
            "tier": "A",
            "confidence": "high",
            "claim_kind": "fact:date_or_number",
            "warnings": [],
        }, ensure_ascii=False)

    out = fact_retrieve(
        query="펩시 창업",
        project_research_dir=research,
        entities=["펩시콜라"],
        year=1898,
        claim_kind="fact:date_or_number",
        invoker=mock,
    )
    assert out["found"] is True
    assert out["claim"] == "1898 펩시 창업"


def test_fact_retrieve_rejects_when_evidence_verification_fails(tmp_path: Path):
    research = tmp_path / "research"
    notes = research / "raw" / "x" / "run" / "source_notes"
    notes.mkdir(parents=True)
    (notes / "src_p.md").write_text("실제 raw 내용이 다릅니다. 펩시 창업 1898 같은 직접 인용이 없음.", encoding="utf-8")

    def mock(prompt: str) -> str:
        return json.dumps({
            "found": True,
            "claim": "펩시 창업",
            "evidence": {
                # raw에 없는 환각 span (충분히 길어 길이 게이트 통과)
                "span": "1898년에 노스캐롤라이나에서 캘럽 브래드햄이 펩시콜라를 창업했다고 알려져 있습니다 — 50자 이상.",
                "source_id": "src_p",
                "anchor": "raw/x/run/source_notes/src_p.md",
                "tier": "A",
            },
            "tier": "A",
            "confidence": "high",
        })

    out = fact_retrieve(
        query="펩시 창업",
        project_research_dir=research,
        invoker=mock,
        verify_evidence=True,
    )
    # 외부 검증으로 거부
    assert out["found"] is False
    assert "evidence 검증 실패" in out["reason"]


def test_fact_retrieve_passthrough_when_not_found(tmp_path: Path):
    def mock(prompt: str) -> str:
        return json.dumps({"found": False, "reason": "관련 source 없음", "warnings": []})

    out = fact_retrieve(
        query="존재하지 않는 사실",
        project_research_dir=tmp_path,
        invoker=mock,
    )
    assert out["found"] is False
    assert "관련 source 없음" in out["reason"]


def test_fact_retrieve_handles_invoker_error(tmp_path: Path):
    def boom(prompt: str) -> str:
        raise RuntimeError("CLI 미설치")

    out = fact_retrieve(
        query="x",
        project_research_dir=tmp_path,
        invoker=boom,
    )
    assert out["found"] is False
    assert "CLI/parse 실패" in out["reason"]
