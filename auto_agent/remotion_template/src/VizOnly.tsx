import React from "react";
import { AbsoluteFill } from "remotion";
import { VisualizationRenderer } from "./components/VisualizationRenderer";
import { DesignTokenProvider } from "./contexts/DesignTokenContext";
import type { SceneManifest } from "./types/manifest";

interface Props {
  manifest: SceneManifest;
  sceneNumber: number;
}

/**
 * 시각화 전용 렌더링 컴포넌트
 * 트랜지션, 자막, 오디오 없이 순수 시각화만 렌더링
 */
export const VizOnly: React.FC<Props> = ({ manifest, sceneNumber }) => {
  const scene = manifest.scenes.find((s) => s.sceneNumber === sceneNumber);
  const fps = manifest.meta.fps || 30;

  if (!scene || !scene.visualization) {
    return (
      <AbsoluteFill
        style={{
          backgroundColor: "#111",
          color: "#666",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 24,
        }}
      >
        Scene {sceneNumber}: no visualization data
      </AbsoluteFill>
    );
  }

  const durationInFrames = Math.ceil(scene.audioDurationSec * fps);

  return (
    <DesignTokenProvider tokens={manifest.meta.designTokens}>
      <AbsoluteFill>
        <VisualizationRenderer
          data={scene.visualization}
          durationInFrames={durationInFrames}
          fps={fps}
          vizAnimation={scene.vizAnimation}
          vizBackgroundPath={scene.vizBackgroundPath}
        />
      </AbsoluteFill>
    </DesignTokenProvider>
  );
};
