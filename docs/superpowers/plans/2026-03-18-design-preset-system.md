# Design Preset System Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remotion SimpleVideo의 모든 하드코딩 디자인 값을 아트스타일별 프리셋으로 추출하여, 대시보드에서 편집/저장하고 Studio에서 오버라이드 가능하게 한다.

**Architecture:** manifest.meta.designPreset 경유 방식. DesignPresetContext(React Context)가 deep merge로 기본 프리셋 + 아트스타일 프리셋 + 사용자 오버라이드를 합산. 모든 컴포넌트가 이 Context에서 디자인 토큰을 읽음.

**Tech Stack:** TypeScript (Remotion), Python (FastAPI dashboard), React Context API

**Spec:** `docs/superpowers/specs/2026-03-18-design-preset-system-design.md`

---

## Chunk 1: 기반 타입 + 기본 프리셋 + Context Provider

### Task 1: DesignPreset 타입 정의

**Files:**
- Create: `remotion/src/design/types.ts`

- [ ] **Step 1: 타입 파일 생성**

```typescript
// remotion/src/design/types.ts

export interface FontFile {
  file: string;    // "fonts/Pretendard-Regular.otf"
  weight: string;  // "400"
}

export interface FontDef {
  family: string;
  fallback: string;
  files: FontFile[];
}

export interface TagTextSizes {
  sm: number;
  md: number;
  lg: number;
}

export interface TagPadding {
  sm: [number, number];
  md: [number, number];
  lg: [number, number];
}

export interface PresetColors {
  bg: string;
  text: string;
  textMuted: string;
  textDim: string;
  accent: string;
  accentRgb: string;
  accentBg: string;
  accentBorder: string;
  accentSoft: string;
  cardBg: string;
  cardBorder: string;
  divider: string;
  positive: string;
  negative: string;
  warning: string;
  rank: [string, string, string];
}

export interface PresetFonts {
  body: FontDef;
  title?: FontDef;
  quote?: { family: string };
}

export interface PresetTypography {
  headlineAccent: number;
  headlineBase: number;
  metricValue: number;
  itemText: number;
  descText: number;
  labelText: number;
  sourceText: number;
  captionText: number;
  quoteText: number;
  quoteMarkSize: number;
  chartTitle: number;
  chartValue: number;
  pillText: number;
  tagText: TagTextSizes;
  progressLabel: number;
  metricCardLabel: number;
  metricCardChange: number;
  comparisonLabel: number;
  comparisonValue: number;
  comparisonSub: number;
  timelineDotLabel: number;
  stepBadgeLabel: number;
  calloutText: number;
  annotationText: number;
  miniBarLabel: number;
  flagCardLabel: number;
  splitLabel: number;
  splitVsText: number;
}

export interface PresetLayout {
  scenePadding: [number, number];
  contentWidth: string;
  headlineMaxWidth: string;
  maxContentWidth: number;
  gap: number;
  itemsGap: number;
  sectionMarginTop: number;
  cardRadius: number;
  cardPadding: [number, number];
  pillRadius: number;
  tagRadius: number;
  dividerThickness: number;
  badgeSize: number;
  imageBadgeSize: number;
  rankBadgeSize: number;
  stepBadgeSize: number;
  timelineDotSize: number;
  statusDotSize: number;
  logoIconSize: number;
  barHeight: number;
  barLabelWidth: number;
  barValueWidth: number;
  sparklineSize: [number, number];
  progressBarHeight: number;
  miniBarHeight: number;
  pieLegendSwatchSize: number;
  connectorLength: number;
  connectorWidth: number;
  annotationLineLength: number;
  calloutBorderWidth: number;
  timelineConnectorHeight: number;
  timelineConnectorWidth: number;
  splitDividerWidth: number;
  splitVsWidth: number;
  personCardImgHeight: number;
  carouselCardWidth: number;
  carouselImgHeight: number;
  tagPadding: TagPadding;
  pillPadding: [number, number];
}

export interface MoodOverride {
  accent?: string;
  accentRgb?: string;
  speed?: number;
  glow?: number;
  gradient?: string;
}

export interface PresetSubtitle {
  fontFamily?: string;
  fontSize: number;
  fontWeight: number;
  color: string;
  strokeColor: string;
  strokeWidth: number;
  keywordColor: string;
  keywordStrokeColor: string;
  bottomOffset: number;
  maxWidth: string;
  lineHeight: number;
}

export interface PresetAnimation {
  stagger: number;
  itemDuration: number;
  easing: string;
  titleFadeIn: number;
}

export interface PresetBackground {
  pattern: "dots" | "grid" | "lines" | "none";
  opacity: number;
}

export interface PresetMap {
  defaultTheme: string;
  fontOverride?: string;
}

export interface DesignPreset {
  id: string;
  name: string;
  description: string;
  version: number;
  author?: string;
  tags?: string[];
  artStyle?: string;
  baseTheme: "dark" | "white";

  colors: PresetColors;
  fonts: PresetFonts;
  typography: PresetTypography;
  layout: PresetLayout;
  moods: Record<string, MoodOverride>;
  map: PresetMap;
  subtitle: PresetSubtitle;
  animation: PresetAnimation;
  background: PresetBackground;
}

/** manifest에서 전달되는 partial 오버라이드 (모든 필드 optional) */
export type DesignPresetOverride = DeepPartial<Omit<DesignPreset, "id" | "name" | "description" | "version">>;

/** 재귀적 Partial 유틸 */
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};
```

- [ ] **Step 2: 빌드 확인**

Run: `cd /Users/hannah/Projects/auto_kairos_v3/remotion && npx tsc --noEmit remotion/src/design/types.ts 2>&1 | head -20`
Expected: 에러 없음

- [ ] **Step 3: 커밋**

```bash
git add remotion/src/design/types.ts
git commit -m "feat: add DesignPreset type definitions"
```

---

### Task 2: 기본 프리셋 (DEFAULT_PRESET)

**Files:**
- Create: `remotion/src/design/defaults.ts`

