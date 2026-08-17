"""chartagent 연동 — 차트 디자인 명세서(chart_spec.json)를 받아 AE 친화 토큰으로 변환.

v3 철학 그대로: 색은 artstyle(ae_tokens)이 소유, chartagent는 패턴/모티프/레이아웃만 명세.
chartagent는 의존성 없는 결정적 CLI(LLM 미사용)라 subprocess로 직접 호출한다.

흐름: AE 씬(chart 데이터) → chart_task.json → chartagent run → chart_spec.json
      → motif/layout 토큰 추출 → {이미지 없이} chart_{sid}.spec.json 사이드카
      → manifest가 chartSpec으로 전달 → jsx bar 레이아웃이 가이드선/해칭/외곽선 반영.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from backend import themes

# bar 레이아웃 → chartagent goal (v3 _viz_type_to_goal 이식, 현재 AE는 bar만)
_GOAL = {"bar": "show_ranking", "line_chart": "show_trend", "pie": "show_composition"}


def _chartagent_src() -> Path | None:
    """chartagent/src 경로 — CHARTAGENT_ROOT env 또는 ~/Projects/chartagent."""
    root = Path(os.environ.get("CHARTAGENT_ROOT", Path.home() / "Projects" / "chartagent"))
    src = root / "src"
    return src if (src / "chartagent" / "cli.py").is_file() else None


def available() -> bool:
    return _chartagent_src() is not None


def build_chart_task(scene: dict, theme_set: str, theme_overrides: dict | None) -> dict | None:
    """AE 씬(chart={labels,values,unit}, headline) → chartagent chart_task dict.
    chart 데이터 없으면 None."""
    chart = scene.get("chart") or {}
    labels = chart.get("labels") or []
    values = chart.get("values") or []
    if not labels or not values:
        return None
    title = scene.get("headline") or scene.get("title") or ""
    items = [{"label": str(labels[i]), "value": values[i]}
             for i in range(min(len(labels), len(values)))]
    dataset = {"title": title, "items": items}
    if chart.get("unit"):
        dataset["unit"] = chart["unit"]
    task = {
        "task_id": f"scene-{scene.get('sceneNumber', 0):03d}",
        "request_origin": "auto_kairos_adobe",
        "goal": _GOAL.get(scene.get("layout") or "bar", "show_ranking"),
        "question": title,
        "dataset": dataset,
        "theme_set": theme_set or "dashboard_analytical",
        "source_hints": [],
        "constraints": {"preserve_order": True},
        "context": {"scene_number": scene.get("sceneNumber", 0), "layout": scene.get("layout")},
    }
    if theme_overrides:
        task["theme_overrides"] = theme_overrides
    return task


def _run_cli(task_path: Path, out_dir: Path) -> Path:
    """chartagent run 실행 → chart_spec.json 경로. 실패 시 예외."""
    src = _chartagent_src()
    if not src:
        raise RuntimeError("chartagent 미설치 — CHARTAGENT_ROOT 환경변수 확인")
    script = (
        "import sys; sys.path.insert(0, r'%s');"
        " sys.argv=['chartagent','run','--task',r'%s','--out-dir',r'%s'];"
        " from chartagent.cli import main; main()"
    ) % (src, task_path, out_dir)
    r = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"chartagent 실행 실패:\n{r.stderr[-800:]}")
    spec = out_dir / "chart_spec.json"
    if not spec.is_file():
        raise FileNotFoundError(f"chart_spec.json 없음: {spec}")
    return spec


def extract_ae_tokens(chart_spec: dict) -> dict:
    """chart_spec.style_spec → AE jsx가 쓰는 차트 토큰만 추림(색 제외 — artstyle 소유)."""
    ss = chart_spec.get("style_spec") or {}
    motif = ss.get("motif_tokens") or {}
    layout = ss.get("layout_tokens") or {}
    return {
        "theme_set": ss.get("theme_set"),
        "visual_mode": ss.get("visual_mode"),
        # 가이드선(기준선)
        "guideLineCount": motif.get("guide_line_count", 0),
        "guideDash": motif.get("guide_dasharray"),
        "guideOpacity": motif.get("guide_opacity", 0.5),
        "guideStrokeWidth": motif.get("guide_stroke_width", 1),
        # 축/막대
        "axisStrokeWidth": motif.get("axis_stroke_width", 2),
        "barRadius": motif.get("bar_radius", 0),
        # 패턴(해칭) — 막대 채움 스타일
        "patternKind": motif.get("pattern_kind_default"),
        "patternSpacing": motif.get("pattern_spacing", 16),
        "patternOpacity": motif.get("pattern_opacity", 0.5),
        "patternStrokeWidth": motif.get("pattern_stroke_width", 1.2),
        "outlineWidth": motif.get("patterned_outline_width") or motif.get("outline_only_width") or 0,
        # 레이아웃 여백(1920×1080 기준 — jsx가 S 배율 적용)
        "plotLeft": layout.get("plot_left", 80),
        "plotRight": layout.get("plot_right", 40),
        "plotBottom": layout.get("plot_bottom", 90),
    }


def gen_chart_spec(proj_dir: Path, scene: dict) -> dict:
    """씬 1개에 대해 chartagent 명세서 생성 → AE 토큰 추출 → chart_{sid}.spec.json 저장.
    테마는 resolve_theme(proj_dir, scene)["chart"]에서 결정.
    반환 {ok, tokens} 또는 {error}."""
    sid = scene.get("sceneId")
    if not sid:
        return {"error": "sceneId 없음"}
    cfg = (themes.resolve_theme(proj_dir, scene).get("chart")) or {}
    theme_set = cfg.get("theme_set") or "dashboard_analytical"
    theme_overrides = cfg.get("theme_overrides")
    task = build_chart_task(scene, theme_set, theme_overrides)
    if not task:
        return {"error": "chart 데이터(labels/values) 없음"}
    charts_dir = proj_dir / "charts" / sid
    charts_dir.mkdir(parents=True, exist_ok=True)
    task_path = charts_dir / "chart_task.json"
    task_path.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
    spec_path = _run_cli(task_path, charts_dir)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    tokens = extract_ae_tokens(spec)
    # 테마가 patternKind를 명시하면 chartagent 결과를 오버라이드(예: 세모지=한 방향 diagonal_hatch).
    # chartagent의 패턴은 style_combo가 결정해 직접 못 고르므로, 테마에서 강제 선택.
    if cfg.get("patternKind"):
        tokens["patternKind"] = cfg["patternKind"]
    # 씬별 사이드카(무삭제·덮어쓰기) — manifest가 chartSpec으로 읽음
    (proj_dir / f"chart_{sid}.spec.json").write_text(
        json.dumps(tokens, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "tokens": tokens, "theme_set": tokens.get("theme_set")}
