"""대시보드 데이터 파싱 헬퍼."""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional


def resolve_project_by_slug(slug: str) -> Optional[dict]:
    """slug → project dict. 대시보드 라우터 공통 헬퍼 (Supabase 대응)."""
    from auto_agent.db.project_manager import ProjectManager
    pm = ProjectManager()
    return pm.get_project(slug=slug)


def load_project_json(output_dir: str, filename: str) -> Optional[dict]:
    """프로젝트 output 디렉토리에서 JSON 파일 로드."""
    fp = Path(output_dir) / filename
    if fp.exists():
        return json.loads(fp.read_text(encoding="utf-8"))
    return None


def load_project_text(output_dir: str, filename: str) -> Optional[str]:
    """프로젝트 output 디렉토리에서 텍스트 파일 로드."""
    fp = Path(output_dir) / filename
    if fp.exists():
        return fp.read_text(encoding="utf-8")
    return None


def get_file_status(output_dir: str) -> dict:
    """output 디렉토리의 주요 파일 존재 여부/크기/수정일."""
    filenames = [
        "research_report.json", "outline.json", "final_manuscript.md",
        "scene_decomposition.json", "scene_specs.json", "motion_plan.json",
        "tts_results.json", "subtitles.json", "pipeline_state.json",
    ]
    result = {}
    for fname in filenames:
        fp = Path(output_dir) / fname
        if fp.exists():
            st = fp.stat()
            result[fname] = {
                "exists": True,
                "size": st.st_size,
                "size_kb": round(st.st_size / 1024, 1),
                "modified": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
            }
        else:
            result[fname] = {"exists": False, "size": 0, "size_kb": 0, "modified": None}
    return result


def _has_asset_entry(img_dir: Path, scene_num: int) -> bool:
    """image_assets.json에 이 씬 항목이 (이미지 목록과 함께) 있는가."""
    f = img_dir / "image_assets.json"
    if not f.exists():
        return False
    try:
        db = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return False
    return any(e.get("sceneNumber") == scene_num and e.get("images")
               for e in db.get("scenes", []))


def get_scene_image_url(project_dir_name: str, scene_num: int, output_dir: str) -> Optional[str]:
    """씬 이미지 URL 반환 (/output/ 마운트 기준). image_assets.json의 selected 우선."""
    img_dir = Path(output_dir) / "images"

    # 1) image_assets.json에서 selected 파일
    from auto_agent.tools.image_assets import get_selected
    selected = get_selected(img_dir, scene_num)
    if selected and (img_dir / selected).exists():
        return f"/output/{project_dir_name}/images/{selected}"

    # 등록은 돼 있는데 고른 것이 없으면 「일부러 비웠다」는 뜻이다.
    # 도표로 바꾼 씬이 그렇다 — 이미지가 없어야 맞다. 여기서 파일 탐색으로
    # 넘어가면 관련성 관문에서 버린 사진이 썸네일에 그대로 되살아난다.
    if _has_asset_entry(img_dir, scene_num):
        return None

    # 2) 파일 시스템 탐색 fallback
    for subdir in ("", "generated/", "search/"):
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            img = img_dir / f"{subdir}scene_{scene_num:03d}{ext}"
            if img.exists():
                return f"/output/{project_dir_name}/images/{subdir}scene_{scene_num:03d}{ext}"
    for sub in ("generated", "search"):
        sub_dir = img_dir / sub
        if sub_dir.exists():
            for f in sorted(sub_dir.glob(f"scene_{scene_num:03d}_*.*")):
                if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                    return f"/output/{project_dir_name}/images/{sub}/{f.name}"
    return None


def get_scene_audio_url(project_dir_name: str, scene_num: int, output_dir: str,
                        scene_id: str = "") -> Optional[str]:
    """씬 오디오 URL 반환. sceneId.mp3 우선, 없으면 scene_NNN.mp3 폴백.

    project_dir_name: output 디렉토리명 (uuid_{slug} 형식)
    """
    audio_dir = Path(output_dir) / "audio"
    if scene_id:
        p = audio_dir / f"{scene_id}.mp3"
        if p.exists():
            return f"/output/{project_dir_name}/audio/{scene_id}.mp3"
    p = audio_dir / f"scene_{scene_num:03d}.mp3"
    if p.exists():
        return f"/output/{project_dir_name}/audio/scene_{scene_num:03d}.mp3"
    return None


def parse_manuscript_chapters(text: str) -> list:
    """final_manuscript.md를 챕터별로 파싱."""
    chapters = []
    current_chapter = None
    current_scenes = []
    current_scene = None

    for line in text.split("\n"):
        ch_match = re.match(r'^#{1,2}\s*(?:Ch(?:apter)?)\s*(\d+)[:\.\s]+(.+)', line)
        if ch_match:
            if current_scene:
                current_scenes.append(current_scene)
            if current_chapter:
                current_chapter["scenes"] = current_scenes
                chapters.append(current_chapter)
            current_chapter = {
                "number": int(ch_match.group(1)),
                "title": ch_match.group(2).strip(),
                "scenes": [],
            }
            current_scenes = []
            current_scene = None
            continue

        scene_match = re.match(r'^#{2,3}\s*Scene\s*(\d+)[:\.\s]+(.+)', line)
        if scene_match:
            if current_scene:
                current_scenes.append(current_scene)
            current_scene = {
                "number": int(scene_match.group(1)),
                "title": scene_match.group(2).strip(),
                "viz_marker": None,
                "lines": [],
            }
            continue

        if current_chapter and current_scene is None:
            # Scene 마커 없이 챕터 바로 본문이 오는 경우
            if line.strip() and not line.startswith('#'):
                if not current_scenes and current_scene is None:
                    current_scene = {
                        "number": 0,
                        "title": current_chapter["title"],
                        "viz_marker": None,
                        "lines": [],
                    }
                if current_scene is not None:
                    current_scene["lines"].append(line)
            continue

        if current_scene is not None:
            viz_match = re.match(r'^\[VIZ:(.+)\]$', line)
            if viz_match:
                current_scene["viz_marker"] = viz_match.group(1)
            elif line.strip():
                current_scene["lines"].append(line)

    if current_scene:
        current_scenes.append(current_scene)
    if current_chapter:
        current_chapter["scenes"] = current_scenes
        chapters.append(current_chapter)

    return chapters


