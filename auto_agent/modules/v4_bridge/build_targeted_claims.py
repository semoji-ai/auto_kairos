"""v4 research_targeted/*.md → v3 targeted_claims.json 변환기.

v4 target-research 산출물 포맷 (skills/target-research/SKILL.md):
  ---
  question: <원문>
  slug: <slug>
  source: existing | new
  from_wiki: <slug>          # 선택
  wiki_question_id: <Q1>     # 선택
  ---

  본문: 요약 → 근거 → 출처

v3 targeted_claims.json 스키마 (script-director / data-mapper / fact-verifier 입력):
  {
    "claims": [
      {
        "question_id": "q001",
        "question": "...",
        "answer": "...",
        "evidence": "...",
        "confidence": "high | medium | low"
      }
    ]
  }

confidence 매핑:
  - source: existing → "medium" (기존 자료 재활용)
  - source: new → "high" (신규 정밀 리서치)
  - 명시 없음 → "medium"
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .build_research_report import _parse_frontmatter, _strip_frontmatter


_SECTION_HEADERS = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)


def _split_answer_evidence(body: str) -> tuple[str, str]:
    """본문을 answer (요약) + evidence (근거·출처 포함) 로 분리.

    전략:
      1. 첫 ## 헤더가 있으면 첫 헤더 이전 텍스트 = answer, 이후 = evidence
      2. 첫 빈 줄 단락 기준으로 분리 (헤더 없을 때)
      3. 분리 실패 시 body 전체를 answer 로, evidence 빈 문자열
    """
    body = body.strip()
    if not body:
        return "", ""

    # 1. 헤더 기반 분리
    headers = list(_SECTION_HEADERS.finditer(body))
    if headers:
        first = headers[0]
        answer = body[: first.start()].strip()
        evidence = body[first.start():].strip()
        if answer:
            return answer, evidence

    # 2. 단락 기반 분리 (첫 단락 = answer)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    if len(paragraphs) >= 2:
        return paragraphs[0], "\n\n".join(paragraphs[1:])

    # 3. 단일 단락 = 모두 answer
    return body, ""


def build_targeted_claims(targeted_dir: Path) -> dict[str, Any]:
    """v4 research_targeted/*.md → v3 targeted_claims.json dict.

    Args:
        targeted_dir: research_targeted/ 디렉토리 (없거나 비어있어도 OK → claims=[])

    Returns:
        {"claims": [...]}  v3 스키마 호환
    """
    claims: list[dict[str, Any]] = []

    if not targeted_dir or not targeted_dir.exists():
        return {"claims": claims}

    files = sorted(targeted_dir.glob("*.md"))
    for idx, md_path in enumerate(files, start=1):
        raw = md_path.read_text(encoding="utf-8")
        fm = _parse_frontmatter(raw)
        body = _strip_frontmatter(raw).strip()

        question = fm.get("question") or fm.get("slug") or md_path.stem
        question_id = fm.get("wiki_question_id") or f"q{idx:03d}"
        source = (fm.get("source") or "").lower().strip()
        confidence = "high" if source == "new" else "medium"

        answer, evidence = _split_answer_evidence(body)

        claims.append({
            "question_id": question_id,
            "question": question,
            "answer": answer,
            "evidence": evidence,
            "confidence": confidence,
        })

    return {"claims": claims}
