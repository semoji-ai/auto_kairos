"""토큰 최적화 관련 유닛 테스트."""
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from types import SimpleNamespace


class TestVaultRAGCache:
    """VaultRAG 검색 결과 캐싱 테스트."""

    def test_search_for_research_caches_result(self):
        from auto_agent.orchestrator.vault_rag import VaultRAG

        rag = VaultRAG.__new__(VaultRAG)
        rag.enabled = True
        rag._search_cache = {}

        call_count = 0
        original_result = "<vault_knowledge>test</vault_knowledge>"

        def fake_search(topic, category, channel=None):
            nonlocal call_count
            call_count += 1
            return original_result

        rag._do_search_for_research = fake_search

        r1 = rag.search_for_research("AI반도체", "경제")
        r2 = rag.search_for_research("AI반도체", "경제")

        assert r1 == original_result
        assert r2 == original_result
        assert call_count == 1

    def test_search_for_manuscript_caches_result(self):
        from auto_agent.orchestrator.vault_rag import VaultRAG

        rag = VaultRAG.__new__(VaultRAG)
        rag.enabled = True
        rag._search_cache = {}

        call_count = 0

        def fake_search(topic, category, channel=None):
            nonlocal call_count
            call_count += 1
            return "manuscript_result"

        rag._do_search_for_manuscript = fake_search

        r1 = rag.search_for_manuscript("AI반도체", "경제")
        r2 = rag.search_for_manuscript("AI반도체", "경제")

        assert r1 == r2
        assert call_count == 1

    def test_different_topics_not_cached(self):
        from auto_agent.orchestrator.vault_rag import VaultRAG

        rag = VaultRAG.__new__(VaultRAG)
        rag.enabled = True
        rag._search_cache = {}

        call_count = 0

        def fake_search(topic, category, channel=None):
            nonlocal call_count
            call_count += 1
            return f"result_{topic}"

        rag._do_search_for_research = fake_search

        rag.search_for_research("AI반도체", "경제")
        rag.search_for_research("우주탐사", "과학")

        assert call_count == 2


class TestContextMemoryHelper:
    """ContextMemory.has_entries_for_predecessors 테스트."""

    def test_has_entries_when_predecessor_exists(self, tmp_path):
        from auto_agent.orchestrator.context_memory import ContextMemory

        cm = ContextMemory(tmp_path)
        memory = cm.load()
        memory["entries"] = [
            {"step_id": "step_1", "agent": "research-orchestrator",
             "summary": "test", "key_facts": [], "decisions": [],
             "timestamp": "2026-01-01", "category": "research_decision"},
        ]
        cm.save(memory)

        assert cm.has_entries_for_predecessors("step_2") is True

    def test_no_entries_for_first_step(self, tmp_path):
        from auto_agent.orchestrator.context_memory import ContextMemory

        cm = ContextMemory(tmp_path)
        memory = cm.load()
        memory["entries"] = [
            {"step_id": "step_2", "agent": "script-director",
             "summary": "test", "key_facts": [], "decisions": [],
             "timestamp": "2026-01-01", "category": "narrative_structure"},
        ]
        cm.save(memory)

        assert cm.has_entries_for_predecessors("step_1") is False

    def test_empty_memory(self, tmp_path):
        from auto_agent.orchestrator.context_memory import ContextMemory

        cm = ContextMemory(tmp_path)
        assert cm.has_entries_for_predecessors("step_3b") is False


