import json
import subprocess
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from auto_agent.orchestrator import execution as ex
from auto_agent.orchestrator.context_memory import ContextMemory
from auto_agent.orchestrator.runner import PipelineRunner


@pytest.fixture(autouse=True)
def clean_execution_env(monkeypatch):
    for key in ("AUTO_AGENT_PROVIDER", "AUTO_AGENT_EXECUTION_PROFILE", "AUTO_AGENT_CODEX_MODEL",
                "AUTO_AGENT_CLAUDE_MODEL", "AUTO_AGENT_RESEARCH_PROVIDER"):
        monkeypatch.delenv(key, raising=False)


def test_routing_precedence_and_models():
    config = {"execution": {"provider": "claude", "agents": {
        "script-director": {"provider": "codex", "profile": "quality"}}}}
    assert ex.resolve_execution("script-director", {}, config).model == "gpt-6-astra"
    assert ex.resolve_execution("reviewer", {}, config).model == "claude-opus-5"
    selected = ex.resolve_execution("script-director", {}, config,
                                    {"execution": {"provider": "claude", "model": "claude-fable-5-1"}})
    assert selected.model == "claude-fable-5-1"
    assert ex.resolve_execution("writer", {}, {"execution": {"provider": "codex"}}).model == "gpt-5.6-sol"


def test_bad_provider_or_model_does_not_silently_fallback():
    with pytest.raises(ValueError):
        ex.resolve_execution("writer", {}, {"execution": {"provider": "typo"}})
    with pytest.raises(ValueError):
        ex.resolve_execution("writer", {}, {"execution": {"provider": "codex", "model": "opus"}})


@pytest.mark.parametrize("provider,model", [("claude", "claude-opus-5"), ("codex", "gpt-5.6-sol")])
def test_shared_chapter_instructions_survive_provider_selection(tmp_path, monkeypatch, provider, model):
    monkeypatch.setattr(ex.shutil, "which", lambda name: "/bin/" + name)
    proc = Mock(returncode=0)
    proc.communicate.return_value = ('{"result":"ok"}' if provider == "claude" else
                                    '{"type":"turn.completed","usage":{}}', "")
    popen = Mock(return_value=proc)
    monkeypatch.setattr(ex.subprocess, "Popen", popen)
    static = tmp_path / "chapter-system.txt"
    static.write_text("SHARED CHAPTER RULES", encoding="utf-8")
    result = ex.run_cli(ex.ExecutionSpec(provider, model), "CHAPTER TASK", tmp_path,
                        system_prompt_file=static)
    assert result.returncode == 0
    command = popen.call_args.args[0]
    prompt = proc.communicate.call_args.kwargs["input"]
    if provider == "claude":
        assert command[command.index("--append-system-prompt-file") + 1] == str(static)
        assert prompt == "CHAPTER TASK"
    else:
        assert "--append-system-prompt-file" not in command
        assert prompt == "SHARED CHAPTER RULES\n\nCHAPTER TASK"


def test_legacy_preserves_pinned_model():
    result = ex.resolve_execution("writer", {"model": "claude-opus-4-6"}, {"execution": {"profile": "legacy"}})
    assert result.model == "claude-opus-4-6"


def test_codex_usage_sums_turns_and_detects_failure():
    events = [
        {"type": "turn.completed", "usage": {"input_tokens": 50, "output_tokens": 5, "cached_input_tokens": 20}},
        {"type": "item.completed", "item": {"type": "agent_message", "text": "result"}},
        {"type": "turn.completed", "usage": {"input_tokens": 70, "output_tokens": 8}},
        {"type": "turn.failed"},
    ]
    text, usage, failed = ex.parse_cli_output("codex", "\n".join(map(json.dumps, events)))
    assert (text, usage["tokens_in"], usage["tokens_out"], failed) == ("result", 120, 13, True)
    assert usage["cost_known"] is False


def test_timeout_reaps_process_and_records_attempt(tmp_path, monkeypatch):
    monkeypatch.setattr(ex.shutil, "which", lambda _: "/bin/codex")
    proc = Mock()
    proc.communicate.side_effect = [subprocess.TimeoutExpired("codex", 1), ("", "")]
    popen = Mock(return_value=proc)
    monkeypatch.setattr(ex.subprocess, "Popen", popen)
    result = ex.run_cli(ex.ExecutionSpec("codex", "gpt-5.6-sol"), "test", tmp_path, timeout=1)
    assert result.returncode == 124
    proc.kill.assert_called_once()
    assert proc.communicate.call_count == 2
    assert popen.call_count == 1
    record = json.loads(next((tmp_path / ".execution").glob("*.json")).read_text())
    assert record["model"] == "gpt-5.6-sol" and record["returncode"] == 124


