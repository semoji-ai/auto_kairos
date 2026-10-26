"""글자 없는 판 생성(언어 무관) + 글자 스타일 추출.  usage: raster_plates.py <EP>
→ raster/plate/<id>.png, raster/styles.json {"<id>#<n>": {angle,w,h,cx,cy,base,emph,two_tone}}, raster/plate_review_NN.png"""
import glob, json, os, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sg.plate import clean_plate, text_style, blur_text

ep = sys.argv[1]
items = json.load(open(os.path.join(ep, "raster/items.json")))
R = {}                                    # __SKIP__(그림 잡음) 판정만 사용 — 판은 언어 무관이라 있는 번역 아무거나(편마다 만든 언어가 다름)
for _f in sorted(glob.glob(os.path.join(ep, "l10n", "*.json"))):
    if not os.path.basename(_f).startswith("_") and "_" not in os.path.basename(_f)[:-5]:
        R.update(json.load(open(_f)).get("raster", {}))
mp = os.path.join(ep, "raster/manual.json")
manual = json.load(open(mp)) if os.path.exists(mp) else {}   # {"<id>#<n>": {"skip"|"text"|"font"}} 사람이 고친 값
od = os.path.join(ep, "raster/plate"); os.makedirs(od, exist_ok=True)
styles, done = {}, []
for x in items:
    if x["mode"] == "keep_brand" or not x["master_spans"]:
        continue
    src = np.array(Image.open(os.path.join(ep, "raster/src", f"{x['id']}.png")).convert("RGBA"))
    targets = [(n, e) for n, e in enumerate(x["items"])
               if not e["keep"] and R.get(f"{x['id']}#{n}", {}).get("text") != "__SKIP__"
               and not manual.get(f"{x['id']}#{n}", {}).get("skip")]
    if not targets:
        continue
    news = x["mode"] == "news"
    for n, e in targets:                       # 스타일은 원본에서
        st = text_style(src, e["quad"])
        if news and st["h"] < x["h"] * 0.03:   # 뉴스 캡처의 작은 글자: 흐림만, 영어 안 올림
            st["blur_only"] = True
        styles[f"{x['id']}#{n}"] = st
    arr = src
    for n, e in targets:                       # 판은 차례로 채움(뉴스 사진은 흐림)
        arr = blur_text(arr, e["quad"]) if news else clean_plate(arr, e["quad"])
    Image.fromarray(arr).save(os.path.join(od, f"{x['id']}.png")); done.append(x)
for f in os.listdir(od):                       # 이번에 판을 만들지 않은 footage(수동 건너뛰기 등)의 옛 판은 지움
    if f.endswith(".png") and f[:-4] not in {str(x["id"]) for x in done}:
        os.remove(os.path.join(od, f))
json.dump(styles, open(os.path.join(ep, "raster/styles.json"), "w"), indent=1)
pairs = []
for x in done:
    row = []
    for f in [os.path.join(ep, "raster/src", f"{x['id']}.png"), os.path.join(od, f"{x['id']}.png")]:
        im = Image.open(f).convert("RGBA"); bg = Image.new("RGBA", im.size, (110, 110, 110, 255)); bg.alpha_composite(im)
        s = min(1.0, 520 / im.width, 220 / im.height); row.append(bg.convert("RGB").resize((max(1, int(im.width * s)), max(1, int(im.height * s)))))
    pairs.append((x, row))
for si in range(0, len(pairs), 14):
    chunk = pairs[si:si + 14]; H = sum(max(r[0].height, r[1].height) + 24 for _, r in chunk)
    sheet = Image.new("RGB", (1080, H), (25, 25, 25)); d = ImageDraw.Draw(sheet); y = 0
    for x, r in chunk:
        d.text((4, y + 2), f"{x['id']}  {x['name'].split('/')[0]}", fill=(255, 220, 0))
        sheet.paste(r[0], (0, y + 20)); sheet.paste(r[1], (540, y + 20)); y += max(r[0].height, r[1].height) + 24
    sheet.save(os.path.join(ep, "raster", f"plate_review_{si // 14 + 1:02d}.png"))
print("plates", len(done), "styles", len(styles), "sheets", (len(pairs) + 13) // 14)
