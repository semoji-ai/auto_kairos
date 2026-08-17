from backend import srt

BASIC = """1
00:00:01,000 --> 00:00:03,500
첫 자막

2
00:00:04,000 --> 00:00:06,000
둘째 자막
"""


def test_two_cues():
    cues = srt.parse_srt(BASIC)
    assert len(cues) == 2
    assert cues[0] == {"start": 1.0, "end": 3.5, "text": "첫 자막"}
    assert cues[1]["start"] == 4.0


def test_last_cue_has_real_end():
    """SEMOJI 결함 수정 — 마지막 큐 길이가 0이 아니다."""
    cues = srt.parse_srt(BASIC)
    assert cues[-1]["end"] == 6.0
    assert cues[-1]["end"] > cues[-1]["start"]


def test_dot_millis_accepted():
    cues = srt.parse_srt("1\n00:00:01.250 --> 00:00:02.750\n마침표\n")
    assert cues[0]["start"] == 1.25 and cues[0]["end"] == 2.75


def test_multiline_text_joined():
    cues = srt.parse_srt("1\n00:00:01,000 --> 00:00:02,000\n윗줄\n아랫줄\n")
    assert cues[0]["text"] == "윗줄\n아랫줄"


def test_broken_block_skipped():
    text = BASIC + "\nX\n망가진 타임코드\n텍스트\n\n3\n00:00:07,000 --> 00:00:08,000\n셋째\n"
    cues = srt.parse_srt(text)
    assert [c["text"] for c in cues] == ["첫 자막", "둘째 자막", "셋째"]


def test_no_index_line_ok():
    cues = srt.parse_srt("00:00:01,000 --> 00:00:02,000\n번호 없음\n")
    assert cues[0]["text"] == "번호 없음"


def test_bom_and_crlf():
    text = "﻿1\r\n00:00:01,000 --> 00:00:02,000\r\n윈도 파일\r\n"
    cues = srt.parse_srt(text)
    assert cues[0]["text"] == "윈도 파일"


def test_end_before_start_skipped():
    cues = srt.parse_srt("1\n00:00:05,000 --> 00:00:04,000\n역행\n")
    assert cues == []


def test_empty_input():
    assert srt.parse_srt("") == []
    assert srt.parse_srt("   \n\n") == []


def test_endpoint_ok(tmp_path):
    from backend import jobs as jobs_mod
    from backend import router
    status, res = router.handle_request(
        "POST", "/api/tools/srt-parse", {}, {"srt": BASIC},
        {"root": tmp_path, "jobs": jobs_mod.JobRegistry()})
    assert status == 200
    assert len(res["cues"]) == 2


def test_endpoint_no_cues(tmp_path):
    from backend import jobs as jobs_mod
    from backend import router
    status, res = router.handle_request(
        "POST", "/api/tools/srt-parse", {}, {"srt": "쓸모없는 내용"},
        {"root": tmp_path, "jobs": jobs_mod.JobRegistry()})
    assert status == 422
    assert "error" in res