현재 BuildingBlocks.tsx의 COLORS_DARK, CreativeScene.tsx의 MOOD_CONFIGS/MOOD_GRADIENTS, SimpleVideo.tsx의 BUNDLED_FONTS 등 모든 하드코딩 값을 그대로 DEFAULT_PRESET 객체로 추출한다. **값을 변경하지 않는다** — 현재 동작을 정확히 보존.

- [ ] **Step 1: defaults.ts 생성**

현재 하드코딩된 값을 그대로 옮겨서 DEFAULT_PRESET 상수를 생성한다.

주요 출처:
- `BuildingBlocks.tsx:70-81` → colors (COLORS_DARK)
- `BuildingBlocks.tsx:84-96` → colors white 변형은 별도 white preset에서
- `CreativeScene.tsx:225-268` → moods (MOOD_CONFIGS)
- `CreativeScene.tsx:270-302` → moods.gradient (MOOD_GRADIENTS)
- `CreativeScene.tsx:450-473` → typography (getAccentFontSize, getBaseFontSize)
- `SimpleVideo.tsx:33-38` → fonts (BUNDLED_FONTS)
- `SimpleVideo.tsx:282-295` → subtitle (subtitle_config는 Root.tsx에도 있음)
- `vizStyles.ts:69-75` → fonts.files (FONT_DEFS — MapSceneRenderer용 포함)

```typescript
// remotion/src/design/defaults.ts
import type { DesignPreset } from "./types";

export const DEFAULT_PRESET: DesignPreset = {
  id: "default",
  name: "Default Dark",
  description: "기본 다크 테마 — 앰버 액센트",
  version: 1,
  baseTheme: "dark",

  colors: {
    bg: "#0A0A0A",
    text: "#FFFFFF",
    textMuted: "#FFFFFF",
    textDim: "#FFFFFF",
    accent: "#F59E0B",
    accentRgb: "245,158,11",
    accentBg: "rgba(245,158,11,0.08)",
    accentBorder: "rgba(245,158,11,0.3)",
    accentSoft: "rgba(245,158,11,0.15)",
    cardBg: "rgba(245,158,11,0.06)",
    cardBorder: "rgba(245,158,11,0.25)",
    divider: "rgba(255,255,255,0.08)",
    positive: "#22C55E",
    negative: "#EF4444",
    warning: "#F59E0B",
    rank: ["#FFD700", "#C0C0C0", "#CD7F32"],
  },

  fonts: {
    body: {
      family: "Pretendard",
      fallback: "'Apple SD Gothic Neo', sans-serif",
      files: [
        { file: "fonts/Pretendard-Regular.otf", weight: "400" },
        { file: "fonts/Pretendard-Bold.otf", weight: "700" },
      ],
    },
  },

  typography: {
    headlineAccent: 80,
    headlineBase: 48,
    metricValue: 60,
    itemText: 28,
    descText: 20,
    labelText: 22,
    sourceText: 18,
    captionText: 18,
    quoteText: 44,
    quoteMarkSize: 120,
    chartTitle: 48,
    chartValue: 28,
    pillText: 20,
    tagText: { sm: 20, md: 26, lg: 36 },
    progressLabel: 36,
    metricCardLabel: 20,
    metricCardChange: 18,
    comparisonLabel: 24,
    comparisonValue: 48,
    comparisonSub: 24,
    timelineDotLabel: 28,
    stepBadgeLabel: 28,
    calloutText: 28,
    annotationText: 36,
    miniBarLabel: 30,
    flagCardLabel: 24,
    splitLabel: 28,
    splitVsText: 30,
  },

  layout: {
    scenePadding: [60, 48],
    contentWidth: "78%",
    headlineMaxWidth: "90%",
    maxContentWidth: 1100,
    gap: 24,
    itemsGap: 16,
    sectionMarginTop: 32,
    cardRadius: 12,
    cardPadding: [24, 28],
    pillRadius: 20,
    tagRadius: 6,
    dividerThickness: 1,
    badgeSize: 48,
    imageBadgeSize: 56,
    rankBadgeSize: 72,
    stepBadgeSize: 56,
    timelineDotSize: 32,
    statusDotSize: 16,
    logoIconSize: 64,
    barHeight: 32,
    barLabelWidth: 200,
    barValueWidth: 120,
    sparklineSize: [280, 72],
    progressBarHeight: 16,
    miniBarHeight: 12,
    pieLegendSwatchSize: 20,
    connectorLength: 40,
    connectorWidth: 3,
    annotationLineLength: 100,
    calloutBorderWidth: 5,
    timelineConnectorHeight: 36,
    timelineConnectorWidth: 2,
    splitDividerWidth: 2,
    splitVsWidth: 60,
    personCardImgHeight: 140,
    carouselCardWidth: 260,
    carouselImgHeight: 140,
    tagPadding: {
      sm: [8, 18],
      md: [12, 28],
      lg: [16, 36],
    },
    pillPadding: [8, 20],
  },

  moods: {
    dramatic:     { accent: "#F59E0B", accentRgb: "245,158,11", speed: 1.2, glow: 0.6, gradient: "radial-gradient(ellipse 80% 60% at 50% 40%, #1a1005 0%, #0A0A0A 70%)" },
    urgent:       { accent: "#EF4444", accentRgb: "239,68,68",  speed: 1.5, glow: 0.8, gradient: "radial-gradient(ellipse 80% 60% at 50% 40%, #1a0808 0%, #0A0A0A 70%)" },
    somber:       { accent: "#71717A", accentRgb: "113,113,122", speed: 0.7, glow: 0.2, gradient: "radial-gradient(ellipse 80% 60% at 50% 40%, #0d0d0e 0%, #0A0A0A 70%)" },
    informative:  { accent: "#3B82F6", accentRgb: "59,130,246",  speed: 1.0, glow: 0.3, gradient: "radial-gradient(ellipse 80% 60% at 50% 40%, #080d1a 0%, #0A0A0A 70%)" },
    contemplative:{ accent: "#3B82F6", accentRgb: "59,130,246",  speed: 0.6, glow: 0.2, gradient: "radial-gradient(ellipse 80% 60% at 50% 40%, #080d1a 0%, #0A0A0A 70%)" },
    suspense:     { accent: "#F59E0B", accentRgb: "245,158,11", speed: 0.8, glow: 0.5, gradient: "radial-gradient(ellipse 80% 60% at 50% 40%, #14100a 0%, #0A0A0A 70%)" },
    triumphant:   { accent: "#10B981", accentRgb: "16,185,129",  speed: 1.0, glow: 0.5, gradient: "radial-gradient(ellipse 80% 60% at 50% 40%, #081a10 0%, #0A0A0A 70%)" },
  },

  map: {
    defaultTheme: "modern_clean",
  },

  subtitle: {
    fontSize: 44,
    fontWeight: 700,
    color: "#FFFFFF",
    strokeColor: "#3D3B2F",
    strokeWidth: 2,
    keywordColor: "#F7D94C",
    keywordStrokeColor: "#5A4B00",
    bottomOffset: 30,
    maxWidth: "85%",
    lineHeight: 1.5,
  },

  animation: {
    stagger: 8,
    itemDuration: 20,
    easing: "easeOut",
    titleFadeIn: 15,
  },

  background: {
    pattern: "dots",
    opacity: 0.02,
  },
};
```

