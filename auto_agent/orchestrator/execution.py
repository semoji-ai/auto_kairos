"""Provider-neutral CLI execution and explicit, reproducible model profiles.

No API credentials, fallback, or model calls occur during resolution.
"""
from __future__ import annotations

import json
import hashlib
import os
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from auto_agent.utils.codex_cli import build_codex_exec_cmd
from auto_agent.utils.platform import subprocess_kwargs

PROFILES = {
    "balanced": {"claude": "claude-opus-5", "codex": "gpt-5.6-sol"},
    "quality": {"claude": "claude-fable-5-1", "codex": "gpt-6-astra"},
}


def execution_options(config: dict, agent: str = "", step: dict | None = None) -> dict:
    options = dict(config.get("execution", {}))
    overrides = options.pop("agents", {})
    options.update(overrides.get(agent, {}))
    options.update((step or {}).get("execution", {}))
    return options


def execution_profile(config: dict) -> str:
    profile = execution_options(config).get("profile", os.getenv("AUTO_AGENT_EXECUTION_PROFILE", "balanced"))
    if profile not in {"legacy", *PROFILES}:
        raise ValueError(f"Unknown execution profile: {profile}")
    return profile


def resolve_provider(agent: str, agent_def: dict, config: dict, step: dict | None = None) -> str:
    options = execution_options(config, agent, step)
    research = agent in {"flesh-researcher", "targeted-researcher"}
    candidates = [options.get("provider"), os.getenv("AUTO_AGENT_PROVIDER")]
    if research:
        candidates += [config.get("research_provider"), os.getenv("AUTO_AGENT_RESEARCH_PROVIDER")]
    candidates += [agent_def.get("provider"), "claude"]
    for value in candidates:
        if value is not None:
            provider = str(value).strip().lower()
            if provider not in {"claude", "codex"}:
                raise ValueError(f"Unknown provider for {agent}: {value}")
            return provider
    return "claude"


@dataclass(frozen=True)
class ExecutionSpec:
    provider: str
    model: str
    profile: str = "balanced"
    reasoning_effort: str = "medium"


def resolve_execution(agent: str, agent_def: dict, config: dict, step: dict | None = None) -> ExecutionSpec:
    options = execution_options(config, agent, step)
    profile = options.get("profile", execution_profile(config))
    if profile not in {"legacy", *PROFILES}:
        raise ValueError(f"Unknown execution profile: {profile}")
    provider = resolve_provider(agent, agent_def, config, step)
    model = options.get("model") or options.get("models", {}).get(provider)
    model = model or os.getenv(f"AUTO_AGENT_{provider.upper()}_MODEL")
    if not model:
        if profile == "legacy":
            model = agent_def.get("codex_model", "gpt-5.6-sol") if provider == "codex" else (
                (step or {}).get("model") or (step or {}).get("single_call_model") or agent_def.get("model", "sonnet"))
        else:
            model = PROFILES[profile][provider]
    if provider == "codex" and (str(model).startswith("claude-") or model in {"opus", "sonnet", "haiku"}):
        raise ValueError(f"Claude model cannot run on Codex: {model}")
    if provider == "claude" and str(model).startswith("gpt-"):
        raise ValueError(f"Codex model cannot run on Claude: {model}")
    effort = options.get("reasoning_effort", "high" if profile == "quality" else "medium")
    if effort not in {"low", "medium", "high", "xhigh", "max"}:
        raise ValueError(f"Unknown reasoning effort: {effort}")
    return ExecutionSpec(provider, str(model), profile, effort)


@dataclass
class ExecutionResult:
    returncode: int
    text: str = ""
    error: str = ""
    usage: dict = field(default_factory=dict)
    duration_sec: float = 0


def parse_cli_output(provider: str, stdout: str) -> tuple[str, dict, bool]:
    usage = {"tokens_in": 0, "tokens_out": 0, "cache_read_tokens": 0, "cost_usd": 0.0}
    if provider == "claude":
        try:
            data = json.loads(stdout)
            raw = data.get("usage", {})
            usage.update(tokens_in=raw.get("input_tokens", 0), tokens_out=raw.get("output_tokens", 0),
                         cache_read_tokens=raw.get("cache_read_input_tokens", 0),
                         cache_write_tokens=raw.get("cache_creation_input_tokens", 0),
                         cost_usd=data.get("total_cost_usd", 0.0))
            return data.get("result", stdout), usage, bool(data.get("is_error"))
        except (ValueError, AttributeError):
            return stdout, usage, True
    messages = []
    failed = False
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") in {"error", "turn.failed"}:
            failed = True
        if event.get("type") == "turn.completed":
            raw = event.get("usage", {})
            usage["tokens_in"] += raw.get("input_tokens", 0)
            usage["tokens_out"] += raw.get("output_tokens", 0)
            usage["cache_read_tokens"] += raw.get("cached_input_tokens", 0)
        item = event.get("item", {})
        if event.get("type") == "item.completed" and item.get("type") == "agent_message":
            messages.append(item.get("text", ""))
    # CLI subscriptions do not expose a dollar bill; zero is not a cost estimate.
    usage["cost_known"] = False
    return "\n".join(messages), usage, failed


