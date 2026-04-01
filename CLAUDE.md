# Auto Kairos v3 — 프로젝트 가이드

> 이 파일은 모든 Claude 세션이 시작 시 읽는 프로젝트 규칙서입니다.
> 이 파일만 보면 전체 시스템의 구조, 사용법, 규칙을 파악할 수 있어야 합니다.

---

## 1. 언어 및 협업 원칙

- **항상 한글로 답변** (코드 주석/변수명 제외)
- **항상 존댓말** (해요체/합쇼체) — 디스코드 포함 모든 채널
- **무조건 동의 금지** — 더 나은 방향이 있으면 근거와 대안을 함께 반론 제시
- **래칫 원칙** — 기존보다 명확히 우위인 방식만 채택, 아니면 현상 유지
- **승인 대기 금지** — 작업 중간에 확인 묻지 말고 바로 진행, 결과만 보고

---

## 2. 시스템 아키텍처

### 2계층 구조

```
운영 계층 (상시 가동)          제작 계층 (프로젝트별)
┌─────────────────┐         ┌─────────────────────────────────┐
│ Stage 0: 기획    │────────→│ Stage 1: 리서치                  │
│ trend-analyst    │         │ research-orchestrator            │
│                  │         │ → research_report.json           │
│ Stage 4: 분석    │         ├─────────────────────────────────┤
│ performance-     │         │ Stage 2: 원고 + 연출              │
│ analyst          │         │ script-director → scene_specs.json│
│                  │         │ data-mapper → 데이터 매핑          │
│ 운영 에이전트:    │         │ script-reviewer → 래칫 리뷰 루프   │
│ threads-publisher│         │ fact-verifier → 팩트체크 (비차단)  │
│ kairos-admin     │         ├─────────────────────────────────┤
└─────────────────┘         │ Stage 3: 에셋 조립 + 렌더링       │
        ↑                   │ assembly-director                │
        │                   │ → TTS + 이미지 + 자막 + 영상      │
        │                   │ upload-info-generator → 썸네일/제목│
        └───────────────────│ /multi-contents → 쇼츠/블로그/etc │
          성과 데이터 피드백   └─────────────────────────────────┘
```

### 에이전트 × 모듈 관계

| 에이전트 | Stage | 모델 | 사용 모듈(도구) | 입력 | 출력 |
|----------|-------|------|----------------|------|------|
| research-orchestrator | 1 | opus | WebSearch, WebFetch | 주제/기획안 | research_report.json |
| script-director | 2 | opus | — | research_report.json | scene_specs.json |
| data-mapper | 2 | sonnet | — | scene_specs + research | scene_specs.json (데이터 필드) |
| script-reviewer | 2 | sonnet | — | scene_specs.json | review_feedback.json |
| fact-verifier | 2 | sonnet | WebSearch | scene_specs.json | factcheck_report.json |
| assembly-director | 3 | opus | tts/image/subtitle/manifest/render/validate | scene_specs.json | TTS + 이미지 + 자막 + manifest + 영상 |
| upload-info-generator | 3-1 | sonnet | — | scene_specs + manifest | upload_info.json |
| multi-contents-director | — | sonnet | — | scene_specs + manifest + research | 쇼츠/블로그/카드뉴스/스레드/SNS스케줄 |
| trend-analyst | 0 | opus | — | 볼트 데이터 | 기획안 |
| performance-analyst | 4 | sonnet | — | YouTube Analytics + 볼트 | 성과 리포트 |
| threads-publisher | — | sonnet | WebSearch | 볼트 세션 로그 | Threads 포스트 |
| kairos-admin | — | opus | Bash | 작업 로그 | PR/스킬 업데이트 |

### 데이터 흐름

```
볼트(NAS) → Stage 0 기획안 → Stage 1 리서치 → Stage 2 원고+연출 → Stage 3 조립+렌더링 → Stage 4 성과분석 → 볼트
                                                    ↑ 래칫 루프 (최대 3라운드)
```

---

## 3. CLI 사용법 (auto-agent)

### 전체 파이프라인

```bash
# 프로젝트 생성 (대화형 — 주제/채널/분량/아트스타일 설정)
auto-agent project create

# 전체 파이프라인 실행
auto-agent run --project <slug>

# 특정 스테이지부터
auto-agent run --project <slug> --from step_2

# 특정 스텝만
auto-agent run --project <slug> --only step_1

# 백그라운드 실행
auto-agent bg start --project <slug>
auto-agent bg start --project <slug> --from step_2
auto-agent bg status --project <slug>
auto-agent bg logs --project <slug>
auto-agent bg stop --project <slug>
auto-agent bg list
```

