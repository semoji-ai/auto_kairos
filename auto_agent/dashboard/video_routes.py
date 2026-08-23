"""씬 비디오 생성 — 대시보드에서. 힉스필드 CLI 연동.

**애프터이펙트와 아무 상관이 없다.** 그런데 지금까지 어도비 패널에만 있어서,
대시보드만 쓰는 사람은 비디오를 만들 수 없었다. 구현은 이미 `adobe/backend/`
에 있으므로 **다시 쓰지 않고 그대로 불러 쓴다** — 두 벌을 두면 한쪽만 고치는
일이 생긴다(잔액 부족 재시도, 업로드 UUID, 결과 URL 고르기 같은 것을 저쪽에서
이미 겪어 고쳤다).

씬 길이 + 1초를 기본으로 잡는다(`docs/rules/scene-video-rules.md`).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()

_ADOBE = Path(__file__).resolve().parents[2] / "adobe"


def _backend():
    """`adobe/backend` 를 불러온다. 없으면 None — 기능만 빠지고 대시보드는 산다."""
    if not (_ADOBE / "backend").is_dir():
        return None
    if str(_ADOBE) not in sys.path:
        sys.path.insert(0, str(_ADOBE))
    try:
        from backend import video, hf_accounts        # noqa: WPS433
        return video, hf_accounts
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


def _scene_seconds(proj: Path, scene_num) -> int:
    """씬 길이 + 1초, 정수로 올림. 상한 15초(힉스필드 제한)."""
    dur = 5.0
    try:
        specs = json.loads((proj / "scene_specs.json").read_text(encoding="utf-8"))
        rows = specs.get("scenes") if isinstance(specs, dict) else specs
        for s in rows or []:
            if float(s.get("sceneNumber")) == float(scene_num):
                for k in ("duration_estimate_sec", "durationSec"):
                    if s.get(k):
                        dur = float(s[k])
                        break
                break
    except Exception:
        pass
    # 음성이 있으면 그것이 진짜 길이다
    try:
        sc = json.loads((proj / "scenes.json").read_text(encoding="utf-8"))
        rows = sc.get("scenes") if isinstance(sc, dict) else sc
        for s in rows or []:
            if float(s.get("sceneNumber")) == float(scene_num) and s.get("_audio_dur"):
                dur = float(s["_audio_dur"])
                break
    except Exception:
        pass
    return max(4, min(15, math.ceil(dur + 1)))


@router.get("/api/video/accounts")
async def video_accounts():
    """계정과 잔액 — 어느 계정이 얼마 남았는지 화면에서 보이게."""
    mod = _backend()
    if not mod:
        return JSONResponse({"error": "adobe/backend 를 찾을 수 없습니다"}, status_code=503)
    _v, acc = mod
    rows = [acc.status(n) for n in acc.order()]
    return {"accounts": rows, "total": sum((r.get("credits") or 0) for r in rows),
            "order": acc.order()}


@router.get("/api/video/models")
async def video_models():
    mod = _backend()
    if not mod:
        return JSONResponse({"error": "adobe/backend 를 찾을 수 없습니다"}, status_code=503)
    v, _acc = mod
    return {"models": v.load_specs(), "cli": bool(v.cli())}


@router.post("/api/video/generate")
async def video_generate(request: Request):
    """씬 하나를 비디오로. 끝날 때까지 기다린다(씬당 3~5분)."""
    mod = _backend()
    if not mod:
        return JSONResponse({"error": "adobe/backend 를 찾을 수 없습니다"}, status_code=503)
    v, _acc = mod
    b = await request.json()
    slug = (b.get("slug") or "").strip()
    proj = _project_dir(slug)
    if not proj:
        return JSONResponse({"error": f"프로젝트 없음: {slug}"}, status_code=404)
    sn = b.get("sceneNumber")
    prompt = (b.get("prompt") or "").strip()
    if not prompt:
        return JSONResponse({"error": "프롬프트가 필요합니다"}, status_code=400)

    from auto_agent.dashboard.helpers import adobe_scene_ids
    sid = adobe_scene_ids(str(proj)).get(float(sn))
    if not sid:
        return JSONResponse({"error": "이 씬의 어도비 sceneId 를 찾지 못했습니다"},
                            status_code=422)

    # 시작 이미지 — 씬에 링크된 그림
    img = None
    try:
        sc = json.loads((proj / "scenes.json").read_text(encoding="utf-8"))
        rows = sc.get("scenes") if isinstance(sc, dict) else sc
        for s in rows or []:
            if float(s.get("sceneNumber")) == float(sn):
                img = s.get("imageRef")
                break
    except Exception:
        pass
    if not img or not (proj / img).is_file():
        return JSONResponse({"error": "씬 이미지가 없습니다"}, status_code=422)

    sec = int(b.get("duration") or _scene_seconds(proj, sn))
    params = {"prompt": prompt, "duration": sec,
              "aspect_ratio": b.get("aspect_ratio") or "16:9"}
    res = v.generate(proj, b.get("job_type") or "minimax_h3", params,
                     images={"start_image": [img]})
    if res.get("status") != "completed":
        return JSONResponse(res, status_code=422)

    out = proj / "video" / f"v_{sid}_{b.get('job_type') or 'minimax_h3'}.mp4"
    dl = v.download(res["urls"][0], out)
    if dl.get("status") != "completed":
        return JSONResponse(dl, status_code=422)
    return {"ok": True, "sceneNumber": sn, "duration": sec,
            "rel": out.relative_to(proj).as_posix()}
