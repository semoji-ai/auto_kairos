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
            # UUID 접두사(8자리hex_) 제거 후 재시도
            if not proj:
                parts = str(project_id).split("_", 1)
                if len(parts) == 2 and len(parts[0]) == 8:
                    proj = pm.get_project(slug=parts[1])
            # output_dir 경로 매칭으로 재시도
            if not proj and project_dir:
                for p in (pm.list_projects() or []):
                    if str(p.get("output_dir", "")).rstrip("/") == str(project_dir).rstrip("/"):
                        proj = p
                        break
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
        if project_link.is_symlink():
            project_link.unlink()
        elif hasattr(project_link, "is_junction") and project_link.is_junction():
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
                # 새 포맷: images[].selected
                for img in entry.get("images", []):
                    if img.get("selected"):
                        image_assets_lookup[sn] = img["file"]
                        break
                # 구 포맷 호환: selected 문자열
                if sn not in image_assets_lookup:
                    sel = entry.get("selected")
                    if sn and sel:
                        image_assets_lookup[sn] = sel
        except Exception:
            pass

    # audio_assets.json → {sceneNumber: selected_audioFile} 룩업
    audio_assets_lookup: dict = {}
    audio_assets_path = out_dir / "audio" / "audio_assets.json"
    if audio_assets_path.exists():
        try:
            aa_data = json.loads(audio_assets_path.read_text(encoding="utf-8"))
            for aa_entry in aa_data.get("scenes", []):
                sn = aa_entry.get("sceneNumber")
                selected = aa_entry.get("selected")
                if sn is not None and selected:
                    audio_assets_lookup[sn] = selected
        except Exception:
            pass

    # video_assets.json → {sceneNumber: videoAsset} 룩업
    video_assets_lookup: dict = {}
    video_assets_path = out_dir / "video_assets.json"
    if video_assets_path.exists():
        try:
            va_data = json.loads(video_assets_path.read_text(encoding="utf-8"))
            for va_entry in va_data.get("scenes", []):
                sn = va_entry.get("sceneNumber")
                if sn is not None:
                    video_assets_lookup[sn] = va_entry
        except Exception:
            pass

    scenes = []
    for scene in specs["scenes"]:
        num = scene["sceneNumber"] if scene.get("sceneNumber") is not None else scene["scene_number"]
        scene_key = f"scene_{num:03d}"

        # Audio — audio_assets.json selected 우선 → scene_{num}.mp3 폴백
        selected_audio = audio_assets_lookup.get(num)
        if selected_audio:
            audio_src = out_dir / "audio" / selected_audio
            audio_path = link_asset(audio_src, "audio", selected_audio)
        else:
            audio_src = out_dir / "audio" / f"{scene_key}.mp3"
            audio_path = link_asset(audio_src, "audio", f"{scene_key}.mp3")

        # Duration: 로컬 MP3 probe > tts_results > durationFrames/fps
        audio_duration = 0.0
        if audio_src.exists():
            audio_duration = _probe_mp3_duration_local(audio_src)
        if not audio_duration:
            audio_duration = tts_results.get(num, {}).get("duration", 0.0)
        if not audio_duration and scene.get("durationFrames"):
            specs_fps = specs.get("meta", {}).get("fps", 30)
            audio_duration = scene["durationFrames"] / specs_fps

        # Image — imageAsset.source == "none" 이면 이미지 없음 (탐색 스킵)
        _ia_source = (scene.get("imageAsset") or {}).get("source", "")
        image_path = ""
        if _ia_source == "none":
            pass  # 이미지 없음 — image_path 빈 문자열 유지
        # Image — image_assets.json selected 우선 → 루트 → generated/ 순 탐색
        selected_file = image_assets_lookup.get(num) if _ia_source != "none" else None
        if selected_file:
            # 절대경로가 들어온 경우 → 상대 파일명만 추출
            selected_file = selected_file.replace("\\", "/")
            if "/" in selected_file and not selected_file.startswith(("generated/", "search/")):
                # C:/Users/.../images/scene_001.png → scene_001.png
                selected_file = Path(selected_file).name
            img_src = out_dir / "images" / selected_file
            if img_src.exists():
                image_path = link_asset(img_src, "images", selected_file)
        if not image_path and _ia_source != "none":
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
            # 기존 visualization.creative는 에디터 저장값(showHeadline 등)이 있으므로 보존
            _old_creative = (scene.get("visualization") or {}).get("creative", {})
            viz = {}
            for k in ("layout", "headline", "items", "values", "unit", "source",
                       "icons", "flags", "chartConfig", "title"):
                if scene.get(k) is not None:
                    viz[k] = scene[k]
            viz.setdefault("items", [])
            viz.setdefault("values", [])
            if _old_creative:
                viz["creative"] = _old_creative
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
        has_image = bool(image_path) and _ia_source != "none"
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

        # person_card 개인 사진 — scene_NNN_person_01.jpg, _02, _03 ...
        # images/, images/search/, images/generate/ 서브디렉토리 모두 탐색
        person_images: list = []
        subdirs = ["", "search/", "generate/"]
        for pi in range(1, 10):
            found = False
            for subdir in subdirs:
                for ext in (".jpg", ".jpeg", ".png", ".webp"):
                    p_src = out_dir / "images" / f"{subdir}{scene_key}_person_{pi:02d}{ext}"
                    if p_src.exists():
                        person_images.append(link_asset(p_src, "images", f"{subdir}{scene_key}_person_{pi:02d}{ext}"))
                        found = True
                        break
                if found:
                    break
            if not found:
                break  # 해당 번호 파일 없으면 중단

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
        if person_images:
            entry["images"] = person_images
        elif image_path and scene.get("layout") == "person_card":
            # person_card 레이아웃인데 개별 _person_NN 파일이 없으면
            # 씬 이미지 자체를 images[0]에 폴백 (단체 사진 등)
            entry["images"] = [image_path]

        # motionPreset, mood, chapter 필드 추가
        if motion_preset:
            entry["motionPreset"] = motion_preset
        if mood:
            entry["mood"] = mood
        if scene.get("chapter") is not None:
            entry["chapter"] = scene["chapter"]

        # layout 필드 — 단일 소스: 항상 최상위 "layout"으로 기록
        # sceneType은 하위호환용 alias로만 남김
        scene_layout = scene.get("layout") or viz.get("layout") or viz.get("creative", {}).get("layout", "")
        # quote는 레거시 → quote_portrait로 정규화
        if scene_layout == "quote":
            scene_layout = "quote_portrait"
        if scene_layout:
            entry["layout"] = scene_layout   # 단일 소스
            entry["sceneType"] = scene_layout  # 하위호환 유지

        if scene.get("imageAsset"):
            ia = scene["imageAsset"]
            # source: "none" — 이미지 없음 플래그를 매니페스트에 전달
            if ia.get("source") == "none":
                entry["imageAsset"] = {"placement": ia.get("placement", "background"), "opacity": ia.get("opacity", 1.0), "source": "none"}
            else:
                # cinematic/quote 레이아웃은 무조건 opacity 1
                layout = scene_layout or viz.get("creative", {}).get("layout", "")
                _is_quote = layout in ("quote", "quote_portrait")
                if layout == "cinematic":
                    entry["imageAsset"] = {"placement": "fullscreen", "opacity": 1.0}
                else:
                    p = ia.get("placement", "background")
                    # quote/quote_portrait는 배경 이미지 항상 100%
                    opacity = 1.0 if _is_quote else ia.get("opacity", 1.0)
                    image_asset: dict = {
                        "placement": p,
                        "opacity": opacity,
                    }
                    if ia.get("offsetX") is not None:
                        image_asset["offsetX"] = ia["offsetX"]
                    if ia.get("offsetY") is not None:
                        image_asset["offsetY"] = ia["offsetY"]
                    if ia.get("scale") is not None:
                        image_asset["scale"] = ia["scale"]
                    # chartagent SVG 차트: source + chartSvgPath 주입
                    entry["imageAsset"] = image_asset
            # 검색 이미지 출처
            if ia.get("source_url"):
                entry["imageSource"] = {
                    "url": ia["source_url"],
                    "title": ia.get("source_title", ""),
                }

        # Video — video_assets.json에 있으면 videoPath + videoAsset 주입
        va_entry = video_assets_lookup.get(num)
        if va_entry:
            static_path = va_entry.get("staticPath", "")  # remotion/public/ 기준 직접 경로
            video_file = va_entry.get("videoFile", "")
            video_src = out_dir / "video_sources" / video_file if video_file else None
            video_path_str = ""
            if static_path:
                video_path_str = static_path  # public/background/... 등 직접 사용
            elif video_src and video_src.exists():
                video_path_str = link_asset(video_src, "video_sources", video_file)
            entry["videoPath"] = video_path_str
            entry["videoAsset"] = {
                "placement": va_entry.get("placement", "background"),
                "startSec": va_entry.get("startSec", 0.0),
                "endSec": va_entry.get("endSec", None),
                "opacity": va_entry.get("opacity", 0.7),
                "volume": va_entry.get("volume", 0.0),
            }
            # 비디오 첫 프레임을 썸네일용 이미지로 추출 (ffmpeg)
            if video_src and video_src.exists():
                import subprocess as _sp
                thumb_dir = out_dir / "video_sources" / "thumbs"
                thumb_dir.mkdir(parents=True, exist_ok=True)
                thumb_file = thumb_dir / f"scene_{num:03d}.jpg"
                start_sec = va_entry.get("startSec", 0.0)
                if not thumb_file.exists():
                    try:
                        _sp.run(
                            ["ffmpeg", "-y", "-ss", str(start_sec),
                             "-i", str(video_src),
                             "-frames:v", "1", "-q:v", "2",
                             str(thumb_file)],
                            capture_output=True, timeout=30,
                        )
                    except Exception:
                        pass
                if thumb_file.exists():
                    entry["videoThumbPath"] = link_asset(thumb_file, "video_sources/thumbs", thumb_file.name)

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
    _meta_design_preset = specs.get("meta", {}).get("designPreset", None)
    # art_style.json의 design_tokens를 기본값으로 로드하고,
    # 로컬 오버라이드 → meta.designPreset 순으로 딥머지
    _PRESET_KEYS = ("baseTheme", "defaultBackground", "defaultBgOpacity", "colors", "moods",
                    "layout", "map", "subtitle", "fonts", "typography",
                    "disableIcons", "disableSpotlight", "quoteReveal",
                    "defaultItemEntrance", "countUpThreshold", "texture", "variants")

    def _deep_merge(base: dict, override: dict) -> dict:
        result = dict(base)
        for k, v in override.items():
            if isinstance(v, dict) and isinstance(result.get(k), dict):
                result[k] = _deep_merge(result[k], v)
            else:
                result[k] = v
        return result

    # 1) 패키지 기본값 로드 (artstyle JSON)
    _pkg_dt = None
    if art_style:
        for _d in (out_dir / "artstyle" / "styles", workspace / "auto_agent" / "data" / "artstyle" / "styles"):
            _p = _d / f"{art_style}.json"
            if _p.exists():
                try:
                    _pkg_dt = json.loads(_p.read_text(encoding="utf-8")).get("design_tokens")
                except Exception:
                    pass
                break

    # 2) 로컬 오버라이드 로드
    _local_dt = None
    _proj_ast = out_dir / "art_style.json"
    if _proj_ast.exists():
        try:
            _local_dt = json.loads(_proj_ast.read_text(encoding="utf-8")).get("design_tokens")
        except Exception:
            pass

    # 3) 딥머지: 패키지 기본 → 로컬 오버라이드 → meta.designPreset
    _ast_dt = _deep_merge(_pkg_dt or {}, _local_dt or {}) or None
    if _meta_design_preset:
        _ast_dt = _deep_merge(_ast_dt or {}, _meta_design_preset)

    design_preset = None
    if _ast_dt:
        design_preset = {k: v for k, v in _ast_dt.items() if k in _PRESET_KEYS}

    # chartagent_style.json이 있으면 design_preset에 병합
    # (chartagent 스타일 명세서 → Remotion viz 컴포넌트에 자동 적용)
    _chartagent_style_path = out_dir / "charts" / "chartagent_style.json"
    if _chartagent_style_path.exists():
        try:
            _chartagent_style = json.loads(_chartagent_style_path.read_text(encoding="utf-8"))
            # 색상/테마는 artstyle이 소유 — chartagent 패턴/모티프 토큰만 주입
            _chartagent_section = _chartagent_style.get("chartagent") or {}
            if _chartagent_section:
                if design_preset is None:
                    design_preset = {}
                design_preset["chartagent"] = _chartagent_section
        except Exception:
            pass

    # fontagent: 폰트 선택 위임 — DesignPreset.fonts 흡수
    # (CreativeScene + 자막 + chartagent viz 컴포넌트 모두 이 폰트를 사용)
    try:
        from auto_agent.modules.fontagent_adapter import get_project_fonts
        _dominant_mood = specs.get("meta", {}).get("mood", "informative")
        if not _dominant_mood:
            # scene_specs에서 대표 mood 추출 (가장 많이 등장한 mood)
            from collections import Counter as _Counter
            _mood_counts = _Counter(
                s.get("mood") or "informative"
                for s in specs.get("scenes", [])
                if isinstance(s, dict)
            )
            _dominant_mood = _mood_counts.most_common(1)[0][0] if _mood_counts else "informative"
        _fontagent_fonts = get_project_fonts(mood=_dominant_mood)
        if _fontagent_fonts:
            design_preset = design_preset or {}
            # 기존 fonts를 fontagent가 선택한 폰트로 덮어씀 (단일 권한)
            design_preset["fonts"] = _fontagent_fonts
    except Exception:
        pass

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

    _subtitle_override = (design_preset or {}).get("subtitle", {})
    subtitle_config = {
        "visible": True,
        "fontFamily": _subtitle_override.get("fontFamily", font_family),
        "fontSize": _subtitle_override.get("fontSize", 44),
        "fontWeight": _subtitle_override.get("fontWeight", 700),
        "color": _subtitle_override.get("color", "#FFFFFF"),
        "strokeColor": _subtitle_override.get("strokeColor", "#3D3B2F"),
        "strokeWidth": _subtitle_override.get("strokeWidth", 2),
        "keywordColor": _subtitle_override.get("keywordColor", "#F7D94C"),
        "keywordStrokeColor": _subtitle_override.get("keywordStrokeColor", "#5A4B00"),
        "bottomOffset": _subtitle_override.get("bottomOffset", 30),
        "maxWidth": _subtitle_override.get("maxWidth", "85%"),
        "lineHeight": _subtitle_override.get("lineHeight", 1.5),
        **({ "backgroundColor": _subtitle_override["backgroundColor"] } if "backgroundColor" in _subtitle_override else {}),
        **({ "borderRadius": _subtitle_override["borderRadius"] } if "borderRadius" in _subtitle_override else {}),
        **({ "boxShadow": _subtitle_override["boxShadow"] } if "boxShadow" in _subtitle_override else {}),
        **({ "border": _subtitle_override["border"] } if "border" in _subtitle_override else {}),
        **({ "opacity": _subtitle_override["opacity"] } if "opacity" in _subtitle_override else {}),
        **({ "entryAnimation": _subtitle_override["entryAnimation"] } if "entryAnimation" in _subtitle_override else {}),
        **({ "textPaddingTop": _subtitle_override["textPaddingTop"] } if "textPaddingTop" in _subtitle_override else {}),
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

    # output 디렉토리의 manifest.json도 동기화 (씬에디터가 이 파일을 우선 읽음)
    output_manifest = out_dir / "remotion" / "public" / "manifest.json"
    if output_manifest.parent.exists():
        with open(output_manifest, "w", encoding="utf-8") as f:
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
        # 인자 없는 경우: PROJECT_NAME 환경변수로 대시보드 체인 지원
        _slug = os.environ.get("PROJECT_NAME", "").strip()
        if _slug:
            try:
                from auto_agent.db.project_manager import ProjectManager as _PM
                _pm = _PM()
                _proj = _pm.get_project(slug=_slug)
                if not _proj:
                    print(f"[build_manifest] 프로젝트 없음: {_slug}")
                    sys.exit(1)
                _out_dir = _proj.get("output_dir", "")
                if not _out_dir:
                    print(f"[build_manifest] output_dir 없음: {_slug}")
                    sys.exit(1)
                build_manifest(_slug, _slug, _out_dir)
            except Exception as e:
                print(f"[build_manifest] 오류: {e}")
                sys.exit(1)
        else:
            print("Usage: build_manifest.py <project_id> <storage_key> [project_dir]")
            print("       build_manifest.py --local <output_dir>")
            print("       PROJECT_NAME=<slug> build_manifest.py  (대시보드 체인용)")
            sys.exit(1)
