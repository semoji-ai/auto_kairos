"""문체 검사 — 원고가 세모지 목소리인지 잰다.

**있어야 할 자리로 되돌리는 것이다.** 이 검사는 원고 단계에 있어야 하는데
지금까지 하류(어도비 패널)에만 있었다 — 원고는 v3 에서 만드는데 검증이
어도비에만 있어 순서가 거꾸로였다.

기준은 감이 아니라 **세모지 47편 실측 분포**다
(`auto_agent/data/artstyle/semoji-voice-bands.json`).

    존댓말 종결   p10 0.45 · p50 0.61 · p90 0.93
    평서체        p90 0.023   — 5%를 넘으면 미달
    줄 길이 표준편차  p10 6.93  — **하한이 있다**

하한이 핵심이다. AI 가 쓴 글은 문장 길이가 고르고 사람 글은 들쭉날쭉하다.
너무 매끈한 원고도 떨어뜨린다.

⚠️ **게이트는 검출기다 — 자동 재작성을 붙이지 않는다.** v3 에는 이미 3인
페르소나 래칫이 있고 그 루프는 지표가 아니라 **뜻**을 본다. 여기에 regex 를
겨냥한 두 번째 자동 재작성을 얹으면 상위·하위 루프가 서로 다른 목표를
최적화하고, 이미 통과한 지표를 더 만족시키려 억지 「~잖아요」를 넣는다
(어도비 쪽이 실제로 겪은 지표 스터핑이다).
"""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

_ADOBE = Path(__file__).resolve().parents[2] / "adobe"


def _vv():
    if not (_ADOBE / "backend").is_dir():
        return None
    if str(_ADOBE) not in sys.path:
        sys.path.insert(0, str(_ADOBE))
    try:
        from backend import verify_voice        # noqa: WPS433
        return verify_voice
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


@router.get("/api/voice/check")
async def voice_check(slug: str):
    """원고 문체 검사. {ok, violations, metrics}.

    위반 문구는 설명이 아니라 **다음 행동**으로 적혀 있다 — 그대로 재작성
    지시문에 붙여 쓸 수 있다.
    """
    vv = _vv()
    if not vv:
        return JSONResponse({"error": "adobe/backend 를 찾을 수 없습니다"}, status_code=503)
    proj = _project_dir(slug or "")
    if not proj:
        return JSONResponse({"error": f"프로젝트 없음: {slug}"}, status_code=404)
    try:
        return vv.check_project(proj)
    except Exception as e:
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=500)


@router.get("/api/voice/bands")
async def voice_bands():
    """판정 기준 — 무엇을 재는지 화면에서 보이게."""
    vv = _vv()
    if not vv:
        return JSONResponse({"error": "adobe/backend 를 찾을 수 없습니다"}, status_code=503)
    return vv.bands()
