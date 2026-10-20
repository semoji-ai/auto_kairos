"""언어별 공용 에셋 빌드(모든 편에서 재사용).  usage: build_global_assets.py <lang> emotion|title|outro <원본 파일>
emotion: 감정 영상의 글자 덩어리(예: 킥킥의 ㅋ)를 프레임마다 추적 → AE 텍스트 레이어 키프레임으로 다시 만듦.
결과: assets/global/<lang>/<원본 파일명>, 비교 시트 assets/global/<lang>/review_<종류>.png"""
import glob, json, os, shutil, subprocess, sys, tempfile, unicodedata
import numpy as np
import cv2
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from sg.blobs import track_blobs

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AERENDER = "/Applications/Adobe After Effects 2026/aerender"
TEXT = {"en": {"laugh": "ha", "logo_rows": ["SE", "MO", "JI"], "subscribe": "Subscribe", "like": "Like",
               "outro": "Semoji"}}


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate,nb_frames:format=duration", "-of", "json", path],
                         capture_output=True, text=True).stdout
    d = json.loads(out); s = d["streams"][0]; a, b = s["r_frame_rate"].split("/")
    return {"w": s["width"], "h": s["height"], "fps": float(a) / float(b), "dur": float(d["format"]["duration"])}


def frames_rgba(path, tmp):
    subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-pix_fmt", "rgba", os.path.join(tmp, "f_%05d.png")], check=True)
    return [np.array(Image.open(f).convert("RGBA")) for f in sorted(glob.glob(os.path.join(tmp, "f_*.png")))]


def glyph_colors(frames, track):
    """덩어리 안쪽(침식) 중앙값 = 글자색, 가장자리 띠 중앙값 = 외곽선색, 외곽선 두께."""
    i = max((k for k, s in enumerate(track) if s), key=lambda k: track[k]["area"])
    a = frames[i][:, :, 3] > 200
    s = track[i]
    x0, y0 = int(s["cx"] - s["w"]), int(s["cy"] - s["w"])
    box = np.zeros_like(a); box[max(0, y0):y0 + int(2 * s["w"]), max(0, x0):x0 + int(2 * s["w"])] = True
    m = (a & box).astype(np.uint8)
    dist = cv2.distanceTransform(m, cv2.DIST_L2, 3)
    inner = dist > dist.max() * 0.5
    edge = (dist > 0) & (dist <= max(1.5, dist.max() * 0.25))
    rgb = frames[i][:, :, :3].astype(int)
    fill = np.median(rgb[inner], 0); stroke = np.median(rgb[edge], 0)
    # 외곽선 두께 = 외곽선 색 픽셀 면적 / 덩어리 둘레
    near_stroke = (m > 0) & (np.abs(rgb - stroke).sum(2) < np.abs(rgb - fill).sum(2))
    perim = max(1, int(((dist > 0) & (dist <= 1.0)).sum()))
    return fill.astype(int).tolist(), stroke.astype(int).tolist(), float(near_stroke.sum() / perim)


def emotion(lang, src):
    P = probe(src)
    tmp = tempfile.mkdtemp()
    fr = frames_rgba(src, tmp)
    tracks = [t for t in track_blobs(fr) if sum(1 for s in t if s) > len(fr) * 0.3]
    out_tracks = []
    for t in tracks:
        vis = [s for s in t if s]
        w_ref = float(np.median([s["w"] for s in vis])); h_ref = float(np.median([s["h"] for s in vis]))
        ang = float(np.median([s["angle"] for s in vis]))
        rot = ang + 90 if ang <= -45 else ang                # minAreaRect 각도(-90,0] → 기울기
        fill, stroke, sw = glyph_colors(fr, t)
        keys = [None if s is None else {"t": round(i / P["fps"], 5), "cx": s["cx"], "cy": s["cy"], "scale": s["w"] / w_ref,
                                        "alpha": s["alpha"]} for i, s in enumerate(t)]
        out_tracks.append({"h_ref": h_ref, "rot": rot, "fill": fill, "stroke": stroke, "stroke_w": sw, "keys": keys})
    name = os.path.basename(src)
    od = os.path.join(ROOT, "assets", "global", lang); bd = os.path.join(od, "build"); os.makedirs(bd, exist_ok=True)
    out = os.path.join(od, unicodedata.normalize("NFC", name))
    job = {"w": P["w"], "h": P["h"], "fps": P["fps"], "dur": P["dur"], "text": TEXT[lang]["laugh"], "font": "OTSBAggroB",
           "tracks": out_tracks, "save_as": os.path.join(bd, "emotion_" + os.path.splitext(name)[0] + ".aep"),
           "render_to": os.path.join(bd, "emotion_render.mov"), "out": os.path.join(bd, "emotion_log.json")}
    run_jsx("build_emotion_en", job)
    shutil.move(job["render_to"], out)
    check_same(src, out)
    sheet(src, out, os.path.join(od, f"review_emotion.png"))
    shutil.rmtree(tmp, ignore_errors=True)
    print("ok", out, "tracks", len(out_tracks))


