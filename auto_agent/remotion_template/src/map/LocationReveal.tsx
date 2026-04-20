import React from "react";
import { AbsoluteFill, Img, useCurrentFrame, interpolate, Easing, staticFile } from "remotion";
const resolveAsset = (p: string) => p.startsWith("http") ? p : staticFile(p);
import type { MapSceneData } from "../types/manifest";
import type { CameraState } from "./cameraInterpolation";
import { MapBase } from "./MapBase";
import { PrerenderedMapBg } from "./PrerenderedMapBg";
import { MarkerOverlay, LabelOverlay } from "./MapOverlays";

interface Props {
  data: MapSceneData;
  durationInFrames: number;
  fps: number;
}

/**
 * LocationReveal — 위치 표시 씬
 *
 * 렌더링 모드 (우선순위):
 * 1. prerenderedBg: 단일 스크린샷 배경 + HTML 오버레이 (권장)
 * 2. prerenderedFramesDir: 프레임 시퀀스 PNG (레거시)
 * 3. MapBase: MapLibre 실시간 렌더링 (폴백)
 *
 * 15프레임 ease(0.8,0,0.2,1) 줌 → 줌 완료 후 마커 stagger 등장
 */

const ZOOM_FRAMES = 15;
const MARKER_STAGGER = 5;
const ZOOM_EASING = Easing.bezier(0.8, 0, 0.2, 1);

export const LocationReveal: React.FC<Props> = ({
  data,
  durationInFrames,
  fps,
}) => {
  const frame = useCurrentFrame();
  const kfs = data.camera?.keyframes ?? [];
  if (kfs.length === 0) return null;
  const start = kfs[0];
  const end = kfs[kfs.length - 1] ?? start;

  // ease(0.8,0,0.2,1)로 줌 진행률 계산
  const t = interpolate(frame, [0, ZOOM_FRAMES], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: ZOOM_EASING,
  });

  const camera: CameraState = start
    ? {
        center: [
          start.center[0] + (end.center[0] - start.center[0]) * t,
          start.center[1] + (end.center[1] - start.center[1]) * t,
        ],
        zoom: start.zoom + (end.zoom - start.zoom) * t,
        bearing: (start.bearing ?? 0) + ((end.bearing ?? 0) - (start.bearing ?? 0)) * t,
        pitch: (start.pitch ?? 0) + ((end.pitch ?? 0) - (start.pitch ?? 0)) * t,
      }
    : { center: [53, 32] as [number, number], zoom: 5, bearing: 0, pitch: 0 };

  // 줌 완료 후 마커/라벨 표시
  const zoomDone = frame >= ZOOM_FRAMES;

  // 마커/라벨 오버레이 (공통)
  const renderOverlays = (cam: CameraState) => (
    <>
      {zoomDone && data.markers && (
        <MarkerOverlay
          markers={data.markers.map((m, i) => ({
            ...m,
            appearAtFrame: ZOOM_FRAMES + i * MARKER_STAGGER,
          }))}
          camera={cam}
          width={1920}
          height={1080}
        />
      )}
      {zoomDone && data.labels && (
        <LabelOverlay
          labels={data.labels}
          camera={cam}
          width={1920}
          height={1080}
        />
      )}
    </>
  );

  /* ── 모드 1: prerenderedBg (단일 스크린샷) ── */
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
          {renderOverlays(captureCam)}
        </PrerenderedMapBg>
      </AbsoluteFill>
    );
  }

  /* ── 모드 2: prerenderedFramesDir (프레임 시퀀스, 레거시) ── */
  if (data.prerenderedFramesDir) {
    const frameImagePath = `${data.prerenderedFramesDir}/frame_${String(frame).padStart(4, "0")}.png`;

    return (
      <AbsoluteFill>
        <Img
          src={resolveAsset(frameImagePath)}
          style={{
            width: 1920,
            height: 1080,
            objectFit: "cover",
            filter: "brightness(1.6)",
          }}
        />
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: 1920,
            height: 1080,
            pointerEvents: "none",
          }}
        >
          {renderOverlays(camera)}
        </div>
      </AbsoluteFill>
    );
  }

  /* ── 모드 3: MapBase 실시간 렌더링 (폴백) ── */
  return (
    <AbsoluteFill>
      <MapBase
        mapStyle={data.mapStyle}
        cameraState={camera}
        width={1920}
        height={1080}
      >
        {renderOverlays(camera)}
      </MapBase>
    </AbsoluteFill>
  );
};
