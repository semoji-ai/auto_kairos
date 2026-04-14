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
      family: "Pretendard",
      fallback: "'Apple SD Gothic Neo', sans-serif",
      files: [
        {
          file: "fonts/Pretendard-Bold.otf",
          weight: "700",
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
    fontSize: 52,
    fontFamily: "Pretendard",
    fontWeight: 700,
    color: "#1A1A2E",
    strokeWidth: 0,
    strokeColor: "transparent",
    keywordColor: "#4A90D9",
    keywordStrokeColor: "transparent",
    backgroundColor: "rgba(255,255,255,0.92)",
    borderRadius: 8,
    boxShadow: "0 2px 12px rgba(0,0,0,0.15)",
    bottomOffset: 60,
    maxWidth: "92%",
    lineHeight: 1.4,
  },
};
