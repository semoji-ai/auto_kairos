# Token Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 파이프라인 토큰 소비를 ~66% 절감 (프로젝트당 ~172K → ~58K), 기존 파이프라인 호환성 유지

**Architecture:** Stage 1 완료 직후 research_digest.json을 Sonnet으로 생성하여 후속 스텝에서 원문 대신 사용. Ratchet loop은 변경 씬만 delta로 전달. ContextMemory는 opt-in 방식으로 원본 파일을 대체. Vault RAG는 인스턴스 레벨 캐싱.

**Tech Stack:** Python 3.11+, Anthropic SDK, pathlib, json

**Spec:** `docs/superpowers/specs/2026-04-03-token-optimization-design.md`

---

## File Structure

| File | Role | Action |
|------|------|--------|
| `auto_agent/orchestrator/runner.py` | 메인 파이프라인 오케스트레이터 | Modify |
| `auto_agent/orchestrator/context_memory.py` | 컨텍스트 메모리 시스템 | Modify |
| `auto_agent/orchestrator/vault_rag.py` | 볼트 RAG 검색 | Modify |
| `auto_agent/data/pipeline.json` | 파이프라인 스텝 정의 | Modify |
| `auto_agent/data/skills/agents/script-reviewer/SKILL.md` | 리뷰어 스킬 | Modify |
| `auto_agent/data/skills/agents/data-mapper/SKILL.md` | 데이터 매퍼 스킬 | Modify |
| `CLAUDE.md` | 프로젝트 가이드 | Modify |
| `tests/test_token_optimization.py` | 토큰 최적화 테스트 | Create |

---

## Task 1: Vault RAG 캐싱 (가장 독립적, 위험 낮음)

**Files:**
- Modify: `auto_agent/orchestrator/vault_rag.py:130-213`
- Create: `tests/test_token_optimization.py`

- [ ] **Step 1: 테스트 작성 — VaultRAG 캐싱**

`tests/test_token_optimization.py`:
```python
"""토큰 최적화 관련 유닛 테스트."""
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


class TestVaultRAGCache:
    """VaultRAG 검색 결과 캐싱 테스트."""

    def test_search_for_research_caches_result(self):
        """동일 topic+category로 두 번 호출 시 내부 검색은 1회만."""
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
        assert call_count == 1  # 내부 검색은 1회만

    def test_search_for_manuscript_caches_result(self):
        """동일 topic+category로 두 번 호출 시 내부 검색은 1회만."""
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
        """다른 topic이면 캐시 미스."""
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
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `cd /Users/jleavens_macmini/Projects/auto_kairos_v3 && python -m pytest tests/test_token_optimization.py::TestVaultRAGCache -v`
Expected: FAIL — `_do_search_for_research` 메서드 없음

- [ ] **Step 3: vault_rag.py에 캐시 레이어 구현**

`auto_agent/orchestrator/vault_rag.py` — `__init__`에 캐시 dict 추가:

```python
# __init__ 마지막에 추가
self._search_cache: dict[str, str] = {}
```

기존 `search_for_research`를 `_do_search_for_research`로 rename하고, 새 캐시 래퍼 작성:

```python
def search_for_research(self, topic: str, category: str = "", channel: str = None) -> str:
    """리서치용 볼트 검색 (캐시 적용)."""
    if not self.enabled:
        return ""
    cache_key = f"research:{topic}:{category}:{channel or ''}"
    if cache_key in self._search_cache:
        return self._search_cache[cache_key]
    result = self._do_search_for_research(topic, category, channel=channel)
    self._search_cache[cache_key] = result
    return result

def _do_search_for_research(self, topic: str, category: str = "", channel: str = None) -> str:
    """리서치 시작 전: 관련 기존 지식을 검색하여 컨텍스트 텍스트 반환."""
    # ... 기존 search_for_research의 본문 (if not self.enabled: return "" 제거)
