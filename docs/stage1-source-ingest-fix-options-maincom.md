# Stage 1 `source_ingest` 수정안 정리 — 소규모 핫픽스 vs 근본 구조개선

## 목적

메인컴에서 바로 검토/적용할 수 있도록, 현재 Stage 1의 `0 claims completed` 문제에 대해 아래 두 가지 수정 경로를 정리합니다.

1. **소규모 핫픽스** — 현재 구조를 크게 유지하면서 잘못된 성공 판정을 막는 안
2. **근본 구조개선** — `step_1_ingest`를 deterministic Python collector로 재설계하는 안

권장 순서는 다음과 같습니다.

- **1차:** 소규모 핫픽스로 silent failure 차단
- **2차:** 근본 구조개선으로 agent tool-use 의존 제거

---

## 현재 확인된 증상

실제 재실행에서 아래 현상이 확인되었습니다.

- `step_1_ingest` → `OK`
- `step_1a (skeleton_from_vault)` → `OK`
- `step_1b (chapter_projection)` → `OK`
- 하지만 vault manifest는 아래 상태였습니다.
  - `claims.jsonl = 0`
  - `sources.jsonl = 0`
- `source_ingest_status.json.status = "completed"`
- ResearchAgent latest run 상태는 아래였습니다.
  - `stage = quality-assurance`
  - `status = blocked`
  - `notes = Packaging blocked. Next step: collect-subagent-packets. Specialist readiness: seed_only`

즉, **실제 리서치는 usable 상태가 아니었는데 파이프라인은 completed로 간주**했습니다.

---

## 확인된 root cause

### 1. `source_ingest`가 성공 조건을 검증하지 않음

현재 `auto_agent/modules/source_ingest_module.py`는 Claude CLI 호출 후 아래를 수행합니다.

- `research_launcher.py ingest-bundle`
- `research_launcher.py finalize-session`
- 이후 무조건 `return True`

즉 아래 항목을 확인하지 않습니다.

- packet target이 실제로 채워졌는지
- `claims.jsonl`, `sources.jsonl`이 실제로 생성되었는지
- `status-session` 기준 다음 단계가 `collect-subagent-packets`인지
- latest run이 `blocked`인지
- specialist readiness가 여전히 `seed_only`인지

### 2. ResearchAgent는 packet/subagent workflow를 기대하지만, `source_ingest`는 단일 에이전트 직접 수집 프롬프트를 사용함

현재 흐름은 서로 다른 두 방식을 섞고 있습니다.

#### A. ResearchAgent 쪽 기대 흐름

`prepare-session`은 아래 workflow를 전제로 session bundle을 생성합니다.

- assignment별 subagent dispatch
- 각 subagent가 JSON packet 반환
- packet target 저장
- `status-session`
- `ingest-bundle`
- cross-verifier
- `finalize-session`

#### B. `source_ingest` 쪽 실제 프롬프트

현재 Claude에게 아래를 한 번에 시킵니다.

- lane/rss/api 사용
- `register-source`
- `append-claim`
- wiki 작성
- `ingest-bundle`
- `finalize-session`

즉, **ResearchAgent는 packet workflow를 기대하는데, `source_ingest`는 단일 agent direct-write workflow처럼 사용**하고 있습니다.

### 3. lane/rss/api 수집이 deterministic code가 아니라 agent tool-use에 의존함

지금 lane 수집은 Python이 직접 돌리는 단계가 아니라, Claude가 Bash tool로 스스로 실행해야 하는 방식입니다.

즉 현재 구조는 다음과 같습니다.

- Python module이 collector를 직접 실행하는 구조가 아님
- Claude가 프롬프트를 읽고 lane 도구를 직접 호출해야 함
- Claude가 중간에 packet workflow / direct-write workflow 충돌로 완주 못하면 durable output이 0이 될 수 있음

### 4. downstream 단계가 claims 0 상태를 막지 못함

- `skeleton_from_vault`는 wiki만 있으면 통과 가능
- `chapter_projection`도 wiki만 있으면 진행 가능

그래서 `source_ingest`의 잘못된 성공 판정이 Stage 2까지 전파됩니다.

---

## 추가로 확인된 구현 문제

### 1. lane 도구 참조 중 일부가 현재 repo 기준 불명확/누락

`source_ingest_module.py` 프롬프트는 아래를 참조합니다.

- `tools/news_rss_lane.py`
- `tools/wikipedia_lane.py`
- `tools/crossref_lane.py`

확인된 실제 파일은 다음뿐입니다.

- `auto_agent/tools/news_rss_lane.py`

즉 아래 둘은 현재 repo 기준으로 정리 필요합니다.

- `wikipedia_lane.py`
- `crossref_lane.py`

이 문제는 소규모 핫픽스와 별개로, 근본 수정 시 반드시 해결해야 합니다.

