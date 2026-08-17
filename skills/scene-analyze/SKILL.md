---
name: scene-analyze
description: 이미 분할된 씬별 내레이션을 읽고, 각 씬의 시각 연출만 결정한다 (내레이션 재작성 금지)
---

# Scene Analyze (씬 연출 결정)

## 이 스킬의 임무

씬 경계는 **이미 결정되어 있습니다**. 프롬프트에 번호가 매겨진 씬별 내레이션 목록이 주입됩니다.
당신은 **글을 쓰지 않고, 씬 경계도 새로 판단하지 않습니다**. 각 씬에 대해 오직 **연출만** 결정합니다.

### 절대 규칙

- **내레이션을 절대 재작성하지 마세요.** 한 글자도 바꾸지 말고, 출력에 내레이션을 포함하지도 마세요.
- 입력으로 받은 씬 **개수와 순서를 그대로 보존**합니다. 합치거나 쪼개거나 추가하지 마세요.
- 씬 N개를 받으면 연출도 N개를 같은 순서로 출력합니다.

## 해야 할 일

주입된 씬별 내레이션 목록을 순서대로 읽고, 각 씬마다 아래 여섯 가지를 결정합니다.

1. **visual_summary** — 이 씬을 한 줄로 요약한 시각 설명 (무엇을 화면에 보여줄지)
2. **image_prompt** — 이미지 생성용 묘사 (장면/인물/장소/사물/분위기를 구체적으로)
   - 내레이션에 인물이 행위·발언하는 씬이면 그 인물을 묘사에 포함
3. **characters** — 이 씬에 등장하는 인물 이름 배열
   - 인물이 행위·발언하는 씬에만 (대명사로 지칭되는 씬 포함). 등장 인물이 없는 씬(데이터/개념/전환)은 `[]`
   - 동일 인물은 전체에서 동일 문자열로 표기 (1글자라도 다르면 별개로 인식됨)
4. **layout** — (선택) 아래 중 하나를 제안
5. **asset_source** — `"search"` 또는 `"generate"` (아래 분류 기준 참고)
6. **search_query** — asset_source가 `"search"`일 때 실물을 찾을 구체 검색어 (generate일 때는 빈 문자열 또는 생략)
   - `headline_only` — 핵심 메시지 한 줄 강조 (텍스트만)
   - `items_list` — 항목 나열
   - `metric_spotlight` — 단일 수치 강조
   - `quote` — 인용문 + 인물
   - `map` — 지리적 위치 비교가 본질일 때 (위치가 subject)
   - `cinematic` — 분위기 전환·도입·여운 (이미지 중심)

### layout 판단 메모

- 수치 1개 강조 → `metric_spotlight`, 발언 인용 → `quote`, 도입·여운·전환 → `cinematic`
- `map`은 **위치 자체가 핵심**일 때만 (위치를 제거하면 씬 의미가 무너질 때). 단순히 지명이 언급된 정도면 `cinematic` 또는 일반 이미지로 두세요.
- 확신이 없으면 layout을 생략하세요.

## 실사 자료(search) vs AI 생성(generate) 분류

각 씬에 asset_source와 search_query를 함께 출력한다.
- **search(실사 검색)**: 특허·문서, 역사 인물 사진, 실존 제품·로고·장소, 통계 그래프 등 **실재하는 구체물**이 화면의 핵심일 때. search_query에 그 실물을 찾을 구체 검색어를 적는다(예: "US 3691140 patent document", "Spencer Silver 3M scientist").
- **generate(AI 생성)**: 추상 서사·감정·은유·세모지 일러스트 톤 장면.
- 목표: 실재 구체물이 중심인 씬은 적극적으로 search로(대략 전체의 40~50%까지). 애매하면 generate.

## editorial brief 활용

프롬프트에 editorial brief가 있으면 주제·톤·핵심 앵글을 참고해 연출 방향을 잡습니다.
brief의 의도와 어긋나는 연출은 피하세요.

## 출력 형식

오직 아래 JSON만 출력합니다. 입력 씬과 **같은 개수·순서**이며, **narration은 포함하지 않습니다**.

```json
{
  "scenes": [
    {
      "visual_summary": "실존 인물의 역사적 순간",
      "image_prompt": "black and white archival photo of a scientist in a lab coat",
      "characters": ["Spencer Silver"],
      "layout": "cinematic",
      "asset_source": "search",
      "search_query": "Spencer Silver 3M scientist Post-it inventor",
      "shot_relation": "cut",
      "location": "3M 연구실",
      "props": ["접착제", "실험 노트"]
    },
    {
      "visual_summary": "아이디어가 세상으로 퍼져나가는 추상 장면",
      "image_prompt": "abstract illustration of glowing ideas spreading across a dark background",
      "characters": [],
      "layout": "cinematic",
      "asset_source": "generate",
      "search_query": "",
      "shot_relation": "continue",
      "location": "",
      "props": []
    }
  ]
}
```

## 씬 연결성(shot_relation)과 엔티티 태그

각 씬에 shot_relation, location, props도 함께 출력한다.
- **shot_relation**: 이 씬이 이전 씬과 어떤 관계인가.
  - "continue"(연결): 이전 씬과 **시각적으로 이어지는** 장면 — 같은 공간/상황이 카메라 이동·줌으로 연속(특히 cinematic을 한 장면에 걸쳐 연출할 때).
  - "cut"(전환): 시간·장소·소재가 달라진 **새 시퀀스**. **첫 씬은 항상 cut**. headline/items/quote/metric 같은 카드형은 대개 cut.
- **location**: 이 씬의 장소·배경을 짧게(예: "3M 연구실", "교회 성가대석"). 없으면 빈 문자열.
- **props**: 이 씬의 핵심 소품·사물 배열(예: ["포스트잇", "특허 문서"]). 없으면 빈 배열.

## 금지

- 내레이션 재작성·복사·추가
- 입력과 다른 씬 개수·순서
- narration 필드 출력
- 위 layout 목록 밖의 값
- asset_source에 "generate"/"search" 외 값
