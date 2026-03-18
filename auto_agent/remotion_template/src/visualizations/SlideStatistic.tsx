import React from "react";
import { AbsoluteFill, Img, useCurrentFrame, interpolate } from "remotion";
import { STYLE as DEFAULT_STYLE } from "./vizStyles";
import { resolveAsset } from "../utils/resolveAsset";
import { resolveEasing } from "../utils/easingMap";
import { calcItemDelay } from "../utils/syncDelay";
import { countUpValue } from "../utils/countUp";
import { VizShell } from "./VizShell";
import type { VisualizationData, VizAnimationConfig } from "../types/manifest";

interface Props {
  data: VisualizationData;
  durationInFrames: number;
  fps: number;
  vizAnimation?: VizAnimationConfig;
}

/**
 * 핵심 통계 — Pencil S5 균등 그리드 레이아웃
 *
 * 헤더(타이틀 + "BY THE NUMBERS") → 빨간 축선 → N열 균등 스탯 카드
 * 각 카드: 큰 숫자(countUp) + 단위 + 라벨
 *
 * Props 매핑:
 * - items[] → 스탯 라벨 ("즉위 나이", "사망 나이", ...)
 * - values[] → countUp 대상 숫자 (12, 17, 241, 4)
 * - descriptions[] → 각 스탯 단위 ("세", "세", "년", "가지")
 *   (descriptions[0]이 단위가 아닌 컨텍스트 텍스트일 경우 data.unit 폴백)
 * - unit → 공통 단위 폴백
 *
 * 하위호환: items.length <= 1 → 기존 히어로 숫자 + 서브 배지
 */
