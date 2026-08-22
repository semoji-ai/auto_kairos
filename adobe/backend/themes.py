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


# 프로젝트 테마 캐시 — (경로 → (mtime_ns, 크기, 값))
#
# `resolve_theme` 은 **씬마다** 불린다. 그때마다 `scenes.json` 을 통째로
# 파싱하고 있었다. 디아지오편은 그 파일이 1MB 남짓에 142씬이라 시트를 한 번
# 여는 데 **143번 파싱** — 0.7초가 여기서 나갔다. 후보를 하나 바꿀 때마다
# `refreshRow` 가 `/api/scenes` 를 다시 부르므로 그 값이 그대로 체감된다.
#
# 파일이 바뀌면(mtime·크기) 저절로 무효가 되므로 손으로 비울 일이 없다.
_THEME_ID_CACHE: dict = {}


def _project_theme_id(proj_dir: Path) -> str | None:
    # scenes.json 최상위 "theme" — scenes.set_project_theme(Task 3)가 이 키에 기록
    fp = proj_dir / "scenes.json"
    try:
        st = fp.stat()
    except OSError:
        return None
    key = str(fp)
    hit = _THEME_ID_CACHE.get(key)
    if hit and hit[0] == st.st_mtime_ns and hit[1] == st.st_size:
        return hit[2]
    try:
        val = json.loads(fp.read_text(encoding="utf-8")).get("theme")
    except json.JSONDecodeError:
        return None
    _THEME_ID_CACHE[key] = (st.st_mtime_ns, st.st_size, val)
    return val


def resolve_theme(proj_dir: Path, scene: dict | None = None) -> dict:
    """우선순위 병합 → {id, label, colors, chart, map}.
    씬.themeOverride → 프로젝트.theme → ae_tokens 기본."""
    tid = None
    if scene and scene.get("themeOverride"):
        tid = scene["themeOverride"]
    if not tid:
        tid = _project_theme_id(proj_dir)
    return (tid and load_theme(tid)) or _default_theme()
