import json
from pathlib import Path
from backend.research import orchestrator


def _brief(tmp_path, dur="3분"):
    (tmp_path / "plan.md").write_text(f"# 유한양행\n채널: semoji\n분량: {dur}\n", encoding="utf-8")
    (tmp_path / "editorial_brief.json").write_text(
        json.dumps({"real_topic": "유한양행", "core_question": "왜?"}), encoding="utf-8")


def _patch(monkeypatch, *, web=lambda cwd, p, **k: "웹노트: 사실 https://x", synth=True):
    monkeypatch.setattr(orchestrator.query_planner, "plan_queries",
                        lambda b, **k: [{"query": "유한양행", "rationale": "", "lang": "ko"}])
    def fake_collect(proj_dir, queries, **k):
        man = Path(proj_dir) / "research" / "manifests" / "t"
        man.mkdir(parents=True, exist_ok=True)
        (man / "sources.jsonl").write_text(
            '{"title":"위키","url":"u","lane":"wikipedia","tier_hint":"A","snippet":"s"}\n',
            encoding="utf-8")
        return {"runs": [], "sources": 1, "manifest": str(man / "sources.jsonl")}
    monkeypatch.setattr(orchestrator.collector, "collect_queries", fake_collect)
    monkeypatch.setattr(orchestrator.web_agent, "run_web_research", web)
    if synth:
        monkeypatch.setattr(orchestrator, "_synthesize",
                            lambda proj, brief, sources, notes, on_event=None: {
                                "topic": "유한양행", "queries": ["유한양행"],
                                "sources": sources, "web_findings": [{"angle": "a", "claim": "c", "source_url": "x"}],
                                "digest": {}})
    else:
        monkeypatch.setattr(orchestrator, "_synthesize",
                            lambda proj, brief, sources, notes, on_event=None: None)


def test_run_research_full(tmp_path, monkeypatch):
    _brief(tmp_path)
    _patch(monkeypatch)
    r = orchestrator.run_research(tmp_path, max_workers=2)
    rep = Path(r["report"])
    assert rep.name == "research_report.json" and rep.is_file()
    data = json.loads(rep.read_text(encoding="utf-8"))
    assert data["topic"] == "유한양행"
    assert r["sources"] == 1 and r["web_notes"] >= 1
    assert (tmp_path / "research_digest.json").is_file()


def test_run_research_scales_web_agents(tmp_path, monkeypatch):
    _brief(tmp_path, dur="10분")
    calls = {"n": 0}
    def counting_web(cwd, p, **k):
        calls["n"] += 1
        return "노트"
    _patch(monkeypatch, web=counting_web)
    orchestrator.run_research(tmp_path, max_workers=3)
    assert calls["n"] == 6


def test_run_research_partial_web_failure(tmp_path, monkeypatch):
    _brief(tmp_path, dur="1분")
    seq = iter(["", "노트2", "노트3"])
    _patch(monkeypatch, web=lambda cwd, p, **k: next(seq, ""))
    r = orchestrator.run_research(tmp_path, max_workers=1)
    assert r["web_notes"] == 2


def test_run_research_synth_failure_digest_fallback(tmp_path, monkeypatch):
    _brief(tmp_path)
    _patch(monkeypatch, synth=False)
    r = orchestrator.run_research(tmp_path, max_workers=2)
    data = json.loads(Path(r["report"]).read_text(encoding="utf-8"))
    assert data["web_findings"] == []
    assert data["digest"]["source_count"] == 1


def test_run_research_no_brief_errors(tmp_path, monkeypatch):
    (tmp_path / "plan.md").write_text("# x\n", encoding="utf-8")
    r = orchestrator.run_research(tmp_path)
    assert r.get("error")
