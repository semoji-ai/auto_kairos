"""뿌연(저화질) AI 영상 클립을 원본을 스토리보드 삼아 다시 그리고(codex $imagegen) 미니맥스 H3로 다시 움직여 같은 규격 사본을 만든다.
usage: redraw_clips.py <EP> draw|video|assemble [--only a.mp4,b.mp4]
입력: <EP>/assets/zh/redo/jobs.json {"<footage 이름>": {"motion": "...", "text": "...", "green": bool, "keep_package": bool}}
      쓰는 구간은 graph_nas 레이어 시각으로 계산(redo_use.json).
draw     원본 쓰는 구간 첫 프레임을 16:9로 넓혀(가장자리 늘림) codex 편집으로 깨끗하게 다시 그림 → redo/img/<이름>.png
video    다시 그린 그림 → 미니맥스 H3(쓰는 구간 길이) → redo/vid/<이름>.mp4
assemble 미니맥스 영상을 원본 크기·24fps·241프레임으로(쓰는 구간 앞은 첫 프레임 정지, 넓힌 부분 잘라냄) → assets/zh/vid/swap/<이름>,
         l10n/swap_zh.json 에 등록"""
import json, math, os, subprocess, sys, unicodedata
from concurrent.futures import ThreadPoolExecutor
import cv2
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
nfc = lambda s: unicodedata.normalize("NFC", s)
STYLE = ("Redraw image 1 as a clean, crisp, high-resolution flat 2D vector illustration in exactly the same style: keep the composition, "
         "every character, pose, facial expression, object, colour and position exactly as in image 1. Make every outline and colour edge "
         "clean and crisp, every colour area flat and even, every face simple with the same small eyes and pink cheeks. "
         "The left and right edge strips of image 1 are plain stretched background; continue the same background there.")


def src_index(ep):
    idx = {}
    for dp, _, fs in os.walk(os.path.join(ep, "src")):
        for f in fs:
            idx.setdefault(nfc(f), os.path.join(dp, f))
    return idx


def prompt(job):
    parts = [STYLE]
    if job.get("green"):
        parts.append("The background is one uniform flat pure green colour #00FF00 across the whole frame, used for chroma keying.")
    if job.get("text"):
        parts.append(job["text"] + " Each character drawn once, crisp and legible.")
    if job.get("keep_logo"):
        parts.append("The orange SAMYANG logo printed on the white face stays exactly as in image 1, copied from the logo reference in image 2: same lettering, colour, size and position.")
    if job.get("note"):
        parts.append(job["note"])
    if job.get("keep_package"):
        parts.append("The noodle package keeps its original printed design exactly as in image 1.")
    # 일괄 「단색」 지시는 원본 로고까지 지움 → 기본은 원본 로고·글자 유지, 바꿀 글자만 명시
    tit = ((job["text"] + " Every other logo and piece of lettering stays exactly as in image 1") if job.get("text") else
           "the orange SAMYANG logo exactly as in image 1 and image 2" if job.get("keep_logo") else
           "every logo and piece of lettering stays exactly as in image 1")
    return ("\n\n".join(parts) + "\n\nScene: the same moment as image 1.\n\nCamera: identical framing to image 1.\n\n"
            "Lighting: flat, shading shown only as one slightly darker colour block.\n\n"
            "Color grading: the same palette as image 1, colours kept exactly.\n\n"
            "Texture/Medium: flat 2D vector illustration with clean crisp edges and a very soft paper grain.\n\n"
            f"Text-in-image: {tit}.\n\nAR 16:9\n")


def widen(img):
    """원본을 16:9로 넓힌 캔버스(가장자리 픽셀 늘림)와 원래 영역 비율(x0,x1) 반환."""
    h, w = img.shape[:2]; W = int(round(h * 16 / 9))
    if W <= w:
        return img, (0.0, 1.0)
    l = (W - w) // 2; r = W - w - l
    out = cv2.copyMakeBorder(img, 0, 0, l, r, cv2.BORDER_REPLICATE)
    return out, (l / W, (l + w) / W)


def draw_one(ep, name, job, use):
    rd = os.path.join(ep, "assets/zh/redo"); os.makedirs(f"{rd}/img", exist_ok=True); os.makedirs(f"{rd}/work", exist_ok=True)
    base = name[:-4]; out = f"{rd}/img/{base}.png"
    if os.path.exists(out):
        return name, "exists"
    cap = cv2.VideoCapture(src_index(ep)[nfc(name)]); cap.set(1, int(round(use["cs"] * 24)) + 1); ok, fr = cap.read()
    wide, _ = widen(fr)
    ref = f"{rd}/work/{base}_ref.png"; cv2.imwrite(ref, wide)
    pf = f"{rd}/work/{base}.txt"; open(pf, "w").write(prompt(job))
    chk = subprocess.run(["node", os.path.expanduser("~/.claude/skills/image-prompt/scripts/check_prompt.mjs"), pf], capture_output=True, text=True).stdout
    if '"ok": true' not in chk:
        return name, "prompt check failed " + chk[:300]
    env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
    msg = f"/imagegen 결과 파일 이름은 {base}.png 로 이 폴더에 저장. " + open(pf).read()
    subprocess.run(["codex", "-a", "never", "--enable", "image_generation", "exec", "--json", "--skip-git-repo-check", "--ephemeral",
                    "-s", "workspace-write", "-C", f"{rd}/img", "-i", ref] + (["-i", f"{rd}/logo_samyang.png"] if job.get("keep_logo") else []) + ["-"], input=msg, text=True, capture_output=True, env=env, timeout=1500)
    return name, ("ok" if os.path.exists(out) else "missing")


