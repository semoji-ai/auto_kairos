---
name: fact-check
description: 원고의 사실관계(수치·날짜·고유명사·인과 단정)를 자료와 매칭해 검증하고 오류·약점을 보고. 수정은 하지 않음.
---

# fact-check

원고에 들어간 모든 검증 가능한 주장(수치·날짜·고유명사·인과)을 자료와 1:1 매칭해 검증한다. **읽기 전용 검토자**. 수정은 PD가 직접.

## Reads
- `drafts/v{n}.md` (기본: 최신, brief에서 명시 가능)
- `research_reports/*.md`, `research_targeted/*.md`, `wiki/*.md` (있는 모든 자료)
- (선택) `plan.md` — 다루지 않을 영역 등 정책 참고

## Writes
- (선택) `review/factcheck-v{n}-{date}.md` — 검토 노트. 메인은 summary/decisions로 충분

## Input resolution
1. **Auto**: `latest_draft` + 모든 자료 자동 발견
2. **명시 버전**: brief에 버전·경로 지정 시 그것을 사용
3. **부분 검증**: brief에 특정 단락·섹션만 지정 가능
4. **실패**: 자료가 전무하면 검증 불가 — decisions에 명시 후 종료

## 실행 절차

1. 원고를 단위(문장)별로 분해
2. 각 문장에서 **검증 가능한 주장** 식별: 수치, 날짜, 고유명사(인물·기관·작품), 인과 단정("때문에", "결과적으로"), 비교·최상급("최초", "최대")
3. 각 주장을 자료와 매칭. 매칭 결과를 4단계로 분류:
   - `verified` — 자료에 1:1 매칭, 일치
   - `verified_softened` — 자료의 [검증필요]였지만 표현 완화로 안전 처리됨(통과)
   - `mismatch` — 자료와 불일치(오류 후보)
   - `unsupported` — 자료에 근거 없음(추가 검증 필요)
4. summary에 통과율과 발견된 문제 건수
5. decisions에 개별 항목별 위치(단락 번호 또는 인용)와 처리 권장(수정/완화/삭제/추가 검증)

## 금지
- 원고 수정. 검토자는 읽기 전용
- `pd_notebook.md`, `final_manuscript.md` 수정
- 자료에 없는 새 사실 추측

## 한국어 작성 규칙
- 가타카나/히라가나/한자 금지
