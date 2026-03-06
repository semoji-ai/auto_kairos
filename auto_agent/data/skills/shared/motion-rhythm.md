# Motion Rhythm

전체 영상의 전환 효과, 타이밍, 시각적 리듬, 브리딩 포인트 규칙을 정의합니다.
Remotion TransitionSeries 기반 motion_plan.json 생성 규칙을 포함합니다.

**참조 에이전트**: visual-composer, qa-reviewer

---

## 1. 전환 패턴 — 단조로움 방지

```
규칙: 같은 전환 타입 3회 연속 금지

좋은 예: fade → slide → fade → wipe → fade → slide
나쁜 예: fade → fade → fade → slide

전환 타입별 용도:
  fade  — 기본. 자연스러운 전환 (60% 사용)
  slide — 새로운 정보 등장, 에너지 (25% 사용)
  wipe  — 강조, 대비 효과 (15% 사용)
```

---

## 2. 페이싱 — 정보 밀도별 시간 조절

| 씬 특성 | duration_frames | 이유 |
|---------|----------------|------|
| 데이터 차트 (bar, line, pie) | 300-450 | 수치 이해 시간 |
| 아이콘 그리드/흐름도 | 240-360 | 항목 순차 등장 |
| 인용문/강조 | 180-270 | 짧지만 임팩트 |
| 타이틀 카드 | 120-180 | 빠른 전환 |
| 브리딩 포인트 | 120-150 | 쉬는 시간 |

---

## 3. 시각적 리듬 — 강약 곡선

```
Act 1 (도입):  ──────    낮은 강도, 느린 전환
Act 2 (전개):  ──▲──▼──  강약 교차, 데이터→스토리 반복
               ──▲▲──   클라이맥스 구간
Act 3 (결말):  ──────    다시 낮은 강도, 여운
```

---

## 4. 브리딩 포인트

```
3-5개 씬마다 1회 삽입:
  ├─ narration_only 씬 (시각 요소 없이 여운)
  ├─ quote_card (잠시 멈춤, 인용)
  └─ text_highlight (핵심 한 줄)

조건:
  ├─ 데이터 씬(차트) 2-3개 연속 후 반드시 삽입
  └─ 챕터 전환 직전에 삽입 권장
```

---

## 5. internal_timing

각 씬 내부의 콘텐츠 타이밍:

```
content_start: transition_in 완료 후 프레임
content_end:   transition_out 시작 전 프레임
hold_duration: 콘텐츠가 완전히 보이는 시간

규칙:
  hold_duration >= 90 프레임 (3초)  ← 최소 정보 체류 시간
  차트/데이터 씬: hold_duration >= 150 프레임 (5초)
```

---

## 6. 같은 씬 타입 연속 감지

scene_type이 연속될 경우 rhythm_analysis.warnings에 기록:

```json
{
  "warnings": [
    {
      "type": "consecutive_same_type",
      "scenes": [8, 9],
      "scene_type": "bar_chart",
      "suggestion": "씬 8-9 사이에 text_highlight 삽입 권장"
    }
  ]
}
```

---

## 7. motion_plan.json 출력 스키마

```json
{
  "total_duration_frames": 10800,
  "total_duration_sec": 360,
  "fps": 30,
  "transition_series": [
    {
      "scene_number": 1,
      "scene_type": "title_card",
      "duration_frames": 150,
      "transition_in": {
        "type": "fade",
        "duration_frames": 15,
        "params": {}
      },
      "transition_out": {
        "type": "slide",
        "duration_frames": 12,
        "params": { "direction": "left" }
      },
      "internal_timing": {
        "content_start": 15,
        "content_end": 135,
        "hold_duration": 120
      }
    }
  ],
  "rhythm_analysis": {
    "avg_scene_duration_sec": 10.3,
    "breathing_points": [8, 15, 23, 30],
    "intensity_curve": [
      {"scene_range": [1, 5], "intensity": "low", "note": "도입부, 느린 진입"},
      {"scene_range": [6, 12], "intensity": "medium", "note": "정보 전달 시작"},
      {"scene_range": [13, 18], "intensity": "high", "note": "핵심 데이터, 빠른 전환"},
      {"scene_range": [19, 22], "intensity": "low", "note": "브리딩 포인트"},
      {"scene_range": [23, 30], "intensity": "high", "note": "클라이맥스"},
      {"scene_range": [31, 35], "intensity": "low", "note": "마무리, 여운"}
    ]
  },
  "global_settings": {
    "default_spring": { "damping": 200, "stiffness": 100 },
    "min_scene_duration_frames": 120,
    "max_scene_duration_frames": 600,
    "transition_overlap_frames": 15
  }
}
```

---

## 주의사항

- scene_specs.json의 씬 순서는 변경하지 않는다 (순서 제안만)
- spring 설정: damping 최소 150, 바운스 없이 부드럽게
- 전체 재생 시간: 목표 ±10% 이내
- transition_overlap_frames는 TransitionSeries의 오버랩 시간
