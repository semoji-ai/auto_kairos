# images_grid Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `images_grid` 레이아웃을 추가하여 화면을 이미지로 분할 배치하는 새 레이아웃 타입을 구현한다.

**Architecture:** `images_grid`는 기존 레이아웃과 동급으로 나란히 추가되며 기존 코드를 수정하지 않는다. `helpers.py`에서 유효성 검사 및 grid_type 자동 추론을 담당하고, `CreativeScene.tsx`에 `ImagesGrid` 컴포넌트를 신규 작성하여 렌더 분기로 연결한다.

**Tech Stack:** TypeScript, React, Remotion, Python

---

## 파일 변경 범위

| 파일 | 변경 |
|------|------|
| `auto_agent/dashboard/helpers.py` | VALID_LAYOUTS에 추가, 검증 로직, grid_type 자동 추론 헬퍼 |
| `auto_agent/remotion_template/src/simple/CreativeScene.tsx` | LayoutType 추가, ImagesGrid 컴포넌트, 렌더 분기 |
| `remotion/src/simple/CreativeScene.tsx` | 위와 동일 (Remotion 양쪽 동기화 규칙) |

---

## Task 1: helpers.py — VALID_LAYOUTS 및 grid_type 추론 추가

**Files:**
- Modify: `auto_agent/dashboard/helpers.py:296-304` (VALID_LAYOUTS 집합)
- Modify: `auto_agent/dashboard/helpers.py:740-800` (layout별 검증 분기)

- [ ] **Step 1: VALID_LAYOUTS에 "images_grid" 추가**

`auto_agent/dashboard/helpers.py` 296~304줄의 VALID_LAYOUTS 집합을 찾아 아래와 같이 수정:

```python
    VALID_LAYOUTS = {
        "headline_only", "items_grid", "items_list", "person_card", "counter",
        "quote", "split", "bar", "logo_grid", "pie", "line",
        "flow", "timeline", "metric_spotlight", "metric_wall", "rank_list",
        "comparison_table", "before_after", "icon_stat", "stacked_progress",
        "card_carousel", "hero_with_context", "quote_portrait", "annotated_chart",
        "cinematic", "bar_horizontal", "donut", "images_grid",
    }
```

- [ ] **Step 2: infer_grid_type 헬퍼 함수 추가**

`helpers.py` 파일 상단 헬퍼 함수 영역(VALID_LAYOUTS 블록 직후)에 아래 함수를 추가:

```python
def infer_grid_type(image_count: int) -> str:
    """이미지 수를 기반으로 grid_type을 자동 추론한다."""
    mapping = {2: "2x1", 3: "3x1", 4: "2x2", 6: "3x2"}
    return mapping.get(image_count, "auto")
```

- [ ] **Step 3: images_grid 검증 로직 추가**

`helpers.py`에서 layout별 렌더 정보를 구성하는 분기 블록(741줄 근처 `elif layout == "items_grid":` 블록 다음)에 추가:

```python
    # ── images_grid: Remotion — 이미지 분할 그리드 ──
    elif layout == "images_grid":
        images = scene.get("images") or creative.get("images") or []
        if not images:
            logger.warning(f"images_grid 레이아웃인데 images 필드가 없습니다: scene_id={scene.get('id', '?')}")
        grid_type = scene.get("grid_type") or creative.get("grid_type")
        if not grid_type:
            grid_type = infer_grid_type(len(images))
        render_info["grid_type"] = grid_type
        render_info["image_count"] = len(images)
```

- [ ] **Step 4: 검증 실행**

```bash
cd ~/Projects/auto_kairos_v3
python -c "
from auto_agent.dashboard.helpers import infer_grid_type
assert infer_grid_type(2) == '2x1'
assert infer_grid_type(4) == '2x2'
assert infer_grid_type(6) == '3x2'
assert infer_grid_type(5) == 'auto'
print('infer_grid_type OK')
"
```

Expected: `infer_grid_type OK`

- [ ] **Step 5: Commit**

```bash
git add auto_agent/dashboard/helpers.py
git commit -m "feat: add images_grid to VALID_LAYOUTS and grid_type inference"
```

---

