"""chartagent 어댑터 (v4-호환 입력 → v3 chart_task → chartagent CLI).

v3 `auto_kairos_v3/auto_agent/modules/chartagent_adapter.py` 의 누적 규칙을 함께 이식.
계약 1순위 진실 원본: `docs/external-contracts.md` chartagent 절.

규칙 이식 항목:
- CHART_VIZ_TYPES (8종)
- mood → theme_set 매핑
- baseTheme → theme_set 폴백
- 레거시 chartConfig.type → vizType 호환
- layout → vizType 자동 추론
- CHARTAGENT_ROOT 환경 변수(기본 ~/Projects/chartagent)
- chartagent CLI subprocess 호출(`chartagent run --task ... --out-dir ...`)

폴백: chartagent 미가용 또는 실패 시 단순 SVG(stdlib)로 대체.
"""
from __future__ import annotations
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

# chartagent가 인식하는 vizType (v3와 동일)
CHART_VIZ_TYPES: set[str] = {
    "bar_chart", "timeline", "line_chart", "pie_chart",
    "scatter_chart", "area_chart", "ranking_chart", "comparison_chart",
}

# v4 overlay.subtype → chartagent vizType 정규화
_SUBTYPE_TO_VIZ_TYPE: dict[str, str] = {
    "bar_chart": "bar_chart", "bar": "bar_chart",
    "line_chart": "line_chart", "line": "line_chart",
    "pie": "pie_chart", "donut": "pie_chart",
    "area": "area_chart",
    "scatter": "scatter_chart",
    "ranking": "ranking_chart",
    "comparison": "comparison_chart", "comparison_chart": "comparison_chart",
    "timeline": "timeline",
}

# mood → chartagent theme_set 매핑 (v3와 동일 + v4 mood 추가 매핑)
_MOOD_TO_THEME: dict[str, str] = {
    # v3 매핑
    "urgent": "broadcast_signal",
    "dramatic": "broadcast_signal",
    "informative": "dashboard_analytical",
    "contemplative": "editorial_outline",
    "somber": "editorial_outline",
    "suspense": "market_technical",
    "triumphant": "gallery_infographic",
    # v4 mood 추가 매핑(art_style 기준)
    "차분": "dashboard_analytical",
    "교양": "dashboard_analytical",
    "박력": "broadcast_signal",
    "시네마틱": "broadcast_signal",
    "분석적": "dashboard_analytical",
    "풍자": "editorial_outline",
}

# baseTheme 폴백
_BASE_THEME_FALLBACK: dict[str, str] = {
    "dark": "broadcast_signal",
    "light": "neutral_white",
}


def chartagent_root() -> Path:
    return Path(os.environ.get("CHARTAGENT_ROOT", Path.home() / "Projects" / "chartagent"))


def is_available() -> bool:
    src = chartagent_root() / "src"
    return src.exists() and (src / "chartagent" / "cli.py").exists()


def resolve_theme_set(mood: str | list[str] | None, base_theme: str | None = None) -> str:
    """v4 art_style.mood (str 또는 list) → chartagent theme_set 결정."""
    moods: list[str] = []
    if isinstance(mood, list):
        moods = mood
    elif isinstance(mood, str):
        moods = [mood]
    for m in moods:
        if m in _MOOD_TO_THEME:
            return _MOOD_TO_THEME[m]
    if base_theme and base_theme in _BASE_THEME_FALLBACK:
        return _BASE_THEME_FALLBACK[base_theme]
    return "dashboard_analytical"  # 보수 기본값


def overlay_to_chart_task(
    overlay: dict[str, Any],
    *,
    scene_context: dict[str, Any] | None = None,
    theme_set: str = "dashboard_analytical",
    theme_overrides: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """v4 content_overlay (data_viz) → chartagent chart_task dict.

    overlay 필수 필드: type='data_viz', subtype, items, values
    선택 필드: spec(title), value_unit, annotations, data_source
    """
    if overlay.get("type") != "data_viz":
        return None
    subtype = overlay.get("subtype")
    viz_type = _SUBTYPE_TO_VIZ_TYPE.get(subtype, subtype)
    if viz_type not in CHART_VIZ_TYPES:
        return None
    items = overlay.get("items") or []
    values = overlay.get("values") or []
    if not items or not values or len(items) != len(values):
        return None

    task: dict[str, Any] = {
        "vizType": viz_type,
        "title": overlay.get("spec") or overlay.get("title") or "",
        "items": items,
        "values": values,
        "value_unit": overlay.get("value_unit") or "",
        "annotations": overlay.get("annotations") or [],
        "theme_set": theme_set,
        "scene_context": scene_context or {},
    }
    if theme_overrides:
        task["theme_overrides"] = theme_overrides
    return task


def run(
    chart_task: dict[str, Any],
    out_dir: Path,
    *,
    timeout: int = 60,
) -> Path:
    """chartagent CLI 호출 → render.svg 경로 반환.

    사전 검증(items/values 정합)은 호출자가 overlay_to_chart_task 로 처리한 가정.
    실패 시 RuntimeError 또는 FileNotFoundError.
    """
    if not is_available():
        raise RuntimeError("chartagent unavailable (CHARTAGENT_ROOT not found)")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    task_path = out_dir / "chart_task.json"
    task_path.write_text(json.dumps(chart_task, ensure_ascii=False, indent=2), encoding="utf-8")

    chartagent_src = chartagent_root() / "src"
    env = {**os.environ}
    pythonpath = str(chartagent_src)
    if "PYTHONPATH" in env:
        pythonpath = f"{pythonpath}:{env['PYTHONPATH']}"
    env["PYTHONPATH"] = pythonpath

    runner_script = (
        "import sys;"
        f" sys.path.insert(0, r'{chartagent_src}');"
        " sys.argv = ['chartagent', 'run',"
        f" '--task', r'{task_path}',"
        f" '--out-dir', r'{out_dir}'];"
        " from chartagent.cli import main; main()"
    )
    result = subprocess.run(
        [sys.executable, "-c", runner_script],
        capture_output=True, text=True, env=env, timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"chartagent failed: {result.stderr.strip()}")

    svg_path = out_dir / "render.svg"
    if not svg_path.exists():
        raise FileNotFoundError(f"chartagent did not produce render.svg at {svg_path}")
    return svg_path


def render_overlay(
    overlay: dict[str, Any],
    out_dir: Path,
    *,
    mood: str | list[str] | None = None,
    base_theme: str | None = None,
    scene_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """편의 함수: overlay → chart_task → run → svg 경로.

    반환: {status: 'ok'|'fallback'|'error', svg_path, theme_set, error?}
    chartagent 미가용 시 fallback 경로(svg_path=None)로 반환 — 호출자가 폴백 결정.
    """
    theme_set = resolve_theme_set(mood, base_theme)
    task = overlay_to_chart_task(overlay, scene_context=scene_context, theme_set=theme_set)
    if not task:
        return {"status": "error", "error": "invalid overlay (missing/invalid fields)", "theme_set": theme_set}
    if not is_available():
        return {"status": "fallback", "svg_path": None, "theme_set": theme_set,
                "error": "chartagent unavailable, caller should produce fallback SVG"}
    try:
        svg = run(task, out_dir)
        return {"status": "ok", "svg_path": str(svg), "theme_set": theme_set}
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        return {"status": "fallback", "svg_path": None, "theme_set": theme_set, "error": str(e)}
