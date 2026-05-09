"""v4 통합 로더(load_research_v4, load_manuscript_v4) 테스트."""
from pathlib import Path

from auto_agent.dashboard.v4_artifacts import (
    list_md_files,
    list_drafts,
    parse_review_scores,
    load_research_v4,
    load_manuscript_v4,
)

FIXTURE = Path(__file__).parent / "v4_fixtures" / "abc12345_test"


def test_list_md_files_returns_each_file_with_frontmatter_and_content():
    result = list_md_files(FIXTURE / "research_reports")
    assert len(result) == 2
    slugs = {r["slug"] for r in result}
    assert slugs == {"topic-1", "topic-2"}
    fresh = next(r for r in result if r["slug"] == "topic-1")
    assert fresh["frontmatter"]["kind"] == "fresh"
    assert "사실 1입니다" in fresh["content"]


def test_list_md_files_missing_dir_returns_empty():
    assert list_md_files(FIXTURE / "nonexistent_dir") == []


def test_list_drafts_sorted_by_version():
    result = list_drafts(FIXTURE / "drafts")
    assert len(result) == 2
    assert result[0]["version"] == 1
    assert result[1]["version"] == 2
    assert "초안 v2 본문" in result[1]["content"]


def test_list_drafts_missing_dir_returns_empty():
    assert list_drafts(FIXTURE / "nonexistent_dir") == []


def test_parse_review_scores_extracts_score_per_version():
    result = parse_review_scores(FIXTURE / "review")
    assert len(result) == 1
    assert result[0]["version"] == 2
    assert result[0]["viewer_score"] == 8.6
    assert result[0]["expert_verdict"] == "PASS"


def test_parse_review_scores_missing_dir_returns_empty():
    assert parse_review_scores(FIXTURE / "nonexistent_dir") == []


def test_load_research_v4_aggregates_all_sections():
    result = load_research_v4(FIXTURE)
    # frontmatter 제거된 본문만 포함 — body 내 "한 줄 요약" 섹션 헤더 확인
    assert "한 줄 요약" in result["plan_md"]
    assert "테스트 픽스처" in result["plan_md"]
    # frontmatter는 제거됐으므로 plan_md에 없어야 함
    assert "project_id: abc12345" not in result["plan_md"]
    assert len(result["fresh_reports"]) == 2
    assert len(result["targeted"]) == 1
    assert result["targeted"][0]["slug"] == "q-1"


def test_load_research_v4_empty_project_returns_empty_keys():
    empty = FIXTURE.parent / "nonexistent_project"
    result = load_research_v4(empty)
    assert result["plan_md"] == ""
    assert result["fresh_reports"] == []
    assert result["targeted"] == []


def test_load_manuscript_v4_includes_drafts_review_final():
    result = load_manuscript_v4(FIXTURE)
    assert len(result["drafts"]) == 2
    assert len(result["review_scores"]) == 1
    assert "최종 원고 본문" in result["final_manuscript"]
    assert result["final_marked"] == ""


def test_load_manuscript_v4_empty_project():
    empty = FIXTURE.parent / "nonexistent_project"
    result = load_manuscript_v4(empty)
    assert result["drafts"] == []
    assert result["review_scores"] == []
    assert result["final_manuscript"] == ""
    assert result["final_marked"] == ""
