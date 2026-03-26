import type { DesignPresetOverride } from "../types";
import tokensJson from "../../../../data/artstyle/styles/quirky_cartoon.json";

const tokens = (tokensJson as any).design_tokens || {};

export const QUIRKY_CARTOON_PRESET: DesignPresetOverride = {
  artStyle: "quirky_cartoon",
  baseTheme: tokens.baseTheme || "dark",
  defaultBackground: tokens.defaultBackground,
  colors: tokens.colors,
  moods: tokens.moods,
  layout: tokens.layout,
  map: tokens.map,
  subtitle: tokens.subtitle,
};
