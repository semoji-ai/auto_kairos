"""두 영상(로컬 렌더 vs 유튜브 마스터)을 프레임 단위로 비교해 다른 구간을 찾는다.

  python3 scripts/compare_video.py <a.mp4> <b.mp4> <out_dir> [--fps 2] [--thresh 0.80]

- 각 영상을 fps 간격으로 160x90 흑백 프레임으로 뽑아 numpy 배열로 만든다.
- 평균 밝기 곡선의 상호상관으로 b의 시간 오프셋(±30초)을 찾는다.
- 프레임별 유사도 = 정규화 상관계수(밝기·대비 차이에 둔감). thresh 미만이 0.5초 이상 이어지면 "다른 구간".
- out_dir/compare.json (오프셋, 구간 목록, 전체 통계) + 구간마다 나란히 비교 이미지 diff_<t>.jpg
"""
import json, os, subprocess, sys
import numpy as np
from PIL import Image

W, H = 160, 90


def frames(path, fps):
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-vf", f"fps={fps},scale={W}:{H},format=gray", "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32)


def ncc(a, b):
    a = a - a.mean(); b = b - b.mean()
    d = np.sqrt((a * a).sum() * (b * b).sum())
    if d < 1e-6:  # 단색 프레임: 평균 밝기 차이로 판단
        return 1.0 if abs(a.mean() - b.mean()) < 8 else 0.0
    return float((a * b).sum() / d)


def grab(path, t, out):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(t,0):.2f}", "-i", path, "-frames:v", "1",
                    "-vf", "scale=640:-1", out], check=True)


def main():
    a_path, b_path, out = sys.argv[1:4]
    fps = float(sys.argv[sys.argv.index("--fps") + 1]) if "--fps" in sys.argv else 2.0
    th = float(sys.argv[sys.argv.index("--thresh") + 1]) if "--thresh" in sys.argv else 0.80
    os.makedirs(out, exist_ok=True)
    A, B = frames(a_path, fps), frames(b_path, fps)
    la, lb = A.mean(axis=(1, 2)), B.mean(axis=(1, 2))
    la, lb = (la - la.mean()) / (la.std() + 1e-6), (lb - lb.mean()) / (lb.std() + 1e-6)
    best, off = -1e9, 0
    for k in range(-int(30 * fps), int(30 * fps) + 1):  # b[i+k] ~ a[i]
        i0, i1 = max(0, -k), min(len(la), len(lb) - k)
        if i1 - i0 < 10:
            continue
        s = float((la[i0:i1] * lb[i0 + k:i1 + k]).mean())
        if s > best:
            best, off = s, k
    sims = []
    for i in range(len(A)):
        j = i + off
        sims.append(ncc(A[i], B[j]) if 0 <= j < len(B) else None)
    segs, cur = [], None
    for i, s in enumerate(sims):
        bad = s is not None and s < th
        if bad and cur is None:
            cur = [i, i]
        elif bad:
            cur[1] = i
        elif cur is not None:
            segs.append(cur); cur = None
    if cur:
        segs.append(cur)
    segs = [g for g in segs if (g[1] - g[0] + 1) / fps >= 0.5]
    res = {"a": a_path, "b": b_path, "fps": fps, "offset_sec": off / fps, "align_score": best,
           "frames": len(A), "mean_sim": float(np.mean([s for s in sims if s is not None])),
           "below_thresh": sum(1 for s in sims if s is not None and s < th), "segments": []}
    for g in segs:
        t0, t1 = g[0] / fps, (g[1] + 1) / fps
        mid = (t0 + t1) / 2
        seg_sims = [s for s in sims[g[0]:g[1] + 1] if s is not None]
        fa, fb = os.path.join(out, "_a.png"), os.path.join(out, "_b.png")
        grab(a_path, mid, fa); grab(b_path, mid + off / fps, fb)
        ia, ib = Image.open(fa), Image.open(fb)
        im = Image.new("RGB", (ia.width + ib.width, max(ia.height, ib.height)))
        im.paste(ia, (0, 0)); im.paste(ib, (ia.width, 0))
        name = f"diff_{t0:07.1f}.jpg"
        im.save(os.path.join(out, name), quality=85)
        res["segments"].append({"t0": t0, "t1": t1, "min_sim": min(seg_sims), "img": name})
    for f in ("_a.png", "_b.png"):
        p = os.path.join(out, f)
        if os.path.exists(p):
            os.remove(p)
    json.dump(res, open(os.path.join(out, "compare.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "segments"}, ensure_ascii=False))
    for s in res["segments"]:
        print(f"  {s['t0']:7.1f}-{s['t1']:7.1f}  min {s['min_sim']:.2f}  {s['img']}")


if __name__ == "__main__":
    main()
