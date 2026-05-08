# v4 Research Bridge — Design

**날짜:** 2026-05-08
**브랜치:** `v4-research-bridge` (워크트리)
**목표:** auto_kairos_v4의 리서치/원고 작성 방식을 v3 워크트리에 이식하고, v3 Stage 3(에셋 조립 + 렌더링)와 어댑터로 연결한다. 워크트리 검증 후 main으로 머지하면서 v3의 step_1/step_2 파이프라인을 v4 방식으로 점진 대체하는 것이 장기 그림.

---

## 1. 범위

**이식 대상 (v4 → v3 워크트리):**
- `strategy-explore`, `fresh-research`, `deep-research`, `wiki-organize`
- `draft-write`, `target-research`, `review-research`
- `fact-check`, `proofread`
- `vault-search`, `vault-absorb`
- `shared/` (lib, 공통 헬퍼)

**경계 (v3 그대로 유지):**
- Stage 3: `assembly-director`, `release-manager`, `image_batch_module`, Remotion 렌더링
- chartagent, fontagent 어댑터, multi-contents 파이프라인
- 대시보드, DB 스키마

**범위 외 (이번 워크트리에서는 안 함):**
- v4의 후단 스킬 (`scene-decompose`, `manuscript-tag`, `asset-research`, `asset-decide`, `manifest-build`, `image-search/generate/review`, `tts-generate`, `subtitle-sync`, `chart-render`, `font-select`, `remotion-render`) — Stage 3가 이미 담당
- v4 PD 운영 매뉴얼 자체의 이식 (대화 패턴은 메인 Claude가 자연스럽게 따른다)

---

## 2. 폴더 구조

```
auto_kairos_v3 (워크트리: v4-research-bridge)
├── .claude/skills/v4/              ← 이식된 v4 스킬들 (rsync로 동기화)
│   ├── strategy-explore/
│   ├── fresh-research/
│   ├── deep-research/
│   ├── wiki-organize/
│   ├── draft-write/
│   ├── target-research/
│   ├── review-research/
│   ├── fact-check/
│   ├── proofread/
│   ├── vault-search/
│   ├── vault-absorb/
│   └── shared/
├── auto_agent/modules/
│   └── v4_bridge/                  ← 신규
│       ├── __init__.py
│       ├── adapter.py              ← v4 산출물 → v3 입력 변환
│       └── chapter_marker_agent.py ← LLM 호출로 마커 삽입
├── output/{uuid}_{slug}/           ← 단일 프로젝트 폴더 (v4도 v3도 여기 사용)
│   ├── pd_notebook.md              ← v4 PD 노트
│   ├── plan.md                     ← v4 전략·기획 확정안
│   ├── wiki/                        ← v4 wiki
│   ├── research_reports/            ← v4 리서치
│   ├── research_targeted/           ← v4 타겟 리서치
│   ├── drafts/                      ← v4 드래프트 + 보완
│   ├── final_manuscript.md         ← v4 최종 원고 (어댑터 입력)
│   ├── _bridge/                     ← 어댑터 산출물 (v3 Stage 2 입력 호환)
│   │   ├── final_manuscript_marked.md
│   │   ├── outline.json
│   │   ├── research_report.json
│   │   └── art_style.json
│   ├── scene_specs.json            ← script-director (chapters) 산출
│   ├── audio/ images/ subtitles/   ← Stage 3 산출 (변경 없음)
│   ├── remotion/
│   └── {slug}_final.mp4
└── docs/superpowers/specs/2026-05-08-v4-research-bridge-design.md (본 문서)
```

핵심 결정: **프로젝트 폴더는 v3 기존 컨벤션(`output/{uuid}_{slug}/`)을 그대로 사용**한다. v4 스킬은 프로젝트 루트 경로를 인자로 받도록 호출한다(v4 원본의 `projects/{project_id}/` 가정과의 차이는 호출 시 `--project-root` 인자로 흡수).

---

## 3. 데이터 흐름

```
사용자 ↔ 메인 Claude (PD 역할)
        │
        ├─→ strategy-explore         → plan.md
        ├─→ fresh-research / deep-research → research_reports/
        ├─→ wiki-organize            → wiki/
        ├─→ draft-write              → drafts/draft_v1.md
        ├─→ target-research          → research_targeted/
        ├─→ review-draft 래칫        (시청자 ≥ 8.0 + 전문가 PASS 도달까지 v{n}→v{n+1} 반복)
        ├─→ fact-check + proofread   → drafts/draft_final.md
        ├─→ (확정)                    → final_manuscript.md
        ├─→ finalize-for-bridge      → final_manuscript_marked.md + outline.json (PD 직접 작성)
        │
        ├─→ [어댑터: v4_bridge.adapter.run(project_dir)]
        │     │
        │     ├─ 입력 검증: outline.json + final_manuscript_marked.md + final_manuscript.md 존재
        │     ├─ build_research_report(research_reports/, research_targeted/) → research_report.json
        │     ├─ build_art_style(style_id, theme) → art_style.json
        │     ├─ substring 검증 — marked manuscript의 본문이 final_manuscript의 substring인지 확인
        │     └─ 4개 산출물을 _bridge/ + 프로젝트 루트 양쪽에 복사
        │
        └─→ auto-agent run --project <slug> --from step_2
              ├─ step_2 (script-director chapters) → scene_specs.json
              ├─ step_2_consistency, step_2_data, step_2b/c/d
              ├─ step_3b (assembly-director) — 무수정
              └─ step_3c (release-manager) — 무수정
```

