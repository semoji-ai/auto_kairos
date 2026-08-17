"""SRT 자막 파싱 — 패널 도구의 'SRT 가져오기'용.

SEMOJI TOOL의 파서는 시작 타임코드만 읽어 마지막 자막 길이가 0이 되는 결함이
있었다. 여기서는 종료 타임코드를 읽어 각 큐가 자기 종료 시각을 갖는다.
깨진 블록은 건너뛰고 나머지를 살린다.
"""
from __future__ import annotations

import re

_TIME = re.compile(
    r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})")


def _sec(h, m, s, ms) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000.0


def parse_srt(text: str) -> list:
    """[{"start": float, "end": float, "text": str}] — 시작 시각 오름차순.

    번호 줄은 있어도 없어도 된다. end <= start 인 블록은 버린다."""
    if not text:
        return []
    text = text.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
    cues = []
    for block in re.split(r"\n\s*\n", text):
        lines = [ln for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue
        ti = None
        for i, ln in enumerate(lines):
            m = _TIME.search(ln)
            if m:
                ti = (i, m)
                break
        if ti is None:
            continue
        i, m = ti
        start = _sec(m.group(1), m.group(2), m.group(3), m.group(4))
        end = _sec(m.group(5), m.group(6), m.group(7), m.group(8))
        body = "\n".join(lines[i + 1:]).strip()
        if not body or end <= start:
            continue
        cues.append({"start": start, "end": end, "text": body})
    cues.sort(key=lambda c: c["start"])
    return cues
