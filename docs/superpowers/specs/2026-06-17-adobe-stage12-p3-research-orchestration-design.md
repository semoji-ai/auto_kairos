# adobe 독립 Stage 1-2 — P3: 리서치 오케스트레이션 — 설계

작성일: 2026-06-17
상태: 승인됨 (구현 계획 대기)

## 큰 그림

auto_kairos_adobe를 독립적으로 v3 수준의 기획·리서치·원고까지 수행하게 만드는 작업의 P3.
런타임 v3 의존 없음. 전체 흐름:
> 기획 → 브리프 래칫(P2) → **리서치(P3)** → 원고 초안 → 타겟 쿼리 → 타겟 리서치 → 타겟 적용 원고 → 원고 래칫 → 씬 분석(P4)

분해: P1 결정적 리서치 레인(완료) / P2 브리프+래칫(완료) / **P3 리서치 오케스트레이션(이 문서)** / P4 원고+팩트체크 / P5 통합.

## P3 범위 / 목표

editorial_brief.json(P2 산출)에서 출발해 **검색 쿼리를 생성하고, 결정적 레인(P1) 수집 + LLM 웹리서치 fan-out을 병렬 수행한 뒤, 종합해 `research_report.json`을 산출**한다(+보조 `research_digest.json`). 이 리포트가 P4 원고의 입력.

**P3가 하지 않는 것(YAGNI):** 원고·타겟 리서치·씬 분석(P4). 입력은 editorial_brief.json, 출력은 research_report.json.

## 결정사항 (확정)

- **범위:** v3 풀 패리티 — 결정적 레인 + LLM 웹리서치 fan-out.
- **웹리서치 엔진:** **claude** (`claude -p --allowedTools WebSearch,WebFetch`). 2026-06-17 probe로 실제 웹검색 동작 검증(2026 사실+출처 반환). codex 웹은 미검증이라 리서치 fan-out엔 claude 고정.
- **쿼리 생성:** v3 query_planner 이식 — 브리프→5~10 쿼리, LLM 실패 시 결정적 폴백.
- **병렬:** ThreadPoolExecutor 동시 상한(기본 3) — 오프라인 배치·rate/토큰 보호.
- **종합:** claude(스키마 강제)로 레인 소스+웹 노트 → research_report.json.

## 이식 원본 (읽기 전용, 런타임 비의존)

- query_planner: `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/research/query_planner.py` (stdlib + claude CLI, 폴백 포함)
- research-orchestrator 개념(Explorer fan-out): `.../data/skills/agents/research-orchestrator/SKILL.md` — Task 툴 미사용, adobe jobs로 재구현. Explorer 수 스케일: 1분 2~3 / 3분 3~4 / 5분 4~5 / 10분 5~6.

## 아키텍처

### 구성요소
| 단위 | 책임 | 의존 | 인터페이스/산출 |
|---|---|---|---|
| `backend/research/query_planner.py` | 브리프→쿼리 분해(5~10, 폴백) | llm | `plan_queries(brief, *, project_slug="", invoker=None) -> [{query, rationale, lang}]` |
| `backend/research/web_agent.py` | claude 웹리서치 1회 실행 | subprocess(claude) | `run_web_research(cwd, prompt, *, on_line=None, timeout=600) -> str` |
| `backend/research/orchestrator.py` | run_research 지휘 | query_planner, collector(P1), web_agent, llm | `run_research(proj_dir, *, max_workers=3, on_event=None) -> dict` |
| `backend/schemas/research_report.schema.json` | 종합 리포트 계약 | — | JSON 스키마 |

### 데이터 흐름 (run_research)
```
brief = load editorial_brief.json
queries = plan_queries(brief)                                   # 5~10
collect_queries(proj_dir, [q['query'] for q in queries])        # P1 레인 → research/raw + manifests
angles = _angles_from_brief(brief, queries, duration)           # Explorer 수 = 분량 스케일
web_notes = ThreadPool(max_workers): run_web_research(angle) → research/web/<i>_<slug>.md   # 병렬, 실패 격리
report = _synthesize(brief, sources_manifest, web_notes)        # claude+스키마 → research_report.json
digest = _digest(sources_manifest, web_notes)                   # 결정적 통계 → research_digest.json
return {report, queries:len, sources:int, web_notes:int}
```

### 신규 러너 (web_agent)
adobe `claude_runner.run_claude`는 텍스트 전용(도구 없음). 웹리서치는 별도 함수:
- `claude -p --allowedTools WebSearch,WebFetch` (스키마 없음 — 도구 사용 + 자유 텍스트 노트)
- 중첩 env 제거(CLAUDECODE/CLAUDE_CODE_ENTRYPOINT/CLAUDE_CODE_SSE_PORT) — 안 하면 행
- stdin 프롬프트, capture_output, timeout. 실패(rc≠0/예외/타임아웃) → "" 반환(부분 실패 격리)

### research_report.json 구조 (P4 입력 계약)
```json
{
  "topic": "...",
  "queries": ["..."],
  "sources": [{"title","url","tier_hint","lane","snippet"}],
  "web_findings": [{"angle","claim","source_url"}],
  "digest": {"key_facts": ["..."], "figures": ["..."]}
}
```
종합 스키마는 핵심 키만 required + additionalProperties(LLM 거부 방지).

## 에러 처리
- editorial_brief.json 없음 → `{error: "브리프 필요 (P2 먼저)"}`.
- plan_queries LLM 실패 → 결정적 폴백 쿼리(real_topic 등). 쿼리 0이면 `{error}`.
- 레인 수집 부분 실패 → P1이 이미 격리(error 엔트리).
- 웹 에이전트 개별 실패 → 빈 노트, 나머지 진행.
- 종합 LLM 실패/파싱 실패 → 결정적 digest만으로 최소 research_report 생성(sources+digest, web_findings=[]) + 경고.

## 테스트 전략 (stdlib·monkeypatch, 실 LLM/웹 0)
1. **query_planner**: invoker(=가짜 LLM) 주입 → JSON 파싱·쿼리 수 제한·통문장 거부·폴백.
2. **web_agent**: `subprocess.run` monkeypatch → 노트 텍스트 반환 / rc≠0·타임아웃 → "".
3. **orchestrator**: plan_queries·collect_queries·run_web_research·_synthesize 전부 monkeypatch →
   - 쿼리→레인→fan-out 병렬→머지→research_report.json 생성
   - 웹 에이전트 1개 실패해도 나머지 노트 반영(부분 실패 격리)
   - Explorer 수가 분량(plan.md duration)에 따라 스케일
   - 종합 LLM 실패 → digest-only 폴백 리포트
   - brief 없음 → error
4. **스키마/스케일 유틸** 단위 테스트.
5. 실제 웹 스모크: 옵트인 `AK_RESEARCH_E2E=1`(claude 웹 1회) — 기본 skip.

## 범위 밖 (P4~P5)
- 원고 초안·타겟 쿼리·타겟 리서치·타겟 적용·원고 래칫·씬 분석(P4)
- 패널/파이프라인 통합(P5)
