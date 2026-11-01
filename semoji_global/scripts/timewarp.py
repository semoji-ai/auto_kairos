"""변환표 생성.  usage: timewarp.py <EP> <tag> (--durs durs.json | --test-pattern | --test-scale k) [--keep-subs] [--job path]
--test-pattern: 말 구간(nonverbal 제외) 순번 1부터 홀수 ×0.9, 짝수 ×1.15 (번역 길이 변화 흉내)."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sg.warp import build_warp
from sg.edl import part_anchors

ep, tag = sys.argv[1], sys.argv[2]
args = sys.argv[3:]
edl = json.load(open(os.path.join(ep, "master/edl.json")))
src = json.load(open(os.path.join(ep, "master/source.json")))
cfg = json.load(open(os.path.join(ep, "master_config.json")))
segs = src["segments"]
if "--test-pattern" in args:
    spoken = [g for g in segs if not g.get("nonverbal")]
    durs = {g["id"]: (g["out"] - g["in"]) * (0.9 if (i % 2 == 1) else 1.15) for i, g in enumerate(spoken, 1)}
elif "--test-scale" in args:
    k = float(args[args.index("--test-scale") + 1])
    durs = {g["id"]: (g["out"] - g["in"]) * k for g in segs if not g.get("nonverbal")}
else:
    durs = json.load(open(args[args.index("--durs") + 1]))
cuts = [(c["in"], c["out"]) for c in src.get("korea_only", [])]
warp = build_warp(segs, durs, cuts, edl["length"])
out = {"master": warp.to_list(), "length_new": warp(edl["length"]), "parts": {}}
for pid, P in cfg["parts"].items():
    m, dur = part_anchors(edl, warp, pid)
    out["parts"][pid] = {"comp": P["comp"], "anchors": m.to_list(), "dur_new": dur}
bd = os.path.join(ep, "build", tag)
os.makedirs(bd, exist_ok=True)
json.dump(out, open(os.path.join(bd, "warp.json"), "w"), indent=1)
job_path = args[args.index("--job") + 1] if "--job" in args else os.path.join(os.path.dirname(__file__), "ae/localize_job.json")
abs_ep = os.path.abspath(ep)
name = os.path.basename(abs_ep)
json.dump({"aep": os.path.abspath(args[args.index("--aep") + 1]) if "--aep" in args else os.path.join(abs_ep, "src", f"{name}_main_ko.aep"),
           "save_as": os.path.join(abs_ep, "build", tag, f"{name}_{tag}.aep"),
           "out": os.path.join(abs_ep, "build", tag, "localize_log.json"),
           "mute_sources": [P["narration"] for P in cfg["parts"].values()] + cfg.get("extra_narration_sources", []),   # 오타 패치 재녹음 등 내레이션 조각
           "hide_comp_prefix": None if "--keep-subs" in args else "#자막",
           "parts": [{"comp": v["comp"], "anchors": v["anchors"], "dur_new": v["dur_new"]} for v in out["parts"].values()]},
          open(job_path, "w"), ensure_ascii=False, indent=1)
print(f"length {edl['length']:.2f} -> {out['length_new']:.2f}; parts " +
      ", ".join(f"{k} {v['dur_new']:.2f}" for k, v in out["parts"].items()))
