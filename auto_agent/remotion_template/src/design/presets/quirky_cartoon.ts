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
  moods: {
    dramatic:      { accent: "#F59E0B", accentRgb: "245,158,11", speed: 1.2, glow: 0.6, gradient: "radial-gradient(ellipse 80% 60% at 50% 40%, #1a1005 0%, #0A0A0A 70%)" },
    urgent:        { accent: "#EF4444", accentRgb: "239,68,68",  speed: 1.5, glow: 0.8, gradient: "radial-gradient(ellipse 80% 60% at 50% 40%, #1a0808 0%, #0A0A0A 70%)" },
    somber:        { accent: "#9CA3AF", accentRgb: "156,163,175", speed: 0.7, glow: 0.2, gradient: "radial-gradient(ellipse 80% 60% at 50% 40%, #0d0d0e 0%, #0A0A0A 70%)" },
    informative:   { accent: "#F59E0B", accentRgb: "245,158,11", speed: 1.0, glow: 0.3, gradient: "radial-gradient(ellipse 80% 60% at 50% 40%, #1a1005 0%, #0A0A0A 70%)" },
    contemplative: { accent: "#D97706", accentRgb: "217,119,6",  speed: 0.6, glow: 0.2, gradient: "radial-gradient(ellipse 80% 60% at 50% 40%, #14100a 0%, #0A0A0A 70%)" },
    suspense:      { accent: "#F59E0B", accentRgb: "245,158,11", speed: 0.8, glow: 0.5, gradient: "radial-gradient(ellipse 80% 60% at 50% 40%, #14100a 0%, #0A0A0A 70%)" },
    triumphant:    { accent: "#10B981", accentRgb: "16,185,129",  speed: 1.0, glow: 0.5, gradient: "radial-gradient(ellipse 80% 60% at 50% 40%, #081a10 0%, #0A0A0A 70%)" },
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
