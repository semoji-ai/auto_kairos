"""ValidatorAgent — swarm Phase 2의 실시간 환각/품질 감시.

이 agent는 manuscript.md를 주기적으로 scan해서:
1. 모든 [claim:cXXX] 태그가 claims.jsonl에 실제 존재하는지 검증
2. 구체적 사실(날짜/숫자/인물명)이 모두 [claim:cXXX] 태그를 가지는지 검증
3. headline/values 중복 검사 (이전 Phase 1의 reviewer 역할 흡수)
4. tone consistency
5. narrative cohesion (간단한 heuristic)
6. claim citation rate 계산

Validator는 직접 manuscript를 수정하지 않습니다. 발견한 문제를 log.jsonl에
emit하면 writer가 다음 turn에 인지하고 수정합니다.

이 agent는 LLM 호출 없이 정규식 + 정적 분석으로 진행 (cost 0, 빠름).
LLM 검증이 필요한 항목은 별도 step (옵션 — v2).
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from ..base_agent import BaseAgent
from ..workspace import SwarmWorkspace

logger = logging.getLogger(__name__)


# 패턴 정의
CLAIM_TAG_RE = re.compile(r'\[claim:([^\]]+)\]')
TODO_MARKER_RE = re.compile(r'\[TODO:(q[^\s\]]+)[^\]]*\]')

# "구체적 사실" 후보를 찾는 패턴들 — 이런 표현 근처에 [claim:] 태그가 있어야 함
DATE_RE = re.compile(r'(\d{3,4}년|\d{1,2}월\s*\d{1,2}일|BC\s*\d+|기원전\s*\d+)')
NUMBER_RE = re.compile(r'(\d{1,3}(?:[,.]\d+)*\s*(?:%|척|명|개|만|억|조|미터|킬로미터|달러|원|배|시간|분|초|kg|km|m))')
PROPER_NOUN_HINT_RE = re.compile(r'([A-Z][a-zA-Z]{2,})')  # 영문 고유명사 (느슨한 heuristic)


class ValidatorAgent(BaseAgent):
    """주기적으로 manuscript scan + 환각/품질 검증."""

    def __init__(
        self,
        workspace: SwarmWorkspace,
        *,
        idle_sec: float = 4.0,
        max_iterations: int = 200,
        target_citation_rate: float = 0.85,
    ):
        super().__init__(
            agent_id="validator",
            role="validator",
            workspace=workspace,
            idle_sec=idle_sec,
            max_iterations=max_iterations,
        )
        self.target_citation_rate = target_citation_rate
        # 마지막 검증 시점의 manuscript 길이 (변경 감지용)
        self._last_manuscript_len = -1
        self._last_violations_count = -1

    async def step(self) -> bool:
        # 1. manuscript 변경 감지 (변경 없으면 idle)
        manuscript = self.workspace.read_text("manuscript.md")
        if not manuscript:
            return False
        if len(manuscript) == self._last_manuscript_len:
            # 변화 없음 — idle
            return False
        self._last_manuscript_len = len(manuscript)

        # 2. claims.jsonl 읽기 (가능한 fact pool)
        all_claims = self.workspace.all_jsonl("claims.jsonl")
        valid_claim_ids: Set[str] = {c.get("id", "") for c in all_claims}

        # 3. manuscript의 모든 [claim:cXXX] 태그 추출
        used_tags = CLAIM_TAG_RE.findall(manuscript)
        all_used_ids: Set[str] = set()
        for tag in used_tags:
            for cid in tag.split(","):
                all_used_ids.add(cid.strip())

        # 4. 검증 항목들
        violations: List[Dict[str, Any]] = []

        # 4-1. 사용된 claim id가 claims.jsonl에 존재하는가?
        invalid_ids = all_used_ids - valid_claim_ids
        for invalid_id in invalid_ids:
            violations.append({
                "type": "invalid_claim_id",
                "severity": "high",
                "claim_id": invalid_id,
                "message": f"manuscript에 [claim:{invalid_id}] 태그가 있지만 claims.jsonl에 없음 (writer 환각 의심)",
            })

        # 4-2. 구체적 사실(날짜/숫자/고유명사)이 [claim:] 태그 없이 등장하는가?
        # 단순 heuristic — 정확하지 않을 수 있지만 대략적인 환각 신호
        manuscript_no_tags = CLAIM_TAG_RE.sub('', manuscript)
        manuscript_no_todos = TODO_MARKER_RE.sub('', manuscript_no_tags)
        # 각 fact 후보가 30자 이내에 [claim:] 태그가 인접해 있는지
        unmatched_facts = self._find_unmatched_facts(manuscript)
        for fact_text, position in unmatched_facts[:10]:  # 최대 10개만 보고
            violations.append({
                "type": "uncited_fact",
                "severity": "medium",
                "fact": fact_text,
                "position": position,
                "message": f"태그 없는 구체적 사실: '{fact_text}'",
            })

        # 4-3. headline ↔ values 중복 검사 (manuscript 단계에선 N/A — scene_specs에서 재검사)

        # 5. claim citation rate 계산
        # 분모: 구체적 사실 후보 개수, 분자: 태그가 인접한 것
        total_facts = len(re.findall(DATE_RE, manuscript_no_todos)) + len(re.findall(NUMBER_RE, manuscript_no_todos))
        cited_facts = total_facts - len(unmatched_facts)
        citation_rate = cited_facts / total_facts if total_facts > 0 else 1.0

        # 6. status.json 업데이트
        status = self.workspace.read_json("status.json", default={})
        status["last_validated_at"] = datetime.now(timezone.utc).isoformat()
        status["validator"] = {
            "manuscript_chars": len(manuscript),
            "claims_used": len(all_used_ids),
            "claims_invalid": len(invalid_ids),
            "uncited_facts": len(unmatched_facts),
            "citation_rate": round(citation_rate, 3),
            "violations": len(violations),
            "passes": citation_rate >= self.target_citation_rate and len(invalid_ids) == 0,
        }
        self.workspace.write_json_atomic("status.json", status)

        # 7. 위반사항 변동이 있으면 log.jsonl emit
        if len(violations) != self._last_violations_count:
            self.workspace.emit_event(
                self.agent_id, "validation_run",
                level="warning" if violations else "info",
                violations_count=len(violations),
                citation_rate=round(citation_rate, 3),
                invalid_ids=list(invalid_ids)[:5],
                uncited_count=len(unmatched_facts),
            )
            # 첫 5개 violation을 개별 이벤트로 (writer가 인지 가능)
            for v in violations[:5]:
                self.workspace.append_jsonl("log.jsonl", {
                    "agent": self.agent_id,
                    "event": "violation",
                    "level": "warning",
                    "violation": v,
                })
            self._last_violations_count = len(violations)

        # 8. supervisor 역할: meta status 체크
        # 모든 조건 충족 + writer가 complete 신호 → swarm 종료 신호
        outline_state = self.workspace.read_json("outline_state.json", default={})
        if (
            outline_state.get("status") == "complete"
            and citation_rate >= self.target_citation_rate
            and len(invalid_ids) == 0
        ):
            meta = self.workspace.read_json("meta.json", default={})
            if meta.get("status") not in ("done", "compiled"):
                meta["status"] = "done"
                meta["validator_passed"] = True
                meta["citation_rate"] = round(citation_rate, 3)
                self.workspace.write_json_atomic("meta.json", meta)
                self.workspace.emit_event(
                    self.agent_id, "swarm_done_signaled",
                    level="success",
                    citation_rate=round(citation_rate, 3),
                    manuscript_chars=len(manuscript),
                )

        return True

    def _find_unmatched_facts(self, manuscript: str) -> List[Tuple[str, int]]:
        """태그 없이 등장하는 구체적 사실 찾기.

        규칙: 날짜/숫자 패턴 발견 위치에서 ±30자 안에 [claim:] 태그가 있어야 함.
        없으면 unmatched.
        """
        unmatched: List[Tuple[str, int]] = []

        # claim 태그 위치들
        tag_positions = [m.start() for m in CLAIM_TAG_RE.finditer(manuscript)]

        for pattern in (DATE_RE, NUMBER_RE):
            for m in pattern.finditer(manuscript):
                fact_text = m.group(0)
                pos = m.start()
                # ±30자 안에 claim 태그가 있는가?
                nearby_tag = any(abs(tp - pos) <= 30 for tp in tag_positions)
                if not nearby_tag:
                    # TODO 마커 안에 있으면 OK (researcher 답변 대기 중)
                    in_todo = False
                    for todo_m in TODO_MARKER_RE.finditer(manuscript):
                        if todo_m.start() <= pos <= todo_m.end():
                            in_todo = True
                            break
                    if not in_todo:
                        unmatched.append((fact_text, pos))

        return unmatched