def test_claude_error_envelope_fails_even_on_exit_zero(tmp_path, monkeypatch):
    monkeypatch.setattr(ex.shutil, "which", lambda _: "/bin/claude")
    proc = Mock(returncode=0)
    proc.communicate.return_value = (json.dumps({"is_error": True, "result": "budget exhausted"}), "")
    monkeypatch.setattr(ex.subprocess, "Popen", Mock(return_value=proc))
    result = ex.run_cli(ex.ExecutionSpec("claude", "claude-opus-5"), "test", tmp_path)
    assert result.returncode != 0


def test_claude_cache_creation_is_not_lost_from_usage():
    _, usage, _ = ex.parse_cli_output("claude", json.dumps({"result": "ok", "usage": {
        "input_tokens": 2, "output_tokens": 20, "cache_creation_input_tokens": 9000,
        "cache_read_input_tokens": 8000}, "total_cost_usd": .5}))
    assert usage["cache_write_tokens"] == 9000
    assert usage["cache_read_tokens"] == 8000
    assert usage["tokens_in"] == 2  # Native counters remain separate, not mixed across providers.


@pytest.mark.parametrize("isolated", [False, True])
def test_codex_config_isolation_is_opt_in_and_keeps_sandbox(tmp_path, monkeypatch, isolated):
    monkeypatch.setattr(ex.shutil, "which", lambda _: "/bin/codex")
    proc = Mock(returncode=0)
    proc.communicate.return_value = ('{"type":"turn.completed","usage":{}}', "")
    popen = Mock(return_value=proc)
    monkeypatch.setattr(ex.subprocess, "Popen", popen)
    ex.run_cli(ex.ExecutionSpec("codex", "gpt-6-astra"), "test", tmp_path,
               read_only=True, codex_ignore_user_config=isolated)
    command = popen.call_args.args[0]
    assert ("--ignore-user-config" in command) is isolated
    assert command[command.index("--sandbox") + 1] == "read-only"
    assert "--ignore-rules" not in command


def test_codex_persona_is_frozen_logged_and_safely_passed(tmp_path, monkeypatch):
    import hashlib
    monkeypatch.setattr(ex.shutil, "which", lambda _: "/bin/codex")
    proc = Mock(returncode=0)
    proc.communicate.return_value = ('{"type":"turn.completed","usage":{}}', "")
    popen = Mock(return_value=proc)
    monkeypatch.setattr(ex.subprocess, "Popen", popen)
    persona = "Narrative specialist. Do not use tools."
    result = ex.run_cli(ex.ExecutionSpec("codex", "gpt-6-astra"), "test", tmp_path / 'space and 한글',
                        read_only=True, codex_model_instructions=persona)
    assert result.returncode == 0
    command = popen.call_args.args[0]
    option = next(arg for arg in command if arg.startswith("model_instructions_file="))
    from pathlib import Path
    frozen = Path(json.loads(option.split("=", 1)[1]))
    assert frozen.read_text() == persona
    assert command[command.index("--sandbox") + 1] == "read-only"
    record = json.loads(next(frozen.parent.glob("*.json")).read_text())
    assert record["model_instructions_sha256"] == hashlib.sha256(persona.encode()).hexdigest()


def test_codex_persona_rejects_wrong_provider_without_call(tmp_path, monkeypatch):
    popen = Mock()
    monkeypatch.setattr(ex.subprocess, "Popen", popen)
    result = ex.run_cli(ex.ExecutionSpec("claude", "claude-opus-5"), "test", tmp_path,
                        codex_model_instructions="writer")
    assert result.returncode != 0
    popen.assert_not_called()


