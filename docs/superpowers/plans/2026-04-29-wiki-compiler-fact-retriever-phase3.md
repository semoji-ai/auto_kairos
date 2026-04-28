# Phase 3 — Wiki Compiler + Fact Retriever 구현 계획

작성일: 2026-04-29
연관 spec: `docs/superpowers/specs/2026-04-28-research-redesign.md` (Phase 3)
브랜치: `feature/live-doc-snapshot`

---

## 목표

Phase 1(fresh_collector)이 raw + manifests를 만들고, Phase 2(vault_lookup)가 볼트 wiki를 흡수했습니다. 이제:

1. **wiki_compiler**: raw + 흡수자료 → 프로젝트 `wiki/<topic>/{overview,claims,entities,timeline}.md`로 컴파일
2. **fact-retriever**: 글 쓰면서 사실 필요할 때 호출되는 사이드카 에이전트. evidence span 강제 검증
3. **script-director 통합**: `fact_retrieve` tool로 호출 가능하게 노출

성공 기준:
- 펩시 영상 재실행 시 `wiki/pepsi/claims.md`가 raw 252 sources에서 자동 컴파일
- script-director가 글 쓰는 도중 fact-retriever 호출하여 evidence-backed 클레임 ledger 생성
- `claims_ledger.jsonl` 모든 entry에 evidence span + source_url + chunk_anchor 포함
- evidence span은 chunk 원문에 substring으로 매칭 강제 (환각 차단)

## 산출물

```
auto_agent/research/
├── wiki_compiler.py          # raw + 흡수자료 → wiki/*.md 컴파일
└── evidence_check.py         # span ↔ chunk substring 검증

auto_agent/modules/
└── wiki_compiler_module.py   # 파이프라인 진입점

auto_agent/data/skills/agents/
└── fact-retriever/
    └── SKILL.md              # 사이드카 에이전트 정의 (sonnet, max_turns=5)

# script-director 변경
auto_agent/data/skills/agents/script-director/
└── SKILL.md                  # fact_retrieve tool 호출 절차 추가

auto_agent/data/
├── pipeline.json             # step_1d_wiki_compile 추가
└── agents.json               # fact-retriever 등록

tests/
├── test_wiki_compiler.py
├── test_evidence_check.py
└── test_fact_retriever_integration.py
```

## 단계별 실행 순서

### Step 3.1 — Evidence span 검증기 (먼저, 가장 간단)
- `auto_agent/research/evidence_check.py`
  - `verify_span_in_chunk(span, chunk_text) -> bool` — span이 chunk에 substring으로 들어있는지
  - 공백/구두점 normalize 후 비교 (한국어 띄어쓰기 변동 허용)
  - span 길이 30~300자 게이트
- 테스트: 정확 일치, 공백 정규화, 길이 미달, 길이 초과, 환각(없는 span)

