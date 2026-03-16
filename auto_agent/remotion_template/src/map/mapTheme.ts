/**
 * 통합 맵 테마 시스템.
 *
 * 색상뿐 아니라 마커 모양, 타이틀 레이아웃, 경로 스타일, 라벨 배지,
 * 분위기 효과(비네팅/그레인/테두리), 애니메이션 타이밍까지
 * 테마별로 완전히 다른 시각적 정체성을 정의한다.
 */

/* ══════════════════════════════════════════════
   SUB-INTERFACES
   ══════════════════════════════════════════════ */

/** 맵 표면 (D3 SVG / MapLibre CSS 필터) */
export interface MapSurfaceTheme {
  ocean: string;
  land: string;
  landStroke: string;
  landStrokeWidth: number;
  borderStroke: string;
  borderStrokeWidth: number;
  borderDash?: string;
  adminStroke?: string;
  adminStrokeWidth?: number;
  adminOpacity?: number;
  /** 해안선 */
  coastlineStroke?: string;
  coastlineStrokeWidth?: number;
  /** 강 */
  riverStroke?: string;
  riverStrokeWidth?: number;
  riverOpacity?: number;
  /** 호수 */
  lakeFill?: string;
  lakeStroke?: string;
  lakeStrokeWidth?: number;
  cssFilter?: string;
}

/** 마커 모양 */
export type MarkerShape = "circle" | "drop_pin" | "crosshair" | "diamond" | "ring";

/** 마커 테마 */
export interface MarkerTheme {
  shape: MarkerShape;
  size: number;
  dotSize: number;
  borderWidth: number;
  borderColor: string;
  shadow: string;
  pulseAmplitude: number;
  /** 라벨 배지 */
  labelBg: string;
  labelRadius: number;
  labelFontSize: number;
  labelFontWeight: number;
  labelColor: string;
  labelShadow: string;
  labelFontFamily?: string;
}

/** 타이틀 레이아웃 */
export type TitleLayout =
  | "top_center_card"
  | "left_banner"
  | "bottom_bar"
  | "floating_glass"
  | "corner_badge";

/** 타이틀 테마 */
export interface TitleTheme {
  layout: TitleLayout;
  background: string;
  borderRadius: number;
  padding: string;
  fontSize: number;
  fontWeight: number;
  color: string;
  fontFamily: string;
  shadow: string;
  letterSpacing: string;
  border?: string;
  backdropFilter?: string;
  /** 출처 텍스트 */
  source: {
    fontSize: number;
    color: string;
    fontFamily: string;
  };
  /** 애니메이션 */
  animation: {
    fadeInStart: number;
    fadeInEnd: number;
    slideDistance: number;
    slideDirection: "down" | "up" | "left" | "right";
  };
}

/** 경로 스타일 */
export type RouteStyle = "solid" | "dashed" | "glow";

/** 경로 테마 */
export interface RouteTheme {
  style: RouteStyle;
  defaultColor: string;
  defaultWidth: number;
  lineCap: "round" | "butt" | "square";
  lineJoin: "round" | "miter" | "bevel";
  opacity: number;
  dashArray?: string;
  glow?: { color: string; width: number; opacity: number };
}

/** 라벨 스타일 */
export type LabelStyle = "floating" | "card" | "pill" | "tag" | "underline";

/** 라벨 테마 */
export interface LabelTheme {
  style: LabelStyle;
  fontFamily: string;
  fontSize: number;
  fontWeight: number;
  color: string;
  textShadow: string;
  badgeBg?: string;
  badgeRadius?: number;
  badgePadding?: string;
  badgeShadow?: string;
  badgeBorder?: string;
  fadeInFrames: number;
}

/** 영역 오버레이 테마 */
export interface TerritoryTheme {
  strokeWidth: number;
  strokeOpacityMultiplier: number;
}

/** 분위기 효과 */
export type BorderDecoration = "none" | "ornate" | "thin_line" | "corner_marks";

export interface AtmosphereTheme {
  vignette: number;
  vignetteColor?: string;
  grain: number;
  borderDecoration: BorderDecoration;
  borderColor?: string;
  borderWidth?: number;
}

/** 애니메이션 타이밍 */
export interface MapAnimationTheme {
  markerFadeIn: number;
  markerScaleFrom: number;
  labelFadeIn: number;
  routeDrawDelay: number;
}

/* ══════════════════════════════════════════════
   UNIFIED THEME
   ══════════════════════════════════════════════ */

