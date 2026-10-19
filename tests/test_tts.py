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
