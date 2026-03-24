---
tags: [improvement, creative-direction, remotion]
date: 2026-03-24
priority: low
status: decided
---

# concept 필드 역할 명확화

## 현재
concept이 "렌더러가 읽는 필드"로 오해되지만, 실제로는:
- CreativeScene.tsx에서 spotlight/강조/마지막 3개 키워드만 체크
- source_images.py에서 인물명 추출 텍스트로 사용
- 그 외 활용 없음

## 결정 (A안 채택)
concept을 **LLM 전용 사고 도구**로 명확히 정의.
- 렌더러가 concept을 직접 해석하는 것은 구조적으로 불가능 (React는 확정적 props 필요)
- concept → reveal/emphasis/mood/layout 선택의 근거로만 사용
- 렌더러에서 concept 참조 코드(spotlight 키워드 매칭) 제거 검토