- [ ] **Step 2: 빌드 확인**

Run: `cd /Users/hannah/Projects/auto_kairos_v3/remotion && npx tsc --noEmit`
Expected: 에러 없음

- [ ] **Step 3: 커밋**

```bash
git add remotion/src/design/defaults.ts
git commit -m "feat: extract DEFAULT_PRESET from hardcoded values"
```

---

### Task 3: 아트스타일별 프리셋 (4종)

**Files:**
- Create: `remotion/src/design/presets/semoji.ts`
- Create: `remotion/src/design/presets/lego.ts`
- Create: `remotion/src/design/presets/quirky_cartoon.ts`
- Create: `remotion/src/design/presets/stickman_cute.ts`
- Create: `remotion/src/design/presets/index.ts`

각 프리셋은 DEFAULT_PRESET과의 **diff만** 정의한다 (DeepPartial). 현재 BuildingBlocks의 ART_STYLE_ACCENTS에서 accent만 갖고 있던 것을, 풀 프리셋으로 확장.

- [ ] **Step 1: 4개 프리셋 파일 생성**

예시 — semoji.ts:
```typescript
import type { DesignPresetOverride } from "../types";

export const SEMOJI_PRESET: DesignPresetOverride = {
  artStyle: "semoji",
  baseTheme: "dark",
  colors: {
    accent: "#6366F1",
    accentRgb: "99,102,241",
    accentBg: "rgba(99,102,241,0.08)",
    accentBorder: "rgba(99,102,241,0.3)",
    accentSoft: "rgba(99,102,241,0.15)",
    cardBg: "rgba(99,102,241,0.06)",
    cardBorder: "rgba(99,102,241,0.25)",
  },
  layout: {
    cardRadius: 16,
    gap: 28,
  },
  map: {
    defaultTheme: "modern_clean",
  },
  subtitle: {
    keywordColor: "#6366F1",
  },
};
```

나머지(lego, quirky_cartoon, stickman_cute)도 동일 패턴. index.ts에서 Record로 export:

```typescript
// remotion/src/design/presets/index.ts
import type { DesignPresetOverride } from "../types";
import { SEMOJI_PRESET } from "./semoji";
import { LEGO_PRESET } from "./lego";
import { QUIRKY_CARTOON_PRESET } from "./quirky_cartoon";
import { STICKMAN_CUTE_PRESET } from "./stickman_cute";

export const ART_PRESETS: Record<string, DesignPresetOverride> = {
  semoji: SEMOJI_PRESET,
  lego: LEGO_PRESET,
  quirky_cartoon: QUIRKY_CARTOON_PRESET,
  stickman_cute: STICKMAN_CUTE_PRESET,
};
```

- [ ] **Step 2: 빌드 확인**
- [ ] **Step 3: 커밋**

```bash
git add remotion/src/design/presets/
git commit -m "feat: add art style presets (semoji, lego, quirky_cartoon, stickman_cute)"
```

---

### Task 4: Deep Merge 유틸 + resolvePreset

**Files:**
- Create: `remotion/src/design/resolvePreset.ts`

- [ ] **Step 1: resolvePreset.ts 생성**

```typescript
// remotion/src/design/resolvePreset.ts
import type { DesignPreset, DesignPresetOverride } from "./types";
import { DEFAULT_PRESET } from "./defaults";
import { ART_PRESETS } from "./presets";

/** 재귀적 deep merge — source의 값이 있으면 base를 덮어씀 */
export function deepMerge<T extends Record<string, any>>(
  base: T,
  ...overrides: (Partial<T> | undefined)[]
): T {
  const result = { ...base };
  for (const override of overrides) {
    if (!override) continue;
    for (const key of Object.keys(override) as (keyof T)[]) {
      const val = override[key];
      if (val === undefined) continue;
      if (
        val !== null &&
        typeof val === "object" &&
        !Array.isArray(val) &&
        typeof result[key] === "object" &&
        !Array.isArray(result[key])
      ) {
        result[key] = deepMerge(result[key] as any, val as any);
      } else {
        result[key] = val as T[keyof T];
      }
    }
  }
  return result;
}

/** artStyle 문자열에서 이름 추출: "artstyle/styles/semoji.json" → "semoji" */
function extractStyleName(artStyle: string): string {
  return artStyle.replace(/.*\//, "").replace(/\.json$/, "");
}

/**
 * manifest meta에서 최종 DesignPreset을 해석
 * 우선순위: DEFAULT → artStyle 프리셋 → 사용자 오버라이드(designPreset)
 */
export function resolvePreset(meta: {
  artStyle?: string;
  designPreset?: DesignPresetOverride;
  videoTheme?: string;
}): DesignPreset {
  // 1. 기본
  let base = DEFAULT_PRESET;

  // videoTheme이 "white"이면 white 기본 프리셋 (향후 WHITE_PRESET 추가 가능)
  // 지금은 DEFAULT_PRESET이 dark — white는 사용자 오버라이드로 처리

  // 2. artStyle 프리셋
  const artPreset = meta.artStyle
    ? ART_PRESETS[extractStyleName(meta.artStyle)]
    : undefined;

  // 3. 사용자 오버라이드
  const userOverride = meta.designPreset;

  return deepMerge(base, artPreset as any, userOverride as any);
}
```