def test_artifact_index_never_replaces_original_evidence(tmp_path, monkeypatch):
    import auto_agent.orchestrator.context_memory as cm
    forbidden = Mock(side_effect=AssertionError("summary LLM must not be called"))
    monkeypatch.setattr(cm.subprocess, "run", forbidden)
    evidence = tmp_path / "research.json"
    evidence.write_text('{"source": "original"}')
    memory = ContextMemory(tmp_path)
    memory.collect_after_step("step_1", "researcher", [str(evidence)])
    assert str(evidence) in memory.build_context_prompt("step_2")
    assert not memory.has_entries_for_predecessors("step_2")
    forbidden.assert_not_called()


def test_chapter_coverage_rejects_missing_or_duplicate():
    expected = [{"sceneNumber": 1}, {"sceneNumber": 2}]
    for scenes in ([{"sceneNumber": 1}], [{"sceneNumber": 1}, {"sceneNumber": 1}]):
        with pytest.raises(ValueError):
            PipelineRunner._validate_chapter_coverage(scenes, expected)


def test_general_agent_codex_bypasses_sdk_and_does_not_fallback(tmp_path, monkeypatch):
    runner = PipelineRunner.__new__(PipelineRunner)
    runner.project_dir, runner.project_slug = tmp_path, "test"
    runner.state = SimpleNamespace(config={"execution": {"provider": "codex"}})
    runner._load_agents_config = lambda: {"subagents": {"writer": {"use_sdk": True}}}
    runner._get_agent_budget = lambda _: 3
    runner._get_agent_timeout = lambda _: 60
    runner._build_agent_prompt = lambda _: "write"
    runner._run_selected_cli = Mock(return_value=ex.ExecutionResult(1, error="no access"))
    runner._find_claude_cli = Mock(side_effect=AssertionError("no fallback"))
    result = runner._run_agent_step({"id": "step_2", "agent": "writer", "output": [], "skip_resume": True})
    assert result.status == "failed" and result.error == "no access"
    runner._find_claude_cli.assert_not_called()


def test_output_validation_rejects_corrupt_json(tmp_path):
    runner = PipelineRunner.__new__(PipelineRunner)
    runner._resolve_output_path = lambda out: tmp_path / out
    (tmp_path / "scene_specs.json").write_text("{invalid json}")
    with pytest.raises(ValueError):
        runner._validate_agent_outputs(["scene_specs.json"])


def test_dry_run_resolves_models_without_execution_or_notifications(capsys):
    runner = PipelineRunner.__new__(PipelineRunner)
    runner.state = SimpleNamespace(config={})
    runner.context_memory = SimpleNamespace(config={})
    runner.pipeline = {"phases": [{"steps": [{"id": "step_2", "agent": "writer"}]}]}
    runner._load_agents_config = lambda: {"subagents": {}}
    runner.run(dry_run=True, execution={"provider": "codex"})
    assert "codex/gpt-5.6-sol" in capsys.readouterr().out


def test_single_call_missing_output_fails_before_writing(tmp_path):
    runner = PipelineRunner.__new__(PipelineRunner)
    runner.state = SimpleNamespace(config={"execution": {"provider": "codex"}})
    runner.project_dir = tmp_path
    runner.SINGLE_CALL_PROMPTS = {}
    runner._load_agents_config = lambda: {"subagents": {}}
    runner._resolve_output_path = lambda out: tmp_path / out
    runner._build_agent_prompt = lambda step: "task"
    runner._load_agent_skill = lambda *args: ""
    runner._run_selected_cli = Mock(return_value=ex.ExecutionResult(0, text='{"files": {"a.json": {"ok": true}}}'))
    result = runner._run_single_call_step({"id": "test", "agent": "writer", "output": ["a.json", "b.json"]})
    assert result.status == "failed"
    assert not (tmp_path / "a.json").exists()


def test_summary_counts_failed_attempt_tokens(tmp_path):
    from auto_agent.scripts.summarize_execution import summarize
    logs = tmp_path / ".execution"
    logs.mkdir()
    for i, code in enumerate([0, 1]):
        (logs / f"{i}.json").write_text(json.dumps({
            "provider": "codex", "model": "gpt-5.6-sol", "profile": "balanced",
            "returncode": code, "usage": {"tokens_in": 10, "tokens_out": 3},
            "prompt_chars": 20, "duration_sec": 1,
        }))
    group = summarize(tmp_path)["groups"]["codex/gpt-5.6-sol/balanced"]
    assert group["calls"] == 2 and group["failed_calls"] == 1
    assert group["input_tokens"] == 20 and group["output_tokens"] == 6
