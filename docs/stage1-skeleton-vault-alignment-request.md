# Stage 1 정렬 수정 요청 — `step_1a`를 vault 기반 skeleton 생성 단계로 변경

## 배경

현재 Stage 1은 새 research architecture 방향과 일부 정렬되었지만, 중간 단계인 `step_1a`가 아직 과거 웹 리서치 방식에 머물러 있어 **중복 수집**이 발생합니다.

의도한 구조는 아래와 같습니다.

```text
lane/rss/api 수집
→ vault wiki / claims 저장
→ skeleton / outline 생성
→ chapter_facts projection
```

하지만 실제 구현은 아래에 가깝습니다.

```text
step_1_ingest: lane/rss/api + ResearchAgent 기반 수집
→ vault wiki / claims 저장
→ step_1a: WebSearch / WebFetch로 다시 skeleton 리서치
→ step_1b: vault + outline 기반 projection
```

즉, Stage 1 안에서 **수집을 한 번 더 하고 있는 상태**입니다.

---

## 현재 확인된 문제

### 1. `step_1_ingest`는 이미 외부 수집 단계 역할을 수행함

`source_ingest_module.py`는 lane/rss/api 우선 수집을 프롬프트에 명시하고 있습니다.

- lane 도구 우선 사용
- 부족한 부분만 WebSearch/WebFetch fallback
- 결과를 vault wiki/claims에 저장

이 단계는 이미 canonical research store를 만드는 역할을 수행하고 있습니다.

### 2. `step_1a`가 ingest 결과를 직접 소비하지 않음

현재 `pipeline.json`에서 `step_1a`는 다음처럼 정의되어 있습니다.

- step id: `step_1a`
- name: `skeleton_research`
- agent: `skeleton-researcher`
- input: `project_config`
- output: `skeleton.json`, `outline.json`

즉, `source_ingest_status.json`, vault wiki, claims manifest 등을 직접 입력으로 받지 않습니다.

### 3. `step_1a`는 여전히 웹 탐색 기반임

`skeleton-researcher` 정의와 SKILL은 다음 행동을 요구합니다.

- Wikipedia 검색
- 권위 소스 2~3개 추가 탐색
- WebSearch / WebFetch 사용
- 그 결과로 skeleton / outline 작성

이 구조는 ingest 이전 시대의 skeleton 수집 로직에 가깝고, 현재 설계 철학인 **collect once, derive many**와 어긋납니다.

---

## 실제로 발생하는 문제

### 1. 속도 저하

`step_1_ingest`에서 이미 자료를 모았는데 `step_1a`가 다시 외부 검색을 수행하므로, Stage 1 전체 시간이 불필요하게 늘어납니다.

### 2. 토큰 낭비

이미 vault에 저장된 내용을 재사용하지 않고 다시 검색/읽기/요약하므로 토큰 사용량이 증가합니다.

### 3. 재현성 저하

동일 주제를 다시 실행해도 `step_1a`가 외부 검색에 의존하면 skeleton 결과가 매번 조금씩 달라질 수 있습니다.

### 4. canonical store 개념 약화

vault wiki/claims를 source of truth로 삼아야 하는데, 중간 단계가 다시 웹을 보면 사실상 source of truth가 분산됩니다.

---

## 수정 요청

### 요청 1. `step_1_ingest`를 Stage 1의 유일한 외부 수집 단계로 고정

Stage 1에서 외부 웹/뉴스/API 수집은 `step_1_ingest`에서만 일어나야 합니다.

원칙:
- 외부 탐색은 ingest에서 1회 수행
- 이후 단계는 ingest 산출물을 기반으로 파생물 생성

---

### 요청 2. `step_1a`를 vault 기반 skeleton 생성 단계로 변경

`step_1a`의 책임을 다음처럼 재정의해 주세요.

현재:
- Wikipedia + 권위 소스를 다시 찾아 skeleton 형성

변경 후:
- vault wiki / claims를 읽고
- timeline / key_figures / key_episodes를 정리하고
- `skeleton.json`, `outline.json`을 생성

