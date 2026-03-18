import React from "react";
import { AbsoluteFill, Img, useCurrentFrame, interpolate } from "remotion";
import { STYLE as DEFAULT_STYLE } from "./vizStyles";
import { resolveAsset } from "../utils/resolveAsset";
import { resolveEasing } from "../utils/easingMap";
import { calcItemDelay } from "../utils/syncDelay";
import { countUpValue } from "../utils/countUp";
import { VizShell } from "./VizShell";
import { VIZ_STRINGS } from "./vizI18n";
import type { VisualizationData, VizAnimationConfig } from "../types/manifest";

interface Props {
  data: VisualizationData;
  durationInFrames: number;
  fps: number;
  vizAnimation?: VizAnimationConfig;
}

/**
 * 연출 모드 자동 선택 기준:
 *
 * ┌──────────────────────────────────────────────────────────────┐
 * │ 모드          │ 조건                        │ 연출           │
 * ├──────────────────────────────────────────────────────────────┤
 * │ DATA (수치)   │ items 2개 + values 숫자 2개+ │ 카운트업 숫자  │
 * │               │                             │ 화살표 + 변화율│
 * │               │                             │ "기존"→"변경후"│
 * ├──────────────────────────────────────────────────────────────┤
 * │ VS (대결)     │ left/right 구조 있음         │ VS 배지        │
 * │               │ 또는 items 2개 + values 없음 │ 좌우 카드+불릿 │
 * │               │                             │ 이미지 지원    │
 * │               │                             │ 분할 배경      │
 * ├──────────────────────────────────────────────────────────────┤
 * │ MULTI (다항목)│ items 3개+ with values       │ 세로 카드 리스트│
 * │               │                             │ 마지막 항목 강조│
 * │               │                             │ 카운트업 숫자  │
 * └──────────────────────────────────────────────────────────────┘
 */
type CompareMode = "data" | "vs" | "multi";

function detectMode(data: VisualizationData): CompareMode {
  const hasLeftRight = !!(data.left && data.right);
  const items = data.items ?? [];
  const values = data.values ?? [];
  const hasNumericValues = values.length >= 2 && values.every((v) => typeof v === "number" && v > 0);

  if (hasLeftRight) return "vs";
  if (items.length === 2 && hasNumericValues) return "data";
  if (items.length >= 3 && values.length >= 3) return "multi";
  if (items.length === 2) return "vs";
  return values.length >= 2 ? "data" : "vs";
}

export const Compare: React.FC<Props> = ({ data, durationInFrames, fps, vizAnimation }) => {
  const mode = detectMode(data);

  // VS mode uses hideTitle + internal title rendering
  const isVs = mode === "vs";

  return (
    <VizShell
      title={data.title}
      source={data.source}
      durationInFrames={durationInFrames}
      vizAnimation={vizAnimation}
      background={isVs ? undefined : undefined}
      hideTitle={isVs}
    >
      {mode === "data" && (
        <DataCompare data={data} fps={fps} vizAnimation={vizAnimation} />
      )}
      {mode === "vs" && (
        <VsCompare data={data} fps={fps} vizAnimation={vizAnimation} />
      )}
      {mode === "multi" && (
        <MultiCompare data={data} fps={fps} vizAnimation={vizAnimation} />
      )}
    </VizShell>
  );
};

// ─── 강조 보간 헬퍼 ──────────────────────────────────────────

