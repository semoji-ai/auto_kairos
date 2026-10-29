"""삽입 구간 중 cut(빈 삽입) — 이어붙일 때 그 구간을 빼기만 한다."""
from scripts.inserts import splice_segments
from sg.timemap import PiecewiseMap


def test_cut_insert_drops_range_without_insert_piece():
    T = PiecewiseMap.identity()
    plan = {"intro": {"replace_master": [0.0, 10.0], "dur": 12.0},
            "cut_law": {"replace_master": [30.0, 50.0], "dur": 0.0, "cut": True}}
    segs = splice_segments(plan, T, 100.0)
    assert segs == [("ins", "intro"), ("prev", 10.0, 30.0), ("prev", 50.0, 100.0)]


def test_plain_inserts_unchanged():
    T = PiecewiseMap.identity()
    plan = {"end": {"replace_master": [90.0, 100.0], "dur": 5.0}}
    assert splice_segments(plan, T, 100.0) == [("prev", 0.0, 90.0), ("ins", "end")]
