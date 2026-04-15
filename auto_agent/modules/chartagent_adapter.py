"""
chartagent_adapter.py
---------------------
auto_kairos_v3 ↔ chartagent 연결을 위한 어댑터 3종:

1. scene_to_chart_task()      — scene_specs 씬 → chartagent chart_task dict
2. design_tokens_to_theme()   — auto_kairos design_tokens → chartagent theme_set 이름
3. inject_chart_svg()         — render.svg 경로 → scene_specs imageAsset 갱신

사용 예:
    from auto_agent.modules.chartagent_adapter import (
        scene_to_chart_task,
        design_tokens_to_theme,
        inject_chart_svg,
        CHART_VIZ_TYPES,
    )
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

# chartagent가 인식하는 vizType → goal 매핑
CHART_VIZ_TYPES: set[str] = {
    "bar_chart",
    "timeline",
    "line_chart",
    "pie_chart",
    "scatter_chart",
    "area_chart",
    "ranking_chart",
    "comparison_chart",
}

# mood → chartagent theme_set 매핑
_MOOD_TO_THEME: dict[str, str] = {
    "urgent":        "broadcast_signal",
    "dramatic":      "broadcast_signal",
    "informative":   "dashboard_analytical",
    "contemplative": "editorial_outline",
    "somber":        "editorial_outline",
    "suspense":      "market_technical",
    "triumphant":    "gallery_infographic",
}

# baseTheme → 기본 theme_set 매핑
_BASE_THEME_FALLBACK: dict[str, str] = {
    "dark":  "broadcast_signal",
    "light": "neutral_white",
}


# ---------------------------------------------------------------------------
# Adapter 1: scene_specs 씬 → chart_task dict
# ---------------------------------------------------------------------------

# chartConfig.type → vizType 하위 호환 매핑 (플랫 스키마 + 레거시 visualization 모두 지원)
_CHART_TYPE_TO_VIZ_TYPE: dict[str, str] = {
    "bar":        "bar_chart",
    "pie":        "pie_chart",
    "donut":      "pie_chart",
    "line":       "line_chart",
    "area":       "area_chart",
    "scatter":    "scatter_chart",
    "ranking":    "ranking_chart",
    "comparison": "comparison_chart",
}

# layout → vizType 자동 추론 (vizType/chartConfig 모두 없을 때 최후 fallback)
_LAYOUT_TO_VIZ_TYPE: dict[str, str] = {
    "bar":          "bar_chart",
    "pie":          "pie_chart",
    "line":         "line_chart",
    "rank_list":    "ranking_chart",
    "before_after": "comparison_chart",
    "timeline":     "timeline",
}


def _resolve_viz_type(scene: dict[str, Any]) -> str:
    """씬에서 vizType을 결정합니다. 우선순위: vizType > chartConfig.type > layout 추론."""
    # 1순위: 최상위 vizType (플랫 스키마 신규 필드)
    vt = scene.get("vizType", "")
    if vt in CHART_VIZ_TYPES:
        return vt

    # 2순위: visualization.vizType (레거시 중첩 스키마)
    viz = scene.get("visualization") or {}
    vt = viz.get("vizType", "")
    if vt in CHART_VIZ_TYPES:
        return vt

    # 3순위: chartConfig.type → vizType 변환
    chart_cfg = scene.get("chartConfig") or viz.get("chartConfig") or {}
    chart_type = str(chart_cfg.get("type") or "").lower()
    if chart_type and chart_type in _CHART_TYPE_TO_VIZ_TYPE:
        return _CHART_TYPE_TO_VIZ_TYPE[chart_type]

    # 4순위: layout → vizType 추론 (values가 있을 때만)
    layout = scene.get("layout") or viz.get("layout") or ""
    values = scene.get("values") or viz.get("values") or []
    if layout in _LAYOUT_TO_VIZ_TYPE and len(values) >= 2:
        return _LAYOUT_TO_VIZ_TYPE[layout]

    return ""


def scene_to_chart_task(
    scene: dict[str, Any],
    theme_set: str = "",
    theme_overrides: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """
    scene_specs의 씬 1개를 chartagent chart_task dict으로 변환합니다.

    차트가 없는 씬(vizType이 CHART_VIZ_TYPES에 없는 경우)은 None 반환.
    vizType은 scene.vizType > chartConfig.type > layout 순으로 자동 결정됩니다.

    Parameters
    ----------
    scene      : scene_specs.json의 씬 dict 1개
    theme_set  : chartagent theme_set 이름 (비어 있으면 mood에서 자동 결정)

    Returns
    -------
    chart_task dict (chartagent 입력 형식) or None
    """
    viz_type = _resolve_viz_type(scene)

    if viz_type not in CHART_VIZ_TYPES:
        return None

    viz = scene.get("visualization") or {}

    scene_num = scene.get("sceneNumber", 0)
    # 플랫 스키마(최상위) 우선, visualization 중첩 스키마 fallback
    title = scene.get("title") or viz.get("title") or ""
    items: list[Any] = scene.get("items") or viz.get("items") or []
    values: list[Any] = scene.get("values") or viz.get("values") or []
    unit: str = scene.get("unit") or viz.get("unit") or ""
    source: str = scene.get("source") or viz.get("source") or ""
    descriptions: list[str] = scene.get("descriptions") or viz.get("descriptions") or []
    mood: str = scene.get("mood") or (viz.get("creative") or {}).get("mood") or "informative"

    # dataset 구성
    dataset_items: list[dict[str, Any]] = []
    for i, label in enumerate(items):
        entry: dict[str, Any] = {"label": str(label)}
        if i < len(values):
            entry["value"] = values[i]
        if i < len(descriptions):
            entry["description"] = descriptions[i]
        dataset_items.append(entry)

    dataset: dict[str, Any] = {
        "title": title,
        "items": dataset_items,
    }
    if unit:
        dataset["unit"] = unit

    # vizType → chartagent goal 변환
    goal = _viz_type_to_goal(viz_type)

    # theme_set 결정
    resolved_theme = theme_set or _MOOD_TO_THEME.get(mood, "dashboard_analytical")

    # 시계열/순서가 의미있는 vizType은 원래 순서 유지
    _PRESERVE_ORDER_TYPES = {"timeline", "line_chart", "area_chart", "bar_chart"}
    constraints: dict[str, Any] = {}
    if viz_type in _PRESERVE_ORDER_TYPES:
        constraints["preserve_order"] = True

    chart_task: dict[str, Any] = {
        "task_id": f"scene-{scene_num:03d}",
        "request_origin": "auto_kairos_v3",
        "goal": goal,
        "question": title,
        "dataset": dataset,
        "theme_set": resolved_theme,
        "source_hints": [source] if source else [],
        "constraints": constraints,
        "context": {
            "scene_number": scene_num,
            "mood": mood,
            "viz_type": viz_type,
        },
    }

    if theme_overrides:
        chart_task["theme_overrides"] = theme_overrides

    return chart_task


def _viz_type_to_goal(viz_type: str) -> str:
    _MAP = {
        "bar_chart":        "show_ranking",
        "timeline":         "show_trend",
        "line_chart":       "show_trend",
        "area_chart":       "show_trend",
        "pie_chart":        "show_composition",
        "scatter_chart":    "show_relationship",
        "ranking_chart":    "show_ranking",
        "comparison_chart": "compare_values",
    }
    return _MAP.get(viz_type, "communicate_pattern")


# ---------------------------------------------------------------------------
# Adapter 2: design_tokens → chartagent theme_set 이름
# ---------------------------------------------------------------------------

def design_tokens_to_theme(design_tokens: dict[str, Any], mood: str = "informative") -> str:
    """
    auto_kairos artstyle의 design_tokens를 chartagent theme_set 이름으로 변환합니다.

    매핑 우선순위:
      1. design_tokens.chartagent.theme_set (명시적 계약 — 최우선)
      2. design_tokens.colors.accent 색상 계열 분석
      3. design_tokens.baseTheme (dark/light)
      4. mood 기반 fallback

    Parameters
    ----------
    design_tokens : artstyle JSON의 design_tokens 필드
    mood          : 씬 mood (fallback용)

    Returns
    -------
    chartagent theme_set 이름 문자열
    """
    if not design_tokens:
        return _MOOD_TO_THEME.get(mood, "dashboard_analytical")

    # 1순위: 명시적 계약
    explicit = str((design_tokens.get("chartagent") or {}).get("theme_set") or "").strip()
    if explicit:
        return explicit

    base_theme = str(design_tokens.get("baseTheme") or "").lower()

    # mood 색상 우선
    moods_data = design_tokens.get("moods") or {}
    mood_colors = moods_data.get(mood) or {}
    accent_hex = mood_colors.get("accent") or (design_tokens.get("colors") or {}).get("accent") or ""

    if accent_hex:
        theme = _accent_to_theme(accent_hex, base_theme)
        if theme:
            return theme

    # baseTheme fallback
    if base_theme in _BASE_THEME_FALLBACK:
        return _BASE_THEME_FALLBACK[base_theme]

    return _MOOD_TO_THEME.get(mood, "dashboard_analytical")


def _accent_to_theme(hex_color: str, base_theme: str) -> str:
    """accent 색상 hex → chartagent theme_set 이름"""
    hex_color = hex_color.lstrip("#").lower()
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
    except (ValueError, IndexError):
        return ""

    # 빨간/주황 계열 → broadcast_signal (고대비, 긴박)
    if r > 180 and g < 120 and b < 120:
        return "broadcast_signal"

    # 노란/앰버 계열 → gallery_infographic 또는 editorial_outline
    if r > 200 and g > 140 and b < 80:
        return "editorial_outline" if base_theme == "light" else "broadcast_signal"

    # 초록 계열 → market_technical
    if g > 160 and r < 100:
        return "market_technical"

    # 파란 계열 → neutral_white 또는 dashboard_analytical
    if b > 160 and r < 100:
        return "dashboard_analytical" if base_theme == "dark" else "neutral_white"

    return ""


# ---------------------------------------------------------------------------
# Adapter 3: render.svg → scene_specs imageAsset 주입
# ---------------------------------------------------------------------------

def inject_chart_svg(
    scene: dict[str, Any],
    svg_path: Path,
    image_assets: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    chartagent가 생성한 render.svg를 scene_specs 씬의 imageAsset에 주입합니다.

    imageAsset.source를 'chart'로 변경하고, chartSvgPath를 설정합니다.
    scene_specs.json의 해당 씬 dict을 수정하여 반환합니다 (원본 수정 없음).

    Parameters
    ----------
    scene        : scene_specs.json 씬 dict (수정 대상)
    svg_path     : chartagent 출력 render.svg 절대 경로
    image_assets : image_assets.json dict (있을 경우 chart 항목 추가)

    Returns
    -------
    수정된 씬 dict (깊은 복사본)
    """
    import copy
    updated = copy.deepcopy(scene)

    svg_path = Path(svg_path)
    if not svg_path.exists():
        raise FileNotFoundError(f"render.svg 없음: {svg_path}")

    scene_num = updated.get("sceneNumber", 0)

    # imageAsset 갱신
    image_asset = updated.get("imageAsset") or {}
    image_asset["source"] = "chart"
    image_asset["chartSvgPath"] = str(svg_path)
    image_asset["placement"] = image_asset.get("placement") or "fullscreen"
    updated["imageAsset"] = image_asset

    # image_assets.json에 차트 항목 추가 (있을 경우)
    if image_assets is not None:
        key = f"scene_{scene_num:03d}"
        image_assets[key] = {
            "type": "chart",
            "svg_path": str(svg_path),
            "selected": str(svg_path),
            "source": "chartagent",
        }

    return updated


