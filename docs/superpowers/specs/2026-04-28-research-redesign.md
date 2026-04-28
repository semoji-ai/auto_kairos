# 리서치 파이프라인 재설계 — Lazy Validation + 2-Tier Retrieval

작성일: 2026-04-28
대상 모듈: `step_1_ingest`, `step_1b`, `step_2_draft`, `step_2_target`
연관 이슈: 유한양행 step_1_ingest 실패(specialist `seed_only` blocked), 2차 토픽 `source_ids=n/a`

---

## 1. 문제 (Why)

현재 `step_1_ingest`는 **수집 + 신뢰도 게이팅 + 클레임화**를 한 번에 처리합니다. 그 결과:

- ResearchAgent의 7-stage 루프가 quality-assurance에서 `blocked / specialist seed_only`로 멈추는 사례 빈발
- 게이트가 너무 많아 정작 중요한 정보도 차단될 위험
- 게이트 통과한 클레임도 `source_ids: []`로 비어 나오는 경우 — LLM 사전지식 의존 (환각 위험)
- 한국 뉴스 RSS URL 데드(404/400) — 외부 NAS 코드라 우리 레포에서 패치 불가
- 클레임은 _수집 시점_이 아니라 _글 쓰는 시점_에 만들어져야 의미 있는데, 순서가 반대

근본: **검증 게이트가 앞단에 너무 무겁게 박혀 있음.**

## 2. 목표 (What)

1. Fresh 단계는 **가볍게**: lane(API/RSS) 호출 + raw 보관 + 메타 인덱싱만. 검증 게이트 제거.
2. 클레임 생성을 **원고 작성 시점**으로 이동. 글의 맥락에서 retrieve.
3. 모든 클레임에 **Evidence span 강제**. 환각 차단.
4. 토큰 부담은 **2-tier retrieval**(메타 + 벡터)로 통제.
5. ResearchAgent 의존성 제거 — lane만 우리 레포로.

## 3. 핵심 설계 결정

### 3-1. 인덱스 — 메타 + 벡터 듀얼

| Tier | 위치 | 용도 |
|---|---|---|
| 메타 인덱스 | `output/<proj>/research/index/meta.jsonl` | 제목/URL/엔티티/날짜/태그/요약 50자 — 통전달 가능 |
| 벡터 인덱스 | `output/<proj>/research/index/vectors/` (chromadb) | source 본문을 chunk(~500자)로 분할, embedding 저장 |

### 3-2. 클레임 주체 — `fact-retriever` 신규 에이전트

script-director는 narrative만 책임. 클레임이 필요하면 tool 호출.

```
script-director가 글 쓰던 중:
  "이 챕터에 '1933 안티푸라민 출시' 사실이 들어가야 함"
   ↓ tool: fact_retrieve(query="1933 안티푸라민 출시", entity=["안티푸라민"], year=1933)
fact-retriever (sonnet, max_turns=5):
  1. 메타 인덱스에서 entity/year 매칭 → top-N source 후보
  2. 후보 source의 vector chunks에서 query top-K retrieval
  3. evidence span 추출 + tier 판정
  4. 반환: { claim, evidence_span, source_id, tier, confidence }
   ↓
script-director: claims_ledger.jsonl 한 줄 추가 + 본문에 인라인 참조
```

### 3-3. Evidence 기준 — claim_kind 차등

| claim_kind | 필수 evidence | 비고 |
|---|---|---|
| `fact:date_or_number` | A 1건 + 인용 span | 정확성 핵심 |
| `fact:event` | A 1건 또는 B 2건 |  |
| `fact:context` | A 1건 또는 B 2건 교차 | 배경 설명 |
| `interpretation` | A 1건 + "작성자 의견" 명시 | 해석/평가 |
| `filler / transition` | 불필요 | 연결어 |

**Tier 정의**:
- **A (canonical)**: ko/en.wikipedia.org, 공식 도메인(`*.go.kr`, `yuhan.co.kr` 같은 회사 official), 언론 mainstream(연합/조선/한겨레/동아/중앙/매경 등)
- **B (corroborated)**: Crossref/학술, 1차 사료 PDF, 정부 발간물
- **C (excluded)**: 블로그/나무위키/카페 — 색인은 하되 evidence 채택 ❌

**Evidence span 규격**:
- 30~300자 인용 텍스트
- 필수 메타: `source_url`, `retrieved_at`, `source_id`, `paragraph_anchor` (문단 번호 또는 chunk_id)

### 3-4. ResearchAgent 위치 — lane만 import

| 옵션 | 결정 |
|---|---|
| a) 외부 NAS 그대로 사용 + fresh 모드 플래그 | ❌ — 7-stage 무게 + NAS 의존 |
| **b) lane만 떼어 우리 레포로** | ✅ **채택** |
| c) 전체 fork | ❌ — 유지보수 부담 |

**구체화**:
- `auto_agent/research/lanes/` 신규 — `wikipedia.py`, `news_rss.py`, `crossref.py`, `openlibrary.py`
- 한국 RSS 데드 URL 우리 레포에서 패치 (Naver Open API 또는 카테고리 RSS로 대체)
- 7-stage 루프, specialist subagent, quality-assurance 게이트 — **전부 폐기**
- ResearchAgent 자체는 targeted_research 정밀 보강 단계에서만 (옵션) 호출 — 또는 영원히 안 호출

### 3-5. 토큰 부담 — 2-tier retrieval

**원고 길이별 데이터량 예상**:
| 길이 | 씬 | raw 소스 | 메타 인덱스 토큰 | 본문 총 토큰 |
|---|---|---|---|---|
| 1분 | 5-7 | 50-100 | ~5K | ~50K |
| 3분 | 15-20 | 200-300 | ~15K | ~150K |
| 5분 | 25-30 | 300-500 | ~25K | ~250K |
| 10분 | 50+ | 500-1000 | ~50K | ~500K |

