"""trend-analyst / performance-analyst 실행 래퍼."""
import json
import logging
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from auto_agent.paths import get_vault_dir, get_data_dir, get_workspace_dir
from auto_agent.utils.platform import subprocess_kwargs
from auto_agent.utils import codex_cli as codex_cli_util

logger = logging.getLogger(__name__)


CHANNEL_SIGNAL_PROFILES = {
    "이로미즘": {
        "positive_patterns": [
            r"투자", r"주식", r"etf", r"배당", r"isa", r"연금", r"금리", r"환율",
            r"관세", r"수출", r"인플레", r"채권", r"부동산", r"실적", r"증시",
            r"실수령", r"소득세", r"종합소득세", r"법인세", r"건보료",
        ],
        "negative_patterns": [
            r"연예", r"드라마", r"고양이", r"강아지", r"레시피",
            r"간편결제", r"자동이체", r"관리비", r"프로모션", r"쿠폰", r"통신",
            r"재약정", r"스타필드", r"앱카드", r"네삼페",
        ],
        "source_boosts": {
            "google-news-business-ko": 2,
            "daum-news-home": 1,
            "finance-community-signals": 3,
        },
        "source_penalties": {
            "google-news-top-ko": -1,
            "ai-community-signals": -4,
            "hacker-news-frontpage": -3,
        },
        "blocked_sources": [
            "ai-community-signals",
        ],
    },
    "세모지": {
        "positive_patterns": [
            r"실록", r"왕조", r"조선", r"기원", r"유래", r"문파", r"계보", r"제국",
            r"브랜드", r"기업사", r"발명", r"원조", r"백과", r"문명", r"전쟁",
        ],
        "negative_patterns": [r"연애", r"감량", r"반려", r"레시피"],
        "source_boosts": {
            "daum-cafe-popular-mobile": 2,
            "reddit-todayilearned-hot": 2,
        },
        "source_penalties": {
            "finance-community-signals": -2,
            "ai-community-signals": -2,
            "hacker-news-frontpage": -1,
        },
    },
    "ai백과사전": {
        "positive_patterns": [
            r"\bai\b", r"llm", r"모델", r"추론", r"파인튜닝", r"rag", r"agent",
            r"gpu", r"npu", r"반도체", r"데이터센터", r"openai", r"anthropic",
            r"gemini", r"nvidia", r"benchmark", r"로봇", r"멀티모달",
        ],
        "negative_patterns": [r"연예", r"고양이", r"강아지", r"레시피", r"입주"],
        "source_boosts": {
            "hacker-news-frontpage": 3,
            "ai-community-signals": 3,
            "google-news-business-ko": 2,
            "reddit-popular-hot": 1,
        },
        "source_penalties": {
            "google-news-top-ko": -2,
            "finance-community-signals": -4,
            "daum-cafe-popular-mobile": -2,
            "damoang-free": -2,
        },
        "blocked_sources": [
            "finance-community-signals",
        ],
    },
}


