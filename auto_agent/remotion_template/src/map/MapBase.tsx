import React from "react";
import type maplibregl from "maplibre-gl";
import type { CameraState } from "./cameraInterpolation";
import { RemotionMap } from "./RemotionMap";

/**
 * MapBase — MapLibre 맵 렌더러
 *
 * mapStyle 프리셋에 따라 레이어 오버라이드를 적용한 MapLibre 벡터 타일 맵을 렌더링.
 */

interface MapBaseProps {
  /** 맵 스타일 프리셋명 */
  mapStyle?: string;
  /** 카메라 상태 */
  cameraState: CameraState;
  /** 맵 로드 콜백 */
  onMapReady?: (map: maplibregl.Map) => void;
  /** 프레임 업데이트 콜백 */
  onFrameUpdate?: (map: maplibregl.Map) => void;
  width?: number;
  height?: number;
  children?: React.ReactNode;
}

export const MapBase: React.FC<MapBaseProps> = ({
  mapStyle,
  cameraState,
  onMapReady,
  onFrameUpdate,
  width = 1920,
  height = 1080,
  children,
}) => {
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
