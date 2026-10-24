import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.raster_apply import split_emph, text_spec


def test_split_emph_returns_plain_text_and_ranges():
    assert split_emph("Can [[Costco]] win?") == ("Can Costco win?", [[4, 10]])
    assert split_emph("plain") == ("plain", [])


def test_text_spec_scales_to_footage_and_uses_emph_only_for_two_tone():
    st = {"angle": -10.0, "w": 400.0, "h": 40.0, "cx": 200.0, "cy": 80.0, "two_tone": False,
          "base": [250, 250, 250], "emph": [255, 0, 0]}
    t = text_spec("Go [[now]]", st, 0.25, "gothic")
    assert t["text"] == "Go now" and t["emph"] == []           # 원본이 한 색이면 강조 없음
    assert t["cx"] == 50.0 and t["cy"] == 20.0 and t["wmax"] == 100.0
    assert abs(t["size"] - 40 * 0.72 * 0.25) < 1e-6 and t["font"] == "OTSBAggroB"
    st["two_tone"] = True
    t = text_spec("Go [[now]]", st, 0.25, "hand")
    assert t["emph"] == [[3, 6]] and t["font"] == "Noteworthy-Bold"


def test_text_spec_passes_outline_scaled():
    st = {"angle": 0.0, "w": 400.0, "h": 40.0, "cx": 0.0, "cy": 0.0, "two_tone": False,
          "base": [0, 0, 0], "emph": [0, 0, 0], "stroke": [255, 255, 255], "stroke_w": 12.0}
    t = text_spec("Hi", st, 0.25, "hand")
    assert t["stroke"] == [255, 255, 255] and t["stroke_w"] == 3.0
    del st["stroke"], st["stroke_w"]
    assert text_spec("Hi", st, 0.25, "hand")["stroke"] is None


def test_check_entry_flags_key_drift_missing_emph_and_glyphs():
    from scripts.raster_apply import check_entry
    font = "/Users/jleavens_macmini/Library/Fonts/SBAggroOTF-B.otf"
    ok = check_entry("1#0", "회원", {"ko": "회원", "text": "Members"}, {}, {"two_tone": False}, font)
    assert ok == []
    assert any("키" in e for e in check_entry("1#0", "회비", {"ko": "회원", "text": "Members"}, {}, {"two_tone": False}, font))
    assert any("강조" in e for e in check_entry("1#0", "회원", {"ko": "회원", "text": "Members"}, {}, {"two_tone": True}, font))
    assert any("글리프" in e for e in check_entry("1#0", "회원", {"ko": "회원", "text": "x"}, {"text": "₩5"}, {"two_tone": False}, font))


def test_font_role_by_kind_outline_and_angle():
    from scripts.raster_apply import font_role
    assert font_role("hand", has_stroke=True, angle=0) == "brush"
    assert font_role("hand", has_stroke=False, angle=0) == "hand"
    assert font_role("gothic", has_stroke=False, angle=-10.9) == "title"
    assert font_role("gothic", has_stroke=False, angle=0.5) == "label"


def test_text_spec_uses_profile_fonts_for_role():
    zh = {"label": {"ps": "SourceHanSansCN-Heavy"}, "title": {"ps": "SmileySans-Oblique"},
          "hand": {"ps": "ZCOOLKuaiLe-Regular"}, "brush": {"ps": "ZhiMangXing-Regular"}}
    st = {"angle": 0.0, "w": 40.0, "h": 10.0, "cx": 0.0, "cy": 0.0, "two_tone": False, "base": [0, 0, 0], "emph": [0, 0, 0]}
    assert text_spec("你好", st, 1.0, "brush", zh)["font"] == "ZhiMangXing-Regular"
    assert text_spec("Hi", st, 1.0, "gothic")["font"] == "OTSBAggroB"      # 영어 기존 호출 그대로
