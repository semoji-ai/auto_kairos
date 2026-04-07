# Token Optimization — 설계 스펙

> auto_kairos_v3 파이프라인의 토큰 효율 최적화. 기존 파이프라인 호환성 유지.

## 배경

현재 구현은 "품질 방어를 위해 맥락을 넉넉히 주는 설계"로, 같은 대형 문서(research_report.json 50-200KB)가 4-5개 스텝에서 반복 소비됨. 프로젝트당 ~200K 토큰 중 ~120K가 중복. 목표: **~70-80K로 절감 (60%)**, 품질 저하 없이.

---

## 변경 사항 (5개)

### 1. research_digest.json 생성

**목적:** research_report.json 전문 대신 정형 축약본을 후속 스텝에 전달

**시점:** `_merge_research_artifacts()` 완료 직후, runner.py에서 Sonnet 1회 호출

**스키마:**
```json
{
  "topic": "string",
  "core_thesis": "핵심 논지 2-3문장",
  "key_facts": [
    {"fact": "string", "source": "string", "confidence": "high|medium|low"}
  ],
  "statistics": [
    {"label": "string", "value": "number|string", "unit": "string", "source": "string"}
  ],
  "episodes": [
    {"title": "string", "summary": "1-2문장", "characters": ["string"]}
  ],
  "timeline": [
    {"date": "string", "event": "string"}
  ],
  "sources": [
    {"title": "string", "url": "string", "reliability": "high|medium|low"}
  ]
}
```

**생성 방법:**
- `runner.py`에 `_generate_research_digest()` 메서드 추가
- Anthropic API로 Sonnet 1회 호출 (research_report.json 전문 입력 → digest 출력)
- 비용: ~$0.05/프로젝트
- 출력: `{project_dir}/research_digest.json`

**소비자 매핑 변경:**

| 스텝 | 현재 input | 변경 후 input |
|------|-----------|--------------|
| step_2 (script-director) | research_report.json | research_report.json (유지) |
| step_2_review (ratchet reviewer) | research_report.json | **research_digest.json** |
| step_2_review (ratchet reviser) | research_report.json | **research_digest.json** |
| step_2_data (data-mapper) | research_report.json | **research_digest.json** |
| step_2b (fact-verifier) | research_report.json | research_report.json (유지) |
| step_3b (assembly-director) | (pipeline.json에 없지만 챕터 빌드에서 인라인) | **research_digest.json** |

**script-director(초벌):** 서사 깊이를 위해 원문 유지
**fact-verifier:** 원문 대조가 본질이므로 원문 유지
**나머지:** digest로 충분

**안전장치:**
- `research_digest.json` 생성 실패 시 `research_report.json`으로 fallback
- `_generate_research_digest()` 내부에서 try/except → fallback 로그 출력

**챕터 병렬 빌드 변경 (runner.py 1796, 1917):**
- 현재: `research_report.json[:50000]` 인라인 주입
- 변경: `research_digest.json` 인라인 주입 (digest는 ~5-10KB이므로 truncation 불필요)

### 2. Ratchet Delta Review

**목적:** 매 라운드 전체 재전송 대신 변경 씬만 전달

**구현:**

`runner.py`의 `_run_ratchet_loop()` 내부에 `_compute_scene_delta()` 추가:

```python
def _compute_scene_delta(self, prev_specs: str, curr_specs: str) -> dict:
    """이전/현재 scene_specs 비교 → 변경된 씬 번호 + JSON 추출."""
    prev = json.loads(prev_specs)
    curr = json.loads(curr_specs)
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

**적용 방식:**
- **R1 (첫 리뷰):** 전체 scene_specs.json 전달 (기준선)
- **R2, R3:** delta만 전달 + `<unchanged_scenes_summary>N개 씬 미변경 — 이전 점수 유지</unchanged_scenes_summary>`
- reviewer SKILL.md의 재심 규칙(미수정 씬 점수 고정)과 자연스럽게 연결

**reviewer input 변경:**
```python
# R1: 기존과 동일
review_step["input"] = ["scene_specs.json", "research_digest.json"]

# R2+: delta 주입
review_step["_scene_delta"] = delta_json  # 변경 씬만
review_step["input"] = ["research_digest.json"]  # scene_specs.json 전체 제거
```

**reviser input 변경:**
```python
# 현재
"input": ["scene_specs.json", "review_feedback.json", "research_report.json"]
# 변경
"input": ["scene_specs.json", "review_feedback.json", "research_digest.json"]
```
- reviser는 Edit 도구로 수정하므로 scene_specs.json 전체 접근 필요 (유지)
- research_report → research_digest로 교체

**안전장치:**
- delta 계산 실패 시 전체 scene_specs.json 전달 (기존 동작)

**_build_agent_prompt에 delta 주입:**
- `step.get("_scene_delta")`가 있으면 `<scene_delta>` 태그로 프롬프트에 추가
- reviewer SKILL.md 수정: delta 모드 안내 추가 (R2+ 시 delta만 받을 수 있음)

### 3. ContextMemory 원본 대체 모드

**목적:** context_memory가 있으면 원본 파일 동시 주입 방지

**구현:**

pipeline.json의 step 정의에 `context_replaces` 필드 추가:

```json
{
  "id": "step_3b",
  "name": "assembly",
  "context_replaces": ["research_report.json"],
  ...
}
```

`_build_agent_prompt()`에서:
```python
context_replaces = set(step.get("context_replaces", []))
for inp in inputs:
    if inp in context_replaces:
        # context_memory에 해당 스텝 요약이 있으면 스킵
        if self.context_memory.has_entries_for_predecessors(step["id"]):
            continue
    # 기존 로직
    resolved = self._resolve_output_path(inp)
    ...
