---
tags: [pattern, data-flow, topic]
date: 2026-03-24
occurrences: 1
related: [[errors/2026-03-24-vault-topic-fallback]]
---

# topic 값 소스 불일치 패턴

## 패턴
같은 "topic" 값을 가져오는데 코드 위치마다 **다른 소스**를 참조:
- DB `projects.topic` 컬럼
- `state.config["topic"]`
- `project_slug` (fallback)

## 위험
config에 topic이 없으면 slug로 fallback → 한글 검색 매칭 실패, 볼트 검색 실패 등.

## 방지 규칙
1. topic 참조는 항상 동일 패턴: `self.project.get("topic") or self.state.config.get("topic", self.project_slug)`
2. 새 코드에서 topic 사용 시 위 패턴 복사
3. 이상적으로는 `self._get_topic()` 유틸 메서드로 추출
