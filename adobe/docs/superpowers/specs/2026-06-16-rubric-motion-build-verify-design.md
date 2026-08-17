# rubric 기반 모션 생성 + 검증 설계 (Part 1 빌더 P1 / Part 2 Phase B)

> 작성: 2026-06-16 · 브랜치: feat/tylenol-motion-recreation
> 선행: 모션 학습 파이프라인 Phase A(수집·분석·기법화) 완료, 튜토리얼 리서치 rubric(`docs/research/ae_motion_techniques.md`) 확보.

## 1. 목적

같은 rubric(`docs/research/ae_motion_techniques.md`)을 두 곳에 적용한다.
- **Part 1 — 생성**: 빌더(`build_from_json.jsx`)가 rubric의 이징·역할·변위 원칙으로 모션을 만든다.
- **Part 2 — 검증(Phase B)**: 만든 결과를 헤드리스 렌더 후 원본과 대조해 같은 rubric으로 판정한다.

Part 2가 Part 1을 검증하는 닫힌 루프다 — 빌더 P1이 smoothness/role을 제대로 구현하면 verify의 gemini 충실도 점수가 오른다. 즉 verify는 빌더 변경의 회귀 안전망 역할도 한다.

"임의로 만들어 이상한 결과"를 두 겹으로 막는 것이 핵심 의도다: (a) 생성 시 rubric 수치를 따르고, (b) 검증 시 구조 일치 + rubric 기반 지각 점수로 거른다.

## 2. 배경 — 현재 빌더 사실

- `cep/com.autokairos.pd/jsx/tylenol/build_from_json.jsx` (324줄). `akBuildFromJson()` 안에서 motion.json을 읽어 컷·레이어를 빌드.
- `easeKeys(prop, dim, ease)` (line 167~175): influence가 `(ease === "linear") ? 0.1 : 75`로 **하드코딩**. easeOut/overshoot는 마지막 키, easeInOut는 첫·끝 키에 적용.
- `applyPreset(layer, isText, presetName, t0, dur, params)` (line 176~220): 6 분기(type_on/fade_scale_in/slide_in/pop_bounce/mask_reveal/tilt_2_5d). 컷별 `params`가 프리셋 `params`를 오버라이드(line 178~179).
- 프리셋 정의: `data/artstyle/motion/motion_presets.json` (canonical) + `cep/.../jsx/tylenol/motion_presets.json` (빌더가 읽는 복사본, Phase A merge가 동기화).
- 빌더는 CEP 패널 `evalScript`로 라이브 AE 세션에서 실행. 헤드리스 빌드·렌더 경로는 없음.
- aerender: `/Applications/Adobe After Effects 2026/aerender`. ffmpeg/ffprobe 가용.
- gemini 인프라: `scripts/motion_learn/analyze.py`에 File API 업로드 + 모델 폴백(2.5-flash→2.0-flash→2.5-pro) + JSON 파싱이 인라인 구현됨.

## 3. Part 1 — rubric 기반 빌더 P1 (생성 정교화)

모든 신규 필드는 **옵셔널**이며 기본값이 현행 동작과 동일하다 → 기존 7프리셋·기존 motion.json 무변경 동작(후방호환).

### 3.1 `smoothness` → influence 변환 (가장 큰 래칫)

`easeKeys`의 하드코딩 influence를 smoothness 파라미터로 대체.

변환 테이블 (rubric §1-1 근거):

| smoothness | influence | 의미 |
|---|---|---|
| 0.0 | 0 (linear) | 즉각/기계적 |
| 0.5 | 33 | Easy Ease 기본(대칭, 부드럽지만 무난) |
| 0.75 | 75 | **현행 기본값** snappy 착지 |
| 0.9 | 90 | dramatic |
| 1.0 | 95 | 매우 부드러움 |

- **구현 명세(정확)**: 표의 5개 앵커 포인트(0.0→0, 0.5→33, 0.75→75, 0.9→90, 1.0→95) 사이를 구간별 선형 보간하는 함수 `smoothnessToInfluence(s)`:
  - s<=0.0 → 0
  - 0.0<s<=0.5 → `33 * (s/0.5)` 반올림
  - 0.5<s<=0.75 → `33 + (75-33)*((s-0.5)/0.25)` 반올림
  - 0.75<s<=0.9 → `75 + (90-75)*((s-0.75)/0.15)` 반올림
  - 0.9<s<=1.0 → `90 + (95-90)*((s-0.9)/0.1)` 반올림
- `easeKeys`는 `ease`(기존 이름)와 무관하게, 호출부가 결정한 smoothness로 influence를 받아 적용. ease명만 있고 smoothness 미지정이면 기본 매핑: `linear→0.0, easeOut→0.75, easeInOut→0.75, overshoot→0.75`. (현행 75 유지 → 동작 동일)
- smoothness 출처 우선순위: 컷별 `params.smoothness` > 프리셋 `smoothness` > ease명 기본값.

