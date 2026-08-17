import json
from pathlib import Path

import pytest

from backend import vectorize

SID = "abc123"
SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0"/></svg>'


def _proj(tmp_path: Path, stems, specs=None):
    lay = tmp_path / "layers"
    lay.mkdir(parents=True)
    for stem in stems:
        (lay / (stem + ".png")).write_bytes(b"png")
    (lay / f"{SID}__elements.json").write_text(
        json.dumps(specs or [], ensure_ascii=False), encoding="utf-8")
    return tmp_path


def test_all_layers_vectorized(tmp_path, monkeypatch):
    proj = _proj(tmp_path, [f"{SID}__bg", f"{SID}__0_car"])
    monkeypatch.setattr(vectorize, "vectorize_png", lambda p, **kw: SVG)
    res = vectorize.vectorize_layers(proj, SID, [f"{SID}__bg", f"{SID}__0_car"])
    assert sorted(res["ok"]) == sorted([f"{SID}__bg", f"{SID}__0_car"])
    assert res["failed"] == []
    assert (proj / "layers" / f"{SID}__0_car.svg").read_bytes() == SVG


def test_partial_failure_keeps_going(tmp_path, monkeypatch):
    """3장 중 2번째가 실패해도 1·3번은 저장된다."""
    stems = [f"{SID}__0_a", f"{SID}__1_b", f"{SID}__2_c"]
    proj = _proj(tmp_path, stems)

    def flaky(path, **kw):
        if Path(path).stem == f"{SID}__1_b":
            raise vectorize.VectorizeError("서버 오류")
        return SVG

    monkeypatch.setattr(vectorize, "vectorize_png", flaky)
    res = vectorize.vectorize_layers(proj, SID, stems)
    assert sorted(res["ok"]) == [f"{SID}__0_a", f"{SID}__2_c"]
    assert len(res["failed"]) == 1
    assert res["failed"][0]["layer"] == f"{SID}__1_b"
    assert (proj / "layers" / f"{SID}__0_a.svg").is_file()
    assert (proj / "layers" / f"{SID}__2_c.svg").is_file()
    assert not (proj / "layers" / f"{SID}__1_b.svg").exists()


def test_existing_svg_is_skipped(tmp_path, monkeypatch):
    """이미 SVG가 있으면 API를 호출하지 않는다 — 크레딧을 또 쓰지 않는다."""
    proj = _proj(tmp_path, [f"{SID}__0_car"])
    (proj / "layers" / f"{SID}__0_car.svg").write_bytes(b"old")
    calls = []
    monkeypatch.setattr(vectorize, "vectorize_png",
                        lambda p, **kw: calls.append(p) or SVG)
    res = vectorize.vectorize_layers(proj, SID, [f"{SID}__0_car"])
    assert res["skipped"] == [f"{SID}__0_car"]
    assert res["ok"] == []
    assert calls == []
    assert (proj / "layers" / f"{SID}__0_car.svg").read_bytes() == b"old"


def test_force_overwrites_existing_svg(tmp_path, monkeypatch):
    """개별 재벡터화는 force로 기존 SVG를 덮어쓴다."""
    proj = _proj(tmp_path, [f"{SID}__0_car"])
    (proj / "layers" / f"{SID}__0_car.svg").write_bytes(b"old")
    monkeypatch.setattr(vectorize, "vectorize_png", lambda p, **kw: SVG)
    res = vectorize.vectorize_layers(proj, SID, [f"{SID}__0_car"], force=True)
    assert res["ok"] == [f"{SID}__0_car"]
    assert (proj / "layers" / f"{SID}__0_car.svg").read_bytes() == SVG


def test_removed_layer_is_not_vectorized(tmp_path, monkeypatch):
    specs = [{"layer": f"{SID}__0_car", "name": "차", "name_en": "car", "removed": True}]
    proj = _proj(tmp_path, [f"{SID}__0_car"], specs)
    calls = []
    monkeypatch.setattr(vectorize, "vectorize_png",
                        lambda p, **kw: calls.append(p) or SVG)
    res = vectorize.vectorize_layers(proj, SID, [f"{SID}__0_car"])
    assert calls == []
    assert res["ok"] == []
    assert res["skipped"] == [f"{SID}__0_car"]


def test_missing_png_is_failure(tmp_path, monkeypatch):
    proj = _proj(tmp_path, [])
    monkeypatch.setattr(vectorize, "vectorize_png", lambda p, **kw: SVG)
    res = vectorize.vectorize_layers(proj, SID, [f"{SID}__9_ghost"])
    assert len(res["failed"]) == 1
    assert res["failed"][0]["layer"] == f"{SID}__9_ghost"


