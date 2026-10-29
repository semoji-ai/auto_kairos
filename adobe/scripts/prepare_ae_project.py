"""Prepare an Auto Kairos output project for the AE panel without copying assets.

    python3 adobe/scripts/prepare_ae_project.py output/<project>
    python3 adobe/scripts/prepare_ae_project.py output/<project> --write

The default is read-only. --write creates scenes.json only when absent; existing
AE edits and source files are never rewritten.
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

ADOBE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ADOBE_ROOT))

from backend.v3_import import _map_scene  # noqa: E402


def _json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _selected_by_number(project: Path) -> dict[int, str]:
    path = project / "images" / "image_assets.json"
    if not path.is_file():
        return {}
    result: dict[int, str] = {}
    for entry in _json(path).get("scenes", []):
        if not isinstance(entry, dict) or not isinstance(entry.get("sceneNumber"), int):
            continue
        selected = next((v.get("file") for v in entry.get("images", [])
                         if isinstance(v, dict) and v.get("selected") and v.get("file")), None)
        if selected is None and not entry.get("images"):
            selected = entry.get("selected")
        if selected:
            result[entry["sceneNumber"]] = selected.removeprefix("images/")
    return result


def _image_ref(project: Path, scene: dict, selected: dict[int, str]) -> str:
    if (scene.get("imageAsset") or {}).get("source") == "none":
        return ""
    number = scene["sceneNumber"]
    candidate = selected.get(number)
    if candidate:
        return f"images/{candidate}"
    candidate = (scene.get("imageAsset") or {}).get("localPath") or scene.get("imagePath") or ""
    if candidate.startswith("/output/"):
        marker = f"/output/{project.name}/"
        candidate = candidate[len(marker):] if candidate.startswith(marker) else ""
    return candidate if candidate and not Path(candidate).is_absolute() else ""


def prepare(project: Path, *, write: bool = False) -> dict:
    project = Path(project).expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []
    specs_path = project / "scene_specs.json"
    scenes_path = project / "scenes.json"
    if not specs_path.is_file():
        return {"project": str(project), "ok": False,
                "errors": ["scene_specs.json 없음"], "warnings": []}
    specs = _json(specs_path).get("scenes", [])
    if not isinstance(specs, list) or not specs:
        return {"project": str(project), "ok": False,
                "errors": ["scene_specs.json의 scenes가 비어 있음"], "warnings": []}

    selected = _selected_by_number(project)
    records = []
    numbers: set[int] = set()
    for source in specs:
        if not isinstance(source, dict) or not isinstance(source.get("sceneNumber"), int):
            errors.append("sceneNumber가 없는 씬이 있음")
            continue
        number = source["sceneNumber"]
        if number in numbers:
            errors.append(f"씬 번호 중복: {number}")
            continue
        numbers.add(number)
        record = _map_scene(source)
        record["sceneId"] = source.get("sceneId") or uuid.uuid5(
            uuid.NAMESPACE_URL, f"auto-kairos:{project.name}:{number}:{source.get('narration', '')}"
        ).hex[:8]
        record["imageRef"] = _image_ref(project, source, selected)
        if record["imageRef"]:
            ref = Path(record["imageRef"])
            if ref.is_absolute() or ".." in ref.parts:
                errors.append(f"씬 {number}: 프로젝트 밖의 이미지 경로 {ref}")
            elif not (project / ref).is_file():
                errors.append(f"씬 {number}: 선택 이미지 없음 {ref}")
        records.append(record)

    catalog_path = ADOBE_ROOT / "data/semoji-motion/dogam/techniques.json"
    registry_path = ADOBE_ROOT / "cep/com.autokairos.pd/jsx/dogam/registry.json"
    if not catalog_path.is_file() or not registry_path.is_file():
        errors.append("AE 도감 번들 또는 registry.json 없음")
    else:
        catalog = {item["id"] for item in json.loads(catalog_path.read_text(encoding="utf-8"))}
        registry = {item["id"] for item in _json(registry_path).get("techniques", [])}
        for record in records:
            for technique in record.get("techniques") or []:
                if technique not in catalog:
                    errors.append(f"씬 {record['sceneNumber']}: 도감에 없는 기법 {technique}")
                elif technique not in registry:
                    warnings.append(f"씬 {record['sceneNumber']}: {technique}는 AE 수동 연출 대상")

    if not (project / "art_style.json").is_file():
        warnings.append("art_style.json 없음: 채널 화풍을 작업 전에 확인")
    if scenes_path.is_file():
        existing = _json(scenes_path).get("scenes", [])
        existing_numbers = [s.get("sceneNumber") for s in existing if isinstance(s, dict)]
        source_numbers = [s["sceneNumber"] for s in records]
        if existing_numbers != source_numbers:
            errors.append("기존 scenes.json의 씬 번호·순서가 scene_specs.json과 다름; 자동 덮어쓰기 금지")
        expected = {s["sceneNumber"]: s for s in records}
        for scene in existing:
            if not isinstance(scene, dict) or scene.get("sceneNumber") not in expected:
                continue
            number = scene["sceneNumber"]
            original = expected[number]
            if scene.get("narration", "") != original.get("narration", ""):
                warnings.append(f"씬 {number}: AE 원고와 scene_specs 원고가 다름; 편집 의도 확인")
            ref = scene.get("imageRef") or ""
            if ref and ref != original.get("imageRef"):
                warnings.append(f"씬 {number}: AE 선택 이미지와 스토리보드 선택 이미지가 다름")
            if ref:
                path = Path(ref)
                if path.is_absolute() or ".." in path.parts or not (project / path).is_file():
                    errors.append(f"씬 {number}: AE 이미지 경로가 없거나 프로젝트 밖임 {ref}")
        status = "existing"
    else:
        status = "ready_to_create"

    if write and not errors and status == "ready_to_create":
        with scenes_path.open("x", encoding="utf-8") as handle:
            json.dump({"scenes": records}, handle, ensure_ascii=False, indent=2)
        status = "created"

    return {"project": str(project), "ok": not errors, "status": status,
            "scene_count": len(records), "selected_images": sum(bool(s["imageRef"]) for s in records),
            "errors": errors, "warnings": warnings}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="output/<project> directory")
    parser.add_argument("--write", action="store_true", help="create scenes.json only when absent")
    args = parser.parse_args()
    try:
        result = prepare(args.project, write=args.write)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {"project": str(args.project), "ok": False, "errors": [str(exc)], "warnings": []}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