# ---------------------------------------------------------------------------
# 편의 함수: 프로젝트의 chart vizType 씬 전체 처리
# ---------------------------------------------------------------------------

def run_chartagent_for_scene(
    scene: dict[str, Any],
    out_dir: Path,
    design_tokens: dict[str, Any] | None = None,
) -> Path | None:
    """
    씬 1개에 대해 chartagent CLI를 실행하고 render.svg 경로를 반환합니다.

    Parameters
    ----------
    scene         : scene_specs.json 씬 dict
    out_dir       : 출력 디렉토리 (프로젝트 output/{slug}/charts/)
    design_tokens : artstyle design_tokens (theme 결정용)

    Returns
    -------
    render.svg Path or None (차트 씬 아닌 경우)
    """
    viz_type = _resolve_viz_type(scene)
    if viz_type not in CHART_VIZ_TYPES:
        return None

    mood = scene.get("mood") or "informative"
    dt = design_tokens or {}
    theme_set = design_tokens_to_theme(dt, mood)
    theme_overrides = (dt.get("chartagent") or {}).get("theme_overrides") or None

    chart_task = scene_to_chart_task(scene, theme_set=theme_set, theme_overrides=theme_overrides)
    if not chart_task:
        return None

    scene_num = scene.get("sceneNumber", 0)
    scene_out_dir = Path(out_dir) / f"scene_{scene_num:03d}"
    scene_out_dir.mkdir(parents=True, exist_ok=True)

    task_path = scene_out_dir / "chart_task.json"
    task_path.write_text(json.dumps(chart_task, ensure_ascii=False, indent=2), encoding="utf-8")

    import os
    chartagent_src = Path(os.environ.get("CHARTAGENT_ROOT", Path.home() / "Projects" / "chartagent")) / "src"
    env = {**os.environ}
    pythonpath = str(chartagent_src)
    if "PYTHONPATH" in env:
        pythonpath = f"{pythonpath}:{env['PYTHONPATH']}"
    env["PYTHONPATH"] = pythonpath

    # chartagent CLI를 현재 Python으로 직접 실행 (python3.12 하드코딩 제거)
    import sys as _sys
    runner_script = (
        "import sys;"
        f" sys.path.insert(0, r'{chartagent_src}');"
        " sys.argv = ['chartagent', 'run',"
        f" '--task', r'{task_path}',"
        f" '--out-dir', r'{scene_out_dir}'];"
        " from chartagent.cli import main; main()"
    )
    result = subprocess.run(
        [_sys.executable, "-c", runner_script],
        capture_output=True,
        text=True,
        env=env,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"chartagent 실행 실패 (씬 {scene_num}):\n{result.stderr}"
        )

    svg_path = scene_out_dir / "render.svg"
    if not svg_path.exists():
        raise FileNotFoundError(f"chartagent 출력 render.svg 없음: {svg_path}")

    return svg_path


