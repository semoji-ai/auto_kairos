import React from "react";
import { AbsoluteFill, Sequence } from "remotion";
import { SubtitleOverlay } from "./SubtitleOverlay";
import type { SceneEntry, SubtitleConfig } from "../types/manifest";

interface Props {
  scenes: SceneEntry[];
  fps: number;
  config: SubtitleConfig;
}

/**
 * 자막 전용 레이어 (트랙 분리)
 *
 * 영상/이미지 레이어와 독립적으로 렌더링되어
 * Studio에서 자막만 따로 제어할 수 있다.
 */
export const SubtitleTrack: React.FC<Props> = ({ scenes, fps, config }) => {
  if (!config.visible) return null;

  let frameOffset = 0;

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {scenes.map((scene) => {
        const durationInFrames = Math.ceil(scene.audioDurationSec * fps) + 2;
        const from = frameOffset;
        frameOffset += durationInFrames;

        if (scene.subtitles.length === 0) return null;

        return (
          <Sequence
            key={`sub-${scene.sceneNumber}`}
            from={from}
            durationInFrames={durationInFrames}
            layout="none"
          >
            <SubtitleOverlay
              subtitles={scene.subtitles}
              fps={fps}
              config={config}
            />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
