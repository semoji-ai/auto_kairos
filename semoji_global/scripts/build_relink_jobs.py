"""scan.jsonl + 인덱스 → 최종 aep별 relink 작업(json) 생성.

  python3 -I scripts/build_relink_jobs.py reports/final_aeps.json reports/scan.jsonl \
      reports/index.json reports/nas_index.json reports/relink_plan.json

후보 점수 = 원래 경로와 뒤에서부터 일치하는 경로 요소 수(대소문자 무시).
동점 최고 후보가 여러 개면: 같은 에피소드 폴더 > 세모지 트리 > 파일 크기가 모두 같으면 아무거나 > 아니면 AMBIG(연결 안 함).
경로는 디스크 실제 이름(NFD/NFC 혼재)으로 바꿔서 기록한다.
"""
import json, os, sys, unicodedata

NFC = lambda s: unicodedata.normalize("NFC", s)
final_p, scan_p, idx_p, nas_p, out_p = sys.argv[1:6]
ROOT = open(os.path.join(os.path.dirname(final_p), "root.txt")).read().strip()

final = json.load(open(final_p))
final_set = set(final.values())
rows = {}
for l in open(scan_p):
    d = json.loads(l)
    if d["aep"] in final_set:
        rows[d["aep"]] = d

by_name = {}
for rel in json.load(open(idx_p)):
    by_name.setdefault(os.path.basename(rel).lower(), []).append(("T", rel))
for ab in json.load(open(nas_p)):
    by_name.setdefault(os.path.basename(ab).lower(), []).append(("N", ab))

_ls = {}
def real(nfc_abs):
    """NFC 절대경로 → 디스크 실제 경로."""
    cur = "/"
    for part in nfc_abs.strip("/").split("/"):
        if cur not in _ls:
            try:
                _ls[cur] = {NFC(n): n for n in os.listdir(cur)}
            except OSError:
                _ls[cur] = {}
        n = _ls[cur].get(part)
        if n is None:
            return None
        cur = os.path.join(cur, n)
    return cur

ROOT_NFC = NFC(ROOT)
ALL = set(json.load(open(nas_p))) | {ROOT_NFC + "/" + r for r in json.load(open(idx_p))}

def unc_ok(key):
    """//서버/공유/나머지 → /Volumes/공유/나머지 가 존재하면 True (AE의 서버경로 해석)."""
    p = [x for x in key.split("/") if x]
    if key.startswith("//") and len(p) > 2:
        return "/Volumes/" + "/".join(p[1:]) in ALL
    return key.startswith("/Volumes/") and key in ALL
def to_abs(kind, p):
    return ROOT_NFC + "/" + p if kind == "T" else p

def tail_score(orig, cand):
    a = [x.lower() for x in orig.replace("\\", "/").split("/") if x]
    b = [x.lower() for x in cand.split("/") if x]
    s = 0
    while s < min(len(a), len(b)) and a[-1 - s] == b[-1 - s]:
        s += 1
    return s

plan, stats = [], {"aeps": 0, "map": 0, "ambig": 0, "none": 0}
for ep, aep in sorted(final.items()):
    d = rows.get(aep)
    if not d:
        continue
    todo = [r for r in d["refs"] if not r["folder"] and r["status"] in ("FIX_EPISODE", "FIX_GLOBAL", "MISSING")]
    if not todo:
        continue
    m, ambig, none = {}, [], []
    for r in todo:
        fp = r["fullpath"]
        key = fp.replace("\\", "/")
        if key in m:
            continue
        if unc_ok(key):  # AE가 //서버/공유/… 를 /Volumes/공유/… 로 스스로 찾음
            stats["unc_ok"] = stats.get("unc_ok", 0) + 1
            continue
        cands = by_name.get(fp.replace("\\", "/").split("/")[-1].lower(), [])
        if not cands:
            none.append(fp); continue
        sc = [(tail_score(fp, c[1]), c) for c in cands]
        top = max(s for s, _ in sc)
        best = [c for s, c in sc if s == top]
        pick = None
        local = [c for c in best if c[0] == "T" and c[1].startswith(ep + "/")]
        if local:
            pick = local[0]
        elif len(best) == 1:
            pick = best[0]
        else:
            tree = [c for c in best if c[0] == "T"]
            pool = tree or best
            sizes = set()
            for c in pool[:20]:
                rp = real(to_abs(*c))
                sizes.add(os.path.getsize(rp) if rp else -1)
            if len(sizes) == 1 and -1 not in sizes:
                pick = pool[0]
        if pick is None:
            ambig.append({"fullpath": fp, "cands": [to_abs(*c) for c in best[:5]]}); continue
        rp = real(to_abs(*pick))
        if not rp:
            none.append(fp); continue
        m[key] = rp
    aep_real = real(ROOT_NFC + "/" + aep)
    stem, ext = os.path.splitext(aep_real)
    plan.append({"episode": ep, "aep": aep_real, "save_as": stem + "_relinked" + ext,
                 "map": m, "ambig": ambig, "none": none})
    stats["aeps"] += 1; stats["map"] += len(m); stats["ambig"] += len(ambig); stats["none"] += len(none)

json.dump(plan, open(out_p, "w"), ensure_ascii=False, indent=1)
print(stats)
