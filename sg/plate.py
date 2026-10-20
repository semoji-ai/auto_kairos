"""글자 없는 판 만들기: 글자 영역을 판의 색(단색/그라데이션)으로 채운다. 인페인팅·투명도 추정 없음.
새 글자는 AE 텍스트 레이어로 올린다(text_style이 위치·각도·색을 준다)."""
import math
import numpy as np
import cv2
from sg.raster import quad_geom, _region, _background


def unpremultiply(rgba):
    """AE 'TIFF with Alpha'는 검정 매트 프리멀티플라이드 → 일반(straight) 알파로."""
    a = rgba[:, :, 3:4].astype(np.float32)
    rgb = np.where(a > 0, rgba[:, :, :3].astype(np.float32) * 255.0 / np.maximum(a, 1), 0)
    return np.dstack([np.clip(np.round(rgb), 0, 255), rgba[:, :, 3:4]]).astype(np.uint8)


def _axes(quad):
    ang, w, h, cx, cy = quad_geom(quad)
    ux = np.array([math.cos(math.radians(ang)), math.sin(math.radians(ang))])
    uy = np.array([-ux[1], ux[0]])
    return ang, w, h, np.array([cx, cy]), ux, uy


def clean_plate(rgba, quad, pad_x=0.5, pad_y=0.3):
    """글자 영역을 판 색으로 채운 RGBA. 판 색은 판 그룹 픽셀만으로 2차원 보간(그라데이션·글로우 유지),
    지우는 것은 대부분이 글자 영역 안에 있는 덩어리뿐(테두리·이웃 줄 보존). 받침판 없는 글자는 투명으로."""
    out = rgba.copy()
    H, W = rgba.shape[:2]
    ang, w, h, c, ux, uy = _axes(quad)
    region = _region((H, W), quad, pad_x, pad_y)
    yy, xx = np.mgrid[:H, :W]
    u = (xx - c[0]) * ux[0] + (yy - c[1]) * ux[1]          # 글자 방향 좌표
    v = (xx - c[0]) * uy[0] + (yy - c[1]) * uy[1]          # 수직 방향 좌표
    # 판 샘플: 글자 사각형(약간 넓힘)과 바로 바깥 링의 픽셀을 색으로 3그룹 → 바깥 링과 가장 가까운 그룹 = 판
    core = _region((H, W), quad, 0.15, 0.1)
    ring = _region((H, W), quad, 0.5, 0.35) & ~core
    pool = core | ring
    # 색 그룹: 불투명 픽셀은 RGB(투명도 무시 → 그라데이션 바가 여러 그룹으로 쪼개지지 않음)로 k-means, 투명 픽셀은 별도 그룹
    P_rgba = rgba[pool]
    opq = P_rgba[:, 3] > 20
    k_op = 3 if opq.sum() > 300 else (2 if opq.sum() > 20 else 1)
    k = k_op + 1
    lab = np.full(len(P_rgba), k_op, np.int32)
    if opq.sum() > 0:
        if k_op > 1:
            _, lo_, _ = cv2.kmeans(P_rgba[opq][:, :3].astype(np.float32), k_op, None,
                                   (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0), 3, cv2.KMEANS_PP_CENTERS)
            lab[opq] = lo_.ravel()
        else:
            lab[opq] = 0
    # 후보 = 글자 사각형 안에 15% 이상 있는 그룹(링이 전부 투명한 얇은 띠에서 투명 그룹이 이기지 않게)
    cl = lab[core[pool]]
    cf = np.bincount(cl, minlength=k) / max(1, len(cl))
    cand = [ci for ci in range(k) if cf[ci] >= 0.15] or list(range(k))
    # 판 = 크게 이어진 덩어리를 가진 그룹들(가장 큰 것의 절반 이상). 그라데이션이 두 그룹으로 갈려도 함께 판이 되고,
    # 글자 획·그림자는 글자마다 끊겨 작음
    bigs = {}
    for ci in cand:
        m = np.zeros((H, W), np.uint8); m[pool] = (lab == ci)
        n, _, st, _ = cv2.connectedComponentsWithStats(m, 8)
        bigs[ci] = st[1:, cv2.CC_STAT_AREA].max() if n > 1 else 0
    top = max(bigs.values())
    plates = [ci for ci in cand if bigs[ci] >= 0.5 * top]
    plate_px = np.zeros((H, W), bool); plate_px[pool] = np.isin(lab, plates)
    # 받침판 없는 글자: 글자 사각형 안 투명이 15%↑이고 바깥 링이 대부분 투명(또는 링이 없음) → 판 = 투명
    rt = (rgba[ring][:, 3] <= 20).mean() if ring.sum() >= 0.05 * pool.sum() else 1.0
    if cf[k_op] >= 0.15 and rt >= 0.6:
        plate_px = np.zeros((H, W), bool); plate_px[pool] = lab == k_op
    a = rgba[:, :, 3]
    a = rgba[:, :, 3]
    # 국소 대비(국소 중간값과의 차이): 판의 완만한 변화와 글자 획을 가르는 데 씀
    bgm = _background(rgba, h).astype(np.float32)
    pmc = rgba[:, :, :3].astype(np.float32) * (a[:, :, None] / 255.0)
    pmb = bgm[:, :, :3] * (bgm[:, :, 3:4] / 255.0)
    loc = np.abs(pmc - pmb).sum(2) + np.abs(a.astype(np.float32) - bgm[:, :, 3]) * 1.5
    # 판 안쪽만 고친다: 판 테두리(두께 h*0.15)는 건드리지 않음
    plate_opaque = a > 20
    ke = max(3, int(h * 0.15) | 1)
    interior = cv2.erode(plate_opaque.astype(np.uint8), np.ones((ke, ke), np.uint8)) > 0
    # 판 색 = 판 픽셀만으로 2차원 정규화 블러 보간(가로·세로 그라데이션, 원형 글로우 모두). 작은 반경부터 채움.
    # 두 번: 첫 추정과 크게 다른 판 샘플(같은 색 그룹에 섞인 그림자·안티에일리어싱)을 빼고 다시
    af = a.astype(np.float32)[:, :, None] / 255.0
    val = np.dstack([rgba[:, :, :3].astype(np.float32) * af, a.astype(np.float32)[:, :, None]])

    def interp(mask):
        wk = mask.astype(np.float32)
        f = np.zeros((H, W, 4), np.float32); g = np.zeros((H, W), bool)
        sigs = (0.15, 0.3, 0.6, 1.2, 2.4, 5.0)
        for i, sg_ in enumerate(sigs):
            sig = max(1.0, h * sg_)
            wb = cv2.GaussianBlur(wk, (0, 0), sig)
            vb = cv2.GaussianBlur(val * wk[:, :, None], (0, 0), sig)
            ok = (wb > (0.08 if i < len(sigs) - 1 else 1e-6)) & ~g
            f[ok] = vb[ok] / wb[ok][:, None]; g |= ok
        return f, g

    band = plate_px
    fill, got = interp(band)
    if not got.any():
        return out
    err = np.abs(val - fill).sum(2)
    band2 = band & (err < 30)
    if band2.sum() >= 0.5 * band.sum():
        fill, got = interp(band2)
    fill = cv2.GaussianBlur(fill, (0, 0), max(1.0, h * 0.2))   # 반경이 바뀌는 경계의 계단 제거
    pa = np.maximum(fill[:, :, 3:4], 1e-3)
    fill[:, :, :3] = np.where(fill[:, :, 3:4] > 0.5, fill[:, :, :3] * 255.0 / pa, 0)
    plate_a = fill[:, :, 3]
    allowed = region & ((interior & (plate_a >= 30)) | ((plate_a < 30) & (a > 0)))
    # 판과 다른 덩어리 중 대부분(60%↑)이 글자 영역 안에 있는 것만 지운다 → 영역 밖으로 이어진 테두리·이웃 줄은 보존
    fa = fill[:, :, 3:4] / 255.0
    pm_cur = rgba[:, :, :3].astype(np.float32) * (a[:, :, None] / 255.0)
    dif = np.abs(pm_cur - fill[:, :, :3] * fa).sum(2) + np.abs(a.astype(np.float32) - plate_a) * 1.5
    odd = ((dif > 60) & ((loc > 40) | core)).astype(np.uint8)   # 글자 사각형 밖의 완만한 판 변화(글로우 가장자리)는 덩어리로 치지 않음
    n, lab_cc, st, _ = cv2.connectedComponentsWithStats(odd, 8)
    inside_cnt = np.bincount(lab_cc[region], minlength=n)
    keep_ids = np.where((inside_cnt >= 0.6 * st[:, cv2.CC_STAT_AREA]) & (np.arange(n) > 0))[0]
    erase = np.isin(lab_cc, keep_ids).astype(np.uint8)
    erase = cv2.dilate(erase, np.ones((3, 3), np.uint8), iterations=max(1, int(h / 12))) > 0
    # 받침판 없는 글자(투명 위)는 덩어리 규칙과 무관하게 영역 안 전부
    target = allowed & (erase | (plate_a < 30))
    # 받침판 없는 곳(샘플 투명)은 투명으로, 판 위는 판 색·판 투명도로
    out[target] = np.clip(np.round(fill[target]), 0, 255).astype(np.uint8)
    clear = target & (plate_a < 30)
    out[clear, 3] = 0
    return out


