"""레이어 빗금 제거 — 사내 벡터라이저(~/Projects/vectorizer)로 레이어를 벡터화해 면을 단색으로 만든다.

codex 재드로잉 에셋에는 대각선 빗금 결이 남는다. 벡터화하면 각 면이 한 색 path가 되어
결이 구조적으로 사라진다. 레시피(벡터라이저 메모): 크로마 그린 합성 → mean-shift 평탄화 →
UP배 LANCZOS → planar 벡터화 → 크로마 path 삭제 → 목표 해상도로 래스터화.
    ~/Projects/vectorizer/.venv/bin/python vectorize_layers.py <in.png|jpg> <out.png> [--bg]
"""
import sys
from pathlib import Path

import cairosvg
import cv2
import numpy as np
from PIL import Image

VEC = Path.home() / "Projects/vectorizer"
sys.path.insert(0, str(VEC))
from vectorizer.engine import VectorizeParams, simplify_palette  # noqa: E402
from scripts.compose_layers import components_for, emit_group, flatten_texture  # noqa: E402

CHROMA = np.array([0.0, 177.0, 64.0])
UP = 2
OUT_W = 1920


def vectorize(src: Path, dst: Path, is_bg: bool):
    im = Image.open(src)
    W, H = im.size
    if is_bg:
        rgb = np.asarray(im.convert("RGB"))
        x0, y0, x1, y1 = 0, 0, W, H
        crop = rgb
        keep = None
    else:
        rgba = np.asarray(im.convert("RGBA"))
        a = rgba[..., 3]
        ys, xs = np.nonzero(a > 20)
        x0, y0 = max(0, xs.min() - 6), max(0, ys.min() - 6)
        x1, y1 = min(W, xs.max() + 7), min(H, ys.max() + 7)
        sub = rgba[y0:y1, x0:x1].astype(float)
        al = sub[..., 3:] / 255.0
        crop = (sub[..., :3] * al + CHROMA * (1 - al)).astype(np.uint8)
        keep = a[y0:y1, x0:x1] > 127
    flat = flatten_texture(crop, sp=8, sr=22)
    big = np.asarray(Image.fromarray(flat).resize((flat.shape[1] * UP, flat.shape[0] * UP), Image.LANCZOS))
    params = VectorizeParams(planar=True, smooth_sigma=1.2, fit_error=1.0,
                             min_area=(40 if is_bg else 14) * UP, min_width=0.0,
                             missed_err_threshold=16.0, quant_error_target=6.0, gradients=False)
    km = None
    if keep is not None:
        km = np.asarray(Image.fromarray(keep.astype(np.uint8) * 255).resize((big.shape[1], big.shape[0]), Image.NEAREST)) > 127
    comps = components_for(big, params, keep_mask=km, affine=(1 / UP, x0, y0))
    if not is_bg:
        comps = [c for c in comps if np.linalg.norm(np.array(c.color, float) - CHROMA) > 60]
    simplify_palette(comps)
    lines, defs, idx = [], [], [0]
    emit_group(comps, params, "layer", "", lines, defs, idx)
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    if defs:
        svg.append("<defs>" + "".join(defs) + "</defs>")
    svg += lines + ["</svg>"]
    svg_s = "\n".join(svg)
    dst.with_suffix(".svg").write_text(svg_s)
    out_h = round(OUT_W * H / W)
    png = cairosvg.svg2png(bytestring=svg_s.encode(), output_width=OUT_W, output_height=out_h)
    dst.write_bytes(png)
    if not is_bg:
        # 가장자리 AA: 원본 알파의 부드러운 외곽을 살린다(벡터 경계 × 원본 알파 확대본)
        v = np.asarray(Image.open(dst).convert("RGBA")).copy()
        a_src = np.asarray(Image.fromarray(np.asarray(im.convert("RGBA"))[..., 3]).resize((OUT_W, out_h), Image.LANCZOS))
        v[..., 3] = np.minimum(v[..., 3], a_src)
        Image.fromarray(v).save(dst)
    else:
        Image.open(dst).convert("RGB").save(dst.with_suffix(".jpg"), quality=94)
    print(dst.name, len(comps), "paths")


if __name__ == "__main__":
    vectorize(Path(sys.argv[1]), Path(sys.argv[2]), "--bg" in sys.argv)
