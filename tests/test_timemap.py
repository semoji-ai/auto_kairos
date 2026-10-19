import pytest
from sg.timemap import PiecewiseMap


def test_identity():
    m = PiecewiseMap.identity()
    assert m(0) == 0 and m(12.5) == 12.5 and m(-3) == -3


def test_interpolation_and_extrapolation():
    m = PiecewiseMap([(0, 0), (10, 15), (20, 20)])
    assert m(5) == pytest.approx(7.5)
    assert m(15) == pytest.approx(17.5)
    assert m(-2) == pytest.approx(-2)      # 앞쪽 기울기 1
    assert m(25) == pytest.approx(25)      # 뒤쪽 기울기 1


def test_collapsed_segment_is_allowed():
    m = PiecewiseMap([(0, 0), (10, 10), (19, 10), (30, 21)])
    assert m(14) == pytest.approx(10)
    assert m(30) == pytest.approx(21)


def test_rejects_non_monotonic():
    with pytest.raises(ValueError):
        PiecewiseMap([(0, 0), (10, 8), (5, 9)])
    with pytest.raises(ValueError):
        PiecewiseMap([(0, 0), (10, 8), (20, 7)])


def test_ratio():
    m = PiecewiseMap([(0, 0), (10, 12)])
    assert m.ratio(0, 10) == pytest.approx(1.2)


def test_child_map_for_precomp_layer():
    # 부모 시간 t = st + u*sx. 레이어 startTime 2→3, stretch 50%
    m = PiecewiseMap([(0, 0), (10, 20)])
    c = m.child(st_old=2.0, st_new=3.0, sx=0.5)
    # 자식 u=4 → 부모 old 4 → new 8 → 자식 new (8-3)/0.5 = 10
    assert c(4) == pytest.approx(10)


def test_to_list_roundtrip():
    a = [(0.0, 0.0), (1.0, 2.0)]
    assert PiecewiseMap(a).to_list() == [[0.0, 0.0], [1.0, 2.0]]
