from pathlib import Path
from backend import pipeline


def test_pipeline_order():
    assert pipeline.PIPELINE == [
        "plan-explore", "deep-research", "draft-write",
        "target-research", "finalize-manuscript", "review-refine",
    ]


def test_run_pipeline_calls_each_stage(tmp_path, monkeypatch):
    import backend.pipeline as p
    proj = tmp_path / "proj"; proj.mkdir()
    (proj / "plan.md").write_text("# 테스트 주제", encoding="utf-8")
    called = []

    def fake_run_one(skills_dir, proj_dir, name, on_line=None):
        called.append(name)
        from backend import skills_cfg
        cfg = skills_cfg.load_config(skills_dir, name)
        out = proj_dir / cfg["output"]
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("산출", encoding="utf-8")
        return {"status": "completed", "output": str(out)}

    monkeypatch.setattr(p, "run_one", fake_run_one)
    result = p.run_pipeline(Path(__file__).resolve().parents[1] / "skills", proj)
    assert called == p.PIPELINE
    assert result["status"] == "completed"
