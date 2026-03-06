import React from "react";
import { AbsoluteFill, Audio } from "remotion";
import { SceneImage } from "./components/SceneImage";
import { SubtitleOverlay } from "./components/SubtitleOverlay";
import { TransitionEffect } from "./components/TransitionEffect";
import { VisualizationRenderer } from "./components/VisualizationRenderer";
import { DesignTokenProvider } from "./contexts/DesignTokenContext";
import { resolveAsset } from "./utils/resolveAsset";
import type { SceneManifest, SubtitleConfig } from "./types/manifest";

interface Props {
  manifest: SceneManifest;
  sceneNumber: number;
  subtitleConfig: SubtitleConfig;
}

/**
 * 씬 단위 편집/프리뷰 컴포넌트
 *
 * Remotion Studio에서 개별 씬을 독립적으로 프리뷰하고
 * Props Editor로 자막/이미지/오디오/시각화를 수정할 수 있다.
 */
export const SceneEditor: React.FC<Props> = ({ manifest, sceneNumber, subtitleConfig }) => {
  const scene = manifest.scenes.find((s) => s.sceneNumber === sceneNumber);
  const fps = manifest.meta.fps || 30;

  if (!scene) {
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
        Scene {sceneNumber} not found in manifest
      </AbsoluteFill>
    );
  }

  const durationInFrames = Math.ceil(scene.audioDurationSec * fps);

  return (
    <DesignTokenProvider tokens={manifest.meta.designTokens}>
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      {/* Layer 1: 영상/이미지 */}
      <TransitionEffect
        type={scene.transition.type}
        durationFrames={scene.transition.durationFrames}
        totalFrames={durationInFrames}
      >
        {scene.visualization ? (
          <VisualizationRenderer
            data={scene.visualization}
            durationInFrames={durationInFrames}
            fps={fps}
            vizAnimation={scene.vizAnimation}
            vizBackgroundPath={scene.vizBackgroundPath}
          />
        ) : (
          <SceneImage
            src={resolveAsset(scene.imagePath)}
            kenBurns={scene.kenBurns}
            durationInFrames={durationInFrames}
            imageMode={scene.imageMode}
          />
        )}
      </TransitionEffect>

      {/* Layer 2: 자막 (독립 레이어) */}
      <SubtitleOverlay
        subtitles={scene.subtitles}
        fps={fps}
        config={subtitleConfig}
      />

      {/* Layer 3: 오디오 */}
      {scene.audioPath ? (
        <Audio src={resolveAsset(scene.audioPath)} />
      ) : null}
    </AbsoluteFill>
    </DesignTokenProvider>
  );
};