# ---------------------------------------------------------------------------
# Adapter 4: chart_spec.json → design_tokens (스타일 명세서 추출)
# ---------------------------------------------------------------------------

def extract_theme_tokens(chart_spec_path: Path) -> dict[str, Any]:
    """
    chartagent가 생성한 chart_spec.json에서 디자인 토큰을 추출하여
    auto_kairos design_tokens 형식으로 반환합니다.

    chartagent는 렌더링을 담당하지 않고 스타일 명세서 역할만 합니다.
    추출된 토큰은 기존 Remotion viz 컴포넌트에 주입되어 chartagent 스타일이
    애니메이션 차트에 적용됩니다.

    Parameters
    ----------
    chart_spec_path : chartagent 출력 chart_spec.json 경로

    Returns
    -------
    auto_kairos design_tokens 형식 dict:
        {
          "baseTheme": "dark" | "light",
          "colors": { "accent": "#...", "accentRgb": "r,g,b", ... },
          "fonts": { "title": "...", "body": "...", "mono": "..." },
          "palette": { "bg": "#...", "panel": "#...", ... },
          "chartagent": {
            "theme_set": "broadcast_signal",
            "layout_tokens": {...},
            "motif_tokens": {...},
            "component_tokens": {...},
          }
        }
    """
    chart_spec_path = Path(chart_spec_path)
    if not chart_spec_path.exists():
        raise FileNotFoundError(f"chart_spec.json 없음: {chart_spec_path}")

    spec = json.loads(chart_spec_path.read_text(encoding="utf-8"))
    style_spec = spec.get("style_spec") or {}
    theme_tokens = style_spec.get("theme_tokens") or {}

    # bg 밝기로 baseTheme 결정
    bg_hex = theme_tokens.get("bg", "#000000")
    base_theme = _hex_is_dark(bg_hex)

    # accent RGB 분해
    accent_hex = theme_tokens.get("accent", "#3B82F6")
    accent_rgb = _hex_to_rgb_str(accent_hex)

    # auto_kairos design_tokens 형식으로 매핑
    design_tokens: dict[str, Any] = {
        "baseTheme": "dark" if base_theme else "light",
        "colors": {
            "accent": accent_hex,
            "accentRgb": accent_rgb,
            "accentBg": f"rgba({accent_rgb},0.08)",
            "accentBorder": f"rgba({accent_rgb},0.3)",
            "accentSoft": f"rgba({accent_rgb},0.15)",
            "cardBg": f"rgba({accent_rgb},0.06)",
            "cardBorder": f"rgba({accent_rgb},0.25)",
            "accentAlt": theme_tokens.get("accent_alt", ""),
            "positive": theme_tokens.get("positive", "#4ade80"),
            "negative": theme_tokens.get("negative", "#fb7185"),
            "neutral": theme_tokens.get("neutral", "#94a3b8"),
            "series": theme_tokens.get("series", []),
        },
        "fonts": {
            "title": theme_tokens.get("font_title", ""),
            "body": theme_tokens.get("font_body", ""),
            "mono": theme_tokens.get("font_mono", ""),
        },
        "fontSizes": {
            "title": theme_tokens.get("title_size", 28),
            "subtitle": theme_tokens.get("subtitle_size", 18),
            "body": theme_tokens.get("body_size", 16),
            "tick": theme_tokens.get("tick_size", 14),
            "source": theme_tokens.get("source_size", 14),
        },
        "palette": {
            "bg": theme_tokens.get("bg", ""),
            "panel": theme_tokens.get("panel", ""),
            "panelAlt": theme_tokens.get("panel_alt", ""),
            "plotBg": theme_tokens.get("plot_bg", ""),
            "textPrimary": theme_tokens.get("text_primary", ""),
            "textSecondary": theme_tokens.get("text_secondary", ""),
            "textMuted": theme_tokens.get("text_muted", ""),
            "grid": theme_tokens.get("grid", ""),
            "gridStrong": theme_tokens.get("grid_strong", ""),
            "track": theme_tokens.get("track", ""),
            "annotationFill": theme_tokens.get("annotation_fill", ""),
            "annotationStroke": theme_tokens.get("annotation_stroke", ""),
            "cardFills": theme_tokens.get("card_fills", []),
        },
        "radius": {
            "card": theme_tokens.get("radius_card", 14),
            "chip": theme_tokens.get("radius_chip", 8),
        },
        # chartagent 전용 메타데이터 (Remotion viz 컴포넌트에서 필요 시 참조)
        "chartagent": {
            "theme_set": style_spec.get("theme_set", ""),
            "theme_name": style_spec.get("theme_name", ""),
            "visual_mode": style_spec.get("visual_mode", ""),
            "tone": style_spec.get("tone", ""),
            "layout_tokens": style_spec.get("layout_tokens") or {},
            "motif_tokens": style_spec.get("motif_tokens") or {},
            "component_tokens": style_spec.get("component_tokens") or {},
        },
    }

    return design_tokens


