"""
Manifest Builder Script (로컬 중심)
Combines scene_specs.json + motion_plan.json + audio durations + subtitles
into Remotion SceneManifest format (manifest.json).

에셋 참조: 로컬 파일 → Remotion staticFile() 상대 경로.
Supabase는 프로젝트 config 조회에만 사용 (오프라인 시 fallback).
"""
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from auto_agent.paths import get_workspace_dir; load_dotenv(get_workspace_dir() / ".env")


def _probe_mp3_duration_local(path: Path) -> float:
    """로컬 MP3 파일에서 duration 측정."""
    try:
        from mutagen.mp3 import MP3
        mp3 = MP3(str(path))
        return round(mp3.info.length, 3)
    except Exception:
        try:
            size = path.stat().st_size
            return round(size / 16000, 1) if size else 0.0  # 128kbps 추정
        except Exception:
            return 0.0


def _load_project_config(project_id: str, project_dir: str = None) -> dict:
    """프로젝트 config 로드. 로컬 ProjectManager → Supabase fallback."""
    # 1. 로컬 ProjectManager에서 로드
    try:
        from auto_agent.db.project_manager import ProjectManager
        pm = ProjectManager()
        # project_id가 숫자면 ID로, 아니면 slug로 조회
        try:
            pid = int(project_id)
            config = pm.get_config(pid)
        except (ValueError, TypeError):
            proj = pm.get_project(slug=str(project_id))
            config = pm.get_config(proj["id"]) if proj else None
        if config:
            return config
    except Exception:
        pass
    # 2. Supabase fallback
    try:
        from auto_agent.supabase_client import get_supabase, supabase_enabled
        if supabase_enabled():
            sb = get_supabase()
            resp = sb.table("projects").select("config").eq("id", project_id).execute()
            if resp.data:
                return resp.data[0].get("config") or {}
    except Exception:
        pass
    return {}


