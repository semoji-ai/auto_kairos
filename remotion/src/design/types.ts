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
  headline?: FontDef;  // 헤드라인/타이틀 전용 (display 폰트)
  value?: FontDef;     // 숫자/지표 전용 (tabular/condensed)
  mono?: FontDef;      // 장식 따옴표 등 (시스템 폰트 가능, files: [])
  subtitle?: FontDef;  // 자막 전용 폰트
  /** @deprecated headline 사용 권장 */
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

export interface ComponentVariants {
  circleBadge: "circle" | "rounded-square" | "square";
  iconBadge: "circle" | "rounded-square" | "square";
  imageBadge: "circle" | "rounded-square" | "square";
  flagBadge: "circle" | "card" | "rounded-square";
  logoBadge: "circle" | "rounded-square" | "square";
  rankBadge: "circle" | "shield" | "square";
  card: "bordered" | "filled" | "glass" | "minimal";
  metricCard: "bordered" | "filled" | "glass";
  comparisonCell: "bordered" | "filled" | "accent-top" | "none";
  itemsList: "default" | "accent-filled";
  callout: "left-border" | "full-border" | "highlight";
  tag: "rounded" | "pill" | "square";
  pill: "pill" | "rounded" | "square";
  statusDot: "dot" | "icon" | "badge";
  progressBar: "rounded" | "flat" | "thick";
  miniBar: "rounded" | "flat";
  connector: "arrow" | "line" | "dashed";
  timelineDot: "circle" | "diamond" | "square";
  stepBadge: "circle" | "rounded-square";
  quoteMark: "large" | "small" | "none";
  divider: "solid" | "dashed" | "dotted" | "gradient";
  glowDot: "glow" | "solid" | "ring";
  annotationLine: "solid" | "dashed";
  sparkline: "line" | "area";
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
  defaultBackground?: string;  // 이미지 없는 씬의 기본 배경 이미지 경로
  defaultBgOpacity?: number;  // 기본 배경 이미지 오퍼시티 (기본 0.35, 스타일별 오버라이드)
  texture?: { src: string; blendMode?: string; opacity?: number };  // 최상위 텍스처 오버레이

  colors: PresetColors;
  fonts: PresetFonts;
  typography: PresetTypography;
  layout: PresetLayout;
  moods: Record<string, MoodOverride>;
  map: PresetMap;
  subtitle: PresetSubtitle;
  animation: PresetAnimation;
  background: PresetBackground;
  variants: ComponentVariants;
}

/** manifest에서 전달되는 partial 오버라이드 (모든 필드 optional) */
export type DesignPresetOverride = DeepPartial<Omit<DesignPreset, "id" | "name" | "description" | "version">>;

/** 재귀적 Partial 유틸 */
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};
