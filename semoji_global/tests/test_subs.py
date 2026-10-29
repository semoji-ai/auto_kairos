from sg.subs import split_cues


def even(text, cps=15.0):
    ch = list(text)
    st = [i / cps for i in range(len(ch))]
    en = [(i + 1) / cps for i in range(len(ch))]
    return ch, st, en


def test_short_line_is_one_cue():
    cues = split_cues(*even("Costco opened in Korea in 1998."))
    assert len(cues) == 1 and cues[0]["text"] == "Costco opened in Korea in 1998."


def test_long_line_splits_at_word_boundaries_within_max_chars():
    t = ("Costco has sold its hot dog combo for one dollar and fifty cents for forty years, "
         "and it still makes money thanks to its membership model.")
    cues = split_cues(*even(t))
    assert all(len(c["text"]) <= 42 for c in cues)
    assert " ".join(c["text"] for c in cues) == t
    assert cues[0]["text"].endswith(",") or len(cues[0]["text"]) > 30   # 쉼표 뒤 우선 분할
    assert all(c["t1"] > c["t0"] for c in cues)


def test_tiny_tail_cue_is_merged():
    cues = split_cues(*even("This line is exactly long enough to split here. Yes."), max_chars=48)
    assert all(c["t1"] - c["t0"] >= 0.8 for c in cues)


from sg.subs import resolve_overlaps, retext


def test_overlaps_across_segments_are_trimmed_to_next_start_minus_gap():
    cues = [{"in": 0.0, "out": 2.0, "text": "a"}, {"in": 1.7, "out": 3.0, "text": "b"}, {"in": 3.5, "out": 4.0, "text": "c"}]
    out = resolve_overlaps(cues, gap=0.04)
    assert out[0]["out"] == 1.66 and out[1]["in"] == 1.7
    assert all(out[i]["out"] <= out[i + 1]["in"] for i in range(len(out) - 1))


def test_abbreviation_period_does_not_end_a_cue():
    t = "and reportedly become Korea's No. 2 big-box chain in a year."
    cues = split_cues(*even(t), max_chars=42)
    assert not any(c["text"].endswith("No.") for c in cues)


def test_retext_maps_display_words_onto_cues_from_pronunciation_text():
    cues = [{"t0": 0, "t1": 1, "text": "Kirk land Signature"}, {"t0": 1, "t1": 2, "text": "is cheap."}]
    out = retext(cues, "Kirkland Signature is cheap.")
    assert " ".join(c["text"] for c in out) == "Kirkland Signature is cheap."
    assert len(out) == 2 and out[0]["t1"] == 1


def test_bar_intervals_merge_short_gaps_and_shift_to_main_time():
    from sg.subs import bar_intervals
    cues = [{"in": 1.0, "out": 3.0}, {"in": 3.3, "out": 5.0}, {"in": 9.0, "out": 10.0}]
    # 자막 프리컴프가 메인 컴프 2초에 놓임 → 메인 시각 = 큐 + 2. 0.6초 미만 공백(0.3)은 이어 붙임
    assert bar_intervals(cues, 2.0, merge_gap=0.6) == [[3.0, 7.0], [11.0, 12.0]]


def test_close_gaps_extends_cue_to_next_when_gap_is_tiny():
    from sg.subs import close_gaps
    cues = [{"in": 0.0, "out": 2.19, "text": "a"}, {"in": 2.27, "out": 3.0, "text": "b"}, {"in": 4.0, "out": 5.0, "text": "c"}]
    out = close_gaps(cues, max_gap=0.3)
    assert [(c["in"], c["out"]) for c in out] == [(0.0, 2.27), (2.27, 3.0), (4.0, 5.0)]   # 0.08초 틈만 메움


def test_cjk_splits_at_chinese_punctuation_without_spaces():
    t = "1998年，开市客进入韩国。如今它已是全球第三大零售商，年销售额超过两千亿美元。"
    cues = split_cues(*even(t, cps=5.0), max_chars=18, cjk=True)
    assert "".join(c["text"] for c in cues) == t                 # 공백 없이 이어 붙음
    assert all(len(c["text"]) <= 18 for c in cues)
    assert cues[0]["text"].endswith(("，", "。"))                  # 문장부호 뒤에서 끊음


def test_cjk_keeps_latin_and_digit_runs_whole():
    t = "Costco的Kirkland Signature品牌在1995年诞生，它的价格非常便宜。"
    cues = split_cues(*even(t, cps=5.0), max_chars=12, cjk=True)
    joined = "|".join(c["text"] for c in cues)
    assert "Kirk|land" not in joined and "19|95" not in joined and "Cost|co" not in joined


