import React from "react";
import type maplibregl from "maplibre-gl";
import type { CameraState } from "./cameraInterpolation";
import type { RouteData, TerritoryData } from "../types/manifest";
import { resolveMapStyle } from "./mapStyles";
import { RemotionMap } from "./RemotionMap";
import { D3MapRenderer } from "./D3MapRenderer";

/**
 * MapBase — MapLibre/D3 통합 맵 렌더러
 *
 * mapStyle 프리셋에 따라 자동으로 렌더러를 선택:
 * - "modern_clean", "historical", "dark_cyber" → MapLibre (벡터 타일)
 * - "vintage_parchment", "minimal_light", "dark_elegant", "blueprint", "warm_earth" → D3 (SVG)
 *
 * 씬 컴포넌트(LocationReveal, RouteAnimation 등)는 이 컴포넌트만 사용하면 됨.
 */

interface MapBaseProps {
  /** 맵 스타일 프리셋명 */
  mapStyle?: string;
  /** 카메라 상태 */
  cameraState: CameraState;
  /** MapLibre: 맵 로드 콜백 */
  onMapReady?: (map: maplibregl.Map) => void;
  /** MapLibre: 프레임 업데이트 콜백 */
  onFrameUpdate?: (map: maplibregl.Map) => void;
  /** D3: 경로 렌더링 */
  route?: {
    data: RouteData;
    progress: number;
  };
  /** D3: 영역 렌더링 */
  territories?: {
    data: TerritoryData;
    opacity: number;
  }[];
  width?: number;
  height?: number;
  children?: React.ReactNode;
}

export const MapBase: React.FC<MapBaseProps> = ({
  mapStyle,
  cameraState,
  onMapReady,
  onFrameUpdate,
  route,
  territories,
  width = 1920,
  height = 1080,
  children,
}) => {
  const styleConfig = resolveMapStyle(mapStyle);

  if (styleConfig.renderer === "d3" && styleConfig.d3Theme) {
    return (
      <D3MapRenderer
        theme={styleConfig.d3Theme}
        cameraState={cameraState}
        route={route}
        territories={territories}
        width={width}
        height={height}
      >
        {children}
      </D3MapRenderer>
    );
  }

  // MapLibre (기본)
  return (
    <RemotionMap
      mapStyle={mapStyle}
      cameraState={cameraState}
      onMapReady={onMapReady}
      onFrameUpdate={onFrameUpdate}
      width={width}
      height={height}
    >
      {children}
    </RemotionMap>
  );
};
