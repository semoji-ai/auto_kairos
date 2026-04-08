"""SkeletonIdentifyAgent — swarm Phase 1 (sequential setup).

skeleton 조사 + 매력 포인트 식별 + outline + research_targets 작성을
단일 호출로 수행.

이 agent는 swarm의 진입점. 한 번만 호출되고 종료. 결과:
- workspace/outline.json
- workspace/research_targets.json

이 두 파일이 생성되면 Phase 2 (parallel swarm) 시작 가능.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

from ..base_agent import BaseAgent
from ..claude_cli import call_claude_cli_with_retry
from ..workspace import SwarmWorkspace

logger = logging.getLogger(__name__)


# Skeleton+Identify 에이전트는 한 번 호출. 산출물 두 파일.
class SkeletonIdentifyAgent(BaseAgent):
    """Phase 1: skeleton + identify (단일 호출)."""

    def __init__(
        self,
        workspace: SwarmWorkspace,
        topic: str,
        duration_min: int,
        creative_brief: str = "",
        reference_examples: str = "",
        *,
        model: str = "claude-opus-4-6",
        max_turns: int = 30,
    ):
        super().__init__(
            agent_id="skeleton_identify",
            role="skeleton_identify",
            workspace=workspace,
            idle_sec=1,
            max_iterations=2,  # 한 번만 시도, 실패 시 1번 retry
        )
        self.topic = topic
        self.duration_min = duration_min
        self.creative_brief = creative_brief
        self.reference_examples = reference_examples
        self.model = model
        self.max_turns = max_turns

    async def step(self) -> bool:
        """단일 호출 — outline.json + research_targets.json 작성."""
        # 이미 산출물이 있으면 skip
        if self.workspace.exists("outline.json") and self.workspace.exists("research_targets.json"):
            self.workspace.emit_event(self.agent_id, "skipped", reason="outputs exist")
            self.stop()
            return False

        # prompt 빌드
        prompt = self._build_prompt()

        self.workspace.emit_event(self.agent_id, "started", model=self.model)
        result = await call_claude_cli_with_retry(
            prompt,
            model=self.model,
            allowed_tools=["Read", "Write", "Glob", "WebSearch", "WebFetch"],
            max_turns=self.max_turns,
            timeout_sec=600,
            project_dir=self.workspace.dir,
            max_retries=1,
        )

        if not result.success:
            self.workspace.emit_event(
                self.agent_id, "failed",
                level="warning",
                error=result.error,
                elapsed_sec=result.elapsed_sec,
            )
            self.stop()
            return False

        # 산출물 검증
        if not (self.workspace.exists("outline.json") and self.workspace.exists("research_targets.json")):
            self.workspace.emit_event(
                self.agent_id, "missing_outputs",
                level="warning",
                error="agent did not write outline.json or research_targets.json",
            )
            self.stop()
            return False

        # 검증 — JSON 파싱 OK?
        outline = self.workspace.read_json("outline.json")
        targets = self.workspace.read_json("research_targets.json")
        if not isinstance(outline, dict) or "chapters" not in outline:
            self.workspace.emit_event(
                self.agent_id, "invalid_outline",
                level="warning",
                outline_keys=list(outline.keys()) if isinstance(outline, dict) else None,
            )
            self.stop()
            return False
        if not isinstance(targets, dict) or "targets" not in targets:
            self.workspace.emit_event(
                self.agent_id, "invalid_targets",
                level="warning",
            )
            self.stop()
            return False

        n_chapters = len(outline.get("chapters", []))
        n_targets = len(targets.get("targets", []))
        n_beats = sum(len(c.get("key_beats", [])) for c in outline.get("chapters", []))
        self.workspace.emit_event(
            self.agent_id, "completed",
            level="success",
            chapters=n_chapters,
            beats=n_beats,
            targets=n_targets,
            cost_usd=result.cost_usd,
            elapsed_sec=result.elapsed_sec,
        )

        # research_queue.jsonl 초기화 — research_targets의 각 question을 query로 등록
        for target in targets.get("targets", []):
            target_id = target.get("id", "")
            for i, question in enumerate(target.get("questions", [])):
                q_id = f"{target_id}_q{i+1:02d}"
                self.workspace.append_jsonl("research_queue.jsonl", {
                    "id": q_id,
                    "target_id": target_id,
                    "target": target.get("target", ""),
                    "type": target.get("type", ""),
                    "for_beat": target.get("for_beat", ""),
                    "question": question,
                    "angle": target.get("angle", ""),
                    "priority": "high",
                })

        n_queries = sum(len(t.get("questions", [])) for t in targets.get("targets", []))
        self.workspace.emit_event(
            self.agent_id, "queue_initialized",
            level="success",
            queries=n_queries,
        )
        self.stop()
        return True

    def _build_prompt(self) -> str:
        """skeleton+identify prompt 조립."""
        # SKILL.md 로드
        skill_path = Path(__file__).parent.parent / "prompts" / "skeleton_identify.md"
        skill_text = skill_path.read_text(encoding="utf-8") if skill_path.exists() else ""

        creative_brief_block = ""
        if self.creative_brief:
            creative_brief_block = f"\n<creative_brief>\n{self.creative_brief}\n</creative_brief>\n"

        ref_block = ""
        if self.reference_examples:
            ref_block = (
                "\n<reference_examples>\n"
                "tone_anchors 추출에 사용하세요.\n\n"
                f"{self.reference_examples}\n"
                "</reference_examples>\n"
            )

        return f"""<system_context>
당신은 swarm Phase 1의 단일 에이전트 — Skeleton + Identify.
역할: 주제 골격 조사 + outline.json + research_targets.json 작성.
작업 디렉토리: {self.workspace.dir}
</system_context>

<topic>
{self.topic}
</topic>

<project_config>
duration_minutes: {self.duration_min}
</project_config>

{creative_brief_block}{ref_block}

<skill>
{skill_text}
</skill>

<task>
지금 즉시 다음 두 파일을 작성하고 종료하세요:
1. {self.workspace.dir}/outline.json
2. {self.workspace.dir}/research_targets.json

skill의 출력 형식과 절대 규칙을 정확히 따르세요.
WebSearch + WebFetch로 골격만 빠르게 조사. 깊은 연구는 다음 phase의 다른 agent가 합니다.
두 파일을 모두 Write 도구로 저장하면 즉시 종료합니다.
</task>
"""
