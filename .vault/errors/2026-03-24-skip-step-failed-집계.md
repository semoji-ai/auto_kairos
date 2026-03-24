---
tags: [error, runner, pipeline]
date: 2026-03-24
severity: blocking
pipeline-step: step_8b_legacy
status: resolved
recurrence: 1
related: [[patterns/병렬실행-상태관리]]
---

# skip=true 스텝이 failed로 집계되어 파이프라인 중단

## 증상
`step_8b_legacy`가 `skip: true`로 설정되어 있는데, 파이프라인이 "실패"로 집계하고 중단됨.
```
[SKIP] step_8b_legacy: skip=true
*** 파이프라인 중단: ['step_8b_legacy'] 실패 ***
```

## 원인
`runner.py` 병렬 실행 경로(ThreadPoolExecutor)에서 `_execute_step` 반환값 분기:
```python
if result.status == "completed":
    # OK
elif step.get("blocking") is not False:
    self.state.failed_steps.append(step["id"])  # ← skipped도 여기로!
```
`status="skipped"`가 completed도 아니고 blocking 예외도 아니라서 failed로 빠짐.

## 해결
`result.status == "skipped"` 분기 추가 → `skipped_steps`로 올바르게 분류.

## 재발 방지
- [x] runner.py 병렬 실행 경로에 skipped 분기 추가
- [ ] 순차 실행 경로(`_run_steps_sequential`)에도 동일 패턴 확인 필요