def test_events_reported(tmp_path, monkeypatch):
    stems = [f"{SID}__0_a", f"{SID}__1_b"]
    proj = _proj(tmp_path, stems)
    monkeypatch.setattr(vectorize, "vectorize_png", lambda p, **kw: SVG)
    seen = []
    vectorize.vectorize_layers(proj, SID, stems, on_event=lambda e: seen.append(e))
    assert len(seen) == 2
    assert seen[0]["layer"] == f"{SID}__0_a"
    assert seen[0]["status"] == "completed"


def test_no_key_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(vectorize, "api_key", lambda: "")
    with pytest.raises(vectorize.VectorizeError):
        vectorize.vectorize_png(tmp_path / "x.png")


def test_multipart_body_has_file_and_format():
    body, ctype = vectorize._multipart({"response_format": "url"}, "file", b"PNGDATA", "a.png")
    assert ctype.startswith("multipart/form-data; boundary=")
    assert b'name="response_format"' in body
    assert b"url" in body
    assert b'name="file"; filename="a.png"' in body
    assert b"PNGDATA" in body


def test_endpoint_requires_key(tmp_path, monkeypatch):
    from backend import jobs as jobs_mod
    from backend import router
    proj = tmp_path / "p1"
    (proj / "layers").mkdir(parents=True)
    (proj / "layers" / f"{SID}__0_car.png").write_bytes(b"png")
    (proj / "scenes.json").write_text(json.dumps({"scenes": [
        {"sceneNumber": 1, "sceneId": SID, "title": "t", "narration": "n"}]},
        ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(vectorize, "api_key", lambda: "")
    status, res = router.handle_request(
        "POST", "/api/layers/vectorize", {},
        {"project_id": "p1", "sceneNumber": 1, "layers": [f"{SID}__0_car"]},
        {"root": tmp_path, "jobs": jobs_mod.JobRegistry()})
    assert status == 422
    assert "RECRAFT_API_KEY" in res["error"]


def test_endpoint_requires_layers(tmp_path, monkeypatch):
    from backend import jobs as jobs_mod
    from backend import router
    proj = tmp_path / "p1"
    (proj / "layers").mkdir(parents=True)
    (proj / "scenes.json").write_text(json.dumps({"scenes": [
        {"sceneNumber": 1, "sceneId": SID, "title": "t", "narration": "n"}]},
        ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(vectorize, "api_key", lambda: "k")
    status, res = router.handle_request(
        "POST", "/api/layers/vectorize", {},
        {"project_id": "p1", "sceneNumber": 1, "layers": []},
        {"root": tmp_path, "jobs": jobs_mod.JobRegistry()})
    assert status == 400


def test_non_dict_response_raises_error(tmp_path, monkeypatch):
    """Recraft가 dict가 아닌 JSON(예: 리스트)을 돌려주면 VectorizeError."""
    import urllib.request
    proj = _proj(tmp_path, [f"{SID}__0_car"])

    # API 키 설정
    monkeypatch.setattr(vectorize, "api_key", lambda: "test_key")

    def mock_urlopen(req, timeout=300):
        # 첫 번째 호출(벡터화 요청) → 리스트 반환 (dict가 아님)
        class MockResponse:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read(self):
                return b'[]'  # dict가 아닌 리스트
        return MockResponse()

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
    with pytest.raises(vectorize.VectorizeError) as exc_info:
        vectorize.vectorize_png(proj / "layers" / f"{SID}__0_car.png")
    assert "형식 오류" in str(exc_info.value) or "dict" in str(exc_info.value)


def test_unexpected_exception_doesnt_break_loop(tmp_path, monkeypatch):
    """vectorize_png가 VectorizeError도 OSError도 아닌 예외(RuntimeError)를 던져도
    vectorize_layers가 그 레이어만 failed에 담고 나머지는 계속 처리한다."""
    stems = [f"{SID}__0_ok", f"{SID}__1_err", f"{SID}__2_ok"]
    proj = _proj(tmp_path, stems)

    def boom(path, **kw):
        if Path(path).stem == f"{SID}__1_err":
            raise RuntimeError("예상치 못한 오류")
        return SVG

    monkeypatch.setattr(vectorize, "vectorize_png", boom)
    res = vectorize.vectorize_layers(proj, SID, stems)
    assert sorted(res["ok"]) == [f"{SID}__0_ok", f"{SID}__2_ok"]
    assert len(res["failed"]) == 1
    assert res["failed"][0]["layer"] == f"{SID}__1_err"
    # 오류 메시지에 예외 타입이 포함되어야 함
    assert "RuntimeError" in res["failed"][0]["error"]