```

동일하게 `search_for_manuscript` → `_do_search_for_manuscript` rename + 캐시 래퍼:

```python
def search_for_manuscript(self, topic: str, category: str = "", channel: str = None) -> str:
    """원고용 볼트 검색 (캐시 적용)."""
    if not self.enabled:
        return ""
    cache_key = f"manuscript:{topic}:{category}:{channel or ''}"
    if cache_key in self._search_cache:
        return self._search_cache[cache_key]
    result = self._do_search_for_manuscript(topic, category, channel=channel)
    self._search_cache[cache_key] = result
    return result

def _do_search_for_manuscript(self, topic: str, category: str = "", channel: str = None) -> str:
    """원고 작성 전: 서사 패턴/문체 DNA를 검색."""
    # ... 기존 search_for_manuscript의 본문 (if not self.enabled: return "" 제거)
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `cd /Users/jleavens_macmini/Projects/auto_kairos_v3 && python -m pytest tests/test_token_optimization.py::TestVaultRAGCache -v`
Expected: 3 tests PASS

- [ ] **Step 5: 커밋**

```bash
cd /Users/jleavens_macmini/Projects/auto_kairos_v3
git add auto_agent/orchestrator/vault_rag.py tests/test_token_optimization.py
git commit -m "feat: VaultRAG 검색 결과 캐싱 추가 — 동일 프로젝트 내 중복 검색 방지"
```

---

## Task 2: ContextMemory — has_entries_for_predecessors 헬퍼

**Files:**
- Modify: `auto_agent/orchestrator/context_memory.py:192-196`
- Modify: `tests/test_token_optimization.py`

- [ ] **Step 1: 테스트 작성**

`tests/test_token_optimization.py`에 추가:
```python
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
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `cd /Users/jleavens_macmini/Projects/auto_kairos_v3 && python -m pytest tests/test_token_optimization.py::TestContextMemoryHelper -v`
Expected: FAIL — `has_entries_for_predecessors` 없음

- [ ] **Step 3: 구현**

`auto_agent/orchestrator/context_memory.py` 끝에 (클래스 내부, `_step_order` 위):

```python
    def has_entries_for_predecessors(self, current_step_id: str) -> bool:
        """현재 step 이전에 수집된 엔트리가 있는지 확인."""
        memory = self.load()
        return any(
            _step_order(e["step_id"]) < _step_order(current_step_id)
            for e in memory.get("entries", [])
        )
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `cd /Users/jleavens_macmini/Projects/auto_kairos_v3 && python -m pytest tests/test_token_optimization.py::TestContextMemoryHelper -v`
Expected: 3 tests PASS

- [ ] **Step 5: 커밋**

```bash
cd /Users/jleavens_macmini/Projects/auto_kairos_v3
git add auto_agent/orchestrator/context_memory.py tests/test_token_optimization.py
git commit -m "feat: ContextMemory.has_entries_for_predecessors() 추가"
```

---

## Task 3: research_digest.json 생성

**Files:**
- Modify: `auto_agent/orchestrator/runner.py:875` (digest 생성 호출 삽입)
- Modify: `tests/test_token_optimization.py`

- [ ] **Step 1: 테스트 작성 — digest 생성**

