"""영어 자막 큐 → AE job + SRT.  usage: subtitles.py <EP> <lang>"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sg.subs import split_cues, resolve_overlaps, retext, bar_intervals, close_gaps
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
L10N = json.load(open(os.path.join(ep, "l10n", f"{lang}.json")))
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
    cues = split_cues(al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"],
                      prof["subs"]["max_chars"], prof["subs"]["min_dur"])
    seg_l = L10N["segments"].get(g["id"], {})
    if seg_l.get("tts"):          # 발음용 표기로 읽었으면 화면 문구는 원래 번역문으로
        cues = retext(cues, seg_l["text"])
    for c in cues:
        parts[pid].append({"in": round(base_part + c["t0"] - sc_st_new, 3),
                           "out": round(base_part + c["t1"] - sc_st_new, 3), "text": c["text"]})
        srt.append({"in": base_master + c["t0"], "out": base_master + c["t1"], "text": c["text"]})
# 구간 사이 겹침 정리(다음 큐 시작 - gap)
parts = {pid: close_gaps(resolve_overlaps(c, prof["subs"]["gap"])) for pid, c in parts.items()}
srt = resolve_overlaps(srt, prof["subs"]["gap"])      # SRT는 플레이어가 그리므로 틈 유지

abs_ep = os.path.abspath(ep); name = os.path.basename(abs_ep)
json.dump({"aep": os.path.join(abs_ep, "build", lang, f"{name}_{lang}.aep"),
           "save_as": os.path.join(abs_ep, "build", lang, f"{name}_{lang}_subs.aep"),
           "out": os.path.join(abs_ep, "build", lang, "subtitles_log.json"),
           "bar_layers": cfg.get("subtitle_bar_layers", ["자막바", "자막바그림자"]),
           "parts": [{"comp": cfg["parts"][pid]["comp"], "sub_comp_id": subcomp[pid][0], "cues": cues,
                      # 자막 바는 자막이 있을 때만(영어는 큐 사이 공백이 길어 빈 바가 드러남)
                      "bar": bar_intervals(cues, pmap[pid](subcomp[pid][1]))} for pid, cues in parts.items()]},
          open(os.path.join(root, "scripts/ae/subtitles_job.json"), "w"), ensure_ascii=False, indent=1)
os.makedirs(os.path.join(ep, "render", lang), exist_ok=True)
fmt = lambda t: f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{int(t % 60):02d},{int(round((t % 1) * 1000)) % 1000:03d}"
with open(os.path.join(ep, "render", lang, f"{lang}.srt"), "w") as f:
    for n, c in enumerate(srt, 1):
        f.write(f"{n}\n{fmt(c['in'])} --> {fmt(c['out'])}\n{c['text']}\n\n")
print({pid: len(c) for pid, c in parts.items()}, "srt", len(srt))
