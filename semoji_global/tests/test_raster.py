import numpy as np
from PIL import Image, ImageDraw
from sg.raster import quad_geom, erase_text, missing_glyphs, draw_text

SB = "/Users/jleavens_macmini/Library/Fonts/SBAggroOTF-B.otf"


def bar_with_text():
    """반투명 어두운 바(알파 200) 위 흰 글자 막대 + 검은 그림자."""
    im = Image.new("RGBA", (400, 80), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 10, 399, 70], fill=(40, 36, 37, 200))
    for x in range(60, 340, 40):
        d.rectangle([x + 3, 28, x + 23, 56], fill=(0, 0, 0, 255))      # 그림자
        d.rectangle([x, 25, x + 20, 53], fill=(250, 250, 250, 255))    # 글자 획
    return np.array(im), [[55, 22], [345, 22], [345, 58], [55, 58]]


def card_two_tone():
    im = Image.new("RGBA", (600, 300), (0, 0, 0, 0))
    card = Image.new("RGBA", (560, 120), (255, 255, 255, 255))
    d = ImageDraw.Draw(card)
    for x in range(40, 260, 30):
        d.rectangle([x, 40, x + 18, 80], fill=(5, 5, 5, 255))
    for x in range(280, 520, 30):
        d.rectangle([x, 40, x + 18, 80], fill=(245, 40, 40, 255))
    card = card.rotate(10, expand=True, resample=Image.BICUBIC)
    im.alpha_composite(card, (0, 30))
    arr = np.array(im)
    ys, xs = np.where((np.abs(arr[:, :, :3].astype(int) - [255, 255, 255]).sum(2) > 200) & (arr[:, :, 3] > 200))
    pts = np.stack([xs, ys], 1).astype(np.float32)
    import cv2
    box = cv2.boxPoints(cv2.minAreaRect(pts))
    o = box[np.argsort(box[:, 0])]                      # 왼쪽 둘 / 오른쪽 둘 → 각각 위·아래
    left = o[:2][np.argsort(o[:2, 1])]; right = o[2:][np.argsort(o[2:, 1])]
    quad = [left[0].tolist(), right[0].tolist(), right[1].tolist(), left[1].tolist()]
    return arr, quad


def test_quad_geom_angle_and_size():
    ang, w, h, cx, cy = quad_geom([[0, 10], [100, 0], [102, 20], [2, 30]])
    assert -7 < ang < -5 and 99 < w < 102 and 19 < h < 21


def test_erase_removes_text_and_shadow_on_translucent_bar():
    arr, quad = bar_with_text()
    out, colors, two = erase_text(arr, quad)
    reg = out[24:56, 60:340]
    assert np.abs(reg[:, :, :3].astype(int) - [40, 36, 37]).max() <= 25
    assert np.abs(reg[:, :, 3].astype(int) - 200).max() <= 20
    assert colors[0][0] > 230 and not two


def test_two_tone_card_keeps_edges_and_detects_black_red():
    arr, quad = card_two_tone()
    out, colors, two = erase_text(arr, quad)
    assert two
    reds = [c for c in colors if c[0] > 180 and c[1] < 100]
    darks = [c for c in colors if max(c) < 60]
    assert reds and darks
    outside = arr[:, :, 3] < 10
    assert (out[:, :, 3][outside] < 10).mean() > 0.995      # 카드 밖 투명도 그대로


def test_missing_glyphs():
    assert missing_glyphs("₩5", SB) == ["₩"]
    assert missing_glyphs("Costco 1998", SB) == []


def test_draw_text_paints_emphasis_in_second_color():
    arr = np.zeros((100, 600, 4), np.uint8); arr[:, :, 3] = 255; arr[:, :, :3] = 255
    out = draw_text(arr, [[10, 20], [590, 20], [590, 80], [10, 80]], "Stores & sales [[up every year]]",
                    [(245, 40, 40), (5, 5, 5)], True, SB)
    right = out[20:80, 320:590, :3].astype(int)
    left = out[20:80, 10:250, :3].astype(int)
    assert ((right[:, :, 0] > 180) & (right[:, :, 1] < 100)).sum() > 50       # 강조(빨강)
    assert ((left.max(2) < 60)).sum() > 50                                     # 기본(검정)


def test_mixed_colors_without_spatial_split_are_not_two_tone():
    """흰 글자 + 회색 외곽선이 섞여 있으면(위치로 갈리지 않으면) 두 색 강조가 아니다."""
    im = Image.new("RGBA", (400, 80), (30, 30, 30, 255))
    d = ImageDraw.Draw(im)
    for x in range(40, 360, 40):
        d.rectangle([x - 3, 22, x + 23, 58], fill=(150, 150, 150, 255))   # 회색 외곽
        d.rectangle([x, 25, x + 20, 55], fill=(250, 250, 250, 255))       # 흰 획
    _, colors, two = erase_text(np.array(im), [[35, 20], [385, 20], [385, 60], [35, 60]])
    assert not two


def test_text_on_transparent_background_is_cleared():
    """받침판 없이 투명 위에 그려진 글자는 투명도를 0으로 지운다."""
    im = Image.new("RGBA", (300, 80), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for x in range(40, 260, 35):
        d.rectangle([x, 25, x + 18, 55], fill=(20, 20, 20, 255))
    out, colors, two = erase_text(np.array(im), [[35, 22], [265, 22], [265, 58], [35, 58]])
    assert out[25:56, 40:260, 3].max() <= 10
    assert max(colors[0]) < 60


def test_shape_corners_survive_when_text_is_near_edges():
    """검은 띠(불투명) 끝까지 꽉 찬 노란 글자 → 지운 뒤에도 띠 모서리 투명도가 그대로."""
    im = Image.new("RGBA", (320, 100), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([10, 20, 310, 80], fill=(0, 0, 0, 255))
    for x in range(14, 300, 30):
        d.rectangle([x, 26, x + 22, 74], fill=(250, 235, 60, 255))
    arr = np.array(im)
    out, _, _ = erase_text(arr, [[12, 24], [308, 24], [308, 76], [12, 76]])
    for (y, x) in [(20, 10), (20, 310), (80, 10), (80, 310), (22, 12), (78, 308)]:
        assert out[y, x, 3] == 255, (y, x, out[y, x, 3])
    assert out[0:18, :, 3].max() == 0



def _two_lines():
    im = Image.new("RGBA", (300, 140), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for y in (20, 58):
        for x in range(40, 260, 35):
            d.rectangle([x, y, x + 18, y + 30], fill=(20, 20, 20, 255))
    return im, [[35, 17], [265, 17], [265, 53], [35, 53]], [[35, 55], [265, 55], [265, 91], [35, 91]]


def test_replace_items_keeps_first_line_intact_when_second_is_erased(tmp_path):
    from sg.raster import replace_items
    im, q1, q2 = _two_lines()
    src = tmp_path / "a.png"; im.save(src)
    replace_items(str(src), str(tmp_path / "two.png"), [{"quad": q1, "en": "FIRST"}, {"quad": q2, "en": "SECOND"}], SB)
    blank = np.zeros((140, 300, 4), np.uint8)
    one = draw_text(blank, q1, "FIRST", [(20, 20, 20)], False, SB)[10:50, :, 3] > 200   # 첫 줄만 그렸을 때
    two = np.array(Image.open(tmp_path / "two.png"))[10:50, :, 3] > 200
    assert two.sum() >= 0.9 * one.sum()
