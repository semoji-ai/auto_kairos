"""일러스트·이미지 속 글자 교체: 글자+그림자를 RGBA 배경 추정으로 지우고, 원래 색·기울기로 새 문구를 그린다."""
import math
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont, TTCollection

_cmaps = {}


def quad_geom(q):
    """사변형(왼위, 오위, 오아, 왼아) → (각도°, 폭, 높이, 중심x, 중심y)."""
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = q
    ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
    w = math.hypot(x1 - x0, y1 - y0)
    h = math.hypot(x3 - x0, y3 - y0)
    return ang, w, h, (x0 + x1 + x2 + x3) / 4, (y0 + y1 + y2 + y3) / 4


def _region(shape, quad, sx=1.12, sy=1.5):
    q = np.array(quad, np.float32)
    c = q.mean(0)
    ang, w, h, _, _ = quad_geom(quad)
    # 글자 방향 기준으로 넓힘(가로 sx, 세로 sy)
    ux = np.array([math.cos(math.radians(ang)), math.sin(math.radians(ang))])
    uy = np.array([-ux[1], ux[0]])
    rel = q - c
    qq = c + np.outer(rel @ ux * sx, ux) + np.outer(rel @ uy * sy, uy)
    m = np.zeros(shape, np.uint8)
    cv2.fillPoly(m, [qq.astype(np.int32)], 255)
    return m > 0


