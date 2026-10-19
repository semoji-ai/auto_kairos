"""일러스트·이미지 내보내기 + OCR + 교체 대상 선별.  usage: raster_scan.py <EP> [--skip-export]
→ raster/src/<id>.png, raster/ocr.jsonl, raster/items.json"""
import glob, json, os, re, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sg.graph import reach_items
from sg.edl import part_span_to_master

ep = os.path.abspath(sys.argv[1]); root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
cfg = json.load(open(os.path.join(ep, "master_config.json")))
G = json.load(open(os.path.join(ep, cfg["graph"])))
rd = os.path.join(ep, "raster"); src = os.path.join(rd, "src"); os.makedirs(src, exist_ok=True)
HANGUL = re.compile("[가-힣]")

edl = json.load(open(os.path.join(ep, "master/edl.json")))
items = {}
for pid, P in cfg["parts"].items():
    for k, v in reach_items(G, P["comp_id"], 0, P["dur"]).items():
        f = (v["file"] or "").lower()
        if f.endswith((".ai", ".eps", ".pdf", ".png", ".jpg", ".jpeg", ".psd", ".tif", ".tiff", ".gif")):
            e = items.setdefault(k, {**v, "master_spans": []})
            for a, b in v["spans"]:
                e["master_spans"] += part_span_to_master(edl, pid, a, b)
print("footage", len(items))

if "--skip-export" not in sys.argv:
    for f in glob.glob(os.path.join(src, "*")):
        os.remove(f)
    json.dump({"aep": os.path.join(ep, "src", f"{os.path.basename(ep)}_main_ko.aep"), "ids": [int(k) for k in items],
               "k": 4, "max_px": 3000, "out_dir": src, "save_as": os.path.join(rd, "export.aep"),
               "out": os.path.join(rd, "build_export_log.json")},
              open(os.path.join(root, "scripts/ae/build_export_job.json"), "w"), ensure_ascii=False)
    subprocess.run([os.path.join(root, "scripts/ae/run.sh"), os.path.join(root, "scripts/ae/build_export.jsx")], check=True)
    log = json.load(open(os.path.join(rd, "build_export_log.json")))
    print("queued", len(log["queued"]), "errors", log["errors"][:5])
    subprocess.run(["/Applications/Adobe After Effects 2026/aerender", "-project", os.path.join(rd, "export.aep")],
                   check=True, capture_output=True)
    for t in glob.glob(os.path.join(src, "*_0.tif")):
        subprocess.run(["sips", "-s", "format", "png", t, "--out", t[:-6] + ".png"], check=True, capture_output=True)
        os.remove(t)

log = {str(x["id"]): x for x in json.load(open(os.path.join(rd, "build_export_log.json")))["queued"]}
pngs = sorted(glob.glob(os.path.join(src, "*.png")))
with open(os.path.join(rd, "ocr.jsonl"), "w") as f:
    for k in range(0, len(pngs), 50):
        f.write(subprocess.run([os.path.join(root, "tools/ocr")] + pngs[k:k + 50], capture_output=True, text=True).stdout)

brands = set(cfg.get("keep_brands", []))
out = []
for line in open(os.path.join(rd, "ocr.jsonl")):
    d = json.loads(line)
    iid = os.path.basename(d["file"])[:-4]
    ko = [i for i in d.get("items", []) if HANGUL.search(i["text"])]
    if not ko:
        continue
    meta = log[iid]; name = meta["name"]
    kind = "image" if not re.search(r"\.(ai|eps|pdf)$", (items[iid]["file"] or "").lower()) else "ai"
    news = kind == "image" and d["w"] >= 1280
    entries = []
    for i in ko:
        t = re.sub(r"\s+", "", i["text"])
        keep = t in brands
        small = news and i["box"][3] < d["h"] * 0.03
        entries.append({"text": i["text"], "quad": i["quad"], "box": i["box"], "conf": i["conf"],
                        "keep": keep, "blur": bool(small and not keep)})
    mode = "keep_brand" if all(e["keep"] for e in entries) else ("news" if news else "replace")
    out.append({"id": iid, "name": name, "kind": kind, "w": meta["w"], "h": meta["h"], "k": meta["k"],
                "png_w": d["w"], "png_h": d["h"], "mode": mode, "master_spans": items[iid]["master_spans"], "items": entries})
json.dump(out, open(os.path.join(rd, "items.json"), "w"), ensure_ascii=False, indent=1)
from collections import Counter
print("hangul layers", len(out), Counter(x["mode"] for x in out), "text items", sum(len(x["items"]) for x in out),
      "keep", sum(e["keep"] for x in out for e in x["items"]), "blur", sum(e["blur"] for x in out for e in x["items"]))
