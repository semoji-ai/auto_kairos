"""중국어판용 세계지도 다시 그리기(원본 그림체·범위 유지, 중국 영토 표현은 중국 관점).
usage: cn_world_map.py <원본 지도 png> <출력 png> [--review 검토용 png] [--countries [--keep x0,y0,x1,y1]]
--countries: 나라별 색칠 + 국경선 지도(예: B019 KFC 진출국 빨강/미진출 검정). 나라 색은 원본에서 그 나라 자리의 다수 색으로 옮김,
             중국(대만·홍콩·마카오 포함)은 대륙 색 하나, 국경선은 원본 선 색 1px. --keep 영역(로고 등)은 원본 그대로
- 데이터: Natural Earth 10m admin-0 worldview CHN(대만·장난·악사이친·西沙·南沙·钓鱼岛가 중국) → data/ne/ 에 받아 둠
- 원본 육지 마스크에 정거원통 투영 축척·위치를 맞춤(모멘트 초기값 + 국소 탐색)
- 국경선 없이 원본 육지색 한 색으로 칠함. 중국 섬(작아서 안 보이는 것 포함)은 최소 점 크기로, 黄岩岛도 표시
- 남해 단속선(9단 + 대만 동쪽 1단 = 10단)을 육지색보다 짙게
자체 심의 항목은 docs/zh/map_self_review.md"""
import json, os, sys, urllib.request, zipfile
import numpy as np
import cv2
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NE = os.path.join(ROOT, "data", "ne")
URL = "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_0_countries_chn.zip"
# 남해 단속선 대략 위치(경도, 위도) — 각 단의 중심과 방향(다음 점 쪽). 지도 축척(약 3px/도)에서 1도 안팎 오차는 보이지 않음
DASHES = [(109.7, 17.4, 109.8, 16.2), (110.0, 13.8, 110.0, 12.6), (109.6, 10.4, 109.9, 9.2), (110.9, 7.3, 111.6, 6.3),
          (112.4, 4.4, 113.4, 4.0), (115.6, 5.9, 116.4, 6.8), (117.5, 9.0, 118.2, 10.0), (119.0, 13.4, 119.2, 14.6),
          (119.5, 18.4, 119.9, 19.6), (123.2, 23.0, 123.4, 24.2)]
SCARBOROUGH = (117.75, 15.15)
_ROB = np.array([[0, 1.0, 0.0], [5, .9986, .0620], [10, .9954, .1240], [15, .9900, .1860], [20, .9822, .2480], [25, .9730, .3100],
                 [30, .9600, .3720], [35, .9427, .4340], [40, .9216, .4958], [45, .8962, .5571], [50, .8679, .6176], [55, .8350, .6769],
                 [60, .7986, .7346], [65, .7597, .7903], [70, .7186, .8435], [75, .6732, .8936], [80, .6213, .9394], [85, .5722, .9761],
                 [90, .5322, 1.0]])
PROJ = ["eq"]                                   # fit()이 원본에 가장 잘 맞는 투영으로 정함


def proj(lon, lat, kind=None):
    """경위도 → 투영 좌표(도 단위 비슷한 크기). eq=정거원통, miller, robinson"""
    kind = kind or PROJ[0]
    lon = np.asarray(lon, float); lat = np.clip(np.asarray(lat, float), -89.9, 89.9)
    if kind == "eq":
        return lon, lat
    if kind == "miller":
        return lon, np.degrees(1.25 * np.log(np.tan(np.pi / 4 + 0.4 * np.radians(lat))))
    a = np.abs(lat)
    X = np.interp(a, _ROB[:, 0], _ROB[:, 1]); Y = np.interp(a, _ROB[:, 0], _ROB[:, 2]) * np.sign(lat)
    return lon * X, Y * 90 * 1.3523 / 1.0


