import React from "react";
import { AbsoluteFill, Img, useCurrentFrame, interpolate } from "remotion";
import { STYLE as DEFAULT_STYLE, TYPO as DEFAULT_TYPO } from "./vizStyles";
import { resolveAsset } from "../utils/resolveAsset";
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

export const SlideHighlight: React.FC<Props> = ({ data, durationInFrames, fps, vizAnimation }) => {
  const frame = useCurrentFrame();
  const highlightText = data.items?.[0] ?? "";
  const sourceText = data.source ?? "";
  const imagePath =
    typeof data.imagePath === "string" ? data.imagePath : undefined;
  const hasImage = !!imagePath;

  const easingFn = resolveEasing(vizAnimation?.easing);
  const accentColor = DEFAULT_STYLE.colors[DEFAULT_STYLE.accentIndex ?? 0];

  // ── Phase 1: 등장 ──
  const ENTRANCE_BASE = 8;
  const FADE_IN = 12;
  const textOpacity = interpolate(frame, [ENTRANCE_BASE, ENTRANCE_BASE + FADE_IN], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: easingFn,
  });
  const textSlide = interpolate(frame, [ENTRANCE_BASE, ENTRANCE_BASE + FADE_IN], [-20, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: easingFn,
  });
  const sourceOpacity = interpolate(frame, [ENTRANCE_BASE + 10, ENTRANCE_BASE + 22], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // 하이라이트 바 스윕 (등장과 함께)
  const highlightWidth = interpolate(frame, [ENTRANCE_BASE + 4, ENTRANCE_BASE + 4 + FADE_IN], [0, 100], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: easingFn,
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
  const textScale = 1 + hl * 0.015;
  const glowFilter = hl > 0 ? `drop-shadow(0 0 ${8 + hl * 16}px ${accentColor}40)` : undefined;

  // Unique background: radial glow
  const bg = (
    <AbsoluteFill>
      <div
        style={{
          width: "100%",
          height: "100%",
          background: `radial-gradient(ellipse at center, ${accentColor}12 0%, transparent 70%)`,
        }}
      />
    </AbsoluteFill>
  );

  return (
    <VizShell
      title={data.title}
      source={undefined}
      durationInFrames={durationInFrames}
      vizAnimation={vizAnimation}
      background={bg}
      hideTitle
    >
      <div style={{ flex: 1, display: "flex", flexDirection: "row" }}>
        {/* Optional image */}
        {hasImage && (
          <div
            style={{
              width: "40%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              paddingRight: "4%",
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

        {/* Highlight content */}
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
              opacity: textOpacity,
              transform: `translateY(${textSlide}px) scale(${textScale})`,
              transformOrigin: "center center",
              maxWidth: hasImage ? "100%" : "80%",
              position: "relative",
              filter: glowFilter,
            }}
          >
            {/* Highlighter background effect */}
            <div
              style={{
                position: "absolute",
                bottom: "8%",
                left: "-2%",
                width: `${highlightWidth}%`,
                height: "35%",
                background: `${accentColor}35`,
                borderRadius: 4,
                zIndex: 0,
              }}
            />

            {/* Highlight text */}
            <div
              style={{
                position: "relative",
                zIndex: 1,
                color: "var(--viz-text)",
                fontSize: "var(--viz-hero-size)",
                fontWeight: "var(--viz-hero-weight)" as any,
                fontFamily: "var(--viz-title-font)",
                lineHeight: 1.4,
                letterSpacing: "var(--viz-hero-tracking)",
              }}
            >
              {highlightText.split("\\n").map((line, i) => (
                <React.Fragment key={i}>
                  {i > 0 && <br />}
                  {line}
                </React.Fragment>
              ))}
            </div>
          </div>

          {/* Source text */}
          {sourceText && (
            <div
              style={{
                marginTop: 32,
                color: "var(--viz-subtitle)",
                fontSize: DEFAULT_TYPO.subtitle.size - 6,
                fontWeight: "var(--viz-caption-weight)" as any,
                opacity: sourceOpacity,
              }}
            >
              {sourceText}
            </div>
          )}
        </div>
      </div>
    </VizShell>
  );
};