def build_manifest(project_id: str, storage_key: str, project_dir: str = None):
    """로컬 파일 기반 manifest 빌드.
    이미지/오디오 경로를 Remotion staticFile() 상대 경로로 설정.

    Args:
        project_id: Supabase 프로젝트 UUID (config 조회용)
        storage_key: Storage 경로 키 (매니페스트 파일명)
        project_dir: 프로젝트 출력 디렉토리 (None이면 자동 탐색)
    """
    workspace = get_workspace_dir()

    # 프로젝트 디렉토리 결정
    if project_dir:
        out_dir = Path(project_dir)
    else:
        # output/ 아래에서 찾기
        for d in (workspace / "output").iterdir():
            if d.is_dir():
                if (d / "scene_specs.json").exists():
                    out_dir = d
                    break
        else:
            print("ERROR: scene_specs.json을 찾을 수 없습니다")
            sys.exit(1)

    # ── 로컬 파일 로드 ──
    specs = json.loads((out_dir / "scene_specs.json").read_text(encoding="utf-8"))

    motion = {"transition_series": []}
    motion_path = out_dir / "motion_plan.json"
    if motion_path.exists():
        motion = json.loads(motion_path.read_text(encoding="utf-8"))

    subs_data = {"scenes": []}
    subs_path = out_dir / "subtitles.json"
    if subs_path.exists():
        subs_data = json.loads(subs_path.read_text(encoding="utf-8"))

    tts_results = {}
    tts_path = out_dir / "tts_results.json"
    if tts_path.exists():
        tts_data = json.loads(tts_path.read_text(encoding="utf-8"))
        for r in tts_data.get("results", []):
            tts_results[r["scene"]] = r

    motion_lookup = {}
    for entry in motion.get("transition_series", []):
        motion_lookup[entry["scene_number"]] = entry

    sub_lookup = {s["sceneNumber"]: s for s in subs_data.get("scenes", [])}

    # ── Remotion public 디렉토리에 프로젝트 심볼릭 링크 ──
    remotion_public = workspace / "remotion" / "public"

    # 프로젝트 slug로 심볼릭 링크 (output/{slug} → remotion/public/project)
    # Windows에서 심볼릭 링크는 관리자 권한 필요 → 실패 시 junction 또는 복사로 폴백
    project_link = remotion_public / "project"
    if project_link.exists() or project_link.is_symlink():
        if project_link.is_symlink() or project_link.is_junction() if hasattr(project_link, "is_junction") else False:
            project_link.unlink()
        else:
            import shutil as _sh
            _sh.rmtree(project_link)
    try:
        project_link.symlink_to(out_dir.resolve())
        print(f"    [LINK] remotion/public/project → {out_dir}")
    except OSError:
        # Windows 폴백: junction 시도 → 실패 시 디렉토리 복사
        try:
            import subprocess as _sp
            if os.name == "nt":
                _sp.run(["cmd", "/c", "mklink", "/J", str(project_link), str(out_dir.resolve())],
                        capture_output=True, timeout=10)
                if project_link.exists():
                    print(f"    [JUNCTION] remotion/public/project → {out_dir}")
                else:
                    raise OSError("junction failed")
            else:
                raise OSError("not windows")
        except (OSError, Exception):
            import shutil as _sh
            _sh.copytree(out_dir, project_link, dirs_exist_ok=True)
            print(f"    [COPY] remotion/public/project ← {out_dir}")

    # 하위 호환: assets/{storage_key} 심볼릭 링크도 유지
    if storage_key:
        asset_dir = remotion_public / "assets" / storage_key
        if not asset_dir.exists() and not asset_dir.is_symlink():
            asset_dir.parent.mkdir(parents=True, exist_ok=True)
            try:
                asset_dir.symlink_to(out_dir.resolve())
            except OSError:
                try:
                    if os.name == "nt":
                        import subprocess as _sp2
                        _sp2.run(["cmd", "/c", "mklink", "/J", str(asset_dir), str(out_dir.resolve())],
                                 capture_output=True, timeout=10)
                        if not asset_dir.exists():
                            raise OSError("junction failed")
                    else:
                        raise OSError("not windows")
                except (OSError, Exception):
                    try:
                        import shutil as _sh
                        _sh.copytree(out_dir, asset_dir, dirs_exist_ok=True)
                    except Exception:
                        pass

    def link_asset(src: Path, dest_subdir: str, dest_name: str) -> str:
        """로컬 에셋의 staticFile 상대 경로 반환. project/ 기준."""
        if not src.exists():
            return ""
        return f"project/{dest_subdir}/{dest_name}"

    # ── 씬별 매니페스트 엔트리 생성 ──
    # 프로젝트 config
    cfg = _load_project_config(project_id, str(out_dir))
    font_family = cfg.get("font_family", "Pretendard")
    # art_style: 경로("artstyle/styles/quirky_cartoon.json")이면 스타일명만 추출
    art_style_raw = cfg.get("art_style", "")
    art_style = Path(art_style_raw.replace(".json", "")).name if art_style_raw else ""
    video_theme = cfg.get("video_theme", "dark")
    map_theme = cfg.get("map_theme", "modern_clean")

    # art_style.json에서 배경 이미지 경로 읽기
    default_background = ""
    if art_style:
        for _ast_dir in (out_dir / "artstyle" / "styles", workspace / "auto_agent" / "data" / "artstyle" / "styles"):
            _ast_path = _ast_dir / f"{art_style}.json"
            if _ast_path.exists():
                try:
                    _ast_data = json.loads(_ast_path.read_text(encoding="utf-8"))
                    _bg = (_ast_data.get("design_tokens") or {}).get("defaultBackground", "")
                    # 절대경로 보장: "background/..." → "/background/..."
                    default_background = ("/" + _bg) if _bg and not _bg.startswith("/") else _bg
                except Exception:
                    pass
                break

    # image_assets.json → {sceneNumber: selected_filename} 룩업
    image_assets_lookup = {}
    image_assets_path = out_dir / "images" / "image_assets.json"
    if image_assets_path.exists():
        try:
            ia_data = json.loads(image_assets_path.read_text(encoding="utf-8"))
            for entry in ia_data.get("scenes", []):
                sn = entry.get("sceneNumber")
                sel = entry.get("selected")
                if sn and sel:
                    image_assets_lookup[sn] = sel
        except Exception:
            pass

    scenes = []
    for scene in specs["scenes"]:
        num = scene.get("sceneNumber") or scene["scene_number"]
        scene_key = f"scene_{num:03d}"

        # Audio — 로컬 파일 링크
        audio_src = out_dir / "audio" / f"{scene_key}.mp3"
        audio_path = link_asset(audio_src, "audio", f"{scene_key}.mp3")

        # Duration: tts_results > 로컬 MP3 probe > durationFrames/fps
        audio_duration = tts_results.get(num, {}).get("duration", 0.0)
        if not audio_duration and audio_src.exists():
            audio_duration = _probe_mp3_duration_local(audio_src)
        if not audio_duration and scene.get("durationFrames"):
            specs_fps = specs.get("meta", {}).get("fps", 30)
            audio_duration = scene["durationFrames"] / specs_fps

        # Image — image_assets.json selected 우선 → 루트 → generated/ 순 탐색
        image_path = ""
        selected_file = image_assets_lookup.get(num)
        if selected_file:
            img_src = out_dir / "images" / selected_file
            if img_src.exists():
                image_path = link_asset(img_src, "images", selected_file)
        if not image_path:
            for subdir in ("", "generated/"):
                if image_path:
                    break
                for ext in (".jpg", ".jpeg", ".png", ".webp"):
                    img_src = out_dir / "images" / f"{subdir}{scene_key}{ext}"
                    if img_src.exists():
                        image_path = link_asset(img_src, "images", f"{subdir}{scene_key}{ext}")
                        break

        # Subtitles
        sub_entries = []
        if num in sub_lookup:
            sub_entries = [
                {"text": e["text"], "startSec": e["startSec"], "endSec": e["endSec"]}
                for e in sub_lookup[num].get("entries", [])
            ]

        # Visualization — 플랫 스키마 + 중첩 스키마 모두 지원
        is_flat = "layout" in scene and "motion" in scene  # 플랫 스키마 판별: 최상위에 layout+motion
        viz = scene.get("visualization")
        if is_flat:
            # 플랫: 최상위 필드에서 visualization 블록 조립
            viz = {}
            for k in ("layout", "headline", "items", "values", "unit", "source",
                       "icons", "flags", "chartConfig", "title"):
                if scene.get(k) is not None:
                    viz[k] = scene[k]
            viz.setdefault("items", [])
            viz.setdefault("values", [])
        elif not viz:
            _skip = {"scene_number", "sceneNumber", "narration", "narration_tts",
                     "durationFrames", "sceneType", "transition", "vizAnimation",
                     "accentColor", "mapScene", "imageAsset", "chapter",
                     "layout", "motion", "mood"}
            viz = {k: v for k, v in scene.items() if k not in _skip}
            viz.setdefault("items", [])
            viz.setdefault("values", [])
            viz.setdefault("unit", "")
            viz.setdefault("source", "")

        # chartConfig가 creative 안에 잘못 들어간 경우 → visualization 레벨로 승격
        creative = viz.get("creative", {})
        if creative.get("chartConfig") and not viz.get("chartConfig"):
            viz["chartConfig"] = creative.pop("chartConfig")

        # Motion preset (v5) — motionPreset 필드로 매니페스트에 전달
        motion_preset = scene.get("motion", "")
        mood = scene.get("mood", "")

        # Transition — v5는 motion preset에서 자동 결정, v4는 기존 로직
        if is_flat:
            # motion preset 기반 자동 전환 결정
            _dramatic_motions = {"dramatic_shake", "glitch_alert", "split_compare"}
            if motion_preset in _dramatic_motions:
                transition = {"type": "cut", "durationFrames": 0}
            elif motion_preset == "cinematic_fade":
                transition = {"type": "crossfade", "durationFrames": 20}
            else:
                transition = {"type": "crossfade", "durationFrames": 15}
        else:
            motion_entry = motion_lookup.get(num, {})
            transition_in = motion_entry.get("transition_in", scene.get("transition", {}))
            transition = {
                "type": transition_in.get("type", "crossfade"),
                "durationFrames": transition_in.get("duration_frames", transition_in.get("durationFrames", 15)),
            }

        # Ken Burns
        has_image = bool(image_path) or bool(scene.get("imageAsset"))
        ken_burns = {
            "enabled": has_image,
            "zoomFactor": 1.08 if has_image else 1.0,
            "zoomDirection": "in",
            "panDirection": "none",
        }

        # VizAnimation — v5는 motion preset에서 자동, v4는 기존
        if is_flat:
            # motion preset → vizAnimation 자동 매핑
            _motion_anim_map = {
                "stagger_wave": {"stagger": 6, "itemDuration": 20, "easing": "easeOut"},
                "cascade_rank": {"stagger": 8, "itemDuration": 22, "easing": "easeOut"},
                "fade_rise": {"stagger": 0, "itemDuration": 25, "easing": "easeOut"},
                "count_and_grow": {"stagger": 4, "itemDuration": 30, "easing": "linear"},
                "number_spotlight": {"stagger": 0, "itemDuration": 35, "easing": "easeInOut"},
                "dramatic_shake": {"stagger": 0, "itemDuration": 20, "easing": "easeOut"},
                "bounce_celebrate": {"stagger": 5, "itemDuration": 18, "easing": "easeOut"},
                "calm_float": {"stagger": 8, "itemDuration": 30, "easing": "easeInOut"},
                "type_and_draw": {"stagger": 2, "itemDuration": 25, "easing": "linear"},
                "glitch_alert": {"stagger": 0, "itemDuration": 15, "easing": "easeOut"},
                "pie_spin": {"stagger": 4, "itemDuration": 25, "easing": "easeInOut"},
                "split_compare": {"stagger": 0, "itemDuration": 20, "easing": "easeOut"},
                "map_reveal": {"stagger": 0, "itemDuration": 30, "easing": "easeInOut"},
                "cinematic_fade": {"stagger": 0, "itemDuration": 30, "easing": "easeInOut"},
                "build_sequence": {"stagger": 6, "itemDuration": 20, "easing": "easeOut"},
            }
            viz_animation = _motion_anim_map.get(motion_preset,
                                                  {"stagger": 6, "itemDuration": 20, "easing": "easeOut"})
        else:
            viz_anim = scene.get("vizAnimation", {})
            viz_animation = {
                "stagger": viz_anim.get("stagger", 6),
                "itemDuration": viz_anim.get("itemDuration", 20),
                "easing": viz_anim.get("easing", "easeOut"),
            }

        entry = {
            "sceneNumber": num,
            "imagePath": image_path,
            "audioPath": audio_path,
            "audioDurationSec": round(audio_duration, 3),
            "subtitles": sub_entries,
            "visualization": viz,
            "kenBurns": ken_burns,
            "transition": transition,
            "vizAnimation": viz_animation,
        }

        # motionPreset, mood 필드 추가
        if motion_preset:
            entry["motionPreset"] = motion_preset
        if mood:
            entry["mood"] = mood

        # layout 필드 (v5 최상위 또는 v4 creative 내부)
        scene_layout = scene.get("layout") or viz.get("layout") or viz.get("creative", {}).get("layout", "")
        if scene_layout:
            entry["sceneType"] = scene_layout

        if scene.get("imageAsset"):
            ia = scene["imageAsset"]
            # cinematic 레이아웃은 무조건 fullscreen + opacity 1
            layout = scene_layout or viz.get("creative", {}).get("layout", "")
            if layout == "cinematic":
                entry["imageAsset"] = {"placement": "fullscreen", "opacity": 1.0}
            else:
                entry["imageAsset"] = {
                    "placement": ia.get("placement", "background"),
                    "opacity": ia.get("opacity", 0.4),
                }
            # 검색 이미지 출처
            if ia.get("source_url"):
                entry["imageSource"] = {
                    "url": ia["source_url"],
                    "title": ia.get("source_title", ""),
                }

        # cinematic_overlay → cinematicOverlay 변환
        co = viz.get("cinematic_overlay") or viz.get("cinematicOverlay")
        if co:
            entry.setdefault("visualization", {})["cinematicOverlay"] = {
                "type": co.get("type", "caption"),
                "text": co.get("text", ""),
                "position": co.get("position", "bottom_left"),
            }

        if scene.get("mapScene"):
            ms = dict(scene["mapScene"])
            if not ms.get("mapStyle"):
                ms["mapStyle"] = map_theme
            if not ms.get("mapType"):
                ms["mapType"] = "location_reveal"
            # markers 변환: {lat, lng, label} → {coordinates: [lng, lat], label}
            if ms.get("markers"):
                converted = []
                for mk in ms["markers"]:
                    if "coordinates" in mk:
                        converted.append(mk)
                    elif "lat" in mk and "lng" in mk:
                        converted.append({
                            "coordinates": [mk["lng"], mk["lat"]],
                            "label": mk.get("label", ""),
                            "style": mk.get("style", "pin"),
                        })
                    else:
                        converted.append(mk)
                ms["markers"] = converted
            # center: scene_specs는 [lat, lng], Remotion/MapLibre는 [lng, lat]
            if ms.get("center") and len(ms["center"]) == 2:
                ms["center"] = [ms["center"][1], ms["center"][0]]
            # camera 필드 보장
            center_lnglat = ms.get("center", [0, 0])
            if not ms.get("camera"):
                zoom = ms.get("zoom", 5)
                dur = scene.get("durationFrames", 150)
                ms["camera"] = {
                    "keyframes": [
                        {"frame": 0, "center": list(center_lnglat), "zoom": max(2, zoom - 2)},
                        {"frame": int(dur * 0.4), "center": list(center_lnglat), "zoom": zoom},
                    ],
                    "easing": "easeInOutCubic",
                }
            else:
                for kf in ms.get("camera", {}).get("keyframes", []):
                    if kf.get("center") and len(kf["center"]) == 2:
                        kf["center"] = [kf["center"][1], kf["center"][0]]
            entry["mapScene"] = ms

        scenes.append(entry)

    # Manifest 조립
    topic = specs.get("topic", storage_key)
    design_preset = specs.get("meta", {}).get("designPreset", None)
    manifest = {
        "meta": {
            "topic": topic,
            "resolution": {"width": 1920, "height": 1080},
            "fps": 30,
            "subtitleFont": font_family,
            "vizFont": font_family,
            "videoTheme": video_theme,
            **({"artStyle": art_style} if art_style else {}),
            **({"designPreset": design_preset} if design_preset else {}),
            **({"defaultBackground": default_background} if default_background else {}),
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

    # 매니페스트 파일명 결정: uuid_{slug}.json (DB 조회) 또는 fallback
    try:
        from auto_agent.db.project_manager import ProjectManager
        pm = ProjectManager()
        manifest_fname = pm.get_manifest_filename(
            project_id=int(project_id) if str(project_id).isdigit() else None,
            slug=project_id if not str(project_id).isdigit() else None,
        )
        if not manifest_fname:
            manifest_fname = f"{storage_key}.json"
    except Exception:
        manifest_fname = f"{storage_key}.json"

    # 로컬 manifest 파일 저장
    manifest_dir = remotion_public / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / manifest_fname
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False, indent=2)

    # 레거시 manifest.json에도 복사
    legacy_path = remotion_public / "manifest.json"
    with open(legacy_path, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False, indent=2)


    total_duration = sum(s["audioDurationSec"] for s in scenes)
    audio_count = sum(1 for s in scenes if s["audioPath"])
    image_count = sum(1 for s in scenes if s["imagePath"])
    print(f"Manifest built: {manifest_path}")
    print(f"  Scenes: {len(scenes)}, Audio: {audio_count}, Images: {image_count}")
    print(f"  Total duration: {total_duration:.1f}s ({total_duration/60:.1f}min)")
    print(f"  Project dir: {out_dir}")
    return manifest_path


if __name__ == "__main__":
    if "--local" in sys.argv:
        # 로컬 모드: output 디렉토리에서 직접 빌드
        idx = sys.argv.index("--local")
        if idx + 1 < len(sys.argv):
            local_dir = sys.argv[idx + 1]
            # build_manifest_local: scene_specs.json → manifest.json (로컬 전용)
            from pathlib import Path
            out = Path(local_dir)
            specs_path = out / "scene_specs.json"
            if not specs_path.exists():
                print(f"scene_specs.json not found in {local_dir}")
                sys.exit(1)
            slug = out.name
            build_manifest(slug, slug, str(out))
        else:
            print("Usage: build_manifest.py --local <output_dir>")
            sys.exit(1)
    elif len(sys.argv) >= 3:
        args = [a for a in sys.argv[1:] if not a.startswith("--")]
        if len(args) >= 2:
            project_dir = args[2] if len(args) >= 3 else None
            build_manifest(args[0], args[1], project_dir)
        else:
            print("Usage: build_manifest.py <project_id> <storage_key> [project_dir]")
            sys.exit(1)
    else:
        print("Usage: build_manifest.py <project_id> <storage_key> [project_dir]")
        print("       build_manifest.py --local <output_dir>")
        sys.exit(1)
