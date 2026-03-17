---
name: outline-template
description: Use when structuring video outlines with chapter organization and narrative arc design
---

# Outline Template

3막 구조의 영상 아웃라인 설계 규칙을 정의합니다.
챕터 설계, 씬 힌트 원칙, duration_ratio, outline.json 스키마를 포함합니다.

**참조 에이전트**: write-manuscript

---

## 1. 3막 구조

```
Act 1 (도입) — 전체의 15-20%
  ├─ 후킹: 충격적 수치, 질문, 일화로 시작
  ├─ 문제 제기: 왜 이 주제가 중요한지
  └─ 로드맵: 영상에서 다룰 내용 예고

Act 2 (전개) — 전체의 60-70%
  ├─ 에피소드 중심 구성 (사건/사례 기반)
  ├─ 데이터 시각화 교차 배치
  ├─ 인물 인용으로 신뢰감
  └─ 비교/대조로 이해도 상승

Act 3 (결말) — 전체의 15-20%
  ├─ 핵심 정리 (numbered_list or icon_grid)
  ├─ 미래 전망
  └─ 행동 촉구 또는 여운
```

---

## 2. 씬 타입 힌트 원칙

1. **같은 타입 연속 금지**: bar_chart 다음에 또 bar_chart 배치하지 않기
2. **데이터 씬과 텍스트 씬 교차**: 정보 과부하 방지
3. **챕터 시작은 title_card**: 시각적 구분감
4. **이미지 씬은 전략적**: 전체 씬의 30% 이하. 실존 인물/제품/장소에만
5. **브리딩 포인트**: 3-4개 씬마다 한 번 여유 씬(quote_card, narration_only)

---

## 3. 씬 힌트 세분화 원칙 (필수)

각 scene_hint는 **정확히 하나의 개념**만 담는다. `scene-segmentation` 스킬의 과밀 씬 정의 참조.

- "인물 소개 + 사건 전개"를 하나의 hint로 쓰지 않는다
- key_points의 각 항목이 별도의 scene_hint가 되어야 한다
- 챕터당 scene_hints 수 = key_points 수 x 1.5~2

잘못된 예:
```json
"scene_hints": [
  { "type": "icon_grid", "note": "수양대군과 세 심복 소개 + 거사 준비 + 김종서 표적" }
]
```

올바른 예:
```json
"scene_hints": [
  { "type": "icon_grid", "note": "수양대군의 세 심복 (한명회, 권람, 신숙주)" },
  { "type": "text_highlight", "note": "1년간의 거사 준비" },
  { "type": "narration_only", "note": "칼끝이 향한 대상 — 좌의정 김종서" }
]
```

---

## 4. 씬 힌트 참고 (아웃라인용)

아래는 scene_hints에서 사용할 수 있는 **시각화 힌트**입니다. 렌더러 타입이 아니며, visual-composer가 creative 필드를 설계할 때 참고하는 의도 표현입니다.

```
타이틀/텍스트: title_card, text_highlight, quote_card
데이터 시각화: bar_chart, line_chart, pie_chart, timeline, table_view
비교/구조:    compare_card, list_card, numbered_list, diagram
아이콘 조합:  icon_grid, icon_stat
특수:         narration_only, image_scene
```

---

## 5. 목표 분량 기반 챕터 설계 (필수)

목표 분량에 따라 챕터 수와 챕터별 분량을 동적으로 결정합니다.

### 5.1 기본 공식

```
1분 영상 ≈ 나레이션 500자
목표 분량(자) ÷ 500 = 예상 영상 길이(분)
```

### 5.2 챕터 수 가이드

| 목표 분량 | 영상 길이 | 챕터 수 | 챕터당 분량 |
|----------|:-------:|:------:|-----------|
| ~500자 | ~1분 | 1 | 500자 |
| ~3,000자 | ~6분 | 4~5 | 500~800자 |
| ~5,000자 | ~10분 | 6~8 | 500~1000자 |
| ~10,000자 | ~20분 | 10~14 | 500~1300자 |
| ~15,000자 | ~30분 | 15~20 | 500~1300자 |

### 5.3 챕터 분량 규칙

- **최소 500자**: 이보다 짧으면 인접 챕터와 합침
- **최대 1300자**: 이보다 길면 서브 주제 기준으로 분할
- **내용 풍성함에 따라 유동 배분**: 에피소드/데이터가 풍부한 챕터는 길게, 단순 설명은 짧게
- **1챕터 = 1서브 주제**: 여러 주제를 뭉뚱그리지 않음

### 5.4 씬 수 추정

```
챕터 분량(자) ÷ 100~130 = 챕터 내 씬 수
전체 씬 수 = 각 챕터 씬 수의 합
```

예: 10,000자 원고 → 12챕터 → 챕터당 5~10씬 → 총 70~100씬

---

## 5.5 duration_ratio 가이드

- 전체 합은 1.0
- 각 챕터의 ratio = 해당 챕터 목표 글자수 ÷ 전체 목표 분량
- Act 2의 가장 중요한 챕터에 가장 큰 비율 배정

---

## 6. image_scenes 판단 기준

이미지 에셋이 정보 전달을 극대화하는 경우에만:
- 실존 인물 소개 → wikimedia 우선
- 제품/서비스 시연 → search
- 역사적 장면 → wikimedia 우선
- 추상적 분위기 → generate (최후 수단)

---

## 7. outline.json 출력 스키마

```json
{
  "title": "영상 제목",
  "estimated_duration_sec": 600,
  "total_scenes_estimate": 35,
  "structure": {
    "act_1": "도입 (관심 유발, 문제 제기)",
    "act_2": "전개 (핵심 정보, 에피소드, 데이터)",
    "act_3": "결말 (정리, 전망, 행동 촉구)"
  },
  "chapters": [
    {
      "chapter_number": 1,
      "title": "챕터 제목",
      "act": 1,
      "purpose": "이 챕터의 역할/목적",
      "duration_ratio": 0.15,
      "key_points": ["핵심 포인트 1", "핵심 포인트 2"],
      "episodes": ["episode_id_1", "episode_id_2"],
      "scene_hints": [
        {
          "type": "title_card",
          "icon": "Brain",
          "note": "챕터 시작. AI 에이전트 주제 소개"
        }
      ],
      "image_scenes": [
        {
          "type": "image_scene",
          "subject": "인물/제품/장소",
          "reason": "왜 이미지가 필요한지",
          "source_hint": "wikimedia | search | generate"
        }
      ]
    }
  ],
  "flow_notes": {
    "hooks": "도입부 후킹 전략 설명",
    "pacing": "정보 밀도 조절 전략",
    "transitions": "챕터 간 연결 전략"
  }
}
```

---

## 주의사항

- research_report.json의 episodes와 매칭하여 누락된 에피소드가 없는지 확인
- scene_hints의 icon 필드는 반드시 Lucide React에 존재하는 아이콘명 사용
- 챕터 수: 목표 분량에 따라 동적 결정 (§5.2 참조)
- 챕터당 분량: 500~1300자 범위 (§5.3 참조)
- 총 씬 수 예측: 챕터별 분량 기반 자동 산출 (§5.4 참조)
