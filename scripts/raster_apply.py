"""글자 없는 판 + 영어 텍스트 레이어로 footage 교체 작업 파일을 만들고 AE를 돌린다.
usage: raster_apply.py <EP> <lang> [--dry]
입력: raster/items.json, raster/plate/<id>.png, raster/styles.json, l10n/<lang>.json(raster), raster/manual.json
→ scripts/ae/replace_items_job.json → run.sh replace_items.jsx → build/<lang>/<EP>_<lang>_text_raster.aep"""
import json, os, re, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

FONTS = {"gothic": "OTSBAggroB", "hand": "Noteworthy-Bold"}
FONT_FILES = {"gothic": os.path.expanduser("~/Library/Fonts/SBAggroOTF-B.otf"), "hand": "/System/Library/Fonts/Noteworthy.ttc"}


def check_entry(key, ocr_text, tr, mm, st, font_file):
    """적용 전 검사 → 문제 목록. 번역 키가 다른 글자를 가리키는지(재OCR로 번호가 밀림), 두 색인데 강조 구간이 없는지,
    최종 문구에 폰트에 없는 글자가 있는지."""
    from sg.raster import missing_glyphs
    errs = []
    want = mm.get("ko", tr.get("ko"))
    if want is not None and want != ocr_text:
        errs.append(f"{key}: 번역 키 불일치(번역 원문 '{want}' ≠ OCR '{ocr_text}')")
    t = mm.get("text", tr.get("text", ""))
    if st.get("two_tone") and "[[" not in t:
        errs.append(f"{key}: 두 색 글자인데 강조 구간([[ ]])이 없음")
    miss = missing_glyphs(t, font_file) if t and t != "__SKIP__" else []
    if miss:
        errs.append(f"{key}: 폰트에 없는 글리프 {miss}")
    return errs


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
            "base": list(st["base"]), "emph_color": list(st["emph"]),
            "stroke": list(st["stroke"]) if st.get("stroke") else None, "stroke_w": st.get("stroke_w", 0) * s}


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
    jobs, problems = [], []
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
            problems += check_entry(key, x["items"][n]["text"], tr, mm, st, FONT_FILES[font])
            texts.append({"key": key, **text_spec(t, st, s, font)})
        jobs.append({"id": int(x["id"]), "name": x["name"].split("/")[-1], "png": png,
                     "w": x["w"], "h": x["h"], "scale": s * 100, "texts": texts})
    bd = os.path.join(ep, "build", lang)
    job = {"aep": os.path.join(bd, f"{code}_{lang}_text.aep"),
           "save_as": os.path.join(bd, f"{code}_{lang}_text_raster.aep"),
           "out": os.path.join(bd, "replace_items_log.json"), "jobs": jobs}
    json.dump(job, open(os.path.join(root, "scripts/ae/replace_items_job.json"), "w"), ensure_ascii=False, indent=1)
    print("footage", len(jobs), "text layers", sum(len(j["texts"]) for j in jobs))
    if problems:
        print("\n".join(problems))
        sys.exit(f"적용 전 검사 실패 {len(problems)}건")
    if "--dry" not in sys.argv:
        if os.path.exists(job["out"]):
            os.remove(job["out"])                 # 옛 기록을 성공으로 오인하지 않게
        subprocess.run([os.path.join(root, "scripts/ae/run.sh"), os.path.join(root, "scripts/ae/replace_items.jsx")], check=True)
        if not os.path.exists(job["out"]):
            sys.exit("replace_items.jsx가 기록을 남기지 않음(AE 스크립트 오류 대화상자 확인)")
        log = json.load(open(job["out"]))
        print({k: (v if not isinstance(v, list) else len(v)) for k, v in log.items()})
        print("errors", log.get("errors", [])[:10])
        bad = {k: log.get(k) for k in ("errors", "not_found", "emph_failed", "name_mismatch") if log.get(k)}
        if bad:
            sys.exit(f"AE 교체 문제: {bad}")