`tests/test_token_optimization.py`에 추가:
```python
class TestResearchDigest:
    """research_digest.json 생성 테스트."""

    def test_generate_digest_creates_file(self, tmp_path):
        """research_report.json이 있으면 digest가 생성됨."""
        from auto_agent.orchestrator.runner import PipelineRunner

        # research_report.json 준비
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

        # Mock runner
        runner = PipelineRunner.__new__(PipelineRunner)
        runner.project_dir = tmp_path
        runner.project_slug = "test-project"

        # Mock Anthropic API
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({
            "topic": "AI 반도체",
            "core_thesis": "AI 반도체 시장이 급성장 중",
            "key_facts": [{"fact": "2025년 800억 달러", "source": "IDC", "confidence": "high"}],
            "statistics": [{"label": "시장 규모", "value": 800, "unit": "억 달러", "source": "IDC"}],
            "episodes": [],
            "timeline": [],
            "sources": [{"title": "IDC Report", "url": "https://example.com", "reliability": "high"}],
        }, ensure_ascii=False))]

        with patch("anthropic.Anthropic") as mock_cls:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_cls.return_value = mock_client

            runner._generate_research_digest()

        digest_path = tmp_path / "research_digest.json"
        assert digest_path.exists()
        digest = json.loads(digest_path.read_text(encoding="utf-8"))
        assert digest["topic"] == "AI 반도체"
        assert len(digest["key_facts"]) > 0
        assert len(digest["statistics"]) > 0

    def test_generate_digest_fallback_on_failure(self, tmp_path):
        """Anthropic API 실패 시 research_report.json을 digest로 복사."""
        from auto_agent.orchestrator.runner import PipelineRunner

        report = {"topic": "test", "summary": "test", "sections": [], "sources": []}
        report_path = tmp_path / "research_report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")

        runner = PipelineRunner.__new__(PipelineRunner)
        runner.project_dir = tmp_path
        runner.project_slug = "test-project"

        with patch("anthropic.Anthropic", side_effect=Exception("API error")):
            runner._generate_research_digest()

        digest_path = tmp_path / "research_digest.json"
        assert digest_path.exists()
        # fallback: 원본 복사
        digest = json.loads(digest_path.read_text(encoding="utf-8"))
        assert digest["topic"] == "test"
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `cd /Users/jleavens_macmini/Projects/auto_kairos_v3 && python -m pytest tests/test_token_optimization.py::TestResearchDigest -v`
Expected: FAIL — `_generate_research_digest` 없음

- [ ] **Step 3: runner.py에 `_generate_research_digest()` 구현**

`auto_agent/orchestrator/runner.py` — `_merge_research_outputs` 메서드 아래에 추가:

```python
    def _generate_research_digest(self):
        """research_report.json → research_digest.json 축약본 생성 (Sonnet 1회).

        실패 시 research_report.json을 그대로 복사 (fallback).
        """
        report_path = self.project_dir / "research_report.json"
        digest_path = self.project_dir / "research_digest.json"

        if not report_path.exists():
            return

        report_text = report_path.read_text(encoding="utf-8")

        try:
            import anthropic

            client = anthropic.Anthropic()
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": (
                        "아래 리서치 보고서를 정형 축약본(digest)으로 변환하세요.\n"
                        "원본의 모든 수치, 출처, 에피소드를 빠짐없이 포함하되, "
                        "서사적 설명은 제거하고 구조화된 JSON으로 출력하세요.\n\n"
                        f"<research_report>\n{report_text}\n</research_report>\n\n"
                        "출력 JSON 스키마:\n"
                        "{\n"
                        '  "topic": "string",\n'
                        '  "core_thesis": "핵심 논지 2-3문장",\n'
                        '  "key_facts": [{"fact": "string", "source": "string", "confidence": "high|medium|low"}],\n'
                        '  "statistics": [{"label": "string", "value": "number|string", "unit": "string", "source": "string"}],\n'
                        '  "episodes": [{"title": "string", "summary": "1-2문장", "characters": ["string"]}],\n'
                        '  "timeline": [{"date": "string", "event": "string"}],\n'
                        '  "sources": [{"title": "string", "url": "string", "reliability": "high|medium|low"}]\n'
                        "}\n\n"
                        "JSON만 출력하세요. 다른 텍스트 없이."
                    ),
                }],
            )

            digest_data = json.loads(response.content[0].text)
            digest_path.write_text(
                json.dumps(digest_data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"    [DIGEST] research_digest.json 생성 완료 "
                  f"(facts: {len(digest_data.get('key_facts', []))}, "
                  f"stats: {len(digest_data.get('statistics', []))})")

        except Exception as e:
            print(f"    [DIGEST] 생성 실패 ({e}) → research_report.json fallback")
            import shutil
            shutil.copy2(report_path, digest_path)
```

- [ ] **Step 4: `_validate_step` step_1 블록에서 digest 생성 호출 추가**

`runner.py:977` 부근 (step_1 검증 성공 후) — 기존 코드에서 검증이 통과된 직후에 삽입:

`_validate_step` 메서드 내 step_1 블록의 검증 성공 지점(return 전)에 추가:
```python
            # digest 생성 (토큰 최적화)
            try:
                self._generate_research_digest()
            except Exception as e:
                print(f"    [WARN] digest 생성 실패: {e}")
```

- [ ] **Step 5: 테스트 실행 — 통과 확인**

Run: `cd /Users/jleavens_macmini/Projects/auto_kairos_v3 && python -m pytest tests/test_token_optimization.py::TestResearchDigest -v`
Expected: 2 tests PASS

- [ ] **Step 6: 커밋**

```bash
cd /Users/jleavens_macmini/Projects/auto_kairos_v3
git add auto_agent/orchestrator/runner.py tests/test_token_optimization.py
git commit -m "feat: Stage 1 완료 후 research_digest.json 자동 생성 (Sonnet 1회)"
```

---

## Task 4: pipeline.json input 변경 + context_replaces

**Files:**
- Modify: `auto_agent/data/pipeline.json`

- [ ] **Step 1: step_2_review input 변경**

`pipeline.json:89` — ratchet loop의 input에서 `research_report.json` → `research_digest.json`:

```json
"input": ["scene_specs.json", "research_digest.json"],
```

- [ ] **Step 2: step_2_data input 변경**

`pipeline.json:109-110` — data-mapper의 input:

```json
"input": ["scene_specs.json", "research_digest.json"],
```

- [ ] **Step 3: step_3b에 context_replaces 추가**

`pipeline.json:138-143` — assembly-director:

```json
{
  "id": "step_3b",
  "name": "assembly",
  "description": "에이전트가 이미지+TTS+자막+매니페스트를 직접 처리. 렌더링은 대시보드에서 수동.",
  "agent": "assembly-director",
  "input": ["scene_specs.json", "art_style.json", "project_config", "images/"],
  "context_replaces": ["research_report.json"],
  ...
}
```

- [ ] **Step 4: stage_4 추가**

`pipeline.json` — `stage_3` 블록 뒤, `summary` 블록 앞에 추가:

```json
    ,{
      "id": "stage_4",
      "name": "성과 분석",
      "description": "영상 업로드 후 성과 데이터 수집 및 분석. 외부 스케줄러(launchd)로 실행.",
      "execution": "external_schedule",
      "steps": [
        {
          "id": "step_4",
          "name": "performance_analysis",
          "description": "주간 성과 데이터 수집 + 볼트 회고 저장",
          "type": "external",
          "schedule": "weekly_monday_0630",
          "script": "auto_agent/scripts/stage4_weekly.py",
          "notes": "launchd로 실행. 파이프라인 runner에서 호출하지 않음."
        }
      ]
    }
```

- [ ] **Step 5: 커밋**

```bash
cd /Users/jleavens_macmini/Projects/auto_kairos_v3
git add auto_agent/data/pipeline.json
git commit -m "feat: pipeline.json — digest input 전환 + context_replaces + stage_4 정의"
```

---

## Task 5: runner.py — ratchet delta review + context_replaces 로직

**Files:**
- Modify: `auto_agent/orchestrator/runner.py:3093-3244` (ratchet loop)
- Modify: `auto_agent/orchestrator/runner.py:3414-3584` (prompt builder)
- Modify: `auto_agent/orchestrator/runner.py:1796, 1917` (챕터 빌드 인라인)
- Modify: `tests/test_token_optimization.py`

- [ ] **Step 1: 테스트 작성 — scene delta 계산**

`tests/test_token_optimization.py`에 추가:
```python
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
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `cd /Users/jleavens_macmini/Projects/auto_kairos_v3 && python -m pytest tests/test_token_optimization.py::TestSceneDelta -v`
Expected: FAIL — `_compute_scene_delta` 없음

- [ ] **Step 3: `_compute_scene_delta` 구현**

`runner.py` — `_accumulate_cost` 메서드 뒤에 추가:

```python
    @staticmethod
    def _compute_scene_delta(prev_specs_json: str, curr_specs_json: str) -> dict:
        """이전/현재 scene_specs 비교 → 변경 씬 추출.

        Returns:
            {"changed_scenes": [...], "added_scenes": [...],
             "removed_scene_numbers": [...], "unchanged_count": int}
        """
        prev = json.loads(prev_specs_json)
        curr = json.loads(curr_specs_json)

        # list → sceneNumber 기준 dict
        if isinstance(prev, dict):
            prev = prev.get("scenes", prev.get("data", []))
        if isinstance(curr, dict):
            curr = curr.get("scenes", curr.get("data", []))

        prev_map = {s["sceneNumber"]: s for s in prev}
        curr_map = {s["sceneNumber"]: s for s in curr}

        changed = []
        added = []
        removed = []

        for sn, scene in curr_map.items():
            if sn not in prev_map:
                added.append(scene)
            elif scene != prev_map[sn]:
                changed.append(scene)

        for sn in prev_map:
            if sn not in curr_map:
                removed.append(sn)

        return {
            "changed_scenes": changed,
            "added_scenes": added,
            "removed_scene_numbers": removed,
            "unchanged_count": len(curr_map) - len(changed) - len(added),
        }
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `cd /Users/jleavens_macmini/Projects/auto_kairos_v3 && python -m pytest tests/test_token_optimization.py::TestSceneDelta -v`
Expected: 4 tests PASS

- [ ] **Step 5: ratchet loop에 delta 로직 적용**

`runner.py:3116` — `_run_ratchet_loop` 메서드의 for 루프 내부 수정:

R2+ 리뷰 시 delta를 `review_step`에 주입. 기존 코드(3126-3143) 수정:

```python
        for round_num in range(1, max_rounds + 1):
            # ... 기존 출력 유지 ...

            # ── 1. 리뷰 실행 ──
            round_feedback = self.project_dir / f"review_feedback_r{round_num}.json"

            review_inputs = list(step.get("input", []))
            prev_review_context = ""
            if round_num > 1 and feedback_path.exists():
                review_inputs.append("review_feedback.json")
                prev_review_context = feedback_path.read_text(encoding="utf-8")

            review_step = {
                "id": f"{step_id}_review_r{round_num}",
                "name": f"review_r{round_num}",
                "agent": reviewer_agent,
                "input": review_inputs,
                "output": ["review_feedback.json"],
                "skip_resume": True,
            }

            # Delta review: R2+ 에서는 변경 씬만 전달
            if round_num > 1 and best_specs:
                curr_specs = specs_path.read_text(encoding="utf-8") if specs_path.exists() else ""
                if curr_specs:
                    try:
                        delta = self._compute_scene_delta(best_specs, curr_specs)
                        review_step["_scene_delta"] = json.dumps(delta, ensure_ascii=False)
                        # scene_specs.json을 input에서 제거 (delta로 대체)
                        review_step["input"] = [
                            inp for inp in review_step["input"]
                            if inp != "scene_specs.json"
                        ]
                        print(f"    [래칫 R{round_num}] delta 모드: "
                              f"변경 {len(delta['changed_scenes'])}씬, "
                              f"추가 {len(delta['added_scenes'])}씬, "
                              f"삭제 {len(delta['removed_scene_numbers'])}씬")
                    except Exception as e:
                        print(f"    [래칫 R{round_num}] delta 계산 실패 ({e}) → 전체 전달")

            if prev_review_context:
                review_step["_previous_review"] = prev_review_context

            review_result = self._run_agent_step(review_step)
            # ... 이후 기존 코드 유지 ...
```

- [ ] **Step 6: ratchet reviser input에서 research_report → research_digest 변경**

`runner.py:3227` — revise_step의 input 수정:

```python
            revise_step = {
                "id": f"{step_id}_revise_r{round_num}",
                "name": f"revise_r{round_num}",
                "agent": reviser_agent,
                "conditional": "review_verdict_revise",
                "input": ["scene_specs.json", "review_feedback.json", "research_digest.json"],
                "output": ["scene_specs.json"],
                "skills": step.get("skills", []),
                "skip_resume": True,
            }
```

- [ ] **Step 7: `_build_agent_prompt`에 delta 및 context_replaces 로직 추가**

`runner.py:3450-3458` — input 처리 부분 수정:

```python
        # context_replaces 체크
        context_replaces = set(step.get("context_replaces", []))

        input_lines = []
        for inp in inputs:
            # context_replaces: context_memory로 대체 가능하면 스킵
            if inp in context_replaces:
                if self.context_memory.has_entries_for_predecessors(step.get("id", "")):
                    print(f"    [context_replaces] {inp} → context_memory로 대체")
                    continue
            resolved = self._resolve_output_path(inp)
            tag = "✓" if resolved.exists() else "✗ MISSING"
            input_lines.append(f"- {inp}: {resolved} [{tag}]")
        for inp in optional_inputs:
            if inp in context_replaces:
                if self.context_memory.has_entries_for_predecessors(step.get("id", "")):
                    continue
            resolved = self._resolve_output_path(inp)
            tag = "✓" if resolved.exists() else "없음 (선택)"
            input_lines.append(f"- {inp}: {resolved} [{tag}]")
```

프롬프트 조립(3541-3555) 부분에 scene_delta 주입 추가:

```python
<task>
Step: {step.get("id", "")} — {step.get("name", "")}
{step.get("description", "")}
{step.get("notes", "")}

{self._build_scene_delta_context(step)}

입력 파일:
{chr(10).join(input_lines) if input_lines else "- 없음"}

출력 파일 (반드시 아래 경로에 저장):
{chr(10).join(output_lines)}

{self._build_previous_review_context(step)}
{self._build_revision_instruction(step)}
모든 출력 파일을 성공적으로 생성하면 작업 완료입니다.
</task>
```

새 헬퍼 메서드:

```python
    @staticmethod
    def _build_scene_delta_context(step: dict) -> str:
        """R2+ 리뷰에서 변경 씬 delta를 프롬프트에 주입."""
        delta_json = step.get("_scene_delta", "")
        if not delta_json:
            return ""

        delta = json.loads(delta_json)
        lines = [
            "<scene_delta>",
            "⚠️ 이번 라운드는 delta 모드입니다. 아래 변경/추가된 씬만 재평가하세요.",
            f"미변경 씬 {delta['unchanged_count']}개는 이전 점수를 그대로 유지합니다.",
            "",
        ]
        if delta["changed_scenes"]:
            lines.append("## 변경된 씬:")
            lines.append(json.dumps(delta["changed_scenes"], ensure_ascii=False, indent=2))
        if delta["added_scenes"]:
            lines.append("## 추가된 씬:")
            lines.append(json.dumps(delta["added_scenes"], ensure_ascii=False, indent=2))
        if delta["removed_scene_numbers"]:
            lines.append(f"## 삭제된 씬 번호: {delta['removed_scene_numbers']}")

        lines.append("</scene_delta>")
        return "\n".join(lines)
```

- [ ] **Step 8: 챕터 빌드에서 research_report → research_digest 변경**

`runner.py:1796` 및 `1917` — 두 곳 모두 동일 수정:

기존:
```python
for fname in ["research_report.json", "outline.json"]:
```

변경:
```python
for fname in ["research_digest.json", "research_report.json", "outline.json"]:
    fpath = self.project_dir / fname
    if fpath.exists():
        context_block += f"\n<file name=\"{fname}\">\n{fpath.read_text(encoding='utf-8')[:50000]}\n</file>\n"
        break  # digest가 있으면 report 스킵
```

⚠️ 주의: 이 코드는 `research_digest.json`이 있으면 그것만 사용하고, 없으면 `research_report.json`으로 fallback. `outline.json`은 별도이므로 별도의 루프 필요. 실제로는:

```python
# 리서치 컨텍스트: digest 우선, 없으면 report fallback
for fname in ["research_digest.json", "research_report.json"]:
    fpath = self.project_dir / fname
    if fpath.exists():
        context_block += f"\n<file name=\"{fname}\">\n{fpath.read_text(encoding='utf-8')[:50000]}\n</file>\n"
        break
# outline은 별도 체크
outline_path = self.project_dir / "outline.json"
if outline_path.exists():
    context_block += f"\n<file name=\"outline.json\">\n{outline_path.read_text(encoding='utf-8')[:50000]}\n</file>\n"
```

두 곳(1796, 1917) 모두 동일하게 수정.

- [ ] **Step 9: 테스트 전체 실행**

Run: `cd /Users/jleavens_macmini/Projects/auto_kairos_v3 && python -m pytest tests/test_token_optimization.py -v`
Expected: ALL PASS

- [ ] **Step 10: 커밋**

```bash
cd /Users/jleavens_macmini/Projects/auto_kairos_v3
git add auto_agent/orchestrator/runner.py tests/test_token_optimization.py
git commit -m "feat: ratchet delta review + context_replaces + 챕터 빌드 digest 전환"
```

---

## Task 6: 에이전트 SKILL.md 업데이트

**Files:**
- Modify: `auto_agent/data/skills/agents/script-reviewer/SKILL.md`
- Modify: `auto_agent/data/skills/agents/data-mapper/SKILL.md`

- [ ] **Step 1: script-reviewer SKILL.md — delta 모드 안내 + digest 참조**

`script-reviewer/SKILL.md:82-88` — Phase 1 작업 흐름 수정:

기존:
```
1. scene_specs.json 읽기
2. research_report.json 읽기 (팩트 대조용)
3. 이전 리뷰(previous_review)가 있으면 반드시 읽기
4. 씬별로 시청자 + 전문가 관점 평가
5. 씬별 점수 + 구체적 피드백 생성
```

변경:
```
1. scene_specs.json 읽기 (delta 모드에서는 `<scene_delta>` 블록의 변경 씬만 대상)
2. research_digest.json 읽기 (팩트 대조용 — 핵심 팩트/통계 축약본)
3. 이전 리뷰(previous_review)가 있으면 반드시 읽기
4. 씬별로 시청자 + 전문가 관점 평가
5. 씬별 점수 + 구체적 피드백 생성
```

재심 규칙 앞(90번 줄 부근)에 delta 모드 설명 추가:

```markdown
### ⚠️ Delta 모드 (R2+ 자동 적용)

프롬프트에 `<scene_delta>` 블록이 있으면 delta 모드입니다:
- `<scene_delta>` 안의 변경/추가된 씬만 재채점합니다
- 미변경 씬은 이전 리뷰의 점수를 그대로 사용합니다
- scene_specs.json 전체를 다시 읽을 필요 없습니다
- 삭제된 씬 번호가 있으면 overall 점수 계산에서 제외합니다
```

- [ ] **Step 2: data-mapper SKILL.md — input 변경**

`data-mapper/SKILL.md:20-21` — 입력 섹션:

기존:
```markdown
- `scene_specs.json` — 원고+연출 완성본. 데이터 필드가 비어있거나 불완전할 수 있음
- `research_report.json` — 리서치 결과 (statistics, episodes, key_figures, timeline)
```

변경:
```markdown
- `scene_specs.json` — 원고+연출 완성본. 데이터 필드가 비어있거나 불완전할 수 있음
- `research_digest.json` — 리서치 축약본 (statistics, key_facts, episodes, timeline). 정형화된 수치/출처를 이 파일에서 매핑.
```

Step 2 설명(44번 줄)도 수정:

기존:
```markdown
`research_report.json`에서 정확한 수치를 찾아 매핑합니다.
```

변경:
```markdown
`research_digest.json`에서 정확한 수치를 찾아 매핑합니다. statistics 배열의 label/value/unit/source를 그대로 사용하세요.
```

- [ ] **Step 3: 커밋**

```bash
cd /Users/jleavens_macmini/Projects/auto_kairos_v3
git add auto_agent/data/skills/agents/script-reviewer/SKILL.md auto_agent/data/skills/agents/data-mapper/SKILL.md
git commit -m "docs: reviewer/data-mapper SKILL.md — digest 참조 + delta 모드 안내"
```

---

## Task 7: Stage 4 레거시 정리 + CLAUDE.md 업데이트

**Files:**
- Modify: `auto_agent/orchestrator/runner.py:111-123`
- Modify: `CLAUDE.md`

- [ ] **Step 1: runner.py 레거시 phase 주석 정리**

`runner.py:111-123` — `STEP_MSG` dict의 `# phase_4`, `# phase_5` 주석과 해당 항목들을 `# stage_3 (assembly-director 내부)` 주석으로 변경:

기존:
```python
    # phase_4
    "tts_preprocess":             ("TTS 전처리",           "TTS 전처리 완료"),
    "tts_generation":             ("음성 생성",            "음성 생성 완료"),
    ...
    # phase_5
    "data_validation":            ("데이터 정합성 검증",     "데이터 검증 통과"),
    ...
```

변경:
```python
    # stage_3 내부 (assembly-director 서브태스크)
    "tts_preprocess":             ("TTS 전처리",           "TTS 전처리 완료"),
    "tts_generation":             ("음성 생성",            "음성 생성 완료"),
    "image_asset_sourcing":       ("이미지 소싱",           "이미지 소싱 완료"),
    "subtitle_sync":              ("자막 동기화",           "자막 동기화 완료"),
    "tts_verification":           ("TTS 발음 검증",         "TTS 발음 검증 완료"),
    "data_validation":            ("데이터 정합성 검증",     "데이터 검증 통과"),
    "manifest_building":          ("매니페스트 빌드",        "매니페스트 빌드 완료"),
    "still_capture":              ("스틸 프레임 캡처",       "스틸 프레임 캡처 완료"),
    "qa_pre_render":              ("사전 QA 검수",          "사전 QA 검수 통과"),
    "video_assembly":             ("영상 렌더링",           "영상 렌더링 완료"),
    "qa_post_render":             ("사후 QA 검수",          "사후 QA 검수 완료"),
```

- [ ] **Step 2: CLAUDE.md — 데이터 흐름에 digest 반영**

`CLAUDE.md`의 에이전트 × 모듈 관계 표:

data-mapper 행의 입력 변경:
```markdown
| data-mapper | 2 | sonnet | scene_specs + research_digest | scene_specs.json (데이터) |
```

데이터 흐름 다이어그램에 digest 노드 추가:
```
볼트(NAS) → Stage 0 기획안 → Stage 1 리서치 → research_digest → Stage 2 원고+연출 → Stage 3 조립+렌더링 → Stage 4 성과분석 → 볼트
```

- [ ] **Step 3: 커밋**

```bash
cd /Users/jleavens_macmini/Projects/auto_kairos_v3
git add auto_agent/orchestrator/runner.py CLAUDE.md
git commit -m "docs: Stage 4 레거시 주석 정리 + CLAUDE.md에 digest 흐름 반영"
```

---

## Task 8: 통합 검증

- [ ] **Step 1: 전체 테스트 실행**

Run: `cd /Users/jleavens_macmini/Projects/auto_kairos_v3 && python -m pytest tests/test_token_optimization.py -v`
Expected: ALL PASS (9 tests)

- [ ] **Step 2: pipeline.json 유효성 검증**

Run: `cd /Users/jleavens_macmini/Projects/auto_kairos_v3 && python -c "import json; d=json.load(open('auto_agent/data/pipeline.json')); print(f'phases: {len(d[\"phases\"])}, steps: {sum(len(p[\"steps\"]) for p in d[\"phases\"])}')"`
Expected: `phases: 5, steps: 9` (기존 4 phases + stage_4, 기존 8 steps + step_4)

- [ ] **Step 3: import 검증**

Run: `cd /Users/jleavens_macmini/Projects/auto_kairos_v3 && python -c "from auto_agent.orchestrator.runner import PipelineRunner; from auto_agent.orchestrator.context_memory import ContextMemory; from auto_agent.orchestrator.vault_rag import VaultRAG; print('imports OK')"`
Expected: `imports OK`

- [ ] **Step 4: dry-run (preflight만)**

Run: `cd /Users/jleavens_macmini/Projects/auto_kairos_v3 && python -m auto_agent run --only step_0 2>&1 | tail -5`
Expected: preflight 정상 통과 (기존 동작 유지 확인)

- [ ] **Step 5: 최종 커밋 (있다면)**

변경 사항이 있으면 커밋. 없으면 스킵.
