import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import {
  BarChart as RBarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Cell,
  LabelList,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import { useDesignTokens } from "../contexts/DesignTokenContext";
import { resolveEasing } from "../utils/easingMap";
import { calcItemDelay, msToFrames } from "../utils/syncDelay";
import { adaptiveBarSize, adaptiveYAxisWidth } from "../utils/adaptiveSize";
import { VizShell, ANIM } from "./VizShell";
import type { VisualizationData, VizAnimationConfig } from "../types/manifest";

interface Props {
  data: VisualizationData;
  durationInFrames: number;
  fps: number;
  vizAnimation?: VizAnimationConfig;
}

export const BarChart: React.FC<Props> = ({ data, durationInFrames, fps, vizAnimation }) => {
  const { STYLE, TYPO, VIZ_FONT } = useDesignTokens();
  const frame = useCurrentFrame();
  const items = data.items ?? [];
  const values = data.values ?? [];
  const maxVal = Math.max(...values, 1);
  const minVal = Math.min(...values, 0);
  const hasNegative = minVal < 0;
  const domainMax = Math.ceil(maxVal * 1.15);
  const domainMin = hasNegative ? Math.floor(minVal * 1.15) : 0;

  const barDur = msToFrames(vizAnimation?.itemDuration, fps, 30);
  const easingFn = resolveEasing(vizAnimation?.easing);

  // Adaptive sizing
  const barSize = adaptiveBarSize(items.length, 1080);
  const yAxisWidth = adaptiveYAxisWidth(items, TYPO.label.size);
  // Adaptive gap: compact for all counts, max bar height capped to prevent oversized bars
  const barGap = items.length <= 3 ? "20%" : items.length <= 6 ? "18%" : items.length <= 8 ? "14%" : "10%";
  const maxBarSize = items.length <= 3 ? 80 : items.length <= 5 ? 60 : undefined;

  const chartData = items.map((item, i) => {
    // ── 타임스탬프 기반 등장 (바 성장) ──
    const syncDelay = calcItemDelay(i, fps, vizAnimation, 8, 4, items);
    const progress = interpolate(frame, [syncDelay, syncDelay + barDur], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: easingFn,
    });

    return {
      name: item,
      value: values[i] * progress,
      fullValue: values[i],
      displayValue:
        progress > 0.6
          ? `${values[i]?.toLocaleString()}${data.unit ?? ""}`
          : "",
    };
  });

  const chartOpacity = interpolate(
    frame,
    [ANIM.CONTENT_FADE_START, ANIM.CONTENT_FADE_END],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  /** 음수 바 라벨을 왼쪽에 렌더링하는 커스텀 라벨 */
  const renderLabel = (props: any) => {
    const { x, y, width, height, value, index } = props;
    if (!value) return null;
    const isNeg = values[index] < 0;
    return (
      <text
        x={isNeg ? x - 8 : x + width + 8}
        y={y + height / 2}
        textAnchor={isNeg ? "end" : "start"}
        dominantBaseline="central"
        fill={isNeg ? STYLE.semantic.negative : STYLE.text}
        fontSize={TYPO.value.size}
        fontWeight={TYPO.value.weight}
        fontFamily={VIZ_FONT}
      >
        {value}
      </text>
    );
  };

  const renderYTick = (props: any) => {
    const { x, y, payload } = props;
    return (
      <text
        x={x}
        y={y}
        textAnchor="end"
        dominantBaseline="central"
        fill={STYLE.text}
        fontSize={TYPO.label.size}
        fontWeight={TYPO.label.weight}
        fontFamily={VIZ_FONT}
      >
        {payload.value}
      </text>
    );
  };

  return (
    <VizShell
      title={data.title}
      source={data.source}
      durationInFrames={durationInFrames}
      vizAnimation={vizAnimation}
    >
      <div style={{ flex: 1, opacity: chartOpacity, padding: "0 2%" }}>
        <ResponsiveContainer width="100%" height="100%">
          <RBarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 20, right: 100, left: 10, bottom: 20 }}
            barCategoryGap={barGap}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke={STYLE.grid}
              horizontal={false}
            />
            <XAxis
              type="number"
              domain={[domainMin, domainMax]}
              tickFormatter={(v: number) => Number.isInteger(v) ? String(v) : v.toFixed(1)}
              tick={{ fill: STYLE.subtitle, fontSize: TYPO.caption.size, fontFamily: VIZ_FONT }}
              axisLine={{ stroke: STYLE.grid }}
              tickLine={false}
            />
            <YAxis
              type="category"
              dataKey="name"
              width={yAxisWidth}
              tick={renderYTick}
              axisLine={false}
              tickLine={false}
            />
            {/* 양수/음수 혼합 시 0 기준선 */}
            {hasNegative && (
              <ReferenceLine x={0} stroke={STYLE.border} strokeWidth={2} />
            )}
            <Bar
              dataKey="value"
              radius={[0, 8, 8, 0]}
              isAnimationActive={false}
              barSize={barSize}
              maxBarSize={maxBarSize}
            >
              {chartData.map((d, i) => {
                const isNeg = values[i] < 0;
                const baseFill = hasNegative
                  ? (isNeg ? STYLE.semantic.negative : STYLE.semantic.positive)
                  : STYLE.colors[i % STYLE.colors.length];
                return (
                  <Cell
                    key={i}
                    fill={baseFill}
                  />
                );
              })}
              <LabelList
                dataKey="displayValue"
                content={renderLabel}
              />
            </Bar>
          </RBarChart>
        </ResponsiveContainer>
      </div>
    </VizShell>
  );
};
