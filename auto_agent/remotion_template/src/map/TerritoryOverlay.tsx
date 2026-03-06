import React, { useCallback, useState } from "react";
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  delayRender,
  continueRender,
  staticFile,
} from "remotion";
import type maplibregl from "maplibre-gl";
import type { MapSceneData, TerritoryData } from "../types/manifest";
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

/**
 * TerritoryOverlay — 영역 변화 씬
 *
 * GeoJSON 폴리곤이 점진적으로 fade-in되어 영역을 표시.
 * 여러 영역을 시간차로 표시 가능.
 *
 * 예: 고구려 최대 영토, 조선 8도 등
 */
export const TerritoryOverlay: React.FC<Props> = ({
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

  const territories = data.territories ?? [];

  // GeoJSON 로딩 (파일 경로가 있는 경우)
  const [loadedGeoJSON, setLoadedGeoJSON] = useState<
    Record<number, GeoJSON.FeatureCollection>
  >({});
  const [loadHandle] = useState(() => {
    const hasExternalFiles = territories.some((t) => t.geojsonPath && !t.geojsonInline);
    return hasExternalFiles ? delayRender("Loading GeoJSON files") : null;
  });

  // 외부 GeoJSON 파일 로딩
  React.useEffect(() => {
    const loadFiles = async () => {
      const loaded: Record<number, GeoJSON.FeatureCollection> = {};
      for (let i = 0; i < territories.length; i++) {
        const t = territories[i];
        if (t.geojsonPath && !t.geojsonInline) {
          try {
            const url = staticFile(t.geojsonPath);
            const res = await fetch(url);
            loaded[i] = await res.json();
          } catch (err) {
            console.error(`GeoJSON load failed: ${t.geojsonPath}`, err);
          }
        }
      }
      setLoadedGeoJSON(loaded);
      if (loadHandle) continueRender(loadHandle);
    };
    loadFiles();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // 맵 로드 시 레이어 추가
  const handleMapReady = useCallback(
    (map: maplibregl.Map) => {
      territories.forEach((territory, i) => {
        const sourceId = `territory-source-${i}`;
        const fillLayerId = `territory-fill-${i}`;
        const lineLayerId = `territory-line-${i}`;

        const geojson = territory.geojsonInline ?? loadedGeoJSON[i];
        if (!geojson) return;

        if (!map.getSource(sourceId)) {
          map.addSource(sourceId, {
            type: "geojson",
            data: geojson as GeoJSON.GeoJSON,
          });

          // 채우기 레이어
          map.addLayer({
            id: fillLayerId,
            type: "fill",
            source: sourceId,
            paint: {
              "fill-color": territory.fillColor,
              "fill-opacity": 0, // 초기 투명 → 프레임별 업데이트
            },
          });

          // 경계선 레이어
          if (territory.strokeColor) {
            map.addLayer({
              id: lineLayerId,
              type: "line",
              source: sourceId,
              paint: {
                "line-color": territory.strokeColor,
                "line-width": 2,
                "line-opacity": 0,
              },
            });
          }
        }
      });
    },
    [loadedGeoJSON], // eslint-disable-line react-hooks/exhaustive-deps
  );

  // 매 프레임 투명도 업데이트
  const handleFrameUpdate = useCallback(
    (map: maplibregl.Map) => {
      territories.forEach((territory, i) => {
        const fillLayerId = `territory-fill-${i}`;
        const lineLayerId = `territory-line-${i}`;

        const appearAt = territory.appearAtFrame ?? 0;
        const fadeIn = territory.fadeInFrames ?? 20;

        const opacity = interpolate(
          frame,
          [appearAt, appearAt + fadeIn],
          [0, territory.fillOpacity],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
        );

        if (map.getLayer(fillLayerId)) {
          map.setPaintProperty(fillLayerId, "fill-opacity", opacity);
        }
        if (map.getLayer(lineLayerId)) {
          map.setPaintProperty(
            lineLayerId,
            "line-opacity",
            Math.min(opacity * 2, 1),
          );
        }
      });
    },
    [frame], // eslint-disable-line react-hooks/exhaustive-deps
  );

  const styleConfig = resolveMapStyle(data.mapStyle);
  const isD3 = styleConfig.renderer === "d3";

  // D3: 영역 투명도 계산
  const d3Territories = isD3
    ? territories.map((territory) => {
        const appearAt = territory.appearAtFrame ?? 0;
        const fadeIn = territory.fadeInFrames ?? 20;
        const opacity = interpolate(
          frame,
          [appearAt, appearAt + fadeIn],
          [0, 1],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
        );
        return { data: territory, opacity };
      })
    : undefined;

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
          territories={d3Territories}
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
