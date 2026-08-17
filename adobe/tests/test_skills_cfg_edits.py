from pathlib import Path
from backend import skills_cfg, edits


def test_build_prompt_includes_recent_edits(tmp_path):
    skills = tmp_path / "skills" / "x"; skills.mkdir(parents=True)
    (skills / "SKILL.md").write_text("스킬 지시", encoding="utf-8")
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "plan.md").write_text("원래", encoding="utf-8")
    edits.save_file(proj, "plan.md", "사용자가 고침")
    cfg = {"inputs": ["plan.md"], "output": "o.md", "output_kind": "md"}
    prompt = skills_cfg.build_prompt(tmp_path / "skills", "x", cfg, proj)
    assert "최근 사용자 수정 내역" in prompt and "사용자가 고침" in prompt


def test_build_prompt_no_edits_clean(tmp_path):
    skills = tmp_path / "skills" / "x"; skills.mkdir(parents=True)
    (skills / "SKILL.md").write_text("스킬", encoding="utf-8")
    proj = tmp_path / "p"; proj.mkdir()
    cfg = {"inputs": [], "output": "o.md", "output_kind": "md"}
    assert "최근 사용자 수정 내역" not in skills_cfg.build_prompt(tmp_path / "skills", "x", cfg, proj)