## Task 2: CreativeScene.tsx — LayoutType 타입 추가 (remotion_template)

**Files:**
- Modify: `auto_agent/remotion_template/src/simple/CreativeScene.tsx:118-145`

- [ ] **Step 1: LayoutType 유니온에 "images_grid" 추가**

118줄 근처 `type LayoutType = ` 블록을 찾아 `"donut"` 뒤에 추가:

```typescript
  | "donut"
  | "images_grid";   // 이미지 분할 그리드
```

- [ ] **Step 2: TypeScript 컴파일 확인**

```bash
cd ~/Projects/auto_kairos_v3/auto_agent/remotion_template
npx tsc --noEmit 2>&1 | head -20
```

Expected: 에러 없음 (또는 기존에 있던 에러만 표시)

- [ ] **Step 3: Commit**

```bash
git add auto_agent/remotion_template/src/simple/CreativeScene.tsx
git commit -m "feat: add images_grid to LayoutType union (remotion_template)"
```

---

## Task 3: ImagesGrid 컴포넌트 작성 (remotion_template)

**Files:**
- Modify: `auto_agent/remotion_template/src/simple/CreativeScene.tsx` (ItemsGrid 컴포넌트 다음에 삽입)

- [ ] **Step 1: ImagesGrid 컴포넌트 작성**

`ItemsGrid` 컴포넌트 블록(1144줄 근처) 바로 다음에 아래 컴포넌트를 삽입:

```typescript
/* ================================================================
   ImagesGrid — 이미지 화면 분할 레이아웃
   ================================================================ */

type ImagesGridEntrance = "fade" | "slide" | "overshoot";

const FEATURED_TEMPLATES: Record<string, { areas: string; columns: string; rows: string }> = {
  featured_left: {
    areas: '"main sub1" "main sub2"',
    columns: "1fr 1fr",
    rows: "1fr 1fr",
  },
  featured_right: {
    areas: '"sub1 main" "sub2 main"',
    columns: "1fr 1fr",
    rows: "1fr 1fr",
  },
  featured_top: {
    areas: '"main main main" "sub1 sub2 sub3"',
    columns: "1fr 1fr 1fr",
    rows: "1fr 1fr",
  },
};

function parseGridType(gridType: string): { cols: number; rows: number } | null {
  const match = gridType.match(/^(\d+)x(\d+)$/);
  if (!match) return null;
  return { cols: parseInt(match[1], 10), rows: parseInt(match[2], 10) };
}

function inferGridType(count: number): string {
  const map: Record<number, string> = { 2: "2x1", 3: "3x1", 4: "2x2", 6: "3x2" };
  return map[count] || "auto";
}

const ImagesGrid: React.FC<{
  images: string[];
  gridType?: string;
  captions?: (string | null)[];
  entrance?: ImagesGridEntrance;
  delays: number[];
}> = ({ images, gridType, captions, entrance = "fade", delays }) => {
  const frame = useCurrentFrame();
  const STAGGER = 8;
  const DURATION = 15;

  const resolvedGridType = gridType || inferGridType(images.length);
  const isFeatured = resolvedGridType in FEATURED_TEMPLATES;
  const featured = isFeatured ? FEATURED_TEMPLATES[resolvedGridType] : null;
  const parsed = !isFeatured ? parseGridType(resolvedGridType) : null;

  const gridStyle: React.CSSProperties = {
    display: "grid",
    gap: 0,
    width: "100%",
    height: "100%",
    position: "absolute",
    inset: 0,
  };

  if (featured) {
    gridStyle.gridTemplateAreas = featured.areas;
    gridStyle.gridTemplateColumns = featured.columns;
    gridStyle.gridTemplateRows = featured.rows;
  } else if (parsed) {
    gridStyle.gridTemplateColumns = `repeat(${parsed.cols}, 1fr)`;
    gridStyle.gridTemplateRows = `repeat(${parsed.rows}, 1fr)`;
  } else {
    // auto: 이미지 수 기반 자동
    const autoCols = Math.ceil(Math.sqrt(images.length));
    gridStyle.gridTemplateColumns = `repeat(${autoCols}, 1fr)`;
  }

  const AREA_NAMES = ["main", "sub1", "sub2", "sub3"];

  return (
    <div style={gridStyle}>
      {images.map((src, i) => {
        const d = delays[i] ?? i * STAGGER;
        const captionText = captions?.[i] ?? null;
        const captionDelay = d + DURATION + 5;

        let opacity = 1;
        let transform = "none";

        if (entrance === "fade") {
          opacity = interpolate(frame, [d, d + DURATION], [0, 1], clamp);
        } else if (entrance === "slide") {
          opacity = interpolate(frame, [d, d + DURATION], [0, 1], clamp);
          const translateY = interpolate(frame, [d, d + DURATION], [20, 0], {
            ...clamp,
            easing: Easing.out(Easing.ease),
          });
          transform = `translateY(${translateY}px)`;
        } else if (entrance === "overshoot") {
          opacity = interpolate(frame, [d, d + Math.floor(DURATION * 0.3)], [0, 1], clamp);
          const scale = interpolate(
            frame,
            [d, d + DURATION],
            [0.7, 1],
            { ...clamp, easing: Easing.out(Easing.back(1.5)) }
          );
          transform = `scale(${scale})`;
        }

        const captionOpacity = captionText
          ? interpolate(frame, [captionDelay, captionDelay + 10], [0, 1], clamp)
          : 0;

        const cellStyle: React.CSSProperties = {
          position: "relative",
          overflow: "hidden",
          opacity,
          transform,
        };

        if (featured && i < AREA_NAMES.length) {
          cellStyle.gridArea = AREA_NAMES[i];
        }

        return (
          <div key={i} style={cellStyle}>
            <img
              src={src}
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
                display: "block",
              }}
            />
            {captionText && (
              <div
                style={{
                  position: "absolute",
                  bottom: 0,
                  left: 0,
                  right: 0,
                  background: "rgba(0,0,0,0.45)",
                  color: "#fff",
                  fontSize: 20,
                  padding: "8px 12px",
                  opacity: captionOpacity,
                }}
              >
                {captionText}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
```

