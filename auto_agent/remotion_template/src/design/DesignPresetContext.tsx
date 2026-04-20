// remotion/src/design/DesignPresetContext.tsx
import React, { useMemo } from "react";
import type { DesignPreset, DesignPresetOverride } from "./types";
import { DEFAULT_PRESET } from "./defaults";
import { resolvePreset } from "./resolvePreset";

const DesignPresetCtx = React.createContext<DesignPreset>(DEFAULT_PRESET);

interface ProviderProps {
  meta: {
    artStyle?: string;
    designPreset?: DesignPresetOverride;
    videoTheme?: string;
  };
  children: React.ReactNode;
}

export const DesignPresetProvider: React.FC<ProviderProps> = ({
  meta,
  children,
}) => {
  const preset = useMemo(() => resolvePreset(meta), [
    meta.artStyle,
    meta.videoTheme,
    // designPreset은 객체라 JSON 비교 필요 — 실제로는 manifest가 바뀔 때만 재계산
    JSON.stringify(meta.designPreset),
  ]);

  return (
    <DesignPresetCtx.Provider value={preset}>
      {children}
    </DesignPresetCtx.Provider>
  );
};

/** 현재 디자인 프리셋 전체를 가져온다 */
export const useDesignPreset = (): DesignPreset =>
  React.useContext(DesignPresetCtx);

/** 하위호환: 기존 useC()와 동일한 인터페이스 — colors만 반환 */
export const usePresetColors = () => React.useContext(DesignPresetCtx).colors;

/** 타이포 토큰 */
export const usePresetTypo = () => React.useContext(DesignPresetCtx).typography;

/** 레이아웃 토큰 */
export const usePresetLayout = () => React.useContext(DesignPresetCtx).layout;

/** 컴포넌트 변형 토큰 */
export const usePresetVariants = () => React.useContext(DesignPresetCtx).variants;
