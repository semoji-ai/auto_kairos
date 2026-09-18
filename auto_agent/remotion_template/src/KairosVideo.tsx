import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import {VideoTrackLayer} from "./components/VideoTrackLayer";
import { SceneSequencer } from "./components/SceneSequencer";
import { SubtitleTrack } from "./components/SubtitleTrack";
import { OverlayLayer } from "./components/OverlayLayer";
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
  const frame = useCurrentFrame();
  let offset = 0;
  const current = manifest.scenes.find(s => {
    const start = offset;
    offset += s.durationFrames ?? Math.max(1, Math.ceil(s.audioDurationSec * manifest.meta.fps));
    return frame >= start && frame < offset;
  });
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

        <VideoTrackLayer clips={manifest.videoClips} scene={current} />
        <AbsoluteFill style={{zIndex: 3, pointerEvents: "none"}}>
        {/* Layer 3: GIF/Lottie 오버레이 */}
        <OverlayLayer scenes={manifest.scenes} fps={manifest.meta.fps} />

        {/* Layer 4: 자막 (독립 트랙) */}
        <SubtitleTrack
          scenes={manifest.scenes}
          fps={manifest.meta.fps}
          config={subtitleConfig}
        />
        </AbsoluteFill>
      </AbsoluteFill>
    </DesignTokenProvider>
  );
};
