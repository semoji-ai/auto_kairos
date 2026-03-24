---
date: 2026-03-18
type: error-fix
status: fixed
tags: [pipeline, research, timeout]
---

# step_1 리서치 타임아웃 (1200s)

## 증상
- 1분 영상 프로젝트에서 research-orchestrator가 1200초(20분) 타임아웃
- 5개 Explorer 에이전트가 모두 완료했으나 통합 작업 중 시간 초과
- STEP FAILED 후에도 파이프라인이 다음 phase로 계속 진행됨

## 원인
- `agents.json`의 research-orchestrator max_turns=70이 분량과 무관하게 고정
- 1분 영상에 5개 Explorer + 70턴은 과도
- CLI 서브프로세스 timeout이 1200초로 짧음 (70턴 소화하기엔 부족)

## 해결
- `runner.py`에 `duration_minutes` 기반 리서치 규모 차등 로직 추가:
  - 1분: max_turns=20, timeout=600s (10분)
  - 3분: max_turns=35, timeout=900s (15분)
  - 5분: max_turns=50, timeout=1200s (20분)
  - 10분+: agents.json 기본값, timeout=1500s (25분)
- step 실패 시 파이프라인 중단 로직 수정 (run() for-loop에서 break)

## 2차 수정 (300s에서도 타임아웃)
- 1분 영상도 리서치에 최소 10분 필요 → timeout 600s로 상향
- 파이프라인 중단 버그: _run_sequential의 return이 run()의 for-loop를 안 멈춤 → failed_steps 체크 + break 추가

## 3차 수정 (Explorer 완료 후 JSON 변환에서 계속 타임아웃)
- 근본 원인: CLI 세션 안에서 탐색+변환을 하나로 묶어서 변환 시간 부족
- 해결: step_1 실패 시 Explorer 산출물(sources.jsonl, summary.md)이 있으면 Python으로 병합 후 성공 처리
- 타임아웃 상향: 1분=1800s, 3분=2400s, 5분=3000s

## 방지 규칙
- 새 프로젝트 분량 추가 시 리서치 스케일링 매핑 확인 필수
- 리서치 timeout은 넉넉하게 (1분 영상도 최소 30분)
- CLI 타임아웃 시 Explorer 산출물 존재하면 Python fallback 병합
