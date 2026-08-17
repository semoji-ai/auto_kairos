import json
from pathlib import Path
from backend import manuscript


def _report(tmp_path):
    (tmp_path / "research_report.json").write_text('{"topic":"유한양행"}', encoding="utf-8")
    (tmp_path / "editorial_brief.json").write_text('{"real_topic":"유한양행"}', encoding="utf-8")


def _patch(monkeypatch, tmp_path, reviews, *, questions=("q1",), draft_ok=True):
    def fake_draft(proj_dir, **k):
        if not draft_ok:
            return None, []
        (Path(proj_dir) / "draft.md").write_text("초고", encoding="utf-8")
        return Path(proj_dir) / "draft.md", list(questions)
    monkeypatch.setattr(manuscript, "generate_draft", fake_draft)
    monkeypatch.setattr(manuscript, "targeted_research",
                        lambda proj, qs, **k: [{"question": q, "claim": "c"} for q in qs])
    def fake_write(proj_dir, *, version, prev=None, revisions=None, on_event=None):
        p = Path(proj_dir) / f"final_manuscript.v{version}.md"
        p.write_text(f"원고 v{version}", encoding="utf-8")
        return p
    monkeypatch.setattr(manuscript, "write_manuscript", fake_write)
    it = iter(reviews)
    monkeypatch.setattr(manuscript, "review_manuscript", lambda proj, ms, **k: next(it))


def test_pipeline_round1_pass(tmp_path, monkeypatch):
    _report(tmp_path)
    _patch(monkeypatch, tmp_path, [{"score": 95, "verdict": "PASS", "revision_instructions": []}])
    r = manuscript.run_manuscript_pipeline(tmp_path)
    assert r["rounds"] == 1 and r["score"] == 95 and r["verdict"] == "PASS"
    assert (tmp_path / "final_manuscript.md").read_text(encoding="utf-8") == "원고 v1"
    assert r["claims"] == 1


def test_pipeline_revise_then_pass(tmp_path, monkeypatch):
    _report(tmp_path)
    _patch(monkeypatch, tmp_path,
           [{"score": 80, "verdict": "REVISE", "revision_instructions": ["x"]},
            {"score": 91, "verdict": "PASS", "revision_instructions": []}])
    r = manuscript.run_manuscript_pipeline(tmp_path)
    assert r["rounds"] == 2 and r["verdict"] == "PASS"
    assert (tmp_path / "final_manuscript.md").read_text(encoding="utf-8") == "원고 v2"


def test_pipeline_no_pass_locks_best(tmp_path, monkeypatch):
    _report(tmp_path)
    _patch(monkeypatch, tmp_path,
           [{"score": 80, "verdict": "REVISE", "revision_instructions": ["a"]},
            {"score": 88, "verdict": "REVISE", "revision_instructions": ["b"]},
            {"score": 85, "verdict": "REVISE", "revision_instructions": ["c"]}])
    r = manuscript.run_manuscript_pipeline(tmp_path)
    assert r["rounds"] == 3 and r["score"] == 88 and r["verdict"] == "REVISE"
    assert (tmp_path / "final_manuscript.md").read_text(encoding="utf-8") == "원고 v2"


def test_pipeline_monotonic_keeps_best(tmp_path, monkeypatch):
    _report(tmp_path)
    _patch(monkeypatch, tmp_path,
           [{"score": 85, "verdict": "REVISE", "revision_instructions": ["a"]},
            {"score": 70, "verdict": "REVISE", "revision_instructions": ["b"]},
            {"score": 75, "verdict": "REVISE", "revision_instructions": ["c"]}])
    r = manuscript.run_manuscript_pipeline(tmp_path)
    assert r["score"] == 85
    assert (tmp_path / "final_manuscript.md").read_text(encoding="utf-8") == "원고 v1"


def test_pipeline_no_questions_skips_targeted(tmp_path, monkeypatch):
    _report(tmp_path)
    called = {"targeted": False}
    _patch(monkeypatch, tmp_path, [{"score": 95, "verdict": "PASS", "revision_instructions": []}],
           questions=())
    monkeypatch.setattr(manuscript, "targeted_research",
                        lambda *a, **k: called.__setitem__("targeted", True) or [])
    r = manuscript.run_manuscript_pipeline(tmp_path)
    assert called["targeted"] is False and r["claims"] == 0


def test_pipeline_no_report_errors(tmp_path, monkeypatch):
    r = manuscript.run_manuscript_pipeline(tmp_path)
    assert r.get("error")


def test_pipeline_draft_failure_errors(tmp_path, monkeypatch):
    _report(tmp_path)
    _patch(monkeypatch, tmp_path, [], draft_ok=False)
    r = manuscript.run_manuscript_pipeline(tmp_path)
    assert r.get("error")
