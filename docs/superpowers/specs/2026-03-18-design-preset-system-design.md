# Design Preset System — 아트스타일별 디자인 프리셋

## 목적

Remotion SimpleVideo 렌더 파이프라인의 **모든 하드코딩 디자인 값**(컬러, 폰트, 타이포, 레이아웃, 너비/높이, 무드, 맵 테마, 자막)을 **아트스타일별 프리셋**으로 추출하여 외부에서 관리한다.

## 현재 문제

1. 디자인 값이 `BuildingBlocks.tsx`, `CreativeScene.tsx`, `SimpleVideo.tsx`, `vizStyles.ts`, `mapTheme.ts` 등 **6개 파일에 하드코딩**
2. 아트스타일을 바꿔도 **accent 색상 1개만** 변경됨 — 폰트, 사이즈, 간격, 맵 테마 등은 전부 고정
3. 대시보드 프리셋 시스템(`design_presets.py`)이 존재하지만, Remotion 렌더링과 약하게 연결됨
4. `vizStyles.ts`는 레거시 시스템으로 SimpleVideo에서 미사용이나 MapSceneRenderer에서 FONT_DEFS만 참조

## 설계 결정

- **A안 채택**: manifest.json 경유 — 프리셋을 `scene_specs → build_manifest → manifest.json`에 포함시켜 Remotion이 props로 받음
- Studio에서는 Props Editor로 개별 값 오버라이드 가능 (deep merge)
- 대시보드에서 프리셋 CRUD + 프로젝트 적용
- 향후 디자인 마켓에서 프리셋을 불러와 적용 가능하도록 설계

## 데이터 흐름

```
대시보드 프리셋 편집기 (확장)
    ↓ (저장)
workspace/.auto_agent/design_presets/{name}.json
    ↓ (apply-preset → scene_specs.json)
scene_specs.json → meta.designPreset = { 전체 디자인 설정 }
    ↓ (build_manifest.py)
manifest.json → meta.designPreset (그대로 전달)
    ↓ (Remotion)
SimpleVideo → DesignPresetProvider (React Context)
    → CreativeScene (컬러, 타이포, 레이아웃, 무드 적용)
    → BuildingBlocks (모든 UI 컴포넌트가 Context에서 읽음)
    → MapSceneRenderer (맵 테마 + 폰트 적용)
    → SubtitleOverlay (자막 스타일 적용)
    → SingleScenePlayer (동일한 Provider 사용 — 에디터 동기화)
```

## 프리셋 스키마