class AgentRunner:
    """에이전트 실행 래퍼 — provider별 CLI로 에이전트 호출."""

    def __init__(self, provider: Optional[str] = None):
        self._load_workspace_env()
        self._vault_dir = get_vault_dir()
        self._data_dir = get_data_dir()
        self._agents_config = self._load_agents_config()
        self._provider = (provider or os.getenv("AUTO_AGENT_PROVIDER", "claude")).strip().lower()
        if self._provider not in {"claude", "codex"}:
            raise ValueError(f"지원하지 않는 provider: {self._provider}")

    def _load_workspace_env(self) -> None:
        env_path = get_workspace_dir() / ".env"
        if not env_path.exists():
            return
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path, override=False)
        except Exception:
            pass
        try:
            for raw_line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key, value)
        except Exception:
            pass

    def run_trend_analyst(self, channel: str, seed: Optional[str] = None,
                          autoresearch: bool = False, max_rounds: int = 5,
                          on_progress: Optional[callable] = None) -> Dict:
        """trend-analyst 에이전트 실행."""
        config = self._optimize_codex_agent_config(
            "trend-analyst",
            self._agents_config.get("agents", {}).get("trend-analyst", {}),
        )
        if autoresearch:
            from auto_agent.modules.auto_research_loop import AutoResearchLoop
            loop = AutoResearchLoop(channel=channel, max_rounds=max_rounds, seed=seed)
            if self._provider == "codex":
                return self._run_codex_autoresearch(loop, config, on_progress=on_progress)
            prompt = loop.build_loop_prompt(provider=self._provider)
            extra_tools = ["WebSearch", "WebFetch"] if self._provider == "claude" else None
            return self._run_agent(prompt, config,
                                   extra_tools=extra_tools,
                                   on_progress=on_progress)
        prompt = self.build_trend_analyst_prompt(channel, seed)
        return self._run_agent(prompt, config, on_progress=on_progress)

    def _run_codex_autoresearch(
        self,
        loop,
        config: Dict,
        on_progress: Optional[callable] = None,
    ) -> Dict:
        """Codex용 Stage 0 래칫 — Python이 라운드를 오케스트레이션."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        planning_dir = self._vault_dir / "insights" / "planning"
        planning_dir.mkdir(parents=True, exist_ok=True)
        digest_paths = self._build_stage0_digests(loop._channel)
        packet_path = self._write_stage0_context_packet(loop._channel, digest_paths)

        candidates: List[Dict] = []
        ratchet_score = 0.0
        usage_totals = {
            "total_cost_usd": 0,
            "duration_ms": 0,
            "num_turns": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_read_tokens": 0,
            "cache_creation_tokens": 0,
        }
        rounds_completed = 0

        for round_number in range(1, loop._max_rounds + 1):
            round_path = planning_dir / f"{today}-{loop._channel}-autoresearch-round-{round_number}.json"
            prompt = loop.build_codex_round_prompt(
                round_number=round_number,
                current_candidates=candidates,
                ratchet_score=ratchet_score,
                packet_path=packet_path.relative_to(self._vault_dir),
            )
            if on_progress:
                on_progress(f"Round {round_number}: candidate ratchet")
            result = self._run_agent(prompt, config, on_progress=on_progress)
            if result.get("status") != "success":
                return result
            usage_totals = self._accumulate_usage(usage_totals, result.get("usage", {}))
            round_candidates = self._load_round_candidates_from_result(result, round_path, round_number, loop._channel)
            if not round_candidates:
                return {
                    "status": "error",
                    "returncode": -1,
                    "stdout": result.get("stdout", ""),
                    "stderr": f"Codex autoresearch round output invalid or empty: {round_path}",
                    "usage": usage_totals,
                }
            candidates = self._merge_candidates(candidates, round_candidates)
            ratchet_score = max((float(c.get("topic_score", 0) or 0) for c in candidates), default=0.0)
            rounds_completed = round_number

        final_json_path = planning_dir / f"{today}-{loop._channel}-autoresearch.json"
        final_md_path = planning_dir / f"{today}-{loop._channel}-기획안.md"
        final_candidates = sorted(candidates, key=lambda c: float(c.get("topic_score", 0) or 0), reverse=True)[:5]
        final_payload = {
            "date": today,
            "channel": loop._channel,
            "rounds_completed": rounds_completed,
            "ratchet_score": ratchet_score,
            "candidates": final_candidates,
            "removed": [],
        }
        final_json_path.write_text(
            json.dumps(final_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        final_md_path.write_text(
            self._render_autoresearch_markdown(loop._channel, final_candidates),
            encoding="utf-8",
        )
        return {
            "status": "success",
            "returncode": 0,
            "stdout": str(final_json_path),
            "stderr": "",
            "usage": usage_totals,
        }

    def _build_stage0_digests(self, channel: str) -> Dict[str, Path]:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        base_dir = self._vault_dir / "insights" / "planning" / "_inputs"
        base_dir.mkdir(parents=True, exist_ok=True)

        trend_digest = base_dir / f"{today}-{channel}-trend-digest.md"
        feedback_digest = base_dir / f"{today}-{channel}-feedback-digest.md"
        channel_digest = base_dir / f"{today}-{channel}-channel-digest.md"
        competitor_digest = base_dir / f"{today}-{channel}-competitor-digest.md"
        previous_digest = base_dir / f"{today}-{channel}-previous-digest.md"

        self._write_digest(
            trend_digest,
            title="Trend + News + Social + Community Signal Digest",
            files=self._select_signal_digest_files(channel=channel),
            channel=channel,
        )
        self._write_digest(
            feedback_digest,
            title="Stage0 Feedback + Performance Learning Digest",
            files=self._select_multi_recent_files(
                [
                    self._vault_dir / "insights" / "feedback",
                    self._vault_dir / "insights" / "performance",
                ],
                limit=5,
            ),
        )
        self._write_digest(
            channel_digest,
            title=f"{channel} Channel Performance Digest",
            files=self._select_recent_files(self._vault_dir / "channels" / channel / "videos", limit=5),
        )
        self._write_digest(
            competitor_digest,
            title="Competitor Digest",
            files=self._select_competitor_files(limit=5),
        )
        self._write_digest(
            previous_digest,
            title="Previous Planning Digest",
            files=self._select_recent_planning_files(channel, limit=1),
        )

        return {
            "trend_digest": trend_digest.relative_to(self._vault_dir),
            "feedback_digest": feedback_digest.relative_to(self._vault_dir),
            "channel_digest": channel_digest.relative_to(self._vault_dir),
            "competitor_digest": competitor_digest.relative_to(self._vault_dir),
            "previous_digest": previous_digest.relative_to(self._vault_dir),
        }

    def _build_stage4_digests(self, channel: str) -> Dict[str, Path]:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        base_dir = self._vault_dir / "insights" / "performance" / "_inputs"
        base_dir.mkdir(parents=True, exist_ok=True)

        performance_digest = base_dir / f"{today}-{channel}-performance-digest.md"
        analytics_digest = base_dir / f"{today}-{channel}-analytics-digest.md"
        signal_digest = base_dir / f"{today}-{channel}-signal-digest.md"
        competitor_digest = base_dir / f"{today}-{channel}-competitor-digest.md"
        planning_digest = base_dir / f"{today}-{channel}-planning-digest.md"

        self._write_digest(
            performance_digest,
            title=f"{channel} Weekly Performance Digest",
            files=self._select_multi_recent_files(
                [
                    self._vault_dir / "channels" / channel / "videos",
                    self._vault_dir / "insights" / "performance",
                ],
                limit=6,
            ),
        )
        self._write_digest(
            analytics_digest,
            title=f"{channel} Analytics Digest",
            files=self._select_recent_files(self._vault_dir / "channels" / channel / "analytics", limit=4),
        )
        self._write_digest(
            signal_digest,
            title="Trend Signal Digest",
            files=self._select_signal_digest_files(channel=channel),
            channel=channel,
        )
        self._write_digest(
            competitor_digest,
            title="Competitor Digest",
            files=self._select_competitor_files(limit=5),
        )
        self._write_digest(
            planning_digest,
            title="Recent Planning Digest",
            files=self._select_recent_planning_files(channel, limit=2),
        )

        return {
            "performance_digest": performance_digest.relative_to(self._vault_dir),
            "analytics_digest": analytics_digest.relative_to(self._vault_dir),
            "signal_digest": signal_digest.relative_to(self._vault_dir),
            "competitor_digest": competitor_digest.relative_to(self._vault_dir),
            "planning_digest": planning_digest.relative_to(self._vault_dir),
        }

    def _prepare_stage4_output_templates(self, channel: str) -> Dict[str, Path]:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        weekly_path = self._vault_dir / "insights" / "performance" / f"{today}-{channel}-weekly-review.md"
        feedback_path = self._vault_dir / "insights" / "feedback" / f"{today}-{channel}-stage0-feedback.md"
        weekly_path.parent.mkdir(parents=True, exist_ok=True)
        feedback_path.parent.mkdir(parents=True, exist_ok=True)

        weekly_template = f"""---
type: weekly-review
channel: {channel}
period: {today}
created: {today}
tags: [performance, weekly-review]
---

## 채널 성과 요약

## 패턴 발견

## 경쟁 채널 동향

## 브리지 패턴 회고

## Stage 0 피드백 요약
"""
        feedback_template = f"""---
type: stage0-feedback
channel: {channel}
created: {today}
tags: [feedback, stage0]
---

## 성과 좋았던 주제 유형

## 성과 안 좋았던 주제 유형

