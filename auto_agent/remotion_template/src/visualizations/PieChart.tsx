import React, { useMemo } from "react";
import { useCurrentFrame, interpolate } from "remotion";
import {
  PieChart as RPieChart,
  Pie,
  Cell,
  ResponsiveContainer,
} from "recharts";
import { resolveEasing } from "../utils/easingMap";
import { calcItemDelay, msToFrames } from "../utils/syncDelay";
import { countUpValue } from "../utils/countUp";
import { VizShell, ANIM } from "./VizShell";
import { VIZ_STRINGS } from "./vizI18n";
import { useDesignPreset } from "../design";
import { useChartMotif } from "../simple/CreativeScene";
import type { VisualizationData, VizAnimationConfig } from "../types/manifest";

interface Props {
  data: VisualizationData;
  durationInFrames: number;
  fps: number;
  vizAnimation?: VizAnimationConfig;
}

export const PieChart: React.FC<Props> = ({ data, durationInFrames, fps, vizAnimation }) => {
  const frame = useCurrentFrame();
  const motif = useChartMotif();
  const preset = useDesignPreset();
  const palette = (preset as any).palette ?? {};
  const colors = (preset as any).colors ?? {};
  const sliceStroke =
    palette.annotationStroke ||
    palette.gridStrong ||
    colors.cardBorder ||
    "var(--viz-card-bg)";
  const sliceStrokeWidth = motif.outlineWidth || 3;
  const items = data.items ?? [];
  const values = data.values ?? [];
  const total = values.reduce((a, b) => a + b, 0) || 1;

  const sliceDuration = msToFrames(vizAnimation?.itemDuration, fps, 40);
  const easingFn = resolveEasing(vizAnimation?.easing);

  // Max donut size — callout labels spread to sides, not stacked near pie
  const outerRadius =
    items.length <= 2 ? "64%" :
    items.length <= 3 ? "56%" :
    items.length <= 5 ? "46%" : "36%";
  const innerRadius =
    items.length <= 2 ? "38%" :
    items.length <= 3 ? "34%" :
    items.length <= 5 ? "26%" : "22%";
  const useLegend = items.length > 7;

  // Animate sweep
  const totalProgress = interpolate(frame, [8, 8 + sliceDuration], [0, 360], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: easingFn,
  });

  const chartData = items.map((item, i) => {
    const fraction = values[i] / total;
    const sliceDelay = calcItemDelay(i, fps, vizAnimation, 8, 4);
    const labelVisible = interpolate(frame, [sliceDelay + 15, sliceDelay + 25], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }) > 0.5;

    return {
      name: item,
      value: values[i],
      percentage: Math.round(fraction * 100),
      _labelVisible: labelVisible,
    };
  });

  // Collision-avoidant label positions
  const labelPositions = useMemo(() => {
    if (useLegend) return [];
    const positions: Array<{ y: number; index: number }> = [];
    let cumAngle = 90;
    for (let i = 0; i < items.length; i++) {
      const fraction = values[i] / total;
      const midAngle = cumAngle - fraction * 360 / 2;
      cumAngle -= fraction * 360;
      const RADIAN = Math.PI / 180;
      const rawY = -Math.sin(midAngle * RADIAN);
      positions.push({ y: rawY * 300 + 540, index: i });
    }
    // Sort by y and push apart
    positions.sort((a, b) => a.y - b.y);
    const minGap = 36;
    for (let i = 1; i < positions.length; i++) {
      if (positions[i].y - positions[i - 1].y < minGap) {
        positions[i].y = positions[i - 1].y + minGap;
      }
    }
    return positions;
  }, [items.length, values, total, useLegend]);

  /** Elbow-style callout: radial stub → horizontal line to side margin, 2-line label */
  const renderLabel = (props: any) => {
    const { cx, cy, midAngle, outerRadius: or, index, payload } = props;
    if (!payload._labelVisible || useLegend) return null;

    const RADIAN = Math.PI / 180;
    const cos = Math.cos(-midAngle * RADIAN);
    const sin = Math.sin(-midAngle * RADIAN);
    const isRight = cos >= 0;

    // Step 1: radial stub from pie edge
    const stubLen = 16;
    const startX = cx + (or + 4) * cos;
    const startY = cy + (or + 4) * sin;
    const elbowX = cx + (or + stubLen) * cos;
    const elbowY = cy + (or + stubLen) * sin;

    // Step 2: horizontal line to side margin
    const sideMargin = 60; // px from SVG edge
    const endX = isRight ? cx + or + 120 : cx - or - 120;
    const textAnchor = isRight ? "start" : "end";
    const textX = endX + (isRight ? 10 : -10);
    const color = `var(--viz-color-${index % 10})`;

    return (
      <g>
        {/* Radial stub */}
        <line x1={startX} y1={startY} x2={elbowX} y2={elbowY}
          stroke="var(--viz-subtitle)" strokeWidth={1.5} />
        {/* Horizontal arm */}
        <line x1={elbowX} y1={elbowY} x2={endX} y2={elbowY}
          stroke="var(--viz-subtitle)" strokeWidth={1.5} />
        {/* Name (line 1) */}
        <text
          x={textX} y={elbowY - 6}
          textAnchor={textAnchor}
          fill="var(--viz-text)"
          fontSize="var(--viz-label-size)"
          fontWeight="var(--viz-label-weight)"
          fontFamily="var(--viz-font)"
        >
          {payload.name}
        </text>
        {/* Percentage (line 2) */}
        <text
          x={textX} y={elbowY + 28}
          textAnchor={textAnchor}
          fill={color}
          fontSize="var(--viz-value-size)"
          fontWeight="var(--viz-value-weight)"
          fontFamily="var(--viz-font)"
        >
          {payload.percentage}%
        </text>
      </g>
    );
  };

  // Center total
  const centerOpacity = interpolate(frame, [8 + sliceDuration - 10, 8 + sliceDuration + 5], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const animatedTotal = countUpValue(frame, 8 + sliceDuration - 10, 20, total, easingFn);

  const chartOpacity = interpolate(
    frame,
    [ANIM.CONTENT_FADE_START, ANIM.CONTENT_FADE_END],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

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
          position: "relative",
          opacity: chartOpacity,
        }}
      >
        {/* Donut Chart */}
        <div style={{ flex: useLegend ? "0 0 60%" : 1, position: "relative" }}>
          <ResponsiveContainer width="100%" height="100%">
            <RPieChart>
              <Pie
                data={chartData}
                dataKey="value"
                cx="50%"
                cy="50%"
                outerRadius={outerRadius}
                innerRadius={innerRadius}
                startAngle={90}
                endAngle={90 - totalProgress}
                stroke={sliceStroke}
                strokeWidth={sliceStrokeWidth}
                isAnimationActive={false}
                label={useLegend ? false : renderLabel}
                labelLine={false}
              >
                {chartData.map((_, i) => (
                  <Cell
                    key={i}
                    fill={`var(--viz-color-${i % 10})`}
                  />
                ))}
              </Pie>
            </RPieChart>
          </ResponsiveContainer>

          {/* Center total */}
          <div
            style={{
              position: "absolute",
              top: "50%",
              left: "50%",
              transform: "translate(-50%, -50%)",
              textAlign: "center",
              opacity: centerOpacity,
            }}
          >
            <div
              style={{
                fontSize: "var(--viz-caption-size)",
                color: "var(--viz-subtitle)",
                fontWeight: "var(--viz-subtitle-weight)",
              }}
            >
              {VIZ_STRINGS.pie_total}
            </div>
            <div
              style={{
                fontSize: "var(--viz-title-size)",
                fontWeight: "var(--viz-title-weight)",
                color: "var(--viz-text)",
              }}
            >
              {animatedTotal.toLocaleString()}
            </div>
          </div>
        </div>

        {/* Legend (7+ items) */}
        {useLegend && (
          <div
            style={{
              flex: "0 0 38%",
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
              gap: 12,
              paddingLeft: "2%",
            }}
          >
            {chartData.map((entry, i) => {
              const legendDelay = calcItemDelay(i, fps, vizAnimation, 20, 3);
              const legendOpacity = interpolate(frame, [legendDelay, legendDelay + 12], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              });
              return (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    opacity: legendOpacity,
                  }}
                >
                  <div
                    style={{
                      width: 16,
                      height: 16,
                      borderRadius: 4,
                      background: `var(--viz-color-${i % 10})`,
                      flexShrink: 0,
                    }}
                  />
                  <span
                    style={{
                      flex: 1,
                      color: "var(--viz-text)",
                      fontSize: "var(--viz-label-size)",
                      fontWeight: "var(--viz-label-weight)",
                      fontFamily: "var(--viz-font)",
                    }}
                  >
                    {entry.name}
                  </span>
                  <span
                    style={{
                      color: `var(--viz-color-${i % 10})`,
                      fontSize: "var(--viz-value-size)",
                      fontWeight: "var(--viz-value-weight)",
                      fontFamily: "var(--viz-font)",
                    }}
                  >
                    {entry.percentage}%
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </VizShell>
  );
};
