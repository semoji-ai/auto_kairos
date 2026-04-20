# auto_agent/tools/scene_split.py
"""씬 분할 핵심 로직."""
import re
import copy
from pathlib import Path
from auto_agent.tools.scene_id import new_scene_id


def split_narration_by_sentence(narration: str) -> tuple[str, str]:
    """나레이션을 문장 단위로 절반 분할. 문장이 하나면 (전체, "") 반환."""
    sentences = [s.strip() for s in re.split(r'(?<=[.!?。])\s+', narration.strip()) if s.strip()]
    if len(sentences) <= 1:
        return narration, ""
    mid = max(1, len(sentences) // 2)
    a = " ".join(sentences[:mid])
    b = " ".join(sentences[mid:])
    return a, b


def apply_split_to_specs(specs: dict, scene_num: int, narration_a: str, narration_b: str) -> dict:
    """scene_specs 딕셔너리에 씬 분할을 적용한다. 원본을 수정하지 않고 새 dict 반환."""
    result = copy.deepcopy(specs)
    scenes = result["scenes"]

    # 대상 씬 찾기
    target_idx = next((i for i, s in enumerate(scenes) if s["sceneNumber"] == scene_num), None)
    if target_idx is None:
        raise ValueError(f"sceneNumber {scene_num} not found")

    # 원본 씬 수정 (narration_a, sceneId 유지)
    original = scenes[target_idx]
    original["narration"] = narration_a
    original.pop("narration_tts", None)
    original.pop("subtitle_lines", None)
    original.pop("subtitle_lines_tts", None)
    original.pop("tts_changes", None)

    # 새 씬 생성 (narration_b, 신규 sceneId)
    new_scene = copy.deepcopy(original)
    new_scene["sceneId"] = new_scene_id()
    new_scene["narration"] = narration_b
    new_scene["imageAsset"] = {
        "source": original.get("imageAsset", {}).get("source", "generate"),
        "prompt": "",
        "placement": "fullscreen",
        "opacity": 1.0,
    }
    new_scene.pop("narration_tts", None)
    new_scene.pop("subtitle_lines", None)
    new_scene.pop("subtitle_lines_tts", None)
    new_scene.pop("tts_changes", None)

    # num+1 이후 씬 sceneNumber +1
    for scene in scenes[target_idx + 1:]:
        scene["sceneNumber"] += 1

    # 새 씬 삽입 (target_idx+1 위치)
    new_scene["sceneNumber"] = scene_num + 1
    scenes.insert(target_idx + 1, new_scene)

    return result


def renumber_files(out_dir: Path, from_scene: int, is_legacy: bool) -> None:
    """레거시 프로젝트: from_scene 이후 파일들을 역순으로 +1 rename."""
    if not is_legacy:
        return

    audio_dir = out_dir / "audio"
    subtitles_dir = out_dir / "subtitles"
    img_gen_dir = out_dir / "images" / "generated"
    img_search_dir = out_dir / "images" / "search"

    # 최대 씬 번호 파악
    max_n = from_scene
    if audio_dir.exists():
        for f in audio_dir.glob("scene_*.mp3"):
            try:
                n = int(f.stem.split("_")[1])
                max_n = max(max_n, n)
            except (IndexError, ValueError):
                pass

    # 역순 rename으로 충돌 방지
    for n in range(max_n, from_scene - 1, -1):
        # audio mp3
        if audio_dir.exists():
            src = audio_dir / f"scene_{n:03d}.mp3"
            if src.exists():
                src.rename(audio_dir / f"scene_{n+1:03d}.mp3")
            # timestamps.json
            ts = audio_dir / f"scene_{n:03d}.timestamps.json"
            if ts.exists():
                ts.rename(audio_dir / f"scene_{n+1:03d}.timestamps.json")
        # subtitles
        if subtitles_dir.exists():
            src = subtitles_dir / f"scene_{n:03d}.json"
            if src.exists():
                src.rename(subtitles_dir / f"scene_{n+1:03d}.json")
        # generated images
        if img_gen_dir.exists():
            for f in list(img_gen_dir.glob(f"scene_{n:03d}_*.png")) + list(img_gen_dir.glob(f"scene_{n:03d}_*.jpg")):
                new_name = f.name.replace(f"scene_{n:03d}_", f"scene_{n+1:03d}_")
                f.rename(f.parent / new_name)
        # search images
        if img_search_dir.exists():
            for f in list(img_search_dir.glob(f"scene_{n:03d}_*.png")) + list(img_search_dir.glob(f"scene_{n:03d}_*.jpg")):
                new_name = f.name.replace(f"scene_{n:03d}_", f"scene_{n+1:03d}_")
                f.rename(f.parent / new_name)

    # image_assets.json selected 경로 업데이트
    ia_path = out_dir / "images" / "image_assets.json"
    if ia_path.exists():
        import json as _json
        ia = _json.loads(ia_path.read_text(encoding="utf-8"))
        for entry in ia.get("scenes", []):
            sel = entry.get("selected", "")
            if not sel:
                continue
            # 접두어 정규화: images/search/ → search/, images/generated/ → generated/
            import re as _re
            sel = _re.sub(r'^images/', '', sel)
            # scene_NNN_ 패턴이 from_scene 이상이면 +1
            def _bump(m):
                n = int(m.group(1))
                return f"scene_{n+1:03d}_" if n >= from_scene else m.group(0)
            sel = _re.sub(r'scene_(\d+)_', _bump, sel)
            entry["selected"] = sel
        ia_path.write_text(_json.dumps(ia, ensure_ascii=False, indent=2))
