/**
 * CreativeScene — Intent-Based Creative Renderer
 *
 * 레이아웃 결정 (resolveLayout):
 *   1순위: creative.layout 직접 지정 (의도 기반, asset-advisory가 설정)
 *   2순위: displayMode / chartConfig (하위호환)
 *   3순위: 데이터 구조 기반 추론 (fallback)
 *
 * 기본 11 + 확장 13 = 24개 LayoutType 지원
 * Styling: mood(색상/속도) + emphasis({{}} 강조) + reveal(애니메이션)
 * Overlays: spotlight + flash
 * Whisper 자막 타임스탬프 동기화 지원
 */
import React, { useRef, useLayoutEffect, useState, useEffect } from "react";
import {
  AbsoluteFill,
  Img,
  staticFile,
  useCurrentFrame,
  interpolate,
  Easing,
} from "remotion";

/** staticFile 대체: 절대 URL이면 그대로, 상대경로면 staticFile() 사용 */
const resolveAsset = (path: string): string =>
  path.startsWith("http://") || path.startsWith("https://")
    ? path
    : staticFile(path);

import { useDesignPreset, usePresetColors, usePresetTypo, usePresetLayout } from "../design";
import { DEFAULT_PRESET } from "../design/defaults";

/** 숫자 포맷: 연도(1000~2999)는 그대로, 나머지는 세 자리 콤마 */
const fmtNum = (v: number | string | null | undefined): string => {
  if (v == null) return "";
  const n = typeof v === "string" ? parseFloat(v) : v;
  if (isNaN(n)) return String(v);
  // 연도 판별: 1000~2999 정수
  if (Number.isInteger(n) && n >= 1000 && n <= 2999) return String(n);
  return n.toLocaleString();
};
import { resolveSceneMotion, type MotionConfig } from "../utils/resolveMotion";

import {
  C as C_DEFAULT,
  useC,
  ease,
  ease8020,
  clamp,
  useFade,
  useFadeRise,
  useCountUp,
  useScale,
  CircleBadge,
  ImageBadge,
  extractNumber,
  formatWithTemplate,
  Icon,
  IconBadge,
  FlagBadge,
  FlagCard,
  LogoBadge,
  resolveIcon,
  resolveLogo,
  useOvershootScale,
  useBounceIn,
  useShake,
  staggerDelay,
  Tag,
  Divider,
  ProgressBar,
  StatusDot,
  AccentText,
  Connector,
  TimelineDot,
  MetricCard,
  Sparkline,
  Callout,
  StepBadge,
  ComparisonCell,
  RankBadge,
  QuoteMark as QuoteMarkBlock,
  GlowDot,
  AnnotationLine,
  MiniBar,
  useFadeSlide,
  Card,
  Pill,
  usePulse,
  useTypewriter,
  useSpringValue,
  TextWithBreaks,
  fadeRise,
  fadeSlide,
  fadeVal,
  scaleAnim,
} from "./BuildingBlocks";

/* ================================================================
   Types
   ================================================================ */

interface SubtitleEntry {
  text: string;
  startSec: number;
  endSec: number;
}

interface MoodConfig {
  accent: string;
  accentRgb: string;
  speed: number;
  glow: number;
}

type LayoutType =
  | "headline_only"
  | "items_grid"
  | "items_list"
  | "person_card"
  | "counter"
  | "quote"
  | "split"
  | "bar"
  | "logo_grid"
  | "pie"
  | "line"
  // ── 확장 레이아웃 (의도 기반 컴포지션) ──
  | "flow"              // StepBadge + Connector 체인 (프로세스/인과)
  | "timeline"          // TimelineDot + Card 수직 배치 (시간순)
  | "metric_spotlight"  // MetricCard 1개 + Sparkline (단일 KPI 극적 강조)
  | "metric_wall"       // MetricCard 2×2 그리드 (여러 KPI 동시)
  | "rank_list"         // RankBadge + 항목 + MiniBar (순위)
  | "comparison_table"  // ComparisonCell 행×열 (다차원 비교)
  | "before_after"      // ComparisonCell 2열 + 화살표 (변화 전후)
  | "icon_stat"         // IconBadge 중앙 + 큰 수치 + 트렌드 (단일 통계)
  | "stacked_progress"  // ProgressBar 수직 스택 (점유율 비교)
  | "card_carousel"     // Card 3-4장 수평 스태거 (정보 카드)
  | "hero_with_context" // 큰 헤드라인 + 작은 부연 카드들
  | "quote_portrait"    // ImageBadge 큰 사이즈 + QuoteMark + 인용문
  | "annotated_chart"   // bar/pie/line + AnnotationLine + Callout
  | "cinematic"         // 이미지 풀스크린 + Ken Burns, 텍스트 없음 (나레이션만)
  | "bar_horizontal"    // 가로 바 차트 (항목별 비교, 긴 라벨에 적합)
  | "donut";            // 도넛 차트 (점유율, 중앙에 총합 표시)

const HEADLINE_PRIMARY_LAYOUTS: LayoutType[] = ["headline_only"];
const INLINE_SUPPORT_HEADLINE_LAYOUTS: LayoutType[] = [
  "metric_spotlight",
  "before_after",
  "metric_wall",
  "comparison_table",
  "icon_stat",
];
const ITEM_PRIMARY_LAYOUTS: LayoutType[] = [
  "items_grid",
  "items_list",
  "person_card",
  "flow",
  "timeline",
  "rank_list",
  "comparison_table",
  "before_after",
  "stacked_progress",
  "card_carousel",
];
const VALUE_PRIMARY_LAYOUTS: LayoutType[] = [
  "counter",
  "bar",
  "logo_grid",
  "pie",
  "line",
  "metric_spotlight",
  "metric_wall",
  "icon_stat",
  "annotated_chart",
  "bar_horizontal",
  "donut",
];

type LayoutHierarchy = "headline" | "item" | "value" | "neutral";

const getLayoutHierarchy = (layout: LayoutType): LayoutHierarchy => {
  if (HEADLINE_PRIMARY_LAYOUTS.includes(layout)) return "headline";
  if (ITEM_PRIMARY_LAYOUTS.includes(layout)) return "item";
  if (VALUE_PRIMARY_LAYOUTS.includes(layout)) return "value";
  return "neutral";
};

const usesSupportHeadline = (layout: LayoutType): boolean => getLayoutHierarchy(layout) !== "headline";
const usesInlineSupportHeadline = (layout: LayoutType): boolean => INLINE_SUPPORT_HEADLINE_LAYOUTS.includes(layout);

/* ================================================================
   Layout Resolution — 의도 기반 (creative.layout 직접 지정) + 데이터 추론 fallback
   ================================================================ */

/** 유효한 LayoutType인지 검증 */
const VALID_LAYOUTS = new Set<LayoutType>([
  "headline_only", "items_grid", "items_list", "person_card", "counter",
  "quote", "split", "bar", "logo_grid", "pie", "line",
  "flow", "timeline", "metric_spotlight", "metric_wall", "rank_list",
  "comparison_table", "before_after", "icon_stat", "stacked_progress",
  "card_carousel", "hero_with_context", "quote_portrait", "annotated_chart",
  "cinematic", "bar_horizontal", "donut",
]);

function resolveLayout(data: any, creative: any): LayoutType {
  // ── 0순위: 명시적 layout 지정 (씬에디터에서 수동 변경 시) ──
  const explicit = data.layout || creative.layout || "";
  if (explicit && VALID_LAYOUTS.has(explicit)) {
    // bar/pie/line 계열인데 values가 없으면 items_grid로 전환
    const values: number[] = data.values || [];
    if ((explicit === "bar" || explicit === "bar_horizontal" || explicit === "pie" || explicit === "donut" || explicit === "line") && values.length === 0) {
      const items: string[] = data.items || [];
      return items.length >= 3 ? "items_grid" : items.length >= 1 ? "items_list" : "headline_only";
    }
    return explicit as LayoutType;
  }

  // ── 1순위: 콘텐츠 구조 기반 자동 결정 ──
  return inferFromContent(data, creative);
}

function normalizeLayoutOptions(data: any, creative: any) {
  const resolvedLayout = resolveLayout(data, creative);
  const imagePlacement = (data.imageAsset || creative.imageAsset || {}).placement;
  const items: string[] = data.items || [];
  const values: number[] = data.values || [];
  const isAutoPortraitQuote =
    resolvedLayout === "quote" &&
    items.length === 1 &&
    values.length === 0 &&
    (imagePlacement === "left" || imagePlacement === "right");
  const legacyOptions =
    resolvedLayout === "donut"
      ? { layout: "pie" as LayoutType, chartStyle: "donut" as const }
      : resolvedLayout === "bar_horizontal"
        ? { layout: "bar" as LayoutType, orientation: "horizontal" as const }
        : resolvedLayout === "quote_portrait" || isAutoPortraitQuote
          ? {
              layout: "quote" as LayoutType,
              withPortrait: true,
              portraitPlacement: imagePlacement || "right",
            }
          : { layout: resolvedLayout };

  return {
    layout: legacyOptions.layout,
    chartStyle: data.chartStyle ?? creative.chartStyle ?? legacyOptions.chartStyle,
    orientation: data.orientation ?? creative.orientation ?? legacyOptions.orientation,
    withPortrait: data.withPortrait ?? creative.withPortrait ?? legacyOptions.withPortrait,
    portraitPlacement:
      data.portraitPlacement ?? creative.portraitPlacement ?? legacyOptions.portraitPlacement,
  };
}

