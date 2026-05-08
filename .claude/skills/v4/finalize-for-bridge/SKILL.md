---
name: finalize-for-bridge
description: 원고 확정 단계에서 PD가 v3 Stage 3 인계용 산출물을 직접 작성하도록 안내. final_manuscript_marked.md + outline.json 양식 + 무결성 규칙.
---

# finalize-for-bridge

`review-draft` 래칫이 종료되고 fact-check + proofread를 통과한 `final_manuscript.md`가 확정된 다음 단계. PD가 v3 어댑터 호출 전에 두 파일을 직접 작성한다.

## Reads
- `final_manuscript.md` (확정본)
- `plan.md` — 챕터 구조 결정·톤
- `pd_notebook.md` — 캐릭터 ID, 결정 로그
- `wiki/characters/*` (있으면) — 캐릭터 ID

## Writes
- `final_manuscript_marked.md` — final_manuscript.md에 마커 삽입한 사본
- `outline.json` — 챕터 메타데이터 (v3 스키마)

## final_manuscript_marked.md 규칙

원본 `final_manuscript.md`의 본문(narration)을 한 글자도 수정하지 않고, 다음 마커만 삽입한다:

1. **챕터 시작**: `# Ch N. <챕터 제목>` 라인 (N=1부터)
2. **씬 경계**: 8~15초 분량(약 60~120자) 단위에 `---` 라인. 의미 단위가 자연스럽게 끊기는 곳.
3. **캐릭터 등장**: 해당 단락 직전에 `<!-- chars: ID1, ID2 -->` 주석. 캐릭터 ID는 `wiki/characters/` 또는 `pd_notebook.md`에 기록된 ID.

**무결성:** 마커·주석·공백을 제거하면 `final_manuscript.md`의 본문이 그대로 substring으로 들어 있어야 한다. v3 step_2 hook이 자동 검증한다.

## outline.json 규칙

`auto_agent/modules/v4_bridge/schema_samples/outline.example.json` 의 키 구조 그대로 작성:

- `title` (str) — 영상 제목
- `core_question` (str) — plan.md의 핵심 질문
- `target_duration_minutes` (number)
- `chapters[]` 각 항목:
  - `chapter_number` (1부터 연속)
  - `title` (final_manuscript_marked.md의 `# Ch N.` 와 일치)
  - `act` (1~3, 3막 구조 위치)
  - `purpose` (이 챕터가 영상에서 하는 일 한 문장)
  - `duration_ratio` (이 챕터의 분량 비율, 합 1.0)
  - `research_focus[]` (이 챕터가 다루는 리서치 토픽 라벨)
  - `key_points[]` (이 챕터의 핵심 메시지 항목)

## 절차

1. `final_manuscript.md` Read → 챕터 경계와 씬 경계 식별
2. `pd_notebook.md`에서 챕터별 결정·캐릭터 ID 회수
3. `final_manuscript_marked.md` Write — 본문 그대로 + 마커 삽입
4. `outline.json` Write — 위 스키마 그대로
5. PD에게 양식 점검 요청 (특히 챕터 제목 일치, duration_ratio 합)

## 금지
- final_manuscript.md 본문 변경
- outline.json에 v3 스키마 외 키 추가 (다른 키는 step_2가 무시할 뿐 아니라 review에서 노이즈)

## 한국어 작성 규칙
- 가타카나/히라가나/한자 금지
- 외래어는 한글 표기 또는 영어
