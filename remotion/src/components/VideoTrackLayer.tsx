import React from "react";
import {AbsoluteFill, OffthreadVideo, Sequence, staticFile, useCurrentFrame, useVideoConfig} from "remotion";
import type {VideoTrackClip} from "../types/manifest";

export const activeTrack = (clips: VideoTrackClip[] = [], frame: number) =>
  clips.find(c => frame >= c.timelineStartFrame && frame < c.timelineStartFrame + c.timelineDurationFrames);

const url = (p: string) => /^(https?:\/\/|\/)/.test(p) ? p : staticFile(p);

export const TrackSource: React.FC<{scene: any}> = ({scene}) => {
  const text = scene?.attribution || scene?.visualization?.source || scene?.source;
  return text ? <div style={{position: "absolute", bottom: 16, right: 40, fontSize: 22,
    color: scene?.attributionStatus === "negotiate" ? "#ff3b30" : "white",
    textShadow: "0 1px 3px black", zIndex: 2}}>
    {scene?.attributionStatus === "negotiate" ? "협의 필요 · " : "출처: "}{text}
  </div> : null;
};

/** One Sequence per clip, never per scene: source time cannot restart at a scene boundary. */
export const VideoTrackLayer: React.FC<{clips?: VideoTrackClip[]; scene?: any}> = ({clips = [], scene}) => {
  const {fps} = useVideoConfig();
  const frame = useCurrentFrame();
  return <AbsoluteFill style={{zIndex: 1, pointerEvents: "none"}}>
    {clips.map(c => <Sequence key={c.clipId} from={c.timelineStartFrame}
      durationInFrames={c.timelineDurationFrames} premountFor={fps}>
      <OffthreadVideo src={url(c.sourcePath)} startFrom={Math.round(c.sourceIn * fps)}
        endAt={Math.round(c.sourceOut * fps)} muted volume={0}
        style={{width: "100%", height: "100%", objectFit: "contain", backgroundColor: "black"}} />
    </Sequence>)}
    {activeTrack(clips, frame) && <TrackSource scene={scene} />}
  </AbsoluteFill>;
};
