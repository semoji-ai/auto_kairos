"""영상 footage에 박힌 글자(간판 등)를 언어별로 바꾼 사본 만들기.  usage: patch_video_text.py <EP> <lang>
입력 l10n/video_text_<lang>.json:
  {"<footage 이름>": {"src": "src/…/x.mp4", "out": "assets/<lang>/vid/swap/x.mp4",
     "items": [{"box": [x,y,w,h], "t": 기준 초, "text": "新文字"|"", "pad": 8, "track": true}]}}
- 기준 프레임의 box(+pad)를 템플릿으로 매 프레임 위치를 찾아(±search px) 따라가며
  그 칸을 바탕색(테두리 중앙값)으로 덮고 새 글자를 원래 글자색으로 쓴다. text가 ""면 흐림만.
- 크기·길이·프레임 수는 원본과 같게(swap_assets가 검사) — 소리는 그대로 복사.
결과 사본은 l10n/swap_<lang>.json(편 전용 대체 표)에 이름 → out 으로 등록한다."""
import json, os, subprocess, sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT = os.path.expanduser("~/Library/Fonts/SourceHanSansCN-Heavy.otf")


def probe(p):
    d = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height,r_frame_rate,nb_frames", "-of", "json", p],
                                  capture_output=True, text=True).stdout)["streams"][0]
    n, m = d["r_frame_rate"].split("/")
    return d["width"], d["height"], d["r_frame_rate"], float(n) / float(m)


def colours(crop):
    """바탕색 = 칸 테두리 중앙값, 글자색 = 바탕에서 가장 먼 색들의 중앙값."""
    border = np.concatenate([crop[:3].reshape(-1, 3), crop[-3:].reshape(-1, 3), crop[:, :3].reshape(-1, 3), crop[:, -3:].reshape(-1, 3)])
    bg = np.median(border, axis=0)
    px = crop.reshape(-1, 3).astype(float)
    d = np.linalg.norm(px - bg, axis=1)
    fg = np.median(px[d >= np.percentile(d, 90)], axis=0)
    return tuple(int(v) for v in bg), tuple(int(v) for v in fg)


def draw(frame, box, bg, fg, text):
    x, y, w, h = box
    H, W = frame.shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return frame
    if not text:
        frame[y0:y1, x0:x1] = cv2.GaussianBlur(frame[y0:y1, x0:x1], (0, 0), max(4, h / 4))
        return frame
    frame[y0:y1, x0:x1] = bg[::-1]                       # BGR
    im = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)); d = ImageDraw.Draw(im)
    size = int(h * 0.72)
    f = ImageFont.truetype(FONT, size)
    while d.textlength(text, font=f) > w * 0.92 and size > 8:
        size -= 2; f = ImageFont.truetype(FONT, size)
    d.text((x + w / 2, y + h / 2), text, font=f, fill=fg, anchor="mm")
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)


def ocr_boxes(frames, root):
    """mode "ocr": 매 프레임 판독해 한글 칸 목록 [[x,y,w,h]…] (움직이는·기우는 글자용)."""
    import re, tempfile
    H = re.compile("[가-힣]")
    d = tempfile.mkdtemp(); fs = []
    for i, fr in enumerate(frames):
        f = os.path.join(d, f"{i:05d}.png"); cv2.imwrite(f, fr); fs.append(f)
    out = {}
    for k in range(0, len(fs), 60):
        res = subprocess.run([os.path.join(root, "tools/ocr")] + fs[k:k + 60], capture_output=True, text=True).stdout
        for line in res.splitlines():
            r = json.loads(line); i = int(os.path.basename(r["file"])[:5])
            out[i] = [[int(v) for v in it["box"]] for it in r["items"] if H.search(it["text"]) and it["conf"] >= 0.3]
    return [out.get(i, []) for i in range(len(frames))]


def run(ep, job):
    src, out = os.path.join(ep, job["src"]), os.path.join(ep, job["out"])
    W, H, rate, fps = probe(src)
    cap = cv2.VideoCapture(src); frames = []
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        frames.append(fr)
    items = []
    for it in job["items"]:
        pad = it.get("pad", 8); x, y, w, h = it["box"]
        box = [x - pad, y - pad, w + 2 * pad, h + 2 * pad]
        ref = frames[min(len(frames) - 1, int(round(it.get("t", 0) * fps)))]
        tpl = ref[max(0, box[1]):box[1] + box[3], max(0, box[0]):box[0] + box[2]]
        bg, fg = colours(cv2.cvtColor(tpl, cv2.COLOR_BGR2RGB))
        items.append((box, tpl, bg, fg, it.get("text", ""), it.get("track", True), it.get("search", 90)))
    per = None
    if job.get("mode") == "ocr":
        per = ocr_boxes(frames, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    last = {}
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out + ".video.mp4"
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", rate, "-i", "-",
                          "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    for fi, fr in enumerate(frames):
        for k, (box, tpl, bg, fg, text, track, search) in enumerate(items):
            b = list(box)
            if per is not None:                            # 판독한 한글 칸 중 이 항목 기준 칸에 가장 가까운 것(없으면 직전 프레임 칸, 6프레임까지)
                cands = per[fi]
                if cands:
                    c = min(cands, key=lambda c: (c[0] + c[2] / 2 - box[0] - box[2] / 2) ** 2 + (c[1] + c[3] / 2 - box[1] - box[3] / 2) ** 2)
                    pad = (box[3] - c[3]) // 2 if box[3] > c[3] else 4
                    last[k] = ([c[0] - 4, c[1] - 4, c[2] + 8, c[3] + 8], fi)
                if k in last and fi - last[k][1] <= 6:
                    fr = draw(fr, last[k][0], bg, fg, text)
                continue
            if track:
                x0, y0 = max(0, b[0] - search), max(0, b[1] - search)
                win = fr[y0:min(H, b[1] + b[3] + search), x0:min(W, b[0] + b[2] + search)]
                if win.shape[0] >= tpl.shape[0] and win.shape[1] >= tpl.shape[1]:
                    r = cv2.matchTemplate(win, tpl, cv2.TM_CCOEFF_NORMED); _, sc, _, loc = cv2.minMaxLoc(r)
                    if sc > 0.4:
                        b[0], b[1] = x0 + loc[0], y0 + loc[1]
                    else:
                        continue                           # 놓쳤으면(글자가 기울거나 가려짐) 엉뚱한 자리에 칠하지 않음
            fr = draw(fr, b, bg, fg, text)
        p.stdin.write(fr.tobytes())
    p.stdin.close(); p.wait()
    has_audio = "audio" in subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", src],
                                          capture_output=True, text=True).stdout
    args = ["ffmpeg", "-v", "error", "-y", "-i", tmp] + (["-i", src, "-map", "0:v", "-map", "1:a", "-c:a", "copy"] if has_audio else []) + ["-c:v", "copy", out]
    subprocess.run(args, check=True); os.remove(tmp)
    return out, len(frames)


if __name__ == "__main__":
    ep, lang = sys.argv[1], sys.argv[2]
    jobs = json.load(open(os.path.join(ep, "l10n", f"video_text_{lang}.json")))
    sw_p = os.path.join(ep, "l10n", f"swap_{lang}.json")
    sw = json.load(open(sw_p)) if os.path.exists(sw_p) else {}
    for name, job in jobs.items():
        if name.startswith("_"):
            continue
        out, n = run(ep, job)
        sw[name] = job["out"]
        print(name, "->", out, n, "frames", flush=True)
    json.dump(sw, open(sw_p, "w"), ensure_ascii=False, indent=1)
