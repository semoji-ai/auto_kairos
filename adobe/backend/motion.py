"""모션 디렉터 — 내레이션+레이어 목록으로 LLM이 프리셋 모션 플랜 생성(바운디드 enum).
임의 키프레임 좌표는 LLM이 내지 않음 — 수치는 jsx가 결정적으로 계산."""
from __future__ import annotations

import json
from pathlib import Path

from backend import scenes, llm, tts, imagegen, camera_plan

_SCHEMA = Path(__file__).resolve().parent / "schemas" / "motion_plan.schema.json"

# ── 까딱임 기본값 (단일 소스) ──────────────────────────────────────────────
#
# 인물 idle. **발밑을 축으로 세로만 눌렀다 편다** — 위치를 흔드는 wiggle 과
# 다르다. 발이 땅에 붙어 있어야 서 있는 사람으로 보인다.
#
#     반주기 10프레임 · 100% → 101% · 양 키 easy ease
#
# 이 숫자가 정본이다. `SemojiLayerScene.tsx` 가 처음부터 이 값이었고
# (`max_scale: 1.01`, `period_frames: 20`), 애프터이펙트와 `build_layered_props`
# 만 다른 값으로 벌어져 있었다 — 같은 인물이 렌더러마다 다르게 까딱였다.
#
# **여기서만 고친다.** jsx 는 매니페스트가 실어 보낸 값을 쓰고, 리모션 쪽은
# 아래 두 함수로 환산해 쓴다. 어느 쪽도 숫자를 직접 적지 않는다.
BOB_HALF_FRAMES = 10        # 100 → 101 까지 걸리는 시간(되돌아오는 데 또 10)
BOB_AMOUNT = 1              # 세로 스케일 증가분(%) — 100 → 101
BOB_FPS = 30.0              # 프레임을 초로 바꿀 때의 기준 (timeline.FPS 와 같다)


def bob_move(start: float = 0.0, duration: float = 0.0) -> dict:
    """매니페스트에 실어 보낼 까딱임 지시. jsx 가 이 값으로 키를 찍는다."""
    return {"type": "bob", "start": start, "duration": duration,
            "half_frames": BOB_HALF_FRAMES, "amount": BOB_AMOUNT}


def bob_remotion(fps: float = BOB_FPS) -> dict:
    """리모션 `LayerSpec.bob` 값. `amp` 는 비율, `period` 는 초당 주기(Hz).

    한 바퀴는 반주기의 두 배다 — 눌렸다가 되돌아와야 한 번이다.
    """
    return {"amp": BOB_AMOUNT / 100.0,
            "period": fps / (BOB_HALF_FRAMES * 2)}

PRESET_GUIDE = (
    "- slide_in: 화면 밖에서 등장(direction 필수). 등장 연출.\n"
    "- fade_in: 서서히 나타남.\n"
    "- pop: 통통 튀며 등장(스케일 바운스). 강조 등장.\n"
    "- drift: 천천히 떠다님(미세 이동). 정적 씬의 생동감.\n"
    "- bob: 위아래로 살랑임. 캐릭터 idle 기본.\n"
    "- shake: 짧고 빠른 흔들림. 충격·놀람.\n"
    "- zoom_emphasis: 살짝 커졌다 복귀. 내레이션 강조 시점.\n"
    "- exit_fade: 서서히 사라짐(씬 끝 무렵).\n"
    "- stamp: 도장처럼 크게서 작아지며 쾅 등장(5프레임). 사물 강조 등장.\n"
    "- wiggle: 잔잔히 흔들림(익스프레션). 긴장·불안·강조 유지.\n"
)

CAMERA_GUIDE = (
    "- slow_zoom_in / slow_zoom_out: 씬 전체를 천천히 밀거나 당김.\n"
    "- pan_left / pan_right: 씬 전체를 옆으로 흘림.\n"
    "- none: 카메라 무브 없음.\n"
)