/** 콘텐츠 구조 기반 레이아웃 자동 결정 */
function inferFromContent(data: any, creative: any): LayoutType {
  const items: string[] = data.items || [];
  const values: number[] = data.values || [];
  const headline: string = data.headline || creative.headline || "";
  const chartType = data.chartConfig?.type || creative.chartConfig?.type;
  const placement = (data.imageAsset || creative.imageAsset || {}).placement || "";
  const icons: string[] = data.icons || data.itemIcons || [];

  // 차트 — chartConfig가 있으면 차트 종류로
  if (chartType === "pie") return "pie";
  if (chartType === "line") return "line";
  if (chartType === "bar") return "bar";

  // cinematic — items 없고 이미지 fullscreen
  if (items.length === 0 && placement === "fullscreen") return "cinematic";

  // 인용문 — items 1개 + imageAsset left/right + values 없음
  if (items.length === 1 && values.length === 0 && (placement === "left" || placement === "right")) return "quote";
  if (items.length === 1 && /["""']/.test(items[0])) return "quote";

  // counter — headline에 {{숫자}}
  if (headline) {
    const accentMatch = headline.match(/\{\{([^}]+)\}\}/);
    if (accentMatch) {
      const num = extractNumber(accentMatch[1]);
      if (num > 0 && items.length <= 1) return "counter";
    }
  }

  // icon_stat — items 1개 + values 1개 + icon
  if (items.length === 1 && values.length === 1 && icons.length >= 1) return "icon_stat";

  // metric_spotlight — items 1개 + values 1개
  if (items.length === 1 && values.length === 1) return "metric_spotlight";

  // metric_spotlight — items 1개 + values 0개 (단일 항목)
  if (items.length === 1 && values.length === 0) return "metric_spotlight";

  // 2항목 비교
  if (items.length === 2 && values.length >= 2) return "before_after";
  if (items.length === 2) return "split";

  // 3~6항목 + values 매칭 → bar
  if (items.length >= 3 && values.length >= 3 && items.length === values.length) return "bar";

  // 3~6항목 + values 없음 → items_list
  if (items.length >= 3 && values.length === 0) return "items_list";

  // 3~6항목 → items_grid
  if (items.length >= 3) return "items_grid";

  // headline + items → hero_with_context
  if (headline && items.length >= 1) return "hero_with_context";

  // 이미지만 있는 씬 (items/headline 없음) → cinematic
  if (placement) return "cinematic";

  // headline만 있음 (items 없음) — 정말 텍스트만
  if (headline) return "counter";

  // 최종 fallback — 빈 씬 (narration만)
  return "items_list";
}

/* ================================================================
   Layer 1: Mood → 색상 팔레트 + 속도 + 배경 그라데이션
   ================================================================ */

const MOOD_CONFIGS: Record<string, MoodConfig> = {
  dramatic: {
    accent: "#F59E0B",
    accentRgb: "245,158,11",
    speed: 1.2,
    glow: 0.6,
  },
  urgent: {
    accent: "#EF4444",
    accentRgb: "239,68,68",
    speed: 1.5,
    glow: 0.8,
  },
  somber: {
    accent: "#71717A",
    accentRgb: "113,113,122",
    speed: 0.7,
    glow: 0.2,
  },
  informative: {
    accent: "#3B82F6",
    accentRgb: "59,130,246",
    speed: 1.0,
    glow: 0.3,
  },
  contemplative: {
    accent: "#3B82F6",
    accentRgb: "59,130,246",
    speed: 0.6,
    glow: 0.2,
  },
  suspense: {
    accent: "#F59E0B",
    accentRgb: "245,158,11",
    speed: 0.8,
    glow: 0.5,
  },
  triumphant: {
    accent: "#10B981",
    accentRgb: "16,185,129",
    speed: 1.0,
    glow: 0.5,
  },
};

const MOOD_GRADIENTS: Record<string, string> = {
  dramatic:
    "radial-gradient(ellipse 80% 60% at 50% 40%, #1a1005 0%, #0A0A0A 70%)",
  urgent:
    "radial-gradient(ellipse 80% 60% at 50% 40%, #1a0808 0%, #0A0A0A 70%)",
  somber:
    "radial-gradient(ellipse 80% 60% at 50% 40%, #0d0d0e 0%, #0A0A0A 70%)",
  informative:
    "radial-gradient(ellipse 80% 60% at 50% 40%, #080d1a 0%, #0A0A0A 70%)",
  contemplative:
    "radial-gradient(ellipse 80% 60% at 50% 40%, #080d1a 0%, #0A0A0A 70%)",
  suspense:
    "radial-gradient(ellipse 80% 60% at 50% 40%, #14100a 0%, #0A0A0A 70%)",
  triumphant:
    "radial-gradient(ellipse 80% 60% at 50% 40%, #081a10 0%, #0A0A0A 70%)",
};

const MOOD_GRADIENTS_WHITE: Record<string, string> = {
  dramatic:
    "radial-gradient(ellipse 80% 60% at 50% 40%, #FFF7E6 0%, #FAFAFA 70%)",
  urgent:
    "radial-gradient(ellipse 80% 60% at 50% 40%, #FFF1F0 0%, #FAFAFA 70%)",
  somber:
    "radial-gradient(ellipse 80% 60% at 50% 40%, #F0F0F2 0%, #FAFAFA 70%)",
  informative:
    "radial-gradient(ellipse 80% 60% at 50% 40%, #EFF4FF 0%, #FAFAFA 70%)",
  contemplative:
    "radial-gradient(ellipse 80% 60% at 50% 40%, #EFF4FF 0%, #FAFAFA 70%)",
  suspense:
    "radial-gradient(ellipse 80% 60% at 50% 40%, #FFF8F0 0%, #FAFAFA 70%)",
  triumphant:
    "radial-gradient(ellipse 80% 60% at 50% 40%, #EFFFEF 0%, #FAFAFA 70%)",
};

/** accent 색상에서 RGB 문자열 추출 (hex → "r,g,b") */
function hexToRgb(hex: string): string {
  const h = hex.replace("#", "");
  const r = parseInt(h.substring(0, 2), 16);
  const g = parseInt(h.substring(2, 4), 16);
  const b = parseInt(h.substring(4, 6), 16);
  return `${r},${g},${b}`;
}

/** mood 팔레트를 가져오되, dramatic/suspense의 기본 accent를 컨텍스트 accent로 대체 */
function getMoodConfig(mood: string, themeAccent?: string): MoodConfig {
  const base = MOOD_CONFIGS[mood] || MOOD_CONFIGS.informative;
  // dramatic/suspense는 기본 amber(#F59E0B) — 아트스타일 accent로 대체
  if (themeAccent && (mood === "dramatic" || mood === "suspense") && base.accent === "#F59E0B") {
    return { ...base, accent: themeAccent, accentRgb: hexToRgb(themeAccent) };
  }
  return base;
}

/** preset-aware mood config: preset.moods 우선, MOOD_CONFIGS fallback */
function getMoodConfigFromPreset(
  mood: string,
  preset: ReturnType<typeof useDesignPreset>,
): MoodConfig {
  const override = preset.moods[mood];
  const fallback: MoodConfig = {
    accent: preset.colors.accent,
    accentRgb: preset.colors.accentRgb,
    speed: 1.0,
    glow: 0.3,
  };
  return {
    accent: override?.accent ?? fallback.accent,
    accentRgb: override?.accentRgb ?? fallback.accentRgb,
    speed: override?.speed ?? fallback.speed,
    glow: override?.glow ?? fallback.glow,
  };
}

/** preset-aware mood gradient: preset.moods[mood].gradient 우선, 없으면 DEFAULT_PRESET fallback */
function getMoodGradient(mood: string, preset: ReturnType<typeof useDesignPreset>): string {
  return preset.moods[mood]?.gradient
    ?? DEFAULT_PRESET.moods[mood as keyof typeof DEFAULT_PRESET.moods]?.gradient
    ?? `radial-gradient(ellipse 80% 60% at 50% 40%, #1a1005 0%, ${preset.colors.bg || "#0A0A0A"} 70%)`;
}

/* ================================================================
   Layer 2: Reveal → 타이밍 계산
   ================================================================ */

function computeSubtitleDelays(
  subtitles: SubtitleEntry[],
  count: number,
  fps: number,
): number[] {
  if (!subtitles.length || count <= 0) return Array(count).fill(0);
  const subCount = subtitles.length;
  return Array.from({ length: count }, (_, i) => {
    const subIdx = Math.min(
      Math.floor((i * subCount) / count),
      subCount - 1,
    );
    return Math.round(subtitles[subIdx].startSec * fps);
  });
}

/**
 * 아이템별 자막 텍스트 매칭 — 각 아이템을 해당 나레이션 자막에 시간 동기화
 * 같은 자막에 여러 아이템이 매칭되면 그 구간 내에서 stagger 처리
 */
function computeItemSubtitleDelays(
  subtitles: SubtitleEntry[],
  items: string[],
  fps: number,
): number[] {
  if (!subtitles.length || !items.length) return items.map(() => 0);

  // 각 아이템을 가장 잘 매칭되는 자막에 연결
  const itemSubIdx = items.map((item) => {
    const words = item
      .toLowerCase()
      .replace(/[()（）\[\]'"]/g, " ")
      .split(/\s+/)
      .filter((w) => w.length > 1);
    let bestIdx = 0;
    let bestScore = 0;

    for (let si = 0; si < subtitles.length; si++) {
      const subText = subtitles[si].text.toLowerCase();
      const score = words.filter((w) => subText.includes(w)).length;
      if (score > bestScore) {
        bestScore = score;
        bestIdx = si;
      }
    }
    return bestIdx;
  });

  // 같은 자막에 매칭된 아이템끼리 그룹화 → 구간 내 stagger
  const groups = new Map<number, number[]>();
  itemSubIdx.forEach((si, i) => {
    if (!groups.has(si)) groups.set(si, []);
    groups.get(si)!.push(i);
  });

  const delays = new Array(items.length).fill(0);
  for (const [si, indices] of groups) {
    const startFrame = Math.round(subtitles[si].startSec * fps);
    const endFrame = Math.round(subtitles[si].endSec * fps);
    const available = endFrame - startFrame;
    const staggerGap =
      indices.length > 1
        ? Math.min(Math.round(available / (indices.length + 1)), 30)
        : 0;
    const offset = Math.min(5, Math.round(available * 0.05));
    indices.forEach((idx, j) => {
      delays[idx] = startFrame + offset + staggerGap * j;
    });
  }

  return delays;
}

function computeFixedDelays(
  reveal: string,
  count: number,
  speed: number,
): number[] {
  const s = (f: number) => Math.round(f / speed);
  const base = s(8);
  const gap = s(12);

  switch (reveal) {
    case "fade_in":
    case "parallel":
    case "zoom_in":
      return Array(count).fill(base);
    case "stagger":
    case "typewriter":
      return Array.from({ length: count }, (_, i) => base + i * gap);
    case "cascade":
      return Array.from(
        { length: count },
        (_, i) => base + i * Math.round(gap * 1.5),
      );
    case "build_up":
      return Array.from(
        { length: count },
        (_, i) => base + (count - 1 - i) * gap,
      );
    case "stagger_then_flash":
      return Array.from(
        { length: count },
        (_, i) => base + i * Math.round(gap * 0.7),
      );
    case "count_up":
    case "dramatic_pause":
      return Array.from({ length: count }, (_, i) =>
        i === 0 ? base : base + s(30),
      );
    case "spotlight":
      return Array.from({ length: count }, (_, i) => s(25) + i * gap);
    case "split_reveal":
      return Array.from({ length: count }, () => s(25));
    default:
      return Array(count).fill(base);
  }
}

/* ================================================================
   Layer 3: Emphasis → {{}} 스타일
   ================================================================ */

function getAccentFontSize(emphasis: string): number {
  switch (emphasis) {
    case "number":
      return 80;
    case "keyword":
      return 80;
    case "count":
      return 80;
    default:
      return 80;
  }
}

function getBaseFontSize(emphasis: string): number {
  switch (emphasis) {
    case "number":
    case "count":
      return 48;
    case "quote":
      return 48;
    default:
      return 48;
  }
}

/* ================================================================
   EmphasisAccentText — {{}} 파싱 + emphasis 스타일 + multi count-up
   ================================================================ */

const EmphasisAccentText: React.FC<{
  text: string;
  emphasis: string;
  moodCfg: MoodConfig;
  countedValues: number[];
  glowOpacity: number;
  accentFontSizeOverride?: number;
  accentStartIndex?: number;
}> = ({
  text,
  emphasis,
  moodCfg,
  countedValues,
  glowOpacity,
  accentFontSizeOverride,
  accentStartIndex = 0,
}) => {
  const C = useC();
  const T = usePresetTypo();
  const isCountEmphasis = emphasis === "number" || emphasis === "count";
  const accentSize = accentFontSizeOverride || T.headlineAccent;
  const baseSize = accentFontSizeOverride ? Math.round(accentFontSizeOverride * 0.6) : T.headlineBase;
  const sizeDiff = accentSize - baseSize;

  const parts = text.split(/(\{\{[^}]+\}\})/g);
  const nonEmpty = parts.filter((p) => p.trim());
  const hasAccent = nonEmpty.some((p) => p.startsWith("{{"));
  const hasNormal = nonEmpty.some((p) => !p.startsWith("{{"));
  const hasMixed = hasAccent && hasNormal;

  // Track which {{}} index we're on for multi-counter (글로벌 인덱스)
  let accentIdx = accentStartIndex;

  // --- 렌더 헬퍼: accent span (counter/quote 등 전용 레이아웃용) ---
  const renderAccent = (part: string, pi: number) => {
    const content = part.slice(2, -2);
    const num = extractNumber(content);
    const isNum = !isNaN(num) && num > 0;
    const currentCountIdx = accentIdx;
    accentIdx++;
    const counted = countedValues[currentCountIdx] || 0;
    const shouldCountUp = isCountEmphasis && isNum && num >= 100;
    const displayText = shouldCountUp
      ? formatWithTemplate(content, counted)
      : content;
    return (
      <span
        key={pi}
        style={{
          fontSize: accentSize,
          fontWeight: 800,
          color: moodCfg.accent,
          lineHeight: 1.2,
          textShadow: shouldCountUp
            ? `0 0 60px rgba(${moodCfg.accentRgb},${glowOpacity})`
            : undefined,
        }}
      >
        {displayText}
      </span>
    );
  };

  // ============================================================
  // 인라인 레이아웃: accent에 좌우 여백 추가 (사이즈 차이 클 때)
  // ============================================================
  const accentMargin = hasMixed && sizeDiff >= 6 ? "0 12px" : undefined;

  return (
    <>
      {parts.map((part, pi) => {
        if (part.startsWith("{{") && part.endsWith("}}")) {
          // accent span에 좌우 여백 추가
          const content = part.slice(2, -2);
          const num = extractNumber(content);
          const isNum = !isNaN(num) && num > 0;
          const currentCountIdx = accentIdx;
          accentIdx++;
          const counted = countedValues[currentCountIdx] || 0;
          const shouldCountUp = isCountEmphasis && isNum && num >= 100;
          const displayText = shouldCountUp
            ? formatWithTemplate(content, counted)
            : content;
          return (
            <span
              key={pi}
              style={{
                fontSize: accentSize,
                fontWeight: 800,
                color: moodCfg.accent,
                lineHeight: 1.2,
                verticalAlign: "baseline",
                margin: accentMargin,
                textShadow: shouldCountUp
                  ? `0 0 60px rgba(${moodCfg.accentRgb},${glowOpacity})`
                  : undefined,
              }}
            >
              {displayText}
            </span>
          );
        }
        return (
          <span key={pi} style={{ color: C.textMuted }}>
            {part}
          </span>
        );
      })}
    </>
  );
};

/* ================================================================
   MoodBackground — mood별 그라데이션 배경
   ================================================================ */

const MoodBackground: React.FC<{ mood: string; transparent?: boolean }> = ({ mood, transparent }) => {
  const C = useC();
  const preset = useDesignPreset();
  const isWhite = C.bg === "#FAFAFA";
  // preset-aware gradient (아트스타일 프리셋에 정의된 gradient 우선)
  const gradientFromPreset = getMoodGradient(mood, preset);
  // white 테마 fallback: 기존 MOOD_GRADIENTS_WHITE 참조 (프리셋에 white용 gradient 미정의 시)
  const gradient = isWhite
    ? (MOOD_GRADIENTS_WHITE[mood] || MOOD_GRADIENTS_WHITE.informative)
    : gradientFromPreset;
  return (
  <div
    style={{
      position: "absolute",
      inset: 0,
      background: transparent
        ? (isWhite ? "rgba(250,250,250,0.45)" : "rgba(10,10,10,0.45)")
        : gradient,
      zIndex: 0,
    }}
  />
  );
};

/* ================================================================
   SpotlightOverlay — radial-gradient
   ================================================================ */

const SpotlightOverlay: React.FC<{ speed: number }> = ({ speed }) => {
  const C = useC();
  const isWhite = C.bg === "#FAFAFA";
  const frame = useCurrentFrame();
  const s = (f: number) => Math.round(f / speed);
  const overlayOpacity = interpolate(
    frame,
    [0, s(30), s(50)],
    isWhite ? [0.6, 0.3, 0.1] : [0.95, 0.7, 0.3],
    clamp,
  );
  const size = interpolate(frame, [s(10), s(45)], [100, 600], {
    ...clamp,
    easing: ease,
  });
  const overlayColor = isWhite ? `rgba(200,200,200,${overlayOpacity})` : `rgba(0,0,0,${overlayOpacity})`;

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        zIndex: 1,
        pointerEvents: "none",
        background: `radial-gradient(circle ${size}px at 50% 45%, transparent 0%, ${overlayColor} 100%)`,
      }}
    />
  );
};

/* ================================================================
   FlashOverlay — stagger_then_flash 완성용
   ================================================================ */

const FlashOverlay: React.FC<{
  flashAt: number;
  accentRgb: string;
}> = ({ flashAt, accentRgb }) => {
  const frame = useCurrentFrame();
  const flash = interpolate(
    frame,
    [flashAt, flashAt + 4, flashAt + 25],
    [0, 0.15, 0],
    clamp,
  );
  return flash > 0 ? (
    <div
      style={{
        position: "absolute",
        inset: 0,
        zIndex: 10,
        pointerEvents: "none",
        background: `radial-gradient(ellipse at 50% 50%, rgba(${accentRgb},${flash}) 0%, transparent 70%)`,
      }}
    />
  ) : null;
};

/* ================================================================
   SplitLayout — split_reveal 전용 좌/우 분할
   ================================================================ */

const SplitLayout: React.FC<{
  lines: string[];
  delays: number[];
  emphasis: string;
  moodCfg: MoodConfig;
  countedValues: number[];
  glowOpacity: number;
  source: string;
  mood: string;
  hasImageBg?: boolean;
  images?: string[];
  descriptions?: string[];
}> = ({
  lines,
  delays,
  emphasis,
  moodCfg,
  countedValues,
  glowOpacity,
  source,
  mood,
  hasImageBg,
  images,
  descriptions,
}) => {
  const C = useC();
  const T = usePresetTypo();
  const L = usePresetLayout();
  const frame = useCurrentFrame();
  const leftRef = useRef<HTMLDivElement>(null);
  const rightRef = useRef<HTMLDivElement>(null);
  const [boxWidth, setBoxWidth] = useState<number | undefined>(undefined);

  useLayoutEffect(() => {
    const lw = leftRef.current?.scrollWidth || 0;
    const rw = rightRef.current?.scrollWidth || 0;
    const max = Math.max(lw, rw) + 10;
    if (max > 10) setBoxWidth(max);
  }, []);

  const leftDelay = delays[0] || 0;
  const rightDelay = delays[1] || delays[0] || 0;

  const leftOpacity = interpolate(
    frame,
    [leftDelay, leftDelay + 18],
    [0, 1],
    clamp,
  );
  const leftSlide = interpolate(
    frame,
    [leftDelay, leftDelay + 18],
    [-40, 0],
    { ...clamp, easing: ease },
  );

  const rightOpacity = interpolate(
    frame,
    [rightDelay, rightDelay + 18],
    [0, 1],
    clamp,
  );
  const rightSlide = interpolate(
    frame,
    [rightDelay, rightDelay + 18],
    [40, 0],
    { ...clamp, easing: ease },
  );

  const divHeight = interpolate(
    frame,
    [
      Math.min(leftDelay, rightDelay) + 5,
      Math.min(leftDelay, rightDelay) + 30,
    ],
    [0, 100],
    { ...clamp, easing: ease },
  );
  const vsScale = useScale(Math.max(leftDelay, rightDelay) + 10, 15);
  const sourceFade = useFade(Math.max(leftDelay, rightDelay) + 40, 15, 0.8);

  // descriptions는 VS 등장 후 딜레이로 표시 (스포일러 방지)
  const descDelay = Math.max(leftDelay, rightDelay) + 35;
  const descOpacity = interpolate(frame, [descDelay, descDelay + 15], [0, 1], clamp);
  const descSlideY = interpolate(frame, [descDelay, descDelay + 15], [12, 0], { ...clamp, easing: ease });

  // 승리 도장: descriptions에 "승리" 포함 시 분리 → 도장으로 표시
  const winnerIdx = descriptions ? descriptions.findIndex((d) => d?.includes("승리")) : -1;
  const stampDelay = descDelay + 20;
  const stampEasing = Easing.bezier(0.34, 1.56, 0.64, 1); // overshoot bounce
  const stampScaleVal = interpolate(frame, [stampDelay, stampDelay + 10], [3, 1], { ...clamp, easing: stampEasing });
  const stampOpacity = interpolate(frame, [stampDelay, stampDelay + 5], [0, 1], clamp);
  const stampRotation = interpolate(frame, [stampDelay, stampDelay + 10], [-15, -5], { ...clamp, easing: ease });
  // 도장 임팩트 플래시
  const stampFlash = interpolate(frame, [stampDelay, stampDelay + 3, stampDelay + 12], [0, 0.6, 0], clamp);

  // VS 표시 조건: headline에 "vs"가 포함되어 있을 때만
  const hasVs = lines.some((l) => /^\s*vs\s*$/i.test(l));
  const leftImg = images?.[0] || null;
  const rightImg = images?.[1] || null;
  const rawLeftDesc = descriptions?.[0] || null;
  const rawRightDesc = descriptions?.[1] || null;
  // "승리" 텍스트를 description에서 제거 (도장으로 표시)
  const leftDesc = rawLeftDesc?.replace(/\s*승리\s*/, "").trim() || rawLeftDesc;
  const rightDesc = rawRightDesc?.replace(/\s*승리\s*/, "").trim() || rawRightDesc;

  return (
    <AbsoluteFill>
      <MoodBackground mood={mood} transparent={hasImageBg} />
      <div
        style={{
          position: "relative",
          zIndex: 1,
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          padding: "80px 40px",
        }}
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: hasImageBg ? "1fr auto 1fr" : "1fr auto 1fr",
            width: "100%",
            alignItems: "center",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              opacity: leftOpacity,
              transform: `translateX(${leftSlide}px)`,
            }}
          >
            <div
              ref={leftRef}
              style={{
                position: "relative",
                display: "inline-flex",
                flexDirection: "column",
                alignItems: "center",
                textAlign: "center",
                fontSize: T.splitLabel,
                fontWeight: 600,
                lineHeight: 1.6,
                padding: hasImageBg ? "40px 48px" : "40px 24px",
                ...(hasImageBg ? {
                  backgroundColor: "rgba(0,0,0,0.65)",
                  borderRadius: 16,
                  ...(boxWidth ? { width: boxWidth } : {}),
                } : {}),
              }}
            >
              {leftImg && (
                <ImageBadge imageUrl={leftImg} size={120} style={{ margin: "0 auto 16px" }} />
              )}
              <EmphasisAccentText
                text={lines[0] || ""}
                emphasis={emphasis}
                moodCfg={moodCfg}
                countedValues={countedValues}
                glowOpacity={glowOpacity}
              />
              {leftDesc && (
                <div style={{ fontSize: T.splitVsText, color: C.textDim, marginTop: 12, fontWeight: 400, opacity: descOpacity, transform: `translateY(${descSlideY}px)` }}>
                  {leftDesc}
                </div>
              )}
              {/* 승리 도장 */}
              {winnerIdx === 0 && (
                <>
                  <div style={{
                    position: "absolute", inset: 0, borderRadius: 16,
                    backgroundColor: `rgba(${moodCfg.accentRgb},${stampFlash})`,
                    pointerEvents: "none",
                  }} />
                  <div style={{
                    position: "absolute", top: -20, right: -20,
                    opacity: stampOpacity,
                    transform: `scale(${stampScaleVal}) rotate(${stampRotation}deg)`,
                    fontSize: 28, fontWeight: 900,
                    color: "#fff",
                    backgroundColor: "#EF4444",
                    padding: "8px 20px",
                    borderRadius: 8,
                    border: "3px solid #fff",
                    boxShadow: "0 4px 20px rgba(239,68,68,0.5)",
                    zIndex: 10,
                    whiteSpace: "nowrap",
                  }}>
                    승리
                  </div>
                </>
              )}
            </div>
          </div>

          <div
            style={{
              position: "relative",
              width: hasVs ? 60 : 24,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            <div
              style={{
                position: "absolute",
                width: 2,
                height: `${divHeight}%`,
                backgroundColor: moodCfg.accent,
                opacity: 1,
              }}
            />
            {hasVs && (
              <div
                style={{
                  ...vsScale,
                  fontSize: T.splitVsText,
                  fontWeight: 800,
                  color: moodCfg.accent,
                  backgroundColor: C.bg,
                  padding: "16px 24px",
                  borderRadius: 8,
                  border: `1px solid ${moodCfg.accent}33`,
                  position: "relative",
                  zIndex: 1,
                }}
              >
                VS
              </div>
            )}
          </div>

          <div
            style={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              opacity: rightOpacity,
              transform: `translateX(${rightSlide}px)`,
            }}
          >
            <div
              ref={rightRef}
              style={{
                position: "relative",
                display: "inline-flex",
                flexDirection: "column",
                alignItems: "center",
                textAlign: "center",
                fontSize: T.splitLabel,
                fontWeight: 600,
                lineHeight: 1.6,
                padding: hasImageBg ? "40px 48px" : "40px 24px",
                ...(hasImageBg ? {
                  backgroundColor: "rgba(0,0,0,0.65)",
                  borderRadius: 16,
                  ...(boxWidth ? { width: boxWidth } : {}),
                } : {}),
              }}
            >
              {rightImg && (
                <ImageBadge imageUrl={rightImg} size={120} style={{ margin: "0 auto 16px" }} />
              )}
              <EmphasisAccentText
                text={lines.length > 2 ? lines[2] : lines[1] || ""}
                emphasis={emphasis}
                moodCfg={moodCfg}
                countedValues={countedValues}
                glowOpacity={glowOpacity}
              />
              {rightDesc && (
                <div style={{ fontSize: T.splitVsText, color: C.textDim, marginTop: 12, fontWeight: 400, opacity: descOpacity, transform: `translateY(${descSlideY}px)` }}>
                  {rightDesc}
                </div>
              )}
              {/* 승리 도장 */}
              {winnerIdx === 1 && (
                <>
                  <div style={{
                    position: "absolute", inset: 0, borderRadius: 16,
                    backgroundColor: `rgba(${moodCfg.accentRgb},${stampFlash})`,
                    pointerEvents: "none",
                  }} />
                  <div style={{
                    position: "absolute", top: -20, right: -20,
                    opacity: stampOpacity,
                    transform: `scale(${stampScaleVal}) rotate(${stampRotation}deg)`,
                    fontSize: 28, fontWeight: 900,
                    color: "#fff",
                    backgroundColor: "#EF4444",
                    padding: "8px 20px",
                    borderRadius: 8,
                    border: "3px solid #fff",
                    boxShadow: "0 4px 20px rgba(239,68,68,0.5)",
                    zIndex: 10,
                    whiteSpace: "nowrap",
                  }}>
                    승리
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

      </div>
    </AbsoluteFill>
  );
};

/* ================================================================
   ItemsGrid — 아이템 그리드 레이아웃 (6+ items)
   ================================================================ */

const ItemsGrid: React.FC<{
  items: string[];
  delays: number[];
  headlineDelays: number[];
  moodCfg: MoodConfig;
  reveal: string;
  itemIcons?: string[];
  itemFlags?: string[];
  motionConfig?: MotionConfig;
}> = ({ items, delays, headlineDelays, moodCfg, reveal, itemIcons, itemFlags, motionConfig }) => {
  const C = useC();
  const T = usePresetTypo();
  const L = usePresetLayout();
  const frame = useCurrentFrame();
  const cols = items.length === 4 ? (items.some(it => it.length > 8) ? 2 : 4)
    : items.length >= 5 ? 3 : items.length >= 3 ? 3 : 2;
  const isFlash = reveal === "stagger_then_flash";
  const allDone = Math.max(...delays, ...headlineDelays) + 20;
  const flashGlow = isFlash
    ? interpolate(frame, [allDone, allDone + 4, allDone + 30], [0, 1, 0.3], clamp)
    : 0;
  const entranceDur = motionConfig?.entrance.duration || 15;
  const entranceType = motionConfig?.entrance.type || "fadeRise";

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: `repeat(${cols}, 1fr)`,
        gap: L.itemsGap,
        width: "100%",
        maxWidth: L.maxContentWidth,
        margin: `${L.sectionMarginTop}px auto 0`,
      }}
    >
      {items.map((item, i) => {
        const d = delays[i] || 0;
        // entrance type별 애니메이션
        let opacity: number, rise: number, scaleVal = 1, extraTransform = "";
        if (entranceType === "bounce") {
          opacity = interpolate(frame, [d, d + entranceDur * 0.3], [0, 1], clamp);
          const bounceP = interpolate(frame, [d, d + entranceDur], [0, 1], clamp);
          scaleVal = bounceP < 0.5 ? interpolate(bounceP, [0, 0.5], [0.3, 1.15], clamp) : interpolate(bounceP, [0.5, 1], [1.15, 1], clamp);
          rise = 0;
        } else if (entranceType === "scale" || entranceType === "spring") {
          opacity = interpolate(frame, [d, d + entranceDur * 0.4], [0, 1], clamp);
          scaleVal = interpolate(frame, [d, d + entranceDur], [0.5, 1], { ...clamp, easing: Easing.out(Easing.exp) });
          rise = 0;
        } else if (entranceType === "overshoot") {
          opacity = interpolate(frame, [d, d + entranceDur * 0.3], [0, 1], clamp);
          rise = interpolate(frame, [d, d + entranceDur], [-30, 0], { ...clamp, easing: Easing.out(Easing.back(1.5)) });
        } else {
          // fadeRise (기본)
          opacity = interpolate(frame, [d, d + entranceDur], [0, 1], clamp);
          rise = interpolate(frame, [d, d + entranceDur], [12, 0], { ...clamp, easing: ease });
        }
        // emphasis 후처리
        if (motionConfig?.emphasis && frame > d + entranceDur) {
          const eD = d + entranceDur + (motionConfig.emphasis.delay || 0);
          const eDur = motionConfig.emphasis.duration || 20;
          if (motionConfig.emphasis.type === "shake") {
            const sp = interpolate(frame, [eD, eD + eDur], [0, 1], clamp);
            if (sp > 0 && sp < 1) extraTransform = ` translateX(${Math.sin(sp * Math.PI * 6) * (motionConfig.emphasis.intensity || 4) * (1 - sp)}px)`;
          } else if (motionConfig.emphasis.type === "pulse") {
            const pp = interpolate(frame, [eD, eD + eDur], [0, 1], clamp);
            if (pp > 0) scaleVal *= 1 + Math.sin(pp * Math.PI * 2) * 0.03;
          } else if (motionConfig.emphasis.type === "glitch") {
            const gp = interpolate(frame, [eD, eD + eDur], [0, 1], clamp);
            if (gp > 0 && gp < 1) {
              const glitchX = Math.sin(gp * Math.PI * 12) * (motionConfig.emphasis.intensity || 6) * (1 - gp);
              const glitchY = Math.cos(gp * Math.PI * 8) * 2 * (1 - gp);
              extraTransform = ` translate(${glitchX}px, ${glitchY}px)`;
            }
          } else if (motionConfig.emphasis.type === "bounce") {
            const bp = interpolate(frame, [eD, eD + eDur], [0, 1], clamp);
            if (bp > 0) scaleVal *= 1 + Math.abs(Math.sin(bp * Math.PI * 3)) * 0.06 * (1 - bp);
          }
        }
        const borderGlow =
          flashGlow > 0
            ? `0 0 20px rgba(${moodCfg.accentRgb},${flashGlow})`
            : "none";

        return (
          <div
            key={i}
            style={{
              opacity,
              transform: `translateY(${rise}px) scale(${scaleVal})${extraTransform}`,
              padding: "14px 16px",
              borderRadius: 16,
              border: `2px solid ${moodCfg.accent}${flashGlow > 0 ? "FF" : "BB"}`,
              backgroundColor: "rgba(0,0,0,0.4)",
              textAlign: "center",
              fontSize: T.itemText,
              fontWeight: 600,
              color: C.text,
              boxShadow: borderGlow,
              transition: "box-shadow 0.1s",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 6,
            }}
          >
            {/* 국기가 있으면 국기 우선 (아이콘 숨김), 없으면 아이콘 */}
            {itemFlags?.[i] ? (
              <FlagCard countryCode={itemFlags[i]} label={item} width={items.length > 6 ? 120 : 160} />
            ) : (
              <>
                {itemIcons?.[i] && (() => {
                  const Ic = resolveIcon(itemIcons[i]);
                  return Ic ? (
                    <Icon icon={Ic} size={items.length > 6 ? 20 : 24} color={moodCfg.accent} />
                  ) : null;
                })()}
                <TextWithBreaks text={item} />
              </>
            )}
          </div>
        );
      })}
    </div>
  );
};

/* ================================================================
   PersonCardRow — 인물 카드 가로 레이아웃
   ================================================================ */

const PersonCardRow: React.FC<{
  items: string[];
  delays: number[];
  moodCfg: MoodConfig;
  images?: string[];
  itemStatuses?: Array<"positive" | "negative" | "neutral" | "warning">;
}> = ({ items, delays, moodCfg, images, itemStatuses }) => {
  const C = useC();
  const frame = useCurrentFrame();
  const count = items.length;
  const cardW = count <= 3 ? 280 : count <= 4 ? 240 : 200;
  const imgH = count <= 3 ? 280 : 240;

  return (
    <div
      style={{
        display: "flex",
        gap: 20,
        justifyContent: "center",
        marginTop: 28,
      }}
    >
      {items.map((item, i) => {
        const d = delays[i] || 0;
        const opacity = interpolate(frame, [d, d + 18], [0, 1], clamp);
        const slideY = interpolate(frame, [d, d + 18], [30, 0], {
          ...clamp,
          easing: ease,
        });
        const img = images?.[i];
        const imgSrc = img
          ? resolveAsset(img)
          : null;
        const status = itemStatuses?.[i];
        const isNegative = status === "negative";

        return (
          <div
            key={i}
            style={{
              opacity,
              transform: `translateY(${slideY}px)`,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              width: cardW,
              borderRadius: 16,
              backgroundColor: "rgba(0,0,0,0.4)",
              border: `2px solid ${isNegative ? "#EF4444BB" : moodCfg.accent + "BB"}`,
              overflow: "hidden",
            }}
          >
            {/* Person image or silhouette */}
            <div
              style={{
                width: "100%",
                height: imgH,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                backgroundColor: isNegative
                  ? "rgba(239,68,68,0.08)"
                  : "rgba(255,255,255,0.02)",
                overflow: "hidden",
              }}
            >
              {imgSrc ? (
                <Img
                  src={imgSrc}
                  style={{
                    width: "100%",
                    height: "100%",
                    objectFit: "cover",
                    objectPosition: "center 20%",
                    filter: isNegative ? "grayscale(0.6)" : "none",
                  }}
                />
              ) : (
                <svg
                  width={imgH * 0.5}
                  height={imgH * 0.5}
                  viewBox="0 0 24 24"
                  fill="none"
                >
                  <circle
                    cx="12"
                    cy="8"
                    r="4"
                    fill={isNegative ? "rgba(239,68,68,0.25)" : "rgba(255,255,255,0.15)"}
                  />
                  <path
                    d="M4 21c0-4.4 3.6-8 8-8s8 3.6 8 8"
                    fill={isNegative ? "rgba(239,68,68,0.15)" : "rgba(255,255,255,0.1)"}
                  />
                </svg>
              )}
            </div>

            {/* Name + status */}
            <div
              style={{
                padding: "14px 10px",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 6,
                width: "100%",
              }}
            >
              <span
                style={{
                  fontSize: count <= 3 ? 24 : 22,
                  fontWeight: 600,
                  color: C.text,
                  textAlign: "center",
                  lineHeight: 1.3,
                }}
              >
                <TextWithBreaks text={item} />
              </span>
              {isNegative && (
                <span
                  style={{
                    fontSize: 26,
                    fontWeight: 700,
                    color: "#EF4444",
                    letterSpacing: 2,
                  }}
                >
                  ✕ 폭사
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};

/* ================================================================
   ItemsList — 아이템 리스트 레이아웃 (3-5 items)
   ================================================================ */

const ItemsList: React.FC<{
  items: string[];
  delays: number[];
  headlineDelays: number[];
  moodCfg: MoodConfig;
  emphasis: string;
  concept: string;
  images?: string[];
  itemIcons?: string[];
  itemFlags?: string[];
  itemStatuses?: Array<"positive" | "negative" | "neutral" | "warning">;
  motionConfig?: MotionConfig;
}> = ({ items, delays, headlineDelays, moodCfg, emphasis, concept, images, itemIcons, itemFlags, itemStatuses, motionConfig }) => {
  const C = useC();
  const T = usePresetTypo();
  const L = usePresetLayout();
  const frame = useCurrentFrame();
  const showBadge = emphasis === "sequence" || emphasis === "person";
  const hasImages = images && images.length > 0;
  const conceptLower = concept.toLowerCase();
  const hasSpotlightHint =
    conceptLower.includes("spotlight") ||
    conceptLower.includes("강조") ||
    conceptLower.includes("마지막");

  // 이미지가 있으면 가로 카드형 레이아웃
  if (hasImages) {
    return (
      <div
        style={{
          display: "flex",
          gap: L.itemsGap,
          width: "100%",
          justifyContent: "center",
          flexWrap: "wrap",
          marginTop: L.sectionMarginTop,
        }}
      >
        {items.map((item, i) => {
          const d = delays[i] || 0;
          const opacity = interpolate(frame, [d, d + 18], [0, 1], clamp);
          const slideY = interpolate(frame, [d, d + 18], [24, 0], {
            ...clamp,
            easing: ease,
          });
          const img = images[i] || null;
          const isLast = i === items.length - 1;
          const spotlight = hasSpotlightHint && isLast;

          const imgSrc = img
            ? resolveAsset(img)
            : null;

          return (
            <div
              key={i}
              style={{
                opacity,
                transform: `translateY(${slideY}px)`,
                display: "flex",
                flexDirection: "column",
                borderRadius: 16,
                backgroundColor: "rgba(0,0,0,0.4)",
                border: `2px solid ${spotlight ? moodCfg.accent : moodCfg.accent + "BB"}`,
                width: items.length <= 3 ? 260 : 200,
                overflow: "hidden",
              }}
            >
              {imgSrc && (
                <div style={{ width: "100%", height: items.length <= 3 ? 140 : 110, overflow: "hidden" }}>
                  <Img
                    src={imgSrc}
                    style={{
                      width: "100%",
                      height: "100%",
                      objectFit: "cover",
                    }}
                  />
                </div>
              )}
              <span
                style={{
                  fontSize: T.itemText,
                  fontWeight: spotlight ? 700 : 600,
                  color: spotlight ? moodCfg.accent : C.text,
                  textAlign: "center",
                  lineHeight: 1.3,
                  padding: "14px 12px",
                }}
              >
                <TextWithBreaks text={item} />
              </span>
            </div>
          );
        })}
      </div>
    );
  }

  // 이미지 없으면 기존 세로 리스트 — 가장 긴 텍스트 기준 너비
  // 텍스트 길이 기반 너비 계산 (가장 긴 아이템 + 좌우 5% 여백)
  const maxTextLen = Math.max(...items.map(t => t.length));
  // 한글 1자 ≈ fontSize, 영문 ≈ 0.6*fontSize. 보수적으로 0.85 적용 + 아이콘/배지 여백
  const estimatedTextWidth = maxTextLen * (T.itemText || 20) * 0.85 + 80; // 80px = 아이콘+패딩
  const fitWidth = Math.min(Math.max(estimatedTextWidth * 1.1, 300), L.maxContentWidth); // 좌우 5% 여백 = 1.1배
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 12,
        width: fitWidth,
        margin: `${L.sectionMarginTop}px auto 0`,
      }}
    >
      {items.map((item, i) => {
        const d = delays[i] || 0;
        const entrDur = motionConfig?.entrance.duration || 15;
        const entrType = motionConfig?.entrance.type || "fadeSlide";
        let opacity: number, slideX = 0, scaleVal = 1, extraT = "";
        if (entrType === "bounce") {
          opacity = interpolate(frame, [d, d + entrDur * 0.3], [0, 1], clamp);
          const bp = interpolate(frame, [d, d + entrDur], [0, 1], clamp);
          scaleVal = bp < 0.5 ? interpolate(bp, [0, 0.5], [0.3, 1.15], clamp) : interpolate(bp, [0.5, 1], [1.15, 1], clamp);
        } else if (entrType === "scale" || entrType === "spring") {
          opacity = interpolate(frame, [d, d + entrDur * 0.4], [0, 1], clamp);
          scaleVal = interpolate(frame, [d, d + entrDur], [0.5, 1], { ...clamp, easing: Easing.out(Easing.exp) });
        } else {
          opacity = interpolate(frame, [d, d + entrDur], [0, 1], clamp);
          slideX = interpolate(frame, [d, d + entrDur], [-20, 0], { ...clamp, easing: ease });
        }
        if (motionConfig?.emphasis && frame > d + entrDur) {
          const eD = d + entrDur + (motionConfig.emphasis.delay || 0);
          const eDur = motionConfig.emphasis.duration || 20;
          if (motionConfig.emphasis.type === "shake") {
            const sp = interpolate(frame, [eD, eD + eDur], [0, 1], clamp);
            if (sp > 0 && sp < 1) extraT = ` translateX(${Math.sin(sp * Math.PI * 6) * (motionConfig.emphasis.intensity || 4) * (1 - sp)}px)`;
          } else if (motionConfig.emphasis.type === "pulse") {
            const pp = interpolate(frame, [eD, eD + eDur], [0, 1], clamp);
            if (pp > 0) scaleVal *= 1 + Math.sin(pp * Math.PI * 2) * 0.03;
          } else if (motionConfig.emphasis.type === "glitch") {
            const gp = interpolate(frame, [eD, eD + eDur], [0, 1], clamp);
            if (gp > 0 && gp < 1) {
              extraT = ` translate(${Math.sin(gp * Math.PI * 12) * (motionConfig.emphasis.intensity || 6) * (1 - gp)}px, ${Math.cos(gp * Math.PI * 8) * 2 * (1 - gp)}px)`;
            }
          } else if (motionConfig.emphasis.type === "bounce") {
            const bp = interpolate(frame, [eD, eD + eDur], [0, 1], clamp);
            if (bp > 0) scaleVal *= 1 + Math.abs(Math.sin(bp * Math.PI * 3)) * 0.06 * (1 - bp);
          }
        }
        const isLast = i === items.length - 1;
        const spotlight = hasSpotlightHint && isLast;

        return (
          <div
            key={i}
            style={{
              opacity,
              transform: `translateX(${slideX}px) scale(${scaleVal})${extraT}`,
              display: "flex",
              alignItems: "center",
              gap: 14,
              padding: "12px 28px",
              borderRadius: 50,
              backgroundColor: spotlight
                ? `rgba(${moodCfg.accentRgb},0.15)`
                : "rgba(0,0,0,0.4)",
              border: `2px solid ${spotlight ? moodCfg.accent : moodCfg.accent + "BB"}`,
            }}
          >
            {/* 국기가 있으면 국기 우선 (아이콘 숨김), 없으면 아이콘 */}
            {itemFlags?.[i] ? (
              <FlagCard countryCode={itemFlags[i]} width={100} />
            ) : itemIcons?.[i] ? (() => {
              const Ic = resolveIcon(itemIcons[i]);
              return Ic ? <IconBadge icon={Ic} size={36} /> : null;
            })() : null}
            {/* Per-item status dot */}
            {itemStatuses?.[i] && (
              <StatusDot status={itemStatuses[i]} />
            )}
            {/* Sequence/person badge (fallback) */}
            {showBadge && !itemIcons?.[i] && !itemFlags?.[i] && !itemStatuses?.[i] && (
              <CircleBadge
                text={
                  emphasis === "person"
                    ? item.charAt(0)
                    : String(i + 1)
                }
                size={36}
                filled={spotlight}
              />
            )}
            <span
              style={{
                fontSize: T.itemText,
                fontWeight: spotlight ? 700 : 500,
                color: spotlight ? moodCfg.accent : C.text,
                flex: 1,
              }}
            >
              <TextWithBreaks text={item} />
            </span>
          </div>
        );
      })}
    </div>
  );
};

/* ================================================================
   QuoteDisplay — 인용문 전용 레이아웃
   ================================================================ */

// mono 폰트는 usePresetFonts()가 --font-mono CSS var로 주입 — 별도 로딩 불필요
const GYEONGGI_FONT_FAMILY = "var(--font-mono, 'GyeonggiMillenniumBatang', serif)";

const QuoteDisplay: React.FC<{
  items: string[];
  source: string;
  moodCfg: MoodConfig;
  reveal: string;
  speed: number;
  mood: string;
  hasImageBg?: boolean;
  portrait?: string;
}> = ({ items, source, moodCfg, reveal, speed, mood, hasImageBg, portrait }) => {
  const C = useC();
  const T = usePresetTypo();
  const frame = useCurrentFrame();
  const s = (f: number) => Math.round(f / speed);
  const quoteText = items[0] || "";

  // typewriter effect
  const isTypewriter = reveal === "typewriter";
  const charCount = quoteText.length;
  const typeLen = Math.max(charCount * 2, 1);
  const visibleChars = isTypewriter
    ? Math.floor(
        interpolate(frame, [s(10), s(10) + typeLen], [0, charCount], clamp),
      )
    : charCount;
  const displayText = isTypewriter
    ? quoteText.slice(0, visibleChars)
    : quoteText;

  const quoteOpacity = interpolate(frame, [s(5), s(15)], [0, 1], clamp);
  const quoteRise = interpolate(frame, [s(5), s(15)], [15, 0], {
    ...clamp,
    easing: ease,
  });

  const markOpacity = interpolate(frame, [s(3), s(10)], [0, 0.6], clamp);
  const sourceOpacity = interpolate(
    frame,
    [s(10) + (isTypewriter ? charCount * 2 + 10 : 25), s(10) + (isTypewriter ? charCount * 2 + 25 : 40)],
    [0, 0.6],
    clamp,
  );

  const portraitSrc = portrait ? resolveAsset(portrait) : null;
  const portraitOpacity = interpolate(frame, [0, 20], [0, 1], clamp);

  const quoteFontSize = T.quoteText;
  const markFontSize = T.quoteMarkSize * 1.2;

  return (
    <AbsoluteFill>
      <MoodBackground mood={mood} transparent={hasImageBg || !!portrait} />

      {/* Portrait as background image */}
      {portraitSrc && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            zIndex: 0,
            opacity: portraitOpacity * 0.3,
            overflow: "hidden",
          }}
        >
          <Img
            src={portraitSrc}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              filter: "blur(2px) grayscale(0.4)",
            }}
          />
          <div
            style={{
              position: "absolute",
              inset: 0,
              background: `radial-gradient(ellipse at center, transparent 30%, ${C.bg} 80%)`,
            }}
          />
        </div>
      )}

      <div
        style={{
          position: "relative",
          zIndex: 1,
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          padding: "80px 100px",
        }}
      >
        {/* Quote text box — inline-grid 3행: 여는따옴표(좌) / 텍스트 / 닫는따옴표(우) */}
        <div
          style={{
            display: "inline-grid",
            gridTemplateRows: "auto auto auto auto",
            opacity: quoteOpacity,
            transform: `translateY(${quoteRise}px)`,
          }}
        >
          {/* 1행: 여는 따옴표 — 왼쪽 정렬 */}
          <div style={{
            justifySelf: "start",
            fontSize: markFontSize,
            fontWeight: 700,
            fontFamily: GYEONGGI_FONT_FAMILY,
            color: moodCfg.accent,
            opacity: markOpacity,
            lineHeight: 1,
            marginBottom: "-0.8em",
            marginLeft: "-0.6em",
            userSelect: "none",
          }}>&ldquo;</div>

          {/* 2행: 인용 텍스트 */}
          <div style={{
            fontSize: quoteFontSize,
            fontWeight: 400,
            fontFamily: GYEONGGI_FONT_FAMILY,
            color: C.text,
            textAlign: "center",
            lineHeight: 1.65,
            whiteSpace: "pre-line",
            wordBreak: "keep-all",
          }}>
            {displayText}
            {isTypewriter && visibleChars < charCount && (
              <span style={{
                display: "inline-block",
                width: 3,
                height: "1em",
                backgroundColor: moodCfg.accent,
                marginLeft: 2,
                opacity: frame % 20 < 10 ? 1 : 0,
              }} />
            )}
          </div>

          {/* 3행: 닫는 따옴표 — 오른쪽 정렬 */}
          <div style={{
            justifySelf: "end",
            fontSize: markFontSize,
            fontWeight: 700,
            fontFamily: GYEONGGI_FONT_FAMILY,
            color: moodCfg.accent,
            opacity: markOpacity,
            lineHeight: 1,
            marginRight: "-0.6em",
            userSelect: "none",
          }}>&rdquo;</div>

          {/* 4행: 스피커/출처 — 오른쪽 정렬 */}
          {source && (
            <div style={{
              justifySelf: "center",
              marginTop: "-1.6em",
              opacity: sourceOpacity,
              fontSize: T.sourceText,
              color: C.textMuted,
              fontFamily: GYEONGGI_FONT_FAMILY,
              letterSpacing: "0.05em",
            }}>
              — {source}
            </div>
          )}
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* ================================================================
   LogoGridLayout — 브랜드 로고 그리드
   ================================================================ */

/** 브랜드 컬러 맵 */
const BRAND_COLORS: Record<string, string> = {
  apple: "#A2AAAD",
  microsoft: "#00A4EF",
  nvidia: "#76B900",
  amazon: "#FF9900",
  alphabet: "#4285F4",
  google: "#4285F4",
  meta: "#0668E1",
  tesla: "#CC0000",
};

/** 로고 이미지 경로 (Simple Icons에 없는 브랜드용) */
const LOGO_IMAGE_PATH: Record<string, string> = {
  amazon: "logos/amazon.svg",
  microsoft: "logos/microsoft.svg",
};

const renderItemLeadVisual = ({
  flag,
  icon,
  logo,
  flagLabel,
  flagWidth = 100,
  iconSize = 36,
  logoSize = 40,
  iconFilled = false,
}: {
  flag?: string;
  icon?: string;
  logo?: string;
  flagLabel?: string;
  flagWidth?: number;
  iconSize?: number;
  logoSize?: number;
  iconFilled?: boolean;
}): React.ReactNode => {
  if (flag) {
    return <FlagCard countryCode={flag} label={flagLabel} width={flagWidth} />;
  }

  if (icon) {
    const IconComp = resolveIcon(icon);
    if (IconComp) {
      return <IconBadge icon={IconComp} size={iconSize} filled={iconFilled} />;
    }
  }

  if (logo) {
    const resolvedLogo = resolveLogo(logo);
    if (resolvedLogo || LOGO_IMAGE_PATH[logo.toLowerCase().replace(/\s+/g, "")]) {
      return <LogoBadge logo={logo} size={logoSize} />;
    }
  }

  return null;
};

const LogoGridLayout: React.FC<{
  items: string[];
  values: number[];
  unit: string;
  headline: string;
  moodCfg: MoodConfig;
  source: string;
  mood: string;
  emphasis: string;
  countedValues: number[];
  glowOpacity: number;
  hasImageBg?: boolean;
  logoMap?: Record<string, string>;
}> = ({
  items,
  values,
  unit,
  headline,
  moodCfg,
  source,
  mood,
  emphasis,
  countedValues,
  glowOpacity,
  hasImageBg,
  logoMap,
}) => {
  const C = useC();
  const T = usePresetTypo();
  const L = usePresetLayout();
  const frame = useCurrentFrame();
  const maxVal = Math.max(...values, 1);
  const lines = headline.split("\n").filter((l: string) => l.trim());

  // headline fade
  const headlineFade = useFade(5, 15, 0.8);

  // source fade
  const sourceFade = useFade(items.length * 8 + 40, 15, 0.8);

  return (
    <AbsoluteFill>
      <MoodBackground mood={mood} transparent={hasImageBg} />
      <div
        style={{
          position: "relative",
          zIndex: 2,
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          padding: `${L.scenePadding[0]}px ${L.scenePadding[1]}px`,
          paddingBottom: `${L.scenePadding[0] + 100}px`,
          gap: L.sectionMarginTop,
        }}
      >
        {/* Headline */}
        <div style={{ opacity: headlineFade, textAlign: "center", maxWidth: "90%" }}>
          {lines.map((line, i) => (
            <div
              key={i}
              style={{
                fontSize: T.chartTitle,
                fontWeight: 700,
                color: C.text,
                lineHeight: 1.3,
              }}
            >
              <AccentText text={line} baseColor={C.text} />
            </div>
          ))}
        </div>

        {/* Logo Grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: items.length <= 4
              ? `repeat(${items.length}, 1fr)`
              : items.length <= 6
                ? "repeat(3, 1fr)"
                : "repeat(4, 1fr)",
            gap: L.gap,
            width: "100%",
            maxWidth: L.maxContentWidth,
          }}
        >
          {items.map((item, i) => {
            const delay = 10 + i * 8;
            const itemFade = interpolate(frame, [delay, delay + 12], [0, 1], clamp);
            const itemScale = interpolate(frame, [delay, delay + 12], [0.85, 1], clamp);
            const key = (logoMap?.[item] || item).toLowerCase().replace(/\s+/g, "");
            const brandColor = BRAND_COLORS[key] || moodCfg.accent;
            const logoPath = LOGO_IMAGE_PATH[key];
            const LogoComp = resolveLogo(logoMap?.[item] || item);
            const val = values[i];

            return (
              <div
                key={i}
                style={{
                  opacity: itemFade,
                  transform: `scale(${itemScale})`,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 12,
                  padding: "20px 12px",
                  borderRadius: 16,
                  backgroundColor: "rgba(255,255,255,0.05)",
                  border: "1px solid rgba(255,255,255,0.1)",
                }}
              >
                {/* Logo */}
                <div
                  style={{
                    width: 64,
                    height: 64,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  {logoPath ? (
                    <Img
                      src={resolveAsset(logoPath)}
                      style={{ width: 52, height: 52, objectFit: "contain" }}
                    />
                  ) : LogoComp ? (
                    <LogoComp size={52} color={brandColor} />
                  ) : (
                    <div
                      style={{
                        width: 52,
                        height: 52,
                        borderRadius: 12,
                        backgroundColor: brandColor,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: 24,
                        fontWeight: 700,
                        color: "#FFF",
                      }}
                    >
                      {item.charAt(0)}
                    </div>
                  )}
                </div>

                {/* Company name */}
                <div
                  style={{
                    fontSize: T.labelText,
                    fontWeight: 600,
                    color: C.text,
                    textAlign: "center",
                    lineHeight: 1.2,
                  }}
                >
                  <TextWithBreaks text={item} />
                </div>

                {/* Value */}
                {val !== undefined && (
                  <div
                    style={{
                      fontSize: 26,
                      fontWeight: 700,
                      color: brandColor,
                    }}
                  >
                    {fmtNum(val)}{unit}
                  </div>
                )}
              </div>
            );
          })}
        </div>

      </div>
    </AbsoluteFill>
  );
};

/* ================================================================
   BarDisplay — 수평 바 차트
   ================================================================ */

const BarDisplay: React.FC<{
  items: string[];
  values: number[];
  unit: string;
  headline: string;
  moodCfg: MoodConfig;
  source: string;
  mood: string;
  emphasis: string;
  countedValues: number[];
  glowOpacity: number;
  hasImageBg?: boolean;
  subtitles?: SubtitleEntry[];
  fps?: number;
}> = ({
  items,
  values,
  unit,
  headline,
  moodCfg,
  source,
  mood,
  emphasis,
  countedValues,
  glowOpacity,
  hasImageBg,
  subtitles,
  fps = 30,
}) => {
  const C = useC();
  const T = usePresetTypo();
  const L = usePresetLayout();
  const frame = useCurrentFrame();
  const hasNegative = values.some((v) => v < 0);

  // 자막 동기화: 아이템별 등장 딜레이
  const itemDelays = (subtitles && subtitles.length > 0)
    ? computeItemSubtitleDelays(subtitles, items, fps)
    : items.map((_, i) => 15 + i * 10);  // fallback: 고정 딜레이
  const maxVal = Math.max(...values, 1);
  const NEG_COLOR = "#EF4444";
  // 마이너스 포함: 0축 위치를 전체 범위(min~max) 대비로 계산
  const rangeMin = Math.min(...values, 0);
  const rangeMax = Math.max(...values, 0);
  const totalRange = rangeMax - rangeMin || 1;
  const zeroPos = hasNegative ? (Math.abs(rangeMin) / totalRange) * 100 : 0;

  const headlineOpacity = interpolate(frame, [5, 18], [0, 1], clamp);
  const headlineRise = interpolate(frame, [5, 18], [15, 0], {
    ...clamp,
    easing: ease,
  });
  const sourceFade = interpolate(
    frame,
    [15 + items.length * 10 + 20, 15 + items.length * 10 + 35],
    [0, 0.4],
    clamp,
  );

  return (
    <AbsoluteFill>
      <MoodBackground mood={mood} transparent={hasImageBg} />
      <div
        style={{
          position: "relative",
          zIndex: 1,
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          padding: `${L.scenePadding[0]}px 80px`,
          paddingBottom: `${L.scenePadding[0] + 100}px`,
        }}
      >
        {/* Headline */}
        <div
          style={{
            opacity: headlineOpacity,
            transform: `translateY(${headlineRise}px)`,
            fontSize: T.chartTitle,
            fontWeight: 600,
            marginBottom: L.sectionMarginTop,
            textAlign: "center",
            lineHeight: 1.4,
          }}
        >
          <EmphasisAccentText
            text={headline}
            emphasis={emphasis}
            moodCfg={moodCfg}
            countedValues={countedValues}
            glowOpacity={glowOpacity}
            accentFontSizeOverride={80}
          />
        </div>

        {/* Bars */}
        <div
          style={{
            width: "100%",
            maxWidth: L.maxContentWidth,
            display: "flex",
            flexDirection: "column",
            gap: 12,
          }}
        >
          {items.map((label, i) => {
            const d = itemDelays[i] || (15 + i * 10);
            const val = values[i] || 0;
            const isNeg = val < 0;
            // barProgress: 0→1 애니메이션 (비율은 바 너비에서 적용)
            const barProgress = interpolate(
              frame,
              [d, d + 25],
              [0, 1],
              { ...clamp, easing: ease8020 },
            );
            const labelOpacity = interpolate(frame, [d, d + 12], [0, 1], clamp);
            const valOpacity = interpolate(
              frame,
              [d + 15, d + 25],
              [0, 1],
              clamp,
            );
            // 바 너비: 전체 범위 대비 비율
            const barWidthPct = hasNegative
              ? (Math.abs(val) / totalRange) * 100 * barProgress
              : (val / maxVal) * 100 * barProgress;

            return (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 16,
                  opacity: labelOpacity,
                }}
              >
                <div
                  style={{
                    minWidth: L.barLabelWidth,
                    textAlign: "right",
                    fontSize: T.labelText,
                    fontWeight: 500,
                    color: C.textMuted,
                    flexShrink: 0,
                    whiteSpace: "nowrap",
                  }}
                >
                  {label}
                </div>

                {hasNegative ? (
                  /* 마이너스 포함: 0축 기준 양방향 바 */
                  <div
                    style={{
                      flex: 1,
                      height: L.barHeight,
                      backgroundColor: "rgba(255,255,255,0.05)",
                      borderRadius: L.barHeight / 2,
                      position: "relative",
                    }}
                  >
                    {/* 0축 라인 */}
                    <div
                      style={{
                        position: "absolute",
                        left: `${zeroPos}%`,
                        top: -4,
                        bottom: -4,
                        width: 2,
                        backgroundColor: "rgba(255,255,255,0.3)",
                        zIndex: 2,
                      }}
                    />
                    {isNeg ? (
                      /* 마이너스 바: 0축에서 왼쪽으로 */
                      <div
                        style={{
                          position: "absolute",
                          right: `${100 - zeroPos}%`,
                          top: 0,
                          height: "100%",
                          width: `${barWidthPct}%`,
                          backgroundColor: NEG_COLOR,
                          borderRadius: `${L.barHeight / 2}px 0 0 ${L.barHeight / 2}px`,
                        }}
                      />
                    ) : (
                      /* 플러스 바: 0축에서 오른쪽으로 */
                      <div
                        style={{
                          position: "absolute",
                          left: `${zeroPos}%`,
                          top: 0,
                          height: "100%",
                          width: `${barWidthPct}%`,
                          backgroundColor: moodCfg.accent,
                          borderRadius: `0 ${L.barHeight / 2}px ${L.barHeight / 2}px 0`,
                        }}
                      />
                    )}
                  </div>
                ) : (
                  /* 양수만: 기존 레이아웃 */
                  <div
                    style={{
                      flex: 1,
                      height: L.barHeight,
                      backgroundColor: "rgba(255,255,255,0.05)",
                      borderRadius: L.barHeight / 2,
                      overflow: "hidden",
                      position: "relative",
                    }}
                  >
                    <div
                      style={{
                        width: `${barWidthPct}%`,
                        height: "100%",
                        backgroundColor: moodCfg.accent,
                        borderRadius: L.barHeight / 2,
                      }}
                    />
                  </div>
                )}

                <div
                  style={{
                    opacity: valOpacity,
                    minWidth: L.barValueWidth,
                    fontSize: T.chartValue,
                    fontWeight: 700,
                    color: isNeg ? NEG_COLOR : moodCfg.accent,
                    textAlign: "left",
                    flexShrink: 0,
                    whiteSpace: "nowrap",
                  }}
                >
                  {(() => {
                    const sign = hasNegative && !isNeg ? "+" : "";
                    const prefix = unit === "$" || unit === "₩" ? unit : "";
                    return `${prefix}${sign}${fmtNum(val)}`;
                  })()}
                </div>
              </div>
            );
          })}
        </div>

        {/* Unit */}
        {unit && (
          <div
            style={{
              opacity: sourceFade,
              fontSize: T.splitVsText,
              color: C.textMuted,
              marginTop: 16,
            }}
          >
            (단위: {unit})
          </div>
        )}

      </div>
    </AbsoluteFill>
  );
};

/* ================================================================
   PieChartDisplay — SVG 도넛 차트
   ================================================================ */

const PIE_COLORS = ["#F59E0B", "#3B82F6", "#10B981", "#EF4444", "#8B5CF6", "#6B7280", "#EC4899", "#14B8A6"];

const PieChartDisplay: React.FC<{
  items: string[];
  values: number[];
  unit: string;
  headline: string;
  moodCfg: MoodConfig;
  source: string;
  mood: string;
  hasImageBg?: boolean;
  chartConfig?: { maxSlices?: number; highlightIndex?: number; showTotal?: boolean };
}> = ({ items, values, unit, headline, moodCfg, source, mood, hasImageBg, chartConfig }) => {
  const C = useC();
  const T = usePresetTypo();
  const L = usePresetLayout();
  const frame = useCurrentFrame();
  const lines = headline.split("\n").filter((l: string) => l.trim());
  const headlineFade = useFade(5, 15, 0.8);
  const sourceFade = useFade(items.length * 6 + 60, 15, 0.8);

  const maxSlices = chartConfig?.maxSlices ?? 8;
  const displayItems = items.slice(0, maxSlices);
  const displayValues = values.slice(0, maxSlices);
  const total = displayValues.reduce((a, b) => a + b, 0);

  // SVG donut
  const cx = 200, cy = 200, r = 150, strokeW = 60;
  const circumference = 2 * Math.PI * r;

  // sweep 애니메이션: frame 10→70 에서 0→360
  const sweepProgress = interpolate(frame, [10, 70], [0, 1], { ...clamp, easing: ease8020 });

  // 각 슬라이스의 시작 각도와 크기 계산
  let accumulated = 0;
  const slices = displayValues.map((val, i) => {
    const fraction = total > 0 ? val / total : 0;
    const startAngle = accumulated;
    accumulated += fraction;
    return { fraction, startAngle, color: PIE_COLORS[i % PIE_COLORS.length] };
  });

  return (
    <AbsoluteFill>
      <MoodBackground mood={mood} transparent={hasImageBg} />
      <div
        style={{
          position: "relative",
          zIndex: 2,
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          padding: `${L.scenePadding[0]}px ${L.scenePadding[1]}px`,
          paddingBottom: `${L.scenePadding[0] + 100}px`,
          gap: L.gap,
        }}
      >
        {/* Headline */}
        <div style={{ opacity: headlineFade, textAlign: "center", maxWidth: "90%" }}>
          {lines.map((line, i) => (
            <div key={i} style={{ fontSize: T.chartTitle, fontWeight: 700, color: C.text, lineHeight: 1.3 }}>
              <AccentText text={line} baseColor={C.text} />
            </div>
          ))}
        </div>

        {/* Chart + Legend row */}
        <div style={{ display: "flex", alignItems: "center", gap: 48, width: "100%", maxWidth: L.maxContentWidth, justifyContent: "center" }}>
          {/* SVG Donut */}
          <svg width={700} height={700} viewBox="0 0 400 400" style={{ flexShrink: 0 }}>
            {/* 역순 렌더링: slice 0(accent)이 DOM 마지막 = 최상단 z-order → 경계 bleed 방지 */}
            {[...slices].map((_, ri) => {
              const i = slices.length - 1 - ri;
              const slice = slices[i];
              // 글로벌 sweep: 0→1 진행 중 이 슬라이스가 보이는 비율 계산
              const sliceEnd = slice.startAngle + slice.fraction;
              let visibleFraction = 0;
              if (sweepProgress >= sliceEnd) {
                visibleFraction = slice.fraction;
              } else if (sweepProgress > slice.startAngle) {
                visibleFraction = sweepProgress - slice.startAngle;
              }
              if (visibleFraction <= 0) return null;
              const visibleLen = circumference * visibleFraction;
              return (
                <circle
                  key={i}
                  cx={cx}
                  cy={cy}
                  r={r}
                  fill="none"
                  stroke={slice.color}
                  strokeWidth={strokeW}
                  strokeLinecap="butt"
                  strokeDasharray={`${visibleLen} ${circumference - visibleLen}`}
                  strokeDashoffset={-circumference * slice.startAngle}
                  transform={`rotate(-90 ${cx} ${cy})`}
                  style={{ transition: "none" }}
                />
              );
            })}
            {/* Center text */}
            {chartConfig?.showTotal !== false && (
              <text x={cx} y={cy + 8} textAnchor="middle" fontSize={32} fontWeight={700} fill={C.text}>
                {total}{unit}
              </text>
            )}
          </svg>

          {/* Legend */}
          <div style={{
            display: "flex", flexDirection: "column", gap: 12,
            backgroundColor: "rgba(0,0,0,0.5)", backdropFilter: "blur(8px)",
            borderRadius: 16, padding: "20px 24px",
            border: "1px solid rgba(255,255,255,0.08)",
          }}>
            {displayItems.map((item, i) => {
              const delay = 20 + i * 6;
              const labelFade = interpolate(frame, [delay, delay + 12], [0, 1], clamp);
              return (
                <div key={i} style={{ opacity: labelFade, display: "flex", alignItems: "center", gap: 12 }}>
                  <div style={{ width: 20, height: 20, borderRadius: 4, backgroundColor: PIE_COLORS[i % PIE_COLORS.length], flexShrink: 0 }} />
                  <TextWithBreaks text={item} style={{ fontSize: T.labelText, color: C.text, fontWeight: 500 }} />
                  <span style={{ fontSize: T.labelText, color: PIE_COLORS[i % PIE_COLORS.length], fontWeight: 700, marginLeft: 8 }}>
                    {displayValues[i]}{unit}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

      </div>
    </AbsoluteFill>
  );
};

/* ================================================================
   LineChartDisplay — SVG 라인 차트
   ================================================================ */

const LineChartDisplay: React.FC<{
  items: string[];
  values: number[];
  unit: string;
  headline: string;
  moodCfg: MoodConfig;
  source: string;
  mood: string;
  hasImageBg?: boolean;
  chartConfig?: { showGrid?: boolean; showDots?: boolean; showArea?: boolean };
}> = ({ items, values, unit, headline, moodCfg, source, mood, hasImageBg, chartConfig }) => {
  const C = useC();
  const T = usePresetTypo();
  const L = usePresetLayout();
  const frame = useCurrentFrame();
  const lines = headline.split("\n").filter((l: string) => l.trim());
  const headlineFade = useFade(5, 15, 0.8);
  const sourceFade = useFade(items.length * 4 + 60, 15, 0.8);

  const showGrid = chartConfig?.showGrid !== false;
  const showDots = chartConfig?.showDots !== false;
  const showArea = chartConfig?.showArea !== false;

  // Chart dimensions
  const W = 1100, H = 600;
  const padL = 80, padR = 80, padT = 50, padB = 60;
  const chartW = W - padL - padR;
  const chartH = H - padT - padB;

  const maxVal = Math.max(...values, 1);
  const minVal = Math.min(...values, 0);
  const range = maxVal - minVal || 1;

  // Points
  const points = values.map((v, i) => ({
    x: padL + (items.length > 1 ? (i / (items.length - 1)) * chartW : chartW / 2),
    y: padT + chartH - ((v - minVal) / range) * chartH,
  }));

  const pathD = points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ");
  const areaD = `${pathD} L${points[points.length - 1].x},${padT + chartH} L${points[0].x},${padT + chartH} Z`;

  // Drawing animation via clipPath
  const drawProgress = interpolate(frame, [15, 70], [0, 1], { ...clamp, easing: ease8020 });
  const clipX = padL + drawProgress * chartW;

  // Grid lines (4 horizontal)
  const gridLines = showGrid ? [0, 0.25, 0.5, 0.75, 1].map((frac) => ({
    y: padT + chartH * (1 - frac),
    label: Math.round(minVal + range * frac),
  })) : [];

  return (
    <AbsoluteFill>
      <MoodBackground mood={mood} transparent={hasImageBg} />
      <div
        style={{
          position: "relative",
          zIndex: 2,
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          padding: `${L.scenePadding[0]}px 40px`,
          paddingBottom: `${L.scenePadding[0] + 100}px`,
          gap: L.gap,
          overflow: "visible",
        }}
      >
        {/* Headline */}
        <div style={{ opacity: headlineFade, textAlign: "center", maxWidth: "90%" }}>
          {lines.map((line, i) => (
            <div key={i} style={{ fontSize: T.chartTitle, fontWeight: 700, color: C.text, lineHeight: 1.3 }}>
              <AccentText text={line} baseColor={C.text} />
            </div>
          ))}
        </div>

        {/* SVG Chart */}
        <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ overflow: "visible", flexShrink: 0 }}>
          <defs>
            <clipPath id="line-clip">
              <rect x={0} y={0} width={clipX + 10} height={H + 20} />
            </clipPath>
            <linearGradient id="area-grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={moodCfg.accent} stopOpacity={0.4} />
              <stop offset="100%" stopColor={moodCfg.accent} stopOpacity={0.02} />
            </linearGradient>
          </defs>

          {/* Grid */}
          {gridLines.map((gl, i) => (
            <g key={i}>
              <line x1={padL} y1={gl.y} x2={W - padR} y2={gl.y} stroke="rgba(255,255,255,0.1)" strokeWidth={1} />
              <text x={padL - 10} y={gl.y + 5} textAnchor="end" fontSize={22} fill="rgba(255,255,255,0.5)">
                {gl.label}{unit}
              </text>
            </g>
          ))}

          {/* X-axis labels */}
          {items.map((label, i) => {
            const x = padL + (items.length > 1 ? (i / (items.length - 1)) * chartW : chartW / 2);
            const labelFade = interpolate(frame, [15 + i * 3, 20 + i * 3], [0, 1], clamp);
            return (
              <text key={i} x={x} y={H - 10} textAnchor="middle" fontSize={22} fill={`rgba(255,255,255,${labelFade * 0.7})`}>
                {label}
              </text>
            );
          })}

          <g clipPath="url(#line-clip)">
            {/* Area */}
            {showArea && points.length >= 2 && (
              <path d={areaD} fill="url(#area-grad)" />
            )}

            {/* Line */}
            <path d={pathD} fill="none" stroke={moodCfg.accent} strokeWidth={4} strokeLinecap="round" strokeLinejoin="round" />

            {/* Dots */}
            {showDots && points.map((p, i) => {
              const dotDelay = 15 + (i / (points.length - 1 || 1)) * 55;
              const dotScale = interpolate(frame, [dotDelay, dotDelay + 8], [0, 1], clamp);
              return (
                <g key={i}>
                  <circle cx={p.x} cy={p.y} r={7 * dotScale} fill={moodCfg.accent} stroke={C.bg} strokeWidth={2} />
                  {dotScale > 0.5 && (
                    <text
                      x={p.x}
                      y={p.y - 16}
                      textAnchor={i === points.length - 1 ? "end" : i === 0 ? "start" : "middle"}
                      fontSize={20}
                      fontWeight={700}
                      fill={C.text}
                    >
                      {fmtNum(values[i])}{unit}
                    </text>
                  )}
                </g>
              );
            })}
          </g>
        </svg>

      </div>
    </AbsoluteFill>
  );
};

/* ================================================================
   BadgeRow — 배지 (국기/아이콘/로고) 행
   ================================================================ */

const BadgeRow: React.FC<{
  badges: Array<{
    type: "flag" | "icon" | "logo";
    code?: string;
    name?: string;
    label?: string;
  }>;
  delay: number;
}> = ({ badges, delay }) => {
  const C = useC();
  const frame = useCurrentFrame();
  const overshoot = Easing.out(Easing.back(1.7));

  return (
    <div
      style={{
        display: "flex",
        gap: 24,
        justifyContent: "center",
        alignItems: "center",
        marginBottom: 24,
      }}
    >
      {badges.map((badge, i) => {
        const d = delay + i * 6;
        const f = frame - d;
        const opacity = interpolate(f, [0, 8], [0, 1], {
          ...clamp,
          easing: ease,
        });
        const scale = interpolate(f, [0, 20], [0.5, 1], {
          ...clamp,
          easing: overshoot,
        });
        const IconComp =
          badge.type === "icon" && badge.name
            ? resolveIcon(badge.name)
            : null;

        return (
          <div
            key={i}
            style={{
              opacity,
              transform: `scale(${scale})`,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 8,
            }}
          >
            {badge.type === "flag" && badge.code && (
              <FlagCard countryCode={badge.code} label={badge.label} width={100} />
            )}
            {badge.type === "icon" && IconComp && (
              <IconBadge icon={IconComp} size={56} />
            )}
            {badge.type === "logo" && badge.name && (
              <LogoBadge logo={badge.name} size={56} />
            )}
            {badge.label && badge.type !== "flag" && (
              <span
                style={{
                  fontSize: 24,
                  color: C.textMuted,
                  fontWeight: 500,
                }}
              >
                {badge.label}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
};

/* ================================================================
   StatusDotList — 상태 표시 도트 리스트
   ================================================================ */

const StatusDotList: React.FC<{
  dots: Array<{
    label: string;
    status: "positive" | "negative" | "neutral" | "warning";
  }>;
  delay: number;
}> = ({ dots, delay }) => {
  const frame = useCurrentFrame();

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 10,
        marginTop: 24,
        maxWidth: 600,
      }}
    >
      {dots.map((dot, i) => {
        const d = delay + i * 8;
        const opacity = interpolate(frame, [d, d + 15], [0, 1], clamp);
        const slideX = interpolate(frame, [d, d + 15], [-15, 0], {
          ...clamp,
          easing: ease,
        });

        return (
          <div
            key={i}
            style={{
              opacity,
              transform: `translateX(${slideX}px)`,
            }}
          >
            <StatusDot status={dot.status} label={dot.label} />
          </div>
        );
      })}
    </div>
  );
};

/* ================================================================
   TagRow — 태그/칩 행
   ================================================================ */

const TagRow: React.FC<{
  tags: Array<{ text: string; active?: boolean }>;
  delay: number;
}> = ({ tags, delay }) => {
  const frame = useCurrentFrame();

  return (
    <div
      style={{
        display: "flex",
        gap: 10,
        flexWrap: "wrap",
        justifyContent: "center",
        marginTop: 16,
        marginBottom: 8,
      }}
    >
      {tags.map((tag, i) => {
        const d = delay + i * 5;
        const opacity = interpolate(frame, [d, d + 12], [0, 1], clamp);
        const rise = interpolate(frame, [d, d + 12], [10, 0], {
          ...clamp,
          easing: ease,
        });

        return (
          <div
            key={i}
            style={{ opacity, transform: `translateY(${rise}px)` }}
          >
            <Tag text={tag.text} active={tag.active} size="md" />
          </div>
        );
      })}
    </div>
  );
};

/* ================================================================
   CreativeScene — 메인 컴포넌트
   ================================================================ */

interface CreativeSceneProps {
  data: any;
  subtitles?: SubtitleEntry[];
  fps?: number;
  hasImageBackground?: boolean;
  imageAssetPlacement?: "fullscreen" | "background" | "center" | "left" | "right" | "inline";
}

export const CreativeScene: React.FC<CreativeSceneProps> = (props) => {
  const safeData = props.data || {};
  const source = safeData.source || "";
  const creative = safeData.creative || {};
  const srcX = creative.sourceOffsetX || 0;
  const srcY = creative.sourceOffsetY || 0;
  return (
    <>
      <CreativeSceneInner {...props} />
      {source && (
        <div style={{
          position: "absolute",
          bottom: 130,
          right: 40,
          fontSize: 22,
          color: "rgba(255,255,255,0.4)",
          pointerEvents: "none",
          zIndex: 5,
          transform: (srcX || srcY) ? `translate(${srcX}px, ${srcY}px)` : undefined,
        }}>
          출처: {source}
        </div>
      )}
    </>
  );
};

const CreativeSceneInner: React.FC<CreativeSceneProps> = ({
  data,
  subtitles,
  fps = 30,
  hasImageBackground,
  imageAssetPlacement,
}) => {
  const C = useC(); // 테마 컨텍스트에서 색상 팔레트 읽기 (dark/white)
  const preset = useDesignPreset();
  const T = preset.typography;
  const L = preset.layout;
  const frame = useCurrentFrame();
  // data가 없으면 빈 객체로 fallback
  if (!data) data = {};
  const creative = data.creative || {};
  // 플랫 스키마: 최상위 필드 우선, creative 중첩 fallback
  const headline: string = data.headline || creative.headline || data.title || "";
  const mood: string = data.mood || creative.mood || "informative";
  const source: string = data.source || "";
  const items: string[] = data.items || [];
  const values: number[] = data.values || [];
  const unit: string = data.unit || "";
  const concept: string = creative.concept || "";
  const itemIcons: string[] = data.itemIcons || data.icons || [];
  const itemFlags: string[] = data.itemFlags || data.flags || [];
  const itemLogos: string[] = items.map((item, i) => data.logoMap?.[item] || data.logoMap?.[String(i)] || item);
  const getItemLeadVisual = (i: number, options?: { flagLabel?: string; flagWidth?: number; iconSize?: number; logoSize?: number; iconFilled?: boolean }) =>
    renderItemLeadVisual({
      flag: itemFlags[i],
      icon: itemIcons[i],
      logo: itemLogos[i],
      flagLabel: options?.flagLabel,
      flagWidth: options?.flagWidth,
      iconSize: options?.iconSize,
      logoSize: options?.logoSize,
      iconFilled: options?.iconFilled,
    });

  // motion preset 연동
  const motionPreset: string = data.motionPreset || "";
  const motionConfig: MotionConfig = resolveSceneMotion(motionPreset, mood, items.length);

  // motionConfig → 기존 reveal/emphasis 시스템 매핑
  const _entranceToReveal: Record<string, string> = {
    fade: "fade_in", fadeRise: "fade_in", fadeSlide: "fade_in",
    scale: "zoom_in", spring: "fade_in", overshoot: "cascade",
    bounce: "stagger", typewriter: "typewriter",
  };
  const reveal: string = motionPreset
    ? (_entranceToReveal[motionConfig.entrance.type] || "fade_in")
    : (creative.reveal || "fade_in");

  const _emphasisToEmphasis: Record<string, string> = {
    countUp: "number", shake: "shake", glitch: "glitch", pulse: "pulse",
    glow: "number", bounce: "bounce", lineExpand: "lineExpand", none: "none",
  };
  const normalizedLayoutOptions = normalizeLayoutOptions(data, creative);
  const layout = normalizedLayoutOptions.layout;
  const chartStyle = normalizedLayoutOptions.chartStyle || "pie";
  const orientation = normalizedLayoutOptions.orientation || "vertical";
  const withPortrait = normalizedLayoutOptions.withPortrait ?? false;
  const isQuotePortrait = layout === "quote" && withPortrait;
  const isPieLayout = layout === "pie" && (chartStyle === "pie" || chartStyle === "donut");
  const isHorizontalBarLayout = layout === "bar" && orientation === "horizontal";
  const isVerticalBarLayout = layout === "bar" && orientation !== "horizontal";
  const portraitPlacement = normalizedLayoutOptions.portraitPlacement || "right";
  let emphasis: string = motionPreset
    ? (_emphasisToEmphasis[motionConfig.emphasis?.type || "none"] || creative.emphasis || "none")
    : (creative.emphasis || "none");
  // counter/metric_spotlight → 자동으로 number emphasis (countUp 활성화)
  if ((layout === "counter" || layout === "metric_spotlight") && emphasis === "none") {
    emphasis = "number";
  }

  const headlineTransform = (creative.headlineOffsetX || creative.headlineOffsetY)
    ? `translate(${creative.headlineOffsetX || 0}px, ${creative.headlineOffsetY || 0}px)` : undefined;
  const itemsTransform = (creative.itemsOffsetX || creative.itemsOffsetY)
    ? `translate(${creative.itemsOffsetX || 0}px, ${creative.itemsOffsetY || 0}px)` : undefined;
  const badges: any[] = data.badges || [];
  const statusDots: any[] = data.statusDots || [];
  const tags: any[] = data.tags || [];

  const _rawMoodCfg = getMoodConfigFromPreset(mood, preset);
  // motionConfig.speedFactor를 mood speed에 곱함
  const moodCfg = motionPreset
    ? { ..._rawMoodCfg, speed: _rawMoodCfg.speed * motionConfig.speedFactor }
    : _rawMoodCfg;
  const lines = headline.split("\n").filter((l: string) => l.trim());
  const layoutHierarchy = getLayoutHierarchy(layout);
  const headlineIsPrimary = layoutHierarchy === "headline";
  const supportHeadlineInline = usesInlineSupportHeadline(layout);
  const showHeadlineField: boolean = creative.showHeadline !== false; // 기본 true, false로 끌 수 있음
  const showSupportHeadline = usesSupportHeadline(layout);
  const showCommonSupportHeadline = showSupportHeadline && !supportHeadlineInline;

  // === 타이밍 ===
  const headlineLineCount = lines.length;
  const itemCount =
    layout === "items_grid" || layout === "items_list" ? items.length : 0;

  // headline/item 애니메이션 지속 시간 — motionConfig에서 동적 결정
  const LINE_ANIM_DUR = motionPreset
    ? Math.round(motionConfig.entrance.duration * motionConfig.speedFactor)
    : 18;
  const ITEM_ANIM_DUR = motionPreset
    ? Math.round((motionConfig.entrance.duration * 0.8) * motionConfig.speedFactor)
    : 15;

  // Raw TTS 시작 프레임 (count-up 타이밍 기준용)
  const headlineSubtitleStarts =
    subtitles && subtitles.length > 0
      ? computeSubtitleDelays(subtitles, headlineLineCount, fps)
      : computeFixedDelays(reveal, headlineLineCount, moodCfg.speed);

  // headline 딜레이: 애니메이션이 TTS 시작 시점에 완료되도록 앞당김
  const headlineDelays = headlineSubtitleStarts.map((d) =>
    Math.max(d - LINE_ANIM_DUR, 0),
  );

  // items 딜레이: 자막 텍스트 매칭 사용 (각 아이템이 나레이션되는 시점에 등장)
  let itemDelays: number[];
  if (itemCount === 0) {
    itemDelays = [];
  } else if (subtitles && subtitles.length > 0) {
    // Raw TTS 시작 프레임에서 아이템 애니메이션 시간만큼 앞당김
    const rawItemDelays = computeItemSubtitleDelays(subtitles, items, fps);
    itemDelays = rawItemDelays.map((d) => Math.max(d - ITEM_ANIM_DUR, 0));
  } else {
    const headlineDone = Math.max(...headlineDelays, 0) + 15;
    if (motionPreset && motionConfig.stagger) {
      // motionConfig stagger 기반 딜레이
      const gap = motionConfig.stagger.gap;
      itemDelays = Array.from({ length: itemCount }, (_, i) => headlineDone + i * gap);
    } else {
      itemDelays = computeFixedDelays(reveal, itemCount, moodCfg.speed).map(
        (d) => d + headlineDone,
      );
    }
  }

  const allDelays = [...headlineDelays, ...itemDelays];

  // === Multi-counter: {{}}에서 최대 4개 숫자 추출 ===
  const accentMatches = [...headline.matchAll(/\{\{([^}]+)\}\}/g)];
  const numTargets = accentMatches.map((m) => extractNumber(m[1]));
  const isCountEmphasis = emphasis === "number" || emphasis === "count";

  // 각 accent가 어느 headline 라인에 속하는지 매핑
  const COUNT_UP_DURATION = 35;
  const accentLineDelays: number[] = (() => {
    if (!isCountEmphasis) return [9999, 9999, 9999, 9999];
    let accentI = 0;
    const delays: number[] = [];
    for (let li = 0; li < lines.length; li++) {
      const lineAccents = [...lines[li].matchAll(/\{\{[^}]+\}\}/g)];
      for (let _j = 0; _j < lineAccents.length; _j++) {
        // 카운트업은 TTS 시작 시점에 완료되도록: raw TTS start - duration
        const ttsStart = headlineSubtitleStarts[li] || 0;
        delays.push(Math.max(ttsStart - COUNT_UP_DURATION, 0));
        accentI++;
      }
    }
    // 4개 채우기
    while (delays.length < 4) delays.push(9999);
    return delays;
  })();

  // 항상 4개 counter hook 호출 (React rules)
  // >= 100인 숫자만 카운트업 (점점 올라가는 의미가 있는 큰 수치만)
  const counted0 = useCountUp(
    isCountEmphasis && (numTargets[0] || 0) >= 100 ? accentLineDelays[0] : 9999,
    COUNT_UP_DURATION,
    numTargets[0] || 1,
  );
  const counted1 = useCountUp(
    isCountEmphasis && (numTargets[1] || 0) >= 100 ? accentLineDelays[1] : 9999,
    COUNT_UP_DURATION,
    numTargets[1] || 1,
  );
  const counted2 = useCountUp(
    isCountEmphasis && (numTargets[2] || 0) >= 100 ? accentLineDelays[2] : 9999,
    COUNT_UP_DURATION,
    numTargets[2] || 1,
  );
  const counted3 = useCountUp(
    isCountEmphasis && (numTargets[3] || 0) >= 100 ? accentLineDelays[3] : 9999,
    COUNT_UP_DURATION,
    numTargets[3] || 1,
  );
  const countedValues = [counted0, counted1, counted2, counted3];

  const earliestCountDelay = Math.min(...accentLineDelays.filter((d) => d < 9999), 9999);
  const glowOpacity = interpolate(
    frame,
    [earliestCountDelay, earliestCountDelay + 40],
    [0, moodCfg.glow],
    clamp,
  );

  const sourceFade = useFade(Math.max(...allDelays, 0) + 50, 15, 0.8);

  // hook은 조건 밖에서 항상 호출 (map 안에서 useFade 호출 금지 → 미리 계산)
  const supportLineOpacities = lines.map((_, i) => useFade(headlineDelays[i] || 0, LINE_ANIM_DUR, 1)); // eslint-disable-line react-hooks/rules-of-hooks

  const renderSupportHeadline = (options?: { marginBottom?: number; maxWidth?: string }) => {
    if (!showSupportHeadline || !headline || lines.length === 0) return null;
    const supportFontSize = T.chartTitle;
    const supportWeight = layoutHierarchy === "value" ? 600 : 700;
    const supportColor = layoutHierarchy === "value" ? C.textMuted : C.textDim;

    return (
      <div
        style={{
          marginBottom: options?.marginBottom ?? L.sectionMarginTop,
          textAlign: "center",
          maxWidth: options?.maxWidth ?? L.headlineMaxWidth,
          transform: headlineTransform,
          visibility: showHeadlineField ? "visible" : "hidden",
          height: showHeadlineField ? undefined : 0,
          overflow: "hidden",
        }}
      >
        {lines.map((line, i) => (
          <div
            key={i}
            style={{
              opacity: supportLineOpacities[i] ?? 0,
              fontSize: supportFontSize,
              fontWeight: supportWeight,
              color: supportColor,
              lineHeight: 1.35,
              letterSpacing: 0.5,
              marginBottom: i < lines.length - 1 ? 6 : 0,
            }}
          >
            <TextWithBreaks text={line.replace(/\{\{|\}\}/g, "")} />
          </div>
        ))}
      </div>
    );
  };

  const headlineClean = headline.replace(/\{\{|\}\}/g, "");
  const quoteTitle = data.title || creative.title || "";
  const headlineHasBreak = headline.includes("\n") || headline.includes("\\n");
  const rawQuoteText = items[0] || data.quote || quoteTitle || "";
  const isNameOnly = rawQuoteText.length > 0 && rawQuoteText.length <= 10 && !rawQuoteText.includes(" ");
  const quoteText = (!rawQuoteText || isNameOnly || headlineHasBreak) ? headlineClean : rawQuoteText;
  // speaker 필드 우선, 없으면 source 폴백 (출처와 화자 구분)
  const speaker: string = data.speaker || creative.speaker || "";
  const quoteSource = speaker || (isNameOnly && !source) ? (speaker || rawQuoteText) : source;

  // === Layout routing ===

  // Quote
  if (layout === "quote" && !isQuotePortrait) {
    return (
      <QuoteDisplay
        items={[quoteText]}
        source={quoteSource}
        moodCfg={moodCfg}
        reveal={reveal}
        speed={moodCfg.speed}
        mood={mood}
        hasImageBg={hasImageBackground}
        portrait={data.images?.[0]}
      />
    );
  }

  // Split
  if (layout === "split" && lines.length >= 2) {
    return (
      <SplitLayout
        lines={lines}
        delays={headlineDelays}
        emphasis={emphasis}
        moodCfg={moodCfg}
        countedValues={countedValues}
        glowOpacity={glowOpacity}
        source={source}
        mood={mood}
        hasImageBg={hasImageBackground}
        images={data.images}
        descriptions={data.descriptions}
      />
    );
  }

  // Pie / Donut chart
  if (isPieLayout) {
    return (
      <PieChartDisplay
        items={items}
        values={values}
        unit={unit}
        headline={headline}
        moodCfg={moodCfg}
        source={source}
        mood={mood}
        hasImageBg={hasImageBackground}
        chartConfig={{
          ...creative.chartConfig,
          chartStyle,
          showTotal: chartStyle === "donut" ? true : creative.chartConfig?.showTotal,
        }}
      />
    );
  }

  // Line chart
  if (layout === "line") {
    return (
      <LineChartDisplay
        items={items}
        values={values}
        unit={unit}
        headline={headline}
        moodCfg={moodCfg}
        source={source}
        mood={mood}
        hasImageBg={hasImageBackground}
        chartConfig={creative.chartConfig}
      />
    );
  }

  // Logo grid
  if (layout === "logo_grid") {
    return (
      <LogoGridLayout
        items={items}
        values={values}
        unit={unit}
        headline={headline}
        moodCfg={moodCfg}
        source={source}
        mood={mood}
        emphasis={emphasis}
        countedValues={countedValues}
        glowOpacity={glowOpacity}
        hasImageBg={hasImageBackground}
        logoMap={creative.logoMap}
      />
    );
  }

  // Horizontal Bar chart
  if (isHorizontalBarLayout) {
    const maxVal = Math.max(...values.map(Math.abs), 1);
    return (
      <AbsoluteFill style={{ backgroundColor: hasImageBackground ? "transparent" : C.bg, fontFamily: "inherit" }}>
        <MoodBackground mood={mood} transparent={hasImageBackground} />
        <div style={{
          width: "78%", margin: "0 auto", height: "100%",
          display: "flex", flexDirection: "column", justifyContent: "center", gap: 16, padding: "60px 0"
        }}>
          {headline && lines.length > 0 && (
            <div style={{ marginBottom: 20, textAlign: "center" }}>
              {lines.map((line, i) => (
                <div key={i} style={{ fontSize: T.title?.size || 42, fontWeight: 800, color: C.text }}>
                  <TextWithBreaks text={line} accentColor={moodCfg.accent} />
                </div>
              ))}
            </div>
          )}
          {items.map((item, i) => {
            const val = values[i] || 0;
            const pct = (Math.abs(val) / maxVal) * 100;
            const delay = staggerDelay(i, items.length, moodCfg.speed);
            const barW = interpolate(frame - delay, [0, 20], [0, pct], {
              extrapolateLeft: "clamp", extrapolateRight: "clamp",
              easing: Easing.out(Easing.cubic),
            });
            const fade = interpolate(frame - delay, [0, 10], [0, 1], {
              extrapolateLeft: "clamp", extrapolateRight: "clamp",
            });
            return (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, opacity: fade }}>
                <div style={{ width: 120, textAlign: "right", fontSize: 14, fontWeight: 600, color: C.text, flexShrink: 0 }}>
                  {item}
                </div>
                <div style={{ flex: 1, height: 28, background: "rgba(255,255,255,0.06)", borderRadius: 4, overflow: "hidden" }}>
                  <div style={{
                    width: `${barW}%`, height: "100%",
                    background: moodCfg.accent,
                    borderRadius: 4,
                    transition: "width 0.3s",
                  }} />
                </div>
                <div style={{ width: 60, fontSize: 14, fontWeight: 700, color: moodCfg.accent }}>
                  {emphasis === "number" ? (
                    <span>{Math.round(interpolate(frame - delay, [0, 20], [0, val], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }))}{unit}</span>
                  ) : (
                    <span>{val}{unit}</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    );
  }

  // Bar chart
  if (isVerticalBarLayout) {
    return (
      <BarDisplay
        items={items}
        values={values}
        unit={unit}
        headline={headline}
        moodCfg={moodCfg}
        source={source}
        mood={mood}
        emphasis={emphasis}
        countedValues={countedValues}
        glowOpacity={glowOpacity}
        hasImageBg={hasImageBackground}
        subtitles={subtitles}
        fps={fps}
      />
    );
  }

  /* ── Cinematic Overlay Components ── */

  const OVERLAY_POSITIONS: Record<string, React.CSSProperties> = {
    top_left:     { top: 80, left: 80 },
    top_right:    { top: 80, right: 80 },
    bottom_left:  { bottom: 120, left: 80 },
    bottom_right: { bottom: 120, right: 80 },
    center:       { top: "50%", left: "50%", transform: "translate(-50%, -50%)" },
  };

  const SpeechBubble: React.FC<{ text: string; position: string; delay: number }> = ({
    text, position, delay,
  }) => {
    const frame = useCurrentFrame();
    const scale = interpolate(frame - delay, [0, 8], [0, 1], {
      extrapolateLeft: "clamp", extrapolateRight: "clamp",
      easing: Easing.out(Easing.back(1.5)),
    });
    const pos = OVERLAY_POSITIONS[position] || OVERLAY_POSITIONS.center;
    const tailSide = position.includes("right") ? "left" : "right";
    const tailStyle: React.CSSProperties = {
      position: "absolute",
      bottom: -14,
      [tailSide === "left" ? "left" : "right"]: 24,
      width: 0, height: 0,
      borderLeft: "12px solid transparent",
      borderRight: "12px solid transparent",
      borderTop: "16px solid #fff",
      filter: "drop-shadow(0 2px 0 #222)",
    };
    return (
      <div style={{
        position: "absolute", ...pos, zIndex: 10,
        transform: `${pos.transform || ""} scale(${scale})`,
        opacity: scale,
      }}>
        <div style={{
          position: "relative",
          background: "#fff",
          border: "4px solid #222",
          borderRadius: 20,
          padding: "16px 28px",
          fontFamily: "inherit",
          fontSize: 42,
          fontWeight: 800,
          color: "#222",
          boxShadow: "4px 4px 0 #222",
        }}>
          {text}
          <div style={tailStyle} />
        </div>
      </div>
    );
  };

  const EmotionOverlay: React.FC<{ text: string; position: string; delay: number }> = ({
    text, position, delay,
  }) => {
    const frame = useCurrentFrame();
    const scale = interpolate(frame - delay, [0, 6], [0, 1], {
      extrapolateLeft: "clamp", extrapolateRight: "clamp",
      easing: Easing.out(Easing.back(2)),
    });
    const shake = Math.sin((frame - delay) * 0.8) * 3;
    const pos = OVERLAY_POSITIONS[position] || OVERLAY_POSITIONS.center;
    return (
      <div style={{
        position: "absolute", ...pos, zIndex: 10,
        transform: `${pos.transform || ""} scale(${scale}) rotate(${-8 + shake}deg)`,
        opacity: scale,
        fontSize: 72,
        fontWeight: 900,
        color: "#FFE033",
        textShadow: "3px 3px 0 #222, -1px -1px 0 #222",
        fontFamily: "inherit",
      }}>
        {text}
      </div>
    );
  };

  const CaptionOverlay: React.FC<{ text: string; position: string; delay: number }> = ({
    text, position, delay,
  }) => {
    const frame = useCurrentFrame();
    const opacity = interpolate(frame - delay, [0, 10], [0, 1], {
      extrapolateLeft: "clamp", extrapolateRight: "clamp",
    });
    const pos = OVERLAY_POSITIONS[position] || OVERLAY_POSITIONS.bottom_left;
    return (
      <div style={{
        position: "absolute", ...pos, zIndex: 10, opacity,
        background: "rgba(0,0,0,0.75)",
        borderRadius: 8,
        padding: "10px 20px",
        fontSize: 28,
        fontWeight: 600,
        color: "#fff",
        fontFamily: "inherit",
      }}>
        {text}
      </div>
    );
  };

  const CinematicOverlayRenderer: React.FC<{
    overlay: { type: string; text: string; position: string };
    delay?: number;
  }> = ({ overlay, delay = 9 }) => {
    if (!overlay?.text) return null;
    switch (overlay.type) {
      case "speech_bubble": return <SpeechBubble text={overlay.text} position={overlay.position} delay={delay} />;
      case "emotion":       return <EmotionOverlay text={overlay.text} position={overlay.position} delay={delay} />;
      case "caption":       return <CaptionOverlay text={overlay.text} position={overlay.position} delay={delay} />;
      default: return null;
    }
  };

  // === cinematic: 이미지 풀스크린 + Ken Burns + optional 오버레이 ===
  // 이미지는 부모(SimpleVideo)의 SceneImage가 렌더링.
  // 오버레이가 있으면 말풍선/감탄부호/캡션을 이미지 위에 표시.
  if (layout === "cinematic") {
    const cinematicOverlay = data?.cinematicOverlay;
    return (
      <AbsoluteFill>
        {!hasImageBackground && <MoodBackground mood={mood} transparent={false} />}
        {cinematicOverlay && (
          <CinematicOverlayRenderer overlay={cinematicOverlay} delay={9} />
        )}
      </AbsoluteFill>
    );
  }

  // === 공통 레이아웃: headline + optional items ===
  const isFlash = reveal === "stagger_then_flash";
  const flashAt = isFlash ? Math.max(...allDelays) + 20 : 9999;

  // === width 조정 (이전 SimpleScene 역할 통합) ===
  const hasAssetSide = imageAssetPlacement === "left" || imageAssetPlacement === "right";
  const useFullWidth = hasImageBackground || hasAssetSide || imageAssetPlacement === "fullscreen" || imageAssetPlacement === "center";
  const contentWidth = useFullWidth ? "100%" : "90%";

  const isSidePlacement = imageAssetPlacement === "left" || imageAssetPlacement === "right";

  return (
    <AbsoluteFill style={{ backgroundColor: (hasImageBackground || isSidePlacement) ? "transparent" : C.bg, fontFamily: "inherit" }}>
      <div style={{ width: contentWidth, height: "100%", margin: "0 auto", position: "relative" }}>
      {!isSidePlacement && <MoodBackground mood={mood} transparent={hasImageBackground} />}

      {/* Spotlight overlay */}
      {reveal === "spotlight" && <SpotlightOverlay speed={moodCfg.speed} />}

      {/* Flash overlay */}
      {isFlash && (
        <FlashOverlay flashAt={flashAt} accentRgb={moodCfg.accentRgb} />
      )}

      {/* Quote mark — portrait quote는 레이아웃 내부에 좌우 따옴표가 있으므로 제외 */}
      {emphasis === "quote" && !(isQuotePortrait) && (
        <div style={{ position: "relative", zIndex: 2 }}>
          <QuoteMark color={moodCfg.accent} delay={headlineDelays[0] || 0} />
        </div>
      )}

      {/* Main content */}
      <div
        style={isQuotePortrait ? {
          position: "relative",
          zIndex: 2,
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        } : {
          position: "relative",
          zIndex: 2,
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          padding: `${L.scenePadding[0]}px ${L.scenePadding[1]}px`,
          paddingBottom: `${L.scenePadding[0] + 100}px`,
        }}
      >
        {/* Badges — portrait quote/cinematic 는 스킵 */}
        {!(isQuotePortrait) && layout !== "cinematic" && badges.length > 0 && (
          <BadgeRow
            badges={badges}
            delay={Math.max((headlineDelays[0] || 0) - 10, 0)}
          />
        )}

        {/* Headline lines — portrait quote는 자체 인용문 레이아웃 사용, cinematic은 이미지만 */}
        {!(isQuotePortrait) && layout !== "cinematic" && headlineIsPrimary && (
        <div
          style={{
            textAlign: "center",
            maxWidth: "95%",
            transform: headlineTransform,
            visibility: showHeadlineField ? "visible" : "hidden",
            height: showHeadlineField ? undefined : 0,
            overflow: "hidden",
          }}
        >
          {lines.map((line: string, i: number) => {
            // 이 라인 이전 라인들의 accent 개수 합산 → accent 시작 인덱스
            const accentOffset = lines
              .slice(0, i)
              .reduce((sum, l) => sum + ([...l.matchAll(/\{\{[^}]+\}\}/g)].length), 0);
            return (
              <LineReveal
                key={i}
                line={line}
                delay={headlineDelays[i] || 0}
                reveal={reveal}
                emphasis={emphasis}
                moodCfg={moodCfg}
                countedValues={countedValues}
                glowOpacity={glowOpacity}
                lineIndex={i}
                totalLines={lines.length}
                accentOffset={accentOffset}
                motionConfig={motionPreset ? motionConfig : undefined}
                accentFontSizeOverride={items.length > 0 ? 80 : undefined}
              />
            );
          })}
        </div>
        )}

        {!(isQuotePortrait) && layout !== "cinematic" && showCommonSupportHeadline && renderSupportHeadline()}

        {/* Tags — portrait quote는 스킵 */}
        {!(isQuotePortrait) && tags.length > 0 && (
          <TagRow
            tags={tags}
            delay={Math.max(...headlineDelays, 0) + 15}
          />
        )}

        {/* Items 영역 (위치 조절 가능) */}
        <div style={{ width: "100%", transform: itemsTransform }}>

        {/* Person cards */}
        {layout === "person_card" && (
          <PersonCardRow
            items={items}
            delays={itemDelays}
            moodCfg={moodCfg}
            images={data.images}
            itemStatuses={data.itemStatuses}
          />
        )}

        {/* Items grid */}
        {layout === "items_grid" && (
          <ItemsGrid
            items={items}
            delays={itemDelays}
            headlineDelays={headlineDelays}
            moodCfg={moodCfg}
            reveal={reveal}
            itemIcons={itemIcons}
            itemFlags={itemFlags}
            motionConfig={motionPreset ? motionConfig : undefined}
          />
        )}

        {/* Items list */}
        {layout === "items_list" && (
          <ItemsList
            items={items}
            delays={itemDelays}
            headlineDelays={headlineDelays}
            moodCfg={moodCfg}
            emphasis={emphasis}
            concept={concept}
            images={data.images}
            itemIcons={itemIcons}
            itemFlags={itemFlags}
            itemStatuses={data.itemStatuses}
            motionConfig={motionPreset ? motionConfig : undefined}
          />
        )}

        {/* ── 확장 레이아웃 렌더러 ── */}

        {/* Flow — 프로세스/인과 흐름 */}
        {layout === "flow" && items.length >= 2 && (() => {
          const isHorizontal = items.length <= 4;
          return (
            <div style={{
              display: "flex",
              flexDirection: isHorizontal ? "row" : "column",
              alignItems: isHorizontal ? "center" : "flex-start",
              justifyContent: "center",
              gap: 0,
              width: isHorizontal ? "100%" : "auto",
              margin: "0 auto",
            }}>
              {items.map((item, i) => (
                <React.Fragment key={i}>
                  <div style={{ ...fadeRise(frame, staggerDelay(i, 10, 15), 15) }}>
                    <StepBadge step={i + 1} label={item} active={i === items.length - 1} />
                  </div>
                  {i < items.length - 1 && (
                    <div style={{ opacity: fadeVal(frame, staggerDelay(i, 10, 15) + 8, 10) }}>
                      <Connector direction={isHorizontal ? "right" : "down"} length={isHorizontal ? 48 : 32} color={moodCfg.accent} />
                    </div>
                  )}
                </React.Fragment>
              ))}
            </div>
          );
        })()}

        {/* Timeline — 가로 시간순 사건 나열 */}
        {layout === "timeline" && items.length >= 2 && (
          <div style={{ position: "relative", display: "flex", justifyContent: "space-between", alignItems: "flex-start", width: "100%", padding: `0 ${L.timelineDotSize}px` }}>
            {/* 연결선: 첫 도트 중앙 ~ 마지막 도트 중앙 */}
            <div style={{
              position: "absolute",
              top: L.timelineDotSize / 2 - L.timelineConnectorWidth / 2,
              left: L.timelineDotSize + L.timelineDotSize / 2,
              right: L.timelineDotSize + L.timelineDotSize / 2,
              height: L.timelineConnectorWidth,
              backgroundColor: C.cardBorder,
            }} />
            {items.map((item, i) => {
              const desc = (data.descriptions || [])[i] || "";
              const isLast = i === items.length - 1;
              const anim = fadeRise(frame, staggerDelay(i, 12, 15), 15);
              return (
                <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8, position: "relative", zIndex: 1, flex: 1, ...anim }}>
                  <div style={{
                    width: L.timelineDotSize, height: L.timelineDotSize,
                    borderRadius: L.timelineDotSize / 2,
                    backgroundColor: isLast ? moodCfg.accent : "transparent",
                    border: `${L.timelineConnectorWidth}px solid ${isLast ? moodCfg.accent : C.cardBorder}`,
                    flexShrink: 0,
                  }} />
                  <div style={{ fontSize: T.itemText, fontWeight: isLast ? 700 : 500, color: isLast ? moodCfg.accent : C.text, textAlign: "center" }}>
                    <TextWithBreaks text={item} />
                  </div>
                  {desc && <div style={{ fontSize: T.descText, color: C.textMuted, textAlign: "center" }}>{desc}</div>}
                </div>
              );
            })}
          </div>
        )}

        {/* Metric Spotlight — 단일 KPI 극적 강조 */}
        {layout === "metric_spotlight" && (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 18, ...scaleAnim(frame, 15) }}>
            {renderSupportHeadline({ marginBottom: 8, maxWidth: "70%" })}
            <MetricCard
              label={items[0] || data.title || ""}
              value={values.length > 0 ? `${fmtNum(values[0])}${data.unit || ""}` : ""}
              change={items[1]}
              trend={values.length > 1 ? (values[1] > 0 ? "up" : "down") : undefined}
              style={{ width: "100%", maxWidth: 720, transform: "scale(1.08)" }}
            />
            {values.length > 2 && (
              <div style={{ opacity: fadeVal(frame, 30, 15), transform: "scale(1.05)" }}>
                <Sparkline data={values} width={240} height={52} color={moodCfg.accent} />
              </div>
            )}
          </div>
        )}

        {/* Metric Wall — 여러 KPI 동시 */}
        {layout === "metric_wall" && items.length >= 2 && (() => {
          // 가장 긴 텍스트 기준으로 카드 최소 너비 계산
          const maxLabelLen = Math.max(...items.map(it => it.length));
          const maxValueLen = Math.max(...values.map((v, i) => `${fmtNum(v)}${data.unit || ""}`.length), 0);
          const cardMinW = Math.max(maxLabelLen * 22, maxValueLen * 80) + 48;
          const cols = Math.min(items.length, Math.max(1, Math.floor(1824 / (cardMinW + 50))));
          const gridW = cols * cardMinW + (cols - 1) * 50;
          return (
            <div style={{
              display: "grid",
              gridTemplateColumns: `repeat(${cols}, ${cardMinW}px)`,
              gap: 50, width: gridW, margin: "0 auto",
              justifyContent: "center",
            }}>
              {items.map((item, i) => (
                <div key={i} style={fadeRise(frame, staggerDelay(i, 8, 12), 15)}>
                  <MetricCard
                    label={item}
                    value={values[i] != null ? `${fmtNum(values[i])}${data.unit || ""}` : ""}
                    style={{ width: "100%" }}
                  />
                  {(() => {
                    const leadVisual = getItemLeadVisual(i, { flagLabel: item, logoSize: 32 });
                    return leadVisual ? (
                      <div style={{ marginTop: 12, display: "flex", justifyContent: "center" }}>
                        {leadVisual}
                      </div>
                    ) : null;
                  })()}
                </div>
              ))}
            </div>
          );
        })()}

        {/* Rank List — 순위 시각화 */}
        {layout === "rank_list" && items.length >= 2 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16, width: "100%" }}>
            {items.map((item, i) => {
              const maxVal = Math.max(...(values.length ? values : [1]));
              return (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 16, ...fadeRise(frame, staggerDelay(i, 10, 12), 15) }}>
                  <RankBadge rank={i + 1} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 24, fontWeight: 600, color: C.text, marginBottom: 6 }}><TextWithBreaks text={item} /></div>
                    {values[i] != null && (
                      <MiniBar value={values[i]} maxValue={maxVal} color={i === 0 ? moodCfg.accent : C.cardBorder} />
                    )}
                  </div>
                  {values[i] != null && (
                    <span style={{ fontSize: 24, fontWeight: 700, color: i === 0 ? moodCfg.accent : C.textMuted }}>
                      {fmtNum(values[i])}{data.unit || ""}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Before/After — 변화 전후 */}
        {layout === "before_after" && items.length >= 2 && (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 18, width: "100%" }}>
            {renderSupportHeadline({ marginBottom: 4, maxWidth: "72%" })}
            <div style={{ display: "flex", alignItems: "center", gap: 48, justifyContent: "center" }}>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 20, ...fadeSlide(frame, 15, 15, -30) }}>
                {getItemLeadVisual(0, { flagLabel: items[0], iconSize: 56, logoSize: 52 })}
                <ComparisonCell
                  label="BEFORE"
                  value={items[0]}
                  sublabel={values[0] != null ? `${fmtNum(values[0])}${data.unit || ""}` : undefined}
                  variant="before"
                  size="lg"
                  style={{ minWidth: 480 }}
                />
              </div>
              <div style={{ opacity: fadeVal(frame, 25, 10), transform: "scale(1.3)" }}>
                <Connector direction="right" length={64} color={moodCfg.accent} />
              </div>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 20, ...fadeSlide(frame, 35, 15, 30) }}>
                {getItemLeadVisual(1, { flagLabel: items[1], iconSize: 56, logoSize: 52 })}
                <ComparisonCell
                  label="AFTER"
                  value={items[1]}
                  sublabel={values[1] != null ? `${fmtNum(values[1])}${data.unit || ""}` : undefined}
                  variant="after"
                  size="lg"
                  style={{ minWidth: 480 }}
                />
              </div>
            </div>
          </div>
        )}

        {/* Comparison Table — 다차원 비교 */}
        {layout === "comparison_table" && items.length >= 2 && (() => {
          // metric_wall과 동일한 카드 크기 계산
          const maxLabelLen = Math.max(...items.map(it => it.length));
          const maxValueLen = Math.max(...values.map((v, i) => `${fmtNum(v)}${data.unit || ""}`.length), 0);
          const cardMinW = Math.max(maxLabelLen * 22, maxValueLen * 88) + 64;
          const cols = Math.min(items.length, Math.max(1, Math.floor(1824 / (cardMinW + 50))));
          const gridW = cols * cardMinW + (cols - 1) * 50;
          return (
            <div style={{ display: "flex", flexDirection: "column", gap: 18, width: "100%", alignItems: "center" }}>
              {renderSupportHeadline({ marginBottom: 0, maxWidth: "72%" })}
              <div style={{
                display: "grid",
                gridTemplateColumns: `repeat(${cols}, ${cardMinW}px)`,
                gap: 50, width: gridW, margin: "0 auto",
                justifyContent: "center",
              }}>
                {items.map((item, i) => (
                  <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12, ...fadeRise(frame, staggerDelay(i, 8, 12), 15) }}>
                    {getItemLeadVisual(i, { flagLabel: item, iconSize: 40, logoSize: 36 })}
                    <ComparisonCell
                      label={item}
                      value={values[i] != null ? `${fmtNum(values[i])}${data.unit || ""}` : ""}
                      style={{ width: "100%", transform: "scale(1.04)" }}
                    />
                  </div>
                ))}
              </div>
            </div>
          );
        })()}

        {/* Icon Stat — 단일 통계 + 아이콘 */}
        {layout === "icon_stat" && (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 20, ...scaleAnim(frame, 15) }}>
            {renderSupportHeadline({ marginBottom: 0, maxWidth: "70%" })}
            {data.itemIcons?.[0] && resolveIcon(data.itemIcons[0]) && (
              <IconBadge icon={resolveIcon(data.itemIcons[0])!} size={80} filled />
            )}
            {values[0] != null && (
              <div style={{ fontSize: T.metricValue + 12, fontWeight: 800, color: moodCfg.accent, lineHeight: 1.05 }}>
                {fmtNum(values[0])}{data.unit || ""}
              </div>
            )}
            {items[0] && (
              <div style={{ fontSize: T.labelText + 2, fontWeight: 600, color: C.text }}>{items[0]}</div>
            )}
          </div>
        )}

        {/* Stacked Progress — 점유율 비교 */}
        {layout === "stacked_progress" && items.length >= 2 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20, width: "100%", maxWidth: 600 }}>
            {items.map((item, i) => {
              const maxVal = Math.max(...(values.length ? values : [100]));
              return (
                <div key={i} style={fadeRise(frame, staggerDelay(i, 10, 12), 15)}>
                  <ProgressBar
                    progress={values[i] != null ? values[i] / maxVal : 0}
                    label={`${item} — ${values[i] != null ? fmtNum(values[i]) : 0}${data.unit || ""}`}
                    color={i === 0 ? moodCfg.accent : `${moodCfg.accent}88`}
                  />
                </div>
              );
            })}
          </div>
        )}

        {/* Card Carousel — 정보 카드 나열 */}
        {layout === "card_carousel" && items.length >= 2 && (
          <div style={{ display: "flex", gap: 20, justifyContent: "center", flexWrap: "wrap" }}>
            {items.map((item, i) => {
              const desc = (data.descriptions || [])[i] || "";
              return (
                <div key={i} style={fadeRise(frame, staggerDelay(i, 10, 15), 15)}>
                  <Card style={{ minWidth: 200, maxWidth: 280, textAlign: "center" }}>
                    {(() => {
                      const leadVisual = getItemLeadVisual(i, { flagLabel: item, iconSize: 48, logoSize: 44 });
                      return leadVisual ? (
                        <div style={{ marginBottom: 12, display: "flex", justifyContent: "center" }}>
                          {leadVisual}
                        </div>
                      ) : null;
                    })()}
                    <div style={{ fontSize: T.itemText, fontWeight: 700, color: C.text, marginBottom: desc ? 8 : 0 }}><TextWithBreaks text={item} /></div>
                    {desc && <div style={{ fontSize: T.descText, color: C.textMuted }}>{desc}</div>}
                  </Card>
                </div>
              );
            })}
          </div>
        )}

        {/* Hero with Context — 큰 헤드라인 + 부연 카드 */}
        {layout === "hero_with_context" && items.length >= 1 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 24, width: "100%", alignItems: "center" }}>
            {items.length > 0 && (
              <div style={{ display: "flex", gap: 16, justifyContent: "center", flexWrap: "wrap" }}>
                {items.map((item, i) => (
                  <div key={i} style={fadeRise(frame, staggerDelay(i, 8, 30), 15)}>
                    <Card style={{ padding: "12px 20px" }}>
                      <TextWithBreaks text={item} style={{ fontSize: T.labelText, color: C.textMuted }} />
                    </Card>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Quote Portrait — 인용문 텍스트만 (이미지는 SceneRenderer SideLayout에서 처리) */}
        {isQuotePortrait && (
          <div style={{ display: "flex", flexDirection: "column", justifyContent: "center",
                        alignItems: "center", textAlign: "center",
                        padding: portraitPlacement === "left" ? "40px 48px 40px 80px" : "40px 80px 40px 48px", width: "100%", height: "100%" }}>
            <div style={{ ...fadeRise(frame, 15, 20), display: "inline-grid", gridTemplateRows: "auto auto auto auto" }}>
              {/* 1행: 여는 따옴표 — 왼쪽 정렬 */}
              <span style={{
                justifySelf: "start",
                fontSize: T.quoteMarkSize * 1.2,
                fontWeight: 700,
                color: moodCfg.accent,
                opacity: 0.6,
                lineHeight: 1,
                marginBottom: "-0.8em",
                marginLeft: "-0.6em",
                fontFamily: GYEONGGI_FONT_FAMILY,
                userSelect: "none",
              }}>&ldquo;</span>
              {/* 2행: 텍스트 */}
              <div style={{
                fontSize: T.quoteText,
                fontWeight: 400,
                fontFamily: GYEONGGI_FONT_FAMILY,
                color: C.text,
                lineHeight: 1.65,
                whiteSpace: "pre-line",
                wordBreak: "keep-all",
                textAlign: "center",
              }}>
                {quoteText}
              </div>
              {/* 3행: 닫는 따옴표 — 오른쪽 정렬 */}
              <span style={{
                justifySelf: "end",
                fontSize: T.quoteMarkSize * 1.2,
                fontWeight: 700,
                color: moodCfg.accent,
                opacity: 0.6,
                lineHeight: 1,
                marginRight: "-0.6em",
                fontFamily: GYEONGGI_FONT_FAMILY,
                userSelect: "none",
              }}>&rdquo;</span>
              {/* 4행: 스피커/출처 — 오른쪽 정렬 */}
              {quoteSource && (
                <div style={{
                  justifySelf: "center",
                  fontSize: T.sourceText,
                  color: C.textMuted,
                  marginTop: "-1.6em",
                  fontFamily: GYEONGGI_FONT_FAMILY,
                }}>— {quoteSource}</div>
              )}
            </div>
          </div>
        )}

        {/* Annotated Chart — chartConfig.type에 따라 line/pie/bar 렌더링 */}
        {layout === "annotated_chart" && items.length >= 2 && (() => {
          const annotatedChartType = creative.chartConfig?.type || data.chartConfig?.type || "bar";
          if (annotatedChartType === "line") {
            return (
              <LineChartDisplay
                items={items}
                values={values}
                unit={unit}
                headline=""
                moodCfg={moodCfg}
                source=""
                mood={mood}
                hasImageBg={hasImageBackground}
                chartConfig={creative.chartConfig}
              />
            );
          }
          if (annotatedChartType === "pie") {
            return (
              <PieChartDisplay
                items={items}
                values={values}
                unit={unit}
                headline=""
                moodCfg={moodCfg}
                source=""
                mood={mood}
                hasImageBg={hasImageBackground}
                chartConfig={creative.chartConfig}
              />
            );
          }
          // 기본: bar (MiniBar + 주석)
          return (
            <div style={{ display: "flex", flexDirection: "column", gap: 16, width: "100%" }}>
              {/* 간이 바 렌더링 */}
              <div style={{ display: "flex", flexDirection: "column", gap: 12, width: "100%" }}>
                {items.map((item, i) => {
                  const maxVal = Math.max(...(values.length ? values : [1]));
                  return (
                    <div key={i} style={fadeRise(frame, staggerDelay(i, 10, 12), 15)}>
                      <MiniBar
                        value={values[i] || 0}
                        maxValue={maxVal}
                        label={`${item}  ${values[i] != null ? fmtNum(values[i]) : ""}${data.unit || ""}`}
                        color={moodCfg.accent}
                        height={10}
                      />
                    </div>
                  );
                })}
              </div>
              {/* 주석 */}
              {data.annotations?.map((ann: { text: string; index?: number }, i: number) => (
                <div key={i} style={{ opacity: fadeVal(frame, staggerDelay(i, 8, 40), 12), paddingLeft: 48 }}>
                  <AnnotationLine text={ann.text} width={80} color={moodCfg.accent} />
                </div>
              ))}
            </div>
          );
        })()}

        {/* Status Dots */}
        {statusDots.length > 0 && (
          <StatusDotList
            dots={statusDots}
            delay={
              itemDelays.length > 0
                ? Math.max(...itemDelays) + 15
                : Math.max(...headlineDelays, 0) + 30
            }
          />
        )}

        </div>{/* Items 영역 끝 */}
      </div>
      </div>{/* contentWidth wrapper */}
    </AbsoluteFill>
  );
};

/* ================================================================
   LineReveal — 라인별 등장 애니메이션
   ================================================================ */

const LineReveal: React.FC<{
  line: string;
  delay: number;
  reveal: string;
  emphasis: string;
  moodCfg: MoodConfig;
  countedValues: number[];
  glowOpacity: number;
  lineIndex: number;
  totalLines: number;
  accentOffset?: number;
  motionConfig?: MotionConfig;
}> = ({
  line,
  delay,
  reveal,
  emphasis,
  moodCfg,
  countedValues,
  glowOpacity,
  lineIndex,
  totalLines,
  accentOffset = 0,
  motionConfig,
}) => {
  const T = usePresetTypo();
  const frame = useCurrentFrame();
  const dur = motionConfig?.entrance.duration || 18;
  const entranceType = motionConfig?.entrance.type || "";

  // 모든 애니메이션 훅을 무조건 최상위에서 호출 (Rules of Hooks 준수)
  const bounceAnim = useBounceIn(delay, dur);
  const springVal = useSpringValue(delay, motionConfig?.entrance.springConfig);
  const fadeSlideAnim = useFadeSlide(delay, dur, motionConfig?.entrance.rise || 20);

  let opacity: number;
  let transform: string;
  let extraStyle: React.CSSProperties = {};

  // motionConfig가 있으면 entrance.type 기반 애니메이션
  if (entranceType === "bounce") {
    opacity = bounceAnim.opacity as number;
    transform = bounceAnim.transform as string;
  } else if (entranceType === "scale" || entranceType === "overshoot") {
    opacity = interpolate(frame, [delay, delay + dur], [0, 1], clamp);
    const s = entranceType === "overshoot"
      ? interpolate(frame, [delay, delay + dur], [0.5, 1], { ...clamp, easing: Easing.out(Easing.back(1.7)) })
      : interpolate(frame, [delay, delay + dur], [0.6, 1], { ...clamp, easing: Easing.out(Easing.exp) });
    transform = `scale(${s})`;
  } else if (entranceType === "spring") {
    opacity = interpolate(frame, [delay, delay + 8], [0, 1], clamp);
    transform = `scale(${0.5 + springVal * 0.5})`;
  } else if (entranceType === "fadeSlide") {
    opacity = fadeSlideAnim.opacity as number;
    transform = fadeSlideAnim.transform as string;
  } else if (entranceType === "typewriter") {
    opacity = interpolate(frame, [delay, delay + 5], [0, 1], clamp);
    transform = "";
  } else if (reveal === "zoom_in") {
    opacity = interpolate(frame, [delay, delay + dur], [0, 1], clamp);
    const s = interpolate(frame, [delay, delay + dur], [0.6, 1], { ...clamp, easing: Easing.out(Easing.exp) });
    transform = `scale(${s})`;
  } else if (reveal === "dramatic_pause") {
    if (lineIndex === 0) {
      opacity = interpolate(frame, [delay, delay + dur], [0, 1], clamp);
      const rise = interpolate(frame, [delay, delay + dur], [20, 0], { ...clamp, easing: ease });
      transform = `translateY(${rise}px)`;
    } else {
      opacity = interpolate(frame, [delay, delay + 20], [0, 1], clamp);
      const s = interpolate(frame, [delay, delay + 20], [1.3, 1], { ...clamp, easing: Easing.out(Easing.exp) });
      transform = `scale(${s})`;
    }
  } else {
    // fadeRise (기본)
    opacity = interpolate(frame, [delay, delay + dur], [0, 1], clamp);
    const rise = interpolate(frame, [delay, delay + dur], [motionConfig?.entrance.rise || 20, 0], { ...clamp, easing: ease });
    transform = `translateY(${rise}px)`;
  }

  // emphasis 후처리 (entrance 이후)
  if (motionConfig?.emphasis && frame > delay + dur) {
    const emphDelay = delay + dur + (motionConfig.emphasis.delay || 0);
    const emphDur = motionConfig.emphasis.duration || 20;
    if (motionConfig.emphasis.type === "shake") {
      const shakeIntensity = motionConfig.emphasis.intensity || 6;
      const shakeProgress = interpolate(frame, [emphDelay, emphDelay + emphDur], [0, 1], clamp);
      if (shakeProgress > 0 && shakeProgress < 1) {
        const offset = Math.sin(shakeProgress * Math.PI * 6) * shakeIntensity * (1 - shakeProgress);
        transform = (transform || "") + ` translateX(${offset}px)`;
      }
    } else if (motionConfig.emphasis.type === "pulse") {
      const pulseProgress = interpolate(frame, [emphDelay, emphDelay + emphDur], [0, 1], clamp);
      if (pulseProgress > 0) {
        const pulse = 1 + Math.sin(pulseProgress * Math.PI * 2) * 0.03;
        transform = (transform || "") + ` scale(${pulse})`;
      }
    } else if (motionConfig.emphasis.type === "glow") {
      const glowP = interpolate(frame, [emphDelay, emphDelay + emphDur], [0, 0.6], clamp);
      if (glowP > 0) {
        extraStyle = { textShadow: `0 0 ${20 + glowP * 40}px rgba(${moodCfg.accentRgb},${glowP})` };
      }
    } else if (motionConfig.emphasis.type === "glitch") {
      const gp = interpolate(frame, [emphDelay, emphDelay + emphDur], [0, 1], clamp);
      if (gp > 0 && gp < 1) {
        const glitchX = Math.sin(gp * Math.PI * 12) * (motionConfig.emphasis.intensity || 8) * (1 - gp);
        const glitchY = Math.cos(gp * Math.PI * 8) * 3 * (1 - gp);
        transform = (transform || "") + ` translate(${glitchX}px, ${glitchY}px)`;
        extraStyle = { textShadow: `${glitchX * 0.5}px 0 rgba(255,0,0,${0.5 * (1 - gp)}), ${-glitchX * 0.5}px 0 rgba(0,255,255,${0.5 * (1 - gp)})` };
      }
    } else if (motionConfig.emphasis.type === "bounce") {
      const bp = interpolate(frame, [emphDelay, emphDelay + emphDur], [0, 1], clamp);
      if (bp > 0) {
        const bounceScale = 1 + Math.abs(Math.sin(bp * Math.PI * 3)) * 0.08 * (1 - bp);
        transform = (transform || "") + ` scale(${bounceScale})`;
      }
    }
  }

  const isChapterLabel = /^CHAPTER\s*\d/i.test(line.trim());
  const baseFontSize = isChapterLabel ? T.splitVsText : T.headlineBase;
  const showBadge = false; // 헤드라인에 숫자 뱃지 비활성 — 시퀀스 뱃지는 items에서만 표시

  const resolvedBaseFontSize = accentFontSizeOverride
    ? Math.max(Math.round(accentFontSizeOverride * 0.58), T.chartTitle)
    : baseFontSize;

  return (
    <div
      style={{
        opacity,
        transform,
        fontSize: resolvedBaseFontSize,
        fontWeight: 600,
        lineHeight:
          emphasis === "number" || emphasis === "count" ? 2.4 : 1.6,
        marginBottom: lineIndex < totalLines - 1 ? 8 : 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: showBadge ? 16 : 0,
        ...extraStyle,
      }}
    >
      {showBadge && (
        <CircleBadge
          text={String(lineIndex + 1)}
          size={40}
          filled={lineIndex === totalLines - 1}
        />
      )}
      <EmphasisAccentText
        text={line}
        emphasis={emphasis}
        moodCfg={moodCfg}
        countedValues={countedValues}
        glowOpacity={glowOpacity}
        accentStartIndex={accentOffset}
      />
    </div>
  );
};

/* ================================================================
   QuoteMark — 인용 장식
   ================================================================ */

const QuoteMark: React.FC<{ color: string; delay: number }> = ({
  color,
  delay,
}) => {
  const T = usePresetTypo();
  const qFade = useFadeRise(delay, 15, 10);
  return (
    <div
      style={{
        ...qFade,
        fontSize: T.quoteMarkSize,
        fontWeight: 800,
        color,
        opacity: (qFade.opacity as unknown as number) * 0.3,
        lineHeight: 1,
        marginBottom: -20,
        position: "relative",
        zIndex: 2,
      }}
    >
      &ldquo;
    </div>
  );
};
