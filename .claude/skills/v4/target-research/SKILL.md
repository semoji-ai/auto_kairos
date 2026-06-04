---
name: target-research
description: 좁고 깊은 타겟 퀘스쳔에 대해 답변을 만들어 질문별 아티팩트로 저장. wiki의 open_question도 직접 입력으로 받을 수 있음.
---

# target-research

## Reads
- (선택) `wiki/*.md` — open_question을 입력으로 가져올 수 있음
- (선택) `research_reports/*.md`, 기존 `research_targeted/*.md` — 이미 답이 있는지 먼저 확인
- (선택) `pd_notebook.md` — 기획 의도 참고만

## Writes
- `research_targeted/{question_slug}.md`

## Input resolution
1. **Brief 필수**: 질문 리스트 + 각 질문의 짧은 맥락
2. **Vault 우선 검색**: 각 질문에 대해 `vault-search`로 기존 답변 후보 확인. 충분하면 외부 경로 normalize로 가져와 새 리서치 생략
3. **Wiki open_question 인입**: brief에 `from_wiki: <slug>` 형태로 토픽을 지정하면 해당 wiki 파일의 Open Questions 섹션을 자동 로드
4. **외부 답변 normalize**: brief에 이미 답변 자료(또는 vault 경로)가 있으면 normalize 후 저장만
5. **실패**: 질문이 비어 있으면 종료

## 실행 절차

1. 각 질문에 대해 기존 자료(wiki, research_reports, research_targeted)에서 충분히 답할 수 있는지 먼저 확인. 가능하면 출처 인용한 짧은 답변으로 작성하고 `source: existing` 표시
2. 부족한 질문만 새 리서치 수행
3. 답변 포맷: 요약 → 근거 → 출처. frontmatter:
   ```yaml
   ---
   question: <원문>
   slug: <slug>
   source: existing | new
   from_wiki: <slug>          # 해당하면
   wiki_question_id: <Q1>     # 해당하면
   ---
   ```
4. 200~400단어 요약과 decisions(답을 못 찾은 질문, 신뢰도 낮은 답)을 반환

## 금지
- `pd_notebook.md`, `wiki/`, `drafts/` 수정

## 한국어 작성 규칙
- 가타카나/히라가나/한자 금지
