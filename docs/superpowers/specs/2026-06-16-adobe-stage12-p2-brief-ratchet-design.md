# adobe 독립 Stage 1-2 — P2: editorial brief + 평가·개선 래칫 — 설계

작성일: 2026-06-16
상태: 승인됨 (구현 계획 대기)

## 큰 그림

auto_kairos_adobe를 독립적으로 v3 수준의 기획·리서치·원고까지 수행하게 만드는 작업의 P2.
**런타임에 v3 의존 없음** — v3 프롬프트·로직을 adobe로 이식(복사)해 내재화한다(P1과 동일 원칙: `auto_agent` 참조 0).

지켜야 할 전체 흐름:
> 기획 → **브리프 평가·개선 래칫(점수 게이트)** → 리서치 → 원고 초안 → 타겟 쿼리 추출 → 타겟 리서치 → 타겟 적용 원고 → **원고 평가·개선 래칫(점수 게이트)** → 씬 분석

분해: P1 결정적 리서치(완료) / **P2 브리프+래칫(이 문서)** / P3 리서치 오케스트레이션 / P4 원고+팩트체크 / P5 통합.

## P2 범위 / 목표

plan.md(주제·채널·분량·톤)에서 출발해 **editorial brief를 생성하고, 100점 루브릭으로 채점하는 평가·개선 래칫**을 거쳐, 기준 점수를 넘긴(또는 최고점) brief를 잠가 다음 단계(P3 리서치)에 넘긴다.

**P2가 하지 않는 것(YAGNI):** 리서치 쿼리 생성·수집(P3), 원고(P4). 출력은 잠긴 `editorial_brief.json`.

## 결정사항 (확정)

- **엔진:** adobe 기존 추상화 `llm.run_orchestrator` 사용(기본 claude, `AK_ORCHESTRATOR`/llm_config로 codex 전환 가능). 이미지 없음.
- **래칫:** 100점 루브릭, **90점↑ = PASS**(잠금·진행), 미만은 필드별 REVISE 지시로 다음 버전 생성. **최대 3라운드.** 3라운드 내 미PASS → **최고점 버전 채택(비블로킹)**. **점수 단조 증가**(v{N} < v{N-1}이면 v{N-1} 복원).
- **v3 거대 러너 미사용** — `backend/brief.py`의 단순 Python 루프(adobe pipeline.py 패턴).

## 이식 원본 (읽기 전용, 런타임 비의존)

`/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/skills/agents/`:
- `brief-interviewer-auto/SKILL.md` — best-of-N 자가 Q&A, DNA 레버, coherence_spine 우선
- `brief-reviewer/SKILL.md` — 100점 루브릭(기획 구체성40/실행가능성30/DNA·척추 일관성30) + 사전 블로킹 게이트(spine G1~G5), 판정 90↑ PASS
- `shared/brief-dna.md` — DNA 레버 정의(coherence_spine + narrative_arc + human_truth + hidden_truth + present_connection + evidence_anchors)

이식 시 v3의 `shared/...` 경로 참조는 adobe 인라인/`data/brief-dna.md` 참조로 치환. semoji 기본(plan.md 채널로 파라미터화).

## 아키텍처

### 구성요소
| 단위 | 책임 | 의존 | 인터페이스/산출 |
|---|---|---|---|
| `skills/brief-interview/SKILL.md` (+`skill.json`) | 브리프 생성 프롬프트 이식 | data/brief-dna.md | 입력 plan.md → `editorial_brief.v{N}.json` |
| `skills/brief-review/SKILL.md` (+`skill.json`) | 브리프 채점 프롬프트 이식 | data/brief-dna.md | 입력 brief vN → `brief_review_feedback.v{N}.json` |
| `data/brief-dna.md` | DNA 레버 정의 이식 | — | 두 스킬이 참조 |
| `backend/schemas/editorial_brief.schema.json` | 브리프 구조 계약 | — | JSON 스키마 |
| `backend/schemas/brief_review.schema.json` | 리뷰 구조 계약(score/verdict/spine_blocking/revision_instructions) | — | JSON 스키마 |
| `backend/brief.py` | 래칫 오케스트레이터 | llm, scenes/projects(plan.md) | 아래 함수 |

