---
tags: [error, pipeline, single_call]
date: 2026-03-17
severity: blocking
pipeline-step: step_6d
agent: visual-composer
status: resolved
recurrence: 0
---

# single_call 1턴 모드에서 error_max_turns 발생

## 증상
step_6d(motion_planning) 실행 시 CLI가 `error_max_turns` + `stop_reason: tool_use` 반환. motion_plan.json에 CLI JSON 래퍼가 그대로 저장됨.

## 원인
`--max-turns 1`로 실행하지만 `--tools ""` 옵션이 없어서:
1. LLM이 Read/Write 등 도구를 사용하려고 시도
2. 1턴 제한에 걸려 도구 응답을 받지 못함
3. `error_max_turns`로 종료
4. `_extract_json_from_cli_output`이 이 에러를 감지 못하고 raw JSON을 파일에 저장

## 해결
`_run_single_call_step`과 `_execute_chapter`의 CLI 명령에 `--tools ""` 플래그 추가:
```python
cmd = [cli_path, "--print", "--output-format", "json",
       "--model", model, "--max-turns", "1",
       "--tools", ""]  # 도구 완전 비활성화
```

## 수정 파일
- `auto_agent/orchestrator/runner.py` — `_run_single_call_step` + `_execute_chapter` CLI cmd에 `--tools ""` 추가

## 재발 방지
- 1턴 모드(single_call) CLI 호출 시 반드시 `--tools ""` 포함
- 새 single_call 스텝 추가 시 이 패턴 따를 것
