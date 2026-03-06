import React, { useState, useEffect } from "react";
import { AbsoluteFill, Img, useCurrentFrame, interpolate, Easing, staticFile } from "remotion";
import type { MapSceneData } from "../types/manifest";
import type { CameraState } from "./cameraInterpolation";
import { MapBase } from "./MapBase";
import { MarkerOverlay, LabelOverlay } from "./MapOverlays";

interface Props {
  data: MapSceneData;
  durationInFrames: number;
  fps: number;
}

/**
 * LocationReveal — 위치 표시 씬
 *
 * 프리렌더 모드: map_frames/scene_N/frame_XXXX.png → <Img>로 배경 표시
 * 폴백 모드: MapBase(MapLibre/D3) 실시간 렌더링
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
  const kfs = data.camera.keyframes;
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

  // 프리렌더 프레임 경로 (mapScene.prerenderedFramesDir이 있으면 사용)
  const framesDir = data.prerenderedFramesDir;
  const usePrerendered = !!framesDir;

  // 현재 프레임 이미지 경로
  const frameImagePath = usePrerendered
    ? `${framesDir}/frame_${String(frame).padStart(4, "0")}.png`
    : null;

  return (
    <AbsoluteFill>
      {usePrerendered && frameImagePath ? (
        /* ── 프리렌더 모드: PNG 이미지 배경 ── */
        <>
          <Img
            src={staticFile(frameImagePath)}
            style={{
              width: 1920,
              height: 1080,
              objectFit: "cover",
              filter: "brightness(1.6)",
            }}
          />
          {/* 마커/라벨 오버레이 — 프리렌더 이미지 위에 HTML로 합성 */}
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
            {zoomDone && data.markers && (
              <MarkerOverlay
                markers={data.markers.map((m, i) => ({
                  ...m,
                  appearAtFrame: ZOOM_FRAMES + i * MARKER_STAGGER,
                }))}
                camera={camera}
                width={1920}
                height={1080}
              />
            )}
            {zoomDone && data.labels && (
              <LabelOverlay
                labels={data.labels}
                camera={camera}
                width={1920}
                height={1080}
              />
            )}
          </div>
        </>
      ) : (
        /* ── 폴백 모드: MapBase 실시간 렌더링 ── */
        <MapBase
          mapStyle={data.mapStyle}
          cameraState={camera}
          width={1920}
          height={1080}
        >
          {zoomDone && data.markers && (
            <MarkerOverlay
              markers={data.markers.map((m, i) => ({
                ...m,
                appearAtFrame: ZOOM_FRAMES + i * MARKER_STAGGER,
              }))}
              camera={camera}
              width={1920}
              height={1080}
            />
          )}
          {zoomDone && data.labels && (
            <LabelOverlay
              labels={data.labels}
              camera={camera}
              width={1920}
              height={1080}
            />
          )}
        </MapBase>
      )}
    </AbsoluteFill>
  );
};
