"""
Manifest Builder Script
Combines scene_specs.json + motion_plan.json + audio durations + subtitles
into Remotion SceneManifest format (manifest.json).
"""
import json
import os
import struct
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv

from auto_agent.paths import get_workspace_dir; load_dotenv(get_workspace_dir() / ".env")

from auto_agent.scripts.project_paths import PROJECT_ROOT, get_project_dir, get_manifest_path


def get_mp3_duration(path: Path) -> float:
    """Get MP3 duration using ffprobe (accurate) with file-size fallback."""
    if not path.exists():
        return 0.0
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(path)],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            info = json.loads(result.stdout)
            return float(info["format"]["duration"])
    except (subprocess.TimeoutExpired, KeyError, json.JSONDecodeError, FileNotFoundError):
        pass
    # Fallback: estimate from file size (128kbps CBR)
    size = path.stat().st_size
    return (size * 8) / 128000


def parse_srt_file(srt_path: Path) -> list:
    """Parse an SRT file into subtitle entries."""
    if not srt_path.exists():
        return []
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    entries = []
    for block in content.split("\n\n"):
        lines = block.strip().split("\n")
        if len(lines) >= 3:
            times = lines[1].split(" --> ")
            if len(times) == 2:
                start = parse_srt_time(times[0].strip())
                end = parse_srt_time(times[1].strip())
                text = " ".join(lines[2:])
                entries.append({"text": text, "startSec": start, "endSec": end})
    return entries


def load_subtitles(scene_number: int, subtitles_json: Path, subtitle_dir: Path) -> list:
    """Load subtitle entries. SRT 파일이 subtitles.json보다 최신이면 SRT 우선."""
    srt_path = subtitle_dir / f"scene_{scene_number:03d}.srt"
    srt_exists = srt_path.exists()
    json_exists = subtitles_json.exists()

    # SRT가 subtitles.json보다 최신이면 SRT 우선 (수동 수정 반영)
    if srt_exists and json_exists:
        srt_mtime = srt_path.stat().st_mtime
        json_mtime = subtitles_json.stat().st_mtime
        if srt_mtime > json_mtime:
            return parse_srt_file(srt_path)

    # subtitles.json에서 로드
    if json_exists:
        with open(subtitles_json, "r", encoding="utf-8") as f:
            subs_data = json.load(f)
        for scene_sub in subs_data.get("scenes", []):
            if scene_sub["sceneNumber"] == scene_number:
                return [
                    {
                        "text": e["text"],
                        "startSec": e["startSec"],
                        "endSec": e["endSec"],
                    }
                    for e in scene_sub.get("entries", [])
                ]

    # Fallback: SRT 파싱
    return parse_srt_file(srt_path)


def parse_srt_time(time_str: str) -> float:
    """Parse SRT time format (HH:MM:SS,mmm) to seconds."""
    parts = time_str.replace(",", ".").split(":")
    if len(parts) == 3:
        return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    return 0.0


def update_project_symlink(project_dir: Path):
    """remotion/public/project 심볼릭 링크를 현재 프로젝트로 갱신."""
    symlink = PROJECT_ROOT / "remotion" / "public" / "project"
    target = os.path.relpath(project_dir, symlink.parent)

    if symlink.is_symlink():
        current = os.readlink(symlink)
        if current == target:
            return  # 이미 올바른 대상
        symlink.unlink()
    elif symlink.exists():
        # 심볼릭 링크가 아닌 실제 디렉토리/파일이면 건드리지 않음
        print(f"WARNING: {symlink} 이 심볼릭 링크가 아닙니다 — 갱신 건너뜀")
        return

    symlink.symlink_to(target)
    print(f"  Symlink: remotion/public/project -> {target}")


