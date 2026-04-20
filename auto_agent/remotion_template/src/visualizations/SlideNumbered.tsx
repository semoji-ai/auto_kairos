import React from "react";
import { AbsoluteFill, Img, useCurrentFrame, interpolate } from "remotion";
import { STYLE as DEFAULT_STYLE } from "./vizStyles";
import { calcItemDelay } from "../utils/syncDelay";
import { VizShell } from "./VizShell";
import { resolveAsset } from "../utils/resolveAsset";
import type { VisualizationData, VizAnimationConfig } from "../types/manifest";

interface Props {
  data: VisualizationData;
  durationInFrames: number;
  fps: number;
  vizAnimation?: VizAnimationConfig;
}

export const SlideNumbered: React.FC<Props> = ({ data, durationInFrames, fps, vizAnimation }) => {
  const frame = useCurrentFrame();
  const items = data.items ?? [];
  const descriptions = (data as any).descriptions ?? [];
  const hasImage = !!data.imagePath && typeof data.imagePath === "string";

  const accentColor = DEFAULT_STYLE.colors[DEFAULT_STYLE.accentIndex ?? 0];

  // Adaptive sizing
  const n = items.length;
  const cardGap = n >= 6 ? 8 : n >= 5 ? 10 : 12;
  const titleSize = n >= 6 ? 30 : n >= 5 ? 32 : 36;
  const descSize = n >= 6 ? 24 : n >= 5 ? 26 : 30;
  const numSize = n >= 6 ? 32 : n >= 5 ? 36 : 40;

  // ── Image entrance animation ──
  const imgOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const imgSlide = interpolate(frame, [0, 15], [-30, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  // ── Title entrance ──
  const titleOpacity = interpolate(frame, [4, 16], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const titleSlide = interpolate(frame, [4, 16], [-12, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
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
          flexDirection: "row",
          overflow: "hidden",
          // Negative margin to counteract VizShell padding so image goes edge-to-edge
          margin: hasImage ? `0 0 0 -${6}%` : undefined,
        }}
      >
        {/* ── Left: Hero image ── */}
        {hasImage && (
          <div
            style={{
              width: 540,
              flexShrink: 0,
              position: "relative",
              overflow: "hidden",
              opacity: imgOpacity,
              transform: `translateX(${imgSlide}px)`,
            }}
          >
            <Img
              src={resolveAsset(data.imagePath as string)}
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
              }}
            />
            {/* Gradient overlay at bottom */}
            <div
              style={{
                position: "absolute",
                bottom: 0,
                left: 0,
                right: 0,
                height: "50%",
                background: `linear-gradient(to bottom, transparent, var(--viz-bg))`,
              }}
            />
          </div>
        )}

        {/* ── Right: Content panel ── */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            padding: hasImage ? "40px 48px 0 48px" : "40px 0 0 0",
            gap: 24,
            minWidth: 0,
          }}
        >
          {/* Title */}
          <div
            style={{
              opacity: titleOpacity,
              transform: `translateY(${titleSlide}px)`,
            }}
          >
            <div
              style={{
                color: "var(--viz-text)",
                fontSize: "var(--viz-title-size)",
                fontWeight: "var(--viz-title-weight)" as any,
                fontFamily: "var(--viz-title-font)",
                letterSpacing: "var(--viz-title-tracking)",
                lineHeight: 1.2,
              }}
            >
              {data.title}
            </div>
            {/* Red divider */}
            <div
              style={{
                width: 80,
                height: 3,
                background: accentColor,
                borderRadius: 2,
                marginTop: 12,
              }}
            />
          </div>

          {/* Card list */}
          <div
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              gap: cardGap,
              justifyContent: "center",
            }}
          >
            {items.map((item, i) => {
              // ── Phase 1: Entrance (top→bottom stagger) ──
              const ENTRANCE_BASE = 8;
              const ENTRANCE_STAGGER = 4;
              const FADE_IN = 12;
              const entranceDelay = ENTRANCE_BASE + i * ENTRANCE_STAGGER;
              const itemOpacity = interpolate(frame, [entranceDelay, entranceDelay + FADE_IN], [0, 1], {
                extrapolateLeft: "clamp", extrapolateRight: "clamp",
              });
              const itemSlide = interpolate(frame, [entranceDelay, entranceDelay + FADE_IN], [-20, 0], {
                extrapolateLeft: "clamp", extrapolateRight: "clamp",
              });

              // ── Phase 2: Highlight on narration sync ──
              const syncDelay = calcItemDelay(i, fps, vizAnimation, 0, 0);
              const HIGHLIGHT_IN = 8;
              const HIGHLIGHT_HOLD = 20;
              const HIGHLIGHT_OUT = 12;
              const hlStart = syncDelay;
              const hlPeak = hlStart + HIGHLIGHT_IN;
              const hlHoldEnd = hlPeak + HIGHLIGHT_HOLD;
              const hlEnd = hlHoldEnd + HIGHLIGHT_OUT;
              const hl = interpolate(
                frame,
                [hlStart, hlPeak, hlHoldEnd, hlEnd],
                [0, 1, 1, 0],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
              );

              const scale = 1 + hl * 0.025;
              const borderAlpha = Math.round(40 + hl * 80).toString(16).padStart(2, "0");

              const numStr = String(i + 1).padStart(2, "0");

              return (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 24,
                    background: "var(--viz-card-bg)",
                    padding: "24px 28px",
                    borderRadius: "var(--viz-card-radius)",
                    borderLeft: `4px solid ${accentColor}${borderAlpha}`,
                    opacity: itemOpacity,
                    transform: `translateY(${itemSlide}px) scale(${scale})`,
                    transformOrigin: "left center",
                  }}
                >
                  {/* Number */}
                  <span
                    style={{
                      color: accentColor,
                      fontSize: numSize,
                      fontWeight: 700,
                      fontFamily: "var(--viz-font)",
                      flexShrink: 0,
                      minWidth: numSize * 1.4,
                    }}
                  >
                    {numStr}
                  </span>
                  {/* Title */}
                  <span
                    style={{
                      color: "var(--viz-text)",
                      fontSize: titleSize,
                      fontWeight: 600,
                      fontFamily: "var(--viz-font)",
                      flexShrink: 0,
                    }}
                  >
                    {item}
                  </span>
                  {/* Description */}
                  {descriptions[i] && (
                    <span
                      style={{
                        color: "var(--viz-subtitle)",
                        fontSize: descSize,
                        fontWeight: 400,
                        fontFamily: "var(--viz-font)",
                      }}
                    >
                      {descriptions[i]}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </VizShell>
  );
};
