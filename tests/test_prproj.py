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
