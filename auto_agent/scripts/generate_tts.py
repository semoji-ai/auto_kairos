"""
TTS Audio Generation Script
Reads scene_specs.json, sends narration_tts to ElevenLabs API, saves audio files.
"""
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Load .env
from auto_agent.paths import get_workspace_dir; load_dotenv(get_workspace_dir() / ".env")
from auto_agent.tools.scene_id import load_scene_specs

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
    """voice_id, voice_settings 해석: DB → pipeline_state → .env → 기본값."""
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

    # 2) pipeline_state.json config 폴백 (runner가 writing_style에서 매핑한 voice_id)
    if not voice_id:
        try:
            from pathlib import Path
            output_dir = Path(os.environ.get("PROJECT_OUTPUT_DIR", ""))
            if not output_dir.exists():
                # 활성 프로젝트의 output_dir 찾기
                from auto_agent.db.connection import db_exists
                if db_exists():
                    from auto_agent.db.project_manager import ProjectManager
                    pm = ProjectManager()
                    project = pm.get_active_project()
                    if project:
                        output_dir = Path(project.get("output_dir", ""))
            state_file = output_dir / "pipeline_state.json"
            if state_file.exists():
                state = json.loads(state_file.read_text(encoding="utf-8"))
                config = state.get("config", {})
                voice_id = config.get("voice_id")
                vs = config.get("voice_settings")
                if vs:
                    voice_settings = vs
        except Exception:
            pass

    # 3) .env 폴백
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


# 의심 패턴: 변환되지 않은 숫자/영문 단어/마크다운이 잔존하면 재처리 트리거
_SUSPECT_PATTERNS = [
    re.compile(r'\d+'),                # 임의의 숫자
    re.compile(r'[A-Za-z]{2,}'),       # 영문 단어 2글자 이상
    re.compile(r'\*\*'),               # 마크다운 볼드
]


def _is_suspect(text: str) -> list:
    """의심 패턴 잔존 여부 검사. 발견된 패턴 리스트 반환 (빈 리스트 = OK)."""
    if not text:
        return []
    found = []
    for pat in _SUSPECT_PATTERNS:
        m = pat.search(text)
        if m:
            found.append(m.group(0))
    return found


def _preprocess_tts_text(text: str) -> tuple:
    """TTS 전처리 — 공용 TTSPreprocessor를 통해 direct/script 경로를 정렬.

    Returns:
        (processed_text, changes_list). silent failure 없음 — 예외는 위로 전파.
    """
    if not text:
        return text, []

    from auto_agent.tools.korean_tts_preprocessor import KoreanTTSPreprocessor

    preprocessor = KoreanTTSPreprocessor()
    result, changes = preprocessor.process_text(text)
    if changes:
        logger.info("TTS 전처리 (%d 변환): %s", len(changes), changes)
    return result, changes


