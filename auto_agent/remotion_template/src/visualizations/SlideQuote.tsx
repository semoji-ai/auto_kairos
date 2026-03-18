import React from "react";
import { AbsoluteFill, Img, useCurrentFrame, interpolate } from "remotion";
import { STYLE as DEFAULT_STYLE, TYPO as DEFAULT_TYPO } from "./vizStyles";
import { resolveAsset } from "../utils/resolveAsset";
import { resolveEasing } from "../utils/easingMap";
import { calcItemDelay, msToFrames } from "../utils/syncDelay";
import { VizShell } from "./VizShell";
import type { VisualizationData, VizAnimationConfig } from "../types/manifest";

interface Props {
  data: VisualizationData;
  durationInFrames: number;
  fps: number;
  vizAnimation?: VizAnimationConfig;
}

export const SlideQuote: React.FC<Props> = ({ data, durationInFrames, fps, vizAnimation }) => {
  const frame = useCurrentFrame();
  const quoteText = data.items?.[0] ?? "";
  const speaker = data.source ?? "";
  const imagePath =
    typeof data.imagePath === "string" ? data.imagePath : undefined;
  const hasImage = !!imagePath;

  const easingFn = resolveEasing(vizAnimation?.easing);

  // ── Phase 1: 등장 ──
  const ENTRANCE_BASE = 8;
  const FADE_IN = 12;
  const quoteOpacity = interpolate(frame, [ENTRANCE_BASE, ENTRANCE_BASE + FADE_IN], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const quoteSlide = interpolate(frame, [ENTRANCE_BASE, ENTRANCE_BASE + FADE_IN], [-20, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const speakerOpacity = interpolate(frame, [ENTRANCE_BASE + 8, ENTRANCE_BASE + 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // ── Phase 2: 타임스탬프 기반 강조 ──
  const syncDelay = calcItemDelay(0, fps, vizAnimation, 0, 0);
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
  const quoteScale = 1 + hl * 0.015;

  const quoteMarkSize = DEFAULT_TYPO.title.size * 2;
  const grad = DEFAULT_STYLE.gradients[0];

  // Unique background: large faded quotation mark watermark
  const bg = (
    <AbsoluteFill
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        opacity: 0.04,
        overflow: "hidden",
      }}
    >
      <span
        style={{
          fontSize: 600,
          fontWeight: 900,
          color: "var(--viz-text)",
          lineHeight: 1,
          userSelect: "none",
        }}
      >
        {"\u201C"}
      </span>
    </AbsoluteFill>
  );

  return (
    <VizShell
      hideTitle
      source={undefined}
      durationInFrames={durationInFrames}
      vizAnimation={vizAnimation}
      background={bg}
    >
      <div style={{ flex: 1, display: "flex", flexDirection: "row" }}>
        {/* Optional image */}
        {hasImage && (
          <div
            style={{
              width: "40%",
              display: "flex",
              alignItems: "flex-start",
              justifyContent: "center",
              paddingRight: "4%",
              paddingTop: "2%",
              opacity: interpolate(frame, [0, 20], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }),
            }}
          >
            <Img
              src={resolveAsset(imagePath!)}
              style={{
                maxWidth: "100%",
                maxHeight: "80%",
                objectFit: "cover",
                borderRadius: "var(--viz-card-radius)",
                boxShadow: "var(--viz-card-shadow)",
              }}
            />
          </div>
        )}

        {/* Quote content */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            alignItems: hasImage ? "flex-start" : "center",
            textAlign: hasImage ? "left" : "center",
          }}
        >
          <div
            style={{
              opacity: quoteOpacity,
              transform: `translateY(${quoteSlide}px) scale(${quoteScale})`,
              transformOrigin: "center center",
              maxWidth: hasImage ? "100%" : "80%",
              filter: hl > 0 ? `drop-shadow(0 0 ${8 + hl * 12}px ${grad[0]}40)` : undefined,
            }}
          >
            {/* Opening quote mark */}
            <span
              style={{
                background: `linear-gradient(135deg, ${grad[0]}, ${grad[1]})`,
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                fontSize: quoteMarkSize,
                fontWeight: 700,
                lineHeight: 0.5,
                display: "block",
                marginBottom: 20,
              }}
            >
              {"\u201C"}
            </span>

            {/* Quote text */}
            <div
              style={{
                color: "var(--viz-text)",
                fontSize: "var(--viz-title-size)",
                fontWeight: "var(--viz-title-weight)" as any,
                fontFamily: "var(--viz-title-font)",
                lineHeight: 1.5,
                letterSpacing: "var(--viz-title-tracking)",
              }}
            >
              {quoteText.split("\\n").map((line, i) => (
                <React.Fragment key={i}>
                  {i > 0 && <br />}
                  {line}
                </React.Fragment>
              ))}
            </div>

            {/* Closing quote mark */}
            <span
              style={{
                background: `linear-gradient(135deg, ${grad[0]}, ${grad[1]})`,
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                fontSize: quoteMarkSize,
                fontWeight: 700,
                lineHeight: 0.5,
                display: "block",
                textAlign: "right",
                marginTop: 20,
              }}
            >
              {"\u201D"}
            </span>
          </div>

          {/* Speaker */}
          <div
            style={{
              marginTop: 24,
              color: "var(--viz-subtitle)",
              fontSize: "var(--viz-subtitle-size)",
              fontWeight: "var(--viz-subtitle-weight)" as any,
              opacity: speakerOpacity,
            }}
          >
            {speaker ? `\u2014 ${speaker}` : ""}
          </div>
        </div>
      </div>
    </VizShell>
  );
};