function useHighlight(frame: number, syncDelay: number) {
  const HIGHLIGHT_IN = 8;
  const HIGHLIGHT_HOLD = 20;
  const HIGHLIGHT_OUT = 12;
  const hlStart = syncDelay;
  const hlPeak = hlStart + HIGHLIGHT_IN;
  const hlHoldEnd = hlPeak + HIGHLIGHT_HOLD;
  const hlEnd = hlHoldEnd + HIGHLIGHT_OUT;
  return interpolate(
    frame,
    [hlStart, hlPeak, hlHoldEnd, hlEnd],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
}

// ─── 모드 1: DATA (수치 전후 비교) ───────────────────────────

const DataCompare: React.FC<{
  data: VisualizationData;
  fps: number;
  vizAnimation?: VizAnimationConfig;
}> = ({ data, fps, vizAnimation }) => {
  const frame = useCurrentFrame();
  const easingFn = resolveEasing(vizAnimation?.easing);

  const items = data.items ?? [];
  const values = data.values ?? [];
  const unit = data.unit ?? "";

  const change =
    values.length >= 2 && values[0] !== 0
      ? (((values[1] - values[0]) / Math.abs(values[0])) * 100).toFixed(1)
      : null;
  const changePositive = values.length >= 2 && values[1] >= values[0];

  // ── Phase 1: 등장 (좌→우 순차) ──
  const LEFT_ENTRANCE = 8;
  const RIGHT_ENTRANCE = 16;
  const FADE_IN = 15;

  const leftOpacity = interpolate(frame, [LEFT_ENTRANCE, LEFT_ENTRANCE + FADE_IN], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easingFn,
  });
  const leftSlide = interpolate(frame, [LEFT_ENTRANCE, LEFT_ENTRANCE + FADE_IN], [-30, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easingFn,
  });
  const arrowOpacity = interpolate(frame, [12, 24], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const rightOpacity = interpolate(frame, [RIGHT_ENTRANCE, RIGHT_ENTRANCE + FADE_IN], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easingFn,
  });
  const rightSlide = interpolate(frame, [RIGHT_ENTRANCE, RIGHT_ENTRANCE + FADE_IN], [30, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easingFn,
  });

  // ── Phase 2: 타임스탬프 기반 강조 ──
  const leftSyncDelay = calcItemDelay(0, fps, vizAnimation, 0, 0);
  const rightSyncDelay = calcItemDelay(1, fps, vizAnimation, 0, 0);
  const leftHl = useHighlight(frame, leftSyncDelay);
  const rightHl = useHighlight(frame, rightSyncDelay);

  const leftValue = countUpValue(frame, LEFT_ENTRANCE, 25, values[0], easingFn);
  const rightValue = countUpValue(frame, RIGHT_ENTRANCE, 25, values[1], easingFn);
  const accentIdx = DEFAULT_STYLE.accentIndex ?? 0;
  const accentColor = `var(--viz-color-${accentIdx})`;

  return (
    <div
      style={{
        flex: 1,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: "4%",
      }}
    >
      {/* Left - Before */}
      <div
        style={{
          width: "36%",
          background: "var(--viz-card-bg)",
          borderRadius: "var(--viz-card-radius)",
          padding: "40px 32px",
          textAlign: "center",
          opacity: leftOpacity,
          transform: `translateX(${leftSlide}px) scale(${1 + leftHl * 0.02})`,
          boxShadow: `0 4px ${20 + leftHl * 20}px rgba(61,59,47,${0.08 + leftHl * 0.14})`,
          border: `${2 + leftHl * 2}px solid var(--viz-grid)`,
          transformOrigin: "center center",
        }}
      >
        <div style={{ color: "var(--viz-subtitle)", fontSize: "var(--viz-label-size)", fontWeight: "var(--viz-label-weight)", marginBottom: 10 }}>
          {VIZ_STRINGS.diagram_before}
        </div>
        <div style={{ color: "var(--viz-text)", fontSize: "var(--viz-label-size)", fontWeight: "var(--viz-label-weight)", marginBottom: 20 }}>
          {items[0]}
        </div>
        <div style={{ color: "var(--viz-text)", fontSize: "var(--viz-hero-size)", fontWeight: "var(--viz-hero-weight)" }}>
          {leftValue.toLocaleString()}
          <span style={{ fontSize: "var(--viz-label-size)", fontWeight: "var(--viz-caption-weight)" }}>{unit}</span>
        </div>
      </div>

      {/* Arrow + Change Badge */}
      <div style={{ opacity: arrowOpacity, textAlign: "center" }}>
        <svg width="72" height="72" viewBox="0 0 60 60">
          <path
            d="M10 30 L40 30 L35 20 M40 30 L35 40"
            fill="none"
            stroke="var(--viz-border)"
            strokeWidth={4}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        {change && (
          <div
            style={{
              marginTop: 8,
              padding: "6px 18px",
              borderRadius: 20,
              background: changePositive ? "var(--viz-positive-bg)" : "var(--viz-negative-bg)",
              color: changePositive ? "var(--viz-positive)" : "var(--viz-negative)",
              fontSize: "var(--viz-label-size)",
              fontWeight: "var(--viz-title-weight)",
            }}
          >
            {changePositive ? "+" : ""}{change}%
          </div>
        )}
      </div>

      {/* Right - After */}
      <div
        style={{
          width: "36%",
          background: `linear-gradient(135deg, ${DEFAULT_STYLE.colors[accentIdx]}15, ${DEFAULT_STYLE.colors[accentIdx]}08)`,
          border: `${3 + rightHl * 2}px solid ${accentColor}`,
          borderRadius: "var(--viz-card-radius)",
          padding: "40px 32px",
          textAlign: "center",
          opacity: rightOpacity,
          transform: `translateX(${rightSlide}px) scale(${1 + rightHl * 0.02})`,
          boxShadow: `0 4px ${20 + rightHl * 20}px rgba(61,59,47,${0.08 + rightHl * 0.14})`,
          transformOrigin: "center center",
        }}
      >
        <div style={{ color: accentColor, fontSize: "var(--viz-label-size)", fontWeight: "var(--viz-label-weight)", marginBottom: 10 }}>
          {VIZ_STRINGS.diagram_after}
        </div>
        <div style={{ color: "var(--viz-text)", fontSize: "var(--viz-label-size)", fontWeight: "var(--viz-label-weight)", marginBottom: 20 }}>
          {items[1]}
        </div>
        <div style={{ color: "var(--viz-text)", fontSize: "var(--viz-hero-size)", fontWeight: "var(--viz-hero-weight)" }}>
          {rightValue.toLocaleString()}
          <span style={{ fontSize: "var(--viz-label-size)", fontWeight: "var(--viz-caption-weight)" }}>{unit}</span>
        </div>
      </div>
    </div>
  );
};