```

**적용 범위:** step_3b만 (assembly-director)
- assembly는 scene_specs.json 중심으로 작동
- research 맥락은 context_memory의 step_1 요약으로 충분
- step_3b는 이미 `context_replaces`에 의해 research_report.json 대신 research_digest.json을 받게 되므로, 실질적으로는 digest마저도 context_memory로 대체하는 2중 절감

**ContextMemory에 헬퍼 추가:**
```python
def has_entries_for_predecessors(self, current_step_id: str) -> bool:
    """현재 스텝 이전에 수집된 엔트리가 있는지 확인."""
    memory = self.load()
    return any(
        _step_order(e["step_id"]) < _step_order(current_step_id)
        for e in memory.get("entries", [])
    )
```

### 4. Stage 4 문서/코드 정리

**목적:** pipeline.json과 CLAUDE.md 간 Stage 4 정의 일치

**변경 내용:**

**(a) pipeline.json에 stage_4 추가:**
```json
{
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
      "notes": "launchd로 실행. 파이프라인 내부에서 호출하지 않음."
    }
  ]
}
```

**(b) runner.py 레거시 정리:**
- `phase_4`, `phase_5` 관련 메시지/코드 흔적 검색 → 제거

**(c) CLAUDE.md:** 이미 Stage 4를 "성과 분석"으로 기술하고 있으므로 pipeline.json과 일치시키기만 하면 됨

### 5. Vault RAG 결과 캐싱

**목적:** 동일 프로젝트 내 중복 검색 방지

**구현:**

`vault_rag.py`의 `VaultRAG` 클래스에:

```python
def __init__(self, ...):
    ...
    self._search_cache: dict[str, str] = {}

def search_for_research(self, topic: str, category: str) -> str:
    cache_key = f"research:{topic}:{category}"
    if cache_key in self._search_cache:
        return self._search_cache[cache_key]
    result = self._do_search_for_research(topic, category)
    self._search_cache[cache_key] = result
    return result

def search_for_manuscript(self, topic: str, category: str) -> str:
    cache_key = f"manuscript:{topic}:{category}"
    if cache_key in self._search_cache:
        return self._search_cache[cache_key]
    result = self._do_search_for_manuscript(topic, category)
    self._search_cache[cache_key] = result
    return result
```

- 기존 `search_for_research` → `_do_search_for_research`로 rename
- 기존 `search_for_manuscript` → `_do_search_for_manuscript`로 rename
- 캐시는 VaultRAG 인스턴스 수명(= runner 실행 단위)과 동일

---

## 수정 대상 파일 목록

| 파일 | 변경 내용 |
|------|----------|
| `auto_agent/orchestrator/runner.py` | digest 생성, ratchet delta, context_replaces 로직, 레거시 정리, 챕터 빌드 변경 |
| `auto_agent/orchestrator/context_memory.py` | `has_entries_for_predecessors()` 추가 |
| `auto_agent/orchestrator/vault_rag.py` | 캐시 레이어 추가 |
| `auto_agent/data/pipeline.json` | step input 변경, context_replaces 추가, stage_4 추가 |
| `auto_agent/data/skills/agents/script-reviewer/SKILL.md` | delta 모드 안내, research_digest 참조로 변경 |
| `auto_agent/data/skills/agents/data-mapper/SKILL.md` | input을 research_digest.json으로 변경 |
| `CLAUDE.md` | Stage 4 설명 pipeline.json과 일치 |

## 건드리지 않는 것

- scene_specs.json 스키마
- 에이전트 호출 방식 (stdin)
- Guard hooks, post-step validators
- Remotion 관련 코드
- research-orchestrator (리서치 자체는 변경 없음)
- fact-verifier (원문 접근 유지)

## 예상 토큰 절감

| 항목 | 현재 | 변경 후 | 절감 |
|------|------|---------|------|
| research_report 반복 읽기 | ~60K | ~15K (digest 4회) | ~45K |
| ratchet loop (3라운드) | ~90K | ~40K (delta + digest) | ~50K |
| assembly context | ~20K | ~2K (context_memory) | ~18K |
| vault 중복 검색 | ~2K | ~1K | ~1K |
| **합계** | ~172K | ~58K | **~114K (66% 절감)** |

추가 비용: digest 생성 Sonnet 1회 ~$0.05/프로젝트

## 안전장치 요약

1. research_digest.json 생성 실패 → research_report.json fallback
2. delta 계산 실패 → 전체 scene_specs.json 전달
3. context_replaces는 pipeline.json에 명시한 스텝만 적용
4. Stage 4는 문서 정리만, 실행 로직 변경 없음
5. 모든 변경은 기존 output 파일 구조와 호환
