from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "skills" / "manuscript-write" / "SKILL.md"


def test_skill_instructs_scene_marker():
    t = SKILL.read_text(encoding="utf-8")
    assert "<!--SCENE-->" in t
    assert "마커는 사용하지 않습니다" not in t
