# Auto Kairos 리서치 아키텍처 변경 요청

## 제목
`chapter_facts 직접 생성` 구조를 `raw source → LLM wiki/claim store → chapter_facts projection` 구조로 변경 요청

## 배경
현재 Stage 1 리서치는 챕터별로 LLM이 WebSearch/WebFetch를 수행하고, 그 결과를 바로 `chapter_facts/`로 정리하는 방식입니다.

이 구조의 장점은 빠르게 원고용 fact pack을 만들 수 있다는 점이지만, 아래 한계가 분명합니다.

### 현재 구조의 한계
1. **속도 비효율**
   - 챕터별 검색이 반복되어 같은 주제/같은 기사군을 여러 번 다시 찾음
   - 리런 시에도 검색 비용과 시간이 다시 들어감

2. **provenance 약화**
   - LLM이 여러 기사 내용을 하나의 `answer`로 합성하면서
   - 어떤 문장이 정확히 어느 source에서 왔는지 추적이 약해짐

3. **재사용성 부족**
   - 현재 지식 저장 단위가 “챕터”라서
   - draft/fact-check/rewrite에서 다른 문맥으로 재조합하기 어려움

4. **팩트체크 비효율**
   - `chapter_facts`는 writer-friendly하지만 verifier-friendly하지 않음
   - claim/source 단위 역추적이 어려움

---

## 제안 요약
리서치 저장의 canonical layer를 `chapter_facts`에서 `LLM wiki + claim store`로 올리고, `chapter_facts`는 그 위에서 생성되는 파생 산출물(view)로 바꾸는 구조를 제안합니다.

### 제안 구조
1. **Raw Source Ingestion**
   - lane API / RSS API / 기타 구조화된 API로 대량 수집
   - 부족한 항목만 WebSearch/WebFetch로 fallback

2. **Corpus Normalization**
   - dedupe / canonical URL / content hash / publish date 정리
   - 원문과 메타데이터를 문서 단위로 저장

3. **LLM Wiki / Claim Store 생성**
   - 문서들을 엔티티/사건/수치/주장 단위로 정규화
   - 페이지 간 위키 링크 생성
   - 각 claim에 source 연결

4. **Chapter Facts Projection**
   - outline + editorial_brief 기준으로
   - wiki/claims에서 필요한 것만 챕터별로 projection
   - 기존 `chapter_facts/chapter_{N}.json`은 유지하되, 내부적으로는 파생 뷰로 취급

---

## 핵심 설계 원칙
### `chapter_facts`는 source of truth가 아니라 writer-facing view여야 합니다.

즉 계층은 아래처럼 분리되어야 합니다.

- **소스 레이어**: raw documents / feeds
- **정규화 레이어**: research wiki / claim store
- **소비 레이어**: chapter_facts / draft inputs

현재는 소비 레이어(`chapter_facts`)가 사실상 유일한 리서치 저장소 역할을 하고 있어서,
속도·추적성·재사용성 모두에 손해가 있습니다.

---

## 권장 파이프라인 개편안

### 현재
- `step_1a`: skeleton_research
- `step_1b`: flesh_research → `chapter_facts/`

### 제안
- `step_1_ingest`: **source_ingest**
  - lane/RSS/API 우선 수집
  - 부족한 경우만 WebSearch fallback
  - 출력: `raw_sources/`, `source_index.jsonl`

- `step_1_norm`: **knowledge_normalize**
  - dedupe / canonicalize / claim extraction / entity linking
  - 출력:
    - `research_corpus.jsonl`
    - `research_claims.jsonl`
    - `research_wiki/pages/*.md` 또는 `research_wiki.json`

- `step_1a`: **skeleton_research**
  - 입력: `editorial_brief + research_wiki`
  - 역할: 내러티브 골격 설계

- `step_1b`: **chapter_projection**
  - 입력: `outline + research_wiki + research_claims`
  - 출력: `chapter_facts/`

즉 `flesh_research`를 완전히 없애자는 뜻이 아니라,
**“챕터별 검색”에서 “지식베이스 기반 챕터 프로젝션”으로 역할을 바꾸자**는 제안입니다.

