import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import type { MapSceneData } from "../types/manifest";
import { interpolateCamera, type CameraState } from "./cameraInterpolation";
import { MapBase } from "./MapBase";
import { MarkerOverlay, LabelOverlay, MapTitleOverlay } from "./MapOverlays";
import { AtmosphereOverlay } from "./AtmosphereOverlay";

interface Props {
  data: MapSceneData;
  durationInFrames: number;
  fps: number;
}

/**
 * FlyThrough — 카메라 플라이스루 씬
 *
 * 여러 카메라 키프레임을 따라 자유롭게 이동.
 * 줌/bearing/pitch 동시 보간으로 cinematic 카메라 워크 구현.
 *
 * 예: 챕터 전환 시 서울 → 영월 → 청령포 순차 이동
 */
export const FlyThrough: React.FC<Props> = ({
  data,
  durationInFrames,
  fps,
}) => {
  const frame = useCurrentFrame();

  const camera: CameraState = interpolateCamera(
    frame,
    data.camera.keyframes,
    data.camera.easing,
  );

  return (
    <AbsoluteFill>
      <MapBase
        mapStyle={data.mapStyle}
        cameraState={camera}
        width={1920}
        height={1080}
      >
        {data.markers && (
          <MarkerOverlay
            markers={data.markers}
            camera={camera}
            width={1920}
            height={1080}
          />
        )}
        {data.labels && (
          <LabelOverlay
            labels={data.labels}
            camera={camera}
            width={1920}
            height={1080}
          />
        )}
      </MapBase>
      <AtmosphereOverlay />
      <MapTitleOverlay title={data.title} source={data.source} />
    </AbsoluteFill>
  );
};
