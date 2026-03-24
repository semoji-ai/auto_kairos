---
date: 2026-03-18
type: error-fix
status: fixed
tags: [pipeline, single_call, tools]
---

# single_call --tools "" 에서 LLM이 도구 사용 시도 → error_max_turns

## 증상
- scene_decomposition(step_5)이 single_call로 실행
- `--tools ""` + `--max-turns 1`로 실행
- LLM이 Write 도구로 파일 쓰려고 시도 → 도구 비활성 → 턴 초과
- CLI가 `error_max_turns` 메타데이터를 반환 → 실제 씬 데이터 없음
- scene_specs.json이 빈 상태로 생성됨 → 이후 모든 스텝 실패

## 원인
- CLAUDE.md 규칙 8: "CLI 호출 시 반드시 --tools "" 포함" → 하지만 LLM이 JSON 직접 출력 대신 Write 도구 사용 시도
- max-turns 1에서는 도구 사용 후 결과 반환이 2턴 필요 (도구 호출 + 결과 확인)

## 해결
- `--tools ""` → `--allowedTools Write`로 변경 (Write 도구 허용)
- `--max-turns 1` → `--max-turns 2`로 변경 (도구 사용 + 결과 반환)
- stdout 파싱 실패 시 Write 도구로 직접 저장된 파일 존재 확인 → 성공 처리

## 방지 규칙
- single_call에서 JSON 출력 기대할 때 Write 도구 허용 필수
- CLAUDE.md 규칙 8 수정 필요: --tools ""는 도구 비활성이 아닌 제한적 허용으로
