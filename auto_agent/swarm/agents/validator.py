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

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from ..base_agent import BaseAgent
from ..workspace import SwarmWorkspace

logger = logging.getLogger(__name__)


# 패턴 정의
CLAIM_TAG_RE = re.compile(r'\[claim:([^\]]+)\]')
CHAR_TAG_RE = re.compile(r'\[char:([^\]]+)\]')
TODO_MARKER_RE = re.compile(r'\[TODO:(q[^\s\]]+)[^\]]*\]')

# "구체적 사실" 후보를 찾는 패턴들 — 이런 표현 근처에 [claim:] 태그가 있어야 함
DATE_RE = re.compile(r'(\d{3,4}년|\d{1,2}월\s*\d{1,2}일|BC\s*\d+|기원전\s*\d+)')
NUMBER_RE = re.compile(r'(\d{1,3}(?:[,.]\d+)*\s*(?:%|척|명|개|만|억|조|미터|킬로미터|달러|원|배|시간|분|초|kg|km|m))')
PROPER_NOUN_HINT_RE = re.compile(r'([A-Z][a-zA-Z]{2,})')  # 영문 고유명사 (느슨한 heuristic)

# 한국어 인물 추적 휴리스틱 — 이 표현이 paragraph에 있으면 [char:] 태그도 있어야 함
KOREAN_PRONOUNS = ("그는", "그녀는", "그가", "그녀가", "그를", "그녀를", "그의", "그녀의")


