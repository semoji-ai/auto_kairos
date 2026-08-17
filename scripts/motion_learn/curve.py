"""smoothness(0~1) → AE Keyframe influence(%) 변환. rubric §1-1 스펙 잠금.
빌더 jsx가 동일 수치를 구현하며, 이 함수가 회귀 기준이다.
주의: AE는 influence 최소 0.1을 요구하므로 jsx 측은 0을 0.1로 클램프한다(여기선 rubric 값 0 반환).
반올림은 jsx의 Math.round(half-up)와 일치시키기 위해 int(x+0.5)를 쓴다(Python 기본 round는 banker's라 .5 경계에서 갈림)."""
from __future__ import annotations

_ANCHORS = [(0.0, 0), (0.5, 33), (0.75, 75), (0.9, 90), (1.0, 95)]


def smoothness_to_influence(s: float) -> int:
    if s <= 0.0:
        return 0
    if s >= 1.0:
        return 95
    for (x0, y0), (x1, y1) in zip(_ANCHORS, _ANCHORS[1:]):
        if x0 < s <= x1:
            return int(y0 + (y1 - y0) * (s - x0) / (x1 - x0) + 0.5)
    return 0
