---
tags: [error, vault-rag, topic]
date: 2026-03-24
severity: degraded
pipeline-step: step_1
status: resolved
recurrence: 1
related: [[patterns/topic-해석-불일치]]
---

# VaultRAG 리서치 검색에서 topic fallback 불일치

## 증상
볼트에 `배의_역사_1min.md`가 존재하는데 "리서치용 볼트 지식 없음" 출력.
v1 리서치 결과가 있는데도 v2에서 재활용 안 됨.

## 원인
`runner.py:2797`에서 topic을 가져올 때:
```python
topic = self.state.config.get("topic", self.project_slug)
```
DB `topic` 컬럼("배의 역사")을 안 보고, config dict에만 의존.
config에 topic이 없으면 slug("배의_역사_1min_v2")로 fallback → 검색 매칭 실패.

같은 파일 661번 줄은 올바른 패턴:
```python
topic = self.project.get("topic") or self.state.config.get("topic", self.project_slug)
```

## 해결
2797번 줄도 661번 줄과 동일한 `self.project.get("topic")` 우선 참조로 통일.
리서치 결과 저장(2690번)도 동일 패턴으로 수정.

## 재발 방지
- [x] topic 참조 패턴 3곳 모두 통일
- [ ] topic 가져오는 유틸 메서드로 추출 검토