export interface MapTheme {
  name: string;
  surface: MapSurfaceTheme;
  marker: MarkerTheme;
  title: TitleTheme;
  route: RouteTheme;
  label: LabelTheme;
  territory: TerritoryTheme;
  atmosphere: AtmosphereTheme;
  animation: MapAnimationTheme;
}

/* ══════════════════════════════════════════════
   8종 테마 정의
   ══════════════════════════════════════════════ */

const VINTAGE_PARCHMENT: MapTheme = {
  name: "vintage_parchment",
  surface: {
    ocean: "#D4C5A9",
    land: "#F5E6C8",
    landStroke: "#5E4830",
    landStrokeWidth: 1.8,
    borderStroke: "#3E2E18",
    borderStrokeWidth: 1.0,
    borderDash: "4,2",
    adminStroke: "#7A6A4C",
    adminStrokeWidth: 0.7,
    adminOpacity: 0.6,
    coastlineStroke: "#5E4830",
    coastlineStrokeWidth: 1.2,
    riverStroke: "#7A6A4C",
    riverStrokeWidth: 1.0,
    riverOpacity: 0.6,
    lakeFill: "#CFC0A6",
    lakeStroke: "#7A6A4C",
    lakeStrokeWidth: 0.6,
  },
  marker: {
    shape: "drop_pin",
    size: 28,
    dotSize: 14,
    borderWidth: 2,
    borderColor: "#F5E6C8",
    shadow: "0 2px 6px rgba(107,91,69,0.4)",
    pulseAmplitude: 0.06,
    labelBg: "transparent",
    labelRadius: 6,
    labelFontSize: 20,
    labelFontWeight: 700,
    labelColor: "#5A4A3A",
    labelShadow: "none",
  },
  title: {
    layout: "top_center_card",
    background: "rgba(245,230,200,0.92)",
    borderRadius: 10,
    padding: "12px 32px",
    fontSize: 42,
    fontWeight: 700,
    color: "#4A3A2A",
    fontFamily: "'Pretendard', sans-serif",
    shadow: "0 3px 12px rgba(107,91,69,0.2)",
    letterSpacing: "-0.01em",
    border: "1px solid rgba(139,115,85,0.3)",
    source: {
      fontSize: 16,
      color: "#8B7355",
      fontFamily: "'Pretendard', sans-serif",
    },
    animation: { fadeInStart: 8, fadeInEnd: 22, slideDistance: 20, slideDirection: "down" },
  },
  route: {
    style: "dashed",
    defaultColor: "#8B5E3C",
    defaultWidth: 4,
    lineCap: "round",
    lineJoin: "round",
    opacity: 0.85,
    dashArray: "10,6",
  },
  label: {
    style: "tag",
    fontFamily: "'Pretendard', sans-serif",
    fontSize: 22,
    fontWeight: 600,
    color: "#5A4A3A",
    textShadow: "none",
    badgeBg: "rgba(245,230,200,0.88)",
    badgeRadius: 4,
    badgePadding: "3px 10px",
    badgeShadow: "0 1px 4px rgba(107,91,69,0.2)",
    badgeBorder: "1px solid rgba(139,115,85,0.25)",
    fadeInFrames: 16,
  },
  territory: { strokeWidth: 1.5, strokeOpacityMultiplier: 2 },
  atmosphere: {
    vignette: 0.3,
    vignetteColor: "#8B7355",
    grain: 0.12,
    borderDecoration: "ornate",
    borderColor: "#8B7355",
    borderWidth: 2,
  },
  animation: { markerFadeIn: 18, markerScaleFrom: 0.3, labelFadeIn: 16, routeDrawDelay: 15 },
};

