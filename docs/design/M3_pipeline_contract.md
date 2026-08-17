# M3 — 콘텐츠→이미지 파이프라인 (v4 참고 + 자체 구현 계약)

> 사용자 확정 10단계를 auto_kairos_adobe에 자체 구현. v4는 참고 전용.
> 테스트 실행: **주제 "테슬라의 역사" / 아트스타일 semoji / 분량 1분.**
> 작성일: 2026-06-05 · 근거: auto_kairos_v4 스킬 매핑(Explore)

---

## 1. 파이프라인 (사용자 확정)

```
① 기획 → ② 딥리서치 → ③ 원고/시나리오(모션그래픽 연출 포함)
→ ④ 타겟리서치(원고 중 흥미 포인트 쿼리) → ⑤ 최종 원고
→ ⑥ 오토리서치(시청자/전문가 관점 평가) → ⑦ 고도화(반복 개선)
→ ⑧ 레퍼런스 리스트업 → ⑨ 레퍼런스 이미지 생성(codex imagegen)
→ ⑩ 스토리보드 생성
```

## 2. 단계별 자체 구현 매핑 (v4 참고)

| 단계 | 스킬(자체, skills/<name>/) | 입력 | 출력 | 실행 |
|------|---------------------------|------|------|------|
| ① 기획 | `plan-explore` | 주제 + 채널/분량 | `strategy/options.md` (각도/훅/구조 옵션) | codex(텍스트) |
| ② 딥리서치 | `deep-research` | plan + 주제 | `research_reports/{slug}.md` | codex(웹) |
| ③ 원고/시나리오 | `draft-write` | research + plan | `drafts/v{n}.md` (모션그래픽 메타라인 `[B-roll:]`/`(연출:)` 포함) | codex(텍스트) |
| ④ 타겟리서치 | `target-research` | draft에서 추출한 쿼리 | `research_targeted/{q}.md` | codex(웹) |
| ⑤ 최종원고 | `finalize-manuscript` | 최신 draft + targeted | `final_manuscript.md` (메타라인 보존) | codex(텍스트) |
| ⑥⑦ 오토리서치+고도화 | `review-refine` | final + research | `review/review-v{n}.md` + 개선된 final | codex 루프(시청자/전문가) |
| ⑧ 레퍼런스 | `reference-list` | final_manuscript | `references.json` | codex(텍스트, 가능시 웹) |
| ⑨ 레퍼런스 이미지 | (백엔드 모듈 `imagegen`) | references + semoji style | `images/ref_{n}.png` | **codex imagegen(PNG)** |
| ⑩ 스토리보드 | (백엔드 모듈 `imagegen` + `storyboard` 스킬) | 씬 + 레퍼런스 이미지 + semoji style | 씬별 `storyboard/sb_{scene}.png` + `storyboard.json`(메타+경로) | **codex imagegen(PNG)** |

> ③ 모션그래픽 연출은 v4처럼 **원고 메타라인**(`[B-roll: ...]`, `(연출: ...)`)으로 담는다. TTS/씬분해 대상 아님(보존).
> ⑥⑦ "오토리서치/고도화" = **시청자 점수(0~10) + 전문가 verdict(PASS/CONDITIONAL/REVISION)** 병렬 평가 → 약점 패치 → 재평가, **점수 정체/PASS까지 반복**(v4 review-draft 래칫). 점수 하락 시 직전 롤백.

## 3. 핵심 구현 결정

### 3.1 오케스트레이션
- 각 텍스트 단계 = codex 스킬 → 기존 `POST /api/skills/run`(codex exec, --output-schema/-o, stdin 프롬프트)로 실행. 출력은 단계별 산출 파일.
- 단계 체인: 백엔드가 순차 실행(M2 동기 방식 계승). 신규 `POST /api/pipeline/run`(전체) 또는 단계별 `/api/skills/run` 반복.
- **세션 지속(멀티턴)**: ③→④→⑤, ⑥⑦ 루프는 codex `exec resume <session_id>`로 맥락 유지(M3에서 router에 session 저장 배선 — M2 백로그 해소).

