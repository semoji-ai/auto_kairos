"""WriterAgent — swarm Phase 2의 manuscript 작성자.

단일 instance (단일 챕터). 매 step에 작은 단위(1~3 문장 또는 1 beat)씩 작성.
researcher들이 claims.jsonl에 추가하는 fact를 기다리며 점진적으로 manuscript 누적.

주요 동작:
1. outline + claims + manuscript 읽기
2. 다음 작업 결정 (TODO 해결 / 새 beat / 종료)
3. claude CLI 호출 (Read/Write/Edit/Bash 도구)
4. manuscript.md 업데이트 (LLM이 직접 도구로)
5. outline_state.json 업데이트
6. 모든 beat 완료 시 status="complete"

종료 조건:
- outline_state.json status == "complete"
- 또는 max_iterations 도달 (안전장치)
- 또는 timeout
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base_agent import BaseAgent
from ..claude_cli import call_claude_cli_with_retry
from ..workspace import SwarmWorkspace

logger = logging.getLogger(__name__)


# manuscript에서 claim 태그 추출
CLAIM_TAG_RE = re.compile(r'\[claim:([^\]]+)\]')
TODO_MARKER_RE = re.compile(r'\[TODO:(q[^\s\]]+)[^\]]*\]')


class WriterAgent(BaseAgent):
    """매 step에 작은 단위로 manuscript 작성. claim-tagged."""

    def __init__(
        self,
        workspace: SwarmWorkspace,
        topic: str,
        duration_min: int,
        writing_style: str = "iromism",
        creative_brief: str = "",
        reference_examples: str = "",
        *,
        model: str = "claude-opus-4-6",
        idle_sec: float = 3.0,
        max_iterations: int = 50,
        timeout_per_step_sec: int = 180,
    ):
        super().__init__(
            agent_id="writer",
            role="writer",
            workspace=workspace,
            idle_sec=idle_sec,
            max_iterations=max_iterations,
        )
        self.topic = topic
        self.duration_min = duration_min
        self.writing_style = writing_style
        self.creative_brief = creative_brief
        self.reference_examples = reference_examples
        self.model = model
        self.timeout_per_step_sec = timeout_per_step_sec

    async def step(self) -> bool:
        # 1. Phase 1 산출물 대기 (outline 없으면 일하지 않음)
        if not self.workspace.exists("outline.json"):
            return False
        outline = self.workspace.read_json("outline.json")
        if not isinstance(outline, dict) or "chapters" not in outline:
            return False

        # 2. 종료 상태 확인
        state = self.workspace.read_json("outline_state.json", default={})
        if state.get("status") == "complete":
            self.workspace.emit_event(self.agent_id, "writer_done", level="success")
            self.stop()
            return False

        # 3. claims pool 충분한가? — 첫 작업 전에 최소한의 claim 필요
        claims = self.workspace.all_jsonl("claims.jsonl")
        manuscript = self.workspace.read_text("manuscript.md")
        if not claims and not manuscript:
            # 첫 step — claims 도착 대기
            return False  # idle, will retry after sleep

        # 4. prompt 빌드 — stable system prompt (캐시 대상) + dynamic user prompt
        # outline이 바뀌지 않는 한 system_prompt는 모든 step에서 동일 → cache hit
        system_prompt = self._build_system_prompt(outline)
        prompt = self._build_dynamic_prompt(state, claims, len(manuscript))

        # 5. claude CLI 호출
        result = await call_claude_cli_with_retry(
            prompt,
            system_prompt=system_prompt,
            model=self.model,
            allowed_tools=["Read", "Write", "Edit", "Glob", "Bash"],
            max_turns=15,
            timeout_sec=self.timeout_per_step_sec,
            project_dir=self.workspace.dir,
            max_retries=1,
        )

        if not result.success:
            self.workspace.emit_event(
                self.agent_id, "step_failed",
                level="warning",
                error=result.error,
                elapsed_sec=result.elapsed_sec,
            )
            return False

        # 6. 작성 결과 metric 추적
        new_manuscript = self.workspace.read_text("manuscript.md")
        manuscript_chars = len(new_manuscript)
        used_claims = set(CLAIM_TAG_RE.findall(new_manuscript))
        # 각 [claim:cXXX] 태그가 여러 id를 포함할 수 있음 (R1_c001,R1_c002)
        all_used = set()
        for tag_content in used_claims:
            for cid in tag_content.split(","):
                all_used.add(cid.strip())
        todo_markers = TODO_MARKER_RE.findall(new_manuscript)

        new_state = self.workspace.read_json("outline_state.json", default={})
        new_state["iteration"] = new_state.get("iteration", 0) + 1
        new_state["manuscript_chars"] = manuscript_chars
        new_state["claims_used"] = len(all_used)
        new_state["todo_count"] = len(todo_markers)
        if "status" not in new_state:
            new_state["status"] = "drafting"
        self.workspace.write_json_atomic("outline_state.json", new_state)

        self.workspace.emit_event(
            self.agent_id, "step_completed",
            level="info",
            iteration=new_state["iteration"],
            chars=manuscript_chars,
            claims_used=len(all_used),
            todo_count=len(todo_markers),
            cost_usd=result.cost_usd,
            elapsed_sec=result.elapsed_sec,
        )

        # 7. 종료 조건 자체 점검
        if new_state.get("status") == "complete":
            self.stop()

        return True

    def _build_system_prompt(self, outline: Dict[str, Any]) -> str:
        """Step 간에 변하지 않는 안정적인 컨텍스트 → --system-prompt-file로 전달.

        Claude CLI가 동일 내용을 ephemeral 5분 캐시로 보관.
        writer step 2..N은 이 부분 토큰을 cache_read_input_tokens로 처리 → 비용 절감.

        포함: skill text, outline JSON, reference_examples, creative_brief, project_config
        제외: outline_state, claims, manuscript (step마다 변함 → dynamic prompt로)
        """
        skill_path = Path(__file__).parent.parent / "prompts" / "writer.md"
        skill_text = skill_path.read_text(encoding="utf-8") if skill_path.exists() else ""
        workspace_str = str(self.workspace.dir)
        skill_text = skill_text.replace("WORKSPACE_PATH", workspace_str)

        ref_block = ""
        if self.reference_examples:
            ref_block = f"\n<reference_examples>\n{self.reference_examples}\n</reference_examples>\n"

        creative_brief_block = ""
        if self.creative_brief:
            creative_brief_block = f"\n<creative_brief>\n{self.creative_brief}\n</creative_brief>\n"

        target_chars = {1: 400, 3: 1200, 5: 2000, 10: 4000}.get(self.duration_min, self.duration_min * 400)

        return f"""당신은 swarm Phase 2의 writer.
