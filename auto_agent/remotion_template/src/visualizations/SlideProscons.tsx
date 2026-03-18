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
 * 장단점/찬반 비교 슬라이드
 *
 * - left: { label: "장점", items: [...] }
 * - right: { label: "단점", items: [...] }
 * - 또는 items 배열로 폴백: 전반부=장점, 후반부=단점
 */
export const SlideProscons: React.FC<Props> = ({ data, durationInFrames, fps, vizAnimation }) => {
  const frame = useCurrentFrame();
  const easingFn = resolveEasing(vizAnimation?.easing);

  const imagePath =
    typeof data.imagePath === "string" ? data.imagePath : undefined;
  const hasImage = !!imagePath;

  // 데이터 추출: left/right 구조 우선, 없으면 items를 반으로 분할
  const hasLeftRight = !!(data.left && data.right);
  const prosLabel = data.left?.label ?? "장점";
  const consLabel = data.right?.label ?? "단점";
  let prosItems: string[];
  let consItems: string[];

  if (hasLeftRight) {
    prosItems = data.left!.items;
    consItems = data.right!.items;
  } else {
    const items = data.items ?? [];
    const mid = Math.ceil(items.length / 2);
    prosItems = items.slice(0, mid);
    consItems = items.slice(mid);
  }

  const totalItems = prosItems.length + consItems.length;

  // Adaptive sizing
  const maxSide = Math.max(prosItems.length, consItems.length);
  const cardPadV = maxSide >= 5 ? 12 : maxSide >= 4 ? 16 : 20;
  const cardGap = maxSide >= 5 ? 10 : maxSide >= 4 ? 14 : 18;
  const textSize = maxSide >= 5 ? 28 : maxSide >= 4 ? 32 : 36;

  const prosColor = DEFAULT_STYLE.semantic.positive;
  const consColor = DEFAULT_STYLE.semantic.negative;

  // ── Phase 1: 등장 ──
  const HEADER_START = 8;
  const HEADER_FADE = 12;
  const DIVIDER_START = 10;
  const DIVIDER_DURATION = 18;
  const ITEM_BASE = 16;
  const ITEM_STAGGER = 4;
  const FADE_IN = 12;

  // 헤더 등장
  const prosHeaderOpacity = interpolate(frame, [HEADER_START, HEADER_START + HEADER_FADE], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const consHeaderOpacity = interpolate(frame, [HEADER_START + 4, HEADER_START + 4 + HEADER_FADE], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  // 분리선 드로잉
  const dividerHeight = interpolate(frame, [DIVIDER_START, DIVIDER_START + DIVIDER_DURATION], [0, 100], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easingFn,
  });

  // Shared highlight helper
  const useHl = (syncDelay: number) => {
    const HIGHLIGHT_IN = 8;
    const HIGHLIGHT_HOLD = 20;
    const HIGHLIGHT_OUT = 12;
    return interpolate(
      frame,
      [syncDelay, syncDelay + HIGHLIGHT_IN, syncDelay + HIGHLIGHT_IN + HIGHLIGHT_HOLD, syncDelay + HIGHLIGHT_IN + HIGHLIGHT_HOLD + HIGHLIGHT_OUT],
      [0, 1, 1, 0],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
    );
  };

  // Background: 좌우 분할 톤
  const bg = (
    <AbsoluteFill>
      <div style={{ position: "absolute", left: 0, top: 0, width: "50%", height: "100%", background: `${prosColor}05` }} />
      <div style={{ position: "absolute", right: 0, top: 0, width: "50%", height: "100%", background: `${consColor}05` }} />
    </AbsoluteFill>
  );

  const renderColumn = (
    items: string[],
    label: string,
    color: string,
    bgColor: string,
    side: "left" | "right",
    headerOpacity: number,
    indexOffset: number,
  ) => {
    const isLeft = side === "left";
    const icon = isLeft ? "\u2713" : "\u2717";

    return (
      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: cardGap }}>
        {/* 헤더 */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            opacity: headerOpacity,
            marginBottom: 8,
          }}
        >
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: "50%",
              background: color,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "white",
              fontSize: 20,
              fontWeight: 700,
            }}
          >
            {icon}
          </div>
          <span
            style={{
              color,
              fontSize: "var(--viz-subtitle-size)",
              fontWeight: "var(--viz-title-weight)" as any,
              fontFamily: "var(--viz-title-font)",
            }}
          >
            {label}
          </span>
        </div>

        {/* 아이템 카드들 */}
        {items.map((item, i) => {
          const globalIndex = indexOffset + i;
          const entranceDelay = ITEM_BASE + (isLeft ? i * ITEM_STAGGER : (i * ITEM_STAGGER + 2));
          const itemOpacity = interpolate(frame, [entranceDelay, entranceDelay + FADE_IN], [0, 1], {
            extrapolateLeft: "clamp", extrapolateRight: "clamp",
          });
          const itemSlide = interpolate(
            frame,
            [entranceDelay, entranceDelay + FADE_IN],
            [isLeft ? -20 : 20, 0],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
          );

          const syncDelay = calcItemDelay(globalIndex, fps, vizAnimation, 0, 0);
          const hl = useHl(syncDelay);

          const scale = 1 + hl * 0.025;
          const shadowBlur = 16 + hl * 20;
          const shadowAlpha = 0.06 + hl * 0.12;
          const borderW = 4 + hl * 3;

          return (
            <div
              key={i}
              style={{
                background: `linear-gradient(135deg, ${hl > 0 ? bgColor : "transparent"}, var(--viz-card-bg))`,
                borderLeft: `${borderW}px solid ${color}`,
                borderRadius: "var(--viz-card-radius)",
                padding: `${cardPadV}px 24px`,
                boxShadow: `0 3px ${shadowBlur}px rgba(61,59,47,${shadowAlpha})`,
                opacity: itemOpacity,
                transform: `translateX(${itemSlide}px) scale(${scale})`,
                transformOrigin: isLeft ? "left center" : "right center",
              }}
            >
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
    );
  };

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
          gap: 16,
          paddingTop: "2%",
        }}
      >
        {/* Optional header image */}
        {hasImage && (
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              opacity: interpolate(frame, [0, 20], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }),
              marginBottom: 8,
            }}
          >
            <Img
              src={resolveAsset(imagePath!)}
              style={{
                maxWidth: "40%",
                maxHeight: 200,
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
          justifyContent: "center",
          alignItems: "flex-start",
          gap: 32,
        }}
      >
        {/* 장점 열 */}
        {renderColumn(prosItems, prosLabel, prosColor, DEFAULT_STYLE.semantic.positiveBg, "left", prosHeaderOpacity, 0)}

        {/* 세로 분리선 */}
        <div
          style={{
            width: 2,
            alignSelf: "stretch",
            background: `linear-gradient(to bottom, transparent, var(--viz-grid), transparent)`,
            clipPath: `inset(${100 - dividerHeight}% 0 0 0)`,
            flexShrink: 0,
          }}
        />

        {/* 단점 열 */}
        {renderColumn(consItems, consLabel, consColor, DEFAULT_STYLE.semantic.negativeBg, "right", consHeaderOpacity, prosItems.length)}
      </div>
      </div>
    </VizShell>
  );
};
