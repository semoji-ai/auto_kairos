import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from auto_agent.modules.content_planner_module import REQUIRED_BRIEF_FIELDS as REQUIRED_FIELDS

def test_validate_brief_valid():
    from auto_agent.modules.content_planner_module import validate_brief
    brief = {f: "x" for f in REQUIRED_FIELDS}
    brief["excluded_angles"] = ["a"]
    brief["success_criteria"] = ["b"]
    brief["must_cover"] = ["c"]
    brief["key_persons"] = ["d"]
    errors = validate_brief(brief)
    assert errors == []

def test_validate_brief_missing_field():
    from auto_agent.modules.content_planner_module import validate_brief
    brief = {"core_question": "Q"}
    errors = validate_brief(brief)
    assert any("real_topic" in e for e in errors)
    assert any("must_cover" in e for e in errors)

def test_save_brief_creates_file(tmp_path):
    from auto_agent.modules.content_planner_module import save_brief
    brief = {"core_question": "Q", "real_topic": "T"}
    path = save_brief(brief, tmp_path)
    assert path.exists()
    import json
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["core_question"] == "Q"

def test_save_brief_no_overwrite(tmp_path):
    from auto_agent.modules.content_planner_module import save_brief
    brief = {"core_question": "Q"}
    save_brief(brief, tmp_path)
    with pytest.raises(FileExistsError):
        save_brief({"core_question": "Q2"}, tmp_path, overwrite=False)

def test_save_brief_overwrite(tmp_path):
    from auto_agent.modules.content_planner_module import save_brief
    import json
    save_brief({"core_question": "Q1"}, tmp_path)
    save_brief({"core_question": "Q2"}, tmp_path, overwrite=True)
    data = json.loads((tmp_path / "editorial_brief.json").read_text())
    assert data["core_question"] == "Q2"

def test_default_brief_has_must_cover():
    from auto_agent.modules.content_planner_module import _default_planner_brief
    brief = _default_planner_brief("포켓몬 30주년")
    assert "must_cover" in brief
    assert isinstance(brief["must_cover"], list)
    assert "key_persons" in brief

def test_default_brief_empty_topic():
    from auto_agent.modules.content_planner_module import _default_planner_brief
    brief = _default_planner_brief("")
    assert brief["entity_slug"] != ""
    assert brief["real_topic"] != ""

def test_default_brief_special_chars():
    from auto_agent.modules.content_planner_module import _default_planner_brief
    brief = _default_planner_brief("C++ 역사")
    # slug에 + 가 포함되면 안 됨
    assert "+" not in brief["entity_slug"]
    assert "+" not in brief["section_slug"]
