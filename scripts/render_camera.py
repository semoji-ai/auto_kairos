#!/usr/bin/env python3
"""카메라 계획대로 씬을 렌더한다 — 나레이션이 무엇을 말할 때 무엇을 보여줄지.

레이어(벡터/PNG) + 카메라 계획 + 오디오를 받아 mp4를 만든다.
벡터 층은 화각 배율대로 **다시 그려** 확대해도 깨지지 않는다.

    python3 scripts/render_camera.py <layers.json> <plan.json> -o out.mp4 --audio a.mp3
"""
from __future__ import annotations
import argparse, io, json, math, subprocess, sys
from pathlib import Path
import cairosvg
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from animate_scene import bob_params

W, H, FPS = 1792, 1024, 30


def ease(name: str, u: float) -> float:
    if name == "linear":
        return u
    if name == "70:30":                      # 느리게-빠르게-느리게
        lo, hi = 0.0, 1.0
        for _ in range(24):
            m = (lo + hi) / 2
            x = 3*(1-m)**2*m*0.7 + 3*(1-m)*m*m*0.3 + m**3
            lo, hi = (m, hi) if x < u else (lo, m)
        m = (lo + hi) / 2
        return 3*(1-m)*m*m + m**3
    return u * u * (3 - 2 * u)               # ease


def rect_of(spec: dict, boxes: dict) -> tuple[float, float, float, float]:
    """화각을 사각형으로 푼다. 무엇을 잡든 16:9로 맞춘다."""
    if spec.get("rect"):
        x, y, w, h = [float(v) for v in spec["rect"]]
    elif spec.get("target") in (None, "full"):
        return 0.0, 0.0, float(W), float(H)
    else:
        b = boxes.get(spec["target"])
        if not b:
            return 0.0, 0.0, float(W), float(H)
        # tight = 대상이 화면 세로에서 차지할 비율. 0.55면 전신이 화면의 55%다.
        # 그런데 인물이 크면 그 화각이 캔버스보다 커진다 — 실제로 박정희(626px)에
        # 0.55를 주니 화각 1138px가 되어 화면 밖으로 나갔고, 확대가 아니라 축소가
        # 되며 검은 여백이 생겼다. 그럴 때는 **상반신 화각**으로 바꾼다.
        tight = float(spec.get("tight", 0.6))
        bh = b[3] - b[1]
        h = bh / max(tight, 0.15)
        if h > H:                       # 전신을 다 넣을 수 없다 → 얼굴·가슴을 잡는다
            h = bh * 0.72
            cy = b[1] + bh * 0.30
        else:
            cy = b[1] + bh * 0.35
        cx = (b[0] + b[2]) / 2
        w = h * W / H
        x, y = cx - w/2, cy - h/2
    ar = W / H
    if w / h > ar:
        h = w / ar
    else:
        w = h * ar
    # 화각이 캔버스보다 크면 검은 여백이 생긴다. 넘지 않게 조인다.
    if w > W or h > H:
        k = min(W / w, H / h)
        w, h = w * k, h * k
    x = min(max(x, 0.0), max(W - w, 0.0))
    y = min(max(y, 0.0), max(H - h, 0.0))
    return x, y, w, h


