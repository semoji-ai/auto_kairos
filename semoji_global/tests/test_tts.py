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


def test_zh_spoken_reads_years_digit_by_digit():
    from sg.tts import zh_spoken
    assert zh_spoken("1831年，") == "一八三一年，"
    assert zh_spoken("而从1850年代起，") == "而从一八五零年代起，"
    assert zh_spoken("在2025年Interbrand榜上") == "在二零二五年Interbrand榜上"


def test_zh_spoken_reads_month_and_day_as_numbers():
    from sg.tts import zh_spoken
    assert zh_spoken("1861年4月12日，") == "一八六一年，四月十二日，"
    assert zh_spoken("1888年8月16日，") == "一八八八年，八月十六日，"
    assert zh_spoken("1978年12月") == "一九七八年，十二月"


def test_zh_spoken_leaves_other_numbers():
    from sg.tts import zh_spoken
    assert zh_spoken("每升约含37克古柯叶，") == "每升约含37克古柯叶，"
    assert zh_spoken("投资2400美元") == "投资2400美元"
    assert zh_spoken("持续了20年") == "持续了20年"



def test_context_text_wraps_segment_with_neighbor_clauses():
    from sg.tts import context_text
    comp, a, b = context_text("此后他在罗马市研修药剂和外科手术，", "一八五五年，", "在佐治亚州哥伦布开了自己的药店。")
    assert comp[a:b] == "一八五五年，"
    assert comp.startswith("市研修药剂和外科手术，") and comp.endswith("在佐治亚州哥伦布开了")


def test_context_text_without_neighbors_is_plain():
    from sg.tts import context_text
    assert context_text("", "南北战争爆发。", "") == ("南北战争爆发。", 0, 7)


def test_slice_alignment_keeps_only_segment_chars():
    from sg.tts import slice_alignment
    al = {"characters": list("前，本句后"), "character_start_times_seconds": [0, .2, .4, .6, .8],
          "character_end_times_seconds": [.2, .4, .6, .8, 1.0]}
    s = slice_alignment(al, 2, 4)
    assert s["characters"] == ["本", "句"] and s["character_start_times_seconds"] == [.4, .6]


def test_bounds_skip_chinese_punctuation():
    al = {"characters": list("，好。"), "character_start_times_seconds": [0, .3, .5],
          "character_end_times_seconds": [.3, .5, 1.2]}
    assert speech_bounds(al) == (.3, .5)


def test_cut_bounds_snaps_to_pauses_around_segment():
    from sg.tts import cut_bounds
    spans = [(0.0, 0.55), (0.8, 1.9), (2.15, 3.0)]      # 앞 문맥 | 본문 | 뒤 문맥 (쉼표 쉼으로 나뉨)
    assert cut_bounds(spans, 0.67, 2.05, True, True) == (0.8, 1.9)


def test_cut_bounds_keeps_alignment_when_no_pause_nearby():
    from sg.tts import cut_bounds
    assert cut_bounds([(0.0, 3.0)], 1.0, 2.0, True, True) == (1.0, 2.0)


def test_cut_bounds_without_neighbors_uses_speech_edges():
    from sg.tts import cut_bounds
    assert cut_bounds([(0.1, 1.2)], 0.03, 1.4, False, False) == (0.1, 1.2)


def test_cut_bounds_end_pause_must_follow_last_char():
    from sg.tts import cut_bounds
    # "之后，他" + 뒤 문맥: 쉼표 쉼(1.2~1.4)은 본문 안, 본문 끝(他 1.55) 뒤 쉼은 1.6~1.8
    spans = [(0.0, 1.2), (1.35, 1.5), (1.9, 2.5)]
    assert cut_bounds(spans, 0.0, 1.48, False, True) == (0.0, 1.5)