def _check_step_outputs_exist(step: dict, output_dir: str) -> bool:
    """스텝의 output 파일/디렉토리 중 주요 산출물이 존재하는지 확인.

    output 배열에서 확인 가능한 파일/디렉토리 중
    하나라도 존재하면 completed로 판단한다.
    (외부 경로, 템플릿 변수 등 확인 불가한 항목은 건너뜀)
    """
    if not output_dir:
        return False
    outputs = step.get("output")
    if not outputs:
        return False
    if isinstance(outputs, str):
        outputs = [outputs]
    out_path = Path(output_dir)
    found = 0
    for o in outputs:
        # output/{project}/audio/ → audio/ 로 변환
        cleaned = o
        if "output/{project}/" in cleaned:
            cleaned = cleaned.split("output/{project}/", 1)[1]
        # 글로브/템플릿 패턴 ({N}, {NNN}, {topic} 등) → 부모 디렉토리만 확인
        if "{" in cleaned:
            parent = cleaned.split("{")[0].rstrip("/")
            if parent:
                p = out_path / parent
                if p.is_dir() and any(p.iterdir()):
                    found += 1
            continue
        p = out_path / cleaned
        if cleaned.endswith("/") or cleaned.endswith("\\"):
            if p.is_dir() and any(p.iterdir()):
                found += 1
        else:
            if p.exists():
                found += 1
    return found > 0


def get_pipeline_progress(output_dir: str, data_dir: str,
                          db_runs: list = None) -> dict:
    """pipeline.json + DB 실행 이력 + 산출물 존재 여부를 조합하여 진행률 계산.

    우선순위:
    1. DB 이력에 상태가 있으면 사용
    2. DB에 없지만 산출물 파일이 존재하면 completed로 추론
    3. 둘 다 없으면 pending
    """
    pipeline_path = Path(data_dir) / "pipeline.json"
    if not pipeline_path.exists():
        return {"phases": []}

    pipeline_def = json.loads(pipeline_path.read_text(encoding="utf-8"))

    # DB 이력에서 각 스텝의 최신 상태를 추출
    step_status_map: dict[str, str] = {}
    if db_runs:
        for run in reversed(db_runs):  # 오래된 것부터 → 최신이 덮어씀
            step_key = run.get("step", "")
            status = run.get("status", "")
            if step_key and status:
                step_status_map[step_key] = status

    status_sets: dict[str, set] = {
        "completed": set(), "failed": set(), "skipped": set(), "running": set(),
    }
    for k, v in step_status_map.items():
        if v in status_sets:
            status_sets[v].add(k)
    completed_steps = status_sets["completed"]
    failed_steps = status_sets["failed"]
    skipped_steps = status_sets["skipped"]
    running_steps = status_sets["running"]

    phases = []
    for phase in pipeline_def.get("phases", []):
        steps = []
        for step in phase.get("steps", []):
            step_id = step["id"]
            if step_id in completed_steps:
                s_status = "completed"
            elif step_id in failed_steps:
                s_status = "failed"
            elif step_id in skipped_steps:
                s_status = "skipped"
            elif step_id in running_steps:
                s_status = "running"
            elif step_id not in step_status_map and _check_step_outputs_exist(step, output_dir):
                # DB 레코드 없지만 산출물 존재 → completed 추론
                s_status = "completed"
            else:
                s_status = "pending"
            steps.append({**step, "status": s_status})

        if all(s["status"] == "completed" for s in steps):
            phase_status = "completed"
        elif any(s["status"] == "running" for s in steps):
            phase_status = "running"
        elif any(s["status"] == "failed" for s in steps):
            phase_status = "failed"
        elif any(s["status"] == "completed" for s in steps):
            phase_status = "partial"
        else:
            phase_status = "pending"

        phases.append({
            "id": phase["id"],
            "name": phase["name"],
            "status": phase_status,
            "steps": steps,
        })

    return {"phases": phases}


def infer_grid_type(image_count: int) -> str:
    """이미지 수를 기반으로 grid_type을 자동 추론한다."""
    mapping = {2: "2x1", 3: "3x1", 4: "2x2", 6: "3x2"}
    return mapping.get(image_count, "auto")


def resolve_layout(scene: dict) -> tuple[str, bool]:
    """씬의 레이아웃을 결정. Remotion CreativeScene.resolveLayout과 동일 로직.

    Returns:
        (layout_name, is_explicit) — is_explicit이 True면 AI 지정, False면 자동 추론.
    """
    # hero_with_context는 items_grid의 alias (레거시 데이터 호환)
    if scene.get("layout") == "hero_with_context":
        scene = {**scene, "layout": "items_grid"}
    viz = scene.get("visualization") or {}
    creative_check = viz.get("creative") or {}
    if creative_check.get("layout") == "hero_with_context":
        creative_check = {**creative_check, "layout": "items_grid"}
        viz = {**viz, "creative": creative_check}
        scene = {**scene, "visualization": viz}

    # 맵씬이면 무조건 map
    map_scene = scene.get("mapScene") or {}
    if map_scene and map_scene.get("markers"):
        return "map", True

    viz = scene.get("visualization") or {}
    creative = viz.get("creative") or {}

    VALID_LAYOUTS = {
        "headline_only", "items_grid", "items_list", "person_card", "counter",
        "quote", "split", "bar", "logo_grid", "pie", "line",
        "flow", "timeline", "metric_spotlight", "metric_wall", "rank_list",
        "comparison_table", "before_after", "icon_stat", "stacked_progress",
        "card_carousel", "hero_with_context", "quote_portrait", "annotated_chart",
        "cinematic", "bar_horizontal", "donut", "images_grid",
    }

    # 0순위: 명시적 layout (build_manifest가 항상 최상위에 기록)
    # fallback 순서: scene.layout → sceneType → viz.layout → creative.layout
    _explicit = (scene.get("layout") or scene.get("sceneType")
                 or viz.get("layout") or creative.get("layout") or "")
    if _explicit and _explicit in VALID_LAYOUTS:
        return _explicit, True

    # 2순위: displayMode / chartConfig
    if creative.get("displayMode") == "logo_grid":
        return "logo_grid", False
    chart_type = (scene.get("chartConfig") or creative.get("chartConfig") or {}).get("type", "")
    if creative.get("displayMode") == "pie_chart" or chart_type == "pie":
        return "pie", False
    if creative.get("displayMode") == "line_chart" or chart_type == "line":
        return "line", False
    if chart_type == "bar":
        return "bar", False

    # 3순위: 데이터 구조 기반 추론
    reveal = creative.get("reveal", "fade_in")
    emphasis = creative.get("emphasis", "none")
    # items/values/headline은 최상위 또는 viz 내부
    items = scene.get("items") or viz.get("items") or []
    values = scene.get("values") or viz.get("values") or []
    headline = scene.get("headline") or creative.get("headline", "")

    if emphasis == "quote" or (len(items) == 1 and re.search(r'["""\']', items[0])):
        return "quote_portrait", False
    if reveal == "split_reveal":
        return "split", False
    if emphasis == "contrast" and len(items) == 2:
        return "split", False
    if emphasis == "person" and len(items) >= 2:
        return "person_card", False
    if emphasis in ("number", "count"):
        m = re.search(r'\{\{([^}]+)\}\}', headline)
        if m:
            nums = re.findall(r'[\d,.]+', m.group(1))
            if nums:
                try:
                    val = float(nums[0].replace(",", ""))
                    if val > 0:
                        return "counter", False
                except ValueError:
                    pass
    if emphasis == "sequence" and len(items) >= 2:
        return "items_list", False
    if (len(items) >= 3 and len(values) >= 3
            and len(items) == len(values)
            and emphasis not in ("keyword", "sequence")):
        return "bar", False
    if len(items) >= 3:
        hl = headline.lower()
        items_are_data = any(len(it) > 1 and it.lower() not in hl for it in items)
        if items_are_data:
            return ("items_grid" if len(items) >= 6 else "items_list"), False
    if len(items) == 2 and len(values) >= 2:
        return "items_list", False

    return "headline_only", False


