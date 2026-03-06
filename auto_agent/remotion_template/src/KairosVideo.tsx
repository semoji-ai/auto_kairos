import React from "react";
import { AbsoluteFill } from "remotion";
import { SceneSequencer } from "./components/SceneSequencer";
import { SubtitleTrack } from "./components/SubtitleTrack";
import { BGMLayer } from "./components/BGMLayer";
import { DesignTokenProvider } from "./contexts/DesignTokenContext";
import type { SceneManifest, SubtitleConfig } from "./types/manifest";

interface Props {
  manifest: SceneManifest;
  subtitleConfig: SubtitleConfig;
}

export const KairosVideo: React.FC<Props> = ({
  manifest,
  subtitleConfig,
}) => {
  return (
    <DesignTokenProvider tokens={manifest.meta.designTokens}>
      <AbsoluteFill style={{ backgroundColor: "#000" }}>
        {/* Layer 1: BGM */}
        {manifest.bgm && <BGMLayer config={manifest.bgm} />}

        {/* Layer 2: 영상/이미지 + 오디오 */}
        <SceneSequencer
          scenes={manifest.scenes}
          fps={manifest.meta.fps}
        />

        {/* Layer 3: 자막 (독립 트랙) */}
        <SubtitleTrack
          scenes={manifest.scenes}
          fps={manifest.meta.fps}
          config={subtitleConfig}
        />
      </AbsoluteFill>
    </DesignTokenProvider>
  );
};