BORDER_OF = []                                  # load_polys 순서대로 각 다각형의 나라 이름(국경 스타일용)
SAME_AS_CHINA = {"Hong Kong S.A.R.", "Macao S.A.R"}   # 국경 틈을 두지 않음


def load_polys():
    shp = os.path.join(NE, "ne_10m_admin_0_countries_chn.shp")
    if not os.path.exists(shp):
        os.makedirs(NE, exist_ok=True)
        z = os.path.join(NE, "chn.zip")
        urllib.request.urlretrieve(URL, z)
        zipfile.ZipFile(z).extractall(NE)
    import shapefile
    out = []
    for sr in shapefile.Reader(shp).iterShapeRecords():
        pts = np.array(sr.shape.points); parts = list(sr.shape.parts) + [len(pts)]
        china = sr.record["SOVEREIGNT"] == "China" or sr.record["ADMIN"] == "Scarborough Reef"
        for a, b in zip(parts[:-1], parts[1:]):
            p = pts[a:b]
            if p[:, 1].max() < -58 or len(p) < 3:
                continue
            out.append((p, china)); BORDER_OF.append(sr.record["ADMIN"])
            if p[:, 0].max() < -160 and p[:, 1].min() > 50:      # 180도 너머 추코트카 끝 → 오른쪽에도
                out.append((p + [360, 0], china)); BORDER_OF.append(sr.record["ADMIN"])
    return out


def land_mask(im):
    if im.mode == "RGBA" and (np.array(im)[:, :, 3] < 10).mean() > 0.3:     # 투명 배경 + 국경 틈 스타일
        a = np.array(im).astype(int)
        m = (a[:, :, 3] > 200).astype(np.uint8)
        land = tuple(int(x) for x in np.median(a[m > 0][:, :3], axis=0))
        return cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)), None, land
    a = np.array(im.convert("RGB")).astype(int)
    sea = a[5, 5]
    land = np.median(a[(np.abs(a - sea).sum(2) > 40)], axis=0)
    m = (((a - land) ** 2).sum(2) < ((a - sea) ** 2).sum(2)).astype(np.uint8)
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)), tuple(int(x) for x in sea), tuple(int(x) for x in land)


def draw(polys, f, w, h, k=1.0, kind=None):
    sx, sy, ox, oy = f
    img = Image.new("L", (w, h), 0); d = ImageDraw.Draw(img)
    for p, _ in polys:
        u, v = proj(p[:, 0], p[:, 1], kind)
        d.polygon(list(zip((u * sx + ox) * k, (-v * sy + oy) * k)), fill=1)
    return np.array(img)


def fit(polys, mask):
    best = None
    for kind in ("eq", "miller", "robinson"):
        f, sc = _fit(polys, mask, kind)
        if best is None or sc > best[1]:
            best = (f, sc, kind)
    PROJ[0] = best[2]
    return best[0], best[1]


