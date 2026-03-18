import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import { STYLE as DEFAULT_STYLE } from "./vizStyles";
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
 * 요약/리캡 카드
 *
 * - items: 요점들
 * - descriptions[0]: 결론/takeaway 메시지 (선택)
 */
export const SlideSummary: React.FC<Props> = ({ data, durationInFrames, fps, vizAnimation }) => {
  const frame = useCurrentFrame();
  const items = data.items ?? [];
  const descriptions = data.descriptions ?? [];
  const takeaway = descriptions[0] ?? "";

  const n = items.length;
  const useGrid = n >= 4;
  const cols = useGrid ? 2 : 1;

  // Adaptive sizing
  const cardPadV = n >= 6 ? 14 : n >= 5 ? 16 : 20;
  const cardPadH = n >= 6 ? 20 : n >= 5 ? 24 : 28;
  const cardGap = n >= 6 ? 10 : n >= 5 ? 12 : 16;
  const textSize = n >= 6 ? 26 : n >= 5 ? 30 : 34;

  const accentColor = DEFAULT_STYLE.colors[DEFAULT_STYLE.accentIndex ?? 0];

  // ── Phase 1: 등장 ──
  const TITLE_FADE = 15;
  const CARD_BASE = 12;
  const CARD_STAGGER = 3; // 빠른 스태거 (요약은 밀도 높게)
  const FADE_IN = 10;
  const TAKEAWAY_START = CARD_BASE + n * CARD_STAGGER + 8;

  // 타이틀 이중 밑줄
  const titleOpacity = interpolate(frame, [0, TITLE_FADE], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  // Takeaway
  const takeawayOpacity = takeaway
    ? interpolate(frame, [TAKEAWAY_START, TAKEAWAY_START + FADE_IN + 4], [0, 1], {
        extrapolateLeft: "clamp", extrapolateRight: "clamp",
      })
    : 0;
  const takeawaySlide = takeaway
    ? interpolate(frame, [TAKEAWAY_START, TAKEAWAY_START + FADE_IN + 4], [15, 0], {
        extrapolateLeft: "clamp", extrapolateRight: "clamp",
      })
    : 0;

  // Background: subtle grid pattern
  const bg = (
    <AbsoluteFill style={{ opacity: 0.03 }}>
      <div
        style={{
          width: "100%",
          height: "100%",
          backgroundImage: `
            repeating-linear-gradient(0deg, ${DEFAULT_STYLE.border}15, ${DEFAULT_STYLE.border}15 1px, transparent 1px, transparent 40px),
            repeating-linear-gradient(90deg, ${DEFAULT_STYLE.border}15, ${DEFAULT_STYLE.border}15 1px, transparent 1px, transparent 40px)
          `,
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
          gap: 24,
        }}
      >
        {/* 카드 그리드 */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: useGrid ? "1fr 1fr" : "1fr",
            gap: cardGap,
            width: useGrid ? "92%" : "fit-content",
            minWidth: useGrid ? undefined : "40%",
            maxWidth: "95%",
          }}
        >
          {items.map((item, i) => {
            // Grid stagger: 좌→우, 위→아래
            const row = Math.floor(i / cols);
            const col = i % cols;
            const gridIndex = useGrid ? row * 2 + col : i;
            const entranceDelay = CARD_BASE + gridIndex * CARD_STAGGER;

            const itemOpacity = interpolate(frame, [entranceDelay, entranceDelay + FADE_IN], [0, 1], {
              extrapolateLeft: "clamp", extrapolateRight: "clamp",
            });
            const itemSlide = interpolate(frame, [entranceDelay, entranceDelay + FADE_IN], [-15, 0], {
              extrapolateLeft: "clamp", extrapolateRight: "clamp",
            });

            // Phase 2: 하이라이트
            const syncDelay = calcItemDelay(i, fps, vizAnimation, 0, 0);
            const HIGHLIGHT_IN = 8;
            const HIGHLIGHT_HOLD = 20;
            const HIGHLIGHT_OUT = 12;
            const hl = interpolate(
              frame,
              [syncDelay, syncDelay + HIGHLIGHT_IN, syncDelay + HIGHLIGHT_IN + HIGHLIGHT_HOLD, syncDelay + HIGHLIGHT_IN + HIGHLIGHT_HOLD + HIGHLIGHT_OUT],
              [0, 1, 1, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
            );

            const color = DEFAULT_STYLE.colors[i % DEFAULT_STYLE.colors.length];
            const grad = DEFAULT_STYLE.gradients[i % DEFAULT_STYLE.gradients.length];
            const scale = 1 + hl * 0.02;
            const shadowBlur = 16 + hl * 20;
            const shadowAlpha = 0.06 + hl * 0.12;
            const borderTopW = 4 + hl * 2;

            return (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 14,
                  background: `linear-gradient(135deg, ${hl > 0 ? `${color}0a` : "transparent"}, var(--viz-card-bg))`,
                  borderTop: `${borderTopW}px solid ${color}`,
                  borderRadius: "var(--viz-card-radius)",
                  padding: `${cardPadV}px ${cardPadH}px`,
                  boxShadow: `0 3px ${shadowBlur}px rgba(61,59,47,${shadowAlpha})`,
                  opacity: itemOpacity,
                  transform: `translateY(${itemSlide}px) scale(${scale})`,
                  transformOrigin: "center top",
                }}
              >
                {/* 번호 배지 */}
                <div
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: "50%",
                    background: `linear-gradient(135deg, ${grad[0]}, ${grad[1]})`,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "white",
                    fontSize: 16,
                    fontWeight: 700,
                    flexShrink: 0,
                    marginTop: 2,
                  }}
                >
                  {i + 1}
                </div>
                <span
                  style={{
                    color: "var(--viz-text)",
                    fontSize: textSize,
                    fontWeight: "var(--viz-label-weight)" as any,
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

        {/* Takeaway 메시지 */}
        {takeaway && (
          <div
            style={{
              marginTop: 12,
              padding: "16px 32px",
              borderRadius: 12,
              background: `${accentColor}12`,
              border: `2px solid ${accentColor}30`,
              opacity: takeawayOpacity,
              transform: `translateY(${takeawaySlide}px)`,
            }}
          >
            <span
              style={{
                color: "var(--viz-text)",
                fontSize: "var(--viz-subtitle-size)",
                fontWeight: "var(--viz-title-weight)" as any,
                fontFamily: "var(--viz-title-font)",
              }}
            >
              {takeaway}
            </span>
          </div>
        )}
      </div>
    </VizShell>
  );
};