def run_jsx(name, job):
    jp = os.path.join(ROOT, "scripts", "ae", f"{name}_job.json")
    json.dump(job, open(jp, "w"), ensure_ascii=False, indent=1)
    if os.path.exists(job["out"]):
        os.remove(job["out"])
    js = os.path.join(ROOT, "scripts", "ae", f"{name}.jsx")
    tmpjs = os.path.join(tempfile.gettempdir(), f"{name}_check.js"); shutil.copy(js, tmpjs)
    subprocess.run(["node", "--check", tmpjs], check=True)        # AE 오류 대화상자로 멈추기 전에 문법 확인
    subprocess.run([os.path.join(ROOT, "scripts", "ae", "run.sh"), os.path.join(ROOT, "scripts", "ae", f"{name}.jsx")], check=True)
    if not os.path.exists(job["out"]):
        sys.exit(f"{name}.jsx가 기록을 남기지 않음(AE 오류 대화상자 확인)")
    log = json.load(open(job["out"]))
    if log.get("errors"):
        sys.exit(f"{name}.jsx 오류: {log['errors']}")
    r = subprocess.run([AERENDER, "-project", job["save_as"]], capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(job["render_to"]):
        sys.exit("aerender 실패: " + r.stdout[-800:])


def check_same(a, b):
    pa, pb = probe(a), probe(b)
    bad = [k for k in ("w", "h") if pa[k] != pb[k]] + [k for k in ("fps", "dur") if abs(pa[k] - pb[k]) > 0.02]
    if bad:
        sys.exit(f"대체 에셋이 원본과 다름 {bad}: {pa} vs {pb}")


def sheet(a, b, out, n=4):
    d = probe(a)["dur"]; rows = []
    for k in range(n):
        t = d * (k + 1) / (n + 1); pair = []
        for f in (a, b):
            raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", f, "-frames:v", "1", "-f", "image2pipe",
                                  "-vcodec", "png", "-"], capture_output=True).stdout
            im = Image.open(__import__("io").BytesIO(raw)).convert("RGBA")
            bg = Image.new("RGBA", im.size, (120, 120, 120, 255)); bg.alpha_composite(im)
            pair.append(bg.convert("RGB").resize((640, 360)))
        rows.append(pair)
    sh = Image.new("RGB", (1290, 370 * n), (20, 20, 20))
    for k, (x, y) in enumerate(rows):
        sh.paste(x, (0, k * 370)); sh.paste(y, (650, k * 370))
    sh.save(out)


def ocr(png):
    d = json.loads(subprocess.run([os.path.join(ROOT, "tools", "ocr"), png], capture_output=True, text=True).stdout)
    return d["items"]


def ring_color(img, box, pad=12):
    """상자 바로 바깥 띠의 중앙값 색(판 색)."""
    x, y, w, h = [int(v) for v in box]
    H, W = img.shape[:2]
    m = np.zeros((H, W), bool); m[max(0, y - pad):y + h + pad, max(0, x - pad):x + w + pad] = True
    m[y:y + h, x:x + w] = False
    return np.median(img[m][:, :3], 0).astype(int).tolist()


def ink_color(img, box, bg):
    x, y, w, h = [int(v) for v in box]
    r = img[y:y + h, x:x + w, :3].astype(int)
    d = np.abs(r - np.array(bg)).sum(2)
    return np.median(r[d > d.max() * 0.6], 0).astype(int).tolist()


def pad_box(b, p):
    return [b[0] - p, b[1] - p, b[2] + 2 * p, b[3] + 2 * p]