def test_cjk_retext_splits_by_characters():
    from sg.subs import retext
    cues = [{"t0": 0, "t1": 1, "text": "一九九八年，"}, {"t0": 1, "t1": 2, "text": "开市客来了。"}]
    out = retext(cues, "1998年，开市客来了。", cjk=True)
    assert "".join(c["text"] for c in out) == "1998年，开市客来了。" and len(out) == 2


def test_snap_cue_starts_to_speech_onsets_after_pauses():
    from sg.subs import snap_to_onsets
    cues = [{"t0": 0.0, "t1": 2.0, "text": "a，"}, {"t0": 2.0, "t1": 4.0, "text": "b，"}, {"t0": 4.0, "t1": 6.0, "text": "c。"}]
    onsets = [0.05, 2.9, 4.1]                      # 실제 소리는 2.9초·4.1초에 다시 시작
    out = snap_to_onsets(cues, onsets, max_shift=1.2)
    assert [round(c["t0"], 2) for c in out] == [0.0, 2.9, 4.1]      # 첫 큐는 그대로, 나머지는 가까운 쉼 뒤 시작으로
    assert round(out[0]["t1"], 2) == 2.9 and round(out[1]["t1"], 2) == 4.1   # 앞 큐 끝은 다음 시작까지
    far = snap_to_onsets(cues, [0.05, 5.5], max_shift=1.2)
    assert far[1]["t0"] == 2.0                                       # 먼 쉼은 무시


def test_srt_time_rounds_whole_value_not_parts():
    from sg.subs import srt_time
    assert srt_time(82.99999) == "00:01:23,000"     # 초 버림 + 밀리초 반올림으로 1초 이르게 적히던 버그
    assert srt_time(83.0004) == "00:01:23,000" and srt_time(3725.5) == "01:02:05,500"


_NOSTART = "，。！？、；：）」”』…"


def test_cjk_cue_never_starts_with_punctuation_or_closing_mark():
    t = "而是为方便洛杉矶公务员而成立的合作社。所以Fedco表示无意到其他地区开店扩张，也拒绝了索尔的提议（这是关键）。"
    cues = split_cues(*even(t, cps=5.0), max_chars=18, cjk=True)
    assert "".join(c["text"] for c in cues) == t
    assert all(c["text"][0] not in _NOSTART for c in cues)


def test_cjk_long_clause_is_split_evenly_without_orphan_tail():
    t = "仿照Price Club推出的热狗套餐"           # 18자 상한에 1자 넘침 → '…套' + '餐'이 되면 안 됨
    cues = split_cues(*even(t, cps=5.0), max_chars=16, cjk=True)
    assert len(cues) == 2 and min(len(c["text"]) for c in cues) >= 6 and max(len(c["text"]) for c in cues) <= 16


def test_cjk_protected_terms_are_not_split():
    t = "就是1998年来韩的美国仓储会员店开市客，它改变了韩国零售业。"
    cues = split_cues(*even(t, cps=5.0), max_chars=16, cjk=True, protect=["开市客"])
    assert not any(c["text"].endswith(("开", "开市")) for c in cues)


def test_snap_never_moves_a_cue_past_the_next_cue_start():
    from sg.subs import snap_to_onsets
    cues = [{"t0": 0.0, "t1": 1.0, "text": "a"}, {"t0": 1.0, "t1": 1.9, "text": "b"}, {"t0": 1.9, "t1": 2.8, "text": "c"}]
    out = snap_to_onsets(cues, [0.0, 2.15], max_shift=1.2)
    assert [c["t0"] for c in out] == sorted(c["t0"] for c in out)
    assert out[1]["t0"] < 1.9


def test_cues_for_segment_uses_display_text_when_tts_differs():
    from sg.subs import cues_for_segment
    tts = "二零一九年，开市客来了。"
    ch, st, en = even(tts, cps=5.0)
    cues = cues_for_segment(ch, st, en, display="2019年，开市客来了。", max_chars=18, min_dur=0.8, cjk=True)
    assert "".join(c["text"] for c in cues) == "2019年，开市客来了。"
    assert abs(cues[0]["t0"] - 0.0) < 1e-6 and abs(cues[-1]["t1"] - len(tts) / 5.0) < 1e-6


def test_cjk_long_clause_is_not_cut_inside_a_word():
    t = "说出来你可能不信，这位零售之父，直到快四十岁，干的还是一份跟零售八竿子打不着的工作——律师。"   # 실제로 「八竿|子」로 끊겼던 문장
    cues = split_cues(*even(t, cps=5.0), max_chars=18, cjk=True)
    joined = "|".join(c["text"] for c in cues)
    assert "".join(c["text"] for c in cues) == t
    assert "八竿|子" not in joined and "竿子|打" not in joined and "打不|着" not in joined
