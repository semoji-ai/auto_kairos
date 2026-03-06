import React, { useCallback } from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import * as turf from "@turf/turf";
import type maplibregl from "maplibre-gl";
import type { MapSceneData } from "../types/manifest";
import { interpolateCamera, type CameraState } from "./cameraInterpolation";
import { resolveMapStyle } from "./mapStyles";
import { RemotionMap } from "./RemotionMap";
import { MapBase } from "./MapBase";
import { MarkerOverlay, LabelOverlay, MapTitleOverlay } from "./MapOverlays";
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
 * 출발지에서 도착지까지 경로가 점진적으로 그려지는 애니메이션.
 * Turf.js lineSliceAlong()으로 프레임별 가시 경로를 계산.
 *
 * 예: 한양→영월 유배 경로가 프레임별로 그려짐
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
  if (!route || route.coordinates.length < 2) {
    return (
      <AbsoluteFill>
        <MapBase mapStyle={data.mapStyle} cameraState={camera} />
        <MapTitleOverlay title={data.title} source={data.source} />
      </AbsoluteFill>
    );
  }

  // 전체 경로 GeoJSON LineString
  const fullLine = turf.lineString(route.coordinates);
  const totalLength = turf.length(fullLine, { units: "kilometers" });

  // 경로 그리기 시작/끝 프레임
  const drawStart = 15; // 카메라 안정화 후 시작
  const drawDuration = route.drawDurationFrames ?? Math.floor(durationInFrames * 0.6);
  const drawEnd = drawStart + drawDuration;

  // 현재 진행률
  const progress = interpolate(frame, [drawStart, drawEnd], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const currentLength = totalLength * progress;

  // 가시 경로 계산
  let visibleCoords: [number, number][];
  if (progress <= 0) {
    visibleCoords = [route.coordinates[0]];
  } else if (progress >= 1) {
    visibleCoords = route.coordinates;
  } else {
    const sliced = turf.lineSliceAlong(fullLine, 0, currentLength, {
      units: "kilometers",
    });
    visibleCoords = sliced.geometry.coordinates as [number, number][];
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

  // 맵 로드 시 레이어 추가
  const handleMapReady = useCallback(
    (map: maplibregl.Map) => {
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
    },
    [], // eslint-disable-line react-hooks/exhaustive-deps
  );

  // 매 프레임 GeoJSON 데이터 업데이트
  const handleFrameUpdate = useCallback(
    (map: maplibregl.Map) => {
      const source = map.getSource(ROUTE_SOURCE_ID) as maplibregl.GeoJSONSource | undefined;
      if (source) {
        source.setData(visibleGeoJSON);
      }
    },
    [frame], // eslint-disable-line react-hooks/exhaustive-deps
  );

  const styleConfig = resolveMapStyle(data.mapStyle);
  const isD3 = styleConfig.renderer === "d3";

  const overlays = (
    <>
      {data.markers && (
        <MarkerOverlay markers={data.markers} camera={camera} width={1920} height={1080} />
      )}
      {data.labels && (
        <LabelOverlay labels={data.labels} camera={camera} width={1920} height={1080} />
      )}
    </>
  );

  return (
    <AbsoluteFill>
      {isD3 ? (
        <MapBase
          mapStyle={data.mapStyle}
          cameraState={camera}
          route={{ data: route, progress }}
          width={1920}
          height={1080}
        >
          {overlays}
        </MapBase>
      ) : (
        <RemotionMap
          mapStyle={data.mapStyle}
          cameraState={camera}
          onMapReady={handleMapReady}
          onFrameUpdate={handleFrameUpdate}
          width={1920}
          height={1080}
        >
          {overlays}
        </RemotionMap>
      )}
      <AtmosphereOverlay />
      <MapTitleOverlay title={data.title} source={data.source} />
    </AbsoluteFill>
  );
};