### 3.2 `role: "in" | "out"`

빌더가 `role:"out"`이면 키프레임 값을 반전한다. 기본 `role:"in"`(현행).

| 프리셋 | in (현행) | out (반전) |
|---|---|---|
| fade_scale_in | opacity 0→100, scale from→100 | opacity 100→0, scale 100→from |
| slide_in | position offset→target | position target→offset |
| pop_bounce | scale 0→ov→100 | scale 100→ov→0 |
| mask_reveal | trimEnd 0→100 | trimEnd 100→0 |
| tilt_2_5d | rotationY 0→angle | rotationY angle→0 |
| type_on | textOffset 0→100 | textOffset 100→0 (역타이핑) |

- 반전은 각 분기에서 `setValueAtTime`의 시작/끝 값을 교환하는 방식. role 출처: 컷별 `params.role` > 프리셋 `role` > `"in"`.

### 3.3 `distance` 스케일러

변위 크기를 `distance`(기본 1.0)로 곱한다. 0.5 subtle ~ 2.0 dramatic (rubric §4-2).

| 프리셋 | distance가 곱해지는 값 |
|---|---|
| slide_in | `offset` (기본 80) |
| fade_scale_in | `scaleFrom`의 100으로부터의 거리 → `100 - (100-scaleFrom)*distance` |
| pop_bounce | `overshoot`의 100 초과분 → `100 + (overshoot-100)*distance` |
| tilt_2_5d | `angle` |

- distance 출처: 컷별 `params.distance` > 프리셋 `distance` > 1.0.

### 3.4 스키마 (motion_presets.json + 컷 params)

프리셋·컷 params 양쪽에서 다음 옵셔널 키 인식:
```json
{ "role": "in|out", "smoothness": 0.0~1.0, "distance": 0.5~2.0 }
```
기존 `props`/`ease`/`params`(cps/scaleFrom/dir/offset/overshoot/settle/angle 등)는 그대로. 새 키 미지정 시 현행 동작.

## 4. Part 2 — Phase B 검증·평가

### 4.1 헤드리스 원샷 AE (`cep/.../jsx/tylenol/verify_render.jsx`, 신규)

- AE를 `afterfx -r verify_render.jsx`로 무인 실행.
- 경로 수신: `$.getenv("AK_VERIFY_MOTION")`(motion.json 절대경로), `$.getenv("AK_VERIFY_OUT")`(출력 .mov 절대경로), `$.getenv("AK_VERIFY_AEP")`(저장할 .aep 절대경로).
- 동작: 새 프로젝트 → `build_from_json.jsx`를 `$.evalFile`로 로드해 `akBuildFromJson`을 motion.json으로 실행 → 빌드된 **최상위 컴프**를 렌더 큐에 추가(기본 OM, Lossless .mov) → .aep 저장 → `app.project.renderQueue.render()` (블로킹) → `app.quit()`.
- **렌더 대상 컴프 확정**: `akBuildFromJson`이 현재 컴프를 반환하지 않으므로, 이 작업에서 빌더가 생성한 최상위 컴프를 반환(또는 약속된 이름으로 생성)하도록 최소 수정한다. verify_render.jsx는 그 반환 컴프(없으면 마지막으로 추가된 CompItem)를 렌더한다.
- 컷·레이어 빌드는 기존 빌더 함수 재사용(중복 금지). verify_render.jsx는 "로드 → 빌드 호출 → 컴프 확정 → 렌더 → 저장 → 종료" 오케스트레이션만.

### 4.2 verify.py (`scripts/motion_learn/verify.py`, 신규)

`verify(slug, refs_dir, lib_path) -> dict` 오케스트레이션:
1. 전제: `refs/{slug}/motion.json` 존재, `refs/{slug}.mp4`(원본) 존재. 없으면 error 반환(state 미변경).
2. **구조적 검사(결정론적)**: motion.json 파싱 → 컷 수, 각 컷 dur 합, 사용된 preset 이름이 라이브러리에 존재하는지 확인. 빌드 산출 .aep 메타가 아니라 motion.json 자체 정합성 + 프리셋 존재성 검사. 실패 항목을 `structural.issues[]`에 기록, `structural.pass = issues가 없음`.
3. **렌더**: 환경변수 설정 후 `afterfx -r verify_render.jsx` subprocess 실행(타임아웃). 산출 .mov 존재 확인.
4. **ffmpeg**: `render.mov → render.mp4` (H.264). 
5. **지각 검사(듀얼 비디오 gemini)**: gemini_client로 원본.mp4 + render.mp4 업로드 → rubric §5 검증 지침을 프롬프트에 주입 → `{score: 0~100, diffs:[{cut, kind, detail}], summary}`. kind ∈ {timing, position, easing, color, missing, polish}.
6. **게이트**: `passed = structural.pass and (score >= threshold)` (threshold 기본 75).
7. 산출: `refs/{slug}/verify/verdict.json` = `{structural, score, diffs, summary, threshold, passed}`. state stage = `verified`(passed) | `needs_improvement`(else).
8. **무삭제**: build.aep/render는 회차 번호로 보존(`build_01.aep`, `render_01.mov` …), 재실행 시 덮어쓰지 않음.

