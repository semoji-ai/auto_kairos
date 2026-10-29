"""영상 프레임에서 영역이 고정되는 시각·나타나는 시각."""
import numpy as np


def _crop(f, box):
    x, y, w, h = box
    return f[y:y + h, x:x + w].astype(np.float32)


def static_from(frames, box, tol=6.0, fps=29.97):
    """영역이 그 시각 이후 끝까지 마지막 프레임과 같은(평균 절대차 < tol) 첫 시각(초)."""
    last = _crop(frames[-1], box)
    k = len(frames) - 1
    while k > 0 and np.abs(_crop(frames[k - 1], box) - last).mean() < tol:
        k -= 1
    return round(k / fps, 4)


def appear_time(frames, box, bg, tol=12.0, fps=29.97):
    """영역이 바탕색과 처음 달라지는 시각(초). 끝까지 같으면 None."""
    for k, f in enumerate(frames):
        if np.abs(_crop(f, box) - np.array(bg, np.float32)).mean() > tol:
            return round(k / fps, 4)
    return None
