import React from "react";
import { AbsoluteFill, Img, useCurrentFrame, interpolate } from "remotion";
import { STYLE as DEFAULT_STYLE } from "./vizStyles";
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

/**
 * 프로세스/흐름도 슬라이드
 *
 * - items: 단계 라벨
 * - descriptions: 단계 설명 (선택)
 * - 가로(≤5개) 또는 세로(6+개) 자동 전환
 */
export const SlideProcess: React.FC<Props> = ({ data, durationInFrames, fps, vizAnimation }) => {
  const frame = useCurrentFrame();
  const easingFn = resolveEasing(vizAnimation?.easing);

  const imagePath =
    typeof data.imagePath === "string" ? data.imagePath : undefined;
  const hasImage = !!imagePath;

  const items = data.items ?? [];
  const descriptions = data.descriptions ?? [];
  const n = items.length;
  const isVertical = n >= 6;

  // Adaptive sizing
  const cardWidth = isVertical ? "85%" : `${Math.min(220, 800 / n)}px`;
  const stepSize = isVertical ? 40 : n >= 5 ? 36 : 44;
  const textSize = isVertical ? 28 : n >= 5 ? 24 : 28;
  const descSize = isVertical ? 22 : n >= 5 ? 18 : 22;

  // ── Animation constants ──
  const ENTRANCE_BASE = 8;
  const ENTRANCE_STAGGER = 6;
  const FADE_IN = 12;
  const ARROW_DELAY = 4; // 화살표는 카드 등장 후 약간 지연

  // Background: subtle flow pattern
  const bg = (
    <AbsoluteFill style={{ opacity: 0.03 }}>
      <div
        style={{
          width: "100%",
          height: "100%",
          backgroundImage: isVertical
            ? `repeating-linear-gradient(180deg, ${DEFAULT_STYLE.border}15 0px, transparent 1px, transparent 60px)`
            : `repeating-linear-gradient(90deg, ${DEFAULT_STYLE.border}15 0px, transparent 1px, transparent 60px)`,
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
      <div style={{ flex: 1, display: "flex", flexDirection: "row" }}>
        {/* Optional image */}
        {hasImage && (
          <div
            style={{
              width: "30%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              paddingRight: "2%",
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
                maxHeight: "85%",
                objectFit: "cover",
                borderRadius: "var(--viz-card-radius)",
                boxShadow: "var(--viz-card-shadow)",
              }}
            />
          </div>
        )}

      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <div
          style={{
            display: "flex",
            flexDirection: isVertical ? "column" : "row",
            alignItems: "center",
            justifyContent: "center",
            gap: 0,
            width: isVertical ? "85%" : "95%",
          }}
        >
          {items.map((item, i) => {
            const entranceDelay = ENTRANCE_BASE + i * ENTRANCE_STAGGER;
            const desc = descriptions[i] ?? "";
            const color = DEFAULT_STYLE.colors[i % DEFAULT_STYLE.colors.length];
            const grad = DEFAULT_STYLE.gradients[i % DEFAULT_STYLE.gradients.length];
            const isLast = i === n - 1;

            // 카드 등장
            const cardOpacity = interpolate(frame, [entranceDelay, entranceDelay + FADE_IN], [0, 1], {
              extrapolateLeft: "clamp", extrapolateRight: "clamp",
            });
            const cardSlide = isVertical
              ? interpolate(frame, [entranceDelay, entranceDelay + FADE_IN], [-20, 0], {
                  extrapolateLeft: "clamp", extrapolateRight: "clamp",
                })
              : interpolate(frame, [entranceDelay, entranceDelay + FADE_IN], [-15, 0], {
                  extrapolateLeft: "clamp", extrapolateRight: "clamp",
                });

            // 화살표 드로잉 (SVG stroke-dashoffset)
            const arrowStart = entranceDelay + ARROW_DELAY;
            const arrowProgress = interpolate(frame, [arrowStart, arrowStart + 10], [0, 1], {
              extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easingFn,
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

            const scale = 1 + hl * 0.025;
            const shadowBlur = 16 + hl * 20;
            const shadowAlpha = 0.06 + hl * 0.14;

            return (
              <React.Fragment key={i}>
                {/* 단계 카드 */}
                <div
                  style={{
                    display: "flex",
                    flexDirection: isVertical ? "row" : "column",
                    alignItems: "center",
                    gap: isVertical ? 16 : 10,
                    width: isVertical ? "100%" : cardWidth,
                    padding: isVertical ? "14px 20px" : "20px 16px",
                    background: `linear-gradient(135deg, ${hl > 0 ? `${color}0a` : "transparent"}, var(--viz-card-bg))`,
                    borderRadius: "var(--viz-card-radius)",
                    boxShadow: `0 3px ${shadowBlur}px rgba(61,59,47,${shadowAlpha})`,
                    border: hl > 0 ? `2px solid ${color}40` : `1px solid var(--viz-grid)`,
                    opacity: cardOpacity,
                    transform: isVertical
                      ? `translateY(${cardSlide}px) scale(${scale})`
                      : `translateX(${cardSlide}px) scale(${scale})`,
                    transformOrigin: "center center",
                    flexShrink: 0,
                  }}
                >
                  {/* 스텝 번호 배지 */}
                  <div
                    style={{
                      width: stepSize,
                      height: stepSize,
                      borderRadius: "50%",
                      background: `linear-gradient(135deg, ${grad[0]}, ${grad[1]})`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "white",
                      fontSize: Math.round(stepSize * 0.45),
                      fontWeight: "var(--viz-title-weight)" as any,
                      flexShrink: 0,
                      boxShadow: `0 3px 8px ${grad[0]}30`,
                    }}
                  >
                    {i + 1}
                  </div>

                  <div
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      alignItems: isVertical ? "flex-start" : "center",
                      gap: 4,
                      flex: isVertical ? 1 : undefined,
                    }}
                  >
                    <span
                      style={{
                        color: "var(--viz-text)",
                        fontSize: textSize,
                        fontWeight: "var(--viz-label-weight)" as any,
                        textAlign: isVertical ? "left" : "center",
                        lineHeight: 1.3,
                      }}
                    >
                      {item}
                    </span>
                    {desc && (
                      <span
                        style={{
                          color: "var(--viz-subtitle)",
                          fontSize: descSize,
                          fontWeight: "var(--viz-caption-weight)" as any,
                          textAlign: isVertical ? "left" : "center",
                          lineHeight: 1.4,
                        }}
                      >
                        {desc}
                      </span>
                    )}
                  </div>
                </div>

                {/* 화살표 (마지막 아이템 뒤에는 안 그림) */}
                {!isLast && (
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                      padding: isVertical ? "4px 0" : "0 2px",
                    }}
                  >
                    <svg
                      width={isVertical ? 28 : 36}
                      height={isVertical ? 28 : 24}
                      viewBox={isVertical ? "0 0 28 28" : "0 0 36 24"}
                    >
                      {isVertical ? (
                        // 세로 화살표 (↓)
                        <path
                          d="M14 4 L14 20 M8 16 L14 22 L20 16"
                          fill="none"
                          stroke={color}
                          strokeWidth={2.5}
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeDasharray={40}
                          strokeDashoffset={40 * (1 - arrowProgress)}
                        />
                      ) : (
                        // 가로 화살표 (→)
                        <path
                          d="M4 12 L28 12 M22 6 L30 12 L22 18"
                          fill="none"
                          stroke={color}
                          strokeWidth={2.5}
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeDasharray={50}
                          strokeDashoffset={50 * (1 - arrowProgress)}
                        />
                      )}
                    </svg>
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>
      </div>
    </VizShell>
  );
};