---

## 산출물 제안

### 1) Raw source layer
#### `source_index.jsonl`
각 문서/피드 항목 단위 메타데이터 저장

예시 필드:
- `source_id`
- `source_type` (`lane`, `rss`, `web_search`, `manual`)
- `title`
- `url`
- `canonical_url`
- `domain`
- `published_at`
- `fetched_at`
- `lang`
- `content_hash`
- `snippet`
- `raw_path`

### 2) Claim layer
#### `research_claims.jsonl`
검증 가능한 주장 단위 저장

예시 필드:
- `claim_id`
- `claim_text`
- `entity_ids`
- `source_ids`
- `first_seen_at`
- `confidence`
- `verification_status` (`verified`, `weak`, `disputed`, `derived`)
- `claim_type` (`numeric`, `quote`, `timeline`, `causal`, `context`)

### 3) Wiki layer
#### `research_wiki/pages/*.md` 또는 JSON
엔티티/사건/제도 중심 페이지 저장

예시:
- `sk-hynix-bonus-2964`
- `korea-earned-income-tax-progressive`
- `dc-pension-tax-deferral`
- `tax-revenue-shortfall-2023-2024`

각 페이지에는:
- summary
- linked pages
- related claim_ids
- canonical source_ids

### 4) Chapter projection layer
#### `chapter_facts/chapter_{N}.json`
기존 포맷 유지 가능. 단, 아래 참조 필드 추가 권장:
- `page_ids`
- `claim_ids`
- `source_ids`

이렇게 하면 draft-writer는 지금처럼 읽기 쉬운 챕터 팩트를 쓰면서도,
필요 시 원문/위키/claim까지 역추적할 수 있습니다.

---

## 기대 효과

### 1. 속도 개선
- 챕터별 중복 WebSearch 감소
- source 수집과 정규화를 캐시 가능
- 리런 시 전체 검색을 다시 하지 않아도 됨

### 2. draft 작성 품질 개선
- 챕터 단위 facts뿐 아니라
- 위키 링크를 따라가며 맥락 확장 가능
- 같은 사실을 여러 챕터/여러 버전 원고에서 재활용 가능

### 3. fact-check 정확도 개선
- claim 단위 source 추적 가능
- 재인용/중복 기사 구분 가능
- verifier가 `chapter_facts`를 다시 해석하는 게 아니라 `claim_id/source_id` 기준으로 검증 가능

### 4. editorial control 강화
- `editorial_brief` 기준으로 어떤 page/claim를 chapter_facts에 투영할지 결정 가능
- 즉, 리서치 품질과 기획 정렬을 동시에 잡을 수 있음

---

## 구현 원칙

### 1. 수집 우선순위
- 1순위: lane / RSS / 구조화 API
- 2순위: 공식 사이트 / 위키 / 정부 자료
- 3순위: WebSearch/WebFetch fallback

### 2. fallback 정책
기존처럼 무조건 WebSearch부터 하지 말고,
**feed/API에서 커버되지 않는 구멍(hole)만 LLM 검색으로 메우는 구조**가 필요합니다.

### 3. canonical layer 고정
`chapter_facts`는 계속 사용하더라도 canonical knowledge store는 반드시 아래 중 하나여야 합니다.
- `research_claims`
- `research_wiki`

### 4. incremental refresh
새 기사/새 소스가 들어와도 전체 재생성 대신
- raw source append
- affected claims/pages만 갱신
- 필요한 chapter만 projection 재생성
이 가능해야 합니다.

---

## 토큰/비용 최적화 관점
이 아키텍처 변경의 중요한 기대 효과 중 하나는 **LLM 토큰 사용량 절감**입니다.

현재 구조는 챕터마다 WebSearch/WebFetch를 반복하고, 비슷한 기사군을 여러 번 읽고, 각 챕터별로 다시 요약하는 패턴이라 **중복 검색 + 중복 읽기 + 중복 요약** 비용이 큽니다.

반면 제안 구조는 아래처럼 비용 구조가 달라집니다.

1. **수집 단계**
   - lane/RSS/API 수집은 LLM 토큰을 거의 사용하지 않음
   - raw source를 빠르게 확보 가능

