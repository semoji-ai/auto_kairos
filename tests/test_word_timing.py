"""v4 글자 타임스탬프 → 어절 시각, 키워드 큐 — 한화 EP01 챕터1 실제 응답 발췌로 검증."""
import importlib.util
import json
from pathlib import Path

import pytest

from auto_agent.tools.word_timing import find_cue, scene_spans, words_from_alignment

ROOT = Path(__file__).resolve().parent.parent
FX = json.loads((Path(__file__).parent / "fixtures" / "v4_hanwha_ch1_excerpt.json").read_text(encoding="utf-8"))


def _load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_words_split_by_whitespace_and_newline():
    al = FX["alignment"]
    ws = words_from_alignment(al["characters"], al["character_start_times_seconds"],
                              al["character_end_times_seconds"])
    assert [w["w"] for w in ws[:4]] == ["1922년", "11월", "12일,", "충남"]
    assert ws[0]["start"] == 0.0 and ws[0]["end"] == 1.04
    assert ws[1]["start"] == 1.12
    # 줄바꿈(씬 경계)도 어절 경계 — "부대리." 와 "부친" 이 붙지 않는다
    assert "부대리." in [w["w"] for w in ws] and "부친" in [w["w"] for w in ws]
    assert all(w["start"] <= w["end"] for w in ws)


def test_find_cue_single_and_multi_word_and_occurrence():
    al = FX["alignment"]
    ws = words_from_alignment(al["characters"], al["character_start_times_seconds"],
                              al["character_end_times_seconds"])
    t_kim = find_cue(ws, "김종희")
    assert t_kim is not None
    w = next(x for x in ws if x["w"].startswith("김종희"))
    assert t_kim == w["start"]
    assert find_cue(ws, "천안군 북일면") == next(x for x in ws if x["w"] == "천안군")["start"]
    assert find_cue(ws, "김종희", lead=0.1) == round(t_kim - 0.1, 3)
    assert find_cue(ws, "없는말") is None
    assert find_cue(ws, "한", occurrence=99) is None


def test_scene_spans_match_v4_chapter_text():
    text, spans = scene_spans([s["narration"] for s in FX["scenes"]])
    assert text == FX["text"]
    assert spans[0] == (0, len(FX["scenes"][0]["narration"]))
    assert text[spans[1][0]:spans[1][1]] == FX["scenes"][1]["narration"]


def test_chapter_timing_exports_scene_words():
    m = _load_script("tts_v4_chapters")
    t = m.chapter_timing(1, FX["scenes"], FX["text"], FX["alignment"], Path("ch1.mp3"), FX["duration"])
    sc = t["scenes"]
    assert [s["n"] for s in sc] == [s["sceneNumber"] for s in FX["scenes"]]
    assert sc[0]["start"] == 0.0 and sc[-1]["end"] == FX["duration"]
    assert sc[0]["end"] == sc[1]["start"]
    # 씬마다 그 씬의 어절만
    assert sc[0]["words"][0]["w"] == "1922년" and sc[0]["words"][-1]["w"] == "부대리."
    assert sc[1]["words"][0]["w"] == "부친"
    assert all(sc[1]["start"] <= w["start"] <= sc[1]["end"] for w in sc[1]["words"])
    assert find_cue(sc[2]["words"], "한국화약") is not None
