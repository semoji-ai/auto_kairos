import json
from pathlib import Path

from backend import subtitles


def test_split_lines_word_boundary():
    text = "우주 탐사의 역사는 인류의 도전 정신을 보여줍니다"
    lines = subtitles.split_lines(text, max_len=20)
    assert all(len(l) <= 20 for l in lines)
    assert " ".join(lines) == text                  # 어절 보존
    assert len(lines) >= 2


def test_split_lines_empty():
    assert subtitles.split_lines("") == []
    assert subtitles.split_lines(None) == []


def test_split_lines_single_short():
    assert subtitles.split_lines("짧다") == ["짧다"]


def test_fmt_srt_time():
    assert subtitles._fmt_srt_time(0.0) == "00:00:00,000"
    assert subtitles._fmt_srt_time(3.456) == "00:00:03,456"
    assert subtitles._fmt_srt_time(3661.5) == "01:01:01,500"


def test_line_cues_maps_char_timings():
    # "안녕 하세요" — alignment에 공백 포함, 줄 분할은 max 3자 → ["안녕", "하세요"]
    ts = {"text": "안녕 하세요",
          "characters": ["안", "녕", " ", "하", "세", "요"],
          "starts": [0.0, 0.2, 0.4, 0.5, 0.7, 0.9],
          "ends": [0.2, 0.4, 0.5, 0.7, 0.9, 1.1]}
    cues = subtitles.line_cues(ts, max_len=3)
    assert [c["text"] for c in cues] == ["안녕", "하세요"]
    assert cues[0]["start"] == 0.0 and cues[0]["end"] == 0.4
    assert cues[1]["start"] == 0.5 and cues[1]["end"] == 1.1


def test_line_cues_empty_alignment():
    assert subtitles.line_cues({"text": "안녕", "characters": [], "starts": [], "ends": []}) == []


def _ts(text, chars, starts, ends):
    return {"text": text, "characters": chars, "starts": starts, "ends": ends}


def test_mapped_cues_identical_text_matches_line_cues():
    ts = _ts("안녕 하세요", ["안", "녕", " ", "하", "세", "요"],
             [0.0, 0.2, 0.4, 0.5, 0.7, 0.9], [0.2, 0.4, 0.5, 0.7, 0.9, 1.1])
    assert subtitles.mapped_cues(ts, "안녕 하세요", max_len=3) == subtitles.line_cues(ts, max_len=3)
    assert subtitles.mapped_cues(ts, "", max_len=3) == subtitles.line_cues(ts, max_len=3)