- [ ] **Step 2: 빌드 확인**
- [ ] **Step 3: 커밋**

```bash
git add remotion/src/design/resolvePreset.ts
git commit -m "feat: add resolvePreset with deep merge"
```

---

### Task 5: DesignPresetContext (React Context + Provider)

**Files:**
- Create: `remotion/src/design/DesignPresetContext.tsx`

- [ ] **Step 1: Context 파일 생성**

```typescript
// remotion/src/design/DesignPresetContext.tsx
import React, { useMemo } from "react";
import type { DesignPreset, DesignPresetOverride } from "./types";
import { DEFAULT_PRESET } from "./defaults";
import { resolvePreset } from "./resolvePreset";

const DesignPresetCtx = React.createContext<DesignPreset>(DEFAULT_PRESET);

interface ProviderProps {
  meta: {
    artStyle?: string;
    designPreset?: DesignPresetOverride;
    videoTheme?: string;
  };
  children: React.ReactNode;
}

export const DesignPresetProvider: React.FC<ProviderProps> = ({
  meta,
  children,
}) => {
  const preset = useMemo(() => resolvePreset(meta), [
    meta.artStyle,
    meta.videoTheme,
    // designPreset은 객체라 JSON 비교 필요 — 실제로는 manifest가 바뀔 때만 재계산
    JSON.stringify(meta.designPreset),
  ]);

  return (
    <DesignPresetCtx.Provider value={preset}>
      {children}
    </DesignPresetCtx.Provider>
  );
};

/** 현재 디자인 프리셋 전체를 가져온다 */
export const useDesignPreset = (): DesignPreset =>
  React.useContext(DesignPresetCtx);

/** 하위호환: 기존 useC()와 동일한 인터페이스 — colors만 반환 */
export const usePresetColors = () => React.useContext(DesignPresetCtx).colors;

/** 타이포 토큰 */
export const usePresetTypo = () => React.useContext(DesignPresetCtx).typography;

/** 레이아웃 토큰 */
export const usePresetLayout = () => React.useContext(DesignPresetCtx).layout;
```

- [ ] **Step 2: 진입점 index 생성**

```typescript
// remotion/src/design/index.ts
export type { DesignPreset, DesignPresetOverride, FontFile } from "./types";
export { DEFAULT_PRESET } from "./defaults";
export { resolvePreset, deepMerge } from "./resolvePreset";
export {
  DesignPresetProvider,
  useDesignPreset,
  usePresetColors,
  usePresetTypo,
  usePresetLayout,
} from "./DesignPresetContext";
```

- [ ] **Step 3: 빌드 확인**
- [ ] **Step 4: 커밋**

```bash
git add remotion/src/design/
git commit -m "feat: add DesignPresetContext with Provider and hooks"
```

---

### Task 6: 통합 폰트 로딩 유틸

**Files:**
- Create: `remotion/src/design/fonts.ts`

SimpleVideo.tsx의 `useFonts()`와 MapSceneRenderer의 `useFonts()`를 하나로 통합. 프리셋의 `fonts` 설정에서 읽음.

- [ ] **Step 1: fonts.ts 생성**

```typescript
// remotion/src/design/fonts.ts
import { useState, useEffect } from "react";
import { delayRender, continueRender, staticFile } from "remotion";
import type { FontDef } from "./types";
import { useDesignPreset } from "./DesignPresetContext";

const resolveUrl = (path: string): string =>
  path.startsWith("http://") || path.startsWith("https://") ? path : staticFile(path);

const isSystemFont = (family: string): boolean => {
  try {
    return document.fonts.check(`16px "${family}"`);
  } catch {
    return false;
  }
};

async function loadFontDef(def: FontDef): Promise<void> {
  if (isSystemFont(def.family)) return;
  await Promise.all(
    def.files.map(async (f) => {
      const face = new FontFace(def.family, `url('${resolveUrl(f.file)}')`, {
        weight: f.weight,
        style: "normal",
      });
      const loaded = await face.load();
      document.fonts.add(loaded);
    }),
  );
}

/** 프리셋 기반 통합 폰트 로딩 훅 */
export function usePresetFonts(): void {
  const preset = useDesignPreset();
  const [handle] = useState(() => delayRender("Loading preset fonts"));

  useEffect(() => {
    const load = async () => {
      // body 폰트
      await loadFontDef(preset.fonts.body);
      // title 폰트 (있으면)
      if (preset.fonts.title) {
        await loadFontDef(preset.fonts.title);
      }
      continueRender(handle);
    };
    load().catch(() => continueRender(handle));
  }, [handle]);
}

/** 프리셋에서 CSS font-family 문자열 생성 */
export function buildFontFamily(preset: { fonts: { body: FontDef; title?: FontDef } }): string {
  const body = preset.fonts.body;
  return `'${body.family}', ${body.fallback}`;
}

export function buildTitleFontFamily(preset: { fonts: { body: FontDef; title?: FontDef } }): string {
  const title = preset.fonts.title || preset.fonts.body;
  return `'${title.family}', ${title.fallback}`;
}
```

- [ ] **Step 2: 빌드 확인**
- [ ] **Step 3: design/index.ts에 export 추가**
- [ ] **Step 4: 커밋**

```bash
git add remotion/src/design/fonts.ts remotion/src/design/index.ts
git commit -m "feat: add unified font loading from preset"
```

---

