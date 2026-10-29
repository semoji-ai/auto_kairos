"""graph.jsx 출력 순회: 루트 컴프 시간 구간에 실제로 도달하는 레이어."""


def _merge(spans):
    m = []
    for a, b in sorted(spans):
        if m and a <= m[-1][1] + 0.05:
            m[-1][1] = max(m[-1][1], b)
        else:
            m.append([a, b])
    return [[round(a, 3), round(b, 3)] for a, b in m]


def walk(graph, root_id, t0, t1):
    comps = graph["comps"]
    acc = {}

    def rec(cid, a, b, k, off, path, depth):
        if depth > 30:
            return
        for L in comps[cid]["layers"]:
            if not (L["en"] or L["matte"] or L["au"]):
                continue
            lo = max(a, min(L["in"], L["out"]))
            hi = min(b, max(L["in"], L["out"]))
            if lo >= hi:
                continue
            key = (cid, L["i"])
            e = acc.setdefault(key, {"comp_id": cid, "layer": L["i"], "src": L["src"], "spans": [], "path": path, "occ": []})
            e["spans"].append([lo * k + off, hi * k + off])
            # 루트 시간 = 이 컴프의 로컬 시간 * k + off (레이어 자체 startTime/stretch는 L에서 따로 적용)
            e["occ"].append({"k": k, "off": off, "span": [lo * k + off, hi * k + off]})
            sid = str(L["src"]) if L["src"] is not None else None
            if sid in comps:
                sx = (L["sx"] or 100) / 100.0
                if L["tr"]:
                    rec(sid, 0, comps[sid]["dur"], 0.0, lo * k + off, path + [comps[sid]["name"]], depth + 1)
                    continue
                ca, cb = (lo - L["st"]) / sx, (hi - L["st"]) / sx
                if sx < 0:
                    ca, cb = cb, ca
                rec(sid, ca, cb, k * sx, off + L["st"] * k, path + [comps[sid]["name"]], depth + 1)

    rec(root_id, t0, t1, 1.0, 0.0, [comps[root_id]["name"]], 0)
    out = []
    for e in acc.values():
        e["spans"] = _merge(e["spans"])
        out.append(e)
    return out


def reach_items(graph, root_id, t0, t1):
    items = graph["items"]
    res = {}
    for r in walk(graph, root_id, t0, t1):
        sid = str(r["src"]) if r["src"] is not None else None
        if sid in items:
            e = res.setdefault(sid, {**items[sid], "spans": [], "via": r["path"]})
            e["spans"] += r["spans"]
    for e in res.values():
        e["spans"] = _merge(e["spans"])
    return res
