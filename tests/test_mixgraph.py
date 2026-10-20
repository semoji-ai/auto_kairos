import numpy as np
from sg.mixgraph import envelope, place


def test_envelope_constant_and_linear_ramp():
    t = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
    assert np.allclose(envelope(t, 0.5, []), 0.5)
    e = envelope(t, 1.0, [[1.0, 1.0], [3.0, 0.0]])     # 키 앞은 첫 값, 뒤는 마지막 값
    assert np.allclose(e, [1.0, 1.0, 0.5, 0.0, 0.0])


def test_place_adds_at_offset_with_gain_curve_and_fade():
    sr = 10
    buf = np.zeros((40, 2), np.float32)
    x = np.ones((20, 2), np.float32)
    place(buf, x, t=1.0, sr=sr, gain=np.full(20, 0.5), fade_out=1.0)
    assert buf[9].sum() == 0 and np.allclose(buf[10], 0.5)
    assert buf[29, 0] < 0.1 and buf[30].sum() == 0          # 끝 1초 페이드, 그 뒤 없음


def test_place_clips_at_buffer_end():
    buf = np.zeros((10, 2), np.float32)
    place(buf, np.ones((20, 2), np.float32), t=0.5, sr=10, gain=np.ones(20), fade_out=0)
    assert np.allclose(buf[5:], 1.0)


def test_level_gain_places_premiere_fade_at_clip_relative_time():
    # B209 Sand_Castle: 클립 시작 978.077, 키 8.6458→10.163 (선형 0.1413 → 0), key_base=clip
    from scripts.audio_mix import level_gain, SR
    piece = {"pr_in": 978.077, "src_in": 0.0, "gain": 0.0, "gain_keys": [],
             "levels": [{"clip_start": 978.077, "clip_in": 0.0, "gain": 0.1413, "keys": [[8.6458, 0.1413], [10.163, 0.0]]}]}
    g = level_gain(piece, 900.0, int(11 * SR), "clip")
    assert abs(g[int(5 * SR)] - 0.1413) < 1e-4            # 페이드 전
    assert abs(g[int(9.4044 * SR)] - 0.0707) < 2e-3        # 페이드 중간
    assert g[int(10.5 * SR)] == 0.0                        # 페이드 끝 뒤
