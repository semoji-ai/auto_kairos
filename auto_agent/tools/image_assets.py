"""
이미지 에셋 관리 — image_assets.json (단일 DB)

images/image_assets.json 구조:
{
  "scenes": [
    {
      "sceneNumber": 1,
      "images": [
        {"file": "generated/scene_001_gen_01.png", "type": "generate", "selected": true, "prompt": "..."},
        {"file": "generated/scene_001_gen_02.png", "type": "generate", "selected": false},
        {"file": "search/scene_001_search_01.jpg", "type": "search", "selected": false, "source_url": "...", "license": "..."}
      ]
    }
  ]
}

- selected: true인 이미지가 스토리보드/렌더링에 사용
- 파일 복사 없음 — selected 필드 토글만
- 검색/생성/URL 모두 images[]에 등록
"""
import hashlib
import json
import shutil
import threading
from pathlib import Path
from typing import Optional

_file_lock = threading.Lock()


def _load(images_dir: Path) -> dict:
    path = images_dir / "image_assets.json"
    result = {"scenes": []}

    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))

            # 새 포맷: images[] with selected boolean
            if "scenes" in raw and isinstance(raw["scenes"], list):
                first_scene = raw["scenes"][0] if raw["scenes"] else {}
                if "images" in first_scene:
                    # 이미 새 포맷
                    result = raw
                elif "versions" in first_scene:
                    # 구 포맷 → 새 포맷 마이그레이션
                    for s in raw["scenes"]:
                        selected_file = s.get("selected", "")
                        images = []
                        for v in s.get("versions", []):
                            img = {**v, "selected": v.get("file", "") == selected_file}
                            images.append(img)
                        s["images"] = images
                        s.pop("versions", None)
                        s.pop("selected", None)
                    result = raw

            # assembly-director 레거시: {"assets": [...]}
            elif "assets" in raw:
                scenes = []
                for a in raw["assets"]:
                    scene_key = a.get("scene", "")
                    num_str = scene_key.replace("scene_", "").lstrip("0") or "0"
                    try:
                        num = int(num_str)
                    except ValueError:
                        continue
                    fname = Path(a.get("final", a.get("origin", ""))).name
                    scenes.append({
                        "sceneNumber": num,
                        "images": [{"file": fname, "type": a.get("type", "generate"), "selected": True}],
                    })
                scenes.sort(key=lambda x: x["sceneNumber"])
                result = {"scenes": scenes}

            # 숫자 키 dict 레거시: {"1": {...}, "3": {...}}
            elif all(k.isdigit() for k in raw.keys()):
                pass  # 파일 스캔으로 처리

        except Exception:
            pass

    # 파일 시스템 자동 스캔: DB에 없는 이미지를 자동 등록
    if images_dir.exists():
        registered = set()
        for s in result["scenes"]:
            for img in s.get("images", []):
                registered.add(img.get("file", ""))

        scan_dirs = [(images_dir, "")]
        for sub in ("generated", "search"):
            sub_dir = images_dir / sub
            if sub_dir.exists():
                scan_dirs.append((sub_dir, sub + "/"))

        for scan_dir, prefix in scan_dirs:
            for f in sorted(scan_dir.glob("scene_*")):
                if f.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
                    continue
                rel = prefix + f.name
                if rel in registered:
                    continue
                name_part = f.stem
                num_str = name_part.split("_")[1] if "_" in name_part else ""
                try:
                    num = int(num_str)
                except ValueError:
                    continue
                vtype = "generate" if "gen" in name_part or prefix == "generated/" else "search"

                scene_entry = None
                for s in result["scenes"]:
                    if s["sceneNumber"] == num:
                        scene_entry = s
                        break
                if not scene_entry:
                    scene_entry = {"sceneNumber": num, "images": []}
                    result["scenes"].append(scene_entry)

                # 다른 이미지가 없으면 첫 번째를 selected
                has_selected = any(img.get("selected") for img in scene_entry["images"])
                scene_entry["images"].append({
                    "file": rel, "type": vtype, "selected": not has_selected,
                })
                registered.add(rel)

        result["scenes"].sort(key=lambda x: x["sceneNumber"])

    # 중복 제거 (같은 file이 여러 번 등록된 경우)
    for s in result["scenes"]:
        seen = set()
        deduped = []
        for img in s.get("images", []):
            f = img.get("file", "")
            if f not in seen:
                seen.add(f)
                deduped.append(img)
        s["images"] = deduped

    return result


def _normalize_paths(data: dict):
    r"""모든 file 경로를 / 로 정규화 (Windows \ 방지)."""
    for s in data.get("scenes", []):
        for img in s.get("images", []):
            if img.get("file"):
                img["file"] = img["file"].replace("\\", "/")