# 레이어 종류별 허용 프리셋 — 인물은 오퍼시티 키프레임 금지 규칙 때문에 fade류가 없다.
# 배경은 목록 자체가 없다(카메라가 담당).
ALLOWED_BY_KIND = {
    "character": {"bob", "zoom_emphasis"},
    "object": {"slide_in", "fade_in", "pop", "drift", "shake",
               "zoom_emphasis", "exit_fade", "stamp", "wiggle"},
}


def layer_kinds(proj_dir: Path, sid: str, elements: list) -> dict:
    """{stem: "character"|"object"} — 사이드카 우선, 없으면 _char 접미사."""
    specs = {s.get("layer"): s for s in imagegen.load_element_specs(Path(proj_dir) / "layers", sid)}
    out = {}
    for stem in elements or []:
        sp = specs.get(stem) or {}
        kind = sp.get("kind")
        if kind not in ("character", "object"):
            kind = "character" if "_char" in stem else "object"
        out[stem] = kind
    return out


def filter_plan_moves(plan: dict, kinds: dict) -> dict:
    """LLM 플랜을 종류별 허용 목록으로 거른다. 모르는 레이어·빈 레이어는 버린다."""
    filtered = []
    for L in plan.get("layers", []):
        kind = kinds.get(L.get("layer"))
        if not kind:
            continue
        allowed = ALLOWED_BY_KIND.get(kind) or set()
        mvs = [m for m in L.get("moves", []) if m.get("type") in allowed]
        if mvs:
            filtered.append({"layer": L["layer"], "moves": mvs})
    plan["layers"] = filtered
    return plan


_PRESET_GUIDE = PRESET_GUIDE        # 기존 사용처(plan_scene_motion) 보존


def motion_path(proj_dir: Path, sid: str) -> Path:
    return Path(proj_dir) / f"motion_{sid}.json"


def _scene_duration(proj_dir: Path, s: dict) -> float:
    if s.get("_audio"):
        d = tts.audio_duration(Path(proj_dir) / s["_audio"])
        if d:
            return d
    return float(s.get("duration_estimate_sec") or 3.0)


def _clamp_plan(plan: dict, dur: float) -> dict:
    """start/duration을 씬 길이 안으로 클램프. 알 수 없는 레이어/타입은 스키마가 차단.
    camera.amount 단위 정규화: 0.06(비율) → 6(퍼센트/px 계열) + 타입별 범위 클램프."""
    for L in plan.get("layers", []):
        for mv in L.get("moves", []):
            mv["start"] = max(0.0, min(float(mv.get("start") or 0), dur))
            mv["duration"] = max(0.1, min(float(mv.get("duration") or 0.5), dur - mv["start"]))
    cam = plan.get("camera") or {}
    if isinstance(cam, list):                   # 화각 키 배열 — camera_plan이 이미 규칙을 지켰다
        return plan
    amt = cam.get("amount")
    if amt is not None:
        amt = float(amt)
        if 0 < amt <= 1.0:
            amt *= 100.0                        # 비율 표기 → 퍼센트
        ctype = cam.get("type", "")
        if ctype in ("slow_zoom_in", "slow_zoom_out"):
            amt = max(2.0, min(amt, 15.0))      # 줌 2~15%
        elif ctype in ("pan_left", "pan_right"):
            amt = max(20.0, min(amt, 160.0))    # 팬 20~160px
        cam["amount"] = round(amt, 2)
    return plan