def _background(rgba, h):
    """글자 높이보다 큰 창의 중간값 필터(1/4 축소)로 RGBA 배경 추정."""
    kz = max(3, int(h * 1.6 / 4) | 1)
    H, W = rgba.shape[:2]
    small = cv2.resize(rgba, (max(1, W // 4), max(1, H // 4)), interpolation=cv2.INTER_AREA)
    bgs = np.dstack([cv2.medianBlur(np.ascontiguousarray(small[:, :, i]), kz) for i in range(4)])
    return cv2.resize(bgs, (W, H), interpolation=cv2.INTER_LINEAR).astype(int)


def erase_text(rgba, quad):
    """→ (지운 RGBA, 글자색 목록(많은 순), 두 색 강조 여부)."""
    rgba = rgba.copy()
    H, W = rgba.shape[:2]
    _, w, h, _, _ = quad_geom(quad)
    region = _region((H, W), quad)
    bg = _background(rgba, h)
    cur = rgba.astype(int)
    a = rgba[:, :, 3]
    pm = lambda x: x[:, :, :3] * x[:, :, 3:4] / 255.0
    diff = np.abs(pm(cur) - pm(bg)).sum(2) + np.abs(cur[:, :, 3] - bg[:, :, 3]) * 1.5
    inside = cv2.erode((bg[:, :, 3] > 128).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    txt = region & (diff > 45) & inside
    cdiff = np.abs(cur[:, :, :3] - bg[:, :, :3]).sum(2)
    strong = region & inside & (cdiff > 180) & (a > 200)
    cols = rgba[:, :, :3][strong] if strong.sum() > 30 else rgba[:, :, :3][txt & (a > 128)]
    colors, two = [(255, 255, 255)], False
    sel = strong if strong.sum() > 30 else (txt & (a > 128))
    if len(cols) > 0:
        Z = cols.astype(np.float32)
        k = 2 if len(Z) > 50 else 1
        _, lab, cen = cv2.kmeans(Z, k, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0), 3,
                                 cv2.KMEANS_PP_CENTERS)
        counts = np.bincount(lab.ravel(), minlength=k)
        colors = [tuple(int(v) for v in cen[i]) for i in np.argsort(-counts)]
        if k == 2 and min(counts) / max(counts) > 0.15 and np.abs(cen[0] - cen[1]).sum() > 150:
            # 두 색이 글자 방향으로 갈려 있어야 강조(앞/뒤 구간). 섞여 있으면 외곽선·그림자.
            ys, xs = np.where(sel)
            ang = math.radians(quad_geom(quad)[0])
            proj = xs * math.cos(ang) + ys * math.sin(ang)
            lab = lab.ravel()
            p0, p1 = proj[lab == 0], proj[lab == 1]
            if len(p0) and len(p1):
                overlap = max(0.0, min(np.percentile(p0, 90), np.percentile(p1, 90)) - max(np.percentile(p0, 10), np.percentile(p1, 10)))
                span = max(1.0, np.percentile(proj, 98) - np.percentile(proj, 2))
                two = overlap < span * 0.15
    inside2 = cv2.erode((a > 200).astype(np.uint8), np.ones((3, 3), np.uint8)) | inside.astype(np.uint8)
    mask = (cv2.dilate(txt.astype(np.uint8) * 255, np.ones((5, 5), np.uint8), iterations=2) * (inside2 > 0)).astype(np.uint8)
    a2 = np.where((mask > 0) & inside, bg[:, :, 3], a).astype(np.uint8)
    fill = rgba[:, :, :3].copy()
    fill[a2 < 30] = bg[:, :, :3][a2 < 30]
    rgb = cv2.inpaint(fill.astype(np.uint8), mask, 7, cv2.INPAINT_TELEA)
    return np.dstack([rgb, a2]).astype(np.uint8), colors, bool(two)


def _cmap(font_path):
    if font_path not in _cmaps:
        if font_path.lower().endswith(".ttc"):
            f = TTCollection(font_path).fonts[0]
        else:
            f = TTFont(font_path)
        _cmaps[font_path] = set(f.getBestCmap().keys())
    return _cmaps[font_path]


def missing_glyphs(text, font_path):
    cm = _cmap(font_path)
    return sorted({ch for ch in text.replace("[[", "").replace("]]", "") if not ch.isspace() and ord(ch) not in cm})


def _font(path, size, index=0):
    return ImageFont.truetype(path, size, index=index)


def draw_text(rgba, quad, text, colors, two_tone, font_path, size_ratio=0.72, font_index=0):
    """quad 중심·각도에 맞춰 text를 그린다. [[…]] 부분은 강조색(두 색 중 채도 높은 쪽)."""
    ang, w, h, cx, cy = quad_geom(quad)
    parts = [(t, i % 2) for i, t in enumerate(text.replace("]]", "[[").split("[["))] if "[[" in text else [(text, 0)]
    plain = "".join(t for t, _ in parts)
    size = max(6, int(h * size_ratio))
    font = _font(font_path, size, font_index)
    while font.getlength(plain) > w * 0.98 and size > 6:
        size -= 1
        font = _font(font_path, size, font_index)
    sat = lambda c: max(c) - min(c)
    if two_tone and len(colors) > 1:
        emph, base = (colors[0], colors[1]) if sat(colors[0]) >= sat(colors[1]) else (colors[1], colors[0])
    else:
        emph = base = colors[0]
    tw = int(font.getlength(plain)) + 8
    th = int(size * 1.5)
    layer = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    dr = ImageDraw.Draw(layer)
    x = 4
    for t, e in parts:
        dr.text((x, th / 2), t, font=font, fill=(emph if e else base) + (255,), anchor="lm")
        x += font.getlength(t)
    layer = layer.rotate(-ang, expand=True, resample=Image.BICUBIC)
    out = Image.fromarray(rgba.copy())
    out.alpha_composite(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)))
    return np.array(out)


def replace_items(png_in, png_out, items, font_path, font_index=0):
    """items: [{"quad", "en"}] → 지우고 그린 PNG 저장."""
    arr = np.array(Image.open(png_in).convert("RGBA"))
    for it in items:
        arr, colors, two = erase_text(arr, it["quad"])
        arr = draw_text(arr, it["quad"], it["en"], colors, two, font_path, font_index=font_index)
    Image.fromarray(arr).save(png_out)