def video_one(ep, name, job, use):
    sys.path.insert(0, os.path.join(ROOT, "..", "adobe"))
    from backend import video
    rd = os.path.join(ep, "assets/zh/redo"); os.makedirs(f"{rd}/vid", exist_ok=True)
    base = name[:-4]; out = f"{rd}/vid/{base}.mp4"
    if os.path.exists(out):
        return name, "exists"
    d = min(15, max(5, math.ceil(use["ce"] - use["cs"] + 0.5)))
    lock = "A locked-off shot: the frame and the background stay where they are from the first frame to the last frame. "
    if job.get("green"):
        lock += "The background stays one uniform flat pure green #00FF00 the whole time. "
    from pathlib import Path
    r = video.generate(Path(os.path.abspath(ep)), "minimax_h3", {"prompt": lock + job["motion"] + TAIL, "duration": d, "aspect_ratio": "16:9"},
                       images={"start_image": [f"assets/zh/redo/img/{base}.png"]}, timeout=2400)
    if r.get("status") != "completed":
        return name, "failed " + str(r.get("error")) + str(r.get("log_tail", ""))[-200:]
    video.download(r["urls"][0], Path(out))
    return name, "ok"


TAIL = ("\n\nFlat 2D vector illustration in exactly the attached style — smooth flat colour planes, clean crisp edges. "
        "Preserve the artwork exactly; only add the motion described above.\n\n"
        "Keep the time of day, sky colour and overall lighting exactly as in the attached frame.\n\n"
        "Keep each character's face shape, hairstyle and clothing exactly as in the attached frame. Facial expression may change if the motion calls for it.\n\n"
        "Every object keeps the exact shape, size and position it has in the attached frame unless the motion above moves it. Any lettering and logos stay exactly as drawn.\n\n"
        "Natural on-location sound only.\n\nCamera holds completely still.")


def assemble_one(ep, name, job, use):
    rd = os.path.join(ep, "assets/zh/redo"); base = name[:-4]
    src = src_index(ep)[nfc(name)]
    cap = cv2.VideoCapture(src); W, H, N = int(cap.get(3)), int(cap.get(4)), int(cap.get(7))
    _, (x0, x1) = widen(np.zeros((H, W, 3), np.uint8))
    vin = f"{rd}/vid/{base}.mp4"
    vw, vh = [int(x) for x in subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height",
                                              "-of", "csv=p=0", vin], capture_output=True, text=True).stdout.strip().split(",")]
    cx, cw = int(vw * x0), int(vw * (x1 - x0))
    lead = int(round(use["cs"] * 24))
    out = os.path.join(ep, "assets/zh/vid/swap", name); os.makedirs(os.path.dirname(out), exist_ok=True)
    vf = (f"crop={cw}:{vh}:{cx}:0,scale={W}:{H}:flags=lanczos,fps=24,"
          f"tpad=start_mode=clone:start_duration={lead / 24:.4f}:stop_mode=clone:stop_duration=15")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", vin, "-vf", vf, "-frames:v", str(N), "-an", "-c:v", "libx264", "-crf", "14",
                    "-pix_fmt", "yuv420p", "-r", "24", out], check=True)
    if job.get("green"):                          # 크로마 초록을 원본 클립의 초록으로(AE 키 설정이 원본 색에 맞춰져 있음)
        ok, f0 = cap.read() if cap.set(1, 0) else (False, None)
        g = np.median(f0[10:60, 10:60].reshape(-1, 3), axis=0).astype(np.uint8)
        c2 = cv2.VideoCapture(out); frames = []
        while True:
            ok, fr = c2.read()
            if not ok:
                break
            hsv = cv2.cvtColor(fr, cv2.COLOR_BGR2HSV)
            m = (hsv[..., 0] >= 40) & (hsv[..., 0] <= 85) & (hsv[..., 1] >= 110) & (hsv[..., 2] >= 110)
            fr[m] = g; frames.append(fr)
        tmp = out + ".g.mp4"
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", "24", "-i", "-",
                              "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
        for fr in frames:
            p.stdin.write(fr.tobytes())
        p.stdin.close(); p.wait(); os.replace(tmp, out)
    return name, "ok"


if __name__ == "__main__":
    ep, stage = sys.argv[1], sys.argv[2]
    jobs = json.load(open(os.path.join(ep, "assets/zh/redo/jobs.json")))
    uses = json.load(open(os.path.join(ep, "assets/zh/redo/redo_use.json")))
    only = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
    names = [n for n in jobs if not only or n in only]
    fn = {"draw": draw_one, "video": video_one, "assemble": assemble_one}[stage]
    with ThreadPoolExecutor(6 if stage != "assemble" else 4) as ex:
        def safe(n):                      # 한 장면 실패가 전체를 멈추지 않게(실패는 결과로 보고, 다시 돌리면 없는 것만 이어서 함)
            try:
                return fn(ep, n, jobs[n], uses[n])
            except Exception as e:
                return n, f"error {type(e).__name__}: {e}"
        for res in ex.map(safe, names):
            print(*res, flush=True)
    if stage == "assemble":
        p = os.path.join(ep, "l10n/swap_zh.json"); sw = json.load(open(p)) if os.path.exists(p) else {}
        for n in names:
            sw[n] = f"assets/zh/vid/swap/{n}"
        json.dump(sw, open(p, "w"), ensure_ascii=False, indent=1)
