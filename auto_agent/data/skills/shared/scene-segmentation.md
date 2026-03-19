---
name: scene-segmentation
description: Use when splitting manuscript narration into individual scenes with duration and transition planning
---

# Scene Segmentation

원고를 씬 단위로 분할하는 규칙을 정의합니다.
씬 경계 판단, 과밀 씬 탐지, 이미지 에셋 판단, 캐릭터 추적 규칙을 포함합니다.

**참조 에이전트**: visual-composer, write-manuscript, qa-reviewer

---

## 1. 이미지 에셋 배치 판단

대부분의 씬에 이미지를 배치하여 시각적 풍부함을 확보한다.

| 상황 | 이미지 배치 | 예시 |
|------|-----------|------|
| 수치/통계 | O (배경 이미지 + 타이포 오버레이) | 유가 차트 배경 + 숫자 |
| 개념 설명 | O (관련 이미지 배경) | 해협 사진 + 아이콘 |
| 인물 소개 | O (인물 사진, placement=left) | 트럼프 사진 |
| 역사 사건 | O (당시 사진/일러스트) | 1979년 이란 혁명 |
| 장소 소개 | **map_scene** 사용 (이미지 불필요) | 호르무즈 해협 지도 |
| 감성적 전환 | O (cinematic, 이미지만) | 폭격 장면 |
| 순수 데이터 비교 | X (타이포만으로 충분한 경우) | 국가별 수치 비교 |

**목표 비율**: 이미지 에셋 씬 = 전체의 **약 70%** (맵씬 제외)

---

## 2. 캐릭터 등장 추적

각 씬의 narration에서 등장하는 인물을 추출하여 `notes`에 기록합니다.

- 이름이 직접 언급된 인물 → `notes`에 "등장인물: 이름1, 이름2" 기록
- 같은 인물이 2씬 이상 등장 → 후속 단계(character-planner)에서 캐릭터 계획 수립
- 동일 캐릭터는 동일한 생성 이미지를 참조하여 시각적 일관성 유지

---

## 3. data_dependencies

수치/통계가 포함된 씬에서 research_report.json의 어떤 데이터가 필요한지 명시:
- `statistics.{metric_name}`
- `timeline`
- `comparisons.{index}`
- `key_figures.{name}`

---

## 4. 과밀 씬 탐지 및 분할 (필수)

하나의 씬은 **정확히 하나의 개념**만 담는다.

### 하나의 개념 정의

| atomic_unit |
|-------------|
| 하나의 수치/통계 (예: 시장 규모 150억 달러) |
| 하나의 인물 소개 (예: 수양대군의 야망) |
| 하나의 사건 (예: 김종서 암살) |
| 하나의 비교 (예: 세조실록 vs 숙종실록) |
| 하나의 인용문 + 맥락 |
| 하나의 장소/배경 묘사 |
| 하나의 인과 관계 (A → B, 단 A→B→C→D는 분할) |

### 과밀 판정 기준 (하나라도 해당하면 반드시 분할)

- 나레이션 글자 수가 **100자 초과** (범용 상한)
- 나레이션 내 전환어 1개 이상 ("한편", "그런데", "그러나", "이어서", "한 사람이 더", "반면", "동시에", "게다가", "뿐만 아니라")
- 2명 이상의 새로운 인물이 소개됨
- 시간/장소가 1회 이상 전환됨
- **시각적 연출 전환**: 질문→답변, 서스펜스→공개, 설명→지도/차트 등 화면이 바뀌어야 하는 구간

### 분할 패턴 예시 (MUST FOLLOW)

```
❌ 1씬에 질문+답변+지도:
  "전 세계 경제를 무릎 꿇릴 수 있는 곳이 어디일까요?
   월스트리트? 실리콘밸리? 아닙니다.
   지도를 펼쳐보시죠. 페르시아만과 오만만 사이, 호르무즈 해협입니다."

✅ 2씬으로 분할:
  씬 A (headline_only, suspense):
    "전 세계 경제를 무릎 꿇릴 수 있는 곳이 어디일까요?
     월스트리트? 실리콘밸리? 아닙니다."
  씬 B (mapScene, dramatic):
    "지도를 펼쳐보시죠. 페르시아만과 오만만 사이, 호르무즈 해협입니다."
```