**검색 패턴**:
1. 챕터 시작 시 — 메타 인덱스에서 entity/keyword 필터 → top-N (5~10) source 후보 압축
2. claim 단위로 — 후보 source의 vector chunks 안에서 query top-K retrieval → evidence span
3. 챕터 종료 시 — 이전 raw 컨텍스트 dump, 메타 인덱스만 유지

**효과**: 본문 raw는 LLM에 통째로 넣지 않음. 10분 영상 1000건도 토큰 통제 가능.

## 4. 새 파이프라인 흐름

```
[기존]
step_1_ingest    수집 + 클레임 (게이트로 막힘)        ❌
step_1b          chapter_facts (검증된 클레임만)
step_2_target    부족분 추가 검색

[제안]
step_1_fresh     lane으로 raw 광역 수집 + 메타 + 벡터 인덱싱  ✅
step_2_draft     초고 작성 + on-the-fly 클레임 (fact-retriever tool 호출)
step_2_target    부족 entity/topic 정밀 보강 (그대로 유지)
step_2_evidence  클레임 evidence 누락 검증 게이트 (신규)
step_2 (chapters) script-director — 클레임 ledger 임베드된 scene_specs 생성
```

## 5. 디렉토리 구조

```
output/<proj>/research/
├── raw/                      # 기존 source_notes/*.md 유지
├── index/
│   ├── meta.jsonl            # 1줄 = 1 source 메타
│   └── vectors/              # chromadb 디렉토리
├── manifests/                # 기존 유지 (호환)
└── claims_ledger.jsonl       # 신규 — 원고 작성 중 누적되는 클레임
```

`claims_ledger.jsonl` 한 줄:
```json
{
  "claim_id": "...",
  "claim": "1933년 안티푸라민 출시 (자체개발 1호)",
  "kind": "fact:date_or_number",
  "tier": "A",
  "evidence": {
    "source_id": "src_yuhan_history_official",
    "url": "https://www.yuhan.co.kr/introduce/history/",
    "span": "1933년 12월, 자체 개발 진통소염제 안티푸라민을 출시...",
    "retrieved_at": "2026-04-28T16:42:00Z",
    "anchor": "chunk_07"
  },
  "used_in_chapter": 3,
  "used_in_scene": null,
  "created_by": "fact-retriever",
  "created_at": "..."
}
```

## 6. 마이그레이션 계획

### Phase 1 — Fresh Collector (독립 모듈, 기존과 병행)
- `auto_agent/research/lanes/` 4종 import (Wikipedia/News/Crossref/OpenLibrary)
- 한국 RSS URL 패치
- `fresh_collector_module.py` — lane 호출 → raw + meta.jsonl 생성
- 새 step `step_1_fresh` 추가, **`step_1_ingest`와 병행**해서 비교 검증
- 벡터 인덱싱은 Phase 2로 미룸

### Phase 2 — 벡터 인덱스
- `auto_agent/research/indexer.py` — raw → chunk → embedding → chromadb
- chunking 정책 결정 (~500자, overlap 50자)
- 임베딩 모델: text-embedding-3-small or 로컬 sentence-transformers

### Phase 3 — fact-retriever 에이전트
- `auto_agent/data/skills/agents/fact-retriever/SKILL.md`
- script-director에 tool로 노출
- claim_kind 차등 게이트 + Evidence span 검증

### Phase 4 — 파이프라인 컷오버
- `step_1_ingest` 폐기, `step_1_fresh`로 교체
- `step_1b`(chapter_projection) — 메타 인덱스 기반으로 재작성
- `step_2_evidence` 게이트 추가 (evidence 누락 클레임 검출)
- ResearchAgent 호출 코드 제거

### Phase 5 — Cleanup
- ResearchAgent NAS 의존성 제거
- 옛 manifests 형식 호환 코드 정리

## 7. 위험과 미결 질문

| 항목 | 해결 방안 |
|---|---|
| **fact-retriever 호출 비용 증가** | sonnet + max_turns=5 + 결과 캐싱(claim_id 단위) |
| **embedding 비용** | 로컬 모델 우선 검토 (sentence-transformers); 10분 영상 ~1000 chunks → 클라우드 비용 미미 |
| **챕터 컨텍스트 슬라이싱 경계** | runner.py에 `chapter_context_manager` 신규 — director에 챕터별 메타만 주입 |
| **기존 프로젝트 마이그레이션** | 옛 `claims.jsonl`(ResearchAgent 형식) → `claims_ledger.jsonl` 자동 변환 스크립트 |
| **fact-retriever evidence 환각** | retrieved chunk 원문 vs span 일치 검증 — span이 chunk 안에 substring인지 강제 체크 |
| **Tier A 도메인 화이트리스트** | `auto_agent/research/trust_tiers.json` 별도 관리, PR로 갱신 |

## 8. 결정 필요 (다음 세션에서)

- [ ] embedding 모델 — 로컬 vs 클라우드
- [ ] chunk 크기 / overlap 수치 확정
- [ ] Tier A 도메인 초기 리스트 작성
- [ ] step_1_fresh와 기존 step_1_ingest 병행 기간 설정
- [ ] fact-retriever를 별도 에이전트(Claude CLI subprocess) vs script-director 내부 tool 함수로 호출할지

---

**작성 후 결정 흐름**: 이 spec을 기반으로 Phase 1 구현 plan을 별도 파일로 작성 → `docs/superpowers/plans/2026-04-28-fresh-collector-phase1.md`
