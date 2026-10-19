"""글자 없는 판 + 영어 텍스트 레이어로 footage 교체 작업 파일을 만들고 AE를 돌린다.
usage: raster_apply.py <EP> <lang> [--dry]
입력: raster/items.json, raster/plate/<id>.png, raster/styles.json, l10n/<lang>.json(raster), raster/manual.json
→ scripts/ae/replace_items_job.json → run.sh replace_items.jsx → build/<lang>/<EP>_<lang>_text_raster.aep"""
import json, os, re, subprocess, sys

FONTS = {"gothic": "OTSBAggroB", "hand": "Noteworthy-Bold"}


def split_emph(text):
    """'a [[b]] c' → ('a b c', [[2, 3]])  (강조 구간: 글자 위치 [시작, 끝))"""
    plain, ranges, pos = "", [], 0
    for i, part in enumerate(re.split(r"\[\[|\]\]", text)):
        if i % 2 and part:
            ranges.append([len(plain), len(plain) + len(part)])
        plain += part
    return plain, ranges


def text_spec(text, st, s, font):
    """styles.json 한 항목(내보낸 PNG 좌표) → footage 좌표의 AE 텍스트 레이어 사양. s = footage폭/PNG폭."""
    plain, rng = split_emph(text)
    return {"text": plain, "emph": rng if st.get("two_tone") else [],
            "font": FONTS[font], "size": st["h"] * 0.72 * s,
            "cx": st["cx"] * s, "cy": st["cy"] * s, "angle": st["angle"], "wmax": st["w"] * s,
            "base": list(st["base"]), "emph_color": list(st["emph"])}


if __name__ == "__main__":
    ep, lang = sys.argv[1], sys.argv[2]
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    ep = os.path.abspath(ep)
    code = os.path.basename(ep)
    rd = os.path.join(ep, "raster")
    items = json.load(open(os.path.join(rd, "items.json")))
    styles = json.load(open(os.path.join(rd, "styles.json")))
    R = json.load(open(os.path.join(ep, "l10n", f"{lang}.json"))).get("raster", {})
    mp = os.path.join(rd, "manual.json")
    manual = json.load(open(mp)) if os.path.exists(mp) else {}
    hand = set(manual.get("_hand_footage", []))
    jobs = []
    for x in items:
        png = os.path.join(rd, "plate", f"{x['id']}.png")
        if not os.path.exists(png):
            continue
        s = x["w"] / x["png_w"]
        texts = []
        for n, _ in enumerate(x["items"]):
            key = f"{x['id']}#{n}"
            st, tr, mm = styles.get(key), R.get(key, {}), manual.get(key, {})
            if not st or st.get("blur_only") or mm.get("skip"):
                continue
            t = mm.get("text", tr.get("text"))
            if not t or t == "__SKIP__":
                continue
            font = mm.get("font") or ("hand" if x["id"] in hand else "gothic")
            texts.append({"key": key, **text_spec(t, st, s, font)})
        jobs.append({"id": int(x["id"]), "name": x["name"].split("/")[-1], "png": png,
                     "w": x["w"], "h": x["h"], "scale": s * 100, "texts": texts})
    bd = os.path.join(ep, "build", lang)
    job = {"aep": os.path.join(bd, f"{code}_{lang}_text.aep"),
           "save_as": os.path.join(bd, f"{code}_{lang}_text_raster.aep"),
           "out": os.path.join(bd, "replace_items_log.json"), "jobs": jobs}
    json.dump(job, open(os.path.join(root, "scripts/ae/replace_items_job.json"), "w"), ensure_ascii=False, indent=1)
    print("footage", len(jobs), "text layers", sum(len(j["texts"]) for j in jobs))
    if "--dry" not in sys.argv:
        subprocess.run([os.path.join(root, "scripts/ae/run.sh"), os.path.join(root, "scripts/ae/replace_items.jsx")], check=True)
        log = json.load(open(job["out"]))
        print({k: (v if not isinstance(v, list) else len(v)) for k, v in log.items()})
        print("errors", log.get("errors", [])[:10])