역할: outline에 따라 claim-tagged manuscript 작성.
workspace_path: {workspace_str}

⚠️ 모든 helper CLI 명령에서 workspace_path 인자는 위 경로를 그대로 사용:
   --workspace {workspace_str}

<project_config>
topic: {self.topic}
duration_minutes: {self.duration_min}
writing_style: {self.writing_style}
target_chars: 약 {target_chars}자 (±10%)
</project_config>
{creative_brief_block}{ref_block}
<outline>
{json.dumps(outline, ensure_ascii=False, indent=2)[:3000]}
</outline>

<skill>
{skill_text}
</skill>
"""

    def _build_dynamic_prompt(
        self,
        state: Dict[str, Any],
        claims: List[Dict[str, Any]],
        manuscript_chars: int = 0,
    ) -> str:
        """Step마다 바뀌는 동적 컨텍스트 — stdin으로 전달 (캐시 불가 부분).

        P1 compaction:
        - claims: 최근 10개만 (전체 개수는 표시).
        - manuscript: prompt에서 제거 — writer가 매 step 시작 시 Read로 직접 전체 확인.
        - state: 핵심 필드만 추출 (beats_done/pending, current_beat, unresolved_todos).
        """
        def _first_src(c):
            urls = c.get("source_urls")
            if isinstance(urls, list) and urls:
                return urls[0]
            return c.get("source_url", "")

        # 최근 10개 claims만 — 오래된 것은 이미 사용됐거나 현재 beat과 무관
        recent_claims = claims[-10:] if len(claims) > 10 else claims
        claims_summary = "\n".join(
            f"  - [{c.get('id', '?')}]{'✓✓' if c.get('cross_checked') else ''} "
            f"{c.get('text', '')[:120]} (src: {_first_src(c)[:60]})"
            for c in recent_claims
        )
        if len(claims) > 10:
            claims_summary = f"(전체 {len(claims)}개 중 최근 10개)\n" + claims_summary

        # state 핵심 필드만 (전체 JSON 불필요)
        state_compact = {
            "status": state.get("status", "drafting"),
            "iteration": state.get("iteration", 0) + 1,
            "current_beat": state.get("current_beat"),
            "beats_done": state.get("beats_done", []),
            "beats_pending": state.get("beats_pending", []),
            "unresolved_todos": state.get("unresolved_todos", []),
            "manuscript_chars": state.get("manuscript_chars", 0),
        }

        register = self.workspace.read_json("character_register.json", default={"characters": []})
        characters = register.get("characters", [])
        character_summary = "\n".join(
            f"  - id={c.get('id', '?')} | {c.get('name_ko', '')} ({c.get('name_en', '')}) — {c.get('role', '')}"
            for c in characters
        )
        if not character_summary:
            character_summary = "  (아직 없음 — 필요하면 register에 직접 append)"

        manuscript_status = f"{manuscript_chars}자 작성됨" if manuscript_chars else "빈 상태 (첫 작업)"

        return f"""<current_state>
