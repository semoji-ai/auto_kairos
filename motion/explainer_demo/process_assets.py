"""codex 생성 원본(imagegen/out) → 크로마키 제거(#00B140) → 알파 bbox 트림 → video/public/explainer_demo/img
    python3 process_assets.py [id ...]
"""
import subprocess, sys, shutil
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).parent
SRC = ROOT / "imagegen/out"
TMP = ROOT / "imagegen/keyed"
DST = ROOT.parent / "video/public/explainer_demo/img"
TMP.mkdir(parents=True, exist_ok=True)
DST.mkdir(parents=True, exist_ok=True)
KEY = Path.home() / ".codex/skills/.system/imagegen/scripts/remove_chroma_key.py"

WIDE = {"sil_far", "sil_mid", "sil_near"}  # 가로 전체 유지(패럴랙스 타일)


def key(src: Path, out: Path):
    im = Image.open(src)
    if im.mode == "RGBA" and im.getchannel("A").getextrema()[0] == 0:
        shutil.copy(src, out)  # codex 가 이미 투명 처리
        return
    subprocess.run(["python3", str(KEY), "--input", str(src), "--out", str(out), "--key-color", "#00B140",
                    "--soft-matte", "--despill", "--force"], check=True, capture_output=True)


def trim(p: Path, keep_w=False, pad=6):
    im = Image.open(p).convert("RGBA")
    a = im.getchannel("A").point(lambda v: 255 if v > 12 else 0)
    bb = a.getbbox()
    if not bb:
        return im
    x0, y0, x1, y1 = bb
    if keep_w:
        x0, x1 = 0, im.width
    return im.crop((max(0, x0 - pad), max(0, y0 - pad), min(im.width, x1 + pad), min(im.height, y1 + pad)))


def split_cols(im: Image.Image, n: int):
    """가로로 늘어선 스프라이트를 알파 열 투영으로 n 조각 분리"""
    a = im.getchannel("A")
    w, h = im.size
    colsum = [sum(1 for y in range(0, h, 2) if a.getpixel((x, y)) > 12) for x in range(w)]
    runs, cur = [], None
    for x, c in enumerate(colsum):
        if c and cur is None:
            cur = x
        if not c and cur is not None:
            runs.append((cur, x)); cur = None
    if cur is not None:
        runs.append((cur, w))
    runs = sorted(runs, key=lambda r: r[1] - r[0], reverse=True)[:n]
    runs.sort()
    return [trim_img(im.crop((r0 - 4, 0, r1 + 4, h))) for r0, r1 in runs]


def trim_img(im, pad=4):
    bb = im.getchannel("A").point(lambda v: 255 if v > 12 else 0).getbbox()
    return im.crop((bb[0] - pad, bb[1] - pad, bb[2] + pad, bb[3] + pad)) if bb else im


ids = sys.argv[1:] or [p.stem for p in sorted(SRC.glob("*.png"))]
for i in ids:
    src = SRC / f"{i}.png"
    if not src.exists():
        print("missing", i); continue
    k = TMP / f"{i}.png"
    key(src, k)
    im = trim(k, keep_w=i in WIDE)
    if i == "skull_mouths":
        for j, m in enumerate(split_cols(im, 3)):
            m.save(DST / f"skull_mouth{j}.png"); print("ok", f"skull_mouth{j}", m.size)
        continue
    im.save(DST / f"{i}.png")
    print("ok", i, im.size)