def _fit(polys, mask, kind):
    H, W = mask.shape
    g = draw(polys, (4, 4, 720, 400), 1440, 900, 1.0, kind)
    gy, gx = np.nonzero(g); lx, ly = (gx - 720) / 4, -(gy - 400) / 4
    ys, xs = np.nonzero(mask)
    sx, sy = xs.std() / lx.std(), ys.std() / ly.std()
    cur = [sx, sy, xs.mean() - sx * lx.mean(), ys.mean() + sy * ly.mean()]
    small = cv2.resize(mask, (W // 2, H // 2), interpolation=cv2.INTER_NEAREST)
    iou = lambda a: (a & small).sum() / max(1, (a | small).sum())
    sc = iou(draw(polys, cur, W // 2, H // 2, 0.5, kind))
    for step in [(0.02, 6), (0.01, 3), (0.004, 1)]:
        better = True
        while better:
            better = False
            for i, dd in enumerate([step[0], step[0], step[1], step[1]]):
                for sgn in (-1, 1):
                    c = cur[:]; c[i] = c[i] * (1 + sgn * dd) if i < 2 else c[i] + sgn * dd
                    s = iou(draw(polys, c, W // 2, H // 2, 0.5, kind))
                    if s > sc:
                        sc, cur, better = s, c, True
    return cur, sc


def render(polys, f, size, sea, land, line):
    W, H = size
    sx, sy, ox, oy = f
    P = lambda lon, lat: (lambda u, v: (float(u * sx + ox), float(-v * sy + oy)))(*proj(lon, lat))
    if sea is None:                                               # 투명 배경: 나라마다 칠하고 국경은 투명한 틈
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
        landa = land + (255,)
        for p, china in polys:
            d.polygon([P(*q) for q in p], fill=landa)
        for (p, china), name in zip(polys, BORDER_OF):
            if name in SAME_AS_CHINA:
                continue
            q = [P(*v) for v in p]
            d.line(q + [q[0]], fill=(0, 0, 0, 0), width=1)
        for p, china in polys:                                    # 중국 섬 최소 점(국경 틈에 지워지지 않게 마지막에)
            if china:
                x, y = P(*p.mean(0)); d.ellipse([x - 1.3, y - 1.3, x + 1.3, y + 1.3], fill=landa)
        for (p, china), name in zip(polys, BORDER_OF):            # 홍콩·마카오와 대륙 사이 틈 메움
            if name in SAME_AS_CHINA:
                d.polygon([P(*q) for q in p], fill=landa)
        x, y = P(*SCARBOROUGH); d.ellipse([x - 1.3, y - 1.3, x + 1.3, y + 1.3], fill=landa)
        for a, b, c, e in DASHES:
            d.line([P(a, b), P(c, e)], fill=line + (255,), width=2)
        return img
    img = Image.new("RGB", (W, H), sea); d = ImageDraw.Draw(img)
    for p, china in polys:
        q = np.array([P(*x) for x in p])
        area = 0.5 * abs(np.dot(q[:, 0], np.roll(q[:, 1], 1)) - np.dot(q[:, 1], np.roll(q[:, 0], 1)))
        if area < 6 and not china:                               # 원본 그림체처럼 아주 작은 섬은 생략(중국 섬은 예외)
            continue
        d.polygon([tuple(x) for x in q], fill=land)
    r = 1.3                                                      # 중국 섬 최소 점 반지름(px)
    for p, china in polys:
        if china:
            x, y = P(*p.mean(0))
            d.ellipse([x - r, y - r, x + r, y + r], fill=land)
    x, y = P(*SCARBOROUGH); d.ellipse([x - r, y - r, x + r, y + r], fill=land)
    for a, b, c, e in DASHES:
        d.line([P(a, b), P(c, e)], fill=line, width=2)
    return img


def country_mask(im, keep=None):
    """나라별 색 지도: 바다(모서리 색)와 다른 곳 = 육지(국경선 포함). keep 영역은 맞춤에서 뺌."""
    a = np.array(im.convert("RGB")).astype(int)
    sea = a[5, 5]
    m = (np.abs(a - sea).sum(2) > 60).astype(np.uint8)
    if keep:
        x0, y0, x1, y1 = keep; m[y0:y1, x0:x1] = 0
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8)), tuple(int(x) for x in sea), a


def render_countries(polys, f, size, sea, a, keep=None):
    """나라마다 원본 다수 색으로 칠하고 국경선. 반환: (그림, 나라→색, 선 색)"""
    W, H = size
    sx, sy, ox, oy = f
    P = lambda lon, lat: (lambda u, v: (float(u * sx + ox), float(-v * sy + oy)))(*proj(lon, lat))
    land = a[np.abs(a - np.array(sea)).sum(2) > 60]
    dark = land[land.sum(1) < 120]
    line = tuple(int(x) for x in np.median(dark, axis=0)) if len(dark) else (0, 0, 0)
    # 원본 칠 색 후보: 육지 화소 색을 묶어 많이 쓰인 2~3색
    q = (land // 64) * 64 + 32; cols, cnt = np.unique(q, axis=0, return_counts=True)
    pal = [tuple(int(v) for v in c) for c in cols[np.argsort(-cnt)][:2]]
    lab = np.argmin(np.stack([((land - np.array(c)) ** 2).sum(1) for c in pal]), 0)      # 칠 색 = 묶음별 실제 화소 중앙값
    canon = [tuple(int(x) for x in np.median(land[lab == i], axis=0)) for i in range(len(pal))]
    names = {}
    for (p, china), name in zip(polys, BORDER_OF):
        key = "China" if (china or name in SAME_AS_CHINA) else name
        names.setdefault(key, []).append(p)
    colour = {}
    for key, ps in names.items():
        mk = Image.new("L", (W, H), 0); d = ImageDraw.Draw(mk)
        for p in ps:
            d.polygon([P(*x) for x in p], fill=1)
        mk = cv2.erode(np.array(mk), np.ones((3, 3), np.uint8))
        if keep:
            x0, y0, x1, y1 = keep; mk[y0:y1, x0:x1] = 0
        px = a[mk > 0]
        if key == "China":                                       # 대륙 본토 자리 색(대만 등 섬도 같은 색)
            u, v = P(105, 35); px = a[int(v) - 3:int(v) + 4, int(u) - 3:int(u) + 4].reshape(-1, 3)
        if len(px) < 3:
            continue
        dist = [((px - np.array(c)) ** 2).sum(1) for c in pal]
        idx = np.argmin(np.stack(dist), 0)
        colour[key] = canon[int(np.bincount(idx, minlength=len(pal)).argmax())]
    fill_default = min(canon, key=sum)                           # 알 수 없는 작은 나라: 어두운 색(원본 미표시국)
    img = Image.new("RGB", (W, H), sea); d = ImageDraw.Draw(img)
    for key, ps in names.items():
        for p in ps:
            q2 = [P(*x) for x in p]
            qa = np.array(q2); area = 0.5 * abs(np.dot(qa[:, 0], np.roll(qa[:, 1], 1)) - np.dot(qa[:, 1], np.roll(qa[:, 0], 1)))
            if area < 2 and key != "China":
                continue
            d.polygon(q2, fill=colour.get(key, fill_default), outline=line)
    china_col = colour["China"]
    r = 1.3
    for p, china in polys:                                       # 중국 섬 최소 점(작아서 안 보이는 섬만)
        if china:
            qa = np.array([P(*x) for x in p]); area = 0.5 * abs(np.dot(qa[:, 0], np.roll(qa[:, 1], 1)) - np.dot(qa[:, 1], np.roll(qa[:, 0], 1)))
            if area < 6:
                x, y = P(*p.mean(0)); d.ellipse([x - r, y - r, x + r, y + r], fill=china_col, outline=line)
    x, y = P(*SCARBOROUGH); d.ellipse([x - r, y - r, x + r, y + r], fill=china_col, outline=line)
    for (p, china), name in zip(polys, BORDER_OF):              # 홍콩·마카오: 대륙과 같은 색, 경계선 없이
        if name in SAME_AS_CHINA:
            d.polygon([P(*x) for x in p], fill=china_col)
    for a_, b_, c_, e_ in DASHES:
        d.line([P(a_, b_), P(c_, e_)], fill=line, width=2)
    return img, colour, line, china_col


def checks(img, f, land, line):
    """자체 심의 자동 점검: 각 요소 위치에 육지색/단속선 색이 칠해졌는지."""
    a = np.array(img).astype(int)
    sx, sy, ox, oy = f
    def at(lon, lat, col, rad=2):
        u, v = proj(lon, lat)
        x, y = int(round(float(u) * sx + ox)), int(round(float(-v) * sy + oy))
        win = a[max(0, y - rad):y + rad + 1, max(0, x - rad):x + rad + 1]
        return bool((np.abs(win - np.array(col)).sum(2) < 30).any())
    res = {"台湾岛": at(121.0, 23.7, land), "海南岛": at(109.8, 19.2, land), "西沙群岛": at(112.3, 16.5, land),
           "南沙群岛": at(114.3, 10.0, land), "黄岩岛": at(*SCARBOROUGH, land), "钓鱼岛": at(123.5, 25.75, land),
           "藏南(中国境内,无国界线)": at(93.5, 28.0, land), "阿克赛钦": at(79.5, 35.2, land)}
    res.update({f"南海断续线 第{i + 1}段": at((d[0] + d[2]) / 2, (d[1] + d[3]) / 2, line, 3) for i, d in enumerate(DASHES)})
    return res


if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    im = Image.open(src)
    if "--countries" in sys.argv:
        keep = tuple(int(v) for v in sys.argv[sys.argv.index("--keep") + 1].split(",")) if "--keep" in sys.argv else None
        mask, sea, a = country_mask(im, keep)
        polys = load_polys()
        f, sc = fit(polys, mask)
        img, colour, line, china_col = render_countries(polys, f, im.size, sea, a, keep)
        if keep:
            x0, y0, x1, y1 = keep; img.paste(im.convert("RGB").crop(keep), (x0, y0))
        img.save(out)
        res = checks(img, f, china_col, line)
        print(json.dumps({"proj": PROJ[0], "fit_iou": round(float(sc), 3), "fit": [round(x, 4) for x in f], "line": line,
                          "colours": {k: v for k, v in sorted(colour.items())}, "checks": res}, ensure_ascii=False, indent=1))
        if "--review" in sys.argv:
            sx, sy, ox, oy = f
            (u0, v0), (u1, v1) = [tuple(map(float, proj(a_, b_))) for a_, b_ in ((70, 45), (135, 2))]
            x0, x1 = int(u0 * sx + ox), int(u1 * sx + ox); y0, y1 = int(-v0 * sy + oy), int(-v1 * sy + oy)
            img.crop((x0, y0, x1, y1)).resize(((x1 - x0) * 5, (y1 - y0) * 5), Image.NEAREST).save(sys.argv[sys.argv.index("--review") + 1])
        if not all(res.values()):
            sys.exit("자체 심의 자동 점검 실패: " + ", ".join(k for k, v in res.items() if not v))
        sys.exit(0)
    mask, sea, land = land_mask(im)
    polys = load_polys()
    f, sc = fit(polys, mask)
    line = tuple(max(0, int(c * 0.55)) for c in land)
    img = render(polys, f, im.size, sea, land, line)
    if im.mode == "RGBA" and sea is not None:
        img = img.convert("RGBA"); img.putalpha(im.getchannel("A"))
    img.save(out)
    res = checks(img.convert("RGB"), f, land, line)
    print(json.dumps({"proj": PROJ[0], "fit_iou": round(float(sc), 3), "fit": [round(x, 4) for x in f], "checks": res}, ensure_ascii=False, indent=1))
    if "--review" in sys.argv:
        sx, sy, ox, oy = f
        (u0, v0), (u1, v1) = [tuple(map(float, proj(a_, b_))) for a_, b_ in ((100, 30), (130, 2))]
        x0, x1 = int(u0 * sx + ox), int(u1 * sx + ox); y0, y1 = int(-v0 * sy + oy), int(-v1 * sy + oy)
        crop = img.convert("RGB").crop((x0, y0, x1, y1)).resize(((x1 - x0) * 8, (y1 - y0) * 8), Image.NEAREST)
        crop.save(sys.argv[sys.argv.index("--review") + 1])
    if not all(res.values()):
        sys.exit("자체 심의 자동 점검 실패: " + ", ".join(k for k, v in res.items() if not v))
