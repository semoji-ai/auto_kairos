---
name: fresh-research
description: 최신성·현재 이슈·기본 윤곽을 빠르고 얕게 확인. 뉴스성·트렌드·짧은 영상은 이것만으로 종결 가능, 깊은 영상에서는 deep-research의 사전 정찰 역할.
---

# fresh-research

## 목적

- 주제의 **현재 상태**(최근 사건, 최신 데이터, 화제) 확인
- 주제의 **윤곽** 빠르게 잡기(주요 인물·기관·날짜·키워드)
- 깊게 팔 가치가 있는 영역 후보 식별(deep-research가 들어갈 좌표)

깊이보다 폭과 최신성. 빠르게 끝낸다.

## Reads
- (선택) `pd_notebook.md`, `plan.md` — 톤·각도 참고만

## Writes
- `research_reports/{topic_slug}.md` (frontmatter `kind: fresh`)

## Input resolution
1. **Vault 우선 검색(권장 Step 0)**: 진행 전 PD가 `vault-search` 호출하여 재사용 후보 확인. 후보가 충분하면 외부 경로 normalize 모드로 가져와 새 리서치를 줄이거나 생략
2. **Brief 직접**(기본): 주제·범위만 있으면 바로 진행
3. **외부 자료 normalize**: brief에 외부(또는 vault) 자료 경로가 있으면 frontmatter만 붙여 표준 위치로 복사
4. **실패**: 주제 미결정 시 종료

## 산출물 포맷

```yaml
---
topic: <주제>
slug: <slug>
kind: fresh
created: <YYYY-MM-DD>
---
```

본문 권장 섹션:
- 최신 사건·맥락(최근 N개월 기준 명시)
- 주요 인물·기관·키워드
- 자주 쓰이는 수치·날짜
- 더 파볼 만한 영역(deep 후보)
- 출처

## 반환

Skill Contract 준수. summary 200~400단어, decisions에 (a) 신뢰도 낮은 부분, (b) deep 권장 영역, (c) 풀린 의문/남은 의문.

## 금지
- `pd_notebook.md`, `wiki/`, `drafts/` 수정

## 한국어 작성 규칙
- 가타카나/히라가나/한자 금지
