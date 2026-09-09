# Auto Kairos 5.0 — 프로젝트 가이드

> 이 파일은 모든 Claude 세션이 시작 시 읽는 프로젝트 규칙서입니다.
> 상세 규칙은 `docs/rules/`에 분리되어 있습니다.

## Essential (Post-Compact)

> 컨텍스트 압축 후에도 반드시 기억해야 할 핵심 규칙:
> 1. **한글 + 존댓말** — 디스코드 포함 모든 채널
> 2. **이미지 파일 삭제 절대 금지** — 버전 번호로 생성, selected 필드만 전환
> 3. **Remotion 단일 소스** — `auto_agent/remotion_template/src/`만 수정, `remotion/src/` 직접 수정 금지 (`scripts/sync_remotion_src.py`로 미러링)
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
│ 운영 에이전트:    │         │ manuscript-reviewer → 원고 게이트  │
│ threads-publisher│         │ script-reviewer → 씬 게이트        │
│ kairos-admin     │         │ fact-verifier → 팩트체크 (비차단)  │
│                  │         ├─────────────────────────────────┤
└─────────────────┘         │ Stage 3: 에셋 조립 + 렌더링       │
        ↑                   │ assembly-director                │
        │                   │ → TTS + 이미지 + 자막 + 영상      │
        │                   │ release-manager → 업로드 패키지    │
        └───────────────────│ /multi-contents → 쇼츠/블로그/etc │
          성과 데이터 피드백   └─────────────────────────────────┘
```

### 에이전트 × 모듈 관계

| 에이전트 | Stage | 모델 | 입력 | 출력 |
|----------|-------|------|------|------|
| skeleton-from-vault | 1a | module | vault wiki/claims + ingest status | skeleton.json + outline.json |
| flesh-researcher | 1b | opus | outline.json | chapter_facts/ |
| draft-writer | 2_draft | opus | outline.json + chapter_facts/ | draft.md + research_questions.json |
| targeted-researcher | 2_target | sonnet | research_questions.json | targeted_claims.json |
| script-director (manuscript) | 2_manuscript | opus | draft.md + targeted_claims.json | final_manuscript.md |
| manuscript-reviewer | 2_manuscript_review | sonnet | final_manuscript.md + brief | manuscript_review.json + drafts/v{N}.md |
| script-director (chapters) | 2 | opus | final_manuscript.md | scene_specs.json |
| script-reviewer | 2_review | sonnet | scene_specs.json | review_feedback.json |
| data-mapper | 2_data | sonnet | scene_specs + targeted_claims | scene_specs.json (데이터) |
| fact-verifier | 2b | sonnet | scene_specs.json | factcheck_report.json |
| assembly-director | 3b | opus | scene_specs.json | TTS + 이미지 + 자막 + 영상 |
| release-manager | 3c | sonnet | scene_specs + manifest + final_manuscript | upload_info.json |
| multi-contents-director | — | sonnet | scene_specs + manifest | 쇼츠/블로그/카드뉴스/스레드 |

### 데이터 흐름

```
볼트(NAS) → Stage 0 기획안 → skeleton → chapter_facts/ → draft.md → targeted_claims → final_manuscript → scene_specs → Stage 3 조립+렌더링 → Stage 4 성과분석 → 볼트
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
auto-agent plan --project <slug> --topic <주제>           # 기획안 독립 생성 (파이프라인 외부)
auto-agent plan-trend --channel <채널>                    # trend-analyst Stage 0 (기획 트렌드 분석)
```

### 대시보드 직접 실행 (uvicorn)

```bash
# 올바른 방법 — 루트 app.py가 진짜 대시보드
python -m uvicorn app:app --host 0.0.0.0 --port 8080

