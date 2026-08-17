import json
from pathlib import Path

from backend import motion

SID = "abc123"


def _proj(tmp_path: Path, kinds: dict):
    lay = tmp_path / "layers"
    lay.mkdir(parents=True)
    specs = []
    for i, (stem, kind) in enumerate(kinds.items()):
        (lay / (stem + ".png")).write_bytes(b"png")
        specs.append({"layer": stem, "index": i, "name": stem, "name_en": stem,
                      "location": "", "kind": kind, "intent": ""})
    (lay / f"{SID}__elements.json").write_text(
        json.dumps(specs, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def test_allowed_by_kind_contents():
    assert motion.ALLOWED_BY_KIND["character"] == {"bob", "zoom_emphasis"}
    assert "stamp" in motion.ALLOWED_BY_KIND["object"]
    assert "wiggle" in motion.ALLOWED_BY_KIND["object"]
    assert "bob" not in motion.ALLOWED_BY_KIND["object"]


def test_layer_kinds_from_sidecar(tmp_path):
    proj = _proj(tmp_path, {f"{SID}__0_kid": "character", f"{SID}__1_car": "object"})
    kinds = motion.layer_kinds(proj, SID, [f"{SID}__0_kid", f"{SID}__1_car"])
    assert kinds[f"{SID}__0_kid"] == "character"
    assert kinds[f"{SID}__1_car"] == "object"


def test_layer_kinds_char_suffix_fallback(tmp_path):
    """사이드카 없는 구버전 — _char 접미사로 인물을 가른다."""
    (tmp_path / "layers").mkdir(parents=True)
    kinds = motion.layer_kinds(tmp_path, SID, [f"{SID}__0_kid_char", f"{SID}__1_car"])
    assert kinds[f"{SID}__0_kid_char"] == "character"
    assert kinds[f"{SID}__1_car"] == "object"


def _plan(layer, types):
    return {"layers": [{"layer": layer,
                        "moves": [{"type": t, "start": 0, "duration": 1,
                                   "direction": None, "amount": None} for t in types]}],
            "camera": {"type": "none", "amount": None}}


def test_filter_keeps_char_bob_drops_slide(tmp_path):
    plan = _plan("kid", ["bob", "slide_in", "zoom_emphasis"])
    out = motion.filter_plan_moves(plan, {"kid": "character"})
    got = [m["type"] for m in out["layers"][0]["moves"]]
    assert got == ["bob", "zoom_emphasis"]


def test_filter_keeps_object_stamp_wiggle_drops_bob(tmp_path):
    plan = _plan("car", ["stamp", "wiggle", "bob"])
    out = motion.filter_plan_moves(plan, {"car": "object"})
    got = [m["type"] for m in out["layers"][0]["moves"]]
    assert got == ["stamp", "wiggle"]


def test_filter_drops_unknown_layer_entirely(tmp_path):
    plan = _plan("ghost", ["bob"])
    out = motion.filter_plan_moves(plan, {"kid": "character"})
    assert out["layers"] == []


def test_filter_drops_layer_with_no_surviving_moves(tmp_path):
    plan = _plan("kid", ["slide_in"])
    out = motion.filter_plan_moves(plan, {"kid": "character"})
    assert out["layers"] == []


def test_schema_has_new_presets():
    schema = json.loads(
        (Path("backend/schemas/motion_plan.schema.json")).read_text(encoding="utf-8"))
    enum = schema["properties"]["layers"]["items"]["properties"]["moves"]["items"][
        "properties"]["type"]["enum"]
    assert "stamp" in enum and "wiggle" in enum


def test_preset_guide_mentions_new_presets():
    assert "stamp" in motion.PRESET_GUIDE
    assert "wiggle" in motion.PRESET_GUIDE