def _save(images_dir: Path, data: dict):
    _normalize_paths(data)
    path = images_dir / "image_assets.json"
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
    scene: dict = {"sceneNumber": scene_num, "images": []}
    if scene_id:
        scene["sceneId"] = scene_id
    data["scenes"].append(scene)
    data["scenes"].sort(key=lambda x: x["sceneNumber"])
    return scene


def has_generated_version(images_dir: Path, scene_num: int) -> bool:
    """해당 씬에 이미 generate 타입이 있는지."""
    data = _load(images_dir)
    for s in data["scenes"]:
        if s["sceneNumber"] == scene_num:
            return any(img.get("type") == "generate" for img in s.get("images", []))
    return False


def has_search_version(images_dir: Path, scene_num: int) -> bool:
    """해당 씬에 이미 search 타입이 image_assets에 등록되어 있는지."""
    data = _load(images_dir)
    for s in data["scenes"]:
        if s["sceneNumber"] == scene_num:
            return any(img.get("type") == "search" for img in s.get("images", []))
    return False


def add_version(images_dir: Path, scene_num: int, file_name: str,
                version_type: str, auto_select: bool = True, **meta) -> dict:
    """이미지 등록. auto_select=True면 이 이미지를 selected로. 스레드 안전."""
    file_name = file_name.replace("\\", "/")
    with _file_lock:
        data = _load(images_dir)
        scene = _get_scene(data, scene_num)

        # 중복 방지: 같은 파일이 이미 있으면 선택만 변경
        for existing in scene["images"]:
            if existing["file"] == file_name:
                if auto_select:
                    for img in scene["images"]:
                        img["selected"] = img["file"] == file_name
                    _save(images_dir, data)
                return existing

        img_entry = {"file": file_name, "type": version_type, "selected": False, **meta}

        if auto_select:
            # 기존 selected 해제
            for img in scene["images"]:
                img["selected"] = False
            img_entry["selected"] = True

        scene["images"].append(img_entry)
        _save(images_dir, data)
        return img_entry


def select_version(images_dir: Path, scene_num: int, file_name: str) -> bool:
    """selected 변경 — 해당 파일을 selected, 나머지 해제. 스레드 안전."""
    file_name = file_name.replace("\\", "/")
    with _file_lock:
        data = _load(images_dir)
        scene = _get_scene(data, scene_num)

        found = False
        for img in scene["images"]:
            if img["file"] == file_name:
                img["selected"] = True
                found = True
            else:
                img["selected"] = False

        if found:
            _save(images_dir, data)
        return found


def get_selected(images_dir: Path, scene_num: int) -> Optional[str]:
    """현재 selected 파일명 반환."""
    data = _load(images_dir)
    for s in data["scenes"]:
        if s["sceneNumber"] == scene_num:
            for img in s.get("images", []):
                if img.get("selected"):
                    return img["file"]
    return None


def get_scene_versions(images_dir: Path, scene_num: int) -> dict:
    """씬의 모든 이미지 + selected 정보. (API 호환용)"""
    data = _load(images_dir)
    for s in data["scenes"]:
        if s["sceneNumber"] == scene_num:
            # API 호환: selected 파일명 + versions 형태로 변환
            selected = None
            versions = []
            for img in s.get("images", []):
                v = {**img}
                if img.get("selected"):
                    selected = img["file"]
                versions.append(v)
            return {"sceneNumber": scene_num, "selected": selected, "versions": versions}
    return {"sceneNumber": scene_num, "selected": None, "versions": []}


def get_all_scenes(images_dir: Path) -> list:
    """전체 씬 에셋 정보."""
    data = _load(images_dir)
    return data["scenes"]


def next_filename(images_dir: Path, scene_num: int, version_type: str, ext: str = ".png") -> str:
    """다음 버전 파일명 생성. scene_001_search_01.jpg 등."""
    prefix = f"scene_{scene_num:03d}_{version_type}_"
    # generated/ 또는 search/ 폴더에서 기존 파일 수 확인
    sub_dir = images_dir / ("generated" if version_type == "gen" else "search")
    if sub_dir.exists():
        existing = list(sub_dir.glob(f"{prefix}*"))
    else:
        existing = list(images_dir.glob(f"{prefix}*"))
    num = len(existing) + 1
    return f"{prefix}{num:02d}{ext}"


def set_qa_result(images_dir: Path, scene_num: int, passed: bool, issues: Optional[list] = None) -> None:
    """QA 결과를 image_assets.json에 기록. Thread-safe.

    Args:
        images_dir: images/ 디렉토리 경로
        scene_num: 씬 번호
        passed: True=통과, False=미달
        issues: 미달 이유 목록 (passed=False일 때)
    """
    from datetime import datetime
    with _file_lock:
        data = _load(images_dir)
        scene = _get_scene(data, scene_num)
        scene["qa"] = {
            "passed": passed,
            "issues": issues or [],
            "checked_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
        }
        _save(images_dir, data)


