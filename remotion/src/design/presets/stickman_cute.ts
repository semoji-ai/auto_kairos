// AUTO-GENERATED — auto_agent/data/artstyle/styles/stickman_cute.json에서 생성
// 직접 수정 금지. JSON을 수정한 후 scripts/generate_presets.py를 실행하세요.
import type { DesignPresetOverride } from "../types";

export const STICKMANCUTE_PRESET: DesignPresetOverride = {
  artStyle: "stickman_cute",
  baseTheme: "dark",
  colors: {
    accent: "#10B981",
    accentRgb: "16,185,129",
    accentBg: "rgba(16,185,129,0.08)",
    accentBorder: "rgba(16,185,129,0.3)",
    accentSoft: "rgba(16,185,129,0.15)",
    cardBg: "rgba(16,185,129,0.06)",
    cardBorder: "rgba(16,185,129,0.25)",
  },
  layout: {
    gap: 20,
    cardRadius: 16,
  },
  map: {
    defaultTheme: "clean_white",
  },
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
      fallback: "sans-serif",
      files: [
        {
          file: "fonts/BarlowCondensed-Bold.ttf",
          weight: "700",
        },
      ],
    },
    subtitle: {
      family: "Pretendard",
      fallback: "'Apple SD Gothic Neo', sans-serif",
      files: [
        {
          file: "fonts/Pretendard-Bold.otf",
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
    fontFamily: "Pretendard",
    fontWeight: 700,
    color: "#FFFFFF",
    strokeWidth: 0,
    strokeColor: "transparent",
    keywordColor: "#10B981",
    keywordStrokeColor: "transparent",
    backgroundColor: "rgba(0,0,0,0.7)",
    borderRadius: 8,
    boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
    bottomOffset: 60,
    maxWidth: "90%",
    lineHeight: 1.4,
  },
};