def _build_supabase_url_maps(slug: str) -> tuple:
    """Supabase assets 테이블에서 이미지/오디오 URL 맵 구축.
    Returns (image_urls, audio_urls) — 각각 {scene_num: url} dict.
    Supabase 비활성 시 빈 dict 반환."""
    image_urls: dict[int, str] = {}
    audio_urls: dict[int, str] = {}
    try:
        from auto_agent.supabase_client import supabase_enabled
        if not supabase_enabled():
            return image_urls, audio_urls
        from auto_agent.dashboard.supabase_data import SupabaseProjectManager
        pm = SupabaseProjectManager()
        project = pm.get_project(slug=slug)
        if not project:
            return image_urls, audio_urls
        pid = project["id"]
        # 이미지 URL 조회
        resp = pm.sb.table("assets").select("scene_number, storage_url").eq(
            "project_id", pid).eq("asset_type", "image").execute()
        for row in (resp.data or []):
            sn = row.get("scene_number")
            url = row.get("storage_url")
            if sn is not None and url:
                image_urls[int(sn)] = url
        # 오디오 URL 조회
        resp = pm.sb.table("assets").select("scene_number, storage_url").eq(
            "project_id", pid).eq("asset_type", "audio").execute()
        for row in (resp.data or []):
            sn = row.get("scene_number")
            url = row.get("storage_url")
            if sn is not None and url:
                audio_urls[int(sn)] = url
        print(f"  Supabase URLs: {len(image_urls)} images, {len(audio_urls)} audios")
    except Exception as e:
        print(f"  Supabase URL lookup skipped: {e}")
    return image_urls, audio_urls