# 잘못된 방법 — auto_agent.dashboard.app:app 은 존재하지 않음
```

- **루트 `app.py`** = 실제 대시보드 엔트리 포인트
- `auto_agent/dashboard/` 폴더의 템플릿/라우터를 서빙
- 탭: 리서치 / 원고 / 스토리보드 / 스튜디오 / 업로드 / 멀티 / 버전 / 에이전트 / 파이프라인
- 대시보드는 1개, 별도의 "구버전"은 없음

### 스텝 ID

| 스텝 | 에이전트/모듈 | 설명 |
|------|-------------|------|
| step_0 | preflight | API키, Node, ffmpeg 검증 |
| step_1a | skeleton_from_vault_module | 초기 내러티브 골격(skeleton.json) |
| step_1_strategy | research-strategist | outline + research_queries + hook_strategy |
| **step_1_fresh** | **fresh_collector_module** | **lane 4종(wiki/news/crossref/openlib) 병렬 + tier_hint** [Phase 1] |
| **step_1_vault_lookup** | **vault_lookup_module** | **NAS 02-research에서 매칭 토픽 흡수 (LLM slug 매처)** [Phase 2] |
| **step_1d_wiki_compile** | **wiki_compiler_module** | **raw → wiki/<topic>/{overview,claims,entities,timeline,index}.md** [Phase 3] |
| ~~step_1_ingest~~ | source_ingest_module | **[LEGACY]** ENABLE_LEGACY_INGEST=1로만 실행. step_1_fresh+vault_lookup으로 대체됨 |
| step_1b | chapter_projection_module | vault wiki/claims + outline → chapter_facts/ |
| step_1c | brief_deepener | editorial_brief v1 → v2 심화 |
| step_2_draft | draft-writer | 초고 + WHY/HOW 질문 목록 |
| step_2_target | targeted-researcher | 정밀 웹 리서치 → targeted_claims.json |
| step_2_target_deepen | brief_deepener | brief v2 → v3 최종 잠금 |
| step_2_manuscript | script-director (manuscript) | 최종 원고 prose + claims_ledger.jsonl (fact-retriever 절차). **문체 미적용** |
| **step_2_polish** | **script-polisher** | **윤문 전담 — 확정된 원고에 채널 문체 적용. 수치·고유명사·인과 불변** |
| **step_2_manuscript_review** | **manuscript-reviewer** | **원고 게이트 — 자체 3라운드 래칫. 분량·서사·문체. 씬분할 전 마지막 수정 지점** |
| step_2 | script-director (chapters) | 씬 분할 + 연출 결정 |
| **step_2_review** | **script-reviewer** | **씬 게이트 — 자체 3라운드 래칫. 시청자 + 콘텐츠 전문가 2관점** |
| step_2_consistency | script-director (consistency) | 내러티브 흐름 보정 |
| step_2_data | data-mapper | 데이터 필드 매핑 |
| step_2b | fact-verifier (비차단) | 팩트체크 + 비문 검사 (grammar_issues) |
| step_2c | fact-fixer (비차단) | fact-verifier 권고 자동 패치 + 비문 수정 |
| step_2d | scene_enricher | 씬 에셋 풍부화 |
| step_3b | assembly-director | TTS + 이미지 + 자막 + 매니페스트 |
| step_3c | release-manager | 제목 4종·더보기란·해시태그·썸네일 스펙 |
| (외부) | **fact-retriever** | script-director가 글 쓰며 호출하는 사이드카 — evidence span 검증 [Phase 3] |
| (외부) | **vault-sync-agent** | `auto-agent vault-sync --project <slug>` — 프로젝트 wiki/claims_ledger를 NAS 볼트로 push [Phase 4] |

> step_3a는 별도 파이프라인 스텝이 아님 — assembly-director가 Phase B-2에서 `image_batch_module`을 Bash로 직접 호출하고, Phase B-3에서 LLM이 결과 이미지를 멀티모달로 검수·재생성한다.

### Claude Code 슬래시 스킬

```
/auto-kairos [주제]     /kairos-research [slug]     /kairos-write [slug]
/kairos-product [slug]  /multi-contents [slug]
```

---

## 4. 핵심 프로세스

### 문체는 초고에 걸지 않는다 — 구성/문체/연출 3분할

문체 규격(세모지 "그런데" 3~7회 등)을 초고부터 강제하면 작가가 형식을 맞추느라 내용이 밀린다.
그래서 채널 스타일 스킬을 셋으로 나누고 단계별로 준다.

| 가족 | 내용 | 받는 단계 |
|---|---|---|
| `narrative-<style>` | 구성·서사 — 후킹, 서사 구조, 챕터 전환, 클로징, 페이싱 | `step_2_draft`부터 (초고) |
| `voice-<style>` | 문체 — 시그니처 빈도, 톤·어미, 인용, 볼드 마커, 참조 원고 | `step_2_polish`부터 (윤문) |
| `direction-<style>` | 연출 — layout 선택, imageAsset, 씬 분할 기준 | `step_2`부터 (씬분할) |

- 파이프라인 스텝은 **`style/narrative` · `style/voice` · `style/direction`**로 선언한다.
  runner의 `_resolve_style_skills()`가 활성 `writing_style`에 맞는 변종으로 해석한다.
- **자동 주입하지 않는다.** 예전에는 활성 writing-style 스킬을 모든 에이전트에 넣고
  `<project_config>`로 "문체 필수 적용"을 무조건 지시했다. 초고 작가는 규칙서(스킬)는 못 받고
  준수 명령만 받는 상태였다. 지금은 스텝이 선언한 가족만 가고, 문체 지시문도
  `_step_applies_voice()`가 참일 때만 들어간다.
- `writing-style-<style>.md`는 포인터 스텁으로만 남아 있다. 내용은 3분할 파일에 있다.
- **윤문은 사실을 바꾸지 않는다.** 리듬·빈도 규격을 채우려고 없는 사실을 만들지 말 것.
  규격 미달은 `polish_report.json`의 `unmet_targets`에 사유와 함께 적는다.

### 래칫 리뷰 루프 — 게이트 2개

같은 래칫 패턴을 **원고 단계와 씬 단계에 각각** 건다. 문장을 고치는 것은 싸고 씬을 다시 쪼개는 것은
비싸므로, 분량·서사·문체처럼 원고에서 잡을 수 있는 것은 씬분할 전에 끝낸다.

```
step_2_draft / step_2_manuscript → final_manuscript.md   (내용 + 구성, 문체 미적용)
  → [step_2_polish] script-polisher — 채널 문체 적용, 수치·고유명사·인과 불변
  → [step_2_manuscript_review] manuscript-reviewer 평가 (100점, 연출 제외)
       블로킹 게이트 G1~G5: 분량 ±10% / 챕터 정합 / 금지 각도 / 필수 누락 / 근거 없는 수치
       → 미달: drafts/v{N}.md로 개정본 저장 + final_manuscript.md 동기화 → 재평가
       → 최대 3라운드, 점수 하락 시 이전 버전 복원

