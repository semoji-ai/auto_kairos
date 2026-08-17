# auto_kairos Adobe PD Assistant — PRD v0.1

> 근거 문서: `docs/spec/SPEC_v0.2.md`(고정 스펙), `docs/poc/*`(PoC 4건 통과).
> 이 PRD는 스펙을 **사용자 스토리 · 기능 요구사항(FR) · 수용 기준**으로 변환한다.
> 작성일: 2026-06-04

---

## 1. 개요 / 목표

After Effects(1차)·Premiere(2차) 안에서 작동하는 **PD 비서 패널**. 사용자가 Adobe 앱을 떠나지 않고 auto_kairos 제작 워크플로우(프로젝트 관리 → 씬 분해 → 이미지 생성 → 검수 → AE 컴프 자동 생성)를 실행·관리한다.

- **1차 목표**: 완성형 자동 편집기가 아니라, Adobe 앱 안에서 워크플로우를 실행/관리하는 비서.
- **차별점**: Remotion(헤드리스 렌더)과 달리 **편집자가 AE에서 직접 손볼 수 있는** 컴프를 자동 생성.
- **v4 관계**: auto_kairos_v4는 **설계 레퍼런스 전용**. 동등 기능을 이 레포에 **자체 구현**(v4 호출/의존 없음, 완전 자체완결). v3도 미변경.

## 2. 대상 사용자

| 페르소나 | 설명 | 핵심 니즈 |
|----------|------|----------|
| **PD (기획·연출)** | 주제→영상 기획을 주도, 코딩 비전문 | Adobe 안에서 자연어로 제작 지시, 결과 선택 |
| **모션 편집자** | AE로 마감 다듬는 사람 | 자동 생성된 컴프를 **손으로 수정 가능**해야 함 |

## 3. 핵심 사용자 스토리

- US-1: PD로서, 패널에서 auto_kairos 프로젝트 목록을 보고 하나를 불러오고 싶다.
- US-2: PD로서, 패널 채팅으로 "이 원고 씬 분해해줘"라고 지시하면 units.json이 생기길 원한다.
- US-3: PD로서, 씬별로 codex 이미지를 생성하고 후보 중 하나를 **내가 선택**하고 싶다.
- US-4: 편집자로서, 선택된 에셋이 AE에 씬별 컴프 + Final로 자동 배치되어 바로 다듬고 싶다.
- US-5: PD로서, 각 작업의 진행/실패 상태를 보고 실패한 것만 재실행하고 싶다.
- US-6: 누구든, codex 로그인 1회 외에 별도 API 키 설정 없이 쓰고 싶다.

## 4. 기능 요구사항 (FR) — 우선순위: [MVP] / [post]

