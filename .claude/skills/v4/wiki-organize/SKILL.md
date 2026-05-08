---
name: wiki-organize
description: 리서치 보고서를 원고용 지식베이스로 재구성. 단순 요약이 아니라 claim / timeline / entity / open question 중심 구조화. 깊은 경로(다큐형) 전용.
---

# wiki-organize

가벼운 영상 경로(fresh + target)에서는 호출하지 않는다. deep-research 결과를 원고가 곧바로 끌어다 쓸 수 있는 형태로 재구성하는 스킬.

## Reads
- `research_reports/*.md` (자동, kind 무관)
- `research_targeted/*.md` (자동, 있으면 함께 반영)
- (선택) `wiki/*.md`, `wiki/index.md` — 기존 wiki에 병합

## Writes
- `wiki/{topic_slug}.md` (다수)
- `wiki/index.md`

## Input resolution
1. **Auto**: 표준 위치 자동 발견
2. **외부 경로 normalize**: brief에 외부 보고서 경로가 있으면 `research_reports/`로 복사 후 진행
3. **부분 갱신**: brief에 특정 슬러그만 명시되면 해당 토픽만 재정리
4. **실패**: 입력 자료 전무 시 종료

## 산출물 포맷

각 `wiki/{slug}.md`는 다음 4개 섹션을 가진다.

```markdown
---
topic: <주제>
slug: <slug>
sources:
  - research_reports/<file>.md
  - research_targeted/<file>.md
updated: <YYYY-MM-DD>
---

## Claims
- [C1] <주장 한 줄> — 근거: <보고서:문단 또는 출처>
- [C2] ...

## Timeline
- YYYY-MM-DD — <사건>
- YYYY — <시기 단위 사건>

## Entities
- **<인물·기관·개념>**: <한 줄 설명>, 관련 claim: C1, C3

## Open Questions
- [Q1] <아직 답이 안 나온 질문 — target-research 입력 후보>
```

식별자(C1, Q1)는 토픽 파일 내부에서만 유일. open_question은 그대로 `target-research` brief로 가져갈 수 있게 자체 완결로 작성.

## index.md

`wiki_index.upsert(slug, 한 줄 요약)` 사용. 한 줄 요약은 토픽의 주제와 다루는 범위를 압축.

## 반환

Skill Contract 준수. decisions에 (a) 보고서 간 상충, (b) 비어 있어 보이는 영역, (c) target-research 권장 open question 리스트.

## 금지
- 원본 보고서 변경
- `pd_notebook.md`, `drafts/` 수정

## 한국어 작성 규칙
- 가타카나/히라가나/한자 금지
