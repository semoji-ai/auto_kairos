"""문단 위 형광펜(가로로 칠해 나가는 막대)을 번역 문장의 같은 뜻 구절에 다시 맞추는 계산.
막대 레이어: 왼쪽 기준 앵커, Scale X 키가 0에서 커짐(sweep). 좌표는 레이어 변형(anchor·pos·scale%)으로 오간다."""


def _scale_keys(L):
    return [k for k in L.get("keys", []) if k[0] == "ADBE Scale"]


def is_sweep(L):
    """Scale X가 0에서 시작해 커지고 Y는 그대로인 키 → 칠해 나가는 막대."""
    k = _scale_keys(L)
    return len(k) >= 2 and k[0][2][0] == 0 and k[-1][2][0] > 0 and k[0][2][1] == k[-1][2][1]


def bar_span(L, w, h):
    """막대가 다 칠해졌을 때 메인 컴프에서의 [x0, x1, y0, y1]."""
    sx, sy = _scale_keys(L)[-1][2][:2]
    ax, ay = L["anchor"][:2]; px, py = L["pos"][:2]
    return (px + (0 - ax) * sx / 100, px + (w - ax) * sx / 100, py + (0 - ay) * sy / 100, py + (h - ay) * sy / 100)


def to_local(x, y, T):
    """메인 컴프 좌표 → 레이어(T) 안 좌표."""
    return (T["anchor"][0] + (x - T["pos"][0]) * 100 / T["scale"][0], T["anchor"][1] + (y - T["pos"][1]) * 100 / T["scale"][1])


def to_main(u, v, T):
    return (T["pos"][0] + (u - T["anchor"][0]) * T["scale"][0] / 100, T["pos"][1] + (v - T["anchor"][1]) * T["scale"][1] / 100)


def ko_span(text, line_x0, line_x1, hx0, hx1):
    """한국어 줄(상자 line_x0~x1, 글자 폭 거의 같음)에서 형광펜 x 범위가 덮는 글자 [i0, i1)."""
    n = len(text)
    f0 = max(0.0, (hx0 - line_x0) / max(1e-6, line_x1 - line_x0))
    f1 = min(1.0, (hx1 - line_x0) / max(1e-6, line_x1 - line_x0))
    return int(f0 * n), min(n, max(int(f0 * n) + 1, round(f1 * n)))


def fit_bar(L, w, x0, x1):
    """막대가 메인 x0~x1을 칠하도록 → (새 position x, 마지막 Scale X%). 앵커·Y는 그대로."""
    sx = 100.0 * (x1 - x0) / w
    return x0 + L["anchor"][0] * sx / 100, sx