## 경쟁 채널에서 배울 점

## 추천 주제 방향

## winning_bridge_patterns

## losing_bridge_patterns

## title_trigger_patterns

## competitor_lessons

## recommended_topic_directions
"""
        weekly_path.write_text(weekly_template, encoding="utf-8")
        feedback_path.write_text(feedback_template, encoding="utf-8")
        return {
            "weekly_review_path": weekly_path.relative_to(self._vault_dir),
            "feedback_path": feedback_path.relative_to(self._vault_dir),
        }

    def run_performance_analyst(
        self, mode: str, channel: str, video_id: Optional[str] = None
    ) -> Dict:
        """performance-analyst 에이전트 실행."""
        config = self._optimize_codex_agent_config(
            "performance-analyst",
            self._agents_config.get("agents", {}).get("performance-analyst", {}),
        )
        if self._provider == "codex" and mode != "video":
            return self._run_codex_performance_analyst(mode, channel, config)
        prompt = self.build_performance_analyst_prompt(mode, channel, video_id)
        return self._run_agent(prompt, config)

    def _run_codex_performance_analyst(self, mode: str, channel: str, config: Dict) -> Dict:
        digest_paths = self._build_stage4_digests(channel)
        output_paths = self._prepare_stage4_output_templates(channel)
        weekly_abs = self._vault_dir / output_paths["weekly_review_path"]
        feedback_abs = self._vault_dir / output_paths["feedback_path"]
        weekly_before = weekly_abs.read_text(encoding="utf-8")
        feedback_before = feedback_abs.read_text(encoding="utf-8")

        usage_totals = {
            "total_cost_usd": 0,
            "duration_ms": 0,
            "num_turns": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_read_tokens": 0,
            "cache_creation_tokens": 0,
        }

        weekly_prompt = self.build_codex_weekly_review_prompt(channel, digest_paths, output_paths)
        weekly_result = self._run_agent(weekly_prompt, config)
        if weekly_result.get("status") != "success":
            return weekly_result
        usage_totals = self._accumulate_usage(usage_totals, weekly_result.get("usage", {}))

        feedback_prompt = self.build_codex_stage0_feedback_prompt(channel, digest_paths, output_paths)
        feedback_result = self._run_agent(feedback_prompt, config)
        if feedback_result.get("status") != "success":
            return feedback_result
        usage_totals = self._accumulate_usage(usage_totals, feedback_result.get("usage", {}))

        weekly_after = weekly_abs.read_text(encoding="utf-8")
        feedback_after = feedback_abs.read_text(encoding="utf-8")
        if weekly_after == weekly_before or feedback_after == feedback_before:
            return {
                "status": "error",
                "returncode": -1,
                "stdout": "",
                "stderr": "Codex performance analysis did not update one or more output templates",
                "usage": usage_totals,
            }
        return {
            "status": "success",
            "returncode": 0,
            "stdout": str(weekly_abs),
            "stderr": "",
            "usage": usage_totals,
        }

    # ── 프롬프트 빌더 ──

    def build_trend_analyst_prompt(self, channel: str, seed: Optional[str] = None) -> str:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        skill_content = self._load_skill("agents/trend-analyst/SKILL.md")
        shared_skills = self._load_shared_skills(["market-analysis"])

        if seed:
            mode_text = f"""## 실행 모드: 시드 모드
사용자 키워드: "{seed}"
이 키워드를 기반으로 볼트에서 관련 데이터를 탐색하고,
트렌드 적합성 + 채널 적합성을 검증하여 기획안 1개를 구체화하세요."""
        else:
            mode_text = """## 실행 모드: 자율 모드
볼트의 트렌드, 채널 성과, 경쟁 채널 데이터를 교차 분석하여
주제 후보 3~5개를 순위화한 기획안을 생성하세요."""

        return f"""# trend-analyst 에이전트 실행

날짜: {today}
채널: {channel}

{mode_text}

## 볼트 구조
- 트렌드 신호: market/trends/, market/news/, market/social/, market/communities/
- 채널 성과: channels/{channel}/videos/
- 경쟁 채널: channels/competitors/
- 기존 피드백: insights/feedback/
- 기존 기획안: insights/planning/

## 출력
기획안을 insights/planning/{today}-기획안.md 로 저장하세요.
후보마다 `trigger_keyword`, `knowledge_anchor`, `bridge_reason`, `timing_window`를 반드시 포함하세요.
실시간 화제만 나열하지 말고, 왜 이 채널이 이 주제를 지금 풀어야 하는지 브리지 논리를 적으세요.

{skill_content}

{shared_skills}

{self._load_shared_skills(["trend-bridge-planning"])}
"""

    def build_codex_performance_analyst_prompt(self, mode: str, channel: str) -> str:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        digest_paths = self._build_stage4_digests(channel)
        output_paths = self._prepare_stage4_output_templates(channel)
        digest_lines = "\n".join(f"- {label}: `{path}`" for label, path in digest_paths.items())
        return f"""# Stage 4 Codex Weekly Analysis

날짜: {today}
채널: {channel}
모드: {mode}

## 목표
업로드 성과, 경쟁 채널, 최신 신호를 함께 보고
1. weekly review를 `{output_paths["weekly_review_path"]}`에 작성
2. stage0 feedback를 `{output_paths["feedback_path"]}`에 작성

## 읽을 입력 파일
아래 digest 파일만 읽으세요. raw 디렉터리를 직접 훑지 마세요.
{digest_lines}

## 수정할 출력 파일
- weekly review: `{output_paths["weekly_review_path"]}`
- stage0 feedback: `{output_paths["feedback_path"]}`
- 이미 템플릿이 만들어져 있으니 섹션을 채우는 방식으로 수정하세요

## 필수 규칙
- `winning_bridge_patterns`
- `losing_bridge_patterns`
- `title_trigger_patterns`
- `competitor_lessons`
- `recommended_topic_directions`
를 feedback에 반드시 포함
- 외부 웹 검색 금지
- 근거는 digest에 나온 원본 파일 경로를 따라 설명

## 분석 원칙
- 조회수만 보지 말고 주제 유형, 제목 트리거, 브리지 패턴을 본다
- `trigger_keyword -> knowledge_anchor` 연결이 먹힌 사례와 실패 사례를 나눈다
- 경쟁 채널이 이미 같은 각도로 선점했는지 확인한다
- 다음 Stage 0가 바로 쓸 수 있게 구체적인 주제 방향으로 적는다
- weekly review는 요약 중심, feedback은 의사결정 중심으로 쓴다