즉 `step_1a`는 **수집 단계가 아니라 구조화 단계**여야 합니다.

---

### 요청 3. `step_1a` 입력 계약 수정

현재 `step_1a` 입력은 `project_config`뿐입니다.

아래 입력을 직접 받도록 바꿔 주세요.

- `source_ingest_status.json`
- vault wiki 경로
- vault claims 경로
- 필요 시 entity_slug / section_slug / topic_slug 정보

예상 소비 대상:
- `wiki/<slug>/overview.md`
- `wiki/<slug>/timeline.md`
- `wiki/<slug>/entities.md`
- `manifests/<slug>/claims.jsonl`

---

### 요청 4. `step_1a`를 Python module로 전환하는 안 우선 검토

가장 권장하는 방향은 `step_1a`를 LLM agent가 아니라 Python module로 바꾸는 것입니다.

예시 이름:
- `skeleton_from_vault`
- `outline_from_claims`

이 모듈은 아래를 수행하면 됩니다.

- vault wiki 문서 파싱
- claims 집계
- timeline / key figures / key episodes 초안 도출
- 영상 분량에 맞춘 outline / research_focus 생성

장점:
- 속도 향상
- 토큰 절감
- 재현성 향상
- 장애 분석 단순화

---

### 요청 5. LLM 유지 시에도 외부 검색 도구 제거

만약 `step_1a`를 LLM으로 유지해야 한다면, 최소한 아래 제약을 걸어 주세요.

- allowed tools: `Read`, `Write`, `Glob`
- 제거: `WebSearch`, `WebFetch`

즉 웹 탐색 에이전트가 아니라 **vault reader / structurer**로 바꿔야 합니다.

---

### 요청 6. `skeleton-researcher` SKILL 문서 수정

현재 SKILL은 명시적으로 다음을 요구합니다.

- Wikipedia 탐색
- WebSearch
- WebFetch
- 권위 소스 추가 탐색

이 문서를 아래 기준으로 바꿔 주세요.

- 입력은 ingest 결과물(vault wiki/claims)
- 외부 검색 금지
- skeleton / outline / research_focus 생성에만 집중
- timeline / entity / claim provenance를 가능한 한 그대로 보존

---

### 요청 7. `step_1a` 진행 로그 세분화

현재는 진행 상태가 거칠어서 멈춤과 작업 중을 구분하기 어렵습니다.

예시 progress 메시지:
- ingest 결과 로드 중
- wiki overview 파싱 중
- claims manifest 읽는 중
- timeline 정리 중
- key figures 추출 중
- outline 생성 중
- research_focus 생성 중
- skeleton 저장 완료

이렇게 하면 dashboard/CLI에서 병목 지점을 바로 파악할 수 있습니다.

---

### 요청 8. Stage 1 가드레일 추가

아래 조건을 강제해 주세요.

- `source_ingest_status.json.status != completed`이면 `step_1a` 실패
- vault wiki/claims가 비어 있으면 명시적 fallback 또는 실패
- `step_1a`에서는 외부 네트워크 도구 사용 금지

---

## 목표 구조

최종적으로 Stage 1은 아래처럼 정렬되어야 합니다.

```text
step_1_ingest
  = lane/rss/api 우선 수집
  = canonical research store(vault wiki / claims) 생성

step_1a
  = vault 기반 skeleton / outline 생성
  = 외부 검색 없음

step_1b
  = vault + outline 기반 chapter_facts projection
```

이 구조가 되어야 Stage 1이 진짜로

**collect once, derive many**

형태를 갖추게 됩니다.

---

## 기대 효과

- Stage 1 속도 단축
- 중복 검색 제거
- 토큰 사용량 절감
- skeleton/outline 재현성 향상
- canonical store 일관성 강화
- 장애 분석 및 모니터링 단순화

---

## 한 줄 요약

`step_1_ingest`가 이미 수집을 끝냈다면, `step_1a`는 더 이상 웹을 뒤지지 말고 **vault wiki/claims에서 skeleton과 outline을 파생 생성하는 단계**로 바뀌어야 합니다.
