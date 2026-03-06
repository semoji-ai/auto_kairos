"""
Manifest Builder Script
Combines scene_specs.json + motion_plan.json + audio durations + subtitles
into Remotion SceneManifest format (manifest.json).
"""
import json
import os
import struct
import subprocess
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


def build_manifest():
    project_dir = get_project_dir()
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

    # Build scene entries
    scenes = []
    for scene in specs["scenes"]:
        num = scene.get("sceneNumber") or scene["scene_number"]

        # Audio path and duration
        audio_path_mp3 = AUDIO_DIR / f"scene_{num:03d}.mp3"
        audio_duration = get_mp3_duration(audio_path_mp3)
        audio_rel = f"project/audio/scene_{num:03d}.mp3" if audio_path_mp3.exists() else ""

        # Image path: scene_NNN.png/jpg 또는 images/ 디렉토리 내 모든 파일 검색
        image_rel = ""
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            candidate = IMAGE_DIR / f"scene_{num:03d}{ext}"
            if candidate.exists():
                image_rel = f"project/images/scene_{num:03d}{ext}"
                break
        # imageAsset이 있는 씬: scene 번호로 매칭되는 파일만 사용
        # (아직 생성되지 않은 이미지는 빈 문자열 유지 — 다른 씬 이미지 재사용 금지)
        if not image_rel and scene.get("imageAsset"):
            ia = scene["imageAsset"]
            # wikimedia/search 소스의 경우 query 기반 파일명 매칭 시도
            query = ia.get("query", "")
            if query and IMAGE_DIR.exists():
                query_lower = query.lower().replace(" ", "_")
                for f in sorted(IMAGE_DIR.iterdir()):
                    if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                        if query_lower[:20] in f.stem.lower() or f.stem.lower() in query_lower:
                            image_rel = f"project/images/{f.name}"
                            break

        # Subtitles
        subtitles = load_subtitles(num, SUBTITLES_JSON, SUBTITLE_DIR)

        # Visualization data: scene_specs v4.0에서는 vizType, title, items 등이
        # 씬 최상위에 있으므로 visualization 객체로 조립
        viz = scene.get("visualization")
        if not viz and scene.get("vizType"):
            # 매니페스트/메타 필드 제외한 나머지를 visualization으로 묶기
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
        has_image = bool(image_rel) or scene.get("sceneType") == "image_scene" or scene.get("vizType") == "image_scene"
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

    # Build manifest
    topic = specs.get("topic", project_dir.name.replace("_", " "))
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

    # Also create subtitleConfig for rendering
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


if __name__ == "__main__":
    build_manifest()
