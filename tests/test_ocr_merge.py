import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sg.ocr import merge_items


def it(text, x, y, w, h, conf=1.0):
    return {"text": text, "box": [x, y, w, h], "conf": conf}


def test_extra_items_append_after_base_and_skip_overlaps():
    base = [it("회원권", 0, 0, 100, 30)]
    extra = [it("회원권", 2, 1, 98, 29), it("회비", 0, 50, 60, 30), it("회비", 1, 51, 60, 29), it("ㅂㅂ", 0, 90, 30, 10), it("가격", 0, 120, 30, 10, 0.3)]
    out = merge_items(base, extra)
    assert [o["text"] for o in out] == ["회원권", "회비"]       # 기존 순서 유지 + 겹치지 않는 새 항목만, 잡음(자모·낮은 신뢰도) 제외


def test_low_conf_base_item_does_not_block_clear_reading():
    base = [it("공목0? -여?", 20, 15, 190, 60, 0.3)]
    extra = [it("자사 제품을", 30, 20, 150, 25), it("팔 수 있다니!", 30, 50, 160, 25)]
    assert [o["text"] for o in merge_items(base, extra)] == ["공목0? -여?", "자사 제품을", "팔 수 있다니!"]