- [ ] **Step 2: TypeScript 컴파일 확인**

```bash
cd ~/Projects/auto_kairos_v3/auto_agent/remotion_template
npx tsc --noEmit 2>&1 | head -30
```

Expected: 에러 없음

- [ ] **Step 3: Commit**

```bash
git add auto_agent/remotion_template/src/simple/CreativeScene.tsx
git commit -m "feat: add ImagesGrid component (remotion_template)"
```

---

## Task 4: 렌더 분기 추가 (remotion_template)

**Files:**
- Modify: `auto_agent/remotion_template/src/simple/CreativeScene.tsx:3685` 근처 (items_grid 렌더 분기 다음)

- [ ] **Step 1: 렌더 분기 추가**

`{layout === "items_grid" && ( <ItemsGrid ... /> )}` 블록 바로 다음에 추가:

```tsx
        {/* Images grid */}
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

- [ ] **Step 2: TypeScript 컴파일 확인**

```bash
cd ~/Projects/auto_kairos_v3/auto_agent/remotion_template
npx tsc --noEmit 2>&1 | head -30
```

Expected: 에러 없음

- [ ] **Step 3: Commit**

```bash
git add auto_agent/remotion_template/src/simple/CreativeScene.tsx
git commit -m "feat: add images_grid render branch (remotion_template)"
```

---

## Task 5: remotion/src 동기화

**Files:**
- Modify: `remotion/src/simple/CreativeScene.tsx`

> CLAUDE.md 규칙: Remotion 양쪽 동기화 — `remotion/src/` ↔ `auto_agent/remotion_template/src/` 항상 동일하게 유지.

- [ ] **Step 1: LayoutType에 images_grid 추가**

`remotion/src/simple/CreativeScene.tsx`에서 LayoutType 유니온을 찾아 `"donut"` 뒤에 추가:

```typescript
  | "donut"
  | "images_grid";   // 이미지 분할 그리드
