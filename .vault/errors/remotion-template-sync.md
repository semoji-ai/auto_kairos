---
tags: [error, remotion, sync, 반복발생]
date: 2026-03-16
severity: major
pipeline-step: remotion-render
agent: visual-composer
status: resolved
recurrence: 3
---

# remotion/src 수정이 remotion_template에 반영 안 됨

## 증상
remotion/src/에서 버그를 수정했는데 실제 프로젝트에서 여전히 구버전이 실행됨.
- 헤드라인 숫자뱃지: remotion/src에서 `showBadge = false` 했지만 remotion_template에는 `emphasis === "sequence"` 그대로
- 인용구 줄바꿈: remotion/src에서 `whiteSpace: "pre-line"` 추가했지만 remotion_template에는 미반영

## 원인
**두 벌의 소스 코드** 존재:
- `remotion/src/` — 개발/Studio용 (직접 수정하는 곳)
- `auto_agent/remotion_template/src/` — 패키지 배포용 (프로젝트에 실제 복사되는 곳)

수정 후 sync를 잊으면 패키지에 구버전이 포함됨.

## 해결
양쪽 모두 수정. 향후 sync 프로세스 필요.

## 수정 파일
- `remotion/src/simple/CreativeScene.tsx` — showBadge=false, whiteSpace:pre-line
- `auto_agent/remotion_template/src/simple/CreativeScene.tsx` — 동일 수정

## 재발 방지
- [x] CLAUDE.md에 "remotion 수정 시 remotion_template도 반드시 동기화" 규칙 추가
- [ ] sync.py에 자동 동기화 스크립트 강화
- [ ] pre-commit hook으로 diff 체크

## 관련 패턴
- [[패키지-데이터-누락]]
