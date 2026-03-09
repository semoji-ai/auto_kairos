"""대시보드 데이터 파싱 헬퍼."""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional


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


def get_scene_image_url(slug: str, scene_num: int, output_dir: str) -> Optional[str]:
    """씬 이미지 URL 반환 (/output/ 마운트 기준)."""
    img = Path(output_dir) / "images" / f"scene_{scene_num:03d}.png"
    if img.exists():
        return f"/output/{slug}/images/scene_{scene_num:03d}.png"
    return None


def get_scene_audio_url(slug: str, scene_num: int, output_dir: str) -> Optional[str]:
    """씬 오디오 URL 반환."""
    audio = Path(output_dir) / "audio" / f"scene_{scene_num:03d}.mp3"
    if audio.exists():
        return f"/output/{slug}/audio/scene_{scene_num:03d}.mp3"
    return None


def parse_manuscript_chapters(text: str) -> list:
    """final_manuscript.md를 챕터별로 파싱."""
    chapters = []
    current_chapter = None
    current_scenes = []
    current_scene = None

    for line in text.split("\n"):
        ch_match = re.match(r'^# Ch(\d+)\.\s*(.+)', line)
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

        scene_match = re.match(r'^## Scene (\d+):\s*(.+)', line)
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


def get_pipeline_progress(output_dir: str, data_dir: str,
                          db_runs: list = None) -> dict:
    """pipeline.json + DB 실행 이력을 조합하여 진행률 계산.

    db_runs가 제공되면 DB 기반으로 상태를 결정하고,
    없으면 pipeline_state.json을 폴백으로 사용한다.
    """
    pipeline_path = Path(data_dir) / "pipeline.json"
    if not pipeline_path.exists():
        return {"phases": []}

    pipeline_def = json.loads(pipeline_path.read_text(encoding="utf-8"))

    # DB 이력에서 각 스텝의 최신 상태를 추출
    if db_runs:
        step_status_map = {}
        for run in reversed(db_runs):  # 오래된 것부터 → 최신이 덮어씀
            step_key = run.get("step", "")
            status = run.get("status", "")
            if step_key and status:
                step_status_map[step_key] = status
        completed_steps = {k for k, v in step_status_map.items() if v == "completed"}
        failed_steps = {k for k, v in step_status_map.items() if v == "failed"}
        skipped_steps = {k for k, v in step_status_map.items() if v == "skipped"}
        running_steps = {k for k, v in step_status_map.items() if v == "running"}
    else:
        # 폴백: pipeline_state.json
        state = load_project_json(output_dir, "pipeline_state.json") or {}
        completed_steps = set(state.get("completed_steps", []))
        failed_steps = set(state.get("failed_steps", []))
        skipped_steps = set(state.get("skipped_steps", []))
        running_steps = {state.get("current_step")} if state.get("current_step") else set()

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


def enrich_scenes_with_media(scenes: list, slug: str, output_dir: str,
                              tts_results: Optional[dict] = None) -> list:
    """씬 목록에 이미지/오디오 URL + TTS 정보를 추가."""
    tts_map = {}
    if tts_results:
        for r in tts_results.get("results", []):
            tts_map[r["scene"]] = r

    for scene in scenes:
        sn = scene["sceneNumber"]
        scene["_image_url"] = get_scene_image_url(slug, sn, output_dir)
        scene["_audio_url"] = get_scene_audio_url(slug, sn, output_dir)
        tts = tts_map.get(sn, {})
        scene["_tts_duration"] = tts.get("duration")
        scene["_tts_status"] = tts.get("status")

    return scenes


def format_headline(headline: str) -> str:
    """{{텍스트}} → <span class="accent-text">텍스트</span> 변환."""
    if not headline:
        return ""
    return re.sub(r'\{\{(.+?)\}\}', r'<span class="accent-text">\1</span>', headline)


def get_recent_images(slug: str, output_dir: str, limit: int = 3) -> list:
    """최근 이미지 파일 URL 목록."""
    img_dir = Path(output_dir) / "images"
    if not img_dir.exists():
        return []
    images = sorted(img_dir.glob("scene_*.png"))
    return [f"/output/{slug}/images/{img.name}" for img in images[:limit]]
