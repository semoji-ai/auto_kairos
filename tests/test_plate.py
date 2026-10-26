import numpy as np
from PIL import Image, ImageDraw
from sg.plate import clean_plate, text_style


def gradient_bar():
    im = Image.new("RGBA", (400, 80), (0, 0, 0, 0))
    px = im.load()
    for x in range(400):
        for y in range(10, 70):
            v = 20 + x * 80 // 400                       # 가로 그라데이션 20→100
            px[x, y] = (v, v, v, 210)
    d = ImageDraw.Draw(im)
    for x in range(60, 340, 40):
        d.rectangle([x + 3, 28, x + 23, 56], fill=(0, 0, 0, 255))
        d.rectangle([x, 25, x + 20, 53], fill=(250, 250, 250, 255))
    return np.array(im), [[55, 22], [345, 22], [345, 58], [55, 58]]


def test_gradient_bar_is_filled_following_the_gradient():
    arr, q = gradient_bar()
    out = clean_plate(arr, q)
    for x in (70, 200, 330):
        expect = 20 + x * 80 // 400
        assert abs(int(out[40, x, 0]) - expect) <= 8, (x, out[40, x])
        assert abs(int(out[40, x, 3]) - 210) <= 10


def test_bubble_border_is_untouched():
    im = Image.new("RGBA", (300, 200), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([10, 10, 290, 190], fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), width=6)
    for x in range(70, 230, 30):
        d.rectangle([x, 80, x + 18, 120], fill=(10, 10, 10, 255))
    arr = np.array(im)
    out = clean_plate(arr, [[65, 76], [235, 76], [235, 124], [65, 124]])
    border = (np.abs(arr.astype(int) - out.astype(int)).sum(2) > 0)
    ring = np.zeros(arr.shape[:2], bool); ring[:, :] = False
    yy, xx = np.mgrid[:200, :300]
    r = ((xx - 150) / 140.0) ** 2 + ((yy - 100) / 90.0) ** 2
    assert not (border & (r > 0.85)).any()                          # 테두리 근처는 변화 없음
    assert (out[80:121, 70:230, :3] > 240).all()                     # 글자 자리는 흰색으로 채움


def test_floating_text_is_cleared():
    im = Image.new("RGBA", (300, 80), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for x in range(40, 260, 35):
        d.rectangle([x, 25, x + 18, 55], fill=(20, 20, 20, 255))
    out = clean_plate(np.array(im), [[35, 22], [265, 22], [265, 58], [35, 58]])
    assert out[20:60, 30:270, 3].max() == 0


def test_text_style_detects_two_tone_left_black_right_red():
    im = Image.new("RGBA", (600, 100), (255, 255, 255, 255)); d = ImageDraw.Draw(im)
    for x in range(40, 260, 30):
        d.rectangle([x, 30, x + 18, 70], fill=(5, 5, 5, 255))
    for x in range(300, 560, 30):
        d.rectangle([x, 30, x + 18, 70], fill=(245, 40, 40, 255))
    st = text_style(np.array(im), [[35, 26], [565, 26], [565, 74], [35, 74]])
    assert st["two_tone"] and max(st["base"]) < 60 and st["emph"][0] > 180 and st["emph"][1] < 100


def test_fill_samples_only_plate_interior_not_outside_background():
    """말풍선 끝에 걸친 글자: 말풍선 밖(회색 배경)을 판 색으로 쓰면 안 된다."""
    im = Image.new("RGBA", (300, 200), (0, 0, 0, 0)); d = ImageDraw.Draw(im)        # 말풍선 밖은 투명
    d.ellipse([10, 10, 250, 190], fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), width=5)
    for x in range(90, 245, 25):
        d.rectangle([x, 85, x + 15, 115], fill=(10, 10, 10, 255))
    out = clean_plate(np.array(im), [[85, 80], [262, 80], [262, 120], [85, 120]])   # OCR 영역이 말풍선 밖까지
    inside = out[90:111, 95:225, :3].astype(int)
    assert (inside.min(2) > 230).mean() > 0.97      # 말풍선 안 글자 자리는 흰색
    assert out[90:111, 95:225, 3].min() == 255       # 구멍(투명) 없음


def test_gradient_fill_has_no_vertical_streaks():
    arr, q = gradient_bar()
    d = Image.fromarray(arr); dr = ImageDraw.Draw(d)
    for x in range(60, 340, 40):                     # 실제 한글처럼 글자 끝이 OCR 영역 위아래로 삐져나옴
        dr.rectangle([x, 16, x + 20, 64], fill=(250, 250, 250, 255))    # 실제 한글처럼 OCR 영역 위아래로 17% 넘침
    arr = np.array(d)
    out = clean_plate(arr, q)
    row = out[40, 60:340, 0].astype(int)
    assert np.abs(np.diff(row)).max() <= 4          # 줄무늬 없이 부드럽게


