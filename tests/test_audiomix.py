import numpy as np
from sg.audiomix import flatten, to_master, warp_piece, sound_chunks, place_chunk
from sg.timemap import PiecewiseMap

EDL = {"parts": [], "cuts": [{"pr_in": 100.0, "pr_out": 109.0}], "outro": None, "pr_length": 200.0, "length": 191.0}


def tl():
    return [{"sequence": "main", "uid": "M", "tracks": [
                {"kind": "audio", "index": 2, "items": [
                    {"start": 10.0, "end": 20.0, "in": 5.0, "out": 15.0, "name": "a.mp3", "file": "a.mp3", "seq_uid": None, "speed": 1.0, "gain": 0.5, "gain_keys": []},
                    {"start": 50.0, "end": 60.0, "in": 0.0, "out": 10.0, "name": "nest", "file": None, "seq_uid": "N", "speed": 1.0, "gain": 1.0, "gain_keys": []}]}]},
            {"sequence": "nest", "uid": "N", "tracks": [
                {"kind": "audio", "index": 0, "items": [
                    {"start": 2.0, "end": 8.0, "in": 30.0, "out": 36.0, "name": "b.mp3", "file": "b.mp3", "seq_uid": None, "speed": 1.0, "gain": 0.25, "gain_keys": []}]}]}]


def test_flatten_expands_nested_sequence_with_offsets_and_gain():
    p = flatten(tl(), "M", [2])
    assert [(x["name"], x["pr_in"], x["pr_out"], x["src_in"]) for x in p] == [("a.mp3", 10.0, 20.0, 5.0), ("b.mp3", 52.0, 58.0, 30.0)]
    assert p[1]["gain"] == 0.25          # 중첩 안 클립 gain × 바깥 클립 gain(1.0)


def test_to_master_splits_piece_across_cut():
    p = to_master([{"name": "c", "file": "c", "pr_in": 95.0, "pr_out": 115.0, "src_in": 0.0, "gain": 1.0, "gain_keys": []}], EDL)
    assert [(x["m_in"], x["m_out"], x["src_in"]) for x in p] == [(95.0, 100.0, 0.0), (100.0, 106.0, 14.0)]


def test_warp_piece_longer_than_source_is_capped_with_fade():
    T = PiecewiseMap([[0, 0], [100, 150]])
    w = warp_piece({"m_in": 10.0, "m_out": 30.0, "src_in": 5.0}, T, src_len=30.0)
    assert w["t"] == 15.0 and w["dur"] == 25.0 and w["fade_out"] > 0   # 원래 30 > 남은 소스 25


def test_warp_piece_shorter_gets_fade_and_longer_has_none():
    T = PiecewiseMap([[0, 0], [100, 80]])
    assert warp_piece({"m_in": 0.0, "m_out": 10.0, "src_in": 0.0}, T, 100.0)["fade_out"] > 0
    T = PiecewiseMap([[0, 0], [100, 120]])
    assert warp_piece({"m_in": 0.0, "m_out": 10.0, "src_in": 0.0}, T, 100.0)["fade_out"] == 0


def test_sound_chunks_splits_on_silence():
    sr = 16000
    x = np.zeros(sr * 3, np.float32); x[sr // 2: sr] = 0.5; x[2 * sr: 2 * sr + sr // 4] = 0.5
    c = sound_chunks(x, sr)
    assert len(c) == 2 and abs(c[0][0] - 0.5) < 0.05 and abs(c[1][1] - 2.25) < 0.05


def test_place_chunk_inside_cut_is_dropped():
    T = PiecewiseMap([[0, 0], [200, 200]])
    assert place_chunk(101.0, 102.0, 0.0, 0.0, EDL, T) is None
    assert place_chunk(110.0, 111.0, 0.0, 0.0, EDL, T)["t"] == 101.0


def test_to_master_second_piece_gets_its_own_pr_in():
    p = to_master([{"name": "c", "file": "c", "pr_in": 95.0, "pr_out": 115.0, "src_in": 0.0, "gain": 1.0, "gain_keys": []}], EDL)
    assert [(x["pr_in"], x["pr_out"]) for x in p] == [(95.0, 100.0), (109.0, 115.0)]


def test_chunk_segments_split_across_cut():
    from sg.audiomix import chunk_segments
    # 효과음 wav가 프리미어 90초에 src 0으로 놓임, 덩어리 wav 8~14초 = 프리미어 98~104 → 컷(100~109)에 걸침
    seg = chunk_segments(8.0, 14.0, 90.0, 0.0, EDL)
    assert seg == [(8.0, 10.0, 98.0)]                      # 컷 안(100~104)은 사라짐
    seg = chunk_segments(17.0, 21.0, 90.0, 0.0, EDL)      # 프리미어 107~111 → 컷 뒤 109~111만, 마스터 100~102
    assert seg == [(19.0, 21.0, 100.0)]


def test_contiguous_same_song_pieces_have_no_fade_between():
    from sg.audiomix import join_fades
    w = [{"name": "a", "t": 0.0, "dur": 5.0, "fade_out": 0.33}, {"name": "a", "t": 5.0, "dur": 4.0, "fade_out": 0.33},
         {"name": "b", "t": 9.0, "dur": 3.0, "fade_out": 0.33}]
    assert [x["fade_out"] for x in join_fades(w)] == [0.0, 0.33, 0.33]