def enrich_scenes_with_media(scenes: list, project_dir_name: str, output_dir: str,
                              tts_results: Optional[dict] = None,
                              project_accent: Optional[str] = None,
                              art_style: Optional[str] = None) -> list:
    """씬 목록에 이미지/오디오 URL + TTS 정보 + 레이아웃을 추가.

    project_dir_name: output 디렉토리명 (uuid_{slug} 형식) — URL 구성에 사용.
    """
    tts_map = {}
    if tts_results:
        for r in tts_results.get("results", []):
            tts_map[r["scene"]] = r

    # 썸네일 디렉토리 확인
    thumb_dir = Path(output_dir) / "thumbnails" if output_dir else None
    has_thumbs = thumb_dir and thumb_dir.exists()

    # manifest의 최종 layout을 우선 사용해 스토리보드 배지와 실제 렌더를 정렬
    manifest_layout_map = {}
    if output_dir:
        try:
            from auto_agent.paths import get_workspace_dir
            manifest_path = get_workspace_dir() / "remotion" / "public" / "manifests" / f"{project_dir_name}.json"
            if manifest_path.exists():
                manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest = manifest_data.get("manifest", manifest_data)
                for manifest_scene in manifest.get("scenes", []):
                    sn = manifest_scene.get("sceneNumber")
                    layout = manifest_scene.get("layout") or manifest_scene.get("sceneType")
                    if sn is not None and layout:
                        manifest_layout_map[sn] = layout
        except Exception:
            pass

    # video_assets.json → {sceneNumber: videoFile} 룩업
    video_asset_map: dict = {}
    if output_dir:
        va_path = Path(output_dir) / "video_assets.json"
        if va_path.exists():
            try:
                va_data = json.loads(va_path.read_text(encoding="utf-8"))
                for va in va_data.get("scenes", []):
                    sn_va = va.get("sceneNumber")
                    if sn_va is not None:
                        video_asset_map[sn_va] = va
            except Exception:
                pass

    # 캐릭터 폴더에서 캐릭터별 이미지 매핑 ({char_id: url})
    char_thumb_map = {}
    if output_dir:
        char_dir = Path(output_dir) / "characters"
        if char_dir.exists():
            # 파일명 룩업: 공백→언더스코어 변환 후 prefix 매칭
            char_files = list(char_dir.iterdir())
            import unicodedata as _ud
            # HFS+ NFD → NFC 정규화 후 매핑
            char_files_by_stem = {_ud.normalize("NFC", f.stem): f for f in char_files if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")}
            project_dir_name_local = Path(output_dir).name
            for char_id in {c for s in scenes for c in s.get("characters", [])}:
                char_key = _ud.normalize("NFC", char_id.replace(" ", "_"))
                # 1순위: char_key로 시작하는 semoji_3D 파일
                match = next((f for stem, f in char_files_by_stem.items() if stem.startswith(char_key) and "semoji_3D" in stem), None)
                # 2순위: char_key 단순 파일
                if not match:
                    match = char_files_by_stem.get(char_key)
                if match:
                    char_thumb_map[char_id] = f"/output/{project_dir_name_local}/characters/{match.name}"

    for scene in scenes:
        sn = scene["sceneNumber"]
        # 비디오 에셋 정보 주입
        va_entry = video_asset_map.get(sn)
        scene["_video_file"] = va_entry.get("staticPath", va_entry.get("videoFile", "")) if va_entry else ""
        scene["_video_start_sec"] = va_entry.get("startSec", 0.0) if va_entry else None
        scene["_video_end_sec"] = va_entry.get("endSec") if va_entry else None
        # video_assets.json에 항목이 있으면 videoAsset 동기화 (scene_specs에 누락된 경우 대비)
        if va_entry and scene["_video_file"] and not scene.get("videoAsset"):
            scene["videoAsset"] = {
                "staticPath": scene["_video_file"],
                "startSec": scene["_video_start_sec"],
                "endSec": scene["_video_end_sec"],
            }
        # 비디오 썸네일: {basename}_thumb.jpg 규칙 (/background/ 라우트 사용)
        if scene["_video_file"]:
            import re as _re
            vf = scene["_video_file"]
            stem = _re.sub(r'\.[^.]+$', '', vf.split('/')[-1])
            folder = vf.rsplit('/', 1)[0] if '/' in vf else ''
            thumb_rel = (folder + '/' if folder else '') + stem + '_thumb.jpg'
            scene["_video_thumb_url"] = f"/{thumb_rel}"
        else:
            scene["_video_thumb_url"] = ""

        scene["_image_url"] = get_scene_image_url(project_dir_name, sn, output_dir)
        scene["_audio_url"] = get_scene_audio_url(project_dir_name, sn, output_dir,
                                                    scene_id=scene.get("sceneId", ""))
        tts = tts_map.get(sn, {})
        scene["_tts_duration"] = tts.get("duration")
        scene["_tts_status"] = tts.get("status")
        # mapScene(markers 있음)이면 manifest layout보다 우선
        _map_scene = scene.get("mapScene") or {}
        if _map_scene and _map_scene.get("markers"):
            layout, explicit = "map", True
        else:
            manifest_layout = manifest_layout_map.get(sn)
            if manifest_layout:
                layout, explicit = manifest_layout, True
            else:
                layout, explicit = resolve_layout(scene)
        scene["_layout"] = layout
        scene["_layout_explicit"] = explicit
        scene["_preview_html"] = render_scene_preview(scene, project_accent=project_accent, art_style=art_style or "")

        # Remotion 캡처 썸네일 (있으면 우선 사용)
        scene["_thumbnail_url"] = None
        if has_thumbs:
            thumb_path = thumb_dir / f"scene_{str(sn).zfill(3)}.png"
            if thumb_path.exists():
                slug_part = project_dir_name.split("_", 1)[-1] if "_" in project_dir_name else project_dir_name
                scene["_thumbnail_url"] = f"/api/p/{slug_part}/thumbnails/scene/{sn}"

        # QA 결과 병합
        from auto_agent.tools.image_assets import get_qa_result
        sn_key = scene.get("sceneNumber") or scene.get("scene_number") or (scenes.index(scene) + 1)
        qa_result = get_qa_result(Path(output_dir) / "images", sn_key)
        if qa_result:
            scene["qa"] = qa_result

    # 분리해 둔 레이어가 있으면 씬에 표시한다.
    #
    # 그동안은 레이어 칸을 펼쳐야만 알 수 있었다 — 목록에서는 나눈 씬과
    # 안 나눈 씬이 똑같아 보였다.
    from auto_agent.paths import layer_sets

    slug = project_dir_name.split("_", 1)[-1] if "_" in project_dir_name else project_dir_name
    layer_count: dict = {}
    for scene in scenes:
        sn = scene.get("sceneNumber")
        if sn is None:
            continue
        for d in layer_sets(slug, sn):
            try:
                meta = json.loads((d / "layers.json").read_text(encoding="utf-8"))
            except Exception:
                continue
            layer_count[sn] = max(layer_count.get(sn, 0), len(meta))

    # 캐릭터 썸네일을 각 씬에 주입 (2차 패스)
    roster = load_roster()
    for scene in scenes:
        scene["_char_thumbs"] = {}
        for char_id in scene.get("characters", []):
            if char_id in char_thumb_map:
                scene["_char_thumbs"][char_id] = char_thumb_map[char_id]
        # cast(로스터 id)를 시트에 잇는다 — 씬 이미지를 실제로 만든 근거가 이쪽이다
        cast = []
        for cid in scene.get("cast") or []:
            info = roster.get(cid)
            if info:
                cast.append({"id": cid, "label": info["label"], "thumb": info["thumb"]})
            else:
                cast.append({"id": cid, "label": cid, "thumb": ""})
        scene["_cast"] = cast
        scene["_layer_count"] = layer_count.get(scene.get("sceneNumber"), 0)

    return scenes


_ROSTER_CACHE: Optional[dict] = None


def load_roster() -> dict:
    """로스터 id → 표시 이름·시트 URL.

    씬의 `cast`가 담는 것은 `koo_inhoe_40s` 같은 로스터 id다. 그 자체로는
    누구인지 읽히지 않고 시트 경로도 알 수 없어, 스토리보드에서 인물이
    비어 보였다. 로스터가 이름과 나이를 갖고 있으므로 여기서 이어 준다.
    """
    global _ROSTER_CACHE
    if _ROSTER_CACHE is not None:
        return _ROSTER_CACHE
    out: dict = {}
    try:
        from auto_agent.paths import get_charsheet_dir

        sheets = get_charsheet_dir()
        if sheets is None:
            return out
        raw = json.loads((sheets.parent / "roster.json").read_text(encoding="utf-8"))
        entries = raw if isinstance(raw, list) else raw.get("characters", [])
        for e in entries:
            cid = e.get("id")
            if not cid:
                continue
            age = e.get("age") or ""
            label = f"{e.get('name', cid)}{f' ({age})' if age else ''}"
            thumb = f"/charsheets/{cid}_sheet.png" if (sheets / f"{cid}_sheet.png").exists() else ""
            out[cid] = {"label": label, "thumb": thumb}
    except Exception:
        pass
    _ROSTER_CACHE = out
    return out


def format_headline(headline: str) -> str:
    """{{텍스트}} → <span class="accent-text">텍스트</span> 변환."""
    if not headline:
        return ""
    return re.sub(r'\{\{(.+?)\}\}', r'<span class="accent-text">\1</span>', headline)


# ─── 씬 프리뷰 렌더러 ───

# 기본 mood 색상 (artstyle design_tokens가 없을 때 fallback)
_DEFAULT_MOOD_COLORS = {
    "dramatic": ("#F59E0B", "#1a1005"),
    "urgent": ("#EF4444", "#1a0808"),
    "somber": ("#71717A", "#0d0d0e"),
    "informative": ("#3B82F6", "#080d1a"),
    "contemplative": ("#3B82F6", "#080d1a"),
    "suspense": ("#F59E0B", "#14100a"),
    "triumphant": ("#10B981", "#081a10"),
}

def _load_design_tokens(art_style: str) -> dict:
    """artstyle JSON에서 design_tokens 로드. 캐시됨."""
    if not hasattr(_load_design_tokens, "_cache"):
        _load_design_tokens._cache = {}
    if art_style in _load_design_tokens._cache:
        return _load_design_tokens._cache[art_style]
    try:
        from auto_agent.paths import get_workspace_dir
        style_path = get_workspace_dir() / "auto_agent" / "data" / "artstyle" / "styles" / f"{art_style}.json"
        if style_path.exists():
            import json as _json
            data = _json.loads(style_path.read_text(encoding="utf-8"))
            tokens = data.get("design_tokens", {})
            _load_design_tokens._cache[art_style] = tokens
            return tokens
    except Exception:
        pass
    _load_design_tokens._cache[art_style] = {}
    return {}

def get_mood_color(mood: str, art_style: str = "", project_accent: str = None) -> tuple:
    """mood + artstyle design_tokens에서 accent/bg 색상 반환."""
    tokens = _load_design_tokens(art_style) if art_style else {}
    moods = tokens.get("moods", {})
    mood_entry = moods.get(mood, {})
    default_accent, default_bg = _DEFAULT_MOOD_COLORS.get(mood, ("#3B82F6", "#080d1a"))
    accent = mood_entry.get("accent", default_accent)
    # project_accent가 있으면 urgent/somber 외에는 대체 (Remotion resolvePreset과 동일)
    if project_accent and mood not in ("urgent", "somber"):
        accent = project_accent
    return accent, default_bg


def _esc(text: str) -> str:
    """HTML 이스케이프 (프리뷰용)."""
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _format_headline_preview(headline: str, accent: str) -> str:
    """{{텍스트}} → accent 색상 span. 줄바꿈 처리."""
    if not headline:
        return ""
    h = _esc(headline)
    h = re.sub(
        r'\{\{(.+?)\}\}',
        rf'<span style="color:{accent};font-weight:700">\1</span>',
        h,
    )
    return h.replace("\\n", "<br>").replace("\n", "<br>")


# ISO 3166-1 alpha-2 → 국기 이모지
def _flag_emoji(code: str) -> str:
    if not code or len(code) != 2:
        return ""
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in code.upper())


