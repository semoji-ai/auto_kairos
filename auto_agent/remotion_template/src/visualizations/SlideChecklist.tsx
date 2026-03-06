import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate, spring } from "remotion";
import { useDesignTokens } from "../contexts/DesignTokenContext";
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
 * 체크리스트/검증 목록
 *
 * - items: 체크 항목
 * - values: [1=통과, 0=실패]
 * - descriptions: 부가 설명 (선택)
 *
 * spring() API 최초 도입 — 아이콘 팝 애니메이션
 */
export const SlideChecklist: React.FC<Props> = ({ data, durationInFrames, fps, vizAnimation }) => {
  const { STYLE, TYPO } = useDesignTokens();
  const frame = useCurrentFrame();

  const items = data.items ?? [];
  const values = data.values ?? [];
  const descriptions = data.descriptions ?? [];

  const n = items.length;
  const cardPadV = n >= 6 ? 12 : n >= 5 ? 16 : 20;
  const cardGap = n >= 6 ? 10 : n >= 5 ? 12 : 16;
  const textSize = n >= 6 ? 28 : n >= 5 ? 32 : 36;
  const iconSize = n >= 6 ? 32 : n >= 5 ? 36 : 40;

  const passColor = STYLE.semantic.positive;
  const passBg = STYLE.semantic.positiveBg;
  const failColor = STYLE.semantic.negative;
  const failBg = STYLE.semantic.negativeBg;

  // 요약 배지 계산
  const passCount = values.filter((v) => v === 1).length;
  const totalCount = items.length;

  // ── Phase 1: 등장 ──
  const ENTRANCE_BASE = 8;
  const ENTRANCE_STAGGER = 4;
  const FADE_IN = 12;

  // Background
  const bg = (
    <AbsoluteFill style={{ opacity: 0.03 }}>
      <div
        style={{
          width: "100%",
          height: "100%",
          backgroundImage: `repeating-linear-gradient(135deg, ${STYLE.border}15, ${STYLE.border}15 1px, transparent 1px, transparent 20px)`,
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
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          gap: 16,
        }}
      >
        {/* 체크리스트 카드들 */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: cardGap,
            width: "fit-content",
            minWidth: "40%",
            maxWidth: "95%",
          }}
        >
          {items.map((item, i) => {
            const isPass = values[i] === 1;
            const desc = descriptions[i] ?? "";
            const color = isPass ? passColor : failColor;
            const bgTintColor = isPass ? passBg : failBg;

            // Phase 1: 카드 등장 (아이콘 숨김)
            const entranceDelay = ENTRANCE_BASE + i * ENTRANCE_STAGGER;
            const itemOpacity = interpolate(frame, [entranceDelay, entranceDelay + FADE_IN], [0, 1], {
              extrapolateLeft: "clamp", extrapolateRight: "clamp",
            });
            const itemSlide = interpolate(frame, [entranceDelay, entranceDelay + FADE_IN], [-20, 0], {
              extrapolateLeft: "clamp", extrapolateRight: "clamp",
            });

            // Phase 2: 나레이션 싱크 시점에 아이콘 공개
            const syncDelay = calcItemDelay(i, fps, vizAnimation, 0, 0);

            // spring() 기반 아이콘 팝 애니메이션
            const iconSpring = syncDelay > 0
              ? spring({
                  frame: frame - syncDelay,
                  fps,
                  config: { damping: 12, stiffness: 200, mass: 0.8 },
                })
              : 0;
            const iconVisible = frame >= syncDelay && syncDelay > 0;

            // 하이라이트 (표준 trapezoidal)
            const HIGHLIGHT_IN = 8;
            const HIGHLIGHT_HOLD = 20;
            const HIGHLIGHT_OUT = 12;
            const hl = interpolate(
              frame,
              [syncDelay, syncDelay + HIGHLIGHT_IN, syncDelay + HIGHLIGHT_IN + HIGHLIGHT_HOLD, syncDelay + HIGHLIGHT_IN + HIGHLIGHT_HOLD + HIGHLIGHT_OUT],
              [0, 1, 1, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
            );

            const scale = 1 + hl * 0.02;
            const shadowBlur = 16 + hl * 16;
            const shadowAlpha = 0.06 + hl * 0.1;

            // 배경 틴트: 아이콘 공개 후 활성화
            const bgTint = iconVisible ? bgTintColor : STYLE.cardBg;

            return (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 16,
                  background: bgTint,
                  padding: `${cardPadV}px 24px`,
                  borderRadius: STYLE.cardRadius,
                  boxShadow: `0 3px ${shadowBlur}px rgba(61,59,47,${shadowAlpha})`,
                  borderLeft: iconVisible ? `4px solid ${color}` : `4px solid ${STYLE.grid}`,
                  opacity: itemOpacity,
                  transform: `translateY(${itemSlide}px) scale(${scale})`,
                  transformOrigin: "left center",
                }}
              >
                {/* 아이콘 영역 */}
                <div
                  style={{
                    width: iconSize,
                    height: iconSize,
                    borderRadius: "50%",
                    background: iconVisible ? color : STYLE.grid,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                    transform: iconVisible ? `scale(${iconSpring})` : "scale(0)",
                    opacity: iconVisible ? 1 : 0.3,
                  }}
                >
                  {iconVisible && (
                    <svg width={iconSize * 0.55} height={iconSize * 0.55} viewBox="0 0 24 24">
                      {isPass ? (
                        // 체크마크
                        <path
                          d="M5 13l4 4L19 7"
                          fill="none"
                          stroke="white"
                          strokeWidth={3}
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      ) : (
                        // X 마크
                        <g>
                          <path d="M6 6l12 12" fill="none" stroke="white" strokeWidth={3} strokeLinecap="round" />
                          <path d="M18 6l-12 12" fill="none" stroke="white" strokeWidth={3} strokeLinecap="round" />
                        </g>
                      )}
                    </svg>
                  )}
                  {!iconVisible && (
                    <span style={{ color: STYLE.subtitle, fontSize: 16, fontWeight: 600 }}>?</span>
                  )}
                </div>

                {/* 텍스트 */}
                <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 2 }}>
                  <span
                    style={{
                      color: STYLE.text,
                      fontSize: textSize,
                      fontWeight: TYPO.label.weight,
                      lineHeight: 1.4,
                    }}
                  >
                    {item}
                  </span>
                  {desc && (
                    <span
                      style={{
                        color: STYLE.subtitle,
                        fontSize: textSize - 8,
                        fontWeight: TYPO.caption.weight,
                        lineHeight: 1.3,
                      }}
                    >
                      {desc}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* 요약 배지 */}
        {values.length > 0 && (
          <div
            style={{
              marginTop: 8,
              padding: "10px 24px",
              borderRadius: 20,
              background: passCount === totalCount ? passBg : `${STYLE.grid}`,
              border: `2px solid ${passCount === totalCount ? passColor : STYLE.grid}40`,
              opacity: interpolate(
                frame,
                [ENTRANCE_BASE + n * ENTRANCE_STAGGER + 8, ENTRANCE_BASE + n * ENTRANCE_STAGGER + 18],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
              ),
            }}
          >
            <span
              style={{
                color: passCount === totalCount ? passColor : STYLE.text,
                fontSize: TYPO.label.size,
                fontWeight: TYPO.title.weight,
              }}
            >
              {passCount}/{totalCount} 달성
            </span>
          </div>
        )}
      </div>
    </VizShell>
  );
};
