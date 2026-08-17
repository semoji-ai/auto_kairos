"""레이어 낱개 삭제·재생성 — 사이드카 왕복, _prev 보존, 배경 재생성 대상."""
import json

import pytest

from backend import imagegen


def _layers_dir(tmp_path):
    d = tmp_path / "layers"
    d.mkdir(parents=True)
    return d


def _touch(d, name):
    (d / name).write_bytes(b"\x89PNG")
    return d / name


def test_write_and_load_element_specs(tmp_path):
    d = _layers_dir(tmp_path)
    specs = [{"layer": "ab__0_인물_char", "index": 0, "name": "왼쪽 인물",
              "location": "화면 좌측", "kind": "character"}]
    imagegen.write_element_specs(d, "ab", specs)
    assert (d / "ab__elements.json").is_file()
    assert imagegen.load_element_specs(d, "ab") == specs


def test_load_element_specs_recovers_from_filenames(tmp_path):
    """사이드카 없는 옛 프로젝트 — 파일명 + kinds.json으로 복원(location만 빈다)."""
    d = _layers_dir(tmp_path)
    _touch(d, "ab__0_왼쪽_인물_char.png")
    _touch(d, "ab__1_탁자.png")
    _touch(d, "ab__bg.png")                      # 배경은 요소가 아님
    (d / "ab__kinds.json").write_text(json.dumps({"ab__0_왼쪽_인물_char": "character"}),
                                      encoding="utf-8")
    specs = imagegen.load_element_specs(d, "ab")
    assert [s["index"] for s in specs] == [0, 1]
    assert specs[0]["kind"] == "character" and specs[1]["kind"] == "object"
    assert specs[0]["name"] == "왼쪽 인물" and specs[0]["location"] == ""


def test_is_background_layer():
    assert imagegen.is_background_layer("layers/ab__bg.png") is True
    assert imagegen.is_background_layer("ab__bg_v2") is True
    assert imagegen.is_background_layer("ab__0_인물.png") is False


def test_regenerate_missing_spec_errors(tmp_path):
    _layers_dir(tmp_path)
    res = imagegen.regenerate_layer(tmp_path, str(tmp_path / "scene.png"), "ab", "ab__7_없음")
    assert "error" in res
