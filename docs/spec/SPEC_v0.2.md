# auto_kairos Adobe PD Assistant — 기능 스펙 v0.2 (고정본)

> 상태: **확정(locked)**. 이 문서를 기준으로 PRD/로드맵을 작성한다.
> v0.1(사용자 작성) → v0.2(8개 핵심 결정 반영). 변경점은 각 절 끝 `[v0.2 변경]`에 표기.
> 작성일: 2026-06-04

---

## 0. v0.1 → v0.2 고정 결정

| # | 항목 | 확정 |
|---|------|------|
| 1 | 패널 구조 | **공통 패널 구조 + AE 먼저** (CEP 익스텐션 1개가 host 목록으로 다중 앱 지원, PPro는 가산 확장) |
| 2 | 이미지 후보 수 | **Lock=1 / Explore=3 / 상한 4** |
| 3 | AE 자동 모션 수준 | **최소** — 배치 + transform 키프레임 + 카메라 1종 + 자막/오디오 싱크. 캐릭터 리깅(발끝 까딱·스프라이트)은 v2. **"작동" 우선, 모션은 추후 업데이트** |
| 4 | 렌더 흐름 | **AE 렌더 신설(post-MVP)**, remotion-render는 이 제품에 미포함(v3/v4에 잔존) |
| 5 | imagegen MVP 포함 여부 | **포함**. 단 빌드 순서상 **맨 마지막 단계**(먼저 기존 이미지로 AE 왕복 증명 → 그 위에 codex imagegen) |
| 6 | 이미지·LLM provider | **둘 다 Codex 인증 단일** (`codex login` 1회로 image_gen 빌트인 + LLM 모델). raw OPENAI_API_KEY/CLI 폴백은 비상용, FAL 제외 |
| 7 | 백엔드 ↔ codex 연결 | **`codex exec` 주력**(`-o`/`--json`/`--output-schema`). **대화형: `codex exec resume <session_id>`로 멀티턴 + `--json` 스트리밍** → PD Chat 협업. (옵션 `app-server`). ~~Python SDK~~ 부재 확인(PoC) |
| 9 | v4 관계 | **참고 전용 — 자체 구현, v4 호출/의존 없음** `[v0.2 추가]` |
| 8 | 패널 기술 / 기동 | **CEP** + 패널 기동 시 **백엔드 자동 spawn/health-check** |

---

## 1. 제품 정의

auto_kairos Adobe PD Assistant는 After Effects(1차)와 Premiere Pro(2차) 안에서 작동하는 영상 제작 보조 패널이다. 사용자가 Adobe 앱을 벗어나지 않고 auto_kairos 제작 워크플로우를 실행·관리한다.

수행 작업: 프로젝트 생성/불러오기, 원고·아티팩트 확인, 씬 분해, 이미지 생성, 이미지 검수, AE 컴포지션 자동 생성, (2차) Premiere 타임라인 배치, 제작 상태 관리, Codex 기반 작업 실행.

**1차 목표**: 완성형 자동 편집기가 아니라, **Adobe 앱 안에서 auto_kairos 제작 워크플로우를 실행·관리하는 PD 비서 패널**.

---

## 2. 아키텍처

```
[Adobe Panel — CEP/HTML]            ← 사용자 인터페이스 (얇게 유지)
        ↕  HTTP (localhost REST)
[Local Python Backend — FastAPI]    ← 상태·로그·재실행·승인 게이트 관장
        ├─ Codex Runner             ← Codex SDK/exec/app-server (codex 인증)
        │      · LLM 작업(PD챗·씬분해·모션플랜·이미지검수)
        │      · 이미지 생성(codex 빌트인 image_gen)
        ├─ AE JSX Builder           ← ae_manifest.json → .jsx
        └─ auto_kairos Project Store ← projects/{project_id}/ (auto_kairos_v4 구조 재사용)
        ↕  JSX 파일 전달 / evalScript
[After Effects]                     ← 패널이 JSX 실행 → 컴프 생성
```

**재사용 모델 (참고 전용, v4 호출 안 함)** `[v0.2 변경]`: auto_kairos_v4를 **설계 레퍼런스**로만 삼고, 동등 기능(프로젝트 스토어 + 스킬: scene-decompose/motion-plan/image-generate 등 + codex imagegen)을 **이 레포에 자체 구현**한다. auto_kairos_v4 폴더에 대한 import/호출/런타임 의존은 **없다**(완전 자체완결). auto_kairos_v3(Remotion 기반)도 손대지 않는다.

