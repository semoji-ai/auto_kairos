"""나레이션 기반 카메라 플랜 — 화각 키 [{t, rect, ease}]를 결정적으로 만든다.

v3 시제품(render_camera.py)에서 실측으로 확정된 규칙의 이식이다.
- 동작의 끝은 그 대상을 부르는 발음보다 LEAD(0.3초) 이상 앞선다 — 눈이 귀보다 먼저.
- 씬당 동작은 최대 MAX_MOVES개. 계속 움직이면 멀미가 난다.
- 마지막 동작은 씬 끝 END_HOLD(0.4초) 전에 멈춘다.
- 정지 구간은 같은 rect를 두 번 넣어 명시한다 — 생략하면 AE가 계속 보간한다.
- 인물이 커서 전신 화각이 캔버스를 넘으면 상반신을 잡는다(rect_of의 클램프).
- rect는 항상 컴프 비율(16:9) — camera_keys(s=W/vw)가 세로를 정확히 채우는 전제다.

큐는 ElevenLabs 타임스탬프 사이드카(audio/tts_{sid}.timestamps.json)에서 뽑는다.
LLM을 부르지 않는다 — 전부 결정적이다.
"""
from __future__ import annotations

import json
from pathlib import Path

AR = 1920 / 1080          # 컴프 비율 — 화각은 항상 이 비율
LEAD = 0.3                # 동작 끝이 발음보다 앞서는 최소 초
MOVE = 1.8                # 한 동작의 길이(실측 10.45→12.25)
MIN_HOLD = 0.6            # 동작 사이 최소 정지
END_HOLD = 0.4            # 씬 끝 정지
TIGHT = 0.6               # 전신이 화면 세로에서 차지하는 비율
MAX_MOVES = 2


def full_rect(sw: float, sh: float) -> list:
    """씬 이미지 안에서 가장 큰 16:9 화각(중앙)."""
    w = min(float(sw), float(sh) * AR)
    h = w / AR
    return [round((sw - w) / 2, 2), round((sh - h) / 2, 2), round(w, 2), round(h, 2)]


def rect_for_bbox(bbox, sw: float, sh: float, *, tight: float = TIGHT):
    """대상 bbox를 잡는 16:9 화각 — v3 rect_of의 클램프 규칙 그대로.

    전신 화각(h = 대상높이/tight)이 캔버스 세로를 넘으면 확대가 아니라 축소가 되어
    검은 여백이 생긴다(박정희 626px 실측). 그럴 때는 상반신(높이 72%, 중심 30% 지점)을
    잡는다. 마지막에 항상 캔버스 안으로 조인다."""
    try:
        l, t, r, b = [float(v) for v in bbox]
    except (TypeError, ValueError):
        return None
    bh = b - t
    if bh <= 0 or r - l <= 0:
        return None
    sw, sh = float(sw), float(sh)
    h = bh / max(float(tight), 0.15)
    if h > sh:                          # 전신을 다 넣을 수 없다 → 얼굴·가슴을 잡는다
        h = bh * 0.72
        cy = t + bh * 0.30
    else:
        cy = t + bh * 0.35
    cx = (l + r) / 2
    w = h * AR
    if w > sw or h > sh:                # 화각이 캔버스보다 크면 검은 여백 — 넘지 않게 조인다
        k = min(sw / w, sh / h)
        w, h = w * k, h * k
    x = min(max(cx - w / 2, 0.0), max(sw - w, 0.0))
    y = min(max(cy - h / 2, 0.0), max(sh - h, 0.0))
    return [round(x, 2), round(y, 2), round(w, 2), round(h, 2)]


def _load_timestamps(proj_dir: Path, sid: str):
    """(characters, starts) 또는 None."""
    fp = Path(proj_dir) / "audio" / f"tts_{sid}.timestamps.json"
    if not fp.is_file():
        return None
    try:
        d = json.loads(fp.read_text(encoding="utf-8"))
        chars, starts = d.get("characters"), d.get("starts")
        if isinstance(chars, list) and isinstance(starts, list) and len(chars) == len(starts):
            return chars, starts
    except Exception:
        pass
    return None


