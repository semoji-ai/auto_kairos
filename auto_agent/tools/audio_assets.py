"""
오디오 에셋 관리 — selected 기반 (image_assets.py와 동일 패턴).

audio/audio_assets.json 구조:
{
  "scenes": [
    {
      "sceneNumber": 1,
      "selected": "scene_001_v2.mp3",
      "versions": [
        {"file": "scene_001_v1.mp3", "type": "original", "voice_id": "...", "text": "..."},
        {"file": "scene_001_v2.mp3", "type": "regen", "voice_id": "...", "text": "..."}
      ]
    }
  ]
}
"""
import json
import shutil
from pathlib import Path
from typing import Optional


def _load(audio_dir: Path) -> dict:
    path = audio_dir / "audio_assets.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"scenes": []}


def _save(audio_dir: Path, data: dict):
    path = audio_dir / "audio_assets.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _get_scene(data: dict, scene_num: int, scene_id: str | None = None) -> dict:
    # sceneId 우선 조회
    if scene_id:
        for s in data["scenes"]:
            if s.get("sceneId") == scene_id:
                return s
    # sceneNumber 폴백
    for s in data["scenes"]:
        if s["sceneNumber"] == scene_num:
            return s
    # 신규 생성
    scene: dict = {"sceneNumber": scene_num, "selected": None, "versions": []}
    if scene_id:
        scene["sceneId"] = scene_id
    data["scenes"].append(scene)
    data["scenes"].sort(key=lambda x: x["sceneNumber"])
    return scene


def add_version(audio_dir: Path, scene_num: int, file_name: str,
                version_type: str, auto_select: bool = True,
                scene_id: str = "", **meta) -> dict:
    """버전 추가."""
    data = _load(audio_dir)
    scene = _get_scene(data, scene_num, scene_id)
    version = {"file": file_name, "type": version_type, **meta}
    scene["versions"].append(version)

    if auto_select:
        scene["selected"] = file_name
        _update_selected(audio_dir, scene_num, file_name, scene_id=scene_id)

    _save(audio_dir, data)
    return version


def select_version(audio_dir: Path, scene_num: int, file_name: str) -> bool:
    """selected 변경."""
    data = _load(audio_dir)
    scene = _get_scene(data, scene_num)
    found = any(v["file"] == file_name for v in scene["versions"])
    if not found:
        return False
    scene["selected"] = file_name
    _update_selected(audio_dir, scene_num, file_name)
    _save(audio_dir, data)
    return True


def get_selected(audio_dir: Path, scene_num: int) -> Optional[str]:
    data = _load(audio_dir)
    for s in data["scenes"]:
        if s["sceneNumber"] == scene_num:
            return s.get("selected")
    return None


def get_scene_versions(audio_dir: Path, scene_num: int) -> dict:
    data = _load(audio_dir)
    for s in data["scenes"]:
        if s["sceneNumber"] == scene_num:
            return s
    return {"sceneNumber": scene_num, "selected": None, "versions": []}


def next_filename(audio_dir: Path, scene_num: int, scene_id: str = "") -> str:
    """다음 버전 파일명. sceneId 있으면 {sceneId}_v1.mp3, 없으면 scene_NNN_v1.mp3."""
    prefix = f"{scene_id}_v" if scene_id else f"scene_{scene_num:03d}_v"
    existing = list(audio_dir.glob(f"{prefix}*"))
    num = len(existing) + 1
    return f"{prefix}{num}.mp3"


def _update_selected(audio_dir: Path, scene_num: int, file_name: str,
                     scene_id: str = ""):
    """selected를 정규 파일명(sceneId.mp3 또는 scene_NNN.mp3)으로 복사."""
    src = audio_dir / file_name
    if not src.exists():
        return
    canonical = f"{scene_id}.mp3" if scene_id else f"scene_{scene_num:03d}.mp3"
    dst = audio_dir / canonical
    if dst.exists() and dst.name != file_name:
        dst.unlink()
    if src.name != dst.name:
        shutil.copy2(src, dst)
