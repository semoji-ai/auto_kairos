"""프로젝트 건강 상태 — 얼마나 됐나 · 다음에 뭘 하나 · 뭐가 수상한가.

대시보드가 리서치와 원고를 다시 보여 주고 있었다. 그건 각 탭이 하는 일이고,
정작 「지금 어디까지 왔고 다음에 뭘 해야 하나」는 어디에도 없었다. 12편을
동시에 굴리면서 매번 파일을 세어 확인했다.

여기서 세는 것은 전부 **파일에 있는 사실**이다. 추측하지 않는다.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from auto_agent.paths import episode_label, get_package_dir, layer_sets


def _load(p: Path) -> Optional[dict]:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _selected_image(img_dir: Path, n: int) -> bool:
    from auto_agent.tools.image_assets import get_selected

    sel = get_selected(img_dir, n)
    return bool(sel and (img_dir / sel).exists())


def collect(project: dict) -> dict:
    """한 프로젝트의 상태를 모은다."""
    out_dir = Path(project.get("output_dir") or "")
    slug = project.get("slug") or ""
    ep = episode_label(slug)
    specs = _load(out_dir / "scene_specs.json") or {}
    scenes = specs.get("scenes") or []
    img_dir = out_dir / "images"
    audio_dir = out_dir / "audio"

    # ── 얼마나 됐나 ──────────────────────────────────────
    need_image = [s for s in scenes
                  if (s.get("imageAsset") or {}).get("source") in ("generate", "search")]
    have_image = [s for s in need_image
                  if _selected_image(img_dir, s.get("sceneNumber"))]
    have_audio = [s for s in scenes
                  if (audio_dir / f"{s.get('sceneId')}.mp3").exists()
                  or (audio_dir / f"scene_{s.get('sceneNumber'):03d}.mp3").exists()]
    have_layers = [s for s in scenes if layer_sets(slug, s.get("sceneNumber"))]
    subs = out_dir / "subtitles.json"
    finals = list(out_dir.glob("*_final.mp4"))

    root = get_package_dir().parent
    mode = _load(root / "_imggen" / f"{ep}_mode.json") if ep else None
    info_scenes = [s for s in (mode or {}).get("scenes", []) if s.get("mode") == "infographic"]
    info_assets_planned = sum(len(s.get("assets") or []) for s in info_scenes)
    info_dir = root / "_imggen" / f"{ep.lower()}_info" if ep else None
    info_made = len([p for p in info_dir.glob("*.png") if "_raw" not in p.name]) \
        if info_dir and info_dir.exists() else 0

    progress = [
        {"name": "씬", "done": len(scenes), "total": len(scenes)},
        {"name": "이미지", "done": len(have_image), "total": len(need_image)},
        {"name": "음성", "done": len(have_audio), "total": len(scenes)},
        {"name": "인포그래픽 에셋", "done": info_made, "total": info_assets_planned},
        {"name": "레이어 분리", "done": len(have_layers), "total": len(scenes)},
        {"name": "자막", "done": 1 if subs.exists() else 0, "total": 1},
        {"name": "완성본", "done": len(finals), "total": 1},
    ]

    # ── 다음에 뭘 하나 ───────────────────────────────────
    todos = []
    miss_img = [s["sceneNumber"] for s in need_image
                if not _selected_image(img_dir, s.get("sceneNumber"))]
    if miss_img:
        todos.append({"text": f"이미지가 없는 씬 {len(miss_img)}개", "scenes": miss_img[:20],
                      "hint": "스토리보드에서 씬을 골라 생성하거나 자료를 채웁니다"})
    dirty = [s["sceneNumber"] for s in scenes if s.get("narration_dirty")]
    if dirty:
        todos.append({"text": f"원고가 바뀌어 음성과 어긋난 씬 {len(dirty)}개", "scenes": dirty[:20],
                      "hint": "TTS를 다시 만들어야 합니다"})
    no_audio = [s["sceneNumber"] for s in scenes
                if not ((audio_dir / f"{s.get('sceneId')}.mp3").exists()
                        or (audio_dir / f"scene_{s.get('sceneNumber'):03d}.mp3").exists())]
    if no_audio:
        todos.append({"text": f"음성이 없는 씬 {len(no_audio)}개", "scenes": no_audio[:20],
                      "hint": "TTS 생성"})
    if info_scenes and info_made < info_assets_planned:
        todos.append({"text": f"인포그래픽 에셋 {info_assets_planned - info_made}개 남음",
                      "scenes": [], "hint": f"scripts/gen_info_assets.py {ep}"})
    if not subs.exists() and len(have_audio) == len(scenes) and scenes:
        todos.append({"text": "자막을 만들 차례입니다", "scenes": [],
                      "hint": "음성이 모두 있습니다"})
    if not finals and subs.exists():
        todos.append({"text": "렌더가 남았습니다", "scenes": [], "hint": ""})

    # ── 뭐가 수상한가 ────────────────────────────────────
    suspects = []
    # 자료를 쓰면서 왜 그 자료인지 적지 않은 씬 — 오용 76%가 여기 있었다
    ledger = _load(root / "_imggen" / f"{ep}_search_assets2.json") if ep else None
    rows = ledger if isinstance(ledger, list) else (ledger or {}).get("assets") or []
    blank = [r.get("n") for r in rows
             if r.get("found") and not (r.get("relevance") or "").strip()]
    if blank:
        suspects.append({"kind": "자료 근거 없음",
                         "text": f"쓰고 있는 자료 {len(blank)}건에 「왜 이 자료인가」가 비어 있습니다",
                         "scenes": [x for x in blank if x][:20]})
    # 인물이 나오는데 시트를 안 붙이고 그린 씬
    no_cast = [s["sceneNumber"] for s in scenes
               if (s.get("imageAsset") or {}).get("source") == "generate"
               and (s.get("characters") or s.get("people")) and not s.get("cast")]
    if no_cast:
        suspects.append({"kind": "시트 없이 그린 인물",
                         "text": f"인물이 나오는 씬 {len(no_cast)}개가 시트 없이 그려졌습니다",
                         "scenes": no_cast[:20]})
    # 층 계획은 섰는데 나누지 않은 씬
    planned_only = []
    if ep:
        base = root / "_imggen" / f"{ep.lower()}_anim"
        for d in sorted(base.glob("s*")) if base.exists() else []:
            if (d / "layer_plan.json").is_file() and not (d / "layers.json").is_file():
                planned_only.append(int(d.name[1:4]))
    if planned_only:
        suspects.append({"kind": "계획만 서 있음",
                         "text": f"층 계획을 세워 두고 나누지 않은 씬 {len(planned_only)}개",
                         "scenes": planned_only[:20]})

    # ── 평가 ────────────────────────────────────────────
    review = None
    score = _load(root / "_imggen" / f"{ep}_score.json") if ep else None
    if score:
        rows_s = score if isinstance(score, list) else score.get("scenes") or []
        keys = ("content", "style", "character", "period", "quality")
        avg = {}
        for k in keys:
            vals = [r[k] for r in rows_s if isinstance(r.get(k), (int, float))]
            if vals:
                avg[k] = round(sum(vals) / len(vals), 2)
        verdicts: dict = {}
        for r in rows_s:
            v = r.get("verdict")
            if v:
                verdicts[v] = verdicts.get(v, 0) + 1
        review = {"count": len(rows_s), "avg": avg, "verdicts": verdicts}

    return {"episode": ep, "progress": progress, "todos": todos,
            "suspects": suspects, "review": review}
