# tests/tools/test_scene_id.py
import pytest
from auto_agent.tools.scene_id import new_scene_id, get_scene_id, ensure_scene_ids

def test_new_scene_id_is_8char_hex():
    sid = new_scene_id()
    assert len(sid) == 8
    assert all(c in "0123456789abcdef" for c in sid)

def test_new_scene_id_unique():
    assert new_scene_id() != new_scene_id()

def test_get_scene_id_returns_existing():
    scene = {"sceneId": "abc12345", "sceneNumber": 1}
    assert get_scene_id(scene) == "abc12345"

def test_get_scene_id_fallback_to_none_for_number():
    scene = {"sceneNumber": 3}
    assert get_scene_id(scene) is None

def test_ensure_scene_ids_adds_missing():
    scenes = [{"sceneNumber": 1}, {"sceneNumber": 2, "sceneId": "existing1"}]
    result = ensure_scene_ids(scenes)
    assert result[0]["sceneId"] is not None
    assert len(result[0]["sceneId"]) == 8
    assert result[1]["sceneId"] == "existing1"
