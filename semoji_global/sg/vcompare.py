"""변환표로 시각을 맞춘 프레임 대조."""
import subprocess
import numpy as np

W, H = 160, 90


def sample_pairs(part_map, t0, t1, step, max_new=None):
    anchors = [o for o, _ in part_map.pts]
    out, t = [], t0
    while t <= t1 + 1e-9:
        near = any(abs(t - a) <= 0.2 for a in anchors)
        collapsed = False
        for (o0, n0), (o1, n1) in zip(part_map.pts, part_map.pts[1:]):
            if o0 <= t <= o1 and n1 - n0 < 1e-6:
                collapsed = True
        if max_new is not None and part_map(t) > max_new:
            collapsed = True
        if not near and not collapsed:
            out.append((round(t, 3), round(part_map(t), 3)))
        t += step
    return out


def frame(path, t):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1",
                          "-vf", f"scale={W}:{H},format=gray", "-f", "rawvideo", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(H, W).astype(np.float32)


def ncc(a, b):
    a = a - a.mean(); b = b - b.mean()
    d = np.sqrt((a * a).sum() * (b * b).sum())
    if d < 1e-6:
        return 1.0 if abs(a.mean() - b.mean()) < 8 else 0.0
    return float((a * b).sum() / d)
