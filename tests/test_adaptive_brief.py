import json
from unittest.mock import Mock

from auto_agent.modules import content_planner_module as planner
from auto_agent.modules import brief_review_module as reviewer


def test_stagnation_keeps_best_and_supplies_feedback(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTO_AGENT_EXECUTION_PROFILE", "balanced")
    generate = Mock(side_effect=[{"core_question": "first"}, {"core_question": "second"}])
    monkeypatch.setattr(planner, "generate_auto_brief", generate)
    review = Mock(side_effect=[
        {"score_total": 80, "verdict": "REVISE", "revision_instructions": ["fix evidence"]},
        {"score_total": 79, "verdict": "REVISE", "revision_instructions": ["fix evidence"]},
    ])
    monkeypatch.setattr(reviewer, "review_brief", review)
    result = planner.ratchet_brief_v1(tmp_path, "topic", max_rounds=5)
    assert generate.call_count == review.call_count == 2
    assert generate.call_args.kwargs["feedback"]["revision_instructions"] == ["fix evidence"]
    assert result["stop_reason"] == "no_quality_gain"
    selected = json.loads((tmp_path / "editorial_brief.json").read_text())
    assert selected["core_question"] == "first"
    assert len(list(tmp_path.glob("brief_attempt_*.json"))) == 2


def test_high_score_does_not_override_failed_gate(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTO_AGENT_EXECUTION_PROFILE", "balanced")
    monkeypatch.setattr(planner, "generate_auto_brief", Mock(return_value={"core_question": "q"}))
    monkeypatch.setattr(reviewer, "review_brief", Mock(return_value={
        "score_total": 95, "verdict": "REVISE", "score_breakdown": {
            "spine_blocking": {"failed_gates": ["G1"]}}}))
    result = planner.ratchet_brief_v1(tmp_path, "topic")
    assert result["verdict"] == "REVISE"
    assert result["stop_reason"] != "quality_pass"


def test_quality_pass_stops_after_one_review(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTO_AGENT_EXECUTION_PROFILE", "balanced")
    generate = Mock(return_value={"core_question": "q"})
    monkeypatch.setattr(planner, "generate_auto_brief", generate)
    monkeypatch.setattr(reviewer, "review_brief", Mock(return_value={"score_total": 90, "verdict": "PASS"}))
    assert planner.ratchet_brief_v1(tmp_path, "topic")["stop_reason"] == "quality_pass"
    assert generate.call_count == 1
