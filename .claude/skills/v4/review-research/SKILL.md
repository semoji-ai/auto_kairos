---
name: review-research
description: 리서치 자료가 기획 의도 대비 충분한지 점검하고 빈 영역·약점을 보고. **조건부**: Deep 경로에서 자료 토픽이 3개 이상일 때 권장. Light 경로 또는 자료 1~2개일 때는 PD 직접 검토가 더 효율적이라 호출하지 않는다.
---

# review-research

## 호출 기준
- ✅ Deep 경로 + research_reports/wiki 토픽 ≥ 3개 — 시스템적 커버리지 점검 가치
- ❌ Light 경로 — fresh report 한두 건은 PD가 직접 읽고 빈 곳 식별이 더 빠름
- ❌ 자료가 너무 적거나 너무 많은 모든 케이스 — 적으면 PD 직접, 많으면 토픽별 분할 검토 권장

## Reads
- `research_reports/*.md`, `research_targeted/*.md`, `wiki/*.md` (가용한 것 모두)
- (권장) brief 또는 `plan.md` — 기획 의도 비교 기준

## Writes
- (선택) `review/research-{date}.md` — 검토 노트. 부수 출력일 뿐, 메인은 summary/decisions로 충분

## Input resolution
1. **Auto**: 표준 위치에서 발견되는 자료를 검토
2. **부분 검토**: brief에 특정 파일/슬러그만 명시되면 그 범위만
3. **실패**: 자료가 전무하면 종료, decisions에 명시

## 실행 절차
1. `discover.snapshot` 으로 검토 대상 확정
2. 기획 의도와 매칭하여 (a) 다뤄진 영역, (b) 빈 영역, (c) 신뢰도 낮은 부분, (d) 상충/중복을 정리
3. summary와 decisions(추가 리서치 권장 항목)을 반환

## 금지
- 어떤 입력 아티팩트도 수정하지 않음(읽기 전용 검토자)
- `pd_notebook.md` 수정

## 한국어 작성 규칙
- 가타카나/히라가나/한자 금지
