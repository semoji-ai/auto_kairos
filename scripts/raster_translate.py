"""일러스트 문구 번역.  usage: raster_translate.py <EP> <lang>  → l10n/<lang>.json 의 "raster" 섹션
키 "<footage id>#<n>": {"text", "font", "two_tone"}  (text == "__SKIP__"면 OCR 잡음 → 건드리지 않음)"""
import json, os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sg.raster import missing_glyphs, quad_geom
from sg.plate import text_style
from sg.translate import translate_batch, claude_runner

ep, lang = sys.argv[1], sys.argv[2]
root = os.path.join(os.path.dirname(__file__), "..")
gloss = json.load(open(os.path.join(root, "glossary", f"{lang}.json")))
_prof = json.load(open(os.path.join(root, "profiles", f"{lang}.json")))
_rf = {k: os.path.expanduser(v["file"]) for k, v in _prof["raster_fonts"].items()}
FONTS = {"gothic": [_rf["label"], _rf["title"]], "hand": [_rf["hand"], _rf["brush"]]}   # 종류별로 쓰일 수 있는 폰트 전부
segs = json.load(open(os.path.join(ep, "master/source.json")))["segments"]
items = json.load(open(os.path.join(ep, "raster/items.json")))
lp = os.path.join(ep, "l10n", f"{lang}.json"); L = json.load(open(lp)); L.setdefault("raster", {})
mp = os.path.join(ep, "raster/manual.json")
hand = set(json.load(open(mp)).get("_hand_footage", [])) if os.path.exists(mp) else set()   # 적용 단계와 같은 폰트 규칙


def context(spans):
    if not spans:
        return ""
    a, b = spans[0]
    return " ".join(g["ko"] for g in segs if g["out"] > a - 1 and g["in"] < b + 1 and not g.get("nonverbal"))[:300]


todo = []
for x in items:
    if x["mode"] == "keep_brand" or not x["master_spans"]:
        continue
    arr = np.array(Image.open(os.path.join(ep, "raster/src", f"{x['id']}.png")).convert("RGBA"))
    font = "hand" if x["id"] in hand else "gothic"
    for n, e in enumerate(x["items"]):
        if e["keep"] or e["blur"]:
            continue
        key = f"{x['id']}#{n}"
        if key in L["raster"]:
            continue
        _, w, h, _, _ = quad_geom(e["quad"])
        two = text_style(arr, e["quad"])["two_tone"]     # 적용 단계(raster_apply)와 같은 판정
        todo.append({"id": key, "ko": e["text"], "max_chars": max(6, int(w / (0.4 * h) * 1.3)), "two_tone": two,
                     "layer": x["name"].split("/")[0], "context": context(x["master_spans"]), "_font": font})
print("to translate", len(todo))
for k in range(0, len(todo), 30):
    batch = todo[k:k + 30]
    pending = batch
    for attempt in range(3):
        res = translate_batch([{kk: v for kk, v in it.items() if not kk.startswith("_")} for it in pending], gloss, lang, "raster", claude_runner)
        bad = []
        for it in pending:
            t = res[it["id"]].strip()
            if t != "__SKIP__" and any(missing_glyphs(t, f) for f in FONTS[it["_font"]]):
                bad.append(it); continue
            L["raster"][it["id"]] = {"text": t, "font": it["_font"], "two_tone": it["two_tone"], "ko": it["ko"]}
        if not bad:
            break
        pending = [{**it, "context": it["context"] + " (previous answer used characters the font lacks; use only common characters)"} for it in bad]
    json.dump(L, open(lp, "w"), ensure_ascii=False, indent=1)
    print(f"{min(k + 30, len(todo))}/{len(todo)}", flush=True)
skip = sum(1 for v in L["raster"].values() if v["text"] == "__SKIP__")
print("done", len(L["raster"]), "skip", skip)
