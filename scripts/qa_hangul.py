"""영상 전체 한글 검사(게이트).  usage: qa_hangul.py <EP> <lang> [--step 1.0]
미리보기에서 step초 간격 프레임 → tools/ocr → 한글 포함 항목 중 브랜드 표기만인 것 제외 → render/<lang>/qa/hangul.json + 문제 프레임 시트."""
import glob, json, os, re, subprocess, sys

HANGUL = re.compile(r"[가-힣ㄱ-ㆎ]")


def is_problem(text, brands):
    """한글이 있고, 브랜드 표기를 빼고도 한글이 남으면 문제."""
    if not HANGUL.search(text):
        return False
    rest = text
    for b in sorted(brands, key=len, reverse=True):
        rest = rest.replace(b, " ")
    return bool(HANGUL.search(rest))


SYL = re.compile(r"[가-힣]")


NUM_UNIT = re.compile(r"\d[\d.,]*\s*[가-힣]")
LATIN = re.compile(r"[A-Za-z]")


def is_noise(text, conf):
    """OCR 오독 '형태'만 잡음으로 본다(진짜 한글을 숨기지 않게 좁게):
    신뢰도 1.0·숫자+단위·한글 2자 이상은 절대 잡음 아님. 잡음 = 자모/기호만, 또는 영문 사이에 낀 한글 1자."""
    syl = len(SYL.findall(text))
    if conf >= 1.0 or NUM_UNIT.search(text) or syl >= 2:
        return False
    return syl == 0 or len(LATIN.findall(text)) >= 3


HAN = re.compile(r"[一-鿿]")


def read_as_chinese(item, zh_items, min_conf=0.5, min_overlap=0.5):
    """한국어 판독에서 한글로 나온 상자를 중국어 판독이 같은 자리에서 한자로 자신 있게 읽었으면 → 실제로는 중국어."""
    x, y, w, h = item["box"]
    for z in zh_items:
        if z["conf"] < min_conf or not HAN.search(z["text"]):
            continue
        zx, zy, zw, zh_ = z["box"]
        ix = max(0, min(x + w, zx + zw) - max(x, zx)); iy = max(0, min(y + h, zy + zh_) - max(y, zy))
        if ix * iy >= min_overlap * min(w * h, zw * zh_):
            return True
    return False


if __name__ == "__main__":
    ep, lang = os.path.abspath(sys.argv[1]), sys.argv[2]
    step = float(sys.argv[sys.argv.index("--step") + 1]) if "--step" in sys.argv else 1.0
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    code = os.path.basename(ep)
    cfg = json.load(open(os.path.join(ep, "master_config.json")))
    brands = cfg.get("keep_brands", [])
    video = os.path.join(ep, "render", lang, f"{code}_{lang.upper()}_preview.mp4")
    qd = os.path.join(ep, "render", lang, "qa"); fd = os.path.join(qd, "frames")
    os.makedirs(fd, exist_ok=True)
    for f in glob.glob(os.path.join(fd, "*.png")):
        os.remove(f)
    subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", f"fps=1/{step},scale=1920:-2", os.path.join(fd, "f_%05d.png")], check=True)
    frames = sorted(glob.glob(os.path.join(fd, "*.png")))
    # 중국어판: 한국어 판독은 한자를 한글로 잘못 읽음 → 중국어로도 읽어 같은 자리에 한자가 있으면 제외
    zh_read = {}
    if lang.startswith("zh"):
        for k in range(0, len(frames), 50):
            res = subprocess.run([os.path.join(root, "tools/ocr")] + frames[k:k + 50], capture_output=True, text=True,
                                 env={**os.environ, "OCR_LANGS": "zh-Hans,en-US"}).stdout
            for line in res.splitlines():
                d = json.loads(line); zh_read[d["file"]] = d["items"]
    out = []
    for k in range(0, len(frames), 50):
        res = subprocess.run([os.path.join(root, "tools/ocr")] + frames[k:k + 50], capture_output=True, text=True).stdout
        for line in res.splitlines():
            d = json.loads(line)
            t = (int(os.path.basename(d["file"])[2:7]) - 1) * step
            bad = [it for it in d["items"] if is_problem(it["text"], brands)
                   and not read_as_chinese(it, zh_read.get(d["file"], []))]
            if bad:
                out.append({"t": round(t, 2), "file": d["file"],
                            "items": [{"text": b["text"], "box": b["box"], "conf": b["conf"], "noise": is_noise(b["text"], b["conf"])} for b in bad]})
    json.dump(out, open(os.path.join(qd, "hangul.json"), "w"), ensure_ascii=False, indent=1)
    out = [dict(o, items=[b for b in o["items"] if not b["noise"]]) for o in out]   # 시트·게이트는 잡음 제외
    out = [o for o in out if o["items"]]
    from PIL import Image, ImageDraw
    for si in range(0, len(out), 12):
        chunk = out[si:si + 12]
        sheet = Image.new("RGB", (960 * 2, 560 * ((len(chunk) + 1) // 2)), (20, 20, 20)); d = ImageDraw.Draw(sheet)
        for i, o in enumerate(chunk):
            im = Image.open(o["file"]).convert("RGB"); dr = ImageDraw.Draw(im)
            for b in o["items"]:
                x, y, w, h = b["box"]                      # 픽셀, 왼쪽 위 기준
                dr.rectangle([x, y, x + w, y + h], outline=(255, 0, 0), width=4)
            im = im.resize((960, 540)); px, py = (i % 2) * 960, (i // 2) * 560
            sheet.paste(im, (px, py)); d.text((px + 6, py + 542), f"{o['t']:.0f}s  " + " | ".join(b["text"] for b in o["items"])[:120], fill=(255, 220, 0))
        sheet.save(os.path.join(qd, f"hangul_sheet_{si // 12 + 1:02d}.png"))
    print("frames", len(frames), "problem frames", len(out))
    if "--gate" in sys.argv and out:
        sys.exit(1)