### 스텝 ID 목록

| 스텝 | 이름 | 에이전트/모듈 | 설명 |
|------|------|-------------|------|
| step_0 | environment_check | preflight (모듈) | API키, Node, ffmpeg 검증 |
| step_1 | deep_research | research-orchestrator | 심층 리서치 (Explorer 병렬) |
| step_2 | script_and_direct | script-director | 원고 + 씬 분할 + 시각 연출 |
| step_2_data | data_mapping | data-mapper | 리서치 데이터 → scene_specs 매핑 |
| step_2_review | ratchet_loop | script-reviewer + script-director | 래칫 리뷰 (90점 목표, 최대 3라운드) |
| step_2b | fact_check | fact-verifier (비차단) | 원고 팩트체크 |
| step_3b | assembly | assembly-director | TTS + 이미지 + 자막 + 매니페스트 |
| step_3c | upload_info | upload-info-generator | 썸네일 + 제목 + 더보기란 |

> **주의**: step_3a (image_batch)는 삭제됨 — assembly-director가 직접 이미지 생성

### 프로젝트 설정

```bash
auto-agent config set --project <slug> art_style quirky_cartoon   # 아트스타일
auto-agent config set --project <slug> voice_id <id>               # TTS 음성
auto-agent config set --project <slug> writing_style iromism        # 문체 (semoji/iromism)
auto-agent config set --project <slug> duration_minutes 10          # 영상 분량
```

### 별도 명령어

```bash
# 멀티포맷 콘텐츠 (Stage 3 완료 후)
auto-agent multi-contents --project <slug>
# → 쇼츠 16개 + 카드뉴스 + 블로그 + 스레드 + SNS 4주 스케줄

# 대시보드
auto-agent dashboard   # http://localhost:8080
```

### Claude Code 슬래시 스킬

```
/auto-kairos [주제]          # 아트스타일 선택 → 추천 주제 → 전체 파이프라인
/kairos-research [slug]      # Stage 1 리서치만
/kairos-write [slug]         # Stage 2 원고+연출만
/kairos-product [slug]       # Stage 3 에셋조립만
/multi-contents [slug]       # 멀티포맷 콘텐츠
```

---

## 4. 핵심 프로세스 상세

### 래칫 리뷰 루프 (Step 2_review)

```
script-director가 scene_specs.json 작성
  → script-reviewer가 평가 (시청자 60점 + 전문가 50점 = 100점)
  → 90점 미만이면 script-director가 Edit 모드로 수정
  → 재평가 (래칫: 점수 하락 시 이전 버전 복원)
  → 최대 3라운드 반복
```

**중요 규칙:**
- 수정은 반드시 **Edit 도구** 사용 (Write로 80씬 전체 재작성하면 턴 소진)
- `skip_resume: True`로 resume 스킵 (래칫 루프 강제 재실행)
- 피드백 히스토리 보존 (`review_feedback_r1.json` ~ `r5.json`)
- 점수 하락 시 이전 최고 버전으로 복원 후 새 이슈로 재수정

### Assembly Director (Step 3b)

assembly-director는 6개 모듈을 도구로 사용:
1. **tts_tool**: ElevenLabs TTS (speed/stability/style 조절)
2. **image_tool**: FAL.ai 이미지 생성 + Serper 이미지 검색
3. **subtitle_tool**: WhisperX 자막 정렬
4. **manifest_tool**: Remotion 매니페스트 빌드
5. **render_tool**: Remotion 영상 렌더링
6. **validate_tool**: 데이터 정합성 검증

> step_3a (image_batch 모듈)는 삭제됨. assembly-director가 직접 판단하며 이미지 생성.

### Creative Brief 주입

Stage 0에서 생성된 기획안이 있으면 에이전트 프롬프트에 `<creative_brief>` 태그로 주입:
- `core_angle`: 핵심 앵글 → 리서치 범위 제한
- `story_points`: 스토리 포인트 → 우선 팩트 검색
- `must_include_episodes`: 필수 에피소드 → 원고에 반드시 포함

---

## 5. runner.py 내부 구조 (검증된 사실)

### CLI 호출 방식
- **모든 에이전트 호출은 stdin으로 프롬프트 전달** (`-p` 플래그 사용 안 함)
- 프롬프트를 임시 파일(`.prompt_{step_id}.md`)에 저장 → stdin으로 전달 → 완료 후 삭제
- "Argument list too long" 에러는 이 코드에서 발생하지 않음

