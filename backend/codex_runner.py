"""codex exec 래퍼 — 커맨드 빌드(순수) + 스킬 실행(subprocess, stdin 프롬프트 + 스트리밍)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def build_codex_cmd(
    *,
    session_id: str | None = None,
    output_schema: str | None = None,
    output_last: str | None = None,
    json_events: bool = True,
    skip_git: bool = True,
    sandbox: str | None = None,
    images: list | None = None,
) -> list[str]:
    """codex exec 커맨드 리스트. 프롬프트는 stdin으로 넘기므로 positional은 '-'.
    session_id 있으면 resume."""
    cmd = ["codex", "exec"]
    if session_id:
        cmd += ["resume", session_id]
    if sandbox:
        cmd += ["-s", sandbox]
    if images:
        for img in images:
            cmd += ["-i", img]
    if skip_git:
        cmd += ["--skip-git-repo-check"]
    if json_events:
        cmd += ["--json"]
    if output_schema:
        cmd += ["--output-schema", output_schema]
    if output_last:
        cmd += ["-o", output_last]
    cmd += ["-"]  # 프롬프트는 stdin (긴/'--'로 시작하는 프롬프트 안전)
    return cmd


def _extract_session_id(json_line: str) -> str | None:
    try:
        evt = json.loads(json_line)
    except ValueError:
        return None
    if isinstance(evt, dict):
        for key in ("session_id", "sessionId", "conversation_id", "thread_id"):
            if evt.get(key):
                return str(evt[key])
    return None


def run_skill(
    prompt: str,
    cwd: Path,
    *,
    session_id: str | None = None,
    output_schema: str | None = None,
    output_last: str | None = None,
    sandbox: str | None = None,
    images: list | None = None,
    on_line=None,
) -> dict:
    """codex exec 실행. 프롬프트는 stdin으로 전달. 각 stdout 라인을 on_line(line)으로 흘림.
    반환: {returncode, session_id, output_last}."""
    cmd = build_codex_cmd(
        session_id=session_id, output_schema=output_schema,
        output_last=output_last, sandbox=sandbox, images=images,
    )
    proc = subprocess.Popen(
        cmd, cwd=str(cwd),
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", bufsize=1,
    )
    try:
        if proc.stdin is not None:
            proc.stdin.write(prompt)
            proc.stdin.close()
    except BrokenPipeError:
        pass
    found_session = session_id
    if proc.stdout is not None:
        for line in proc.stdout:
            line = line.rstrip("\n")
            if on_line:
                on_line(line)
            if found_session is None:
                sid = _extract_session_id(line)
                if sid:
                    found_session = sid
    proc.wait()
    return {
        "returncode": proc.returncode,
        "session_id": found_session,
        "output_last": output_last,
    }
