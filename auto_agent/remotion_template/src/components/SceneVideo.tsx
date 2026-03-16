import React from "react";
import { AbsoluteFill, OffthreadVideo, staticFile } from "remotion";
const resolveAsset = (p: string) => p.startsWith("http") ? p : staticFile(p);

interface Props {
  src: string;
  startFrom?: number;
  endAt?: number;
  durationInFrames: number;
  fps: number;
}

export const SceneVideo: React.FC<Props> = ({
  src,
  startFrom = 0,
  endAt,
  durationInFrames,
  fps,
}) => {
  const startFromFrame = Math.round(startFrom * fps);

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <OffthreadVideo
        src={resolveAsset(src)}
        startFrom={startFromFrame}
        endAt={endAt ? Math.round(endAt * fps) : undefined}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
        }}
        volume={0}
      />
    </AbsoluteFill>
  );
};
