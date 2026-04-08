"""BaseAgent — swarm worker의 추상 클래스.

각 worker는 long-running async loop:
1. workspace tail (event log + queue 등) → 자기 작업 발견
2. context 추출 → claude CLI single-shot 호출
3. 결과 → workspace에 통합 (atomic)
4. log emit
5. repeat

종료 조건: workspace.meta status가 "done" 또는 timeout.
"""
from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from .workspace import SwarmWorkspace

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """추상 base class. 구체 agent는 step() 메서드만 구현하면 됨."""

    def __init__(
        self,
        agent_id: str,
        role: str,
        workspace: SwarmWorkspace,
        *,
        idle_sec: float = 2.0,
        max_iterations: int = 100,
    ):
        self.agent_id = agent_id  # 예: "writer", "R1", "R2", "miner_1"
        self.role = role  # 예: "writer", "researcher", "episode_miner"
        self.workspace = workspace
        self.idle_sec = idle_sec
        self.max_iterations = max_iterations
        self._stopped = False
        self._iter = 0

    @abstractmethod
    async def step(self) -> bool:
        """한 turn의 작업.

        Returns:
            True — 작업했음 (즉시 다음 step)
            False — 할 일 없음 (idle_sec 대기)
        """
        ...

    def stop(self) -> None:
        """외부 (orchestrator)에서 종료 신호."""
        self._stopped = True

    def is_done(self) -> bool:
        """workspace meta가 'done' 상태인지 확인."""
        meta = self.workspace.read_json("meta.json", default={})
        return meta.get("status") in ("done", "stopped", "failed")

    async def run(self) -> None:
        """worker 메인 루프. orchestrator가 이걸 asyncio.create_task로 감쌈."""
        self.workspace.emit_event(self.agent_id, "agent_started", role=self.role)
        try:
            while not self._stopped and self._iter < self.max_iterations:
                if self.is_done():
                    break
                try:
                    worked = await self.step()
                except Exception as e:
                    logger.exception("Agent %s step error", self.agent_id)
                    self.workspace.emit_event(
                        self.agent_id, "step_error",
                        level="warning",
                        error=f"{type(e).__name__}: {e}",
                    )
                    worked = False
                self._iter += 1
                if not worked:
                    await asyncio.sleep(self.idle_sec)
        finally:
            self.workspace.emit_event(
                self.agent_id, "agent_stopped",
                iterations=self._iter,
            )
