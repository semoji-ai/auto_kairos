#!/usr/bin/env python3
"""브랜드백과사전 썸네일 — 채널 기존 판을 보고 맞춘 조립기.

`~/Downloads/썸네일_예시` 의 세 장(신세계·코스트코·삼성 비스포크)에서 읽어 낸
규칙이다. 세 장이 공통으로 지키는 것만 골랐다.

    1920x1080
    · 남색(#041328) 테두리 17px — 위·왼쪽·오른쪽·아래
    · 왼쪽 위 **채널 배지** — 남색 둥근 모서리 + 인물 선화 + 「브랜드」
    · 배경은 **실사**. 여러 장이면 세로 칸으로 나누고 가는 선으로 가른다
    · 브랜드 로고/말머리 한 줄
    · 아래 **큰 헤드라인 2줄** — 검은고딕, 노랑 또는 분홍, 검은 외곽선

헤드라인 색은 예시가 둘로 갈린다 — 코스트코·비스포크는 노랑, 신세계는 분홍.
밝은 배경엔 노랑이 안 읽히므로 **배경을 어둡게 깔고 노랑**을 기본으로 둔다.

인물 아이콘은 채널 자산이라 예시에서 떠 온다(`--icon`). 없으면 생략한다.

    python3 scripts/make_thumbnail.py -o out.png \
        --line1 "10·14·15·16" --line2 "이 숫자는 누가 정했나?"
"""
from __future__ import annotations

import argparse
from pathlib import Path

W, H = 1920, 1080
NAVY = (4, 19, 40)
FRAME = 17
YELLOW = (255, 222, 0)
PINK = (255, 45, 120)
WHITE = (255, 255, 255)

ROOT = Path(__file__).resolve().parent.parent
FONT_DIRS = [Path.home() / "Library/Fonts", Path("/Library/Fonts"),
             ROOT / "auto_agent/data/artstyle/fonts"]


def font(names, size):
    """이름 후보 중 처음 찾은 것. 없으면 기본 폰트(모양은 달라진다)."""
    from PIL import ImageFont
    for n in names:
        for d in FONT_DIRS:
            p = d / n
            if p.is_file():
                return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def headline_font(size):
    # 예시의 헤드라인은 획이 굵고 속공간이 좁다 — 검은고딕 계열이다
    return font(["BlackHanSans-Regular.ttf", "Jalnan.ttf", "BMJUA_otf.otf",
                 "NanumGothicExtraBold.ttf"], size)


def label_font(size):
    return font(["GmarketSansTTFBold.ttf", "GmarketSansBold.otf",
                 "NanumGothicExtraBold.ttf"], size)


# 검은고딕에는 가운뎃점 글리프가 없다 — `10·14` 를 그대로 쓰면 그 자리가 빈다.
# 토막으로 갈라 글자는 폰트로, 점은 원으로 그린다.
DOT = "·"


