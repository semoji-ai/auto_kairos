import React from "react";
import { AbsoluteFill, Video } from "remotion";

interface Props {
  src: string;
  opacity: number;
  blendMode: string;
}

export const TextureOverlay: React.FC<Props> = ({
  src,
  opacity,
  blendMode,
}) => {
  return (
    <AbsoluteFill
      style={{
        mixBlendMode: blendMode as React.CSSProperties["mixBlendMode"],
        opacity,
      }}
    >
      <Video
        src={src}
        loop
        muted
        style={{ width: "100%", height: "100%", objectFit: "cover" }}
      />
    </AbsoluteFill>
  );
};
