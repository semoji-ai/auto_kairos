import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "enforce_real_first", Path(__file__).resolve().parents[1] / "scripts" / "enforce_real_first.py")
erf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(erf)

LEDGER = {"scenes": [{"n": 1, "found": True, "image_url": "https://x/a.jpg", "license": "cc0",
                      "desc": "1959년 A-501 라디오", "relevance": "씬이 말하는 그 라디오"}]}


def test_found_asset_flips_generate_back_to_search():
    scenes = [{"sceneNumber": 1, "imageAsset": {"source": "generate", "prompt": "라디오"}}]
    stat = erf.apply_ledger(scenes, LEDGER)
    assert scenes[0]["imageAsset"]["source"] == "search"
    assert stat["flipped_back"] == 1


def test_documented_generate_choice_is_kept_and_asset_becomes_reference():
    scenes = [{"sceneNumber": 1, "imageAsset": {
        "source": "generate", "prompt": "라디오", "keepGenerateReason": "실물 사진 화질이 낮아 전체화면에 못 쓴다"}}]
    stat = erf.apply_ledger(scenes, LEDGER)
    ia = scenes[0]["imageAsset"]
    assert ia["source"] == "generate"
    assert ia["refAssets"][0]["url"] == "https://x/a.jpg"
    assert stat["kept_generate"] == 1


def test_relevance_wrong_is_not_promoted():
    scenes = [{"sceneNumber": 1, "imageAsset": {"source": "generate", "prompt": "라디오"}}]
    stat = erf.apply_ledger(scenes, LEDGER, verdicts={1: {"verdict": "wrong", "why": "다른 모델", "instead": "A-501"}})
    ia = scenes[0]["imageAsset"]
    assert ia["source"] == "generate" and "url" not in ia
    assert "관련성 wrong" in ia["assetNote"]
    assert stat["relevance_rejected"] == 1
