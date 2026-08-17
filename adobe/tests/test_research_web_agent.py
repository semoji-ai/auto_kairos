import subprocess
from backend.research import web_agent


def test_run_web_research_returns_note(tmp_path, monkeypatch):
    def fake_run(cmd, *, input=None, cwd=None, capture_output=None, text=None, timeout=None, env=None):
        assert "--allowedTools" in cmd
        class R:
            returncode = 0
            stdout = "WEBSEARCH_OK: fact https://x"
            stderr = ""
        return R()
    monkeypatch.setattr(subprocess, "run", fake_run)
    note = web_agent.run_web_research(tmp_path, "research tesla")
    assert "WEBSEARCH_OK" in note


def test_run_web_research_strips_nesting_env(tmp_path, monkeypatch):
    seen = {}
    def fake_run(cmd, *, input=None, cwd=None, capture_output=None, text=None, timeout=None, env=None):
        seen["env"] = env
        class R:
            returncode = 0; stdout = "ok"; stderr = ""
        return R()
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setattr(subprocess, "run", fake_run)
    web_agent.run_web_research(tmp_path, "q")
    assert "CLAUDECODE" not in seen["env"]


def test_run_web_research_failure_returns_empty(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise subprocess.TimeoutExpired(cmd="claude", timeout=1)
    monkeypatch.setattr(subprocess, "run", boom)
    assert web_agent.run_web_research(tmp_path, "q") == ""


def test_run_web_research_nonzero_returns_empty(tmp_path, monkeypatch):
    def fake_run(*a, **k):
        class R:
            returncode = 1; stdout = ""; stderr = "err"
        return R()
    monkeypatch.setattr(subprocess, "run", fake_run)
    assert web_agent.run_web_research(tmp_path, "q") == ""