완료 후 두 파일을 저장했다는 짧은 메시지만 남기세요.
"""

    def build_codex_weekly_review_prompt(
        self,
        channel: str,
        digest_paths: Dict[str, Path],
        output_paths: Dict[str, Path],
    ) -> str:
        digest_lines = "\n".join(
            f"- {label}: `{path}`"
            for label, path in digest_paths.items()
            if label in {"performance_digest", "analytics_digest", "signal_digest", "competitor_digest", "planning_digest"}
        )
        return f"""# Stage 4 Codex Weekly Review

채널: {channel}

## 목표
`{output_paths["weekly_review_path"]}` 파일만 채우세요.

## 읽을 입력 파일
{digest_lines}

## 반드시 채울 섹션
- 채널 성과 요약
- 패턴 발견
- 경쟁 채널 동향
- 브리지 패턴 회고
- Stage 0 피드백 요약

## 규칙
- 외부 웹 검색 금지
- 템플릿 구조 유지
- 핵심만 간결하게 작성

완료 후 짧게 완료 메시지만 남기세요.
"""

    def build_codex_stage0_feedback_prompt(
        self,
        channel: str,
        digest_paths: Dict[str, Path],
        output_paths: Dict[str, Path],
    ) -> str:
        digest_lines = "\n".join(
            f"- {label}: `{path}`"
            for label, path in digest_paths.items()
            if label in {"performance_digest", "analytics_digest", "signal_digest", "competitor_digest", "planning_digest"}
        )
        return f"""# Stage 4 Codex Stage0 Feedback

채널: {channel}

## 목표
`{output_paths["feedback_path"]}` 파일만 채우세요.

## 읽을 입력 파일
{digest_lines}

## 반드시 채울 섹션
- 성과 좋았던 주제 유형
- 성과 안 좋았던 주제 유형
- 경쟁 채널에서 배울 점
- 추천 주제 방향
- winning_bridge_patterns
- losing_bridge_patterns
- title_trigger_patterns
- competitor_lessons
- recommended_topic_directions

## 규칙
- 외부 웹 검색 금지
- 템플릿 구조 유지
- Stage 0가 바로 쓸 수 있게 구체적으로 작성

완료 후 짧게 완료 메시지만 남기세요.
"""

    def build_performance_analyst_prompt(
        self, mode: str, channel: str, video_id: Optional[str] = None
    ) -> str:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        skill_content = self._load_skill("agents/performance-analyst/SKILL.md")
        shared_skills = self._load_shared_skills(["channel-metrics", "market-analysis"])

        if mode == "video" and video_id:
            mode_text = f"""## 실행 모드: 영상 성과 분석
영상 ID: {video_id}
channels/{channel}/videos/ 에서 해당 영상 노트를 찾아 성과를 분석하세요.
기획안의 예상 성과 대비 실제 달성률을 평가하세요."""
        else:
            mode_text = f"""## 실행 모드: 주간 종합 리뷰
이번 주 {channel} 채널의 전체 성과를 분석하세요.
경쟁 채널 동향을 확인하고 watchlist 리뷰를 수행하세요.
Stage 0 피드백을 insights/feedback/ 에 저장하세요."""

        return f"""# performance-analyst 에이전트 실행

날짜: {today}
채널: {channel}

{mode_text}

## 볼트 구조
- 채널 성과: channels/{channel}/videos/
- 채널 Analytics: channels/{channel}/analytics/
- 경쟁 채널: channels/competitors/
- 트렌드 신호: market/trends/, market/news/, market/social/, market/communities/
- 기존 인사이트: insights/performance/
- 피드백 출력: insights/feedback/

## 출력 강제 규칙
- weekly 리뷰에는 `브리지 패턴 회고`를 포함
- Stage 0 피드백에는 아래 필드를 반드시 포함
  - `winning_bridge_patterns`
  - `losing_bridge_patterns`
  - `title_trigger_patterns`
  - `competitor_lessons`
  - `recommended_topic_directions`

{skill_content}

{shared_skills}