### 타임아웃 스케일링
- research-orchestrator: 분량별 (1분→20턴, 5분→50턴)
- script-director: `600 + duration_min × 180`초
- assembly-director: `600 + scene_count × 60`초

### Resume 로직
- 출력 파일이 이미 존재하면 스킵 (재실행 시 이미 완료된 스텝 건너뜀)
- `skip_resume: True` 설정 시 강제 재실행 (래칫 루프에서 사용)

---

## 6. 프로젝트 디렉토리 구조

```
output/{uuid}_{slug}/
├── research_report.json      # Stage 1 리서치 결과
├── research_report.md        # 마크다운 버전
├── RESEARCH/                 # 리서치 원본 데이터
├── scene_specs.json          # Stage 2 원고+연출 (핵심 파일)
├── review_feedback.json      # 래칫 리뷰 최종 피드백
├── review_feedback_r1~r5.json # 래칫 라운드별 히스토리
├── factcheck_report.json     # 팩트체크 결과
├── art_style.json            # 아트스타일 설정
├── audio/                    # TTS 오디오 파일
├── images/                   # 씬 이미지
├── subtitles/                # 자막 파일
├── remotion/                 # Remotion 매니페스트 + 정적 파일
├── upload_info.json          # 썸네일/제목/더보기란
├── multi-contents/           # 멀티포맷 출력
│   ├── shorts_manifest.json  # 쇼츠 16개 (플랫폼별 제목/해시태그)
│   ├── card_news.json        # 카드뉴스 10장
│   ├── blog.md               # SEO 블로그
│   ├── threads_post.json     # Threads 체인
│   └── sns_schedule.json     # 4주 SNS 스케줄
├── pipeline_state.json       # 파이프라인 상태
├── logs/                     # 실행 로그
└── {slug}_final.mp4          # 최종 렌더링 영상
```

---

## 7. 설정 파일 위치

| 파일 | 위치 | 역할 |
|------|------|------|
| agents.json | `auto_agent/data/agents.json` | 에이전트 정의 (모델/턴/예산/도구) |
| pipeline.json | `auto_agent/data/pipeline.json` | 파이프라인 스텝 정의 |
| SKILL.md | `auto_agent/data/skills/agents/{name}/SKILL.md` | 에이전트별 스킬 프롬프트 |
| 공유 스킬 | `auto_agent/data/skills/shared/*.md` | writing-style, motion-presets 등 |
| 아트스타일 | `auto_agent/data/artstyle/styles/*.json` | design_tokens, staging |
| .env | 프로젝트 루트 | API키, 경로, 환경 설정 |

---

## 8. API 사용 규칙

- Anthropic API 직접 호출은 사용자가 명시적으로 요청할 때만
- 기본적으로 모든 에이전트 실행은 **Claude CLI (`claude` 바이너리)** 우선
- Qwen3.5 로컬 호출: **Ollama chat API + `think: false`** (generate API는 thinking에 토큰 소진됨)

---

## 9. 반복 에러 방지 규칙

### 9-1. Remotion 수정 시 반드시 양쪽 동기화
- `remotion/src/` 수정 → `auto_agent/remotion_template/src/`에도 반드시 동일 수정
- 대시보드 반영 시 `cd remotion && npx vite build --config vite.thumb.config.ts && npx vite build --config vite.editor.config.ts` 필수
- **절대 한쪽만 수정하고 끝내지 말 것**

### 9-2. 씬 렌더링 단일 소스 — SceneRenderer.tsx
- **모든 씬 렌더링은 `remotion/src/components/SceneRenderer.tsx`의 `SceneRendererInner`를 사용**
- 스토리보드, 스튜디오, 씬에디터, Remotion Studio 4뷰 모두 동일 렌더러
- **CreativeScene은 순수 텍스트/데이터 렌더링만 담당** — 이미지 처리를 직접 하지 않음
- 레이아웃/이미지 수정 시 **SceneRenderer.tsx 한 곳만 수정**

### 9-3. 새 파일 추가 시 패키지 데이터 체크
- `pyproject.toml` package-data에 포함되는지 확인
- `.gitignore`에 의해 제외되지 않는지 확인

### 9-4. 스킬 추가 시 체크리스트
- [ ] 스킬 .md 파일 생성 (`auto_agent/data/skills/shared/` 또는 `agents/`)
- [ ] `agents.json` 해당 에이전트 shared_skills 배열에 추가
- [ ] `rule_manager.py` RULE_MANIFEST에 등록

