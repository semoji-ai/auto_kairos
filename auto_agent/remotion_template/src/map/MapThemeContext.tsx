import React, { createContext, useContext, useMemo } from "react";
import { resolveMapTheme, type MapTheme } from "./mapTheme";

const MapThemeCtx = createContext<MapTheme | null>(null);

interface Props {
  theme: string | MapTheme;
  children: React.ReactNode;
}

/** MapSceneRenderer 에서 1회 감싸기. */
export const MapThemeProvider: React.FC<Props> = ({ theme, children }) => {
  const resolved = useMemo<MapTheme>(
    () => (typeof theme === "string" ? resolveMapTheme(theme) : theme),
    [theme],
  );
  return <MapThemeCtx.Provider value={resolved}>{children}</MapThemeCtx.Provider>;
};

/** 맵 오버레이 컴포넌트에서 소비. MapThemeProvider 바깥이면 에러. */
export const useMapTheme = (): MapTheme => {
  const ctx = useContext(MapThemeCtx);
  if (!ctx) throw new Error("useMapTheme must be used within MapThemeProvider");
  return ctx;
};
