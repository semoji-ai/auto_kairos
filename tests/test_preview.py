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
