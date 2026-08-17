import pytest
from backend import brief


def test_parse_plan_full(tmp_path):
    (tmp_path / "plan.md").write_text(
        "# 타이레놀 페이스리프트\n채널: semoji\n분량: 1분\n톤: 흥미로운 다큐\n",
        encoding="utf-8")
    p = brief.parse_plan(tmp_path)
    assert p["topic"] == "타이레놀 페이스리프트"
    assert p["writing_style"] == "semoji"
    assert p["duration"] == "1분"
    assert p["tone"] == "흥미로운 다큐"


def test_parse_plan_defaults_style_semoji(tmp_path):
    (tmp_path / "plan.md").write_text("# 주제만 있음\n", encoding="utf-8")
    p = brief.parse_plan(tmp_path)
    assert p["topic"] == "주제만 있음"
    assert p["writing_style"] == "semoji"   # 채널 없으면 기본


def test_parse_plan_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        brief.parse_plan(tmp_path)
