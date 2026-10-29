"""말자막 — TTS 타임스탬프 기반 줄 분할·타이밍 → subtitles.srt + subtitles.json(전역).
씬 오프셋은 timeline.scene_timings — 컴프·타임라인과 같은 길이 계산을 쓴다."""
from __future__ import annotations

import json
import re
from pathlib import Path

from backend import scenes, timeline, tts

MAX_LINE = 32      # 자막 한 줄 최대 글자 — 뜻 단락으로 나누되 이보다 길면 더 쪼갠다(디아지오 최대 35)
DEFAULT_DUR = timeline.DEFAULT_DUR   # 길이 규칙은 timeline이 단일 기준


def split_lines(text: str, max_len: int = MAX_LINE) -> list:
    """자막 한 줄씩 — 글자 수가 아니라 **뜻 단락**으로 나눈다(세모지 디아지오편 실측).

    디아지오 자막 413줄: 중앙값 20자·최대 35자, 끝자리는 마침 198 · 쉼표 80 · 구 경계 135.
    「이 시기 서덜랜드 영지에서만 / 약 1만 5천 명이 …」처럼 말의 덩어리에서 끊는다.

      ① 문장 단위 — max_len 이하면 한 줄
      ② 길면 쉼표에서
      ③ 그래도 길면 절 끝(-고·-며·-는데·-지만·-면서 …) > 주어·주제(은·는·이·가) >
         목적어·부사어(을·를·에서·으로 …) 뒤에서, 가운데에 가까운 자리
    어느 줄도 너무 짧게(6자 미만) 남기지 않는다.
    """
    forced = _forced_lines(text)
    if forced:
        return forced
    out = []
    for sent in split_sentences(text) or [(text or "").strip()]:
        for chunk in _split_commas(sent, max_len):
            out.extend(_split_phrase(chunk, max_len))
    return [x for x in out if x]


# 사람이 정한 줄나눔(subtitle_breaks.json — {씬번호: [줄, …]}) — 규칙으로는 「몇 명이 / 꾸리는」처럼
# 관형절 안의 주어에서 끊는 것을 못 막는다(10/3 점검). 줄을 이어 붙인 글자가 원문과 같을 때만 쓴다.
_FORCE: list = []


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def _forced_lines(text: str):
    key = _norm(text)
    if not key:
        return None
    for lines in _FORCE:
        nl = [_norm(x) for x in lines]
        for i in range(len(nl)):
            acc = ""
            for j in range(i, len(nl)):
                acc += nl[j]
                if acc == key:
                    return [x.strip() for x in lines[i:j + 1]]
                if not key.startswith(acc):
                    break
    return None


def load_breaks(proj_dir: Path) -> int:
    """프로젝트의 subtitle_breaks.json 을 읽어 _FORCE 에 싣는다. 원문과 글자가 다른 항목은 버린다."""
    global _FORCE
    _FORCE = []
    fp = Path(proj_dir) / "subtitle_breaks.json"
    if not fp.is_file():
        return 0
    try:
        d = json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return 0
    texts = {}
    for s in scenes.load_scenes(Path(proj_dir)).get("scenes", []):
        texts[str(s.get("sceneNumber"))] = scenes.subtitle_text(s)
    for k, lines in d.items():
        if isinstance(lines, list) and lines and _norm("".join(lines)) == _norm(texts.get(str(k), "")):
            _FORCE.append(lines)
    return len(_FORCE)


_CLAUSE = ("는데", "지만", "면서", "니까", "으며", "거나", "든지", "고", "며", "서", "면", "데", "듯",
           "려", "아", "어", "여", "해", "워", "져", "쳐", "고서")
# 꾸미는 말(관형형) — 뒤 명사와 한 덩어리라 여기서 끊지 않는다(「넘는 / 돈을」 방지)
_ADNOMINAL = ("하는", "되는", "있는", "없는", "넘는", "오는", "가는", "주는", "보는", "받는", "리는", "치는",
              "르는", "드는", "지는", "내는", "놓는", "쓰는", "파는", "사는", "던", "될", "할", "갈", "올", "한", "된")
_TOPIC = ("은", "는", "이", "가", "도", "만")
_OBJECT = ("을", "를", "에서", "에게", "으로", "로", "에", "와", "과", "께서", "부터", "까지", "처럼")


def _split_commas(sent: str, max_len: int) -> list:
    if len(sent) <= max_len:
        return [sent]
    # 숫자 안의 쉼표(2,000·1,800)는 세 자리 구분이지 끊는 자리가 아니다 — 숫자 사이 쉼표는 건너뛴다
    parts = [p.strip() + "," for p in re.split(r"(?<!\d),|,(?!\d)", sent)]
    parts[-1] = parts[-1][:-1]
    lines, cur = [], ""
    for p in parts:
        if cur and len(cur) + 1 + len(p) > max_len:
            lines.append(cur); cur = p
        else:
            cur = (cur + " " + p).strip()
    if cur:
        lines.append(cur)
    return lines


def _split_phrase(chunk: str, max_len: int, min_len: int = 6) -> list:
    if len(chunk) <= max_len:
        return [chunk]
    words = chunk.split()
    if len(words) < 2:
        return [chunk]
    mid, best = len(chunk) / 2, None
    for i in range(1, len(words)):
        left, right = " ".join(words[:i]), " ".join(words[i:])
        if len(left) < min_len or len(right) < min_len:
            continue
        w = words[i - 1].rstrip(",.?!")
        if w.endswith(_ADNOMINAL):
            rank = 9
        else:
            rank = 0 if w.endswith(_CLAUSE) else 1 if w.endswith(_TOPIC) else 2 if w.endswith(_OBJECT) else 3
        score = rank * 100 + abs(len(left) - mid)
        if best is None or score < best[0]:
            best = (score, left, right)
    if not best:
        return [chunk]
    return _split_phrase(best[1], max_len, min_len) + _split_phrase(best[2], max_len, min_len)


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
    load_breaks(proj_dir)
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
