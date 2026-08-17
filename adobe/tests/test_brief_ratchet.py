import json
from pathlib import Path
from backend import brief


def _setup(tmp_path):
    (tmp_path / "plan.md").write_text("# 주제\n채널: semoji\n", encoding="utf-8")


def _fake_generate(tmp_path):
    """generate_brief 대체 — v{version}.json 생성하고 경로 반환."""
    def gen(proj_dir, *, version, prev_brief=None, revisions=None, on_event=None):
        p = Path(proj_dir) / f"editorial_brief.v{version}.json"
        p.write_text(json.dumps({"v": version}), encoding="utf-8")
        return p
    return gen


def test_round1_pass_locks(tmp_path, monkeypatch):
    _setup(tmp_path)
    monkeypatch.setattr(brief, "generate_brief", _fake_generate(tmp_path))
    monkeypatch.setattr(brief, "review_brief",
                        lambda pd, bp, **k: {"score": 95, "verdict": "PASS",
                                             "spine_blocking": None, "revision_instructions": []})
    r = brief.run_brief_ratchet(tmp_path)
    assert r["rounds"] == 1 and r["score"] == 95 and r["verdict"] == "PASS"
    locked = json.loads((tmp_path / "editorial_brief.json").read_text(encoding="utf-8"))
    assert locked["v"] == 1


def test_revise_then_pass(tmp_path, monkeypatch):
    _setup(tmp_path)
    monkeypatch.setattr(brief, "generate_brief", _fake_generate(tmp_path))
    scores = iter([{"score": 80, "verdict": "REVISE", "spine_blocking": None, "revision_instructions": ["x"]},
                   {"score": 92, "verdict": "PASS", "spine_blocking": None, "revision_instructions": []}])
    monkeypatch.setattr(brief, "review_brief", lambda pd, bp, **k: next(scores))
    r = brief.run_brief_ratchet(tmp_path)
    assert r["rounds"] == 2 and r["verdict"] == "PASS"
    assert json.loads((tmp_path / "editorial_brief.json").read_text(encoding="utf-8"))["v"] == 2


def test_no_pass_locks_best(tmp_path, monkeypatch):
    _setup(tmp_path)
    monkeypatch.setattr(brief, "generate_brief", _fake_generate(tmp_path))
    scores = iter([{"score": 80, "verdict": "REVISE", "spine_blocking": None, "revision_instructions": ["a"]},
                   {"score": 88, "verdict": "REVISE", "spine_blocking": None, "revision_instructions": ["b"]},
                   {"score": 85, "verdict": "REVISE", "spine_blocking": None, "revision_instructions": ["c"]}])
    monkeypatch.setattr(brief, "review_brief", lambda pd, bp, **k: next(scores))
    r = brief.run_brief_ratchet(tmp_path)
    assert r["rounds"] == 3 and r["verdict"] == "REVISE"
    assert r["score"] == 88
    assert json.loads((tmp_path / "editorial_brief.json").read_text(encoding="utf-8"))["v"] == 2


def test_monotonic_keeps_best_on_drop(tmp_path, monkeypatch):
    _setup(tmp_path)
    monkeypatch.setattr(brief, "generate_brief", _fake_generate(tmp_path))
    scores = iter([{"score": 85, "verdict": "REVISE", "spine_blocking": None, "revision_instructions": ["a"]},
                   {"score": 70, "verdict": "REVISE", "spine_blocking": None, "revision_instructions": ["b"]},
                   {"score": 75, "verdict": "REVISE", "spine_blocking": None, "revision_instructions": ["c"]}])
    monkeypatch.setattr(brief, "review_brief", lambda pd, bp, **k: next(scores))
    r = brief.run_brief_ratchet(tmp_path)
    assert r["score"] == 85
    assert json.loads((tmp_path / "editorial_brief.json").read_text(encoding="utf-8"))["v"] == 1


def test_spine_blocking_forbids_pass(tmp_path, monkeypatch):
    _setup(tmp_path)
    monkeypatch.setattr(brief, "generate_brief", _fake_generate(tmp_path))
    monkeypatch.setattr(brief, "review_brief",
                        lambda pd, bp, **k: {"score": 95, "verdict": "REVISE",
                                             "spine_blocking": {"failed_gates": ["G1"], "reasons": ["no spine"]},
                                             "revision_instructions": ["spine 작성"]})
    r = brief.run_brief_ratchet(tmp_path, max_rounds=2)
    assert r["verdict"] != "PASS"
    assert r["rounds"] == 2


def test_generate_failure_locks_best_or_errors(tmp_path, monkeypatch):
    _setup(tmp_path)
    monkeypatch.setattr(brief, "generate_brief", lambda *a, **k: None)
    monkeypatch.setattr(brief, "review_brief", lambda *a, **k: {"score": 0, "verdict": "REVISE",
                                                               "spine_blocking": None, "revision_instructions": []})
    r = brief.run_brief_ratchet(tmp_path)
    assert r.get("error")