def get_qa_result(images_dir: Path, scene_num: int) -> Optional[dict]:
    """qa 필드 반환. qa 기록 없으면 None.

    Returns:
        {"passed": bool, "issues": list, "checked_at": str} 또는 None
    """
    data = _load(images_dir)
    for s in data["scenes"]:
        if s["sceneNumber"] == scene_num:
            return s.get("qa") or None
    return None


# ── narration 기반 씬번호 reconciliation ──────────────────────────────────────

def _narration_hash(narration: str) -> str:
    """narration 앞 200자를 MD5 해시 (8자리). 씬 동일성 식별자."""
    return hashlib.md5((narration or "").strip()[:200].encode("utf-8")).hexdigest()[:8]


def reconcile_scene_numbers(
    images_dir: Path,
    old_scenes: list,
    new_scenes: list,
) -> dict:
    """씬번호 재부여 후 image_assets.json + image_candidates.json을 narration 기반으로 재매핑.

    Args:
        images_dir: images/ 디렉토리 경로
        old_scenes: 이전 scene_specs["scenes"] 리스트
        new_scenes: 새 scene_specs["scenes"] 리스트

    Returns:
        {"remapped": int, "unmapped": int, "files_renamed": int}
    """
    # old narration_hash → old sceneNumber
    old_hash_to_num: dict[str, int] = {}
    for s in old_scenes:
        h = _narration_hash(s.get("narration", ""))
        if h:
            old_hash_to_num[h] = s["sceneNumber"]

    # new narration_hash → new sceneNumber
    new_hash_to_num: dict[str, int] = {}
    for s in new_scenes:
        h = _narration_hash(s.get("narration", ""))
        if h:
            new_hash_to_num[h] = s["sceneNumber"]

    # old sceneNumber → new sceneNumber (narration 일치 기준)
    old_to_new: dict[int, int] = {}
    for h, old_num in old_hash_to_num.items():
        if h in new_hash_to_num:
            new_num = new_hash_to_num[h]
            if old_num != new_num:
                old_to_new[old_num] = new_num

    if not old_to_new:
        return {"remapped": 0, "unmapped": 0, "files_renamed": 0}

    stats = {"remapped": 0, "unmapped": 0, "files_renamed": 0}

    # ── image_assets.json 재매핑 ──
    assets_path = images_dir / "image_assets.json"
    if assets_path.exists():
        with _file_lock:
            data = _load(images_dir)
            changed = False
            for scene in data["scenes"]:
                old_num = scene["sceneNumber"]
                if old_num not in old_to_new:
                    # 이미 올바른 번호거나 매핑 없음
                    if old_num not in {s["sceneNumber"] for s in new_scenes}:
                        stats["unmapped"] += 1
                    continue
                new_num = old_to_new[old_num]
                scene["sceneNumber"] = new_num
                changed = True
                stats["remapped"] += 1

                # 파일 이름 업데이트 (scene_011_xxx → scene_018_xxx)
                for img in scene.get("images", []):
                    old_file = img.get("file", "")
                    old_fname = Path(old_file).name
                    old_prefix = f"scene_{old_num:03d}_"
                    if old_fname.startswith(old_prefix):
                        new_fname = f"scene_{new_num:03d}_" + old_fname[len(old_prefix):]
                        new_rel = str(Path(old_file).parent / new_fname).replace("\\", "/")
                        # 실제 파일 이름 변경
                        old_abs = images_dir / old_file
                        new_abs = images_dir / new_rel
                        if old_abs.exists() and not new_abs.exists():
                            new_abs.parent.mkdir(parents=True, exist_ok=True)
                            shutil.move(str(old_abs), str(new_abs))
                            stats["files_renamed"] += 1
                        img["file"] = new_rel

            if changed:
                data["scenes"].sort(key=lambda x: x["sceneNumber"])
                _save(images_dir, data)

    # ── image_candidates.json 재매핑 ──
    cands_path = images_dir / "image_candidates.json"
    if cands_path.exists():
        try:
            cands_data = json.loads(cands_path.read_text(encoding="utf-8"))
            cands_changed = False
            for scene in cands_data.get("scenes", []):
                old_num = scene.get("sceneNumber")
                if old_num in old_to_new:
                    scene["sceneNumber"] = old_to_new[old_num]
                    cands_changed = True
            if cands_changed:
                cands_data["scenes"].sort(key=lambda x: x.get("sceneNumber", 0))
                cands_path.write_text(
                    json.dumps(cands_data, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
        except Exception as e:
            print(f"[image_assets] image_candidates.json 재매핑 실패: {e}", flush=True)

    return stats
