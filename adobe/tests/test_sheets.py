from pathlib import Path
from backend import sheets


def test_looks_from_visual_joins_fields():
    looks = sheets._looks_from_visual({"hair": "갈색 단발", "outfit": "노란 셔츠", "appearance": "둥근 얼굴"})
    assert "갈색 단발" in looks and "노란 셔츠" in looks
    assert sheets._looks_from_visual({}) == "원본 그대로"


def test_character_prompt_keeps_layout_and_name():
    p = sheets.build_character_sheet_prompt("하루", {"hair": "검은 머리", "expressions": ["미소", "놀람"]}, "references/characters/char-1.png")
    assert "하루" in p
    assert "헤어" in p                       # 바꾸는 것: 헤어·의상
    assert "눈" in p                         # 유지: 세모지 눈 스타일(애니메 금지)
    assert "등신" in p                        # 유지: ~4등신 비율 잠금
    assert "미소" in p                        # 표정 칸 정서


def test_location_prompt_six_panels_no_person():
    p = sheets.build_location_sheet_prompt("거실", {"space": "아파트 거실", "mood": "따뜻함", "lighting": "오후"}, "references/locations/loc-1.png")
    assert "6패널" in p or "6" in p
    assert "인물" in p  # 인물 금지 문구
    assert "거실" in p


def test_prop_prompt_four_views_no_person():
    p = sheets.build_prop_sheet_prompt("포스트잇", {"form": "사각 메모지", "material": "종이", "color": "노랑"}, "references/props/prop-1.png")
    assert "4" in p
    assert "인물" in p
    assert "포스트잇" in p


def test_base_sheet_returns_none_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(sheets, "_BASE_SHEET", tmp_path / "nope.png")
    assert sheets.base_sheet() is None
    (tmp_path / "yes.png").write_bytes(b"x")
    monkeypatch.setattr(sheets, "_BASE_SHEET", tmp_path / "yes.png")
    assert sheets.base_sheet() == tmp_path / "yes.png"

import json
from backend import imagegen


def _fake_codex(monkeypatch, fail_ids=()):
    calls = []

    def fake(proj_dir, out, prompt, *, images=None, retries=2, on_line=None, post=None, **k):
        calls.append({"out": str(out), "prompt": prompt, "images": images})
        if any(fid in str(out) for fid in fail_ids):
            return {"status": "failed", "error": "no_file"}
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_bytes(b"\x89PNG\r\n\x1a\n")
        return {"status": "completed", "path": str(out)}

    monkeypatch.setattr(imagegen, "_run_codex_image", fake)
    return calls


def _entities_doc():
    return {"entities": [
        {"id": "char-1", "type": "character", "name": "하루", "visual": {"hair": "검은 머리"}, "scenes": [1, 2]},
        {"id": "loc-1", "type": "location", "name": "거실", "visual": {"space": "거실"}, "scenes": [1]},
        {"id": "prop-1", "type": "prop", "name": "포스트잇", "visual": {"color": "노랑"}, "scenes": [1, 3]},
        {"id": "prop-2", "type": "prop", "name": "컵", "visual": {}, "scenes": [2]},
    ]}


def test_generate_all_sheets_happy(tmp_path, monkeypatch):
    (tmp_path / "entities.json").write_text(json.dumps(_entities_doc(), ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(sheets, "base_sheet", lambda: tmp_path / "bs.png")
    (tmp_path / "bs.png").write_bytes(b"x")
    _fake_codex(monkeypatch)
    r = sheets.generate_all_sheets(tmp_path)
    assert r["sheets"] == {"character": 1, "location": 1, "prop": 1}
    assert r["skipped"] == []
    doc = json.loads((tmp_path / "entities.json").read_text(encoding="utf-8"))
    by_id = {e["id"]: e for e in doc["entities"]}
    assert by_id["char-1"]["sheet"] == "references/characters/char-1.png"
    assert by_id["loc-1"]["sheet"] == "references/locations/loc-1.png"
    assert by_id["prop-1"]["sheet"] == "references/props/prop-1.png"
    assert "sheet" not in by_id["prop-2"]   # 1씬 소품 미생성
    assert (tmp_path / "references/characters/char-1.png").exists()


def test_prop_single_scene_filtered(tmp_path, monkeypatch):
    (tmp_path / "entities.json").write_text(json.dumps(_entities_doc(), ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(sheets, "base_sheet", lambda: tmp_path / "bs.png")
    (tmp_path / "bs.png").write_bytes(b"x")
    calls = _fake_codex(monkeypatch)
    sheets.generate_all_sheets(tmp_path)
    assert not any("prop-2" in c["out"] for c in calls)   # 컵(1씬) codex 미호출


def test_character_without_base_sheet_skipped(tmp_path, monkeypatch):
    (tmp_path / "entities.json").write_text(json.dumps(_entities_doc(), ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(sheets, "base_sheet", lambda: None)
    _fake_codex(monkeypatch)
    r = sheets.generate_all_sheets(tmp_path)
    assert r["sheets"]["character"] == 0
    assert any(s["id"] == "char-1" for s in r["skipped"])
    assert r["sheets"]["location"] == 1   # 나머지 진행


def test_codex_failure_isolated(tmp_path, monkeypatch):
    (tmp_path / "entities.json").write_text(json.dumps(_entities_doc(), ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(sheets, "base_sheet", lambda: tmp_path / "bs.png")
    (tmp_path / "bs.png").write_bytes(b"x")
    _fake_codex(monkeypatch, fail_ids=("loc-1",))
    r = sheets.generate_all_sheets(tmp_path)
    assert r["sheets"]["location"] == 0
    assert any(s["id"] == "loc-1" for s in r["skipped"])
    assert r["sheets"]["character"] == 1


def test_no_entities_errors(tmp_path):
    assert sheets.generate_all_sheets(tmp_path).get("error")


def test_build_base_sheet_prompt_has_turnaround_and_expressions(tmp_path, monkeypatch):
    captured = {}

    def fake(proj_dir, out, prompt, *, images=None, retries=2, on_line=None, post=None, **k):
        captured["prompt"] = prompt
        captured["images"] = images
        return {"status": "completed", "path": str(out)}

    monkeypatch.setattr(imagegen, "_run_codex_image", fake)
    monkeypatch.setattr(imagegen, "base_img", lambda: tmp_path / "base.jpg")
    (tmp_path / "base.jpg").write_bytes(b"x")
    r = sheets.build_base_character_sheet()
    assert r["status"] == "completed"
    assert "턴어라운드" in captured["prompt"] or "전신" in captured["prompt"]
    assert "표정" in captured["prompt"]
    assert captured["images"] == [str(tmp_path / "base.jpg")]


def test_build_base_sheet_no_base_fails(monkeypatch):
    monkeypatch.setattr(imagegen, "base_img", lambda: None)
    assert sheets.build_base_character_sheet()["status"] == "failed"
