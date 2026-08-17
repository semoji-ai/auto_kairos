"""시드 테마 3종 생성 — chartagent theme_set + 지도 테마(v3 이식)를 통합 테마로 매핑.
멱등(이미 있으면 덮어씀). 사용: python -m scripts.seed_themes"""
from __future__ import annotations

import json
from pathlib import Path

# 지도 레이어 오버라이드 — cep/js/mapgen.js의 MAP_THEMES와 동일 값(단일 소스 시드)
_WARM_EARTH = [
    {"match": "background", "paint": {"background-color": "#F0E8DE"}},
    {"match": "water", "paint": {"fill-color": "#C8BAA0"}},
    {"match": "boundary*", "paint": {"line-color": "#8A6E48", "line-width": 1.6, "line-opacity": 0.9}},
    {"match": "road*", "paint": {"line-color": "#C8B498", "line-opacity": 0.7}},
]
_CLEAN_WHITE = [
    {"match": "background", "paint": {"background-color": "#FFFFFF"}},
    {"match": "water", "paint": {"fill-color": "#D6E6F5"}},
    {"match": "boundary*", "paint": {"line-color": "#A0AAB8", "line-width": 1.2, "line-opacity": 0.8}},
    {"match": "road*", "paint": {"line-color": "#D8DCE4", "line-opacity": 0.7}},
]
_MATTE_SLATE = [
    {"match": "background", "paint": {"background-color": "#1A1C22"}},
    {"match": "water", "paint": {"fill-color": "#0E1018"}},
    {"match": "boundary*", "paint": {"line-color": "#6A6E7C", "line-width": 1.4, "line-opacity": 0.8}},
    {"match": "road*", "paint": {"line-color": "#383C48", "line-opacity": 0.6}},
]

_THEMES = [
    {"id": "semoji", "label": "세모지", "source": "내장 시드",
     "colors": {"accentRgb": [74, 144, 217], "textRgb": [232, 234, 237],
                "mutedRgb": [154, 160, 166], "bgRgb": [35, 38, 43]},
     "chart": {"theme_set": "gallery_infographic", "theme_overrides": {"pattern_mode": "outline_plus_hatch"},
               "patternKind": "diagonal_hatch"},   # 한 방향 빗금(chartagent crosshatch 오버라이드)
     "map": {"tile": "bright", "overrides": _WARM_EARTH, "rasterFilter": "sepia(0.32) saturate(0.85) brightness(1.03)"}},
    {"id": "modern_clean", "label": "모던클린", "source": "내장 시드",
     "colors": {"accentRgb": [74, 144, 217], "textRgb": [33, 37, 41],
                "mutedRgb": [134, 142, 150], "bgRgb": [248, 249, 250]},
     "chart": {"theme_set": "neutral_white", "theme_overrides": {}},
     "map": {"tile": "bright", "overrides": _CLEAN_WHITE, "rasterFilter": ""}},
    {"id": "dark_broadcast", "label": "다크방송", "source": "내장 시드",
     "colors": {"accentRgb": [255, 80, 80], "textRgb": [240, 240, 240],
                "mutedRgb": [150, 150, 150], "bgRgb": [18, 18, 20]},
     "chart": {"theme_set": "broadcast_signal", "theme_overrides": {}},
     "map": {"tile": "dark", "overrides": _MATTE_SLATE, "rasterFilter": ""}},
]


def seed(catalog_dir: Path) -> None:
    catalog_dir.mkdir(parents=True, exist_ok=True)
    for t in _THEMES:
        (catalog_dir / f"{t['id']}.json").write_text(
            json.dumps(t, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    target = Path(__file__).resolve().parents[1] / "data" / "artstyle" / "themes"
    seed(target)
    print(f"시드 완료: {target}")
