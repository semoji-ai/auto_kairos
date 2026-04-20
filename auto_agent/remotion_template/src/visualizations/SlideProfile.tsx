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
 * 인물/개체 프로필 카드 — Pencil S2 레이아웃
 *
 * 좌: 풀하이트 사진(680px) + 배지 오버레이
 * 우: 이름/부제/구분선/설명문/스탯 행
 *
 * Props 매핑:
 * - profileName → 이름
 * - profileSubtitle → 직함/부제 (한자 포함)
 * - descriptions[0] → 설명문 (멀티라인)
 * - items[] → 스탯 라벨 ("신분", "사후 추증", ...)
 * - descriptions[1+] → 스탯 값 ("호장(戶長)", "공조참판", ...)
 * - imagePath → 초상 이미지
 */
export const SlideProfile: React.FC<Props> = ({ data, durationInFrames, fps, vizAnimation }) => {
  const frame = useCurrentFrame();
  const easingFn = resolveEasing(vizAnimation?.easing);

  const name = data.profileName ?? data.items?.[0] ?? "";
  const subtitle = data.profileSubtitle ?? "";
  const imagePath = typeof data.imagePath === "string" ? data.imagePath : undefined;
  const hasImage = !!imagePath;
  const descriptions = (data as any).descriptions ?? [];

  // descriptions[0] = 설명문, descriptions[1+] = 스탯 값
  const descText = descriptions[0] ?? "";

  // 스탯 매핑: items = labels, descriptions[1+] = values
  const hasNameInItems = !data.profileName && data.items && data.items.length > 0;
  const statLabels = hasNameInItems ? (data.items ?? []).slice(1) : (data.items ?? []);
  const statValues = descriptions.slice(1);

  const accentColor = DEFAULT_STYLE.colors[DEFAULT_STYLE.accentIndex ?? 0];

  // ── Entrance animations ──
  const imgOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const imgSlide = interpolate(frame, [0, 15], [-40, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easingFn,
  });

  const nameOpacity = interpolate(frame, [6, 18], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const nameSlide = interpolate(frame, [6, 18], [-15, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  const subtitleOpacity = interpolate(frame, [12, 22], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  const descOpacity = interpolate(frame, [18, 28], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const descSlide = interpolate(frame, [18, 28], [10, 0], {
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
          margin: hasImage ? `0 0 0 -${6}%` : undefined,
        }}
      >
        {/* ── Left: Full-height photo ── */}
        {hasImage && (
          <div
            style={{
              width: 680,
              flexShrink: 0,
              position: "relative",
              overflow: "hidden",
              opacity: imgOpacity,
              transform: `translateX(${imgSlide}px)`,
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
            {/* Badge overlay (top-left) */}
            <div
              style={{
                position: "absolute",
                top: 40,
                left: 40,
                background: accentColor,
                padding: "8px 20px",
                borderRadius: 4,
              }}
            >
              <span
                style={{
                  color: "#FFFFFF",
                  fontSize: "var(--viz-label-size)",
                  fontWeight: 600,
                  fontFamily: "var(--viz-font)",
                }}
              >
                핵심 인물
              </span>
            </div>
          </div>
        )}

        {/* ── Right: Info panel ── */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            padding: 60,
            gap: 28,
            minWidth: 0,
          }}
        >
          {/* Name */}
          <div
            style={{
              opacity: nameOpacity,
              transform: `translateX(${nameSlide}px)`,
            }}
          >
            <div
              style={{
                color: "var(--viz-text)",
                fontSize: "var(--viz-hero-size)",
                fontWeight: "var(--viz-hero-weight)" as any,
                fontFamily: "var(--viz-title-font)",
                letterSpacing: "var(--viz-hero-tracking)",
                lineHeight: 1.2,
              }}
            >
              {name}
            </div>
          </div>

          {/* Subtitle (hanja / role) */}
          {subtitle && (
            <div
              style={{
                color: accentColor,
                fontSize: 34,
                fontWeight: 400,
                fontFamily: "var(--viz-font)",
                opacity: subtitleOpacity,
                marginTop: -12,
              }}
            >
              {subtitle}
            </div>
          )}

          {/* Red divider */}
          <div
            style={{
              width: 80,
              height: 3,
              background: accentColor,
              borderRadius: 2,
              opacity: nameOpacity,
            }}
          />

          {/* Description text (multi-line) */}
          {descText && (
            <div
              style={{
                color: "var(--viz-subtitle)",
                fontSize: 34,
                fontWeight: 400,
                fontFamily: "var(--viz-font)",
                lineHeight: 1.5,
                maxWidth: 1000,
                opacity: descOpacity,
                transform: `translateY(${descSlide}px)`,
                whiteSpace: "pre-line",
              }}
            >
              {descText}
            </div>
          )}

          {/* Stats row */}
          {statLabels.length > 0 && (
            <div
              style={{
                display: "flex",
                flexDirection: "row",
                gap: 40,
                marginTop: 8,
              }}
            >
              {statLabels.map((label, i) => {
                const statDelay = 24 + i * 5;
                const statOpacity = interpolate(frame, [statDelay, statDelay + 10], [0, 1], {
                  extrapolateLeft: "clamp", extrapolateRight: "clamp",
                });
                const statSlide = interpolate(frame, [statDelay, statDelay + 10], [12, 0], {
                  extrapolateLeft: "clamp", extrapolateRight: "clamp",
                });

                // Phase 2: highlight
                const syncDelay = calcItemDelay(i, fps, vizAnimation, 0, 0);
                const hl = interpolate(
                  frame,
                  [syncDelay, syncDelay + 8, syncDelay + 28, syncDelay + 40],
                  [0, 1, 1, 0],
                  { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
                );
                const scale = 1 + hl * 0.03;

                return (
                  <div
                    key={i}
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: 4,
                      opacity: statOpacity,
                      transform: `translateY(${statSlide}px) scale(${scale})`,
                      transformOrigin: "bottom left",
                    }}
                  >
                    <span
                      style={{
                        color: "var(--viz-subtitle)",
                        fontSize: "var(--viz-label-size)",
                        fontWeight: 400,
                        fontFamily: "var(--viz-font)",
                      }}
                    >
                      {label}
                    </span>
                    <span
                      style={{
                        color: "var(--viz-text)",
                        fontSize: 36,
                        fontWeight: 700,
                        fontFamily: "var(--viz-font)",
                      }}
                    >
                      {statValues[i] ?? ""}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </VizShell>
  );
};
