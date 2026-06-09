// AUTO-GENERATED — auto_agent/data/artstyle/styles/quirky_cartoon.json에서 생성
// 직접 수정 금지. JSON을 수정한 후 scripts/generate_presets.py를 실행하세요.
import type { DesignPresetOverride } from "../types";

export const QUIRKYCARTOON_PRESET: DesignPresetOverride = {
  artStyle: "quirky_cartoon",
  baseTheme: "dark",
  colors: {
    accent: "#F59E0B",
    accentRgb: "245,158,11",
    accentBg: "rgba(245,158,11,0.08)",
    accentBorder: "rgba(245,158,11,0.3)",
    accentSoft: "rgba(245,158,11,0.15)",
    cardBg: "rgba(245,158,11,0.06)",
    cardBorder: "rgba(245,158,11,0.25)",
  },
  layout: {
    cardRadius: 16,
    gap: 28,
  },
  defaultBackground: "background/light-gray-distorted-square-tile-texture-background-illustration.jpg",
  disableIcons: true,
  fonts: {
    body: {
      family: "Pretendard",
      fallback: "'Apple SD Gothic Neo', sans-serif",
      files: [
        {
          file: "fonts/Pretendard-Regular.otf",
          weight: "400",
        },
        {
          file: "fonts/Pretendard-Bold.otf",
          weight: "700",
        },
      ],
    },
    headline: {
      family: "Tenada",
      fallback: "sans-serif",
      files: [
        {
          file: "fonts/Tenada.woff2",
          weight: "400",
        },
      ],
    },
    value: {
      family: "Barlow Condensed",
      fallback: "'Tenada', sans-serif",
      files: [
        {
          file: "fonts/BarlowCondensed-Bold.ttf",
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
    subtitle: {
      family: "EunpyeongSagaDogseoText",
      fallback: "sans-serif",
      files: [
        {
          file: "fonts/EunpyeongSagaDogseoText-Regular.ttf",
          weight: "400",
        },
      ],
    },
  },
  subtitle: {
    fontSize: 63,
    fontFamily: "EunpyeongSagaDogseoText",
    fontWeight: 400,
    color: "#1A1A1A",
    strokeWidth: 0,
    strokeColor: "transparent",
    keywordColor: "#C05000",
    keywordStrokeColor: "transparent",
    backgroundColor: "#FFFFFF",
    borderRadius: 0,
    boxShadow: "10px 10px 0 0 #F59E0B",
    border: "3px solid #F59E0B",
    opacity: 0.9,
    entryAnimation: false,
    textPaddingTop: 2,
    bottomOffset: 80,
    maxWidth: "90%",
    lineHeight: 1.4,
  },
};
