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


def _db_frames(x, sr):
    hop = int(sr * 0.01)
    n = len(x) // hop
    fr = x[: n * hop].reshape(n, hop)
    return 20 * np.log10(np.sqrt((fr ** 2).mean(axis=1)) + 1e-9)


def split_long(x, sr, spans, max_len=15.0, min_runs=(0.2, 0.1)):
    """max_len보다 긴 말 구간을 그 구간 안의 상대적으로 조용한 지점(구간 중앙값 −12dB 미만이 0.2초 이상)에서 나눈다.
    배경 잡음 때문에 고정 임계값으로 문장 사이가 안 끊기는 녹음용."""
    db = _db_frames(x, sr)
    out = []
    for a, b in spans:
        if b - a <= max_len:
            out.append((a, b))
            continue
        i0, i1 = int(a * 100), min(int(b * 100), len(db))
        seg = db[i0:i1]
        thr = np.median(seg) - 12.0
        pieces = [(a, b)]
        for min_run in min_runs:
            low = seg < thr
            cuts, j = [], 0
            while j < len(low):
                if low[j]:
                    k = j
                    while k < len(low) and low[k]:
                        k += 1
                    if (k - j) * 0.01 >= min_run:
                        cuts.append(((i0 + j) * 0.01, (i0 + k) * 0.01))
                    j = k
                else:
                    j += 1
            pieces, start = [], a
            for c0, c1 in cuts:
                if c0 - start > 0.15:
                    pieces.append((round(start, 3), round(c0, 3)))
                start = c1
            if b - start > 0.15:
                pieces.append((round(start, 3), round(b, 3)))
            if pieces and max(q - p for p, q in pieces) <= max_len:
                break
        out += pieces or [(a, b)]
    return out