## Chunk 2: vizStyles 백업 + manifest 타입 확장

### Task 7: vizStyles.ts 백업

**Files:**
- Rename: `remotion/src/visualizations/vizStyles.ts` → `remotion/src/visualizations/vizStyles.legacy.ts`
- Create: `remotion/src/visualizations/vizStyles.ts` (리다이렉트 심)

vizStyles.ts를 직접 import하는 파일이 24개 있으므로, 이름 변경 후 리다이렉트 심을 만들어 빌드를 깨뜨리지 않는다. 이후 Chunk 3-4에서 각 파일의 import를 점진적으로 교체한 뒤 심을 제거.

- [ ] **Step 1: 파일 이름 변경**

```bash
cd /Users/hannah/Projects/auto_kairos_v3
mv remotion/src/visualizations/vizStyles.ts remotion/src/visualizations/vizStyles.legacy.ts
```

- [ ] **Step 2: 리다이렉트 심 생성**

```typescript
// remotion/src/visualizations/vizStyles.ts
/**
 * @deprecated — design/defaults.ts + design/fonts.ts로 이전됨.
 * 기존 import 하위호환을 위한 리다이렉트.
 */
export { STYLE, TYPO, LAYOUT, VIZ_FONT, VIZ_TITLE_FONT, FONT_DEFS } from "./vizStyles.legacy";
```

- [ ] **Step 3: 빌드 확인**

Run: `cd /Users/hannah/Projects/auto_kairos_v3/remotion && npx tsc --noEmit`
Expected: 에러 없음 (기존 import 모두 심을 통해 동작)

- [ ] **Step 4: 커밋**

```bash
git add remotion/src/visualizations/vizStyles.ts remotion/src/visualizations/vizStyles.legacy.ts
git commit -m "refactor: backup vizStyles.ts as legacy, add redirect shim"
```

---

### Task 8: manifest.ts에 DesignPreset 타입 추가

**Files:**
- Modify: `remotion/src/types/manifest.ts:57` (meta에 designPreset 필드 추가)

- [ ] **Step 1: manifest.ts 수정**

`SceneManifest.meta`에 `designPreset` 필드 추가:

```typescript
// manifest.ts의 SceneManifest.meta에 추가:
import type { DesignPresetOverride } from "../design/types";

// meta 안에:
    /** 디자인 프리셋 오버라이드 (아트스타일 기본값 위에 덮어씀) */
    designPreset?: DesignPresetOverride;
```

기존 `designTokens`, `videoTheme`, `artStyle`은 유지 (하위호환).

- [ ] **Step 2: 빌드 확인**
- [ ] **Step 3: 커밋**

```bash
git add remotion/src/types/manifest.ts
git commit -m "feat: add designPreset field to SceneManifest.meta"
```

---

## Chunk 3: BuildingBlocks.tsx 마이그레이션

### Task 9: BuildingBlocks — 디자인 토큰 제거 + Context 전환

**Files:**
- Modify: `remotion/src/simple/BuildingBlocks.tsx`

이 태스크가 가장 크다. 단계적으로 진행:

- [ ] **Step 1: import 추가 + VideoThemeProvider 교체**

파일 상단에 design import 추가:
```typescript
import { useDesignPreset, usePresetColors, usePresetTypo, usePresetLayout } from "../design";
```

기존 `VideoThemeProvider`를 `DesignPresetProvider`를 래핑하는 호환 레이어로 교체:
```typescript
// 하위호환: VideoThemeProvider → DesignPresetProvider 브릿지
export const VideoThemeProvider: React.FC<{
  theme: string;
  artStyle?: string;
  children: React.ReactNode;
}> = ({ theme, artStyle, children }) => {
  // 새 시스템이 적용되면 SimpleVideo에서 직접 DesignPresetProvider를 사용하므로
  // 이 컴포넌트는 점진적으로 제거됨
  return <>{children}</>;
};
```

- [ ] **Step 2: useC() → usePresetColors()로 변경**

기존 `useC()` 훅을 `usePresetColors()`의 별칭으로 교체:
```typescript
/** @deprecated — usePresetColors() 사용 권장 */
export const useC = (): PresetColors => usePresetColors();
```

`ColorTokens` 인터페이스 → `PresetColors` re-export:
```typescript
export type { PresetColors as ColorTokens } from "../design/types";
```

- [ ] **Step 3: 전역 C 상수 제거 → useC() 통일**

7개 컴포넌트(Icon, Connector, Divider, QuoteMark, GlowDot, AnnotationLine, Sparkline)의 props 기본값에서 `C.accent` / `C.divider` 사용을 제거. 대신 컴포넌트 내부에서 `useC()`로 읽도록 변경.

예시 — Icon:
```typescript
// Before:
export const Icon: React.FC<{
  icon: LucideIcon; size?: number; color?: string;
}> = ({ icon: LucideComp, size = 24, color = C.accent, style }) => (
  <LucideComp size={size} color={color} strokeWidth={1.5} style={style} />
);

// After:
export const Icon: React.FC<{
  icon: LucideIcon; size?: number; color?: string; style?: React.CSSProperties;
}> = ({ icon: LucideComp, size = 24, color, style }) => {
  const C = useC();
  return <LucideComp size={size} color={color ?? C.accent} strokeWidth={1.5} style={style} />;
};
```

동일 패턴을 Connector, Divider, QuoteMark, GlowDot, AnnotationLine, Sparkline에 적용.

- [ ] **Step 4: 시맨틱 색상 하드코딩 → Context에서 읽기**

StatusDot, RankBadge, MetricCard, ComparisonCell, Callout의 하드코딩 색상을 `usePresetColors()`에서 읽도록 변경.

예시 — StatusDot:
```typescript
// Before:
const colors = { positive: "#22C55E", negative: "#EF4444", neutral: "rgba(255,255,255,0.4)", warning: "#F59E0B" };

// After:
const C = useC();
const colors = { positive: C.positive, negative: C.negative, neutral: C.textDim, warning: C.warning };
```

