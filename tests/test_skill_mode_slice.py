"""script-director SKILL.md 모드별 슬라이싱 검증.

토큰 낭비 감사(docs/token-waste-audit.md) 1번 항목 — 챕터 병렬 호출마다
SKILL.md 전문(44.5k자)을 재주입하던 것을 모드별 필요 섹션만 주입하도록 축소.
"""
from pathlib import Path

import pytest

from auto_agent.orchestrator.skill_slicer import slice_agent_skill

SKILL_PATH = (
    Path(__file__).parent.parent
    / "auto_agent" / "data" / "skills" / "agents" / "script-director" / "SKILL.md"
)


@pytest.fixture(scope="module")
def skill_text() -> str:
    return SKILL_PATH.read_text(encoding="utf-8")


def test_non_script_director_untouched(skill_text):
    """다른 에이전트는 슬라이싱하지 않는다."""
    assert slice_agent_skill(skill_text, "draft-writer", "chapters") == skill_text


def test_unknown_mode_untouched(skill_text):
    """모르는 모드는 원본 유지 (안전 기본값)."""
    assert slice_agent_skill(skill_text, "script-director", None) == skill_text
    assert slice_agent_skill(skill_text, "script-director", "weird") == skill_text


def test_frontmatter_preserved(skill_text):
    """frontmatter(allowed_tools 등)는 모든 모드에서 보존."""
    for mode in ("manuscript", "chapters", "consistency", "outline"):
        out = slice_agent_skill(skill_text, "script-director", mode)
        assert out.startswith("---")
        assert "allowed_tools:" in out


def test_only_active_mode_section_kept(skill_text):
    """다단계 실행 모드 섹션에서 활성 모드만 남는다."""
    out = slice_agent_skill(skill_text, "script-director", "chapters")
    assert "모드 2: Chapter Split" in out
    assert "모드 1.5: Manuscript Mode" not in out
    assert "모드 3: Consistency Mode" not in out


def test_chapters_keeps_scene_direction_rules(skill_text):
    """챕터 모드는 씬 연출 규칙이 반드시 남아야 한다."""
    out = slice_agent_skill(skill_text, "script-director", "chapters")
    for required in ("씬 스키마", "에셋 결정 규칙", "headline 규칙", "모션 프리셋"):
        assert required in out, f"chapters 모드에 {required} 누락"
    # 씬 작성 실무(Step 2)는 유지, 아웃라인/검증 단계는 제거
    assert "Step 2: 챕터별 씬 작성" in out
    assert "Step 1: 구조 설계" not in out


def test_manuscript_drops_scene_direction(skill_text):
    """manuscript 모드는 prose 전용 — 연출 섹션 제거 (SKILL.md 모드 1.5 명시)."""
    out = slice_agent_skill(skill_text, "script-director", "manuscript")
    assert "모드 1.5: Manuscript Mode" in out
    for dropped in ("## 씬 스키마", "## 에셋 결정 규칙", "## 모션 프리셋"):
        assert dropped not in out, f"manuscript 모드에 {dropped} 잔존"
    # 기획 의도/금지 사항 같은 공통 규칙은 유지
    assert "Editorial Brief 준수 체크리스트" in out
    assert "## 금지 사항" in out


def test_meaningful_size_reduction(skill_text):
    """실질 절감이 있어야 한다 (챕터 25%+, manuscript 60%+)."""
    full = len(skill_text)
    ch = len(slice_agent_skill(skill_text, "script-director", "chapters"))
    ms = len(slice_agent_skill(skill_text, "script-director", "manuscript"))
    assert ch < full * 0.75, f"chapters 절감 부족: {ch}/{full}"
    assert ms < full * 0.40, f"manuscript 절감 부족: {ms}/{full}"