def text_style(rgba, quad):
    """OCR 사변형 안 글자 픽셀에서 색(두 색 강조 포함)·각도·크기·중심을 뽑는다."""
    ang, w, h, c, ux, uy = _axes(quad)
    H, W = rgba.shape[:2]
    clean = clean_plate(rgba, quad)
    inq = _region((H, W), quad, 0.0, 0.0)
    diff = np.abs(rgba[:, :, :3].astype(int) - clean[:, :, :3].astype(int)).sum(2)
    # 글자 잉크: 판과 색이 크게 다르거나, 판이 투명한 곳의 불투명 픽셀(받침판 없는 글자는 검은 속까지 포함)
    txt = inq & (rgba[:, :, 3] > 200) & ((diff > 150) | (clean[:, :, 3] < 30))
    if txt.sum() < 10:
        txt = inq & (rgba[:, :, 3] > 200) & (np.abs(rgba[:, :, 3].astype(int) - clean[:, :, 3].astype(int)) > 60)
    st = {"angle": ang, "w": w, "h": h, "cx": float(c[0]), "cy": float(c[1]), "two_tone": False,
          "base": (255, 255, 255), "emph": (255, 255, 255)}
    cols = rgba[:, :, :3][txt].astype(np.float32)
    if len(cols) == 0:
        return st
    k = 2 if len(cols) > 50 else 1
    _, lab, cen = cv2.kmeans(cols, k, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0), 3,
                             cv2.KMEANS_PP_CENTERS)
    lab = lab.ravel(); counts = np.bincount(lab, minlength=k)
    order = np.argsort(-counts)
    st["base"] = st["emph"] = tuple(int(x) for x in cen[order[0]])
    if k == 2 and min(counts) / max(counts) > 0.15 and np.abs(cen[0] - cen[1]).sum() > 150:
        ys, xs = np.where(txt)
        proj = (xs - c[0]) * ux[0] + (ys - c[1]) * ux[1]
        p0, p1 = proj[lab == 0], proj[lab == 1]
        overlap = max(0.0, min(np.percentile(p0, 90), np.percentile(p1, 90)) - max(np.percentile(p0, 10), np.percentile(p1, 10)))
        span = max(1.0, np.percentile(proj, 98) - np.percentile(proj, 2))
        if overlap < span * 0.15:
            sat = lambda cc: float(max(cc) - min(cc))
            a_, b_ = tuple(int(x) for x in cen[0]), tuple(int(x) for x in cen[1])
            st["emph"], st["base"] = (a_, b_) if sat(a_) >= sat(b_) else (b_, a_)
            st["two_tone"] = True
        else:
            # 두 색이 겹쳐 있음 = 외곽선. 잉크 가장자리에서 먼 쪽 색이 글자 속, 가까운 쪽이 외곽선
            dist = cv2.distanceTransform(txt.astype(np.uint8), cv2.DIST_L2, 3)[txt]
            fill_i, stroke_i = (0, 1) if dist[lab == 0].mean() > dist[lab == 1].mean() else (1, 0)
            sw = float(np.median(dist[lab == stroke_i]) * 2)
            # 가장자리 중간색 띠(안티에일리어싱, 두께 ~2px)는 외곽선이 아님 → 원래 다수 색 그대로
            if sw >= 3.0:
                st["base"] = st["emph"] = tuple(int(x) for x in cen[fill_i])
                st["stroke"] = tuple(int(x) for x in cen[stroke_i])
                st["stroke_w"] = sw
    return st


def blur_text(rgba, quad, pad_x=0.3, pad_y=0.3):
    """사진 위 글자(뉴스 캡처): 글자 영역만 강하게 흐림."""
    _, w, h, _, _ = quad_geom(quad)
    region = _region(rgba.shape[:2], quad, pad_x, pad_y)
    kz = max(3, int(h * 1.2) | 1)
    bl = cv2.GaussianBlur(rgba, (kz, kz), 0)
    soft = cv2.GaussianBlur(region.astype(np.float32), (5, 5), 0)[:, :, None]
    return (rgba * (1 - soft) + bl * soft).astype(np.uint8)