### 9-5. 환경변수
- 새 환경변수 추가 시 `.env.example`에도 추가
- subprocess 실행 시 환경변수 전달 여부 확인
- `CLAUDECODE` 환경변수는 서브프로세스에서 pop 해야 함 (중첩 세션 방지)

### 9-6. Node.js / npx 경로
- `NODEJS_BIN_DIR` 또는 `NODE_DIR` 환경변수로 설정
- 코드에서 하드코딩 금지 — `auto_agent/utils/platform.py`의 `find_node()` 사용

### 9-7. 서버 시작 시 .env 로드 필수

### 9-8. 경로 규칙
- 항상 `pathlib.Path` 사용 (문자열 결합 금지)
- 절대경로 하드코딩 금지 — `KAIROS_HOME` 또는 `get_workspace_dir()` 사용
- `get_workspace_dir()` fallback: `get_package_dir().parent` (CWD에 의존하지 않음)
- 크로스플랫폼: `os.name`, `platform.system()` 분기
- Windows backslash: ChromaDB 등에 전달 시 `str(path).replace("\\", "/")` 필수

### 9-9. mapScene 좌표 규칙
- scene_specs: `[위도, 경도]` (LLM 자연 순서)
- Remotion/MapLibre: `[경도, 위도]` — build_manifest.py가 swap 담당
- **절대 프롬프트에서 [lng, lat] 순서를 강제하지 말 것**

### 9-10. 이미지 파일 삭제 절대 금지
- 재생성/재검색 시 기존 파일 유지
- 새 이미지는 버전 번호로 생성 (`_gen_02`, `_gen_03`)
- `image_assets.json`의 `selected` 필드만 전환
- `rm -f scene_*.png` 같은 명령 **절대 금지**

### 9-11. Remotion 렌더러 규칙
- 씬 렌더링은 **CreativeScene** (`remotion/src/simple/CreativeScene.tsx`)만 수정
- 디자인 토큰은 `artstyle/styles/*.json`의 `design_tokens`에서 관리 (단일 소스)

### 9-12. 디자인 시스템
- 단일 소스: `auto_agent/data/artstyle/styles/<style>.json`의 `design_tokens`
- TypeScript: `resolvePreset.ts` → `DesignPresetProvider`
- Python: `helpers.py` → `_load_design_tokens()` → `get_mood_color()`
- 하드코딩 색상 금지 — 프리셋에서 읽을 것

### 9-13. scene_specs 플랫 스키마
- 모든 필드는 최상위 (layout, motion, mood, headline, items 등)
- `visualization.creative` 중첩 구조 사용하지 않음
- `imageAsset.prompt`로 장면 묘사 (한글), 아트스타일 키워드 넣지 않음
- `imageAsset.source`를 반드시 존중 (search/generate)

### 9-14. 에이전트 턴 소진 방지
- 대용량 JSON 수정 시 **Edit 도구** 사용 (Write로 전체 재작성 금지)
- max_turns 부족 시 `agents.json` + CLI 하드코딩 양쪽 모두 수정
- multi-contents: 80턴 (쇼츠 15 + 카드뉴스 10 + 블로그 10 + 스레드 5 + 스케줄 3)

---

## 10. 트러블슈팅 가이드

### "래칫 점수가 안 오른다" (최고 87.5점 등)
- script-reviewer 채점 기준 확인 (`SKILL.md`의 평가 항목 가중치)
- pass_threshold를 85로 낮추는 것도 옵션
- 원고 자체의 깊이/에피소드/근거가 부족한 경우 리서치 보충 필요

### "에이전트가 파일을 안 쓰고 끝남"
- max_turns 확인 — 너무 적으면 파일 작성 전에 종료
- SKILL.md에 "반드시 Write/Edit으로 결과를 저장하라" 명시
- `skip_resume` 확인 — resume 로직이 기존 파일 감지하고 스킵할 수 있음

### "프로젝트 경로를 못 찾는다"
- `project["output_dir"]`에서 직접 Path 생성 (slug 기반 경로 조합 금지 — uuid 접두사)
- `get_workspace_dir()` 사용 — CWD에 의존하지 않음
- `AUTO_AGENT_DB` 환경변수 확인

