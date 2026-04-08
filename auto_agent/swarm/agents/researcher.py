"""ResearcherAgent — swarm Phase 2의 deep researcher.

여러 instance가 병렬로 실행됨. 각 instance:
1. research_queue.jsonl tail
2. pending query 1개 atomic claim
3. claude CLI 호출 (WebSearch + WebFetch + sourced fact 추출)
4. findings.jsonl + claims.jsonl에 결과 append
5. 다음 query 또는 idle

환각 방지: prompt + JSON schema + post-validation 3중.
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


# claim id 카운터 (instance별 unique id 생성용)
_claim_counter_lock_marker = "claims_counter.txt"


def _next_claim_id(workspace: SwarmWorkspace, instance_id: str) -> str:
    """workspace 안에서 unique claim id 생성. (간단한 sequence — race-free하지 않아도 OK,
    final compile 단계에서 dedup하기 때문)
    """
    # claim_id는 c001, c002, ... 형식. researcher instance가 자기 prefix를 갖도록 한다.
    # 예: R1_c001, R2_c001
    # claims.jsonl에 그대로 append. compile 시 unique 보장 확인.
    counter_file = workspace.path(f".counter_{instance_id}.txt")
    n = 0
    if counter_file.exists():
        try:
            n = int(counter_file.read_text().strip())
        except ValueError:
            pass
    n += 1
    counter_file.write_text(str(n))
    return f"{instance_id}_c{n:03d}"


class ResearcherAgent(BaseAgent):
    """Deep researcher — query 1개씩 처리, 병렬로 N instance."""

    def __init__(
        self,
        workspace: SwarmWorkspace,
        instance_id: str,
        *,
        # 2026-04-08 (저녁): sonnet 복귀 확인 (단발 8s 정상 응답).
        # default를 sonnet으로 되돌림. claude_cli.call_claude_cli_with_retry 안에
        # sonnet→opus 자동 fallback 가드가 있어서 다시 overload 와도 안전.
        model: str = "claude-sonnet-4-6",
        idle_sec: float = 2.0,
        max_iterations: int = 30,
        timeout_per_query_sec: int = 180,  # 빠른 루프 + cross-check + 이미지 수집 (2026-04-09: 150 → 180)
    ):
        super().__init__(
            agent_id=instance_id,
            role="researcher",
            workspace=workspace,
            idle_sec=idle_sec,
            max_iterations=max_iterations,
        )
        self.model = model
        self.timeout_per_query_sec = timeout_per_query_sec

    async def step(self) -> bool:
        # 1. queue에서 atomic claim
        task = self.workspace.claim_task("research_queue.jsonl", claimer=self.agent_id)
        if not task:
            return False

        q_id = task.get("id", "unknown")
        self.workspace.emit_event(
            self.agent_id, "claimed_query",
            q_id=q_id,
            target=task.get("target", ""),
            type=task.get("type", ""),
        )

        # 2. prompt 빌드
        prompt = self._build_prompt(task)

        # 3. claude CLI 호출 — 빠른 루프: max_turns 5로 제한, single source 정책
        result = await call_claude_cli_with_retry(
            prompt,
            model=self.model,
            allowed_tools=["WebSearch", "WebFetch", "Read", "Write"],
            max_turns=5,  # FAST mode: WebSearch 1~2 + WebFetch 1 + Write 1 = 3~4 turns
            timeout_sec=self.timeout_per_query_sec,
            project_dir=self.workspace.dir,
            max_retries=1,
        )

        if not result.success:
            self.workspace.emit_event(
                self.agent_id, "research_failed",
                level="warning",
                q_id=q_id,
                error=result.error[:300],
                elapsed_sec=result.elapsed_sec,
            )
            # status="failed"로 마크. claim_task가 fail_count로 retry 가능 여부 판단.
            # max_retries(기본 2)까지 다른 researcher가 자동 retry. 그 후엔 영구 포기.
            self.workspace.complete_task(
                q_id,
                completer=self.agent_id,
                status="failed",
                error=result.error[:200],
            )
            return True

        # 4. JSON 파싱
        parsed = self._parse_research_output(result.text, q_id)
        if not parsed:
            self.workspace.emit_event(
                self.agent_id, "parse_failed",
                level="warning",
                q_id=q_id,
                raw_preview=result.text[:200],
            )
            self.workspace.complete_task(q_id, completer=self.agent_id, status="parse_failed")
            return True

        # 5. claims.jsonl에 추출된 fact 추가 + findings.jsonl에 메타 기록
        claims = parsed.get("claims", [])
        valid_claims = []
        cross_checked_count = 0
        image_candidates_total = 0
        for claim in claims:
            # 환각 방지: source_urls(list) 또는 source_url(string) + source_quote 필수
            # 새 schema: source_urls (list of url), legacy: source_url (string)
            source_urls = claim.get("source_urls")
            if not source_urls:
                # legacy fallback: source_url (string) → wrap to list
                legacy_url = claim.get("source_url")
                if legacy_url:
                    source_urls = [legacy_url] if isinstance(legacy_url, str) else list(legacy_url)
                    claim["source_urls"] = source_urls
                else:
                    continue
            if not isinstance(source_urls, list) or not source_urls:
                continue
            if not claim.get("source_quote"):
                continue
            # source_url legacy 필드도 backward-compat용으로 항상 채움 (1번째 url)
            claim.setdefault("source_url", source_urls[0])
            # cross_checked: 명시되지 않으면 source_urls 길이로 추론
            if "cross_checked" not in claim:
                claim["cross_checked"] = len(source_urls) >= 2
            if claim.get("cross_checked"):
                cross_checked_count += 1
            # image_candidates 정규화 (없으면 빈 배열)
            img_cands = claim.get("image_candidates") or []
            if not isinstance(img_cands, list):
                img_cands = []
            claim["image_candidates"] = img_cands
            image_candidates_total += len(img_cands)
            # claim id 부여 (instance prefix)
            new_id = _next_claim_id(self.workspace, self.agent_id)
            claim["id"] = new_id
            claim["q_id"] = q_id
            claim["researcher"] = self.agent_id
            self.workspace.append_jsonl("claims.jsonl", claim)
            valid_claims.append(new_id)

        finding_record = {
            "q_id": q_id,
            "target_id": task.get("target_id", ""),
            "researcher": self.agent_id,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "claim_ids": valid_claims,
            "claims_count": len(valid_claims),
            "cross_checked_count": cross_checked_count,
            "image_candidates_total": image_candidates_total,
            "rejected_count": len(claims) - len(valid_claims),
            "not_found": parsed.get("not_found", []),
            "elapsed_sec": result.elapsed_sec,
            "cost_usd": result.cost_usd,
        }
        self.workspace.append_jsonl("findings.jsonl", finding_record)

        self.workspace.complete_task(q_id, completer=self.agent_id, status="completed")
        self.workspace.emit_event(
            self.agent_id, "research_completed",
            level="success",
            q_id=q_id,
            claims=len(valid_claims),
            rejected=len(claims) - len(valid_claims),
            cost_usd=result.cost_usd,
            elapsed_sec=result.elapsed_sec,
        )
        return True

    def _build_prompt(self, task: Dict[str, Any]) -> str:
        skill_path = Path(__file__).parent.parent / "prompts" / "researcher.md"
        skill_text = skill_path.read_text(encoding="utf-8") if skill_path.exists() else ""

        return f"""<system_context>
당신은 swarm Phase 2의 researcher (instance: {self.agent_id}).
역할: query 1개를 source-tied claim들로 답함. 환각 절대 금지.
워크스페이스: {self.workspace.dir}
</system_context>

<query>
{json.dumps(task, ensure_ascii=False, indent=2)}
</query>

<skill>
{skill_text}
</skill>

<task>
위 query를 처리하세요.
WebSearch + WebFetch (최대 2회)로 주 source + cross-check source를 찾고, 모든 fact에
source_urls(list) + source_quote를 명시합니다. 핵심 fact는 가능하면 2개 source로 cross-check
(cross_checked: true). 시각화 가능한 fact는 image_candidates에 Wikimedia 이미지 url 수집.
완료되면 단일 JSON 객체로 응답하세요. 다른 텍스트는 출력하지 마세요.
</task>
"""

    def _parse_research_output(self, text: str, q_id: str) -> Optional[Dict[str, Any]]:
        """LLM 응답에서 JSON 추출. 마크다운 펜스 + 부분 매칭 지원."""
        text = text.strip()
        if not text:
            return None
        # 1. 그대로 시도
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
        # 2. 마크다운 펜스 제거
        m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
        # 3. 첫 { ... } 매칭
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        return None
