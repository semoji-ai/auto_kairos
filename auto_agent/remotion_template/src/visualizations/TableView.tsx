import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { TYPO as DEFAULT_TYPO } from "./vizStyles";
import { calcItemDelay } from "../utils/syncDelay";
import { countUpValue } from "../utils/countUp";
import { resolveEasing } from "../utils/easingMap";
import { VizShell } from "./VizShell";
import { VIZ_STRINGS } from "./vizI18n";
import type { VisualizationData, VizAnimationConfig } from "../types/manifest";

interface Props {
  data: VisualizationData;
  durationInFrames: number;
  fps: number;
  vizAnimation?: VizAnimationConfig;
}

export const TableView: React.FC<Props> = ({ data, durationInFrames, fps, vizAnimation }) => {
  const frame = useCurrentFrame();
  const items = data.items ?? [];
  const values = data.values ?? [];
  const easingFn = resolveEasing(vizAnimation?.easing);

  // Pipe-separated column detection
  const hasPipes = items.some((item) => item.includes("|"));
  const hasValues = values.length > 0 && values.some((v) => typeof v === "number" && v !== 0);
  const maxCols = hasPipes
    ? Math.max(...items.map((item) => item.split("|").length), 1)
    : 1;

  // Adaptive sizing
  const n = items.length;
  const rowPadV = n >= 7 ? 14 : n >= 5 ? 18 : 22;
  const rowPadH = 32;
  const fontSize = n >= 7 ? DEFAULT_TYPO.label.size - 4 : DEFAULT_TYPO.label.size;
  const valueFont = n >= 7 ? DEFAULT_TYPO.value.size - 2 : DEFAULT_TYPO.subtitle.size;

  // Alternating row background — need grid hex for alpha concat
  const altRowBg = "color-mix(in srgb, var(--viz-grid) 25%, transparent)";

  // ── Header 등장 ──
  const HEADER_ENTRANCE = 5;
  const HEADER_FADE = 10;
  const headerOpacity = interpolate(frame, [HEADER_ENTRANCE, HEADER_ENTRANCE + HEADER_FADE], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <VizShell
      title={data.title}
      source={data.source}
      durationInFrames={durationInFrames}
      vizAnimation={vizAnimation}
    >
      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "center",
          overflow: "hidden",
        }}
      >
        {/* 너비 규칙: fit-content, minWidth 55%, maxWidth 95% */}
        <div
          style={{
            width: "fit-content",
            minWidth: "55%",
            maxWidth: "95%",
            borderRadius: "var(--viz-card-radius)",
            overflow: "hidden",
            boxShadow: "var(--viz-card-shadow)",
          }}
        >
          {/* Header */}
          <div
            style={{
              display: "flex",
              background: `linear-gradient(135deg, var(--viz-border), var(--viz-subtitle))`,
              padding: `${rowPadV}px ${rowPadH}px`,
              opacity: headerOpacity,
            }}
          >
            {hasPipes ? (
              <>
                {/* 컬러바 spacer */}
                <div style={{ width: 7, marginRight: 16, flexShrink: 0 }} />
                {Array.from({ length: maxCols }).map((_, ci) => (
                  <span
                    key={ci}
                    style={{
                      flex: ci === 0 ? 1 : undefined,
                      width: ci > 0 ? `${Math.floor(70 / (maxCols - 1))}%` : undefined,
                      color: "white",
                      fontSize: "var(--viz-value-size)",
                      fontWeight: "var(--viz-title-weight)",
                      fontFamily: "var(--viz-font)",
                      textAlign: ci > 0 ? "center" : "left",
                    }}
                  >
                    {ci === 0 ? VIZ_STRINGS.table_header_item : ""}
                  </span>
                ))}
              </>
            ) : (
              <>
                <span style={{ flex: 1, color: "white", fontSize: "var(--viz-value-size)", fontWeight: "var(--viz-title-weight)", fontFamily: "var(--viz-font)" }}>
                  {VIZ_STRINGS.table_header_item}
                </span>
                <span
                  style={{
                    width: "30%",
                    color: "white",
                    fontSize: "var(--viz-value-size)",
                    fontWeight: "var(--viz-title-weight)",
                    textAlign: "right",
                    fontFamily: "var(--viz-font)",
                  }}
                >
                  {data.unit ? `${VIZ_STRINGS.table_header_value} (${data.unit})` : VIZ_STRINGS.table_header_value}
                </span>
              </>
            )}
          </div>

          {/* Rows */}
          {items.map((item, i) => {
            // ── Phase 1: 등장 (위→아래 순차 스태거) ──
            const ENTRANCE_BASE = 10;
            const ENTRANCE_STAGGER = 4;
            const FADE_IN = 12;
            const entranceDelay = ENTRANCE_BASE + i * ENTRANCE_STAGGER;
            const rowOpacity = interpolate(frame, [entranceDelay, entranceDelay + FADE_IN], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            const rowSlide = interpolate(frame, [entranceDelay, entranceDelay + FADE_IN], [-20, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });

            // ── Phase 2: 타임스탬프 기반 강조 ──
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

            const color = `var(--viz-color-${i % 10})`;
            const animatedValue = countUpValue(frame, entranceDelay, 18, values[i] ?? 0, easingFn);

            // 강조 스타일 (테이블 행: scale 없이 컬러바 + 배경 + 그림자)
            const barWidth = 7 + hl * 5;
            const baseBg = i % 2 === 0 ? "var(--viz-card-bg)" : altRowBg;
            const rowShadow = hl > 0 ? `0 2px ${8 + hl * 12}px rgba(61,59,47,${hl * 0.12})` : "none";

            return (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  padding: `${rowPadV}px ${rowPadH}px`,
                  background: baseBg,
                  opacity: rowOpacity,
                  transform: `translateX(${rowSlide}px)`,
                  boxShadow: rowShadow,
                  position: "relative",
                  zIndex: hl > 0 ? 1 : 0,
                }}
              >
                {/* 컬러 바 — 강조 시 두꺼워짐 */}
                <div
                  style={{
                    width: barWidth,
                    height: 38,
                    borderRadius: 4,
                    background: color,
                    marginRight: 16,
                    flexShrink: 0,
                    transition: "width 0.1s",
                  }}
                />
                {hasPipes ? (
                  // 파이프 구분자 → 멀티 컬럼 렌더링
                  (() => {
                    const cells = item.split("|").map((c) => c.trim());
                    return cells.map((cell, ci) => (
                      <span
                        key={ci}
                        style={{
                          flex: ci === 0 ? 1 : undefined,
                          width: ci > 0 ? `${Math.floor(70 / (maxCols - 1))}%` : undefined,
                          color: ci === 0 ? "var(--viz-text)" : "var(--viz-subtitle)",
                          fontSize: ci === 0 ? fontSize : fontSize - 2,
                          fontWeight: ci === 0 ? "var(--viz-label-weight)" : "var(--viz-caption-weight)",
                          fontFamily: "var(--viz-font)",
                          textAlign: ci > 0 ? "center" : "left",
                        }}
                      >
                        {cell}
                      </span>
                    ));
                  })()
                ) : (
                  <>
                    <span
                      style={{
                        flex: 1,
                        color: "var(--viz-text)",
                        fontSize: fontSize,
                        fontWeight: "var(--viz-label-weight)",
                        fontFamily: "var(--viz-font)",
                      }}
                    >
                      {item}
                    </span>
                    <span
                      style={{
                        width: "30%",
                        color: "var(--viz-text)",
                        fontSize: valueFont,
                        fontWeight: "var(--viz-title-weight)",
                        textAlign: "right",
                        fontFamily: "var(--viz-font)",
                      }}
                    >
                      {animatedValue.toLocaleString()}
                      {data.unit ?? ""}
                    </span>
                  </>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </VizShell>
  );
};