---

# 수정안 A — 소규모 핫픽스

## 목표

현재 구조를 크게 바꾸지 않고, **빈 결과를 completed로 통과시키는 문제를 즉시 차단**합니다.

## 적용 범위

주 변경 파일:

- `auto_agent/modules/source_ingest_module.py`
- `auto_agent/modules/skeleton_from_vault_module.py`
- `auto_agent/modules/chapter_projection_module.py`
- `tests/test_source_ingest_module.py`

## 핵심 아이디어

현재 agent-heavy 구조는 당장 유지하되, 아래 조건을 만족하지 않으면 절대 성공 처리하지 않습니다.

### A-1. `source_ingest` postcondition 검증 추가

`ingest-bundle` / `finalize-session` 이후 아래를 검증합니다.

필수 검증 항목:

- `claims.jsonl` line count >= 3
- `sources.jsonl` line count >= 3
- `status-session.recommended_next_step != "collect-subagent-packets"`
- latest run `status != "blocked"`
- `specialist_readiness != "seed_only"`

실패 시:

- `source_ingest_status.json.status = "partial"` 또는 `"failed"`
- module exit code non-zero
- 로그에 검증 실패 이유 명시

### A-2. Claude subprocess 결과 로깅 강화

현재는 `RESEARCH_COMPLETE`가 없으면 stdout 마지막 500자만 출력합니다.

핫픽스에서는 아래를 추가합니다.

- Claude stdout 전체를 project 내 별도 debug log에 저장
- Claude stderr도 함께 저장
- packet target별 ready/empty 상태를 로그에 기록
- `status-session` 결과(JSON)도 로그에 저장

이렇게 해야 다음 실패 시 “도구를 안 썼는지 / 일부만 썼는지 / packet 저장을 못 했는지”를 바로 확인할 수 있습니다.

### A-3. `step_1a` 가드레일 강화

`skeleton_from_vault`에서 아래를 추가합니다.

- `claims < threshold`면 실패
- wiki-only 상태는 성공으로 간주하지 않음

권장 threshold:

- 최소 3 claims

### A-4. `step_1b` 가드레일 강화

`chapter_projection`에서 아래를 추가합니다.

- claims 0이면 projection 진행 금지
- Stage 1 품질 실패로 처리

즉, `source_ingest`의 실패가 downstream에서 조용히 덮이지 않게 합니다.

### A-5. 테스트 추가

권장 테스트:

1. `source_ingest`가 blocked run / empty manifests면 실패하는지
2. `skeleton_from_vault`가 claims 0이면 실패하는지
3. `chapter_projection`이 claims 0이면 중단하는지

## 장점

- 코드 변경 범위가 비교적 작음
- 즉시 silent failure 차단 가능
- 재현/디버깅이 쉬워짐
- 메인컴에서 빠르게 적용 가능

## 한계

- 여전히 `step_1_ingest`가 agent tool-use에 의존함
- lane/rss/api 수집 성공이 deterministic하지 않음
- packet workflow vs direct-write workflow 혼선은 남음
- 근본적으로는 brittle한 구조를 유지함

## 이 안이 적합한 경우

- 지금 당장 `0 claims completed`를 막아야 할 때
- Stage 1을 우선 안정화하고, 구조개선은 후속으로 나누고 싶을 때

---

# 수정안 B — 근본 구조개선

## 목표

`step_1_ingest`를 **agent-heavy research step이 아니라 deterministic Python collector**로 바꿉니다.

핵심 원칙:

> 수집은 코드가 하고, 에이전트는 해석/보강만 한다.

## 적용 범위

주 변경 파일 후보:

- `auto_agent/modules/source_ingest_module.py`
- `auto_agent/tools/news_rss_lane.py`
- 신규/대체 collector 구현
  - 예: `auto_agent/tools/wikipedia_lane.py`
  - 예: `auto_agent/tools/crossref_lane.py`
  - 또는 별도 aggregator/helper 모듈
- `auto_agent/modules/skeleton_from_vault_module.py`
- `auto_agent/modules/chapter_projection_module.py`
- 관련 테스트 파일

## 핵심 아이디어

`step_1_ingest`의 주 경로를 아래처럼 재구성합니다.

```text
Python deterministic collectors
→ normalize source records
→ append claims / sources into vault
→ build/update wiki pages
→ validate usable ingest
→ source_ingest_status = completed
```

즉, **collector 실행과 vault 기록을 Python이 직접 책임**집니다.

## 구체 구조

### B-1. lane/rss/api 수집을 Python이 직접 실행

`source_ingest_module.py` 내부에서 아래를 직접 호출합니다.

- 뉴스: `news_rss_lane`
- 위키: Wikipedia collector
- 학술: CrossRef collector
- 필요 시 기타 공식/기관 데이터 수집기

