from sg.mixgraph import volume_expr, entry


def test_volume_expr_constant_gain():
    assert volume_expr(0.5, [], "clip", 0.0, 10.0) == "0.5"


def test_volume_expr_keyframes_clip_base_are_offset_by_placement():
    e = volume_expr(1.0, [[2.0, 1.0], [4.0, 0.0]], "clip", 0.0, 10.0)
    # 출력 시각 12~14초에서 1→0 선형
    assert "between(t,12.0,14.0)" in e and "gte(t,14.0)" in e


def test_volume_expr_media_base_subtracts_src_in():
    e = volume_expr(1.0, [[7.0, 1.0], [9.0, 0.0]], "media", 5.0, 10.0)
    assert "between(t,12.0,14.0)" in e


def test_entry_trims_source_and_delays():
    args, flt = entry("x.mp3", 3.0, 1.5, 2.0, 0.5, [], "clip", 0.0)
    assert args == ["-ss", "1.5", "-t", "2.0", "-i", "x.mp3"]
    assert "adelay=3000|3000" in flt and "volume=" in flt
