import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import { useDesignTokens } from "../contexts/DesignTokenContext";
import { calcItemDelay } from "../utils/syncDelay";
import { VizShell } from "./VizShell";
import type { VisualizationData, VizAnimationConfig } from "../types/manifest";

interface Props {
  data: VisualizationData;
  durationInFrames: number;
  fps: number;
  vizAnimation?: VizAnimationConfig;
}

export const SlideList: React.FC<Props> = ({ data, durationInFrames, fps, vizAnimation }) => {
  const { STYLE, TYPO } = useDesignTokens();
  const frame = useCurrentFrame();
  const items = data.items ?? [];

  // 아이템 수에 따른 적응형 사이징
  const n = items.length;
  const cardPadV = n >= 6 ? 14 : n >= 5 ? 18 : 24;
  const cardPadH = n >= 6 ? 32 : n >= 5 ? 36 : 40;
  const cardGap = n >= 6 ? 10 : n >= 5 ? 14 : 20;
  const textSize = n >= 6 ? 30 : n >= 5 ? 34 : 38;
  const numSize = n >= 6 ? 22 : n >= 5 ? 24 : 28;

  // Unique background: left gradient strip
  const bg = (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          bottom: 0,
          width: "2.5%",
          background: `linear-gradient(to bottom, ${STYLE.colors[STYLE.accentIndex ?? 0]}30, ${STYLE.colors[2]}30)`,
        }}
      />
    </AbsoluteFill>
  );

  return (
    <VizShell
      title={data.title}
      source={data.source}
      durationInFrames={durationInFrames}
      vizAnimation={vizAnimation}
      background={bg}
    >
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        {/* 너비 규칙: fit-content로 가장 긴 카드 기준 자동 결정,
            minWidth/maxWidth로 극단값 방지.
            같은 시각화 내 모든 카드가 동일 너비 유지. */}
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
          // syncPoint에서 해당 아이템의 나레이션 시작 시점을 가져옴
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

          const color = STYLE.colors[i % STYLE.colors.length];

          // 강조 스타일
          const scale = 1 + hl * 0.025;
          const shadowBlur = 20 + hl * 20;
          const shadowAlpha = 0.08 + hl * 0.14;
          const borderW = 5 + hl * 3;
          const bgTint = hl > 0 ? `${color}${Math.round(hl * 10).toString(16).padStart(2, "0")}` : "transparent";

          return (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 18,
                background: `linear-gradient(135deg, ${bgTint}, ${STYLE.cardBg})`,
                padding: `${cardPadV}px ${cardPadH}px`,
                borderRadius: STYLE.cardRadius,
                boxShadow: `0 4px ${shadowBlur}px rgba(61,59,47,${shadowAlpha})`,
                borderLeft: `${borderW}px solid ${color}`,
                opacity: itemOpacity,
                transform: `translateX(${itemSlide}px) scale(${scale})`,
                transformOrigin: "left center",
              }}
            >
              {/* 넘버링 배지 */}
              <div
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 8,
                  background: color + (hl > 0 ? "40" : "18"),
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: numSize,
                  fontWeight: 700,
                  color: color,
                  flexShrink: 0,
                }}
              >
                {i + 1}
              </div>
              <span
                style={{
                  color: STYLE.text,
                  fontSize: textSize,
                  fontWeight: TYPO.label.weight,
                  lineHeight: 1.45,
                }}
              >
                {item.split("\\n").map((line, j) => (
                  <React.Fragment key={j}>
                    {j > 0 && <br />}
                    {line}
                  </React.Fragment>
                ))}
              </span>
            </div>
          );
        })}
        </div>
      </div>
    </VizShell>
  );
};
