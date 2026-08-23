"""레이어 분리 · 벡터화 · 자세 수정 — 대시보드에서.

셋 다 순수 API 호출이라 **애프터이펙트와 상관이 없다.** 그런데 어도비 패널에만
있어서 대시보드만 쓰면 못 했다. 구현은 `adobe/backend/` 에 있으므로 다시 쓰지
않고 그대로 불러 쓴다 — 두 벌을 두면 한쪽만 고치게 된다. 저쪽에서 이미 겪어
고친 것이 많다(이름 대조, 못 뗀 요소 기록, 극단적 가로세로 비 거부).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()

_ADOBE = Path(__file__).resolve().parents[2] / "adobe"


def _backend():
    if not (_ADOBE / "backend").is_dir():
        return None
    if str(_ADOBE) not in sys.path:
        sys.path.insert(0, str(_ADOBE))
    try:
        from backend import imagegen, vectorize, layer_edit, scenes   # noqa: WPS433
        return imagegen, vectorize, layer_edit, scenes
    except Exception:
        return None


def _project_dir(slug: str) -> Path | None:
    from auto_agent.paths import get_workspace_dir
    root = get_workspace_dir() / "output"
    if (root / slug).is_dir():
        return root / slug
    for d in root.iterdir():
        if d.is_dir() and (d.name == slug or d.name.endswith("_" + slug)):
            return d
    return None


def _sid(proj: Path, scene_num) -> str | None:
    from auto_agent.dashboard.helpers import adobe_scene_ids
    return adobe_scene_ids(str(proj)).get(float(scene_num))


def _scene(proj: Path, scene_num) -> dict:
    try:
        d = json.loads((proj / "scenes.json").read_text(encoding="utf-8"))
        rows = d.get("scenes") if isinstance(d, dict) else d
        for s in rows or []:
            if float(s.get("sceneNumber")) == float(scene_num):
                return s
    except Exception:
        pass
    return {}


@router.post("/api/layers/analyze")
async def layers_analyze(request: Request):
    """이 씬을 어떤 요소로 가를지 코덱스에게 묻는다. 씨드림 프롬프트도 함께 낸다."""
    mod = _backend()
    if not mod:
        return JSONResponse({"error": "adobe/backend 를 찾을 수 없습니다"}, status_code=503)
    imagegen, _vec, _le, _sc = mod
    from backend import fal_api, vault
    b = await request.json()
    proj = _project_dir(b.get("slug") or "")
    if not proj:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)
    s = _scene(proj, b.get("sceneNumber"))
    img = s.get("imageRef")
    if not img or not (proj / img).is_file():
        return JSONResponse({"error": "씬 이미지가 없습니다"}, status_code=422)
    res = imagegen.analyze_scene_layers(
        proj, str(proj / img),
        narration=s.get("narration", "") or "",
        context=f"제목: {s.get('title','')}",
        image_prompt=s.get("image_prompt", "") or "",
        briefing=vault.read_context(proj))
    els = res.get("elements", [])
    names = [(e.get("name_en") or "").strip() for e in els]
    return {"elements": els, "dropped": res.get("dropped", []),
            "error": res.get("error"),
            "prompt": fal_api.build_layerize_prompt([n for n in names if n])}


@router.post("/api/layers/split")
async def layers_split(request: Request):
    """요소를 실제로 떼어 낸다(fal 씨드림). 기존 레이어는 지우지 않는다."""
    mod = _backend()
    if not mod:
        return JSONResponse({"error": "adobe/backend 를 찾을 수 없습니다"}, status_code=503)
    imagegen, _vec, _le, _sc = mod
    b = await request.json()
    proj = _project_dir(b.get("slug") or "")
    if not proj:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)
    sid = _sid(proj, b.get("sceneNumber"))
    s = _scene(proj, b.get("sceneNumber"))
    img = s.get("imageRef")
    if not (sid and img and (proj / img).is_file()):
        return JSONResponse({"error": "씬 이미지 또는 sceneId 가 없습니다"}, status_code=422)
    els = b.get("elements") or []
    if not els:
        return JSONResponse({"error": "elements 필요"}, status_code=400)
    try:
        res = imagegen.split_scene_to_elements(
            proj, str(proj / img), sid, els, prompt=(b.get("prompt") or "").strip() or None)
    except Exception as e:
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=422)
    return {"ok": True, **res}


@router.post("/api/layers/vectorize")
async def layers_vectorize(request: Request):
    """레이어를 SVG 로. 이미 있으면 건너뛴다."""
    mod = _backend()
    if not mod:
        return JSONResponse({"error": "adobe/backend 를 찾을 수 없습니다"}, status_code=503)
    _ig, vectorize, _le, _sc = mod
    b = await request.json()
    proj = _project_dir(b.get("slug") or "")
    if not proj:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)
    sid = _sid(proj, b.get("sceneNumber"))
    if not sid:
        return JSONResponse({"error": "sceneId 를 찾지 못했습니다"}, status_code=422)
    L = proj / "layers"
    stems = b.get("stems") or [f.stem for f in sorted(L.glob(f"{sid}__*.png"))]
    res = vectorize.vectorize_layers(proj, sid, stems, force=bool(b.get("force")))
    return {"ok": True, **res}


@router.post("/api/layers/edit")
async def layers_edit(request: Request):
    """레이어 한 장만 고친다 — 자세·표정(씨드림 5.0 Pro). 새 판본으로 쌓는다."""
    mod = _backend()
    if not mod:
        return JSONResponse({"error": "adobe/backend 를 찾을 수 없습니다"}, status_code=503)
    _ig, _vec, layer_edit, _sc = mod
    b = await request.json()
    proj = _project_dir(b.get("slug") or "")
    if not proj:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)
    rel = (b.get("layer") or "").strip()
    if not rel:
        return JSONResponse({"error": "layer 필요"}, status_code=400)
    res = layer_edit.edit_layer(proj, rel, b.get("instruction") or "",
                                keep_frame=b.get("keep_frame", True))
    return JSONResponse(res, status_code=200 if res.get("status") == "completed" else 422)
