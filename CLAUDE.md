# Auto Kairos v3 — 프로젝트 가이드

> 이 파일은 모든 Claude 세션이 시작 시 읽는 프로젝트 규칙서입니다.
> 상세 규칙은 `.claude/rules/`에 분리되어 있습니다.

## Essential (Post-Compact)

> 컨텍스트 압축 후에도 반드시 기억해야 할 핵심 규칙:
> 1. **한글 + 존댓말** — 디스코드 포함 모든 채널
> 2. **이미지 파일 삭제 절대 금지** — 버전 번호로 생성, selected 필드만 전환
> 3. **Remotion 양쪽 동기화** — `remotion/src/` ↔ `auto_agent/remotion_template/src/`
> 4. **래칫 원칙** — 기존보다 명확히 우위인 방식만 채택
> 5. **scene_specs 플랫 스키마** — 중첩 구조 사용 안 함, imageAsset.source 존중
> 6. **경로: pathlib.Path** — 절대경로 하드코딩 금지, `get_workspace_dir()` 사용
> 7. **에이전트 호출은 stdin** — `-p` 플래그 사용 안 함

---

<!-- STATIC: 아래 아키텍처와 구조는 거의 변경되지 않습니다. 높은 신뢰도로 캐시 가능. -->

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

| 에이전트 | Stage | 모델 | 입력 | 출력 |
|----------|-------|------|------|------|
| research-orchestrator | 1 | opus | 주제/기획안 | research_report.json |
| script-director | 2 | opus | research_report.json | scene_specs.json |
| data-mapper | 2 | sonnet | scene_specs + research_digest | scene_specs.json (데이터) |
| script-reviewer | 2 | sonnet | scene_specs.json | review_feedback.json |
| fact-verifier | 2 | sonnet | scene_specs.json | factcheck_report.json |
| assembly-director | 3 | opus | scene_specs.json | TTS + 이미지 + 자막 + 영상 |
| upload-info-generator | 3-1 | sonnet | scene_specs + manifest | upload_info.json |
| multi-contents-director | — | sonnet | scene_specs + manifest | 쇼츠/블로그/카드뉴스/스레드 |

### 데이터 흐름

```
볼트(NAS) → Stage 0 기획안 → Stage 1 리서치 → research_digest → Stage 2 원고+연출 → Stage 3 조립+렌더링 → Stage 4 성과분석 → 볼트
                                                    ↑ 래칫 루프 (최대 3라운드)
```

---

## 3. CLI 사용법 (auto-agent)

```bash
auto-agent project create                              # 프로젝트 생성
auto-agent run --project <slug>                         # 전체 파이프라인
auto-agent run --project <slug> --from step_2           # Stage 2부터
auto-agent run --project <slug> --only step_1           # Stage 1만
auto-agent bg start --project <slug>                    # 백그라운드
auto-agent multi-contents --project <slug>              # 멀티포맷 (Stage 3 후)
auto-agent dashboard                                    # http://localhost:8080
```

### 스텝 ID

| 스텝 | 에이전트/모듈 | 설명 |
|------|-------------|------|
| step_0 | preflight | API키, Node, ffmpeg 검증 |
| step_1 | research-orchestrator | 심층 리서치 |
| step_2 | script-director | 원고 + 씬 분할 + 연출 |
| step_2_data | data-mapper | 리서치 데이터 매핑 |
| step_2_review | ratchet_loop | 래칫 리뷰 (90점, 최대 3라운드) |
| step_2b | fact-verifier (비차단) | 팩트체크 |
| step_3b | assembly-director | TTS + 이미지 + 자막 + 매니페스트 |
| step_3c | upload-info-generator | 썸네일 + 제목 |

> step_3a (image_batch)는 삭제됨 — assembly-director가 직접 이미지 생성

### Claude Code 슬래시 스킬

```
/auto-kairos [주제]     /kairos-research [slug]     /kairos-write [slug]
/kairos-product [slug]  /multi-contents [slug]
```

---

## 4. 핵심 프로세스

### 래칫 리뷰 루프

```
script-director → scene_specs → script-reviewer 평가 (100점)
  → 90점 미만: Edit 모드로 수정 → 재평가 (미수정 씬 점수 고정)
  → 최대 3라운드, 점수 하락 시 이전 버전 복원
```

