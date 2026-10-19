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
