"""리뷰어 스킬(점수게이트)이 비문·오타를 평가·블로킹하는지 검증."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_manuscript_review_checks_bimun():
    t = (ROOT / "skills" / "manuscript-review" / "SKILL.md").read_text(encoding="utf-8")
    assert "비문" in t
    assert "오타" in t
    # 블로킹: 다수/심각 비문이면 점수 무관 REVISE 강제
    assert "verdict" in t and "REVISE" in t
    assert "블로킹" in t


def test_brief_review_checks_bimun():
    t = (ROOT / "skills" / "brief-review" / "SKILL.md").read_text(encoding="utf-8")
    assert "비문" in t
    assert "G6" in t          # 비문 게이트가 사전 블로킹 게이트에 편입
