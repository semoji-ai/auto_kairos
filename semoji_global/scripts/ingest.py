"""편 가져오기(옛 PD 경로로 링크가 끊긴 aep용).  usage: ingest.py <EP> <NAS 편 폴더 이름> <aep 파일 이름> [--main main]
1) graph_nas.json·inventory_nas.json(이미 만든 것)에서 메인 컴프가 실제로 쓰는 footage만 고름(reach)
2) 각 파일을 NAS에서 찾음: 원래 경로 꼬리(편 폴더 아래 상대경로)로 먼저, 안 되면 파일명+꼬리 일치 점수로
   (찾을 곳: NAS 편 폴더, 세모지 공용 폴더들, 이미 가져온 다른 편의 src)
3) episodes/<EP>/src/ 로 복사(NFC 이름, 편 폴더 기준 상대경로) → relink 작업 파일 → relink.jsx → prep_main.jsx
결과: episodes/<EP>/src/<EP>_main_ko.aep, episodes/<EP>/ingest_report.json"""
import collections, json, os, shutil, subprocess, sys, unicodedata
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from sg.graph import reach_items
from scripts.audio_fetch import resolve

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
nfc = lambda s: unicodedata.normalize("NFC", s or "")
COMMON = [["002_intra", "001_세상의모든지식", "필수이미지"], ["001_shared_drive"], ["002_intra", "001_세상의모든지식", "유투브용 무료음악"]]


def index(root, depth=7):
    idx = {}
    for dp, ds, fs in os.walk(root):
        if dp[len(root):].count(os.sep) >= depth:
            ds[:] = []
        ds[:] = [d for d in ds if not d.startswith(("Adobe ", "."))]
        for f in fs:
            idx.setdefault(nfc(f).lower(), []).append(os.path.join(dp, f))
    return idx


def tail_score(a, b):
    a = [x.lower() for x in nfc(a).replace("\\", "/").split("/")][::-1]
    b = [x.lower() for x in nfc(b).replace("\\", "/").split("/")][::-1]
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


if __name__ == "__main__":
    ep, nas_dir, aep_name = sys.argv[1], sys.argv[2], sys.argv[3]
    main_name = sys.argv[sys.argv.index("--main") + 1] if "--main" in sys.argv else "main"
    E = os.path.abspath(os.path.join(ROOT, "episodes", ep))
    G = json.load(open(os.path.join(E, "graph_nas.json"))); I = json.load(open(os.path.join(E, "inventory_nas.json")))
    mid = [k for k, c in G["comps"].items() if c["name"] == main_name][0]; dur = G["comps"][mid]["dur"]
    R = reach_items(G, mid, 0, dur); F = {str(f["id"]): f for f in I["footage"]}
    nas_ep = resolve(["002_intra", "001_세상의모든지식", "◆브랜드백과사전", nas_dir])
    print("reached", len(R), "indexing NAS…", flush=True)
    idx = index(nas_ep)
    extra = {}
    for c in COMMON:
        r = resolve(c)
        if r:
            for k, v in index(r, 4).items():
                extra.setdefault(k, []).extend(v)
    for other in os.listdir(os.path.join(ROOT, "episodes")):
        s = os.path.join(ROOT, "episodes", other, "src")
        if other != ep and os.path.isdir(s):
            for k, v in index(s).items():
                extra.setdefault(k, []).extend(v)
    # 원래 PD 경로의 편 폴더: 같은 이름 폴더가 footage 경로에 있으면 그것(옆 편 폴더 파일은 상대경로 ../옆편/… 로 둠 → AE 상대경로 탐색)
    dirs = collections.Counter(os.path.dirname(nfc(f["file"]).replace("\\", "/")) for f in F.values() if f.get("file"))
    pd_ep = next((d for d, _ in dirs.most_common() if os.path.basename(d) == nfc(nas_dir)), None)
    plan, missing = {}, []
    for k, v in R.items():
        f = F.get(k)
        if not f or not f.get("file"):
            continue
        orig = nfc(f["file"]).replace("\\", "/")
        name = os.path.basename(orig).lower()
        cands = idx.get(name, []) or extra.get(name, [])
        if not cands:
            missing.append(orig); continue
        best = max(cands, key=lambda c: tail_score(orig, c))
        # 편 폴더 기준 상대경로(없으면 공용/파일명)
        rel = nfc(os.path.relpath(best, nas_ep)) if best.startswith(nas_ep) else os.path.join("_common", nfc(os.path.basename(best)))
        if pd_ep and orig.startswith(os.path.dirname(pd_ep) + "/") and not orig.startswith(pd_ep + "/"):
            rel = os.path.relpath(orig, pd_ep)            # 예: ../B019_KFC/찐_KFC_2.ai (원래 구조 그대로)
        plan[orig] = (best, rel)
    src = os.path.join(E, "src"); os.makedirs(src, exist_ok=True)
    copied = 0
    for orig, (best, rel) in plan.items():
        dst = os.path.join(src, rel)
        if not os.path.exists(dst):
            os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy2(best, dst); copied += 1
    # relink: 원래 경로 → 로컬 사본
    # aep를 src/(원래 편 폴더와 같은 구조)에 두고 열면 AE가 상대경로로 footage를 스스로 찾음.
    # 레이어별로 불러온 .ai/.psd는 replace()하면 레이어 선택이 풀려(빈 그림) 이 방식이어야 함.
    aep_local = os.path.join(src, "_orig_" + aep_name); out_aep = os.path.join(src, f"{ep}_main_ko.aep")
    shutil.copy2(os.path.join(E, "nas_aep", aep_name), aep_local)
    job = {"jobs": [{"aep": aep_local, "save_as": out_aep, "map": {o: os.path.join(src, r) for o, (b, r) in plan.items()}}],
           "log": os.path.join(E, "relink_log.json")}
    json.dump(job, open(os.path.join(ROOT, "scripts/ae/relink_job.json"), "w"), ensure_ascii=False)
    if os.path.exists(job["log"]):
        os.remove(job["log"])
    subprocess.run([os.path.join(ROOT, "scripts/ae/run.sh"), os.path.join(ROOT, "scripts/ae/relink.jsx")], check=True)
    log = json.load(open(job["log"]))
    pj = {"aep": out_aep, "comp_id": int(mid), "new_name": "MAIN_KO", "check_ids": [int(k) for k in R],
          "save_as": out_aep, "out": os.path.join(E, "prep_main.json")}
    json.dump(pj, open(os.path.join(ROOT, "scripts/ae/prep_main_job.json"), "w"), ensure_ascii=False)
    subprocess.run([os.path.join(ROOT, "scripts/ae/run.sh"), os.path.join(ROOT, "scripts/ae/prep_main.jsx")], check=True)
    prep = json.load(open(pj["out"]))
    rep = {"reached": len(R), "planned": len(plan), "copied": copied, "not_found_on_nas": missing,
           "relink": {k: (len(v) if isinstance(v, list) else v) for k, v in log[0].items()} if isinstance(log, list) else log,
           "prep": {"missing_used": prep.get("missing_used"), "ok": prep.get("ok"), "dur": prep.get("dur"), "errors": prep.get("errors")}}
    json.dump(rep, open(os.path.join(E, "ingest_report.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in rep.items()}, ensure_ascii=False))
    print("not found:", missing[:15]); print("still missing used:", prep.get("missing_used", [])[:15])
