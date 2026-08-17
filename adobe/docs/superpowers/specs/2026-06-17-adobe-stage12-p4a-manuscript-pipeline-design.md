# adobe 독립 Stage 1-2 — P4a: 원고 파이프라인 — 설계

작성일: 2026-06-17
상태: 승인됨 (구현 계획 대기)

## 큰 그림

auto_kairos_adobe를 독립적으로 v3 수준으로 기획·리서치·원고→제작까지 수행하게 만드는 작업의 P4a.
런타임 v3 의존 0 — v3 프롬프트·로직을 adobe로 이식해 내재화(P1~P3과 동일: `auto_agent` 참조 0).

전체 흐름:
> 기획 → 브리프 래칫(P2) → 리서치(P3) → **원고 초안 → 타겟 쿼리 → 타겟 리서치 → 타겟 적용 원고 → 원고 래칫(P4a)** → 씬 분석(P4b)

분해: P1 리서치레인 / P2 브리프+래칫 / P3 리서치 오케스트레이션 (모두 완료) / **P4a 원고 파이프라인(이 문서)** / P4b 씬 분석 / P5 통합.

## P4a 범위 / 목표

research_report.json(P3) + editorial_brief.json(P2)에서 출발해 **초안 작성 → 타겟 쿼리 추출 → 타겟 웹리서치 → 타겟 적용 원고 → 100점 루브릭 평가·개선 래칫**을 거쳐 잠긴 `final_manuscript.md`를 산출한다. 이 원고가 P4b 씬 분석의 입력.

**P4a가 하지 않는 것(YAGNI):** 씬 분할·scene_specs·adobe scenes 정규화(P4b). 출력은 `final_manuscript.md`.

## 결정사항 (확정, P2·P3 재사용)

- **엔진:** `llm.run_orchestrator`(기본 claude). 타겟 웹리서치 = **P3 `backend/research/web_agent.run_web_research`**(claude `--allowedTools WebSearch,WebFetch`).
- **래칫:** **P2 `run_brief_ratchet`와 동일 패턴**(write/review로 일반화) — 100점, 90↑ PASS, 최대 3라운드, 단조증가(하락 폐기), 최고점 채택(비블로킹).
- **v3 거대 러너 미사용** — `backend/manuscript.py` 단순 Python.

## 이식 원본 (읽기 전용, 런타임 비의존)

`/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/skills/agents/`:
- `draft-writer/SKILL.md` — research_report+brief → 초안 + research_questions(타겟 쿼리)
- `script-director/SKILL.md`(manuscript 모드) — 초안+targeted_claims → final_manuscript prose
- `script-reviewer/SKILL.md` — 원고 채점(시청자+전문가 관점, brief DNA 가중) → 점수/판정
- `targeted-researcher/SKILL.md` — 질문→웹리서치→targeted_claims (개념 참조; 실제 웹은 P3 web_agent 재사용)

## 아키텍처

### 구성요소
| 단위 | 책임 | 산출 |
|---|---|---|
| `skills/manuscript-draft/` (SKILL.md+skill.json) | research_report+brief → 초안+타겟쿼리 | `draft.md`, research_questions JSON |
| `skills/manuscript-write/` | 초안+claims → prose | `final_manuscript.v{N}.md` |
| `skills/manuscript-review/` | 원고 채점 | `manuscript_review.v{N}.json` |
| `backend/schemas/research_questions.schema.json` | 타겟 쿼리 계약 | `{questions:[str]}` |
| `backend/schemas/manuscript_review.schema.json` | 채점 계약 | `{score_total, verdict, revision_instructions}` |
| `backend/manuscript.py` | 파이프라인 오케스트레이터 | `final_manuscript.md`(잠금) |

