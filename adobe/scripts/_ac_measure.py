"""프리뷰 webm 한 편을 재서 움직임 곡선을 뽑는다.

프리셋 본체는 암호화돼 열리지 않지만, 프리뷰는 그 프리셋이 실제로 그린 결과다.
화면을 프레임 단위로 재면 스케일·위치·투명도 곡선이 그대로 나온다.

프리뷰 한 편에는 **등장 → 유지 → 퇴장**이 모두 들어 있다. 그래서 먼저
「유지 구간(plateau)」을 찾아 기준 크기를 정하고, 그 앞뒤를 각각 등장·퇴장으로
갈라서 잰다. 꼬리를 기준으로 삼으면 퇴장 중인 크기가 기준이 되어 전부 어긋난다.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

W, H = 320, 180
FPS = 29.97
THR = 24.0          # 배경에서 이만큼 떨어지면 요소로 본다
FLAT = 0.02         # 유지 구간 판정 폭 (±2%)


def decode(path: Path) -> np.ndarray:
    p = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path),
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True,
    )
    buf = np.frombuffer(p.stdout, dtype=np.uint8)
    n = buf.size // (W * H * 3)
    if n == 0:
        raise ValueError("no frames")
    return buf[: n * W * H * 3].reshape(n, H, W, 3)


def background(frames: np.ndarray) -> np.ndarray:
    edge = np.concatenate([
        frames[:, :4, :, :].reshape(-1, 3),
        frames[:, -4:, :, :].reshape(-1, 3),
        frames[:, :, :4, :].reshape(-1, 3),
        frames[:, :, -4:, :].reshape(-1, 3),
    ])
    return np.median(edge, axis=0)


def series(path: Path) -> dict:
    frames = decode(path)
    n = len(frames)
    bg = background(frames)
    dist = np.linalg.norm(frames.astype(np.float32) - bg, axis=3)
    mask = dist > THR

    diag, cov, ink, cx, cy, aspect, alive = [], [], [], [], [], [], []
    for i in range(n):
        m = mask[i]
        c = float(m.mean())
        cov.append(c)
        if c < 1e-5:
            alive.append(False)
            diag.append(0.0); ink.append(0.0); aspect.append(0.0)
            cx.append(np.nan); cy.append(np.nan)
            continue
        ys, xs = np.nonzero(m)
        w = int(xs.max() - xs.min()) + 1
        h = int(ys.max() - ys.min()) + 1
        alive.append(True)
        diag.append(float(np.hypot(w, h)))
        aspect.append(w / h)
        ink.append(float(dist[i][m].mean() * c))
        cx.append(float(xs.mean()) / W)
        cy.append(float(ys.mean()) / H)

    return {
        "n": n, "bg": [round(float(v)) for v in bg],
        "diag": np.array(diag), "cov": np.array(cov), "ink": np.array(ink),
        "cx": np.array(cx), "cy": np.array(cy), "aspect": np.array(aspect),
        "alive": np.array(alive),
    }


def find_hold(diag: np.ndarray, ink: np.ndarray,
              alive: np.ndarray) -> tuple[int, int, float, float]:
    """가장 긴 「아무것도 안 변하는 구간」 → (시작, 끝, 기준 크기, 기준 잉크).

    크기만 보면 **페이드를 놓친다** — 투명도만 오르는 등장은 bbox 가 처음부터
    끝 크기라, 크기 기준으로는 첫 프레임부터 유지 구간이 되어 「등장 1프레임」이
    된다. 표본 120편에서 fade_in 26편이 전부 그렇게 나왔다.
    그래서 크기와 잉크(= 배경 대비 강도 × 화면 점유율, 투명도 대용)를
    **함께** 평평한지 본다.
    """
    idx = np.nonzero(alive)[0]
    if len(idx) < 3:
        return -1, -1, 0.0, 0.0
    best = (0, int(idx[0]), int(idx[0]))
    for a in idx:
        vd, vi = diag[a], ink[a]
        if vd <= 0 or vi <= 0:
            continue
        b = a
        for j in idx[idx >= a]:
            if (abs(diag[j] - vd) / vd <= FLAT
                    and abs(ink[j] - vi) / vi <= FLAT * 2):
                b = j
            else:
                break
        run = b - a + 1
        if run > best[0]:
            best = (run, int(a), int(b))
    _, h0, h1 = best
    ds = diag[h0:h1 + 1]
    ins = ink[h0:h1 + 1]
    return h0, h1, float(np.median(ds[ds > 0])), float(np.median(ins[ins > 0]))


def phase(scale: np.ndarray, opacity: np.ndarray) -> dict:
    """한 구간(등장 또는 퇴장)의 오버슛·바운스·길이·투명도 상승."""
    if len(scale) < 2:
        return {"frames": int(len(scale)), "overshoot": 0.0, "bounces": 0,
                "scale_edge": 1.0, "opacity_edge": 1.0, "opacity_frames": 0}
    over = float(scale.max() - 1.0)
    bounces = int(sum(1 for i in range(1, len(scale) - 1)
                      if scale[i] > scale[i - 1] and scale[i] >= scale[i + 1]
                      and abs(scale[i] - 1.0) > 0.015))
    # 투명도가 정착값 95% 에 닿는 데 걸린 프레임
    op_f = int(len(opacity))
    for i, v in enumerate(opacity):
        if v >= 0.95:
            op_f = i
            break
    return {
        "frames": int(len(scale)),
        "overshoot": round(max(0.0, over), 4),
        "bounces": bounces,
        "scale_edge": round(float(scale[0]), 4),
        "opacity_edge": round(float(opacity[0]), 4),
        "opacity_frames": op_f,
        "curve": [round(float(v), 4) for v in scale],
        "opacity_curve": [round(float(v), 4) for v in opacity],
    }


def classify(f: dict) -> str:
    ins = f.get("in") or {}
    # 정착 구간이 없다 = 터졌다 사라지는 것. 표본에서 32%가 여기였고,
    # 눈으로 확인하니 폭죽·플래시류였다. 등장/퇴장으로 재면 뜻이 안 맞는다.
    if f.get("hold_frames", 0) <= 2:
        return "burst_fullscreen" if f.get("fullscreen") else "burst"
    if f.get("fullscreen"):
        return "transition"
    if f.get("direction") and f.get("travel", 0) > 0.06:
        return "position_in" if ins.get("overshoot", 0) <= 0.02 else "overshoot_position_in"
    edge = ins.get("scale_edge", 1.0)
    if edge < 0.55:
        if ins.get("bounces", 0) >= 2 and ins.get("overshoot", 0) > 0.02:
            return "bounce_scale_in"
        if ins.get("overshoot", 0) > 0.02:
            return "overshoot_scale_in"
        return "scale_in"
    if f.get("draw_ratio", 0) > 1.6:
        return "draw_reveal"
    if ins.get("overshoot", 0) > 0.02:
        return "overshoot_in"
    if ins.get("opacity_frames", 0) >= 2 and ins.get("opacity_edge", 1.0) < 0.7:
        return "fade_in"
    # 등장/퇴장 변형이 없다면 「가만히 있는 것」이 아니라 대개 **지속 효과**다.
    # 전체 구간의 흔들림·회전·맥동을 재서 가른다.
    if f.get("jitter", 0) > 0.004:
        return "loop_wiggle"
    if f.get("aspect_var", 0) > 0.05:
        return "loop_rotate"
    if f.get("ink_var", 0) > 0.06:
        return "loop_pulse"
    return "cut_in"


def analyze(path: Path) -> dict:
    s = series(path)
    diag, alive = s["diag"], s["alive"]
    idx = np.nonzero(alive)[0]
    if len(idx) < 4:
        return {"kind": "empty", "frames": s["n"]}

    h0, h1, base, base_ink = find_hold(diag, s["ink"], alive)
    if base <= 0 or base_ink <= 0:
        return {"kind": "empty", "frames": s["n"]}

    scale = np.where(alive, diag / base, np.nan)
    opac = np.where(alive, s["ink"] / base_ink, np.nan)
    first, last = int(idx[0]), int(idx[-1])

    def clean(a, b):
        sc, op = scale[a:b], opac[a:b]
        keep = ~np.isnan(sc)
        return sc[keep], op[keep]

    in_seg, in_op = clean(first, h0 + 1)
    out_seg, out_op = clean(h1, last + 1)

    # 위치: 등장 첫 프레임 → 유지 구간
    hold_cx = float(np.nanmedian(s["cx"][h0:h1 + 1]))
    hold_cy = float(np.nanmedian(s["cy"][h0:h1 + 1]))
    dx = float(s["cx"][first] - hold_cx)
    dy = float(s["cy"][first] - hold_cy)
    travel = float(np.hypot(dx, dy))
    direction = None
    if travel > 0.06:
        direction = ("from_left" if dx < 0 else "from_right") if abs(dx) > abs(dy) \
            else ("from_top" if dy < 0 else "from_bottom")

    # 그리기 판정: bbox 는 일찍 다 커졌는데 잉크(칠해진 양)가 계속 는다
    in_ink = s["ink"][first:h0 + 1]
    ink_late = float(np.mean(in_ink[len(in_ink) // 2:])) if len(in_ink) >= 2 else base_ink
    draw_ratio = float(base_ink / max(ink_late, 1e-6))

    f = {
        "frames": s["n"],
        "dur": round(s["n"] / FPS, 2),
        "bg": s["bg"],
        "first_frame": first,
        "hold": [int(h0), int(h1)],
        "hold_frames": int(h1 - h0 + 1),
        "in": phase(in_seg, in_op),
        # 퇴장은 뒤집어 재면 등장과 같은 형태가 되어 같은 잣대로 비교된다
        "out": phase(out_seg[::-1], out_op[::-1]),
        "travel": round(travel, 4),
        "direction": direction,
        "max_cov": round(float(s["cov"].max()), 4),
        "fullscreen": bool(s["cov"].max() > 0.85),
        "draw_ratio": round(draw_ratio, 3),
        "aspect_hold": round(float(np.nanmedian(s["aspect"][h0:h1 + 1])), 3),
    }

    # 버스트는 등장/유지/퇴장이 아니라 터짐(attack)과 사그라듦(decay)으로 잰다
    peak = int(np.nanargmax(np.where(alive, s["ink"], np.nan)))
    f["peak_frame"] = peak
    f["attack"] = peak - first
    f["decay"] = last - peak

    # 유지 구간 안에서의 흔들림 — 지속 효과(wiggle/rotate/pulse) 판정용.
    hs = slice(h0, h1 + 1)
    if h1 - h0 >= 4:
        f["jitter"] = round(float(np.nanstd(s["cx"][hs]) + np.nanstd(s["cy"][hs])), 5)
        asp = s["aspect"][hs]
        asp = asp[asp > 0]
        f["aspect_var"] = round(float(np.std(asp) / max(np.mean(asp), 1e-6)), 4) if len(asp) else 0.0
        f["ink_var"] = round(float(np.std(s["ink"][hs]) / max(base_ink, 1e-6)), 4)
    else:
        f["jitter"] = f["aspect_var"] = f["ink_var"] = 0.0

    f["kind"] = classify(f)
    return f


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        p = Path(arg)
        try:
            out = {"file": p.name, "product": p.parent.parent.name, **analyze(p)}
        except Exception as e:  # noqa: BLE001
            out = {"file": p.name, "product": p.parent.parent.name, "error": repr(e)}
        print(json.dumps(out, ensure_ascii=False))
