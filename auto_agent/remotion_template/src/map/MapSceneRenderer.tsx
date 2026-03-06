import React, { useEffect, useState } from "react";
import { AbsoluteFill, delayRender, continueRender, staticFile } from "remotion";
import { FONT_DEFS } from "../visualizations/vizStyles";
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

const useFonts = () => {
  const [handle] = useState(() => delayRender("Loading map fonts"));

  useEffect(() => {
    const loadAll = async () => {
      const promises = FONT_DEFS.map(async (f) => {
        const url = staticFile(f.file);
        const descriptors: FontFaceDescriptors = {
          weight: f.weight,
          style: "normal",
        };
        const face = new FontFace(f.family, `url('${url}')`, descriptors);
        const loaded = await face.load();
        document.fonts.add(loaded);
      });
      await Promise.all(promises);
      continueRender(handle);
    };
    loadAll().catch((err) => {
      console.error("Font loading failed:", err);
      continueRender(handle);
    });
  }, [handle]);
};

export const MapSceneRenderer: React.FC<Props> = ({
  data,
  durationInFrames,
  fps,
}) => {
  useFonts();

  const commonProps = { data, durationInFrames, fps };

  return (
    <AbsoluteFill style={{ filter: "brightness(1.0)" }}>
      <MapThemeProvider theme={data.mapStyle ?? "modern_clean"}>
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