def build_manifest():
    project_dir = get_project_dir()
    # Supabase 모드에서는 심볼릭 링크 불필요 (이미지/오디오 모두 URL)
    try:
        from auto_agent.supabase_client import supabase_enabled
        if not supabase_enabled():
            update_project_symlink(project_dir)
    except Exception:
        update_project_symlink(project_dir)
    AUDIO_DIR = project_dir / "audio"
    SUBTITLE_DIR = project_dir / "subtitles"
    SUBTITLES_JSON = project_dir / "subtitles.json"
    IMAGE_DIR = project_dir / "images"

    # 프로젝트 디렉토리 기준 경로 (모듈 레벨 X)
    scene_specs_path = project_dir / "scene_specs.json"
    motion_plan_path = project_dir / "motion_plan.json"
    MANIFEST_OUT = get_manifest_path()
    MANIFEST_LEGACY = PROJECT_ROOT / "remotion" / "public" / "manifest.json"

    if not scene_specs_path.exists():
        print(f"ERROR: {scene_specs_path} 없음")
        import sys; sys.exit(1)
    if not motion_plan_path.exists():
        print(f"ERROR: {motion_plan_path} 없음")
        import sys; sys.exit(1)

    # Load inputs
    with open(scene_specs_path, "r", encoding="utf-8") as f:
        specs = json.load(f)

    with open(motion_plan_path, "r", encoding="utf-8") as f:
        motion = json.load(f)

    # Build motion lookup
    motion_lookup = {}
    for entry in motion["transition_series"]:
        motion_lookup[entry["scene_number"]] = entry

    # Supabase URL 맵 (활성화 시 로컬 경로 대신 사용)
    slug = project_dir.name
    sb_image_urls, sb_audio_urls = _build_supabase_url_maps(slug)

    # 이미지 인덱스 구축 (N+1 파일 검색 방지)
    import shutil
    _image_index: dict[str, Path] = {}  # "scene_001" → Path
    _search_dirs = [IMAGE_DIR, IMAGE_DIR / "search", IMAGE_DIR / "generated"]
    for search_d in _search_dirs:
        if not search_d.exists():
            continue
        for f in search_d.iterdir():
            if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                key = f.stem.rsplit("_", 1)[0] if search_d != IMAGE_DIR else f.stem
                if search_d == IMAGE_DIR:
                    key = f.stem
                else:
                    # search/generated: scene_001_01.png → scene_001
                    parts = f.stem.split("_")
                    key = "_".join(parts[:2]) if len(parts) >= 2 else f.stem
                # 메인 폴더 우선 (덮어쓰지 않음)
                if key not in _image_index or search_d == IMAGE_DIR:
                    _image_index[key] = f

    # Build scene entries
    scenes = []
    for scene in specs["scenes"]:
        num = scene.get("sceneNumber") or scene["scene_number"]

        # Audio path and duration
        audio_path_mp3 = AUDIO_DIR / f"scene_{num:03d}.mp3"
        audio_duration = get_mp3_duration(audio_path_mp3)
        audio_rel = f"project/audio/scene_{num:03d}.mp3" if audio_path_mp3.exists() else ""

        # Supabase URL 우선 사용 (활성화 시)
        if num in sb_audio_urls:
            audio_rel = sb_audio_urls[num]

        # Image path: Supabase URL 우선, 없으면 로컬 인덱스
        image_rel = ""
        scene_key = f"scene_{num:03d}"
        if num in sb_image_urls:
            image_rel = sb_image_urls[num]
        else:
            img_path = _image_index.get(scene_key)
            if img_path:
                # 서브폴더에서 찾은 경우 메인 폴더로 복사
                if img_path.parent != IMAGE_DIR:
                    final = IMAGE_DIR / f"{scene_key}{img_path.suffix}"
                    if not final.exists():
                        shutil.copy2(img_path, final)
                image_rel = f"project/images/{scene_key}{img_path.suffix}"

        # Subtitles
        subtitles = load_subtitles(num, SUBTITLES_JSON, SUBTITLE_DIR)

        # Visualization data: scene_specs에서 visualization 객체 추출
        # creative 필드 기반 렌더링 — vizType 불필요
        viz = scene.get("visualization")
        if not viz:
            # visualization 필드가 없으면 씬 최상위 필드들로 조립
            _skip = {"scene_number", "sceneNumber", "narration", "narration_tts",
                     "durationFrames", "sceneType", "transition", "vizAnimation",
                     "accentColor", "mapScene", "imageAsset", "chapter"}
            viz = {}
            for k, v in scene.items():
                if k not in _skip:
                    viz[k] = v
            # items/values 기본값 보장 (Remotion VisualizationData 계약)
            viz.setdefault("items", [])
            viz.setdefault("values", [])
            viz.setdefault("unit", "")
            viz.setdefault("source", "")

        # Transition from motion plan or scene_specs
        motion_entry = motion_lookup.get(num, {})
        transition_in = motion_entry.get("transition_in", scene.get("transition", {}))
        transition = {
            "type": transition_in.get("type", "crossfade"),
            "durationFrames": transition_in.get("duration_frames", transition_in.get("durationFrames", 15)),
        }

        # Ken Burns (only for image scenes)
        has_image = bool(image_rel) or scene.get("sceneType") == "image_scene" or bool(scene.get("imageAsset"))
        ken_burns = {
            "enabled": has_image,
            "zoomFactor": 1.08 if has_image else 1.0,
            "zoomDirection": "in" if has_image else "in",
            "panDirection": "none",
        }

        # VizAnimation
        viz_anim = scene.get("vizAnimation", {})
        viz_animation = {
            "stagger": viz_anim.get("stagger", 6),
            "itemDuration": viz_anim.get("itemDuration", 20),
            "easing": viz_anim.get("easing", "easeOut"),
        }

        entry = {
            "sceneNumber": num,
            "imagePath": image_rel,
            "audioPath": audio_rel,
            "audioDurationSec": round(audio_duration, 3),
            "subtitles": subtitles,
            "visualization": viz,
            "kenBurns": ken_burns,
            "transition": transition,
            "vizAnimation": viz_animation,
        }

        # imageAsset 메타데이터 패스스루 (placement, opacity)
        if scene.get("imageAsset") and image_rel:
            ia = scene["imageAsset"]
            entry["imageAsset"] = {
                "placement": ia.get("placement", "background"),
                "opacity": ia.get("opacity", 0.4),
            }

        # mapScene 패스스루 (creative direction에서 지도 씬 결정)
        if scene.get("mapScene"):
            entry["mapScene"] = scene["mapScene"]

        scenes.append(entry)

    # 프로젝트 config에서 폰트/아트스타일 설정 읽기
    font_family = "Pretendard"
    art_style = None
    try:
        from auto_agent.db.connection import db_exists
        if db_exists():
            from auto_agent.db.project_manager import ProjectManager
            pm_font = ProjectManager()
            slug = project_dir.name
            proj = pm_font.get_project(slug=slug)
            if proj:
                cfg = pm_font.get_config(proj["id"])
                font_family = cfg.get("font_family", "Pretendard")
                art_style = cfg.get("art_style")
    except Exception:
        pass

    # Build manifest
    topic = specs.get("topic", project_dir.name.replace("_", " "))
    manifest = {
        "meta": {
            "topic": topic,
            "resolution": {"width": 1920, "height": 1080},
            "fps": 30,
            "subtitleFont": font_family,
            "vizFont": font_family,
            **({"artStyle": art_style} if art_style else {}),
        },
        "scenes": scenes,
        "bgm": None,
    }

    # Also create subtitleConfig for rendering
    subtitle_config = {
        "visible": True,
        "fontFamily": font_family,
        "fontSize": 44,
        "fontWeight": 700,
        "color": "#FFFFFF",
        "strokeColor": "#3D3B2F",
        "strokeWidth": 2,
        "keywordColor": "#F7D94C",
        "keywordStrokeColor": "#5A4B00",
        "bottomOffset": 30,
        "maxWidth": "85%",
        "lineHeight": 1.5,
    }

    # The props file that Remotion expects
    props = {
        "manifest": manifest,
        "subtitleConfig": subtitle_config,
    }

    # Write manifest
    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_OUT, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False, indent=2)

    # 레거시 호환: manifest.json에도 복사
    if MANIFEST_OUT != MANIFEST_LEGACY:
        MANIFEST_LEGACY.parent.mkdir(parents=True, exist_ok=True)
        with open(MANIFEST_LEGACY, "w", encoding="utf-8") as f:
            json.dump(props, f, ensure_ascii=False, indent=2)

    # DB 에셋 등록 (선택적)
    try:
        from auto_agent.db.connection import db_exists
        if db_exists():
            from auto_agent.db.project_manager import ProjectManager
            pm = ProjectManager()
            slug = project_dir.name
            project = pm.get_project(slug=slug)
            if project:
                pm.register_asset(
                    project["id"], "json", str(MANIFEST_OUT),
                    metadata={"type": "manifest"},
                )
    except Exception:
        pass

    # SRT → subtitles.json 역동기화: SRT가 더 최신인 씬의 entries를 subtitles.json에 반영
    if SUBTITLES_JSON.exists():
        with open(SUBTITLES_JSON, "r", encoding="utf-8") as f:
            subs_data = json.load(f)
        json_mtime = SUBTITLES_JSON.stat().st_mtime
        updated = False
        sub_lookup = {s["sceneNumber"]: s for s in subs_data.get("scenes", [])}
        for s in scenes:
            num = s["sceneNumber"]
            srt_path = SUBTITLE_DIR / f"scene_{num:03d}.srt"
            if srt_path.exists() and srt_path.stat().st_mtime > json_mtime:
                srt_entries = parse_srt_file(srt_path)
                if srt_entries and num in sub_lookup:
                    sub_lookup[num]["entries"] = [
                        {"index": i + 1, "text": e["text"], "startSec": e["startSec"], "endSec": e["endSec"]}
                        for i, e in enumerate(srt_entries)
                    ]
                    updated = True
        if updated:
            subs_data["scenes"] = list(sub_lookup.values())
            with open(SUBTITLES_JSON, "w", encoding="utf-8") as f:
                json.dump(subs_data, f, ensure_ascii=False, indent=2)
            print("  subtitles.json synced from SRT edits")

    # Stats
    total_duration = sum(s["audioDurationSec"] for s in scenes)
    total_frames = int(total_duration * 30)
    scenes_with_audio = sum(1 for s in scenes if s["audioPath"])
    scenes_with_viz = sum(1 for s in scenes if s["visualization"])
    scenes_with_subs = sum(1 for s in scenes if s["subtitles"])

    print(f"Manifest built: {MANIFEST_OUT}")
    print(f"  Scenes: {len(scenes)}")
    print(f"  With audio: {scenes_with_audio}")
    print(f"  With viz: {scenes_with_viz}")
    print(f"  With subtitles: {scenes_with_subs}")
    print(f"  Total duration: {total_duration:.1f}s ({total_duration/60:.1f}min)")
    print(f"  Total frames: {total_frames}")