2. **정규화 단계**
   - 같은 문서를 여러 챕터가 반복 소비하지 않고
   - unique source를 기준으로 **한 번만 claim/wiki로 정규화**

3. **projection 단계**
   - chapter_facts는 raw source를 다시 읽어 만드는 것이 아니라
   - 이미 정규화된 `research_claims` / `research_wiki`에서 필요한 내용만 조합

4. **draft / fact-check 단계**
   - 전체 chapter dump를 통째로 다시 읽는 대신
   - 실제 관련 page/claim/source만 retrieval 방식으로 주입 가능

### 기대 절감 효과
잘 설계되면 토큰 사용량은 다음과 같이 줄어들 가능성이 큽니다.

- **첫 풀런(Stage 1 기준)**: 약 30~60% 절감 가능
- **재실행/부분 수정**: 약 60~90% 절감 가능
- **Stage 2까지 포함한 전체 파이프라인**: 약 10~35% 추가 절감 가능

특히 아래 조건에서 효과가 큽니다.
- 같은 기사/같은 사건을 여러 챕터에서 반복 참조하는 프로젝트
- 뉴스형/시사형/단일 사건 집중형 주제
- 리런, 수정, 팩트체크 루프가 잦은 워크플로우

### 주의사항
레이어만 추가한다고 자동으로 절감되지는 않습니다. 아래 원칙이 지켜져야 진짜 최적화가 일어납니다.

#### 1. dedupe는 LLM 이전에 수행
- 포털 전재
- 거의 동일한 재송고 기사
- 중복 RSS 항목

을 LLM에 넣기 전에 제거해야 함

#### 2. source 정규화는 1회 처리 원칙
- source마다 `claim_ids`, `entity_ids`, `source_ids`를 한 번만 생성
- 리런 시 동일 문서를 다시 장문 요약하지 않음

#### 3. chapter_facts는 claim/wiki 기반 projection만 허용
- raw docs를 매번 다시 읽어 chapter_facts를 생성하면 절감 효과가 무너짐

#### 4. incremental refresh 필수
- 새 source만 append
- 영향 받은 claim/page만 갱신
- 영향 받은 chapter만 재생성

이 가능해야 재실행 비용이 크게 줄어듦

#### 5. draft / verifier도 retrieval 기반으로 전환
- draft-writer가 긴 리서치 덤프 전체를 읽지 않도록 하고
- 필요한 claim/page만 top-k retrieval로 주입해야 함

### 실무적 결론
이 구조는 **첫 실행 비용을 다소 낮추는 것**보다도,
**재실행·원고 수정·팩트체크 반복 시 비용을 크게 줄이는 데 가장 큰 의미**가 있습니다.

즉, lane/RSS/API 기반 수집 + wiki/claim canonical layer는 단순히 리서치 품질 개선안이 아니라,
**토큰 비용 구조 자체를 중복 소비형에서 재사용형으로 바꾸는 최적화안**으로 보는 것이 맞습니다.

---

## MVP 범위
처음부터 풀스택 지식그래프까지 갈 필요는 없습니다. MVP는 아래만 해도 의미가 큽니다.

1. lane/RSS/API로 raw source 수집
2. `source_index.jsonl` + `research_claims.jsonl` 생성
3. `chapter_facts`에 `claim_ids`, `source_ids` 추가
4. `flesh_research`를 “챕터별 WebSearch”가 아니라 “claim store 기반 projection”으로 전환

이 4개만 해도:
- 속도
- provenance
- fact-check
- draft 재사용성
- 토큰 효율
이 모두 개선됩니다.

---

## 한 줄 요약
현재 `chapter_facts 직접 생성` 방식은 writer-friendly하지만 canonical knowledge layer로 쓰기엔 약합니다.
리서치 아키텍처를 **`lane/RSS/API 기반 raw ingestion → LLM wiki/claim store → chapter_facts projection`** 구조로 바꾸면 속도, 추적성, 원고 작성 효율, 팩트체크 품질뿐 아니라 **토큰 비용 구조까지 더 재사용 친화적으로 최적화**할 수 있습니다.
