"""v4_artifacts 모듈의 frontmatter 파서 테스트."""
from auto_agent.dashboard.v4_artifacts import parse_frontmatter, strip_frontmatter, read_or_empty
from pathlib import Path

FIXTURE = Path(__file__).parent / "v4_fixtures" / "abc12345_test"


def test_parse_frontmatter_returns_dict():
    text = "---\nkey: value\nnum: 42\n---\n\n본문"
    result = parse_frontmatter(text)
    assert result == {"key": "value", "num": 42}


def test_parse_frontmatter_no_block_returns_empty():
    text = "본문만 있음"
    assert parse_frontmatter(text) == {}


def test_parse_frontmatter_malformed_returns_empty():
    text = "---\n: : :\n---\n"
    result = parse_frontmatter(text)
    assert isinstance(result, dict)


def test_strip_frontmatter_returns_body_only():
    text = "---\nkey: value\n---\n\n본문 시작\n둘째 줄"
    body = strip_frontmatter(text)
    assert "key: value" not in body
    assert body.startswith("본문 시작")


def test_strip_frontmatter_no_block_returns_full_text():
    text = "본문만 있음"
    assert strip_frontmatter(text) == "본문만 있음"


def test_read_or_empty_existing_file():
    p = FIXTURE / "plan.md"
    text = read_or_empty(p)
    assert "테스트 영상 기획안" in text


def test_read_or_empty_missing_file_returns_empty_string():
    p = FIXTURE / "nonexistent.md"
    assert read_or_empty(p) == ""
