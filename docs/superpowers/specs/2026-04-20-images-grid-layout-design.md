# images_grid 레이아웃 설계

**날짜:** 2026-04-20  
**상태:** 승인됨

---

## 개요

화면을 이미지로 분할 배치하는 새 레이아웃 타입 `images_grid`를 추가한다. 기존 레이아웃(`items_grid`, `items_list` 등)과 동급으로 추가되며, 기존 코드를 오버라이드하지 않는다.

---

## 데이터 스키마

```json
{
  "layout": "images_grid",
  "images": ["img1.jpg", "img2.jpg", "img3.jpg", "img4.jpg"],
  "grid_type": "2x2",
  "headline": "선택적 제목",
  "captions": ["캡션1", "캡션2", null, "캡션4"],
  "entrance": "fade"
}
```

### 필드 정의

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `layout` | `"images_grid"` | ✅ | 레이아웃 식별자 |
| `images` | `string[]` | ✅ | 이미지 경로 배열 |
| `grid_type` | `string` | ❌ | 분할 방식 (없으면 이미지 수로 자동 추론) |
| `headline` | `string` | ❌ | 상단 제목 |
| `captions` | `(string \| null)[]` | ❌ | 셀별 캡션 (null이면 해당 셀 캡션 없음) |
| `entrance` | `"fade" \| "slide" \| "overshoot"` | ❌ | 등장 애니메이션 (기본: `"fade"`) |

---

## grid_type 규칙

### 표기 방식
`{cols}x{rows}` — 열 수 × 행 수

| grid_type | 의미 |
|-----------|------|
| `2x1` | 2열 1행 (좌우 분할) |
| `1x2` | 1열 2행 (상하 분할) |
| `2x2` | 2열 2행 (4분할) |
| `3x1` | 3열 1행 (가로 3분할) |
| `1x3` | 1열 3행 (세로 3분할) |
| `3x2` | 3열 2행 (6분할) |
| `2x3` | 2열 3행 (6분할) |

### 비균등 프리셋

| grid_type | 의미 |
|-----------|------|
| `featured_left` | 좌 1/2 크게 + 우 2분할 |
| `featured_right` | 우 1/2 크게 + 좌 2분할 |
| `featured_top` | 상 1/2 크게 + 하 3분할 |

### 이미지 수 → 자동 추론 (grid_type 생략 시)

| 이미지 수 | 기본 grid_type |
|-----------|---------------|
| 2 | `2x1` |
| 3 | `3x1` |
| 4 | `2x2` |
| 6 | `3x2` |
| 기타 | CSS auto-fill |

---

## Remotion 컴포넌트 설계

### 추가 위치
`auto_agent/remotion_template/src/simple/CreativeScene.tsx`

### 타입 유니온 추가
```ts
type SceneLayout =
  | "headline_only"
  | "items_grid"
  | "items_list"
  | "person_card"
  | "counter"
  | "images_grid"   // 신규
  // ...
```

### 유효 레이아웃 목록 추가
```ts
const VALID_LAYOUTS = [
  "headline_only", "items_grid", "items_list", "person_card", "counter",
  "images_grid",   // 신규
  // ...
];
```

### 렌더 분기 추가
```tsx
{layout === "images_grid" && (
  <ImagesGrid
    images={data.images ?? []}
    gridType={data.grid_type}
    captions={data.captions}
    entrance={data.entrance ?? "fade"}
    delays={itemDelays}
  />
)}
```

### ImagesGrid 컴포넌트 props
```ts
const ImagesGrid: React.FC<{
  images: string[];
  gridType?: string;
  captions?: (string | null)[];
  entrance?: "fade" | "slide" | "overshoot";
  delays: number[];
}>
```

---

## 렌더링 방식

### 균등 그리드
```css
display: grid;
grid-template-columns: repeat(cols, 1fr);
grid-template-rows: repeat(rows, 1fr);
gap: 0;
width: 100%;
height: 100%;
```

### 비균등 프리셋 (featured_left 예시)
```css
grid-template-areas:
  "main sub1"
  "main sub2";
grid-template-columns: 1fr 1fr;
```

### 이미지 렌더링
- `object-fit: cover`로 셀 전체 채움
- 셀 크기는 그리드가 결정

### 캡션
- 셀 하단 반투명 오버레이 (`background: rgba(0,0,0,0.45)`)
- 해당 셀 entrance 완료 후 +5프레임 fade in

---

## 애니메이션

### Stagger 순서
행 우선, 좌→우, 위→아래 (인덱스 순)

### 셀당 딜레이
8프레임 간격

### entrance 타입별 동작

| entrance | 동작 |
|----------|------|
| `fade` | opacity 0→1, 15프레임 |
| `slide` | opacity + translateY 20px→0 |
| `overshoot` | scale 0.7→1.08→1, `Easing.out(Easing.back(1.5))` |

---

## helpers.py 수정

- `VALID_LAYOUTS` 목록에 `"images_grid"` 추가
- `images_grid` 레이아웃 시 `images` 필드 존재 여부 검증
- 이미지 수 기반 `grid_type` 자동 추론 헬퍼 함수 추가

---

## 변경 범위 요약

| 파일 | 변경 내용 |
|------|----------|
| `CreativeScene.tsx` (remotion_template) | 타입 추가, 렌더 분기 추가, `ImagesGrid` 컴포넌트 신규 작성 |
| `CreativeScene.tsx` (remotion/src) | 동일 |
| `helpers.py` | 유효 레이아웃 목록, 검증, 자동 추론 추가 |

기존 레이아웃 코드는 수정하지 않는다.
