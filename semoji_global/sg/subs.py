"""정렬(글자 시각) 기반 자막 큐 분할."""
_PUNCT = ".,?!;:，。！？、；："
_END = ".?!。！？"
_ABBR = {"no.", "mr.", "mrs.", "ms.", "dr.", "st.", "vs.", "u.s.", "u.k.", "inc.", "co.", "jr.", "sr.", "etc."}


def _ends_sentence(word):
    return word[-1] in _END and word.lower() not in _ABBR


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


def _tokens_cjk(chars):
    """띄어쓰기 없는 언어: 글자 하나가 토큰, 단 영문·숫자 묶음(Costco, 1998, 2.5)은 하나로. 공백도 토큰(이어 붙일 때 보존)."""
    out, i, n = [], 0, len(chars)
    while i < n:
        j = i + 1
        if chars[i].isascii() and (chars[i].isalnum()):
            while j < n and chars[j].isascii() and (chars[j].isalnum() or chars[j] in ".%'-"):
                j += 1
        out.append((i, j - 1, "".join(chars[i:j])))
        i = j
    return out


_CLAUSE_END = "，。！？；：、"
_NO_START = "，。！？、；：）」”』…）》"
_NO_END = "（「“『《"


def _cjk_groups(tokens, max_chars, protect=()):
    """띄어쓰기 없는 언어의 큐 묶음: 구(문장부호까지)로 자르고, 구들을 max_chars 안에서 채움.
    max_chars를 넘는 구는 고르게 n등분(보호어·영문 묶음 안, 닫는 부호 앞, 여는 부호 뒤에서는 끊지 않음)."""
    text = "".join(t[2] for t in tokens)
    pos, acc = [], 0
    for t in tokens:
        pos.append(acc); acc += len(t[2])
    blocked = set()
    for w in protect:
        k = text.find(w)
        while k >= 0:
            blocked.update(range(k + 1, k + len(w))); k = text.find(w, k + 1)
    try:                                        # 중국어 낱말 안(八竿|子)에서는 끊지 않음 — jieba 분절
        import jieba
        jieba.setLogLevel(60)
        k = 0
        for w in jieba.lcut(text):
            blocked.update(range(k + 1, k + len(w))); k += len(w)
    except ImportError:
        pass

    def ok(i):                                  # tokens[i] 앞에서 끊어도 되는가
        return (0 < i < len(tokens) and pos[i] not in blocked and tokens[i][2][0] not in _NO_START
                and tokens[i - 1][2][-1] not in _NO_END and not tokens[i][2].isspace()
                and not tokens[i - 1][2].isspace())            # 'Kirkland Signature'처럼 공백으로 이은 영문은 한 덩어리

    clauses, cur = [], []
    for i, t in enumerate(tokens):
        cur.append(i)
        nxt_closes = i + 1 < len(tokens) and tokens[i + 1][2][0] in _NO_START
        if t[2][-1] in _CLAUSE_END and not nxt_closes:
            clauses.append(cur); cur = []
    if cur:
        clauses.append(cur)
    L = lambda idx: sum(len(tokens[i][2]) for i in idx)
    pieces = []
    for c in clauses:
        n = -(-L(c) // max_chars)
        if n <= 1:
            pieces.append(c); continue
        target = L(c) / n; start, run = 0, 0
        cuts = []
        for k in range(1, n):
            goal = target * k
            best = None
            for j in range(start + 1, len(c)):
                if not ok(c[j]):
                    continue
                d = abs(sum(len(tokens[i][2]) for i in c[:j]) - goal)
                if best is None or d < best[0]:
                    best = (d, j)
            if best is None:
                break
            cuts.append(best[1]); start = best[1]
        bounds = [0] + cuts + [len(c)]
        pieces += [c[a:b] for a, b in zip(bounds, bounds[1:]) if b > a]
    groups, cur = [], []
    for pc in pieces:
        if cur and L(cur) + L(pc) > max_chars:
            groups.append(cur); cur = []
        cur = cur + pc
    if cur:
        groups.append(cur)
    return [[tokens[i] for i in g] for g in groups]


def split_cues(chars, starts, ends, max_chars=42, min_dur=0.8, cjk=False, protect=()):
    """cjk=True(중국어·일본어): 구 단위로 채우고 긴 구는 고르게 나누며 공백 없이 잇는다(protect: 끊지 않을 낱말)."""
    J = "" if cjk else " "
    words = _tokens_cjk(chars) if cjk else _words(chars)
    groups, cur = [], []
    for w in ([] if cjk else words):
        trial = J.join(x[2] for x in cur + [w])
        if cur and len(trial) > max_chars:
            # 쉼표 등 뒤에서 끊을 수 있으면 그 지점까지만 현재 그룹으로
            cut = max((k for k in range(len(cur)) if cur[k][2][-1] in _PUNCT and cur[k][2].lower() not in _ABBR), default=None)
            if cut is not None and cut < len(cur) - 1 and len(J.join(x[2] for x in cur[:cut + 1])) >= max_chars * 0.5:
                groups.append(cur[:cut + 1]); cur = cur[cut + 1:] + [w]
            else:
                groups.append(cur); cur = [w]
        else:
            cur.append(w)
            if _ends_sentence(w[2]) and len(J.join(x[2] for x in cur)) >= max_chars * 0.6:
                groups.append(cur); cur = []
    if cur:
        groups.append(cur)
    if cjk:
        groups = _cjk_groups(words, max_chars, protect)
    cues = [{"t0": starts[g[0][0]], "t1": ends[g[-1][1]], "text": J.join(x[2] for x in g)} for g in groups]
    i = 0
    while i < len(cues):
        c = cues[i]
        if c["t1"] - c["t0"] < min_dur and len(cues) > 1:
            if i > 0 and len(cues[i - 1]["text"]) + len(J) + len(c["text"]) <= max_chars:
                cues[i - 1] = {"t0": cues[i - 1]["t0"], "t1": c["t1"], "text": cues[i - 1]["text"] + J + c["text"]}
                cues.pop(i); continue
            if i + 1 < len(cues) and (not cjk or len(c["text"]) + len(cues[i + 1]["text"]) <= max_chars):
                cues[i + 1] = {"t0": c["t0"], "t1": cues[i + 1]["t1"], "text": c["text"] + J + cues[i + 1]["text"]}
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


def retext(cues, display, cjk=False):
    """발음용 텍스트로 만든 큐의 시각은 그대로 두고, 문구는 화면용 텍스트 단어(cjk면 글자 토큰)를 글자 비율로 나눠 넣는다."""
    J = "" if cjk else " "
    words = [t[2] for t in _tokens_cjk(list(display))] if cjk else display.split()
    total = sum(len(c["text"]) for c in cues) or 1
    out, k, acc = [], 0, 0
    for i, c in enumerate(cues):
        acc += len(c["text"])
        upto = len(words) if i == len(cues) - 1 else round(len(words) * acc / total)
        upto = max(upto, k + 1) if k < len(words) else k
        out.append({**c, "text": J.join(words[k:upto])})
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


def snap_to_onsets(cues, onsets, max_shift=1.2):
    """구간 안 큐 시작(첫 큐 제외)을 가장 가까운 '쉼 뒤 소리 시작'으로 옮김(max_shift 안). 앞 큐 끝은 새 시작까지.
    중국어처럼 TTS 글자 시각이 균등 분배로만 오는 언어에서 자막이 말보다 앞서거나 늦는 것을 줄임."""
    out = [dict(c) for c in cues]
    for i in range(1, len(out)):
        t = out[i]["t0"]
        hi = cues[i + 1]["t0"] - 0.3 if i + 1 < len(cues) else float("inf")      # 다음 큐를 넘지 않게(순서 유지)
        cand = [o for o in onsets if abs(o - t) <= max_shift and out[i - 1]["t0"] + 0.3 < o < hi]
        if cand:
            o = min(cand, key=lambda o: abs(o - t))
            out[i]["t0"] = o
            out[i - 1]["t1"] = o
            out[i]["t1"] = max(out[i]["t1"], o + 0.3)
    return out


def srt_time(t):
    """초 → SRT 시각. 전체를 밀리초로 먼저 반올림(부분별로 버림·반올림하면 82.99999초가 01:22,000이 됨)."""
    ms = max(0, int(round(t * 1000)))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def cues_for_segment(chars, starts, ends, display=None, max_chars=42, min_dur=0.8, cjk=False, protect=()):
    """정렬(읽은 글자 시각)로 큐를 만들고, 화면 문장(display)이 읽은 문장과 다르면(발음용 표기) 화면 문장으로 바꿈.
    cjk: 화면 문장을 같은 규칙으로 다시 나누고 시각은 읽은 전체 구간에 글자 비율로 펼침. 그 외: 단어를 글자 비율로 배분."""
    cues = split_cues(chars, starts, ends, max_chars, min_dur, cjk=cjk, protect=protect)
    if display is None or display == "".join(chars) or not cues or not display:
        return cues
    if cjk:
        disp = list(display); a0, a1 = cues[0]["t0"], cues[-1]["t1"]
        st = [a0 + (a1 - a0) * i / len(disp) for i in range(len(disp))]
        en = [a0 + (a1 - a0) * (i + 1) / len(disp) for i in range(len(disp))]
        return split_cues(disp, st, en, max_chars, min_dur, cjk=True, protect=protect)
    return retext(cues, display)