```typescript
interface FontFile {
  file: string;    // "fonts/Pretendard-Regular.otf"
  weight: string;  // "400"
}

interface DesignPreset {
  // ── 메타 ──
  id: string;                      // "semoji_dark_v1"
  name: string;                    // "세모지 다크"
  description: string;
  version: number;                 // 스키마 버전 (마켓 호환용)
  author?: string;                 // 공유/마켓용
  tags?: string[];                 // ["dark", "semoji", "교육"]
  artStyle?: string;               // 연결된 아트스타일 (선택)
  baseTheme: "dark" | "white";     // 기본 밝기

  // ── 1. 컬러 팔레트 ──
  colors: {
    bg: string;
    text: string;
    textMuted: string;
    textDim: string;
    accent: string;
    accentRgb: string;             // rgba용 "99,102,241"
    accentBg: string;
    accentBorder: string;
    accentSoft: string;
    cardBg: string;
    cardBorder: string;
    divider: string;
    // 시맨틱
    positive: string;              // #22C55E
    negative: string;              // #EF4444
    warning: string;               // #F59E0B
    // 순위 (금/은/동)
    rank: [string, string, string]; // ["#FFD700", "#C0C0C0", "#CD7F32"]
  };

  // ── 2. 폰트 ──
  fonts: {
    body: { family: string; fallback: string; files: FontFile[] };
    title?: { family: string; fallback: string; files: FontFile[] };
    quote?: { family: string };     // 인용부호 전용 (Georgia 등)
  };

  // ── 3. 타이포 스케일 ──
  typography: {
    headlineAccent: number;         // 80 — CreativeScene {{}} 강조 텍스트
    headlineBase: number;           // 48 — CreativeScene 기본 헤드라인
    metricValue: number;            // 60 — MetricCard, metric_spotlight 큰 숫자
    itemText: number;               // 28 — items_list, items_grid 아이템 텍스트
    descText: number;               // 20 — descriptions, 부연 설명
    labelText: number;              // 22 — 차트 라벨, 컴포넌트 라벨
    sourceText: number;             // 18 — 출처 텍스트
    captionText: number;            // 18 — 캡션
    quoteText: number;              // 44 — 인용문 본문
    quoteMarkSize: number;          // 120 — 큰 인용부호
    chartTitle: number;             // 48 — 차트 제목
    chartValue: number;             // 28 — 차트 값 텍스트
    pillText: number;               // 20
    tagText: { sm: number; md: number; lg: number }; // 20/26/36
    progressLabel: number;          // 36 — ProgressBar/StatusDot 라벨
    metricCardLabel: number;        // 20
    metricCardChange: number;       // 18
    comparisonLabel: number;        // 24
    comparisonValue: number;        // 48
    comparisonSub: number;          // 24
    timelineDotLabel: number;       // 28
    stepBadgeLabel: number;         // 28
    calloutText: number;            // 28
    annotationText: number;         // 36
    miniBarLabel: number;           // 30
    flagCardLabel: number;          // 24
    splitLabel: number;             // 28 — split 상단 라벨
    splitVsText: number;            // 30 — VS 텍스트
  };

  // ── 4. 레이아웃 토큰 ──
  layout: {
    // 씬 전체
    scenePadding: [number, number]; // [vertical, horizontal] — [60, 48]
    contentWidth: string;           // "78%" — 이미지 없을 때 메인 콘텐츠 폭
    headlineMaxWidth: string;       // "90%"
    maxContentWidth: number;        // 1100 — 레이아웃 최대폭 기준값

    // 간격
    gap: number;                    // 24 — 기본 간격
    itemsGap: number;              // 16 — 아이템 간 간격
    sectionMarginTop: number;       // 32 — 섹션 상단 여백

    // 카드
    cardRadius: number;             // 12
    cardPadding: [number, number];  // [24, 28]

    // 기타 라운딩
    pillRadius: number;             // 20
    tagRadius: number;              // 6

    // 구분선
    dividerThickness: number;       // 1

    // 배지/아이콘 기본 크기
    badgeSize: number;              // 48 — CircleBadge, IconBadge, FlagBadge, LogoBadge
    imageBadgeSize: number;         // 56
    rankBadgeSize: number;          // 72
    stepBadgeSize: number;          // 56
    timelineDotSize: number;        // 32
    statusDotSize: number;          // 16
    logoIconSize: number;           // 64 — 로고 그리드용

    // 차트/바
    barHeight: number;              // 32
    barLabelWidth: number;          // 200
    barValueWidth: number;          // 120
    sparklineSize: [number, number]; // [280, 72]
    progressBarHeight: number;      // 16
    miniBarHeight: number;          // 12
    pieLegendSwatchSize: number;    // 20

    // 연결선
    connectorLength: number;        // 40
    connectorWidth: number;         // 3
    annotationLineLength: number;   // 100
    calloutBorderWidth: number;     // 5
    timelineConnectorHeight: number; // 36
    timelineConnectorWidth: number; // 2

    // 분할(split) 레이아웃
    splitDividerWidth: number;      // 2
    splitVsWidth: number;           // 60

    // person_card / card_carousel
    personCardImgHeight: number;    // 아이템 수 기반 계산의 기준값
    carouselCardWidth: number;      // 260
    carouselImgHeight: number;      // 140

    // Tag 패딩
    tagPadding: {
      sm: [number, number];         // [8, 18]
      md: [number, number];         // [12, 28]
      lg: [number, number];         // [16, 36]
    };

    // Pill 패딩
    pillPadding: [number, number];  // [8, 20]
  };

  // ── 5. 무드 오버라이드 ──
  moods: Record<string, {
    accent?: string;
    accentRgb?: string;
    speed?: number;                 // 애니메이션 속도 배율
    glow?: number;                  // 글로우 강도
    gradient?: string;              // 배경 그라데이션
  }>;

  // ── 6. 맵 ──
  map: {
    defaultTheme: string;           // "modern_clean"
    fontOverride?: string;          // 맵 전용 폰트 (없으면 body 사용)
  };

  // ── 7. 자막 ──
  subtitle: {
    fontFamily?: string;            // 없으면 body.family 사용
    fontSize: number;               // 44
    fontWeight: number;             // 700
    color: string;                  // "#FFFFFF"
    strokeColor: string;            // "#3D3B2F"
    strokeWidth: number;            // 2
    keywordColor: string;           // accent와 연동 가능
    keywordStrokeColor: string;     // "#5A4B00"
    bottomOffset: number;           // 30
    maxWidth: string;               // "85%"
    lineHeight: number;             // 1.5
  };

  // ── 8. 애니메이션 기본값 ──
  animation: {
    stagger: number;                // 8 — 아이템 간 지연 프레임
    itemDuration: number;           // 20 — 아이템 등장 프레임
    easing: string;                 // "easeOut"
    titleFadeIn: number;            // 15 — 제목 페이드인 프레임
  };

  // ── 9. 배경 패턴 ──
  background: {
    pattern: "dots" | "grid" | "lines" | "none";
    opacity: number;                // 0.02
  };
}
```

## 기본 프리셋 (5종)

### default (아트스타일 미지정)
- baseTheme: "dark", accent: "#F59E0B" (앰버)
- body font: Pretendard, 맵: modern_clean

### semoji
- baseTheme: "dark", accent: "#6366F1" (인디고)
- 둥근 느낌 — cardRadius 크게, gap 넉넉, 부드러운 타이포
- 맵: modern_clean

