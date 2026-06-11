"""TTS 전처리/생성 경로 parity 회귀 테스트."""

import importlib
from pathlib import Path
from unittest.mock import patch

import pytest

from auto_agent.tools.elevenlabs import TTSPreprocessor
from auto_agent.tools.korean_tts_preprocessor import KoreanTTSPreprocessor


@pytest.fixture()
def generate_tts_module(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    import auto_agent.scripts.generate_tts as module

    module = importlib.reload(module)
    monkeypatch.setattr(module, "API_KEY", "test-key")
    # VOICE_ID/VOICE_SETTINGS 전역은 voice 해석 체인(_get_voice_config)으로 대체됨
    monkeypatch.setattr(module, "_get_voice_config", lambda: ("test-voice", {"stability": 0.5}))
    return module


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("ETF에 투자합니다", "이티에프에 투자합니다"),
        ("아이티에프에 투자합니다", "아이티에프에 투자합니다"),
        ("1~2", "1에서2"),
        ("1~2개", "1에서이개"),
        ("장소: 서울\nETF (미국) 투자??", "이티에프 투자?"),
        ("최고지도자", "최-고-지도자"),
        ("장난감", "장난깜"),
        ("신기록", "신끼록"),
        ("삼만", "'삼'만"),
        ("삼천", "'삼'천"),
        ("삼백", "'삼'백"),
    ],
)
def test_direct_and_script_preprocessors_share_same_rules(text, expected):
    direct = TTSPreprocessor().preprocess(text)
    script, _changes = KoreanTTSPreprocessor().process_text(text)

    assert direct == expected
    assert script == expected
    assert direct == script


def test_generate_tts_script_uses_shared_elevenlabs_generation_path(generate_tts_module, tmp_path):
    output_path = tmp_path / "scene_001.mp3"

    with patch(
        "auto_agent.tools.elevenlabs.ElevenLabsClient.generate_preprocessed_tts",
        return_value=1.23,
    ) as mocked:
        duration = generate_tts_module.generate_tts("이티에프에 투자합니다", output_path)

    mocked.assert_called_once()
    args, _kwargs = mocked.call_args
    assert args[0] == "이티에프에 투자합니다"
    assert args[1] == output_path
    assert duration == pytest.approx(1.23)