- [ ] **Step 5: 타이포 하드코딩 → Context에서 읽기**

각 컴포넌트의 하드코딩 fontSize를 `usePresetTypo()`에서 읽도록 변경.

예시 — MetricCard:
```typescript
const T = usePresetTypo();
// fontSize: 20 → T.metricCardLabel
// fontSize: 44 → T.metricValue  (44 → metricValue는 60이 기본이므로 별도 metricCardValue 토큰 필요하면 추가)
// fontSize: 18 → T.metricCardChange
```

- [ ] **Step 6: 레이아웃 하드코딩 → Context에서 읽기**

Card, Pill, Tag 등의 하드코딩 padding, borderRadius를 `usePresetLayout()`에서 읽도록 변경.

예시 — Card:
```typescript
const L = usePresetLayout();
// borderRadius: 12 → L.cardRadius
// padding: "24px 28px" → `${L.cardPadding[0]}px ${L.cardPadding[1]}px`
```

- [ ] **Step 7: COLORS_DARK, COLORS_WHITE, ART_STYLE_ACCENTS, THEME_PALETTES, resolveVideoTheme 제거**

더 이상 사용되지 않는 코드 블록 삭제. `export const C` 전역 상수도 제거.

- [ ] **Step 8: 빌드 확인**

Run: `cd /Users/hannah/Projects/auto_kairos_v3/remotion && npx tsc --noEmit`

- [ ] **Step 9: 커밋**

```bash
git add remotion/src/simple/BuildingBlocks.tsx
git commit -m "refactor: migrate BuildingBlocks to DesignPreset Context"
```

---

## Chunk 4: SimpleVideo + CreativeScene + MapSceneRenderer 마이그레이션

### Task 10: SimpleVideo.tsx — DesignPresetProvider 래핑

**Files:**
- Modify: `remotion/src/SimpleVideo.tsx`

- [ ] **Step 1: import 교체**

```typescript
// 제거:
import { VideoThemeProvider, resolveVideoTheme, type ColorTokens } from "./simple/BuildingBlocks";

// 추가:
import { DesignPresetProvider, useDesignPreset } from "./design";
import { usePresetFonts, buildFontFamily } from "./design/fonts";
```

- [ ] **Step 2: BUNDLED_FONTS 제거, useFonts 교체**

기존 `BUNDLED_FONTS`, `isSystemFont`, `useFonts` 함수 전부 제거.
대신 `usePresetFonts()` 사용.

- [ ] **Step 3: VideoThemeProvider → DesignPresetProvider**

```typescript
// Before:
<VideoThemeProvider theme={themeName} artStyle={artStyle}>
<AbsoluteFill style={{ backgroundColor: C.bg, fontFamily }}>

// After:
<DesignPresetProvider meta={manifest.meta}>
<SimpleVideoInner manifest={manifest} subtitleConfig={subtitleConfig} />
</DesignPresetProvider>
```

SimpleVideoInner를 분리하여 Provider 내부에서 `useDesignPreset()`, `usePresetFonts()`를 호출.

- [ ] **Step 4: 빌드 확인**
- [ ] **Step 5: 커밋**

```bash
git add remotion/src/SimpleVideo.tsx
git commit -m "refactor: migrate SimpleVideo to DesignPresetProvider"
```

---

### Task 11: CreativeScene.tsx — 하드코딩 디자인 값 교체

**Files:**
- Modify: `remotion/src/simple/CreativeScene.tsx`

가장 큰 파일(3400+ 줄). 교체 대상:

- [ ] **Step 1: MOOD_CONFIGS → 프리셋 moods와 merge**

```typescript
// Before: 하드코딩 MOOD_CONFIGS 직접 사용
const moodCfg = getMoodConfig(mood, themeAccent);

// After: 프리셋 moods를 기본값으로, 데이터 없으면 하드코딩 fallback
const preset = useDesignPreset();
function getMoodConfig(mood: string): MoodConfig {
  const override = preset.moods[mood];
  const fallback = { accent: preset.colors.accent, accentRgb: preset.colors.accentRgb, speed: 1.0, glow: 0.3 };
  return {
    accent: override?.accent ?? fallback.accent,
    accentRgb: override?.accentRgb ?? fallback.accentRgb,
    speed: override?.speed ?? fallback.speed,
    glow: override?.glow ?? fallback.glow,
  };
}
```

- [ ] **Step 2: MOOD_GRADIENTS → 프리셋에서 읽기**

```typescript
// Before:
const gradient = isDark ? MOOD_GRADIENTS[mood] : MOOD_GRADIENTS_WHITE[mood];

// After:
const preset = useDesignPreset();
const gradient = preset.moods[mood]?.gradient ?? `radial-gradient(ellipse 80% 60% at 50% 40%, ${preset.colors.bg} 0%, ${preset.colors.bg} 70%)`;
```

MOOD_GRADIENTS, MOOD_GRADIENTS_WHITE 상수 제거.

- [ ] **Step 3: getAccentFontSize / getBaseFontSize → 프리셋 typography**

```typescript
// Before:
function getAccentFontSize(emphasis: string): number { return 80; }
function getBaseFontSize(emphasis: string): number { return 48; }

// After:
// 이 함수들을 프리셋에서 읽도록 변경
const T = usePresetTypo();
const accentSize = T.headlineAccent;  // 80
const baseSize = T.headlineBase;      // 48
```

- [ ] **Step 4: 각 레이아웃의 하드코딩 px 값 교체**

모든 레이아웃 함수(renderItemsGrid, renderItemsList, renderBar, renderPie, renderLine, renderSplit, 등)에서:
- `padding: "60px 48px"` → `padding: \`${L.scenePadding[0]}px ${L.scenePadding[1]}px\``
- `gap: 16` → `L.itemsGap`
- `maxWidth: 1040` → `L.maxContentWidth`
- `borderRadius: 14` → `L.cardRadius`
- `fontSize: 28` → `T.itemText`
- `fontSize: 18` → `T.sourceText`
- etc.

