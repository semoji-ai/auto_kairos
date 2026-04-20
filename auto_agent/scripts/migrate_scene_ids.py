#!/usr/bin/env python3
# auto_agent/scripts/migrate_scene_ids.py
"""기존 프로젝트 scene_specs에 sceneId 일괄 부여."""
import argparse
import json
import sys
from pathlib import Path

from auto_agent.paths import get_workspace_dir
from auto_agent.tools.scene_id import new_scene_id


def migrate(project_dir: str):
    """scene_specs 및 관련 파일에 sceneId 부여.

    Args:
        project_dir: 프로젝트 slug 또는 절대 경로
    """
    out = (
        Path(project_dir)
        if Path(project_dir).is_absolute()
        else get_workspace_dir() / "output" / project_dir
    )
    specs_path = out / "scene_specs.json"
    if not specs_path.exists():
        print(f"[ERROR] scene_specs.json 없음: {specs_path}")
        sys.exit(1)

    specs = json.loads(specs_path.read_text(encoding="utf-8"))
    added = 0
    for scene in specs.get("scenes", []):
        if not scene.get("sceneId"):
            scene["sceneId"] = new_scene_id()
            added += 1

    scene_id_map = {s["sceneNumber"]: s.get("sceneId") for s in specs["scenes"]}

    # image_assets.json에 sceneId 추가
    ia_path = out / "images" / "image_assets.json"
    if ia_path.exists():
        ia = json.loads(ia_path.read_text(encoding="utf-8"))
        ia_updated = 0
        for entry in ia.get("scenes", []):
            sn = entry.get("sceneNumber")
            if sn and not entry.get("sceneId") and scene_id_map.get(sn):
                entry["sceneId"] = scene_id_map[sn]
                ia_updated += 1
        if ia_updated > 0:
            ia_path.write_text(
                json.dumps(ia, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        print(f"  image_assets.json sceneId 동기화: {ia_updated}개 업데이트")

    # video_assets.json에 sceneId 추가
    va_path = out / "video_assets.json"
    if va_path.exists():
        va = json.loads(va_path.read_text(encoding="utf-8"))
        va_updated = 0
        for entry in va.get("scenes", []):
            sn = entry.get("sceneNumber")
            if sn and not entry.get("sceneId") and scene_id_map.get(sn):
                entry["sceneId"] = scene_id_map[sn]
                va_updated += 1
        if va_updated > 0:
            va_path.write_text(
                json.dumps(va, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        print(f"  video_assets.json sceneId 동기화: {va_updated}개 업데이트")

    specs_path.write_text(
        json.dumps(specs, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[DONE] {added}개 씬에 sceneId 부여 완료: {specs_path.parent.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="기존 프로젝트에 sceneId 일괄 부여"
    )
    parser.add_argument("--project", required=True, help="프로젝트 slug 또는 절대경로")
    args = parser.parse_args()
    migrate(args.project)
