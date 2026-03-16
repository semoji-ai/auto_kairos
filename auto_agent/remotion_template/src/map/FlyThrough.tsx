import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import type { MapSceneData } from "../types/manifest";
import { interpolateCamera, type CameraState } from "./cameraInterpolation";
import { MapBase } from "./MapBase";
import { PrerenderedMapBg } from "./PrerenderedMapBg";
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
 * 렌더링 모드:
 * 1. prerenderedBg: 정적 스크린샷 배경 (카메라 최종 위치 기준)
 * 2. MapBase: MapLibre 실시간 렌더링 (폴백)
 *
 * 여러 카메라 키프레임을 따라 자유롭게 이동.
 * 줌/bearing/pitch 동시 보간으로 cinematic 카메라 워크 구현.
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

  /* ── prerenderedBg 모드: 정적 스크린샷 배경 ── */
  if (data.prerenderedBg) {
    const bg = data.prerenderedBg;
    const captureCam: CameraState = {
      center: bg.cameraState.center,
      zoom: bg.cameraState.zoom,
      bearing: bg.cameraState.bearing,
      pitch: bg.cameraState.pitch,
    };

    return (
      <AbsoluteFill>
        <PrerenderedMapBg
          imagePath={bg.imagePath}
          captureCamera={captureCam}
          width={1920}
          height={1080}
        >
          {data.markers && (
            <MarkerOverlay markers={data.markers} camera={captureCam} width={1920} height={1080} />
          )}
          {data.labels && (
            <LabelOverlay labels={data.labels} camera={captureCam} width={1920} height={1080} />
          )}
        </PrerenderedMapBg>
        <AtmosphereOverlay />
        <MapTitleOverlay title={data.title} source={data.source} />
      </AbsoluteFill>
    );
  }

  /* ── MapBase 실시간 렌더링 (폴백) ── */
  return (
    <AbsoluteFill>
      <MapBase
        mapStyle={data.mapStyle}
        cameraState={camera}
        width={1920}
        height={1080}
      >
        {data.markers && (
          <MarkerOverlay markers={data.markers} camera={camera} width={1920} height={1080} />
        )}
        {data.labels && (
          <LabelOverlay labels={data.labels} camera={camera} width={1920} height={1080} />
        )}
      </MapBase>
      <AtmosphereOverlay />
      <MapTitleOverlay title={data.title} source={data.source} />
    </AbsoluteFill>
  );
};
