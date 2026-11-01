from sg.preview import plan_audio
from sg.timemap import PiecewiseMap


def test_plan_places_tts_and_nonverbal_at_warped_starts():
    segs = [{"id": "n001", "in": 1.0, "out": 3.0}, {"id": "n002", "in": 4.0, "out": 4.5, "nonverbal": True},
            {"id": "n003", "in": 5.0, "out": 7.0}]
    w = PiecewiseMap([(0, 0), (3, 4), (20, 21)])
    p = plan_audio(segs, w, "/t")
    assert p[0] == {"file": "/t/n001.mp3", "t": w(1.0), "id": "n001"}
    assert p[1]["kind"] == "nonverbal" and p[1]["src_in"] == 4.0 and p[1]["t"] == w(4.0)
    assert p[2]["t"] == w(5.0)


from sg.preview import part_to_wav


def test_part_time_to_wav_time_through_precomp_offset_and_layer_start():
    # 파트 시간 = (L.st + wav*sx) * k + off  → wav = ((u - off)/k - L.st)/sx
    L = {"st": 0.5, "sx": 100}
    occ = [{"k": 1.0, "off": 1.735, "span": [1.735, 337.6]}]
    assert abs(part_to_wav(10.0, L, occ) - (10.0 - 1.735 - 0.5)) < 1e-9
    assert part_to_wav(0.5, L, occ) is None          # 프리컴프 구간 밖


def test_mix_is_stale_when_older_than_parts_or_warp(tmp_path):
    import os, time
    from sg.preview import mix_is_fresh
    mix, part, warp = tmp_path / "mix.wav", tmp_path / "part.mp4", tmp_path / "warp.json"
    for f in (part, warp, mix):
        f.write_text("x"); time.sleep(0.01)
    assert mix_is_fresh(str(mix), [str(part), str(warp)])
    os.utime(part, (time.time() + 5, time.time() + 5))     # 파트를 다시 렌더함
    assert not mix_is_fresh(str(mix), [str(part), str(warp)])


def test_plan_skips_segments_blanked_in_translation():
    # 번역문을 비운 구간(장면 삭제)은 옛 TTS가 남아 있어도 내레이션에 넣지 않는다
    segs = [{"id": "n001", "in": 1.0, "out": 3.0}, {"id": "n002", "in": 4.0, "out": 6.0}]
    w = PiecewiseMap([(0, 0), (20, 20)])
    p = plan_audio(segs, w, "/t", blank={"n002"})
    assert [x["id"] for x in p] == ["n001"]