def merge_chartagent_into_design_tokens(
    base_tokens: dict[str, Any],
    chartagent_tokens: dict[str, Any],
    mood: str = "informative",
) -> dict[str, Any]:
    """
    기존 artstyle design_tokens에 chartagent 추출 토큰을 병합합니다.

    병합 전략:
    - chartagent accent/palette가 기존 tokens를 덮어씁니다
    - moods 매핑은 chartagent accent를 해당 mood에 주입합니다
    - chartagent 메타데이터는 별도 키로 보존합니다

    Parameters
    ----------
    base_tokens       : 기존 artstyle design_tokens dict (또는 {})
    chartagent_tokens : extract_theme_tokens() 반환값
    mood              : 현재 씬 mood (moods 매핑 갱신용)

    Returns
    -------
    병합된 design_tokens dict (원본 수정 없음)
    """
    import copy
    merged = copy.deepcopy(base_tokens)

    # baseTheme 덮어쓰기
    merged["baseTheme"] = chartagent_tokens.get("baseTheme", merged.get("baseTheme", "dark"))

    # colors 병합 (accent 계열)
    merged_colors = dict(merged.get("colors") or {})
    merged_colors.update(chartagent_tokens.get("colors") or {})
    merged["colors"] = merged_colors

    # fonts 추가
    merged["fonts"] = chartagent_tokens.get("fonts") or {}

    # palette 추가
    merged["palette"] = chartagent_tokens.get("palette") or {}

    # radius 추가
    merged["radius"] = chartagent_tokens.get("radius") or {}

    # chartagent 메타데이터 보존
    merged["chartagent"] = chartagent_tokens.get("chartagent") or {}

    # moods 갱신 — 현재 mood에 chartagent accent 주입
    accent = (chartagent_tokens.get("colors") or {}).get("accent", "")
    accent_rgb = (chartagent_tokens.get("colors") or {}).get("accentRgb", "")
    if accent and mood:
        merged_moods = dict(merged.get("moods") or {})
        mood_entry = dict(merged_moods.get(mood) or {})
        mood_entry["accent"] = accent
        if accent_rgb:
            mood_entry["accentRgb"] = accent_rgb
        merged_moods[mood] = mood_entry
        merged["moods"] = merged_moods

    return merged