**주의**: 값이 레이아웃마다 미묘하게 다른 경우(items_grid: maxWidth 1040, items_list: 940, bar: 800) → `maxContentWidth` 하나를 기준으로 레이아웃별 비율 계산, 또는 레이아웃별 토큰 추가 검토.

- [ ] **Step 5: 빌드 확인**
- [ ] **Step 6: 커밋**

```bash
git add remotion/src/simple/CreativeScene.tsx
git commit -m "refactor: migrate CreativeScene to DesignPreset Context"
```

---

### Task 12: MapSceneRenderer — FONT_DEFS 교체

**Files:**
- Modify: `remotion/src/map/MapSceneRenderer.tsx`

- [ ] **Step 1: vizStyles import 제거, design/fonts 사용**

```typescript
// Before:
import { FONT_DEFS } from "../visualizations/vizStyles";

// After:
import { usePresetFonts } from "../design/fonts";
```

기존 `useFonts()` 함수 전체를 `usePresetFonts()` 호출로 교체.

- [ ] **Step 2: 빌드 확인**
- [ ] **Step 3: 커밋**

```bash
git add remotion/src/map/MapSceneRenderer.tsx
git commit -m "refactor: migrate MapSceneRenderer fonts to design preset"
```

---

### Task 13: SingleScenePlayer + SceneEditor 마이그레이션

**Files:**
- Modify: `remotion/src/editor/SingleScenePlayer.tsx`
- Modify: `remotion/src/SceneEditor.tsx`

- [ ] **Step 1: SingleScenePlayer — DesignPresetProvider 래핑**

```typescript
// Before:
import { VideoThemeProvider, resolveVideoTheme } from "../simple/BuildingBlocks";
<VideoThemeProvider theme={themeName} artStyle={artStyle}>

// After:
import { DesignPresetProvider } from "../design";
<DesignPresetProvider meta={meta}>
```

- [ ] **Step 2: SceneEditor — DesignTokenProvider를 DesignPresetProvider로 교체**

SceneEditor는 현재 `DesignTokenProvider` (레거시)를 사용중. 이를 새 Provider로 교체.

```typescript
// Before:
import { DesignTokenProvider } from "./contexts/DesignTokenContext";
<DesignTokenProvider tokens={manifest.meta.designTokens}>

// After:
import { DesignPresetProvider } from "./design";
<DesignPresetProvider meta={manifest.meta}>
```

- [ ] **Step 3: 빌드 확인**
- [ ] **Step 4: 커밋**

```bash
git add remotion/src/editor/SingleScenePlayer.tsx remotion/src/SceneEditor.tsx
git commit -m "refactor: migrate SingleScenePlayer and SceneEditor to DesignPresetProvider"
```

---

## Chunk 5: Python 파이프라인 + 대시보드

### Task 14: build_manifest.py — designPreset 전달

**Files:**
- Modify: `auto_agent/scripts/build_manifest.py:266-280`

- [ ] **Step 1: meta에 designPreset 포함**

scene_specs.json에 `meta.designPreset`이 있으면 manifest에 그대로 전달:

```python
# build_manifest.py — manifest 조립 부분
design_preset = specs.get("meta", {}).get("designPreset", None)

manifest = {
    "meta": {
        "topic": topic,
        "resolution": {"width": 1920, "height": 1080},
        "fps": 30,
        "subtitleFont": font_family,
        "vizFont": font_family,
        "videoTheme": video_theme,
        **({"artStyle": art_style} if art_style else {}),
        **({"designPreset": design_preset} if design_preset else {}),
    },
    "scenes": scenes,
    "bgm": None,
}
```

- [ ] **Step 2: 커밋**

```bash
git add auto_agent/scripts/build_manifest.py
git commit -m "feat: pass designPreset through build_manifest"
```

---

### Task 15: design_presets.py — 스키마 확장

**Files:**
- Modify: `auto_agent/dashboard/design_presets.py`

- [ ] **Step 1: BUILTIN_PRESETS를 새 DesignPreset 스키마로 확장**

기존 `global`, `defaults`, `animation` 구조를 유지하면서, 새 `designPreset` 필드를 추가. `apply-preset` 엔드포인트가 `scene_specs.json`의 `meta.designPreset`에 전체 프리셋을 기록하도록 변경.

- [ ] **Step 2: apply-preset 엔드포인트 수정**

기존에 `meta.videoTheme`, `meta.artStyle`, `meta.vizFont`만 설정하던 것을, `meta.designPreset` 전체를 기록하도록 확장.

```python
# apply_preset_to_project에서:
if "meta" not in specs:
    specs["meta"] = {}

# 기존 필드 유지 (하위호환)
if gl.get("videoTheme"):
    specs["meta"]["videoTheme"] = gl["videoTheme"]
if gl.get("artStyle"):
    specs["meta"]["artStyle"] = gl["artStyle"]

# 새 designPreset 필드
if preset.get("designPreset"):
    specs["meta"]["designPreset"] = preset["designPreset"]
```

- [ ] **Step 3: 커밋**

```bash
git add auto_agent/dashboard/design_presets.py
git commit -m "feat: extend design presets API for full DesignPreset schema"
```

---

### Task 16: 대시보드 UI 확장

**Files:**
- Modify: `auto_agent/dashboard/templates/partials/_design.html`

- [ ] **Step 1: 편집 폼에 새 섹션 추가**

기존 "글로벌 설정", "씬 기본값", "애니메이션" 섹션에 추가:
- **폰트 설정** — body font family, title font 선택
- **타이포 스케일** — headlineAccent, headlineBase 등 주요 사이즈 슬라이더
- **레이아웃** — cardRadius, gap, scenePadding 등 슬라이더
- **맵 테마** — defaultMapTheme 드롭다운 (10개 테마)
- **자막 스타일** — keywordColor, strokeWidth 등

- [ ] **Step 2: _collectForm에 새 필드 반영**

