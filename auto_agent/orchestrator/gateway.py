"""
에이전트 감시 시스템 (규칙 기반 Gateway).

pipeline.json gateway 섹션의 detection 규칙을 Python으로 구현:
  - repetition: 동일 도구+입력 N회 연속
  - token_explosion: 단일 write > 500KB
  - no_progress: N턴 연속 read만
  - error_loop: 동일 에러 N회 반복
"""

import json
from collections import deque
from dataclasses import dataclass, field


class GatewayIntervention(Exception):
    """Gateway가 에이전트를 중단시킬 때 발생."""

    def __init__(self, reason: str, level: int = 2):
        self.reason = reason
        self.level = level  # 1=warning, 2=restart, 3=shrink, 4=skip
        super().__init__(reason)


@dataclass
class GatewayConfig:
    """pipeline.json gateway 섹션에서 로드."""

    max_consecutive_same_tool: int = 5
    max_consecutive_same_call: int = 3
    max_write_size_bytes: int = 500_000
    max_read_only_turns: int = 10
    max_consecutive_errors: int = 3


class GatewayMonitor:
    """에이전트 루프 내부에서 턴마다 호출되는 규칙 기반 감시."""

    def __init__(self, agent_name: str, config: GatewayConfig = None):
        self.agent_name = agent_name
        self.config = config or GatewayConfig()
        self.call_history: deque = deque(maxlen=50)
        self.error_history: deque = deque(maxlen=10)
        self.warnings: list = []

    def check_tool_call(
        self,
        turn: int,
        tool_name: str,
        tool_input: dict,
        tokens_in: int = 0,
        tokens_out: int = 0,
    ):
        """도구 호출 전 규칙 기반 감시. 위반 시 GatewayIntervention 발생."""
        call_sig = (
            tool_name,
            json.dumps(tool_input, sort_keys=True, ensure_ascii=False),
        )
        self.call_history.append(call_sig)

        # 규칙 1: 동일 호출 N회 연속 반복
        n = self.config.max_consecutive_same_call
        if len(self.call_history) >= n:
            recent = list(self.call_history)[-n:]
            if len(set(recent)) == 1:
                raise GatewayIntervention(
                    f"[{self.agent_name}] 동일 호출 {n}회 연속 반복: "
                    f"{tool_name}({list(tool_input.keys())})",
                    level=2,
                )

        # 규칙 2: 동일 도구 N회 연속
        n2 = self.config.max_consecutive_same_tool
        if len(self.call_history) >= n2:
            recent_tools = [c[0] for c in list(self.call_history)[-n2:]]
            if len(set(recent_tools)) == 1:
                self.warnings.append(
                    f"Turn {turn}: {tool_name} {n2}회 연속 호출"
                )

        # 규칙 3: 대용량 write 감지
        if tool_name == "write_file":
            content = tool_input.get("content", "")
            size = len(content.encode("utf-8"))
            if size > self.config.max_write_size_bytes:
                raise GatewayIntervention(
                    f"[{self.agent_name}] Token explosion: "
                    f"write_file {size:,} bytes > "
                    f"{self.config.max_write_size_bytes:,}",
                    level=3,
                )

        # 규칙 4: read만 계속 (no_progress)
        n3 = self.config.max_read_only_turns
        if len(self.call_history) >= n3:
            recent_tools = [c[0] for c in list(self.call_history)[-n3:]]
            if all(t == "read_file" for t in recent_tools):
                raise GatewayIntervention(
                    f"[{self.agent_name}] No progress: "
                    f"{n3}턴 연속 read_file만 호출",
                    level=2,
                )

    def record_error(self, error_msg: str):
        """에러 기록. 동일 에러 반복 시 GatewayIntervention."""
        self.error_history.append(error_msg)
        n = self.config.max_consecutive_errors
        if len(self.error_history) >= n:
            recent = list(self.error_history)[-n:]
            if len(set(recent)) == 1:
                raise GatewayIntervention(
                    f"[{self.agent_name}] Error loop: "
                    f"동일 에러 {n}회 반복 -- {error_msg[:100]}",
                    level=4,
                )