def run_cli(spec: ExecutionSpec, prompt: str, workdir: Path, *, timeout: int = 900,
            max_turns: int = 30, allowed_tools: list | None = None,
            env: dict | None = None, read_only: bool = False, label: str = "agent",
            codex_ignore_user_config: bool = False,
            codex_model_instructions: str | None = None,
            system_prompt_file: Path | None = None) -> ExecutionResult:
    """Run once; retries belong to the caller. Keep a separate usage record per attempt."""
    workdir = Path(workdir)
    run_id = uuid.uuid4().hex
    record_dir = workdir / ".execution"
    record_dir.mkdir(parents=True, exist_ok=True)
    last = record_dir / f"{run_id}.last.txt"
    started = time.monotonic()
    proc = None
    try:
        if codex_model_instructions is not None and spec.provider != "codex":
            raise ValueError("Custom Codex model instructions require the Codex provider")
        if spec.provider == "codex":
            if system_prompt_file is not None:
                prompt = Path(system_prompt_file).read_text(encoding="utf-8") + "\n\n" + prompt
            cmd = build_codex_exec_cmd(workdir=workdir, output_last_message=str(last),
                                      model=spec.model, reasoning_effort=spec.reasoning_effort,
                                      search=any(t in {"WebSearch", "WebFetch"} for t in (allowed_tools or [])),
                                      sandbox="read-only" if read_only else "workspace-write")
            if codex_ignore_user_config:
                cmd.insert(2, "--ignore-user-config")
            if codex_model_instructions is not None:
                if not codex_model_instructions.strip():
                    raise ValueError("Custom model instructions must not be empty")
                instructions_path = record_dir / f"{run_id}.instructions.md"
                instructions_path.write_text(codex_model_instructions, encoding="utf-8")
                cmd += ["-c", "model_instructions_file=" + json.dumps(str(instructions_path.resolve()))]
        else:
            cli = os.getenv("CLAUDE_CLI") or shutil.which("claude")
            if not cli:
                raise FileNotFoundError("Claude CLI not found")
            cmd = [cli, "--print", "--output-format", "json", "--model", spec.model,
                   "--max-turns", str(max_turns), "--permission-mode", "acceptEdits"]
            if spec.profile != "legacy":
                cmd += ["--effort", spec.reasoning_effort]
            if system_prompt_file is not None:
                cmd += ["--append-system-prompt-file", str(system_prompt_file)]
            if read_only:
                cmd += ["--tools", ""]
            else:
                for tool in allowed_tools or ["Read", "Write", "Edit", "Glob"]:
                    cmd += ["--allowedTools", tool]
        child_env = dict(env if env is not None else os.environ)
        child_env.pop("CLAUDECODE", None)
        proc = subprocess.Popen(cmd, cwd=str(workdir), env=child_env, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                encoding="utf-8", **subprocess_kwargs())
        stdout, stderr = proc.communicate(input=prompt, timeout=timeout)
        text, usage, failed = parse_cli_output(spec.provider, stdout)
        if spec.provider == "codex" and last.exists():
            text = last.read_text(encoding="utf-8") or text
        result = ExecutionResult(proc.returncode or (1 if failed else 0), text,
                                 (stderr or text)[-2000:] if proc.returncode or failed else "", usage)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, _ = proc.communicate()
        _, usage, _ = parse_cli_output(spec.provider, stdout)
        result = ExecutionResult(124, error=f"CLI timeout ({timeout}s)", usage=usage)
    except (OSError, ValueError) as exc:
        result = ExecutionResult(1, error=str(exc))
    result.duration_sec = time.monotonic() - started
    record = {"run_id": run_id, "label": label, "provider": spec.provider, "model": spec.model,
              "profile": spec.profile, "reasoning_effort": spec.reasoning_effort,
              "codex_ignore_user_config": codex_ignore_user_config if spec.provider == "codex" else False,
              "model_instructions_sha256": hashlib.sha256(codex_model_instructions.encode()).hexdigest()
                  if codex_model_instructions is not None else None,
              "prompt_chars": len(prompt), "duration_sec": result.duration_sec,
              "returncode": result.returncode, "usage": result.usage}
    (record_dir / f"{run_id}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
