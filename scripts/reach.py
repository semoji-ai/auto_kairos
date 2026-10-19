"""graph.json에서 루트 컴프의 [t0,t1] 구간에 실제로 도달하는 footage와 그 메인 타임라인 시간 구간을 계산.

  python3 -I scripts/reach.py <graph.json> <root_comp_id> [t0 t1] > reach.json

규칙: enabled 이거나 track matte로 쓰이는 레이어, 또는 오디오가 켜진 레이어만 도달로 본다.
시간 변환: 자식 로컬 시간 = (부모 시간 - startTime) / (stretch/100). time remap 레이어는 보수적으로 자식 전체 구간을 도달로 본다.
출력: {item_id: {"name", "file", "missing", "spans": [[main_t0, main_t1], ...], "via": [컴프 경로 예시]}}
"""
import json, sys

g = json.load(open(sys.argv[1]))
root = sys.argv[2]
comps, items = g["comps"], g["items"]
c0 = comps[root]
t0, t1 = (float(sys.argv[3]), float(sys.argv[4])) if len(sys.argv) > 4 else tuple(c0["wa"])

out = {}


def add(iid, a, b, path):
    e = out.setdefault(iid, {**items[iid], "spans": [], "via": path})
    e["spans"].append([round(a, 3), round(b, 3)])


def walk(cid, a, b, k, off, path, depth=0):
    """cid 컴프의 로컬 구간 [a,b]. 메인 시간 = 로컬 * k + off."""
    if depth > 30:
        return
    for L in comps[cid]["layers"]:
        if L["src"] is None:
            continue
        if not (L["en"] or L["matte"] or L["au"]):
            continue
        lo, hi = max(a, min(L["in"], L["out"])), min(b, max(L["in"], L["out"]))
        if lo >= hi:
            continue
        sid = str(L["src"])
        if sid in comps:
            sx = (L["sx"] or 100) / 100.0
            if L["tr"]:
                ca, cb = 0, comps[sid]["dur"]
                walk(sid, ca, cb, 0, lo * k + off, path + [comps[sid]["name"]], depth + 1)
                # time remap: 메인 시간 정보는 근사(레이어 구간 시작점)로만 기록
                continue
            ca, cb = (lo - L["st"]) / sx, (hi - L["st"]) / sx
            if sx < 0:
                ca, cb = cb, ca
            walk(sid, ca, cb, k * sx, off + L["st"] * k, path + [comps[sid]["name"]], depth + 1)
        elif sid in items:
            add(sid, lo * k + off, hi * k + off, path)


walk(root, t0, t1, 1.0, 0.0, [c0["name"]])
for e in out.values():  # 구간 병합
    s = sorted(e["spans"])
    m = []
    for a, b in s:
        if m and a <= m[-1][1] + 0.05:
            m[-1][1] = max(m[-1][1], b)
        else:
            m.append([a, b])
    e["spans"] = m
json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
