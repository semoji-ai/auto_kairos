import React from "react";
import { useVideoConfig } from "remotion";
import { RemotionMap } from "./RemotionMap";

/** 오버레이 없는 세모지 지도 한 장 — AE 가이드(배경) 레이어로 쓴다. 오토카이로스 PrerenderedMapBg 와 같은 역할 */
export const MapBg: React.FC<{ lng: number; lat: number; zoom: number; sea?: string; land?: string }> = ({ lng, lat, zoom, sea = "#8FBFD6", land = "#EAD9B6" }) => {
  const { width, height } = useVideoConfig();
  const onReady = React.useCallback((map: any) => {
    try { map.setPaintProperty("background", "background-color", land); map.setPaintProperty("water", "fill-color", sea); } catch { /* 없음 */ }
  }, [sea, land]);
  return <RemotionMap mapStyle="semoji" cameraState={{ center: [lng, lat], zoom, bearing: 0, pitch: 0 }} onMapReady={onReady} width={width} height={height} />;
};