const MINIMAL_LIGHT: MapTheme = {
  name: "minimal_light",
  surface: {
    ocean: "#E8EDF2",
    land: "#FAFAFA",
    landStroke: "#708090",
    landStrokeWidth: 1.2,
    borderStroke: "#7A8898",
    borderStrokeWidth: 0.8,
    adminStroke: "#8A96A8",
    adminStrokeWidth: 0.6,
    adminOpacity: 0.5,
    coastlineStroke: "#708090",
    coastlineStrokeWidth: 0.8,
    riverStroke: "#7888A0",
    riverStrokeWidth: 0.7,
    riverOpacity: 0.55,
    lakeFill: "#C8D4E0",
    lakeStroke: "#7888A0",
    lakeStrokeWidth: 0.5,
  },
  marker: {
    shape: "circle",
    size: 16,
    dotSize: 10,
    borderWidth: 2.5,
    borderColor: "#FFFFFF",
    shadow: "0 1px 4px rgba(0,0,0,0.12)",
    pulseAmplitude: 0.05,
    labelBg: "transparent",
    labelRadius: 20,
    labelFontSize: 18,
    labelFontWeight: 600,
    labelColor: "#3A4450",
    labelShadow: "none",
  },
  title: {
    layout: "top_center_card",
    background: "rgba(255,255,255,0.85)",
    borderRadius: 10,
    padding: "12px 32px",
    fontSize: 36,
    fontWeight: 700,
    color: "#2A3440",
    fontFamily: "'Pretendard', sans-serif",
    shadow: "0 3px 12px rgba(0,0,0,0.06)",
    letterSpacing: "-0.01em",
    source: {
      fontSize: 14,
      color: "#8A95A2",
      fontFamily: "'Pretendard', sans-serif",
    },
    animation: { fadeInStart: 6, fadeInEnd: 16, slideDistance: 15, slideDirection: "down" },
  },
  route: {
    style: "solid",
    defaultColor: "#4A8FE7",
    defaultWidth: 3.5,
    lineCap: "round",
    lineJoin: "round",
    opacity: 0.9,
  },
  label: {
    style: "pill",
    fontFamily: "'Pretendard', sans-serif",
    fontSize: 20,
    fontWeight: 600,
    color: "#3A4450",
    textShadow: "none",
    badgeBg: "rgba(255,255,255,0.88)",
    badgeRadius: 16,
    badgePadding: "4px 14px",
    badgeShadow: "0 1px 4px rgba(0,0,0,0.08)",
    fadeInFrames: 10,
  },
  territory: { strokeWidth: 1, strokeOpacityMultiplier: 2 },
  atmosphere: {
    vignette: 0,
    grain: 0,
    borderDecoration: "none",
  },
  animation: { markerFadeIn: 12, markerScaleFrom: 0.4, labelFadeIn: 10, routeDrawDelay: 12 },
};

const DARK_ELEGANT: MapTheme = {
  name: "dark_elegant",
  surface: {
    ocean: "#1A1A2E",
    land: "#2D2D44",
    landStroke: "#8888BB",
    landStrokeWidth: 1.4,
    borderStroke: "#9999CC",
    borderStrokeWidth: 1.2,
    adminStroke: "#60608A",
    adminStrokeWidth: 0.6,
    adminOpacity: 0.5,
    coastlineStroke: "#7272A0",
    coastlineStrokeWidth: 1.0,
    riverStroke: "#60608A",
    riverStrokeWidth: 0.7,
    riverOpacity: 0.55,
    lakeFill: "#22223A",
    lakeStroke: "#60608A",
    lakeStrokeWidth: 0.5,
  },
  marker: {
    shape: "ring",
    size: 26,
    dotSize: 14,
    borderWidth: 3,
    borderColor: "#D4AF37",
    shadow: "0 0 12px rgba(212,175,55,0.4)",
    pulseAmplitude: 0.07,
    labelBg: "transparent",
    labelRadius: 8,
    labelFontSize: 20,
    labelFontWeight: 600,
    labelColor: "#E8DCC8",
    labelShadow: "none",
    labelFontFamily: "'Pretendard', sans-serif",
  },
  title: {
    layout: "top_center_card",
    background: "rgba(26,26,46,0.75)",
    borderRadius: 14,
    padding: "14px 36px",
    fontSize: 42,
    fontWeight: 700,
    color: "#E8DCC8",
    fontFamily: "'Pretendard', sans-serif",
    shadow: "0 4px 20px rgba(0,0,0,0.3)",
    letterSpacing: "-0.01em",
    border: "1px solid rgba(212,175,55,0.2)",
    backdropFilter: "blur(12px)",
    source: {
      fontSize: 15,
      color: "#B0B0CC",
      fontFamily: "'Pretendard', sans-serif",
    },
    animation: { fadeInStart: 10, fadeInEnd: 24, slideDistance: 20, slideDirection: "down" },
  },
  route: {
    style: "glow",
    defaultColor: "#D4AF37",
    defaultWidth: 3.5,
    lineCap: "round",
    lineJoin: "round",
    opacity: 0.9,
    glow: { color: "#D4AF37", width: 12, opacity: 0.25 },
  },
  label: {
    style: "floating",
    fontFamily: "'Pretendard', sans-serif",
    fontSize: 22,
    fontWeight: 600,
    color: "#E8DCC8",
    textShadow: "0 0 10px rgba(212,175,55,0.3), 0 1px 3px rgba(0,0,0,0.5)",
    fadeInFrames: 14,
  },
  territory: { strokeWidth: 1.5, strokeOpacityMultiplier: 2 },
  atmosphere: {
    vignette: 0.5,
    vignetteColor: "#0A0A1A",
    grain: 0.05,
    borderDecoration: "none",
  },
  animation: { markerFadeIn: 18, markerScaleFrom: 0.3, labelFadeIn: 14, routeDrawDelay: 18 },
};

