---
tags: [error, dashboard, uvicorn]
date: 2026-03-24
severity: blocking
pipeline-step: none
status: resolved
recurrence: 2
related: [[patterns/대시보드-안정성]]
---

# 대시보드 --reload 모드에서 파이프라인 중 먹통

## 증상
파이프라인 실행 중 대시보드가 응답 없음. curl timeout (5초).
프로세스는 살아있으나 요청 처리 불가.

## 원인
`uvicorn --reload` (StatReload)가 프로젝트 디렉토리 **전체**를 감시.
파이프라인이 output/ 폴더에 이미지, JSON, 오디오 파일을 계속 생성
→ StatReload가 매번 코드 변경으로 오인 → 서버 재시작 반복 → 먹통.

## 해결
`--reload` 플래그 제거. 에셋 변경은 SSE/폴링으로 별도 처리됨.

## 재발 방지
- [x] 대시보드 시작 시 --reload 사용 금지
- [ ] CLI `auto-agent dashboard` 명령에서 --reload 기본값 제거
- [ ] 대시보드 시작 스크립트 표준화
