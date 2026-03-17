"""
Manifest Builder Script (Supabase 전용)
Combines scene_specs.json + motion_plan.json + audio durations + subtitles
into Remotion SceneManifest format (manifest.json).

모든 이미지/오디오는 Supabase Storage 공개 URL로 참조.
"""
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

from auto_agent.paths import get_workspace_dir; load_dotenv(get_workspace_dir() / ".env")


def _probe_mp3_duration(url: str) -> float:
    """MP3 URL에서 duration 측정 (mutagen → Content-Length fallback)."""
    import io
    import urllib.request
    try:
        from mutagen.mp3 import MP3
        data = urllib.request.urlopen(url).read()
        mp3 = MP3(io.BytesIO(data))
        return round(mp3.info.length, 3)
    except Exception:
        try:
            req = urllib.request.Request(url, method="HEAD")
            resp = urllib.request.urlopen(req)
            size = int(resp.headers.get("Content-Length", 0))
            return round(size / 16000, 1) if size else 0.0  # 128kbps
        except Exception:
            return 0.0


def build_manifest(project_id: str, storage_key: str):
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

    # 파일 프리픽스: storage_key에서 proj- 제거 후 앞 6자
    file_prefix = storage_key.replace("proj-", "")[:6]

    def _strip_prefix(name: str) -> str:
        """파일명에서 프리픽스 제거 → scene_NNN 키 추출."""
        if name.startswith(f"{file_prefix}_"):
            return name[len(file_prefix) + 1:]
        return name

    # 이미지/오디오 파일 목록 (한 번에 조회)
    image_files = {}
    try:
        for f in sb.storage.from_(bucket).list(f"{storage_key}/images"):
            name = f.get("name", "")
            if any(name.lower().endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp")):
                key = _strip_prefix(name).rsplit(".", 1)[0]
                image_files[key] = f"images/{name}"
    except Exception:
        pass

    audio_files = {}
    try:
        for f in sb.storage.from_(bucket).list(f"{storage_key}/audio"):
            name = f.get("name", "")
            if name.endswith(".mp3"):
                key = _strip_prefix(name).rsplit(".", 1)[0]
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

    # 프로젝트 config에서 폰트/아트스타일/테마 읽기
    font_family = "Pretendard"
    art_style = None
    video_theme = "dark"
    try:
        proj_resp = sb.table("projects").select("config").eq("id", project_id).execute()
        if proj_resp.data:
            cfg = proj_resp.data[0].get("config") or {}
            font_family = cfg.get("font_family", "Pretendard")
            art_style = cfg.get("art_style")
            video_theme = cfg.get("video_theme", "dark")
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
            "imagePath": image_url,
            "audioPath": audio_url,
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
            "subtitleFont": font_family,
            "vizFont": font_family,
            "videoTheme": video_theme,
            **({"artStyle": art_style} if art_style else {}),
        },
        "scenes": scenes,
        "bgm": None,
    }

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
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    with open(legacy_path, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False, indent=2)

    total_duration = sum(s["audioDurationSec"] for s in scenes)
    print(f"Manifest built: {manifest_path}")
    print(f"  Scenes: {len(scenes)}, Audio: {sum(1 for s in scenes if s['audioPath'])}")
    print(f"  Total duration: {total_duration:.1f}s ({total_duration/60:.1f}min)")
    return manifest_path


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        # build_manifest.py <project_id> <storage_key>
        # 또는 build_manifest.py --supabase <project_id> <storage_key> (레거시 호환)
        args = [a for a in sys.argv[1:] if not a.startswith("--")]
        if len(args) >= 2:
            build_manifest(args[0], args[1])
        else:
            print("Usage: build_manifest.py <project_id> <storage_key>")
            sys.exit(1)
    else:
        print("Usage: build_manifest.py <project_id> <storage_key>")
        sys.exit(1)
