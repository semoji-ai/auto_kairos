"""말자막 — TTS 타임스탬프 기반 줄 분할·타이밍 → subtitles.srt + subtitles.json(전역).
씬 오프셋은 timeline.scene_timings — 컴프·타임라인과 같은 길이 계산을 쓴다."""
from __future__ import annotations

import json
import re
from pathlib import Path

from backend import scenes, timeline, tts

MAX_LINE = 20      # 자막 한 줄 최대 글자(어절 경계 분할)
DEFAULT_DUR = timeline.DEFAULT_DUR   # 길이 규칙은 timeline이 단일 기준


def split_lines(text: str, max_len: int = MAX_LINE) -> list:
    """어절(공백) 경계로 max_len 이하 줄들로 분할."""
    words = (text or "").split()
    lines, cur = [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > max_len:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines


def split_sentences(text: str) -> list:
    """문장 경계(.!?。) 기준 분할. 경계가 없으면 [전체]."""
    parts = [p.strip() for p in re.split(r"(?<=[.!?。])\s+", (text or "").strip()) if p.strip()]
    return parts


def _spread(text: str, start: float, end: float, max_len: int) -> list:
    """text를 줄로 나눠 [start, end] 구간에 글자수 비율로 배분."""
    lines = split_lines(text, max_len)
    if not lines:
        return []
    total = sum(len(L) for L in lines) or 1
    span = max(0.0, end - start)
    cues, t = [], start
    for i, L in enumerate(lines):
        w = span * (len(L) / total)
        e = end if i == len(lines) - 1 else t + w
        cues.append({"text": L, "start": round(t, 3), "end": round(e, 3)})
        t = e
    return cues


def _sentence_span(ts: dict, sent: str, ci: int) -> tuple:
    """alignment 문자열을 ci부터 소비하며 sent의 [start, end, 다음 ci]. 못 찾으면 (None, None, ci)."""
    chars, starts, ends = ts.get("characters", []), ts.get("starts", []), ts.get("ends", [])
    first = last = None
    for ch in sent:
        if ch.isspace():
            continue
        while ci < len(chars) and chars[ci] != ch:
            ci += 1
        if ci >= len(chars):
            break
        if first is None:
            first = ci
        last = ci
        ci += 1
    if first is None or last is None:
        return None, None, ci
    try:
        return float(starts[first]), float(ends[last]), ci
    except (IndexError, ValueError, TypeError):
        return None, None, ci


def mapped_cues(ts: dict, sub_text: str, max_len: int = MAX_LINE) -> list:
    """자막 텍스트(sub_text)를 TTS alignment 시간에 얹어 [{text,start,end}] (씬 로컬).

    TTS 텍스트와 자막 텍스트를 문장 단위로 짝지어, 문장의 alignment 구간 안에서
    자막 줄들을 글자수 비율로 나눈다. 문장 수가 다르면 씬 전체 구간에 비율 배분.
    자막 텍스트가 TTS 텍스트와 같으면 line_cues와 같은 결과가 된다."""
    tts_txt = ts.get("text", "")
    sub_text = (sub_text or "").strip()
    if not sub_text or sub_text == tts_txt.strip():
        return line_cues(ts, max_len)
    tts_sents, sub_sents = split_sentences(tts_txt), split_sentences(sub_text)
    starts, ends = ts.get("starts", []), ts.get("ends", [])
    if not starts or not ends:
        return []
    scene_start, scene_end = float(starts[0]), float(ends[-1])
    if len(tts_sents) != len(sub_sents) or not tts_sents:
        return _spread(sub_text, scene_start, scene_end, max_len)
    cues, ci = [], 0
    for tsent, ssent in zip(tts_sents, sub_sents):
        s0, s1, ci = _sentence_span(ts, tsent, ci)
        if s0 is None:
            return _spread(sub_text, scene_start, scene_end, max_len)
        cues.extend(_spread(ssent, s0, s1, max_len))
    return cues


def _load_ts(proj_dir: Path, sid: str) -> dict | None:
    fp = Path(proj_dir) / "audio" / f"tts_{sid}.timestamps.json"
    if not fp.is_file():
        return None
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return None


def line_cues(ts: dict, max_len: int = MAX_LINE) -> list:
    """타임스탬프 dict → [{text, start, end}] (씬 로컬 시간).
    alignment characters를 줄 텍스트와 순서대로 소비하며 각 줄의 [첫글자 start, 끝글자 end]."""
    text = ts.get("text", "")
    chars, starts, ends = ts.get("characters", []), ts.get("starts", []), ts.get("ends", [])
    lines = split_lines(text, max_len)
    cues, ci = [], 0
    for line in lines:
        # 줄의 첫 비공백 글자부터 매칭(공백은 건너뜀)
        first_idx = last_idx = None
        for chx in line:
            while ci < len(chars) and chars[ci] != chx:
                ci += 1
            if ci < len(chars):
                if first_idx is None:
                    first_idx = ci
                last_idx = ci
                ci += 1
        if first_idx is None or last_idx is None:
            continue
        try:
            cues.append({"text": line,
                         "start": float(starts[first_idx]),
                         "end": float(ends[last_idx])})
        except (IndexError, ValueError, TypeError):
            continue
    return cues


def _scene_durations(proj_dir: Path, data: dict) -> list:
    """씬 길이 목록(Final 배치 오프셋용) — 컴프·타임라인과 같은 계산을 쓴다."""
    return [d for _s, _start, d in timeline.scene_timings(Path(proj_dir), data)]


def _num(n):
    """씬 번호 비교용 — 삽입 씬의 소수 번호(25.25)를 int로 자르면 다른 씬이 섞인다."""
    try:
        return float(n)
    except (TypeError, ValueError):
        return None


def _fmt_srt_time(sec: float) -> str:
    ms = int(round(sec * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_subtitles(proj_dir: Path, only_scenes: list | None = None) -> dict:
    """자막 빌드 → subtitles.json([{start,end,text}] 전역) + subtitles.srt.
    타임스탬프 없는 씬은 균등 분배 폴백. 반환 {json, srt, lines, scenes_no_ts}.

    only_scenes 를 주면 그 씬들의 자막만 담는다. 오프셋은 전체 씬 기준으로 누적하므로
    부분 빌드도 전체 빌드와 같은 시각에 놓인다."""
    proj_dir = Path(proj_dir)
    data = scenes.load_scenes(proj_dir)
    durs = _scene_durations(proj_dir, data)
    picked = {_num(x) for x in only_scenes} if only_scenes else None
    cues_all, no_ts = [], []
    offset = 0.0
    for s, dur in zip(data.get("scenes", []), durs):
        if picked is not None and _num(s.get("sceneNumber")) not in picked:
            offset += dur                       # 건너뛰어도 시각은 전체 기준 유지
            continue
        sid = s.get("sceneId")
        ts = _load_ts(proj_dir, sid) if sid else None
        if ts and ts.get("characters"):
            for c in mapped_cues(ts, scenes.subtitle_text(s)):
                cues_all.append({"start": round(offset + c["start"], 3),
                                 "end": round(offset + c["end"], 3), "text": c["text"]})
        else:
            text = scenes.subtitle_text(s)
            if text:
                no_ts.append(s.get("sceneNumber"))
                lines = split_lines(text)
                step = dur / max(1, len(lines))
                for i, line in enumerate(lines):       # 균등 분배 폴백
                    cues_all.append({"start": round(offset + i * step, 3),
                                     "end": round(offset + (i + 1) * step - 0.05, 3), "text": line})
        offset += dur
    jpath = proj_dir / "subtitles.json"
    jpath.write_text(json.dumps({"cues": cues_all}, ensure_ascii=False, indent=2), encoding="utf-8")
    srt = []
    for i, c in enumerate(cues_all, 1):
        srt.append(f"{i}\n{_fmt_srt_time(c['start'])} --> {_fmt_srt_time(c['end'])}\n{c['text']}\n")
    spath = proj_dir / "subtitles.srt"
    spath.write_text("\n".join(srt), encoding="utf-8")
    return {"json": str(jpath), "srt": str(spath), "lines": len(cues_all), "scenes_no_ts": no_ts}
