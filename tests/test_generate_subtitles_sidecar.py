"""
tests/test_generate_subtitles_sidecar.py

chars_to_words() 단위 테스트
"""
import pytest
from auto_agent.scripts.generate_subtitles import chars_to_words


def test_normal_sentence_with_spaces():
    """공백 포함 문장 → 올바른 단어 경계 및 타임스탬프."""
    sidecar = {
        "characters": ["안", "녕", " ", "하", "세", "요"],
        "character_start_times_seconds": [0.0, 0.05, 0.1, 0.15, 0.2, 0.25],
        "character_end_times_seconds": [0.05, 0.1, 0.15, 0.2, 0.25, 0.3],
    }
    words = chars_to_words(sidecar)
    assert len(words) == 2
    assert words[0]["word"] == "안녕"
    assert words[0]["start"] == 0.0
    assert words[0]["end"] == 0.1
    assert words[1]["word"] == "하세요"
    assert words[1]["start"] == 0.15
    assert words[1]["end"] == 0.3


def test_empty_input():
    """빈 입력 → 빈 리스트."""
    assert chars_to_words({}) == []
    assert chars_to_words({"characters": [], "character_start_times_seconds": [], "character_end_times_seconds": []}) == []


def test_mismatched_lengths():
    """길이 불일치 → 빈 리스트."""
    sidecar = {
        "characters": ["가", "나"],
        "character_start_times_seconds": [0.0],
        "character_end_times_seconds": [0.1, 0.2],
    }
    assert chars_to_words(sidecar) == []


def test_single_word_no_spaces():
    """공백 없는 단어 → 단일 단어 엔트리."""
    sidecar = {
        "characters": ["테", "스", "트"],
        "character_start_times_seconds": [0.0, 0.1, 0.2],
        "character_end_times_seconds": [0.1, 0.2, 0.3],
    }
    words = chars_to_words(sidecar)
    assert len(words) == 1
    assert words[0]["word"] == "테스트"
    assert words[0]["start"] == 0.0
    assert words[0]["end"] == 0.3


def test_trailing_space_handled():
    """끝 공백은 무시 — 마지막 단어는 정상 처리."""
    sidecar = {
        "characters": ["가", " ", "나", " "],
        "character_start_times_seconds": [0.0, 0.1, 0.2, 0.3],
        "character_end_times_seconds": [0.1, 0.2, 0.3, 0.4],
    }
    words = chars_to_words(sidecar)
    assert len(words) == 2
    assert words[0]["word"] == "가"
    assert words[1]["word"] == "나"
    assert words[1]["end"] == 0.3
