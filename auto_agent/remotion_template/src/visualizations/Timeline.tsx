import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { useDesignTokens } from "../contexts/DesignTokenContext";
import { resolveEasing } from "../utils/easingMap";
import { calcItemDelay } from "../utils/syncDelay";
import { VizShell } from "./VizShell";
import type { VisualizationData, VizAnimationConfig } from "../types/manifest";

interface Props {
  data: VisualizationData;
  durationInFrames: number;
  fps: number;
  vizAnimation?: VizAnimationConfig;
}

/**
 * 타임라인 — Pencil S4 가로 카드 레이아웃
 *
 * 헤더(타이틀 + 날짜 범위) → 빨간 축선 → 가로 N열 카드
 * 각 카드: 연도 + 이미지 플레이스홀더 + 제목 + 설명
 */
export const Timeline: React.FC<Props> = ({ data, durationInFrames, fps, vizAnimation }) => {
  const { STYLE, TYPO, VIZ_FONT, VIZ_TITLE_FONT } = useDesignTokens();
  const frame = useCurrentFrame();
  const items = data.items ?? [];
  const values = data.values ?? [];
  const descriptions = (data as any).descriptions ?? [];

  const easingFn = resolveEasing(vizAnimation?.easing);
  const accentColor = STYLE.colors[STYLE.accentIndex ?? 0];

  const n = items.length;
  const cardGap = n >= 6 ? 4 : n >= 5 ? 6 : 8;
  const yearSize = n >= 6 ? 32 : n >= 5 ? 36 : 40;
  const titleSize = n >= 6 ? 28 : n >= 5 ? 30 : 34;
  const descSize = n >= 6 ? 24 : n >= 5 ? 26 : 30;
  const imgHeight = n >= 6 ? 140 : n >= 5 ? 160 : 200;

  // Date range text from first/last values
  const firstVal = values[0] != null ? String(values[0]) : "";
  const lastVal = values[values.length - 1] != null ? String(values[values.length - 1]) : "";
  const rangeText = firstVal && lastVal && firstVal !== lastVal ? `${firstVal} — ${lastVal}` : "";

  // ── Header entrance ──
  const headerOpacity = interpolate(frame, [0, 12], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const headerSlide = interpolate(frame, [0, 12], [-10, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  // ── Axis line sweep ──
  const lineWidth = interpolate(frame, [4, 4 + n * 6], [0, 100], {
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
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          gap: 32,
          overflow: "hidden",
        }}
      >
        {/* ── Header: Title + Range ── */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-end",
            opacity: headerOpacity,
            transform: `translateY(${headerSlide}px)`,
          }}
        >
          <div
            style={{
              color: STYLE.text,
              fontSize: TYPO.title.size,
              fontWeight: TYPO.title.weight,
              fontFamily: VIZ_TITLE_FONT,
              letterSpacing: TYPO.title.letterSpacing,
            }}
          >
            {data.title}
          </div>
          {rangeText && (
            <div
              style={{
                color: accentColor,
                fontSize: 36,
                fontWeight: 700,
                fontFamily: VIZ_FONT,
              }}
            >
              {rangeText}
            </div>
          )}
        </div>

        {/* ── Axis line ── */}
        <div
          style={{
            width: "100%",
            height: 3,
            background: STYLE.border,
            position: "relative",
            flexShrink: 0,
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

        {/* ── Event columns ── */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "row",
            gap: cardGap,
            minHeight: 0,
          }}
        >
          {items.map((item, i) => {
            // ── Phase 1: Entrance (left→right stagger) ──
            const ENTRANCE_BASE = 8;
            const ENTRANCE_STAGGER = 5;
            const FADE_IN = 12;
            const entranceDelay = ENTRANCE_BASE + i * ENTRANCE_STAGGER;
            const colOpacity = interpolate(frame, [entranceDelay, entranceDelay + FADE_IN], [0, 1], {
              extrapolateLeft: "clamp", extrapolateRight: "clamp",
            });
            const colSlide = interpolate(frame, [entranceDelay, entranceDelay + FADE_IN], [30, 0], {
              extrapolateLeft: "clamp", extrapolateRight: "clamp",
            });

            // ── Phase 2: Highlight ──
            const syncDelay = calcItemDelay(i, fps, vizAnimation, 0, 0);
            const hl = interpolate(
              frame,
              [syncDelay, syncDelay + 8, syncDelay + 28, syncDelay + 40],
              [0, 1, 1, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
            );

            const scale = 1 + hl * 0.02;
            const yearText = values[i] != null ? String(values[i]) : "";
            const itemText = String(item);
            const descText = descriptions[i] ?? "";

            return (
              <div
                key={i}
                style={{
                  flex: 1,
                  display: "flex",
                  flexDirection: "column",
                  gap: 12,
                  background: STYLE.cardBg,
                  padding: "24px 20px",
                  borderRadius: STYLE.cardRadius,
                  opacity: colOpacity,
                  transform: `translateX(${colSlide}px) scale(${scale})`,
                  transformOrigin: "bottom center",
                  minWidth: 0,
                  overflow: "hidden",
                }}
              >
                {/* Year */}
                {yearText && (
                  <div
                    style={{
                      color: accentColor,
                      fontSize: yearSize,
                      fontWeight: 700,
                      fontFamily: VIZ_FONT,
                    }}
                  >
                    {yearText}
                  </div>
                )}

                {/* Image placeholder */}
                <div
                  style={{
                    width: "100%",
                    height: imgHeight,
                    background: STYLE.border,
                    borderRadius: 8,
                    flexShrink: 0,
                  }}
                />

                {/* Title */}
                <div
                  style={{
                    color: STYLE.text,
                    fontSize: titleSize,
                    fontWeight: 600,
                    fontFamily: VIZ_FONT,
                    lineHeight: 1.3,
                  }}
                >
                  {itemText}
                </div>

                {/* Description */}
                {descText && (
                  <div
                    style={{
                      color: STYLE.subtitle,
                      fontSize: descSize,
                      fontWeight: 400,
                      fontFamily: VIZ_FONT,
                      lineHeight: 1.4,
                    }}
                  >
                    {descText}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </VizShell>
  );
};
