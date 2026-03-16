---
name: asset-advisory
description: Use when deciding image placement, chart type, icon/logo selection, and layout for each scene through multi-perspective advisory
---

# Asset Advisory 스킬

## 목적
씬의 나레이션, 데이터 구조, research_report.json을 분석하여 **텍스트 외 시각 에셋**(차트, 아이콘, 국기, 로고, 이미지)을 추천하고 scene_specs.json에 반영하는 규칙.

> 이 스킬은 visual-composer의 **Phase 2.5**에서 실행된다.
> Phase 2 (Creative Direction)에서 설계된 creative 필드를 **보강**하는 역할이며, 기존 creative 필드를 덮어쓰지 않는다.

---

## 1. 다중 관점 심의 (Multi-Perspective Deliberation)

### 왜 순차 처리가 아닌가

기존 순차 방식(차트→아이콘→국기→로고→이미지→배치→검증)은 **선점 문제**를 일으킨다:
- 차트가 먼저 배정되면 이미지가 자동 제외됨
- 로고로 결정되면 아이콘이 열외됨
- 실제로는 차트+배경이미지, 로고+아이콘 조합이 더 효과적일 수 있음

### 심의 프로세스

**각 씬에 대해 4개 관점으로 독립 분석 → 상호 검토 → 최적 조합 결정**

```
Phase 2 출력 (scene_specs.json)
    ↓
[Step 1] 씬 스캔 — 나레이션 + items + values + creative 분석
    ↓
[Step 2] 4개 관점 독립 제안
    ├─ 📊 차트 관점: "이 데이터는 pie/line/bar로 표현하면 효과적"
    ├─ 🏷️ 심볼 관점: "이 items에는 아이콘/국기/로고가 적합"
    ├─ 🖼️ 이미지 관점: "이 씬에는 배경/사이드 이미지가 필요"
    └─ 📐 레이아웃 관점: "데이터 밀도와 공간을 고려하면..."
    ↓
[Step 3] 상호 검토 — 각 제안을 비교하며 조합 평가
    "차트가 핵심이지만, 배경이미지(opacity 0.15)가 분위기를 살린다"
    "로고보다 아이콘+값 조합이 이 씬의 비교 의도에 더 맞다"
    ↓
[Step 4] 최종 합의 — 에셋 조합 확정 + creative.layout 결정
    📐 레이아웃 관점이 "시청자가 기억해야 할 것"을 기준으로 layout 확정
    기본 11개는 layout 생략 가능, 확장 13개는 반드시 layout 직접 지정
    ↓
[Step 5] 전체 영상 밸런스 검증
    ↓
Phase 3 입력 (scene_specs.json 업데이트, creative.layout 포함)
```

---

## 4. 아이템별 이미지 (images 배열)

items 각각에 대응하는 이미지를 `images` 배열로 설정하면, 렌더러가 `ImageBadge`(원형 이미지)로 표시한다.

### 적합한 상황

| 상황 | 예시 |
|------|------|
| items가 인물 목록 | 워런 버핏, 피터 린치, 잭 보글 → 각각 인물 사진 |
| items가 제품/건물/장소 | NYSE, NASDAQ → 각각 건물 이미지 |
| emphasis="person" + items 2개+ | 인물 카드 형태로 렌더링 |

### 사용 규칙

- `images` 배열 길이 = `items` 배열 길이 (1:1 대응)
- 이미지가 없는 항목은 `null` → CircleBadge(번호) 폴백
- 이미지 파일은 step_8b에서 `images/item_sceneNNN_N.png`로 생성
- `itemIcons`와 `images`가 동시에 있으면 `images` 우선

### scene_specs 반영

```json
{
  "visualization": {
    "items": ["워런 버핏", "피터 린치", "잭 보글"],
    "images": [null, null, null],
    "emphasis": "person"
  },
  "imageAsset": {
    "source": "wikimedia",
    "query": "Warren Buffett, Peter Lynch, Jack Bogle portraits",
    "itemImages": true
  }
}
```

> `imageAsset.itemImages: true`이면 이미지 생성 스크립트가 items 각각에 대해 개별 이미지를 검색/생성하고 `images` 배열을 채운다.

---

## 5. Step 5: 전체 영상 밸런스 검증

모든 씬의 에셋 결정이 끝난 후, 전체 영상 수준에서 검증한다.

### 다양성 검증

- 연속 3씬 이상 같은 에셋 유형(차트만, 아이콘만) 반복 금지
- 연속 2씬 이상 시각 에셋 없는 씬 → 반드시 이미지 추가
- 전체 씬의 **70~90%**에 시각 에셋(이미지/차트/로고/아이콘 중 하나 이상) 존재

### 조합 밸런스

- 차트 씬: 전체의 15~30% (데이터 영상 기준)
- 이미지 씬: 전체의 40~60%
- 아이콘만 씬: 전체의 20~40%
- 에셋 없는 씬: TitleCard, 전환 씬 등 구조적 역할에만 허용

### 공존 조합 가이드

| 조합 | 허용 여부 | 조건 |
|------|----------|------|
| 차트 + 배경이미지 | ✅ | opacity ≤ 0.18, 차트 가독성 우선 |
| 차트 + 아이콘 | ✅ | 차트 외 영역에 보조 아이콘 |
| 차트 + 사이드 이미지 | ✅ | 차트 축소 + 이미지 left/right |
| 로고그리드 + 배경이미지 | ✅ | opacity ≤ 0.18, 로고 가독성 우선 |
| 아이콘 + 배경이미지 | ✅ | 아이콘 밀도에 따라 opacity 조절 |
| 아이콘 + 사이드 이미지 | ✅ | 이미지 반대쪽에 아이콘 리스트 |
| 국기 + 차트 | ✅ | 차트 레이블/범례에 국기 배지 |
| 국기 + 아이콘 (같은 항목) | ⚠️ | 해당 씬에서 더 효과적인 쪽 선택 |
| mapScene + 이미지 | ❌ | 지도가 전체 배경, 중복됨 |
