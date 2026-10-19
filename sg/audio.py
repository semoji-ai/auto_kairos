"""오디오 디코드와 무음 기준 말 구간 분할."""
import subprocess
import numpy as np


def decode(path, sr=16000):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def speech_spans(x, sr, thresh_db=-40.0, min_silence=0.25, min_speech=0.15, pad=0.05):
    hop = int(sr * 0.01)
    n = len(x) // hop
    if n == 0:
        return []
    fr = x[: n * hop].reshape(n, hop)
    db = 20 * np.log10(np.sqrt((fr ** 2).mean(axis=1)) + 1e-9)
    voiced = db > thresh_db
    spans, start, last = [], None, None
    for i, v in enumerate(voiced):
        t = i * 0.01
        if v:
            if start is None:
                start = t
            elif last is not None and t - last > min_silence:
                spans.append((start, last))
                start = t
            last = t + 0.01
    if start is not None:
        spans.append((start, last))
    dur = len(x) / sr
    out = []
    for a, b in spans:
        if b - a < min_speech:
            continue
        out.append((max(0.0, round(a - pad, 3)), min(dur, round(b + pad, 3))))
    return out
