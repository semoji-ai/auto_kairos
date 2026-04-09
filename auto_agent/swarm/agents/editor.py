"""EditorAgent — swarm Phase 4 (Opus 편집자).

초고(draft.md)를 Read 툴로 읽고 최적 내러티브 구조를 설계.
필요한 심층 리서치는 research_queue.jsonl에 추가 → researcher swarm이 처리.
editorial_plan.json 출력 후 종료.

토큰 최적화:
  - system_prompt (캐시): editor skill + outline
  - user_prompt (동적): 최소 지시만
  - 초고/claims는 프롬프트에 넣지 않음 — Read 툴로 직접 읽음
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


class EditorAgent(BaseAgent):
    """Phase 4: Opus 편집자 (단일 또는 최대 2회 호출)."""

    def __init__(
        self,
        workspace: SwarmWorkspace,
        topic: str,
        duration_min: int,
        writing_style: str,
        *,
        model: str = "claude-opus-4-6",
        max_turns: int = 15,
        timeout_sec: int = 300,
    ):
        super().__init__(
            agent_id="editor",
            role="editor",
            workspace=workspace,
            idle_sec=1,
            max_iterations=3,  # 최대 2패스 + 1 retry
        )
        self.topic = topic
        self.duration_min = duration_min
        self.writing_style = writing_style
        self.model = model
        self.max_turns = max_turns
        self.timeout_sec = timeout_sec

    async def step(self) -> bool:
        """편집 패스 1회. 최대 2번 호출됨 (TODO 해소 전·후)."""
        plan = self.workspace.read_json("editorial_plan.json", default={})
        plan_status = plan.get("status", "")

        # 이미 ready면 종료
        if plan_status == "ready":
            self.workspace.emit_event(self.agent_id, "skipped", reason="editorial_plan already ready")
            self.stop()
            return False

        # draft.md가 없으면 아직 draft_writer가 안 끝난 것
        if not self.workspace.exists("draft.md"):
            self.workspace.emit_event(self.agent_id, "waiting", reason="draft.md not yet available")
            return False  # idle, 재시도

        is_first_pass = not plan  # editorial_plan.json이 없으면 첫 패스
        pass_label = "first_pass" if is_first_pass else "todo_resolution"

        system_prompt, user_prompt = self._build_prompts(is_first_pass)

        self.workspace.emit_event(
            self.agent_id, "started",
            model=self.model,
            pass_label=pass_label,
        )

        result = await call_claude_cli_with_retry(
            user_prompt,
            system_prompt=system_prompt,
            model=self.model,
            allowed_tools=["Read", "Write", "Bash", "Glob"],
            max_turns=self.max_turns,
            timeout_sec=self.timeout_sec,
            project_dir=self.workspace.dir,
            max_retries=1,
        )

        if not result.success:
            self.workspace.emit_event(
                self.agent_id, "failed",
                level="warning",
                error=result.error[:300],
                elapsed_sec=result.elapsed_sec,
            )
            return False

        # editorial_plan.json 확인
        new_plan = self.workspace.read_json("editorial_plan.json", default={})
        new_status = new_plan.get("status", "")
        n_todos = sum(
            1 for b in new_plan.get("restructured_beats", [])
            if b.get("todo")
        )

        self.workspace.emit_event(
            self.agent_id, "completed",
            level="success",
            pass_label=pass_label,
            plan_status=new_status,
            todos_remaining=n_todos,
            cost_usd=result.cost_usd,
            elapsed_sec=result.elapsed_sec,
        )

        if new_status == "ready":
            self.stop()
            return True

        # pending_research → orchestrator가 researcher들 대기 후 다시 호출
        return True

    def _build_prompts(self, is_first_pass: bool):
        """(system_prompt, user_prompt) 반환.

        system_prompt (캐시): editor skill + outline
        user_prompt (동적): 최소 지시 (초고/claims는 Read 툴로 읽음)
        """
        skill_path = Path(__file__).parent.parent / "prompts" / "editor.md"
        skill_text = skill_path.read_text(encoding="utf-8") if skill_path.exists() else ""

        outline = self.workspace.read_json("outline.json", default={})
        outline_str = json.dumps(outline, ensure_ascii=False, indent=2)

        system_prompt = f"""당신은 swarm Phase 4의 editor (Opus).
역할: 초고를 읽고 최적 내러티브 구조를 설계하는 편집자.
워크스페이스: {self.workspace.dir}

<project_config>
topic: {self.topic}
duration_min: {self.duration_min}
writing_style: {self.writing_style}
</project_config>

<outline>
{outline_str[:3000]}
</outline>

<skill>
{skill_text}
</skill>
"""

        if is_first_pass:
            user_prompt = f"""<task>
편집 작업을 시작하세요.

1. Read("{self.workspace.dir}/draft.md") — 초고 전체 읽기
2. Read("{self.workspace.dir}/claims.jsonl") — 확보된 사실 목록 확인
3. 편집 판단:
   - 가장 극적인 오프닝 선택
   - 최적 내러티브 구조 설계
   - 더 필요한 리서치 식별 (핵심만, 최대 10개)
4. 필요한 쿼리를 research_queue.jsonl에 추가 (helper_cli 사용)
5. editorial_plan.json 저장

모든 리서치 요청을 마친 후 editorial_plan.json을 저장하고 종료하세요.
TODO가 없으면 status: "ready", 있으면 status: "pending_research".
</task>
"""
        else:
            plan = self.workspace.read_json("editorial_plan.json", default={})
            pending_todos = [
                b.get("todo") for b in plan.get("restructured_beats", [])
                if b.get("todo")
            ]
            user_prompt = f"""<task>
TODO 해소 확인 패스입니다.

미해소 TODO: {pending_todos}

1. Read("{self.workspace.dir}/claims.jsonl") — 새로 추가된 claims 확인
2. Read("{self.workspace.dir}/editorial_plan.json") — 현재 플랜 확인
3. 각 TODO에 해당하는 claim이 도착했으면 beat의 todo를 null로 업데이트
4. 모든 TODO 해소 → status: "ready"
   해소 안 된 TODO → 포기하고 available claims로 대체, status: "ready"
   (무한 대기 금지 — 이번이 마지막 패스입니다)
5. editorial_plan.json 저장 후 종료
</task>
"""

        return system_prompt, user_prompt
