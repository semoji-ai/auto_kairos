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
