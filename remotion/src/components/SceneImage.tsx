import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame, interpolate } from "remotion";
import { resolveEasing } from "../utils/easingMap";
import type { KenBurnsConfig } from "../types/manifest";

interface Props {
  src: string;
  kenBurns: KenBurnsConfig;
  durationInFrames: number;
  imageMode?: "cover" | "contain";
}

const REFERENCE_GRID_BG = staticFile("assets/reference_grid_bg.jpg");

export const SceneImage: React.FC<Props> = ({
  src,
  kenBurns,
  durationInFrames,
  imageMode = "cover",
}) => {
  const frame = useCurrentFrame();
  const easingFn = resolveEasing(kenBurns.easing);

  const zoomStart = kenBurns.zoomDirection === "out" ? kenBurns.zoomFactor : 1;
  const zoomEnd = kenBurns.zoomDirection === "out" ? 1 : kenBurns.zoomFactor;

  const scale = kenBurns.enabled
    ? interpolate(frame, [0, durationInFrames], [zoomStart, zoomEnd], {
        extrapolateRight: "clamp",
        easing: easingFn,
      })
    : 1;

  const panX = kenBurns.panX ?? 0;
  const panY = kenBurns.panY ?? 0;
  const tx =
    kenBurns.enabled && panX !== 0
      ? interpolate(frame, [0, durationInFrames], [0, panX], {
          extrapolateRight: "clamp",
          easing: easingFn,
        })
      : 0;
  const ty =
    kenBurns.enabled && panY !== 0
      ? interpolate(frame, [0, durationInFrames], [0, panY], {
          extrapolateRight: "clamp",
          easing: easingFn,
        })
      : 0;

  let originX = "center";
  let originY = "center";
  const pd = kenBurns.panDirection;
  if (pd === "left") originX = "left";
  else if (pd === "right") originX = "right";
  else if (pd === "up") originY = "top";
  else if (pd === "down") originY = "bottom";

  if (!src) {
    return (
      <AbsoluteFill style={{ backgroundColor: "#111" }} />
    );
  }

  // 레퍼런스 이미지: 그리드 배경 + 원본 비율 유지 (최대 크기)
  if (imageMode === "contain") {
    return (
      <AbsoluteFill>
        <Img
          src={REFERENCE_GRID_BG}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            position: "absolute",
          }}
        />
        <AbsoluteFill
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "3%",
          }}
        >
          <Img
            src={src}
            style={{
              maxWidth: "100%",
              maxHeight: "100%",
              objectFit: "contain",
              borderRadius: 8,
              boxShadow: "0 8px 40px rgba(0,0,0,0.12)",
              transform: `scale(${scale})`,
              transformOrigin: "center center",
            }}
          />
        </AbsoluteFill>
      </AbsoluteFill>
    );
  }

  return (
    <AbsoluteFill>
      <Img
        src={src}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `scale(${scale}) translate(${tx}%, ${ty}%)`,
          transformOrigin: `${originX} ${originY}`,
        }}
      />
    </AbsoluteFill>
  );
};