```

- [ ] **Step 2: ImagesGrid 컴포넌트 복사**

Task 3 Step 1에서 작성한 `ImagesGrid` 컴포넌트 전체(FEATURED_TEMPLATES, parseGridType, inferGridType, ImagesGrid)를 `remotion/src/simple/CreativeScene.tsx`의 동일 위치(ItemsGrid 다음)에 삽입.

- [ ] **Step 3: 렌더 분기 복사**

Task 4 Step 1에서 추가한 렌더 분기를 `remotion/src/simple/CreativeScene.tsx`의 동일 위치에 삽입:

```tsx
        {/* Images grid */}
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

- [ ] **Step 4: TypeScript 컴파일 확인**

```bash
cd ~/Projects/auto_kairos_v3/remotion
npx tsc --noEmit 2>&1 | head -30
```

Expected: 에러 없음

- [ ] **Step 5: Commit**

```bash
git add remotion/src/simple/CreativeScene.tsx
git commit -m "feat: sync images_grid to remotion/src (양쪽 동기화)"
```

---

## Task 6: scene_specs.json 수동 테스트

**Files:**
- 임시 테스트용 scene_specs 작성 후 Remotion Studio에서 확인

- [ ] **Step 1: 테스트 scene_specs 준비**

`output/` 폴더 아래 임의 프로젝트의 `scene_specs.json`을 열어 테스트 씬 하나를 추가하거나, 기존 씬의 layout을 `"images_grid"`로 변경하고 `images` 필드에 실제 존재하는 이미지 경로 2~4개를 입력:

```json
{
  "id": "test_images_grid",
  "layout": "images_grid",
  "images": [
    "output/{uuid_slug}/images/{실제존재이미지1}.jpg",
    "output/{uuid_slug}/images/{실제존재이미지2}.jpg",
    "output/{uuid_slug}/images/{실제존재이미지3}.jpg",
    "output/{uuid_slug}/images/{실제존재이미지4}.jpg"
  ],
  "headline": "테스트 제목",
  "captions": ["셀1", "셀2", null, "셀4"],
  "entrance": "fade"
}
```

- [ ] **Step 2: Remotion Studio 실행**

```bash
cd ~/Projects/auto_kairos_v3/remotion
npm run dev
```

브라우저에서 해당 씬 확인:
- 이미지 4개가 2x2로 분할되어 나타남
- gap 없이 꽉 채워짐
- stagger로 순차 등장
- 캡션이 null인 셀은 캡션 없음

- [ ] **Step 3: entrance 타입 변경 테스트**

scene_specs에서 `"entrance": "slide"`, `"entrance": "overshoot"`으로 각각 변경하여 애니메이션 확인.

- [ ] **Step 4: grid_type 테스트**

`"grid_type": "featured_left"` 로 변경 후 비균등 분할(좌 크게 + 우 2분할) 확인.

- [ ] **Step 5: grid_type 생략 테스트**

`grid_type` 필드 삭제 후 이미지 수에 따라 자동 추론되는지 확인 (이미지 2개 → 2x1, 4개 → 2x2).

---

## Self-Review

### Spec Coverage

| 스펙 요구사항 | 구현 태스크 |
|-------------|-----------|
| `images_grid` 레이아웃 타입 추가 | Task 2, 5 |
| grid_type 자동 추론 (이미지 수 기반) | Task 1 Step 2, Task 3 |
| 균등 분할 (NxM) | Task 3 |
| 비균등 프리셋 (featured_*) | Task 3 |
| captions 선택적 오버레이 | Task 3 |
| entrance: fade/slide/overshoot | Task 3 |
| stagger 8프레임 간격 | Task 3 |
| helpers.py VALID_LAYOUTS 추가 | Task 1 |
| helpers.py 검증 로직 | Task 1 Step 3 |
| 기존 코드 수정 없음 | 전 태스크 |
| Remotion 양쪽 동기화 | Task 5 |
| gap 없음 | Task 3 (gap: 0) |

### Placeholder Scan

없음 — 모든 스텝에 실제 코드 포함.

### Type Consistency

- `ImagesGrid` props: `images`, `gridType`, `captions`, `entrance`, `delays` → 렌더 분기에서 동일 이름 사용
- `ImagesGridEntrance` 타입: `"fade" | "slide" | "overshoot"` → entrance 파라미터와 일치
- `inferGridType` 함수명: Python `infer_grid_type`과 TS `inferGridType` — 각 언어 컨벤션 준수
