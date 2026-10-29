"""번역 길이 예산과 TTS 길이 판정."""
import math


def char_budget(dur, cps):
    return int(math.floor(dur * cps))


def fit_status(orig, new, lo=0.75, hi=1.35):
    r = new / orig
    if r < lo - 1e-9:
        return "short"
    if r > hi + 1e-9:
        return "long"
    return "ok"
