import type { DesignPresetOverride } from "../types";
import { SEMOJI_PRESET } from "./semoji";
import { LEGO_PRESET } from "./lego";
import { QUIRKY_CARTOON_PRESET } from "./quirky_cartoon";
import { STICKMAN_CUTE_PRESET } from "./stickman_cute";

export const ART_PRESETS: Record<string, DesignPresetOverride> = {
  semoji: SEMOJI_PRESET,
  lego: LEGO_PRESET,
  quirky_cartoon: QUIRKY_CARTOON_PRESET,
  stickman_cute: STICKMAN_CUTE_PRESET,
};
