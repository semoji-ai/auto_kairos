// remotion/src/design/fonts.ts
import { useState, useEffect } from "react";
import { delayRender, continueRender, staticFile } from "remotion";
import type { FontDef } from "./types";
import { useDesignPreset } from "./DesignPresetContext";

const resolveUrl = (path: string): string =>
  path.startsWith("http://") || path.startsWith("https://") ? path : staticFile(path);

const isSystemFont = (family: string): boolean => {
  try {
    return document.fonts.check(`16px "${family}"`);
  } catch {
    return false;
  }
};

async function loadFontDef(def: FontDef): Promise<void> {
  if (isSystemFont(def.family)) return;
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
      // body 폰트
      await loadFontDef(preset.fonts.body);
      // title 폰트 (있으면)
      if (preset.fonts.title) {
        await loadFontDef(preset.fonts.title);
      }
      continueRender(handle);
    };
    load().catch(() => continueRender(handle));
  }, [handle]);
}

/** 프리셋에서 CSS font-family 문자열 생성 */
export function buildFontFamily(preset: { fonts: { body: FontDef; title?: FontDef } }): string {
  const body = preset.fonts.body;
  return `'${body.family}', ${body.fallback}`;
}

export function buildTitleFontFamily(preset: { fonts: { body: FontDef; title?: FontDef } }): string {
  const title = preset.fonts.title || preset.fonts.body;
  return `'${title.family}', ${title.fallback}`;
}