const BLUEPRINT: MapTheme = {
  name: "blueprint",
  surface: {
    ocean: "#0F2942",
    land: "#1B3A5C",
    landStroke: "#3A6FA5",
    landStrokeWidth: 1.0,
    borderStroke: "#5A8FBF",
    borderStrokeWidth: 0.6,
    adminStroke: "#2A5A85",
    adminStrokeWidth: 0.3,
    adminOpacity: 0.5,
    coastlineStroke: "#3A6FA5",
    coastlineStrokeWidth: 0.7,
    riverStroke: "#2A5A85",
    riverStrokeWidth: 0.5,
    riverOpacity: 0.5,
    lakeFill: "#143252",
    lakeStroke: "#2A5A85",
    lakeStrokeWidth: 0.3,
  },
  marker: {
    shape: "crosshair",
    size: 28,
    dotSize: 16,
    borderWidth: 0,
    borderColor: "transparent",
    shadow: "0 0 8px rgba(122,176,218,0.5)",
    pulseAmplitude: 0.06,
    labelBg: "transparent",
    labelRadius: 3,
    labelFontSize: 18,
    labelFontWeight: 600,
    labelColor: "#7AB0DA",
    labelShadow: "none",
    labelFontFamily: "'Pretendard', monospace",
  },
  title: {
    layout: "top_center_card",
    background: "rgba(15,41,66,0.92)",
    borderRadius: 6,
    padding: "12px 32px",
    fontSize: 36,
    fontWeight: 600,
    color: "#A0D0F0",
    fontFamily: "'Pretendard', sans-serif",
    shadow: "0 2px 8px rgba(0,0,0,0.3)",
    letterSpacing: "0.01em",
    border: "1px solid rgba(90,143,191,0.35)",
    source: {
      fontSize: 14,
      color: "#8AB8D8",
      fontFamily: "'Pretendard', sans-serif",
    },
    animation: { fadeInStart: 4, fadeInEnd: 14, slideDistance: 15, slideDirection: "down" },
  },
  route: {
    style: "dashed",
    defaultColor: "#7AB0DA",
    defaultWidth: 3,
    lineCap: "butt",
    lineJoin: "miter",
    opacity: 0.85,
    dashArray: "8,5",
  },
  label: {
    style: "underline",
    fontFamily: "'Pretendard', monospace",
    fontSize: 20,
    fontWeight: 500,
    color: "#9AC0E0",
    textShadow: "0 1px 2px rgba(0,0,0,0.5)",
    badgeBorder: "2px solid #5A8FBF",
    fadeInFrames: 8,
  },
  territory: { strokeWidth: 1, strokeOpacityMultiplier: 2 },
  atmosphere: {
    vignette: 0.25,
    vignetteColor: "#0A1E33",
    grain: 0.08,
    borderDecoration: "corner_marks",
    borderColor: "#3A6FA5",
    borderWidth: 2,
  },
  animation: { markerFadeIn: 10, markerScaleFrom: 0.5, labelFadeIn: 8, routeDrawDelay: 10 },
};

