"""Anthropic SDK 기반 Claude 클라이언트 — ephemeral prompt caching 지원.

사용법:
    client = CachingClaudeClient()

    # 단일 호출 (no tools)
    text, usage = client.call_single(
        model="claude-sonnet-4-6",
        static_system=skill_md + shared_skills,   # 캐시 대상
        dynamic_system=project_context + task,    # 캐시 제외
        user_message="작업 내용",
    )

    # 멀티턴 에이전트 루프 (tool_use)
    text, usage = client.call_agent(
        model="claude-opus-4-6",
        static_system=skill_md + shared_skills,   # 캐시 대상
        dynamic_system=project_context,           # 캐시 제외
        initial_message=task,
        tools=LOCAL_TOOL_SCHEMAS,
        tool_handler=handle_local_tool,
        max_turns=80,
    )

    # 캐시 절약 로그
    print(usage)
    # {'input_tokens': 500, 'output_tokens': 1200,
    #  'cache_read_input_tokens': 12000, 'cache_creation_input_tokens': 0}
"""
from __future__ import annotations

import os
from typing import Any, Callable, Optional

import anthropic


class CachingClaudeClient:
    """Anthropic Messages API with ephemeral prompt caching.

    - static_system: SKILL.md + shared_skills (변하지 않음 → cache_control 적용)
    - dynamic_system: project_context + task (매 호출마다 다름 → 캐시 제외)
    - 첫 호출: cache_creation_input_tokens 발생 (캐시 생성)
    - 이후 동일 prefix 호출: cache_read_input_tokens 발생 (90% 할인)
    """

    def __init__(self) -> None:
        self._client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY", "")
        )

    # ── 단일 호출 (no tools) ──────────────────────────────────────────────

    def call_single(
        self,
        model: str,
        static_system: str,
        dynamic_system: str,
        user_message: str,
        max_tokens: int = 8192,
    ) -> tuple[str, dict]:
        """도구 없는 단일 호출. static_system에 cache_control 적용.

        Returns:
            (응답 텍스트, usage 딕셔너리)
        """
        system_blocks = _build_system_blocks(static_system, dynamic_system)

        resp = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_blocks,
            messages=[{"role": "user", "content": user_message}],
        )
        return _extract_text(resp), _extract_usage(resp)

    # ── 멀티턴 에이전트 루프 ─────────────────────────────────────────────

    def call_agent(
        self,
        model: str,
        static_system: str,
        dynamic_system: str,
        initial_message: str,
        tools: list[dict],
        tool_handler: Callable[[str, dict], str],
        max_turns: int = 80,
        on_tool_call: Optional[Callable[[str, dict], None]] = None,
    ) -> tuple[str, dict]:
        """멀티턴 tool-use 루프. static_system + tool 정의 캐싱.

        Args:
            model: 모델 ID
            static_system: SKILL.md + shared_skills (캐시됨)
            dynamic_system: project_context + task (캐시 안됨)
            initial_message: 첫 user 메시지 (task)
            tools: Anthropic tool 스키마 리스트
            tool_handler: (tool_name, tool_input) → 결과 문자열
            max_turns: 최대 턴 수
            on_tool_call: 도구 호출 시 콜백 (진행상황 보고용)

        Returns:
            (마지막 텍스트 응답, 누적 usage 딕셔너리)
        """
        system_blocks = _build_system_blocks(static_system, dynamic_system)
        cached_tools = _add_tool_cache(tools)

        messages: list[dict] = [{"role": "user", "content": initial_message}]
        total_usage: dict[str, int] = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
        }
        last_text = ""

        for _turn in range(max_turns):
            resp = self._client.messages.create(
                model=model,
                max_tokens=8192,
                system=system_blocks,
                tools=cached_tools,
                messages=messages,
            )
            _accumulate_usage(total_usage, resp.usage)

            # 텍스트 누적 (end_turn 직전 최종 응답)
            for block in resp.content:
                if hasattr(block, "text"):
                    last_text = block.text

            if resp.stop_reason == "end_turn":
                break

            if resp.stop_reason == "tool_use":
                tool_results = []
                for block in resp.content:
                    if block.type == "tool_use":
                        if on_tool_call:
                            on_tool_call(block.name, block.input)
                        try:
                            result = tool_handler(block.name, block.input)
                        except Exception as exc:
                            result = f"[ERROR] {exc}"
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(result),
                        })
                messages.append({"role": "assistant", "content": resp.content})
                messages.append({"role": "user", "content": tool_results})
            else:
                # max_tokens 또는 예상치 못한 stop_reason
                break

        return last_text, total_usage

    # ── 유틸: 캐시 절약 요약 ─────────────────────────────────────────────

    @staticmethod
    def format_usage(usage: dict) -> str:
        """usage 딕셔너리를 사람이 읽기 쉬운 형태로 포맷."""
        inp = usage.get("input_tokens", 0)
        out = usage.get("output_tokens", 0)
        cache_read = usage.get("cache_read_input_tokens", 0)
        cache_write = usage.get("cache_creation_input_tokens", 0)
        saved_pct = int(cache_read / (inp + cache_read) * 100) if (inp + cache_read) > 0 else 0
        return (
            f"input={inp:,} out={out:,} "
            f"cache_read={cache_read:,} cache_write={cache_write:,} "
            f"(캐시 절약 {saved_pct}%)"
        )


# ── 내부 헬퍼 ────────────────────────────────────────────────────────────

def _build_system_blocks(static: str, dynamic: str) -> list[dict[str, Any]]:
    """static은 cache_control 적용, dynamic은 일반 블록."""
    blocks: list[dict] = []
    if static:
        blocks.append({
            "type": "text",
            "text": static,
            "cache_control": {"type": "ephemeral"},
        })
    if dynamic:
        blocks.append({"type": "text", "text": dynamic})
    return blocks


def _add_tool_cache(tools: list[dict]) -> list[dict]:
    """마지막 tool 정의에 cache_control 추가 (tool schema 캐싱).

    Anthropic API는 tool 정의도 캐시 가능.
    마지막 tool의 cache_control이 전체 tool 블록을 커버함.
    """
    if not tools:
        return tools
    cached = [dict(t) for t in tools]
    cached[-1] = {**cached[-1], "cache_control": {"type": "ephemeral"}}
    return cached


def _extract_text(resp: Any) -> str:
    return "".join(
        block.text for block in resp.content if hasattr(block, "text")
    )


def _extract_usage(resp: Any) -> dict:
    u = resp.usage
    return {
        "input_tokens": u.input_tokens,
        "output_tokens": u.output_tokens,
        "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", 0),
        "cache_creation_input_tokens": getattr(u, "cache_creation_input_tokens", 0),
    }


def _accumulate_usage(total: dict, u: Any) -> None:
    total["input_tokens"] += u.input_tokens
    total["output_tokens"] += u.output_tokens
    total["cache_read_input_tokens"] += getattr(u, "cache_read_input_tokens", 0)
    total["cache_creation_input_tokens"] += getattr(u, "cache_creation_input_tokens", 0)
