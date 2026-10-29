from sg.timemap import PiecewiseMap
from sg.vcompare import sample_pairs


def test_pairs_follow_map_and_skip_collapsed_and_anchor_edges():
    m = PiecewiseMap([(0, 0), (10, 12), (14, 12), (20, 18)])
    pr = sample_pairs(m, 0, 20, 1.0)
    ts = [a for a, _ in pr]
    assert 5.0 in ts and dict(pr)[5.0] == 6.0
    assert not any(10.0 <= a <= 14.0 for a in ts)       # 접힘 + 경계 제외
    assert 0.0 not in ts                                  # 앵커 경계 ±0.2 제외


def test_pairs_beyond_warped_video_end_are_dropped():
    m = PiecewiseMap([(0, 0), (10, 11)])
    pr = sample_pairs(m, 0, 10, 1.0, max_new=9.5)
    assert pr and max(n for _, n in pr) <= 9.5
