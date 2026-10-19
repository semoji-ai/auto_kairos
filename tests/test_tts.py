from sg.tts import speech_bounds


def test_bounds_skip_leading_and_trailing_space_and_punct():
    al = {"characters": [" ", "H", "i", ".", " "],
          "character_start_times_seconds": [0.0, 0.30, 0.42, 0.55, 0.60],
          "character_end_times_seconds": [0.30, 0.42, 0.55, 0.60, 1.40]}
    assert speech_bounds(al) == (0.30, 0.55)


def test_bounds_on_plain_text():
    al = {"characters": list("ok"), "character_start_times_seconds": [0.1, 0.2],
          "character_end_times_seconds": [0.2, 0.35]}
    assert speech_bounds(al) == (0.1, 0.35)


from sg.tts import text_hash, should_synth


def test_should_synth_skips_unchanged_text_unless_forced(tmp_path):
    mp3 = tmp_path / "n001.mp3"; mp3.write_bytes(b"x")
    fit = {"n001": {"hash": text_hash("Hello.")}}
    assert should_synth(fit, "n001", "Hello.", str(mp3), force=False) is False
    assert should_synth(fit, "n001", "Hello!", str(mp3), force=False) is True
    assert should_synth(fit, "n001", "Hello.", str(mp3), force=True) is True
    assert should_synth({}, "n001", "Hello.", str(mp3), force=False) is True
