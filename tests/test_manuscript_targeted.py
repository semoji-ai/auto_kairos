import json
from pathlib import Path
from backend import manuscript


def test_targeted_research_builds_claims(tmp_path, monkeypatch):
    monkeypatch.setattr(manuscript.web_agent, "run_web_research",
                        lambda cwd, prompt, **k: f"발견: {prompt[:6]} https://x")
    claims = manuscript.targeted_research(tmp_path, ["왜 1933년?", "적자 규모?"], max_workers=2)
    assert len(claims) == 2
    assert all("claim" in c and "question" in c for c in claims)
    assert (tmp_path / "targeted_claims.json").is_file()


def test_targeted_research_isolates_empty(tmp_path, monkeypatch):
    seq = iter(["", "발견2 https://y"])
    monkeypatch.setattr(manuscript.web_agent, "run_web_research",
                        lambda cwd, prompt, **k: next(seq, ""))
    claims = manuscript.targeted_research(tmp_path, ["q1", "q2"], max_workers=1)
    assert len(claims) == 1
    assert claims[0]["question"] == "q2"


def test_targeted_research_empty_questions(tmp_path, monkeypatch):
    claims = manuscript.targeted_research(tmp_path, [])
    assert claims == []
