import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import type { MapMarker, MapLabel } from "../types/manifest";
import type { CameraState } from "./cameraInterpolation";
import { useDesignTokens } from "../contexts/DesignTokenContext";
import { useMapTheme } from "./MapThemeContext";
import type { MarkerShape, TitleLayout, LabelStyle } from "./mapTheme";

/* ══════════════════════════════════════════════
   좌표 → 픽셀 변환
   ══════════════════════════════════════════════ */

export function lngLatToPixel(
  lngLat: [number, number],
  camera: CameraState,
  width: number,
  height: number,
): { x: number; y: number } {
  // MapLibre GL JS 기준 tileSize=512: worldSize = 512 * 2^zoom
  const scale = Math.pow(2, camera.zoom) * 512;
  const toMerc = (lng: number, lat: number) => {
    const x = ((lng + 180) / 360) * scale;
    const latRad = (lat * Math.PI) / 180;
    const y =
      ((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * scale;
    return { x, y };
  };
  const center = toMerc(camera.center[0], camera.center[1]);
  const point = toMerc(lngLat[0], lngLat[1]);
  return {
    x: width / 2 + (point.x - center.x),
    y: height / 2 + (point.y - center.y),
  };
}

/* ══════════════════════════════════════════════
   MarkerPin — 테마별 마커 Shape (인라인 SVG)
   ══════════════════════════════════════════════ */

interface MarkerPinProps {
  shape: MarkerShape;
  size: number;
  color: string;
  borderWidth: number;
  borderColor: string;
}

const MarkerPin: React.FC<MarkerPinProps> = ({ shape, size, color, borderWidth, borderColor }) => {
  const s = size;
  const half = s / 2;

  switch (shape) {
    case "drop_pin":
      return (
        <svg width={s} height={s * 1.4} viewBox={`0 0 ${s} ${s * 1.4}`}>
          <path
            d={`M${half},${s * 1.35} C${half},${s * 1.35} ${s * 0.92},${s * 0.7} ${s * 0.92},${half}
                A${half * 0.84},${half * 0.84} 0 1,0 ${s * 0.08},${half}
                C${s * 0.08},${s * 0.7} ${half},${s * 1.35} ${half},${s * 1.35}Z`}
            fill={color}
            stroke={borderColor}
            strokeWidth={borderWidth}
          />
          <circle cx={half} cy={half} r={s * 0.18} fill={borderColor} />
        </svg>
      );

    case "crosshair":
      return (
        <svg width={s} height={s} viewBox={`0 0 ${s} ${s}`}>
          <line x1={half} y1={2} x2={half} y2={s - 2} stroke={color} strokeWidth={1.5} />
          <line x1={2} y1={half} x2={s - 2} y2={half} stroke={color} strokeWidth={1.5} />
          <circle cx={half} cy={half} r={s * 0.15} fill={color} />
          <circle cx={half} cy={half} r={s * 0.32} fill="none" stroke={color} strokeWidth={1.5} />
        </svg>
      );

    case "diamond":
      return (
        <svg width={s} height={s} viewBox={`0 0 ${s} ${s}`}>
          <rect
            x={half * 0.3}
            y={half * 0.3}
            width={s * 0.7}
            height={s * 0.7}
            fill={color}
            stroke={borderWidth > 0 ? borderColor : "none"}
            strokeWidth={borderWidth}
            transform={`rotate(45 ${half} ${half})`}
          />
        </svg>
      );

    case "ring":
      return (
        <svg width={s} height={s} viewBox={`0 0 ${s} ${s}`}>
          <circle
            cx={half}
            cy={half}
            r={half * 0.7}
            fill="none"
            stroke={borderColor}
            strokeWidth={borderWidth + 1}
          />
          <circle cx={half} cy={half} r={s * 0.12} fill={borderColor} />
        </svg>
      );

    case "circle":
    default:
      return (
        <div
          style={{
            width: s,
            height: s,
            borderRadius: "50%",
            backgroundColor: color,
            border: `${borderWidth}px solid ${borderColor}`,
          }}
        />
      );
  }
};

/* ══════════════════════════════════════════════
   MarkerOverlay — 테마 기반
   ══════════════════════════════════════════════ */

interface MarkerOverlayProps {
  markers: MapMarker[];
  camera: CameraState;
  width: number;
  height: number;
}

export const MarkerOverlay: React.FC<MarkerOverlayProps> = ({
  markers,
  camera,
  width,
  height,
}) => {
  const frame = useCurrentFrame();
  const { STYLE } = useDesignTokens();
  const theme = useMapTheme();
  const mt = theme.marker;
  const anim = theme.animation;
  const accentColor = STYLE.colors[STYLE.accentIndex ?? 0];

  // 모든 마커의 픽셀 좌표를 미리 계산
  const positions = markers.map((m) => lngLatToPixel(m.coordinates, camera, width, height));

  // 라벨 위치 자동 결정 — 그리디 배치: 마커 중심 + 이미 배치된 라벨 모두 고려
  type Rect = { x1: number; y1: number; x2: number; y2: number };
  type Dir = "top" | "bottom" | "left" | "right";
  const labelDirs = (() => {
    const LABEL_W = 100;
    const LABEL_H = 36;
    const MARKER_R = 22;
    const PAD = 4; // 라벨 간 최소 여유
    const dirs: Dir[] = [];
    const placedRects: Rect[] = []; // 이미 배치된 라벨 영역

    const makeRect = (px: number, py: number, dir: Dir): Rect => {
      switch (dir) {
        case "bottom": return { x1: px - LABEL_W / 2, y1: py + MARKER_R, x2: px + LABEL_W / 2, y2: py + MARKER_R + LABEL_H };
        case "top":    return { x1: px - LABEL_W / 2, y1: py - MARKER_R - LABEL_H, x2: px + LABEL_W / 2, y2: py - MARKER_R };
        case "right":  return { x1: px + MARKER_R, y1: py - LABEL_H / 2, x2: px + MARKER_R + LABEL_W, y2: py + LABEL_H / 2 };
        case "left":   return { x1: px - MARKER_R - LABEL_W, y1: py - LABEL_H / 2, x2: px - MARKER_R, y2: py + LABEL_H / 2 };
      }
    };

    const rectsOverlap = (a: Rect, b: Rect): boolean =>
      a.x1 - PAD < b.x2 && a.x2 + PAD > b.x1 && a.y1 - PAD < b.y2 && a.y2 + PAD > b.y1;

    for (let i = 0; i < markers.length; i++) {
      if (markers[i].labelPosition) {
        const dir = markers[i].labelPosition as Dir;
        dirs.push(dir);
        placedRects.push(makeRect(positions[i].x, positions[i].y, dir));
        continue;
      }

      const tryDirs: Dir[] = ["bottom", "top", "right", "left"];
      let bestDir: Dir = "bottom";

      for (const dir of tryDirs) {
        const rect = makeRect(positions[i].x, positions[i].y, dir);
        let hasCollision = false;

        // 다른 마커 중심과 충돌 확인
        for (let j = 0; j < markers.length; j++) {
          if (j === i) continue;
          if (positions[j].x > rect.x1 && positions[j].x < rect.x2 &&
              positions[j].y > rect.y1 && positions[j].y < rect.y2) {
            hasCollision = true;
            break;
          }
        }

        // 이미 배치된 라벨과 충돌 확인
        if (!hasCollision) {
          for (const placed of placedRects) {
            if (rectsOverlap(rect, placed)) {
              hasCollision = true;
              break;
            }
          }
        }

        if (!hasCollision) {
          bestDir = dir;
          break;
        }
      }

      dirs.push(bestDir);
      placedRects.push(makeRect(positions[i].x, positions[i].y, bestDir));
    }
    return dirs;
  })();

  return (
    <>
      {markers.map((marker, i) => {
        const pos = positions[i];
        const appearAt = marker.appearAtFrame ?? 0;
        const fadeIn = anim.markerFadeIn;

        // 마커 핀: 등장 페이드인만, 등장 후 고정 (모션 없음)
        const markerOpacity = interpolate(frame, [appearAt, appearAt + fadeIn], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        // 라벨: 마커 등장 완료 후 페이드인
        const labelOpacity = interpolate(frame, [appearAt + fadeIn, appearAt + fadeIn + 10], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });

        const markerSize = marker.style === "dot" ? mt.dotSize : mt.size;
        const dir = labelDirs[i];

        // 라벨 오프셋: 핀 중심 기준 절대 위치
        const labelOffset = (() => {
          const gap = 6;
          const half = markerSize / 2;
          switch (dir) {
            case "bottom": return { left: "50%", top: markerSize / 2 + gap, transform: "translateX(-50%)" } as const;
            case "top":    return { left: "50%", bottom: markerSize / 2 + gap, transform: "translateX(-50%)" } as const;
            case "right":  return { left: half + gap, top: "50%", transform: "translateY(-50%)" } as const;
            case "left":   return { right: half + gap, top: "50%", transform: "translateY(-50%)" } as const;
          }
        })();

        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: pos.x,
              top: pos.y,
              transform: "translate(-50%, -50%)",
              opacity: markerOpacity,
              pointerEvents: "none",
              width: markerSize,
              height: markerSize,
            }}
          >
            {/* 마커 핀: 항상 좌표 정중앙 고정 */}
            <div style={{
              filter: mt.shadow ? `drop-shadow(${mt.shadow})` : undefined,
              width: markerSize,
              height: markerSize,
            }}>
              <MarkerPin
                shape={mt.shape}
                size={markerSize}
                color={accentColor}
                borderWidth={mt.borderWidth}
                borderColor={mt.borderColor}
              />
            </div>
            {/* 라벨: 핀 기준 방향별 절대 위치 */}
            {marker.label && (
              <div
                style={{
                  position: "absolute",
                  ...labelOffset,
                  padding: "4px 12px",
                  backgroundColor: mt.labelBg,
                  borderRadius: mt.labelRadius,
                  fontSize: mt.labelFontSize,
                  fontWeight: mt.labelFontWeight,
                  color: mt.labelColor,
                  fontFamily: mt.labelFontFamily ?? "'Pretendard', sans-serif",
                  whiteSpace: "nowrap",
                  boxShadow: mt.labelShadow,
                  textShadow: "none",
                  opacity: labelOpacity,
                }}
              >
                {marker.label}
              </div>
            )}
          </div>
        );
      })}
    </>
  );
};

