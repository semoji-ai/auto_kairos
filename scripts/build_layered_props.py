#!/usr/bin/env python3
"""layers.json + 카메라 계획 → Remotion LayeredScene props.

파이썬 렌더러가 하던 계산 중 **결정적인 부분만** 남겨 넘긴다.
발 축·벡터 확대는 브라우저가 CSS로 하므로 여기서 계산하지 않는다.

레이어 파일은 remotion/public 아래로 복사한다 — staticFile()이 그 안만 본다.

    python3 scripts/build_layered_props.py <layers.json> <cam_plan.json> -o props.json \
        --audio <mp3> --name s041
"""
from __future__ import annotations
import argparse, json, math, random, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "remotion" / "public"


def bob(name: str, idx: int) -> dict:
    """인물마다 위상·주기·폭을 흩는다. 이름을 씨앗으로 삼아 재현 가능하게."""
    r = random.Random(f"{name}:{idx}")
    return {"phase": r.uniform(0, 2 * math.pi),
            "period": r.uniform(0.5, 0.85),
            "amp": r.uniform(0.007, 0.013)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("layers", type=Path)
    ap.add_argument("plan", type=Path, nargs="?")
    ap.add_argument("-o", "--out", required=True, type=Path)
    ap.add_argument("--audio", type=Path)
    ap.add_argument("--name", required=True, help="public/layers/<name>/ 아래로 복사")
    ap.add_argument("--order", type=Path)
    ap.add_argument("--canvas", default="1792x1024")
    a = ap.parse_args()

    W, H = (int(x) for x in a.canvas.split("x"))
    meta = json.loads(a.layers.read_text(encoding="utf-8"))
    by = {m["name"]: m for m in meta}
    if a.order and a.order.exists():
        od = json.loads(a.order.read_text(encoding="utf-8"))
        seq = [m for m in meta if not m.get("bbox")] + \
              [by[n] for n in od["order"] if n in by and by[n].get("bbox")]
        people = set(od.get("people") or [])
    else:
        seq = meta
        people = {m["name"] for m in meta if m.get("role") == "person"}

    dst_dir = PUBLIC / "layers" / a.name
    dst_dir.mkdir(parents=True, exist_ok=True)
    layers = []
    for i, m in enumerate(seq):
        # 벡터가 있고 use_png가 아니면 SVG를 쓴다 — 확대해도 브라우저가 다시 그린다
        src = Path(m["svg"]) if (m.get("svg") and not m.get("use_png")) else Path(m["path"])
        out = dst_dir / f"{i:02d}{src.suffix}"
        shutil.copy2(src, out)
        L = {"name": m["name"], "src": f"layers/{a.name}/{out.name}",
             "role": "person" if m["name"] in people else ("bg" if not m.get("bbox") else "prop")}
        if m.get("bbox"):
            x0, y0, x1, y1 = m["bbox"]
            L["bbox"] = [x0, y0, x1 - x0, y1 - y0]
        # 까딱임은 **적힌 의도**가 먼저다(`motion: "bob"`). 인물이라고 다 까딱이는
        # 것은 아니고, 앉아 있거나 등을 돌린 인물은 까딱이면 어색하다.
        # motion 이 아예 없는 옛 메타는 예전대로 role 로 판정한다.
        if m.get("motion") == "bob" or ("motion" not in m and L["role"] == "person"):
            L["bob"] = bob(m["name"], i)
        layers.append(L)

    camera = []
    if a.plan and a.plan.exists():
        for mv in sorted(json.loads(a.plan.read_text(encoding="utf-8"))["moves"],
                         key=lambda x: x["t0"]):
            if not camera:
                camera.append({"t": mv["t0"], "rect": mv["from_rect"]})
            camera.append({"t": mv["t1"], "rect": mv["to_rect"], "ease": mv.get("ease", "ease")})

    props = {"scene": {"width": W, "height": H}, "layers": layers, "camera": camera}
    if a.audio and a.audio.exists():
        ad = PUBLIC / "layers" / a.name / a.audio.name
        shutil.copy2(a.audio, ad)
        props["audioSrc"] = f"layers/{a.name}/{a.audio.name}"
    if camera:
        props["durationSec"] = camera[-1]["t"]
    a.out.write_text(json.dumps(props, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  레이어 {len(layers)} / 카메라 키 {len(camera)} → {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
