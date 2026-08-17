"""Seedream layerize 호출 — 프롬프트·요청 형태·응답 파싱."""
import json
from pathlib import Path

import pytest

from backend import fal_api

FIXTURE = Path(__file__).resolve().parents[1] / "docs" / "notes" / "seedream-layerize-trial-response.json"


def _png(tmp_path, name="scene.png", data=b"SCENE"):
    p = tmp_path / name
    p.write_bytes(data)
    return p


class _Resp:
    def __init__(self, payload):
        self._p = payload
    def read(self):
        return self._p
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


def _fake_transport(seen, payload):
    """POST는 payload를, 그 외(레이어 다운로드)는 URL을 본뜬 바이트를 돌려준다."""
    def _open(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if url == fal_api.LAYERIZE_ENDPOINT:
            seen["headers"] = {k.lower(): v for k, v in req.headers.items()}
            seen["body"] = json.loads(req.data.decode("utf-8"))
            return _Resp(json.dumps(payload).encode())
        seen.setdefault("downloads", []).append(url)
        return _Resp(b"PNG:" + url.encode()[-6:])
    return _open


def test_prompt_lists_names_and_never_says_background():
    """background를 이름으로 쓰면 구멍 뚫린 배경 요소가 한 장 더 온다 — 절대 쓰지 않는다."""
    p = fal_api.build_layerize_prompt(["white electric car", "man on the right"])
    assert "white electric car" in p and "man on the right" in p
    assert "background" not in p.lower()


def test_layerize_posts_expected_request(tmp_path, monkeypatch):
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    seen = {}
    monkeypatch.setattr(fal_api, "api_key", lambda: "KEY1")
    monkeypatch.setattr(fal_api.urllib.request, "urlopen", _fake_transport(seen, payload))

    layers = fal_api.layerize(_png(tmp_path), ["white electric car"])
    assert seen["headers"]["authorization"] == "Key KEY1"
    assert seen["body"]["image_url"].startswith("data:image/png;base64,")
    assert seen["body"]["image_size"] == "auto"
    assert "white electric car" in seen["body"]["prompt"]
    assert len(layers) == 6                       # 픽스처 실측: z0 배경판 + 이름 5장
    assert len(seen["downloads"]) == 6


def test_layerize_returns_layers_sorted_with_plate_first(tmp_path, monkeypatch):
    """z0은 이름·bbox가 없는 인페인팅 배경판 — 항상 맨 앞."""
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    monkeypatch.setattr(fal_api, "api_key", lambda: "K")
    monkeypatch.setattr(fal_api.urllib.request, "urlopen", _fake_transport({}, payload))

    layers = fal_api.layerize(_png(tmp_path), ["white electric car"])
    assert [L["z"] for L in layers] == [0, 1, 2, 3, 4, 5]
    assert layers[0]["name"] is None and layers[0]["bbox"] is None
    car = [L for L in layers if L["name"] == "white electric car"][0]
    assert car["bbox"] == [344, 500, 1254, 912]   # 실측 bbox
    assert car["data"].startswith(b"PNG:")


def test_layerize_without_key_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(fal_api, "api_key", lambda: "")
    with pytest.raises(fal_api.FalError):
        fal_api.layerize(_png(tmp_path), ["a"])


def test_layerize_empty_layers_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(fal_api, "api_key", lambda: "K")
    monkeypatch.setattr(fal_api.urllib.request, "urlopen",
                        _fake_transport({}, {"images": [], "layers": []}))
    with pytest.raises(fal_api.FalError):
        fal_api.layerize(_png(tmp_path), ["a"])


def test_layerize_requires_names(tmp_path, monkeypatch):
    monkeypatch.setattr(fal_api, "api_key", lambda: "K")
    with pytest.raises(fal_api.FalError):
        fal_api.layerize(_png(tmp_path), [])


def test_layer_without_url_raises(tmp_path, monkeypatch):
    """요청한 요소가 조용히 빠지면 호출자는 성공한 줄 안다 — 반드시 알린다."""
    payload = {"images": [], "layers": [
        {"image": {"url": ""}, "z_index": 2, "name": "car", "bounding_box": None}]}
    monkeypatch.setattr(fal_api, "api_key", lambda: "K")
    monkeypatch.setattr(fal_api.urllib.request, "urlopen", _fake_transport({}, payload))
    with pytest.raises(fal_api.FalError) as e:
        fal_api.layerize(_png(tmp_path), ["car"])
    assert "car" in str(e.value)


def test_missing_z_index_sorts_last_not_as_plate(tmp_path, monkeypatch):
    """z_index 결측을 0으로 뭉개면 배경판 자리를 빼앗는다."""
    payload = {"images": [], "layers": [
        {"image": {"url": "https://example.com/u1"}, "z_index": None, "name": "car",
         "bounding_box": {"absolute": [1, 2, 3, 4]}},
        {"image": {"url": "https://example.com/u2"}, "z_index": 0, "name": None, "bounding_box": None}]}
    monkeypatch.setattr(fal_api, "api_key", lambda: "K")
    monkeypatch.setattr(fal_api.urllib.request, "urlopen", _fake_transport({}, payload))
    layers = fal_api.layerize(_png(tmp_path), ["car"])
    assert layers[0]["name"] is None          # 배경판이 먼저
    assert layers[1]["name"] == "car" and layers[1]["z"] is None
