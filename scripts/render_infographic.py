#!/usr/bin/env python3
"""조립한 인포그래픽 화면을 실제로 그린다 — 눈으로 보려고.

지금까지는 좌표를 적어 두고 끝냈다. 숫자로는 멀쩡해 보여도 그려 놓으면
요소가 겹치거나, 화면 밖으로 나가거나, 글자가 그림에 묻힌다. **보지 않으면
모른다.**

미리보기·Remotion과 같은 숫자를 쓰므로, 여기서 보이는 것이 곧 그 화면이다.

    python3 scripts/render_infographic.py EP01 --scenes 14,43
    python3 scripts/render_infographic.py EP01            # 조립된 것 전부
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auto_agent.paths import resolve_project  # noqa: E402

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1280, 720                      # 보기용 — 비율만 맞으면 된다
INK = (47, 62, 82)
ACCENT = (194, 87, 26)


def font(size: int) -> ImageFont.FreeTypeFont:
    f = Path(__file__).resolve().parent.parent / "remotion/public/fonts/BMYeonsung.ttf"
    try:
        return ImageFont.truetype(str(f), size)
    except Exception:
        return ImageFont.load_default()


def base_layer(root: Path, info: dict, scene_img: Path | None) -> Image.Image:
    """배경 — 모눈 · 씬 그림 · 흐린 씬 그림."""
    bg = info.get("background", "grid")
    if bg in ("scene", "scene_blur", "map") and scene_img and scene_img.exists():
        im = Image.open(scene_img).convert("RGB").resize((W, H))
        if bg == "scene_blur":
            im = im.filter(ImageFilter.GaussianBlur(9))
            im = Image.blend(im, Image.new("RGB", (W, H), (0, 0, 0)), 0.38)
        elif bg == "scene":
            im = Image.blend(im, Image.new("RGB", (W, H), (0, 0, 0)), 0.14)
        return im

    grid = root / "remotion/public/background/semoji_grid_bg.jpg"
    if grid.exists():
        return Image.open(grid).convert("RGB").resize((W, H))
    return Image.new("RGB", (W, H), (242, 242, 240))


def draw_text(d: ImageDraw.ImageDraw, xy, text: str, fnt, mode: str, accent: bool):
    """글자 — 대비 방식대로. box는 글자만큼만 판을 깐다."""
    x, y = xy
    box = d.textbbox((0, 0), text, font=fnt)
    tw, th = box[2] - box[0], box[3] - box[1]
    x -= tw // 2
    if mode == "box":
        pad = 6
        d.rounded_rectangle([x - pad, y - pad, x + tw + pad, y + th + pad * 2],
                            radius=6,
                            fill=(ACCENT if accent else (255, 255, 255, 230)))
        d.text((x, y), text, font=fnt, fill=(255, 255, 255) if accent else (23, 23, 26))
    elif mode == "shadow":
        for dx, dy in ((2, 2), (-1, 1), (1, -1)):
            d.text((x + dx, y + dy), text, font=fnt, fill=(0, 0, 0))
        d.text((x, y), text, font=fnt, fill=(255, 208, 138) if accent else (255, 255, 255))
    else:
        d.text((x, y), text, font=fnt, fill=ACCENT if accent else INK)


def render(root: Path, scene: dict, out: Path, scene_img: Path | None) -> bool:
    info = scene.get("infographic") or {}
    items = info.get("items") or []
    if not items:
        return False

    im = base_layer(root, info, scene_img).convert("RGBA")
    d = ImageDraw.Draw(im, "RGBA")
    mode = info.get("contrast", "plain")

    if info.get("divider") == "vertical":
        d.line([(W // 2, int(H * 0.18)), (W // 2, int(H * 0.88))],
               fill=(185, 188, 196), width=2)

    for it in items:
        p = root / "_imggen" / it["src"]
        if not p.exists():
            continue
        el = Image.open(p).convert("RGBA")
        w = max(24, int(W * float(it.get("size", 20)) / 100))
        h = max(24, int(el.height * w / el.width))
        el = el.resize((w, h))
        cx = int(W * float(it.get("left", 50)) / 100)
        cy = int(H * float(it.get("top", 50)) / 100)
        im.alpha_composite(el, (cx - w // 2, cy - h // 2))

        if it.get("label"):
            draw_text(d, (cx, cy + h // 2 + 8), it["label"], font(24), mode,
                      it.get("emphasis") == "accent")

    # 기호(+ = →)는 항을 잇는 말이다. 작고 옅으면 화면이 문장이 되지 않는다 —
    # 실제로 「=」가 어두운 인물 위 회색이라 거의 안 보였다.
    for m in info.get("marks") or []:
        mx = int(W * float(m.get("left", 50)) / 100)
        my = int(H * float(m.get("top", 50)) / 100)
        txt = str(m.get("text", ""))
        f = font(52)
        if info.get("background", "grid") != "grid":
            b = d.textbbox((0, 0), txt, font=f)
            tw, th = b[2] - b[0], b[3] - b[1]
            d.ellipse([mx - tw // 2 - 16, my - th // 2 - 14,
                       mx + tw // 2 + 16, my + th // 2 + 16],
                      fill=(23, 23, 26, 190))
            d.text((mx - tw // 2, my - th // 2), txt, font=f, fill=(255, 255, 255))
        else:
            draw_text(d, (mx, my), txt, f, "plain", False)

    if info.get("title"):
        draw_text(d, (W // 2, int(H * 0.05)), info["title"], font(34), mode, False)

    out.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(out)
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep")
    ap.add_argument("--scenes")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    # 편 라벨이든 프로젝트 slug 든 받는다 — 시리즈가 아닌 프로젝트도 돌아야 한다
    proj, ep = resolve_project(args.ep)
    specs = json.loads((proj / "scene_specs.json").read_text(encoding="utf-8"))

    sys.path.insert(0, str(root))
    from auto_agent.tools.image_assets import get_selected

    want = {int(x) for x in args.scenes.split(",")} if args.scenes else None
    out_dir = root / "_imggen" / f"{ep.lower()}_render"
    made = 0
    for s in specs["scenes"]:
        n = s.get("sceneNumber")
        if want and n not in want:
            continue
        if not (s.get("infographic") or {}).get("items"):
            continue
        sel = get_selected(proj / "images", n)
        img = (proj / "images" / sel) if sel else None
        if render(root, s, out_dir / f"s{n:03d}.png", img):
            made += 1

    print(f"{ep}  {made}장 그림 → {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
