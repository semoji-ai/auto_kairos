"""
Anthropic API 기반 에이전트 루프.

역할:
  - messages.create() 반복 호출로 tool_use 대화 루프 실행
  - 턴별 비용 추적
  - Gateway 감시 통합
  - 콜백 지원 (로깅/대시보드)
"""

import time
from dataclasses import dataclass, field
from typing import Callable, Optional

import anthropic

from .gateway import GatewayIntervention, GatewayMonitor
from .tools import ToolExecutor, filter_tools_for_agent


@dataclass
class AgentResult:
    """에이전트 루프 실행 결과."""

    status: str  # "completed", "failed", "gateway_stopped"
    turns_used: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    cost_usd: float = 0.0
    error: str = ""
    final_text: str = ""


@dataclass
class AgentConfig:
    """에이전트 실행 설정."""

    model: str = "claude-sonnet-4-5-20250929"
    max_turns: int = 30
    max_tokens_per_turn: int = 16384
    budget_usd: float = 3.0
    timeout_sec: int = 900
    allowed_tools: list = field(
        default_factory=lambda: ["Read", "Write", "Glob"]
    )
    system_prompt: Optional[str] = None


class AgentLoop:
    """Anthropic API tool_use 기반 에이전트 루프."""

    PRICING = {
        "opus": {"input": 15.0, "output": 75.0},
        "sonnet": {"input": 3.0, "output": 15.0},
        "haiku": {"input": 0.8, "output": 4.0},
    }

    def __init__(
        self,
        tool_executor: ToolExecutor,
        gateway: Optional[GatewayMonitor] = None,
        on_turn: Optional[Callable] = None,
        on_tool_call: Optional[Callable] = None,
    ):
        self.client = anthropic.Anthropic()
        self.tool_executor = tool_executor
        self.gateway = gateway
        self.on_turn = on_turn
        self.on_tool_call = on_tool_call

    def run(self, config: AgentConfig, prompt: str) -> AgentResult:
        """에이전트 루프 실행.

        1. prompt를 user 메시지로 전송
        2. tool_use 응답 -> 도구 실행 -> 결과 반환 -> 반복
        3. end_turn -> 완료
        4. 매 턴 gateway 감시 + 예산 체크
        """
        tools = filter_tools_for_agent(config.allowed_tools)
        messages = [{"role": "user", "content": prompt}]

        # 시스템 프롬프트 (프롬프트 캐싱 적용)
        system = None
        if config.system_prompt:
            system = [
                {
                    "type": "text",
                    "text": config.system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ]

        total_in = 0
        total_out = 0
        turn = 0
        start_time = time.time()

        while turn < config.max_turns:
            turn += 1

            # 타임아웃 체크
            elapsed = time.time() - start_time
            if elapsed > config.timeout_sec:
                return AgentResult(
                    status="failed",
                    turns_used=turn,
                    total_input_tokens=total_in,
                    total_output_tokens=total_out,
                    cost_usd=self._calc_cost(total_in, total_out, config.model),
                    error=f"Timeout: {elapsed:.0f}s > {config.timeout_sec}s",
                )

            # API 호출
            try:
                create_kwargs = {
                    "model": config.model,
                    "max_tokens": config.max_tokens_per_turn,
                    "messages": messages,
                }
                if system:
                    create_kwargs["system"] = system
                if tools:
                    create_kwargs["tools"] = tools
                response = self.client.messages.create(**create_kwargs)
            except anthropic.APIError as e:
                return AgentResult(
                    status="failed",
                    turns_used=turn,
                    total_input_tokens=total_in,
                    total_output_tokens=total_out,
                    error=f"API error: {e}",
                )

            # 토큰 추적
            total_in += response.usage.input_tokens
            total_out += response.usage.output_tokens
            cost = self._calc_cost(total_in, total_out, config.model)

            # 턴 콜백
            if self.on_turn:
                self.on_turn(turn, response, cost)

            # 예산 초과 체크
            if config.budget_usd > 0 and cost > config.budget_usd:
                return AgentResult(
                    status="failed",
                    turns_used=turn,
                    total_input_tokens=total_in,
                    total_output_tokens=total_out,
                    cost_usd=cost,
                    error=f"Budget exceeded: ${cost:.4f} > ${config.budget_usd}",
                )

            # stop_reason 분기

            # Case 1: 작업 완료
            if response.stop_reason == "end_turn":
                final_text = ""
                for block in response.content:
                    if block.type == "text":
                        final_text += block.text
                return AgentResult(
                    status="completed",
                    turns_used=turn,
                    total_input_tokens=total_in,
                    total_output_tokens=total_out,
                    cost_usd=cost,
                    final_text=final_text,
                )

            # Case 2: 도구 사용 요청
            if response.stop_reason == "tool_use":
                messages.append(
                    {"role": "assistant", "content": response.content}
                )

                tool_results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue

                    # Gateway 감시 (도구 실행 전)
                    if self.gateway:
                        try:
                            self.gateway.check_tool_call(
                                turn=turn,
                                tool_name=block.name,
                                tool_input=block.input,
                                tokens_in=total_in,
                                tokens_out=total_out,
                            )
                        except GatewayIntervention as e:
                            return AgentResult(
                                status="gateway_stopped",
                                turns_used=turn,
                                total_input_tokens=total_in,
                                total_output_tokens=total_out,
                                cost_usd=cost,
                                error=str(e),
                            )

                    # 도구 실행 콜백
                    if self.on_tool_call:
                        self.on_tool_call(turn, block.name, block.input)

                    # 실제 실행
                    try:
                        result_text = self.tool_executor.execute(
                            block.name, block.input
                        )
                    except PermissionError as e:
                        result_text = f"ERROR: {e}"
                    except Exception as e:
                        result_text = (
                            f"ERROR: 도구 실행 실패 -- "
                            f"{type(e).__name__}: {e}"
                        )

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_text,
                        }
                    )

                messages.append({"role": "user", "content": tool_results})
                continue

            # Case 3: max_tokens 도달 (응답 잘림)
            if response.stop_reason == "max_tokens":
                messages.append(
                    {"role": "assistant", "content": response.content}
                )
                messages.append(
                    {"role": "user", "content": "계속하세요."}
                )
                continue

            # Case 4: 예상치 못한 stop_reason
            return AgentResult(
                status="failed",
                turns_used=turn,
                total_input_tokens=total_in,
                total_output_tokens=total_out,
                cost_usd=cost,
                error=f"Unexpected stop_reason: {response.stop_reason}",
            )

        # max_turns 초과
        return AgentResult(
            status="failed",
            turns_used=turn,
            total_input_tokens=total_in,
            total_output_tokens=total_out,
            cost_usd=self._calc_cost(total_in, total_out, config.model),
            error=f"Max turns exceeded: {turn}/{config.max_turns}",
        )

    @staticmethod
    def _calc_cost(tokens_in: int, tokens_out: int, model: str) -> float:
        """모델별 비용 계산 (USD)."""
        model_lower = model.lower()
        for key, prices in AgentLoop.PRICING.items():
            if key in model_lower:
                return (
                    tokens_in * prices["input"]
                    + tokens_out * prices["output"]
                ) / 1_000_000
        return (tokens_in * 3.0 + tokens_out * 15.0) / 1_000_000
