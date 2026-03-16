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

이미지가 **정보 전달을 극대화**하는 경우에만 `has_image_asset: true`:

| 상황 | Remotion 컴포넌트로 충분 | + 이미지 에셋 필요 |
|------|----------------------|------------------|
| 수치/통계 | O (차트/숫자) | X |
| 개념 설명 | O (아이콘) | X |
| 인물 소개 | 실루엣/배지 | O (인물 사진) |
| 제품 소개 | 아이콘+설명 | O (스크린샷) |
| 역사 사건 | 타임라인 | O (당시 사진) |
| 장소 소개 | **map_scene** 사용 | X (지도 자체가 시각화) |
| 감성적 시각화 | 패턴 배경 | 검색/생성 배경 |

**목표 비율**: 이미지 에셋 씬 ≤ 전체의 30%

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

### 과밀 판정 기준 (하나라도 해당하면 과밀)

- 나레이션 글자 수가 **100자 초과** (범용 상한)
- 나레이션 내 전환어 2개 이상 ("한편", "그런데", "그러나", "이어서", "한 사람이 더")
- 2명 이상의 새로운 인물이 소개됨
- 시간/장소가 1회 이상 전환됨

### 과밀 씬 처리

1. 전환어/인물/시간 기준으로 **분할점** 탐지
2. `scene_number` 재번호 매기기 (1부터 연속)
3. `notes`에 "원본 씬 N에서 분할됨" 기록

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
| `quirky_cartoon` (이로미즘) | **250자** | **1~2개** | 서사 흐름 내 전환어 유지 가능 |

quirky_cartoon 적용 시 상세 규칙은 `shared/writing-style-iromism.md` 5번 참조.

---

## 주의사항

- Phase 1은 **순수 분할**만 수행. 씬 분류나 시각 연출 결정은 하지 않는다
- 시각적 연출 결정(creative 필드)은 Phase 2 Creative Direction에서 수행
- 나레이션 텍스트는 원고의 것을 그대로 보존 (수정 금지)
- 원고에는 VIZ/IMG 마커가 없음 — `## Scene N:` 헤더를 씬 경계로 사용
- vizType/이미지 결정은 Phase 2(visual-composer) + Phase 2.5(asset-advisory)에서 수행
