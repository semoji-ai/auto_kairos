"""레이아웃 이름·별칭·데이터 필드의 단일 출처.

v3는 Remotion 컴포넌트 21종으로 그렸고 어도비는 AE 네이티브 렌더러 몇 종만 갖는다.
모르는 이름이 와도 내용을 버리지 않는 것이 이 모듈의 목적이다 —
고유 렌더러 → 별칭 → 범용 렌더러 3단으로 반드시 그린다.
"""
from __future__ import annotations

GENERIC = "generic"

# 어도비가 고유 렌더러를 가진 레이아웃
NATIVE = ("cinematic", "headline_only", "items_list", "metric_spotlight",
          "bar", "quote", "map")

# v3 이름 → 같은 그림을 그리는 어도비 렌더러.
# v3 VisualizationRenderer의 폴백 매핑을 그대로 가져왔다.
ALIASES = {
    # 목록형
    "slide_list": "items_list",
    "slide_numbered": "items_list",
    "slide_ranking": "items_list",
    "narrative_build": "items_list",
    "word_cascade": "items_list",
    "icon_grid": "items_list",
    "reveal_sequence": "items_list",
    # 수치 강조
    "slide_statistic": "metric_spotlight",
    "impact_count": "metric_spotlight",
    "dramatic_number": "metric_spotlight",
    "counter_wall": "metric_spotlight",
    "icon_stat": "metric_spotlight",
    "slide_bignum": "metric_spotlight",
    # 한 문장 선언
    "slide_highlight": "headline_only",
    "spotlight_reveal": "headline_only",
    "title_card": "headline_only",
    # 차트
    "bar_chart": "bar",
    "graph": "bar",
    # 비교형 — 고유 compare 렌더러가 없으므로 범용으로(내용을 버리지 않는다)
    "split_contrast": GENERIC,
    "diagram": GENERIC,
    "slide_compare": GENERIC,
}

# 스키마 enum·검증이 허용하는 이름 전체
KNOWN = frozenset(NATIVE) | frozenset(ALIASES) | {GENERIC}


def resolve_layout(name) -> str:
    """레이아웃 이름 → 실제로 그릴 렌더러 이름.

    고유 렌더러가 있으면 그것, 없으면 별칭, 그래도 없으면 범용.
    모든 유효하지 않은 입력(비문자열, 빈 값, 미지의 이름)은 범용으로 → 내용을 버리지 않는다."""
    if not isinstance(name, str):
        return GENERIC
    key = name.strip()
    if not key:
        return GENERIC
    if key in NATIVE:
        return key
    return ALIASES.get(key, GENERIC)


def _first_nonempty(*vals):
    for v in vals:
        if v is None:
            continue
        if isinstance(v, (str, list, tuple, dict)) and len(v) == 0:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        return v
    return None


def normalize_fields(scene: dict) -> dict:
    """씬의 레이아웃 데이터를 v3 공통 계약으로 정규화한다(값이 있는 것만).

    어도비 기존 어휘(headline/sub/chart/value+label/quote_*)를 정규 이름으로 옮겨,
    jsx 렌더러가 한 가지 형태만 알면 되게 한다. 정규 필드가 이미 있으면 그것을 쓴다.
    씬의 title(씬 이름)은 읽지 않는다 — 뷰 제목은 headline이다."""
    s = scene or {}
    chart = s.get("chart") if isinstance(s.get("chart"), dict) else {}
    out = {
        # 씬의 title은 시트에 보이는 씬 이름이므로 읽지 않는다. 뷰 제목은 headline이다.
        "title": _first_nonempty(s.get("headline")),
        "items": _first_nonempty(s.get("items"), chart.get("labels"),
                                 [s.get("quote_text")] if (s.get("quote_text") is not None and s.get("quote_text") != "") else None,
                                 [s.get("label")] if (s.get("label") is not None and s.get("label") != "") else None),
        "values": _first_nonempty(s.get("values"), chart.get("values"),
                                  [s.get("value")] if (s.get("value") is not None and s.get("value") != "") else None),
        "descriptions": _first_nonempty(s.get("descriptions"),
                                        [s.get("sub")] if (s.get("sub") is not None and s.get("sub") != "") else None),
        "unit": _first_nonempty(s.get("unit"), chart.get("unit")),
        "source": _first_nonempty(s.get("source"), s.get("quote_who")),
        "left": _first_nonempty(s.get("left")),
        "right": _first_nonempty(s.get("right")),
        "relations": _first_nonempty(s.get("relations")),
        "profileName": _first_nonempty(s.get("profileName")),
        "profileSubtitle": _first_nonempty(s.get("profileSubtitle")),
    }
    return {k: v for k, v in out.items() if v is not None}
