"""브리프→검색 쿼리 분해(5~10). LLM 실패 시 결정적 폴백. v3 query_planner 이식.
기본 invoker는 claude CLI(중첩 env 제거). 테스트는 invoker 주입."""
from __future__ import annotations

import json
import os
import re
import subprocess
from typing import Callable

PLANNER_PROMPT = """당신은 리서치 쿼리 플래너입니다. editorial_brief를 읽고
**5~10개의 검색 쿼리**로 분해하세요. 각 쿼리는 위키피디아/뉴스/학술/도서
4개 lane에 모두 던져집니다.

# 출력 규칙
- JSON 객체 한 개. 다른 텍스트 일체 금지.
- 스키마: {"queries": [{"query": "...", "rationale": "...", "lang": "ko|en|auto"}]}
- 5~10개. 통문장 금지 (10어절 이하).
- 각 쿼리는 독립적으로 의미 있는 entity/event/concept이어야 함.
- 한국 주제는 ko + 글로벌 맥락 1~2건 en도 포함.

# 피해야 할 것
- "X에 대한 모든 것" 같은 추상 쿼리
- 너무 길고 구체적인 통문장
- "역사", "이야기" 같은 단독 검색어(오염 위험)
"""

_NEST_ENV = ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SSE_PORT")


def _build_prompt(brief: dict) -> str:
    keep = ("real_topic", "core_question", "hook_angle", "hook_episode",
            "must_include_episodes", "excluded_angles", "audience",
            "key_entities", "entities", "keywords")
    slim = {k: v for k, v in brief.items() if k in keep and v}
    return f"{PLANNER_PROMPT}\n\n<brief>\n{json.dumps(slim, ensure_ascii=False, indent=2)}\n</brief>\n"


def _parse_response(raw: str) -> list[dict]:
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
        out.append({"query": text, "rationale": str(q.get("rationale") or ""),
                    "lang": str(q.get("lang") or "auto")})
    if not out:
        raise ValueError("유효 쿼리 없음")
    return out


def _call_claude_cli(prompt: str, *, timeout: int = 120) -> str:
    env = {k: v for k, v in os.environ.items() if k not in _NEST_ENV}
    claude_bin = os.environ.get("CLAUDE_CLI_BIN", "claude")
    r = subprocess.run([claude_bin, "-p", "--output-format", "text"],
                       input=prompt, capture_output=True, text=True,
                       timeout=timeout, env=env)
    if r.returncode != 0:
        raise RuntimeError(f"claude CLI exit {r.returncode}: {(r.stderr or '')[:200]}")
    return r.stdout


def _fallback_queries(brief: dict, project_slug: str = "") -> list[dict]:
    real = (brief.get("real_topic") or "").strip()
    if real and len(real.split()) <= 8:
        return [{"query": real, "rationale": "fallback (LLM 실패)", "lang": "auto"}]
    if project_slug:
        first = project_slug.replace("_", " ").split()[0]
        return [{"query": first, "rationale": "fallback — slug 첫 토큰", "lang": "auto"}]
    return []


def plan_queries(brief: dict, *, project_slug: str = "",
                 invoker: Callable[[str], str] | None = None) -> list[dict]:
    """브리프를 5~10개 쿼리로 분해. invoker 미지정 시 claude CLI. 실패 시 폴백."""
    invoke = invoker or _call_claude_cli
    prompt = _build_prompt(brief)
    try:
        return _parse_response(invoke(prompt))
    except Exception as exc:
        print(f"[query_planner] LLM 실패, fallback: {exc}", flush=True)
        return _fallback_queries(brief, project_slug=project_slug)