/* ══════════════════════════════════════════════
   LabelOverlay — 테마 기반 배지 스타일
   ══════════════════════════════════════════════ */

interface LabelOverlayProps {
  labels: MapLabel[];
  camera: CameraState;
  width: number;
  height: number;
}

export const LabelOverlay: React.FC<LabelOverlayProps> = ({
  labels,
  camera,
  width,
  height,
}) => {
  const frame = useCurrentFrame();
  const theme = useMapTheme();
  const lt = theme.label;

  const badgeStyle = (labelStyle: LabelStyle): React.CSSProperties => {
    const base: React.CSSProperties = {
      fontFamily: lt.fontFamily,
      fontSize: lt.fontSize,
      fontWeight: lt.fontWeight,
      color: lt.color,
      whiteSpace: "nowrap",
      pointerEvents: "none",
    };
    switch (labelStyle) {
      case "card":
        return {
          ...base,
          backgroundColor: lt.badgeBg,
          borderRadius: lt.badgeRadius ?? 8,
          padding: lt.badgePadding ?? "4px 12px",
          boxShadow: lt.badgeShadow,
        };
      case "pill":
        return {
          ...base,
          backgroundColor: lt.badgeBg,
          borderRadius: lt.badgeRadius ?? 16,
          padding: lt.badgePadding ?? "3px 14px",
          boxShadow: lt.badgeShadow,
          border: lt.badgeBorder,
        };
      case "tag":
        return {
          ...base,
          backgroundColor: lt.badgeBg,
          borderRadius: lt.badgeRadius ?? 4,
          padding: lt.badgePadding ?? "3px 10px",
          boxShadow: lt.badgeShadow,
          border: lt.badgeBorder,
        };
      case "underline":
        return {
          ...base,
          borderBottom: lt.badgeBorder ?? `2px solid ${lt.color}`,
          paddingBottom: 2,
        };
      case "floating":
      default:
        return {
          ...base,
        };
    }
  };

  return (
    <>
      {labels.map((label, i) => {
        const pos = lngLatToPixel(label.coordinates, camera, width, height);
        const appearAt = label.appearAtFrame ?? 0;
        const opacity = interpolate(frame, [appearAt, appearAt + lt.fadeInFrames], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });

        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: pos.x,
              top: pos.y,
              transform: "translate(-50%, -50%)",
              opacity,
              ...badgeStyle(lt.style),
              fontSize: label.fontSize ?? lt.fontSize,
              color: label.color ?? lt.color,
            }}
          >
            {label.text}
          </div>
        );
      })}
    </>
  );
};