핵심: **PD가 `finalize-for-bridge` 스킬을 따라 final_manuscript_marked.md와 outline.json을 직접 작성한다. 어댑터는 입력 검증 → research_report 빌더 → art_style 빌더 → substring 검증 → 파일 복사만 담당**한다.

---

## 4. 어댑터 책임 명세

> **설계 변경 (2026-05-08 리팩터):** outline.json + marked manuscript는 LLM이 역파싱하지 않는다. PD가 `finalize-for-bridge` 스킬을 따라 직접 작성한다. 어댑터는 research_report 빌더 + art_style 빌더 + substring 검증 + 파일 복사만 담당한다.

### 4.1 입력 검증

어댑터는 다음 파일/디렉토리가 `<project_dir>/`에 존재하는지 확인한다:
- `final_manuscript_marked.md` — PD가 finalize-for-bridge 스킬 따라 작성
- `outline.json` — PD가 finalize-for-bridge 스킬 따라 작성
- `final_manuscript.md` — 원본 원고 (substring 검증에 사용)
- `research_reports/` — v4 fresh/deep-research 산출
- `research_targeted/` — v4 target-research 산출

### 4.2 research_report.json 빌더 (결정론적)

**입력:** research_reports/*, research_targeted/*

**출력:** `_bridge/research_report.json`

**스키마:** v3의 기존 `research_report.json` 스키마(`claims[]`, `sources[]`, `quotes[]` 등)에 맞춰 v4의 보고서 본문에서 추출. 가능하면 v4 보고서가 이미 JSON 부속물(`*.facts.json` 등)을 갖는지 확인하고 그것을 우선 사용. 없으면 보고서 본문에서 정규식 + 간단 LLM 호출로 추출.

### 4.3 substring 검증

`final_manuscript.md`(원본)과 `final_manuscript_marked.md`(PD 작성)를 비교한다. 마커(`# Ch N.`, `---`)·주석(`<!-- -->`)·공백을 제거한 후 원본 narration이 그대로 substring으로 포함되어 있어야 한다. 검증 실패 시 `ValueError`로 어댑터 실행을 중단한다.

### 4.4 art_style.json

**입력:** PD 결정값 또는 워크트리 디폴트(`quirky_cartoon`, `dark`)

**출력:** `_bridge/art_style.json` — v3 기존 포맷 그대로

---

## 5. 호출 진입점

### 5.1 PD 운영 (대화형)

워크트리에서 메인 Claude는 v4 CLAUDE.md 운영 방식(PD 모드)을 따른다. 단, 프로젝트 루트는 `output/{uuid}_{slug}/` 컨벤션을 사용한다. 워크트리에 다음 안내 파일을 추가:

- `WORKTREE.md` — "이 워크트리에서는 v4 PD 운영. 리서치/원고는 `.claude/skills/v4/` 사용. 원고 확정 후 `python -m auto_agent.modules.v4_bridge.adapter --project <slug>` 실행 → `auto-agent run --project <slug> --from step_2`"

### 5.2 finalize-for-bridge (PD 작성 단계)

원고 확정 후 어댑터 호출 전에 PD가 `.claude/skills/v4/finalize-for-bridge/SKILL.md` 스킬을 따라 두 파일을 직접 작성한다:

- `output/{slug}/final_manuscript_marked.md` — 마커 삽입된 원고
- `output/{slug}/outline.json` — 챕터 메타데이터

### 5.3 어댑터 CLI

```bash
python -m auto_agent.modules.v4_bridge.adapter --project <slug>
# 출력: output/{uuid}_{slug}/_bridge/{outline.json, research_report.json, art_style.json, final_manuscript.md}
# + output/{uuid}_{slug}/ 루트에 복사
```

심볼릭 링크 vs 복사: **복사** 채택. v3 Stage 2 hook이 파일 변경을 감시하지 않고, 디버깅 시 어느 파일이 어느 시점 산출물인지 추적이 명확하다.

### 5.4 Stage 3 진입

`auto-agent run --project <slug> --from step_2` — 변경 없음.

---

## 6. v4 스킬 이식 정책

- **이식 방법:** rsync로 v4 본가 `~/Projects/auto_kairos_v4/skills/<name>` → 워크트리 `.claude/skills/v4/<name>` 복사. 워크트리 내 수정 금지(읽기 전용 취급). v4 본가 업데이트 시 동기화 스크립트 1개로 갱신.
- **동기화 스크립트:** `scripts/sync_v4_skills.sh` — `rsync -av --delete ~/Projects/auto_kairos_v4/skills/{이식 대상 목록}/ .claude/skills/v4/{name}/`
- **버전 표기:** `.claude/skills/v4/VERSION.txt`에 동기화 시점 v4 git commit hash 기록.
- **vendor 의존:** v4 `skills/shared/lib/_vendor/`는 v3 코드의 vendored 사본(L3). 워크트리에서는 v3 본체를 직접 import 가능하므로, v4 vendor 대신 v3 본체로 리졸브하는 import shim을 추가할지 워크트리 검증 단계에서 결정.

---

## 7. 테스트 전략

**1차 검증 프로젝트:** 새 프로젝트 1개를 처음부터 v4 방식으로 돌린다. 짧은 분량(1분) + 단순 주제로 어댑터 시간 단축. PD 대화로 plan.md → wiki → final_manuscript까지 진행 후 어댑터 + Stage 3 실행 → 최종 mp4 산출 확인.

**검증 체크리스트:**
- [ ] v4 스킬들이 `output/{slug}/` 폴더에 정상 기록
- [ ] PD가 finalize-for-bridge 스킬 따라 outline.json + final_manuscript_marked.md 직접 작성
- [ ] 어댑터가 4개 산출물 모두 생성 (outline + marked는 PD 작성분 검증 후 복사)
- [ ] script-director (chapters)의 narration substring hook 통과
- [ ] step_2_consistency, step_2_data 정상 실행
- [ ] step_3b 이미지/TTS/매니페스트 생성
- [ ] 최종 mp4 렌더링 성공
- [ ] 결과 영상의 사실 정확성 + 톤이 v4 PD가 의도한 plan.md와 일치

**비교 검증 (선택):** 동일 주제로 v3 main 브랜치 파이프라인을 한 번 더 실행해 두 결과의 사실 정확성 + 톤 일치도를 사람이 비교.

---

## 8. 위험과 미해결 질문

1. **v3 outline.json / research_report.json 스키마 정확한 키 목록** — 본 설계에서는 "기존 샘플과 일치"로 가정했으나, 실제 키 누락 시 step_2_consistency가 실패할 수 있다. 구현 1단계에서 워크트리 main 브랜치의 최신 샘플 1개를 골라 스키마를 잠근다.
2. **~~chapter_marker_agent 정확도~~** — **해소됨.** LLM 역파싱을 제거하고 PD가 직접 작성하는 방식으로 전환했으므로 이 위험은 없어졌다.
3. **research_report.json 빌더 정확도** — v4 리서치는 자유 형식 markdown 보고서를 산출한다. 정규식 추출이 약하면 LLM 추출로 대체. 1차 검증에서 측정.
4. **vendor 충돌** — v4 vendor가 v3 본체와 다른 버전일 가능성. 충돌 시 워크트리에서는 v3 본체 우선.
5. **Editorial Brief 경로** — v3 step_1c, step_2_target_deepen은 `editorial_brief.md`(v1~v3)를 만든다. v4에는 동등물이 명확하지 않다. plan.md가 brief를 흡수한 것으로 보고 어댑터에서 plan.md → editorial_brief.md 매핑이 필요한지 1차 검증에서 확인.
6. **PD 마커 양식 위반 + outline 키 누락** — PD가 finalize-for-bridge 스킬을 숙지하지 않으면 outline.json 키 누락이나 marked 마커 양식 오류가 발생할 수 있다. `finalize-for-bridge SKILL.md`가 가이드 역할을 하고, 어댑터의 substring 검증이 narration 변경을 자동으로 차단하는 안전망이다. outline.json 키 누락은 step_2에서 에러로 발견된다.

---

## 9. 단계 분해

후속 implementation plan은 이 설계를 바탕으로 별도 작성한다. 큰 덩어리:

- (A) 워크트리 + 브랜치 생성, v4 스킬 동기화 스크립트
- (B) `auto_agent/modules/v4_bridge/` 패키지 골격 + outline/research_report/art_style 빌더
- (C) chapter_marker_agent (에이전트 정의 + 호출 wrapper)
- (D) 어댑터 CLI 엔트리 + WORKTREE.md
- (E) 1차 검증 프로젝트 실행 + 위험 항목 측정
- (F) 측정 결과 기반 보정

각 덩어리의 종료 조건과 순서는 implementation plan에서 확정.
