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


class TestSceneDelta:
    """_compute_scene_delta 테스트."""

    def test_detects_changed_scene(self):
        from auto_agent.orchestrator.runner import PipelineRunner

        prev = [{"sceneNumber": 1, "narration": "old"}, {"sceneNumber": 2, "narration": "same"}]
        curr = [{"sceneNumber": 1, "narration": "new"}, {"sceneNumber": 2, "narration": "same"}]

        delta = PipelineRunner._compute_scene_delta(json.dumps(prev), json.dumps(curr))
        assert len(delta["changed_scenes"]) == 1
        assert delta["changed_scenes"][0]["sceneNumber"] == 1
        assert delta["unchanged_count"] == 1

    def test_detects_added_scene(self):
        from auto_agent.orchestrator.runner import PipelineRunner

        prev = [{"sceneNumber": 1, "narration": "a"}]
        curr = [{"sceneNumber": 1, "narration": "a"}, {"sceneNumber": 2, "narration": "b"}]

        delta = PipelineRunner._compute_scene_delta(json.dumps(prev), json.dumps(curr))
        assert len(delta["added_scenes"]) == 1
        assert delta["added_scenes"][0]["sceneNumber"] == 2
        assert delta["unchanged_count"] == 1

    def test_detects_removed_scene(self):
        from auto_agent.orchestrator.runner import PipelineRunner

        prev = [{"sceneNumber": 1, "narration": "a"}, {"sceneNumber": 2, "narration": "b"}]
        curr = [{"sceneNumber": 1, "narration": "a"}]

        delta = PipelineRunner._compute_scene_delta(json.dumps(prev), json.dumps(curr))
        assert delta["removed_scene_numbers"] == [2]
        assert delta["unchanged_count"] == 1

    def test_no_changes(self):
        from auto_agent.orchestrator.runner import PipelineRunner

        scenes = [{"sceneNumber": 1, "narration": "a"}, {"sceneNumber": 2, "narration": "b"}]

        delta = PipelineRunner._compute_scene_delta(json.dumps(scenes), json.dumps(scenes))
        assert len(delta["changed_scenes"]) == 0
        assert len(delta["added_scenes"]) == 0
        assert len(delta["removed_scene_numbers"]) == 0
        assert delta["unchanged_count"] == 2
