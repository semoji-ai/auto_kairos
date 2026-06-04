# v4-bridge를 v3 표준 Stage 1/2로 영구 통합

- 작성일: 2026-06-04
- 상태: 설계 승인 대기 → 구현 계획 전 단계
- 선행 문서: [2026-05-08-v4-research-bridge-design.md](./2026-05-08-v4-research-bridge-design.md)

---

## 1. 배경 / 문제

현재 main 브랜치에는 두 개의 Stage 1/2 경로가 **구조적 가드 없이 공존**한다.

1. **v3 네이티브 경로** — `pipeline.json`의 stage 1/2 스텝
   (`step_1a`, `step_1_strategy`, `step_1_fresh`, `step_1_vault_lookup`,
   `step_1d_wiki_compile`, `step_1b`, `step_1c`, `step_2_draft`, `step_2_target`,
   `step_2_target_register`, `step_2_target_deepen`, `step_2_manuscript`)
2. **v4-bridge 경로** — `.claude/skills/v4/` 워크플로 + `auto_agent/modules/v4_bridge/adapter.py`

문제점:

- 두 경로 모두 **활성** 상태다. v4-bridge 프로젝트에 `auto-agent run --project X`(전체)를
  실행하면 네이티브 stage 1 다수 스텝과 `step_2_draft`가 재실행되어 v4 산출물과 충돌/덮어쓰기
  위험이 있다. (현재 방어선은 `.v4_bridge_origin` sentinel로 `step_2b/2c`만 스킵 + resume의
  출력파일 존재 스킵뿐 — 부분적)
- v4 워크플로가 v3 씬분할이 요구하는 **원고 마커**(`# Ch N.`, `---`, `<!-- chars: -->`)와
  `outline.json`을 **자동 생성하지 않는다**. adapter는 이를 "PD가 직접 작성"한다고 가정만 한다.
  (`finalize-for-bridge` 스킬은 adapter 에러 메시지에만 언급되고 실제로 존재하지 않음)
- `.claude/skills/v4/` 트리가 **거의 git 미추적**(13개 중 `semoji-animating`만 추적)이라
  git pull로 다른 머신에 전파되지 않는다.
- v4 `deep-research`는 "외부 deep-research 스킬을 실행기로 사용"이라고 description에만 선언하고
  실제 실행기를 배선하지 않았다 → 자체완결성 결여.

## 2. 목표

콘텐츠 제작 트리거(`/auto-kairos` 또는 "콘텐츠 만들자" 의도)가 발생하면:

1. **PD(LLM 오케스트레이터)** 가 v4 방식으로 리서치 + 원고까지 자동 진행
2. 그 뒤 **기존 v3의 씬분할 + 소스 제작**으로 자연 연결
3. 이 동작이 **별도 v4 설치 없이 `git pull`만으로 적용**되도록 v3 구성 자체를 영구 업데이트
4. 기존 v3 네이티브 경로는 **삭제하지 않고** 플래그로 보존(롤백 가능)

### 비목표 (YAGNI)

- 네이티브 v3 stage 1/2 코드 삭제 (게이팅으로 보존)
- Stage 3(조립/렌더) 변경
- 새로운 리서치 lane 추가

## 3. 표준 흐름 (목표 상태)

```
[트리거] /auto-kairos 또는 "콘텐츠 만들자" 의도
   │
   ├─ PD(LLM 오케스트레이터, auto-kairos 스킬 실행 주체) v4 워크플로:
   │    strategy-explore
   │    → fresh-research (가벼운 경로) / deep-research (깊은 경로)
   │    → target-research → draft-write → proofread
   │    → ★finalize-for-bridge (신규)★
   │         · v4 draft 순수 prose에 v3 마커 삽입: # Ch N. / --- / <!-- chars: -->
   │         · outline.json 생성 (v4_bridge/schema_samples/outline.example.json 스키마)
   │         · final_manuscript_marked.md + final_manuscript.md(클린) 산출
   │
   └─ auto-agent run --project X  (PD가 호출, 풀 파이프라인)
        Stage 1 = step_1_v4bridge (adapter, 신규 스텝)
           · 입력: final_manuscript_marked.md, outline.json, research_reports/, research_targeted/
           · 출력: research_report.json, targeted_claims.json, art_style.json,
                   final_manuscript.md, .v4_bridge_origin
           · 네이티브 stage 1(skeleton~chapter_projection) → ENABLE_LEGACY_V3 없으면 SKIP
        Stage 2 = 기존 v3
           · step_2(chapters 씬분할) → step_2_data → step_2_consistency → step_2d
           · step_2_draft/target/manuscript → ENABLE_LEGACY_V3 없으면 SKIP
           · step_2b/2c → .v4_bridge_origin sentinel로 SKIP (기존 유지)
        Stage 3 = 기존 v3 (조립 + 렌더)
```

