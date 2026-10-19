"""정렬(글자 시각) 기반 자막 큐 분할."""
_PUNCT = ".,?!;:"


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
            cut = max((k for k in range(len(cur)) if cur[k][2][-1] in _PUNCT), default=None)
            if cut is not None and cut < len(cur) - 1 and len(" ".join(x[2] for x in cur[:cut + 1])) >= max_chars * 0.5:
                groups.append(cur[:cut + 1]); cur = cur[cut + 1:] + [w]
            else:
                groups.append(cur); cur = [w]
        else:
            cur.append(w)
            if w[2][-1] in ".?!" and len(" ".join(x[2] for x in cur)) >= max_chars * 0.6:
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