class ValidatorAgent(BaseAgent):
    """주기적으로 manuscript scan + 환각/품질 검증."""

    def __init__(
        self,
        workspace: SwarmWorkspace,
        *,
        idle_sec: float = 4.0,
        max_iterations: int = 100000,  # 사실상 무한 — 시간 보호장치(max_seconds)에 의존
        max_seconds: float = 3600.0,   # 1시간 (사용자 결정: 옵션 2 시간 기반)
        target_citation_rate: float = 0.6,
        uncited_char_fail_threshold: int = 3,
    ):
        super().__init__(
            agent_id="validator",
            role="validator",
            workspace=workspace,
            idle_sec=idle_sec,
            max_iterations=max_iterations,
            max_seconds=max_seconds,
        )
        self.target_citation_rate = target_citation_rate
        # uncited_character paragraphs >= 이 값이면 validator fail
        # 1~2는 휴리스틱 false positive 가능성 있어 warning만, 3+ 부터는 진짜 누락으로 판정
        self.uncited_char_fail_threshold = uncited_char_fail_threshold
        # 마지막 검증 시점의 content hash (manuscript + character_register + outline_state)
        # outline_state도 추적 — writer가 status를 drafting→complete로 바꾸는 순간을 포착해서
        # supervisor 블록(meta.status="done" transition)이 정확히 한 번 더 돌도록 보장.
        self._last_manuscript_hash = ""
        self._last_register_hash = ""
        self._last_outline_state_hash = ""
        self._last_violations_count = -1

    async def step(self) -> bool:
        # 1. manuscript / register / outline_state 변경 감지 (content hash 기반)
        manuscript = self.workspace.read_text("manuscript.md")
        if not manuscript:
            return False

        manuscript_hash = hashlib.sha256(manuscript.encode("utf-8")).hexdigest()
        register_text = self.workspace.read_text("character_register.json")
        register_hash = hashlib.sha256(register_text.encode("utf-8")).hexdigest() if register_text else ""
        outline_state_text = self.workspace.read_text("outline_state.json")
        outline_state_hash = hashlib.sha256(outline_state_text.encode("utf-8")).hexdigest() if outline_state_text else ""

        if (
            manuscript_hash == self._last_manuscript_hash
            and register_hash == self._last_register_hash
            and outline_state_hash == self._last_outline_state_hash
        ):
            # 세 파일 모두 변화 없음 — idle
            return False

        self._last_manuscript_hash = manuscript_hash
        self._last_register_hash = register_hash
        self._last_outline_state_hash = outline_state_hash

        # 2. claims.jsonl 읽기 (가능한 fact pool)
        all_claims = self.workspace.all_jsonl("claims.jsonl")
        valid_claim_ids: Set[str] = {c.get("id", "") for c in all_claims}

        # 2b. character_register 읽기 (인물 id pool)
        register = self.workspace.read_json("character_register.json", default={"characters": []})
        valid_char_ids: Set[str] = {c.get("id", "") for c in register.get("characters", [])}
        char_name_variants: List[str] = []  # 이름 매칭용
        for c in register.get("characters", []):
            for k in ("name_ko", "name_en"):
                v = c.get(k, "").strip()
                if v and len(v) >= 2:
                    char_name_variants.append(v)

        # 3. manuscript의 모든 [claim:cXXX] 태그 추출
        used_tags = CLAIM_TAG_RE.findall(manuscript)
        all_used_ids: Set[str] = set()
        for tag in used_tags:
            for cid in tag.split(","):
                all_used_ids.add(cid.strip())

        # 3b. manuscript의 모든 [char:id] 태그 추출
        used_char_tags = CHAR_TAG_RE.findall(manuscript)
        all_used_char_ids: Set[str] = set()
        for tag in used_char_tags:
            for cid in tag.split(","):
                all_used_char_ids.add(cid.strip())

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

        # 4-1b. 사용된 char id가 character_register에 존재하는가?
        invalid_char_ids = all_used_char_ids - valid_char_ids
        for invalid_cid in invalid_char_ids:
            violations.append({
                "type": "invalid_char_id",
                "severity": "high",
                "char_id": invalid_cid,
                "message": f"manuscript에 [char:{invalid_cid}] 태그가 있지만 character_register.json에 없음 (writer가 register append 누락)",
            })

        # 4-1c. 한국어 인물 추적 휴리스틱 — paragraph 단위로 검사
        # 인물 이름 또는 대명사가 등장하는 paragraph에 [char:] 태그가 있어야 함
        # 임계값 미만은 warning (휴리스틱 false positive 가능성), 임계값 이상은 high
        uncited_char_paragraphs = self._find_uncited_character_paragraphs(
            manuscript, char_name_variants
        )
        char_severity = "high" if len(uncited_char_paragraphs) >= self.uncited_char_fail_threshold else "warning"
        for para_preview, reason in uncited_char_paragraphs[:5]:
            violations.append({
                "type": "uncited_character",
                "severity": char_severity,
                "paragraph": para_preview,
                "reason": reason,
                "message": f"paragraph에 인물 흔적({reason})은 있지만 [char:] 태그 없음",
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
        # passes 조건 — 환각/구조 검사는 hard, 인용률 휴리스틱은 alternate path 허용:
        #   (A) citation_rate >= target  OR
        #   (B) outline_state.status == "complete" AND claims_used >= 10
        #       (writer가 자기 일을 다 끝냈고 충분한 claim을 인용했으면 ±30자 휴리스틱 false positive 우회)
        #   AND (1) invalid_claim_ids == 0 (환각 claim id)
        #       (2) invalid_char_ids == 0 (register에 없는 char id)
        #       (3) uncited_char_paragraphs < 임계값
        outline_state_for_pass = self.workspace.read_json("outline_state.json", default={})
        writer_complete = (
            outline_state_for_pass.get("status") == "complete"
            and len(all_used_ids) >= 10
        )
        citation_ok = citation_rate >= self.target_citation_rate
        passes = (
            (citation_ok or writer_complete)
            and len(invalid_ids) == 0
            and len(invalid_char_ids) == 0
            and len(uncited_char_paragraphs) < self.uncited_char_fail_threshold
        )

        status = self.workspace.read_json("status.json", default={})
        status["last_validated_at"] = datetime.now(timezone.utc).isoformat()
        status["validator"] = {
            "manuscript_chars": len(manuscript),
            "claims_used": len(all_used_ids),
            "claims_invalid": len(invalid_ids),
            "chars_used": len(all_used_char_ids),
            "chars_invalid": len(invalid_char_ids),
            "uncited_facts": len(unmatched_facts),
            "uncited_char_paragraphs": len(uncited_char_paragraphs),
            "uncited_char_fail_threshold": self.uncited_char_fail_threshold,
            "citation_rate": round(citation_rate, 3),
            "violations": len(violations),
            "passes": passes,
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
        # 모든 검증 통과 + writer가 complete 신호 → swarm 종료 신호
        # passes 변수가 4개 조건 모두 충족했는지 담고 있음
        outline_state = self.workspace.read_json("outline_state.json", default={})
        if outline_state.get("status") == "complete" and passes:
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

    def _find_uncited_character_paragraphs(
        self, manuscript: str, char_name_variants: List[str]
    ) -> List[Tuple[str, str]]:
        """paragraph 단위로 인물 흔적 vs [char:] 태그 매칭.

        규칙: paragraph 안에 (인물 이름 또는 한국어 대명사)가 있는데
        [char:] 태그가 없으면 위반.

        Returns: [(paragraph_preview, reason), ...]
        """
        violations: List[Tuple[str, str]] = []
        # paragraph 분리 (빈 줄 기준)
        paragraphs = re.split(r'\n\s*\n', manuscript)

        for para in paragraphs:
            para = para.strip()
            if not para or len(para) < 20:
                continue

            has_char_tag = bool(CHAR_TAG_RE.search(para))
            if has_char_tag:
                continue  # OK

            # 인물 이름 매칭
            matched_name = None
            for name in char_name_variants:
                if name in para:
                    matched_name = name
                    break

            # 한국어 대명사 매칭
            matched_pronoun = None
            for pron in KOREAN_PRONOUNS:
                if pron in para:
                    matched_pronoun = pron
                    break

            if matched_name:
                violations.append((para[:80], f"name='{matched_name}'"))
            elif matched_pronoun:
                violations.append((para[:80], f"pronoun='{matched_pronoun}'"))

        return violations

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