**핸드오프 경계**: PD가 v4 산출물(마커 원고 + outline + research_*)을 만들어 두면, 이후
adapter→씬분할→소스제작은 전부 파이프라인이 자체 처리한다.

## 4. v3 씬분할이 요구하는 마커 규약 (참조 — 단일 소스는 script-director)

`auto_agent/data/skills/agents/script-director/SKILL.md:201-238` 기준:

| 마커 | 형식 | 역할 | runner 검증 |
|------|------|------|------------|
| 챕터 경계 | `# Ch N. 제목` | 챕터별 병렬 씬분할 구간 추출 | — |
| 씬 경계 | `---` | `---` 1개 = 씬 1개 (절대 규칙) | `---` 개수 ↔ 씬 개수 (runner.py 검증) |
| 캐릭터 힌트 | `<!-- chars: 페르비스트, 강희제 -->` | 대명사/주어생략 씬 인물 식별 → `character_plan.json` → Stage 3 | 캐릭터 일관성 훅 (runner.py:606-615) |

캐릭터 시스템: scene_specs `characters` 배열 → runner pre-step hook이 2씬+ 인물을 자동 추출하여
`character_plan.json` 생성(step_3b 직전). `finalize-for-bridge`는 마커만 정확히 박으면 되고
character_plan 생성은 기존 runner가 담당한다.

## 5. 컴포넌트 설계

### 5.1 신규 스킬: `finalize-for-bridge`

- 위치: `.claude/skills/v4/finalize-for-bridge/SKILL.md`
- 단일 목적: v4 draft(순수 prose) + research → v3 입력 변환
- 책임:
  - **마커 삽입**: `# Ch N.` / `---`(의미 단위, 8분≈40~50개) / `<!-- chars: -->`(2씬+ 인물)
    — script-director 규약을 **참조만** 하고 중복 기재 금지(CLAUDE.md §6-1 토큰 최적화)
  - **outline.json 생성**: `v4_bridge/schema_samples/outline.example.json` 스키마 준수
  - **narration 불변 보장**: adapter `_validate_substring`(adapter.py:39-65)을 통과하도록
    원문 한 글자도 변경 금지 (마커/주석/헤더만 추가)
  - 산출: `final_manuscript_marked.md`, `final_manuscript.md`(클린), `outline.json`
- 입력: 최신 `drafts/v{n}.md`, `research_reports/`, `research_targeted/`, (선택) `plan.md`

### 5.2 v4 `deep-research/SKILL.md` 재작성 (외부 실행기 의존 제거)

- 변경 전: description에 "외부 deep-research 스킬을 실행기로 사용"(미배선)
- 변경 후: **Claude Code 내장 리서치 절차를 명시 배선**
  - WebSearch / WebFetch 로 출처 수집
  - Workflow 도구로 병렬 fan-out(주제 갈래별 리서처) → 출처 fetch → adversarial verify(반론 검증)
    → 인용 합성
  - 산출물 포맷(`research_reports/{slug}.md`, frontmatter `kind: deep`)은 기존 유지
- 효과: 외부 레포/플러그인 vendoring 불필요 → git pull 자체완결성 달성

### 5.3 파이프라인 구성 (`auto_agent/data/pipeline.json`)

- 신규 스텝 `step_1_v4bridge` 추가
  - `module: v4_bridge_adapter` (runner가 `v4_bridge.adapter.run_adapter` 래핑 호출)
  - conditional: v4 산출물(`final_manuscript_marked.md` + `outline.json`) 존재 시 실행
  - 위치: stage_1 선두
- 네이티브 stage 1/2 스텝에 `"legacy_only": true` 필드 부여
  - 대상: `step_1a`, `step_1_strategy`, `step_1_fresh`, `step_1_vault_lookup`,
    `step_1d_wiki_compile`, `step_1b`, `step_1c`, `step_2_draft`, `step_2_target`,
    `step_2_target_register`, `step_2_target_deepen`, `step_2_manuscript`

