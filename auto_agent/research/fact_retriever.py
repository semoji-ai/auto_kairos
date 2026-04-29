"""Fact Retriever — script-director가 manuscript 작성 중 호출하는 evidence 검증 함수.

별도 Claude CLI subprocess로 분리해 script-director context를 가볍게 유지.
sonnet + max_turns=5 + 자체 환각 검증 (span chunk substring) 강제.

spec: docs/superpowers/specs/2026-04-28-research-redesign.md (Phase 3)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Callable, Optional

from auto_agent.research.evidence_check import verify_span_in_chunk


SKILL_PATH = (
    Path(__file__).resolve().parents[1]
    / "data" / "skills" / "agents" / "fact-retriever" / "SKILL.md"
)


def _load_skill_text() -> str:
    if SKILL_PATH.exists():
        return SKILL_PATH.read_text(encoding="utf-8")
    return ""


def _build_prompt(
    *,
    query: str,
    entities: list[str] | None = None,
    year: int | None = None,
    claim_kind: str = "fact:event",
    project_research_dir: Path,
) -> str:
    """fact-retriever subprocess에 보낼 프롬프트.

    SKILL.md 본문 + 호출 컨텍스트 + 작업 입력을 합침.
    """
    skill = _load_skill_text()
    body = {
        "query": query,
        "entities": list(entities or []),
        "year": year,
        "claim_kind": claim_kind,
        "project_research_dir": str(project_research_dir),
    }
    return (
        skill
        + "\n\n---\n\n"
        + "# 호출 컨텍스트\n\n"
        + "이번 호출의 입력입니다. SKILL.md 절차 5단계를 수행하고 단일 JSON 객체로 응답하세요.\n\n"
        + f"<input>\n{json.dumps(body, ensure_ascii=False, indent=2)}\n</input>\n"
    )


def _parse_response(raw: str) -> dict:
    """fact-retriever 응답 → dict. 환각 차단 검증은 별도(verify_span_in_chunk)."""
    text = (raw or "").strip()
    # ```json ... ``` 또는 직접 { ... }
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if m:
        text = m.group(1)
    else:
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            text = m.group(0)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("응답이 dict가 아님")
    return data


def _call_claude_cli(prompt: str, *, timeout: int = 90) -> str:
    """Claude CLI subprocess 호출 — 다른 모듈과 동일 패턴."""
    claude_bin = os.environ.get("CLAUDE_CLI_BIN", "claude")
    result = subprocess.run(
        [claude_bin, "-p", "--output-format", "text"],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI exit {result.returncode}: {result.stderr[:200]}")
    return result.stdout


def _verify_evidence_against_chunk(
    evidence: dict,
    project_research_dir: Path,
) -> tuple[bool, Optional[str]]:
    """fact-retriever가 만든 evidence span이 raw chunk에 substring으로 존재하는지 검증.

    SKILL.md에서 자체 검증하지만 외부에서 한 번 더 강제 — defense in depth.
    """
    if not isinstance(evidence, dict):
        return False, "evidence가 dict 아님"
    span = str(evidence.get("span") or "").strip()
    if not span:
        return False, "evidence.span 누락"
    anchor = str(evidence.get("anchor") or "").strip()
    if not anchor:
        return False, "evidence.anchor 누락"
    chunk_path = project_research_dir / anchor
    if not chunk_path.exists():
        return False, f"raw chunk 파일 없음: {anchor}"
    try:
        chunk_text = chunk_path.read_text(encoding="utf-8")
    except Exception as exc:
        return False, f"chunk read 실패: {exc}"
    return verify_span_in_chunk(span, chunk_text)


def fact_retrieve(
    *,
    query: str,
    project_research_dir: Path,
    entities: list[str] | None = None,
    year: int | None = None,
    claim_kind: str = "fact:event",
    invoker: Callable[[str], str] | None = None,
    verify_evidence: bool = True,
) -> dict:
    """script-director(또는 다른 호출자)가 사용하는 main API.

    Args:
        query: 자연어 검색 쿼리
        project_research_dir: 프로젝트 research/ 경로
        entities: 매칭 entity 후보
        year: 매칭 연도
        claim_kind: fact:date_or_number / fact:event / fact:context / interpretation
        invoker: 테스트용 mock callable (prompt → response str). None이면 Claude CLI.
        verify_evidence: True면 응답의 evidence span을 raw chunk와 substring 검증

    Returns:
        SKILL.md 출력 스키마 — found/claim/evidence/tier/confidence 등.
        실패 시 {"found": false, "reason": "..."}.
    """
    invoke = invoker or _call_claude_cli
    prompt = _build_prompt(
        query=query,
        entities=entities,
        year=year,
        claim_kind=claim_kind,
        project_research_dir=project_research_dir,
    )
    try:
        raw = invoke(prompt)
        data = _parse_response(raw)
    except Exception as exc:
        return {"found": False, "reason": f"CLI/parse 실패: {exc}", "warnings": []}

    if not data.get("found"):
        return data

    # evidence 검증
    if verify_evidence:
        evidence = data.get("evidence") or {}
        ok, reason = _verify_evidence_against_chunk(evidence, project_research_dir)
        if not ok:
            warnings = list(data.get("warnings") or [])
            warnings.append(f"외부 evidence 검증 실패: {reason}")
            return {
                "found": False,
                "reason": "evidence 검증 실패",
                "warnings": warnings,
                "_rejected_data": data,  # 디버깅용
            }
    return data
