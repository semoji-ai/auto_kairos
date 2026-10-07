"""세모지 캐릭터 리그 빌더 — 기준 전신 그림(초록 배경) 1장 → 부위별 투명 PNG(같은 캔버스·같은 좌표).

  python3 build_rig.py gen  <name> <base.png>     # 1단계: codex 편집 생성(몸통·눈감음·말하기·팔 + 다리 포즈)
  python3 build_rig.py build <name>               # 2단계: 키잉·정렬 → video/public/kit/<name>/ + rig.json

교훈(walker1 파일럿):
  · 다리 포즈는 기준의 다리 부분 크롭을 ref로 줘야 비율이 유지된다(전신 ref면 다리가 길어짐)
  · 팔은 한쪽만 쓰고 좌우 반전(길이 불일치 방지)
  · 눈·입은 얼굴 패치(편집본마다 어깨폭이 달라 몸통 통째 교체 불가)
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

KIT = Path(__file__).resolve().parent
PUB = KIT.parent.parent / "video/public/kit"
RUNNER = Path.home() / "Projects/codex-fleet/runners/codex_imagegen_runner.py"
KEY = Path.home() / ".codex/skills/.system/imagegen/scripts/remove_chroma_key.py"
W, H = 1024, 1536
COMMON = (" Keep EXACTLY the same illustration style, colors, texture, canvas size, and the same position and scale of everything that remains, as in the attached image."
          " Everything removed becomes flat solid chroma green #00B140. No new objects, no shadows.")
NOLEG = "remove BOTH arms completely, including both sleeves, so the clothing ends cleanly at rounded shoulders; also remove everything below the waist (trousers or skirt, legs, shoes). Keep only the head, neck and the upper-body clothing"
LEGC = (" Keep EXACTLY the same flat illustration style, colors and texture. The waistband at the top must stay at exactly the same position and width as in the attached image, the legs keep the same length and thickness, and the shoes the same size."
        " Do NOT draw the upper-body clothing or the hands: remove any shirt/jacket hem and hands; keep only the lower-body garment, legs and shoes. Front view. Background flat solid chroma green #00B140, no ground, no shadow, nothing else.")


def key(src, dst):
    subprocess.run(["python3", str(KEY), "--input", str(src), "--out", str(dst), "--key-color", "#00B140", "--soft-matte", "--despill", "--force"], check=True, capture_output=True)


def bbox(path):
    a = np.array(Image.open(path).convert("RGBA"))[..., 3] > 128
    ys, xs = np.nonzero(a)
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def gen(name, base, extra=None):
    d = KIT / "rigs" / name
    (d / "out").mkdir(parents=True, exist_ok=True)
    b = Image.open(base).convert("RGB")
    if b.size != (W, H):
        b = b.resize((W, H), Image.LANCZOS)
    b.save(d / "base.png")
    key(d / "base.png", d / "k_base.png")
    x0, y0, x1, y1 = bbox(d / "k_base.png")
    cx = (x0 + x1) // 2
    ly0 = int(y0 + 0.56 * (y1 - y0))            # 다리 크롭: 허리 조금 위부터 600×600
    box = [cx - 300, ly0, cx + 300, ly0 + 600]
    if box[3] > H:
        box[1] -= box[3] - H; box[3] = H
    b.crop(box).resize((1024, 1024), Image.LANCZOS).save(d / "ref_legs.png")
    json.dump({"legbox": box, "bbox": [x0, y0, x1, y1]}, open(d / "meta.json", "w"))
    B, L = str(d / "base.png"), str(d / "ref_legs.png")
    items = [
        ("torso", f"Edit the attached image: {NOLEG}.", B),
        ("torso_blink", f"Edit the attached image: {NOLEG}, and change ONLY the eyes: both eyes closed, drawn as short downward-curved black lines.", B),
        ("torso_talk", f"Edit the attached image: {NOLEG}, and change ONLY the mouth: open mouth talking, a small rounded dark red open mouth.", B),
        ("arm_r", "Edit the attached image: keep ONLY the character's arm on the LEFT side of the image (the character's right arm), including its sleeve from the shoulder down to the hand, as a complete separate arm piece with the sleeve top rounded. Remove everything else.", B),
        ("legs_step", "The attached image shows a character's lower body. Redraw it in a front-view walking step pose: the leg on the LEFT side of the image steps forward toward the viewer, knee slightly bent, its shoe placed a little lower and turned slightly outward; the leg on the RIGHT side of the image is behind, straight, with the heel lifted so only the toe touches.", L),
        ("legs_pass", "The attached image shows a character's lower body. Redraw it in a front-view walking passing pose: the leg on the RIGHT side of the image is lifted with the knee bent forward so its shoe is raised off the ground by about one shoe height; the leg on the LEFT side of the image stands straight with its shoe flat on the ground.", L),
        ("legs_clean", "The attached image shows a character's lower body standing. Keep the same standing pose exactly.", L),
    ] + (extra or [])
    with open(d / "prompts.jsonl", "w") as f:
        for i, p, ref in items:
            suffix = LEGC if ref == L else COMMON
            ar, size = ("1:1", "1024x1024") if ref == L else ("2:3", "1024x1536")
            f.write(json.dumps({"id": i, "ar": ar, "size": size, "prompt": p + suffix, "output_path": i + ".png", "ref_images": [ref]}) + "\n")
    r = subprocess.run(["python3", str(RUNNER)], cwd=d, capture_output=True, text=True)
    print(name, (r.stdout + r.stderr).strip().splitlines()[-1])


# ── 추가 포즈 템플릿 ─────────────────────────────────────────────
ARM = ("Edit the attached image: keep ONLY the character's arm on the LEFT side of the image (the character's right arm), including its sleeve and hand, "
       "and redraw that arm in this pose: {pose}. The top of the sleeve (shoulder joint) must stay at exactly the same place and size as in the original. Remove everything else, including the rest of the body.")
ARMS2 = ("Edit the attached image: keep ONLY both of the character's arms (with sleeves and hands) and redraw them in this pose: {pose}. "
         "The shoulders stay at exactly the same place. Remove everything else, including the head, torso and legs.")
FACE = "Edit the attached image: " + NOLEG + ", and change ONLY the face: {pose}."
POSES = {
    "arm_raise_fist": (ARM, "arm raised straight up above the head with a clenched fist (cheering / fighting-spirit pose)"),
    "arm_guard_fist": (ARM, "elbow bent, forearm up in front of the chest with a clenched fist, like a boxer's guard"),
    "arm_palm_stop": (ARM, "arm stretched out to the side at shoulder height with the open palm facing the viewer, fingers up (a STOP gesture)"),
    "arm_hold": (ARM, "elbow bent, forearm pointing forward and slightly outward at waist height, hand closed in a loose fist as if gripping a handle (the hand holds nothing)"),
    "arm_reach": (ARM, "arm stretched straight out to the side at shoulder height, hand open with the index finger extended, reaching"),
    "arm_point": (ARM, "arm stretched out to the side and slightly up, pointing with the index finger"),
    "arm_out_side": (ARM, "arm raised diagonally outward and up, open palm facing up, a presenting / welcoming gesture"),
    "arm_hand_chest": (ARM, "elbow bent, open hand placed flat on the middle of the chest"),
    "arm_hand_chin": (ARM, "elbow bent, hand raised to the chin with the index finger touching the chin, thinking pose"),
    "arm_up_hang": (ARM, "arm raised straight up, slightly inward, hand closed as if hanging from a rope above the head"),
    "arms_folded": (ARMS2, "both arms folded across the chest, forearms crossed horizontally in front of the torso"),
    "face_angry": (FACE, "angry: eyebrows angled sharply down toward the center, mouth a short straight line"),
    "face_grit": (FACE, "gritting teeth: eyebrows angled down, mouth a wide flat shape showing white clenched teeth"),
    "face_frown": (FACE, "disappointed: eyebrows slanted up in the middle, mouth an upside-down curve"),
    "face_smile": (FACE, "big happy smile: eyes closed as upward curved arcs (^^), open smiling mouth"),
    "face_wide": (FACE, "surprised: eyes wide open as round white circles with small black pupils, small round open mouth"),
    "face_squint": (FACE, "in pain / effort: eyes squeezed shut drawn as > and < shapes, eyebrows slanted worried, mouth gritting teeth"),
    "face_worried": (FACE, "worried: eyebrows slanted up in the middle, small wavy mouth"),
    "face_sparkle": (FACE, "delighted: big sparkling eyes with white star highlights, open smiling mouth"),
    "legs_sit": ("The attached image shows a character's lower body. Redraw it in a SITTING pose seen from the front: thighs pointing toward the viewer and foreshortened, knees bent, lower legs hanging straight down, feet flat. The waistband stays at the top.", None),
    "legs_dangle": ("The attached image shows a character's lower body. Redraw it hanging in the air: both legs straight down and relaxed, toes pointing down, feet slightly apart.", None),
}


def extras(name, ids):
    """추가 포즈 생성: 팔(기준 ref) · 얼굴(기준 ref) · 다리(다리 크롭 ref)"""
    d = KIT / "rigs" / name
    B, L = str(d / "base.png"), str(d / "ref_legs.png")
    tmp = d / "extra_job"; tmp.mkdir(exist_ok=True)
    with open(tmp / "prompts.jsonl", "w") as f:
        for i in ids:
            tpl, pose = POSES[i]
            if i.startswith("legs"):
                p, ref, ar, size = tpl + LEGC, L, "1:1", "1024x1024"
            else:
                p, ref, ar, size = tpl.format(pose=pose) + COMMON, B, "2:3", "1024x1536"
            (d / "out" / (i + ".png")).unlink(missing_ok=True)
            f.write(json.dumps({"id": i, "ar": ar, "size": size, "prompt": p, "output_path": str(d / "out" / (i + ".png")), "ref_images": [ref]}) + "\n")
    r = subprocess.run(["python3", str(RUNNER)], cwd=tmp, capture_output=True, text=True)
    print(name, (r.stdout + r.stderr).strip().splitlines()[-1])


def canvas():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def mirror(im, cx):
    m = im.transpose(Image.FLIP_LEFT_RIGHT)
    c = canvas()
    dx = 2 * cx - W
    c.alpha_composite(m.crop((max(0, -dx), 0, W, H)), (max(0, dx), 0))
    return c


def patch(src, box, out):
    im = Image.open(src).convert("RGBA")
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).ellipse(box, fill=255)
    m = m.filter(ImageFilter.GaussianBlur(6))
    a = np.array(im)
    a[..., 3] = np.minimum(a[..., 3], np.array(m))
    Image.fromarray(a, "RGBA").save(out)


def face_boxes(base_k):
    """눈·입 패치 영역: 머리 bbox 비율로 잡는다(세모지 비율: 눈 ≈ 머리 높이 50%, 입 ≈ 72%)"""
    a = np.array(Image.open(base_k).convert("RGBA"))
    al = a[..., 3] > 128
    ys, xs = np.nonzero(al)
    top = ys.min()
    # 머리 = 위에서부터 폭이 급격히 넓어지기 전(목)까지 — 간단히 전체 키의 22%
    hh = int((ys.max() - top) * 0.22)
    row = np.nonzero(al[top + hh // 2])[0]
    hx0, hx1 = row.min(), row.max()
    hw = hx1 - hx0
    eye = (hx0 + hw * 0.12, top + hh * 0.42, hx1 - hw * 0.12, top + hh * 0.66)
    mouth = (hx0 + hw * 0.3, top + hh * 0.68, hx1 - hw * 0.3, top + hh * 0.9)
    return eye, mouth


def diff_box(a_path, b_path, y0, y1):
    """몸통 ↔ 표정 편집본의 차이가 큰 곳(머리 영역 안)을 감싸는 타원 상자"""
    a = np.array(Image.open(a_path).convert("RGB")).astype(int)
    b = np.array(Image.open(b_path).convert("RGB")).astype(int)
    dm = np.abs(a - b).sum(-1) > 90
    lim = int(y0 + (y1 - y0) * 0.24)
    dm[lim:] = False
    dm = np.array(Image.fromarray((dm * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(9))) > 0
    # 차이가 가장 몰린 가로 띠(±38px)만 — 편집본이 얼굴 전체를 조금씩 바꿔도 눈/입만 잡는다
    rows = dm.sum(1)
    pk = int(np.argmax(np.convolve(rows, np.ones(31), "same")))
    band = np.zeros_like(dm); band[max(0, pk - 38):pk + 38] = True
    dm &= band
    ys, xs = np.nonzero(dm)
    if len(ys) < 20:
        raise SystemExit("표정 차이 영역을 못 찾음: " + str(b_path))
    # 가장 큰 덩어리 주변으로 약간 여유
    x0, x1, yy0, yy1 = np.percentile(xs, 2), np.percentile(xs, 98), np.percentile(ys, 2), np.percentile(ys, 98)
    return (x0 - 18, yy0 - 14, x1 + 18, yy1 + 14)


def build(name):
    d = KIT / "rigs" / name
    meta = json.load(open(d / "meta.json"))
    for f in sorted((d / "out").glob("*.png")):
        key(f, d / f"k_{f.stem}.png")
    o = PUB / name
    o.mkdir(parents=True, exist_ok=True)
    x0, y0, x1, y1 = meta["bbox"]
    cx = (x0 + x1) // 2
    lb = meta["legbox"]
    # 몸통
    Image.open(d / "k_torso.png").convert("RGBA").save(o / "torso.png")
    tb = bbox(d / "k_torso.png")
    # 팔: 한쪽 + 반전
    arm = Image.open(d / "k_arm_r.png").convert("RGBA")
    arm.save(o / "arm_r.png")
    mirror(arm, cx).save(o / "arm_l.png")
    ab = bbox(d / "k_arm_r.png")
    # 다리: 크롭 좌표로 되돌려 놓기
    def legs(stem):
        im = Image.open(d / f"k_{stem}.png").convert("RGBA").resize((lb[2] - lb[0], lb[3] - lb[1]), Image.LANCZOS)
        c = canvas()
        c.alpha_composite(im, (lb[0], lb[1]))
        return c
    legs("legs_clean").save(o / "legs_stand.png")
    st = legs("legs_step"); st.save(o / "legs_step_l.png"); mirror(st, cx).save(o / "legs_step_r.png")
    ps = legs("legs_pass"); ps.save(o / "legs_pass_r.png"); mirror(ps, cx).save(o / "legs_pass_l.png")
    patch(d / "k_torso_blink.png", diff_box(d / "k_torso.png", d / "k_torso_blink.png", y0, y1), o / "eyes_closed.png")
    patch(d / "k_torso_talk.png", diff_box(d / "k_torso.png", d / "k_torso_talk.png", y0, y1), o / "mouth_open.png")
    # 추가 포즈: 팔 한쪽 → _r + 반전 _l / 양팔 그대로 / 얼굴 → 차이 패치 / 다리 → 크롭 좌표 복원
    extra = []
    for f in sorted((d / "out").glob("*.png")):
        st = f.stem
        if st in {"torso", "torso_blink", "torso_talk", "arm_r", "legs_step", "legs_pass", "legs_clean"}:
            continue
        k = d / f"k_{st}.png"
        if st.startswith("arm_"):
            im = Image.open(k).convert("RGBA"); im.save(o / f"{st}_r.png"); mirror(im, cx).save(o / f"{st}_l.png")
        elif st.startswith("face_"):
            patch(k, diff_box(d / "k_torso.png", k, y0, y1), o / f"{st}.png")
        elif st.startswith("legs_"):
            legs(st).save(o / f"{st}.png")
        else:
            Image.open(k).convert("RGBA").save(o / f"{st}.png")
        extra.append(st)
    spec = {"dir": f"kit/{name}", "w": W, "h": H, "feet": [cx, y1], "top": y0,
            "shoulderR": [int((ab[0] + ab[2]) / 2) + 10, ab[1] + 28], "shoulderL": [int(2 * cx - (ab[0] + ab[2]) / 2) - 10, ab[1] + 28],
            "torsoBottom": tb[3], "extras": extra}
    json.dump(spec, open(o / "rig.json", "w"), indent=1)
    # 확인용 시트
    sets = [["legs_stand", "arm_r", "arm_l", "torso"], ["legs_step_l", "arm_r", "arm_l", "torso"], ["legs_pass_r", "arm_r", "arm_l", "torso"],
            ["legs_step_r", "arm_r", "arm_l", "torso"], ["legs_stand", "arm_r", "arm_l", "torso", "eyes_closed"], ["legs_stand", "arm_r", "arm_l", "torso", "mouth_open"]]
    tiles = [Image.open(d / "k_base.png").convert("RGBA")]
    for s in sets:
        c = canvas()
        for l in s:
            c.alpha_composite(Image.open(o / f"{l}.png").convert("RGBA"))
        tiles.append(c)
    sheet = Image.new("RGB", (256 * len(tiles), 384), (200, 210, 200))
    for i, t in enumerate(tiles):
        bg = Image.new("RGBA", (W, H), (200, 210, 200, 255)); bg.alpha_composite(t)
        sheet.paste(bg.convert("RGB").resize((256, 384)), (i * 256, 0))
    sheet.save(d / "sheet.png")
    print(name, "ok", spec)


def regen_legs(name):
    """몸통 아래끝 - 40px 부터 발까지 정사각 크롭으로 다리 포즈 재생성(치마 등 허리선이 높은 경우)"""
    d = KIT / "rigs" / name
    meta = json.load(open(d / "meta.json"))
    x0, y0, x1, y1 = meta["bbox"]
    cx = (x0 + x1) // 2
    tb = bbox(d / "k_torso.png")
    top = tb[3] - 40
    side = max(600, y1 + 20 - top)
    box = [cx - side // 2, top, cx + side // 2, top + side]
    Image.open(d / "base.png").convert("RGB").crop(box).resize((1024, 1024), Image.LANCZOS).save(d / "ref_legs.png")
    meta["legbox"] = box
    json.dump(meta, open(d / "meta.json", "w"))
    lines = [json.loads(l) for l in open(d / "prompts.jsonl")]
    lines = [l for l in lines if l["id"].startswith("legs")]
    tmp = d / "legs_job"; tmp.mkdir(exist_ok=True)
    with open(tmp / "prompts.jsonl", "w") as f:
        for l in lines:
            l["output_path"] = str(d / "out" / (l["id"] + ".png"))
            f.write(json.dumps(l) + "\n")
    r = subprocess.run(["python3", str(RUNNER)], cwd=tmp, capture_output=True, text=True)
    print(name, (r.stdout + r.stderr).strip().splitlines()[-1])


if __name__ == "__main__":
    cmd, name = sys.argv[1], sys.argv[2]
    if cmd == "gen":
        gen(name, sys.argv[3])
    elif cmd == "redo":        # 지정 id 만 다시 생성: redo <name> torso,arm_r
        d = KIT / "rigs" / name
        ids = sys.argv[3].split(",")
        tmp = d / "redo_job"; tmp.mkdir(exist_ok=True)
        for f in tmp.glob("*"):
            f.unlink() if f.is_file() else None
        with open(tmp / "prompts.jsonl", "w") as f:
            for l in open(d / "prompts.jsonl"):
                j = json.loads(l)
                if j["id"] in ids:
                    (d / "out" / (j["id"] + ".png")).unlink(missing_ok=True)
                    j["output_path"] = str(d / "out" / (j["id"] + ".png"))
                    f.write(json.dumps(j) + "\n")
        r = subprocess.run(["python3", str(RUNNER)], cwd=tmp, capture_output=True, text=True)
        print(name, (r.stdout + r.stderr).strip().splitlines()[-1])
    elif cmd == "extras":      # extras <name> arm_raise_fist,face_angry,...
        extras(name, sys.argv[3].split(","))
    elif cmd == "legs":
        regen_legs(name)
    else:
        build(name)
