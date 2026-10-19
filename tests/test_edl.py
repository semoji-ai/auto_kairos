import pytest
from sg.edl import build_edl, pr_to_master, master_to_pr, part_to_master, part_anchors
from sg.timemap import PiecewiseMap


def seq_fixture():
    # 프리미어 V1: A 0~10(src 0), B 10~14(src 0), B 14~20(src 6: src 4~6 건너뜀), OUTRO 20~22
    it = lambda s, e, i, n: {"start": s, "end": e, "in": i, "out": None, "name": n, "file": None, "seq_uid": None, "speed": 1.0}
    return {"tracks": [{"kind": "video", "index": 0, "items": [
        it(0, 10, 0, "A.mp4"), it(10, 14, 0, "B.mp4"), it(14, 20, 6, "B.mp4"), it(20, 22, 0, "OUT.mov")]}]}


def edl():
    return build_edl(seq_fixture(), {"A.mp4": "a", "B.mp4": "b"}, "OUT.mov",
                     [{"pr_in": 16.0, "pr_out": 17.0, "reason": "yt"}])


def test_build_edl_parts_and_length():
    e = edl()
    assert [(p["id"], p["pr_in"], p["src_in"], p["dur"]) for p in e["parts"]] == [
        ("a", 0, 0, 10), ("b", 10, 0, 4), ("b", 14, 6, 6)]
    assert e["outro"] == {"clip": "OUT.mov", "pr_in": 20, "dur": 2}
    assert e["pr_length"] == 22 and e["length"] == 21


def test_pr_master_conversion():
    e = edl()
    assert pr_to_master(e, 15.0) == 15.0
    assert pr_to_master(e, 16.5) == 16.0                 # 컷 안 → 컷 시작으로
    assert pr_to_master(e, 16.5, clamp=False) is None
    assert pr_to_master(e, 18.0) == 17.0
    assert master_to_pr(e, 17.0) == 18.0


def test_part_to_master_skips_unused_source():
    e = edl()
    assert part_to_master(e, "b", 2.0) == 12.0
    assert part_to_master(e, "b", 5.0) is None           # 건너뛴 소스
    assert part_to_master(e, "b", 8.0) == 16.0


def test_part_anchors_identity_warp_collapses_skipped_source():
    e = edl()
    m, dur = part_anchors(e, PiecewiseMap.identity(), "b")
    assert m(0) == pytest.approx(0) and m(4) == pytest.approx(4)
    assert m(6) == pytest.approx(4)                      # src 4~6 접힘
    assert m(8) == pytest.approx(6)
    assert m(12) == pytest.approx(9)                     # 컷 1초 빠짐(pr 16~17)
    assert dur == pytest.approx(9)


def test_part_anchors_follow_master_warp():
    e = edl()
    w = PiecewiseMap([(0, 0), (10, 10), (12, 14), (21, 23)])   # 마스터 10~12가 2초 → 4초
    m, dur = part_anchors(e, w, "b")
    assert m(2) == pytest.approx(4)
    assert dur == pytest.approx(11)


def _seq(items):
    it = lambda s, e, i, n: {"start": s, "end": e, "in": i, "out": None, "name": n, "file": None, "seq_uid": None, "speed": 1.0}
    return {"tracks": [{"kind": "video", "index": 0, "items": [it(*x) for x in items]}]}


def test_subframe_source_overlap_between_clips_is_tolerated():
    # 프리미어 반올림: 앞 클립 소스 끝 13.214, 다음 클립 시작 13.213 (1ms 겹침)
    e = build_edl(_seq([(0, 8.342, 0.0, "B"), (8.342, 13.214, 8.342, "B"), (13.214, 20, 13.213, "B")]), {"B": "b"}, None, [])
    assert len(e["parts"]) == 3


def test_real_source_overlap_raises():
    with pytest.raises(ValueError):
        build_edl(_seq([(0, 10, 0.0, "B"), (10, 20, 9.0, "B")]), {"B": "b"}, None, [])


from sg.edl import part_span_to_master


def test_span_crossing_skipped_source_and_cut_keeps_pieces_outside():
    # 파트 b: src 0~4 → pr 10~14, src 6~12 → pr 14~20, 컷 pr 16~17
    # src 1~9: [1~4]→마스터 11~14, [6~9]→pr 14~17 → 컷 앞 14~16 → 마스터 14~16 → 이어 붙여 [11,16]
    assert part_span_to_master(edl(), "b", 1.0, 9.0) == [[11.0, 16.0]]


def test_span_starting_inside_cut_keeps_tail():
    # src 8.5~11 → pr 16.5~19 → 컷 뒤 17~19 → 마스터 16~18
    assert part_span_to_master(edl(), "b", 8.5, 11.0) == [[16.0, 18.0]]


def test_span_entirely_inside_cut_or_skipped_source_is_empty():
    assert part_span_to_master(edl(), "b", 8.2, 8.8) == []
    assert part_span_to_master(edl(), "b", 4.2, 5.8) == []


def test_clip_speed_change_is_rejected():
    seq = seq_fixture()
    seq["tracks"][0]["items"][0]["speed"] = 1.5
    with pytest.raises(ValueError):
        build_edl(seq, {"A.mp4": "a", "B.mp4": "b"}, "OUT.mov", [])


def test_part_anchors_raises_when_new_time_goes_backwards_beyond_float_noise():
    bad = {"parts": [{"id": "b", "clip": "B", "pr_in": 14, "src_in": 4, "dur": 2},
                     {"id": "b", "clip": "B", "pr_in": 10, "src_in": 6, "dur": 2}],
           "cuts": [], "outro": None, "pr_length": 20, "length": 20}
    with pytest.raises(ValueError):
        part_anchors(bad, PiecewiseMap.identity(), "b")
