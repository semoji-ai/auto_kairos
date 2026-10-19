import numpy as np
from sg.audio import speech_spans

SR = 16000


def tone(sec, amp=0.3):
    t = np.arange(int(sec * SR)) / SR
    return (amp * np.sin(2 * np.pi * 220 * t)).astype(np.float32)


def sil(sec):
    return np.zeros(int(sec * SR), np.float32)


def test_two_phrases():
    x = np.concatenate([sil(0.5), tone(1.0), sil(0.6), tone(0.7), sil(0.3)])
    s = speech_spans(x, SR)
    assert len(s) == 2
    assert abs(s[0][0] - 0.45) < 0.05 and abs(s[0][1] - 1.55) < 0.05
    assert abs(s[1][0] - 2.05) < 0.05 and abs(s[1][1] - 2.85) < 0.05


def test_short_gap_merges():
    x = np.concatenate([tone(1.0), sil(0.1), tone(1.0)])
    assert len(speech_spans(x, SR)) == 1


from sg.audio import split_long


def test_long_span_with_noisy_pauses_is_split_at_relative_dips():
    rng = np.random.default_rng(0)
    parts = []
    for _ in range(6):                      # 5초 말 + 0.4초 '잡음 섞인 쉼'(−32dB 정도) × 6 = 32.4초
        parts.append(tone(5.0, 0.3))
        parts.append((rng.standard_normal(int(0.4 * SR)) * 0.025).astype(np.float32))
    x = np.concatenate(parts)
    assert len(speech_spans(x, SR)) == 1    # 고정 −40dB로는 안 끊김
    out = split_long(x, SR, speech_spans(x, SR), max_len=15.0)
    assert len(out) >= 3 and max(b - a for a, b in out) <= 15.0


def test_short_spans_are_untouched():
    x = np.concatenate([tone(3.0), sil(0.5), tone(2.0)])
    sp = speech_spans(x, SR)
    assert split_long(x, SR, sp, max_len=15.0) == sp
