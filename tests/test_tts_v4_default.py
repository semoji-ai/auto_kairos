"""TTS 기본 모델 eleven_v4 — 전처리 없음, style/speed 미전송, language_code·정규화 전송.

v2(eleven_multilingual_v2)는 폴백으로 남고 그때만 전처리기를 거친다.
"""
import base64
import importlib
from unittest.mock import MagicMock, patch

import pytest

from auto_agent.tools import tts_config


def test_default_model_is_v4(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_MODEL_ID", raising=False)
    assert tts_config.default_model() == "eleven_v4"
    assert tts_config.uses_preprocessor(None) is False


def test_env_selects_v2_fallback(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
    assert tts_config.default_model() == "eleven_multilingual_v2"
    assert tts_config.uses_preprocessor(None) is True


def test_v4_body_has_no_style_or_speed_and_sends_language():
    legacy_flat = {"stability": 1.0, "similarity_boost": 0.9, "style": 0.9,
                   "use_speaker_boost": True, "speed": 1.1}
    body = tts_config.request_body("1968년", "eleven_v4", legacy_flat)
    assert body["model_id"] == "eleven_v4"
    assert body["voice_settings"] == {"stability": 0.5, "similarity_boost": 0.9}
    assert body["language_code"] == "ko"
    assert body["apply_text_normalization"] == "auto"
    assert body["text"] == "1968년"


def test_v4_accepts_per_model_override_but_drops_unsupported_keys():
    ov = {"eleven_v4": {"stability": 0.6, "speed": 1.2},
          "eleven_multilingual_v2": {"stability": 1.0}}
    vs = tts_config.voice_settings_for("eleven_v4", ov)
    assert vs == {"stability": 0.6, "similarity_boost": 0.9}


def test_v2_keeps_style_speed_and_iromism_similarity():
    vs = tts_config.voice_settings_for("eleven_multilingual_v2", None, "9Sj8ugvpK1DmcAXyvi3a")
    assert vs["style"] == 0.9 and vs["speed"] == 1.1 and vs["similarity_boost"] == 0.6
    body = tts_config.request_body("x", "eleven_multilingual_v2")
    assert "language_code" not in body and "apply_text_normalization" not in body


def _payload():
    al = {"characters": ["안"], "character_start_times_seconds": [0.0],
          "character_end_times_seconds": [0.1]}
    return {"audio_base64": base64.b64encode(b"\xff\xfb" + b"\0" * 10).decode(),
            "alignment": al, "normalized_alignment": al}


def test_client_v4_sends_raw_text_without_preprocessing(tmp_path, monkeypatch):
    monkeypatch.delenv("ELEVENLABS_MODEL_ID", raising=False)
    from auto_agent.tools.elevenlabs import ElevenLabsClient
    c = ElevenLabsClient(elevenlabs_api_key="k", voice_id="v",
                         voice_settings={"stability": 1.0, "style": 0.9, "speed": 1.1})
    assert c.model_id == "eleven_v4"
    resp = MagicMock(ok=True)
    resp.json.return_value = _payload()
    with patch("requests.post", return_value=resp) as post:
        c.generate_tts("1968년, 마이디어[1]는 2위에 올랐다.", tmp_path / "a.mp3")
    body = post.call_args.kwargs["json"]
    assert body["text"] == "1968년, 마이디어는 2위에 올랐다."      # 숫자 그대로, 각주만 걷음
    assert "style" not in body["voice_settings"] and "speed" not in body["voice_settings"]
    assert body["language_code"] == "ko"


def test_client_v2_still_preprocesses(tmp_path):
    from auto_agent.tools.elevenlabs import ElevenLabsClient
    c = ElevenLabsClient(elevenlabs_api_key="k", voice_id="v", model_id="eleven_multilingual_v2")
    resp = MagicMock(ok=True)
    resp.json.return_value = _payload()
    with patch("requests.post", return_value=resp) as post:
        c.generate_tts("1968년에 세웠다.", tmp_path / "a.mp3")
    body = post.call_args.kwargs["json"]
    assert body["text"].startswith("천구백육십팔년")
    assert body["voice_settings"]["style"] == 0.9


@pytest.fixture()
def gen_tts(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")
    import auto_agent.scripts.generate_tts as m
    return m


def test_generate_tts_script_skips_preprocessor_on_v4(gen_tts, monkeypatch):
    monkeypatch.setattr(gen_tts, "MODEL_ID", "eleven_v4")
    out, changes = gen_tts._preprocess_tts_text("1968년, 3,500여명이 일했다.[2]")
    assert out == "1968년, 3,500여명이 일했다." and changes == []


def test_generate_tts_script_preprocesses_on_v2(gen_tts, monkeypatch):
    monkeypatch.setattr(gen_tts, "MODEL_ID", "eleven_multilingual_v2")
    out, changes = gen_tts._preprocess_tts_text("1968년에 세웠다.")
    assert out.startswith("천구백육십팔년") and changes


@pytest.mark.parametrize("year,want", [
    ("1968년", "천구백육십팔년"), ("1956년", "천구백오십육년"), ("2001년", "이천일년"),
    ("845년", "팔백사십오년"), ("1990년", "천구백구십년"), ("4,600년", "사천육백년"),
])
def test_v2_preprocessor_year_is_joined_without_liaison(year, want):
    from auto_agent.tools.korean_tts_preprocessor import KoreanTTSPreprocessor
    out, _ = KoreanTTSPreprocessor().process_text(year)
    assert out == want


def test_adobe_backend_v4_body():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "adobe"))
    tts = importlib.import_module("backend.tts")
    b = tts.request_body("x", None, {"stability": 1.0, "style": 0.9, "speed": 1.1})
    assert b["model_id"] == "eleven_v4"
    assert b["voice_settings"] == {"stability": 0.5, "similarity_boost": 0.9}
    assert b["language_code"] == "ko"
    b2 = tts.request_body("x", "eleven_multilingual_v2", {"stability": 0.7})
    assert b2["voice_settings"]["stability"] == 0.7 and b2["voice_settings"]["speed"] == 1.1
