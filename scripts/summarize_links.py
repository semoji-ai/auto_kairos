"""scan.jsonl 요약: 상태별 집계, 누락 파일이 원래 있던 위치(드라이브/폴더) 상위 패턴, 에피소드별 최신 aep 기준 누락 수."""
import json, sys, collections, os
rows = [json.loads(l) for l in open(sys.argv[1])]
st = collections.Counter(); aep_bad = collections.Counter(); roots = collections.Counter(); names = collections.Counter()
errs = 0
for d in rows:
    if "error" in d: errs += 1; continue
    for r in d["refs"]:
        if r["folder"]: continue
        st[r["status"]] += 1
        if r["status"] == "MISSING":
            aep_bad[d["aep"]] += 1
            parts = r["fullpath"].replace("\\", "/").split("/")
            roots["/".join(parts[:4])] += 1
            names[parts[-1]] += 1
print("aep", len(rows), "errors", errs)
print("상태별", dict(st))
print("누락 있는 aep", len(aep_bad))
print("누락 원위치 상위:"); [print("  ", n, k) for k, n in roots.most_common(25)]
print("누락 파일명 상위:"); [print("  ", n, k) for k, n in names.most_common(25)]