def render_scene_preview(scene: dict, project_accent: str = None, art_style: str = "") -> str:
    """씬 데이터로 HTML 미니 프리뷰 생성. 16:9 비율, Remotion CreativeScene과 동일 구조."""
    viz = scene.get("visualization") or {}
    creative = viz.get("creative") or {}
    layout = scene.get("_layout", "headline_only")
    mood = scene.get("mood") or creative.get("mood", "informative")
    accent, bg_tint = get_mood_color(mood, art_style=art_style, project_accent=project_accent)
    headline = scene.get("headline") or creative.get("headline", "")
    emphasis = creative.get("emphasis", "")
    items = scene.get("items") or viz.get("items") or []
    values = scene.get("values") or viz.get("values") or []
    unit = scene.get("unit") or viz.get("unit", "")
    source = scene.get("source") or viz.get("source", "")
    descriptions = scene.get("descriptions") or viz.get("descriptions") or creative.get("descriptions") or []
    item_icons = scene.get("icons") or viz.get("itemIcons") or []
    item_flags = scene.get("flags") or viz.get("itemFlags") or []
    item_statuses = viz.get("itemStatuses") or []
    item_images = viz.get("images") or creative.get("images") or []
    logo_map = creative.get("logoMap") or {}
    chart_config = scene.get("chartConfig") or creative.get("chartConfig") or {}
    image_url = scene.get("_image_url", "")
    img_asset = scene.get("imageAsset") or {}
    placement = img_asset.get("placement", "background")
    # Remotion과 동일: background=0.35, 나머지(fullscreen/center/side)=0.9
    _default_opacity = 0.35 if placement == "background" else 0.9
    img_opacity = img_asset.get("opacity", _default_opacity)
    # fullscreen은 Remotion과 동일하게 최소 0.9 보장
    if placement == "fullscreen" and img_opacity < 0.8:
        img_opacity = 0.9

    # ── 컨테이너 시작 (16:9) ──
    bg_style = f"background:radial-gradient(ellipse 80% 60% at 50% 40%,{bg_tint},#0A0A0A)"
    is_side = placement in ("left", "right") and image_url
    if is_side:
        html = f'<div class="scene-preview sp-layout-side" style="{bg_style}">'
        side = "left" if placement == "left" else "right"
        html += f'<img src="{_esc(image_url)}" class="sp-side-img sp-side-{side}" style="opacity:{img_opacity}">'
        html += '<div class="sp-content sp-content-side">'
    else:
        html = f'<div class="scene-preview" style="{bg_style}">'
        if image_url:
            if placement == "fullscreen":
                html += f'<img src="{_esc(image_url)}" class="sp-bg-img" style="opacity:{img_opacity}">'
            elif placement == "center":
                html += f'<img src="{_esc(image_url)}" class="sp-center-img" style="opacity:{img_opacity}">'
            else:  # background
                html += f'<img src="{_esc(image_url)}" class="sp-bg-img" style="opacity:{img_opacity}">'
        html += '<div class="sp-content">'

    # ── headline 렌더링 (Remotion EmphasisAccentText 방식) ──
    # {{텍스트}}는 accent 컬러 + 큰 폰트, 나머지는 base 폰트
    def _render_headline(headline_text: str, size: str = "normal") -> str:
        """Remotion의 EmphasisAccentText 방식: accent 부분 크게, base 부분 작게.
        size: 'normal'(기본), 'sm'(items 위 작은 헤드라인)"""
        if not headline_text:
            return ""
        cls = "sp-headline" if size == "normal" else "sp-headline sp-sm"
        # accent 크기 / base 크기 비율 — Remotion: accent 108~132, base 60~72
        parts = re.split(r'(\{\{.+?\}\})', headline_text)
        has_accent = any(p.startswith("{{") for p in parts)
        inner = ""
        for p in parts:
            if p.startswith("{{") and p.endswith("}}"):
                txt = _esc(p[2:-2]).replace("\\n", "<br>").replace("\n", "<br>")
                inner += f'<span class="sp-accent" style="color:{accent}">{txt}</span>'
            else:
                txt = _esc(p).replace("\\n", "<br>").replace("\n", "<br>")
                inner += txt
        # Remotion: accent가 있고 emphasis가 number/count면 accent를 극적으로 크게
        if has_accent and size == "normal" and emphasis in ("number", "count"):
            cls += " sp-hl-counter"
        return f'<div class="{cls}">{inner}</div>'

    def _esc_br(text: str) -> str:
        """HTML 이스케이프 후 줄바꿈을 br로."""
        return _esc(text).replace("\\n", "<br>").replace("\n", "<br>")

    # headline과 items 중복 체크
    hl_plain = re.sub(r'\{\{|\}\}', '', headline).replace("\\n", " ").replace("\n", " ").strip()
    items_in_headline = (
        items and hl_plain and
        sum(1 for it in items if it in hl_plain) >= len(items) * 0.5
    )
    show_hl = headline and not items_in_headline

    # 아이템별 뱃지(아이콘/국기/로고)
    def _badge(i: int) -> str:
        parts = []
        if i < len(item_flags) and item_flags[i]:
            parts.append(f'<span class="sp-flag">{_flag_emoji(item_flags[i])}</span>')
        if i < len(item_icons) and item_icons[i]:
            parts.append(f'<span class="sp-icon" style="color:{accent}" title="{_esc(item_icons[i])}">'
                         f'{_esc(item_icons[i][:3])}</span>')
        item_name = items[i] if i < len(items) else ""
        if item_name in logo_map:
            parts.append(f'<span class="sp-logo">{_esc(logo_map[item_name][:4])}</span>')
        return "".join(parts)

    # 아이템 이미지 헬퍼
    def _item_img(i: int) -> str:
        if i < len(item_images) and item_images[i]:
            return f'<img src="{_esc(item_images[i])}" class="sp-item-img">'
        return ""

    # source 렌더링 (Remotion: 하단 출처)
    def _source() -> str:
        return f'<div class="sp-source">{_esc(source)}</div>' if source else ""

    # description 헬퍼
    def _desc(i: int) -> str:
        if i < len(descriptions) and descriptions[i]:
            return f'<div class="sp-desc">{_esc_br(descriptions[i])}</div>'
        return ""

    # ── 맵씬 ──
    map_scene = scene.get("mapScene") or {}

    if map_scene and map_scene.get("markers"):
        if show_hl:
            html += _render_headline(headline, "sm")
        markers = map_scene["markers"]
        map_type = map_scene.get("mapType", "location_reveal")
        # 마커 위치를 캔버스 안에 분산 배치 (%)
        _dot_positions = [
            (28, 38), (62, 28), (52, 58), (24, 62), (72, 48),
            (42, 74), (76, 22), (58, 78), (35, 52), (68, 68),
        ]
        html += '<div class="sp-map">'
        html += f'<div class="sp-map-canvas">'
        html += '<div class="sp-map-bg"></div>'
        for i, mk in enumerate(markers[:8]):
            label = mk.get("label", "")
            px, py = _dot_positions[i % len(_dot_positions)]
            html += (
                f'<div class="sp-map-dot" style="left:{px}%;top:{py}%;'
                f'background:{accent};box-shadow:0 0 6px {accent}88">'
                f'<span class="sp-map-dot-label">{_esc(label)}</span>'
                f'</div>'
            )
        html += '</div>'
        html += f'<div class="sp-map-type" style="color:{accent}">{_esc(map_type)}</div>'
        html += '</div>'

    # ── headline_only: Remotion — headline만, items 숨김 (itemCount=0) ──
    elif layout == "headline_only":
        html += _render_headline(headline)

    # ── counter: Remotion — {{숫자}} 각각 크게, emphasis=count/number ──
    elif layout == "counter":
        # 여러 {{}} 지원 (Remotion multi-counter: 최대 4개)
        matches = re.findall(r'\{\{([^}]+)\}\}', headline)
        rest = re.sub(r'\{\{[^}]+\}\}', '', headline).strip().replace("\\n", " ").replace("\n", " ")
        if len(matches) > 1:
            html += '<div class="sp-multi-counter">'
            for m_text in matches[:4]:
                html += f'<div class="sp-counter" style="color:{accent}">{_esc(m_text)}</div>'
            html += '</div>'
        elif matches:
            html += f'<div class="sp-counter" style="color:{accent}">{_esc(matches[0])}</div>'
        if rest:
            html += f'<div class="sp-sub">{_esc(rest)}</div>'

    # ── quote_portrait (레거시 quote 포함): QuoteMark + 인용문 + source ──
    elif layout in ("quote", "quote_portrait"):
        quote_text = items[0] if items else headline
        html += f'<div class="sp-quote-mark" style="color:{accent}">"</div>'
        html += f'<div class="sp-quote" style="border-color:{accent}">{_esc_br(quote_text)}</div>'
        if source:
            html += f'<div class="sp-quote-source">— {_esc(source)}</div>'

    # ── items_list: Remotion — 카드형(이미지 있으면), spotlight 마지막 항목 ──
    elif layout == "items_list":
        if show_hl:
            html += _render_headline(headline, "sm")
        html += '<div class="sp-list">'
        for i, item in enumerate(items[:8]):
            badge = _badge(i)
            img = _item_img(i)
            val = f'<span class="sp-val" style="color:{accent}">{values[i]}{unit}</span>' if i < len(values) else ""
            # Remotion: 마지막 항목 spotlight 강조
            is_last = (i == len(items[:8]) - 1) and len(items) > 1
            spot = f' style="color:{accent};font-weight:700"' if is_last else ""
            desc = _desc(i)
            html += f'<div class="sp-item{" sp-spotlight" if is_last else ""}">{img}{badge}<span{spot}>{_esc(item)}</span> {val}{desc}</div>'
        if len(items) > 8:
            html += f'<div class="sp-item sp-more">+{len(items)-8}</div>'
        html += '</div>'

    # ── items_grid: Remotion — 2~3열 그리드 ──
    elif layout == "items_grid":
        if show_hl:
            html += _render_headline(headline, "sm")
        cols = 3 if len(items) >= 6 else 2
        html += f'<div class="sp-grid" style="grid-template-columns:repeat({cols},1fr)">'
        for i, item in enumerate(items[:9]):
            badge = _badge(i)
            img = _item_img(i)
            val = f'<div class="sp-val" style="color:{accent}">{values[i]}{unit}</div>' if i < len(values) else ""
            desc = _desc(i)
            html += f'<div class="sp-grid-cell">{img}{badge}<div>{_esc(item)}</div>{val}{desc}</div>'
        if len(items) > 9:
            html += f'<div class="sp-grid-cell sp-more">+{len(items)-9}</div>'
        html += '</div>'

    # ── images_grid: Remotion — 이미지 분할 그리드 ──
    elif layout == "images_grid":
        images = scene.get("images") or creative.get("images") or []
        if not images:
            logger.warning(f"images_grid 레이아웃인데 images 필드가 없습니다: scene_id={scene.get('id', '?')}")
        grid_type = scene.get("grid_type") or creative.get("grid_type")
        if not grid_type:
            grid_type = infer_grid_type(len(images))
        if show_hl:
            html += _render_headline(headline, "sm")
        cols = 2 if len(images) <= 4 else 3
        html += f'<div class="sp-grid" style="grid-template-columns:repeat({cols},1fr)">'
        for img_url in images[:6]:
            if img_url:
                html += f'<div class="sp-grid-cell"><img src="{_esc(img_url)}" style="width:100%;height:100%;object-fit:cover"></div>'
            else:
                html += '<div class="sp-grid-cell" style="background:#333"></div>'
        html += '</div>'
        html += f'<div class="sp-source" style="color:{accent}">{_esc(grid_type)}</div>'

    # ── bar: Remotion — 수평 바 차트 ──
    elif layout == "bar":
        if show_hl:
            html += _render_headline(headline, "sm")
        max_val = max(values) if values else 1
        html += '<div class="sp-bars">'
        for i, item in enumerate(items[:6]):
            badge = _badge(i)
            v = values[i] if i < len(values) else 0
            pct = int((v / max_val) * 100) if max_val else 0
            # Remotion: 첫 번째 항목 accent, 나머지 accent88
            bar_color = accent if i == 0 else f"{accent}88"
            html += (
                f'<div class="sp-bar-row">'
                f'<span class="sp-bar-label">{badge}{_esc(item)}</span>'
                f'<div class="sp-bar-track"><div class="sp-bar-fill" style="width:{pct}%;background:{bar_color}"></div></div>'
                f'<span class="sp-bar-val">{v}{unit}</span>'
                f'</div>'
            )
        html += '</div>'

    # ── split: Remotion — 좌우 비교, VS 표시, 이미지 지원 ──
    elif layout == "split":
        if show_hl:
            html += _render_headline(headline, "sm")
        has_vs = "vs" in headline.lower()
        html += '<div class="sp-split">'
        for i, item in enumerate(items[:2]):
            badge = _badge(i)
            img = _item_img(i)
            val = f'<div class="sp-val" style="color:{accent}">{values[i]}{unit}</div>' if i < len(values) else ""
            status = item_statuses[i] if i < len(item_statuses) else ""
            status_cls = " sp-positive" if status == "positive" else (" sp-negative" if status == "negative" else "")
            desc = _desc(i)
            html += f'<div class="sp-split-half{status_cls}">{img}{badge}{val}<div>{_esc(item)}</div>{desc}</div>'
            # VS 구분자
            if i == 0 and has_vs:
                html += f'<div class="sp-vs" style="color:{accent}">VS</div>'
        html += '</div>'

    # ── person_card: Remotion — 인물 이미지 + 이름 + status ──
    elif layout == "person_card":
        if show_hl:
            html += _render_headline(headline, "sm")
        html += '<div class="sp-persons">'
        for i, item in enumerate(items[:4]):
            badge = _badge(i)
            img = _item_img(i)
            status = item_statuses[i] if i < len(item_statuses) else ""
            status_cls = " sp-negative" if status == "negative" else ""
            desc = _desc(i)
            if img:
                html += (f'<div class="sp-person{status_cls}">'
                         f'{img}{badge}<div class="sp-pname">{_esc(item)}</div>{desc}</div>')
            else:
                html += (f'<div class="sp-person{status_cls}">'
                         f'<div class="sp-avatar" style="border-color:{accent}">{_esc(item[:1])}</div>'
                         f'{badge}<div class="sp-pname">{_esc(item)}</div>{desc}</div>')
        html += '</div>'

    # ── pie / line: Remotion — 차트 ──
    elif layout in ("pie", "line"):
        if headline:
            html += _render_headline(headline, "sm")
        chart_type = chart_config.get("type", layout)
        if chart_type == "pie" and items and values:
            total = sum(values) or 1
            segments = []
            pie_colors = [accent, "#6366F1", "#10B981", "#F59E0B", "#EF4444", "#71717A"]
            deg = 0
            for i, v in enumerate(values[:6]):
                c = pie_colors[i % len(pie_colors)]
                end = deg + (v / total) * 360
                segments.append(f"{c} {deg:.0f}deg {end:.0f}deg")
                deg = end
            grad = ", ".join(segments)
            html += f'<div class="sp-pie" style="background:conic-gradient({grad})"></div>'
            html += '<div class="sp-pie-legend">'
            for i, item in enumerate(items[:6]):
                c = pie_colors[i % len(pie_colors)]
                pct = int((values[i] / total) * 100) if i < len(values) else 0
                html += f'<span class="sp-pie-label"><span class="sp-pie-dot" style="background:{c}"></span>{_esc(item)} {pct}%</span>'
            html += '</div>'
        else:
            html += f'<div class="sp-chart-placeholder" style="border-color:{accent}">LINE</div>'
            if items:
                html += '<div class="sp-list">'
                for i, item in enumerate(items[:4]):
                    badge = _badge(i)
                    html += f'<div class="sp-item">{badge}{_esc(item)}</div>'
                html += '</div>'

    # ── flow: Remotion — StepBadge + Connector, 4이하=가로, 5+=세로 ──
    elif layout == "flow":
        if show_hl:
            html += _render_headline(headline, "sm")
        is_vertical = len(items) > 4
        cls = "sp-flow sp-flow-v" if is_vertical else "sp-flow"
        html += f'<div class="{cls}">'
        for i, item in enumerate(items[:6]):
            if i > 0:
                arrow = "↓" if is_vertical else "→"
                html += f'<span class="sp-connector" style="color:{accent}">{arrow}</span>'
            badge = _badge(i)
            is_active = (i == len(items[:6]) - 1)
            active_style = f"border-color:{accent};color:{accent}" if is_active else ""
            html += f'<span class="sp-step" style="{active_style}">{badge}<span class="sp-step-num" style="color:{accent}">{i+1}</span>{_esc(item)}</span>'
        html += '</div>'

    # ── timeline: Remotion — TimelineDot + 연결선 + 텍스트, 마지막 active ──
    elif layout == "timeline":
        if show_hl:
            html += _render_headline(headline, "sm")
        shown = items[:6]
        html += '<div class="sp-timeline">'
        for i, item in enumerate(shown):
            badge = _badge(i)
            is_active = (i == len(shown) - 1)
            dot_style = f"background:{accent}" if is_active else f"border:0.4cqw solid {accent}"
            line = f'<div class="sp-tl-line" style="background:{accent}44"></div>' if i < len(shown) - 1 else ""
            val_text = f'<span class="sp-tl-year" style="color:{accent}">{values[i]}</span>' if i < len(values) else ""
            desc = _desc(i)
            item_color = f'color:{accent}' if is_active else ""
            html += (f'<div class="sp-tl-item">'
                     f'<div class="sp-tl-dot-col"><div class="sp-tl-dot" style="{dot_style}"></div>{line}</div>'
                     f'<div class="sp-tl-content" style="{item_color}">{val_text}{badge}{_esc(item)}{desc}</div>'
                     f'</div>')
        html += '</div>'

    # ── metric_spotlight / icon_stat: Remotion — 큰 수치 + 레이블 ──
    elif layout in ("metric_spotlight", "icon_stat"):
        m = re.search(r'\{\{([^}]+)\}\}', headline)
        num_text = m.group(1) if m else (str(values[0]) + unit if values else "")
        rest = re.sub(r'\{\{[^}]+\}\}', '', headline).strip().replace("\\n", " ").replace("\n", " ")
        badge = _badge(0) if item_icons or item_flags else ""
        html += f'<div class="sp-metric" style="color:{accent}">{badge}{_esc(num_text)}</div>'
        if rest:
            html += f'<div class="sp-sub">{_esc(rest)}</div>'
        # Remotion: sparkline placeholder
        if len(values) > 2:
            html += f'<div class="sp-sparkline" style="border-color:{accent}"></div>'

    # ── metric_wall: Remotion — 2x2 그리드 ──
    elif layout == "metric_wall":
        cols = 2 if len(items) <= 2 else (3 if len(items) <= 3 else 2)
        html += f'<div class="sp-metric-grid" style="grid-template-columns:repeat({cols},1fr)">'
        for i, item in enumerate(items[:6]):
            badge = _badge(i)
            v = values[i] if i < len(values) else ""
            html += (f'<div class="sp-metric-cell">{badge}'
                     f'<div class="sp-metric-val" style="color:{accent}">{v}{unit}</div>'
                     f'<div class="sp-metric-label">{_esc(item)}</div></div>')
        html += '</div>'

    # ── before_after: Remotion — BEFORE + Connector + AFTER ──
    elif layout == "before_after":
        if show_hl:
            html += _render_headline(headline, "sm")
        html += '<div class="sp-split">'
        labels = ["BEFORE", "AFTER"]
        for i in range(min(2, len(items))):
            badge = _badge(i)
            img = _item_img(i)
            desc = _desc(i)
            html += f'<div class="sp-split-half"><div class="sp-tiny" style="color:{accent}">{labels[i]}</div>{img}{badge}<div>{_esc(items[i])}</div>{desc}</div>'
            if i == 0:
                html += f'<div class="sp-vs" style="color:{accent}">→</div>'
        html += '</div>'

    # ── rank_list: Remotion — RankBadge + MiniBar ──
    elif layout == "rank_list":
        if show_hl:
            html += _render_headline(headline, "sm")
        max_val = max(values) if values else 1
        html += '<div class="sp-rank-list">'
        for i, item in enumerate(items[:5]):
            badge = _badge(i)
            v = values[i] if i < len(values) else 0
            pct = int((v / max_val) * 100) if max_val else 0
            # Remotion: 1위 accent, 나머지 dimmed
            bar_color = accent if i == 0 else f"{accent}66"
            rank_color = "#F59E0B" if i == 0 else ("#94A3B8" if i == 1 else ("#CD7F32" if i == 2 else "#64748B"))
            html += (f'<div class="sp-rank-row">'
                     f'<span class="sp-rank" style="color:{rank_color}">#{i+1}</span>'
                     f'{badge}<span class="sp-rank-label">{_esc(item)}</span>'
                     f'<div class="sp-rank-bar"><div class="sp-bar-fill" style="width:{pct}%;background:{bar_color}"></div></div>'
                     f'<span class="sp-bar-val">{v}{unit}</span>'
                     f'</div>')
        html += '</div>'

    # ── stacked_progress: Remotion — ProgressBar 수직 스택 ──
    elif layout == "stacked_progress":
        if show_hl:
            html += _render_headline(headline, "sm")
        max_val = max(values) if values else 100
        html += '<div class="sp-stacked">'
        for i, item in enumerate(items[:5]):
            badge = _badge(i)
            v = values[i] if i < len(values) else 0
            pct = int((v / max_val) * 100) if max_val else 0
            bar_color = accent if i == 0 else f"{accent}88"
            html += (f'<div class="sp-progress-row">'
                     f'{badge}<span class="sp-bar-label">{_esc(item)}</span>'
                     f'<div class="sp-bar-track"><div class="sp-bar-fill" style="width:{pct}%;background:{bar_color}"></div></div>'
                     f'<span class="sp-bar-val">{v}{unit}</span>'
                     f'</div>')
        html += '</div>'

    # ── card_carousel: Remotion — 카드 나열 ──
    elif layout in ("card_carousel",):
        html += _render_headline(headline)
        if items:
            html += '<div class="sp-cards">'
            for i, item in enumerate(items[:4]):
                badge = _badge(i)
                img = _item_img(i)
                desc = _desc(i)
                html += f'<div class="sp-card">{img}{badge}<div>{_esc(item)}</div>{desc}</div>'
            html += '</div>'

    # ── quote_portrait: Remotion — 인물 이미지 + 인용문 ──
    elif layout == "quote_portrait":
        html += f'<div class="sp-quote-mark" style="color:{accent}">"</div>'
        quote_text = items[0] if items else headline
        html += f'<div class="sp-quote" style="border-color:{accent};font-style:italic">{_esc_br(quote_text)}</div>'
        if source:
            html += f'<div class="sp-quote-source">— {_esc(source)}</div>'

    # ── annotated_chart: Remotion — bar + annotation ──
    elif layout == "annotated_chart":
        if headline:
            html += _render_headline(headline, "sm")
        max_val = max(values) if values else 1
        html += '<div class="sp-bars">'
        for i, item in enumerate(items[:6]):
            badge = _badge(i)
            v = values[i] if i < len(values) else 0
            pct = int((v / max_val) * 100) if max_val else 0
            html += (f'<div class="sp-bar-row">'
                     f'<span class="sp-bar-label">{badge}{_esc(item)}</span>'
                     f'<div class="sp-bar-track"><div class="sp-bar-fill" style="width:{pct}%;background:{accent}"></div></div>'
                     f'<span class="sp-bar-val">{v}{unit}</span>'
                     f'</div>')
        html += '</div>'

    else:
        # 기타 레이아웃 — fallback
        if headline:
            html += _render_headline(headline, "sm")
        if items:
            html += '<div class="sp-list">'
            for i, item in enumerate(items[:5]):
                badge = _badge(i)
                html += f'<div class="sp-item">{badge}{_esc(item)}</div>'
            html += '</div>'

    # ── source (Remotion: 하단 출처) ──
    html += _source()
    html += '</div></div>'
    return html


