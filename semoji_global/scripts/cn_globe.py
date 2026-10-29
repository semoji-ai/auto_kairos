"""중국어판용 지구본 다시 그리기: 원본 지구본의 바다 명암·하이라이트 띠·그림자 그림체는 유지하고, 육지만 중국 관점 데이터로 정사(구면) 투영.
usage: cn_globe.py <원본 지구본 png> <출력 png> [--center lon,lat] [--review 검토용 png]
- 원본 지구본은 손으로 다듬은 그림이라 대만·하이난·필리핀이 빠져 있고 덧그리면 해안선이 겹침(실측) → 육지 전체를 새로
- 바다: 원본 육지를 지우고(inpaint) 남은 바다 명암 사용
- 육지색: 원본 육지 픽셀에서 '그 자리 바다 밝기 → 육지색' 관계를 배워 하이라이트 띠 안팎 색을 재현, 그림자는 오른쪽 아래
- 중국 섬(작아도) 최소 점, 黄岩岛, 남해 단속선 10단
점검 항목은 docs/zh/map_self_review.md"""
import json, os, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cn_world_map import load_polys, DASHES, SCARBOROUGH


def land_of(a):
    return (a[:, :, 1] > a[:, :, 0] + 40) & (a[:, :, 1] > a[:, :, 2] + 20) & (a[:, :, 3] > 200)


def ortho(lon, lat, lon0, lat0):
    lo, la, l0, a0 = map(np.radians, (lon, lat, lon0, lat0))
    x = np.cos(la) * np.sin(lo - l0)
    y = np.cos(a0) * np.sin(la) - np.sin(a0) * np.cos(la) * np.cos(lo - l0)
    vis = np.sin(a0) * np.sin(la) + np.cos(a0) * np.cos(la) * np.cos(lo - l0) > 0
    return x, y, vis


def densify(p, step=0.5):
    out = [p[0]]
    for a, b in zip(p[:-1], p[1:]):
        n = int(max(abs(b[0] - a[0]), abs(b[1] - a[1])) / step)
        for k in range(1, n + 1):
            out.append(a + (b - a) * k / (n + 1))
        out.append(b)
    return np.array(out)


