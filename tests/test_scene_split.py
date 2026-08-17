from backend import scene_analysis


def test_split_two_scenes():
    text = "첫 씬 내레이션.\n<!--SCENE-->\n둘째 씬 내레이션."
    segs = scene_analysis.split_manuscript(text)
    assert len(segs) == 2
    assert segs[0]["narration"] == "첫 씬 내레이션."
    assert segs[1]["narration"] == "둘째 씬 내레이션."
    assert segs[0]["characters"] == []


def test_split_extracts_chars_and_strips_marker():
    text = "본문 한 줄.\n<!--CHARS: 소년, 의사-->\n이어지는 본문."
    segs = scene_analysis.split_manuscript(text)
    assert len(segs) == 1
    assert segs[0]["characters"] == ["소년", "의사"]
    assert "<!--CHARS" not in segs[0]["narration"]
    assert "본문 한 줄." in segs[0]["narration"] and "이어지는 본문." in segs[0]["narration"]


def test_split_no_marker_single_scene():
    segs = scene_analysis.split_manuscript("마커 없는 원고 전체.")
    assert len(segs) == 1 and segs[0]["narration"] == "마커 없는 원고 전체."


def test_split_drops_empty_segments():
    text = "씬1.\n<!--SCENE-->\n\n<!--SCENE-->\n씬3."
    segs = scene_analysis.split_manuscript(text)
    assert [s["narration"] for s in segs] == ["씬1.", "씬3."]