**대화형 협업 (A 구조 + B 경험)** `[v0.2 변경]`: 백엔드는 헤드리스 서비스(A)지만, PD Chat은 codex와 **다회차 대화 + 실시간 작업 스트리밍**으로 "함께 만들어가는"(B) 경험을 준다. 메커니즘:
- 세션 지속: `codex exec resume <session_id> "<후속>"` — 프로젝트/대화별 session id 유지로 멀티턴
- 스트리밍: `codex exec --json`(JSONL 이벤트)을 패널로 흘려 에이전트 작업 과정 실시간 표시
- (옵션) 상주 채널: `codex app-server` daemon

**기술 선택 근거 (CEP)**: 패널이 localhost 백엔드와 HTTP 통신하려면 CEP가 안정적(Node 가능, localhost fetch 제약 없음). UXP는 localhost 통신 제약으로 MVP 부적합. CEP deprecation 리스크는 인지하되 현실해. `[v0.2 변경]`

**Codex 인증 단일화**: codex CLI(0.136+) 설치 + `codex login` 완료 시, codex 빌트인 `image_gen` 도구는 OPENAI_API_KEY 불필요, LLM 모델도 codex 경유. 백엔드는 Codex SDK(우선)/app-server/exec로 codex를 드라이브. → 사용자는 `codex login` 한 번이면 끝. `[v0.2 변경]`

---

## 3. 시스템 구성 요소

### 3.1 Adobe Panel (CEP)
프로젝트 선택, 작업 실행 버튼, 진행 상태, 생성 결과 미리보기, 승인/재실행, AE/PPro 적용 명령. host별 코드(AE JSX / PPro ExtendScript)는 인터페이스 뒤로 분리해 PPro 확장이 가산적이게 한다.

### 3.2 Local Python Backend (FastAPI)
패널과 HTTP 통신, 프로젝트 폴더 읽기, Codex Runner 실행, 결과/이미지 저장, AE JSX 생성, 로그·job 상태 관리. **패널 기동 시 백엔드가 떠있지 않으면 자동 spawn + health-check.** `[v0.2 변경]`

### 3.3 Codex Runner
Codex(SDK/app-server/exec)로 작업 실행. 사용자 명령 → codex 작업 변환, 스킬 실행, **이미지 생성(codex 빌트인 image_gen)**, 실패 재시도, 결과 요약. **LLM·이미지 모두 codex 인증 단일.** `[v0.2 변경]`

### 3.4 auto_kairos Project Store
`projects/{project_id}/` 구조(auto_kairos_v4) 유지: 원고/씬/이미지/manifest/로그/검수 상태.

---

## 4. Adobe 패널 기능

### 4.1 Home / Connection
- Backend 상태 / Codex 상태 / 작업 폴더 표시, Health Check, 백엔드 실행 안내
- `GET /health`, codex 사용 가능 여부, auto_kairos root 확인
- 상태: Backend disconnected/connected · Codex not configured/ready · Project loaded
- **백엔드 미기동 시 자동 실행 시도 + 안내** `[v0.2 변경]`

### 4.2 Project
- 프로젝트 목록/생성/열기, 상태 카드, 최근 아티팩트
- 표시: project_id, 제목, 현재 단계, 마지막 수정, 보유 아티팩트, 다음 추천 작업, 오류
- pd_notebook.md 요약, plan.md/units.json/manifest.json 존재 여부

### 4.3 PD Chat / Command
- 채팅 입력, 실행, 작업 모드 선택, 응답 로그, 결과 링크
- 모드: 일반/원고검토/씬분해/이미지생성/이미지수정/AE컴프/상태점검
- 명령 → 백엔드 → Codex Runner → 결과 요약 → 아티팩트 목록
- **제약: PD Chat은 AE 타임라인을 직접 수정하지 않는다. 컴프 변경은 반드시 별도 승인 버튼.**

### 4.4 Workflow Status
- 단계: 기획·리서치·원고·씬분해·연출설계·이미지생성·이미지검수·manifest·AE컴프·렌더·Premiere·완료
- 단계별 완료/누락 아티팩트/다음 작업 추천/실패/재실행
- 상태값: not_started·ready·running·needs_review·approved·failed·skipped·completed

---

## 5. auto_kairos 작업 기능

### 5.1 Scene Decompose
- 입력: final_manuscript.md(또는 입력 텍스트) → 출력: units.json, scene_plan.json
- 필드: unit_id, scene_id, narration_text, visual_summary, canonical_subject, visual_keywords, duration_estimate, asset_needs, status
- UI: 씬 목록/문장 확인/화면 설명/재분해/병합·분할

### 5.2 Motion Plan
- 입력: units.json, project_chrome.json, style preset → 출력: motion_plan.json
- 필드: scene_id, shot_size, camera_angle, movement, transition, layer_structure, animation_notes, ae_comp_suggestion
- **v1 적용 범위는 §6.1 "최소 모션"으로 한정** — animation_notes는 v2 편집자/리깅용으로 보존 `[v0.2 변경]`

