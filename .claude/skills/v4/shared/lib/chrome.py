"""프로젝트 chrome(로고/텍스처/자막 스타일/인트로·아웃트로) 설정 헬퍼.

`projects/{id}/project_chrome.json` 을 read/write 하고, 채널 프리셋과 머지하여
렌더 시점에 unit별 effective config를 산출.

라이프사이클: 프로젝트 시작 시 설정하거나 스킵 가능. 작업 중 언제든 갱신 가능.
"""
from __future__ import annotations
from pathlib import Path
import json
from . import paths

PRESETS_DIR = paths.ROOT / "templates" / "chrome-presets"


def chrome_path(project_id: str) -> Path:
    return paths.project_dir(project_id) / "project_chrome.json"


def preset_path(channel: str) -> Path:
    return PRESETS_DIR / f"{channel}.json"


def load_preset(channel: str) -> dict:
    p = preset_path(channel)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def load(project_id: str) -> dict:
    p = chrome_path(project_id)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def save(project_id: str, config: dict) -> Path:
    p = chrome_path(project_id)
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
    """채널 프리셋을 그대로 프로젝트 chrome으로 복사. 이미 있으면 덮어쓰지 않음."""
    if chrome_path(project_id).exists():
        return chrome_path(project_id)
    preset = load_preset(channel)
    return save(project_id, preset)


def merged(project_id: str, channel: str | None = None) -> dict:
    """채널 프리셋(있으면) + 프로젝트 오버라이드 머지된 effective config."""
    base = load_preset(channel) if channel else {}
    return _deep_merge(base, load(project_id))


def effective_for_unit(project_id: str, unit: dict, channel: str | None = None) -> dict:
    """unit의 chrome_override를 프로젝트 chrome에 적용한 unit별 최종 chrome.

    unit dict는 manuscript-tag의 units.json 항목이거나 그 일부.
    """
    base = merged(project_id, channel=channel)
    override = unit.get("chrome_override") or {}
    return _deep_merge(base, override)
