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
 * 카운트다운/순차 공개 슬라이드
 *
 * - items: 공개 순서대로 (5위→1위 등)
 * - values: 순위 번호 (5, 4, 3, 2, 1)
 * - descriptions: 부가 설명 (선택)
 *
 * 각 항목이 풀스크린으로 하나씩 순차 공개됨.
 * itemSyncPoints로 공개 타이밍을 제어.
 */
export const SlideCountdown: React.FC<Props> = ({ data, durationInFrames, fps, vizAnimation }) => {
  const frame = useCurrentFrame();
  const easingFn = resolveEasing(vizAnimation?.easing);

  const imagePath =
    typeof data.imagePath === "string" ? data.imagePath : undefined;
  const hasImage = !!imagePath;

  const items = data.items ?? [];
  const values = data.values ?? [];
  const descriptions = data.descriptions ?? [];
  const n = items.length;

  // 각 아이템의 시작/종료 프레임 계산
  // syncPoints가 없거나 durationInFrames보다 길면 균등 분배
  const itemWindows: { start: number; end: number }[] = [];
  const hasSyncPoints = vizAnimation?.itemSyncPoints && vizAnimation.itemSyncPoints.length > 0;
  const sliceDuration = Math.floor(durationInFrames / Math.max(n, 1));
  for (let i = 0; i < n; i++) {
    const start = hasSyncPoints
      ? Math.min(calcItemDelay(i, fps, vizAnimation, 8, 0), durationInFrames - 10)
      : 8 + i * sliceDuration;
    const nextStart = i < n - 1
      ? (hasSyncPoints
          ? Math.min(calcItemDelay(i + 1, fps, vizAnimation, 8, 0), durationInFrames)
          : 8 + (i + 1) * sliceDuration)
      : durationInFrames;
    // end는 반드시 start보다 커야 함
    itemWindows.push({ start, end: Math.max(nextStart, start + 10) });
  }

  // 현재 활성 아이템 찾기
  let activeIndex = -1;
  for (let i = n - 1; i >= 0; i--) {
    if (frame >= itemWindows[i].start) {
      activeIndex = i;
      break;
    }
  }

  // Background: optional image as faded overlay
  const bgImage = hasImage ? (
    <AbsoluteFill
      style={{
        opacity: interpolate(frame, [0, 20], [0, 0.15], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        }),
      }}
    >
      <Img
        src={resolveAsset(imagePath!)}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
        }}
      />
    </AbsoluteFill>
  ) : undefined;

  return (
    <VizShell
      title={data.title}
      source={data.source}
      durationInFrames={durationInFrames}
      vizAnimation={vizAnimation}
      hideTitle={!data.title || data.title.trim() === ""}
      background={bgImage}
    >
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          position: "relative",
        }}
      >
        {items.map((item, i) => {
          const { start, end } = itemWindows[i];
          const rankNumber = values[i] ?? n - i;
          const desc = descriptions[i] ?? "";
          const color = DEFAULT_STYLE.colors[i % DEFAULT_STYLE.colors.length];
          const grad = DEFAULT_STYLE.gradients[i % DEFAULT_STYLE.gradients.length];
          const isLast = i === n - 1;

          // 아이템 가시성: 해당 윈도우 내에서만 보임
          const isActive = i === activeIndex;

          // 등장 애니메이션
          const ITEM_FADE = 12;
          const fadeInEnd = start + ITEM_FADE;
          const fadeOutStart = Math.max(end - 8, fadeInEnd + 1);
          const fadeOutEnd = Math.max(end, fadeOutStart + 1);
          const itemOpacity = isLast
            ? interpolate(frame, [start, fadeInEnd], [0, 1], {
                extrapolateLeft: "clamp", extrapolateRight: "clamp",
              })
            : interpolate(
                frame,
                [start, fadeInEnd, fadeOutStart, fadeOutEnd],
                [0, 1, 1, 0],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
              );

          // 아이템이 윈도우 밖이면 렌더하지 않음
          if (frame < start - 5 || frame > end + 5) return null;

          // 워터마크 번호 scale-down
          const watermarkScale = interpolate(
            frame,
            [start, start + 15],
            [2.0, 1.0],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easingFn },
          );
          const watermarkOpacity = interpolate(
            frame,
            [start, start + 10],
            [0, 0.08],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
          );

          // 텍스트 slide-up
          const textSlide = interpolate(
            frame,
            [start + 4, start + 4 + ITEM_FADE],
            [30, 0],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easingFn },
          );
          const textOpacity = interpolate(
            frame,
            [start + 4, start + 4 + ITEM_FADE],
            [0, 1],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
          );

          // 설명 등장
          const descSlide = interpolate(
            frame,
            [start + 10, start + 10 + ITEM_FADE],
            [15, 0],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
          );
          const descOpacity = interpolate(
            frame,
            [start + 10, start + 10 + ITEM_FADE],
            [0, 1],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
          );

          // 하이라이트 (활성 아이템)
          const HIGHLIGHT_IN = 8;
          const HIGHLIGHT_HOLD = 20;
          const HIGHLIGHT_OUT = 12;
          const hl = isActive
            ? interpolate(
                frame,
                [start + ITEM_FADE, start + ITEM_FADE + HIGHLIGHT_IN, start + ITEM_FADE + HIGHLIGHT_IN + HIGHLIGHT_HOLD, start + ITEM_FADE + HIGHLIGHT_IN + HIGHLIGHT_HOLD + HIGHLIGHT_OUT],
                [0, 1, 1, 0],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
              )
            : 0;
          const glowIntensity = 8 + hl * 20;

          return (
            <AbsoluteFill
              key={i}
              style={{
                display: "flex",
                flexDirection: "column",
                justifyContent: "center",
                alignItems: "center",
                opacity: itemOpacity,
              }}
            >
              {/* 배경 색상 틴트 */}
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  background: `radial-gradient(circle at center, ${color}10 0%, transparent 60%)`,
                }}
              />

              {/* 순위 워터마크 */}
              <div
                style={{
                  position: "absolute",
                  opacity: watermarkOpacity,
                  transform: `scale(${watermarkScale})`,
                  fontSize: 300,
                  fontWeight: 900,
                  color: "var(--viz-text)",
                  lineHeight: 1,
                  userSelect: "none",
                }}
              >
                #{rankNumber}
              </div>

              {/* 메인 컨텐츠 */}
              <div
                style={{
                  position: "relative",
                  zIndex: 1,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 16,
                  filter: hl > 0 ? `drop-shadow(0 0 ${glowIntensity}px ${color}40)` : undefined,
                }}
              >
                {/* 순위 배지 */}
                <div
                  style={{
                    width: isLast ? 72 : 56,
                    height: isLast ? 72 : 56,
                    borderRadius: "50%",
                    background: `linear-gradient(135deg, ${grad[0]}, ${grad[1]})`,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "white",
                    fontSize: isLast ? 32 : 24,
                    fontWeight: 800,
                    boxShadow: `0 4px 16px ${grad[0]}50`,
                    opacity: textOpacity,
                  }}
                >
                  {rankNumber}
                </div>

                {/* 항목 텍스트 */}
                <div
                  style={{
                    color: "var(--viz-text)",
                    fontSize: isLast ? "calc(var(--viz-hero-size) + 8px)" : "var(--viz-hero-size)",
                    fontWeight: "var(--viz-hero-weight)" as any,
                    fontFamily: "var(--viz-title-font)",
                    letterSpacing: "var(--viz-hero-tracking)",
                    textAlign: "center",
                    maxWidth: "75%",
                    lineHeight: 1.3,
                    opacity: textOpacity,
                    transform: `translateY(${textSlide}px)`,
                  }}
                >
                  {item}
                </div>

                {/* 설명 */}
                {desc && (
                  <div
                    style={{
                      color: "var(--viz-subtitle)",
                      fontSize: "var(--viz-subtitle-size)",
                      fontWeight: "var(--viz-subtitle-weight)" as any,
                      textAlign: "center",
                      maxWidth: "65%",
                      lineHeight: 1.5,
                      opacity: descOpacity,
                      transform: `translateY(${descSlide}px)`,
                    }}
                  >
                    {desc}
                  </div>
                )}
              </div>
            </AbsoluteFill>
          );
        })}
      </div>
    </VizShell>
  );
};
