import json
import sys
import types
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from auto_agent.dashboard import actions
from auto_agent.scripts import generate_subtitles as subtitle_script


def test_generate_subtitles_partial_scene_preserves_other_scene_entries(tmp_path, monkeypatch):
    project_dir = tmp_path / "output" / "demo"
    audio_dir = project_dir / "audio"
    audio_dir.mkdir(parents=True)
    (audio_dir / "scene_002.mp3").write_bytes(b"not-a-real-mp3")

    (project_dir / "scene_specs.json").write_text(
        json.dumps(
            {
                "scenes": [
                    {"sceneNumber": 1, "narration": "첫 번째 씬", "narration_tts": "첫 번째 씬"},
                    {"sceneNumber": 2, "narration": "두 번째 씬 새 자막", "narration_tts": "두 번째 씬 새 자막"},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (project_dir / "subtitles.json").write_text(
        json.dumps(
            {
                "scenes": [
                    {
                        "sceneNumber": 1,
                        "audioDurationSec": 1.2,
                        "entries": [{"text": "씬1 유지", "startSec": 0.0, "endSec": 1.2}],
                        "source": "existing",
                    },
                    {
                        "sceneNumber": 2,
                        "audioDurationSec": 0.8,
                        "entries": [{"text": "씬2 오래된 자막", "startSec": 0.0, "endSec": 0.8}],
                        "source": "existing",
                    },
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    google_mod = types.ModuleType("google")
    google_mod.genai = types.SimpleNamespace(Client=lambda api_key=None: None)
    monkeypatch.setitem(sys.modules, "google", google_mod)

    whisperx_mod = types.ModuleType("whisperx")
    whisperx_mod.load_align_model = lambda language_code, device: (object(), object())
    whisperx_mod.load_audio = lambda path: [0] * 16000
    whisperx_mod.align = lambda *args, **kwargs: {"segments": []}
    monkeypatch.setitem(sys.modules, "whisperx", whisperx_mod)

    monkeypatch.setattr(subtitle_script, "get_project_dir", lambda: project_dir)
    monkeypatch.setattr(subtitle_script, "smart_split", lambda text: [text])
    monkeypatch.setattr(subtitle_script, "fix_decimal_splits", lambda lines: lines)
    monkeypatch.setattr(subtitle_script, "fix_quote_splits", lambda lines: lines)
    monkeypatch.setattr(
        subtitle_script,
        "match_lines_to_timestamps",
        lambda lines, words, duration: [
            {"index": 1, "text": lines[0], "startSec": 0.0, "endSec": round(duration or 1.0, 3)}
        ],
    )
    monkeypatch.setattr(subtitle_script, "check_alignment_quality", lambda entries, duration: True)
    monkeypatch.setattr(subtitle_script, "_upload_subtitles_to_supabase", lambda *args, **kwargs: None)
    monkeypatch.setenv("GOOGLE_API_KEY", "")
    monkeypatch.setattr(sys, "argv", ["generate_subtitles.py", "--scene", "2"])

    subtitle_script.main()

    data = json.loads((project_dir / "subtitles.json").read_text(encoding="utf-8"))
    scenes = {scene["sceneNumber"]: scene for scene in data["scenes"]}

    assert set(scenes) == {1, 2}
    assert scenes[1]["entries"][0]["text"] == "씬1 유지"
    assert scenes[2]["entries"][0]["text"] == "두 번째 씬 새 자막"


def test_tts_regenerate_chain_does_not_forward_scene_flag_to_build_manifest(tmp_path, monkeypatch):
    package_dir = tmp_path / "pkg"
    scripts_dir = package_dir / "scripts"
    scripts_dir.mkdir(parents=True)
    for name in ("generate_tts.py", "generate_subtitles.py", "build_manifest.py"):
        (scripts_dir / name).write_text("# stub\n", encoding="utf-8")

    output_dir = tmp_path / "output" / "demo"
    output_dir.mkdir(parents=True)

    calls = []

    def fake_run(cmd_args, **kwargs):
        calls.append(cmd_args)
        return types.SimpleNamespace(returncode=0, stdout="ok", stderr="")

    class FakePM:
        def get_config(self, project_id):
            return {}

    monkeypatch.setattr(actions, "PACKAGE_DIR", package_dir)
    monkeypatch.setattr(actions, "ProjectManager", lambda: FakePM())
    monkeypatch.setattr(actions, "resolve_project_by_slug", lambda slug: {"id": 7, "output_dir": str(output_dir)})
    monkeypatch.setattr(actions.subprocess, "run", fake_run)
    monkeypatch.setattr(actions, "get_workspace_dir", lambda: tmp_path)

    app = FastAPI()
    app.include_router(actions.router)
    client = TestClient(app)

    response = client.post("/api/p/demo/action/tts_regenerate", json={"scene_number": 2})

    assert response.status_code == 200
    assert len(calls) == 3
    # TTS 재생성 자체는 해당 씬만
    assert calls[0][-2:] == ["--scene", "2"]
    # subtitle_sync는 전체 씬 처리 — --scene을 주면 subtitles.json이
    # 1개 씬으로 덮어써져 나머지 자막이 소실됨 (d8142fc 버그픽스)
    assert "--scene" not in calls[1]
    # build_manifest도 --scene 미전달
    assert "--scene" not in calls[2]