### 5.3 Art Style Config
- 출력: project_chrome.json
- 항목: 비율·해상도·색상 팔레트·일러스트/캐릭터/배경 스타일·테두리·텍스트 사용·안전영역·생성 금지 요소
- UI: 프리셋 선택/스타일 편집/전체 적용/씬별 override

### 5.4 Codex Image Generate `[v0.2 변경: provider 명확화]`
- **provider: Codex 빌트인 image_gen (codex 인증). FAL·외부 batch provider 미사용. raw OPENAI_API_KEY CLI는 비상 폴백.**
- 다수 생성은 내부 병렬 worker 디스패치 (1 worker = 1 이미지)
- 모드:
  - **Explore** — 후보 탐색, 기본 3장 (상한 4)
  - **Lock** — 확정 본생성, 1장
  - **Repair** — 기존 수정, 1장
- 입력: scene_id, visual_summary, motion_plan, project_chrome, reference_images, generation_mode, candidate_count
- 출력: image_results/{scene_id}/candidate_{n}.png, metadata.json
- metadata: scene_id, candidate_id, prompt, revised_prompt, generation_mode, reference_used, status, created_at, elapsed_time, error_message, selected
- UI: 씬별/전체 생성, 후보 수·모드 선택, 갤러리, 선택/재생성/수정

### 5.5 Image Review
- 기준: 원고 적합성·스타일 일관성·캐릭터 일관성·구도·사용 가능성·오류
- 출력: image_review.json (approved/needs_repair/rejected/use_as_reference/manual_check_required)
- UI: 후보별 점수/승인·반려/수정 사유/최종 선택/repair 전송

### 5.6 Manifest Build
- 입력: units.json, motion_plan.json, selected images, TTS, subtitle, style config
- 출력: render_manifest.json, ae_manifest.json, premiere_manifest.json
- 필드: scene_id, duration, narration_path, image_layers, text_layers, camera_motion, transitions, subtitles, ae_comp_name, premiere_marker_name

---

## 6. After Effects 기능

### 6.1 AE JSX Build
- 입력: ae_manifest.json → 출력: ae_scripts/build_project.jsx, build_scene_{id}.jsx, build_final_comp.jsx
- **자동 생성 범위 (v1 = 최소 모션):** `[v0.2 변경]`
  - 프로젝트 생성/열기, 컴포지션·씬별 프리컴프 생성
  - 이미지/오디오 import, 레이어 배치(layout)
  - **기본 등장**: opacity 0→100, scale 95→100 (페이드/스케일인)
  - **카메라 무빙 1종**: 느린 push-in 또는 pan (bg에 scale/position 키프레임)
  - 자막 텍스트 레이어(나레이션 타이밍), 오디오 싱크
  - 렌더 큐 등록(렌더 실행 자체는 post-MVP)
- **v1 비포함(v2/편집자 손)**: 캐릭터 리깅(발끝 까딱·스프라이트), 퍼펫, 정교한 안무, 화려한 트랜지션

### 6.2 AE Apply Panel
- 현재 AE 프로젝트 확인, manifest 선택, JSX 실행, 씬별 컴프 + Final Comp 생성, 로그
- **1차 성공 기준**: 이미지 3장 + 나레이션 3개 테스트 manifest → AE에 씬별 컴프 3개 자동 생성 + Final Comp에 순서 배치

---

## 7. Premiere (2차)

### 7.1 Premiere Import
- 입력: premiere_manifest.json, 렌더된 씬 영상, 나레이션, 자막, 음악
- 기능: media import, active sequence 확인, 씬 순서 배치, 마커, 오디오 트랙, 기본 transition, export preset
- **1차 PPro 성공 기준(2차 시작점)**: AE 렌더 mp4를 active sequence에 순서 배치 + 씬 시작점 marker

---

## 8. Local Python Backend API

| Endpoint | Method | 요약 |
|----------|--------|------|
| `/health` | GET | backend_status, codex_status, auto_kairos_root, version |
| `/api/projects` | GET | project_id, title, status, updated_at, artifact_summary |
| `/api/projects/load` | POST | project_id/path → pd_notebook_summary, available_artifacts, next_actions |
| `/api/skills/run` | POST | project_id, skill_name, brief, options → job_id, status, artifact_paths, summary, decisions |
| `/api/jobs/{job_id}` | GET | status, progress, current_step, logs, artifact_paths, error |
| `/api/images/generate` | POST | project_id, scene_id, mode, candidate_count, prompt_override, reference_paths → job_id |
| `/api/images/results` | GET | project_id, scene_id → candidates, selected, review_status |
| `/api/images/select` | POST | project_id, scene_id, candidate_id → selected_image_path, updated_manifest |
| `/api/ae/build-jsx` | POST | project_id, manifest_path → jsx_path, summary, warnings |

---

## 9. 파일/아티팩트 구조

