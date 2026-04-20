import React from "react";
import { AbsoluteFill, Audio, Sequence } from "remotion";
import { SceneImage } from "./SceneImage";
import { SceneVideo } from "./SceneVideo";
import { TransitionEffect } from "./TransitionEffect";
import { VisualizationRenderer } from "./VisualizationRenderer";
import { MapSceneRenderer } from "../map/MapSceneRenderer";
import { resolveAsset } from "../utils/resolveAsset";
import type { SceneEntry } from "../types/manifest";

interface Props {
  scenes: SceneEntry[];
  fps: number;
}

export const SceneSequencer: React.FC<Props> = ({ scenes, fps }) => {
  let frameOffset = 0;

  return (
    <AbsoluteFill>
      {scenes.map((scene, index) => {
        const durationInFrames = Math.ceil(scene.audioDurationSec * fps);
        const from = frameOffset;
        frameOffset += durationInFrames;

        const hasVideo = !!scene.trailerVideoPath;

        return (
          <Sequence
            key={scene.sceneNumber}
            from={from}
            durationInFrames={durationInFrames}
            layout="none"
          >
            <AbsoluteFill>
              <TransitionEffect
                type={scene.transition.type}
                durationFrames={scene.transition.durationFrames}
                totalFrames={durationInFrames}
                easing={scene.transition.easing}
              >
                {hasVideo ? (
                  <SceneVideo
                    src={scene.trailerVideoPath!}
                    startFrom={scene.trailerClip?.startSec ?? 0}
                    endAt={scene.trailerClip?.endSec}
                    durationInFrames={durationInFrames}
                    fps={fps}
                  />
                ) : scene.mapScene ? (
                  <MapSceneRenderer
                    data={scene.mapScene}
                    durationInFrames={durationInFrames}
                    fps={fps}
                  />
                ) : scene.visualization ? (
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

              {scene.audioPath ? <Audio src={resolveAsset(scene.audioPath)} /> : null}
            </AbsoluteFill>
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
