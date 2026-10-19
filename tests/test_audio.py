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
