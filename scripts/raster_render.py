"""교체 PNG 생성 + 검수 시트.  usage: raster_render.py <EP> <lang> [--only id,id]
→ raster/<lang>/<id>.png, raster/review_<lang>_<n>.png"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sg.raster import replace_items

ep, lang = sys.argv[1], sys.argv[2]
only = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
FONTS = {"gothic": (os.path.expanduser("~/Library/Fonts/SBAggroOTF-B.otf"), 0), "hand": ("/System/Library/Fonts/Noteworthy.ttc", 1)}
items = json.load(open(os.path.join(ep, "raster/items.json")))
R = json.load(open(os.path.join(ep, "l10n", f"{lang}.json")))["raster"]
manual = json.load(open(os.path.join(ep, "raster/manual.json"))) if os.path.exists(os.path.join(ep, "raster/manual.json")) else {}
od = os.path.join(ep, "raster", lang); os.makedirs(od, exist_ok=True)
done = []
for x in items:
    if x["mode"] == "keep_brand" or (only and x["id"] not in only):
        continue
    arr = np.array(Image.open(os.path.join(ep, "raster/src", f"{x['id']}.png")).convert("RGBA"))
    changed = False
    todo = []
    for n, e in enumerate(x["items"]):
        key = f"{x['id']}#{n}"
        if e["keep"]:
            continue
        if e["blur"]:   # 뉴스 캡처의 작은 본문: 흐림
            bx, by, bw, bh = [int(v) for v in e["box"]]
            im = Image.fromarray(arr); crop = im.crop((bx, by, bx + bw, by + bh)).filter(ImageFilter.GaussianBlur(max(2, bh // 3)))
            im.paste(crop, (bx, by)); arr = np.array(im); changed = True; continue
        v = R.get(key)
        if not v or v["text"] == "__SKIP__":
            continue
        m = manual.get(key, {})
        todo.append({"quad": e["quad"], "en": m.get("text", v["text"]), "two_tone": v["two_tone"],
                     "colors": [tuple(c) for c in m["colors"]] if "colors" in m else None,
                     "size_ratio": m.get("size_ratio", 0.72), "_font": m.get("font", v["font"])})
    if todo:
        tmp_in = os.path.join(od, f"_{x['id']}_in.png"); Image.fromarray(arr).save(tmp_in)
        font = FONTS[todo[0]["_font"]]
        replace_items(tmp_in, os.path.join(od, f"{x['id']}.png"), todo, font[0], font[1])
        os.remove(tmp_in); arr = np.array(Image.open(os.path.join(od, f"{x['id']}.png"))); changed = True
    if changed:
        Image.fromarray(arr).save(os.path.join(od, f"{x['id']}.png"))
        done.append(x)
print("rendered", len(done))
# 검수 시트(원본 | 교체), 시트당 12쌍
pairs = []
for x in done:
    row = []
    for f in [os.path.join(ep, "raster/src", f"{x['id']}.png"), os.path.join(od, f"{x['id']}.png")]:
        im = Image.open(f).convert("RGBA"); bg = Image.new("RGBA", im.size, (110, 110, 110, 255)); bg.alpha_composite(im)
        s = min(1.0, 520 / im.width, 260 / im.height); row.append(bg.convert("RGB").resize((max(1, int(im.width * s)), max(1, int(im.height * s)))))
    pairs.append((x, row))
for si in range(0, len(pairs), 12):
    chunk = pairs[si:si + 12]
    H = sum(max(r[0].height, r[1].height) + 26 for _, r in chunk)
    sheet = Image.new("RGB", (1080, H), (25, 25, 25)); d = ImageDraw.Draw(sheet); y = 0
    for x, r in chunk:
        d.text((4, y + 2), f"{x['id']}  {x['name'].split('/')[0]}", fill=(255, 220, 0))
        sheet.paste(r[0], (0, y + 22)); sheet.paste(r[1], (540, y + 22)); y += max(r[0].height, r[1].height) + 26
    sheet.save(os.path.join(ep, "raster", f"review_{lang}_{si // 12 + 1:02d}.png"))
print("sheets", (len(pairs) + 11) // 12)
