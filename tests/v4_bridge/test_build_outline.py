"""
TDD tests for build_outline.py — plan.md → outline.json converter.
Schema ground truth: auto_agent/modules/v4_bridge/schema_samples/outline.example.json
"""
from pathlib import Path
import pytest
from auto_agent.modules.v4_bridge.build_outline import build_outline

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "plan.md"
PLAN_MD = FIXTURE_PATH.read_text(encoding="utf-8")


# ─── Top-level keys ───────────────────────────────────────────────────────────

def test_build_outline_top_level_keys():
    result = build_outline(PLAN_MD)
    assert "title" in result, "missing 'title'"
    assert "core_question" in result, "missing 'core_question'"
    assert "target_duration_minutes" in result, "missing 'target_duration_minutes'"
    assert "chapters" in result, "missing 'chapters'"


def test_build_outline_types():
    result = build_outline(PLAN_MD)
    assert isinstance(result["title"], str)
    assert isinstance(result["core_question"], str)
    assert isinstance(result["target_duration_minutes"], (int, float))
    assert isinstance(result["chapters"], list)


# ─── Chapter count and required sub-keys ──────────────────────────────────────

REQUIRED_CHAPTER_KEYS = {
    "chapter_number",
    "title",
    "act",
    "purpose",
    "duration_ratio",
    "research_focus",
    "key_points",
}


def test_build_outline_chapter_count():
    result = build_outline(PLAN_MD)
    # fixture has 3 chapters in 구조 가설
    assert len(result["chapters"]) == 3, (
        f"expected 3 chapters, got {len(result['chapters'])}"
    )


def test_build_outline_chapter_keys():
    result = build_outline(PLAN_MD)
    for i, ch in enumerate(result["chapters"]):
        missing = REQUIRED_CHAPTER_KEYS - set(ch.keys())
        assert not missing, f"chapter[{i}] missing keys: {missing}"


def test_build_outline_chapter_sub_types():
    result = build_outline(PLAN_MD)
    for i, ch in enumerate(result["chapters"]):
        assert isinstance(ch["chapter_number"], int), f"chapter[{i}].chapter_number not int"
        assert isinstance(ch["title"], str), f"chapter[{i}].title not str"
        assert isinstance(ch["act"], int), f"chapter[{i}].act not int"
        assert isinstance(ch["purpose"], str), f"chapter[{i}].purpose not str"
        assert isinstance(ch["duration_ratio"], float), f"chapter[{i}].duration_ratio not float"
        assert isinstance(ch["research_focus"], list), f"chapter[{i}].research_focus not list"
        assert isinstance(ch["key_points"], list), f"chapter[{i}].key_points not list"


# ─── Specific value spot-checks ───────────────────────────────────────────────

def test_build_outline_title_value():
    result = build_outline(PLAN_MD)
    assert "코카콜라" in result["title"], (
        f"title should contain '코카콜라', got: {result['title']}"
    )


def test_build_outline_core_question_nonempty():
    result = build_outline(PLAN_MD)
    assert len(result["core_question"]) > 5, "core_question is too short / empty"


def test_build_outline_duration_minutes_positive():
    result = build_outline(PLAN_MD)
    assert result["target_duration_minutes"] > 0, "target_duration_minutes must be positive"


def test_build_outline_chapter_numbers_sequential():
    result = build_outline(PLAN_MD)
    for i, ch in enumerate(result["chapters"]):
        assert ch["chapter_number"] == i + 1, (
            f"chapter_number should be {i+1}, got {ch['chapter_number']}"
        )


def test_build_outline_duration_ratio_sum():
    result = build_outline(PLAN_MD)
    total = sum(ch["duration_ratio"] for ch in result["chapters"])
    # sum should be close to 1.0 (within 5%)
    assert abs(total - 1.0) < 0.06, (
        f"duration_ratio sum should be ~1.0, got {total:.3f}"
    )


def test_build_outline_act_range():
    result = build_outline(PLAN_MD)
    acts = [ch["act"] for ch in result["chapters"]]
    assert all(1 <= a <= 3 for a in acts), f"all acts should be in [1,2,3], got {acts}"


# ─── Edge cases ───────────────────────────────────────────────────────────────

def test_build_outline_empty_string():
    result = build_outline("")
    assert result["title"] == ""
    assert result["chapters"] == []


def test_build_outline_no_chapters_section():
    minimal = "# 기획안 — 주제 없음\n\n## 한 줄 요약\n테스트용 간단 요약\n"
    result = build_outline(minimal)
    assert result["chapters"] == []
    assert isinstance(result["title"], str)
