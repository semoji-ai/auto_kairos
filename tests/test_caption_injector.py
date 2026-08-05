"""caption 마커 → scene_specs items 결정적 주입 검증."""
from auto_agent.tools.caption_injector import inject, parse_captions


MS = """# Ch1. 시작

전원을 누르면 로고가 뜹니다.

---

G4의 카메라는 어두운 곳에서도 밝게 찍혔습니다.
<!-- caption: F1.8 조리개 / 레이저 오토포커스 -->

---

법정에서 제시된 선택은 둘이었습니다. 현금이거나, 다시 사야 받는 할인이었죠.
<!-- caption: 현금 425달러 / 새 LG폰 구매 시 700달러 할인 -->
"""


def _spec():
    return {"scenes": [
        {"sceneNumber": 1, "narration": "전원을 누르면 로고가 뜹니다.", "layout": "quote", "items": []},
        {"sceneNumber": 2, "narration": "G4의 카메라는 어두운 곳에서도 밝게 찍혔습니다.",
         "layout": "full_image", "items": []},
        {"sceneNumber": 3, "narration": "법정에서 제시된 선택은 둘이었습니다. 현금이거나, 다시 사야 받는 할인이었죠.",
         "layout": "before_after", "items": ["현금 보상", "재구매 할인"]},
    ]}


def test_parse_captions():
    caps = parse_captions(MS)
    assert len(caps) == 2
    assert caps[0][1] == ["F1.8 조리개", "레이저 오토포커스"]
    assert caps[1][1] == ["현금 425달러", "새 LG폰 구매 시 700달러 할인"]


def test_injects_into_matching_scene():
    out = inject(MS, _spec())
    assert out["scenes"][1]["items"] == ["F1.8 조리개", "레이저 오토포커스"]


def test_paraphrase_replaced_by_verbatim():
    """에이전트가 의역해 넣은 항목은 원문 수치로 교체돼야 한다."""
    out = inject(MS, _spec())
    items = out["scenes"][2]["items"]
    assert "현금 425달러" in items
    assert any("700달러" in i for i in items)
    assert "현금 보상" not in items, "의역이 남아 숫자가 유실됨"


def test_layout_promoted_for_visibility():
    """items가 안 보이는 레이아웃이면 노출 가능한 레이아웃으로 승격."""
    out = inject(MS, _spec())
    assert out["scenes"][1]["layout"] == "items_list"


def test_no_narration_pollution():
    out = inject(MS, _spec())
    for s in out["scenes"]:
        assert "F1.8" not in s["narration"]
        assert "425달러" not in s["narration"]


def test_report_counts():
    out = inject(MS, _spec())
    rep = out["_caption_injection"]
    assert rep["total"] == 4
    assert rep["injected"] == 4
    assert rep["unmatched"] == []


def test_manuscript_without_captions_is_noop():
    spec = {"scenes": [{"sceneNumber": 1, "narration": "본문", "layout": "quote", "items": ["원래"]}]}
    out = inject("# Ch1. 제목\n\n본문\n", spec)
    assert out["scenes"][0]["items"] == ["원래"]
    assert out["_caption_injection"]["total"] == 0
