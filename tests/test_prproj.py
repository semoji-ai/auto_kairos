from pathlib import Path
from sg.prproj import parse

FIX = Path(__file__).parent / "fixtures" / "mini.prproj.xml"


def test_parse_main_sequence_items():
    seqs = {s["uid"]: s for s in parse(FIX)}
    v = seqs["seq-main"]["tracks"][0]
    assert v["kind"] == "video"
    a, b = v["items"]
    assert (a["start"], a["end"], a["in"]) == (0.0, 10.0, 1.0)
    assert a["file"] == "C:\\work\\part_a.mp4" and a["seq_uid"] is None
    assert (b["start"], b["end"]) == (10.0, 15.0)
    assert b["file"] is None and b["seq_uid"] == "seq-nest"


def test_audio_item_has_level_and_keyframes():
    seqs = parse(FIX.parent / "level.prproj.xml")
    items = [i for s in seqs for t in s["tracks"] if t["kind"] == "audio" for i in t["items"]]
    it = [i for i in items if i["gain_keys"]][0]
    assert abs(it["gain"] - 0.1412537) < 1e-4
    assert it["gain_keys"][0] == [round(2196171694198 / 254016000000.0, 4), 0.141253754497]
    assert it["gain_keys"][-1][1] == 0.0


def test_item_without_level_defaults_to_unity():
    seqs = parse(FIX)
    a = [i for s in seqs for t in s["tracks"] for i in t["items"]]
    assert a and all(i["gain"] == 1.0 and i["gain_keys"] == [] for i in a)