```
❌ 1씬에 통계 3개:
  "유가 100달러가 2개월 유지되면 GDP가 0.3% 감소합니다.
   그런데 130달러가 하반기까지 이어지면 세계 경제 침체입니다.
   최악의 경우 150달러를 넘으면..."

✅ 3씬으로 분할:
  씬 A: "유가 100달러 2개월 → GDP 0.3% 감소" (counter)
  씬 B: "130달러 하반기 → 세계 경제 침체" (counter, dramatic)
  씬 C: "최악 150달러 초과 → ..." (counter, urgent)
```

```
❌ 1씬에 국가 3개 비교:
  "사우디, UAE, 이라크, 쿠웨이트. 그런데 이 나라들도
   호르무즈를 통과해야 합니다. 파이프라인 대안도..."

✅ 2씬으로 분할:
  씬 A: "사우디, UAE, 이라크, 쿠웨이트 — 수출 강자들" (items_list)
  씬 B: "그런데 이들도 호르무즈를 통과해야 합니다" (mapScene)
```

### 분할 시 시각적 연출 힌트

분할한 씬에 어떤 레이아웃이 적합한지 `notes`에 힌트를 남긴다:
- 질문/서스펜스 → `notes: "headline_only 또는 cinematic 추천"`
- 지도/위치 공개 → `notes: "mapScene 추천"`
- 통계 하나 → `notes: "counter 또는 metric_spotlight 추천"`
- 나열 → `notes: "items_list 또는 items_grid 추천"`
- 비교 → `notes: "split 또는 before_after 추천"`

### 과밀 씬 처리

1. 전환어/인물/시간/시각적 전환 기준으로 **분할점** 탐지
2. `scene_number` 재번호 매기기 (1부터 연속)
3. `notes`에 "원본 씬 N에서 분할됨" + 레이아웃 힌트 기록
4. **분할 후 각 씬이 100자 이내인지 재확인** — 초과 시 추가 분할

### density_check 출력 포맷

```json
{
  "density_check": {
    "scenes_split": 5,
    "original_scene_count": 38,
    "final_scene_count": 55,
    "split_details": [
      {
        "original_scene": 21,
        "split_into": [25, 26, 27],
        "reason": "전환어 3개 + 시간/장소 전환 2회"
      }
    ]
  }
}
```

---

## 5. estimated_duration_sec 계산

나레이션 글자 수 기반으로 산출합니다. 한국어 기준 초당 약 5-6자.

```
estimated_duration_sec = narration_char_count / 5
최소: 4초
최대: 20초
```

---

## 6. scene_decomposition.json 출력 스키마

```json
{
  "total_scenes": 35,
  "total_chapters": 6,
  "image_scene_count": 5,
  "image_ratio": 0.14,
  "scenes": [
    {
      "scene_number": 1,
      "chapter": 1,
      "title": "씬 제목",
      "narration": "나레이션 텍스트 전문",
      "narration_char_count": 45,
      "estimated_duration_sec": 5,
      "has_image_asset": false,
      "image_asset": null,
      "data_dependencies": [],
      "notes": "챕터 1 시작. 등장인물: 단종"
    }
  ],
  "density_check": { ... }
}
```

---

## 7. 아트스타일별 오버라이드

`art_style.json`의 스타일에 따라 과밀 씬 기준이 달라집니다.

| art_style | 글자 수 상한 | 개념 수 | 전환어 분할 |
|-----------|-----------|---------|-----------|
| 기본 (모든 스타일) | 100자 | 1개 | 전환어 등장 시 분할 |
| `quirky_cartoon` (이로미즘) | **80자** (0~2문장) | **1개** | **전환어 등장 시 무조건 분할** |

quirky_cartoon(이로미즘)은 시네마틱 70% 스타일 — 한 씬 = 한 장면 = 한 이미지.
나레이션은 짧게, 그림이 전달. 상세 규칙은 `shared/writing-style-iromism.md` 5번 참조.

---

## 주의사항

- Phase 1은 **순수 분할**만 수행. 씬 분류나 시각 연출 결정은 하지 않는다
- 시각적 연출 결정(creative 필드)은 Phase 2 Creative Direction에서 수행
- 나레이션 텍스트는 원고의 것을 그대로 보존 (수정 금지)
- 원고에는 VIZ/IMG 마커가 없음 — `## Scene N:` 헤더를 씬 경계로 사용
- vizType/이미지 결정은 Phase 2(visual-composer) + Phase 2.5(asset-advisory)에서 수행
