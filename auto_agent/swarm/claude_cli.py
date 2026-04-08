"""Claude CLI subprocess wrapper — swarm agent가 single-shot으로 호출.

핵심:
- single-shot mode (`claude --print --output-format json`)
- 각 호출 stateless — 모든 컨텍스트는 prompt에 포함
- asyncio.Semaphore로 동시 호출 제한 (rate limit 대응)
- timeout + retry
- JSON 출력 파싱
- cost/token 통계 추출

⚠️ 2026-04-08: subprocess 호출은 sync subprocess.run을 asyncio.to_thread로 감싸 사용.
이전에는 asyncio.create_subprocess_exec을 사용했으나 Python 3.9 + macOS에서
큰 prompt + max_turns 높은 케이스에서 stdin/stdout PIPE 데드락이 재현되었음
(writer가 1.9~180s 사이에 exit 1로 죽는 패턴). subprocess.run은 OS-level pipe
draining을 안전하게 처리해서 같은 호출이 정상 동작.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── 글로벌 semaphore (모든 swarm agent가 공유) ──
# 환경변수 SWARM_MAX_PARALLEL로 조정 가능.
#
# 2026-04-08: 8 → 3 으로 하향 조정.
# 이유: Anthropic API 529 Overloaded 에러가 5+ 동시 호출에서 빈번 발생.
# Web search heavy query는 inference 시간이 길어 동시 호출 부하가 매우 큼.
# Claude Max200 ($200) 플랜에서도 5명 동시 webfetch는 부하 → 3 권장.
# 더 늘리려면 환경변수 SWARM_MAX_PARALLEL=N 사용.
_DEFAULT_MAX_PARALLEL = int(os.environ.get("SWARM_MAX_PARALLEL", "3"))
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
            # 2026-04-08: asyncio.create_subprocess_exec → subprocess.run via to_thread.
            # asyncio + PIPE 조합이 큰 prompt에서 stdin/stdout 데드락을 일으켜
            # writer가 1.9~180s 안에 즉시 fail하던 문제 fix.
            def _run_sync() -> subprocess.CompletedProcess:
                return subprocess.run(
                    cmd,
                    input=prompt.encode("utf-8"),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=cwd,
                    env=env,
                    timeout=timeout_sec,
                    check=False,
                )

            try:
                completed = await asyncio.to_thread(_run_sync)
            except subprocess.TimeoutExpired:
                return ClaudeCLIResult(
                    success=False,
                    text="",
                    error=f"timeout after {timeout_sec}s",
                    elapsed_sec=time.time() - start,
                )

            stdout = completed.stdout.decode("utf-8", errors="replace") if completed.stdout else ""
            stderr = completed.stderr.decode("utf-8", errors="replace") if completed.stderr else ""
            elapsed = time.time() - start

            if completed.returncode != 0:
                return ClaudeCLIResult(
                    success=False,
                    text="",
                    error=f"exit {completed.returncode}: {stderr[:500]}",
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

            # ⚠️ 핵심: claude CLI는 returncode 0으로 종료해도 stdout JSON에
            # is_error: true가 들어올 수 있음. 이 케이스는 진짜 실패.
            # 예: API Error 529 Overloaded → claude CLI는 정상 종료처럼 보이지만
            #     result 필드에 에러 메시지가 들어있고 num_turns=1이며 비용 0.
            is_api_error = bool(parsed.get("is_error", False))
            if is_api_error:
                # API 에러 텍스트를 error 필드로 노출 → retry 판단에 사용
                error_text = text[:500] if text else "is_error=true (no message)"
                return ClaudeCLIResult(
                    success=False,
                    text="",
                    error=f"api_error: {error_text}",
                    raw_stdout=stdout,
                    elapsed_sec=elapsed,
                    cost_usd=parsed.get("total_cost_usd", 0.0),
                )

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


# ── Sonnet → Opus 자동 전환 (model overload 회피) ──
#
# 2026-04-08: Anthropic sonnet 서버 overload 패턴 (220초 후 529)이 빈번해서
# sonnet 호출이 retryable error를 1번이라도 만나면 다음 retry부터는 opus로 전환.
# 한 swarm run 안에서 overload를 한 번 만난 모델은 잠시 "기피 모델"로 마킹되어
# 같은 retry 사이클 내에서 재시도하지 않음.
#
# 사용자가 명시적으로 model을 지정한 경우에도 overload면 fallback 우선.
# fallback 후에도 실패하면 최종 결과 반환.
SONNET_ALIASES = {
    "claude-sonnet-4-6",
    "claude-sonnet-4-5",
    "sonnet",
}
OPUS_FALLBACK_MODEL = "claude-opus-4-6"


def _is_sonnet(model: str) -> bool:
    m = model.lower()
    return any(alias in m for alias in SONNET_ALIASES)


def _is_overload_retryable(error: str) -> bool:
    """retryable + overload-class 에러인지 (model fallback 트리거 조건)."""
    err_lower = error.lower()
    return (
        "timeout" in err_lower
        or "529" in err_lower
        or "overloaded" in err_lower
        or "503" in err_lower
        or "500 " in err_lower
        or "service unavailable" in err_lower
    )


async def call_claude_cli_with_retry(
    prompt: str,
    *,
    max_retries: int = 2,
    backoff_sec: float = 30.0,
    enable_model_fallback: bool = True,
    fallback_model: str = OPUS_FALLBACK_MODEL,
    **kwargs: Any,
) -> ClaudeCLIResult:
    """retry + exponential backoff + model fallback.

    timeout / rate limit / API overload 대응:
    - retryable 에러는 backoff 후 재시도 (최대 max_retries회)
    - sonnet에서 overload-class 에러가 발생하면 다음 시도부터 opus로 전환
      (enable_model_fallback=True일 때)

    fallback_model: sonnet overload 시 전환할 대체 모델 (기본 opus-4-6).
    enable_model_fallback=False면 동일 모델로만 재시도.
    """
    current_model = kwargs.get("model", "default")
    swapped = False  # 한 번 swap한 후에는 다시 원래 모델로 돌아가지 않음
    last_result: Optional[ClaudeCLIResult] = None
    for attempt in range(max_retries + 1):
        result = await call_claude_cli(prompt, **kwargs)
        if result.success:
            if swapped:
                logger.info(
                    "CLI fallback success: model=%s (original sonnet → opus)",
                    kwargs.get("model"),
                )
            return result
        last_result = result
        # 다음 에러는 모두 retry 대상:
        #   - timeout
        #   - rate limit / 429
        #   - api_error: ... 529 / overloaded / overloaded_error
        #   - api_error: ... 503 (service unavailable)
        #   - api_error: ... 500 (internal server error)
        err_lower = result.error.lower()
        is_retryable = (
            "timeout" in err_lower
            or "rate limit" in err_lower
            or "429" in err_lower
            or "529" in err_lower
            or "overloaded" in err_lower
            or "503" in err_lower
            or "500 " in err_lower
            or "service unavailable" in err_lower
            or err_lower.startswith("api_error:")
        )
        if not is_retryable:
            return result

        # ── Model fallback 판단 ──
        # sonnet에서 overload-class 에러가 났고 아직 swap 안 했으면 다음 시도부터 opus
        if (
            enable_model_fallback
            and not swapped
            and _is_sonnet(current_model)
            and _is_overload_retryable(result.error)
        ):
            logger.warning(
                "CLI model fallback: %s → %s (overload error: %s)",
                current_model, fallback_model, result.error[:200]
            )
            kwargs["model"] = fallback_model
            current_model = fallback_model
            swapped = True
            # backoff 짧게 (다른 모델이라 즉시 재시도해도 OK)
            if attempt < max_retries:
                await asyncio.sleep(2.0)
                continue

        if attempt < max_retries:
            wait = backoff_sec * (2 ** attempt)
            logger.warning(
                "CLI retry %d/%d after %.1fs (model=%s): %s",
                attempt + 1, max_retries, wait, current_model, result.error[:200]
            )
            await asyncio.sleep(wait)
    return last_result or ClaudeCLIResult(success=False, text="", error="unknown")
