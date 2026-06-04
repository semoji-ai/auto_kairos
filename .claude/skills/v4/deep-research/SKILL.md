---
name: deep-research
description: 주제의 깊은 맥락·역사·구조·논쟁·핵심 근거를 수집. 역사·인물·기업·논쟁적 주제·다큐형 영상에 사용. Claude Code 내장 도구(WebSearch/WebFetch/Workflow)로 직접 수행.
---

# deep-research

## 목적

- 주제의 **역사적 흐름**과 **구조적 맥락** 파악
- **논쟁점**과 각 입장의 **근거** 수집
- 1차·2차 출처 인용 가능한 형태로 정리

가벼운 트렌드 영상에는 사용하지 않는다(fresh-research로 충분).

## Reads
- (권장) `research_reports/*.md` (kind: fresh) — 정찰 결과를 좌표로 사용
- (선택) `pd_notebook.md`, `plan.md`

## Writes
- `research_reports/{topic_slug}.md` (frontmatter `kind: deep`)

## Input resolution
1. **Vault 우선 검색(권장 Step 0)**: PD가 `vault-search`로 기존 deep 자료 확인. 재사용 가능하면 외부 경로 normalize 모드로 가져와 신규 리서치 범위를 줄임
2. **Auto + Brief**: fresh 보고서가 있으면 좌표로, brief는 깊게 팔 영역 명세
3. **Brief 직접**: fresh 없이도 주제·범위가 명확하면 진행
4. **외부 보고서 normalize**: vault 또는 외부 deep 보고서 경로를 받아 표준 위치로 복사
5. **실패**: 주제 미결정 시 종료

## 산출물 포맷

```yaml
---
topic: <주제>
slug: <slug>
kind: deep
created: <YYYY-MM-DD>
source: deep-research | imported
---
```

본문 권장 섹션:
- 역사·타임라인
- 구조·체계·관계
- 주요 논쟁과 입장별 근거
- 핵심 인물·기관·사건의 상세
- 1차·2차 출처

## 실행 방법 (내장 도구)

외부 실행기를 쓰지 않는다. Claude Code 내장 도구로 직접 수행:

1. **fan-out**: Workflow 도구로 주제 갈래(역사/구조/논쟁/인물 등)별 병렬 리서처를 띄운다.
   각 리서처는 WebSearch로 후보 출처를 찾고 WebFetch로 본문을 가져온다.
2. **adversarial verify**: 핵심 주장마다 회의적 검증 에이전트를 붙여 반론 시도.
   다수가 반박하면 주장 폐기.
3. **synthesize**: 검증 통과 주장만 인용과 함께 `research_reports/{slug}.md`로 합성.

Workflow 미사용 환경(경량 호출)에서는 메인 컨텍스트에서 WebSearch/WebFetch를
순차 사용하여 동일 산출물을 만든다.

## 반환

Skill Contract 준수. decisions에 신뢰도 낮은 영역, 추가 자료가 필요한 부분, 입장 간 상충점.

## 금지
- `pd_notebook.md`, `wiki/`, `drafts/` 수정
- 가벼운 트렌드 영상에 호출되는 것(PD 판단 책임)

## 한국어 작성 규칙
- 가타카나/히라가나/한자 금지