def finish_video(render, src, out):
    """AE 결과(무손실 mov)를 원본과 같은 h264로, 원본 오디오가 있으면 다시 입힘."""
    has_audio = bool(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                                     "-of", "csv=p=0", src], capture_output=True, text=True).stdout.strip())
    args = ["ffmpeg", "-v", "error", "-y", "-i", render] + (["-i", src, "-map", "0:v", "-map", "1:a", "-c:a", "copy"] if has_audio else [])
    subprocess.run(args + ["-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", "-r", f"{probe(src)['fps']:.5f}", out], check=True)


def title(lang, src):
    P = probe(src); tmp = tempfile.mkdtemp()
    subprocess.run(["ffmpeg", "-v", "error", "-i", src, os.path.join(tmp, "f_%05d.png")], check=True)
    fs = sorted(glob.glob(os.path.join(tmp, "f_*.png"))); fr = [np.array(Image.open(f).convert("RGB")) for f in fs]
    last = fr[-1]; bg = [int(v) for v in np.median(last[:40, :40].reshape(-1, 3), 0)]
    items = ocr(fs[-1]); T = TEXT[lang]
    rows = sorted([i for i in items if i["box"][1] < 800], key=lambda i: i["box"][1])
    sub = [i for i in items if i["box"][1] >= 800 and i["box"][0] < 900][0]
    like = [i for i in items if i["box"][1] >= 800 and i["box"][0] >= 900][0]
    # 로고 묶음: 프레임마다 로고(위쪽 800px 안 바탕과 다른 픽셀) 외곽 상자 → 마지막 프레임 대비 크기·중심
    def bbox(f):
        d = np.abs(f[:800].astype(int) - np.array(bg)).sum(2) > 60
        if d.sum() < 30:
            return None
        ys, xs = np.where(d); return xs.min(), ys.min(), xs.max(), ys.max()
    L = bbox(last); Lw = L[2] - L[0]; Lc = ((L[0] + L[2]) / 2, (L[1] + L[3]) / 2)
    keys = []
    for k, f in enumerate(fr):
        b = bbox(f)
        keys.append(None if b is None else {"t": round(k / P["fps"], 5), "cx": (b[0] + b[2]) / 2, "cy": (b[1] + b[3]) / 2,
                                           "s": (b[2] - b[0]) / Lw})
    text_box = [min(r["box"][0] for r in rows), min(r["box"][1] for r in rows),
                max(r["box"][0] + r["box"][2] for r in rows) - min(r["box"][0] for r in rows),
                max(r["box"][1] + r["box"][3] for r in rows) - min(r["box"][1] for r in rows)]
    logo_bg = ring_color(last, text_box, 6); ink = ink_color(last, rows[0]["box"], logo_bg)
    # 정지 화면은 로고 외곽 상자 안만(버튼 등 나머지는 투명) — 묶음이 움직일 때 다른 요소가 따라오지 않게
    rgba = np.dstack([last, np.zeros(last.shape[:2], np.uint8)])
    rgba[max(0, L[1] - 4):L[3] + 5, max(0, L[0] - 4):L[2] + 5, 3] = 255
    still = os.path.join(tmp, "logo_still.png"); Image.fromarray(rgba).save(still)
    od = os.path.join(ROOT, "assets", "global", lang); bd = os.path.join(od, "build"); os.makedirs(bd, exist_ok=True)
    keep_still = os.path.join(bd, "title_logo_still.png"); shutil.copy(still, keep_still)
    logo = {"still": keep_still, "keys": keys, "anchor": [Lc[0], Lc[1]],
            "plates": [{"box": pad_box(text_box, 3), "color": logo_bg, "from": 0}],      # 여백 작게(로고 테두리 보존)
            "texts": [{"text": T["logo_rows"][k], "font": "OTSBAggroB", "h": r["box"][3] * 0.78, "color": ink,
                       "x": r["box"][0], "y": r["box"][1] + r["box"][3] / 2, "just": "left", "wmax": text_box[2], "from": 0}
                      for k, r in enumerate(rows)]}
    fx = lambda it: appear_time_box(fr, it["box"], bg, P["fps"])
    sub_bg = ring_color(last, sub["box"], 4); sub_ink = ink_color(last, sub["box"], sub_bg)
    like_ink = ink_color(last, like["box"], bg)
    # 바탕 위 가림판은 단색 대신 0번 프레임(로고 나오기 전 깨끗한 바탕)을 오려 씀 — 바탕의 미세한 명암까지 같게
    def bg_patch(box, name):
        x, y, w, h = [int(v) for v in box]
        a = np.zeros(fr[0].shape[:2], np.uint8); a[max(0, y):y + h, max(0, x):x + w] = 255
        pth = os.path.join(bd, name); Image.fromarray(np.dstack([fr[0], a])).save(pth); return pth
    boxes = [b for b in (bbox(f) for f in fr[:int(P["fps"] * 0.9)]) if b]
    U = [min(b[0] for b in boxes) - 8, min(b[1] for b in boxes) - 8,
         max(b[2] for b in boxes) - min(b[0] for b in boxes) + 16, max(b[3] for b in boxes) - min(b[1] for b in boxes) + 16]
    base = {"still": None, "keys": None,
            "images": [{"png": bg_patch(U, "title_hide_logo.png"), "from": 0},          # 원래 로고(애니메이션 포함)를 가림
                       {"png": bg_patch(pad_box(like["box"], 6), "title_hide_like.png"), "from": fx(like)}],
            "plates": [{"box": pad_box(sub["box"], 4), "color": sub_bg, "from": fx(sub)}],
            "texts": [{"text": T["subscribe"], "font": "OTSBAggroB", "h": sub["box"][3] * 0.6, "color": sub_ink,
                       "x": sub["box"][0] + sub["box"][2] / 2, "y": sub["box"][1] + sub["box"][3] / 2, "just": "center",
                       "wmax": sub["box"][2] + 16, "from": fx(sub)},
                      {"text": T["like"], "font": "OTSBAggroB", "h": like["box"][3] * 0.6, "color": like_ink,
                       "x": like["box"][0], "y": like["box"][1] + like["box"][3] / 2, "just": "left",
                       "wmax": like["box"][2] + 40, "from": fx(like)}]}
    build_overlay(lang, src, "title", [base, logo], P)
    shutil.rmtree(tmp, ignore_errors=True)