// ─── 모드 2: VS (좌우 대결 비교) — Pencil S3 풀하이트 레이아웃 ──

const VsCompare: React.FC<{
  data: VisualizationData;
  fps: number;
  vizAnimation?: VizAnimationConfig;
}> = ({ data, fps, vizAnimation }) => {
  const frame = useCurrentFrame();
  const easingFn = resolveEasing(vizAnimation?.easing);

  const leftLabel = data.left?.label ?? data.items?.[0] ?? "";
  const rightLabel = data.right?.label ?? data.items?.[1] ?? "";
  const leftItems = data.left?.items ?? [];
  const rightItems = data.right?.items ?? [];
  const leftImage = typeof data.imagePath === "object" ? data.imagePath?.left : undefined;
  const rightImage = typeof data.imagePath === "object" ? data.imagePath?.right : undefined;
  const descriptions = (data as any).descriptions ?? [];

  // ── Adaptive sizing based on item count ──
  const maxN = Math.max(leftItems.length, rightItems.length);
  const imgHeight = maxN >= 5 ? 220 : maxN >= 4 ? 270 : 320;
  const panelGap = maxN >= 5 ? 16 : 24;
  const panelPadV = maxN >= 5 ? 24 : 40;
  const panelPadH = maxN >= 5 ? 48 : 60;
  const labelFs = maxN >= 5 ? 38 : 48;
  const descFs = maxN >= 5 ? 26 : 32;

  const accentIdx = DEFAULT_STYLE.accentIndex ?? 0;
  const accentColor = `var(--viz-color-${accentIdx})`;

  // ── Phase 1: Entrance ──
  const headerOpacity = interpolate(frame, [0, 12], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const leftOpacity = interpolate(frame, [6, 18], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easingFn,
  });
  const leftSlide = interpolate(frame, [6, 18], [-40, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easingFn,
  });
  const vsScaleY = interpolate(frame, [10, 22], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const rightOpacity = interpolate(frame, [14, 26], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easingFn,
  });
  const rightSlide = interpolate(frame, [14, 26], [40, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easingFn,
  });

  // ── Phase 2: highlight ──
  const leftSyncDelay = calcItemDelay(0, fps, vizAnimation, 0, 0);
  const rightSyncDelay = calcItemDelay(1, fps, vizAnimation, 0, 0);
  const leftHl = useHighlight(frame, leftSyncDelay);
  const rightHl = useHighlight(frame, rightSyncDelay);

  // Left tag & desc from items/descriptions
  const leftTag = leftItems[0] ?? "";
  const rightTag = rightItems[0] ?? "";
  const leftDesc = descriptions[0] ?? leftItems.slice(1).join("\n");
  const rightDesc = descriptions[1] ?? rightItems.slice(1).join("\n");

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
      {/* ── Top bar with title ── */}
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          padding: "32px 60px",
          opacity: headerOpacity,
        }}
      >
        <div
          style={{
            color: "var(--viz-text)",
            fontSize: "var(--viz-title-size)",
            fontWeight: "var(--viz-title-weight)",
            fontFamily: "var(--viz-title-font)",
            letterSpacing: "var(--viz-title-tracking)",
          }}
        >
          {data.title}
        </div>
      </div>

      {/* ── Body: Left | VS bar | Right ── */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "row",
          minHeight: 0,
        }}
      >
        {/* Left panel */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            gap: panelGap,
            background: "var(--viz-card-bg)",
            padding: `${panelPadV}px ${panelPadH}px`,
            opacity: leftOpacity,
            transform: `translateX(${leftSlide}px) scale(${1 + leftHl * 0.01})`,
            transformOrigin: "right center",
            overflow: "hidden",
          }}
        >
          {/* Image */}
          {leftImage ? (
            <Img
              src={resolveAsset(leftImage)}
              style={{ width: "100%", height: imgHeight, objectFit: "cover", borderRadius: 8, flexShrink: 0 }}
            />
          ) : (
            <div style={{ width: "100%", height: imgHeight, background: "var(--viz-border)", borderRadius: 8, flexShrink: 0 }} />
          )}
          <div style={{ color: "var(--viz-text)", fontSize: labelFs, fontWeight: 700, fontFamily: "var(--viz-font)" }}>
            {leftLabel}
          </div>
          {leftTag && (
            <div style={{ color: accentColor, fontSize: "var(--viz-label-size)", fontWeight: 500, fontFamily: "var(--viz-font)" }}>
              {leftTag}
            </div>
          )}
          {leftDesc && (
            <div style={{ color: "var(--viz-subtitle)", fontSize: descFs, fontFamily: "var(--viz-font)", lineHeight: 1.5, whiteSpace: "pre-line" }}>
              {leftDesc}
            </div>
          )}
        </div>

        {/* VS divider bar */}
        <div
          style={{
            width: 80,
            flexShrink: 0,
            background: accentColor,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transform: `scaleY(${vsScaleY})`,
            transformOrigin: "center center",
          }}
        >
          <span
            style={{
              color: "#FFFFFF",
              fontSize: 40,
              fontWeight: 700,
              fontFamily: "var(--viz-font)",
            }}
          >
            VS
          </span>
        </div>

        {/* Right panel */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            gap: panelGap,
            background: "var(--viz-bg)",
            padding: `${panelPadV}px ${panelPadH}px`,
            opacity: rightOpacity,
            transform: `translateX(${rightSlide}px) scale(${1 + rightHl * 0.01})`,
            transformOrigin: "left center",
            overflow: "hidden",
          }}
        >
          {/* Image */}
          {rightImage ? (
            <Img
              src={resolveAsset(rightImage)}
              style={{ width: "100%", height: imgHeight, objectFit: "cover", borderRadius: 8, flexShrink: 0 }}
            />
          ) : (
            <div style={{ width: "100%", height: imgHeight, background: "var(--viz-border)", borderRadius: 8, flexShrink: 0 }} />
          )}
          <div style={{ color: "var(--viz-text)", fontSize: labelFs, fontWeight: 700, fontFamily: "var(--viz-font)" }}>
            {rightLabel}
          </div>
          {rightTag && (
            <div style={{ color: accentColor, fontSize: "var(--viz-label-size)", fontWeight: 500, fontFamily: "var(--viz-font)" }}>
              {rightTag}
            </div>
          )}
          {rightDesc && (
            <div style={{ color: "var(--viz-subtitle)", fontSize: descFs, fontFamily: "var(--viz-font)", lineHeight: 1.5, whiteSpace: "pre-line" }}>
              {rightDesc}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ─── 모드 3: MULTI (다항목 비교) ─────────────────────────────

const MultiCompare: React.FC<{
  data: VisualizationData;
  fps: number;
  vizAnimation?: VizAnimationConfig;
}> = ({ data, fps, vizAnimation }) => {
  const frame = useCurrentFrame();
  const easingFn = resolveEasing(vizAnimation?.easing);
  const accentIdx = DEFAULT_STYLE.accentIndex ?? 0;
  const accentColor = `var(--viz-color-${accentIdx})`;

  const items = data.items ?? [];
  const values = data.values ?? [];
  const unit = data.unit ?? "";

  // Adaptive sizing
  const n = items.length;
  const cardPadV = n >= 6 ? 14 : n >= 5 ? 18 : 22;
  const cardPadH = n >= 6 ? 28 : n >= 5 ? 32 : 36;
  const cardGap = n >= 6 ? 10 : n >= 5 ? 14 : 18;

  return (
    <div
      style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        overflow: "hidden",
      }}
    >
      {/* 너비 규칙: fit-content, minWidth 40%, maxWidth 95% — 모든 카드 동일 너비 */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: cardGap,
          width: "fit-content",
          minWidth: "40%",
          maxWidth: "95%",
        }}
      >
        {items.map((item, i) => {
          // ── Phase 1: 등장 (위→아래 순차 스태거) ──
          const ENTRANCE_BASE = 8;
          const ENTRANCE_STAGGER = 4;
          const FADE_IN = 12;
          const entranceDelay = ENTRANCE_BASE + i * ENTRANCE_STAGGER;
          const itemOpacity = interpolate(frame, [entranceDelay, entranceDelay + FADE_IN], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          const itemSlide = interpolate(frame, [entranceDelay, entranceDelay + FADE_IN], [-20, 0], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });

          // ── Phase 2: 타임스탬프 기반 강조 ──
          const syncDelay = calcItemDelay(i, fps, vizAnimation, 0, 0);
          const hl = useHighlight(frame, syncDelay);

          const isLast = i === items.length - 1;
          const color = `var(--viz-color-${i % 10})`;
          const animatedValue = countUpValue(frame, entranceDelay, 20, values[i] ?? 0, easingFn);

          // 강조 스타일
          const scale = 1 + hl * 0.025;
          const shadowBlur = 20 + hl * 20;
          const shadowAlpha = 0.08 + hl * 0.14;
          const borderW = 5 + hl * 3;

          // For hex alpha calculations on accent/color, use DEFAULT_STYLE.colors
          const rawColor = DEFAULT_STYLE.colors[i % DEFAULT_STYLE.colors.length];
          const rawAccent = DEFAULT_STYLE.colors[accentIdx];
          const bgTint = hl > 0 ? `${rawColor}${Math.round(hl * 10).toString(16).padStart(2, "0")}` : "transparent";

          return (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "center",
                padding: `${cardPadV}px ${cardPadH}px`,
                background: isLast
                  ? `linear-gradient(135deg, ${rawAccent}${Math.round(15 + hl * 10).toString(16).padStart(2, "0")}, ${rawAccent}08)`
                  : `linear-gradient(135deg, ${bgTint}, var(--viz-card-bg))`,
                borderLeft: isLast ? undefined : `${borderW}px solid ${color}`,
                border: isLast ? `${3 + hl * 2}px solid ${accentColor}` : undefined,
                borderRadius: "var(--viz-card-radius)",
                boxShadow: `0 4px ${shadowBlur}px rgba(61,59,47,${shadowAlpha})`,
                opacity: itemOpacity,
                transform: `translateY(${itemSlide}px) scale(${scale})`,
                transformOrigin: "left center",
              }}
            >
              <span style={{ flex: 1, color: "var(--viz-text)", fontSize: "var(--viz-label-size)", fontWeight: "var(--viz-label-weight)" }}>
                {item}
              </span>
              <span style={{ color: isLast ? accentColor : "var(--viz-text)", fontSize: "var(--viz-subtitle-size)", fontWeight: "var(--viz-title-weight)", marginLeft: 24 }}>
                {animatedValue.toLocaleString()}{unit}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// SplitBackground removed — VS mode now uses full-height panel layout
