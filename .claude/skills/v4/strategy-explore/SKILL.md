---
name: strategy-explore
description: 주제를 받아 채널 컨텍스트를 반영한 각도·훅·구조 옵션을 발산해 옵션 카드 모음 아티팩트를 생성. 리서치 전 단계.
---

# strategy-explore

전략·기획 단계의 발산 작업. 사용자/PD가 정한 주제와 채널을 입력받아 **각도(angle), 훅(hook), 구조 가설(structure)** 옵션을 다수 생성한다. 선택·확정은 PD와 사용자가 직접 한다.

## Reads
- `plan.md` 초안(있으면) — 톤·타겟·범위 참고
- `pd_notebook.md`(있으면)
- (선택) `vault-search` 결과 — 채널 패턴, 기존 콘텐츠 인덱스

## Writes
- `strategy/options-{YYYYMMDD-HHMMSS}.md` — 옵션 카드 모음

## Input resolution
1. **Brief 필수**: 주제, 채널(또는 채널 컨텍스트), 분량 목표 정도
2. **Vault 우선 검색(권장 Step 0)**: 채널 패턴(`01-patterns`)과 채널 데이터(`channels/...`, `03-analysis/channels/`)에서 톤·구조 단서 수집
3. **외부 자료 normalize**: brief에 참고 영상·기획서 경로가 있으면 normalize
4. **실패**: 주제가 없거나 너무 추상적이면 종료, decisions에 명시

## 산출물 포맷

```markdown
---
project_id: <id>
created: <YYYY-MM-DDTHH:MM>
topic: <주제>
channel: <채널>
---

# Strategy Options

## Angles
### A1. <각도 한 줄>
- 핵심 시선: ...
- 어울리는 훅 후보: H1, H3
- 어울리는 구조 후보: S2
- 강점 / 약점

### A2. ...

## Hooks
### H1. <훅 한 줄>
- 도입 시나리오: ...
- 매칭 각도: A1, A2
- 강점 / 약점

## Structures
### S1. <구조 한 줄>
- 챕터 가설: ...
- 매칭 각도/훅: ...
- 강점 / 약점

## 추천 조합
- Top 1: A? + H? + S? — 이유
- Top 2: ... — 이유

## 회피 권장
- 이유와 함께
```

기본 발산량: 각도 3~5개, 훅 3~5개, 구조 2~4개. 상호 매칭과 추천 조합 2~3개 명시.

## 실행 절차

1. brief에서 주제·채널·분량 확인
2. 가능하면 vault-search로 채널 패턴/유사 콘텐츠 검색(채널명 + 주제 키워드)
3. 옵션 발산. 각 옵션은 짧은 카드 형태(강점·약점 포함)
4. 추천 조합 2~3개 제시(매칭 근거 포함)
5. `strategy/options-{stamp}.md` 저장
6. 200~400단어 summary와 decisions(추천 노선과 그 사유, PD가 사용자와 합의해 선택해야 함을 명시)

## 금지

- `plan.md` 직접 수정 금지(PD가 합의 후 갱신)
- `pd_notebook.md` 수정 금지

## 한국어 작성 규칙
- 가타카나/히라가나/한자 금지
- 외래어는 한글 표기 또는 영어
