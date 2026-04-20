# auto_agent/tools/scene_id.py
"""씬 고유 식별자(sceneId) 유틸."""
import uuid


def new_scene_id() -> str:
    """8자리 hex UUID 생성."""
    return uuid.uuid4().hex[:8]


def get_scene_id(scene: dict) -> str | None:
    """씬에서 sceneId 반환. 없으면 None."""
    return scene.get("sceneId") or None


def ensure_scene_ids(scenes: list[dict]) -> list[dict]:
    """sceneId 없는 씬에 신규 UUID 부여 (원본 수정)."""
    for scene in scenes:
        if not scene.get("sceneId"):
            scene["sceneId"] = new_scene_id()
    return scenes