def _normalize_alignment_text(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def _split_subtitle_lines(text: str) -> list[str]:
    if not text or not text.strip():
        return []
    from auto_agent.scripts.generate_subtitles import smart_split, fix_decimal_splits, fix_quote_splits

    lines = smart_split(text)
    lines = fix_decimal_splits(lines)
    lines = fix_quote_splits(lines)
    return [line.strip() for line in lines if line and line.strip()]


def _derive_subtitle_lines_tts(display_lines: list[str], narration_tts: str) -> tuple[list[str] | None, list[str]]:
    if not display_lines or not narration_tts:
        return None, []

    derived: list[str] = []
    changes: list[str] = []
    for line in display_lines:
        processed, line_changes = _preprocess_tts_text(line)
        processed = (processed or "").strip()
        if not processed:
            return None, []
        derived.append(processed)
        changes.extend(line_changes)

    if _normalize_alignment_text("".join(derived)) != _normalize_alignment_text(narration_tts):
        return None, []
    return derived, changes


def _ensure_subtitle_line_contract(scene: dict, raw_text: str, tts_text: str, scene_changes: list[str]) -> bool:
    changed = False
    display_lines = scene.get("subtitle_lines")
    if display_lines and isinstance(display_lines, list) and len(display_lines) > 0:
        display_lines = [line.strip() for line in display_lines if str(line).strip()]
    else:
        display_lines = _split_subtitle_lines(raw_text)
        if display_lines:
            scene["subtitle_lines"] = display_lines
            changed = True

    if display_lines:
        existing_tts_lines = scene.get("subtitle_lines_tts")
        if existing_tts_lines and isinstance(existing_tts_lines, list) and len(existing_tts_lines) > 0:
            existing_tts_lines = [line.strip() for line in existing_tts_lines if str(line).strip()]
        else:
            existing_tts_lines = None

        derived_tts_lines, line_changes = _derive_subtitle_lines_tts(display_lines, tts_text)
        final_tts_lines = derived_tts_lines or existing_tts_lines or _split_subtitle_lines(tts_text)
        if final_tts_lines and scene.get("subtitle_lines_tts") != final_tts_lines:
            scene["subtitle_lines_tts"] = final_tts_lines
            changed = True
        if line_changes:
            scene_changes.extend(line_changes)

    if scene_changes and scene.get("tts_changes") != scene_changes:
        scene["tts_changes"] = scene_changes
        changed = True

    return changed


def generate_tts(text: str, output_path: Path) -> float:
    """Send preprocessed text to the shared ElevenLabs client and save MP3."""
    from auto_agent.tools.elevenlabs import ElevenLabsClient

    client = ElevenLabsClient(
        tts_provider="elevenlabs",
        elevenlabs_api_key=API_KEY,
        voice_id=VOICE_ID,
        model_id=MODEL_ID,
        voice_settings=VOICE_SETTINGS,
    )
    return client.generate_preprocessed_tts(text, output_path)


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

    data = load_scene_specs(scene_specs_path)

    scenes = data["scenes"]

    # --scene N 옵션: 특정 씬만 처리 (대시보드 수동 재생성)
    target_scene = None
    argv = sys.argv[1:]
    for idx, arg in enumerate(argv):
        if arg == "--scene" and idx + 1 < len(argv):
            target_scene = int(argv[idx + 1])
            break
    if target_scene is not None:
        scenes = [s for s in scenes if (s.get("sceneNumber") or s.get("scene_number")) == target_scene]
        print(f"--scene {target_scene}: {len(scenes)}개 씬만 처리")

    total = len(scenes)
    results = []

    print(f"Generating TTS for {total} scenes...")
    print(f"Output: {OUTPUT_DIR}")
    print()

    specs_updated = False
    preprocess_log = []  # 씬별 (original, processed, changes) 기록
    for i, scene in enumerate(scenes):
        num = scene.get("sceneNumber") or scene["scene_number"]
        raw = scene.get("narration", "") or ""
        existing_tts = scene.get("narration_tts") or ""

        # 정책 (B): LLM이 채운 narration_tts가 있고, 의심 패턴 잔존 없으면 그대로 사용.
        # 의심 패턴 발견 또는 미생성 → raw narration을 Python으로 전처리.
        scene_changes: list = []
        if existing_tts and not _is_suspect(existing_tts):
            text = existing_tts
            logger.info("Scene %s: 기존 narration_tts 사용 (검증 통과)", num)
        else:
            if existing_tts:
                suspects = _is_suspect(existing_tts)
                logger.warning(
                    "Scene %s: narration_tts 의심 패턴 %s — raw로 재처리",
                    num, suspects,
                )
            if not raw:
                text = ""
            else:
                text, scene_changes = _preprocess_tts_text(raw)
                if text and text != raw:
                    scene["narration_tts"] = text
                    specs_updated = True

        preprocess_log.append({
            "scene": num,
            "original": raw,
            "processed": text,
            "changes": scene_changes,
        })

        if _ensure_subtitle_line_contract(scene, raw, text, scene_changes):
            specs_updated = True
            preprocess_log[-1]["changes"] = scene_changes

        if not text or not text.strip():
            logger.warning("[%d/%d] Scene %s: SKIP (empty narration)", i + 1, total, num)
            results.append({"scene": num, "status": "skipped", "duration": 0})
            continue

        scene_id = scene.get("sceneId", "")
        output_path = OUTPUT_DIR / (f"{scene_id}.mp3" if scene_id else f"scene_{num:03d}.mp3")

        # Skip if already exists
        if output_path.exists():
            size = output_path.stat().st_size
            duration = (size * 8) / 128000
            print(f"  [{i+1}/{total}] Scene {num}: EXISTS ({duration:.1f}s)")
            results.append({"scene": num, "status": "exists", "duration": duration, "path": str(output_path)})
            continue

        try:
            duration = generate_tts(text, output_path)
            # SRT 삭제: timestamps가 새로 생성되므로 기존 SRT는 무효
            srt_stem = scene_id if scene_id else f"scene_{num:03d}"
            srt_path = OUTPUT_DIR.parent / "subtitles" / f"{srt_stem}.srt"
            if srt_path.exists():
                srt_path.unlink()
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
        "preprocessing": preprocess_log,
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