def get_scene_image_candidates(project_dir_name: str, scene_num: int, output_dir: str) -> list:
    """씬의 이미지 후보 목록 반환 (search/ 폴더에서 scene_NNN_01~05 검색).

    project_dir_name: output 디렉토리명 (uuid_{slug} 형식) — URL 구성에 사용.

    Returns:
        [{"rank": 1, "url": "/output/.../scene_001_01.png", "filename": "...", "selected": True}, ...]
    """
    search_dir = Path(output_dir) / "images" / "search"
    images_dir = Path(output_dir) / "images"
    scene_key = f"scene_{scene_num:03d}"

    candidates = []

    # search/ 폴더에서 scene_NNN_NN.* 파일 검색
    valid_exts = {".png", ".jpg", ".jpeg", ".webp"}
    if search_dir.exists():
        for f in sorted(search_dir.glob(f"{scene_key}_*")):
            if f.suffix.lower() not in valid_exts:
                continue
            # scene_001_01.png → rank 1
            stem = f.stem  # scene_001_01
            parts = stem.rsplit("_", 1)
            if len(parts) == 2:
                try:
                    rank = int(parts[1])
                except ValueError:
                    continue
                candidates.append({
                    "rank": rank,
                    "url": f"/output/{project_dir_name}/images/search/{f.name}",
                    "filename": f.name,
                })

    # 중복 제거 (확장자가 다를 때)
    seen_ranks = set()
    unique = []
    for c in sorted(candidates, key=lambda x: x["rank"]):
        if c["rank"] not in seen_ranks:
            seen_ranks.add(c["rank"])
            unique.append(c)
    candidates = unique

    # image_assets.json에서 selected_rank 읽기
    selected_rank = 1
    registry_path = images_dir / "image_assets.json"
    if registry_path.exists():
        try:
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            for asset in registry.get("assets", []):
                if asset.get("scene") == scene_key:
                    selected_rank = asset.get("selected_rank", 1)
                    # 후보에 메타데이터 보강 (rank → candidate dict)
                    cand_by_rank = {c["rank"]: c for c in candidates}
                    for cand_meta in asset.get("candidates", []):
                        c = cand_by_rank.get(cand_meta.get("rank"))
                        if c:
                            c["score"] = cand_meta.get("score", 0)
                            c["source"] = cand_meta.get("source", "")
                            c["title"] = cand_meta.get("title", "")
                            c["width"] = cand_meta.get("width", 0)
                            c["height"] = cand_meta.get("height", 0)
                    break
        except Exception:
            pass

    for c in candidates:
        c["selected"] = (c["rank"] == selected_rank)

    return candidates


def get_recent_images(project_dir_name: str, output_dir: str, limit: int = 3) -> list:
    """최근 이미지 파일 URL 목록.

    project_dir_name: output 디렉토리명 (uuid_{slug} 형식) — URL 구성에 사용.
    """
    img_dir = Path(output_dir) / "images"
    if not img_dir.exists():
        return []
    images = sorted(img_dir.glob("scene_*.png"))
    return [f"/output/{project_dir_name}/images/{img.name}" for img in images[:limit]]
