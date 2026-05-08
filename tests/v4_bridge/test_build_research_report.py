"""tests/v4_bridge/test_build_research_report.py

v4 research artifacts → v3 research_report.json 변환기 TDD.
fixtures:
  tests/v4_bridge/fixtures/research_reports/report_01.md  (fresh-research 형식)
  tests/v4_bridge/fixtures/research_targeted/targeted_01.md (target-research 형식)
"""

from pathlib import Path
import pytest

FIXTURES = Path(__file__).parent / "fixtures"
REPORTS_DIR = FIXTURES / "research_reports"
TARGETED_DIR = FIXTURES / "research_targeted"
EMPTY_DIR = FIXTURES / "nonexistent_dir_xyz"

from auto_agent.modules.v4_bridge.build_research_report import build_research_report


# ──────────────────────────────────────────────
# 1. Top-level keys all present
# ──────────────────────────────────────────────
def test_top_level_keys_present():
    result = build_research_report(REPORTS_DIR, TARGETED_DIR, topic="테스트 주제")
    required_keys = {"topic", "summary", "sections", "agent_results", "sources", "source_grades", "agents_deployed", "search_mode"}
    assert required_keys.issubset(result.keys()), f"누락 키: {required_keys - result.keys()}"


# ──────────────────────────────────────────────
# 2. topic 주입 및 기본값
# ──────────────────────────────────────────────
def test_topic_from_caller():
    result = build_research_report(REPORTS_DIR, TARGETED_DIR, topic="명시적 주제")
    assert result["topic"] == "명시적 주제"


def test_topic_fallback_from_frontmatter():
    """caller가 topic을 주지 않으면 reports frontmatter에서 추론."""
    result = build_research_report(REPORTS_DIR, TARGETED_DIR, topic="")
    assert result["topic"]  # 비어있지 않아야 함


# ──────────────────────────────────────────────
# 3. sections extracted from markdown headings
# ──────────────────────────────────────────────
def test_sections_extracted_from_reports():
    result = build_research_report(REPORTS_DIR, TARGETED_DIR)
    assert len(result["sections"]) >= 2, "## 헤딩 기반 섹션 2개 이상 기대"
    for sec in result["sections"]:
        assert "title" in sec
        assert "content" in sec


def test_sections_have_nonempty_titles():
    result = build_research_report(REPORTS_DIR, TARGETED_DIR)
    for sec in result["sections"]:
        assert sec["title"].strip(), "섹션 타이틀이 비어있음"


# ──────────────────────────────────────────────
# 4. sources have quality_grade
# ──────────────────────────────────────────────
def test_sources_have_quality_grade():
    result = build_research_report(REPORTS_DIR, TARGETED_DIR)
    assert len(result["sources"]) >= 3, "출처 3개 이상 기대"
    for src in result["sources"]:
        assert "quality_grade" in src, f"quality_grade 없음: {src}"
        assert src["quality_grade"] in ("A", "B", "C"), f"예상 외 등급: {src['quality_grade']}"


def test_source_grades_aggregated():
    result = build_research_report(REPORTS_DIR, TARGETED_DIR)
    assert isinstance(result["source_grades"], dict)
    total_in_grades = sum(result["source_grades"].values())
    assert total_in_grades == len(result["sources"]), "source_grades 합계 != sources 수"


# ──────────────────────────────────────────────
# 5. agents_deployed
# ──────────────────────────────────────────────
def test_agents_deployed_both_dirs():
    result = build_research_report(REPORTS_DIR, TARGETED_DIR)
    # reports/ 있음 → fresh-research, targeted/ 있음 → target-research
    assert result["agents_deployed"] == 2


def test_agents_deployed_reports_only():
    result = build_research_report(REPORTS_DIR, EMPTY_DIR)
    assert result["agents_deployed"] == 1


def test_agents_deployed_targeted_only():
    result = build_research_report(EMPTY_DIR, TARGETED_DIR)
    assert result["agents_deployed"] == 1


# ──────────────────────────────────────────────
# 6. agent_results from targeted/
# ──────────────────────────────────────────────
def test_agent_results_from_targeted():
    result = build_research_report(REPORTS_DIR, TARGETED_DIR)
    assert len(result["agent_results"]) >= 1
    for ar in result["agent_results"]:
        assert "title" in ar
        assert "content" in ar


# ──────────────────────────────────────────────
# 7. search_mode
# ──────────────────────────────────────────────
def test_search_mode_v4_mixed():
    result = build_research_report(REPORTS_DIR, TARGETED_DIR)
    assert result["search_mode"] == "v4-mixed"


# ──────────────────────────────────────────────
# 8. Sources deduplicated across reports/ + targeted/
# ──────────────────────────────────────────────
def test_sources_deduplicated():
    result = build_research_report(REPORTS_DIR, TARGETED_DIR)
    urls = [s["url"] for s in result["sources"]]
    assert len(urls) == len(set(urls)), "중복 URL 발견"


# ──────────────────────────────────────────────
# 9. Empty/missing directories handled gracefully
# ──────────────────────────────────────────────
def test_empty_reports_dir():
    result = build_research_report(EMPTY_DIR, TARGETED_DIR)
    assert isinstance(result["sections"], list)
    assert result["agents_deployed"] == 1  # targeted only


def test_empty_targeted_dir():
    result = build_research_report(REPORTS_DIR, EMPTY_DIR)
    assert isinstance(result["agent_results"], list)
    assert result["agents_deployed"] == 1  # reports only


def test_both_dirs_missing():
    result = build_research_report(EMPTY_DIR, EMPTY_DIR, topic="빈 테스트")
    assert result["topic"] == "빈 테스트"
    assert result["sections"] == []
    assert result["sources"] == []
    assert result["agents_deployed"] == 0


# ──────────────────────────────────────────────
# 10. Wikipedia URL → grade "A"
# ──────────────────────────────────────────────
def test_wikipedia_url_gets_grade_a():
    """wikipedia.org URL 포함 파일에서 A 등급 소스가 있어야 함."""
    # targeted_01.md에는 wikipedia URL 없음, 하지만 구현 로직 검증을 위해 직접 테스트
    from auto_agent.modules.v4_bridge.build_research_report import _infer_quality_grade
    assert _infer_quality_grade("https://en.wikipedia.org/wiki/Foo", "") == "A"
    assert _infer_quality_grade("https://example.com/page", "") == "B"
    assert _infer_quality_grade("https://example.com/page", "partial") == "C"
    assert _infer_quality_grade("https://example.com/page", "verified") == "A"