순수 로직(테스트 대상)으로 분리:
- `smoothness_to_influence(s)` — Part 1 변환 테이블의 Python 참조 구현(빌더 jsx와 수치 일치 검증용 + 문서화). *주: 실제 적용은 jsx. Python 측은 명세 잠금 + 단위테스트.*
- `structural_check(motion: dict, lib: dict) -> dict` — 컷/dur/preset 존재 검사.
- `passes_gate(structural_pass: bool, score: int, threshold: int) -> bool`.
- `parse_verdict(raw: str) -> dict` — gemini JSON 파싱·검증.
- `build_ae_command(aerender_or_afterfx, jsx_path) -> list[str]` 및 env dict 구성.
- `build_ffmpeg_command(mov, mp4) -> list[str]`.

### 4.3 gemini_client.py (`scripts/motion_learn/gemini_client.py`, 신규 — DRY 리팩터)

`analyze.py`의 인라인 gemini(클라이언트 생성, File API 업로드, 모델 폴백, JSON 응답)를 공유 모듈로 추출.
- `class GeminiClient` 또는 함수군: `upload(path) -> file_handle`, `generate(contents, *, response_json=True, models=DEFAULT_MODELS) -> str`.
- `analyze.py`를 이 모듈 사용하도록 수정(동작 동일, 회귀 테스트로 보장).
- verify.py가 듀얼 비디오(파일 2개 + 프롬프트)로 동일 인프라 사용.

### 4.4 CLI (`scripts/motion_learn/__main__.py`, 수정)

`verify --slug <s>` 서브커맨드 추가 → `verify.verify(slug, REFS, LIB)` 호출, verdict 요약 출력.

## 5. 컴포넌트 경계 / 태스크 분해

| # | 파일 | 책임 | 테스트 |
|---|------|------|--------|
| C1 | `build_from_json.jsx` easeKeys/applyPreset | smoothness→influence 테이블 | jsx 구문검증 + Python 참조 함수 단위테스트 |
| C2 | `build_from_json.jsx` applyPreset | role 반전 | jsx 구문검증 |
| C3 | `build_from_json.jsx` + 스키마 문서 | distance 스케일러 | jsx 구문검증 |
| C4 | `gemini_client.py` (신규) + analyze.py 수정 | gemini 공유(DRY) | 모킹 단위테스트 + analyze 회귀 |
| C5 | `verify_render.jsx` (신규) | 헤드리스 빌드+렌더 | jsx 구문검증 |
| C6 | `verify.py` (신규) | 구조검사+ffmpeg+듀얼비디오 gemini+게이트 | 순수 로직 단위테스트 |
| C7 | `__main__.py` | `verify` 서브커맨드 | CLI 단위테스트 |

## 6. 에러 처리

- 원본.mp4/motion.json 없음 → error 반환, state 미변경(멱등 재시도).
- AE 기동 타임아웃/크래시, 렌더 산출물 없음 → error, state 미변경. 구조적 검사 결과는 verdict에 기록.
- ffmpeg 실패 → error.
- gemini 503/레이트리밋 → gemini_client 모델 폴백 재사용. 전부 실패 시 error.
- 무삭제 원칙: build/render 산출물 회차 번호 보존.

## 7. 테스트 전략

- 외부 도구(AE/aerender/gemini/ffmpeg)는 모킹 또는 subprocess 호출 인자 검증. jsx는 구문 검증(노드/패턴) — 헤드리스 실행은 CI 불가.
- 순수 로직은 단위테스트로 100% 커버: `smoothness_to_influence`(앵커·보간값), `structural_check`(컷 수·dur·미존재 프리셋), `passes_gate`(조합), `parse_verdict`(정상/깨진 JSON), 커맨드/env 구성.
- 닫힌 루프: 실제 verify 실행으로 빌더 P1 회귀 확인(수동 E2E, CI 아님).

## 8. 범위 밖 (YAGNI)

- Phase C 개선 루프(차이→프리셋/빌더 보정→재렌더·재대조).
- P2 고급효과(트랜지션/파티클/셰이프 모핑 — 빌더 Effect 레이어 확장 필요).
- Animation Composer의 `bundle`/`layout_preset`/Wiggle·Looper 베이크(P2~P3).
- 다중 레퍼런스 배치 자동화(단일 slug verify부터).
