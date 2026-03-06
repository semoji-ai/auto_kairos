import React from "react";
import { AbsoluteFill } from "remotion";
import { MapSceneRenderer } from "./map/MapSceneRenderer";
import { DesignTokenProvider } from "./contexts/DesignTokenContext";
import type { MapSceneData, DesignTokens } from "./types/manifest";

interface Props {
  mapScene: MapSceneData;
  designTokens?: DesignTokens;
}

/**
 * 맵 씬 스틸 이미지 렌더링용 컴포지션
 *
 * 사용법:
 * node node_modules/@remotion/cli/remotion-cli.js still MapStill output.png \
 *   --props '{"mapScene": {...}}' --frame 45
 */
export const MapStill: React.FC<Props> = ({ mapScene, designTokens }) => {
  return (
    <AbsoluteFill>
      <DesignTokenProvider tokens={designTokens}>
        <MapSceneRenderer
          data={mapScene}
          durationInFrames={90}
          fps={30}
        />
      </DesignTokenProvider>
    </AbsoluteFill>
  );
};