iteration: {state_compact['iteration']}
status: {state_compact['status']}
current_beat: {state_compact['current_beat']}
beats_done: {state_compact['beats_done']}
beats_pending: {state_compact['beats_pending']}
unresolved_todos: {state_compact['unresolved_todos']}
manuscript_chars: {state_compact['manuscript_chars']} ({manuscript_status})
</current_state>

<recent_claims>
지금까지 추가된 source-tied facts (최근 순). 이것만 사용 가능.

{claims_summary if claims else "(아직 없음 — 첫 claim 도착 대기 중)"}
</recent_claims>

<character_register>
manuscript에서 [char:id] 태그로 사용 가능한 인물 id pool.
register에 없는 인물은 character_register.json에 직접 append 후 사용.

{character_summary}
</character_register>

<task>
이번 step의 작업:
0. **manuscript.md를 Read로 전체 확인** (현재 내용 파악 + 연속성/중복 방지).
1. current_state를 보고 다음 우선순위 결정 (TODO 해결 / 새 beat / 종료).
2. **단 1~3 문장 또는 1 beat만** 작성/수정. 한 번에 통째 rewrite 금지.
3. fact는 [claim:cXXX] 태그 필수. claim 없으면 [TODO:qXXX] 마커 + research_queue.jsonl append.
4. manuscript.md 업데이트 (Write 또는 Edit).
5. outline_state.json 업데이트 (필수). iteration, status, manuscript 길이 등 갱신.
6. 모든 beat 완료 + 모든 TODO 해결 시 outline_state.status를 "complete"로.
7. 그 외엔 작업 후 종료 (이 step 끝).

📌 recent_claims는 최근 10개만 제공됨. 이전 claims가 필요하면 claims.jsonl을 Read로 직접 확인.
⚠️ 한 step의 작업이 끝나면 즉시 종료. 다음 turn은 다른 step에서 진행.
</task>
"""
