"""마스터 EDL: 프리미어 V1 → 파트/컷/아웃트로, 그리고 시간 변환."""
from sg.timemap import PiecewiseMap

FRAME = 1 / 29.97  # 프리미어 시간 반올림으로 생기는 1프레임 미만 겹침은 허용


def build_edl(seq, part_clips, outro_clip, cuts_pr):
    v1 = [t for t in seq["tracks"] if t["kind"] == "video"][0]["items"]
    parts, outro = [], None
    for it in v1:
        dur = round(it["end"] - it["start"], 3)
        if it["name"] == outro_clip:
            outro = {"clip": it["name"], "pr_in": it["start"], "dur": dur}
        elif it["name"] in part_clips:
            parts.append({"id": part_clips[it["name"]], "clip": it["name"],
                          "pr_in": it["start"], "src_in": it["in"] or 0.0, "dur": dur})
        else:
            raise ValueError(f"V1 clip not mapped: {it['name']}")
    by = {}
    for p in parts:
        prev = by.get(p["id"])
        if prev and p["src_in"] < prev["src_in"] + prev["dur"] - FRAME:
            raise ValueError(f"part {p['id']} clips overlap or go backwards in source")
        by[p["id"]] = p
    pr_len = max(it["end"] for it in v1)
    cuts = sorted(cuts_pr, key=lambda c: c["pr_in"])
    cut_total = sum(c["pr_out"] - c["pr_in"] for c in cuts)
    return {"parts": parts, "cuts": cuts, "outro": outro,
            "pr_length": pr_len, "length": round(pr_len - cut_total, 3)}


def pr_to_master(edl, p, clamp=True):
    removed = 0.0
    for c in edl["cuts"]:
        if p >= c["pr_out"]:
            removed += c["pr_out"] - c["pr_in"]
        elif p > c["pr_in"]:
            return (c["pr_in"] - removed) if clamp else None
    return p - removed


def master_to_pr(edl, m):
    p = m
    for c in edl["cuts"]:
        if p >= c["pr_in"]:
            p += c["pr_out"] - c["pr_in"]
    return p


def part_to_master(edl, part_id, u):
    for c in edl["parts"]:
        if c["id"] == part_id and c["src_in"] <= u < c["src_in"] + c["dur"] + 1e-9:
            return pr_to_master(edl, c["pr_in"] + (u - c["src_in"]), clamp=False)
    return None


def part_anchors(edl, warp, part_id):
    clips = [c for c in edl["parts"] if c["id"] == part_id]
    if not clips:
        raise KeyError(part_id)
    first_m = pr_to_master(edl, clips[0]["pr_in"])
    base = warp(first_m) - clips[0]["src_in"]
    pts = []
    for c in clips:
        a, b = c["pr_in"], c["pr_in"] + c["dur"]
        bps = {a, b}
        for cut in edl["cuts"]:
            for x in (cut["pr_in"], cut["pr_out"]):
                if a < x < b:
                    bps.add(x)
        for o, _ in warp.pts:
            x = master_to_pr(edl, o)
            if a < x < b:
                bps.add(x)
        for p in sorted(bps):
            u = c["src_in"] + (p - a)
            n = warp(pr_to_master(edl, p)) - base
            if pts and u <= pts[-1][0] + 1e-9:
                pts[-1] = (pts[-1][0], max(pts[-1][1], n))
            else:
                pts.append((u, n))
    for i in range(1, len(pts)):   # 부동소수 오차로 new가 줄어드는 것 방지
        if pts[i][1] < pts[i - 1][1]:
            pts[i] = (pts[i][0], pts[i - 1][1])
    m = PiecewiseMap(pts)
    end = clips[-1]["src_in"] + clips[-1]["dur"]
    return m, m(end) - m(clips[0]["src_in"])
