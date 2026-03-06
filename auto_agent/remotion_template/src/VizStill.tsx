import React from "react";
import { AbsoluteFill } from "remotion";
import { VisualizationRenderer } from "./components/VisualizationRenderer";
import { DesignTokenProvider } from "./contexts/DesignTokenContext";
import type { VisualizationData, DesignTokens, VizAnimationConfig } from "./types/manifest";

interface Props {
  vizData: VisualizationData;
  vizAnimation?: VizAnimationConfig;
  designTokens?: DesignTokens;
}

/**
 * 시각화 스틸 이미지 렌더링용 컴포지션
 *
 * npx remotion still VizStill output.png --props '{"vizData": {...}, "vizAnimation": {...}}'
 */
export const VizStill: React.FC<Props> = ({ vizData, vizAnimation, designTokens }) => {
  return (
    <AbsoluteFill>
      <DesignTokenProvider tokens={designTokens}>
        <VisualizationRenderer
          data={vizData}
          durationInFrames={90}
          fps={30}
          vizAnimation={vizAnimation}
        />
      </DesignTokenProvider>
    </AbsoluteFill>
  );
};
