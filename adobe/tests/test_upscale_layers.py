"""레이어 업스케일 — 제자리 교체, 원본은 백업 폴더로.

`_up` 을 붙여 옆에 두면 매니페스트가 `<sid>__*.png` 를 훑다가 **레이어가 한 장
더 생긴 것으로 잡는다.** 사이드카에도 없으니 자리를 몰라 폴백을 탄다.

제자리에 두어야 bbox·z·motion 이 그대로 살고, 배율은 매니페스트가 다시
계산한다 — `scale = bbox폭 ÷ PNG폭 × …` 이라 분모가 커진 만큼 배율이 줄어
**화면 크기는 그대로**다.
"""
import json

import pytest
from PIL import Image

from backend import upscale_layers as ul


def _proj(tmp_path, png=(400, 300), bbox=(100, 100, 900, 700)):
    L = tmp_path / "layers"; L.mkdir(parents=True)
    Image.new("RGBA", (1792, 1024), (9, 9, 9, 255)).save(L / "ab__bg.png")
    Image.new("RGBA", png, (200, 30, 40, 255)).save(L / "ab__0_잔.png")
    (L / "ab__elements.json").write_text(json.dumps(
        [{"layer": "ab__0_잔", "bbox": list(bbox), "z": 1}]), encoding="utf-8")
    return tmp_path


def test_plan_picks_only_what_is_small(tmp_path):
    """이미 큰 것은 건드리지 않는다 — 시간과 디스크를 쓸 이유가 없다."""
    d = _proj(tmp_path, png=(400, 300), bbox=(100, 100, 900, 700))
    # 화면 폭 = 800 × (1080/1024) ≈ 844 · PNG 400 → 0.47배
    got = ul.plan(d, want=2.0)
    assert [x["stem"] for x in got] == ["ab__0_잔"]
    assert got[0]["ratio"] < 1
    # 넉넉한 PNG 는 안 고른다
    d2 = _proj(tmp_path / "b", png=(3000, 2000))
    assert ul.plan(d2, want=2.0) == []


def test_background_and_extras_are_skipped(tmp_path):
    """배경판·덤 레이어는 자리를 몰라 건드리지 않는다."""
    d = _proj(tmp_path)
    L = d / "layers"
    Image.new("RGBA", (50, 50)).save(L / "ab__x_덤.png")
    stems = [x["stem"] for x in ul.plan(d, want=99)]
    assert "ab__bg" not in stems and "ab__x_덤" not in stems


def test_replace_keeps_the_original(tmp_path, monkeypatch):
    """원본을 지우지 않는다 — 백업 폴더로 옮겨 남긴다."""
    d = _proj(tmp_path)
    L = d / "layers"

    def _fake(src, out, **kw):
        with Image.open(src) as im:
            im.resize((im.width * 2, im.height * 2)).save(out)
        return {"status": "completed"}

    up = ul._tools()
    monkeypatch.setattr(up, "upscale_image", _fake)
    monkeypatch.setattr(up, "upscayl_available", lambda: True)

    r = ul.upscale_one(d, "ab__0_잔")
    assert r["ok"] and r["was"] == [400, 300] and r["now"] == [800, 600]
    assert Image.open(L / "ab__0_잔.png").size == (800, 600)     # 제자리 교체
    bak = L / ul.BACKUP / "ab__0_잔.png"
    assert bak.is_file() and Image.open(bak).size == (400, 300)  # 원본은 남는다
    # 두 번 돌려도 백업이 업스케일본으로 덮이지 않는다
    ul.upscale_one(d, "ab__0_잔")
    assert Image.open(bak).size == (400, 300)


def test_restore_puts_it_back(tmp_path, monkeypatch):
    d = _proj(tmp_path)
    up = ul._tools()
    monkeypatch.setattr(up, "upscayl_available", lambda: True)
    monkeypatch.setattr(up, "upscale_image", lambda s, o, **k: (
        Image.open(s).resize((800, 600)).save(o), {"status": "completed"})[1])
    ul.upscale_one(d, "ab__0_잔")
    assert ul.restore(d, "ab__0_잔")["ok"]
    assert Image.open(d / "layers" / "ab__0_잔.png").size == (400, 300)


def test_no_temp_file_left_behind(tmp_path, monkeypatch):
    """실패해도 찌꺼기를 남기지 않는다 — 글롭에 잡히면 레이어가 하나 더 생긴다."""
    d = _proj(tmp_path)
    up = ul._tools()
    monkeypatch.setattr(up, "upscayl_available", lambda: True)
    monkeypatch.setattr(up, "upscale_image", lambda s, o, **k: {"status": "failed"})
    r = ul.upscale_one(d, "ab__0_잔")
    assert not r["ok"]
    assert not list((d / "layers").glob("*__up_tmp*"))
    assert Image.open(d / "layers" / "ab__0_잔.png").size == (400, 300)
