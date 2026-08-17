import pytest
from pathlib import Path
from backend import skills_cfg

SKILLS = Path(__file__).resolve().parents[1] / "skills"


def test_load_config():
    c = skills_cfg.load_config(SKILLS, "scene-decompose")
    assert c["output"] == "scenes.json"
    assert c["inputs"] == ["final_manuscript.md"]
    assert c["output_kind"] == "json"


def test_build_prompt_includes_skill_and_inputs(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "final_manuscript.md").write_text("원고내용ABC", encoding="utf-8")
    c = skills_cfg.load_config(SKILLS, "scene-decompose")
    prompt = skills_cfg.build_prompt(SKILLS, "scene-decompose", c, proj)
    assert "원고내용ABC" in prompt
    assert "scene-decompose" in prompt
    assert "scenes.json" in prompt


def test_missing_inputs(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    c = skills_cfg.load_config(SKILLS, "scene-decompose")
    missing = skills_cfg.missing_inputs(c, proj)
    assert "final_manuscript.md" in missing


def test_reference_list_config():
    c = skills_cfg.load_config(SKILLS, "reference-list")
    assert c["output"] == "references.json"
    assert c["schema"] == "references.schema.json"
    assert c["inputs"] == ["final_manuscript.md"]


PIPELINE = ["plan-explore", "deep-research", "draft-write",
            "target-research", "finalize-manuscript", "review-refine"]


@pytest.mark.parametrize("name", PIPELINE)
def test_pipeline_skill_configs_load(name):
    c = skills_cfg.load_config(SKILLS, name)
    assert c["name"] == name
    assert c["output"]
    assert (SKILLS / name / "SKILL.md").exists()


def _plan(proj, channel="semoji", duration="5분"):
    (proj / "plan.md").write_text(
        f"# 제목\n\n채널: {channel}\n분량: {duration}\n톤: 흥미로운 다큐\n", encoding="utf-8")


def _proj_for(tmp_path, name):
    proj = tmp_path / "p"; proj.mkdir()
    _plan(proj)
    c = skills_cfg.load_config(SKILLS, name)
    for f in c["inputs"]:
        fp = proj / f
        fp.parent.mkdir(parents=True, exist_ok=True)
        if not fp.exists():
            fp.write_text("x", encoding="utf-8")
    return proj, c


def test_final_stages_receive_plan():
    """target-research/finalize-manuscript/review-refine 이 plan.md 를 입력으로 받는다."""
    for name in ("target-research", "finalize-manuscript", "review-refine"):
        c = skills_cfg.load_config(SKILLS, name)
        assert "plan.md" in c["inputs"], name


def test_build_prompt_injects_voice_pack(tmp_path):
    """plan.md 채널: semoji → data/artstyle/semoji-voice.md 문체 가이드 자동 주입."""
    proj, c = _proj_for(tmp_path, "finalize-manuscript")
    prompt = skills_cfg.build_prompt(SKILLS, "finalize-manuscript", c, proj)
    assert "문체 가이드" in prompt
    assert "다고 합니다" in prompt          # 팩 시그니처가 실제 포함되는지


def test_build_prompt_no_voice_pack_ok(tmp_path):
    """정의 없는 채널이면 문체 주입 없이 정상 동작(실패 금지)."""
    proj, c = _proj_for(tmp_path, "finalize-manuscript")
    _plan(proj, channel="unknown-ch")
    prompt = skills_cfg.build_prompt(SKILLS, "finalize-manuscript", c, proj)
    assert "문체 가이드" not in prompt


def test_build_prompt_injects_duration_target(tmp_path):
    """분량: 5분 → 목표 글자수(분당 250~300자 → 1250~1500자)가 프롬프트에 포함."""
    proj, c = _proj_for(tmp_path, "draft-write")
    prompt = skills_cfg.build_prompt(SKILLS, "draft-write", c, proj)
    assert "5분" in prompt and "1,250" in prompt and "1,500" in prompt


def test_skill_md_duration_hardcoding_removed():
    for name in ("draft-write", "finalize-manuscript", "review-refine"):
        md = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
        assert "1분" not in md, name