### lego
- baseTheme: "dark", accent: "#EF4444" (레드)
- 블록 느낌 — 뚜렷한 보더, 강한 대비
- 맵: minimal_light

### quirky_cartoon
- baseTheme: "dark", accent: "#F59E0B" (앰버, 기본)
- 손그림 느낌 — 둥근 라운딩, 큰 텍스트
- 맵: warm_earth

### stickman_cute
- baseTheme: "dark", accent: "#10B981" (에메랄드)
- 깔끔한 교육 느낌 — 타이트한 간격, 정돈된 레이아웃
- 맵: clean_white

## Remotion 파일 구조 변경

### 새 파일
```
remotion/src/design/
  types.ts                         ← DesignPreset 인터페이스 + FontFile
  defaults.ts                      ← DEFAULT_PRESET (현재 하드코딩 값 그대로)
  presets/
    semoji.ts                      ← 아트스타일별 프리셋 (default와의 diff만)
    lego.ts
    quirky_cartoon.ts
    stickman_cute.ts
  DesignPresetContext.tsx           ← Provider + useDesignPreset() 훅
  fonts.ts                         ← useFonts() 통합 (SimpleVideo/MapScene 공유)
  resolvePreset.ts                 ← manifest → 프리셋 해석 (artStyle fallback 포함)
```

### 수정 파일
```
remotion/src/simple/BuildingBlocks.tsx
  - COLORS_DARK/WHITE, ART_STYLE_ACCENTS 제거
  - useC() → useDesignPreset().colors 로 전환
  - 모든 컴포넌트의 하드코딩 값 → Context에서 읽기
  - 전역 C 기본값 → useC() 통일 (7개 컴포넌트 수정)

remotion/src/simple/CreativeScene.tsx
  - MOOD_CONFIGS 하드코딩 → useDesignPreset().moods와 merge
  - MOOD_GRADIENTS → 프리셋에서 읽기
  - getAccentFontSize/getBaseFontSize → 프리셋 typography에서 읽기
  - 모든 레이아웃의 하드코딩 px 값 → 프리셋 layout에서 읽기

remotion/src/SimpleVideo.tsx
  - BUNDLED_FONTS 제거 → design/fonts.ts의 useFonts() 사용
  - VideoThemeProvider → DesignPresetProvider로 교체
  - resolveVideoTheme → resolvePreset

remotion/src/map/MapSceneRenderer.tsx
  - vizStyles.ts FONT_DEFS import 제거 → design/fonts.ts 사용

remotion/src/editor/SingleScenePlayer.tsx
  - 동일한 DesignPresetProvider 래핑

remotion/src/types/manifest.ts
  - DesignPreset 타입 추가 (meta.designPreset)
  - 기존 DesignTokens는 deprecated 처리

remotion/src/visualizations/vizStyles.ts
  → vizStyles.legacy.ts 이름 변경 (백업)
  → 참조하던 파일들의 import 제거 또는 리다이렉트
```

### Python 수정 파일
```
auto_agent/scripts/build_manifest.py
  - meta.designPreset 필드 생성/전달

auto_agent/dashboard/design_presets.py
  - BUILTIN_PRESETS 스키마를 새 DesignPreset 형식으로 확장
  - 프리셋 CRUD API 스키마 업데이트

auto_agent/dashboard/templates/partials/_design.html
  - 대시보드 UI에 폰트, 타이포, 레이아웃, 맵 테마 편집 추가
```

## Deep Merge 전략

```
1순위: manifest.meta.designPreset (Studio에서 오버라이드한 값)
2순위: artStyle 기본 프리셋 (semoji.ts, lego.ts 등)
3순위: DEFAULT_PRESET (defaults.ts)
```

resolvePreset 흐름:
```typescript
function resolvePreset(manifest: SceneManifest): DesignPreset {
  const base = DEFAULT_PRESET;
  const artPreset = manifest.meta.artStyle
    ? ART_PRESETS[extractStyleName(manifest.meta.artStyle)]
    : {};
  const userOverride = manifest.meta.designPreset ?? {};
  return deepMerge(base, artPreset, userOverride);
}
```

## 공유/마켓 설계 (향후)

- 프리셋 JSON은 독립적으로 export/import 가능 (`version` 필드로 호환성 관리)
- `author`, `tags` 필드로 마켓 검색/필터링
- 프리셋 파일에 `fonts.files` 경로가 포함되므로, 마켓에서 다운로드 시 폰트 파일도 함께 번들
- 프리셋 thumbnail 생성 (대시보드에서 프리뷰 카드 렌더링)

## 하위호환성

- `videoTheme` + `artStyle`만 있고 `designPreset`이 없는 기존 매니페스트:
  - `resolvePreset`이 `baseTheme`과 `artStyle`에서 프리셋 자동 생성
  - 기존 프로젝트 깨지지 않음
- `DesignTokens` (레거시) → deprecated, 새 프로젝트에서는 사용하지 않음
