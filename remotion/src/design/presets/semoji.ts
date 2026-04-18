// AUTO-GENERATED — auto_agent/data/artstyle/styles/semoji.json에서 생성
// 직접 수정 금지. JSON을 수정한 후 scripts/generate_presets.py를 실행하세요.
import type { DesignPresetOverride } from "../types";

export const SEMOJI_PRESET: DesignPresetOverride = {
  artStyle: "semoji",
  baseTheme: "light",
  colors: {
    accent: "#4A90D9",
    accentRgb: "74,144,217",
    accentBg: "rgba(74,144,217,0.08)",
    accentBorder: "rgba(74,144,217,0.3)",
    accentSoft: "rgba(74,144,217,0.15)",
    cardBg: "rgba(74,144,217,0.06)",
    cardBorder: "rgba(74,144,217,0.2)",
  },
  layout: {
    cardRadius: 16,
    gap: 28,
  },
  map: {
    defaultTheme: "warm_earth",
  },
  defaultBackground: "background/semoji_grid_bg.jpg",
  defaultBgOpacity: 1.0,
  disableIcons: true,
  disableSpotlight: true,
  quoteReveal: "typewriter",
  defaultItemEntrance: "overshoot",
  countUpThreshold: 0,
  texture: {
    src: "background/63517.jpg",
    blendMode: "multiply",
    opacity: 0.1,
  },
  fonts: {
    body: {
      family: "SB 어그로체",
      fallback: "'Apple SD Gothic Neo', sans-serif",
      files: [
        {
          file: "fonts/SBAggroOTF-L.otf",
          weight: "300",
        },
        {
          file: "fonts/SBAggroOTF-M.otf",
          weight: "500",
        },
        {
          file: "fonts/SBAggroOTF-B.otf",
          weight: "700",
        },
      ],
    },
    headline: {
      family: "카페24 써라운드",
      fallback: "'Apple SD Gothic Neo', sans-serif",
      files: [
        {
          file: "fonts/Cafe24Ssurround.ttf",
          weight: "700",
        },
      ],
    },
    value: {
      family: "배민 연성체",
      fallback: "sans-serif",
      files: [
        {
          file: "fonts/BMYeonsung.ttf",
          weight: "400",
        },
      ],
    },
    subtitle: {
      family: "G마켓 산스",
      fallback: "'Apple SD Gothic Neo', sans-serif",
      files: [
        {
          file: "fonts/GmarketSansMedium.ttf",
          weight: "500",
        },
        {
          file: "fonts/GmarketSansBold.ttf",
          weight: "700",
        },
      ],
    },
    mono: {
      family: "GyeonggiMillenniumBatang",
      fallback: "serif",
      files: [
        {
          file: "fonts/GyeonggiMillenniumBatang-Regular.ttf",
          weight: "400",
        },
        {
          file: "fonts/GyeonggiMillenniumBatang-Bold.ttf",
          weight: "700",
        },
      ],
    },
  },
  subtitle: {
    fontSize: 52,
    fontFamily: "G마켓 산스",
    fontWeight: 400,
    color: "#FFFFFF",
    strokeWidth: 0,
    strokeColor: "transparent",
    keywordColor: "#4A90D9",
    keywordStrokeColor: "transparent",
    backgroundColor: "rgba(0,0,0,0.85)",
    borderRadius: 8,
    boxShadow: "0 2px 12px rgba(0,0,0,0.15)",
    bottomOffset: 60,
    maxWidth: "92%",
    lineHeight: 1.4,
  },
  variants: {
    itemsList: "accent-filled",
    itemsGrid: "accent-filled",
    comparisonCell: "none",
    metricCard: "stroke_white",
  },
};