### 5.4 러너 게이팅 (`auto_agent/orchestrator/runner.py`)

- `_execute_step` 진입부에 게이팅 추가:
  ```python
  if step.get("legacy_only") and os.getenv("ENABLE_LEGACY_V3") != "1":
      return StepResult(step_id=step_id, status="skipped")  # 로그 남김
  ```
- adapter를 모듈 스텝으로 호출 가능하도록 모듈 디스패치에 `v4_bridge_adapter` 등록
- 기존 `.v4_bridge_origin` sentinel skip(step_2b/2c, runner.py:3274-3281) 유지

### 5.5 auto-kairos 스킬 개정 (`.claude/skills/auto-kairos.md`)

- 인터뷰/브리프 게이트(기존) 유지
- 실행부 개정: v4 워크플로 오케스트레이션(strategy→research→draft→proofread→finalize-for-bridge)
  → `auto-agent run --project X`
- 네이티브 v3 stage 1/2 직접 호출 제거

### 5.6 git 자체완결성

- `.claude/skills/v4/` **전체 커밋** (현재 13개 untracked → tracked)
- 신규 `finalize-for-bridge` 스킬 커밋
- `shared/lib`는 순수 표준 라이브러리만 사용 → 추가 pip 의존성 0 (확인 완료)
- 외부 deep-research 실행기 의존 완전 제거(§5.2로 대체)

## 6. 데이터 흐름 / 산출물 매핑

| 산출물 | 생성 주체 | 비고 |
|--------|----------|------|
| `research_reports/*.md` | fresh/deep-research (v4) | deep는 내장 Workflow 리서치 |
| `research_targeted/*.md` | target-research (v4) | |
| `drafts/v{n}.md` | draft-write (v4) | 순수 prose |
| `final_manuscript_marked.md` | **finalize-for-bridge (신규)** | 마커 삽입 |
| `final_manuscript.md` (클린) | **finalize-for-bridge (신규)** | substring 검증 기준 |
| `outline.json` | **finalize-for-bridge (신규)** | chapters 스키마 |
| `research_report.json` | adapter | v4 frontmatter sources → v3 |
| `targeted_claims.json` | adapter | research_targeted → v3 스키마 |
| `art_style.json` | adapter | |
| `.v4_bridge_origin` | adapter | sentinel |
| `scene_specs.json` | step_2 (chapters, v3) | 씬분할 |
| `character_plan.json` | runner pre-step hook (v3) | `<!-- chars: -->` 기반 자동 추출 |

## 7. 에러 처리 / 엣지

- finalize-for-bridge가 narration을 변경하면 → adapter `_validate_substring`이 `ValueError`로 차단
- v4 산출물 누락 시 `step_1_v4bridge` conditional false → 스킵. 이때 네이티브도 legacy gating으로
  스킵되면 step_2(chapters) 입력 부재로 실패 → **명확한 에러 메시지**로 "v4 워크플로 미완료" 안내
- `ENABLE_LEGACY_V3=1` 설정 시 네이티브 경로 전체 복구

## 8. 검증 방법

1. finalize-for-bridge 산출 원고 → adapter 통과 → step_2(chapters)에서 `---` 개수 ↔ 씬 개수 일치
2. `character_plan.json`에 `<!-- chars: -->` 인물이 정상 추출
3. `ENABLE_LEGACY_V3=1` 시 기존 v3 네이티브 경로 무손상 동작
4. v4 deep-research 재작성본이 내장 도구만으로 `research_reports/*.md`(kind:deep) 생성
5. 새 클론(git pull만)에서 v4 스킬 트리 전부 존재 + 외부 의존 0 확인

## 9. 롤백

- 모든 변경은 게이팅/추가 기반 — 코드 삭제 없음
- `ENABLE_LEGACY_V3=1` 환경변수로 즉시 구 경로 복구
- 전체 되돌림은 `git revert`

## 10. 작업 단위 요약

1. `finalize-for-bridge` 스킬 신규 작성
2. v4 `deep-research/SKILL.md` 내장 리서치 절차로 재작성
3. `pipeline.json` — `step_1_v4bridge` 추가 + `legacy_only` 필드
4. `runner.py` — legacy 게이팅 + adapter 모듈 등록
5. `auto-kairos.md` 실행부 개정
6. `.claude/skills/v4/` 전체 + 신규 스킬 git 추적/커밋