class TestResearchDigest:
    """research_digest.json 생성 테스트."""

    def test_generate_digest_creates_file(self, tmp_path):
        """CLI 호출 성공 시 digest가 생성됨."""
        from auto_agent.orchestrator.runner import PipelineRunner
        import subprocess

        report = {
            "topic": "AI 반도체",
            "summary": "AI 반도체 시장 개요",
            "sections": [
                {"title": "시장 규모", "content": "글로벌 AI 반도체 시장은 2025년 800억 달러 규모입니다."}
            ],
            "sources": [
                {"title": "IDC Report", "url": "https://example.com", "quality_grade": "A"}
            ],
        }
        report_path = tmp_path / "research_report.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")

        runner = PipelineRunner.__new__(PipelineRunner)
        runner.project_dir = tmp_path
        runner.project_slug = "test-project"

        digest_json = json.dumps({
            "topic": "AI 반도체",
            "core_thesis": "AI 반도체 시장이 급성장 중",
            "key_facts": [{"fact": "2025년 800억 달러", "source": "IDC", "confidence": "high"}],
            "statistics": [{"label": "시장 규모", "value": 800, "unit": "억 달러", "source": "IDC"}],
            "episodes": [],
            "timeline": [],
            "sources": [{"title": "IDC Report", "url": "https://example.com", "reliability": "high"}],
        }, ensure_ascii=False)

        mock_proc = MagicMock()
        mock_proc.stdout = json.dumps({"result": digest_json})
        mock_proc.returncode = 0

        with patch.object(runner, '_find_claude_cli', return_value='/usr/bin/claude'), \
             patch.object(runner, '_extract_json_from_cli_output', return_value=json.loads(digest_json)), \
             patch('subprocess.run', return_value=mock_proc):
            runner._generate_research_digest()

        digest_path = tmp_path / "research_digest.json"
        assert digest_path.exists()
        digest = json.loads(digest_path.read_text(encoding="utf-8"))
        assert digest["topic"] == "AI 반도체"
        assert len(digest["key_facts"]) > 0
        assert len(digest["statistics"]) > 0

    def test_generate_digest_fallback_on_failure(self, tmp_path):
        """CLI 실패 시 research_report.json을 digest로 복사."""
        from auto_agent.orchestrator.runner import PipelineRunner

        report = {"topic": "test", "summary": "test", "sections": [], "sources": []}
        report_path = tmp_path / "research_report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")

        runner = PipelineRunner.__new__(PipelineRunner)
        runner.project_dir = tmp_path
        runner.project_slug = "test-project"

        with patch.object(runner, '_find_claude_cli', side_effect=Exception("CLI not found")):
            runner._generate_research_digest()

        digest_path = tmp_path / "research_digest.json"
        assert digest_path.exists()
        digest = json.loads(digest_path.read_text(encoding="utf-8"))
        assert digest["topic"] == "test"


class TestRunnerCliParsing:
    def test_parse_claude_cost_from_stream_json_result_line(self):
        from auto_agent.orchestrator.runner import PipelineRunner

        runner = PipelineRunner.__new__(PipelineRunner)
        stdout = "\n".join([
            json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "partial"}]}}),
            json.dumps({
                "type": "result",
                "subtype": "success",
                "is_error": False,
                "total_cost_usd": 0.1234,
                "usage": {"input_tokens": 111, "output_tokens": 222},
                "model": "claude-opus-4-5-20250514",
            }),
        ])

        cost = runner._parse_claude_cost(stdout, "")
        assert cost["tokens_in"] == 111
        assert cost["tokens_out"] == 222
        assert cost["cost_usd"] == 0.1234

    def test_extract_rate_limit_wait_seconds(self):
        # 구현은 "리셋까지 1시간 이내"일 때만 대기 시간을 반환하므로,
        # 하드코딩된 시각 대신 현재 시각 +30분으로 동적 구성 (플레이키 방지)
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo

        from auto_agent.orchestrator.runner import PipelineRunner

        reset = datetime.now(ZoneInfo("Asia/Seoul")) + timedelta(minutes=30)
        hour12 = reset.hour % 12 or 12
        ampm = "pm" if reset.hour >= 12 else "am"
        msg = f"You've hit your limit · resets {hour12}:{reset.minute:02d}{ampm} (Asia/Seoul)"

        wait = PipelineRunner._extract_rate_limit_wait_seconds(msg)
        assert wait is not None
        assert wait >= 0

    def test_extract_rate_limit_wait_seconds_no_reset_info(self):
        from auto_agent.orchestrator.runner import PipelineRunner

        assert PipelineRunner._extract_rate_limit_wait_seconds("generic error") is None
        assert PipelineRunner._extract_rate_limit_wait_seconds("") is None

    def test_extract_cli_error_message_from_result_wrapper(self):
        from auto_agent.orchestrator.runner import PipelineRunner

        stdout = "\n".join([
            json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "partial"}]}}),
            json.dumps({
                "type": "result",
                "subtype": "success",
                "is_error": True,
                "result": "You've hit your limit · resets 8pm (Asia/Seoul)",
                "usage": {"input_tokens": 0, "output_tokens": 0},
            }),
        ])

        msg = PipelineRunner._extract_cli_error_message(stdout, "")
        assert "You've hit your limit" in msg
