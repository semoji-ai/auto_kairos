# 단계별 기획 게이트 + 분량 자유 입력 — 설계

날짜: 2026-08-03 · 상태: 승인됨

## 배경

현재 새 프로젝트 폼은 분량이 1/3/5분 고정 select이고, 기획 탭은 6단계 텍스트 파이프라인
(plan-explore → deep-research → draft-write → target-research → finalize-manuscript → review-refine)을
버튼 하나로 끝까지 자동 실행한다. 주제 입력 후 기획을 구체화·검토할 개입 지점이 없다.

## 목표

1. 분량: 자유 입력(분 단위 숫자) + 프리셋(1/3/5/10분).
2. 단계별 게이트: 각 단계를 개별 실행 → 산출물 검토·수정 → [다음 단계] 승인 시 진행.
   기존 전체 자동 실행 버튼은 유지.

비목표: 채널 아이덴티티 학습(별도 스펙), 스토리보드 이후 단계 변경.

## 설계

### 백엔드

- `POST /api/pipeline/run-stage` `{project_id, stage}` — `pipeline.run_one()`을 잡으로 실행.
  stage는 `pipeline.PIPELINE` 멤버만 허용(그 외 400).
- 단계 상태는 별도 상태 파일 없이 **산출물 파일 존재로 판정**한다:
  `GET /api/pipeline/status?project_id=` → `{stages: [{name, output, done}]}`.
  done = 각 스킬 cfg의 output 파일 존재 여부. (재실행 시 덮어씀 — 기존 run_one 동작 그대로.)
- 분량은 이미 문자열로 저장되므로 백엔드 변경 없음.

### 패널 (기획 탭)

- 스텝퍼 UI: 6단계를 가로 나열, 상태 표시(✅ 완료 / ⏳ 실행 중 / ○ 대기).
  렌더는 `/api/pipeline/status` 결과 기반.
- [이 단계 실행] → run-stage 잡 → 완료 시 산출물을 기존 파일 편집기(`viewPlanningFile`)에 자동 오픈,
  스텝퍼 갱신. 다음 단계 버튼이 활성화됨(= 게이트: 사용자가 검토 후 직접 다음 실행).
- 완료된 단계도 재실행 가능(수정 반영 재생성).
- 기존 [6단계 자동 실행] 버튼 유지.

### 새 프로젝트 폼

- `newDuration` select → `<input type="number" min="1">` (기본 3) + 프리셋 버튼 1/3/5/10.
  전송값은 `"N분"` 문자열로 조립(하위 호환).

## 에러 처리

- run-stage 실패 시 스텝퍼에 ❌ + 에러 메시지, 해당 단계 재실행으로 복구.
- 입력 누락(missing_inputs)은 기존 run_one 에러 그대로 표면화.

## 테스트

- router: run-stage 유효/무효 stage, status 산출물 존재 판정 (기존 test_router 패턴).
- panel: index.html 스텝퍼·분량 입력 요소 존재, planning.js에 run-stage 호출 존재 (test_panel_structure 패턴).

---

## 부록: B. 채널 아이덴티티 학습 (별도 스펙 예정 — 방향만 합의됨)

- 입력: 유튜브 채널/영상 URL(yt-dlp) + 로컬 mp4 둘 다.
- 분석 산출 = 아이덴티티 팩: `identity/structure.md`(구성·훅), `voice.md`(말투·문체),
  `visual.md`(비주얼), `winning_patterns.md`(성과 상위 패턴). 목표는 채널 아이덴티티 유지.
- 팩을 파이프라인 프롬프트에 자동 주입(기획·원고 ← structure/voice/winning, 스토리보드 ← visual).
- UI: 사이드바 "채널 학습" 섹션. 팩 파일은 기획 탭 편집기로 수정 가능.
