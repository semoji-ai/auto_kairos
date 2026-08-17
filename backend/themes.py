"""통합 테마 카탈로그 + 단일 해석 지점.

카탈로그: data/artstyle/themes/<id>.json (차트+지도+공유색 통합).
해석 우선순위: 씬.themeOverride → 프로젝트 scenes.json.theme → ae_tokens 기본값.
chartgen·manifest·mapgen이 전부 resolve_theme를 경유한다(단일 지점).
"""
from __future__ import annotations

import json
from pathlib import Path

_DATA = Path(__file__).resolve().parents[1] / "data" / "artstyle"


def _catalog_dir() -> Path:
    return _DATA / "themes"


def _ae_tokens() -> dict:
    fp = _DATA / "ae_tokens.json"
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _default_theme() -> dict:
    """ae_tokens.json을 테마 형식으로 래핑한 기본 테마(하위호환)."""
    ae = _ae_tokens()
    ca = ae.get("chartagent") or {}
    mp = ae.get("map") or {}
    return {
        "id": "default", "label": "기본(ae_tokens)",
        "colors": ae.get("colors") or {},
        "chart": {"theme_set": ca.get("theme_set") or "dashboard_analytical",
                  "theme_overrides": ca.get("theme_overrides") or {},
                  "patternKind": ca.get("patternKind")},
        "map": {"tile": "bright", "overrides": [],
                "rasterFilter": "", "defaultTheme": mp.get("defaultTheme") or "warm_earth"},
    }


def list_themes() -> list[dict]:
    """카탈로그의 모든 테마 dict(파일명 정렬). 디렉토리 없으면 빈 리스트."""
    cd = _catalog_dir()
    if not cd.is_dir():
        return []
    out = []
    for p in sorted(cd.glob("*.json")):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            pass
    return out


def load_theme(theme_id: str) -> dict | None:
    """카탈로그 단건 로드 — 없거나 빈 id거나 JSON 오류면 None."""
    if not theme_id:
        return None
    p = _catalog_dir() / f"{theme_id}.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _project_theme_id(proj_dir: Path) -> str | None:
    # scenes.json 최상위 "theme" — scenes.set_project_theme(Task 3)가 이 키에 기록
    fp = proj_dir / "scenes.json"
    if not fp.is_file():
        return None
    try:
        return json.loads(fp.read_text(encoding="utf-8")).get("theme")
    except json.JSONDecodeError:
        return None


def resolve_theme(proj_dir: Path, scene: dict | None = None) -> dict:
    """우선순위 병합 → {id, label, colors, chart, map}.
    씬.themeOverride → 프로젝트.theme → ae_tokens 기본."""
    tid = None
    if scene and scene.get("themeOverride"):
        tid = scene["themeOverride"]
    if not tid:
        tid = _project_theme_id(proj_dir)
    return (tid and load_theme(tid)) or _default_theme()
