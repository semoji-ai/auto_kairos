"""내레이션 구간의 새 길이와 컷으로 마스터 시간 변환표를 만든다."""
from sg.timemap import PiecewiseMap


def build_warp(segments, new_durs, cuts, length):
    cuts = sorted((float(a), float(b)) for a, b in cuts)
    segs = sorted(segments, key=lambda s: s["in"])
    for s0, s1 in zip(segs, segs[1:]):
        if s1["in"] < s0["out"]:
            raise ValueError(f"segments overlap: {s0['id']} / {s1['id']}")
    live = []
    for s in segs:
        inside = any(a <= s["in"] and s["out"] <= b for a, b in cuts)
        crossing = any(a < s["out"] and s["in"] < b for a, b in cuts) and not inside
        if crossing:
            raise ValueError(f"cut crosses segment {s['id']} [{s['in']},{s['out']}]")
        if not inside:
            live.append(s)
    # 이벤트: ('seg', in, out, newdur) / ('cut', a, b, 0)
    ev = [("seg", s["in"], s["out"], float(new_durs.get(s["id"], s["out"] - s["in"]))) for s in live]
    ev += [("cut", a, b, 0.0) for a, b in cuts]
    ev.sort(key=lambda e: e[1])
    anchors = [(0.0, 0.0)]
    old, new = 0.0, 0.0
    for kind, a, b, nd in ev:
        if a > old:                       # 사이 간격 유지
            new += a - old
            old = a
            anchors.append((old, new))
        if b <= old:
            continue
        new += nd if kind == "seg" else 0.0
        old = b
        anchors.append((old, new))
    if length > old:
        anchors.append((float(length), new + (length - old)))
    dedup = []
    for o, n in anchors:
        if dedup and o == dedup[-1][0]:
            dedup[-1] = (o, n)
        else:
            dedup.append((o, n))
    return PiecewiseMap(dedup)
