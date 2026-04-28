"""fact-retriever SKILL.md 정합성 테스트 — schema/구조 검증.

LLM은 호출하지 않음. SKILL.md frontmatter, 출력 스키마 명시 등을 정적 검사.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


SKILL_PATH = Path(__file__).resolve().parents[1] / "auto_agent" / "data" / "skills" / "agents" / "fact-retriever" / "SKILL.md"


@pytest.fixture
def skill_text() -> str:
    return SKILL_PATH.read_text(encoding="utf-8")


def test_skill_file_exists():
    assert SKILL_PATH.exists(), f"SKILL.md 누락: {SKILL_PATH}"


def test_frontmatter_required_fields(skill_text: str):
    fm_match = re.match(r"^---\s*\n(.*?)\n---", skill_text, re.DOTALL)
    assert fm_match, "frontmatter 블록 없음"
    fm = fm_match.group(1)
    assert "name: fact-retriever" in fm
    assert "model:" in fm
    assert "max_turns:" in fm
    assert "allowed_tools:" in fm


def test_frontmatter_max_turns_is_5(skill_text: str):
    """비용 통제 — max_turns: 5 강제."""
    assert re.search(r"max_turns:\s*5\b", skill_text), "max_turns 5 명시 필요"


def test_allowed_tools_no_websearch(skill_text: str):
    """fact-retriever는 외부 검색 안 함 (프로젝트 로컬만)."""
    fm = re.match(r"^---\s*\n(.*?)\n---", skill_text, re.DOTALL).group(1)
    assert "WebSearch" not in fm
    assert "Bash" not in fm
    assert "Read" in fm  # 필수


def test_skill_documents_5_step_workflow(skill_text: str):
    """1~5단계 명시 (메타 → claims 우선 → raw → 게이트 → tier)."""
    for label in ("1단계", "2단계", "3단계", "4단계", "5단계"):
        assert label in skill_text, f"{label} 명시 필요"


def test_skill_documents_evidence_span_constraints(skill_text: str):
    """30~300자 + substring + paraphrase 금지 명시."""
    assert "30" in skill_text and "300" in skill_text
    assert "substring" in skill_text
    assert "paraphrase" in skill_text


def test_skill_documents_claim_kind_gates(skill_text: str):
    """claim_kind 4종 차등 게이트 명시."""
    for kind in ("fact:date_or_number", "fact:event", "fact:context", "interpretation"):
        assert kind in skill_text, f"claim_kind {kind} 누락"


def test_skill_documents_tier_a_b_c(skill_text: str):
    """A/B/C tier 정의 명시."""
    assert "Tier" in skill_text or "tier" in skill_text
    assert "A" in skill_text and "B" in skill_text and "C" in skill_text
    assert "절대" in skill_text  # 금지 규칙 강조


def test_skill_documents_self_verification(skill_text: str):
    """자체 검증 단계 명시 (환각 방지)."""
    assert "환각" in skill_text
    assert "검증" in skill_text


def test_skill_output_is_json_object(skill_text: str):
    """출력은 항상 JSON 객체 — script-director 파싱 안전."""
    assert "JSON" in skill_text
    assert "found" in skill_text  # 필수 필드
    assert "evidence" in skill_text


def test_script_director_references_fact_retriever():
    """script-director가 fact-retriever SKILL.md를 참조하도록 통합되어 있음."""
    sd = SKILL_PATH.parent.parent / "script-director" / "SKILL.md"
    assert sd.exists()
    text = sd.read_text(encoding="utf-8")
    assert "fact-retriever" in text
    assert "claims_ledger" in text
    assert "evidence_span" in text or "evidence span" in text