이 단계는 더 이상 Claude의 Bash tool-use에 맡기지 않습니다.

### B-2. 수집 결과를 Python에서 정규화

Python이 수집 결과를 아래 공통 구조로 변환합니다.

- source title/url/kind/quality/summary
- claim text/evidence/source linkage
- timeline/entity candidates

즉, collector 출력 → vault write 사이에 deterministic normalization layer를 둡니다.

### B-3. vault 쓰기도 Python orchestration으로 고정

아래 작업을 Python에서 직접 수행합니다.

- `register-source`
- `append-claim`
- wiki page refresh/update

ResearchAgent helper script는 저장 포맷/도우미로만 사용하고, research orchestration 자체는 Python이 담당합니다.

### B-4. `step_1_ingest`의 성공 조건을 명시적으로 정의

예시 성공 조건:

- usable sources >= N
- usable claims >= N
- overview/timeline/entities wiki 작성 완료
- ingest validation pass

즉, Stage 1 ingest는 “Claude가 끝났다고 말했다”가 아니라 “구조화된 결과가 임계치 이상 존재한다”로 판정합니다.

### B-5. 에이전트 역할 재정의

근본 수정안에서는 Claude를 아래 중 하나로 제한합니다.

#### 옵션 1. Stage 1 ingest에서 Claude 제거

- ingest는 전부 Python
- Claude는 Stage 1 이후 outline 보강 또는 특수 fallback만 담당

#### 옵션 2. Claude를 fallback/manual escalation로만 사용

- 기본은 Python deterministic ingest
- collector coverage가 부족하거나 특수 주제일 때만 별도 research fallback 실행

권장 방향은 **옵션 2**입니다.

### B-6. `step_1a`, `step_1b`는 vault-derived 단계로 고정

최종 Stage 1 구조:

```text
step_1_ingest
  = deterministic Python collection
  = canonical vault wiki / claims 생성

step_1a
  = vault 기반 skeleton / outline 생성
  = 외부 검색 없음

step_1b
  = vault + outline 기반 chapter projection
```

## 장점

- lane/rss/api 수집이 deterministic해짐
- silent failure 구조 자체 제거
- 재현성 향상
- Stage 1 속도/비용 예측 가능성 증가
- 장애 분석이 쉬워짐
- packet/subagent workflow와 direct-write workflow 혼선 제거

## 단점

- 변경 범위가 큼
- collector 계층 설계/테스트가 필요함
- 현재 agent-based research 철학과 일부 결별함
- 초기 구현 비용이 핫픽스보다 높음

## 이 안이 적합한 경우

- Stage 1을 장기적으로 안정적인 production path로 가져가려는 경우
- `collect once, derive many` 원칙을 실제 코드 구조에 반영하려는 경우
- 수집 단계를 더 이상 agent tool-use에 의존하고 싶지 않은 경우

---

# 두 안의 비교

| 항목 | 수정안 A — 소규모 핫픽스 | 수정안 B — 근본 구조개선 |
|---|---|---|
| 목적 | 잘못된 성공 판정 차단 | 구조적 불안정성 제거 |
| 변경 범위 | 작음 | 큼 |
| 적용 속도 | 빠름 | 느림 |
| 현재 구조 유지 | 대부분 유지 | Stage 1 ingest 책임 재배치 |
| agent 의존성 | 유지 | 크게 감소 |
| silent failure 방지 | 가능 | 근본적으로 해결 |
| 재현성 | 일부 개선 | 크게 개선 |
| 장기 유지보수성 | 보통 | 높음 |

---

# 권장 실행 순서

## 추천안

### 1단계 — 지금 바로
**수정안 A 적용**

이유:
- 더 이상 `0 claims completed`가 통과하면 안 됨
- blocked / seed_only / empty manifest를 즉시 실패로 바꿔야 함
- 다음 디버깅에 필요한 로그를 남겨야 함

### 2단계 — 후속 작업
**수정안 B 설계 및 전환**

이유:
- 현재 문제는 단순 validation 누락이 아니라 구조적 책임 배치 문제임
- 수집 단계를 agent tool-use에 맡기는 한 비슷한 문제가 반복될 가능성이 큼

---

# 메인컴 전달용 한 줄 요약

현재 Stage 1 `source_ingest`는 **packet/subagent workflow와 단일 agent direct-write workflow가 섞인 상태**이며, 이 때문에 fresh research가 실제로 완료되지 않아도 `completed`로 통과할 수 있습니다.

- **소규모 핫픽스:** empty claims / blocked run / seed_only 상태를 즉시 실패로 바꾸고, downstream 가드레일과 로깅을 강화
- **근본 구조개선:** `step_1_ingest`를 Claude 자율 tool-use 기반이 아니라 deterministic Python collector로 전환

권장 순서는 **핫픽스 먼저, 구조개선 후속**입니다.
