"""신규 프리셋 후보 → 라이브러리 머지(검토 게이트). 중복 스킵·무삭제.
빌더(build_from_json.jsx applyPreset)가 지원하는 props만 즉시 동작 — 그 외는 needs_builder 플래그."""
from __future__ import annotations

import json
from pathlib import Path

# P1 빌더 applyPreset이 다루는 props (이 외 props는 빌더 코드 확장 필요)
BUILDER_PROPS = {"opacity", "scale", "position", "rotationY", "trimEnd", "textOffset"}


def is_builder_supported(preset: dict) -> bool:
    return set(preset.get("props", [])) <= BUILDER_PROPS


def list_candidates(new_presets_path: Path) -> list[dict]:
    if not new_presets_path.is_file():
        return []
    try:
        return json.loads(new_presets_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def merge(lib_path: Path, candidates: list[dict], approved: list[str]) -> dict:
    """approved 이름의 후보를 lib_path(motion_presets.json)에 추가. 중복 이름은 스킵.
    반환 {added, skipped_duplicate, needs_builder}."""
    lib = json.loads(lib_path.read_text(encoding="utf-8"))
    presets = lib.setdefault("presets", {})
    added, dup, needs = [], [], []
    by_name = {c.get("name"): c for c in candidates}
    for name in approved:
        c = by_name.get(name)
        if not c:
            continue
        if name in presets:
            dup.append(name); continue
        entry = {k: c[k] for k in ("props", "ease", "params") if k in c}
        presets[name] = entry
        added.append(name)
        if not is_builder_supported(c):
            needs.append(name)
    lib_path.write_text(json.dumps(lib, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"added": added, "skipped_duplicate": dup, "needs_builder": needs}
