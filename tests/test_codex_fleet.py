from pathlib import Path
from unittest.mock import patch

from auto_agent.tools.codex_fleet import CodexImageJob, run_codex_batch, _auto_parallel


def _job(i, tmp_path):
    return CodexImageJob(idx=i, prompt=f"p{i}. AR 16:9", size="1792x1024",
                         out_path=tmp_path / f"scene_{i:03d}_gen_01.png")


@patch("auto_agent.tools.codex_fleet.codex_generate", return_value=(True, ""))
def test_all_success(mock_gen, tmp_path):
    results = run_codex_batch([_job(i, tmp_path) for i in range(3)])
    assert [r.success for r in sorted(results, key=lambda r: r.idx)] == [True] * 3
    assert mock_gen.call_count == 3


@patch("auto_agent.tools.codex_fleet.codex_generate",
       side_effect=[(True, ""), (False, "moderation"), (True, "")])
def test_partial_failure_reported(mock_gen, tmp_path):
    results = sorted(run_codex_batch([_job(i, tmp_path) for i in range(3)]), key=lambda r: r.idx)
    assert sum(1 for r in results if not r.success) == 1


def test_auto_parallel_env_override(monkeypatch):
    monkeypatch.setenv("CODEX_IMG_PARALLEL", "7")
    assert _auto_parallel(100) == 7


def test_auto_parallel_bounds(monkeypatch):
    monkeypatch.delenv("CODEX_IMG_PARALLEL", raising=False)
    assert 1 <= _auto_parallel(2) <= 2
    assert _auto_parallel(1000) <= 32


@patch("auto_agent.tools.codex_fleet.codex_generate",
       side_effect=[RuntimeError("boom"), (True, ""), (True, "")])
def test_worker_exception_isolated(mock_gen, tmp_path):
    results = run_codex_batch([_job(i, tmp_path) for i in range(3)])
    assert len(results) == 3
    assert sum(1 for r in results if r.success) == 2
    failed = [r for r in results if not r.success]
    assert "boom" in failed[0].error
