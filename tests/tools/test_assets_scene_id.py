# tests/tools/test_assets_scene_id.py
import json
import pytest
from pathlib import Path
from auto_agent.tools.image_assets import _get_scene as img_get_scene, _load as img_load, _save as img_save
from auto_agent.tools.audio_assets import _get_scene as audio_get_scene, _load as audio_load, _save as audio_save


def _make_img_dir(tmp_path, scenes_data):
    d = tmp_path / "images"
    d.mkdir()
    (d / "image_assets.json").write_text(json.dumps({"scenes": scenes_data}))
    return d


def _make_audio_dir(tmp_path, scenes_data):
    d = tmp_path / "audio"
    d.mkdir()
    (d / "audio_assets.json").write_text(json.dumps({"scenes": scenes_data}))
    return d


def test_image_get_scene_by_scene_id(tmp_path):
    img_dir = _make_img_dir(tmp_path, [
        {"sceneId": "abc12345", "sceneNumber": 5, "images": []}
    ])
    data = img_load(img_dir)
    scene = img_get_scene(data, scene_num=5, scene_id="abc12345")
    assert scene["sceneId"] == "abc12345"


def test_image_get_scene_fallback_no_scene_id(tmp_path):
    # sceneId 없는 레거시 데이터
    img_dir = _make_img_dir(tmp_path, [
        {"sceneNumber": 3, "images": []}
    ])
    data = img_load(img_dir)
    scene = img_get_scene(data, scene_num=3, scene_id=None)
    assert scene["sceneNumber"] == 3


def test_image_get_scene_creates_new_with_scene_id(tmp_path):
    img_dir = _make_img_dir(tmp_path, [])
    data = img_load(img_dir)
    scene = img_get_scene(data, scene_num=10, scene_id="newid123")
    assert scene["sceneId"] == "newid123"
    assert scene["sceneNumber"] == 10


def test_audio_get_scene_by_scene_id(tmp_path):
    audio_dir = _make_audio_dir(tmp_path, [
        {"sceneId": "xyz99999", "sceneNumber": 2, "selected": None, "versions": []}
    ])
    data = audio_load(audio_dir)
    scene = audio_get_scene(data, scene_num=2, scene_id="xyz99999")
    assert scene["sceneId"] == "xyz99999"


def test_audio_get_scene_fallback_no_scene_id(tmp_path):
    audio_dir = _make_audio_dir(tmp_path, [
        {"sceneNumber": 4, "selected": None, "versions": []}
    ])
    data = audio_load(audio_dir)
    scene = audio_get_scene(data, scene_num=4, scene_id=None)
    assert scene["sceneNumber"] == 4


def test_audio_get_scene_creates_new_with_scene_id(tmp_path):
    audio_dir = _make_audio_dir(tmp_path, [])
    data = audio_load(audio_dir)
    scene = audio_get_scene(data, scene_num=7, scene_id="newaudio456")
    assert scene["sceneId"] == "newaudio456"
    assert scene["sceneNumber"] == 7