const WARM_EARTH: MapTheme = {
  name: "warm_earth",
  surface: {
    ocean: "#E8DDD3",
    land: "#F0E8DE",
    landStroke: "#706048",
    landStrokeWidth: 1.2,
    borderStroke: "#806848",
    borderStrokeWidth: 0.6,
    adminStroke: "#8A7A60",
    adminStrokeWidth: 0.4,
    adminOpacity: 0.6,
    coastlineStroke: "#706048",
    coastlineStrokeWidth: 0.8,
    riverStroke: "#8A7A60",
    riverStrokeWidth: 0.6,
    riverOpacity: 0.55,
    lakeFill: "#D5CCC0",
    lakeStroke: "#8A7A60",
    lakeStrokeWidth: 0.4,
  },
  marker: {
    shape: "drop_pin",
    size: 26,
    dotSize: 14,
    borderWidth: 2.5,
    borderColor: "#FFFFFF",
    shadow: "0 2px 8px rgba(106,90,74,0.3)",
    pulseAmplitude: 0.07,
    labelBg: "transparent",
    labelRadius: 10,
    labelFontSize: 20,
    labelFontWeight: 700,
    labelColor: "#5A4A3A",
    labelShadow: "none",
  },
  title: {
    layout: "top_center_card",
    background: "rgba(255,255,250,0.9)",
    borderRadius: 14,
    padding: "12px 32px",
    fontSize: 42,
    fontWeight: 700,
    color: "#4A3A2A",
    fontFamily: "'Pretendard', sans-serif",
    shadow: "0 3px 14px rgba(106,90,74,0.15)",
    letterSpacing: "-0.01em",
    source: {
      fontSize: 15,
      color: "#A89078",
      fontFamily: "'Pretendard', sans-serif",
    },
    animation: { fadeInStart: 8, fadeInEnd: 20, slideDistance: 18, slideDirection: "down" },
  },
  route: {
    style: "solid",
    defaultColor: "#A0522D",
    defaultWidth: 5,
    lineCap: "round",
    lineJoin: "round",
    opacity: 0.85,
  },
  label: {
    style: "card",
    fontFamily: "'Pretendard', sans-serif",
    fontSize: 22,
    fontWeight: 600,
    color: "#5A4A3A",
    textShadow: "none",
    badgeBg: "rgba(255,255,250,0.9)",
    badgeRadius: 8,
    badgePadding: "4px 12px",
    badgeShadow: "0 2px 6px rgba(106,90,74,0.15)",
    fadeInFrames: 12,
  },
  territory: { strokeWidth: 1.5, strokeOpacityMultiplier: 2 },
  atmosphere: {
    vignette: 0.2,
    vignetteColor: "#8A7A6A",
    grain: 0,
    borderDecoration: "none",
  },
  animation: { markerFadeIn: 15, markerScaleFrom: 0.3, labelFadeIn: 12, routeDrawDelay: 15 },
};

const MODERN_CLEAN: MapTheme = {
  name: "modern_clean",
  surface: {
    ocean: "#E8EDF2",
    land: "#FAFAFA",
    landStroke: "#B0B8C4",
    landStrokeWidth: 0.8,
    borderStroke: "#CCD3DC",
    borderStrokeWidth: 0.5,
    adminStroke: "#D8DFE8",
    adminStrokeWidth: 0.3,
    adminOpacity: 0.5,
    coastlineStroke: "#B0B8C4",
    coastlineStrokeWidth: 0.6,
    riverStroke: "#B8C8DC",
    riverStrokeWidth: 0.5,
    riverOpacity: 0.4,
    lakeFill: "#D8E4F0",
    lakeStroke: "#C0D0E0",
    lakeStrokeWidth: 0.3,
  },
  marker: {
    shape: "circle",
    size: 20,
    dotSize: 12,
    borderWidth: 3,
    borderColor: "#FFFFFF",
    shadow: "0 2px 8px rgba(0,0,0,0.25)",
    pulseAmplitude: 0.08,
    labelBg: "transparent",
    labelRadius: 8,
    labelFontSize: 22,
    labelFontWeight: 700,
    labelColor: "#2A3440",
    labelShadow: "none",
  },
  title: {
    layout: "top_center_card",
    background: "rgba(255,255,255,0.88)",
    borderRadius: 12,
    padding: "12px 32px",
    fontSize: 44,
    fontWeight: 700,
    color: "#3D3B2F",
    fontFamily: "'Pretendard', sans-serif",
    shadow: "0 4px 16px rgba(0,0,0,0.12)",
    letterSpacing: "-0.01em",
    source: {
      fontSize: 16,
      color: "#8D8B7F",
      fontFamily: "'Pretendard', sans-serif",
    },
    animation: { fadeInStart: 8, fadeInEnd: 20, slideDistance: 20, slideDirection: "down" },
  },
  route: {
    style: "solid",
    defaultColor: "#FF6B6B",
    defaultWidth: 4.5,
    lineCap: "round",
    lineJoin: "round",
    opacity: 0.9,
  },
  label: {
    style: "card",
    fontFamily: "'Pretendard', sans-serif",
    fontSize: 24,
    fontWeight: 600,
    color: "#2A3440",
    textShadow: "none",
    badgeBg: "rgba(255,255,255,0.9)",
    badgeRadius: 8,
    badgePadding: "4px 12px",
    badgeShadow: "0 2px 8px rgba(0,0,0,0.12)",
    fadeInFrames: 12,
  },
  territory: { strokeWidth: 1, strokeOpacityMultiplier: 2 },
  atmosphere: {
    vignette: 0,
    grain: 0,
    borderDecoration: "none",
  },
  animation: { markerFadeIn: 15, markerScaleFrom: 0.3, labelFadeIn: 12, routeDrawDelay: 15 },
};

