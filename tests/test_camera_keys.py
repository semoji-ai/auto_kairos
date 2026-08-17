"""camera_keys — 카메라를 가이드 널 키프레임으로 굽는 변환.

입력 두 형태: 인수인계 문서의 화각 키 배열 [{t, rect, ease}] 와
구 모션 플랜·지도 기본값의 {type, amount}(하위호환 번역).
jsx는 계산하지 않으므로 여기 수치가 곧 화면이다."""
import pytest

from backend import manifest

F = 1080 / 1024          # 1792x1024 씬의 세로 기준 배율
OX = (1920 - 1792 * F) / 2


def _keys(cam, dur=10.0, sw=1792, sh=1024):
    return manifest.camera_keys(cam, sw=sw, sh=sh, f=F, ox=OX, dur=dur)


# ---- 구형 {type, amount} 번역 ----

def test_legacy_zoom_in():
    keys = _keys({"type": "slow_zoom_in", "amount": 6})
    assert len(keys) == 2
    assert keys[0] == {"t": 0.0, "scale": 100.0, "position": [960.0, 540.0]}
    assert keys[1]["t"] == 10.0
    assert keys[1]["scale"] == pytest.approx(106.0)
    assert keys[1]["position"] == [960.0, 540.0]
    assert keys[1]["ease"] == "70:30"


def test_legacy_zoom_out():
    keys = _keys({"type": "slow_zoom_out", "amount": 10})
    assert keys[0]["scale"] == pytest.approx(110.0)
    assert keys[1]["scale"] == pytest.approx(100.0)


def test_legacy_pan_matches_old_numbers():
    """이전 구현과 같은 수치 — pan_left는 널이 +x에서 -x로(화면이 왼쪽으로 흐름)."""
    keys = _keys({"type": "pan_left", "amount": 40})
    assert keys[0]["position"] == [980.0, 540.0]
    assert keys[1]["position"] == [940.0, 540.0]
    assert keys[0]["scale"] == 100.0 and keys[1]["scale"] == 100.0


def test_legacy_none_and_empty():
    assert _keys({"type": "none"}) == []
    assert _keys({}) == []
    assert _keys(None) == []


# ---- 화각 키 배열 변환 ----

def test_rect_conversion_applies_f_and_ox():
    """rect는 씬 이미지 좌표 — 레이어와 같은 f·ox 변환을 거친다(두 번 변환 금지)."""
    rect = [412, 180, 896, 504]              # 16:9 화각
    keys = _keys([{"t": 2.0, "rect": rect, "ease": "70:30"}])
    vx, vy, vw, vh = rect[0] * F + OX, rect[1] * F, rect[2] * F, rect[3] * F
    s = 1920 / vw
    cx, cy = vx + vw / 2, vy + vh / 2
    assert keys[0]["t"] == 2.0
    assert keys[0]["scale"] == pytest.approx(s * 100, abs=0.01)
    assert keys[0]["position"][0] == pytest.approx(960 - (cx - 960) * s, abs=0.05)
    assert keys[0]["position"][1] == pytest.approx(540 - (cy - 540) * s, abs=0.05)
    assert keys[0]["ease"] == "70:30"


def test_full_rect_is_near_100():
    """전체 화각은 배율이 100 근처(폭 채움 기준)여야 한다."""
    keys = _keys([{"t": 0.0, "rect": [0, 0, 1792, 1024]}])
    assert keys[0]["scale"] == pytest.approx(1920 / (1792 * F) * 100, abs=0.01)


def test_stationary_duplicate_keys_preserved():
    """정지 구간은 같은 rect 두 키 — 생략하면 AE가 계속 보간하므로 그대로 남겨야 한다."""
    r = [0, 0, 1792, 1024]
    keys = _keys([{"t": 0.0, "rect": r}, {"t": 5.0, "rect": r},
                  {"t": 7.0, "rect": [412, 180, 896, 504]}])
    assert len(keys) == 3
    assert keys[0]["scale"] == keys[1]["scale"]
    assert keys[0]["position"] == keys[1]["position"]


def test_invalid_rect_skipped():
    keys = _keys([{"t": 0.0, "rect": [0, 0, 0, 100]},        # 폭 0
                  {"t": 1.0, "rect": [0, 0, 100]},            # 길이 3
                  {"t": 2.0},                                  # rect 없음
                  {"t": 3.0, "rect": [0, 0, 1792, 1024]}])
    assert len(keys) == 1
    assert keys[0]["t"] == 3.0


def test_ease_absent_means_no_key():
    keys = _keys([{"t": 0.0, "rect": [0, 0, 1792, 1024]}])
    assert "ease" not in keys[0]
