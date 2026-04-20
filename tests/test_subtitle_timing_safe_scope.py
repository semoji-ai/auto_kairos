import json
import sys
import types
from pathlib import Path

from fastapi.testclient import TestClient

import app as dashboard_app
from auto_agent.scripts import generate_subtitles as subtitle_script


def test_format_srt_time_rounds_milliseconds():
    assert subtitle_script.format_srt_time(1.9996) == "00:00:02,000"
    assert subtitle_script.format_srt_time(61.2345) == "00:01:01,234"


def test_generate_subtitles_uses_actual_audio_duration_when_sidecar_ends_early(tmp_path, monkeypatch):
    project_dir = tmp_path / "output" / "demo"
    audio_dir = project_dir / "audio"
    audio_dir.mkdir(parents=True)
    audio_path = audio_dir / "scene_001.mp3"
    audio_path.write_bytes(b"fake-mp3")
    audio_path.with_name("scene_001.timestamps.json").write_text(
        json.dumps(
            {
                "characters": ["안", "녕"],
                "character_start_times_seconds": [0.0, 0.3],
                "character_end_times_seconds": [0.2, 0.8],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (project_dir / "scene_specs.json").write_text(
        json.dumps(
            {"scenes": [{"sceneNumber": 1, "narration": "안녕", "narration_tts": "안녕"}]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    google_mod = types.ModuleType("google")
    google_mod.genai = types.SimpleNamespace(Client=lambda api_key=None: None)
    monkeypatch.setitem(sys.modules, "google", google_mod)

    whisperx_mod = types.ModuleType("whisperx")
    whisperx_mod.load_align_model = lambda language_code, device: (object(), object())
    whisperx_mod.load_audio = lambda path: [0] * 17600
    whisperx_mod.align = lambda *args, **kwargs: {"segments": []}
    monkeypatch.setitem(sys.modules, "whisperx", whisperx_mod)

    monkeypatch.setattr(subtitle_script, "get_project_dir", lambda: project_dir)
    monkeypatch.setattr(subtitle_script, "smart_split", lambda text: [text])
    monkeypatch.setattr(subtitle_script, "fix_decimal_splits", lambda lines: lines)
    monkeypatch.setattr(subtitle_script, "fix_quote_splits", lambda lines: lines)
    monkeypatch.setattr(subtitle_script, "_upload_subtitles_to_supabase", lambda *args, **kwargs: None)
    monkeypatch.setenv("GOOGLE_API_KEY", "")
    monkeypatch.setattr(sys, "argv", ["generate_subtitles.py"])

    subtitle_script.main()

    subtitles = json.loads((project_dir / "subtitles.json").read_text(encoding="utf-8"))
    scene = subtitles["scenes"][0]

    assert scene["audioDurationSec"] == 1.1
    assert scene["entries"][-1]["endSec"] == 1.1


def test_save_subtitles_filters_blank_entries_and_keeps_real_audio_duration(tmp_path, monkeypatch):
    output_dir = tmp_path / "output" / "demo"
    (output_dir / "subtitles").mkdir(parents=True)
    subtitles_json = output_dir / "subtitles.json"
    subtitles_json.write_text(
        json.dumps(
            {
                "scenes": [
                    {
                        "sceneNumber": 1,
                        "audioDurationSec": 2.4,
                        "entries": [{"text": "기존", "startSec": 0.0, "endSec": 2.4}],
                        "source": "existing",
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    class FakePM:
        def get_project(self, slug=None):
            if slug == "demo":
                return {"id": 7, "slug": "demo", "output_dir": str(output_dir)}
            return None

    monkeypatch.setattr(dashboard_app, "get_pm", lambda: FakePM())
    monkeypatch.setattr(dashboard_app, "_resolve_subtitle_audio_duration", lambda out_dir, scene_num, fallback_end_sec=0.0: 2.4)
    monkeypatch.setattr("auto_agent.scripts.build_manifest.build_manifest", lambda *args, **kwargs: None)

    client = TestClient(dashboard_app.app)
    response = client.post(
        "/api/p/demo/subtitles/1",
        json={
            "entries": [
                {"text": "첫 줄", "startSec": 0.0, "endSec": 0.8},
                {"text": "   ", "startSec": 0.8, "endSec": 1.1},
                {"text": "둘째 줄", "startSec": 1.1, "endSec": 1.7},
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["count"] == 2

    saved = json.loads(subtitles_json.read_text(encoding="utf-8"))
    scene = saved["scenes"][0]
    assert scene["audioDurationSec"] == 2.4
    assert [entry["text"] for entry in scene["entries"]] == ["첫 줄", "둘째 줄"]

    srt_text = (output_dir / "subtitles" / "scene_001.srt").read_text(encoding="utf-8")
    assert "첫 줄" in srt_text
    assert "둘째 줄" in srt_text
    assert "   " not in srt_text