const HISTORICAL: MapTheme = {
  name: "historical",
  surface: {
    ocean: "#E8DDD3",
    land: "#F0E8DE",
    landStroke: "#A89078",
    landStrokeWidth: 1.0,
    borderStroke: "#B8A088",
    borderStrokeWidth: 0.5,
    adminStroke: "#C8B8A8",
    adminStrokeWidth: 0.3,
    adminOpacity: 0.6,
    coastlineStroke: "#A89078",
    coastlineStrokeWidth: 0.7,
    riverStroke: "#C0B0A0",
    riverStrokeWidth: 0.5,
    riverOpacity: 0.45,
    lakeFill: "#DDD4C8",
    lakeStroke: "#C0B0A0",
    lakeStrokeWidth: 0.3,
    cssFilter: "sepia(0.25) saturate(0.8) brightness(0.95)",
  },
  marker: {
    shape: "drop_pin",
    size: 24,
    dotSize: 14,
    borderWidth: 2.5,
    borderColor: "#F5E6C8",
    shadow: "0 2px 6px rgba(90,74,58,0.35)",
    pulseAmplitude: 0.06,
    labelBg: "transparent",
    labelRadius: 6,
    labelFontSize: 20,
    labelFontWeight: 700,
    labelColor: "#5A4A3A",
    labelShadow: "none",
  },
  title: {
    layout: "top_center_card",
    background: "rgba(245,230,200,0.9)",
    borderRadius: 10,
    padding: "12px 32px",
    fontSize: 42,
    fontWeight: 700,
    color: "#4A3A2A",
    fontFamily: "'Pretendard', sans-serif",
    shadow: "0 3px 12px rgba(90,74,58,0.18)",
    letterSpacing: "-0.01em",
    source: {
      fontSize: 15,
      color: "#8B7355",
      fontFamily: "'Pretendard', sans-serif",
    },
    animation: { fadeInStart: 8, fadeInEnd: 22, slideDistance: 20, slideDirection: "down" },
  },
  route: {
    style: "dashed",
    defaultColor: "#7A5C3C",
    defaultWidth: 4,
    lineCap: "round",
    lineJoin: "round",
    opacity: 0.85,
    dashArray: "8,5",
  },
  label: {
    style: "tag",
    fontFamily: "'Pretendard', sans-serif",
    fontSize: 22,
    fontWeight: 600,
    color: "#5A4A3A",
    textShadow: "none",
    badgeBg: "rgba(245,230,200,0.85)",
    badgeRadius: 4,
    badgePadding: "3px 10px",
    badgeShadow: "0 1px 4px rgba(90,74,58,0.18)",
    badgeBorder: "1px solid rgba(139,115,85,0.2)",
    fadeInFrames: 14,
  },
  territory: { strokeWidth: 1.5, strokeOpacityMultiplier: 2 },
  atmosphere: {
    vignette: 0.2,
    vignetteColor: "#8B7355",
    grain: 0.08,
    borderDecoration: "none",
  },
  animation: { markerFadeIn: 18, markerScaleFrom: 0.3, labelFadeIn: 14, routeDrawDelay: 15 },
};

