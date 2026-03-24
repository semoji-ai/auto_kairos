---
tags: [vault, index]
---

# Auto-Kairos 개발 볼트

프로젝트 내부 Obsidian 볼트. 반복되는 오류, 아키텍처 결정, 패턴을 기록하여 점층적으로 개선한다.

## 구조

- **errors/** — 발생한 오류와 해결 기록. 재발 시 recurrence 카운트 증가
- **decisions/** — 아키텍처/설계 결정과 그 이유 (ADR)
- **patterns/** — 반복되는 문제 패턴과 방지 규칙
- **improvements/** — 개선 계획과 진행 상태

## 위키링크 규칙

- 관련 이슈끼리 `[[파일명]]`으로 연결
- 에러 → 패턴: 같은 유형 에러 3회 이상 → [[patterns/]] 에 규칙 생성
- 에러 → 결정: 에러 해결이 설계 변경을 수반하면 [[decisions/]] 에 기록
- 패턴 → CLAUDE.md: 검증된 패턴은 CLAUDE.md 규칙에 승격

## 에러 노트 템플릿

```yaml
---
tags: [error, 영역태그]
date: YYYY-MM-DD
severity: blocking | degraded | cosmetic
pipeline-step: step_N
status: resolved | open | wontfix
recurrence: N
related: [[다른노트]]
---
```
