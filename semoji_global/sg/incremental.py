"""부분 렌더 계획: 이전 렌더와 새 타임워프를 견줘 바뀐 구간만 AE로 렌더하고 나머지는 이전 렌더를 시간만 옮겨 재사용.
파트 시간표(anchors)는 원본 파트 시간 u → 렌더 시간. 옛·새 시간표의 기울기가 같은 구간은 내용이 같고 시간만 밀린 것."""
from sg.timemap import PiecewiseMap


def _inverse(anchors):
    pts, last = [], None
    for u, n in anchors:
        if last is None or n > last + 1e-9:
            pts.append((n, u)); last = n
    return PiecewiseMap(pts)


def _snap(t, fps):
    return round(t * fps) / fps


def plan_parts(old_anchors, new_anchors, dur_new, dirty_u=(), margin=0.5, fps=29.97, merge_gap=1.0, scenes_u=()):
    """→ [("reuse", n0, n1, old_n0) | ("render", n0, n1)]  (n = 새 파트 시간, 프레임 경계에 맞춤)
    dirty_u: 시간은 같아도 내용(글자·그림·자막)이 바뀐 원본 파트 구간 [(u0, u1)].
    scenes_u: 장면 레이어 구간 [(in, out)](원본 파트 시간). 바뀐 구간에 걸친 장면은 통째로 렌더 — 장면 안 키 애니메이션(줌 등)은
    가운데 한 문장 길이만 바뀌어도 장면 전체의 보간이 달라져, 시간 비율이 같은 곳도 이전 렌더와 다르다."""
    O, N = PiecewiseMap(old_anchors), PiecewiseMap(new_anchors)
    us = sorted({float(u) for u, _ in old_anchors} | {float(u) for u, _ in new_anchors})
    bad_u = []
    for u0, u1 in zip(us, us[1:]):
        if abs(O.ratio(u0, u1) - N.ratio(u0, u1)) > 1e-6:
            bad_u.append((u0, u1))
    bad_u += [tuple(x) for x in dirty_u]
    grown = []
    for a, b in bad_u:
        for s0, s1 in scenes_u:
            if s0 < b and a < s1:
                a, b = min(a, s0), max(b, s1)
        grown.append((a, b))
    bad = [(N(a), N(b)) for a, b in grown]
    bad = sorted((max(0.0, a - margin), min(dur_new, b + margin)) for a, b in bad)
    merged = []
    for a, b in bad:
        if merged and a <= merged[-1][1] + merge_gap:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    edge = lambda t: t if t in (0.0, dur_new) else _snap(t, fps)
    renders = [(edge(a), edge(b)) for a, b in merged if b > a]
    inv = _inverse(new_anchors)
    plan, t = [], 0.0
    for a, b in renders + [(dur_new, dur_new)]:
        if a > t + 1e-9:
            plan.append(("reuse", t, a, _snap(O(inv(t)), fps) if t else 0.0))
        if b > a:
            plan.append(("render", a, b))
        t = max(t, b)
    return plan