/* ══════════════════════════════════════════════
   MapTitleOverlay — 테마 기반 5종 레이아웃
   ══════════════════════════════════════════════ */

interface MapTitleOverlayProps {
  title?: string;
  source?: string;
}

export const MapTitleOverlay: React.FC<MapTitleOverlayProps> = ({ title, source }) => {
  const frame = useCurrentFrame();
  const theme = useMapTheme();
  const tt = theme.title;
  const anim = tt.animation;

  const titleOpacity = interpolate(frame, [anim.fadeInStart, anim.fadeInEnd], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const slideVal = interpolate(frame, [anim.fadeInStart, anim.fadeInEnd], [anim.slideDistance, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const slideTransform = (() => {
    switch (anim.slideDirection) {
      case "down":
        return `translateY(${slideVal}px)`;
      case "up":
        return `translateY(${-slideVal}px)`;
      case "left":
        return `translateX(${-slideVal}px)`;
      case "right":
        return `translateX(${slideVal}px)`;
    }
  })();

  if (!title && !source) return null;

  /** 출처 텍스트 (항상 오른쪽 상단) */
  const sourceEl = source ? (
    <div
      style={{
        position: "absolute",
        top: 10,
        right: 40,
        opacity: titleOpacity,
        fontSize: tt.source.fontSize,
        fontWeight: 400,
        color: tt.source.color,
        fontFamily: tt.source.fontFamily,
      }}
    >
      {`출처 : ${source}`}
    </div>
  ) : null;

  /** 타이틀 카드 스타일 */
  const cardStyle: React.CSSProperties = {
    opacity: titleOpacity,
    transform: slideTransform,
    background: tt.background,
    borderRadius: tt.borderRadius,
    padding: tt.padding,
    fontSize: tt.fontSize,
    fontWeight: tt.fontWeight,
    color: tt.color,
    fontFamily: tt.fontFamily,
    boxShadow: tt.shadow,
    letterSpacing: tt.letterSpacing,
    border: tt.border,
    backdropFilter: tt.backdropFilter,
    WebkitBackdropFilter: tt.backdropFilter,
  };

  /** 레이아웃별 렌더 */
  const renderLayout = (layout: TitleLayout) => {
    switch (layout) {
      /* ── 상단 중앙 카드 ── */
      case "top_center_card":
        return (
          <div
            style={{
              position: "absolute",
              top: 40,
              left: 0,
              right: 0,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              pointerEvents: "none",
            }}
          >
            {title && <div style={cardStyle}>{title}</div>}
            {sourceEl}
          </div>
        );

      /* ── 하단 바 ── */
      case "bottom_bar":
        return (
          <div
            style={{
              position: "absolute",
              bottom: 0,
              left: 0,
              right: 0,
              pointerEvents: "none",
            }}
          >
            {title && (
              <div style={{ ...cardStyle, width: "100%", textAlign: "center" }}>
                {title}
              </div>
            )}
            {sourceEl}
          </div>
        );

      /* ── 글래스모피즘 (상단 중앙) ── */
      case "floating_glass":
        return (
          <div
            style={{
              position: "absolute",
              top: 40,
              left: 0,
              right: 0,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              pointerEvents: "none",
            }}
          >
            {title && <div style={cardStyle}>{title}</div>}
            {sourceEl}
          </div>
        );

      /* ── 좌상단 배지 ── */
      case "corner_badge":
        return (
          <div style={{ position: "absolute", top: 32, left: 40, pointerEvents: "none" }}>
            {title && <div style={cardStyle}>{title}</div>}
            {sourceEl}
          </div>
        );

      /* ── 좌측 배너 (네온 좌측 보더) ── */
      case "left_banner":
        return (
          <div style={{ position: "absolute", top: 40, left: 0, pointerEvents: "none" }}>
            {title && (
              <div
                style={{
                  ...cardStyle,
                  borderLeft: `4px solid ${theme.route.defaultColor}`,
                  borderRadius: `0 ${tt.borderRadius}px ${tt.borderRadius}px 0`,
                }}
              >
                {title}
              </div>
            )}
            {sourceEl}
          </div>
        );

      default:
        return null;
    }
  };

  return <>{renderLayout(tt.layout)}</>;
};
