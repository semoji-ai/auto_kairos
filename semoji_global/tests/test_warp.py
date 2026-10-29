import pytest
from sg.warp import build_warp

SEG = [{"id": "a", "in": 1.0, "out": 4.0}, {"id": "b", "in": 5.0, "out": 9.0}]


def test_no_change_is_identity():
    m = build_warp(SEG, {}, [], 12.0)
    for t in (0, 1, 3, 4.5, 9, 12):
        assert m(t) == pytest.approx(t)


def test_longer_segment_shifts_rest():
    m = build_warp(SEG, {"a": 4.5}, [], 12.0)   # a: 3초 → 4.5초
    assert m(1.0) == pytest.approx(1.0)
    assert m(4.0) == pytest.approx(5.5)
    assert m(5.0) == pytest.approx(6.5)          # 간격 1초 유지
    assert m(9.0) == pytest.approx(10.5)
    assert m(12.0) == pytest.approx(13.5)


def test_cut_collapses_region():
    m = build_warp(SEG, {}, [(4.2, 4.8)], 12.0)
    assert m(4.2) == pytest.approx(m(4.8))
    assert m(12.0) == pytest.approx(11.4)


def test_segment_inside_cut_is_dropped():
    m = build_warp(SEG, {"b": 10.0}, [(4.5, 9.5)], 12.0)
    assert m(12.0) == pytest.approx(7.0)


def test_cut_crossing_segment_raises():
    with pytest.raises(ValueError):
        build_warp(SEG, {}, [(3.0, 4.5)], 12.0)


def test_overlapping_segments_raise():
    with pytest.raises(ValueError):
        build_warp([{"id": "a", "in": 1, "out": 4}, {"id": "b", "in": 3, "out": 6}], {}, [], 10)
