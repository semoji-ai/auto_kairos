import React from "react";
import { AbsoluteFill } from "remotion";
import { usePresetFonts } from "../design/fonts";
import { useDesignPreset } from "../design";
import type { MapSceneData } from "../types/manifest";
import { MapThemeProvider } from "./MapThemeContext";
import { LocationReveal } from "./LocationReveal";
import { RouteAnimation } from "./RouteAnimation";
import { TerritoryOverlay } from "./TerritoryOverlay";
import { FlyThrough } from "./FlyThrough";

interface Props {
  data: MapSceneData;
  durationInFrames: number;
  fps: number;
}

/**
 * 맵 씬 타입별 디스패처.
 * VisualizationRenderer와 동일한 패턴: 폰트 로딩 + switch 디스패치.
 */

export const MapSceneRenderer: React.FC<Props> = ({
  data,
  durationInFrames,
  fps,
}) => {
  usePresetFonts();
  const preset = useDesignPreset();
  // mapStyle 결정 우선순위: scene data → 아트스타일(preset.map.defaultTheme) → modern_clean
  const resolvedMapStyle = data.mapStyle ?? preset.map?.defaultTheme ?? "modern_clean";

  const commonProps = { data, durationInFrames, fps };

  return (
    <AbsoluteFill style={{ filter: "brightness(1.0)" }}>
      <MapThemeProvider theme={resolvedMapStyle}>
        {(() => {
          switch (data.mapType) {
            case "location_reveal":
              return <LocationReveal {...commonProps} />;
            case "route_animation":
              return <RouteAnimation {...commonProps} />;
            case "territory_overlay":
              return <TerritoryOverlay {...commonProps} />;
            case "fly_through":
              return <FlyThrough {...commonProps} />;
            default:
              return <LocationReveal {...commonProps} />;
          }
        })()}
      </MapThemeProvider>
    </AbsoluteFill>
  );
};
