"""연속 씬 같은 연출·같은 카메라 무빙 검사 — 세모지 통합보고 §0-1 #4, §4.

"연속 씬 같은 무빙 금지 — 씬을 고칠 때마다 ±2씬 카메라 키 비교." 생성 로직은 건드리지
않고, 씬별 계획(카메라·모션)을 받아 가까운 씬(기본 ±2)에서 같은 값이 되풀이되는 곳만 알린다.

비교하지 않는 것(되풀이돼도 정상):
  · 카메라 고정(none) — 인포그래픽·도식·액자 사진 씬은 연속으로 고정이 맞다(§4).
  · 인물 숨쉬기(bob) — 인물 씬 기본값이다(§3-7).
"""
from __future__ import annotations

import json
from pathlib import Path

CAMERA_TOKENS = ("zoom_in", "zoom_out", "pan_left", "pan_right", "tilt_up", "tilt_down",
                 "push_in", "pull_out", "dolly", "orbit", "slow_zoom_in", "slow_zoom_out")
IGNORE_MOTION = {"bob", "breath", "breathing", "idle", "none", ""}


def camera_signature(cam) -> str | None:
    """카메라 계획 → 비교용 이름. 고정·없음은 None."""
    if cam is None:
        return None
    if isinstance(cam, str):
        c = cam.strip().lower()
        return c if c in CAMERA_TOKENS else None          # 구도 설명 문장은 무빙이 아니다
    if isinstance(cam, dict):
        t = (cam.get("type") or "").strip().lower()
        return None if t in ("", "none", "static") else t
    if isinstance(cam, list) and len(cam) >= 2:           # 화각 키 [{t, rect:[x,y,w,h]}]
        r0, r1 = cam[0].get("rect"), cam[-1].get("rect")
        if not (r0 and r1):
            return None
        x0, y0, w0, h0 = r0
        x1, y1, w1, h1 = r1
        parts = []
        k = w1 / w0 if w0 else 1.0
        if k < 0.97:
            parts.append("zoom_in")
        elif k > 1.03:
            parts.append("zoom_out")
        dx = ((x1 + w1 / 2) - (x0 + w0 / 2)) / max(w0, 1e-6)
        dy = ((y1 + h1 / 2) - (y0 + h0 / 2)) / max(h0, 1e-6)
        if abs(dx) > 0.03:
            parts.append("pan_right" if dx > 0 else "pan_left")
        if abs(dy) > 0.03:
            parts.append("tilt_down" if dy > 0 else "tilt_up")
        return "+".join(parts) or None
    return None


def motion_signature(motion) -> str | None:
    """모션 계획 → 비교용 이름(숨쉬기 제외, 종류 정렬). 없으면 None."""
    types: set[str] = set()
    if isinstance(motion, str):
        types.add(motion.strip().lower())
    elif isinstance(motion, list):
        for m in motion:
            if isinstance(m, str):
                types.add(m.strip().lower())
            elif isinstance(m, dict):
                if "moves" in m:                          # motion_{sid}.json layers[]
                    types.update((mv.get("type") or "").lower() for mv in m.get("moves") or [])
                else:
                    types.add((m.get("type") or m.get("name") or "").lower())
    elif isinstance(motion, dict):
        return motion_signature(motion.get("layers") or motion.get("moves") or [])
    types -= IGNORE_MOTION
    return "+".join(sorted(types)) or None


def find_repetitions(plan: list[dict], window: int = 2) -> list[dict]:
    """plan: [{"scene": n, "camera": sig|None, "motion": sig|None}] (씬 순서대로).

    window 안(다음 1~window 씬)에 같은 카메라·같은 모션이 있으면 하나씩 알린다."""
    out = []
    for i, a in enumerate(plan):
        for j in range(i + 1, min(len(plan), i + window + 1)):
            b = plan[j]
            for field in ("camera", "motion"):
                va, vb = a.get(field), b.get(field)
                if va and va == vb:
                    out.append({"field": field, "value": va, "a": a["scene"], "b": b["scene"],
                                "gap": j - i})
    return out


def load_plan(project: Path) -> list[dict]:
    """프로젝트 폴더에서 씬 순서대로 카메라·모션 계획을 모은다.

    순서·sceneId: scenes.json(어도비) → scene_specs.json. 계획: motion_{sceneId}.json 이 있으면
    그것, 없으면 씬의 camera(무빙 낱말일 때만)·motion·techniques 필드."""
    project = Path(project)
    src = project / "scenes.json"
    if not src.is_file():
        src = project / "scene_specs.json"
    scenes = json.loads(src.read_text(encoding="utf-8")).get("scenes", [])
    plan = []
    for s in scenes:
        n = s.get("sceneNumber") or s.get("scene_number")
        sid = s.get("sceneId") or ""
        mf = project / f"motion_{sid}.json" if sid else None
        cam = mot = None
        if mf and mf.is_file():
            m = json.loads(mf.read_text(encoding="utf-8"))
            cam, mot = camera_signature(m.get("camera")), motion_signature(m.get("layers") or [])
        else:
            cam = camera_signature(s.get("camera_move") or s.get("camera"))
            mot = motion_signature(s.get("motion") or s.get("techniques"))
        plan.append({"scene": n, "camera": cam, "motion": mot})
    return plan