def plan_scene_motion(proj_dir: Path, scene_number: int, *, on_line=None) -> dict:
    """씬 모션 플랜 생성 → motion_{sid}.json 저장. 반환=플랜 dict 또는 {error}."""
    proj_dir = Path(proj_dir)
    data = scenes.load_scenes(proj_dir)
    s = next((x for x in data.get("scenes", []) if x.get("sceneNumber") == scene_number), None)
    if not s:
        return {"error": f"scene {scene_number} 없음"}
    sid = s.get("sceneId")
    specs = {sp.get("layer"): sp for sp in imagegen.load_element_specs(proj_dir / "layers", sid)} if sid else {}
    elements = [Path(r).stem for r in (s.get("_layers") or [])
               if "__bg" not in Path(r).name
               and not (specs.get(Path(r).stem) or {}).get("removed")]
    if not elements:
        return {"error": "레이어 없음 — 먼저 레이어 분리 필요"}
    kind_map = layer_kinds(proj_dir, sid, elements)
    chars = [e for e in elements if kind_map.get(e) == "character"]
    objs = [e for e in elements if kind_map.get(e) == "object"]
    if not chars and not objs:
        return {"error": "모션을 줄 요소 레이어 없음"}
    dur = _scene_duration(proj_dir, s)
    # 분리 시점의 연출 의도 — 있으면 모션이 그것과 어긋나지 않게 한다
    intents = []
    for spec in imagegen.load_element_specs(proj_dir / "layers", sid):
        if spec.get("layer") in (chars + objs) and (spec.get("intent") or "").strip():
            intents.append(f"- {spec['layer']}: {spec['intent']}")
    intent_block = ("\n## 분리 시점의 연출 의도(참고)\n" + "\n".join(intents) + "\n") if intents else ""

    def _lines(names):
        return "\n".join(f"- {e}" for e in names) or "- (없음)"
    prompt = (
        "너는 모션그래픽 연출가다. 아래 씬의 레이어에 프리셋 모션을 설계해라.\n\n"
        f"## 내레이션(씬 길이 {dur:.1f}초)\n{s.get('narration', '') or '(없음)'}\n\n"
        f"## 인물 레이어(이 이름을 정확히 그대로 사용)\n{_lines(chars)}\n"
        f"## 사물 레이어(이 이름을 정확히 그대로 사용)\n{_lines(objs)}\n"
        + intent_block + "\n"
        f"## 사용 가능한 모션 프리셋\n{_PRESET_GUIDE}\n"
        "## 연출 원칙(엄수)\n"
        "1) 인물에는 bob(까딱임 idle)과 zoom_emphasis만 쓴다. 인물 기본은 bob 1개.\n"
        "2) 사물 기본은 모션 없음이다. 내레이션이 그 사물을 언급하거나 연출상 필요할 때만 준다 — "
        "등장(slide_in/pop/stamp)은 씬 앞부분, 강조(zoom_emphasis/shake/wiggle)는 해당 시점, "
        "퇴장(exit_fade)은 씬 끝.\n"
        "3) 배경 레이어에는 모션을 주지 않는다.\n"
        "4) 모든 start+duration은 씬 길이 이내.\n"
        "5) camera는 씬 분위기에 맞게 none/slow_zoom_in/slow_zoom_out/pan_left/pan_right 중 선택."
    )
    out = proj_dir / f".motion_plan_{sid}.json"
    res = llm.run_orchestrator(prompt, proj_dir, output_schema=str(_SCHEMA),
                               output_last=str(out), on_line=on_line)
    if res.get("returncode") != 0 or not out.is_file():
        return {"error": "모션 플랜 생성 실패"}
    try:
        plan = json.loads(out.read_text(encoding="utf-8"))
    except Exception:
        return {"error": "모션 플랜 파싱 실패"}
    plan = filter_plan_moves(plan, kind_map)
    plan = _clamp_plan(plan, dur)
    # 나레이션 기반 화각 키 — 타임스탬프와 bbox가 있으면 LLM의 카메라 type을 대체한다.
    # 결정적이라 검증 가능하고, "말보다 먼저 도착" 규칙을 기계가 지킨다.
    try:
        cam_keys = camera_plan.plan_scene_camera(proj_dir, s, duration=dur)
        if cam_keys:
            plan["camera"] = cam_keys
    except Exception:
        pass                                    # 화각 플랜 실패는 모션 플랜을 막지 않는다
    motion_path(proj_dir, sid).write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return plan
