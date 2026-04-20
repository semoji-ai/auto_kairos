import React from "react";
import { AbsoluteFill, Sequence } from "remotion";
import { GifOverlay } from "./GifOverlay";
import { LottieOverlay } from "./LottieOverlay";
import type { SceneEntry } from "../types/manifest";

interface Props {
  scenes: SceneEntry[];
  fps: number;
}

export const OverlayLayer: React.FC<Props> = ({ scenes, fps }) => {
  let frameOffset = 0;

  return (
    <AbsoluteFill className="pointer-events-none">
      {scenes.map((scene) => {
        const durationInFrames = Math.ceil(scene.audioDurationSec * fps);
        const from = frameOffset;
        frameOffset += durationInFrames;

        if (!scene.overlays || scene.overlays.length === 0) return null;

        return (
          <Sequence
            key={`overlay-${scene.sceneNumber}`}
            from={from}
            durationInFrames={durationInFrames}
            layout="none"
          >
            {scene.overlays.map((ov, i) =>
              ov.type === "gif" ? (
                <GifOverlay
                  key={`gif-${i}`}
                  overlay={ov}
                  durationInFrames={durationInFrames}
                />
              ) : (
                <LottieOverlay
                  key={`lottie-${i}`}
                  overlay={ov}
                  durationInFrames={durationInFrames}
                />
              ),
            )}
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
