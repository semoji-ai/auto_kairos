import json
from pathlib import Path
from backend import manuscript, llm


def test_write_manuscript_versioned(tmp_path, monkeypatch):
    (tmp_path / "draft.md").write_text("# 초고\n본문", encoding="utf-8")
    (tmp_path / "targeted_claims.json").write_text('[{"question":"q","claim":"c https://x"}]', encoding="utf-8")
    (tmp_path / "editorial_brief.json").write_text('{"real_topic":"유한양행"}', encoding="utf-8")
    seen = {}

    def fake_orch(prompt, cwd, *, output_schema=None, output_last=None, **k):
        seen["prompt"] = prompt
        Path(output_last).write_text("# 최종 원고\n완성 본문", encoding="utf-8")
        return {"returncode": 0, "output_last": output_last}
    monkeypatch.setattr(llm, "run_orchestrator", fake_orch)

    out = manuscript.write_manuscript(tmp_path, version=1)
    assert out == tmp_path / "final_manuscript.v1.md"
    assert out.read_text(encoding="utf-8").startswith("# 최종 원고")
    assert "초고" in seen["prompt"] and "c https://x" in seen["prompt"]


def test_write_manuscript_with_revisions(tmp_path, monkeypatch):
    (tmp_path / "draft.md").write_text("초고", encoding="utf-8")
    prev = tmp_path / "final_manuscript.v1.md"
    prev.write_text("이전 원고", encoding="utf-8")
    seen = {}

    def fake_orch(prompt, cwd, *, output_schema=None, output_last=None, **k):
        seen["prompt"] = prompt
        Path(output_last).write_text("개선 원고", encoding="utf-8")
        return {"returncode": 0, "output_last": output_last}
    monkeypatch.setattr(llm, "run_orchestrator", fake_orch)

    manuscript.write_manuscript(tmp_path, version=2, prev=prev, revisions=["hook 강화"])
    assert "hook 강화" in seen["prompt"] and "이전 원고" in seen["prompt"]


def test_write_manuscript_failure_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "run_orchestrator",
                        lambda *a, **k: {"returncode": 1, "output_last": k.get("output_last")})
    assert manuscript.write_manuscript(tmp_path, version=1) is None
