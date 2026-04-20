---
date: 2026-03-18
type: error-fix
status: fixed
tags: [pipeline, single_call, opus, tool_use]
---

# single_call + Opus에서 --tools "" 무시하고 도구 사용 시도 반복

## 증상
- step_4(fact_check), step_5(scene_decomposition) 등 single_call 스텝에서 반복 실패
- `--tools ""` + `--max-turns 3`으로 실행해도 `error_max_turns` + `stop_reason: "tool_use"`
- Opus 모델이 JSON 직접 출력 대신 Write/Read 도구를 사용하려고 계속 시도
- Haiku에서는 정상 작동 (1턴에 JSON 출력)

## 원인
- Claude CLI의 `--tools ""`가 Opus에서 시스템 도구까지 완전 비활성화하지 않는 듯
- Opus가 프로젝트의 CLAUDE.md를 읽으면서 도구 사용을 시도하는 패턴
- max_turns를 늘려도 도구 시도 → 실패 → 도구 재시도 루프에 빠짐

## 해결
- pipeline.json에서 모든 single_call 타입 스텝을 agent 타입으로 전환
- agent 모드에서는 Write 도구를 자유롭게 사용 가능
- 영향받은 스텝: step_4, step_5, step_5b, step_6b, step_6c, step_6d

## 방지 규칙
- Opus 모델에서 single_call (도구 비활성 + 1턴) 사용 금지
- 단순 JSON 변환도 agent 모드로 실행 (비용은 약간 증가하지만 안정성 확보)
