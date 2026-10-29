"""GPT(image-layerkit)가 분리한 인물 컷아웃을 원본 씬에 자동 정합한다.

GPT는 인물을 캔버스 중앙에 크게 다시 그려 원위치를 잃는다. 컷아웃을 여러 배율로 줄여
원본과 마스크 템플릿 매칭(TM_SQDIFF)해 위치·크기를 되찾고, 원본 캔버스 좌표의 RGBA로 내보낸다.
    .venv/bin/python register_layers.py assets/layers/s01_family assets/gen/s01_family.png
"""
import glob, json, re, sys
from pathlib import Path
import cv2
import numpy as np

KEYS = {"green": (0, 177, 64), "magenta": (255, 0, 255)}


def key_mask(rgb, key):
    d = np.abs(rgb.astype(int) - np.array(key)).sum(2)
    a = np.clip((d - 60) / 60.0, 0, 1)
    a = cv2.morphologyEx((a * 255).astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    return a


def register(orig, cut_rgb, cut_a):
    """원본 위에서 컷아웃의 (배율, x, y) 탐색. 반판으로 거칠게 → 원판 근방 미세조정."""
    ys, xs = np.where(cut_a > 128)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    T, M = cut_rgb[y0:y1, x0:x1], cut_a[y0:y1, x0:x1]
    H, W = orig.shape[:2]
    k = 0.5
    O = cv2.resize(orig, (int(W * k), int(H * k)), interpolation=cv2.INTER_AREA).astype(np.float32)
    best = None
    for s in np.arange(0.25, 1.30, 0.02):
        tw, th = int(T.shape[1] * s * k), int(T.shape[0] * s * k)
        if tw < 20 or th < 20 or tw >= O.shape[1] or th >= O.shape[0]:
            continue
        t = cv2.resize(T, (tw, th), interpolation=cv2.INTER_AREA).astype(np.float32)
        m = cv2.resize(M, (tw, th), interpolation=cv2.INTER_AREA)
        m3 = cv2.merge([(m > 128).astype(np.float32)] * 3)
        r = cv2.matchTemplate(O, t, cv2.TM_SQDIFF, mask=m3)
        r = r / max(1.0, (m > 128).sum())
        mn, _, loc, _ = cv2.minMaxLoc(r)
        if best is None or mn < best[0]:
            best = (mn, s, loc[0] / k, loc[1] / k)
    # 미세조정(원판)
    _, s0, bx, by = best
    Of = orig.astype(np.float32)
    fine = None
    for s in np.arange(s0 - 0.025, s0 + 0.026, 0.005):
        tw, th = int(T.shape[1] * s), int(T.shape[0] * s)
        t = cv2.resize(T, (tw, th), interpolation=cv2.INTER_AREA).astype(np.float32)
        m = cv2.resize(M, (tw, th), interpolation=cv2.INTER_AREA)
        pad = 24
        xa, ya = int(max(0, bx - pad)), int(max(0, by - pad))
        xb, yb = int(min(W, bx + tw + pad)), int(min(H, by + th + pad))
        win = Of[ya:yb, xa:xb]
        if win.shape[0] <= th or win.shape[1] <= tw:
            continue
        r = cv2.matchTemplate(win, t, cv2.TM_SQDIFF, mask=cv2.merge([(m > 128).astype(np.float32)] * 3))
        r = r / max(1.0, (m > 128).sum())
        mn, _, loc, _ = cv2.minMaxLoc(r)
        if fine is None or mn < fine[0]:
            fine = (mn, s, xa + loc[0], ya + loc[1], t, m)
    err, s, x, y, t, m = fine
    out = np.zeros((H, W, 4), np.uint8)
    th, tw = m.shape
    xe, ye = min(W, x + tw), min(H, y + th)
    out[y:ye, x:xe, :3] = t[: ye - y, : xe - x].astype(np.uint8)
    out[y:ye, x:xe, 3] = m[: ye - y, : xe - x]
    return out, float(np.sqrt(err / 3)), float(s), (int(x), int(y), int(xe), int(ye))


def main(layer_dir, orig_path):
    ld = Path(layer_dir)
    orig = cv2.cvtColor(cv2.imread(orig_path), cv2.COLOR_BGR2RGB)
    L = json.loads((ld / "layers.json").read_text())
    res = []
    for l in L["layers"]:
        stem = Path(l["png"]).stem
        cands = sorted(glob.glob(str(ld / "raw" / f"{stem}*.png")))
        best = None
        for c in cands:
            kname = "green" if ".green." in c else "magenta"
            rgb = cv2.cvtColor(cv2.imread(c), cv2.COLOR_BGR2RGB)
            if rgb.shape[:2] != orig.shape[:2]:
                rgb = cv2.resize(rgb, (orig.shape[1], orig.shape[0]))
            a = key_mask(rgb, KEYS[kname])
            if (a > 128).sum() < 500:
                continue
            out, err, s, box = register(orig, rgb, a)
            if best is None or err < best[1]:
                best = (out, err, s, box, c)
        out, err, s, box, c = best
        dst = ld / "reg" / f"{stem}.png"
        dst.parent.mkdir(exist_ok=True)
        cv2.imwrite(str(dst), cv2.cvtColor(out, cv2.COLOR_RGBA2BGRA))
        H, W = orig.shape[:2]
        res.append({"name": l["name"], "png": f"reg/{stem}.png", "src": Path(c).name, "rms": round(err, 1), "scale": round(s, 3),
                    "bbox": [round(box[0] / W, 4), round(box[1] / H, 4), round(box[2] / W, 4), round(box[3] / H, 4)]})
        print(f"{l['name']}: rms={err:.1f} scale={s:.3f} box={box} ({Path(c).name})")
    (ld / "reg.json").write_text(json.dumps({"size": [orig.shape[1], orig.shape[0]], "bg": "bg.png", "chars": res}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
