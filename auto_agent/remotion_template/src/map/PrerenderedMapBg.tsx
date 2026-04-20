import React from "react";
import { Img, staticFile } from "remotion";
const resolveAsset = (p: string) => p.startsWith("http") ? p : staticFile(p);
import type { CameraState } from "./cameraInterpolation";

interface PrerenderedMapBgProps {
  /** 배경 이미지 경로 (staticFile 기준 상대경로) */
  imagePath: string;
  /** 스크린샷 캡처 시점의 카메라 상태 — 오버레이 좌표 변환에 사용 */
  captureCamera: CameraState;
  width?: number;
  height?: number;
  brightness?: number;
  children?: React.ReactNode;
}

/**
 * PrerenderedMapBg — 프리렌더된 맵 스크린샷 배경 + 오버레이 컨테이너
 *
 * MapLibre 실시간 렌더링 대신 프리렌더된 PNG를 <Img>로 표시.
 * children으로 마커/라벨/경로 등 HTML 오버레이를 합성.
 *
 * captureCamera는 스크린샷 촬영 시 카메라 상태로,
 * lngLatToPixel() 좌표 변환 시 이 값을 사용해야 정확한 위치가 나온다.
 */
export const PrerenderedMapBg: React.FC<PrerenderedMapBgProps> = ({
  imagePath,
  width = 1920,
  height = 1080,
  brightness = 1.0,
  children,
}) => {
  return (
    <div style={{ position: "relative", width, height, overflow: "hidden" }}>
      <Img
        src={resolveAsset(imagePath)}
        style={{
          width,
          height,
          objectFit: "cover",
          filter: brightness !== 1.0 ? `brightness(${brightness})` : undefined,
        }}
      />
      {children && (
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