def test_thin_black_band_stays_opaque():
    """글자 높이와 거의 같은 얇은 검정 띠 + 노란 글자 → 띠는 검정 불투명 그대로 남아야 한다."""
    im = Image.new("RGBA", (360, 100), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle([10, 25, 350, 75], fill=(0, 0, 0, 255))
    for x in range(20, 330, 32):
        d.rectangle([x, 29, x + 22, 71], fill=(250, 235, 60, 255))
    out = clean_plate(np.array(im), [[15, 28], [345, 28], [345, 72], [15, 72]])
    assert out[30:71, 20:340, 3].min() == 255
    assert out[30:71, 20:340, :3].max() < 40


def test_two_line_label_top_line_filled_with_plate_not_other_line():
    """작은 두 줄 칸: 윗줄을 채울 때 아랫줄 글자색이 섞이면 안 된다."""
    im = Image.new("RGBA", (240, 90), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 239, 89], fill=(40, 40, 40, 230))
    for x in range(40, 200, 14):
        d.rectangle([x, 8, x + 9, 24], fill=(240, 240, 240, 255))     # 윗줄 작은 글자
    for x in range(50, 190, 28):
        d.rectangle([x, 34, x + 20, 76], fill=(245, 245, 245, 255))   # 아랫줄 큰 글자
    out = clean_plate(np.array(im), [[36, 6], [204, 6], [204, 26], [36, 26]])
    assert np.abs(out[8:25, 40:200, :3].astype(int) - 40).max() <= 15


def test_alpha_gradient_bar_keeps_alpha_profile():
    # 실제 자막바: 색은 같고 투명도만 가로로 변함(가장자리 0 → 가운데 255). 채운 곳도 같은 투명도여야 함
    W = 228
    arr = np.zeros((72, W, 4), np.uint8)
    for x in range(W):
        arr[4:68, x] = (33, 29, 30, int(255 * min(1.0, min(x, W - 1 - x) / 70)))
    d = ImageDraw.Draw(im := Image.fromarray(arr))
    for x in range(50, 180, 26):
        d.rectangle([x, 20, x + 16, 52], fill=(255, 255, 255, 255))
    out = clean_plate(np.array(im), [[46, 16], [184, 16], [184, 56], [46, 56]])
    for x in (52, 80, 114, 150, 176):
        assert abs(int(out[36, x, 3]) - int(arr[36, x, 3])) <= 12, (x, out[36, x], arr[36, x])
        assert int(out[36, x, 0]) < 60


def test_box_border_and_neighbor_line_survive():
    # 흰 박스(검정 테두리) 안 영어 줄 아래에 한글 줄. 한글 줄만 지우고 영어 줄·테두리는 그대로
    im = Image.new("RGBA", (320, 120), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle([5, 5, 315, 75], fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), width=3)
    for x in range(12, 300, 14):
        d.rectangle([x, 12, x + 9, 40], fill=(0, 0, 0, 255))      # 영어 줄(유지)
    for x in range(90, 230, 20):
        d.rectangle([x, 46, x + 14, 66], fill=(0, 0, 0, 255))     # 한글 줄(지움)
    arr = np.array(im)
    out = clean_plate(arr, [[86, 45], [234, 45], [234, 67], [86, 67]])
    assert out[73, 20:300, :3].max() < 40                       # 아래 테두리
    assert (out[12:41, 12:300] == arr[12:41, 12:300]).all()     # 영어 줄
    assert out[47:66, 92:228, :3].min() > 200                   # 한글 줄 지워짐


def test_blur_text_softens_only_the_region():
    from sg.plate import blur_text
    rng = np.random.default_rng(0)
    arr = np.dstack([rng.integers(0, 255, (100, 200, 3)), np.full((100, 200), 255)]).astype(np.uint8)
    out = blur_text(arr, [[50, 40], [150, 40], [150, 60], [50, 60]])
    assert out[45:56, 60:140, :3].astype(float).std() < arr[45:56, 60:140, :3].astype(float).std() * 0.5
    assert (out[:20] == arr[:20]).all() and (out[:, :20] == arr[:, :20]).all()


def test_text_on_radial_glow_is_fully_erased():
    # 흰 원형 글로우(가운데 불투명 → 바깥 투명) 위 검정 글자가 양 끝 옅은 곳까지 걸쳐 있음
    H, W = 120, 360
    yy, xx = np.mgrid[:H, :W]
    r = np.sqrt(((xx - 180) / 170.0) ** 2 + ((yy - 60) / 30.0) ** 2)
    arr = np.zeros((H, W, 4), np.uint8)
    arr[:, :, :3] = 255
    arr[:, :, 3] = np.clip((1 - r) * 2.2, 0, 1) * 255
    im = Image.fromarray(arr); d = ImageDraw.Draw(im)
    for x in range(40, 320, 30):
        d.rectangle([x, 48, x + 14, 72], fill=(0, 0, 0, 255))
    out = clean_plate(np.array(im), [[38, 46], [326, 46], [326, 74], [38, 74]])
    dark = (out[48:73, 40:320, 3] > 128) & (out[48:73, 40:320, :3].max(2) < 100)
    assert dark.sum() == 0
    # 글로우의 세로 변화도 이어져야 함(가로 띠로 납작해지지 않게): 글자 자리 알파가 원래 글로우 알파와 비슷
    for x, y in ((55, 50), (55, 70), (190, 50), (300, 70)):
        assert abs(int(out[y, x, 3]) - int(arr[y, x, 3])) <= 25, (x, y, out[y, x], arr[y, x])


