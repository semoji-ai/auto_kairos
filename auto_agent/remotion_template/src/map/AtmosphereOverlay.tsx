import React from "react";
import { useMapTheme } from "./MapThemeContext";

/**
 * 분위기 효과 오버레이 — 맵 위, 마커/라벨 아래에 위치.
 *
 * - 비네팅: CSS radial-gradient
 * - 그레인: SVG feTurbulence 필터
 * - 테두리 장식: ornate, thin_line, corner_marks
 */
export const AtmosphereOverlay: React.FC<{ width?: number; height?: number }> = ({
  width = 1920,
  height = 1080,
}) => {
  const theme = useMapTheme();
  const atm = theme.atmosphere;

  if (atm.vignette <= 0 && atm.grain <= 0 && atm.borderDecoration === "none") {
    return null;
  }

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width,
        height,
        pointerEvents: "none",
        zIndex: 5,
      }}
    >
      {/* 비네팅 */}
      {atm.vignette > 0 && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: `radial-gradient(ellipse at center, transparent 50%, ${atm.vignetteColor ?? "rgba(0,0,0,0.8)"} 100%)`,
            opacity: atm.vignette,
          }}
        />
      )}

      {/* 그레인 */}
      {atm.grain > 0 && (
        <>
          <svg width={0} height={0} style={{ position: "absolute" }}>
            <filter id="map-grain">
              <feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" stitchTiles="stitch" />
              <feColorMatrix type="saturate" values="0" />
            </filter>
          </svg>
          <div
            style={{
              position: "absolute",
              inset: 0,
              filter: "url(#map-grain)",
              opacity: atm.grain,
              mixBlendMode: "overlay",
            }}
          />
        </>
      )}

      {/* 테두리 장식 */}
      {atm.borderDecoration !== "none" && (
        <BorderDecoration
          type={atm.borderDecoration}
          color={atm.borderColor ?? "#888"}
          lineWidth={atm.borderWidth ?? 1}
          width={width}
          height={height}
        />
      )}
    </div>
  );
};

/* ── 테두리 장식 서브컴포넌트 ── */

interface BorderDecoProps {
  type: "ornate" | "thin_line" | "corner_marks";
  color: string;
  lineWidth: number;
  width: number;
  height: number;
}

const BorderDecoration: React.FC<BorderDecoProps> = ({
  type,
  color,
  lineWidth,
  width,
  height,
}) => {
  const m = 24; // 마진
  const c = 40; // 코너 마크 길이

  switch (type) {
    case "thin_line":
      return (
        <svg
          width={width}
          height={height}
          style={{ position: "absolute", inset: 0 }}
        >
          <rect
            x={m}
            y={m}
            width={width - m * 2}
            height={height - m * 2}
            fill="none"
            stroke={color}
            strokeWidth={lineWidth}
            strokeOpacity={0.5}
          />
        </svg>
      );

    case "corner_marks":
      return (
        <svg
          width={width}
          height={height}
          style={{ position: "absolute", inset: 0 }}
        >
          {/* 좌상 */}
          <path d={`M${m},${m + c} L${m},${m} L${m + c},${m}`} fill="none" stroke={color} strokeWidth={lineWidth} />
          {/* 우상 */}
          <path d={`M${width - m - c},${m} L${width - m},${m} L${width - m},${m + c}`} fill="none" stroke={color} strokeWidth={lineWidth} />
          {/* 좌하 */}
          <path d={`M${m},${height - m - c} L${m},${height - m} L${m + c},${height - m}`} fill="none" stroke={color} strokeWidth={lineWidth} />
          {/* 우하 */}
          <path d={`M${width - m - c},${height - m} L${width - m},${height - m} L${width - m},${height - m - c}`} fill="none" stroke={color} strokeWidth={lineWidth} />
        </svg>
      );

    case "ornate":
      return (
        <svg
          width={width}
          height={height}
          style={{ position: "absolute", inset: 0 }}
        >
          {/* 이중선 테두리 */}
          <rect
            x={m}
            y={m}
            width={width - m * 2}
            height={height - m * 2}
            fill="none"
            stroke={color}
            strokeWidth={lineWidth}
            strokeOpacity={0.4}
          />
          <rect
            x={m + 6}
            y={m + 6}
            width={width - (m + 6) * 2}
            height={height - (m + 6) * 2}
            fill="none"
            stroke={color}
            strokeWidth={lineWidth * 0.6}
            strokeOpacity={0.25}
          />
        </svg>
      );

    default:
      return null;
  }
};
