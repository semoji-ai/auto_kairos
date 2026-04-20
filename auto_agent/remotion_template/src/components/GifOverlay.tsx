import React from "react";
import { Gif } from "@remotion/gif";
import { useCurrentFrame, interpolate } from "remotion";
import { resolveOverlayPath } from "../overlays/resolveOverlay";
import type { OverlayItem } from "../types/manifest";

interface Props {
  overlay: OverlayItem;
  durationInFrames: number;
}

const POSITION_CLASSES: Record<string, string> = {
  "top-left": "top-[5%] left-[5%]",
  "top-right": "top-[5%] right-[5%]",
  "bottom-left": "bottom-[20%] left-[5%]",
  "bottom-right": "bottom-[20%] right-[5%]",
  "bottom-center": "bottom-[20%] left-1/2 -translate-x-1/2",
  center: "top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2",
};

export const GifOverlay: React.FC<Props> = ({ overlay, durationInFrames }) => {
  const frame = useCurrentFrame();
  const src = resolveOverlayPath("gif", overlay.assetId);

  if (!src) {
    console.warn(`[GifOverlay] asset not found: ${overlay.assetId}`);
    return null;
  }

  const enter = overlay.enterFrame ?? 0;
  const exit = overlay.exitFrame ?? durationInFrames;
  const fadeIn = interpolate(frame, [enter, enter + 10], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fadeOut = interpolate(frame, [exit - 10, exit], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const opacity = Math.min(fadeIn, fadeOut) * (overlay.opacity ?? 1);

  if (frame < enter || frame > exit) return null;

  const scale = overlay.scale ?? 1;
  const posClass =
    overlay.position === "custom"
      ? ""
      : POSITION_CLASSES[overlay.position] ?? "";

  return (
    <div
      className={`absolute pointer-events-none ${posClass}`}
      style={{
        opacity,
        transform: `scale(${scale})`,
        ...(overlay.position === "custom"
          ? { left: overlay.x, top: overlay.y }
          : {}),
      }}
    >
      <Gif
        src={src}
        width={200}
        height={200}
        fit="contain"
        loopBehavior={overlay.loop !== false ? "loop" : "pause-after-finish"}
      />
    </div>
  );
};