step_2(씬분할) → scene_specs.json
  → [step_2_review] script-reviewer 평가 (100점, 시청자 + 콘텐츠 전문가)
       → 90점 미만: 문제 씬만 수정 → 재평가 (미수정 씬 점수 고정 → 단조 증가)
       → 최대 3라운드, 점수 하락 시 이전 버전 복원
```

- 루프는 **에이전트가 SKILL.md 안에서 자체 수행**한다. runner가 라운드를 돌리지 않는다
  (`step_0d` brief-reviewer와 같은 방식).
- 둘 다 `blocking:false` — 점수 미달로 파이프라인을 세우지 않고 최고 점수 버전으로 진행한다.
- 목표 나레이션 글자 수는 runner가 `duration_minutes × 400`으로 계산해 `<project_config>`로 주입한다
  (`runner.py`의 `target_chars`).
- ⚠️ **원고 게이트는 하류 정정을 되돌리면 안 된다.** `editorial_brief.evidence_anchors`는 의뢰인의
  주장이지 검증된 사실이 아니다. `fact_fix_log.json` > `factcheck_report.json` > `claims_ledger` >
  `editorial_brief` 순으로 근거 우선순위를 따른다.

### `auto_agent/orchestrator/runner.py` (검증된 사실)
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

> 상세 규칙은 `docs/rules/` 에 분리되어 있습니다.

@docs/rules/remotion-rules.md
@docs/rules/path-env-rules.md
@docs/rules/scene-specs-rules.md
@docs/rules/design-system-rules.md
@docs/rules/direction-standard.md
@docs/rules/character-sheet-rules.md
@docs/rules/image-review-rules.md
@docs/rules/scene-visual-decision.md
@docs/rules/direction-recipes.md
@docs/rules/infographic-asset-rules.md
@docs/rules/scene-video-rules.md
@docs/rules/shared-vs-branch.md

---

## 6-1. 토큰 최적화 규칙

**모든 에이전트/모듈 개발 시 컨텍스트 중복 주입 금지.**

- **스킬로 위임**: 반복되는 지침(도구 사용법, 포맷 규칙 등)은 `shared/` 스킬로 분리하고 에이전트 프롬프트에서는 스킬 참조만
- **프롬프트 ↔ SKILL.md 중복 금지**: `source_ingest_module.py`의 프롬프트와 `SKILL.md`에 같은 내용이 있으면 SKILL.md 한 곳만 유지
- **스킬 간 중복 금지**: 새 스킬 작성 전 기존 `shared/` 스킬에 이미 있는 내용인지 확인
- **allowed_tools 최소화**: 에이전트가 실제로 사용하는 도구만 선언 (미사용 도구는 컨텍스트 낭비)
- **context_replaces 활용**: runner.py의 `context_replaces` 필드로 대용량 파일을 이전 단계 결과로 교체
- **검토 체크포인트**: 에이전트 프롬프트 수정 시 "이 내용이 SKILL.md 또는 다른 프롬프트에 이미 있는가?" 확인 후 작성

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

### 산출물은 커밋하지 않는다

프로젝트가 만들어 낸 것(이미지·음성·영상·레이어·스토리보드)은 저장소에 올리지
않는다. `output/`·`adobe/projects/`·`_imggen/` 아래의 **바이너리**가 그것이다.
원고·기획·표석 같은 **텍스트(.md/.json/.jsonl)는 기록이라 계속 추적한다.**

완성한 편은 보관 워크스페이스(NAS)로 보낸다.

```bash
python -m auto_agent.scripts.archive_project <프로젝트> [--dry-run]
```

실물만 NAS 로 가고 원래 자리에는 `ARCHIVED.json` 표석이 남는다. **DB 의
`output_dir` 은 건드리지 않는다** — NAS 경로를 박았다가 대시보드가 죽은 적이
있다(`docs/v5-plan.md:76`). 복사 → 해시 검증 → 삭제 순서라 중간에 끊겨도 원본이
남는다(NAS 실측 쓰기 11MB/s·작은 파일 4.3개/초, 한 편이 10분을 넘는다).

> ⚠️ `.gitignore` 의 `projects/*/…` 는 **깊이 하나만** 맞는다. 그래서
> `projects/_archive/<편>/images/` 가 새어 2.9GB(1,802 파일)가 커밋된 적이 있다.
> 지금은 `projects/**/…` 규칙과 pre-commit 관문
> (`auto_agent/scripts/check_no_artifacts.py`)이 두 겹으로 막는다.

## 8. 설정 파일 위치

| 파일 | 위치 | 역할 |
|------|------|------|
| agents.json | `auto_agent/data/agents.json` | 에이전트 정의 |
| pipeline.json | `auto_agent/data/pipeline.json` | 파이프라인 스텝 |
| SKILL.md | `auto_agent/data/skills/agents/{name}/SKILL.md` | 에이전트 스킬 |
| 아트스타일 | `auto_agent/data/artstyle/styles/*.json` | design_tokens |
| 구글 드라이브 공유 | `/Users/jleavens_macmini/Projects/googleDrice_shared` | 로컬↔구글드라이브 공유 폴더 (파일 공유 시 여기에 저장) |

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
| 월 03:00 | `memory_maintenance.py` | 기억 정리 |

## 12. 에러 볼트

에러 해결 시 → `$KAIROS_VAULT_DIR/08-dev/errors/` 노트 생성.
3회 반복 → `docs/rules/`에 방지 규칙 추가.