### `backend/brief.py` 인터페이스
- `parse_plan(proj_dir) -> {topic, writing_style, duration, tone}` — adobe plan.md 파싱(제목/채널/분량/톤). 채널 없으면 style=semoji.
- `generate_brief(proj_dir, *, version, prev_brief=None, revisions=None, on_event=None) -> Path` — brief-interview 스킬을 `llm.run_orchestrator(output_schema=editorial_brief.schema, output_last=editorial_brief.v{N}.json)`로 호출. revisions 있으면 프롬프트에 REVISE 지시 + 이전 brief 주입.
- `review_brief(proj_dir, brief_path, *, prev_path=None, on_event=None) -> dict` — brief-review 스킬 호출 → `{score:int, verdict:'PASS'|'REVISE', spine_blocking:{failed_gates,reasons}, revision_instructions:[...]}`. 파싱 실패 시 `{score:0, verdict:'REVISE', ...}`.
- `run_brief_ratchet(proj_dir, *, threshold=90, max_rounds=3, on_event=None) -> dict` — 아래 흐름. 채택본을 `editorial_brief.json`으로 잠금. 반환 `{brief: path, score, verdict, rounds, history:[{version,score,verdict}]}`.

### 데이터 흐름 (run_brief_ratchet)
```
parse_plan
v1 = generate_brief(version=1)
r1 = review_brief(v1)
best = (v1, r1.score)
if r1.score >= threshold and r1.verdict==PASS: lock(v1); return
for N in 2..max_rounds:
    vN = generate_brief(version=N, prev_brief=best.path, revisions=last_review.revision_instructions)
    rN = review_brief(vN, prev_path=best.path)
    if rN.score < best.score:           # 단조증가 — 하락분 폐기, best 유지
        continue (해당 vN 채택 후보 제외)
    best = (vN, rN.score)
    if rN.score >= threshold and rN.verdict==PASS: lock(vN); return
lock(best.path)                          # 미PASS — 최고점 채택(비블로킹)
return {verdict: best_verdict, ...}
```
`lock(path)` = 해당 vN을 `editorial_brief.json`으로 복사(무삭제: v{N} 원본 보존).

### 사전 블로킹 게이트(spine)
review_brief가 spine 게이트 실패를 감지하면 `verdict='REVISE'` 강제(점수 90↑여도 PASS 금지). brief.py는 verdict를 신뢰 — 게이트 판정은 스킬(LLM) 내부 규칙.

## 입력/출력 파일 (proj_dir 내, 무삭제)
- 입력: `plan.md`
- 중간: `editorial_brief.v1.json`, `v2.json`, ... + `brief_review_feedback.v1.json`, ...
- 출력(잠금): `editorial_brief.json`

## 에러 처리
- generate/review 스킬 rc≠0 또는 출력 파일 없음 → 해당 라운드 실패 기록(history), 루프 중단, 직전 best 잠금 후 진행. best가 없으면(1라운드부터 실패) `{error}` 반환.
- review JSON 파싱 실패 → score=0/REVISE 취급.
- plan.md 없음/필수 필드 없음 → `{error: "plan.md 필요"}`.

## 테스트 전략 (stdlib·monkeypatch, 실제 LLM 0)
`llm.run_orchestrator`를 monkeypatch — 호출 순서대로 미리 정한 brief/review JSON을 output_last에 기록하고 rc=0 반환하는 페이크로 대체.
1. **1라운드 PASS**: review score≥90/PASS → editorial_brief.json 잠금, rounds==1.
2. **REVISE→2라운드 PASS**: v1 점수 80(REVISE) → v2 점수 92(PASS) → 잠금 v2, history 2건.
3. **3라운드 미PASS→최고점**: 80→85→88 → 잠금=88짜리 v3, verdict REVISE, rounds==3.
4. **점수 단조증가**: v1 85 → v2 70(하락) → v2 폐기, best=v1 유지.
5. **spine 블로킹**: review verdict=REVISE+spine_blocking(점수 95라도) → PASS 금지.
6. **plan.md 파싱**: 제목/채널/분량/톤 추출, 채널 없으면 semoji.
7. **스킬 자산 검증**: skill.json input=plan.md·output 경로, 스키마 JSON 유효, data/brief-dna.md 존재.

## 범위 밖 (P3~P5)
- 브리프→리서치 쿼리 생성·수집(P3)
- 원고·타겟 리서치·씬 분석(P4)
- 패널/파이프라인 UI 통합(P5)
