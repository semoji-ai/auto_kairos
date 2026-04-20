---
tags: [error, remotion, chart]
date: 2026-03-17
severity: major
pipeline-step: step_6b, render
agent: visual-composer
status: resolved
recurrence: 0
---

# chartConfig가 있어도 차트 레이아웃으로 안 잡힘

## 증상
scene_specs에 chartConfig(pie/line/bar)가 5개 있고, 매니페스트에도 정상 전달되지만, Remotion에서 차트가 아닌 items_list 등으로 렌더됨.

## 원인
`CreativeScene.tsx`의 `resolveLayout(data, creative)` 함수에서:
- `data` = visualization 객체 (chartConfig **있음**)
- `creative` = visualization.creative 객체 (chartConfig **없음**)
- 148행: `creative.chartConfig?.type` → 항상 undefined
- chartConfig는 creative 안이 아닌 visualization 레벨에 있음

## 해결
`resolveLayout`에서 `data.chartConfig?.type`도 체크하도록 수정:
```tsx
const chartType = data.chartConfig?.type || creative.chartConfig?.type;
if (chartType === "pie") return "pie";
if (chartType === "line") return "line";
if (chartType === "bar") return "bar";
```

## 수정 파일
- `auto_agent/remotion_template/src/simple/CreativeScene.tsx:148` — data.chartConfig 참조 추가

## 재발 방지
- visualization 하위 필드 참조 시 data(visualization)와 creative(visualization.creative) 레벨 구분 필수
- 새 필드 추가 시 resolveLayout이 어느 레벨에서 읽는지 확인