def test_mapped_cues_uses_subtitle_text_within_sentence_span():
    # TTS는 숫자를 풀어 읽고, 자막은 숫자 그대로 — 문장 수 1:1
    ts = _ts("이천이십육 년.", list("이천이십육 년."),
             [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
             [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8])
    cues = subtitles.mapped_cues(ts, "2026년.", max_len=20)
    assert [c["text"] for c in cues] == ["2026년."]      # 화면에는 자막 텍스트
    assert cues[0]["start"] == 0.0 and cues[0]["end"] == 0.8


def test_mapped_cues_sentence_count_mismatch_falls_back_to_ratio():
    ts = _ts("가나. 다라.", list("가나. 다라."),
             [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6], [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7])
    cues = subtitles.mapped_cues(ts, "합친 자막", max_len=20)     # 문장 1개 vs 2개
    assert [c["text"] for c in cues] == ["합친 자막"]
    assert cues[0]["start"] == 0.0 and cues[0]["end"] == 0.7


def test_split_sentences():
    assert subtitles.split_sentences("가. 나! 다?") == ["가.", "나!", "다?"]
    assert subtitles.split_sentences("경계 없음") == ["경계 없음"]
    assert subtitles.split_sentences("") == []


def _proj(tmp_path, scenes_list):
    proj = tmp_path / "p"
    (proj / "audio").mkdir(parents=True)
    (proj / "scenes.json").write_text(json.dumps(
        {"project_id": "p", "scenes": scenes_list}, ensure_ascii=False), encoding="utf-8")
    return proj


def test_build_subtitles_offsets_and_fallback(tmp_path, monkeypatch):
    scenes_list = [
        {"sceneNumber": 1, "sceneId": "aaa", "narration": "안녕 하세요", "duration_estimate_sec": 9},
        {"sceneNumber": 2, "sceneId": "bbb", "narration": "둘째 씬 자막", "duration_estimate_sec": 4},
    ]
    proj = _proj(tmp_path, scenes_list)
    # 씬1: 오디오 + 타임스탬프 사이드카(길이 2.0초로 가장)
    (proj / "audio" / "tts_aaa.mp3").write_bytes(b"x")
    (proj / "audio" / "tts_aaa.timestamps.json").write_text(json.dumps({
        "text": "안녕 하세요",
        "characters": ["안", "녕", " ", "하", "세", "요"],
        "starts": [0.0, 0.2, 0.4, 0.5, 0.7, 0.9],
        "ends": [0.2, 0.4, 0.5, 0.7, 0.9, 1.1]}), encoding="utf-8")
    monkeypatch.setattr(subtitles.tts, "audio_duration", lambda p: 2.0)

    res = subtitles.build_subtitles(proj)
    cues = json.loads((proj / "subtitles.json").read_text(encoding="utf-8"))["cues"]
    # 씬1: 타임스탬프 기반 1줄("안녕 하세요" ≤20자) — [0, 1.1]
    assert cues[0]["text"] == "안녕 하세요"
    assert cues[0]["start"] == 0.0 and cues[0]["end"] == 1.1
    # 씬2: 사이드카 없음 → 균등 폴백, 오프셋 = 씬1 길이(오디오 2.0초)
    assert res["scenes_no_ts"] == [2]
    s2 = [c for c in cues if c["start"] >= 2.0]
    assert s2 and s2[0]["start"] == 2.0
    assert all(c["end"] <= 2.0 + 4.0 for c in s2)            # estimate=4초 내
    assert res["lines"] == len(cues)
    # SRT 형식
    srt = (proj / "subtitles.srt").read_text(encoding="utf-8")
    assert srt.startswith("1\n00:00:00,000 --> 00:00:01,100\n안녕 하세요\n")
    assert " --> " in srt
    assert res["json"].endswith("subtitles.json") and res["srt"].endswith("subtitles.srt")


def test_build_subtitles_prefers_subtitle_text(tmp_path, monkeypatch):
    """자막 필드가 따로 있으면 화면 텍스트는 그쪽, 타이밍은 alignment 범위 안."""
    proj = _proj(tmp_path, [{
        "sceneNumber": 1, "sceneId": "aaa",
        "narration": "2026년.", "narration_tts": "이천이십육 년.", "subtitle_text": "2026년.",
    }])
    (proj / "audio" / "tts_aaa.mp3").write_bytes(b"x")
    (proj / "audio" / "tts_aaa.timestamps.json").write_text(json.dumps(_ts(
        "이천이십육 년.", list("이천이십육 년."),
        [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
        [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8])), encoding="utf-8")
    monkeypatch.setattr(subtitles.tts, "audio_duration", lambda p: 1.0)

    subtitles.build_subtitles(proj)
    cues = json.loads((proj / "subtitles.json").read_text(encoding="utf-8"))["cues"]
    assert [c["text"] for c in cues] == ["2026년."]
    assert cues[0]["start"] == 0.0 and cues[0]["end"] == 0.8


def test_build_subtitles_fallback_uses_subtitle_text(tmp_path):
    """타임스탬프 없는 씬도 자막 필드를 쓴다(TTS 발음 텍스트가 아니라)."""
    proj = _proj(tmp_path, [{
        "sceneNumber": 1, "sceneId": "aaa", "narration": "원고",
        "narration_tts": "발음용 텍스트", "subtitle_text": "자막용 텍스트",
        "duration_estimate_sec": 4,
    }])
    subtitles.build_subtitles(proj)
    cues = json.loads((proj / "subtitles.json").read_text(encoding="utf-8"))["cues"]
    assert [c["text"] for c in cues] == ["자막용 텍스트"]


def test_build_subtitles_no_audio_uses_estimate(tmp_path, monkeypatch):
    scenes_list = [
        {"sceneNumber": 1, "sceneId": "ccc", "narration": "첫 씬", "duration_estimate_sec": 5},
        {"sceneNumber": 2, "sceneId": "ddd", "narration": "둘째 씬"},
    ]
    proj = _proj(tmp_path, scenes_list)
    res = subtitles.build_subtitles(proj)
    cues = json.loads((proj / "subtitles.json").read_text(encoding="utf-8"))["cues"]
    # 씬2 오프셋 = 씬1 estimate(5초); 씬2 길이=기본 3.0
    assert cues[1]["start"] == 5.0
    assert res["scenes_no_ts"] == [1, 2]


def test_build_subtitles_only_scenes_keeps_global_offsets(tmp_path):
    """체크한 씬만 빌드해도 시각은 전체 기준 — 부분 빌드가 타이밍을 어긋내지 않는다."""
    proj = _proj(tmp_path, [
        {"sceneNumber": 1, "sceneId": "a", "narration": "첫째", "duration_estimate_sec": 4},
        {"sceneNumber": 2, "sceneId": "b", "narration": "둘째", "duration_estimate_sec": 4},
        {"sceneNumber": 3, "sceneId": "c", "narration": "셋째", "duration_estimate_sec": 4},
    ])
    res = subtitles.build_subtitles(proj, only_scenes=[3])
    cues = json.loads((proj / "subtitles.json").read_text(encoding="utf-8"))["cues"]
    assert [c["text"] for c in cues] == ["셋째"]
    assert cues[0]["start"] == 8.0          # 앞 두 씬 길이만큼 밀려 있음
    assert res["scenes_no_ts"] == [3]


def test_subtitle_shows_original_not_tts_reading(tmp_path, monkeypatch):
    """v3에서 넘어온 프로젝트: narration_tts는 숫자를 풀어 읽지만 자막은 원문."""
    proj = _proj(tmp_path, [{
        "sceneNumber": 1, "sceneId": "a",
        "narration": "1970년대 이야기다.", "narration_tts": "천구백칠십 년대 이야기다.",
    }])
    (proj / "audio" / "tts_a.mp3").write_bytes(b"x")
    chars = list("천구백칠십 년대 이야기다.")
    (proj / "audio" / "tts_a.timestamps.json").write_text(json.dumps(_ts(
        "천구백칠십 년대 이야기다.", chars,
        [i * 0.1 for i in range(len(chars))],
        [(i + 1) * 0.1 for i in range(len(chars))])), encoding="utf-8")
    monkeypatch.setattr(subtitles.tts, "audio_duration", lambda p: 1.6)

    subtitles.build_subtitles(proj)
    cues = json.loads((proj / "subtitles.json").read_text(encoding="utf-8"))["cues"]
    joined = " ".join(c["text"] for c in cues)
    assert "1970년대" in joined and "천구백칠십" not in joined
