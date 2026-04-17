"""TTS subtitle line contract safe-scope regression tests."""

import importlib
import json
from pathlib import Path

import pytest

from auto_agent.tools.elevenlabs import TTSPreprocessor

FAKE_MP3 = b"\xff\xfb" + b"\x00" * 100


@pytest.fixture()
def generate_tts_module(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    import auto_agent.scripts.generate_tts as module

    module = importlib.reload(module)
    monkeypatch.setattr(module, "API_KEY", "test-key")
    monkeypatch.setattr(module.time, "sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(module, "_upload_audio_to_supabase", lambda *_args, **_kwargs: None)
    return module


def test_generate_tts_persists_subtitle_lines_tts_from_original_subtitle_lines(generate_tts_module, tmp_path, monkeypatch):
    scene_specs_path = tmp_path / "scene_specs.json"
    scene_specs_path.write_text(
        json.dumps(
            {
                "scenes": [
                    {
                        "scene_number": 1,
                        "narration": "ETF에 투자합니다 S&P500을 봅니다",
                        "narration_tts": "이티에프에 투자합니다 에스앤피오백을 봅니다",
                        "subtitle_lines": ["ETF에 투자합니다", "S&P500을 봅니다"],
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("PROJECT_DIR", str(tmp_path))
    monkeypatch.setattr(generate_tts_module.sys, "argv", ["generate_tts.py"])

    def fake_generate_tts(text: str, output_path: Path) -> float:
        output_path.write_bytes(FAKE_MP3)
        return 1.0

    monkeypatch.setattr(generate_tts_module, "generate_tts", fake_generate_tts)

    generate_tts_module.main()

    updated = json.loads(scene_specs_path.read_text(encoding="utf-8"))
    scene = updated["scenes"][0]

    expected = [
        TTSPreprocessor().preprocess("ETF에 투자합니다"),
        TTSPreprocessor().preprocess("S&P500을 봅니다"),
    ]
    assert scene["subtitle_lines"] == ["ETF에 투자합니다", "S&P500을 봅니다"]
    assert scene["subtitle_lines_tts"] == expected


def test_generate_tts_records_tts_changes_when_raw_text_is_preprocessed(generate_tts_module, tmp_path, monkeypatch):
    scene_specs_path = tmp_path / "scene_specs.json"
    scene_specs_path.write_text(
        json.dumps(
            {
                "scenes": [
                    {
                        "scene_number": 1,
                        "narration": "ETF에 투자합니다",
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("PROJECT_DIR", str(tmp_path))
    monkeypatch.setattr(generate_tts_module.sys, "argv", ["generate_tts.py"])

    def fake_generate_tts(text: str, output_path: Path) -> float:
        output_path.write_bytes(FAKE_MP3)
        return 1.0

    monkeypatch.setattr(generate_tts_module, "generate_tts", fake_generate_tts)

    generate_tts_module.main()

    updated = json.loads(scene_specs_path.read_text(encoding="utf-8"))
    scene = updated["scenes"][0]

    assert scene["narration_tts"] == "이티에프에 투자합니다"
    assert scene["subtitle_lines"] == ["ETF에 투자합니다"]
    assert scene["subtitle_lines_tts"] == ["이티에프에 투자합니다"]
    assert scene["tts_changes"]
