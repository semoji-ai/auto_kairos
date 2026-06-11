"""generate_tts.py가 ElevenLabs with-timestamps를 사용하는지 검증."""

import base64
import importlib
import json
from unittest.mock import MagicMock, patch

import pytest


FAKE_MP3 = b"\xff\xfb" + b"\x00" * 100


def _make_with_timestamps_payload():
    alignment = {
        "characters": ["안", "녕"],
        "character_start_times_seconds": [0.0, 0.1],
        "character_end_times_seconds": [0.1, 0.2],
    }
    return {
        "audio_base64": base64.b64encode(FAKE_MP3).decode(),
        "alignment": alignment,
        "normalized_alignment": alignment,
    }


@pytest.fixture()
def generate_tts_module(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    import auto_agent.scripts.generate_tts as module

    module = importlib.reload(module)
    monkeypatch.setattr(module, "API_KEY", "test-key")
    # VOICE_ID/VOICE_SETTINGS 전역은 voice 해석 체인(_get_voice_config)으로 대체됨
    monkeypatch.setattr(module, "_get_voice_config", lambda: ("test-voice", {"stability": 0.5}))
    return module


def test_generate_tts_uses_with_timestamps_and_writes_sidecar(generate_tts_module, tmp_path):
    output_path = tmp_path / "scene_001.mp3"
    payload = _make_with_timestamps_payload()

    fake_response = MagicMock()
    fake_response.ok = True
    fake_response.json.return_value = payload
    fake_response.content = FAKE_MP3

    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append({
            "url": url,
            "headers": headers,
            "json": json,
            "timeout": timeout,
        })
        return fake_response

    with patch("requests.post", side_effect=fake_post):
        duration = generate_tts_module.generate_tts("안녕", output_path)

    assert calls, "ElevenLabs API가 호출되어야 합니다"
    assert calls[0]["url"].endswith("/with-timestamps?output_format=mp3_44100_128")

    assert output_path.exists(), "MP3 파일이 저장되어야 합니다"
    assert output_path.read_bytes() == FAKE_MP3

    sidecar = tmp_path / "scene_001.timestamps.json"
    assert sidecar.exists(), "타임스탬프 사이드카 JSON이 저장되어야 합니다"

    sidecar_data = json.loads(sidecar.read_text(encoding="utf-8"))
    assert sidecar_data["characters"] == ["안", "녕"]
    assert sidecar_data["character_start_times_seconds"] == [0.0, 0.1]
    assert sidecar_data["character_end_times_seconds"] == [0.1, 0.2]
    assert duration == pytest.approx(0.2)


def test_generate_tts_falls_back_to_legacy_endpoint_when_with_timestamps_fails(generate_tts_module, tmp_path):
    output_path = tmp_path / "scene_001.mp3"

    ts_response = MagicMock()
    ts_response.ok = False
    ts_response.status_code = 500
    ts_response.text = "boom"

    legacy_response = MagicMock()
    legacy_response.ok = True
    legacy_response.content = FAKE_MP3

    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(url)
        if url.endswith("/with-timestamps?output_format=mp3_44100_128"):
            return ts_response
        return legacy_response

    with patch("requests.post", side_effect=fake_post):
        duration = generate_tts_module.generate_tts("안녕", output_path)

    assert calls == [
        "https://api.elevenlabs.io/v1/text-to-speech/test-voice/with-timestamps?output_format=mp3_44100_128",
        "https://api.elevenlabs.io/v1/text-to-speech/test-voice?output_format=mp3_44100_128",
    ]
    assert output_path.exists(), "폴백 경로에서도 MP3는 저장되어야 합니다"
    assert not (tmp_path / "scene_001.timestamps.json").exists(), "폴백 경로에서는 사이드카를 만들지 않습니다"
    assert duration == pytest.approx((len(FAKE_MP3) * 8) / 128000)
