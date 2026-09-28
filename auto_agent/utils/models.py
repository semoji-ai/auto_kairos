"""모델 ID 단일 소스.

코드 곳곳에 날짜가 박힌 모델 ID(claude-opus-4-6 등)가 흩어져 있으면 새 모델이
나와도 일부 경로만 옛 모델로 돈다. 모델을 바꿀 때는 이 파일만 고친다.

- CLI(`claude --model`)는 별칭(opus/sonnet/haiku)을 받으면 최신 모델로 풀어 주므로
  CLI 호출에는 CLI_* 별칭을 쓴다.
- Anthropic SDK(Messages API)는 별칭을 받지 않으므로 전체 ID를 쓴다.
- 파이프라인 에이전트의 모델은 `orchestrator/execution.py` 의 PROFILES 가 정한다.
"""
from __future__ import annotations

# Anthropic SDK용 전체 ID
CLAUDE_OPUS = "claude-opus-5-5"
CLAUDE_SONNET = "claude-sonnet-5"
CLAUDE_HAIKU = "claude-haiku-4-5-20251001"

# claude CLI용 별칭 — CLI가 최신 모델로 풀어 준다
CLI_OPUS = "opus"
CLI_SONNET = "sonnet"
CLI_HAIKU = "haiku"

# Codex CLI
CODEX_DEFAULT = "gpt-6-astra"
CODEX_LIGHT = "gpt-5.6-sol"

# Gemini (검수·오디오 분석)
GEMINI_FLASH = "gemini-2.5-flash"
