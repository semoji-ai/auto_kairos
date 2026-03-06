import React from "react";
import { Audio } from "remotion";
import type { BGMConfig } from "../types/manifest";
import { resolveAsset } from "../utils/resolveAsset";

interface Props {
  config: BGMConfig;
}

export const BGMLayer: React.FC<Props> = ({ config }) => {
  const src = resolveAsset(config.path);
  if (!src) return null;

  return (
    <Audio
      src={src}
      volume={config.volume}
      loop={config.loop}
    />
  );
};
