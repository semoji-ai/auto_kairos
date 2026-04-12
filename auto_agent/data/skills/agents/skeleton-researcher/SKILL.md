# Skeleton Researcher

## 역할

`step_1_ingest`가 이미 만든 canonical research store를 읽어 `skeleton.json`, `outline.json`을 구조화합니다.

핵심 원칙:
- 외부 검색 금지
- 입력은 vault wiki / claims만 사용
- collect once, derive many

기본 파이프라인에서는 Python module `skeleton_from_vault`가 우선입니다. 이 스킬은 수동 fallback 또는 구조 확인용입니다.

---

## 입력

- `source_ingest_status.json`
- `editorial_brief.json`
- `project_config.json`
- vault:
  - `wiki/<slug>/overview.md`
  - `wiki/<slug>/timeline.md`
  - `wiki/<slug>/entities.md`
  - `manifests/<slug>/claims.jsonl`
  - `manifests/<slug>/sources.jsonl`

---

## 허용 도구

- `Read`
- `Write`
- `Glob`

금지:
- `WebSearch`
- `WebFetch`

---

## 작업 순서

### Step 1. ingest 결과 확인

- `source_ingest_status.json.status`가 `completed` 또는 `skipped_existing`인지 확인
- 아니면 실패로 종료

### Step 2. vault 페이지 파싱

우선순위:
1. `overview.md`
2. `timeline.md`
3. `entities.md`
4. `claims.jsonl`

해야 할 일:
- Summary bullets 추출
- timeline event 정리
- key figures 정리
- key episodes 후보 정리
- source provenance 유지

### Step 3. skeleton.json 작성

최소 포함:
- `topic`
- `topic_slug`
- `entity_slug`
- `section_slug`
- `timeline`
- `key_figures`
- `key_episodes`
- `sources`

### Step 4. outline.json 작성

해야 할 일:
- 영상 분량에 맞춰 챕터 수 결정
- timeline/key_episodes를 챕터 단위로 묶기
- `chapters[].key_points`
- `chapters[].purpose`
- `chapters[].research_focus`
- `flow_notes`
생성

주의:
- 새로운 사실을 만들지 말 것
- 이미 ingest에서 확인되지 않은 에피소드를 추가하지 말 것
- scene_specs 수준으로 과도하게 내려가지 말 것

---

## 진행 로그

가능하면 아래 단위로 진행을 남깁니다.

- ingest 결과 로드 중
- wiki overview 파싱 중
- claims manifest 읽는 중
- timeline 정리 중
- key figures 추출 중
- outline 생성 중
- skeleton 저장 완료

---

## 출력 파일

- `skeleton.json`
- `outline.json`