const DARK_CYBER: MapTheme = {
  name: "dark_cyber",
  surface: {
    ocean: "#0A0E17",
    land: "#141B2A",
    landStroke: "#2A3A50",
    landStrokeWidth: 0.8,
    borderStroke: "#3A4A60",
    borderStrokeWidth: 0.5,
    adminStroke: "#1E2A3C",
    adminStrokeWidth: 0.3,
    adminOpacity: 0.5,
    coastlineStroke: "#2A3A50",
    coastlineStrokeWidth: 0.6,
    riverStroke: "#1A2A3C",
    riverStrokeWidth: 0.5,
    riverOpacity: 0.4,
    lakeFill: "#0E1420",
    lakeStroke: "#1A2A3C",
    lakeStrokeWidth: 0.3,
  },
  marker: {
    shape: "diamond",
    size: 22,
    dotSize: 14,
    borderWidth: 0,
    borderColor: "transparent",
    shadow: "0 0 14px rgba(0,255,210,0.5)",
    pulseAmplitude: 0.08,
    labelBg: "transparent",
    labelRadius: 4,
    labelFontSize: 18,
    labelFontWeight: 600,
    labelColor: "#00FFD2",
    labelShadow: "none",
    labelFontFamily: "'Pretendard', sans-serif",
  },
  title: {
    layout: "top_center_card",
    background: "rgba(10,14,23,0.85)",
    borderRadius: 8,
    padding: "12px 32px",
    fontSize: 38,
    fontWeight: 700,
    color: "#E0F0FF",
    fontFamily: "'Pretendard', sans-serif",
    shadow: "0 4px 16px rgba(0,0,0,0.4)",
    letterSpacing: "0.01em",
    border: "1px solid rgba(0,255,210,0.2)",
    source: {
      fontSize: 14,
      color: "#8AB0C8",
      fontFamily: "'Pretendard', sans-serif",
    },
    animation: { fadeInStart: 4, fadeInEnd: 14, slideDistance: 15, slideDirection: "down" },
  },
  route: {
    style: "glow",
    defaultColor: "#00FFD2",
    defaultWidth: 3,
    lineCap: "round",
    lineJoin: "round",
    opacity: 0.9,
    glow: { color: "#00FFD2", width: 14, opacity: 0.3 },
  },
  label: {
    style: "pill",
    fontFamily: "'Pretendard', sans-serif",
    fontSize: 20,
    fontWeight: 600,
    color: "#00FFD2",
    textShadow: "0 0 6px rgba(0,255,210,0.3)",
    badgeBg: "rgba(10,14,23,0.8)",
    badgeRadius: 14,
    badgePadding: "3px 14px",
    badgeBorder: "1px solid rgba(0,255,210,0.3)",
    fadeInFrames: 8,
  },
  territory: { strokeWidth: 1, strokeOpacityMultiplier: 2 },
  atmosphere: {
    vignette: 0.4,
    vignetteColor: "#000510",
    grain: 0,
    borderDecoration: "thin_line",
    borderColor: "#00FFD2",
    borderWidth: 1,
  },
  animation: { markerFadeIn: 10, markerScaleFrom: 0.5, labelFadeIn: 8, routeDrawDelay: 10 },
};

const CLEAN_WHITE: MapTheme = {
  name: "clean_white",
  surface: {
    ocean: "#D6E6F5",
    land: "#FFFFFF",
    landStroke: "#C0C8D4",
    landStrokeWidth: 0.8,
    borderStroke: "#A0AAB8",
    borderStrokeWidth: 0.7,
    adminStroke: "#C8D0DC",
    adminStrokeWidth: 0.4,
    adminOpacity: 0.5,
    coastlineStroke: "#A0B4C8",
    coastlineStrokeWidth: 0.7,
    riverStroke: "#A0C0E0",
    riverStrokeWidth: 0.5,
    riverOpacity: 0.5,
    lakeFill: "#D0E4F8",
    lakeStroke: "#A0C0E0",
    lakeStrokeWidth: 0.4,
  },
  marker: {
    shape: "circle",
    size: 20,
    dotSize: 12,
    borderWidth: 3,
    borderColor: "#FFFFFF",
    shadow: "0 2px 8px rgba(0,0,0,0.18)",
    pulseAmplitude: 0.06,
    labelBg: "transparent",
    labelRadius: 8,
    labelFontSize: 22,
    labelFontWeight: 700,
    labelColor: "#1A2030",
    labelShadow: "none",
  },
  title: {
    layout: "top_center_card",
    background: "rgba(255,255,255,0.95)",
    borderRadius: 12,
    padding: "12px 32px",
    fontSize: 42,
    fontWeight: 700,
    color: "#1A2030",
    fontFamily: "'Pretendard', sans-serif",
    shadow: "0 2px 12px rgba(0,0,0,0.08)",
    letterSpacing: "-0.01em",
    border: "1px solid rgba(0,0,0,0.06)",
    source: {
      fontSize: 15,
      color: "#7A8494",
      fontFamily: "'Pretendard', sans-serif",
    },
    animation: { fadeInStart: 6, fadeInEnd: 18, slideDistance: 16, slideDirection: "down" },
  },
  route: {
    style: "solid",
    defaultColor: "#F59E0B",
    defaultWidth: 4.5,
    lineCap: "round",
    lineJoin: "round",
    opacity: 0.9,
  },
  label: {
    style: "card",
    fontFamily: "'Pretendard', sans-serif",
    fontSize: 22,
    fontWeight: 600,
    color: "#1A2030",
    textShadow: "none",
    badgeBg: "rgba(255,255,255,0.95)",
    badgeRadius: 8,
    badgePadding: "4px 14px",
    badgeShadow: "0 1px 6px rgba(0,0,0,0.08)",
    badgeBorder: "1px solid rgba(0,0,0,0.06)",
    fadeInFrames: 10,
  },
  territory: { strokeWidth: 1, strokeOpacityMultiplier: 2 },
  atmosphere: {
    vignette: 0,
    grain: 0,
    borderDecoration: "none",
  },
  animation: { markerFadeIn: 12, markerScaleFrom: 0.4, labelFadeIn: 10, routeDrawDelay: 12 },
};

