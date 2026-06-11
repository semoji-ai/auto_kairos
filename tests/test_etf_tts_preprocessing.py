"""ETF 발음 전처리 회귀 테스트."""

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


def test_elevenlabs_tts_preprocessor_converts_only_english_etf_to_korean_pronunciation():
    preprocessor = TTSPreprocessor()

    assert preprocessor.preprocess("ETF에 투자합니다") == "이티에프에 투자합니다"
    assert preprocessor.preprocess("아이티에프에 투자합니다") == "아이티에프에 투자합니다"


def test_generate_tts_main_normalizes_etf_to_standard_hangul(generate_tts_module, tmp_path, monkeypatch):
    """ETF는 '이티에프' 표준 표기로 강제 — 수기 narration_tts도 narration에서 재생성 (2026-06-11 확정)."""
    scene_specs_path = tmp_path / "scene_specs.json"
    scene_specs_path.write_text(
        json.dumps(
            {
                "scenes": [
                    {
                        "scene_number": 1,
                        "narration": "ETF에 투자합니다",
                        "narration_tts": "아이티에프에 투자합니다",
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

    captured = {}

    def fake_generate_tts(text: str, output_path: Path) -> float:
        captured["text"] = text
        output_path.write_bytes(FAKE_MP3)
        return 1.0

    monkeypatch.setattr(generate_tts_module, "generate_tts", fake_generate_tts)

    generate_tts_module.main()

    assert captured["text"] == "이티에프에 투자합니다"

    updated = json.loads(scene_specs_path.read_text(encoding="utf-8"))
    assert updated["scenes"][0]["narration_tts"] == "이티에프에 투자합니다"
