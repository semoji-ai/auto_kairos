"""말 구간에 자막 텍스트를 붙여 내레이션 구간을 만든다."""


def attach_text(spans, subs):
    segs = [{"in": a, "out": b, "ko": "", "subs": []} for a, b in spans]
    if not segs:
        return segs
    for s in sorted(subs, key=lambda x: x["in"]):
        best, score = None, -1e9
        for i, g in enumerate(segs):
            ov = min(g["out"], s["out"]) - max(g["in"], s["in"])
            if ov <= 0:
                ov = -min(abs(g["in"] - s["out"]), abs(s["in"] - g["out"]))
            if ov > score:
                best, score = i, ov
        segs[best]["subs"].append(s)
    for g in segs:
        g["subs"].sort(key=lambda x: x["in"])
        g["ko"] = " ".join(x["text"].replace("\r", " ").strip() for x in g["subs"])
    return segs



MAX_GAP = 0.5  # 이어지는 말소리로 볼 최대 간격(초). B209 실측 0.15~0.35


def merge_textless(segs, is_speech):
    """텍스트 없는 구간 처리. is_speech(seg)->bool 이 참이면 텍스트 있는 이웃 중 가까운 쪽에 합치되,
    중간에 nonverbal 조각이 있으면 그쪽으로는 못 건너간다. 거짓이면 nonverbal(번역 안 함, 원래 소리 유지).
    말인데 양쪽이 다 막히면 nonverbal+review."""
    out = [dict(g) for g in segs]
    n = len(out)
    speech = {i: (False if g["ko"] else bool(is_speech(g))) for i, g in enumerate(out)}

    def gap(i, j):
        return max(segs[j]["in"] - segs[i]["out"], segs[i]["in"] - segs[j]["out"], 0.0)

    def reach(i, step):
        """한 칸씩 이웃으로 가며 텍스트 구간을 찾는다. 각 연결 간격이 MAX_GAP을 넘거나 nonverbal을 만나면 막힘."""
        k, j = i, i + step
        while 0 <= j < n:
            if gap(k, j) > MAX_GAP:
                return None
            if out[j]["ko"]:
                return j
            if not speech[j]:
                return None
            k, j = j, j + step
        return None

    drop = set()
    for i, g in enumerate(out):
        if g["ko"]:
            continue
        if not speech[i]:
            g["nonverbal"] = True
            continue
        cands = [j for j in (reach(i, -1), reach(i, 1)) if j is not None]
        if not cands:
            g["nonverbal"], g["review"] = True, True
            continue
        j = min(cands, key=lambda j: gap(i, j))
        t = out[j]
        t["in"], t["out"] = min(t["in"], g["in"]), max(t["out"], g["out"])
        drop.add(i)
    return [g for i, g in enumerate(out) if i not in drop]


_HALLU = ("구독", "좋아요", "시청해", "감사합니다", "뉴스", "자막 제공", "다음 영상")


def looks_like_speech(text):
    """whisper 결과로 말인지 판정. 빈 결과·괄호 표기·무음 구간에서 흔한 환각 문장은 말이 아님."""
    t = text.strip()
    if not t or t[0] in "[(":
        return False
    return not any(h in t for h in _HALLU)
