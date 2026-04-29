"""LLM-driven research query planner.

editorial_brief를 읽고 lane 검색에 최적화된 5~10개 쿼리로 분해합니다.
기계적 entity 추출은 쿼리 오염을 일으키기 쉬워 LLM이 판단합니다.

호출 패턴: Claude CLI subprocess + stdin (CLAUDE.md 규칙 준수).
LLM 실패 시 단순 fallback (real_topic 1건만).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from typing import Any, Callable


PLANNER_PROMPT = """당신은 리서치 쿼리 플래너입니다. editorial_brief를 읽고
**5~10개의 검색 쿼리**로 분해하세요. 각 쿼리는 위키피디아/뉴스/학술/도서
4개 lane에 모두 던져집니다.

# 출력 규칙
- JSON 객체 한 개. 다른 텍스트 일체 금지.
- 스키마: {"queries": [{"query": "...", "rationale": "...", "lang": "ko|en|auto"}]}
- 5~10개. 통문장 금지 (10어절 이하).
- 각 쿼리는 독립적으로 의미 있는 entity/event/concept이어야 함.
- 한국 주제는 ko + 글로벌 맥락 1~2건 en도 포함.
- 우선순위: 핵심 인물/회사/제품 → 핵심 사건/연도 → 글로벌 비교/맥락 → 학술 keyword.

# 피해야 할 것
- "X에 대한 모든 것" 같은 추상 쿼리
- 너무 길고 구체적인 통문장 (예: "유일한 박사와 유한양행이 남긴 100개의 숫자로 읽는 한국 기업 정신의 원형")
- "역사", "이야기" 같은 단독 검색어 (오염 위험)

# 좋은 예시
{
  "queries": [
    {"query": "유한양행", "rationale": "회사 본 entity, ko wiki/공식 자료", "lang": "ko"},
    {"query": "유일한 박사", "rationale": "창업자, 인물 자료", "lang": "ko"},
    {"query": "안티푸라민 1933", "rationale": "최초 자체개발 제품 + 연도", "lang": "ko"},
    {"query": "유한양행 종업원지주제", "rationale": "특이 경영사 1936", "lang": "ko"},
    {"query": "lazertinib FDA approval", "rationale": "최근 글로벌 신약 영문", "lang": "en"},
    {"query": "Yuhan Corporation Korea pharmaceutical", "rationale": "영문 위키/학술", "lang": "en"}
  ]
}

이제 아래 brief를 받아 동일한 형식으로 5~10개 쿼리를 출력하세요.
"""


def _build_prompt(brief: dict) -> str:
    """brief 핵심 필드만 추려 프롬프트에 합침."""
    keep_keys = (
        "real_topic", "core_question", "hook_angle", "hook_episode",
        "must_include_episodes", "excluded_angles", "audience",
        "key_entities", "entities", "keywords",
    )
    slim = {k: v for k, v in brief.items() if k in keep_keys and v}
    brief_text = json.dumps(slim, ensure_ascii=False, indent=2)
    return f"{PLANNER_PROMPT}\n\n<brief>\n{brief_text}\n</brief>\n"


def _parse_response(raw: str) -> list[dict]:
    """LLM 응답에서 JSON 추출."""
    raw = (raw or "").strip()
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        raise ValueError("응답에 JSON 블록 없음")
    payload = json.loads(m.group(0))
    queries = payload.get("queries") if isinstance(payload, dict) else None
    if not isinstance(queries, list) or not queries:
        raise ValueError("queries 배열 비어 있음")
    out = []
    for q in queries:
        if not isinstance(q, dict):
            continue
        text = str(q.get("query") or "").strip()
        if not text or len(text) > 80:
            continue
        out.append({
            "query": text,
            "rationale": str(q.get("rationale") or ""),
            "lang": str(q.get("lang") or "auto"),
        })
    if not out:
        raise ValueError("유효 쿼리 없음")
    return out


def _call_claude_cli(prompt: str, *, timeout: int = 120) -> str:
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


def _fallback_queries(brief: dict, project_slug: str = "") -> list[dict]:
    """LLM 실패 시 — real_topic만 1건. 통문장 폐기."""
    real = (brief.get("real_topic") or "").strip()
    if real and len(real.split()) <= 8:
        return [{"query": real, "rationale": "fallback (LLM 실패)", "lang": "auto"}]
    if project_slug:
        # 슬러그 첫 단어
        first = project_slug.replace("_", " ").split()[0]
        return [{"query": first, "rationale": "fallback — slug 첫 토큰", "lang": "auto"}]
    return []


def plan_queries(
    brief: dict,
    *,
    project_slug: str = "",
    invoker: Callable[[str], str] | None = None,
) -> list[dict]:
    """brief를 5~10개 검색 쿼리로 분해.

    invoker: 테스트용 mock. 미지정 시 Claude CLI subprocess 호출.
    LLM 실패 시 fallback 쿼리 반환.
    """
    invoke = invoker or _call_claude_cli
    prompt = _build_prompt(brief)
    try:
        raw = invoke(prompt)
        return _parse_response(raw)
    except Exception as exc:
        print(f"[query_planner] LLM 실패, fallback 사용: {exc}", flush=True)
        return _fallback_queries(brief, project_slug=project_slug)
