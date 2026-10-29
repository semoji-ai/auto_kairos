"""numpy 오디오 믹스: 볼륨 포락선(키프레임 선형)과 버퍼에 더하기(지연·끝 페이드)."""
import numpy as np


def envelope(t, gain, keys):
    """시각 배열 t(초)에서의 선형 볼륨. keys=[[시각, 값]](같은 시각축) — 첫 키 앞은 첫 값, 마지막 뒤는 마지막 값."""
    if not keys:
        return np.full(len(t), float(gain), np.float32)
    k = sorted(keys)
    return np.interp(t, [a for a, _ in k], [v for _, v in k]).astype(np.float32)


def place(buf, x, t, sr, gain, fade_out=0.0):
    """buf[샘플, 채널]의 t초 위치에 x를 gain(샘플별)로 더함. 끝 fade_out초 선형 페이드. 버퍼 밖은 잘림."""
    s = int(round(t * sr))
    if s >= len(buf) or len(x) == 0:
        return
    if s < 0:
        x, gain, s = x[-s:], gain[-s:], 0
    n = min(len(x), len(buf) - s)
    g = np.asarray(gain[:n], np.float32).copy()
    if fade_out > 0:
        f = min(n, int(round(fade_out * sr)))
        if f > 0:
            g[n - f:] *= np.linspace(1.0, 0.0, f, dtype=np.float32)
    buf[s:s + n] += x[:n] * g[:, None]
