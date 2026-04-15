// remotion/src/design/fonts.ts
import { useState, useEffect } from "react";
import { delayRender, continueRender, staticFile } from "remotion";
import type { FontDef, PresetFonts } from "./types";
import { useDesignPreset } from "./DesignPresetContext";

const resolveUrl = (path: string): string =>
  path.startsWith("http://") || path.startsWith("https://") ? path : staticFile(path);

/** 이미 document.fonts에 로드된 폰트 패밀리인지 확인 */
const isFontAlreadyLoaded = (family: string): boolean => {
  const norm = family.toLowerCase();
  for (const ff of document.fonts) {
    if (ff.family.replace(/['"]/g, "").toLowerCase() === norm && ff.status === "loaded") {
      return true;
    }
  }
  return false;
};

async function loadFontDef(def: FontDef): Promise<void> {
  if (!def.files || def.files.length === 0) return; // 파일 없음 = 시스템 폰트
  if (isFontAlreadyLoaded(def.family)) return;      // 이미 로드됨
  await Promise.all(
    def.files.map(async (f) => {
      const face = new FontFace(def.family, `url('${resolveUrl(f.file)}')`, {
        weight: f.weight,
        style: "normal",
      });
      const loaded = await face.load();
      document.fonts.add(loaded);
    }),
  );
}

/** 프리셋 기반 통합 폰트 로딩 훅 */
export function usePresetFonts(): void {
  const preset = useDesignPreset();
  const [handle] = useState(() => delayRender("Loading preset fonts"));

  useEffect(() => {
    const load = async () => {
      const f = preset.fonts;
      await loadFontDef(f.body);
      if (f.headline) await loadFontDef(f.headline);
      if (f.value)    await loadFontDef(f.value);
      if (f.mono)     await loadFontDef(f.mono);
      if (f.subtitle) await loadFontDef(f.subtitle);
      if (f.title)    await loadFontDef(f.title);
      continueRender(handle);
    };
    load().catch((e) => { console.error("[fonts] load error", e); continueRender(handle); });
  }, [handle]);
}

/** 프리셋에서 CSS font-family 문자열 생성 */
export function buildFontFamily(preset: { fonts: Pick<PresetFonts, "body"> }): string {
  const body = preset.fonts.body;
  return `'${body.family}', ${body.fallback}`;
}

export function buildHeadlineFontFamily(fonts: PresetFonts): string {
  const f = fonts.headline ?? fonts.body;
  return `'${f.family}', ${f.fallback}`;
}

export function buildValueFontFamily(fonts: PresetFonts): string {
  const f = fonts.value ?? fonts.body;
  return `'${f.family}', ${f.fallback}`;
}

export function buildMonoFontFamily(fonts: PresetFonts): string {
  const f = fonts.mono ?? { family: "Georgia", fallback: "serif" };
  return `'${f.family}', ${f.fallback}`;
}

/** @deprecated headline 사용 권장 */
export function buildTitleFontFamily(preset: { fonts: Pick<PresetFonts, "body" | "title"> }): string {
  const title = preset.fonts.title || preset.fonts.body;
  return `'${title.family}', ${title.fallback}`;
}
