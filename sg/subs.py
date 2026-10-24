"""정렬(글자 시각) 기반 자막 큐 분할."""
_PUNCT = ".,?!;:"
_ABBR = {"no.", "mr.", "mrs.", "ms.", "dr.", "st.", "vs.", "u.s.", "u.k.", "inc.", "co.", "jr.", "sr.", "etc."}


def _ends_sentence(word):
    return word[-1] in ".?!" and word.lower() not in _ABBR


def _words(chars):
    """(시작 글자 idx, 끝 글자 idx(포함), 단어 문자열) 목록."""
    out, i, n = [], 0, len(chars)
    while i < n:
        while i < n and chars[i].isspace():
            i += 1
        j = i
        while j < n and not chars[j].isspace():
            j += 1
        if j > i:
            out.append((i, j - 1, "".join(chars[i:j])))
        i = j
    return out


def split_cues(chars, starts, ends, max_chars=42, min_dur=0.8):
    words = _words(chars)
    groups, cur = [], []
    for w in words:
        trial = " ".join(x[2] for x in cur + [w])
        if cur and len(trial) > max_chars:
            # 쉼표 등 뒤에서 끊을 수 있으면 그 지점까지만 현재 그룹으로
            cut = max((k for k in range(len(cur)) if cur[k][2][-1] in _PUNCT and cur[k][2].lower() not in _ABBR), default=None)
            if cut is not None and cut < len(cur) - 1 and len(" ".join(x[2] for x in cur[:cut + 1])) >= max_chars * 0.5:
                groups.append(cur[:cut + 1]); cur = cur[cut + 1:] + [w]
            else:
                groups.append(cur); cur = [w]
        else:
            cur.append(w)
            if _ends_sentence(w[2]) and len(" ".join(x[2] for x in cur)) >= max_chars * 0.6:
                groups.append(cur); cur = []
    if cur:
        groups.append(cur)
    cues = [{"t0": starts[g[0][0]], "t1": ends[g[-1][1]], "text": " ".join(x[2] for x in g)} for g in groups]
    i = 0
    while i < len(cues):
        c = cues[i]
        if c["t1"] - c["t0"] < min_dur and len(cues) > 1:
            if i > 0 and len(cues[i - 1]["text"]) + 1 + len(c["text"]) <= max_chars:
                cues[i - 1] = {"t0": cues[i - 1]["t0"], "t1": c["t1"], "text": cues[i - 1]["text"] + " " + c["text"]}
                cues.pop(i); continue
            if i + 1 < len(cues):
                cues[i + 1] = {"t0": c["t0"], "t1": cues[i + 1]["t1"], "text": c["text"] + " " + cues[i + 1]["text"]}
                cues.pop(i); continue
        i += 1
    # 합칠 수 없는 짧은 큐는 표시 시간만 늘림(다음 큐 시작을 넘지 않게, 앞으로는 이전 큐 끝까지)
    for i, c in enumerate(cues):
        if c["t1"] - c["t0"] < min_dur:
            nxt = cues[i + 1]["t0"] if i + 1 < len(cues) else float("inf")
            c["t1"] = min(c["t0"] + min_dur + 1e-6, nxt)
            if c["t1"] - c["t0"] < min_dur:
                prv = cues[i - 1]["t1"] if i > 0 else 0.0
                c["t0"] = max(prv, c["t1"] - min_dur - 1e-6)
    return cues


def resolve_overlaps(cues, gap=0.04):
    """여러 구간에서 모은 큐(in/out)를 시각순으로 정렬하고, 다음 큐 시작 - gap 을 넘는 끝을 자른다."""
    out = sorted((dict(c) for c in cues), key=lambda c: c["in"])
    for i in range(len(out) - 1):
        lim = round(out[i + 1]["in"] - gap, 3)
        if out[i]["out"] > lim:
            out[i]["out"] = max(lim, out[i]["in"] + 0.05)
    return out


def retext(cues, display):
    """발음용 텍스트로 만든 큐의 시각은 그대로 두고, 문구는 화면용 텍스트 단어를 글자 비율로 나눠 넣는다."""
    words = display.split()
    total = sum(len(c["text"]) for c in cues) or 1
    out, k, acc = [], 0, 0
    for i, c in enumerate(cues):
        acc += len(c["text"])
        upto = len(words) if i == len(cues) - 1 else round(len(words) * acc / total)
        upto = max(upto, k + 1) if k < len(words) else k
        out.append({**c, "text": " ".join(words[k:upto])})
        k = upto
    return [c for c in out if c["text"]]


def bar_intervals(cues, sub_start, merge_gap=0.6):
    """자막 바를 보일 구간(메인 컴프 시각). 큐 시각 + 자막 프리컴프 시작, merge_gap 미만 공백은 이어 붙임(깜빡임 방지)."""
    out = []
    for c in sorted(cues, key=lambda c: c["in"]):
        a, b = round(c["in"] + sub_start, 3), round(c["out"] + sub_start, 3)
        if out and a - out[-1][1] < merge_gap:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def close_gaps(cues, max_gap=0.6):
    """큐 사이 틈이 max_gap(=자막 바 이어 붙임 기준) 미만이면 앞 큐를 다음 큐 시작까지 늘림(자막이 바뀔 때 빈 바가 2~3프레임 깜빡이는 것 방지)."""
    out = [dict(c) for c in sorted(cues, key=lambda c: c["in"])]
    for a, b in zip(out, out[1:]):
        if 0 < b["in"] - a["out"] < max_gap:
            a["out"] = b["in"]
    return out