export const SlideStatistic: React.FC<Props> = ({ data, durationInFrames, fps, vizAnimation }) => {
  const frame = useCurrentFrame();
  const easingFn = resolveEasing(vizAnimation?.easing);

  const items = data.items ?? [];
  const values = data.values ?? [];
  const descriptions = data.descriptions ?? [];
  const unit = data.unit ?? "";

  const accentColor = DEFAULT_STYLE.colors[DEFAULT_STYLE.accentIndex ?? 0];

  // Use grid layout for 2+ items
  const useGrid = items.length >= 2;

  if (!useGrid) {
    return <SlideStatisticLegacy data={data} durationInFrames={durationInFrames} fps={fps} vizAnimation={vizAnimation} />;
  }

  const n = items.length;
  const numSize = n >= 6 ? 72 : n >= 5 ? 90 : 120;
  const unitSize = n >= 6 ? 28 : n >= 5 ? 32 : 36;
  const labelSize = n >= 6 ? 28 : n >= 5 ? 32 : 36;

  // ── Header entrance ──
  const headerOpacity = interpolate(frame, [0, 12], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const headerSlide = interpolate(frame, [0, 12], [-10, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  // ── Axis line sweep ──
  const lineWidth = interpolate(frame, [4, 4 + n * 5], [0, 100], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easingFn,
  });

  return (
    <VizShell
      title={data.title}
      source={data.source}
      durationInFrames={durationInFrames}
      vizAnimation={vizAnimation}
      hideTitle
    >
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {/* ── Header ── */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-end",
            padding: "0 0 32px 0",
            opacity: headerOpacity,
            transform: `translateY(${headerSlide}px)`,
          }}
        >
          <div
            style={{
              color: "var(--viz-text)",
              fontSize: "var(--viz-title-size)",
              fontWeight: "var(--viz-title-weight)" as any,
              fontFamily: "var(--viz-title-font)",
              letterSpacing: "var(--viz-title-tracking)",
            }}
          >
            {data.title}
          </div>
          <div
            style={{
              color: accentColor,
              fontSize: "var(--viz-label-size)",
              fontWeight: 600,
              fontFamily: "var(--viz-font)",
              letterSpacing: 2,
            }}
          >
            BY THE NUMBERS
          </div>
        </div>

        {/* ── Axis line ── */}
        <div
          style={{
            width: "100%",
            height: 3,
            background: "var(--viz-border)",
            flexShrink: 0,
            position: "relative",
          }}
        >
          <div
            style={{
              height: "100%",
              width: `${lineWidth}%`,
              background: accentColor,
              borderRadius: 2,
            }}
          />
        </div>

        {/* ── Stats grid ── */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "row",
            minHeight: 0,
          }}
        >
          {items.map((label, i) => {
            const colDelay = 8 + i * 5;
            const colOpacity = interpolate(frame, [colDelay, colDelay + 12], [0, 1], {
              extrapolateLeft: "clamp", extrapolateRight: "clamp",
            });
            const colSlide = interpolate(frame, [colDelay, colDelay + 12], [20, 0], {
              extrapolateLeft: "clamp", extrapolateRight: "clamp",
            });

            // countUp
            const countStart = colDelay;
            const countDuration = 25;
            const numVal = values[i] ?? 0;
            const animated = numVal !== 0
              ? countUpValue(frame, countStart, countDuration, numVal, easingFn)
              : 0;

            // Phase 2: highlight
            const syncDelay = calcItemDelay(i, fps, vizAnimation, 0, 0);
            const hl = interpolate(
              frame,
              [syncDelay, syncDelay + 8, syncDelay + 28, syncDelay + 40],
              [0, 1, 1, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
            );
            const scale = 1 + hl * 0.03;

            // Unit: per-item from descriptions, or global unit
            const itemUnit = descriptions[i] ?? unit;

            return (
              <div
                key={i}
                style={{
                  flex: 1,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 16,
                  background: "var(--viz-card-bg)",
                  padding: "40px 36px",
                  border: `1px solid var(--viz-border)`,
                  opacity: colOpacity,
                  transform: `translateY(${colSlide}px) scale(${scale})`,
                  transformOrigin: "center center",
                  minWidth: 0,
                }}
              >
                {/* Big number */}
                <div
                  style={{
                    color: accentColor,
                    fontSize: numSize,
                    fontWeight: 700,
                    fontFamily: "var(--viz-font)",
                    lineHeight: 1,
                  }}
                >
                  {numVal !== 0 ? animated.toLocaleString() : label}
                </div>
                {/* Unit */}
                {itemUnit && (
                  <div
                    style={{
                      color: "var(--viz-subtitle)",
                      fontSize: unitSize,
                      fontWeight: 500,
                      fontFamily: "var(--viz-font)",
                    }}
                  >
                    {itemUnit}
                  </div>
                )}
                {/* Label */}
                <div
                  style={{
                    color: "var(--viz-text)",
                    fontSize: labelSize,
                    fontWeight: 600,
                    fontFamily: "var(--viz-font)",
                    textAlign: "center",
                  }}
                >
                  {label}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </VizShell>
  );
};

/**
 * Legacy layout: 히어로 숫자 1개 + 서브 배지 (items.length <= 1)
 */
const SlideStatisticLegacy: React.FC<Props> = ({ data, durationInFrames, fps, vizAnimation }) => {
  const frame = useCurrentFrame();
  const easingFn = resolveEasing(vizAnimation?.easing);

  const items = data.items ?? [];
  const values = data.values ?? [];
  const unit = data.unit ?? "";
  const descriptions = data.descriptions ?? [];
  const contextLabel = descriptions[0] ?? "";

  const mainDisplay = items[0] ?? "";
  const mainValue = values[0] ?? 0;
  const hasCountUp = mainValue !== 0;

  const accentColor = DEFAULT_STYLE.colors[DEFAULT_STYLE.accentIndex ?? 0];

  const MAIN_START = 5;
  const MAIN_DURATION = 25;
  const FADE_IN = 12;

  const mainAnimated = hasCountUp
    ? countUpValue(frame, MAIN_START, MAIN_DURATION, mainValue, easingFn)
    : 0;
  const mainOpacity = interpolate(frame, [MAIN_START, MAIN_START + FADE_IN], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  const syncDelay = calcItemDelay(0, fps, vizAnimation, 0, 0);
  const hl = interpolate(
    frame,
    [syncDelay, syncDelay + 8, syncDelay + 28, syncDelay + 40],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const mainScale = 1 + hl * 0.03;

  const mainText = hasCountUp ? mainAnimated.toLocaleString() : mainDisplay;

  return (
    <VizShell
      title={data.title}
      source={data.source}
      durationInFrames={durationInFrames}
      vizAnimation={vizAnimation}
    >
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          gap: 12,
        }}
      >
        {contextLabel && (
          <div style={{ color: "var(--viz-subtitle)", fontSize: "var(--viz-label-size)", fontWeight: "var(--viz-label-weight)" as any }}>
            {contextLabel}
          </div>
        )}
        <div
          style={{
            opacity: mainOpacity,
            transform: `scale(${mainScale})`,
            display: "flex",
            alignItems: "baseline",
            gap: 8,
          }}
        >
          <span
            style={{
              color: "var(--viz-text)",
              fontSize: 110,
              fontWeight: "var(--viz-hero-weight)" as any,
              fontFamily: "var(--viz-title-font)",
              letterSpacing: "-0.03em",
              lineHeight: 1,
            }}
          >
            {mainText}
          </span>
          {unit && (
            <span style={{ color: "var(--viz-subtitle)", fontSize: "var(--viz-title-size)", fontWeight: "var(--viz-subtitle-weight)" as any }}>
              {unit}
            </span>
          )}
        </div>
      </div>
    </VizShell>
  );
};