def appear_time_box(frames, box, bg, fps):
    from sg.regions import appear_time
    return appear_time(frames, [int(v) for v in box], bg, fps=fps) or 0.0


def outro(lang, src):
    P = probe(src); tmp = tempfile.mkdtemp()
    f = os.path.join(tmp, "f.png")
    subprocess.run(["ffmpeg", "-v", "error", "-ss", "5", "-i", src, "-frames:v", "1", f], check=True)
    img = np.array(Image.open(f).convert("RGB"))
    it = [i for i in ocr(f) if any("가" <= c <= "힣" for c in i["text"])][0]
    card = ring_color(img, it["box"], 10); ink = ink_color(img, it["box"], card)
    g = {"still": None, "keys": None, "plates": [{"box": pad_box(it["box"], 10), "color": card, "from": 0}],
         "texts": [{"text": TEXT[lang]["outro"], "font": "Noteworthy-Bold", "h": it["box"][3] * 0.9, "color": ink,
                    "x": it["box"][0] + it["box"][2] / 2, "y": it["box"][1] + it["box"][3] / 2, "just": "center",
                    "wmax": it["box"][2], "from": 0}]}
    build_overlay(lang, src, "outro", [g], P)
    shutil.rmtree(tmp, ignore_errors=True)


def build_overlay(lang, src, kind, groups, P):
    name = os.path.basename(src)
    od = os.path.join(ROOT, "assets", "global", lang); bd = os.path.join(od, "build"); os.makedirs(bd, exist_ok=True)
    out = os.path.join(od, unicodedata.normalize("NFC", name))
    job = {"src": src, "w": P["w"], "h": P["h"], "fps": P["fps"], "dur": P["dur"], "groups": groups,
           "save_as": os.path.join(bd, f"{kind}.aep"), "render_to": os.path.join(bd, f"{kind}_render.mov"),
           "out": os.path.join(bd, f"{kind}_log.json")}
    run_jsx("build_overlay_en", job)
    finish_video(job["render_to"], src, out)
    check_same(src, out)
    sheet(src, out, os.path.join(od, f"review_{kind}.png"))
    print("ok", out)


if __name__ == "__main__":
    lang, kind, src = sys.argv[1], sys.argv[2], sys.argv[3]
    {"emotion": emotion, "title": title, "outro": outro}[kind](lang, os.path.abspath(src))
