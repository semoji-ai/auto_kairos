"""
ElevenLabs /with-timestamps 엔드포인트 단위 테스트
"""
import base64
import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from auto_agent.tools.elevenlabs import ElevenLabsClient


FAKE_MP3 = b"\xff\xfb" + b"\x00" * 100  # 가짜 MP3 바이트


def make_fake_response():
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
def client():
    return ElevenLabsClient(
        tts_provider="elevenlabs",
        elevenlabs_api_key="test-key",
        voice_id="test-voice",
        model_id="eleven_multilingual_v2",
    )


def _make_mutagen_mock(duration: float):
    """mutagen.mp3 모듈을 sys.modules에 주입하는 mock 반환"""
    mp3_instance = MagicMock()
    mp3_instance.info.length = duration

    mp3_class = MagicMock(return_value=mp3_instance)

    mutagen_mod = types.ModuleType("mutagen")
    mutagen_mp3_mod = types.ModuleType("mutagen.mp3")
    mutagen_mp3_mod.MP3 = mp3_class
    mutagen_mod.mp3 = mutagen_mp3_mod
    return mutagen_mod, mutagen_mp3_mod


def _call_with_mocks(client, output_path, duration=3.14):
    fake_resp = MagicMock()
    fake_resp.ok = True
    fake_resp.json.return_value = make_fake_response()

    mutagen_mod, mutagen_mp3_mod = _make_mutagen_mock(duration)

    with patch("requests.post", return_value=fake_resp):
        orig_mutagen = sys.modules.get("mutagen")
        orig_mutagen_mp3 = sys.modules.get("mutagen.mp3")
        sys.modules["mutagen"] = mutagen_mod
        sys.modules["mutagen.mp3"] = mutagen_mp3_mod
        try:
            result = client._generate_tts_elevenlabs("안녕", output_path)
        finally:
            if orig_mutagen is None:
                sys.modules.pop("mutagen", None)
            else:
                sys.modules["mutagen"] = orig_mutagen
            if orig_mutagen_mp3 is None:
                sys.modules.pop("mutagen.mp3", None)
            else:
                sys.modules["mutagen.mp3"] = orig_mutagen_mp3
    return result


def test_sidecar_json_written(client, tmp_path):
    """사이드카 타임스탬프 JSON이 올바르게 저장되는지 확인"""
    output_path = tmp_path / "scene_001.mp3"
    _call_with_mocks(client, output_path)

    sidecar = tmp_path / "scene_001.timestamps.json"
    assert sidecar.exists(), "사이드카 JSON 파일이 존재해야 함"

    data = json.loads(sidecar.read_text(encoding="utf-8"))
    assert data["characters"] == ["안", "녕"]
    assert data["character_start_times_seconds"] == [0.0, 0.1]
    assert data["character_end_times_seconds"] == [0.1, 0.2]


def test_mp3_file_written(client, tmp_path):
    """MP3 파일이 올바르게 저장되는지 확인"""
    output_path = tmp_path / "scene_001.mp3"
    _call_with_mocks(client, output_path)

    assert output_path.exists(), "MP3 파일이 존재해야 함"
    assert output_path.read_bytes() == FAKE_MP3


def test_duration_from_timestamps(client, tmp_path):
    """반환되는 duration이 타임스탬프 마지막 값에서 읽혀야 함 (가장 정확)."""
    output_path = tmp_path / "scene_001.mp3"
    duration = _call_with_mocks(client, output_path, duration=7.77)

    # character_end_times_seconds 마지막 값 = 0.2
    # 파일 크기 추정값(≈0.006)이나 mutagen mock(7.77)이 아닌 0.2여야 함
    assert duration == pytest.approx(0.2), "타임스탬프 마지막 값이 duration으로 반환되어야 함"
