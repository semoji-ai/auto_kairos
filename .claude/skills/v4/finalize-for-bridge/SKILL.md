---
name: finalize-for-bridge
description: v4 draft(순수 prose)를 v3 Stage 2 입력으로 변환. 씬/챕터/캐릭터 마커 삽입 + outline.json 생성. v4 원고 작성 완료 후 adapter 실행 직전에 호출.
---

# finalize-for-bridge

v4 워크플로의 마지막 단계. draft의 순수 prose에 v3 씬분할이 요구하는 마커를 박고
outline.json을 생성한다. **narration 텍스트는 한 글자도 바꾸지 않는다**(마커/주석/헤더만 추가).

## Reads
- `drafts/v{n}.md` — n이 가장 큰 파일이 최신 draft (순수 prose)
- `research_reports/*.md`, `research_targeted/*.md` — 캐릭터·챕터 판단 근거
- (선택) `plan.md`, `pd_notebook.md` — 톤·기획 의도
- `auto_agent/data/skills/agents/script-director/SKILL.md` "마커" 절 — 마커 규약 단일 소스(Read)
- `auto_agent/modules/v4_bridge/schema_samples/outline.example.json` — outline 스키마(Read)

## Writes
- `final_manuscript.md` — draft prose 그대로(클린, frontmatter 제거)
- `final_manuscript_marked.md` — 마커 삽입본
- `outline.json` — 챕터 메타데이터

## Input resolution
- 최신 draft = `drafts/` 에서 `v{n}.md` 중 n 최대값
- draft가 없으면 중단하고 decisions에 사유 명시(원고 작성 미완료)

## 마커 규약 (단일 소스: auto_agent/data/skills/agents/script-director/SKILL.md "마커" 절)
- `# Ch N. 제목` — 챕터 경계 (outline 챕터와 1:1)
- `---` — 씬 경계 (의미 단위 1개 = `---` 1개. 8분 분량 기준 40~50개)
- `<!-- chars: ID1, ID2 -->` — 대명사/주어생략 씬의 등장 인물(2씬+ 등장만)
  - `---` 다음 줄 또는 씬 시작 직후 배치
  - 동일 인물은 전체에서 동일 문자열

상세 삽입 기준·예시는 script-director SKILL.md를 Read해 따른다. 여기서 중복 기재하지 않는다.

## 불변 보장
final_manuscript_marked.md에서 마커와 frontmatter를 제거하면 final_manuscript.md와
정확히 일치해야 한다. adapter의 substring 검증을 통과해야 하며, 실패 시 ValueError로 차단된다.

## 실행 절차
1. `drafts/` 에서 n 최대인 `v{n}.md` 선택. YAML frontmatter(`---...---` 블록)가 있으면
   제거(없으면 그대로) → `final_manuscript.md` 저장
2. `schema_samples/outline.example.json`을 Read해 스키마 확인 → research로 챕터 구조·
   등장 인물 파악 → `outline.json` 작성
3. script-director SKILL.md "마커" 절을 Read → `final_manuscript.md` 복사본에
   `# Ch` / `---` / `<!-- chars: -->` 삽입 → `final_manuscript_marked.md` 저장
4. 자체 검증: marked에서 마커 라인(`^# `, `^---$`, `^<!-- ... -->$`)과 frontmatter를
   제거하고 공백 정규화 → `final_manuscript.md`와 문자열 일치 확인. 불일치면 narration을
   건드린 것이므로 마커만 남기고 원문 복원

## 금지
- narration 텍스트 변경(요약/재작성/오탈자 수정 포함 — proofread 단계에서 이미 완료)
- layout/motion/imageAsset/headline 등 연출 결정(v3 step_2 책임)

## 한국어 작성 규칙
- 가타카나/히라가나/한자 금지
- 외래어는 한글 표기 또는 영어