### `backend/manuscript.py` 인터페이스
- `generate_draft(proj_dir, *, on_event=None) -> tuple[Path|None, list[str]]` — manuscript-draft 스킬(입력 research_report.json + editorial_brief.json) → `draft.md` + 타겟 쿼리 리스트(`research_questions.json` 기록).
- `targeted_research(proj_dir, questions, *, max_workers=3, on_event=None) -> list[dict]` — 각 질문을 `web_agent.run_web_research`로 병렬 리서치 → `targeted_claims.json`(`[{question, claim, source_url}]`). 빈 결과 격리.
- `write_manuscript(proj_dir, *, version, prev=None, revisions=None, on_event=None) -> Path|None` — manuscript-write 스킬(draft.md + targeted_claims.json + (prev+revisions)) → `final_manuscript.v{version}.md`.
- `review_manuscript(proj_dir, ms_path, *, prev_path=None, on_event=None) -> {score:int, verdict, revision_instructions:list}` — manuscript-review 스킬(원고 + brief) → 채점. 파싱/실패 → score 0/REVISE.
- `run_manuscript_pipeline(proj_dir, *, threshold=90, max_rounds=3, max_workers=3, on_event=None) -> dict` — 아래 흐름. 채택본을 `final_manuscript.md`로 잠금.

### 데이터 흐름 (run_manuscript_pipeline)
```
research_report.json 없으면 → {error}
draft, questions = generate_draft()                 # 없으면 error
claims = targeted_research(questions) if questions else []   # web_agent 병렬, 부분 실패 격리
# 원고 래칫 (P2 패턴, write/review로 일반화):
best = None; last_revisions = None
for n in 1..max_rounds:
    vN = write_manuscript(version=n, prev=best.path, revisions=last_revisions)   # 실패→best 잠금/에러
    rv = review_manuscript(vN, prev_path=best.path)
    last_revisions = rv.revision_instructions
    if best is None or rv.score > best.score: best = (vN, rv.score, rv.verdict)
    if rv.score>=threshold and rv.verdict=='PASS': break
lock(best.path → final_manuscript.md)               # 무삭제: v{N} 보존, 복사
return {manuscript, score, verdict, rounds, history, claims:int}
```
write_manuscript/review_manuscript는 **모듈 전역**(테스트 monkeypatch 지점). 래칫 루프는 P2와 동일 구조.

## 출력 파일 (proj_dir, 무삭제)
- 입력: `research_report.json`, `editorial_brief.json`
- 중간: `draft.md`, `research_questions.json`, `targeted_claims.json`, `final_manuscript.v1.md`…, `manuscript_review.v1.json`…
- 출력(잠금): `final_manuscript.md`

## 에러 처리
- research_report.json 없음 → `{error: "research_report.json 필요 (P3 먼저)"}`.
- generate_draft 실패(스킬 rc≠0/파일 없음) → `{error: "초안 생성 실패"}`.
- 타겟 쿼리 0 → 타겟 리서치 스킵, claims=[], draft로 바로 원고.
- 웹리서치 개별 실패 → 빈 claim 격리(P3 동일).
- write 실패 → best 있으면 잠금, 없으면 error. review 파싱 실패 → score 0/REVISE.

## 테스트 전략 (stdlib·monkeypatch, 실 LLM/웹 0)
1. **generate_draft**: llm.run_orchestrator monkeypatch(draft.md + research_questions.json 기록) → 초안 경로·쿼리 리스트, 실패→(None, []).
2. **targeted_research**: web_agent.run_web_research monkeypatch → claims 생성, 1개 빈 결과 격리, targeted_claims.json 기록.
3. **write_manuscript**: monkeypatch → v{N} 기록, prev+revisions 프롬프트 주입, 실패→None.
4. **review_manuscript**: monkeypatch → score/verdict/revisions 파싱, 파싱 실패→0/REVISE.
5. **run_manuscript_pipeline**(하위 전부 monkeypatch): ①1라운드 PASS ②REVISE→2라운드 PASS ③3라운드 미PASS→최고점 ④단조증가 하락 폐기 ⑤타겟쿼리 0 스킵 ⑥research_report 없음→error ⑦draft 실패→error.
6. **스킬/스키마 자산** 검증.

## 범위 밖 (P4b·P5)
- 씬 분할·scene_specs·adobe 네이티브 scenes(P4b)
- 패널/파이프라인 통합(P5)