### Step 3.2 — wiki_compiler
- `auto_agent/research/wiki_compiler.py`
  - 입력: 프로젝트 `research/raw/<topic>/<run>/source_notes/*.md` + `manifests/<topic>/sources.jsonl` + 볼트 흡수 wiki/*.md
  - 출력: 프로젝트 `wiki/<topic>/{overview,claims,entities,timeline,index}.md` (frontmatter + Obsidian 스타일)
- LLM 사용 (sonnet, max_turns=10): raw → 구조화 wiki 페이지
- 컴파일 정책:
  - 흡수된 vault wiki(`overview.vault.md` 등)가 있으면 base로 활용 + 신규 raw 추가분 머지
  - 없으면 raw에서 처음부터 합성
  - claims.md는 jsonl(`manifests/<topic>/claims.jsonl`) 그대로 markdown 렌더 (LLM 안 씀)

### Step 3.3 — fact-retriever 에이전트
- `auto_agent/data/skills/agents/fact-retriever/SKILL.md`
  - 모델: sonnet, max_turns: 5
  - 입력 (tool params): `query`, `entity[]`, `year?`, `claim_kind`
  - 동작:
    1. 프로젝트 wiki/manifests에서 entity/year 매칭 source 후보 추출 (메타 인덱스 활용)
    2. 후보 source의 raw markdown chunk를 Read로 직접 읽음
    3. query에 매칭되는 evidence span 추출 (30~300자)
    4. span이 chunk 원문 substring인지 강제 검증
    5. claim_kind 차등 게이트:
       - `fact:date_or_number` → A 1건 필수
       - `fact:event` → A 1건 또는 B 2건
       - 부족 시 confidence: low + warning
    6. 반환: `{claim, evidence_span, source_id, source_url, tier, confidence, claim_kind, anchor}`
  - 출력 스키마 명시 (script-director가 안전하게 파싱)

### Step 3.4 — wiki_compiler_module 파이프라인 진입점
- `auto_agent/modules/wiki_compiler_module.py`
- step_1_vault_lookup 직후, step_1b 직전에 위치
- PROJECT_DIR 환경변수에서 research/ 경로 추론

### Step 3.5 — script-director SKILL.md에 fact_retrieve tool 통합
- 글 쓰면서 사실이 필요한 시점:
  - "이 챕터에 1933 안티푸라민 출시 사실 필요" → tool call
  - 결과를 `claims_ledger.jsonl`에 한 줄 추가
  - 본문에 evidence-backed 인용 임베드
- claim_ledger 스키마 명시 + script-director가 ledger를 직접 append하도록 instructions

### Step 3.6 — pipeline.json + agents.json 등록
- `step_1d_wiki_compile` 신규 (sequential, blocking, resumable)
- fact-retriever는 step이 아니라 script-director가 호출하는 도구이므로 pipeline.json엔 없음
- agents.json에 fact-retriever 정의

### Step 3.7 — 테스트
- `test_evidence_check.py`: substring + normalize + 길이 게이트
- `test_wiki_compiler.py`: mock LLM으로 raw → wiki/*.md 컴파일 검증, frontmatter 정확성
- `test_fact_retriever_integration.py`: 실제 SKILL.md 로드 + tool call schema 검증 (LLM은 안 부름)

### Step 3.8 — 펩시 프로젝트 재실행 검증
- 기존 `output/4d210cc6_펩시의_역사`에 wiki_compiler만 돌려보기
- `wiki/pepsi/{claims,entities,timeline}.md` 생성 확인
- script-director가 fact-retriever 호출하면 claims_ledger 채워지는지

## 의존성

| 항목 | 필수 | 비고 |
|---|---|---|
| Phase 1 (fresh_collector) | ✅ | raw + manifests 입력 |
| Phase 2 (vault_lookup) | ✅ | 흡수 wiki 입력 (있으면) |
| Claude CLI | ✅ | wiki_compiler + fact-retriever 둘 다 |
| ANTHROPIC_API_KEY | 선택 | CLI subprocess가 사용 |

## 위험과 대응

| 위험 | 대응 |
|---|---|
| LLM이 evidence span을 fabricate | substring 검증 강제. 실패 시 fact-retriever return 거부 |
| wiki_compiler가 vault wiki 덮어쓰기 | 흡수자료는 `*.vault.md` 접미사로 보존 (Phase 2 기존 정책) |
| fact-retriever 호출 비용 | sonnet + max_turns=5 + claim_id 캐싱 (같은 query 재호출 시 캐시 반환) |
| chunk 원문 길이 초과 | sources_notes 마크다운 청크 size limit (~5000자/source) |
| script-director가 ledger 형식 어긋남 | SKILL.md에 strict JSON schema 예시 + validation hint |

## 작업 시간 추정

| Step | 시간 |
|---|---|
| 3.1 evidence_check | 1h |
| 3.2 wiki_compiler | 2h |
| 3.3 fact-retriever SKILL.md | 1.5h |
| 3.4 wiki_compiler_module | 0.5h |
| 3.5 script-director 통합 | 1h |
| 3.6 pipeline.json + agents.json | 0.5h |
| 3.7 테스트 | 1.5h |
| 3.8 펩시 재실행 검증 | 1h |
| **합계** | **~9h** |

## 다음 Phase 미리보기

- **Phase 4**: vault-sync-agent (manual trigger, 프로젝트 wiki/claims_ledger → 볼트 push)
- **Phase 5**: cutover & cleanup (step_1_ingest 폐기, ResearchAgent NAS 의존성 제거)
