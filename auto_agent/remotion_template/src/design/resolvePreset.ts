// remotion/src/design/resolvePreset.ts
import type { DesignPreset, DesignPresetOverride } from "./types";
import { DEFAULT_PRESET } from "./defaults";
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
  // 1. 기본
  let base = DEFAULT_PRESET;

  // videoTheme이 "white"이면 white 기본 프리셋 (향후 WHITE_PRESET 추가 가능)
  // 지금은 DEFAULT_PRESET이 dark — white는 사용자 오버라이드로 처리

  // 2. artStyle 프리셋
  const artPreset = meta.artStyle
    ? ART_PRESETS[extractStyleName(meta.artStyle)]
    : undefined;

  // 3. 사용자 오버라이드
  const userOverride = meta.designPreset;

  return deepMerge(base, artPreset as any, userOverride as any);
}
