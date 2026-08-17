# auto_kairos Adobe PD Assistant — 로드맵 v0.1

> 근거: `SPEC_v0.2.md`, `PRD_v0.1.md`, PoC 4건 통과.
> 마일스톤별 **산출물 + 종료(exit) 기준 + 의존성**. MVP = M1~M5.
> 작성일: 2026-06-04

---

## 전체 그림

```
M0 PoC (완료) ─→ M1 골격(완료, 수직슬라이스) ─→ M2 프로젝트/스킬 연결
   ─→ M3 codex 이미지 ─→ M4 manifest+최소모션+승인 ─→ M5 AE 렌더(post-MVP 경계)
   ─────────────────────── 이후: Premiere(2차), 캐릭터 리깅, 계정/라이선스
```

원칙: **각 마일스톤은 그 자체로 "동작하는 한 흐름"** 이어야 한다(데모 가능). 리스크 높은 것부터 이미 PoC로 제거했으므로, 이후는 통합 위주.

---

## M0 — PoC ✅ (완료)
- 산출물: codex exec 검증, 수직 슬라이스(백엔드+패널+JSX), RUNBOOK
- exit: PoC 4건 통과 (`docs/poc/*`)

## M1 — 골격(수직 슬라이스) ✅ (완료)
- 산출물: `backend/app.py`(/health), CEP 패널, `build_scene.jsx`, sample_manifest
- exit: 패널 연결 + 샘플 manifest로 씬 컴프 3개 + Final 생성 (PoC #3/#4)

## M2 — 프로젝트 & 스킬 연결 (MVP 본격 시작)
**목표**: 샘플이 아니라 **실제 v4 프로젝트**를 읽고, codex로 씬 분해까지.
- 산출물:
  - 백엔드 `GET /api/projects`, `POST /api/projects/load` — v4 `projects/{id}/` 스캔/요약
  - 백엔드 `POST /api/skills/run` + `GET /api/jobs/{id}` — `codex exec` 래퍼(job_id, 로그, `-o` 캡처, **session id 유지 + `--json` 스트리밍**)
  - 패널 Project 탭(목록/상태/아티팩트) + PD Chat **다회차 대화 + 스트리밍**(씬분해 모드)
  - **자체 구현** Scene Decompose 스킬(v4 참고): final_manuscript.md → units.json (codex exec)
- 의존성: **자체 projects 스토어 스키마 확정**(v4 참고), scene-decompose 스킬/프롬프트 자체 작성
- **exit 기준 (데모)**: 실제 v4 프로젝트 선택 → "씬 분해" → units.json 생성 + 패널에 씬 목록 표시
- FR: FR-1·2·3·4·9

## M3 — Codex 이미지 생성 & 선택
**목표**: 씬별 codex 이미지 생성 → 후보 표시 → 사용자 선택.
- 산출물:
  - 백엔드 `POST /api/images/generate`(mode=Lock/Explore/Repair), `GET /api/images/results`, `POST /api/images/select`
  - codex imagegen 호출(빌트인 image_gen / v4 image-generate 패턴, 스타일·캐릭터 ref 첨부)
  - 병렬 worker(1 worker=1 이미지), metadata.json, **무삭제 버전 추가**
  - 패널 갤러리 + 선택/재생성/모드·후보수 UI
- 의존성: project_chrome(스타일) 로딩, reference 이미지 경로 규약
- **exit 기준**: 한 씬 Lock 1장 생성 → 폴더 저장 → 갤러리 표시 → 선택 → selected.json 갱신
- FR: FR-5·6 / NFR-1·3

## M4 — Manifest + 최소 모션 + 승인 게이트 (MVP 완성)
**목표**: 선택 에셋으로 **실제 ae_manifest → 최소 모션 컴프** + 승인 흐름.
- 산출물:
  - Manifest Build: units+selected images+(TTS/subtitle) → ae_manifest.json
  - JSX 확장: 이미지 레이어(fit+페이드인) + **카메라 push-in 1종** + 자막 텍스트 + 오디오 싱크
  - 백엔드 `POST /api/ae/build-jsx` (manifest → jsx_path)
  - 승인 게이트: 이미지 최종선택 / AE 컴프 생성 실행 (필수 승인 버튼)
  - 워크플로우 상태 탭 + 실패 재실행
- 의존성: TTS/subtitle 산출물(v4 재사용 여부 확정), motion_plan→카메라 매핑 규약
- **exit 기준 (MVP 성공지표)**: 실제 프로젝트 1개를 불러와 → 씬분해 → 이미지(씬당1장) → 선택 → ae_manifest → **AE 컴프 자동 생성**까지 한 흐름 완주. API 키 설정 0회.
- FR: FR-5·6·7·8·9 / NFR 전반

## M5 — AE 렌더 (MVP/post-MVP 경계)
**목표**: 컴프 생성에서 더 나아가 AE 렌더 큐.
- 산출물: 렌더 큐 등록/실행, 출력 mp4 경로 회수, 패널 렌더 버튼
- **exit 기준**: Final 컴프 → AE 렌더 → mp4 산출
- FR: FR-10 (post-MVP)

---

## 이후 (2차+)
- **Premiere**: premiere_manifest → 시퀀스 배치 + 마커 (FR-11)
- **캐릭터 리깅 모션**: 발끝 까딱/스프라이트 (semoji-animating 이식, FR-12)
- **계정/라이선스**: 로그인, 디바이스(최대 2), 사용량, 구독 (스펙 §12)
- **CEP→UXP 이전 검토**: AE UXP의 외부 IPC 성숙도 보고 판단

---

## 리스크 레지스터 (PoC로 상당수 제거됨)

| 리스크 | 상태 | 대응 |
|--------|------|------|
| codex 단일 인증 LLM+이미지 | ✅ 해소(PoC) | — |
| CEP↔백엔드 통신 | ✅ 해소(PoC) | — |
| manifest→AE 컴프 | ✅ 해소(PoC 기본형) | M4에서 모션/에셋 확장 |
| CEP deprecation | 🟡 중기 | AE UXP IPC 성숙 시 이전 |
| codex imagegen 품질/속도 | 🟡 | Lock=1 기본, Explore 제한, 무삭제 버전 |
| v4 스토어/스킬 결합도 | 🟡 | 블랙박스 호출 우선, 스키마 계약 고정 |
| AE 상주 전제(헤드리스 아님) | 🟢 수용 | 제품 특성상 정상 |

## 다음 행동
M2 착수 = 첫 구현 단계. 여기서부터는 **implementation plan(태스크 분해)** 으로 들어가는 게 맞다(brainstorming→writing-plans 흐름). PRD/로드맵 확정 후 M2 plan 작성.
