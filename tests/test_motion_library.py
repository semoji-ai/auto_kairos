import json
from pathlib import Path

LIB = Path(__file__).resolve().parents[1] / "data" / "artstyle" / "motion"


def test_motion_presets_schema():
    """7 프리셋 + 각 props/ease 필드."""
    d = json.loads((LIB / "motion_presets.json").read_text(encoding="utf-8"))
    presets = d["presets"]
    expected = {"type_on", "fade_scale_in", "slide_in", "pop_bounce", "mask_reveal", "tilt_2_5d", "stagger"}
    assert set(presets.keys()) == expected
    for name, p in presets.items():
        assert "props" in p or name == "stagger"   # stagger는 메타(base 계승)


def test_font_map():
    d = json.loads((LIB / "font_map.json").read_text(encoding="utf-8"))
    assert d["gothic_bold"] == "OTSBAggroB"
    assert d["serif"] == "GyeonggiBatangR" and d["rounded"] == "Cafe24Ssurround"


def test_color_tokens():
    d = json.loads((LIB / "color_tokens.json").read_text(encoding="utf-8"))
    assert d["brand_red"].upper() == "#E4002B" and d["ink"].upper() == "#333333"