### 3.2 이미지 생성 (⑨) — 별도 경로 [검증 필요]
- PNG 산출이라 JSON 전제의 `/api/skills/run`과 다름 → **신규 `POST /api/images/generate`**(백엔드 모듈, v4 `generate_images_codex.py` 참고).
- **인증 방침 결정 필요**: codex **단일 인증** 원칙 vs v4 CLI(`image_gen.py`, `OPENAI_API_KEY` 필요).
  - 후보 A(권장): **codex 빌트인 `image_gen` 도구**를 `codex exec`로 호출(codex 인증, 키 불필요). → 1차 PoC로 "codex exec가 image_gen 도구로 파일 저장 가능한가" 검증.
  - 후보 B: v4식 CLI `image_gen.py`(gpt-image, `OPENAI_API_KEY` 필요) — 단일 인증 원칙 위배, 폴백으로만.
- semoji 스타일 자산(`semoji.json` design_tokens + `semoji_base.jpg` 레퍼런스)을 adobe에 **복사**(자체완결). `--image` 첫 번째=스타일 참조.
- 산출물 불변: `images/ref_{n}_v{k}.png` 버전 추가, 삭제 금지(v3/v4 계승).

### 3.3 딥리서치 웹 접근 (②④) [검증 필요]
- codex exec가 웹 검색 도구를 쓰는지 확인. 안 되면 WebSearch/WebFetch를 스킬 절차에 명시(Workflow fan-out은 1분 테스트엔 과함 — 경량).

### 3.4 스토리보드 (⑩) — codex imagegen으로 씬별 프레임 생성
- v4에 스토리보드 전용 스킬 없음 → 자체 정의. **씬마다 codex imagegen으로 스토리보드 컷(semoji 스타일)을 그린다.** ⑨의 레퍼런스 이미지 + semoji 스타일 참조를 `--image`로 첨부(v4 image-generate 패턴).
- `storyboard` 스킬(텍스트)이 씬별 image_prompt+연출노트를 구성 → `imagegen` 백엔드 모듈이 씬별 PNG 생성.
- `storyboard.json`: 씬별 `{sceneNumber, narration, 연출노트, ref_image, image_prompt, sb_image}`(생성 경로 포함).
- 패널: M2 씬 목록 렌더를 확장해 **스토리보드 썸네일 + 연출노트** 표시.
- ⑨/⑩ 모두 codex imagegen 사용 → **imagegen 메커니즘 PoC(§3.2)가 M3b·M3c 공통 선행조건.**

## 4. 산출물 구조 (projects/{id}/)
```
plan.md  strategy/options.md
research_reports/*.md  research_targeted/*.md
drafts/v{n}.md  final_manuscript.md
review/review-v{n}.md
references.json  storyboard.json
images/ref_{n}.png  _imagegen_log.json
art_style.json (semoji 복사본)
```

## 5. 단계적 빌드 (phasing) — writing-plans 분리

이 파이프라인은 다수 서브시스템이라 **3개 플랜으로 분리**:

- **M3a — 텍스트 파이프라인 (①~⑦)**: plan-explore/deep-research/draft-write/target-research/finalize/review-refine 스킬 + 순차 오케스트레이션 + 세션 멀티턴. *위험 낮음, 신규 인증 의존 없음. 먼저.*
- **M3b — 레퍼런스+이미지 (⑧⑨)**: reference-list 스킬 + `/api/images/generate` + semoji 자산 복사. *codex image_gen 인증/메커니즘 PoC 선행 필요.*
- **M3c — 스토리보드 (⑩)**: storyboard 스킬(image_prompt 구성) + `imagegen` 모듈로 씬별 프레임 생성 + 패널 썸네일/연출 렌더. *⑨와 동일 imagegen 메커니즘 재사용.*

> 권장 순서: **M3a 먼저** → (imagegen PoC) → **M3b**(imagegen 모듈 신설 + 레퍼런스) → **M3c**(imagegen 모듈 재사용 + 스토리보드). imagegen 백엔드 모듈은 M3b에서 만들어 M3c가 재사용.

## 6. 1분 테스트 설정 (실행 시)
- 주제: **테슬라의 역사** / 채널·스타일: **semoji** / 분량: **1분**(한국어 ≈ 400자)
- M3a 완료 시: 테슬라 최종 원고(시청자/전문가 평가 통과본) 생성·확인.
- 전체 완료 시: 원고→레퍼런스→semoji 이미지→스토리보드까지 패널에서 확인.

## 7. 비범위 / 후속
- TTS, 씬 레이어 애니메이션(semoji-animating), AE 컴프 조립까지 연결은 M4+.
- 완전 비동기/스트리밍 잡(현재 동기) — 긴 파이프라인이면 M3a에서 폴링 도입 검토.