### runner.py (검증된 사실)
- **에이전트 호출은 stdin** (`-p` 플래그 사용 안 함)
- 타임아웃: research `1200s`, script `600+분×180`, assembly `600+씬×60`
- Resume: 출력 파일 존재 시 스킵, `skip_resume: True`로 강제 재실행

### Creative Brief 주입
- Stage 0 기획안 → `<creative_brief>` 태그로 에이전트 프롬프트에 주입
- `core_angle`, `story_points`, `must_include_episodes`

---

## 5. API 규칙

- Anthropic API 직접 호출은 사용자 요청 시만
- 기본: **Claude CLI (`claude` 바이너리)** 우선
- Qwen3.5: **Ollama chat API + `think: false`** (generate API는 thinking 소진)
- Ollama 프록시: `ollama_proxy.py --port 8090` → Anthropic API 호환

---

## 6. 반복 에러 방지 규칙

> 상세 규칙은 `.claude/rules/` 에 분리되어 있습니다.

@docs/rules/remotion-rules.md
@docs/rules/path-env-rules.md
@docs/rules/scene-specs-rules.md

---

<!-- DYNAMIC: 아래 내용은 프로젝트 진행에 따라 변경될 수 있습니다. -->

## 7. 프로젝트 디렉토리 구조

```
output/{uuid}_{slug}/
├── research_report.json      # Stage 1
├── scene_specs.json          # Stage 2 (핵심)
├── review_feedback.json      # 래칫 리뷰
├── audio/ images/ subtitles/ # Stage 3 에셋
├── remotion/                 # 매니페스트 + 정적 파일
├── multi-contents/           # 쇼츠/블로그/카드뉴스/스레드/SNS스케줄
└── {slug}_final.mp4          # 최종 영상
```

## 8. 설정 파일 위치

| 파일 | 위치 | 역할 |
|------|------|------|
| agents.json | `auto_agent/data/agents.json` | 에이전트 정의 |
| pipeline.json | `auto_agent/data/pipeline.json` | 파이프라인 스텝 |
| SKILL.md | `auto_agent/data/skills/agents/{name}/SKILL.md` | 에이전트 스킬 |
| 아트스타일 | `auto_agent/data/artstyle/styles/*.json` | design_tokens |

## 9. 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| 래칫 점수 안 오름 | 리서치 깊이 부족 or 채점 기준 | pass_threshold 85 or 리서치 보충 |
| 에이전트 파일 미생성 | max_turns 부족 | agents.json + CLI 양쪽 수정 |
| 프로젝트 경로 못 찾음 | uuid 접두사 누락 | `project["output_dir"]` 사용 |
| Remotion 렌더링 실패 | 빈 src or Node 25 | 가드 추가 or 직접 node 호출 |
| launchd 안 먹힘 | UTC 미변환 | KST-9, bootout/bootstrap |

## 10. 볼트 기억 시스템

NAS 볼트(`$KAIROS_VAULT_DIR`) — 벡터 3컬렉션: memory / analysis / research

```bash
# 세션 시작
python3 -m auto_agent.modules.memory_index recall "프로젝트 맥락"
# 세션 종료
# 볼트 09-memory/sessions/{date}-{topic}.md 저장 후:
python3 -m auto_agent.modules.memory_index build
```

**세션 요약 6가지:** 설계 결정 / 실험 결과(수치) / 미해결 문제 / 사용자 피드백 / 다음 우선순위 / 시행착오

## 11. 자동화 스케줄 (launchd)

| 시간 (KST) | 스크립트 | 내용 |
|-----------|---------|------|
| 매일 07:00 | `threads_daily.py` | Threads 발행 |
| 매시간 | `todo_reminder.py` | TODO 리마인더 |
| 월 06:30 | `stage4_weekly.py` | Stage 4 수집 |
| 매일 22:00 | `qwen_ratchet_loop.py` | Qwen 래칫 |
| 월 03:00 | `memory_maintenance.py` | 기억 정리 |

## 12. 에러 볼트

에러 해결 시 → `$KAIROS_VAULT_DIR/08-dev/errors/` 노트 생성.
3회 반복 → `.claude/rules/`에 방지 규칙 추가.
