"""프로젝트 캐릭터 로스터/디자인 헬퍼.

`projects/{id}/characters/`
  - `roster.json`               전체 등장 인물 식별·역할·등장 unit
  - `{character_id}/profile.json`  캐릭터별 디자인 brief
  - `{character_id}/refs/*.{jpg|png}`  레퍼런스 이미지(페이즈 3에서 채워짐)
"""
from __future__ import annotations
from pathlib import Path
import json
from . import paths


def characters_dir(project_id: str) -> Path:
    return paths.project_dir(project_id) / "characters"


def roster_path(project_id: str) -> Path:
    return characters_dir(project_id) / "roster.json"


def profile_path(project_id: str, character_id: str) -> Path:
    return characters_dir(project_id) / character_id / "profile.json"


def refs_dir(project_id: str, character_id: str) -> Path:
    return characters_dir(project_id) / character_id / "refs"


def load_roster(project_id: str) -> dict:
    p = roster_path(project_id)
    if not p.exists():
        return {"project_id": project_id, "characters": []}
    return json.loads(p.read_text(encoding="utf-8"))


def save_roster(project_id: str, data: dict) -> Path:
    p = roster_path(project_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def load_profile(project_id: str, character_id: str) -> dict:
    p = profile_path(project_id, character_id)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def save_profile(project_id: str, character_id: str, data: dict) -> Path:
    p = profile_path(project_id, character_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    refs_dir(project_id, character_id).mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def list_characters(project_id: str) -> list[str]:
    """character_id 리스트 반환."""
    data = load_roster(project_id)
    return [c.get("id") for c in data.get("characters", []) if c.get("id")]


def get_character(project_id: str, character_id: str) -> dict | None:
    data = load_roster(project_id)
    for c in data.get("characters", []):
        if c.get("id") == character_id:
            return c
    return None
