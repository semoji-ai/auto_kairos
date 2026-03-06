import React, { useEffect, useRef, useState } from "react";
import { delayRender, continueRender } from "remotion";
import maplibregl from "maplibre-gl";
import type { CameraState } from "./cameraInterpolation";
import { resolveMapStyle, type MapStyleConfig } from "./mapStyles";

// MapLibre CSS는 JS 번들에 포함되지 않으므로 인라인 최소 스타일
const MAP_CSS = `
.maplibregl-canvas { outline: none; }
.maplibregl-ctrl-bottom-left, .maplibregl-ctrl-bottom-right { display: none !important; }
`;

interface RemotionMapProps {
  /** 스타일 프리셋명 또는 직접 URL */
  mapStyle?: string;
  /** 현재 프레임의 카메라 상태 */
  cameraState: CameraState;
  /** 맵 인스턴스가 준비되면 호출 — 레이어 추가 등에 사용 */
  onMapReady?: (map: maplibregl.Map) => void;
  /** 매 프레임 맵 idle 후 호출 — 레이어 업데이트에 사용 */
  onFrameUpdate?: (map: maplibregl.Map) => void;
  /** 베이스맵 텍스트 라벨 숨김 — 경계선만 유지 (기본 true) */
  hideBaseLabels?: boolean;
  width?: number;
  height?: number;
  children?: React.ReactNode;
}

/**
 * Remotion 프레임 동기화 MapLibre 컴포넌트.
 *
 * 핵심 원리:
 * 1. delayRender()로 프레임 캡처를 대기
 * 2. jumpTo()로 카메라를 즉시 이동 (flyTo 금지 — 비동기라 프레임 불일치)
 * 3. triggerRepaint() → idle 이벤트에서 continueRender()
 *    (즉시 resolve하면 WebGL이 아직 이전 프레임을 보여주는 stale 캡처 발생)
 */
export const RemotionMap: React.FC<RemotionMapProps> = ({
  mapStyle,
  cameraState,
  onMapReady,
  onFrameUpdate,
  hideBaseLabels = true,
  width = 1920,
  height = 1080,
  children,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const readyRef = useRef(false);
  const [mapVisible, setMapVisible] = useState(false);
  const [handle] = useState(() => delayRender("Loading map tiles"));

  // 최신 카메라 상태를 ref로 추적 — load 핸들러에서 참조용
  // (mount effect 클로저는 frame 0 카메라만 갖고 있으므로)
  const latestCameraRef = useRef(cameraState);
  latestCameraRef.current = cameraState;

  const styleConfig = resolveMapStyle(mapStyle) as MapStyleConfig;

  // 맵 초기화 (마운트 시 1회)
  useEffect(() => {
    if (!containerRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: styleConfig.url ?? "https://tiles.openfreemap.org/styles/bright",
      center: cameraState.center,
      zoom: cameraState.zoom,
      bearing: cameraState.bearing,
      pitch: cameraState.pitch,
      interactive: false,
      fadeDuration: 0,
      attributionControl: false,
      antialias: true,
      // preserveDrawingBuffer: WebGL 캡처용 — MapOptions 타입에 없지만 런타임 지원
      ...(({ preserveDrawingBuffer: true }) as Record<string, unknown>),
    } as maplibregl.MapOptions);

    map.on("load", () => {
      // 베이스맵 텍스트 라벨 숨김 — 경계선·도로선은 유지
      if (hideBaseLabels) {
        const style = map.getStyle();
        if (style?.layers) {
          for (const layer of style.layers) {
            if (layer.type === "symbol") {
              map.setLayoutProperty(layer.id, "visibility", "none");
            }
          }
        }
      }

      readyRef.current = true;
      mapRef.current = map;

      // 맵 로딩 중 프레임이 진행했을 수 있으므로 최신 카메라로 즉시 점프
      const cam = latestCameraRef.current;
      map.jumpTo({
        center: cam.center,
        zoom: cam.zoom,
        bearing: cam.bearing,
        pitch: cam.pitch,
      });

      setMapVisible(true); // 라벨 숨긴 후에만 맵 표시
      onMapReady?.(map);

      // 라벨 제거 + 카메라 점프 후 재렌더 → idle에서 첫 프레임 캡처 허용
      map.once("idle", () => {
        onFrameUpdate?.(map);
        continueRender(handle);
      });
    });

    return () => {
      map.remove();
      mapRef.current = null;
      readyRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 프레임 변경 시 카메라 + 데이터 업데이트
  // mapVisible을 deps에 포함 — 맵 로드 완료 시 즉시 현재 카메라로 동기화
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;

    const frameHandle = delayRender("Updating map frame");

    map.jumpTo({
      center: cameraState.center,
      zoom: cameraState.zoom,
      bearing: cameraState.bearing,
      pitch: cameraState.pitch,
    });

    // jumpTo 후 반드시 repaint 요청 → idle 대기
    // (즉시 resolve하면 stale WebGL 프레임 캡처됨)
    map.triggerRepaint();

    const onIdle = () => {
      onFrameUpdate?.(map);
      continueRender(frameHandle);
    };
    map.once("idle", onIdle);

    // 클린업: 새 프레임이 들어오면 이전 핸들러 제거 + 미해결 handle 해제
    return () => {
      map.off("idle", onIdle);
      try {
        continueRender(frameHandle);
      } catch {
        // 이미 해제된 handle — 무시
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cameraState.center[0], cameraState.center[1], cameraState.zoom, cameraState.bearing, cameraState.pitch, onFrameUpdate, mapVisible]);

  return (
    <div style={{ position: "relative", width, height, overflow: "hidden" }}>
      <style>{MAP_CSS}</style>
      <div
        ref={containerRef}
        style={{
          width,
          height,
          filter: styleConfig.cssFilter || undefined,
          opacity: mapVisible ? 1 : 0, // load 전 라벨 깜빡임 방지
        }}
      />
      {/* 맵 위에 오버레이되는 마커/라벨 등 — 맵 준비 후에만 표시 */}
      {children && mapVisible && (
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width,
            height,
            pointerEvents: "none",
          }}
        >
          {children}
        </div>
      )}
    </div>
  );
};
