import React, { useMemo } from "react";
import { useCurrentFrame, interpolate } from "remotion";
import {
  LineChart as RLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { STYLE as DEFAULT_STYLE } from "./vizStyles";
import { resolveEasing } from "../utils/easingMap";
import { msToFrames } from "../utils/syncDelay";
import { VizShell, ANIM } from "./VizShell";
import type { VisualizationData, VizAnimationConfig } from "../types/manifest";

interface Props {
  data: VisualizationData;
  durationInFrames: number;
  fps: number;
  vizAnimation?: VizAnimationConfig;
}

export const LineChart: React.FC<Props> = ({ data, durationInFrames, fps, vizAnimation }) => {
  const frame = useCurrentFrame();

  const items = data.items ?? [];
  const values = data.values ?? [];
  const unit = data.unit ?? "";
  const maxVal = Math.ceil(Math.max(...values, 1) * 1.15);

  const drawDuration = msToFrames(vizAnimation?.itemDuration, fps, 60);
  const easingFn = resolveEasing(vizAnimation?.easing);

  // 라인 드로잉: 순차적으로 포인트별 진행
  // 전체 드로잉 시간을 아이템 수에 맞게 분배
  const totalDrawFrames = Math.max(drawDuration, items.length * 4);
  const lineReveal = interpolate(frame, [10, 10 + totalDrawFrames], [0, 100], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: easingFn,
  });

  const clipId = `line-reveal-${data.title ?? "lc"}`;

  /** 도트별 등장 프레임 계산 — 라인 진행에 맞춰 순차 등장 */
  const dotDelays = useMemo(() => {
    return items.map((_, i) => {
      // 라인이 해당 포인트에 도달하는 프레임
      const arrivalFrame = 10 + Math.floor((i / Math.max(items.length - 1, 1)) * totalDrawFrames);
      return arrivalFrame;
    });
  }, [items.length, totalDrawFrames]);

  const accentIdx = DEFAULT_STYLE.accentIndex ?? 0;

  /** Animated dot — 라인 진행에 맞춰 순차 등장 */
  const AnimatedDot = (props: any) => {
    const { cx, cy, index, payload } = props;
    if (cx == null || cy == null) return null;

    const pointProgress = (index / Math.max(items.length - 1, 1)) * 100;
    if (lineReveal < pointProgress - 5) return null;

    const dotDelay = dotDelays[index] ?? 10;
    const scale = interpolate(frame, [dotDelay, dotDelay + 10], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: easingFn,
    });

    const baseColor = `var(--viz-color-${accentIdx})`;
    const dotRadius = 8;

    const isFirst = index === 0;
    const isLast = index === items.length - 1;
    const textAnchor = isLast ? "end" : isFirst ? "start" : "middle";

    return (
      <g>
        <circle
          cx={cx}
          cy={cy}
          r={dotRadius * scale}
          fill={baseColor}
          stroke="var(--viz-card-bg)"
          strokeWidth={3}
        />
        {scale > 0.8 && (
          <text
            x={cx}
            y={cy - 20}
            textAnchor={textAnchor}
            fill="var(--viz-text)"
            fontSize="var(--viz-value-size)"
            fontWeight="var(--viz-value-weight)"
            fontFamily="var(--viz-font)"
          >
            {payload.fullValue?.toLocaleString()}{unit}
          </text>
        )}
      </g>
    );
  };

  // 전체 데이터 항상 존재 — 라인 형태 변하지 않음
  const chartData = items.map((item, i) => ({
    name: item,
    value: values[i],
    fullValue: values[i],
  }));

  const chartOpacity = interpolate(
    frame,
    [ANIM.CONTENT_FADE_START, ANIM.CONTENT_FADE_END],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const lineColor = `var(--viz-color-${accentIdx})`;

  return (
    <VizShell
      title={data.title}
      source={data.source}
      durationInFrames={durationInFrames}
      vizAnimation={vizAnimation}
    >
      <div style={{ flex: 1, opacity: chartOpacity, padding: "0 2%" }}>
        <ResponsiveContainer width="100%" height="100%">
          <RLineChart
            data={chartData}
            margin={{ top: 50, right: 80, left: 20, bottom: 30 }}
          >
            {/* SVG clipPath for progressive line reveal */}
            <defs>
              <clipPath id={clipId}>
                <rect x="0" y="0" width={`${lineReveal}%`} height="100%" />
              </clipPath>
            </defs>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--viz-grid)"
              vertical={false}
            />
            <XAxis
              dataKey="name"
              tick={{ fill: "var(--viz-subtitle)", fontSize: "var(--viz-label-size)", fontFamily: "var(--viz-font)" }}
              axisLine={{ stroke: "var(--viz-grid)" }}
              tickLine={false}
              interval={0}
              dy={8}
              angle={items.length > 8 ? -30 : 0}
              textAnchor={items.length > 8 ? "end" : "middle"}
            />
            <YAxis
              domain={[0, maxVal]}
              tick={{ fill: "var(--viz-subtitle)", fontSize: "var(--viz-caption-size)", fontFamily: "var(--viz-font)" }}
              axisLine={false}
              tickLine={false}
              width={60}
            />
            {/* Hide the default legend completely */}
            <Legend content={() => null} />
            <Line
              type="monotone"
              dataKey="value"
              stroke={lineColor}
              strokeWidth={4}
              dot={<AnimatedDot />}
              isAnimationActive={false}
              clipPath={`url(#${clipId})`}
            />
          </RLineChart>
        </ResponsiveContainer>
      </div>
    </VizShell>
  );
};