### "Remotion 렌더링 실패"
- `<Img src="">` 빈 src 방지: SceneRenderer에 `if (!src) return null` 가드
- Node 25에서 `npx remotion` 실패 시: `node node_modules/@remotion/cli/remotion-cli.js` 직접 호출
- Thumbnail이 Root.tsx 첫 위치면 crash — Formats/ 폴더 격리

### "macOS launchd 스케줄 안 먹힘"
- UTC 변환 필수 (KST - 9시간)
- `load/unload` 대신 `bootout/bootstrap` 사용

---

## 11. 볼트 기억 시스템

NAS 볼트(`$KAIROS_VAULT_DIR`)에 3계층 기억 저장.
벡터 인덱스 3개 컬렉션: memory(기억), analysis(분석), research(리서치).

### 볼트 디렉토리 구조

```
$KAIROS_VAULT_DIR/
├── 01-inbox/                # 새 콘텐츠 수집
├── 03-analysis/             # 영상/채널 분석
│   ├── videos/              # VIDEO_ID별 상세 분석
│   └── images/              # 크롤링 이미지
├── 06-channels/             # 채널별 영상 메타데이터
│   ├── semoji/videos/       # 세모지 498영상
│   └── iromism/videos/      # 이로미즘 117영상
├── 08-dev/                  # 개발 관련
│   ├── TODO.md              # 전체 TODO 리스트
│   └── errors/              # 에러 노트
├── 09-memory/               # 기억 시스템
│   ├── sessions/            # 세션 요약 (날짜-주제.md)
│   ├── decisions/           # 설계 결정 기록
│   ├── compressed/          # 7일+ 압축 기억
│   └── archive/             # 90일+ 아카이브
├── insights/                # 분석 인사이트
│   ├── performance/         # 성과 데이터
│   ├── planning/            # 기획안 (creative brief)
│   └── proposals/           # 문체/연출 업데이트 제안
└── qwen_memory/             # Qwen 래칫 학습 상태
```

### 세션 시작 시 (필수)

```bash
# 벡터 검색으로 관련 기억 로드
python3 -m auto_agent.modules.memory_index search "작업 맥락 키워드" --col memory
python3 -m auto_agent.modules.memory_index recall "프로젝트 맥락"
```

| 목적 | 컬렉션 | 예시 |
|------|--------|------|
| 이전 작업 회상 | memory | `search "래칫 리뷰 점수" --col memory` |
| 채널/경쟁 분석 | analysis | `search "세모지 경쟁채널" --col analysis` |
| 영상/리서치 데이터 | research | `search "삼성 역사 조회수" --col research` |
| 크로스 도메인 | all (기본) | `search "구다이글로벌 전체"` |

### 세션 종료 시 (필수)

볼트 `09-memory/sessions/{date}-{topic}.md`에 저장:

```yaml
---
title: "키워드 풍부하게 (프로젝트명 + 핵심 결과)"
type: session
created: 2026-04-01
tags: [session, 프로젝트명, 핵심기술, 수치결과]
projects: [프로젝트-slug-1, 프로젝트-slug-2]
keywords: [래칫 84→87.5, Write→Edit, $2.51, 75씬]
---
```

**본문 — 6가지만 기록:**
1. **설계 결정**: 왜 이 방식 + 근거
2. **실험 결과**: 수치로 (래칫 81→85, 395초, $2.51)
3. **미해결 문제**: 뭐가 안 되고, 원인 추정
4. **사용자 피드백**: 방향 전환 지시
5. **다음 우선순위**: 번호 매겨서
6. **시행착오**: 실패→원인→해결 한 줄 압축

인덱스 리빌드: `python3 -m auto_agent.modules.memory_index build`

---

## 12. 자동화 스케줄 (launchd)

| 스케줄 | 시간 (KST) | 스크립트 |
|--------|-----------|---------|
| Threads 발행 | 매일 07:00 | `threads_daily.py` |
| TODO 리마인더 | 매시간 | `todo_reminder.py` |
| Stage 4 주간 수집 | 월 06:30 | `stage4_weekly.py` |
| Qwen 래칫 학습 | 매일 22:00 | `qwen_ratchet_loop.py` |
| 기억 정리 | 월 03:00 | `memory_maintenance.py` |
| 문체 업데이트 제안 | 주 1회 | `style_update_proposer.py` |

---

## 13. 에러 볼트 워크플로우

에러를 해결할 때마다:
1. `$KAIROS_VAULT_DIR/08-dev/errors/`에 에러 노트 생성
2. 같은 유형의 에러가 3회 이상 반복되면 → 이 CLAUDE.md의 "반복 에러 방지 규칙"에 추가
