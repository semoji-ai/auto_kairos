// remotion/src/design/resolvePreset.ts
import type { DesignPreset, DesignPresetOverride } from "./types";
import { DEFAULT_PRESET, WHITE_OVERRIDE } from "./defaults";
import { ART_PRESETS } from "./presets";

/** 재귀적 deep merge — source의 값이 있으면 base를 덮어씀 */
export function deepMerge<T extends Record<string, any>>(
  base: T,
  ...overrides: (Partial<T> | undefined)[]
): T {
  const result = { ...base };
  for (const override of overrides) {
    if (!override) continue;
    for (const key of Object.keys(override) as (keyof T)[]) {
      const val = override[key];
      if (val === undefined) continue;
      if (
        val !== null &&
        typeof val === "object" &&
        !Array.isArray(val) &&
        typeof result[key] === "object" &&
        !Array.isArray(result[key])
      ) {
        result[key] = deepMerge(result[key] as any, val as any);
      } else {
        result[key] = val as T[keyof T];
      }
    }
  }
  return result;
}

/** artStyle 문자열에서 이름 추출: "artstyle/styles/semoji.json" → "semoji" */
function extractStyleName(artStyle: string): string {
  return artStyle.replace(/.*\//, "").replace(/\.json$/, "");
}

/**
 * manifest meta에서 최종 DesignPreset을 해석
 * 우선순위: DEFAULT → artStyle 프리셋 → 사용자 오버라이드(designPreset)
 */
export function resolvePreset(meta: {
  artStyle?: string;
  designPreset?: DesignPresetOverride;
  videoTheme?: string;
}): DesignPreset {
  // 1. artStyle 프리셋 먼저 로드 (baseTheme 확인용)
  const styleName = meta.artStyle ? extractStyleName(meta.artStyle) : undefined;
  const artPreset = styleName ? ART_PRESETS[styleName] : undefined;
  console.log("[resolvePreset] artStyle=", meta.artStyle, "styleName=", styleName, "artPreset fonts=", (artPreset as any)?.fonts?.headline?.family);

  // 2. 기본 (videoTheme 또는 artPreset.baseTheme에 따라 white 오버라이드 적용)
  const base = DEFAULT_PRESET;
  const isWhite = meta.videoTheme === "white"
    || meta.designPreset?.baseTheme === "white"
    || meta.designPreset?.baseTheme === "light"
    || artPreset?.baseTheme === "white"
    || artPreset?.baseTheme === "light";
  const themeOverride = isWhite ? WHITE_OVERRIDE : undefined;

  // 3. 사용자 오버라이드
  const userOverride = meta.designPreset;

  const result = deepMerge(base, themeOverride as any, artPreset as any, userOverride as any);

  // designPreset에서 accent가 변경되면 moods의 accent도 일괄 업데이트
  // (moods에 개별 accent가 하드코딩되어 있어도 사용자 선택을 반영)
  const userAccent = userOverride?.colors?.accent;
  if (userAccent && result.moods) {
    const rgbMatch = userAccent.match(/^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i);
    const userAccentRgb = rgbMatch
      ? `${parseInt(rgbMatch[1], 16)},${parseInt(rgbMatch[2], 16)},${parseInt(rgbMatch[3], 16)}`
      : result.colors?.accentRgb || "245,158,11";
    for (const mood of Object.keys(result.moods)) {
      const m = result.moods[mood];
      // urgent(빨강), somber(회색)은 mood 고유 색상 유지
      if (mood === "urgent" || mood === "somber") continue;
      if (m) {
        m.accent = userAccent;
        m.accentRgb = userAccentRgb;
      }
    }
  }

  return result;
}
