---
name: direction-semoji
description: 세모지 연출 규칙 — 데이터 레이아웃 선택, imageAsset 2단계 구조, 매니페스트 우선순위. 씬분할 단계에서 적용한다.
---

# Direction — 세모지 (연출)

씬에 layout과 imageAsset을 배정하는 규칙입니다. **원고 작가는 이 스킬을 쓰지 않습니다** —
씬분할(`step_2`) 이후 단계의 것입니다.

> 구성은 `narrative-semoji`, 문체는 `voice-semoji`.

> **⚠️ 조건부 적용**: `writing_style`이 `semoji`일 때만 적용합니다.

---

## 1. 세모지 연출 규칙 (Layout + 이미지)

### 데이터 시각화 적극 활용
세모지는 **수치와 팩트 중심** 채널이다. 모든 챕터에 최소 1개 이상의 데이터 레이아웃을 포함한다.

| Layout | 용도 | 필수 데이터 |
|--------|------|-----------|
| `items_list` | 리스트형 정보 나열 | items 배열 |
| `counter` | 핵심 숫자 강조 (매출, 성장률) | values + unit |
| `icon_stat` | 아이콘 + 수치 조합 | items + values + icon |
| `bar` / `pie` | 비교/비중 차트 | items + values + unit |
| `before_after` | 변화 비교 (인수 전/후) | items(2개) + values(2개) |
| `metric_wall` | 핵심 지표 모아보기 | items + values 복수 |
| `timeline` | 시간순 사건 나열 | items(연도+사건) |

### 이미지 연출 — 2단계 구조 (기본 연출 100% + 우선순위 배정)

**⚠️ 1단계: 모든 씬에 `imageAsset.prompt` (장면 연출) 작성 = 100% 필수**

어떤 레이아웃이든 상관없이, 모든 씬에 `imageAsset.prompt`로 해당 장면의 시각적 묘사를 작성한다.
데이터 씬이어도, 클로징 씬이어도, "이 장면을 이미지로 그린다면 어떤 장면인가"를 작성한다.

```json
// 데이터 씬이어도 장면 연출 작성
{
  "layout": "bar",
  "items": ["2021년", "2022년", "2023년"],
  "values": [30, 413, 1396],
  "imageAsset": {
    "source": "generate",
    "prompt": "가파르게 상승하는 매출 그래프 앞에서 자신감 있게 서 있는 30대 한국 남성 CEO",
    "placement": "background"
  }
}
```

**2단계: 매니페스트 반영 우선순위 배정**

모든 씬에 장면 연출이 있지만, 최종 영상에서는 씬 성격에 맞는 방식이 우선된다:

| 씬 성격 | 최종 반영 우선순위 | imageAsset 역할 |
|---------|-----------------|----------------|
| cinematic (감성/전환) | **이미지 생성 우선** | fullscreen |
| 인물 등장 | **이미지 생성/검색 우선** | fullscreen 또는 side |
| 데이터 (bar/counter/items) | **데이터 레이아웃 우선** | background (배경으로 깔림) |
| 맵씬 | **지도 우선** | background |
| headline_only | **텍스트 우선** | background (있으면 깔림) |

→ 사용자가 대시보드에서 우선순위를 전환할 수 있음 (이미지 생성 ↔ 데이터 레이아웃)

**imageAsset.source 선택 기준:**
- `search`: 실존 인물, 브랜드 로고, 실제 제품, 실제 건물/장소
- `generate`: 역사적 장면 재현, 추상적 개념, 분위기 이미지, 캐릭터 등장 장면

### 파이프라인 처리
- **TTS**: `korean_tts_preprocessor.py`가 `**` 마커를 자동 제거 → 자막에 포함 안 됨
- **visual-composer**: 볼드 문장 감지 → `emphasis: "keyword"`, `reveal: "dramatic_pause"` 등 극적 연출 적용
- **원고 작가는 볼드만 쓰면 됨** — 나머지는 파이프라인이 처리

---
