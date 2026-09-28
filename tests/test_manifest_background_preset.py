from pathlib import Path

from auto_agent.scripts.build_manifest import _background_preset_path

GRID = "background/약설_그리드 배경.jpg"


def _public(tmp_path: Path) -> Path:
    public = tmp_path / "public"
    (public / "background").mkdir(parents=True)
    (public / GRID).write_bytes(b"jpg")
    return public


def test_text_overlay_without_image_maps_preset(tmp_path):
    scene = {"visual_mode": "text_overlay", "backgroundPreset": GRID}
    assert _background_preset_path(scene, "", _public(tmp_path)) == "/" + GRID


def test_selected_image_wins_over_preset(tmp_path):
    scene = {"visual_mode": "text_overlay", "backgroundPreset": GRID}
    assert _background_preset_path(scene, "project/images/x.png", _public(tmp_path)) == ""


def test_non_text_overlay_scene_is_ignored(tmp_path):
    scene = {"visual_mode": "scene", "backgroundPreset": GRID}
    assert _background_preset_path(scene, "", _public(tmp_path)) == ""


def test_missing_preset_file_is_ignored(tmp_path):
    scene = {"visual_mode": "text_overlay", "backgroundPreset": "background/없음.jpg"}
    assert _background_preset_path(scene, "", _public(tmp_path)) == ""


def test_explicit_image_source_none_keeps_blank(tmp_path):
    scene = {"visual_mode": "text_overlay", "backgroundPreset": GRID, "imageAsset": {"source": "none"}}
    assert _background_preset_path(scene, "", _public(tmp_path)) == ""


def test_leading_slash_is_normalised(tmp_path):
    scene = {"visual_mode": "text_overlay", "backgroundPreset": "/" + GRID}
    assert _background_preset_path(scene, "", _public(tmp_path)) == "/" + GRID
