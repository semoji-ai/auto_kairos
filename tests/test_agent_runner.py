"""에이전트 실행 래퍼 테스트."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from auto_agent.modules.auto_research_loop import AutoResearchLoop
from auto_agent.modules.agent_runner import AgentRunner


@pytest.fixture
def runner(tmp_path, monkeypatch):
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    (vault_dir / "insights" / "planning").mkdir(parents=True)
    monkeypatch.setenv("KAIROS_VAULT_DIR", str(vault_dir))
    return AgentRunner()


class TestBuildPrompt:
    def test_trend_analyst_autonomous(self, runner):
        prompt = runner.build_trend_analyst_prompt(channel="이로미즘", seed=None)
        assert "이로미즘" in prompt
        assert "자율 모드" in prompt
        assert "기획안" in prompt
        assert "trigger_keyword" in prompt
        assert "knowledge_anchor" in prompt

    def test_trend_analyst_seeded(self, runner):
        prompt = runner.build_trend_analyst_prompt(channel="이로미즘", seed="희토류 전쟁")
        assert "희토류 전쟁" in prompt
        assert "시드 모드" in prompt

    def test_performance_analyst_video(self, runner):
        prompt = runner.build_performance_analyst_prompt(
            mode="video", channel="이로미즘", video_id="abc123"
        )
        assert "abc123" in prompt
        assert "영상 성과" in prompt

    def test_performance_analyst_weekly(self, runner):
        prompt = runner.build_performance_analyst_prompt(
            mode="weekly", channel="이로미즘"
        )
        assert "주간 리뷰" in prompt
        assert "winning_bridge_patterns" in prompt

    def test_codex_performance_analyst_prompt_builds_digests(self, tmp_path, monkeypatch):
        vault_dir = tmp_path / "vault"
        (vault_dir / "insights" / "performance").mkdir(parents=True)
        (vault_dir / "insights" / "planning").mkdir(parents=True)
        (vault_dir / "channels" / "이로미즘" / "videos").mkdir(parents=True)
        (vault_dir / "channels" / "이로미즘" / "analytics").mkdir(parents=True)
        (vault_dir / "channels" / "competitors" / "지식한입").mkdir(parents=True)
        (vault_dir / "market" / "trends").mkdir(parents=True)
        (vault_dir / "market" / "news").mkdir(parents=True)
        (vault_dir / "market" / "social").mkdir(parents=True)
        (vault_dir / "market" / "communities").mkdir(parents=True)
        (vault_dir / "channels" / "이로미즘" / "videos" / "v.md").write_text("video", encoding="utf-8")
        (vault_dir / "channels" / "이로미즘" / "analytics" / "a.json").write_text("{}", encoding="utf-8")
        (vault_dir / "channels" / "competitors" / "지식한입" / "_overview.md").write_text("competitor", encoding="utf-8")
        (vault_dir / "market" / "news" / "n.md").write_text("news", encoding="utf-8")
        monkeypatch.setenv("KAIROS_VAULT_DIR", str(vault_dir))
        codex_runner = AgentRunner(provider="codex")
        prompt = codex_runner.build_codex_performance_analyst_prompt(mode="weekly", channel="이로미즘")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assert "Stage 4 Codex Weekly Analysis" in prompt
        assert "winning_bridge_patterns" in prompt
        assert (vault_dir / "insights" / "performance" / "_inputs" / f"{today}-이로미즘-signal-digest.md").exists()
        assert (vault_dir / "insights" / "performance" / "_inputs" / f"{today}-이로미즘-performance-digest.md").exists()
        assert (vault_dir / "insights" / "performance" / f"{today}-이로미즘-weekly-review.md").exists()
        assert (vault_dir / "insights" / "feedback" / f"{today}-이로미즘-stage0-feedback.md").exists()


class TestBuildCommand:
    def test_agent_runner_loads_workspace_env(self, tmp_path, monkeypatch):
        workspace = tmp_path / "workspace"
        vault_dir = tmp_path / "vault"
        workspace.mkdir()
        vault_dir.mkdir()
        (vault_dir / "insights" / "planning").mkdir(parents=True)
        (workspace / ".env").write_text(
            f"KAIROS_VAULT_DIR={vault_dir}\nDISCORD_WEBHOOK_URL=https://example.com/webhook\n",
            encoding="utf-8",
        )
        monkeypatch.setenv("AUTO_AGENT_WORKSPACE", str(workspace))
        monkeypatch.delenv("KAIROS_VAULT_DIR", raising=False)
        monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
        runner = AgentRunner(provider="codex")
        assert runner._vault_dir == vault_dir.resolve()
        assert os.environ.get("DISCORD_WEBHOOK_URL") == "https://example.com/webhook"

    def test_build_claude_cmd(self, runner):
        cmd = runner._build_claude_cmd(model="sonnet", max_turns=40)
        assert "--model" in cmd
        assert "sonnet" in cmd

    def test_build_codex_cmd(self, tmp_path, monkeypatch):
        vault_dir = tmp_path / "vault"
        vault_dir.mkdir()
        monkeypatch.setenv("KAIROS_VAULT_DIR", str(vault_dir))
        runner = AgentRunner(provider="codex")
        workdir = tmp_path / "isolated"
        workdir.mkdir()
        cmd = runner._build_codex_cmd(
            model="gpt-5.4-mini",
            reasoning_effort="low",
            output_last_message="/tmp/out.txt",
            workdir=workdir,
        )
        assert cmd[0].endswith("codex") or cmd[0] == "codex"
        assert "exec" in cmd
        assert "--json" in cmd
        assert "--output-last-message" in cmd
        assert "workspace-write" in cmd
        assert "--ephemeral" in cmd
        assert 'model_reasoning_effort="low"' in cmd
        assert str(workdir) in cmd

    def test_resolve_codex_model_mapping(self, tmp_path, monkeypatch):
        vault_dir = tmp_path / "vault"
        vault_dir.mkdir()
        monkeypatch.setenv("KAIROS_VAULT_DIR", str(vault_dir))
        runner = AgentRunner(provider="codex")
        assert runner._resolve_model("opus") == "gpt-5.4"
        assert runner._resolve_model("sonnet") == "gpt-5.4-mini"

    def test_parse_usage_from_codex_jsonl(self, tmp_path, monkeypatch):
        vault_dir = tmp_path / "vault"
        vault_dir.mkdir()
        monkeypatch.setenv("KAIROS_VAULT_DIR", str(vault_dir))
        runner = AgentRunner(provider="codex")
        stdout = '\n'.join([
            '{"type":"thread.started","thread_id":"x"}',
            '{"type":"turn.completed","usage":{"input_tokens":123,"cached_input_tokens":45,"output_tokens":67}}',
        ])
        usage = runner._parse_usage_from_codex_jsonl(stdout)
        assert usage["input_tokens"] == 123
        assert usage["output_tokens"] == 67
        assert usage["cache_read_tokens"] == 45

    def test_codex_autoresearch_prompt_is_vault_only(self, tmp_path, monkeypatch):
        vault_dir = tmp_path / "vault"
        vault_dir.mkdir()
        (vault_dir / "insights" / "planning").mkdir(parents=True)
        monkeypatch.setenv("KAIROS_VAULT_DIR", str(vault_dir))
        loop = AutoResearchLoop(channel="이로미즘", max_rounds=3, seed="반도체 세금")
        prompt = loop.build_loop_prompt(provider="codex")
        assert "Vault-Only Ratchet Protocol" in prompt
        assert "외부 웹 검색 없이" in prompt
        assert "WebSearch" not in prompt
        assert "trend-analyst 에이전트" not in prompt

    def test_codex_autoresearch_orchestrates_rounds(self, tmp_path, monkeypatch):
        vault_dir = tmp_path / "vault"
        (vault_dir / "insights" / "planning").mkdir(parents=True)
        (vault_dir / "insights" / "feedback").mkdir(parents=True)
        (vault_dir / "insights" / "performance").mkdir(parents=True)
        (vault_dir / "market" / "trends").mkdir(parents=True)
        (vault_dir / "market" / "news").mkdir(parents=True)
        (vault_dir / "market" / "social").mkdir(parents=True)
        (vault_dir / "market" / "communities").mkdir(parents=True)
        (vault_dir / "channels" / "이로미즘" / "videos").mkdir(parents=True)
        (vault_dir / "channels" / "competitors" / "지식한입").mkdir(parents=True)
        (vault_dir / "market" / "trends" / "t.md").write_text("trend", encoding="utf-8")
        (vault_dir / "market" / "news" / "n.md").write_text("news", encoding="utf-8")
        (vault_dir / "market" / "social" / "s.md").write_text("social", encoding="utf-8")
        (vault_dir / "market" / "communities" / "c.md").write_text("community", encoding="utf-8")
        (vault_dir / "insights" / "feedback" / "f.md").write_text("feedback", encoding="utf-8")
        (vault_dir / "insights" / "performance" / "p.md").write_text("performance", encoding="utf-8")
        (vault_dir / "channels" / "이로미즘" / "videos" / "v.md").write_text("video", encoding="utf-8")
        (vault_dir / "channels" / "competitors" / "지식한입" / "_overview.md").write_text("competitor", encoding="utf-8")
        monkeypatch.setenv("KAIROS_VAULT_DIR", str(vault_dir))
        runner = AgentRunner(provider="codex")

        round_candidates = [
            {
                "title": "주제 A",
                "trigger_keyword": "흑백요리사",
                "knowledge_anchor": "중화요리 4대문파",
                "bridge_reason": "화제 직후 관련 계보형 설명 욕구가 생김",
                "timing_window": "3일 내",
                "angle": "각도 A",
                "hook": "훅 A",
                "topic_score": 420,
                "selection_reason": "이유 A",
                "creative_brief": {
                    "tone": "분석적",
                    "recommended_length": "10분",
                    "story_points": ["도입", "전개", "결론"],
                    "must_include_episodes": ["에피소드1", "에피소드2"],
                },
            }
        ]

        def fake_run_agent(prompt, config, extra_tools=None, on_progress=None, cwd_override=None):
            round_marker = "Round 1" if "Round 1" in prompt else "Round 2"
            round_num = 1 if round_marker == "Round 1" else 2
            assert "autoresearch-packet.md" in prompt
            return {
                "status": "success",
                "returncode": 0,
                "stdout": json.dumps(
                    {"round": round_num, "channel": "이로미즘", "candidates": round_candidates},
                    ensure_ascii=False,
                ),
                "stderr": "",
                "usage": {"input_tokens": 10, "output_tokens": 5},
            }

        monkeypatch.setattr(runner, "_run_agent", fake_run_agent)
        result = runner.run_trend_analyst(channel="이로미즘", seed="반도체 세금", autoresearch=True, max_rounds=2)

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assert result["status"] == "success"
        assert (vault_dir / "insights" / "planning" / f"{today}-이로미즘-autoresearch.json").exists()
        assert (vault_dir / "insights" / "planning" / f"{today}-이로미즘-기획안.md").exists()
        assert (vault_dir / "insights" / "planning" / "_inputs" / f"{today}-이로미즘-trend-digest.md").exists()
        assert (vault_dir / "insights" / "planning" / "_inputs" / f"{today}-이로미즘-autoresearch-packet.md").exists()
        trend_digest = (vault_dir / "insights" / "planning" / "_inputs" / f"{today}-이로미즘-trend-digest.md").read_text(encoding="utf-8")
        feedback_digest = (vault_dir / "insights" / "planning" / "_inputs" / f"{today}-이로미즘-feedback-digest.md").read_text(encoding="utf-8")
        planning_md = (vault_dir / "insights" / "planning" / f"{today}-이로미즘-기획안.md").read_text(encoding="utf-8")
        assert "news" in trend_digest
        assert "social" in trend_digest
        assert "community" in trend_digest
        assert "performance" in feedback_digest
        assert "트리거: 흑백요리사" in planning_md
        assert "앵커: 중화요리 4대문파" in planning_md

    def test_codex_autoresearch_uses_lightweight_model_profile_by_default(self, tmp_path, monkeypatch):
        vault_dir = tmp_path / "vault"
        (vault_dir / "insights" / "planning").mkdir(parents=True)
        monkeypatch.setenv("KAIROS_VAULT_DIR", str(vault_dir))
        monkeypatch.delenv("AUTO_AGENT_CODEX_MODEL", raising=False)
        runner = AgentRunner(provider="codex")
        config = runner._optimize_codex_agent_config("trend-analyst", {"model": "opus", "max_turns": 40})
        assert config["model"] == "sonnet"
        assert config["reasoning_effort"] == "low"

    def test_stage0_trend_digest_prioritizes_explainer_signals(self, tmp_path, monkeypatch):
        vault_dir = tmp_path / "vault"
        (vault_dir / "insights" / "planning").mkdir(parents=True)
        (vault_dir / "market" / "communities").mkdir(parents=True)
        (vault_dir / "market" / "news").mkdir(parents=True)
        (vault_dir / "market" / "trends").mkdir(parents=True)
        (vault_dir / "channels" / "이로미즘" / "videos").mkdir(parents=True)
        (vault_dir / "channels" / "competitors" / "지식한입").mkdir(parents=True)
        community_payload = {
            "items": [
                {"title": "LG VS SSG (ㅇㅁㅇ)/", "link": "https://damoang.net/free/6122438"},
                {"title": "숙종에 의해 노산군이 단종으로 복권된 이후, 금성대군은...", "link": "https://damoang.net/free/6122409"},
                {"title": "상여금 10억이면 실제 세금은 얼마나 뗄까", "link": "https://example.com/bonus-tax"},
            ]
        }
        (vault_dir / "market" / "communities" / "2026-04-12-damoang-free.json").write_text(
            json.dumps(community_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (vault_dir / "market" / "news" / "2026-04-12-news.json").write_text(
            json.dumps({"items": [{"keyword": "흑백요리사", "summary": "후속 관심 지속"}]}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (vault_dir / "market" / "trends" / "2026-04-12-trending.md").write_text("- 흑백요리사", encoding="utf-8")
        monkeypatch.setenv("KAIROS_VAULT_DIR", str(vault_dir))
        codex_runner = AgentRunner(provider="codex")
        digest_paths = codex_runner._build_stage0_digests("이로미즘")
        trend_digest_path = vault_dir / digest_paths["trend_digest"]
        trend_digest = trend_digest_path.read_text(encoding="utf-8")
        assert "상여금 10억이면 실제 세금은 얼마나 뗄까" in trend_digest
        assert "숙종에 의해 노산군이 단종으로 복권된 이후" in trend_digest
        assert "LG VS SSG" not in trend_digest

    def test_stage0_trend_digest_prioritizes_daum_cafe_explainer_titles(self, tmp_path, monkeypatch):
        vault_dir = tmp_path / "vault"
        (vault_dir / "insights" / "planning").mkdir(parents=True)
        (vault_dir / "market" / "communities").mkdir(parents=True)
        (vault_dir / "channels" / "이로미즘" / "videos").mkdir(parents=True)
        (vault_dir / "channels" / "competitors" / "지식한입").mkdir(parents=True)
        payload = {
            "items": [
                {"title": "오늘자 새벽 3시 살목지 근황.jpg", "link": "https://m.cafe.daum.net/x/1"},
                {"title": "조선왕조실록에 기록된 미스터리한 일들", "link": "https://m.cafe.daum.net/x/2"},
                {"title": "무알콜 논알콜 맥주 차이점", "link": "https://m.cafe.daum.net/x/3"},
                {"title": "고통을 나누는 고양이", "link": "https://m.cafe.daum.net/x/4"},
            ]
        }
        (vault_dir / "market" / "communities" / "2026-04-12-daum-cafe-popular-mobile.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        monkeypatch.setenv("KAIROS_VAULT_DIR", str(vault_dir))
        codex_runner = AgentRunner(provider="codex")
        digest_paths = codex_runner._build_stage0_digests("이로미즘")
        trend_digest_path = vault_dir / digest_paths["trend_digest"]
        trend_digest = trend_digest_path.read_text(encoding="utf-8")
        section = trend_digest.split("## market/communities/2026-04-12-daum-cafe-popular-mobile.json", 1)[1]
        section = section.split("\n## ", 1)[0]
        assert "조선왕조실록에 기록된 미스터리한 일들" in section
        assert "무알콜 논알콜 맥주 차이점" in section
        assert section.index("조선왕조실록에 기록된 미스터리한 일들") < section.index("오늘자 새벽 3시 살목지 근황.jpg")

    def test_channel_signal_profiles_change_scoring(self, tmp_path, monkeypatch):
        vault_dir = tmp_path / "vault"
        (vault_dir / "insights" / "planning").mkdir(parents=True)
        (vault_dir / "market" / "communities").mkdir(parents=True)
        (vault_dir / "channels" / "이로미즘" / "videos").mkdir(parents=True)
        (vault_dir / "channels" / "ai백과사전" / "videos").mkdir(parents=True)
        (vault_dir / "channels" / "competitors" / "지식한입").mkdir(parents=True)
        payload = {
            "source": "finance-community-signals",
            "items": [
                {"title": "상여금 10억이면 실제 종합소득세는 얼마일까", "link": "https://example.com/tax"},
                {"title": "새 모델 benchmark 유출, 추론 성능 급등", "link": "https://example.com/ai"},
            ],
        }
        (vault_dir / "market" / "communities" / "2026-04-12-profile.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        monkeypatch.setenv("KAIROS_VAULT_DIR", str(vault_dir))
        runner = AgentRunner(provider="codex")
        finance_summary = runner._summarize_signal_json(json.dumps(payload, ensure_ascii=False), channel="이로미즘")
        ai_summary = runner._summarize_signal_json(json.dumps(payload, ensure_ascii=False), channel="ai백과사전")
        assert finance_summary.index("상여금 10억이면 실제 종합소득세는 얼마일까") < finance_summary.index("새 모델 benchmark 유출, 추론 성능 급등")
        assert "새 모델 benchmark 유출, 추론 성능 급등" in ai_summary

    def test_stage0_signal_digest_keeps_community_sources_even_with_many_news_files(self, tmp_path, monkeypatch):
        vault_dir = tmp_path / "vault"
        (vault_dir / "insights" / "planning").mkdir(parents=True)
        (vault_dir / "market" / "news").mkdir(parents=True)
        (vault_dir / "market" / "communities").mkdir(parents=True)
        (vault_dir / "channels" / "이로미즘" / "videos").mkdir(parents=True)
        (vault_dir / "channels" / "competitors" / "지식한입").mkdir(parents=True)
        for idx in range(6):
            (vault_dir / "market" / "news" / f"2026-04-12-news-{idx}.json").write_text(
                json.dumps({"items": [{"title": f"뉴스 {idx}", "link": f"https://example.com/{idx}"}]}, ensure_ascii=False),
                encoding="utf-8",
            )
        (vault_dir / "market" / "communities" / "2026-04-12-finance-community-signals.json").write_text(
            json.dumps({"source": "finance-community-signals", "items": [{"title": "상여금 10억이면 실제 종합소득세는 얼마일까", "link": "https://example.com/tax"}]}, ensure_ascii=False),
            encoding="utf-8",
        )
        (vault_dir / "market" / "communities" / "2026-04-12-ai-community-signals.json").write_text(
            json.dumps({"source": "ai-community-signals", "items": [{"title": "Open source agent stack that actually works in 2026", "link": "https://example.com/agent"}]}, ensure_ascii=False),
            encoding="utf-8",
        )
        monkeypatch.setenv("KAIROS_VAULT_DIR", str(vault_dir))
        runner = AgentRunner(provider="codex")
        digest_paths = runner._build_stage0_digests("이로미즘")
        trend_digest = (vault_dir / digest_paths["trend_digest"]).read_text(encoding="utf-8")
        assert "2026-04-12-finance-community-signals.json" in trend_digest
        assert "2026-04-12-ai-community-signals.json" not in trend_digest

    def test_stage0_signal_digest_filters_channel_mismatched_community_sources(self, tmp_path, monkeypatch):
        vault_dir = tmp_path / "vault"
        (vault_dir / "insights" / "planning").mkdir(parents=True)
        (vault_dir / "market" / "communities").mkdir(parents=True)
        (vault_dir / "channels" / "이로미즘" / "videos").mkdir(parents=True)
        (vault_dir / "channels" / "ai백과사전" / "videos").mkdir(parents=True)
        (vault_dir / "channels" / "competitors" / "지식한입").mkdir(parents=True)
        (vault_dir / "market" / "communities" / "2026-04-12-finance-community-signals.json").write_text(
            json.dumps(
                {
                    "source": "finance-community-signals",
                    "items": [
                        {"title": "상여금 10억이면 실제 종합소득세는 얼마일까", "link": "https://example.com/tax"},
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (vault_dir / "market" / "communities" / "2026-04-12-ai-community-signals.json").write_text(
            json.dumps(
                {
                    "source": "ai-community-signals",
                    "items": [
                        {"title": "Open source agent stack that actually works in 2026", "link": "https://example.com/agent"},
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        monkeypatch.setenv("KAIROS_VAULT_DIR", str(vault_dir))
        runner = AgentRunner(provider="codex")

        finance_digest_paths = runner._build_stage0_digests("이로미즘")
        finance_digest = (vault_dir / finance_digest_paths["trend_digest"]).read_text(encoding="utf-8")
        assert "2026-04-12-finance-community-signals.json" in finance_digest
        assert "2026-04-12-ai-community-signals.json" not in finance_digest

        ai_digest_paths = runner._build_stage0_digests("ai백과사전")
        ai_digest = (vault_dir / ai_digest_paths["trend_digest"]).read_text(encoding="utf-8")
        assert "2026-04-12-ai-community-signals.json" in ai_digest
        assert "2026-04-12-finance-community-signals.json" not in ai_digest

    def test_stage0_signal_digest_uses_filename_when_source_field_missing(self, tmp_path, monkeypatch):
        vault_dir = tmp_path / "vault"
        (vault_dir / "insights" / "planning").mkdir(parents=True)
        (vault_dir / "market" / "communities").mkdir(parents=True)
        (vault_dir / "channels" / "이로미즘" / "videos").mkdir(parents=True)
        (vault_dir / "channels" / "ai백과사전" / "videos").mkdir(parents=True)
        (vault_dir / "channels" / "competitors" / "지식한입").mkdir(parents=True)
        (vault_dir / "market" / "communities" / "2026-04-12-finance-community-signals.json").write_text(
            json.dumps(
                {
                    "source_name": None,
                    "items": [
                        {"title": "상여금 10억이면 실제 종합소득세는 얼마일까", "link": "https://example.com/tax"},
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (vault_dir / "market" / "communities" / "2026-04-12-ai-community-signals.json").write_text(
            json.dumps(
                {
                    "source_name": None,
                    "items": [
                        {"title": "Open source agent stack that actually works in 2026", "link": "https://example.com/agent"},
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        monkeypatch.setenv("KAIROS_VAULT_DIR", str(vault_dir))
        runner = AgentRunner(provider="codex")
        finance_digest = (vault_dir / runner._build_stage0_digests("이로미즘")["trend_digest"]).read_text(encoding="utf-8")
        ai_digest = (vault_dir / runner._build_stage0_digests("ai백과사전")["trend_digest"]).read_text(encoding="utf-8")
        assert "2026-04-12-finance-community-signals.json" in finance_digest
        assert "2026-04-12-ai-community-signals.json" not in finance_digest
        assert "2026-04-12-ai-community-signals.json" in ai_digest
        assert "2026-04-12-finance-community-signals.json" not in ai_digest

    def test_stage0_signal_digest_prioritizes_relevant_news_sources_by_channel(self, tmp_path, monkeypatch):
        vault_dir = tmp_path / "vault"
        (vault_dir / "insights" / "planning").mkdir(parents=True)
        (vault_dir / "market" / "news").mkdir(parents=True)
        (vault_dir / "channels" / "이로미즘" / "videos").mkdir(parents=True)
        (vault_dir / "channels" / "ai백과사전" / "videos").mkdir(parents=True)
        (vault_dir / "channels" / "competitors" / "지식한입").mkdir(parents=True)
        (vault_dir / "market" / "news" / "2026-04-12-google-news-top-ko.json").write_text(
            json.dumps(
                {
                    "source_name": None,
                    "items": [
                        {"title": "정당 대표 출마설과 선거 변수", "link": "https://example.com/politics"},
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (vault_dir / "market" / "news" / "2026-04-12-google-news-business-ko.json").write_text(
            json.dumps(
                {
                    "source_name": None,
                    "items": [
                        {"title": "반도체 장기공급계약과 AI 추론 수요 급증", "link": "https://example.com/semis"},
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        monkeypatch.setenv("KAIROS_VAULT_DIR", str(vault_dir))
        runner = AgentRunner(provider="codex")

        finance_digest = (vault_dir / runner._build_stage0_digests("이로미즘")["trend_digest"]).read_text(encoding="utf-8")
        ai_digest = (vault_dir / runner._build_stage0_digests("ai백과사전")["trend_digest"]).read_text(encoding="utf-8")

        assert "2026-04-12-google-news-business-ko.json" in finance_digest
        assert "반도체 장기공급계약과 AI 추론 수요 급증" in finance_digest
        assert "2026-04-12-google-news-business-ko.json" in ai_digest
        assert "반도체 장기공급계약과 AI 추론 수요 급증" in ai_digest