```javascript
function _collectForm() {
  return {
    name: _v('preset-name'),
    description: _v('preset-desc'),
    // 기존 필드 유지
    global: { ... },
    defaults: { ... },
    animation: { ... },
    // 새 필드
    designPreset: {
      colors: { accent: _v('dp-accent'), positive: _v('dp-positive'), ... },
      fonts: { body: { family: _v('dp-bodyFont') } },
      typography: { headlineAccent: parseInt(_v('dp-headlineAccent')), ... },
      layout: { cardRadius: parseInt(_v('dp-cardRadius')), gap: parseInt(_v('dp-gap')), ... },
      map: { defaultTheme: _v('dp-mapTheme') },
      subtitle: { keywordColor: _v('dp-keywordColor'), ... },
    },
  };
}
```

- [ ] **Step 3: 프리뷰 그리드 확장**

컬러 스와치 외에 폰트 프리뷰, 카드 미니 프리뷰 추가.

- [ ] **Step 4: 커밋**

```bash
git add auto_agent/dashboard/templates/partials/_design.html
git commit -m "feat: extend dashboard design editor with full preset controls"
```

---

## Chunk 6: 정리 + remotion_template 동기화

### Task 17: vizStyles 리다이렉트 심 제거

**Files:**
- Modify: 모든 vizStyles import를 사용하던 파일들

Chunk 3-4에서 MapSceneRenderer, VisualizationRenderer 등이 이미 design/ 모듈로 이전됨. 남은 참조가 있으면 정리.

- [ ] **Step 1: 잔여 import 검색**

```bash
cd /Users/hannah/Projects/auto_kairos_v3
grep -r "vizStyles" remotion/src/ --include="*.ts" --include="*.tsx" | grep -v "legacy" | grep -v "vizStyles.ts"
```

- [ ] **Step 2: 남은 import를 design/ 모듈로 교체**
- [ ] **Step 3: 리다이렉트 심 파일 삭제 가능 여부 확인 후 삭제**
- [ ] **Step 4: 커밋**

```bash
git add -A
git commit -m "cleanup: remove vizStyles redirect shim"
```

---

### Task 18: remotion_template 동기화

**Files:**
- `auto_agent/remotion_template/src/` — remotion/src/ 와 동기화

CLAUDE.md 규칙: "remotion/src/ 수정 → auto_agent/remotion_template/src/에도 반드시 동일 수정"

- [ ] **Step 1: remotion_template에 design/ 디렉토리 복사**

```bash
cp -r remotion/src/design/ auto_agent/remotion_template/src/design/
```

- [ ] **Step 2: 변경된 파일들 동기화**

```bash
cp remotion/src/simple/BuildingBlocks.tsx auto_agent/remotion_template/src/simple/
cp remotion/src/simple/CreativeScene.tsx auto_agent/remotion_template/src/simple/
cp remotion/src/SimpleVideo.tsx auto_agent/remotion_template/src/
cp remotion/src/map/MapSceneRenderer.tsx auto_agent/remotion_template/src/map/
cp remotion/src/editor/SingleScenePlayer.tsx auto_agent/remotion_template/src/editor/
cp remotion/src/SceneEditor.tsx auto_agent/remotion_template/src/
cp remotion/src/types/manifest.ts auto_agent/remotion_template/src/types/
cp remotion/src/visualizations/vizStyles.legacy.ts auto_agent/remotion_template/src/visualizations/
```

- [ ] **Step 3: remotion_template에서 빌드 확인**

```bash
cd auto_agent/remotion_template && npm run build
```

- [ ] **Step 4: 커밋**

```bash
git add auto_agent/remotion_template/
git commit -m "sync: update remotion_template with design preset system"
```

---

### Task 19: remotion-design-system.md 업데이트

**Files:**
- Modify: `auto_agent/data/skills/shared/remotion-design-system.md`

LLM 에이전트(visual-composer, qa-reviewer)가 참조하는 디자인 가이드를 새 프리셋 시스템에 맞게 업데이트.

- [ ] **Step 1: 섹션 1 (컬러 시스템) 업데이트**

```markdown
## 1. 컬러 시스템 — DesignPreset 기반

프로젝트별 디자인 프리셋(`meta.designPreset`)으로 전체 컬러를 제어합니다.
프리셋이 없으면 아트스타일 기본 프리셋 → DEFAULT_PRESET 순으로 fallback합니다.

기본 팔레트 (default preset):
  bg:         '#0A0A0A'
  text:       '#FFFFFF'
  accent:     '#F59E0B'     ← 아트스타일별로 다름
  positive:   '#22C55E'
  negative:   '#EF4444'

아트스타일별 accent:
  semoji:         '#6366F1' (인디고)
  lego:           '#EF4444' (레드)
  quirky_cartoon: '#F59E0B' (앰버)
  stickman_cute:  '#10B981' (에메랄드)
```

- [ ] **Step 2: white 테마, 맵 스타일 10종 등 outdated 내용 업데이트**
- [ ] **Step 3: 커밋**

```bash
git add auto_agent/data/skills/shared/remotion-design-system.md
git commit -m "docs: update remotion-design-system.md for preset system"
```

---

### Task 20: 최종 빌드 + 스모크 테스트

- [ ] **Step 1: Remotion 빌드 확인**

```bash
cd /Users/hannah/Projects/auto_kairos_v3/remotion
export PATH="/Users/hannah/local/nodejs/node-v22.14.0-darwin-x64/bin:$PATH"
npx tsc --noEmit
```

- [ ] **Step 2: Remotion Studio 실행 확인**

```bash
npx remotion studio
```

Studio에서 SimpleVideo가 정상 렌더링되는지 확인.

- [ ] **Step 3: 대시보드 서버 실행 확인**

```bash
cd /Users/hannah/Projects/auto_kairos_v3
set -a; source .env; set +a
python3 -m uvicorn app:app --reload --port 8000
```

`/api/design-presets` 엔드포인트가 정상 응답하는지 확인.

- [ ] **Step 4: 최종 커밋**

```bash
git add -A
git commit -m "feat: complete design preset system implementation"
```
