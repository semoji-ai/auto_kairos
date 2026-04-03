"""토큰 최적화 관련 유닛 테스트."""
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


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
