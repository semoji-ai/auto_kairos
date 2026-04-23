# auto_agent/tools/scene_id.py
"""씬 고유 식별자(sceneId) 유틸."""
from __future__ import annotations
import json
import uuid
from pathlib import Path


def new_scene_id() -> str:
    """8자리 hex UUID 생성."""
    return uuid.uuid4().hex[:8]


def get_scene_id(scene: dict) -> str | None:
    """씬에서 sceneId 반환. 없으면 None."""
    return scene.get("sceneId") or None  # or None: empty string도 None으로 처리


def ensure_scene_ids(scenes: list[dict]) -> list[dict]:
    """sceneId 없는 씬에 신규 UUID 부여 (원본 수정)."""
    for scene in scenes:
        if not scene.get("sceneId"):
            scene["sceneId"] = new_scene_id()
    return scenes


def load_scene_specs(path: Path) -> dict:
    """scene_specs.json 로드 + sceneId 자동 마이그레이션.

    sceneId 없는 씬이 하나라도 있으면 신규 ID를 부여하고 파일을 덮어씀.
    레거시 프로젝트를 처음 처리할 때 한 번만 실행되고 이후는 그냥 로드.
    """
    specs = json.loads(path.read_text(encoding="utf-8"))
    scenes = specs.get("scenes", [])
    missing = [s for s in scenes if not s.get("sceneId")]
    if missing:
        ensure_scene_ids(scenes)
        path.write_text(json.dumps(specs, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[scene_id] sceneId 마이그레이션: {len(missing)}개 씬에 ID 부여 → {path.name}", flush=True)
    return specs
