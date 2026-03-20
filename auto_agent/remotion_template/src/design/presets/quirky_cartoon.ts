import type { DesignPresetOverride } from "../types";

export const QUIRKY_CARTOON_PRESET: DesignPresetOverride = {
  artStyle: "quirky_cartoon",
  baseTheme: "dark",
  defaultBackground: "background/light-gray-distorted-square-tile-texture-background-illustration.jpg",
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
  map: {
    defaultTheme: "warm_earth",
  },
  subtitle: {
    keywordColor: "#F59E0B",
  },
};
