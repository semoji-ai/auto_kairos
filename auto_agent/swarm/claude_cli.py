"""Claude CLI subprocess wrapper — swarm agent가 single-shot으로 호출.

핵심:
- single-shot mode (`claude --print --output-format json`)
- 각 호출 stateless — 모든 컨텍스트는 prompt에 포함
- asyncio.Semaphore로 동시 호출 제한 (rate limit 대응)
- timeout + retry
- JSON 출력 파싱
- cost/token 통계 추출
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── 글로벌 semaphore (모든 swarm agent가 공유) ──
# 환경변수 SWARM_MAX_PARALLEL로 조정 가능
# Claude Max200 ($200) 기준 8 제안. 다른 플랜은 조정.
_DEFAULT_MAX_PARALLEL = int(os.environ.get("SWARM_MAX_PARALLEL", "8"))
_global_semaphore: Optional[asyncio.Semaphore] = None


def get_semaphore() -> asyncio.Semaphore:
    """프로세스 전역 semaphore. 모든 swarm agent가 같은 instance 공유."""
    global _global_semaphore
    if _global_semaphore is None:
        _global_semaphore = asyncio.Semaphore(_DEFAULT_MAX_PARALLEL)
        logger.info("Swarm CLI semaphore initialized: max_parallel=%d", _DEFAULT_MAX_PARALLEL)
    return _global_semaphore


def find_claude_cli() -> str:
    """Claude CLI 바이너리 경로 탐색."""
    env_cli = os.environ.get("CLAUDE_CLI")
    if env_cli and Path(env_cli).exists():
        return env_cli
    result = shutil.which("claude")
    if result:
        return result
    candidate = Path.home() / ".local" / "bin" / "claude"
    if candidate.exists():
        return str(candidate)
    raise FileNotFoundError("claude CLI not found. Set CLAUDE_CLI env var.")


# ── Result data class (light) ──

class ClaudeCLIResult:
    """Claude CLI 호출 결과."""

    def __init__(
        self,
        success: bool,
        text: str,
        cost_usd: float = 0.0,
        tokens_in: int = 0,
        tokens_out: int = 0,
        elapsed_sec: float = 0.0,
        error: str = "",
        raw_stdout: str = "",
    ):
        self.success = success
        self.text = text
        self.cost_usd = cost_usd
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.elapsed_sec = elapsed_sec
        self.error = error
        self.raw_stdout = raw_stdout

    def __repr__(self) -> str:
        return (
            f"ClaudeCLIResult(success={self.success}, "
            f"len={len(self.text)}, cost=${self.cost_usd:.4f}, "
            f"in={self.tokens_in}, out={self.tokens_out}, "
            f"elapsed={self.elapsed_sec:.1f}s)"
        )


def _parse_cli_json(stdout: str) -> Dict[str, Any]:
    """Claude CLI --output-format json 파싱."""
    # Claude CLI는 한 줄 JSON 또는 멀티 라인 JSON을 출력
    stdout = stdout.strip()
    if not stdout:
        return {}
    # 첫 줄이 JSON이면 그대로
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        pass
    # 마지막 JSON 객체 추출 시도
    matches = re.findall(r'\{.*\}', stdout, re.DOTALL)
    if matches:
        try:
            return json.loads(matches[-1])
        except json.JSONDecodeError:
            pass
    return {"raw_text": stdout}


async def call_claude_cli(
    prompt: str,
    *,
    model: str = "default",
    allowed_tools: Optional[List[str]] = None,
    max_turns: int = 30,
    timeout_sec: int = 600,
    project_dir: Optional[Path] = None,
    env_extra: Optional[Dict[str, str]] = None,
    cli_path: Optional[str] = None,
) -> ClaudeCLIResult:
    """Claude CLI를 single-shot으로 호출 (semaphore 보호).

    Args:
        prompt: 전체 prompt (system context + skill + task 모두 포함된 문자열)
        model: 모델 이름 또는 alias ("default", "claude-opus-4-6", "claude-sonnet-4-6")
        allowed_tools: 허용 도구 목록 (Read/Write/Bash/WebSearch 등)
        max_turns: 최대 turn 수
        timeout_sec: 호출 timeout
        project_dir: cwd로 사용할 디렉토리
        env_extra: 추가 환경 변수

    Returns:
        ClaudeCLIResult — success/text/cost/tokens
    """
    import time

    cli = cli_path or find_claude_cli()
    cmd = [
        cli,
        "--print",
        "--output-format", "json",
        "--model", model,
        "--max-turns", str(max_turns),
    ]
    if allowed_tools:
        for t in allowed_tools:
            cmd.extend(["--allowedTools", t])
    cmd.append("--dangerously-skip-permissions")  # swarm은 자동 실행

    env = os.environ.copy()
    env.pop("CLAUDECODE", None)  # 중첩 세션 방지
    if env_extra:
        env.update(env_extra)

    cwd = str(project_dir) if project_dir else None

    sem = get_semaphore()
    async with sem:
        start = time.time()
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(input=prompt.encode("utf-8")),
                    timeout=timeout_sec,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                return ClaudeCLIResult(
                    success=False,
                    text="",
                    error=f"timeout after {timeout_sec}s",
                    elapsed_sec=time.time() - start,
                )

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            elapsed = time.time() - start

            if proc.returncode != 0:
                return ClaudeCLIResult(
                    success=False,
                    text="",
                    error=f"exit {proc.returncode}: {stderr[:500]}",
                    raw_stdout=stdout,
                    elapsed_sec=elapsed,
                )

            parsed = _parse_cli_json(stdout)
            text = (
                parsed.get("result")
                or parsed.get("response")
                or parsed.get("text")
                or parsed.get("raw_text", "")
            )
            usage = parsed.get("usage", {}) or {}
            return ClaudeCLIResult(
                success=True,
                text=text,
                cost_usd=parsed.get("cost_usd", 0.0) or parsed.get("total_cost_usd", 0.0),
                tokens_in=usage.get("input_tokens", 0),
                tokens_out=usage.get("output_tokens", 0),
                elapsed_sec=elapsed,
                raw_stdout=stdout,
            )
        except Exception as e:
            return ClaudeCLIResult(
                success=False,
                text="",
                error=f"{type(e).__name__}: {e}",
                elapsed_sec=time.time() - start,
            )


async def call_claude_cli_with_retry(
    prompt: str,
    *,
    max_retries: int = 2,
    backoff_sec: float = 5.0,
    **kwargs: Any,
) -> ClaudeCLIResult:
    """retry + exponential backoff. timeout이나 transient error 대응."""
    last_result: Optional[ClaudeCLIResult] = None
    for attempt in range(max_retries + 1):
        result = await call_claude_cli(prompt, **kwargs)
        if result.success:
            return result
        last_result = result
        # rate limit 또는 timeout만 retry. 다른 에러는 즉시 실패.
        is_retryable = (
            "timeout" in result.error.lower()
            or "rate limit" in result.error.lower()
            or "429" in result.error
        )
        if not is_retryable:
            return result
        if attempt < max_retries:
            wait = backoff_sec * (2 ** attempt)
            logger.warning("CLI retry %d/%d after %.1fs: %s", attempt + 1, max_retries, wait, result.error)
            await asyncio.sleep(wait)
    return last_result or ClaudeCLIResult(success=False, text="", error="unknown")