def render_layer(m: dict, w: int, h: int) -> Image.Image:
    if m.get("use_png") or not m.get("svg"):
        return Image.open(m["path"]).convert("RGBA").resize((max(w,1), max(h,1)), Image.LANCZOS)
    pad = m.get("svg_pad")
    if pad:
        px, py, S = pad
        ow, oh = m["bbox"][2]-m["bbox"][0], m["bbox"][3]-m["bbox"][1]
        k = w / ow
        big = cairosvg.svg2png(url=m["svg"], output_width=max(int(S*k),1),
                               output_height=max(int(S*k),1))
        im = Image.open(io.BytesIO(big)).convert("RGBA")
        return im.crop((int(px*k), int(py*k), int((px+ow)*k), int((py+oh)*k))).resize((max(w,1), max(h,1)))
    png = cairosvg.svg2png(url=m["svg"], output_width=max(w,1), output_height=max(h,1))
    return Image.open(io.BytesIO(png)).convert("RGBA")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("layers", type=Path); ap.add_argument("plan", type=Path)
    ap.add_argument("-o", "--out", required=True, type=Path)
    ap.add_argument("--audio", type=Path)
    ap.add_argument("--order", type=Path)
    a = ap.parse_args()

    meta = json.loads(a.layers.read_text(encoding="utf-8"))
    plan = json.loads(a.plan.read_text(encoding="utf-8"))
    boxes = {m["name"]: m["bbox"] for m in meta if m.get("bbox")}
    if a.order and a.order.exists():
        od = json.loads(a.order.read_text(encoding="utf-8"))
        by = {m["name"]: m for m in meta}
        seq = [m for m in meta if not m.get("bbox")] + \
              [by[n] for n in od["order"] if n in by and by[n].get("bbox")]
        people = set(od.get("people") or [])
    else:
        seq = meta
        people = {m["name"] for m in meta if m.get("role") == "person"}

    moves = sorted(plan["moves"], key=lambda m: m["t0"])
    dur = max(m["t1"] for m in moves)
    reveals = {r["layer"]: r for r in plan.get("reveals", [])}

    tmp = a.out.parent / "_camframes"; tmp.mkdir(parents=True, exist_ok=True)
    for f in tmp.glob("*.png"):
        f.unlink()

    for k in range(int(FPS * dur)):
        t = k / FPS
        mv = next((m for m in moves if m["t0"] <= t < m["t1"]), moves[-1])
        u = 0.0 if mv["t1"] <= mv["t0"] else (t - mv["t0"]) / (mv["t1"] - mv["t0"])
        u = ease(mv.get("ease", "ease"), min(max(u, 0.0), 1.0))
        r0, r1 = rect_of(mv.get("from", {}), boxes), rect_of(mv.get("to", {}), boxes)
        vx, vy, vw, vh = [p + (q - p) * u for p, q in zip(r0, r1)]
        s = W / vw
        c = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        for i, m in enumerate(seq):
            bb = m.get("bbox")
            ox, oy = (bb[0], bb[1]) if bb else (0, 0)
            bw, bh = (bb[2]-bb[0], bb[3]-bb[1]) if bb else (W, H)
            if m["name"] in people:
                ph, freq, amp = bob_params(m["name"], i)
                e = (1 - math.cos(2*math.pi*(t*freq) + ph)) / 2
                nh = bh * (1 + amp * e); oy += bh - nh; bh = nh
            layer = render_layer(m, int(round(bw*s)), int(round(bh*s)))
            rv = reveals.get(m["name"])
            if rv:                                   # 정해진 시각에 나타난다
                d = float(rv.get("dur", 0.4))
                p = min(max((t - rv["t"]) / d, 0.0), 1.0)
                if p <= 0:
                    continue
                if p < 1:
                    al = layer.split()[-1].point(lambda v: int(v * p))
                    layer.putalpha(al)
                    if rv.get("type") == "rise":
                        oy += (1 - p) * 24
            c.alpha_composite(layer, (int(round((ox-vx)*s)), int(round((oy-vy)*s))))
        c.convert("RGB").save(tmp / f"{k:04d}.png")
        if k % 60 == 0:
            print(f"  {k}/{int(FPS*dur)}  {mv['type']}  {s:.2f}x", flush=True)

    cmd = ["ffmpeg", "-y", "-framerate", str(FPS), "-i", str(tmp / "%04d.png")]
    if a.audio and a.audio.exists():
        cmd += ["-i", str(a.audio), "-c:a", "aac", "-shortest"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", str(a.out)]
    subprocess.run(cmd, capture_output=True)
    print(f"  → {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
