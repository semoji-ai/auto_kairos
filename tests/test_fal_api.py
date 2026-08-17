import base64
import json
from pathlib import Path
import urllib.error

import pytest

from backend import fal_api


def _png(tmp_path, name="s.png", data=b"\x89PNG-bytes"):
    p = tmp_path / name
    p.write_bytes(data)
    return p


def test_data_uri_encodes_png(tmp_path):
    p = _png(tmp_path, data=b"abc")
    uri = fal_api.data_uri(p)
    assert uri.startswith("data:image/png;base64,")
    assert base64.b64decode(uri.split(",", 1)[1]) == b"abc"


def test_edit_image_posts_expected_request(tmp_path, monkeypatch):
    src = _png(tmp_path, data=b"scene")
    seen = {}

    class _Resp:
        def __init__(self, payload):
            self._p = payload
        def read(self):
            return self._p
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    def _fake_urlopen(req, timeout=None):
        url = req.full_url
        if url.endswith("/edit"):
            seen["url"] = url
            seen["headers"] = {k.lower(): v for k, v in req.headers.items()}
            seen["body"] = json.loads(req.data.decode("utf-8"))
            return _Resp(json.dumps({"images": [{"url": "https://cdn.test/out.png",
                                                 "width": 1920, "height": 1080}]}).encode())
        seen["download"] = url
        return _Resp(b"OUTPUT-PNG")

    monkeypatch.setattr(fal_api.env, "get_key", lambda n: "KEY123" if n == "FAL_KEY" else "")
    monkeypatch.setattr(fal_api.urllib.request, "urlopen", _fake_urlopen)

    out = fal_api.edit_image("요소만 남겨라", [src])
    assert out == b"OUTPUT-PNG"
    assert seen["url"] == fal_api.ENDPOINT
    assert seen["headers"]["authorization"] == "Key KEY123"
    assert seen["body"]["prompt"] == "요소만 남겨라"
    assert seen["body"]["output_format"] == "png"
    assert seen["body"]["resolution"] == "2k"
    assert seen["body"]["num_images"] == 1
    assert seen["body"]["image_urls"][0].startswith("data:image/png;base64,")
    assert seen["download"] == "https://cdn.test/out.png"


def test_edit_image_truncates_to_three_images(tmp_path, monkeypatch):
    srcs = [_png(tmp_path, f"s{i}.png", data=bytes([i])) for i in range(5)]
    seen = {}

    class _Resp:
        def __init__(self, p):
            self._p = p
        def read(self):
            return self._p
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    def _fake(req, timeout=None):
        if req.full_url.endswith("/edit"):
            seen["n"] = len(json.loads(req.data.decode())["image_urls"])
            return _Resp(json.dumps({"images": [{"url": "https://cdn.test/o.png"}]}).encode())
        return _Resp(b"X")

    monkeypatch.setattr(fal_api.env, "get_key", lambda n: "K")
    monkeypatch.setattr(fal_api.urllib.request, "urlopen", _fake)
    fal_api.edit_image("p", srcs)
    assert seen["n"] == fal_api.MAX_INPUT_IMAGES == 3


def test_edit_image_without_key_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(fal_api.env, "get_key", lambda n: "")
    with pytest.raises(fal_api.FalError) as e:
        fal_api.edit_image("p", [_png(tmp_path)])
    assert "FAL_KEY" in str(e.value)


def test_edit_image_raises_on_empty_images(tmp_path, monkeypatch):
    class _Resp:
        def read(self):
            return json.dumps({"images": []}).encode()
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    monkeypatch.setattr(fal_api.env, "get_key", lambda n: "K")
    monkeypatch.setattr(fal_api.urllib.request, "urlopen", lambda req, timeout=None: _Resp())
    with pytest.raises(fal_api.FalError):
        fal_api.edit_image("p", [_png(tmp_path)])


def test_edit_image_raises_on_http_error(tmp_path, monkeypatch):
    def _fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 500, "Server Error", {}, None)

    monkeypatch.setattr(fal_api.env, "get_key", lambda n: "K")
    monkeypatch.setattr(fal_api.urllib.request, "urlopen", _fake_urlopen)
    with pytest.raises(fal_api.FalError):
        fal_api.edit_image("p", [_png(tmp_path)])


def test_api_key_accepts_either_name(monkeypatch):
    """v3의 .env는 같은 키를 FAL_API_KEY로 갖고 있다 — 비밀값을 복사하지 않고 둘 다 받는다."""
    monkeypatch.setattr(fal_api.env, "get_key",
                        lambda n: "K1" if n == "FAL_KEY" else "K2")
    assert fal_api.api_key() == "K1"                 # FAL_KEY 우선
    monkeypatch.setattr(fal_api.env, "get_key",
                        lambda n: "" if n == "FAL_KEY" else "K2")
    assert fal_api.api_key() == "K2"                 # 없으면 FAL_API_KEY
    monkeypatch.setattr(fal_api.env, "get_key", lambda n: "")
    assert fal_api.api_key() == ""


def test_edit_image_uses_fal_api_key_fallback(tmp_path, monkeypatch):
    seen = {}

    class _Resp:
        def __init__(self, p):
            self._p = p
        def read(self):
            return self._p
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    def _fake(req, timeout=None):
        if req.full_url.endswith("/edit"):
            seen["auth"] = {k.lower(): v for k, v in req.headers.items()}["authorization"]
            return _Resp(json.dumps({"images": [{"url": "https://cdn.test/o.png"}]}).encode())
        return _Resp(b"X")

    monkeypatch.setattr(fal_api.env, "get_key", lambda n: "FROMV3" if n == "FAL_API_KEY" else "")
    monkeypatch.setattr(fal_api.urllib.request, "urlopen", _fake)
    assert fal_api.edit_image("p", [_png(tmp_path)]) == b"X"
    assert seen["auth"] == "Key FROMV3"
