import json
from pathlib import Path
from backend import brief, llm


def test_generate_brief_writes_versioned(tmp_path, monkeypatch):
    (tmp_path / "plan.md").write_text("# 유한양행\n채널: semoji\n분량: 10분\n톤: 다큐\n", encoding="utf-8")
    captured = {}

    def fake_orch(prompt, cwd, *, output_schema=None, output_last=None, **k):
        captured["prompt"] = prompt
        captured["schema"] = output_schema
        Path(output_last).write_text(json.dumps({
            "real_topic": "유한양행", "core_question": "왜?", "hidden_truth": "사실은",
            "narrative_arc": {}, "human_truth": {}}), encoding="utf-8")
        return {"returncode": 0, "output_last": output_last}
    monkeypatch.setattr(llm, "run_orchestrator", fake_orch)

    out = brief.generate_brief(tmp_path, version=1)
    assert out == tmp_path / "editorial_brief.v1.json"
    assert out.is_file()
    assert "유한양행" in captured["prompt"]
    assert captured["schema"].endswith("editorial_brief.schema.json")


def test_generate_brief_with_revisions_injects_prev(tmp_path, monkeypatch):
    (tmp_path / "plan.md").write_text("# 주제\n", encoding="utf-8")
    prev = tmp_path / "editorial_brief.v1.json"
    prev.write_text(json.dumps({"real_topic": "X"}), encoding="utf-8")
    seen = {}

    def fake_orch(prompt, cwd, *, output_schema=None, output_last=None, **k):
        seen["prompt"] = prompt
        Path(output_last).write_text("{}", encoding="utf-8")
        return {"returncode": 0, "output_last": output_last}
    monkeypatch.setattr(llm, "run_orchestrator", fake_orch)

    brief.generate_brief(tmp_path, version=2, prev_brief=prev,
                         revisions=["hidden_truth를 구체화"])
    assert "hidden_truth를 구체화" in seen["prompt"]
    assert "X" in seen["prompt"]


def test_generate_brief_failure_returns_none(tmp_path, monkeypatch):
    (tmp_path / "plan.md").write_text("# 주제\n", encoding="utf-8")
    monkeypatch.setattr(llm, "run_orchestrator",
                        lambda *a, **k: {"returncode": 1, "output_last": k.get("output_last")})
    assert brief.generate_brief(tmp_path, version=1) is None
