# v4-research-bridge 워크트리 운영 안내

이 워크트리는 v4의 리서치/원고 방식을 v3에 이식해 검증하는 실험 환경입니다.

## 운영 모드: PD 대화형

메인 Claude는 v4 CLAUDE.md의 PD(프로듀서) 운영 방식을 따릅니다 — 매 단계 사용자 합의 + 서브에이전트 위임.

리서치/원고 스킬은 `.claude/skills/v4/`에서 호출합니다(strategy-explore, fresh-research, deep-research, wiki-organize, draft-write, target-research, review-research, fact-check, proofread, vault-search, vault-absorb).

## 프로젝트 폴더

v3 컨벤션 그대로: `output/{uuid}_{slug}/`. v4 스킬에는 `--project-root output/{uuid}_{slug}` 인자로 경로를 주입합니다.

## 단계

1. PD 대화로 `plan.md` 확정 → `output/{slug}/plan.md`
2. 리서치 → `research_reports/`, `research_targeted/`
3. (선택) 위키 정리 → `wiki/`
4. 드래프트 → `drafts/draft_v1.md`
5. 타겟 리서치 + 보완 → `drafts/draft_v2.md`
6. fact-check + proofread → `final_manuscript.md`

## 어댑터 실행

`final_manuscript.md` 확정 후:

```bash
python -m auto_agent.modules.v4_bridge.adapter --project <slug>
```

이 시점에 `output/{slug}/` 안에 다음이 생성됩니다:
- `_bridge/` (작업 산출물)
- `final_manuscript_marked.md`, `outline.json`, `research_report.json`, `art_style.json` (v3 Stage 2 입력)

## Stage 3 진입

```bash
auto-agent run --project <slug> --from step_2
```

이후 step_2(script-director chapters) → step_2_consistency → step_2_data → step_2b/c/d → step_3b → step_3c. **Stage 3 코드는 무수정**.

## v4 스킬 동기화

v4 본가 업데이트 반영:

```bash
V4_ROOT=$HOME/LocalProjects/auto_kairos_v4 bash scripts/sync_v4_skills.sh
```

## 검증 끝나면

main으로 머지하면서 v3의 step_1/step_2 파이프라인을 v4 방식으로 점진 대체합니다.

## 관련 문서

- `docs/superpowers/specs/2026-05-08-v4-research-bridge-design.md` — 설계
- `docs/superpowers/plans/2026-05-08-v4-research-bridge.md` — 구현 플랜
