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
import threading
from pathlib import Path
from typing import Optional

# 멀티스레드 환경에서 image_assets.json 동시 쓰기 방지
_file_lock = threading.Lock()


def _load(images_dir: Path) -> dict:
    path = images_dir / "image_assets.json"
    result = {"scenes": []}

    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            # 표준 포맷
            if "scenes" in raw and isinstance(raw["scenes"], list):
                result = raw
            # assembly-director 레거시 포맷: {"assets": [{"scene": "scene_001", ...}]}
            elif "assets" in raw:
                scenes = []
                for a in raw["assets"]:
                    scene_key = a.get("scene", "")
                    num_str = scene_key.replace("scene_", "").lstrip("0") or "0"
                    try:
                        num = int(num_str)
                    except ValueError:
                        continue
                    version = {
                        "file": Path(a.get("final", a.get("origin", ""))).name,
                        "type": a.get("type", "generated"),
                    }
                    scenes.append({
                        "sceneNumber": num,
                        "selected": version["file"],
                        "versions": [version],
                    })
                scenes.sort(key=lambda x: x["sceneNumber"])
                result = {"scenes": scenes}
            # 숫자 키 dict 레거시: {"1": {...}, "3": {...}}
            elif all(k.isdigit() for k in raw.keys()):
                # 이 포맷은 빈 버전이 많으므로 무시하고 파일 스캔으로 넘어감
                pass
        except Exception:
            pass

    # 파일 시스템 자동 스캔: image_assets.json에 없는 이미지를 자동 등록
    if images_dir.exists():
        registered = {}
        for s in result["scenes"]:
            for v in s.get("versions", []):
                registered[v.get("file", "")] = True

        # images/ 루트 + images/generated/ 스캔
        scan_dirs = [(images_dir, ""), ]
        gen_dir = images_dir / "generated"
        if gen_dir.exists():
            scan_dirs.append((gen_dir, "generated/"))

        for scan_dir, prefix in scan_dirs:
            for f in sorted(scan_dir.glob("scene_*")):
                if f.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
                    continue
                rel = prefix + f.name
                if rel in registered:
                    continue
                # scene_001.png → scene_num=1
                name_part = f.stem  # scene_001 or scene_001_gen_02
                num_str = name_part.split("_")[1] if "_" in name_part else ""
                try:
                    num = int(num_str)
                except ValueError:
                    continue
                vtype = "generate" if "gen" in name_part or prefix == "generated/" else "search"
                # 해당 씬 찾거나 생성
                scene_entry = None
                for s in result["scenes"]:
                    if s["sceneNumber"] == num:
                        scene_entry = s
                        break
                if not scene_entry:
                    scene_entry = {"sceneNumber": num, "selected": None, "versions": []}
                    result["scenes"].append(scene_entry)
                scene_entry["versions"].append({"file": rel, "type": vtype})
                if not scene_entry["selected"]:
                    scene_entry["selected"] = rel
                registered[rel] = True

        result["scenes"].sort(key=lambda x: x["sceneNumber"])

    return result


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
    """버전 추가. auto_select=True면 자동으로 selected 설정. 스레드 안전."""
    with _file_lock:
        data = _load(images_dir)
        scene = _get_scene(data, scene_num)

        version = {"file": file_name, "type": version_type, **meta}
        scene["versions"].append(version)

        if auto_select:
            scene["selected"] = file_name
            _update_selected_link(images_dir, scene_num, file_name)

        _save(images_dir, data)
        return version


def select_version(images_dir: Path, scene_num: int, file_name: str) -> bool:
    """selected 변경. 스레드 안전."""
    with _file_lock:
        data = _load(images_dir)
        scene = _get_scene(data, scene_num)

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
