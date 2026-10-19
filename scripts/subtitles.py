"""영어 자막 큐 → AE job + SRT.  usage: subtitles.py <EP> <lang>"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sg.subs import split_cues
from sg.timemap import PiecewiseMap
from sg.edl import master_to_part

ep, lang = sys.argv[1], sys.argv[2]
root = os.path.join(os.path.dirname(__file__), "..")
prof = json.load(open(os.path.join(root, "profiles", f"{lang}.json")))
cfg = json.load(open(os.path.join(ep, "master_config.json")))
edl = json.load(open(os.path.join(ep, "master/edl.json")))
src = json.load(open(os.path.join(ep, "master/source.json")))
W = json.load(open(os.path.join(ep, "build", lang, "warp.json")))
warp = PiecewiseMap(W["master"])
pmap = {pid: PiecewiseMap(v["anchors"]) for pid, v in W["parts"].items()}
G = json.load(open(os.path.join(ep, cfg["graph"])))

# 파트 컴프 바로 아래 '#자막' 레이어: (sub_comp_id, startTime[원래 파트 시간])
subcomp = {}
for pid, P in cfg["parts"].items():
    Ls = [L for L in G["comps"][P["comp_id"]]["layers"]
          if L["src"] is not None and G["comps"].get(str(L["src"]), {}).get("name", "").startswith(cfg["subtitle_comp_prefix"])]
    if len(Ls) != 1:
        raise ValueError(f"{pid}: subtitle comp layers {len(Ls)}")
    subcomp[pid] = (Ls[0]["src"], Ls[0]["st"])

parts = {pid: [] for pid in cfg["parts"]}
srt = []
for g in src["segments"]:
    if g.get("nonverbal"):
        continue
    al = json.load(open(os.path.join(ep, "tts", lang, f"{g['id']}.align.json")))
    loc = master_to_part(edl, g["in"])
    if loc is None:
        continue
    pid, u = loc
    base_part = pmap[pid](u)                       # 변환 후 파트 시간에서 이 구간 시작
    base_master = warp(g["in"])
    sc_id, sc_st = subcomp[pid]
    sc_st_new = pmap[pid](sc_st)                   # localize.jsx는 프리컴프 startTime을 map(ost)로 옮김
    for c in split_cues(al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"],
                        prof["subs"]["max_chars"], prof["subs"]["min_dur"]):
        parts[pid].append({"in": round(base_part + c["t0"] - sc_st_new, 3),
                           "out": round(base_part + c["t1"] - sc_st_new - prof["subs"]["gap"], 3), "text": c["text"]})
        srt.append((base_master + c["t0"], base_master + c["t1"], c["text"]))

abs_ep = os.path.abspath(ep); name = os.path.basename(abs_ep)
json.dump({"aep": os.path.join(abs_ep, "build", lang, f"{name}_{lang}.aep"),
           "save_as": os.path.join(abs_ep, "build", lang, f"{name}_{lang}_subs.aep"),
           "out": os.path.join(abs_ep, "build", lang, "subtitles_log.json"),
           "parts": [{"comp": cfg["parts"][pid]["comp"], "sub_comp_id": subcomp[pid][0], "cues": cues} for pid, cues in parts.items()]},
          open(os.path.join(root, "scripts/ae/subtitles_job.json"), "w"), ensure_ascii=False, indent=1)
os.makedirs(os.path.join(ep, "render", lang), exist_ok=True)
fmt = lambda t: f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{int(t % 60):02d},{int(round((t % 1) * 1000)) % 1000:03d}"
with open(os.path.join(ep, "render", lang, f"{lang}.srt"), "w") as f:
    for n, (a, b, t) in enumerate(sorted(srt), 1):
        f.write(f"{n}\n{fmt(a)} --> {fmt(b)}\n{t}\n\n")
print({pid: len(c) for pid, c in parts.items()}, "srt", len(srt))
