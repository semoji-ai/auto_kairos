import React, { useCallback, useState } from "react";
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  delayRender,
  continueRender,
  staticFile,
} from "remotion";
const resolveAsset = (p: string) => p.startsWith("http") ? p : staticFile(p);
import type maplibregl from "maplibre-gl";
import type { MapSceneData, TerritoryData } from "../types/manifest";
import { interpolateCamera, type CameraState } from "./cameraInterpolation";
import { RemotionMap } from "./RemotionMap";
import { PrerenderedMapBg } from "./PrerenderedMapBg";
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
 * 렌더링 모드:
 * 1. prerenderedBg: 정적 스크린샷 (영역 포함) + HTML 오버레이
 *    - 프리렌더 스크립트가 MapLibre에 영역 GeoJSON을 추가한 뒤 캡처
 *    - 영역 fade-in은 전체 이미지 opacity로 대체
 * 2. RemotionMap: MapLibre 실시간 렌더링 (폴백)
 */
export const TerritoryOverlay: React.FC<Props> = ({
  data,
  durationInFrames,
  fps,
}) => {
  const frame = useCurrentFrame();

  const keyframes = data.camera?.keyframes ?? [];
  if (keyframes.length === 0) return null;
  const camera: CameraState = interpolateCamera(
    frame,
    keyframes,
    data.camera?.easing,
  );

  const territories = data.territories ?? [];

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

  /* ── prerenderedBg 모드: 영역이 포함된 스크린샷 ── */
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
          {overlays(captureCam)}
        </PrerenderedMapBg>
        <AtmosphereOverlay />
        <MapTitleOverlay title={data.title} source={data.source} />
      </AbsoluteFill>
    );
  }

  /* ── RemotionMap 실시간 렌더링 (폴백) ── */

  // GeoJSON 로딩 (파일 경로가 있는 경우)
  const [loadedGeoJSON, setLoadedGeoJSON] = useState<
    Record<number, GeoJSON.FeatureCollection>
  >({});
  const [loadHandle] = useState(() => {
    const hasExternalFiles = territories.some((t) => t.geojsonPath && !t.geojsonInline);
    return hasExternalFiles ? delayRender("Loading GeoJSON files") : null;
  });

  React.useEffect(() => {
    const loadFiles = async () => {
      const loaded: Record<number, GeoJSON.FeatureCollection> = {};
      for (let i = 0; i < territories.length; i++) {
        const t = territories[i];
        if (t.geojsonPath && !t.geojsonInline) {
          try {
            const url = resolveAsset(t.geojsonPath);
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

          map.addLayer({
            id: fillLayerId,
            type: "fill",
            source: sourceId,
            paint: {
              "fill-color": territory.fillColor,
              "fill-opacity": 0,
            },
          });

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
