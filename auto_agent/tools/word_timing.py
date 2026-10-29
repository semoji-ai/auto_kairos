"""ElevenLabs 글자 타임스탬프 → 어절(띄어쓰기 단위) 시각, 그리고 키워드의 단어 큐 시각.

연출(뿅·타이포·화살표·카운트업)은 **음성에서 그 단어가 실제로 시작되는 시각**에 맞춘다
(세모지 통합보고 §3-1). 템플릿 키 타이밍이나 씬 시작 기준 고정값을 쓰지 않는다.

v4 챕터 생성(`scripts/tts_v4_chapters.py`)의 alignment 는 원고 글자(숫자 포함) 그대로라
"5위", "1975년" 같은 키워드를 원고 표기로 찾을 수 있다.
"""
from __future__ import annotations

import re
from typing import Iterable

_SPACE = {" ", "\n", "\t", "\r", "　"}
# 키워드 비교에서 무시할 문장부호 — 따옴표·괄호·쉼표 등
_PUNCT = re.compile(r"[\s.,!?;:·…'\"“”‘’()\[\]{}<>「」『』《》〈〉~\-—]")


def words_from_alignment(chars: list, starts: list, ends: list,
                         lo: int = 0, hi: int | None = None) -> list[dict]:
    """[lo, hi) 글자 구간을 어절로 나눈다. [{w, start, end, c0, c1}] (c = 글자 인덱스)."""
    hi = len(chars) if hi is None else min(hi, len(chars))
    n = min(len(starts), len(ends))
    out: list[dict] = []
    cur: list[str] = []
    c0 = None
    for i in range(lo, hi):
        ch = chars[i]
        if ch in _SPACE:
            if cur:
                out.append(_word(cur, c0, i, starts, ends, n))
                cur, c0 = [], None
            continue
        if c0 is None:
            c0 = i
        cur.append(ch)
    if cur:
        out.append(_word(cur, c0, hi, starts, ends, n))
    return [w for w in out if w is not None]


def _word(cur, c0, c1, starts, ends, n):
    if c0 >= n:
        return None
    last = min(c1, n) - 1
    return {"w": "".join(cur), "start": round(float(starts[c0]), 3),
            "end": round(float(ends[last]), 3), "c0": c0, "c1": c1}


def _norm(s: str) -> str:
    return _PUNCT.sub("", s or "").lower()


def find_cue(words: Iterable[dict], keyword: str, occurrence: int = 1,
             lead: float = 0.0) -> float | None:
    """씬 어절 목록에서 keyword 가 시작되는 어절의 start(- lead). 못 찾으면 None.

    여러 어절에 걸친 키워드("재계 서열")도 찾는다. 공백·문장부호는 무시하고
    비교한다. occurrence 는 같은 키워드가 여러 번 나올 때 몇 번째인지(1부터)."""
    words = list(words)
    key = _norm(keyword)
    if not key or not words:
        return None
    joined, owner = [], []
    for wi, w in enumerate(words):
        t = _norm(w.get("w", ""))
        joined.append(t)
        owner.extend([wi] * len(t))
    hay = "".join(joined)
    pos, k = -1, 0
    while k < max(1, occurrence):
        pos = hay.find(key, pos + 1)
        if pos < 0:
            return None
        k += 1
    t = float(words[owner[pos]]["start"]) - float(lead or 0.0)
    return round(max(0.0, t), 3)


def scene_spans(texts: list[str]) -> tuple[str, list[tuple[int, int]]]:
    """씬 발화문들을 줄바꿈으로 이은 챕터 텍스트와 씬별 [a, b) 글자 구간."""
    parts, spans, pos = [], [], 0
    for t in texts:
        if parts:
            parts.append("\n")
            pos += 1
        spans.append((pos, pos + len(t)))
        parts.append(t)
        pos += len(t)
    return "".join(parts), spans
