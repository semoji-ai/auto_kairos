"""투명 배경 애니메이션의 글자 덩어리 추적(위치·크기·각도·투명도)."""
import cv2
import numpy as np


def _blobs(rgba, min_area=50):
    a = rgba[:, :, 3]
    n, lab, st, cen = cv2.connectedComponentsWithStats((a > 20).astype(np.uint8), 8)
    out = []
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < min_area:
            continue
        ys, xs = np.where(lab == i)
        (_, _), (w, h), ang = cv2.minAreaRect(np.stack([xs, ys], 1).astype(np.float32))
        out.append({"cx": float(cen[i][0]), "cy": float(cen[i][1]), "w": float(max(w, h)), "h": float(min(w, h)),
                    "angle": float(ang), "alpha": float(a[lab == i].max()) / 255.0, "area": int(st[i, cv2.CC_STAT_AREA])})
    return out


def track_blobs(frames):
    """프레임마다 덩어리를 찾아 직전 위치 최근접(덩어리 크기의 1.5배 안)으로 이어 붙인 트랙 목록.
    tracks[k][f] = 상태 또는 None(그 프레임에 없음). 사라졌다 다시 나타나도 같은 트랙."""
    tracks, last = [], []
    for f, rgba in enumerate(frames):
        for t in tracks:
            t.append(None)
        for b in sorted(_blobs(rgba), key=lambda b: -b["area"]):
            best, bd = None, None
            for k, l in enumerate(last):
                if tracks[k][f] is not None:
                    continue
                d = np.hypot(b["cx"] - l["cx"], b["cy"] - l["cy"])
                if d < 1.5 * max(l["w"], 8) and (bd is None or d < bd):
                    best, bd = k, d
            if best is None:
                tracks.append([None] * f + [b]); last.append(b)
            else:
                tracks[best][f] = b; last[best] = b
    return tracks