def _probe_mp3_duration(url: str) -> float:
    """MP3 URL에서 첫 몇 KB만 다운로드하여 mutagen으로 duration 측정."""
    import io
    import urllib.request
    try:
        from mutagen.mp3 import MP3
        data = urllib.request.urlopen(url).read()
        mp3 = MP3(io.BytesIO(data))
        return round(mp3.info.length, 3)
    except Exception:
        # fallback: Content-Length 기반 추정 (128kbps TTS 기준)
        try:
            req = urllib.request.Request(url, method="HEAD")
            resp = urllib.request.urlopen(req)
            size = int(resp.headers.get("Content-Length", 0))
            return round(size / 16000, 1) if size else 0.0  # 128kbps = 16000 bytes/s
        except Exception:
            return 0.0


def build_manifest_supabase(project_id: str, storage_key: str):
    """Supabase Storage 기반 manifest 빌드.
    이미지/오디오 경로를 Supabase 공개 URL로 설정."""
    from auto_agent.supabase_client import get_supabase, BUCKET_NAME

    sb = get_supabase()
    bucket = BUCKET_NAME

    # scene_specs.json 다운로드
    specs_data = sb.storage.from_(bucket).download(f"{storage_key}/scene_specs.json")
    specs = json.loads(specs_data)

    # motion_plan.json 다운로드 (없으면 빈 구조)
    try:
        motion_data = sb.storage.from_(bucket).download(f"{storage_key}/motion_plan.json")
        motion = json.loads(motion_data)
    except Exception:
        motion = {"transition_series": []}

    # subtitles.json 다운로드 (없으면 빈 구조)
    try:
        subs_raw = sb.storage.from_(bucket).download(f"{storage_key}/subtitles.json")
        subs_data = json.loads(subs_raw)
    except Exception:
        subs_data = {"scenes": []}

    motion_lookup = {}
    for entry in motion.get("transition_series", []):
        motion_lookup[entry["scene_number"]] = entry

    sub_lookup = {s["sceneNumber"]: s for s in subs_data.get("scenes", [])}

    # Storage 파일 목록으로 이미지/오디오 URL 구축
    def public_url(path: str) -> str:
        return sb.storage.from_(bucket).get_public_url(f"{storage_key}/{path}")

    # 이미지/오디오 파일 목록 (한 번에 조회)
    image_files = {}
    try:
        for f in sb.storage.from_(bucket).list(f"{storage_key}/images"):
            name = f.get("name", "")
            if any(name.lower().endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp")):
                # scene_001.png → scene_001
                key = name.rsplit(".", 1)[0]
                image_files[key] = f"images/{name}"
    except Exception:
        pass

    audio_files = {}
    try:
        for f in sb.storage.from_(bucket).list(f"{storage_key}/audio"):
            name = f.get("name", "")
            if name.endswith(".mp3"):
                key = name.rsplit(".", 1)[0]
                audio_files[key] = f"audio/{name}"
    except Exception:
        pass

    # TTS 메타데이터 (duration 정보)
    tts_meta = {}
    try:
        tts_raw = sb.storage.from_(bucket).download(f"{storage_key}/tts_metadata.json")
        tts_data = json.loads(tts_raw)
        for entry in tts_data if isinstance(tts_data, list) else tts_data.get("scenes", []):
            tts_meta[entry.get("sceneNumber", entry.get("scene_number"))] = entry
    except Exception:
        pass

    scenes = []
    for scene in specs["scenes"]:
        num = scene.get("sceneNumber") or scene["scene_number"]
        scene_key = f"scene_{num:03d}"

        # Audio URL
        audio_rel = audio_files.get(scene_key, "")
        audio_url = public_url(audio_rel) if audio_rel else ""
        # duration: tts_metadata > MP3 probe > durationFrames/fps > 0
        audio_duration = tts_meta.get(num, {}).get("duration", 0.0)
        if not audio_duration and audio_url:
            audio_duration = _probe_mp3_duration(audio_url)
        if not audio_duration and scene.get("durationFrames"):
            specs_fps = specs.get("meta", {}).get("fps", 60)
            audio_duration = scene["durationFrames"] / specs_fps

        # Image URL
        image_rel = image_files.get(scene_key, "")
        image_url = public_url(image_rel) if image_rel else ""

        # Subtitles
        sub_entries = []
        if num in sub_lookup:
            sub_entries = [
                {"text": e["text"], "startSec": e["startSec"], "endSec": e["endSec"]}
                for e in sub_lookup[num].get("entries", [])
            ]

        # Visualization
        viz = scene.get("visualization")
        if not viz:
            _skip = {"scene_number", "sceneNumber", "narration", "narration_tts",
                     "durationFrames", "sceneType", "transition", "vizAnimation",
                     "accentColor", "mapScene", "imageAsset", "chapter"}
            viz = {k: v for k, v in scene.items() if k not in _skip}
            viz.setdefault("items", [])
            viz.setdefault("values", [])
            viz.setdefault("unit", "")
            viz.setdefault("source", "")

        # Transition
        motion_entry = motion_lookup.get(num, {})
        transition_in = motion_entry.get("transition_in", scene.get("transition", {}))
        transition = {
            "type": transition_in.get("type", "crossfade"),
            "durationFrames": transition_in.get("duration_frames", transition_in.get("durationFrames", 15)),
        }

        # Ken Burns
        has_image = bool(image_url) or bool(scene.get("imageAsset"))
        ken_burns = {
            "enabled": has_image,
            "zoomFactor": 1.08 if has_image else 1.0,
            "zoomDirection": "in",
            "panDirection": "none",
        }

        # VizAnimation
        viz_anim = scene.get("vizAnimation", {})
        viz_animation = {
            "stagger": viz_anim.get("stagger", 6),
            "itemDuration": viz_anim.get("itemDuration", 20),
            "easing": viz_anim.get("easing", "easeOut"),
        }

        entry = {
            "sceneNumber": num,
            "imagePath": image_url,    # Supabase 공개 URL
            "audioPath": audio_url,    # Supabase 공개 URL
            "audioDurationSec": round(audio_duration, 3),
            "subtitles": sub_entries,
            "visualization": viz,
            "kenBurns": ken_burns,
            "transition": transition,
            "vizAnimation": viz_animation,
        }

        if scene.get("imageAsset") and image_url:
            ia = scene["imageAsset"]
            entry["imageAsset"] = {
                "placement": ia.get("placement", "background"),
                "opacity": ia.get("opacity", 0.4),
            }

        if scene.get("mapScene"):
            entry["mapScene"] = scene["mapScene"]

        scenes.append(entry)

    # Manifest 조립
    topic = specs.get("topic", storage_key)
    manifest = {
        "meta": {
            "topic": topic,
            "resolution": {"width": 1920, "height": 1080},
            "fps": 30,
            "subtitleFont": "Pretendard",
            "vizFont": "Pretendard",
        },
        "scenes": scenes,
        "bgm": None,
    }

    subtitle_config = {
        "visible": True,
        "fontFamily": "Pretendard",
        "fontSize": 44,
        "fontWeight": 700,
        "color": "#FFFFFF",
        "strokeColor": "#3D3B2F",
        "strokeWidth": 2,
        "keywordColor": "#F7D94C",
        "keywordStrokeColor": "#5A4B00",
        "bottomOffset": 30,
        "maxWidth": "85%",
        "lineHeight": 1.5,
    }

    props = {"manifest": manifest, "subtitleConfig": subtitle_config}

    # 로컬 manifest 파일 저장
    workspace = get_workspace_dir()
    manifest_dir = workspace / "remotion" / "public" / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"{storage_key}.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False, indent=2)

    # 레거시 manifest.json에도 복사
    legacy_path = workspace / "remotion" / "public" / "manifest.json"
    with open(legacy_path, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False, indent=2)

    total_duration = sum(s["audioDurationSec"] for s in scenes)
    print(f"Supabase manifest built: {manifest_path}")
    print(f"  Scenes: {len(scenes)}, Audio: {sum(1 for s in scenes if s['audioPath'])}")
    print(f"  Total duration: {total_duration:.1f}s ({total_duration/60:.1f}min)")
    return manifest_path


if __name__ == "__main__":
    # --supabase 모드
    if "--supabase" in sys.argv:
        idx = sys.argv.index("--supabase")
        if idx + 2 < len(sys.argv):
            pid = sys.argv[idx + 1]
            skey = sys.argv[idx + 2]
            build_manifest_supabase(pid, skey)
        else:
            print("Usage: build_manifest.py --supabase <project_id> <storage_key>")
            sys.exit(1)
    else:
        build_manifest()
