import json
from pathlib import Path
from backend import manuscript, llm


def _ms(tmp_path):
    p = tmp_path / "final_manuscript.v1.md"
    p.write_text("# 원고\n본문", encoding="utf-8")
    (tmp_path / "editorial_brief.json").write_text('{"real_topic":"유한양행"}', encoding="utf-8")
    return p


def test_review_manuscript_pass(tmp_path, monkeypatch):
    ms = _ms(tmp_path)

    def fake_orch(prompt, cwd, *, output_schema=None, output_last=None, **k):
        Path(output_last).write_text(json.dumps({
            "score_total": 92, "verdict": "PASS", "revision_instructions": [],
            "viewer_score": 90, "expert_score": 94}), encoding="utf-8")
        return {"returncode": 0, "output_last": output_last}
    monkeypatch.setattr(llm, "run_orchestrator", fake_orch)

    r = manuscript.review_manuscript(tmp_path, ms)
    assert r["score"] == 92 and r["verdict"] == "PASS" and r["revision_instructions"] == []


def test_review_manuscript_revise(tmp_path, monkeypatch):
    ms = _ms(tmp_path)

    def fake_orch(prompt, cwd, *, output_schema=None, output_last=None, **k):
        Path(output_last).write_text(json.dumps({
            "score_total": 80, "verdict": "REVISE",
            "revision_instructions": ["hook 강화", "출처 보강"]}), encoding="utf-8")
        return {"returncode": 0, "output_last": output_last}
    monkeypatch.setattr(llm, "run_orchestrator", fake_orch)

    r = manuscript.review_manuscript(tmp_path, ms)
    assert r["score"] == 80 and r["verdict"] == "REVISE"
    assert "hook 강화" in r["revision_instructions"]


def test_review_manuscript_parse_failure(tmp_path, monkeypatch):
    ms = _ms(tmp_path)
    def fake_orch(prompt, cwd, *, output_schema=None, output_last=None, **k):
        Path(output_last).write_text("nope", encoding="utf-8")
        return {"returncode": 0, "output_last": output_last}
    monkeypatch.setattr(llm, "run_orchestrator", fake_orch)
    r = manuscript.review_manuscript(tmp_path, ms)
    assert r["score"] == 0 and r["verdict"] == "REVISE"
