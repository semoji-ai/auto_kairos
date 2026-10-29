"""usage: compare_warped.py <orig.mp4> <warped.mp4> <warp.json> <part_id> <out_dir> [--t0 0 --t1 120] [--step 1]"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sg.timemap import PiecewiseMap
from sg.vcompare import sample_pairs, frame, ncc

orig, warped, wj, pid, out = sys.argv[1:6]
a = sys.argv[6:]
opt = lambda k, d: float(a[a.index(k) + 1]) if k in a else d
t0, t1, step = opt("--t0", 0.0), opt("--t1", 120.0), opt("--step", 1.0)
m = PiecewiseMap(json.load(open(wj))["parts"][pid]["anchors"])
os.makedirs(out, exist_ok=True)
import subprocess
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", warped],
                           capture_output=True, text=True).stdout)
pairs = sample_pairs(m, t0, t1, step, max_new=dur - 0.1)
sims = [(t, n, ncc(frame(orig, t), frame(warped, n))) for t, n in pairs]
bad = [{"t": t, "t_new": n, "sim": round(s, 3)} for t, n, s in sims if s < 0.85]
res = {"pairs": len(sims), "mean_sim": sum(s for _, _, s in sims) / max(len(sims), 1), "bad": bad}
json.dump(res, open(os.path.join(out, "compare.json"), "w"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "bad"}), "bad", len(bad), bad[:10])