def first_mention(chars: list, starts: list, name: str):
    """name이 처음 나오는 글자의 시각. 공백 차이는 무시하고 찾는다.

    타임스탬프 텍스트와 요소 이름의 띄어쓰기가 다를 수 있다("노란옷 아이" vs "노란옷아이").
    양쪽에서 공백을 걷어낸 문자열로 찾고, 압축 인덱스를 원래 인덱스로 되돌린다."""
    needle = "".join(str(name).split())
    if not needle:
        return None
    packed = []          # 공백 제거 문자열
    back = []            # packed 인덱스 → 원래 인덱스
    for i, c in enumerate(chars):
        if str(c).strip():
            packed.append(str(c))
            back.append(i)
    pos = "".join(packed).find(needle)
    if pos < 0:
        return None
    try:
        return float(starts[back[pos]])
    except (TypeError, ValueError, IndexError):
        return None


def plan_scene_camera(proj_dir: Path, s: dict, *, duration: float | None = None) -> list:
    """씬의 화각 키 [{t, rect, ease?}]. 만들 수 없으면 [] — 정지 화면 유지.

    대상: 사이드카 요소 중 bbox가 있고 제거되지 않은 것. 나레이션(타임스탬프)에서
    이름이 처음 불리는 시각을 큐로 삼아, 이른 순서로 최대 MAX_MOVES개를 민다.
    인물이 사물보다 우선한다(같은 시각대라면)."""
    from backend import imagegen, timeline
    proj_dir = Path(proj_dir)
    sid = s.get("sceneId") or ""
    ts = _load_timestamps(proj_dir, sid)
    if not ts:
        return []
    chars, starts = ts
    size = None
    if s.get("_image"):
        try:
            from PIL import Image
            with Image.open(proj_dir / s["_image"]) as im:
                size = (im.width, im.height)
        except Exception:
            size = None
    if not size:
        return []
    sw, sh = size
    dur = float(duration) if duration else timeline.scene_duration(proj_dir, s)

    specs = imagegen.load_element_specs(proj_dir / "layers", sid)
    cues = []
    for sp in specs:
        if sp.get("removed") or not sp.get("bbox"):
            continue
        t_cue = first_mention(chars, starts, sp.get("name") or "")
        if t_cue is None:
            continue
        rect = rect_for_bbox(sp["bbox"], sw, sh)
        if not rect:
            continue
        is_char = sp.get("kind") == "character" or "_char" in str(sp.get("layer") or "")
        cues.append({"t": t_cue, "rect": rect, "char": is_char})
    if not cues:
        return []
    # 이른 큐 순서, 같은 시각대(0.5초 이내)면 인물 우선
    cues.sort(key=lambda c: (round(c["t"] * 2) / 2, not c["char"]))

    base = full_rect(sw, sh)
    keys = [{"t": 0.0, "rect": base}]
    prev_arrive = 0.0
    last_rect = base
    moves = 0
    for c in cues:
        if moves >= MAX_MOVES:
            break
        arrive = min(c["t"] - LEAD, dur - END_HOLD)
        start = arrive - MOVE
        # 첫 동작은 씬 도입 0.2초만 정지하면 된다 — 이른 언급도 짧은 무브로 받는다.
        floor = prev_arrive + (MIN_HOLD if moves else 0.2)
        if start < floor:
            start = floor
        if arrive - start < 0.6:        # 밀 시간이 없다 — 이 동작은 버린다
            continue
        if c["rect"] == last_rect:      # 이미 그 화각이다
            continue
        keys.append({"t": round(start, 3), "rect": last_rect})          # 정지 구간 명시
        keys.append({"t": round(arrive, 3), "rect": c["rect"], "ease": "70:30"})
        prev_arrive = arrive
        last_rect = c["rect"]
        moves += 1
    if moves == 0:
        return []
    return keys