### FR-1 연결 & 환경 [MVP]
- 패널이 로컬 백엔드 `/health`로 연결 상태(backend/codex/version)를 표시한다.
- 백엔드 미기동 시 자동 spawn을 시도하고, 실패 시 실행 안내를 보여준다.
- **수용 기준**: 백엔드 실행 후 패널이 `connected` + `codex: ready` 표시. *(PoC #3 통과)*

### FR-2 프로젝트 관리 [MVP]
- `GET /api/projects`로 목록(project_id/title/status/updated_at) 표시.
- 프로젝트 불러오기 시 보유 아티팩트 + 다음 추천 작업 표시.
- **수용 기준**: v4 `projects/{id}/` 실제 프로젝트가 목록에 뜨고, 선택 시 plan/units/manifest 존재 여부가 정확히 표시된다.

### FR-3 PD Chat / 대화형 협업 [MVP]
- **다회차 대화**: 자연어 지시 → 백엔드가 codex 세션 유지(`codex exec resume <session_id>`) → 후속 대화가 맥락을 이어감.
- **실시간 스트리밍**: `codex exec --json` 이벤트를 패널 채팅에 흘려 에이전트 작업 과정을 실시간 표시("함께 만들어가는" 경험).
- 결과 요약 + 생성 아티팩트 목록. 작업 모드: 원고검토 / 씬분해 / 이미지생성 / 이미지수정 / AE컴프 / 상태점검.
- **제약**: 채팅은 AE 타임라인을 직접 수정하지 않는다(컴프 변경은 별도 승인 버튼).
- **수용 기준**: 한 대화 세션에서 "씬 분해" → 이어서 "3번 씬 다시 나눠줘" 같은 후속 지시가 맥락을 유지하며 동작하고, 작업 과정이 패널에 스트리밍된다.

### FR-4 씬 분해 [MVP]
- 입력 final_manuscript.md → 출력 units.json, scene_plan.json (스펙 §5.1 필드).
- **수용 기준**: 원고 1개 → 씬 목록이 패널에 표시되고 각 씬 narration/visual_summary 확인 가능.

### FR-5 Codex 이미지 생성 [MVP]
- provider = **codex 인증 단일**(FAL/외부 batch 미사용).
- 모드: Lock(1장)/Explore(3장, 상한4)/Repair(1장).
- 출력: `image_results/{scene_id}/candidate_{n}.png` + metadata.json (스펙 §5.4).
- **재생성 시 기존 결과 삭제 금지, 새 candidate_id로 추가.**
- **수용 기준**: 특정 씬 Lock 1장 생성 → 폴더 저장 → 패널 갤러리에 표시. *(codex 경로 PoC #1/#2 검증)*

### FR-6 이미지 검수 & 선택 [MVP]
- 후보 표시 → 사용자가 최종 선택(필수 승인) → selected.json 갱신.
- **수용 기준**: 후보 중 하나 선택 시 selected가 기록되고 manifest에 반영.

### FR-7 Manifest 빌드 [MVP]
- units + motion_plan + selected images + (TTS/subtitle) → ae_manifest.json (스펙 §5.6).
- **수용 기준**: 선택 완료 후 ae_manifest.json이 생성되고 AE 빌드 입력으로 유효.

### FR-8 AE 컴프 자동 생성 [MVP]
- ae_manifest → JSX 생성 → 패널에서 실행 → 씬별 컴프 + Final 배치.
- v1 모션 = **최소**(레이어 배치 + 페이드인 + 카메라 push-in 1종 + 자막/오디오 싱크).
- **수용 기준**: 이미지3+나레이션3 manifest → 씬 컴프 3개 + Final 순서 배치. *(PoC #4 통과 — 기본형)*

### FR-9 워크플로우 상태 & 재실행 [MVP]
- 단계별 상태(not_started~completed), 누락 아티팩트, job_id 로그, 실패 job 재실행.
- **수용 기준**: 각 작업이 job_id를 갖고, 실패한 것만 재실행되며 성공 결과는 재사용.

### FR-10 AE 렌더 [post]
- AE 렌더 큐 등록/실행. (MVP는 컴프 생성까지)

### FR-11 Premiere 배치 [post]
- premiere_manifest → 시퀀스 클립 배치 + 마커. (2차)

### FR-12 캐릭터 리깅 모션 [post]
- 발끝 까딱/스프라이트 등 (semoji-animating 류). v2.

## 5. 비기능 요구사항 (NFR)

- **NFR-1 인증 단일화**: codex login 1회로 LLM+이미지. 별도 API 키 입력 화면 없음.
- **NFR-2 로컬 우선**: 백엔드는 localhost, 외부 클라우드 의존 없음(MVP).
- **NFR-3 아티팩트 불변**: 생성물은 파일로 남고, 한 번 만든 결과는 덮어쓰지 않음(버전 추가).
- **NFR-4 비파괴**: 패널은 사용자 승인 없이 AE 타임라인/컴프를 바꾸지 않음.
- **NFR-5 의존성 최소**: 백엔드 MVP는 Python 표준 라이브러리로 기동 가능(검증됨).
- **NFR-6 공통 구조**: 호스트별 코드(AE/PPro)는 인터페이스 뒤로 분리 → PPro 확장 가산적.
- **NFR-7 대화형 세션**: 프로젝트/대화별 codex 세션 지속(resume)으로 멀티턴 맥락 유지, 작업 과정 스트리밍.
- **NFR-8 자체완결**: auto_kairos_v4 호출/의존 없음(설계 참고만). git clone만으로 동작.

## 6. 의존성 / 전제 (PoC로 검증됨)

- codex CLI 0.136+ 설치 + `codex login` (auth.json). image_gen 빌트인 + gpt-5.5. ✅
- `codex exec`로 구조화 출력 회수(`-o`/`--json`/`--output-schema`). ✅
- After Effects 2026 + CEP(미서명 → 디버그 모드) 패널. ✅
- auto_kairos_v4 projects 스토어 + 스킬(scene-decompose/image-generate 등). (연결 예정)

## 7. 범위 외 (MVP)
완전 자동 편집/렌더, Premiere 자동 배치, 결제/로그인/디바이스 제한, 팀/클라우드, FAL·외부 imagegen, 다중 사용자, 캐릭터 리깅 모션.

## 8. 성공 지표 (MVP)
- 실제 v4 프로젝트 1개를 패널에서 불러와 → 씬 분해 → codex 이미지(씬당 1장) → 선택 → ae_manifest → **AE 컴프 자동 생성**까지 한 흐름으로 완주.
- 별도 API 키 설정 0회 (codex login만).
- 생성 결과 전부 파일 아티팩트로 잔존, 재실행 시 무삭제.
