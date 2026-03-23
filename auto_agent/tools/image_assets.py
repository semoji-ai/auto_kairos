"""
이미지 에셋 관리 — selected 기반.

images/image_assets.json 구조:
{
  "scenes": [
    {
      "sceneNumber": 1,
      "selected": "scene_001_search_01.jpg",
      "versions": [
        {"file": "scene_001_search_01.jpg", "type": "search", "query": "...", "source_url": "...", "license": "..."},
        {"file": "scene_001_gen_01.png", "type": "generate", "prompt": "...", "art_style": "..."}
      ]
    }
  ]
}
"""
import json
import shutil
from pathlib import Path
from typing import Optional


def _load(images_dir: Path) -> dict:
    path = images_dir / "image_assets.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"scenes": []}


def _save(images_dir: Path, data: dict):
    path = images_dir / "image_assets.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _get_scene(data: dict, scene_num: int) -> dict:
    for s in data["scenes"]:
        if s["sceneNumber"] == scene_num:
            return s
    scene = {"sceneNumber": scene_num, "selected": None, "versions": []}
    data["scenes"].append(scene)
    data["scenes"].sort(key=lambda x: x["sceneNumber"])
    return scene


def has_generated_version(images_dir: Path, scene_num: int) -> bool:
    """해당 씬에 이미 generate 타입 버전이 있는지 확인."""
    data = _load(images_dir)
    for s in data["scenes"]:
        if s["sceneNumber"] == scene_num:
            return any(v.get("type") == "generate" for v in s.get("versions", []))
    return False


def add_version(images_dir: Path, scene_num: int, file_name: str,
                version_type: str, auto_select: bool = True, **meta) -> dict:
    """버전 추가. auto_select=True면 자동으로 selected 설정."""
    data = _load(images_dir)
    scene = _get_scene(data, scene_num)

    version = {"file": file_name, "type": version_type, **meta}
    scene["versions"].append(version)

    if auto_select:
        scene["selected"] = file_name
        # scene_NNN 심볼릭 링크/복사 업데이트
        _update_selected_link(images_dir, scene_num, file_name)

    _save(images_dir, data)
    return version


def select_version(images_dir: Path, scene_num: int, file_name: str) -> bool:
    """selected 변경."""
    data = _load(images_dir)
    scene = _get_scene(data, scene_num)

    # 해당 파일이 versions에 있는지 확인
    found = any(v["file"] == file_name for v in scene["versions"])
    if not found:
        return False

    scene["selected"] = file_name
    _update_selected_link(images_dir, scene_num, file_name)
    _save(images_dir, data)
    return True


def get_selected(images_dir: Path, scene_num: int) -> Optional[str]:
    """현재 selected 파일명 반환."""
    data = _load(images_dir)
    for s in data["scenes"]:
        if s["sceneNumber"] == scene_num:
            return s.get("selected")
    return None


def get_scene_versions(images_dir: Path, scene_num: int) -> dict:
    """씬의 모든 버전 + selected 정보."""
    data = _load(images_dir)
    for s in data["scenes"]:
        if s["sceneNumber"] == scene_num:
            return s
    return {"sceneNumber": scene_num, "selected": None, "versions": []}


def get_all_scenes(images_dir: Path) -> list:
    """전체 씬 에셋 정보."""
    data = _load(images_dir)
    return data["scenes"]


def _update_selected_link(images_dir: Path, scene_num: int, file_name: str):
    """selected 파일을 scene_NNN.{ext}로 복사 (Remotion/helpers 호환)."""
    src = images_dir / file_name
    if not src.exists():
        return

    # 기존 scene_NNN.* 제거
    for old in images_dir.glob(f"scene_{scene_num:03d}.*"):
        if old.name != file_name and old.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            old.unlink()

    # scene_NNN.{ext}로 복사 (파일명이 이미 scene_NNN이면 스킵)
    expected = f"scene_{scene_num:03d}{src.suffix}"
    if src.name != expected:
        dst = images_dir / expected
        shutil.copy2(src, dst)


def next_filename(images_dir: Path, scene_num: int, version_type: str, ext: str = ".png") -> str:
    """다음 버전 파일명 생성. scene_001_search_01.jpg, scene_001_gen_02.png ..."""
    prefix = f"scene_{scene_num:03d}_{version_type}_"
    existing = list(images_dir.glob(f"{prefix}*"))
    num = len(existing) + 1
    return f"{prefix}{num:02d}{ext}"
