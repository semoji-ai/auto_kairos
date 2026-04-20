# tests/tools/test_scene_split.py
import json, shutil
import pytest
from pathlib import Path
from auto_agent.tools.scene_split import split_narration_by_sentence, renumber_files, apply_split_to_specs

def test_split_narration_half():
    narration = "첫 번째 문장입니다. 두 번째 문장입니다. 세 번째 문장입니다. 네 번째 문장입니다."
    a, b = split_narration_by_sentence(narration)
    assert a.strip() != ""
    assert b.strip() != ""
    assert "첫 번째" in a
    assert "네 번째" in b

def test_split_narration_single_sentence():
    narration = "하나의 문장만 있습니다."
    a, b = split_narration_by_sentence(narration)
    assert a == narration
    assert b == ""

def test_apply_split_inserts_new_scene():
    specs = {
        "scenes": [
            {"sceneNumber": 1, "sceneId": "id000001", "narration": "씬 1"},
            {"sceneNumber": 2, "sceneId": "id000002", "narration": "씬 2 앞부분. 씬 2 뒷부분."},
            {"sceneNumber": 3, "sceneId": "id000003", "narration": "씬 3"},
        ]
    }
    result = apply_split_to_specs(specs, scene_num=2, narration_a="씬 2 앞부분.", narration_b="씬 2 뒷부분.")
    scenes = result["scenes"]
    assert len(scenes) == 4
    assert scenes[1]["sceneNumber"] == 2
    assert scenes[1]["narration"] == "씬 2 앞부분."
    assert scenes[1]["sceneId"] == "id000002"  # 기존 sceneId 유지
    assert scenes[2]["sceneNumber"] == 3
    assert scenes[2]["narration"] == "씬 2 뒷부분."
    assert scenes[2]["sceneId"] != "id000002"  # 새 sceneId
    assert scenes[3]["sceneNumber"] == 4  # 기존 씬3 → 씬4
    assert scenes[3]["sceneId"] == "id000003"  # sceneId 불변

def test_apply_split_legacy_no_scene_id():
    specs = {
        "scenes": [
            {"sceneNumber": 1, "narration": "씬 1"},
            {"sceneNumber": 2, "narration": "씬 2 앞. 씬 2 뒤."},
        ]
    }
    result = apply_split_to_specs(specs, scene_num=2, narration_a="씬 2 앞.", narration_b="씬 2 뒤.")
    assert len(result["scenes"]) == 3
    assert result["scenes"][2]["narration"] == "씬 2 뒤."

def test_renumber_files(tmp_path):
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    (audio_dir / "scene_003.mp3").write_bytes(b"audio3")
    (audio_dir / "scene_004.mp3").write_bytes(b"audio4")
    renumber_files(tmp_path, from_scene=3, is_legacy=True)
    assert (audio_dir / "scene_004.mp3").read_bytes() == b"audio3"
    assert (audio_dir / "scene_005.mp3").read_bytes() == b"audio4"