def stroked(draw, xy, text, fnt, fill, stroke, width):
    """외곽선 글자. 예시는 외곽선이 아주 두껍다 — 배경이 복잡해도 읽힌다.

    가운뎃점이 섞여 있으면 그 자리에 원을 그린다.
    """
    x, y = xy
    if DOT not in text:
        draw.text((x, y), text, font=fnt, fill=fill, stroke_width=width,
                  stroke_fill=stroke, anchor="ls")
        return
    gap = max(10, fnt.size // 6)
    r = max(5, fnt.size // 14)
    for i, part in enumerate(text.split(DOT)):
        if i:
            cx, cy = x + gap + r, y - fnt.size * 0.30
            draw.ellipse([cx - r - width, cy - r - width, cx + r + width, cy + r + width],
                         fill=stroke)
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)
            x += gap * 2 + r * 2
        if not part:
            continue
        draw.text((x, y), part, font=fnt, fill=fill, stroke_width=width,
                  stroke_fill=stroke, anchor="ls")
        x += draw.textbbox((0, 0), part, font=fnt)[2]


def line_width(draw, text, fnt):
    """가운뎃점까지 셈에 넣은 실제 폭."""
    if DOT not in text:
        return draw.textbbox((0, 0), text, font=fnt)[2]
    gap = max(10, fnt.size // 6)
    r = max(5, fnt.size // 14)
    parts = text.split(DOT)
    w = sum(draw.textbbox((0, 0), p, font=fnt)[2] for p in parts)
    return w + (len(parts) - 1) * (gap * 2 + r * 2)


def text_w(draw, text, fnt):
    return line_width(draw, text, fnt)


def fit_font(draw, text, maker, want_w, start, floor=40):
    """칸에 들어갈 때까지 크기를 줄인다 — 긴 문구가 밖으로 나가지 않게."""
    size = start
    while size > floor:
        f = maker(size)
        if text_w(draw, text, f) <= want_w:
            return f
        size -= 4
    return maker(floor)


def panels(img, photos, box, gap=6):
    """배경을 세로 칸으로 나눠 사진을 채운다 — 코스트코·비스포크가 쓰는 짜임."""
    from PIL import Image
    x0, y0, x1, y1 = box
    n = max(1, len(photos))
    w = (x1 - x0 - gap * (n - 1)) // n
    for i, p in enumerate(photos):
        im = Image.open(p).convert("RGB")
        # 칸을 채우고 넘치는 쪽을 자른다(비율 유지)
        s = max(w / im.width, (y1 - y0) / im.height)
        im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
        # **위에서 잘라 낸다.** 가운데를 기준으로 자르면 병 라벨이 아래로
        # 밀려 어둡게 깐 자리에 묻힌다 — 숫자가 이 편의 요점인데 안 보인다.
        cx = im.width // 2
        top = int((im.height - (y1 - y0)) * 0.28)
        im = im.crop((cx - w // 2, max(0, top),
                      cx - w // 2 + w, max(0, top) + (y1 - y0)))
        img.paste(im, (x0 + i * (w + gap), y0))


def cutout(path, *, tol=720, chroma=26):
    """흰 바탕 제품컷에서 물건만 떼어 낸다 — RGBA.

    칸으로 나눠 채우면 **물건이 잘린다.** 병 사진은 가로로 넉넉히 찍혀 있어
    세로 칸에 맞추려면 좌우를 크게 잘라내야 하고, 그러면 라벨이 반쪽이 된다.
    떼어 내면 잘릴 일이 없다.

    상자와 병이 서로 닿아 있어 둘로 가르지는 못한다 — 한 덩어리로 쓴다.
    """
    import numpy as np
    from PIL import Image, ImageFilter
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(int)
    m = (a.sum(2) < tol) | (a.max(2) - a.min(2) > chroma)
    ys, xs = np.where(m)
    if not len(ys):
        return im.convert("RGBA")
    al = Image.fromarray((m * 255).astype("uint8"), "L").filter(ImageFilter.GaussianBlur(1.2))
    rgba = im.convert("RGBA")
    rgba.putalpha(al)
    return rgba.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))


def products(img, photos, box, *, gap=18):
    """물건을 떼어 한 줄로 세운다 — 밑선을 맞춘다.

    비스포크 예시가 이 짜임이다. 밑선이 맞아야 넷이 「나란히 놓인」 것으로
    읽힌다 — 대본의 첫 마디가 그 말이다.
    """
    from PIL import Image, ImageFilter
    x0, y0, x1, y1 = box
    cuts = [cutout(p) for p in photos]
    n = max(1, len(cuts))
    slot = (x1 - x0 - gap * (n - 1)) / n
    # 아래 글자 자리를 비워 둔다. 예시 둘 다 **브랜드 워드마크 + 헤드라인**이
    # 왼쪽 아래를 온전히 쓴다 — 물건이 거기까지 내려오면 서로 겹친다.
    room_h = (y1 - y0) * 0.62
    base = y0 + room_h
    for i, c in enumerate(cuts):
        s = min(slot / c.width, room_h / c.height)
        cw, ch = max(1, int(c.width * s)), max(1, int(c.height * s))
        c = c.resize((cw, ch), Image.LANCZOS)
        cx = int(x0 + i * (slot + gap) + slot / 2)
        top = int(base - ch)
        # 바닥에 옅은 그림자 — 떼어 낸 물건이 붕 떠 보이지 않게
        sh = Image.new("L", (cw, max(8, ch // 8)), 0)
        from PIL import ImageDraw as _D
        _D.Draw(sh).ellipse([cw * 0.10, 0, cw * 0.90, sh.height], fill=120)
        sh = sh.filter(ImageFilter.GaussianBlur(cw / 22))
        img.paste(Image.new("RGB", sh.size, (0, 0, 0)),
                  (cx - cw // 2, int(base - sh.height * 0.45)), sh)
        img.paste(c, (cx - cw // 2, top), c)


def build(out, line1, line2, *, photos=(), icon=None, badge="브랜드",
          brand="", top_caption="", color="yellow", mode="panel") -> Path:
    from PIL import Image, ImageDraw, ImageFilter

    img = Image.new("RGB", (W, H), NAVY)
    inner = (FRAME, FRAME, W - FRAME, H - FRAME)
    if photos and mode == "product":
        # 위는 밝게, 아래는 어둡게 — 물건이 뜨고 글자가 앉는다
        import numpy as np
        g = np.linspace(0, 1, H)[:, None] ** 1.6
        top_c, bot_c = np.array([26, 34, 48]), np.array([6, 9, 16])
        bg = (top_c * (1 - g) + bot_c * g).astype("uint8")
        img.paste(Image.fromarray(np.repeat(bg[:, None, :], W, 1), "RGB"), (0, 0))
        products(img, list(photos), inner)
    elif photos and mode == "drinks":
        # **사진 칸을 위쪽으로 물린다.** 헤드라인이 아래 3분의 1을 쓰는데
        # 칸이 바닥까지 내려오면 잔의 아랫도리가 글자에 잘린다 —
        # 잔이 잘리면 그게 무슨 잔인지 안 보인다.
        img.paste(Image.new("RGB", (W, H), (10, 14, 22)), (0, 0))
        cut = int(H * 0.70)
        panels(img, list(photos), (inner[0], inner[1], inner[2], cut))
        ImageDraw.Draw(img).rectangle([inner[0], cut, inner[2], cut + 5], fill=(208, 175, 104))
    elif photos:
        panels(img, list(photos), inner)
    else:
        img.paste(Image.new("RGB", (inner[2] - inner[0], inner[3] - inner[1]), (18, 20, 26)),
                  (inner[0], inner[1]))

    # **아래를 어둡게 깐다.** 큰 글자가 사진 위에 그냥 얹히면 읽히지 않는다.
    # 예시도 아래쪽이 모두 어둡다(코스트코는 마른 나무, 비스포크는 그림자).
    if mode not in ("product", "drinks"):
        sh = Image.new("L", (W, H), 0)
        ImageDraw.Draw(sh).rectangle([0, int(H * 0.68), W, H], fill=255)
        sh = sh.filter(ImageFilter.GaussianBlur(70))
        img = Image.composite(Image.new("RGB", (W, H), (6, 8, 14)), img, sh)

    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W - 1, H - 1], outline=NAVY, width=FRAME)

    # ── 채널 배지 (왼쪽 위) ────────────────────────────────────────────
    bw, bh, r = 360, 104, 26
    d.rounded_rectangle([0, 0, bw, bh], radius=r, fill=NAVY,
                        corners=(False, False, True, False))
    if icon and Path(icon).is_file():
        ic = Image.open(icon).convert("RGB")
        ic = ic.resize((int(ic.width * 76 / ic.height), 76), Image.LANCZOS)
        img.paste(ic, (26, 14))
        tx = 26 + ic.width + 18
    else:
        tx = 34
    bf = headline_font(52)
    d.text((tx, bh // 2), badge, font=bf, fill=WHITE, anchor="lm")

    # ── 위 캡션 (비스포크가 쓰는 한 줄) ─────────────────────────────────
    if top_caption:
        cf = fit_font(d, top_caption, label_font, W - 560, 44)
        d.text((W // 2, 74), top_caption, font=cf, fill=WHITE, anchor="mm",
               stroke_width=6, stroke_fill=(0, 0, 0))

    # ── 헤드라인 2줄 + 그 위 브랜드 워드마크 ────────────────────────────
    # 워드마크 자리가 헤드라인 크기에 매여 있다 — 헤드라인을 먼저 잡는다.
    fill = YELLOW if color == "yellow" else PINK
    avail = W - 128
    # 예시의 헤드라인은 **화면 폭을 거의 다 쓴다.** 작게 잡으면 오른쪽이
    # 텅 비어 균형이 무너진다 — 들어가는 한 크게 잡고 넘칠 때만 줄인다.
    f1 = fit_font(d, line1, headline_font, avail, 176)
    f2 = fit_font(d, line2, headline_font, avail, 176) if line2 else None
    # 두 줄은 같은 크기로 — 예시가 모두 그렇다
    if f2 and f2.size != f1.size:
        s = min(f1.size, f2.size)
        f1, f2 = headline_font(s), headline_font(s)
    y1 = H - 88 - int(f1.size * 1.05) if f2 else H - 96
    if brand:
        # 코스트코는 COSTCO 로고, 비스포크는 Bespoke 워드마크가 헤드라인 바로
        # 위에 크게 놓인다. 작게 적으면 「말머리」로 보여 예시와 결이 달라진다.
        bfnt = fit_font(d, brand, label_font, W * 0.62, 78)
        stroked(d, (64, y1 - int(f1.size * 0.82)), brand, bfnt, WHITE, (0, 0, 0), 10)
    stroked(d, (64, y1), line1, f1, fill, (0, 0, 0), 14)
    if f2:
        stroked(d, (64, H - 74), line2, f2, fill, (0, 0, 0), 14)

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=95)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--line1", required=True)
    ap.add_argument("--line2", default="")
    ap.add_argument("--photo", action="append", default=[])
    ap.add_argument("--icon", default="")
    ap.add_argument("--badge", default="브랜드")
    ap.add_argument("--brand", default="")
    ap.add_argument("--top", default="")
    ap.add_argument("--color", default="yellow", choices=["yellow", "pink"])
    ap.add_argument("--mode", default="panel", choices=["panel", "product", "drinks"],
                    help="panel=세로 칸에 사진, product=흰 바탕에서 떼어 한 줄, "
                         "drinks=사진 칸을 위 70%%로 물리고 아래는 글자 자리")
    a = ap.parse_args()
    p = build(a.out, a.line1, a.line2, photos=a.photo, icon=a.icon or None,
              badge=a.badge, brand=a.brand, top_caption=a.top, color=a.color,
              mode=a.mode)
    print(f"  {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