if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    lon0, lat0 = [float(v) for v in sys.argv[sys.argv.index("--center") + 1].split(",")] if "--center" in sys.argv else (75.0, 22.0)
    a = np.array(Image.open(src).convert("RGBA")).astype(np.uint8)
    H, W = a.shape[:2]
    disk = a[:, :, 3] > 200
    ys, xs = np.nonzero(disk)
    cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
    R = (xs.max() - xs.min()) / 2 * 0.985
    land = land_of(a.astype(int))
    grow = cv2.dilate(land.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0     # 그림자 띠까지
    seapx = disk & ~grow
    # 바다색·밝기 = 바다 픽셀만으로 정규화 블러 보간(원 밖 투명 픽셀이 섞여 가장자리가 검어지지 않게, 하이라이트 띠 유지)
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    from sg.plate import _gblur
    wgt = seapx.astype(np.float32)
    sea = np.zeros((H, W, 3), np.float32)
    for sig in (6, 20, 60, 200):
        wb = _gblur(wgt, sig); vb = _gblur(a[:, :, :3].astype(np.float32) * wgt[:, :, None], sig)
        ok = (wb > 0.05) & (sea.sum(2) == 0)
        sea[ok] = vb[ok] / wb[ok][:, None]
    sea[seapx] = a[:, :, :3][seapx]
    sea = sea.astype(np.uint8)
    # 바다 밝기 → 육지색 (하이라이트 띠 안팎)
    br = sea.astype(float).mean(2)
    lx = br[land]; ly = a[:, :, :3][land].astype(float)
    A = np.c_[lx, np.ones_like(lx)]
    coef = np.linalg.lstsq(A, ly, rcond=None)[0]                                  # (2,3)
    shadow = np.percentile(a[:, :, :3][land & ~cv2.erode(land.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)], 10, axis=0)
    shadow = np.minimum(np.percentile(ly, 2, axis=0), shadow)
    # 새 육지 마스크
    m = Image.new("L", (W, H), 0); dm = ImageDraw.Draw(m)
    P = lambda x, y: (cx + x * R, cy - y * R)
    polys = load_polys()
    for p, china in polys:
        q = densify(p)
        x, y, vis = ortho(q[:, 0], q[:, 1], lon0, lat0)
        if vis.mean() < 0.02:
            continue
        # 뒷면 점은 가장자리로 당김(원 밖으로 안 나가게)
        r = np.hypot(x, y); x = np.where(vis, x, x / np.maximum(r, 1e-9)); y = np.where(vis, y, y / np.maximum(r, 1e-9))
        pts = [P(*v) for v in zip(x, y)]
        if len(pts) >= 3:
            dm.polygon(pts, fill=255)
        if china and vis.all():
            ccx, ccy = P(x.mean(), y.mean()); dm.ellipse([ccx - 2.2, ccy - 2.2, ccx + 2.2, ccy + 2.2], fill=255)
    for lon, lat in [SCARBOROUGH]:
        x, y, v = ortho(np.array([lon]), np.array([lat]), lon0, lat0)
        if v[0]:
            px, py = P(x[0], y[0]); dm.ellipse([px - 2.2, py - 2.2, px + 2.2, py + 2.2], fill=255)
    nl = (np.array(m) > 127) & disk
    off = max(3, int(round(W / 260)))
    sh = np.zeros_like(nl); sh[off:, off:] = nl[:-off, :-off]; sh &= disk & ~nl
    res = a.copy()
    res[:, :, :3][disk] = sea[disk]
    res[:, :, :3][sh] = shadow.astype(np.uint8)
    col = np.clip(np.c_[br[nl], np.ones(nl.sum())] @ coef, 0, 255).astype(np.uint8)
    res[:, :, :3][nl] = col
    # 단속선: 해안 그림자(짙은 초록)와 구분되게 바다색을 크게 어둡게 한 남색
    line = tuple(int(c * 0.4) for c in np.median(a[:, :, :3][seapx], axis=0)) + (255,)
    img = Image.fromarray(res); d = ImageDraw.Draw(img)
    for la, lb, lc, ld in DASHES:
        x, y, v = ortho(np.array([la, lc]), np.array([lb, ld]), lon0, lat0)
        if v.all():
            d.line([P(x[0], y[0]), P(x[1], y[1])], fill=line, width=max(2, off - 1))
    img.save(out)
    o = np.array(img).astype(int)
    def at(lon, lat):
        x, y, v = ortho(np.array([lon]), np.array([lat]), lon0, lat0)
        px, py = P(x[0], y[0]); r = 7                     # 작은 섬은 실제 섬 위치에 점 → 반경 안에서 확인
        return bool(v[0] and land_of(o)[int(py) - r:int(py) + r + 1, int(px) - r:int(px) + r + 1].any())
    checks = {"台湾岛": at(121.0, 23.7), "海南岛": at(109.8, 19.2), "西沙群岛": at(112.3, 16.5), "南沙群岛": at(114.3, 10.0),
              "钓鱼岛": at(123.5, 25.75), "黄岩岛": at(*SCARBOROUGH), "藏南": at(93.5, 28.0), "阿克赛钦": at(79.5, 35.2)}
    print(json.dumps({"center": [lon0, lat0], "checks": checks}, ensure_ascii=False))
    if "--review" in sys.argv:
        x, y, _ = ortho(np.array([100.0, 130.0]), np.array([35.0, 3.0]), lon0, lat0)
        (x0, y0), (x1, y1) = P(x[0], y[0]), P(x[1], y[1])
        img.crop((int(x0), int(y0), int(x1), int(y1))).resize((int(x1 - x0) * 3, int(y1 - y0) * 3), Image.NEAREST)\
            .save(sys.argv[sys.argv.index("--review") + 1])
    if not all(checks.values()):
        sys.exit("자체 심의 점검 실패: " + ", ".join(k for k, v in checks.items() if not v))
