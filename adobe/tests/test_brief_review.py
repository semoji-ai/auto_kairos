import json
from pathlib import Path
from backend import brief, llm


def _brief_file(tmp_path):
    p = tmp_path / "editorial_brief.v1.json"
    p.write_text(json.dumps({"real_topic": "유한양행", "hidden_truth": "사실은"}), encoding="utf-8")
    return p


def test_review_brief_parses_score_verdict(tmp_path, monkeypatch):
    bf = _brief_file(tmp_path)

    def fake_orch(prompt, cwd, *, output_schema=None, output_last=None, **k):
        Path(output_last).write_text(json.dumps({
            "score_total": 92, "verdict": "PASS",
            "revision_instructions": []}), encoding="utf-8")
        return {"returncode": 0, "output_last": output_last}
    monkeypatch.setattr(llm, "run_orchestrator", fake_orch)

    r = brief.review_brief(tmp_path, bf)
    assert r["score"] == 92
    assert r["verdict"] == "PASS"
    assert r["revision_instructions"] == []


def test_review_brief_revise_with_instructions(tmp_path, monkeypatch):
    bf = _brief_file(tmp_path)

    def fake_orch(prompt, cwd, *, output_schema=None, output_last=None, **k):
        Path(output_last).write_text(json.dumps({
            "score_total": 80, "verdict": "REVISE",
            "spine_blocking": {"failed_gates": ["G1"], "reasons": ["spine 없음"]},
            "revision_instructions": ["spine_question 작성", "hidden_truth 구체화"]}), encoding="utf-8")
        return {"returncode": 0, "output_last": output_last}
    monkeypatch.setattr(llm, "run_orchestrator", fake_orch)

    r = brief.review_brief(tmp_path, bf)
    assert r["score"] == 80 and r["verdict"] == "REVISE"
    assert r["spine_blocking"]["failed_gates"] == ["G1"]
    assert "spine_question 작성" in r["revision_instructions"]


def test_review_brief_parse_failure_is_revise_zero(tmp_path, monkeypatch):
    bf = _brief_file(tmp_path)

    def fake_orch(prompt, cwd, *, output_schema=None, output_last=None, **k):
        Path(output_last).write_text("not json", encoding="utf-8")
        return {"returncode": 0, "output_last": output_last}
    monkeypatch.setattr(llm, "run_orchestrator", fake_orch)

    r = brief.review_brief(tmp_path, bf)
    assert r["score"] == 0 and r["verdict"] == "REVISE"
