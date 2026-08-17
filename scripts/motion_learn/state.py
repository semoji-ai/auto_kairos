"""레퍼런스별 진행 상태 — refs/{slug}/state.json. 멱등 단계 진행."""
from __future__ import annotations

import json
from pathlib import Path


def _path(ref_dir: Path) -> Path:
    return ref_dir / "state.json"


def get_state(ref_dir: Path) -> dict:
    fp = _path(ref_dir)
    if not fp.is_file():
        return {}
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def set_stage(ref_dir: Path, stage: str, extra: dict | None = None) -> dict:
    """stage 갱신 + extra 병합(기존 필드 보존). 반환=새 상태."""
    ref_dir.mkdir(parents=True, exist_ok=True)
    s = get_state(ref_dir)
    s["stage"] = stage
    if extra:
        s.update(extra)
    _path(ref_dir).write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
    return s
