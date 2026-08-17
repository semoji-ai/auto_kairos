"""claude 웹리서치 러너 — `claude -p --allowedTools WebSearch,WebFetch`로 웹 노트 생성.
중첩 env 제거(안 하면 claude -p 행). 실패/타임아웃 → "" (부분 실패 격리)."""
from __future__ import annotations

import os
import subprocess

_NEST_ENV = ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SSE_PORT")


def run_web_research(cwd, prompt: str, *, on_line=None, timeout: int = 600) -> str:
    """프롬프트로 claude 웹리서치 1회 → 노트 텍스트. 실패 시 ""."""
    claude_bin = os.environ.get("CLAUDE_CLI_BIN", "claude")
    env = {k: v for k, v in os.environ.items() if k not in _NEST_ENV}
    cmd = [claude_bin, "-p", "--output-format", "text",
           "--allowedTools", "WebSearch,WebFetch"]
    try:
        r = subprocess.run(cmd, input=prompt, cwd=str(cwd), capture_output=True,
                           text=True, timeout=timeout, env=env)
    except Exception as e:  # noqa: BLE001 — 타임아웃/실행오류 모두 격리
        if on_line:
            on_line(f"웹리서치 실패: {e}")
        return ""
    if r.returncode != 0:
        if on_line:
            on_line(f"웹리서치 rc={r.returncode}: {(r.stderr or '')[:150]}")
        return ""
    return (r.stdout or "").strip()
