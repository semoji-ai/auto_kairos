from pathlib import Path
from backend import llm


def test_default_orchestrator_claude(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "_CFG", tmp_path / "llm_config.json")
    monkeypatch.delenv("AK_ORCHESTRATOR", raising=False)
    assert llm.get_orchestrator() == "claude"


def test_set_get_orchestrator(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "_CFG", tmp_path / "llm_config.json")
    llm.set_orchestrator("codex")
    assert llm.get_orchestrator() == "codex"
    llm.set_orchestrator("이상한값")          # 검증 → claude로
    assert llm.get_orchestrator() == "claude"


def test_run_orchestrator_routes_text_to_claude(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "_CFG", tmp_path / "c.json"); llm.set_orchestrator("claude")
    seen = {}
    monkeypatch.setattr(llm.claude_runner, "run_claude", lambda *a, **k: seen.update(engine="claude") or {"returncode": 0})
    monkeypatch.setattr(llm.codex_runner, "run_skill", lambda *a, **k: seen.update(engine="codex") or {"returncode": 0})
    llm.run_orchestrator("p", tmp_path)                       # 텍스트 → claude
    assert seen["engine"] == "claude"


def test_run_orchestrator_forces_codex_for_images(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "_CFG", tmp_path / "c.json"); llm.set_orchestrator("claude")
    seen = {}
    monkeypatch.setattr(llm.claude_runner, "run_claude", lambda *a, **k: seen.update(engine="claude") or {"returncode": 0})
    monkeypatch.setattr(llm.codex_runner, "run_skill", lambda *a, **k: seen.update(engine="codex") or {"returncode": 0})
    llm.run_orchestrator("p", tmp_path, images=["/x.png"])    # 멀티모달 → codex 강제
    assert seen["engine"] == "codex"


def test_run_orchestrator_codex_engine(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "_CFG", tmp_path / "c.json"); llm.set_orchestrator("codex")
    seen = {}
    monkeypatch.setattr(llm.codex_runner, "run_skill", lambda *a, **k: seen.update(engine="codex") or {"returncode": 0})
    llm.run_orchestrator("p", tmp_path)
    assert seen["engine"] == "codex"


def test_claude_model_setting_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "_CFG", tmp_path / "c.json")
    monkeypatch.delenv("AK_CLAUDE_MODEL", raising=False)
    assert llm.claude_model() is None                    # 기본: CLI 기본 모델
    llm.set_orchestrator("claude", claude_model_name="claude-haiku-4-5-20251001")
    assert llm.claude_model() == "claude-haiku-4-5-20251001"
    llm.set_orchestrator("codex")                        # 엔진 변경해도 모델 설정 보존
    assert llm.claude_model() == "claude-haiku-4-5-20251001"
    llm.set_orchestrator("claude", claude_model_name="")  # 해제
    assert llm.claude_model() is None


def test_run_orchestrator_passes_claude_model(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "_CFG", tmp_path / "c.json")
    llm.set_orchestrator("claude", claude_model_name="claude-sonnet-4-6")
    seen = {}
    monkeypatch.setattr(llm.claude_runner, "run_claude",
                        lambda *a, **k: seen.update(model=k.get("model")) or {"returncode": 0})
    llm.run_orchestrator("p", tmp_path)
    assert seen["model"] == "claude-sonnet-4-6"
