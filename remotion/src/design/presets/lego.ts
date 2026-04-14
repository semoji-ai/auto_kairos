// AUTO-GENERATED — auto_agent/data/artstyle/styles/lego.json에서 생성
// 직접 수정 금지. JSON을 수정한 후 scripts/generate_presets.py를 실행하세요.
import type { DesignPresetOverride } from "../types";

export const LEGO_PRESET: DesignPresetOverride = {
  artStyle: "lego",
  baseTheme: "dark",
  colors: {
    accent: "#EF4444",
    accentRgb: "239,68,68",
    accentBg: "rgba(239,68,68,0.08)",
    accentBorder: "rgba(239,68,68,0.3)",
    accentSoft: "rgba(239,68,68,0.15)",
    cardBg: "rgba(239,68,68,0.06)",
    cardBorder: "rgba(239,68,68,0.25)",
  },
  layout: {
    cardRadius: 12,
    gap: 24,
  },
  map: {
    defaultTheme: "minimal_light",
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
  },
  subtitle: {
    fontSize: 54,
    fontFamily: "Pretendard",
    fontWeight: 700,
    color: "#FFFFFF",
    strokeWidth: 0,
    strokeColor: "transparent",
    keywordColor: "#EF4444",
    keywordStrokeColor: "transparent",
    backgroundColor: "rgba(0,0,0,0.75)",
    borderRadius: 8,
    boxShadow: "0 2px 12px rgba(0,0,0,0.4)",
    bottomOffset: 60,
    maxWidth: "90%",
    lineHeight: 1.4,
  },
};
