from sg.segments import attach_text


def test_each_subtitle_attached_exactly_once():
    spans = [(0.0, 3.0), (3.6, 8.0)]
    subs = [{"text": "가", "in": 0.1, "out": 1.5}, {"text": "나", "in": 1.5, "out": 3.4},
            {"text": "다", "in": 3.4, "out": 6.0}, {"text": "라", "in": 9.0, "out": 9.5}]
    segs = attach_text(spans, subs)
    assert [s["ko"] for s in segs] == ["가 나", "다 라"]
    assert sum(len(s["subs"]) for s in segs) == 4


def test_long_merged_span_keeps_all_texts():
    segs = attach_text([(0.0, 10.0)], [{"text": f"문장{i}", "in": i, "out": i + 1} for i in range(10)])
    assert segs[0]["ko"].split() == [f"문장{i}" for i in range(10)]



from sg.segments import merge_textless


def test_textless_speech_merges_into_nearest_neighbor():
    segs = attach_text([(0.0, 3.0), (3.2, 3.9), (5.0, 7.0)],
                       [{"text": "가", "in": 0.0, "out": 3.0}, {"text": "나", "in": 5.0, "out": 7.0}])
    out = merge_textless(segs, is_speech=lambda g: True)
    assert [(g["in"], g["out"], g["ko"]) for g in out] == [(0.0, 3.9, "가"), (5.0, 7.0, "나")]


def test_textless_non_speech_is_kept_as_nonverbal():
    segs = attach_text([(0.0, 3.0), (3.2, 3.9), (5.0, 7.0)],
                       [{"text": "가", "in": 0.0, "out": 3.9}, {"text": "나", "in": 5.0, "out": 7.0}])
    out = merge_textless(segs, is_speech=lambda g: False)
    assert [(g["in"], g.get("nonverbal", False)) for g in out] == [(0.0, False), (3.2, True), (5.0, False)]


def test_textless_speech_with_no_texted_neighbor_stays_nonverbal_flagged_for_review():
    out = merge_textless(attach_text([(0.0, 1.0)], []), is_speech=lambda g: True)
    assert out[0].get("nonverbal") is True and out[0].get("review") is True


from sg.segments import looks_like_speech


def test_whisper_hallucinations_are_not_speech():
    for t in ["", "  ", "[좋아요와 구독 부탁드려요]", "(음악)", "[구독 / 좋아요]", "시청해주셔서 감사합니다.",
              "MBC 뉴스 이준범입니다.", "-감사합니다. -감사합니다.", "자막 제공 배달의민족", "다음 영상에서 만나요"]:
        assert looks_like_speech(t) is False, t
    assert looks_like_speech("헤드코의 가격이 너무 저렴해서") is True


def test_speech_chunk_never_merges_across_a_nonverbal_chunk():
    # A(텍스트) | X(효과음) | Y(말로 판정) | B(텍스트): Y는 양쪽 모두 막혀 있음 → nonverbal+review
    segs = attach_text([(0.0, 3.0), (3.3, 4.0), (4.2, 5.0), (8.0, 9.0)],
                       [{"text": "A", "in": 0.0, "out": 3.0}, {"text": "B", "in": 8.0, "out": 9.0}])
    speech = {3.3: False, 4.2: True}
    out = merge_textless(segs, is_speech=lambda g: speech[g["in"]])
    assert [(g["in"], g["out"], g.get("nonverbal", False), g.get("review", False)) for g in out] == [
        (0.0, 3.0, False, False), (3.3, 4.0, True, False), (4.2, 5.0, True, True), (8.0, 9.0, False, False)]


def test_consecutive_speech_chunks_merge_into_reachable_neighbor():
    segs = attach_text([(0.0, 3.0), (3.1, 3.5), (3.6, 4.0), (9.0, 10.0)],
                       [{"text": "A", "in": 0.0, "out": 3.0}, {"text": "B", "in": 9.0, "out": 10.0}])
    out = merge_textless(segs, is_speech=lambda g: True)
    assert [(g["in"], g["out"]) for g in out] == [(0.0, 4.0), (9.0, 10.0)]


import pytest


def test_far_subtitle_is_attached_but_flagged_for_review():
    segs = attach_text([(0.0, 3.0)], [{"text": "가", "in": 0.0, "out": 3.0}, {"text": "멀다", "in": 10.0, "out": 11.0}])
    assert segs[0]["review"] is True and "멀다" in segs[0]["ko"]


def test_near_subtitle_does_not_flag_review():
    segs = attach_text([(0.0, 3.0)], [{"text": "가", "in": 3.5, "out": 4.0}])
    assert not segs[0].get("review")


def test_subtitles_without_any_speech_span_raise():
    with pytest.raises(ValueError):
        attach_text([], [{"text": "가", "in": 0.0, "out": 1.0}])