{self._load_shared_skills(["trend-bridge-planning"])}
"""

    # ── Claude CLI 실행 ──

    def _run_agent(self, prompt: str, config: Dict,
                   extra_tools: Optional[List[str]] = None,
                   on_progress: Optional[callable] = None,
                   cwd_override: Optional[Path] = None) -> Dict:
        """Claude CLI로 에이전트 실행.

        Args:
            on_progress: 콜백 함수(message: str). 스트리밍 이벤트 발생 시 호출.
        """
        model = self._resolve_model(config.get("model", "sonnet"))
        reasoning_effort = str(config.get("reasoning_effort", "medium"))
        max_turns = config.get("max_turns", 30)
        timeout = config.get("max_duration_minutes", 15) * 60

        streaming = on_progress is not None
        output_last_message = None
        if self._provider == "claude":
            cmd = self._build_claude_cmd(
                model=model, max_turns=max_turns,
                extra_tools=extra_tools,
                streaming=streaming,
            )
        else:
            fd, output_last_message = tempfile.mkstemp(prefix="codex-agent-last-", suffix=".txt")
            os.close(fd)
            cmd = self._build_codex_cmd(
                model=model,
                reasoning_effort=reasoning_effort,
                output_last_message=output_last_message,
                workdir=cwd_override,
            )

        env = os.environ.copy()
        env.pop("CLAUDECODE", None)

        if streaming:
            return self._run_agent_streaming(
                cmd, prompt, env, timeout, on_progress, output_last_message=output_last_message, cwd_override=cwd_override
            )
        else:
            return self._run_agent_batch(cmd, prompt, env, timeout, output_last_message=output_last_message, cwd_override=cwd_override)

    def _run_agent_batch(self, cmd, prompt, env, timeout, output_last_message: Optional[str] = None, cwd_override: Optional[Path] = None) -> Dict:
        """배치 모드 — 결과만 반환."""
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(cwd_override or self._vault_dir),
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                **subprocess_kwargs(),
            )
            stdout, stderr = proc.communicate(input=prompt, timeout=timeout)

            usage = self._parse_usage(stdout)
            if self._provider == "codex" and output_last_message:
                stdout = self._read_output_last_message(output_last_message, fallback=stdout)
            return {
                "status": "success" if proc.returncode == 0 else "error",
                "returncode": proc.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "usage": usage,
            }
        except subprocess.TimeoutExpired:
            proc.kill()
            return {"status": "timeout", "returncode": -1, "stdout": "", "stderr": "timeout"}
        except Exception as e:
            return {"status": "error", "returncode": -1, "stdout": "", "stderr": str(e)}
        finally:
            self._cleanup_tempfile(output_last_message)

    def _run_agent_streaming(self, cmd, prompt, env, timeout, on_progress, output_last_message: Optional[str] = None, cwd_override: Optional[Path] = None) -> Dict:
        """스트리밍 모드 — 과정을 on_progress 콜백으로 전달."""
        import threading

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(cwd_override or self._vault_dir),
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                **subprocess_kwargs(),
            )
            # stdin에 프롬프트 전달 후 닫기
            proc.stdin.write(prompt)
            proc.stdin.close()

            # stderr를 별도 스레드로 수집
            stderr_lines = []
            def read_stderr():
                for line in proc.stderr:
                    stderr_lines.append(line)
            t = threading.Thread(target=read_stderr, daemon=True)
            t.start()

            # stdout에서 stream-json 이벤트 파싱
            last_result = None
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                etype = event.get("type", "")

                if self._provider == "codex" and etype == "item.completed":
                    item = event.get("item", {})
                    if item.get("type") == "agent_message":
                        text = item.get("text", "").strip()
                        if text:
                            on_progress(text[:200])

                # 도구 호출 감지
                if self._provider == "claude" and etype == "assistant" and "tool_use" in str(event.get("message", {}).get("content", "")):
                    content = event.get("message", {}).get("content", [])
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            tool = block.get("name", "")
                            inp = block.get("input", {})
                            if tool == "WebSearch":
                                query = inp.get("query", inp.get("pattern", ""))
                                on_progress(f"🔍 WebSearch: {query[:80]}")
                            elif tool == "WebFetch":
                                url = inp.get("url", "")[:80]
                                on_progress(f"🌐 WebFetch: {url}")
                            elif tool == "Write":
                                path = inp.get("file_path", "")
                                fname = Path(path).name if path else ""
                                on_progress(f"📝 Write: {fname}")
                            elif tool == "Glob":
                                pattern = inp.get("pattern", "")
                                on_progress(f"📂 Glob: {pattern[:60]}")

                # 최종 결과
                if etype == "result":
                    last_result = event
                elif self._provider == "codex" and etype == "turn.completed":
                    last_result = event

            proc.wait(timeout=30)
            t.join(timeout=5)

            usage = {}
            if last_result:
                if self._provider == "codex":
                    usage = {
                        "total_cost_usd": 0,
                        "duration_ms": 0,
                        "num_turns": 1,
                        "input_tokens": last_result.get("usage", {}).get("input_tokens", 0),
                        "output_tokens": last_result.get("usage", {}).get("output_tokens", 0),
                        "cache_read_tokens": last_result.get("usage", {}).get("cached_input_tokens", 0),
                        "cache_creation_tokens": 0,
                    }
                else:
                    usage = {
                        "total_cost_usd": last_result.get("total_cost_usd", 0),
                        "duration_ms": last_result.get("duration_ms", 0),
                        "num_turns": last_result.get("num_turns", 0),
                        "input_tokens": last_result.get("usage", {}).get("input_tokens", 0),
                        "output_tokens": last_result.get("usage", {}).get("output_tokens", 0),
                        "cache_read_tokens": last_result.get("usage", {}).get("cache_read_input_tokens", 0),
                        "cache_creation_tokens": last_result.get("usage", {}).get("cache_creation_input_tokens", 0),
                    }

            return {
                "status": "success" if proc.returncode == 0 else "error",
                "returncode": proc.returncode,
                "stdout": self._read_output_last_message(output_last_message, fallback=json.dumps(last_result) if last_result else ""),
                "stderr": "".join(stderr_lines),
                "usage": usage,
            }
        except subprocess.TimeoutExpired:
            proc.kill()
            return {"status": "timeout", "returncode": -1, "stdout": "", "stderr": "timeout"}
        except Exception as e:
            return {"status": "error", "returncode": -1, "stdout": "", "stderr": str(e)}
        finally:
            self._cleanup_tempfile(output_last_message)

    def _parse_usage(self, stdout: str) -> Dict:
        """provider별 JSON 출력에서 토큰 사용량 파싱."""
        if self._provider == "codex":
            return self._parse_usage_from_codex_jsonl(stdout)
        return self._parse_usage_from_claude_json(stdout)

    def _parse_usage_from_claude_json(self, stdout: str) -> Dict:
        """Claude JSON 출력에서 토큰 사용량 파싱."""
        try:
            cli_result = json.loads(stdout)
            return {
                "total_cost_usd": cli_result.get("total_cost_usd", 0),
                "duration_ms": cli_result.get("duration_ms", 0),
                "num_turns": cli_result.get("num_turns", 0),
                "input_tokens": cli_result.get("usage", {}).get("input_tokens", 0),
                "output_tokens": cli_result.get("usage", {}).get("output_tokens", 0),
                "cache_read_tokens": cli_result.get("usage", {}).get("cache_read_input_tokens", 0),
                "cache_creation_tokens": cli_result.get("usage", {}).get("cache_creation_input_tokens", 0),
            }
        except (json.JSONDecodeError, AttributeError):
            return {}

    def _parse_usage_from_codex_jsonl(self, stdout: str) -> Dict:
        """Codex JSONL 출력에서 토큰 사용량 파싱."""
        usage = {}
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "turn.completed":
                turn_usage = event.get("usage", {})
                usage = {
                    "total_cost_usd": 0,
                    "duration_ms": 0,
                    "num_turns": 1,
                    "input_tokens": turn_usage.get("input_tokens", 0),
                    "output_tokens": turn_usage.get("output_tokens", 0),
                    "cache_read_tokens": turn_usage.get("cached_input_tokens", 0),
                    "cache_creation_tokens": 0,
                }
        return usage

    def _optimize_codex_agent_config(self, agent_name: str, config: Dict) -> Dict:
        if self._provider != "codex":
            return config
        optimized = dict(config)
        if agent_name in {"trend-analyst", "performance-analyst"}:
            if not os.getenv("AUTO_AGENT_CODEX_MODEL", "").strip() and optimized.get("model") == "opus":
                optimized["model"] = "sonnet"
            optimized.setdefault("reasoning_effort", os.getenv("AUTO_AGENT_CODEX_REASONING_EFFORT", "low"))
        return optimized

    def _extract_json_payload(self, text: str) -> Optional[Dict]:
        payload = (text or "").strip()
        if not payload:
            return None
        candidates = [payload]
        if "```json" in payload:
            parts = payload.split("```json")
            for part in parts[1:]:
                candidates.append(part.split("```", 1)[0].strip())
        if "```" in payload:
            parts = payload.split("```")
            for idx, part in enumerate(parts):
                if idx % 2 == 1:
                    candidates.append(part.strip())
        start = payload.find("{")
        end = payload.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidates.append(payload[start:end + 1])
        for candidate in candidates:
            try:
                data = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                return data
        return None

    def _load_round_candidates_from_result(
        self,
        result: Dict,
        round_path: Path,
        round_number: int,
        channel: str,
    ) -> List[Dict]:
        payload = self._extract_json_payload(result.get("stdout", ""))
        if isinstance(payload, dict):
            if "round" not in payload:
                payload["round"] = round_number
            if "channel" not in payload:
                payload["channel"] = channel
            round_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            candidates = payload.get("candidates", [])
            return candidates if isinstance(candidates, list) else []
        if round_path.exists():
            return self._load_round_candidates(round_path)
        return []

    def _load_round_candidates(self, round_path: Path) -> List[Dict]:
        try:
            data = json.loads(round_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        candidates = data.get("candidates", [])
        return candidates if isinstance(candidates, list) else []

    def _merge_candidates(self, existing: List[Dict], new_candidates: List[Dict]) -> List[Dict]:
        merged: Dict[str, Dict] = {}
        for candidate in existing + new_candidates:
            title = str(candidate.get("title", "")).strip()
            if not title:
                continue
            key = title.casefold()
            score = float(candidate.get("topic_score", 0) or 0)
            prev = merged.get(key)
            prev_score = float(prev.get("topic_score", 0) or 0) if prev else -1
            if prev is None or score >= prev_score:
                merged[key] = candidate
        return sorted(
            merged.values(),
            key=lambda c: float(c.get("topic_score", 0) or 0),
            reverse=True,
        )[:5]

    def _build_stage0_context_snapshot(self, digest_paths: Dict[str, Path]) -> str:
        caps = {
            "trend_digest": 1200,
            "feedback_digest": 800,
            "channel_digest": 500,
            "competitor_digest": 700,
            "previous_digest": 200,
        }
        labels = {
            "trend_digest": "트렌드/뉴스/커뮤니티",
            "feedback_digest": "성과 피드백",
            "channel_digest": "채널 최근 성과",
            "competitor_digest": "경쟁 채널",
            "previous_digest": "이전 기획",
        }
        chunks: List[str] = []
        for key, rel_path in digest_paths.items():
            path = self._vault_dir / rel_path
            if not path.exists():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore").strip()
            except OSError:
                continue
            limit = caps.get(key, 800)
            if path.suffix.lower() == ".md":
                text = self._compact_markdown_excerpt(text, limit)
            if len(text) > limit:
                text = text[:limit].rstrip() + "\n...(truncated)"
            chunks.append(f"## {labels.get(key, key)}\n{text}")
        return "\n\n".join(chunks)

    def _write_stage0_context_packet(self, channel: str, digest_paths: Dict[str, Path]) -> Path:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        packet_path = self._vault_dir / "insights" / "planning" / "_inputs" / f"{today}-{channel}-autoresearch-packet.md"
        packet_path.parent.mkdir(parents=True, exist_ok=True)
        packet_path.write_text(self._build_stage0_context_snapshot(digest_paths), encoding="utf-8")
        return packet_path

    def _compact_markdown_excerpt(self, text: str, limit: int) -> str:
        lines = text.splitlines()
        compact: List[str] = []
        in_frontmatter = False
        frontmatter_started = False
        for raw in lines:
            line = raw.strip()
            if line == "---":
                if not frontmatter_started and not compact:
                    frontmatter_started = True
                    in_frontmatter = True
                    continue
                if in_frontmatter:
                    in_frontmatter = False
                continue
            if in_frontmatter:
                continue
            if not line:
                continue
            if line.startswith("#") or line.startswith("-") or line.startswith("*") or re.match(r"^\d+\.", line):
                compact.append(line)
            elif not compact:
                compact.append(line)
            if len("\n".join(compact)) >= limit:
                break
        return "\n".join(compact)[:limit]

    def _select_recent_files(self, directory: Path, limit: int) -> List[Path]:
        if not directory.exists():
            return []
        files = [p for p in directory.rglob("*") if p.is_file() and p.suffix.lower() in {".md", ".json", ".jsonl"}]
        files.sort(key=lambda p: (p.stat().st_mtime, str(p)), reverse=True)
        return files[:limit]

    def _select_multi_recent_files(self, directories: List[Path], limit: int) -> List[Path]:
        files: List[Path] = []
        seen = set()
        for directory in directories:
            for path in self._select_recent_files(directory, limit=limit):
                if path in seen:
                    continue
                seen.add(path)
                files.append(path)
        files.sort(key=lambda p: (p.stat().st_mtime, str(p)), reverse=True)
        return files[:limit]

    def _select_competitor_files(self, limit: int) -> List[Path]:
        competitor_dir = self._vault_dir / "channels" / "competitors"
        if not competitor_dir.exists():
            return []
        overviews = [p for p in competitor_dir.rglob("_overview.md") if p.is_file()]
        overviews.sort(key=lambda p: (p.stat().st_mtime, str(p)), reverse=True)
        return overviews[:limit]

    def _select_signal_digest_files(self, channel: Optional[str] = None) -> List[Path]:
        files: List[Path] = []
        files.extend(self._select_recent_files(self._vault_dir / "market" / "trends", limit=2))
        files.extend(self._select_relevant_signal_files(self._vault_dir / "market" / "news", limit=4, channel=channel))
        files.extend(self._select_relevant_signal_files(self._vault_dir / "market" / "social", limit=2, channel=channel))
        files.extend(self._select_relevant_signal_files(self._vault_dir / "market" / "communities", limit=5, channel=channel))
        deduped: List[Path] = []
        seen = set()
        for path in files:
            if path in seen:
                continue
            seen.add(path)
            deduped.append(path)
        deduped.sort(key=lambda p: (p.stat().st_mtime, str(p)), reverse=True)
        return deduped

    def _select_relevant_signal_files(self, directory: Path, limit: int, channel: Optional[str]) -> List[Path]:
        files = self._select_recent_files(directory, limit=max(limit * 3, limit))
        if not channel or not files:
            return files[:limit]

        scored = []
        for path in files:
            scored.append((self._score_signal_file(path, channel), path))

        positive = [pair for pair in scored if pair[0] > 0]
        if positive:
            positive.sort(key=lambda pair: (pair[0], pair[1].stat().st_mtime, str(pair[1])), reverse=True)
            return [path for _, path in positive[:limit]]

        return files[:limit]

    def _score_signal_file(self, path: Path, channel: str) -> int:
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return 0
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            return 0

        items = payload.get("items")
        if not isinstance(items, list):
            return 0

        source_name = str(
            payload.get("source")
            or payload.get("source_name")
            or payload.get("name")
            or self._derive_signal_source_name(path)
            or ""
        ).strip()
        profile = self._get_signal_profile(channel)
        if source_name and source_name in set(profile.get("blocked_sources", [])):
            return -999
        scores = [
            self._score_signal_item(item, channel=channel, source_name=source_name)
            for item in items
            if isinstance(item, dict)
        ]
        if not scores:
            return 0
        scores.sort(reverse=True)
        return sum(scores[:3])

    def _derive_signal_source_name(self, path: Path) -> str:
        stem = path.stem
        if re.match(r"^\d{4}-\d{2}-\d{2}-", stem):
            return stem.split("-", 3)[-1]
        return stem

    def _select_recent_planning_files(self, channel: str, limit: int) -> List[Path]:
        planning_dir = self._vault_dir / "insights" / "planning"
        if not planning_dir.exists():
            return []
        files = [
            p for p in planning_dir.glob(f"*-{channel}-autoresearch.json")
            if p.is_file()
        ]
        files.sort(key=lambda p: (p.stat().st_mtime, str(p)), reverse=True)
        return files[:limit]

    def _write_digest(self, output_path: Path, title: str, files: List[Path], channel: Optional[str] = None) -> None:
        lines = [f"# {title}", ""]
        if not files:
            lines.append("없음")
            output_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
            return
        for file_path in files:
            rel = file_path.relative_to(self._vault_dir)
            lines.append(f"## {rel}")
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore").strip()
            except OSError:
                content = ""
            excerpt = self._render_digest_excerpt(file_path, content, channel=channel)
            lines.append(excerpt if excerpt else "(empty)")
            lines.append("")
        output_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")

    def _render_digest_excerpt(self, file_path: Path, content: str, channel: Optional[str] = None) -> str:
        rel = file_path.relative_to(self._vault_dir)
        if rel.parts[:2] and rel.parts[0] == "market" and file_path.suffix.lower() == ".json":
            summary = self._summarize_signal_json(
                content,
                channel=channel,
                source_name_hint=self._derive_signal_source_name(file_path),
            )
            if summary:
                return summary
        return content[:1600]

    def _summarize_signal_json(
        self,
        content: str,
        channel: Optional[str] = None,
        source_name_hint: str = "",
    ) -> str:
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            return content[:1600]
        items = payload.get("items")
        if not isinstance(items, list):
            return content[:1600]
        source_name = str(
            payload.get("source")
            or payload.get("source_name")
            or payload.get("name")
            or source_name_hint
            or ""
        ).strip()

        scored = []
        for item in items:
            if not isinstance(item, dict):
                continue
            score = self._score_signal_item(item, channel=channel, source_name=source_name)
            scored.append((score, item))

        positives = sorted(
            [(score, item) for score, item in scored if score > 0],
            key=lambda pair: pair[0],
            reverse=True,
        )
        neutrals = sorted(
            [(score, item) for score, item in scored if score == 0],
            key=lambda pair: pair[0],
            reverse=True,
        )
        negatives = sorted(
            [(score, item) for score, item in scored if score < 0],
            key=lambda pair: pair[0],
            reverse=True,
        )

        if positives:
            selected = positives[:5]
            neutral_slots = max(0, min(2, 6 - len(selected)))
            if neutral_slots:
                selected.extend(neutrals[:neutral_slots])
        else:
            selected = neutrals[:6] or negatives[:3]
        selected = selected[:8]

        lines = []
        for score, item in selected:
            title = str(item.get("title") or item.get("keyword") or "").strip()
            summary = str(item.get("summary") or "").strip()
            link = str(item.get("link") or "").strip()
            if not title and not summary:
                continue
            lead = title or summary[:120]
            line = f"- [{score}] {lead}"
            if summary and summary != lead:
                line += f" | {summary[:140]}"
            lines.append(line)
        return "\n".join(lines)[:1600]

    def _score_signal_item(self, item: Dict, channel: Optional[str] = None, source_name: str = "") -> int:
        text = " ".join(
            str(item.get(key) or "").strip()
            for key in ("title", "keyword", "summary")
        ).lower()
        score = 0

        positive_patterns = [
            r"왜", r"이유", r"배경", r"역사", r"기원", r"계보", r"원리", r"구조",
            r"세금", r"실수령", r"얼마", r"계산", r"정책", r"제도", r"경제", r"상여금",
            r"반도체", r"기업", r"브랜드", r"시장", r"전쟁", r"ai", r"기술", r"흑백요리사",
            r"다시 뜨", r"화제", r"논란", r"무슨", r"어떻게", r"실록", r"왕조", r"조선",
            r"미스터리", r"유래", r"차이점", r"차이", r"문파", r"계파", r"정체",
            r"비밀", r"근거", r"논알콜", r"무알콜",
        ]
        negative_patterns = [
            r"\bvs\b", r"야구", r"축구", r"농구", r"경기", r"선수", r"홈런", r"골", r"gif",
            r"출석", r"잡담", r"삭제된 게시물", r"공지", r"홍보", r"이벤트", r"부친상",
            r"감량", r"강아지", r"고양이", r"레시피", r"드라마", r"콘서트",
        ]

        for pattern in positive_patterns:
            if re.search(pattern, text):
                score += 2
        for pattern in negative_patterns:
            if re.search(pattern, text):
                score -= 3

        profile = self._get_signal_profile(channel)
        if profile:
            for pattern in profile.get("positive_patterns", []):
                if re.search(pattern, text):
                    score += 2
            for pattern in profile.get("negative_patterns", []):
                if re.search(pattern, text):
                    score -= 2
            score += int(profile.get("source_boosts", {}).get(source_name, 0))
            score += int(profile.get("source_penalties", {}).get(source_name, 0))

        title = str(item.get("title") or item.get("keyword") or "")
        if "?" in title or "얼마" in title or "왜" in title:
            score += 2
        return score

    def _get_signal_profile(self, channel: Optional[str]) -> Dict:
        if not channel:
            return {}
        normalized = str(channel).strip().casefold()
        for name, profile in CHANNEL_SIGNAL_PROFILES.items():
            if normalized == name.casefold():
                return profile
        if "ai" in normalized:
            return CHANNEL_SIGNAL_PROFILES.get("ai백과사전", {})
        return {}

    def _render_autoresearch_markdown(self, channel: str, candidates: List[Dict]) -> str:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        lines = [
            "---",
            "type: planning",
            "mode: autonomous",
            f"channel: {channel}",
            f"created: {today}",
            "status: proposed",
            "---",
            "",
        ]
        for idx, candidate in enumerate(candidates[:3], start=1):
            title = candidate.get("title", "")
            score = candidate.get("topic_score", 0)
            trigger_keyword = candidate.get("trigger_keyword", "")
            knowledge_anchor = candidate.get("knowledge_anchor", "")
            bridge_reason = candidate.get("bridge_reason", "")
            timing_window = candidate.get("timing_window", "")
            angle = candidate.get("angle", "")
            reason = candidate.get("selection_reason", "")
            brief = candidate.get("creative_brief", {}) or {}
            story_points = brief.get("story_points", []) or []
            episodes = brief.get("must_include_episodes", []) or []
            lines.extend(
                [
                    f"[{idx}/{min(len(candidates), 3)}] [{score}점] {title}",
                    f"트리거: {trigger_keyword}",
                    f"앵커: {knowledge_anchor}",
                    f"브리지: {bridge_reason}",
                    f"타이밍: {timing_window}",
                    f"앵글: {angle}",
                    f"선정 사유: {reason}",
                    f"길이/톤: {brief.get('recommended_length', '')} | {brief.get('tone', '')}",
                    "이야기 포인트:",
                ]
            )
            for point in story_points[:3]:
                lines.append(f"- {point}")
            lines.append("필수 에피소드:")
            for episode in episodes[:4]:
                lines.append(f"- {episode}")
            lines.append("")
        return "\n".join(lines).strip() + "\n"

    def _accumulate_usage(self, total: Dict, delta: Dict) -> Dict:
        merged = dict(total)
        for key, value in (delta or {}).items():
            if isinstance(value, (int, float)):
                merged[key] = merged.get(key, 0) + value
        return merged

    def _resolve_model(self, model: str) -> str:
        if self._provider == "claude":
            return model
        override = os.getenv("AUTO_AGENT_CODEX_MODEL", "").strip()
        if override:
            return override
        mapped = {
            "opus": "gpt-5.4",
            "sonnet": "gpt-5.4-mini",
            "haiku": "gpt-5.4-mini",
        }
        return mapped.get(model, model)

    def _build_claude_cmd(self, model: str, max_turns: int,
                          extra_tools: Optional[List[str]] = None,
                          streaming: bool = False) -> List[str]:
        """Claude CLI 명령어 빌드."""
        cli_path = self._find_claude_cli()
        tools = ["Read", "Write", "Glob", "Grep"]
        if extra_tools:
            tools.extend(extra_tools)
        output_format = "stream-json" if streaming else "json"
        cmd = [
            cli_path, "--print", "--output-format", output_format,
            "--model", model, "--max-turns", str(max_turns),
        ]
        for tool in tools:
            cmd += ["--allowedTools", tool]
        return cmd

    def _build_codex_cmd(
        self,
        model: str,
        reasoning_effort: str,
        output_last_message: str,
        workdir: Optional[Path] = None,
    ) -> List[str]:
        """Codex CLI 명령어 빌드 — 공용 유틸 위임."""
        return codex_cli_util.build_codex_exec_cmd(
            workdir=workdir or self._vault_dir,
            output_last_message=output_last_message,
            model=model,
            reasoning_effort=reasoning_effort,
        )

    def _find_claude_cli(self) -> str:
        """Claude CLI 바이너리 경로."""
        import shutil
        path = shutil.which("claude")
        if path:
            return path
        raise FileNotFoundError("Claude CLI를 찾을 수 없습니다. 'claude'가 PATH에 있는지 확인하세요.")

    def _find_codex_cli(self) -> str:
        """Codex CLI 바이너리 경로 — 공용 유틸 위임."""
        return codex_cli_util.find_codex_cli()

    def _read_output_last_message(self, path: Optional[str], fallback: str = "") -> str:
        """출력 마지막 메시지 읽기 — 공용 유틸 위임."""
        return codex_cli_util.read_output_last_message(path, fallback)

    def _cleanup_tempfile(self, path: Optional[str]) -> None:
        if not path:
            return
        try:
            Path(path).unlink(missing_ok=True)
        except Exception:
            pass

    # ── 스킬 로딩 ──

    def _load_skill(self, relative_path: str) -> str:
        path = self._data_dir / "skills" / relative_path
        if path.exists():
            return path.read_text(encoding="utf-8")
        logger.warning("스킬 파일 없음: %s", path)
        return ""

    def _load_shared_skills(self, skill_names: List[str]) -> str:
        parts = []
        for name in skill_names:
            content = self._load_skill(f"shared/{name}.md")
            if content:
                parts.append(content)
        return "\n\n---\n\n".join(parts)

    def _load_agents_config(self) -> Dict:
        path = self._data_dir / "agents.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}
