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

// 메달 색상
const MEDAL_COLORS = {
  1: { bg: "linear-gradient(135deg, #FFD700, #FFA500)", shadow: "#FFD70060", text: "#FFFFFF" },
  2: { bg: "linear-gradient(135deg, #C0C0C0, #A8A8A8)", shadow: "#C0C0C060", text: "#FFFFFF" },
  3: { bg: "linear-gradient(135deg, #CD7F32, #A0522D)", shadow: "#CD7F3260", text: "#FFFFFF" },
} as const;

/**
 * 순위/리더보드 슬라이드
 *
 * - items: 순위별 항목 (1위→N위 순서)
 * - values: 각 항목의 수치
 * - unit: 단위
 * - 역순 공개 모드: itemSyncPoints 있으면 자동으로 카운트다운 느낌
 */
export const SlideRanking: React.FC<Props> = ({ data, durationInFrames, fps, vizAnimation }) => {
  const frame = useCurrentFrame();
  const easingFn = resolveEasing(vizAnimation?.easing);

  const imagePath =
    typeof data.imagePath === "string" ? data.imagePath : undefined;
  const hasImage = !!imagePath;

  const items = data.items ?? [];
  const values = data.values ?? [];
  const unit = data.unit ?? "";
  const maxValue = Math.max(...values, 1);

  const n = items.length;
  const cardPadV = n >= 7 ? 10 : n >= 5 ? 14 : 18;
  const cardGap = n >= 7 ? 8 : n >= 5 ? 12 : 16;
  const textSize = n >= 7 ? 26 : n >= 5 ? 30 : 34;
  const rankBadgeSize = n >= 7 ? 38 : n >= 5 ? 44 : 52;

  const accentColor = DEFAULT_STYLE.colors[DEFAULT_STYLE.accentIndex ?? 0];

  // ── Phase 1: 등장 (위→아래 순차) ──
  const ENTRANCE_BASE = 8;
  const ENTRANCE_STAGGER = 4;
  const FADE_IN = 12;

  // Background: subtle accent glow
  const bg = (
    <AbsoluteFill>
      <div
        style={{
          width: "100%",
          height: "100%",
          background: `radial-gradient(ellipse at 30% 30%, ${MEDAL_COLORS[1].shadow} 0%, transparent 50%)`,
          opacity: 0.3,
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
            flexDirection: "column",
            gap: cardGap,
            width: "fit-content",
            minWidth: hasImage ? "80%" : "50%",
            maxWidth: "95%",
          }}
        >
          {items.map((item, i) => {
            const rank = i + 1;
            const isTop3 = rank <= 3;
            const isFirst = rank === 1;
            const medal = MEDAL_COLORS[rank as 1 | 2 | 3];

            const entranceDelay = ENTRANCE_BASE + i * ENTRANCE_STAGGER;
            const itemOpacity = interpolate(frame, [entranceDelay, entranceDelay + FADE_IN], [0, 1], {
              extrapolateLeft: "clamp", extrapolateRight: "clamp",
            });
            const itemSlide = interpolate(frame, [entranceDelay, entranceDelay + FADE_IN], [25, 0], {
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

            const color = isTop3 ? "#FFD700" : DEFAULT_STYLE.colors[i % DEFAULT_STYLE.colors.length];
            const scale = isFirst ? 1 + hl * 0.03 : 1 + hl * 0.025;
            const shadowBlur = 16 + hl * 24;
            const shadowAlpha = 0.06 + hl * 0.14;
            const borderW = isFirst ? 3 + hl * 2 : 0;

            // Fill bar 비율
            const fillRatio = values[i] ? values[i] / maxValue : 0;
            const fillWidth = interpolate(
              frame,
              [entranceDelay + 4, entranceDelay + 4 + 20],
              [0, fillRatio * 100],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easingFn },
            );

            // CountUp
            const animatedValue = values[i]
              ? countUpValue(frame, entranceDelay, 20, values[i], easingFn)
              : 0;

            return (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 16,
                  padding: `${isFirst ? cardPadV + 4 : cardPadV}px 24px`,
                  background: "var(--viz-card-bg)",
                  borderRadius: "var(--viz-card-radius)",
                  boxShadow: isFirst
                    ? `0 4px ${shadowBlur}px rgba(255,215,0,${shadowAlpha})`
                    : `0 3px ${shadowBlur}px rgba(61,59,47,${shadowAlpha})`,
                  border: isFirst ? `${borderW}px solid #FFD70060` : undefined,
                  opacity: itemOpacity,
                  transform: `translateX(${itemSlide}px) scale(${scale})`,
                  transformOrigin: "left center",
                  position: "relative",
                  overflow: "hidden",
                }}
              >
                {/* Fill bar (배경) */}
                <div
                  style={{
                    position: "absolute",
                    left: 0,
                    top: 0,
                    bottom: 0,
                    width: `${fillWidth}%`,
                    background: isTop3
                      ? `linear-gradient(90deg, ${color}10, ${color}06)`
                      : `linear-gradient(90deg, ${color}0a, transparent)`,
                    transition: "none",
                  }}
                />

                {/* 순위 배지 */}
                <div
                  style={{
                    width: isFirst ? rankBadgeSize + 8 : rankBadgeSize,
                    height: isFirst ? rankBadgeSize + 8 : rankBadgeSize,
                    borderRadius: "50%",
                    background: medal?.bg ?? "var(--viz-grid)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: medal?.text ?? "var(--viz-text)",
                    fontSize: isFirst ? Math.round(rankBadgeSize * 0.5) : Math.round(rankBadgeSize * 0.45),
                    fontWeight: "var(--viz-title-weight)" as any,
                    flexShrink: 0,
                    boxShadow: medal ? `0 3px 10px ${medal.shadow}` : undefined,
                    zIndex: 1,
                  }}
                >
                  {rank}
                </div>

                {/* 항목 이름 */}
                <span
                  style={{
                    flex: 1,
                    color: "var(--viz-text)",
                    fontSize: isFirst ? textSize + 4 : textSize,
                    fontWeight: isFirst ? "var(--viz-title-weight)" as any : "var(--viz-label-weight)" as any,
                    fontFamily: isFirst ? "var(--viz-title-font)" : undefined,
                    zIndex: 1,
                  }}
                >
                  {item}
                </span>

                {/* 수치 */}
                {values[i] !== undefined && (
                  <span
                    style={{
                      color: isFirst ? accentColor : "var(--viz-text)",
                      fontSize: isFirst ? textSize + 2 : textSize - 2,
                      fontWeight: "var(--viz-title-weight)" as any,
                      marginLeft: 16,
                      zIndex: 1,
                    }}
                  >
                    {animatedValue.toLocaleString()}{unit}
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
