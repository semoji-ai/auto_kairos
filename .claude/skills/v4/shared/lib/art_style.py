"""프로젝트 art_style(컬러·일러스트 모드·캐릭터 디자인 규칙·무드) 헬퍼.

`projects/{id}/art_style.json` 라이프사이클: 시작 시 채널 프리셋 적용 또는 스킵,
작업 중 언제든 갱신. character-design / image-generate 가 effective config를 읽음.
"""
from __future__ import annotations
from pathlib import Path
import json
from . import paths

PRESETS_DIR = paths.ROOT / "templates" / "art-style-presets"


def style_path(project_id: str) -> Path:
    return paths.project_dir(project_id) / "art_style.json"


def preset_path(channel: str) -> Path:
    return PRESETS_DIR / f"{channel}.json"


def load_preset(channel: str) -> dict:
    p = preset_path(channel)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def load(project_id: str) -> dict:
    p = style_path(project_id)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def save(project_id: str, config: dict) -> Path:
    p = style_path(project_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def init_from_preset(project_id: str, channel: str) -> Path:
    if style_path(project_id).exists():
        return style_path(project_id)
    return save(project_id, load_preset(channel))


def merged(project_id: str, channel: str | None = None) -> dict:
    base = load_preset(channel) if channel else {}
    return _deep_merge(base, load(project_id))
