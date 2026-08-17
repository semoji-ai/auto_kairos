import json
from pathlib import Path
from backend import manuscript, llm


def _inputs(tmp_path):
    (tmp_path / "research_report.json").write_text(json.dumps({"topic": "유한양행", "sources": []}), encoding="utf-8")
    (tmp_path / "editorial_brief.json").write_text(json.dumps({"real_topic": "유한양행"}), encoding="utf-8")


def test_generate_draft_writes_draft_and_questions(tmp_path, monkeypatch):
    _inputs(tmp_path)
    captured = {}

    def fake_orch(prompt, cwd, *, output_schema=None, output_last=None, **k):
        captured["prompt"] = prompt
        Path(output_last).write_text(json.dumps({
            "draft_markdown": "# 초고\n본문...", "questions": ["왜 1933년인가?", "적자 규모는?"]}),
            encoding="utf-8")
        return {"returncode": 0, "output_last": output_last}
    monkeypatch.setattr(llm, "run_orchestrator", fake_orch)

    draft_path, questions = manuscript.generate_draft(tmp_path)
    assert draft_path == tmp_path / "draft.md"
    assert (tmp_path / "draft.md").read_text(encoding="utf-8").startswith("# 초고")
    assert questions == ["왜 1933년인가?", "적자 규모는?"]
    assert (tmp_path / "research_questions.json").is_file()
    assert "유한양행" in captured["prompt"]


def test_generate_draft_failure_returns_none(tmp_path, monkeypatch):
    _inputs(tmp_path)
    monkeypatch.setattr(llm, "run_orchestrator",
                        lambda *a, **k: {"returncode": 1, "output_last": k.get("output_last")})
    draft_path, questions = manuscript.generate_draft(tmp_path)
    assert draft_path is None and questions == []