```
projects/{project_id}/
  pd_notebook.md  plan.md  final_manuscript.md
  units.json  motion_plan.json  project_chrome.json  asset_plan.json
  render_manifest.json  ae_manifest.json  premiere_manifest.json
  image_results/{scene_id}/candidate_NNN.png + metadata.json + selected.json
  image_reviews/  ae_scripts/{build_project,build_scene_NNN,build_final_comp}.jsx  logs/
```

---

## 10. 승인 게이트
- **필수 승인**: 이미지 후보 최종 선택 · AE 컴프 생성 실행 · Premiere 타임라인 반영
- **선택 승인**: 이미지 프롬프트 확정 전 · 씬 분해 확정 · motion plan 확정
- MVP: 이미지 생성은 승인 없이 실행 가능, **결과 선택은 반드시 사용자**

## 11. 로그/재실행
- 모든 작업은 job_id 보유: skill_name, project_id, input summary, start/end, status, artifact_paths, error, retry_count
- 실패 job만 재실행 · 성공 후보 재사용 · **재생성 시 기존 결과 삭제 금지, 새 candidate_id로 추가** (v3 "이미지 삭제 금지" 원칙과 일치)

## 12. 라이선스/계정
1차 제외. 2차+: 로그인, 계정별 디바이스(최대 2대), 사용량 로그, 구독, 팀, 크레딧.

---

## 13. MVP 빌드 순서 + 성공 기준 `[v0.2 변경: 2단계 시퀀스]`

**1단계 — AE 왕복 증명 (기존 이미지 사용)**
1. Adobe 패널 열림
2. 패널 ↔ Local Python Backend 연결(자동 기동 포함)
3. 프로젝트 목록 읽기
4. 특정 프로젝트 불러오기
5. units.json/manifest 표시
9. ae_manifest.json → AE JSX 생성
10. AE에서 JSX 실행 → 씬별 컴프 + Final Comp 생성
→ *이때 이미지는 auto_kairos_v4 프로젝트의 기존 생성 이미지 사용*

**2단계 — codex imagegen 추가**
6. codex 빌트인 image_gen으로 특정 씬 이미지 1장(Lock) 생성
7. 결과를 프로젝트 폴더에 저장
8. 패널에서 생성 이미지 확인

→ **1+2단계 모두 통과 = MVP 완성.** 1단계로 AE 왕복 리스크를, 2단계로 imagegen 리스크를 분리 검증.

## 14. MVP 제외 범위
완전 자동 편집/렌더링, Premiere 자동 배치, 결제/로그인/디바이스 제한, 팀 협업, 클라우드 동기화, **FAL 및 외부 imagegen provider**, 다중 사용자 프로젝트.

---

## 15. 핵심 제품 원칙
1. Adobe 앱 안에서 작업이 시작·종료된다 (백엔드 자동 기동으로 체감 완결)
2. auto_kairos 기존 프로젝트 구조를 깨지 않는다
3. Codex는 실행 엔진이자 PD 보조자다 (LLM·이미지 단일 인증)
4. 사용자는 최종 선택권을 가진다
5. 생성 결과는 항상 파일 아티팩트로 남는다
6. 한 번 생성한 결과는 덮어쓰지 않는다
7. **이미지·LLM 모두 Codex 인증 단일** (FAL 미사용)
8. After Effects 자동 컴프 생성을 먼저 완성한다
9. Premiere는 2차 확장
10. 향후 제품화를 고려해 계정/라이선스를 붙일 수 있게 설계한다

---

## 부록 A. 빌드 착수 시 1차 검증 항목 (PoC 진행 현황)
- ✅ **[검증완료 2026-06-04]** Codex 통합 경로 = `codex exec`(구조화 출력). 공식 Python SDK는 부재. 라이브 왕복 성공(codex 인증, API키 불필요, gpt-5.5). → `docs/poc/POC_codex_runner.md`
- ✅ **[track record로 실증]** codex imagegen — config.toml에 auto-kairos-codex-imagegen 이력 다수 + v4 스크립트 존재. 라이브 1장 생성은 선택 스모크로 남김
- ✅ **[검증완료 2026-06-04]** CEP 익스텐션 ↔ localhost 백엔드 통신 — AE 2026 패널에서 `/health` 연결 확인(codex=ready)
- ✅ **[검증완료 2026-06-04]** ae_manifest.json → JSX → AE 컴프 — 3씬 컴프 + Final 자동 생성 성공. → `docs/poc/RUNBOOK_ae_vertical_slice.md`

> **PoC 4건 전부 통과** — 스펙 v0.2의 핵심 아키텍처(codex 단일 인증 LLM+이미지 / CEP↔백엔드 / manifest→JSX→AE 컴프)가 엔드투엔드 실증됨. 빌드 착수 가능.
