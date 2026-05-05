import React, { useCallback, useMemo } from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import * as turf from "@turf/turf";
import type maplibregl from "maplibre-gl";
import type { MapSceneData } from "../types/manifest";
import { interpolateCamera, type CameraState } from "./cameraInterpolation";
import { RemotionMap } from "./RemotionMap";
import { PrerenderedMapBg } from "./PrerenderedMapBg";
import { MarkerOverlay, LabelOverlay, MapTitleOverlay, lngLatToPixel } from "./MapOverlays";
import { AtmosphereOverlay } from "./AtmosphereOverlay";

interface Props {
  data: MapSceneData;
  durationInFrames: number;
  fps: number;
}

const ROUTE_SOURCE_ID = "route-source";
const ROUTE_LAYER_ID = "route-layer";

/**
 * RouteAnimation — 경로 애니메이션 씬
 *
 * 렌더링 모드:
 * 1. prerenderedBg: 정적 스크린샷 배경 + SVG 경로 오버레이
 * 2. RemotionMap: MapLibre 실시간 렌더링 (폴백)
 *
 * 출발지에서 도착지까지 경로가 점진적으로 그려지는 애니메이션.
 * Turf.js lineSliceAlong()으로 프레임별 가시 경로를 계산.
 */
export const RouteAnimation: React.FC<Props> = ({
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

  const route = data.route;

  // 경로 그리기 진행률 계산
  const drawStart = 15;
  const drawDuration = route?.drawDurationFrames ?? Math.floor(durationInFrames * 0.6);
  const drawEnd = drawStart + drawDuration;
  const progress = interpolate(frame, [drawStart, drawEnd], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // 가시 경로 좌표 계산 (Turf.js)
  const visibleCoords = useMemo(() => {
    if (!route || !route.coordinates || route.coordinates.length < 2) return [];
    const fullLine = turf.lineString(route.coordinates);
    const totalLength = turf.length(fullLine, { units: "kilometers" });

    if (progress <= 0) return [route.coordinates[0]];
    if (progress >= 1) return route.coordinates;

    const sliced = turf.lineSliceAlong(fullLine, 0, totalLength * progress, {
      units: "kilometers",
    });
    return sliced.geometry.coordinates as [number, number][];
  }, [route, progress]);

  const overlays = (cam: CameraState) => (
    <>
      {data.markers && (
        <MarkerOverlay markers={data.markers} camera={cam} width={1920} height={1080} />
      )}
      {data.labels && (
        <LabelOverlay labels={data.labels} camera={cam} width={1920} height={1080} />
      )}
    </>
  );

  /* ── prerenderedBg 모드: 정적 배경 + SVG 경로 오버레이 ── */
  if (data.prerenderedBg) {
    const bg = data.prerenderedBg;
    const captureCam: CameraState = {
      center: bg.cameraState.center,
      zoom: bg.cameraState.zoom,
      bearing: bg.cameraState.bearing,
      pitch: bg.cameraState.pitch,
    };

    // 경로 좌표 → 픽셀 좌표 변환 (캡처 카메라 기준)
    const pixelCoords = visibleCoords.map((coord) =>
      lngLatToPixel(coord as [number, number], captureCam, 1920, 1080),
    );
    const pathD =
      pixelCoords.length > 1
        ? pixelCoords.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ")
        : "";

    return (
      <AbsoluteFill>
        <PrerenderedMapBg
          imagePath={bg.imagePath}
          captureCamera={captureCam}
          width={1920}
          height={1080}
        >
          {/* SVG 경로 오버레이 */}
          {pathD && (
            <svg
              width={1920}
              height={1080}
              style={{ position: "absolute", top: 0, left: 0, pointerEvents: "none" }}
            >
              <path
                d={pathD}
                fill="none"
                stroke={route?.color ?? "#FF6B6B"}
                strokeWidth={route?.width ?? 5}
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeOpacity={0.9}
              />
            </svg>
          )}
          {overlays(captureCam)}
        </PrerenderedMapBg>
        <AtmosphereOverlay />
        <MapTitleOverlay title={data.title} source={data.source} />
      </AbsoluteFill>
    );
  }

  /* ── RemotionMap 실시간 렌더링 (폴백) ── */
  if (!route || !route.coordinates || route.coordinates.length < 2) {
    return (
      <AbsoluteFill>
        <RemotionMap mapStyle={data.mapStyle} cameraState={camera} width={1920} height={1080}>
          {overlays(camera)}
        </RemotionMap>
        <MapTitleOverlay title={data.title} source={data.source} />
      </AbsoluteFill>
    );
  }

  const visibleGeoJSON: GeoJSON.FeatureCollection = {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        properties: {},
        geometry: {
          type: "LineString",
          coordinates: visibleCoords,
        },
      },
    ],
  };

  const handleMapReady = (map: maplibregl.Map) => {
    if (!map.getSource(ROUTE_SOURCE_ID)) {
      map.addSource(ROUTE_SOURCE_ID, {
        type: "geojson",
        data: visibleGeoJSON,
      });
      map.addLayer({
        id: ROUTE_LAYER_ID,
        type: "line",
        source: ROUTE_SOURCE_ID,
        paint: {
          "line-color": route.color ?? "#FF6B6B",
          "line-width": route.width ?? 5,
          "line-opacity": 0.9,
        },
        layout: {
          "line-cap": "round",
          "line-join": "round",
        },
      });
    }
  };

  const handleFrameUpdate = (map: maplibregl.Map) => {
    const source = map.getSource(ROUTE_SOURCE_ID) as maplibregl.GeoJSONSource | undefined;
    if (source) {
      source.setData(visibleGeoJSON);
    }
  };

  return (
    <AbsoluteFill>
      <RemotionMap
        mapStyle={data.mapStyle}
        cameraState={camera}
        onMapReady={handleMapReady}
        onFrameUpdate={handleFrameUpdate}
        width={1920}
        height={1080}
      >
        {overlays(camera)}
      </RemotionMap>
      <AtmosphereOverlay />
      <MapTitleOverlay title={data.title} source={data.source} />
    </AbsoluteFill>
  );
};
