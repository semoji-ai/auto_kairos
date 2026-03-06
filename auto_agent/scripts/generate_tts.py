"""
TTS Audio Generation Script
Reads scene_specs.json, sends narration_tts to ElevenLabs API, saves audio files.
"""
import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load .env
from auto_agent.paths import get_workspace_dir; load_dotenv(get_workspace_dir() / ".env")

API_KEY = os.getenv("ELEVENLABS_API_KEY")
MODEL_ID = "eleven_multilingual_v2"

# 기본값 — DB config로 오버라이드 가능
_DEFAULT_VOICE_ID = "9Sj8ugvpK1DmcAXyvi3a"
_DEFAULT_VOICE_SETTINGS = {
    "stability": 1.0,
    "similarity_boost": 0.6,
    "style": 0.9,
    "use_speaker_boost": True,
    "speed": 1.1,
}


def _resolve_voice_config() -> tuple:
    """voice_id, voice_settings 해석: DB config → .env → 기본값."""
    voice_id = None
    voice_settings = None

    # 1) DB config
    try:
        from auto_agent.db.connection import db_exists
        if db_exists():
            from auto_agent.db.project_manager import ProjectManager
            pm = ProjectManager()
            project = pm.get_active_project()
            if project:
                vc = pm.get_voice_config(project["id"])
                voice_id = vc.get("voice_id")
                voice_settings = vc.get("voice_settings")
    except Exception:
        pass

    # 2) .env 폴백
    if not voice_id:
        voice_id = os.getenv("ELEVENLABS_VOICE_ID", _DEFAULT_VOICE_ID)

    # 3) settings: 환경변수 → 기본값 폴백
    if not voice_settings:
        settings_json = os.getenv("ELEVENLABS_VOICE_SETTINGS")
        if settings_json:
            try:
                voice_settings = json.loads(settings_json)
            except (json.JSONDecodeError, TypeError):
                voice_settings = _DEFAULT_VOICE_SETTINGS
        else:
            voice_settings = _DEFAULT_VOICE_SETTINGS

    return voice_id, voice_settings


VOICE_ID, VOICE_SETTINGS = _resolve_voice_config()

from auto_agent.scripts.project_paths import PROJECT_ROOT, get_project_dir


def generate_tts(text: str, output_path: Path) -> float:
    """Send text to ElevenLabs API and save MP3. Returns estimated duration."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}?output_format=mp3_44100_128"
    headers = {"Content-Type": "application/json", "xi-api-key": API_KEY}
    body = {"text": text, "model_id": MODEL_ID, "voice_settings": VOICE_SETTINGS}

    response = requests.post(url, headers=headers, json=body, timeout=60)
    if not response.ok:
        raise Exception(f"ElevenLabs API error: {response.status_code} - {response.text[:200]}")

    with open(output_path, "wb") as f:
        f.write(response.content)

    # Estimate duration from MP3 file size (128kbps)
    duration = (len(response.content) * 8) / 128000
    return duration


def main():
    if not API_KEY:
        print("ERROR: ELEVENLABS_API_KEY not found in .env")
        sys.exit(1)

    project_dir = get_project_dir()
    scene_specs_path = project_dir / "scene_specs.json"
    if not scene_specs_path.exists():
        print(f"ERROR: {scene_specs_path} 없음")
        sys.exit(1)

    OUTPUT_DIR = project_dir / "audio"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(scene_specs_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    scenes = data["scenes"]
    total = len(scenes)
    results = []

    print(f"Generating TTS for {total} scenes...")
    print(f"Output: {OUTPUT_DIR}")
    print()

    for i, scene in enumerate(scenes):
        num = scene.get("sceneNumber") or scene["scene_number"]
        # Use narration_tts (pre-processed) if available, else original narration
        text = scene.get("narration_tts", scene.get("narration", ""))

        if not text or not text.strip():
            print(f"  [{i+1}/{total}] Scene {num}: SKIP (empty narration)")
            results.append({"scene": num, "status": "skipped", "duration": 0})
            continue

        output_path = OUTPUT_DIR / f"scene_{num:03d}.mp3"

        # Skip if already exists
        if output_path.exists():
            size = output_path.stat().st_size
            duration = (size * 8) / 128000
            print(f"  [{i+1}/{total}] Scene {num}: EXISTS ({duration:.1f}s)")
            results.append({"scene": num, "status": "exists", "duration": duration, "path": str(output_path)})
            continue

        try:
            duration = generate_tts(text, output_path)
            print(f"  [{i+1}/{total}] Scene {num}: OK ({duration:.1f}s)")
            results.append({"scene": num, "status": "ok", "duration": duration, "path": str(output_path)})
            # Small delay to avoid rate limiting
            time.sleep(0.3)
        except Exception as e:
            print(f"  [{i+1}/{total}] Scene {num}: ERROR - {e}")
            results.append({"scene": num, "status": "error", "error": str(e)})

    # Save results
    total_duration = sum(r.get("duration", 0) for r in results)
    ok_count = sum(1 for r in results if r["status"] in ("ok", "exists"))
    err_count = sum(1 for r in results if r["status"] == "error")

    print(f"\nDone: {ok_count}/{total} OK, {err_count} errors")
    print(f"Total audio duration: {total_duration:.1f}s ({total_duration/60:.1f}min)")

    summary = {
        "total_scenes": total,
        "completed": ok_count,
        "errors": err_count,
        "total_duration_sec": round(total_duration, 2),
        "results": results,
    }

    with open(project_dir / "tts_results.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
