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


def _preprocess_tts_text(text: str) -> str:
    """TTS 전처리 — 숫자→한국어, 영어약어→한국어, 발음 교정, 마크다운 제거."""
    try:
        from auto_agent.tools.korean_tts_preprocessor import KoreanTTSPreprocessor
        preprocessor = KoreanTTSPreprocessor()
        result, changes = preprocessor.process_text(text)
        if changes:
            logging.getLogger(__name__).debug("TTS 전처리: %s", changes)
        return result
    except (ImportError, Exception):
        pass
    try:
        from auto_agent.tools.elevenlabs import TTSPreprocessor
        return TTSPreprocessor().preprocess(text, "ko")
    except (ImportError, Exception):
        pass
    # fallback: 기본 숫자 변환만
    import re
    # 쉼표 숫자 (1,514 → 천오백십사)
    def _num_to_kr(m):
        n = int(m.group().replace(",", ""))
        if n >= 100_000_000:
            return f"{n // 100_000_000}억"
        if n >= 10_000:
            return f"{n // 10_000}만"
        if n >= 1_000:
            return f"{n // 1_000}천"
        return str(n)
    text = re.sub(r'[\d,]+', _num_to_kr, text)
    return text


def generate_tts(text: str, output_path: Path) -> float:
    """Send text to ElevenLabs API and save MP3. Returns estimated duration."""
    # 전처리 적용
    text = _preprocess_tts_text(text)

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

    # PROJECT_DIR 우선 (uuid 마이그레이션 후 정확한 경로)
    project_dir_env = os.environ.get("PROJECT_DIR")
    if project_dir_env:
        project_dir = Path(project_dir_env)
    else:
        project_slug = os.environ.get("PROJECT_NAME", "")
        if project_slug:
            # DB에서 정확한 output_dir 조회
            try:
                from auto_agent.db.project_manager import ProjectManager
                pm = ProjectManager()
                project = pm.resolve_project(project_slug)
                if project:
                    project_dir = Path(project["output_dir"])
                else:
                    workspace = PROJECT_ROOT
                    project_dir = workspace / "output" / project_slug
            except Exception:
                workspace = PROJECT_ROOT
                project_dir = workspace / "output" / project_slug
        else:
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

    specs_updated = False
    for i, scene in enumerate(scenes):
        num = scene.get("sceneNumber") or scene["scene_number"]
        # Use narration_tts (pre-processed) if available, else preprocess narration
        if scene.get("narration_tts"):
            text = scene["narration_tts"]
        else:
            raw = scene.get("narration", "")
            text = _preprocess_tts_text(raw) if raw else ""
            if text and text != raw:
                scene["narration_tts"] = text
                specs_updated = True

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

    # narration_tts가 업데이트되었으면 scene_specs 저장
    if specs_updated:
        with open(scene_specs_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  → scene_specs.json에 narration_tts 저장 완료")

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

    # ── Supabase 즉시 업로드 + 에셋 등록 ──
    _upload_audio_to_supabase(project_dir, results)


def _upload_audio_to_supabase(output_dir: Path, results: list):
    """생성된 오디오 에셋을 Supabase Storage에 업로드하고 assets 테이블에 등록."""
    try:
        from auto_agent.supabase_client import supabase_enabled
        if not supabase_enabled():
            return
    except ImportError:
        return

    project_slug = os.environ.get("PROJECT_NAME", "")
    if not project_slug:
        return

    try:
        from auto_agent.sync import SyncManager
        sync = SyncManager(project_slug=project_slug, project_dir=output_dir)
        from auto_agent.dashboard.supabase_data import SupabaseProjectManager
        pm = SupabaseProjectManager()
        project = pm.get_project(slug=project_slug)
        if not project:
            return
        pid = project["id"]
    except Exception:
        return

    uploaded = 0
    for r in results:
        if r.get("status") not in ("ok", "exists") or not r.get("path"):
            continue
        audio_path = Path(r["path"])
        if not audio_path.exists():
            continue
        try:
            sync.register_asset(
                project_id=pid,
                local_path=audio_path,
                asset_type="audio",
                scene_number=r.get("scene"),
            )
            uploaded += 1
        except Exception:
            pass

    if uploaded:
        print(f"  [SYNC] Supabase 오디오 업로드 완료: {uploaded}개")


if __name__ == "__main__":
    main()