const MATTE_SLATE: MapTheme = {
  name: "matte_slate",
  surface: {
    ocean: "#15171C",
    land: "#1E2028",
    landStroke: "#3A3D48",
    landStrokeWidth: 1.0,
    borderStroke: "#4A4D58",
    borderStrokeWidth: 0.8,
    adminStroke: "#2A2D38",
    adminStrokeWidth: 0.4,
    adminOpacity: 0.5,
    coastlineStroke: "#3A3D48",
    coastlineStrokeWidth: 0.8,
    riverStroke: "#2A2D38",
    riverStrokeWidth: 0.5,
    riverOpacity: 0.4,
    lakeFill: "#1A1C24",
    lakeStroke: "#2A2D38",
    lakeStrokeWidth: 0.4,
  },
  marker: {
    shape: "circle",
    size: 20,
    dotSize: 12,
    borderWidth: 2.5,
    borderColor: "#FFFFFF",
    shadow: "0 2px 8px rgba(0,0,0,0.4)",
    pulseAmplitude: 0.06,
    labelBg: "transparent",
    labelRadius: 6,
    labelFontSize: 20,
    labelFontWeight: 600,
    labelColor: "#E8E8EC",
    labelShadow: "none",
  },
  title: {
    layout: "top_center_card",
    background: "rgba(30,32,40,0.92)",
    borderRadius: 10,
    padding: "12px 32px",
    fontSize: 40,
    fontWeight: 700,
    color: "#F0F0F4",
    fontFamily: "'Pretendard', sans-serif",
    shadow: "0 4px 16px rgba(0,0,0,0.3)",
    letterSpacing: "-0.01em",
    border: "1px solid rgba(255,255,255,0.08)",
    source: {
      fontSize: 15,
      color: "#8A8D98",
      fontFamily: "'Pretendard', sans-serif",
    },
    animation: { fadeInStart: 6, fadeInEnd: 18, slideDistance: 15, slideDirection: "down" },
  },
  route: {
    style: "solid",
    defaultColor: "#5C6BC0",
    defaultWidth: 4,
    lineCap: "round",
    lineJoin: "round",
    opacity: 0.9,
  },
  label: {
    style: "card",
    fontFamily: "'Pretendard', sans-serif",
    fontSize: 20,
    fontWeight: 600,
    color: "#E8E8EC",
    textShadow: "none",
    badgeBg: "rgba(30,32,40,0.9)",
    badgeRadius: 6,
    badgePadding: "4px 12px",
    badgeShadow: "0 2px 6px rgba(0,0,0,0.3)",
    badgeBorder: "1px solid rgba(255,255,255,0.06)",
    fadeInFrames: 10,
  },
  territory: { strokeWidth: 1, strokeOpacityMultiplier: 2 },
  atmosphere: {
    vignette: 0.2,
    vignetteColor: "#0A0A10",
    grain: 0,
    borderDecoration: "none",
  },
  animation: { markerFadeIn: 12, markerScaleFrom: 0.4, labelFadeIn: 10, routeDrawDelay: 12 },
};

/* ══════════════════════════════════════════════
   REGISTRY & RESOLVER
   ══════════════════════════════════════════════ */

export const MAP_THEMES: Record<string, MapTheme> = {
  vintage_parchment: VINTAGE_PARCHMENT,
  minimal_light: MINIMAL_LIGHT,
  dark_elegant: DARK_ELEGANT,
  blueprint: BLUEPRINT,
  warm_earth: WARM_EARTH,
  modern_clean: MODERN_CLEAN,
  historical: HISTORICAL,
  dark_cyber: DARK_CYBER,
  matte_slate: MATTE_SLATE,
  clean_white: CLEAN_WHITE,
};

/** 테마명으로 MapTheme 해석. 없으면 modern_clean 폴백. */
export function resolveMapTheme(name?: string): MapTheme {
  if (!name) return MODERN_CLEAN;
  return MAP_THEMES[name] ?? MODERN_CLEAN;
}