def save_chartagent_design_tokens(
    chart_spec_path: Path,
    out_path: Path,
    base_tokens: dict[str, Any] | None = None,
    mood: str = "informative",
) -> dict[str, Any]:
    """
    chart_spec.json → design_tokens 추출 → 파일 저장까지 한 번에 수행.

    Parameters
    ----------
    chart_spec_path : chartagent 출력 chart_spec.json 경로
    out_path        : 저장할 JSON 파일 경로 (예: project_dir/chartagent_style.json)
    base_tokens     : 기존 artstyle design_tokens (없으면 {} 사용)
    mood            : 씬 mood

    Returns
    -------
    저장된 merged design_tokens dict
    """
    extracted = extract_theme_tokens(chart_spec_path)
    merged = merge_chartagent_into_design_tokens(base_tokens or {}, extracted, mood=mood)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")

    return merged


def save_project_chartagent_style(
    charts_dir: Path,
    base_tokens: dict[str, Any] | None = None,
) -> Path | None:
    """
    프로젝트 charts/ 디렉토리의 모든 chart_spec.json을 스캔하여
    가장 많이 사용된 theme_set의 토큰을 프로젝트 레벨 chartagent_style.json으로 저장합니다.

    build_manifest.py가 이 파일을 읽어 manifest.meta.designPreset에 주입합니다.

    Parameters
    ----------
    charts_dir  : 프로젝트 charts/ 디렉토리 (scene_*/chart_spec.json이 있는 곳)
    base_tokens : 기존 artstyle design_tokens (없으면 {} 사용)

    Returns
    -------
    저장된 chartagent_style.json 경로 or None (chart_spec.json 없는 경우)
    """
    charts_dir = Path(charts_dir)
    spec_files = sorted(charts_dir.glob("scene_*/chart_spec.json"))
    if not spec_files:
        return None

    # theme_set 빈도 집계
    from collections import Counter
    theme_counts: Counter = Counter()
    specs_by_theme: dict[str, Path] = {}
    for spec_path in spec_files:
        try:
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            theme_set = (spec.get("style_spec") or {}).get("theme_set", "")
            if theme_set:
                theme_counts[theme_set] += 1
                specs_by_theme.setdefault(theme_set, spec_path)
        except Exception:
            continue

    if not theme_counts:
        return None

    # 가장 많이 사용된 theme_set의 chart_spec을 대표로 사용
    dominant_theme = theme_counts.most_common(1)[0][0]
    representative_spec = specs_by_theme[dominant_theme]

    out_path = charts_dir / "chartagent_style.json"
    save_chartagent_design_tokens(representative_spec, out_path, base_tokens=base_tokens)
    return out_path


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------

def _hex_is_dark(hex_color: str) -> bool:
    """hex 색상이 어두운지 (luminance < 0.5) 판별."""
    hex_color = hex_color.lstrip("#").lower()
    try:
        r = int(hex_color[0:2], 16) / 255
        g = int(hex_color[2:4], 16) / 255
        b = int(hex_color[4:6], 16) / 255
        luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
        return luminance < 0.5
    except (ValueError, IndexError):
        return True


def _hex_to_rgb_str(hex_color: str) -> str:
    """#RRGGBB → 'R,G,B' 문자열."""
    hex_color = hex_color.lstrip("#").lower()
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"{r},{g},{b}"
    except (ValueError, IndexError):
        return "0,0,0"
