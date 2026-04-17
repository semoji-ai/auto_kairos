import json
import sys
import types

from auto_agent.scripts import generate_subtitles as subtitle_script


def test_derive_tts_lines_from_display_lines_uses_shared_preprocessing_rules():
    display_lines = ["ETF ETF ETF ETF ETF ETF"]
    narration_tts = "이티에프 이티에프 이티에프 이티에프 이티에프 이티에프"

    derived = subtitle_script.derive_tts_lines_from_display_lines(display_lines, narration_tts)

    assert derived == [narration_tts]


def test_generate_subtitles_prefers_reverse_mapped_tts_lines_over_proportional_fallback(tmp_path, monkeypatch):
    project_dir = tmp_path / "output" / "demo"
    audio_dir = project_dir / "audio"
    audio_dir.mkdir(parents=True)
    (audio_dir / "scene_001.mp3").write_bytes(b"fake-mp3")

    narration = "ETF ETF ETF ETF ETF ETF"
    narration_tts = "이티에프 이티에프 이티에프 이티에프 이티에프 이티에프"

    (project_dir / "scene_specs.json").write_text(
        json.dumps(
            {
                "scenes": [
                    {"sceneNumber": 1, "narration": narration, "narration_tts": narration_tts}
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    captured = {}

    def fake_smart_split(text):
        if text == narration:
            return [narration]
        if text == narration_tts:
            return ["이티에프 이티에프 이티에프", "이티에프 이티에프 이티에프"]
        return [text]

    google_mod = types.ModuleType("google")
    google_mod.genai = types.SimpleNamespace(Client=lambda api_key=None: None)
    monkeypatch.setitem(sys.modules, "google", google_mod)

    whisperx_mod = types.ModuleType("whisperx")
    whisperx_mod.load_align_model = lambda language_code, device: (object(), object())
    whisperx_mod.load_audio = lambda path: [0] * 16000
    whisperx_mod.align = lambda *args, **kwargs: {"segments": []}
    monkeypatch.setitem(sys.modules, "whisperx", whisperx_mod)

    monkeypatch.setattr(subtitle_script, "get_project_dir", lambda: project_dir)
    monkeypatch.setattr(subtitle_script, "smart_split", fake_smart_split)
    monkeypatch.setattr(subtitle_script, "fix_decimal_splits", lambda lines: lines)
    monkeypatch.setattr(subtitle_script, "fix_quote_splits", lambda lines: lines)
    def fake_match_lines_to_timestamps(lines, words, duration):
        captured["lines"] = list(lines)
        return [
            {"index": 1, "text": lines[0], "startSec": 0.0, "endSec": round(duration or 1.0, 3)}
        ]

    monkeypatch.setattr(
        subtitle_script,
        "match_lines_to_timestamps",
        fake_match_lines_to_timestamps,
    )
    monkeypatch.setattr(subtitle_script, "check_alignment_quality", lambda entries, duration: True)
    monkeypatch.setattr(subtitle_script, "_upload_subtitles_to_supabase", lambda *args, **kwargs: None)
    monkeypatch.setenv("GOOGLE_API_KEY", "")
    monkeypatch.setattr(sys, "argv", ["generate_subtitles.py"])

    subtitle_script.main()

    assert captured["lines"] == [narration_tts]

    subtitles = json.loads((project_dir / "subtitles.json").read_text(encoding="utf-8"))
    scene = subtitles["scenes"][0]
    assert scene["entries"][0]["text"] == narration
