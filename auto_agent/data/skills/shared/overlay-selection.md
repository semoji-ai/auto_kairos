# 오버레이 선택 가이드

씬에 GIF/Lottie 오버레이를 추가할 때의 규칙.

## 원칙

1. 씬당 오버레이 **최대 2개** (과한 장식 방지)
2. visualization이 있는 씬에는 오버레이 **최소화** (차트 가독성 우선)
3. 감정 고조 포인트에 **집중 배치**
4. 모든 씬에 오버레이를 넣지 말 것 — 전체 씬의 30% 이하

## 태그 매칭 가이드

| 씬 감정/맥락 | 추천 태그 | 타입 |
|-------------|----------|------|
| 놀라운 통계/수치 | sparkle, exclamation | gif/lottie |
| 긍정적 결론 | checkmark, thumbsup, celebrate | lottie |
| 비교/대결 | versus, fire | gif |
| 질문/의문 | question, thinking | lottie |
| 경고/위험 | warning, alert | lottie |
| 전환/강조 | arrow, pointer | lottie |

## position 가이드

- `top-right`: 통계 강조 아이콘
- `bottom-right`: 리액션 이모지
- `center`: 전환 효과, 풀스크린 장식
- `bottom-center`: 감정 리액션

## 스키마

```json
{
  "overlays": [
    {
      "type": "lottie",
      "assetId": "arrow-up-01",
      "position": "top-right",
      "scale": 0.8,
      "enterFrame": 15
    }
  ]
}
```

## 주의사항

- `assetId`는 반드시 `public/overlays/gif/manifest.json` 또는 `public/overlays/lottie/manifest.json`에 등록된 id만 사용
- 없는 assetId를 넣으면 console.warn 후 스킵됨 (렌더 크래시 없음)
- `enterFrame` / `exitFrame`으로 등장/퇴장 타이밍 제어 (씬 내 로컬 프레임)