def test_outlined_text_on_transparent_becomes_transparent():
    # 받침판 없이 투명 위: 검정 글자 + 굵은 흰 외곽선(외곽선이 글자끼리 붙음)
    im = Image.new("RGBA", (300, 100), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for x in range(30, 260, 34):
        d.rectangle([x - 8, 22, x + 30, 78], fill=(255, 255, 255, 255))
        d.rectangle([x, 30, x + 22, 70], fill=(0, 0, 0, 255))
    for x in range(30, 260, 68):
        d.rectangle([x + 10, 34, x + 14, 66], fill=(0, 0, 0, 0))   # 글자 속 구멍
    out = clean_plate(np.array(im), [[22, 22], [282, 22], [282, 78], [22, 78]])
    assert out[22:79, 22:283, 3].max() < 30
    # OCR 사각형이 이미지 전체를 덮어 바깥 링이 없어도 같아야 함
    out = clean_plate(np.array(im)[18:83, 14:290], [[0, 0], [276, 0], [276, 65], [0, 65]])
    assert out[22:79, 22:283, 3].max() < 30


def test_unpremultiply_restores_straight_color():
    from sg.plate import unpremultiply
    arr = np.array([[[56, 56, 56, 56], [0, 0, 0, 0], [20, 10, 0, 128], [9, 9, 9, 255]]], np.uint8)
    out = unpremultiply(arr)
    assert tuple(out[0, 0]) == (255, 255, 255, 56)
    assert tuple(out[0, 1]) == (0, 0, 0, 0)
    assert tuple(out[0, 2][:3]) == (40, 20, 0)
    assert tuple(out[0, 3]) == (9, 9, 9, 255)


def test_text_style_outlined_text_gives_fill_and_stroke():
    # 투명 위 검은 글자 + 두꺼운 흰 외곽선 → 글자색 검정, 외곽선 흰색
    im = Image.new("RGBA", (300, 100), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for x in range(30, 260, 50):
        d.rectangle([x - 7, 18, x + 32, 82], fill=(255, 255, 255, 255))
        d.rectangle([x, 25, x + 25, 75], fill=(0, 0, 0, 255))
    st = text_style(np.array(im), [[22, 18], [283, 18], [283, 82], [22, 82]])
    assert max(st["base"]) < 60
    assert st.get("stroke") and min(st["stroke"]) > 200
    assert st["two_tone"] is False


def test_text_style_antialiased_edges_are_not_an_outline():
    from PIL import ImageFont
    # 작은 글자를 4배로 키운 것처럼(내보내기 k=4) 가장자리 중간색 띠가 넓음
    im = Image.new("RGBA", (105, 25), (30, 30, 30, 255)); d = ImageDraw.Draw(im)
    f = ImageFont.truetype("/Users/jleavens_macmini/Library/Fonts/SBAggroOTF-B.otf", 12)
    d.text((5, 6), "Costco members", font=f, fill=(250, 250, 250, 255))
    im = im.resize((420, 100), Image.BICUBIC)
    st = text_style(np.array(im), [[18, 24], [400, 24], [400, 80], [18, 80]])
    assert not st.get("stroke")
    assert min(st["base"]) > 200


def test_clean_plate_with_huge_text_keeps_memory_bounded():
    # 말풍선 속 큰 글자(높이 335px, 1200px 그림): 블러 반경이 글자 높이×5라 OpenCV가 수십 GB 버퍼를 잡던 문제(실측)
    import subprocess, sys, textwrap, os
    code = textwrap.dedent("""
        import sys, resource, numpy as np
        sys.path.insert(0, %r)
        from sg.plate import text_style
        a = np.zeros((1200, 1200, 4), np.uint8); a[..., 2] = 200; a[..., 3] = 255
        a[450:780, 200:1000, :3] = 20
        text_style(a, [[150, 430], [1050, 430], [1050, 765], [150, 765]])
        print(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    """ % os.path.join(os.path.dirname(__file__), ".."))
    p = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)
    import time
    t0 = time.time(); peak = 0
    while p.poll() is None:
        try:
            peak = max(peak, int(subprocess.run(["ps", "-o", "rss=", "-p", str(p.pid)], capture_output=True, text=True).stdout or 0))
        except ValueError:
            pass
        if peak > 2_000_000 or time.time() - t0 > 60:     # KB
            p.kill(); break
        time.sleep(0.2)
    p.wait()
    assert peak <= 2_000_000 and time.time() - t0 <= 60, f"peak RSS {peak / 1e6:.1f} GB"
