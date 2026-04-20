import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import { STYLE as DEFAULT_STYLE, LAYOUT } from "./vizStyles";
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

interface TreeNode {
  index: number;
  label: string;
  description: string;
  relation: string;
  parentIndex: number;
  level: number;
  color: string;
}

export const TechTree: React.FC<Props> = ({ data, durationInFrames, fps, vizAnimation }) => {
  const frame = useCurrentFrame();
  const easingFn = resolveEasing(vizAnimation?.easing);

  const items = data.items ?? [];
  const parentIndices = (data.values ?? []).map((v) => Math.round(v));
  const relations = data.relations ?? [];
  const descriptions = data.descriptions ?? [];

  const nodes: TreeNode[] = items.map((label, i) => {
    const parentIdx = parentIndices[i] ?? -1;
    let level = 0;
    let cur = parentIdx;
    while (cur >= 0 && cur < items.length) {
      level++;
      cur = parentIndices[cur] ?? -1;
    }

    return {
      index: i,
      label,
      description: descriptions[i] ?? "",
      relation: relations[i] ?? "",
      parentIndex: parentIdx,
      level,
      color: `var(--viz-color-${i % 10})`,
    };
  });

  const maxLevel = Math.max(0, ...nodes.map((n) => n.level));

  const levelGroups: TreeNode[][] = [];
  for (let l = 0; l <= maxLevel; l++) {
    levelGroups.push(nodes.filter((n) => n.level === l));
  }

  const nodePositions: Record<number, { cx: number; cy: number }> = {};
  const levelHeight = 84 / (maxLevel + 1);

  levelGroups.forEach((group, level) => {
    const y = LAYOUT.topMargin + LAYOUT.sourceHeight + LAYOUT.titleHeight + 2 + level * levelHeight + levelHeight / 2;
    const step = 84 / (group.length + 1);
    group.forEach((node, gi) => {
      const x = LAYOUT.sidePadding + step * (gi + 1);
      nodePositions[node.index] = { cx: x, cy: y };
    });
  });

  return (
    <VizShell
      title={data.title}
      source={data.source}
      durationInFrames={durationInFrames}
      vizAnimation={vizAnimation}
    >
      {/* SVG connection lines */}
      <svg
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          pointerEvents: "none",
          zIndex: 0,
        }}
      >
        {nodes
          .filter((n) => n.parentIndex >= 0 && nodePositions[n.parentIndex])
          .map((n) => {
            const child = nodePositions[n.index];
            const parent = nodePositions[n.parentIndex];
            if (!child || !parent) return null;

            const nodeDelay = calcItemDelay(n.index, fps, vizAnimation, 8, 4);
            const lineOpacity = interpolate(
              frame,
              [nodeDelay, nodeDelay + 8],
              [0, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easingFn },
            );

            const px = `${parent.cx}%`;
            const py = `${parent.cy + levelHeight * 0.2}%`;
            const cx_ = `${child.cx}%`;
            const cy_ = `${child.cy - levelHeight * 0.2}%`;
            const midY = `${(parent.cy + levelHeight * 0.2 + child.cy - levelHeight * 0.2) / 2}%`;

            return (
              <path
                key={`line-${n.index}`}
                d={`M ${px} ${py} C ${px} ${midY}, ${cx_} ${midY}, ${cx_} ${cy_}`}
                fill="none"
                stroke="var(--viz-grid)"
                strokeWidth={2.5}
                opacity={lineOpacity}
              />
            );
          })}
      </svg>

      {/* Nodes by level */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: Math.max(12, 40 - maxLevel * 6),
          flex: 1,
          justifyContent: "center",
          zIndex: 1,
          position: "relative",
        }}
      >
        {levelGroups.map((group, level) => (
          <div
            key={level}
            style={{
              display: "flex",
              justifyContent: "center",
              gap: Math.max(16, 48 - group.length * 4),
              width: "100%",
            }}
          >
            {group.map((node) => {
              const nodeDelay = calcItemDelay(node.index, fps, vizAnimation, 6, 4);
              const nodeOpacity = interpolate(
                frame,
                [nodeDelay, nodeDelay + 8],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easingFn },
              );
              const nodeY = interpolate(
                frame,
                [nodeDelay, nodeDelay + 8],
                [-16, 0],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easingFn },
              );

              return (
                <div
                  key={node.index}
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: 4,
                    opacity: nodeOpacity,
                    transform: `translateY(${nodeY}px)`,
                  }}
                >
                  {node.relation ? (
                    <div
                      style={{
                        fontSize: "var(--viz-caption-size)",
                        color: "var(--viz-source)",
                        background: "var(--viz-grid)",
                        padding: "4px 12px",
                        borderRadius: 8,
                      }}
                    >
                      {node.relation}
                    </div>
                  ) : null}
                  <div
                    style={{
                      background: "var(--viz-card-bg)",
                      border: `3px solid ${node.color}`,
                      borderRadius: "var(--viz-card-radius)",
                      padding: "16px 28px",
                      textAlign: "center",
                      minWidth: 120,
                      boxShadow: `0 3px 12px ${DEFAULT_STYLE.colors[node.index % DEFAULT_STYLE.colors.length]}20`,
                    }}
                  >
                    <div
                      style={{
                        fontSize: "var(--viz-label-size)",
                        fontWeight: "var(--viz-title-weight)",
                        color: node.color,
                        fontFamily: "var(--viz-font)",
                      }}
                    >
                      {node.label}
                    </div>
                    {node.description ? (
                      <div
                        style={{
                          fontSize: "var(--viz-caption-size)",
                          color: "var(--viz-subtitle)",
                          marginTop: 4,
                        }}
                      >
                        {node.description}
                      </div>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </VizShell>
  );
};
