import React from "react";
import { AbsoluteFill, Img, useCurrentFrame, interpolate } from "remotion";
import { STYLE as DEFAULT_STYLE, TYPO as DEFAULT_TYPO } from "./vizStyles";
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
 * 용어/정의 카드
 *
 * - items[0]: 용어 (예: "양적완화")
 * - items[1]: "정의:" 접두어 + 정의 텍스트
 * - items[2+]: "예:" 접두어 + 예시 텍스트
 * - descriptions[0]: 발음/어원 (예: "Quantitative Easing, QE")
 */
export const SlideDefinition: React.FC<Props> = ({ data, durationInFrames, fps, vizAnimation }) => {
  const frame = useCurrentFrame();
  const easingFn = resolveEasing(vizAnimation?.easing);

  const imagePath =
    typeof data.imagePath === "string" ? data.imagePath : undefined;
  const hasImage = !!imagePath;

  const items = data.items ?? [];
  const descriptions = data.descriptions ?? [];
  const term = items[0] ?? "";
  const pronunciation = descriptions[0] ?? "";

  // 정의와 예시 분리
  const definitionItems: string[] = [];
  const exampleItems: string[] = [];
  for (let i = 1; i < items.length; i++) {
    const item = items[i];
    if (item.startsWith("예:") || item.startsWith("예시:")) {
      exampleItems.push(item.replace(/^예시?:\s*/, ""));
    } else {
      definitionItems.push(item.replace(/^정의:\s*/, ""));
    }
  }

  // Adaptive term font size — hero font is too large for long terms
  const termLen = term.length;
  const termFontSize =
    termLen > 25
      ? DEFAULT_TYPO.title.size - 4
      : termLen > 15
        ? DEFAULT_TYPO.title.size
        : termLen > 8
          ? DEFAULT_TYPO.hero.size
          : DEFAULT_TYPO.hero.size + 8;

  const accentColor = DEFAULT_STYLE.colors[DEFAULT_STYLE.accentIndex ?? 0];
  const grad = DEFAULT_STYLE.gradients[0];

  // ── Phase 1: 등장 ──
  const TERM_START = 0;
  const TERM_FADE = 12;
  const UNDERLINE_START = 8;
  const UNDERLINE_DURATION = 15;
  const PRON_START = 12;
  const DEF_START = 18;
  const EXAMPLE_BASE = 26;
  const FADE_IN = 12;
  const STAGGER = 4;

  // 용어 등장
  const termOpacity = interpolate(frame, [TERM_START, TERM_START + TERM_FADE], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easingFn,
  });
  const termScale = interpolate(frame, [TERM_START, TERM_START + TERM_FADE], [0.92, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easingFn,
  });

  // 밑줄 sweep
  const underlineWidth = interpolate(frame, [UNDERLINE_START, UNDERLINE_START + UNDERLINE_DURATION], [0, 100], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easingFn,
  });

  // 발음/어원
  const pronOpacity = interpolate(frame, [PRON_START, PRON_START + FADE_IN], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  // 정의 카드
  const defOpacity = interpolate(frame, [DEF_START, DEF_START + FADE_IN], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const defSlide = interpolate(frame, [DEF_START, DEF_START + FADE_IN], [20, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  // ── Phase 2: 타임스탬프 기반 강조 ──
  // 용어 자체 강조 (syncPoint 0)
  const termSyncDelay = calcItemDelay(0, fps, vizAnimation, 0, 0);
  const HIGHLIGHT_IN = 8;
  const HIGHLIGHT_HOLD = 20;
  const HIGHLIGHT_OUT = 12;
  const termHl = interpolate(
    frame,
    [termSyncDelay, termSyncDelay + HIGHLIGHT_IN, termSyncDelay + HIGHLIGHT_IN + HIGHLIGHT_HOLD, termSyncDelay + HIGHLIGHT_IN + HIGHLIGHT_HOLD + HIGHLIGHT_OUT],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const termGlow = termHl > 0 ? `drop-shadow(0 0 ${8 + termHl * 16}px ${accentColor}40)` : undefined;

  // Background: faint horizontal lines (dictionary style)
  const bg = (
    <AbsoluteFill style={{ opacity: 0.03 }}>
      <div
        style={{
          width: "100%",
          height: "100%",
          backgroundImage: `repeating-linear-gradient(0deg, ${DEFAULT_STYLE.border}20, ${DEFAULT_STYLE.border}20 1px, transparent 1px, transparent 32px)`,
        }}
      />
    </AbsoluteFill>
  );

  return (
    <VizShell
      title=""
      source={data.source}
      durationInFrames={durationInFrames}
      vizAnimation={vizAnimation}
      background={bg}
      hideTitle
    >
      <div style={{ flex: 1, display: "flex", flexDirection: "row" }}>
        {/* Optional image */}
        {hasImage && (
          <div
            style={{
              width: "35%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              paddingRight: "3%",
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
          alignItems: hasImage ? "flex-start" : "center",
          maxWidth: hasImage ? "100%" : "85%",
          margin: hasImage ? 0 : "0 auto",
        }}
      >
        {/* 용어 */}
        <div
          style={{
            opacity: termOpacity,
            transform: `scale(${termScale})`,
            filter: termGlow,
            position: "relative",
            display: "inline-block",
            marginBottom: 8,
          }}
        >
          <span
            style={{
              color: "var(--viz-text)",
              fontSize: termFontSize,
              fontWeight: "var(--viz-hero-weight)" as any,
              fontFamily: "var(--viz-title-font)",
              letterSpacing: "var(--viz-hero-tracking)",
              lineHeight: 1.3,
            }}
          >
            {term}
          </span>
          {/* 밑줄 sweep */}
          <div
            style={{
              position: "absolute",
              bottom: -4,
              left: 0,
              width: `${underlineWidth}%`,
              height: 5,
              background: `linear-gradient(90deg, ${grad[0]}, ${grad[1]})`,
              borderRadius: 3,
            }}
          />
        </div>

        {/* 발음/어원 */}
        {pronunciation && (
          <div
            style={{
              color: "var(--viz-subtitle)",
              fontSize: "var(--viz-label-size)",
              fontWeight: "var(--viz-caption-weight)" as any,
              fontStyle: "italic",
              opacity: pronOpacity,
              marginTop: 12,
              marginBottom: 24,
            }}
          >
            {pronunciation}
          </div>
        )}

        {/* 정의 카드 */}
        {definitionItems.length > 0 && (
          <div
            style={{
              background: "var(--viz-card-bg)",
              borderLeft: `5px solid ${accentColor}`,
              borderRadius: "var(--viz-card-radius)",
              padding: "24px 32px",
              boxShadow: "var(--viz-card-shadow)",
              opacity: defOpacity,
              transform: `translateY(${defSlide}px)`,
              marginTop: pronunciation ? 0 : 24,
              width: "100%",
            }}
          >
            {definitionItems.map((def, i) => {
              const defSyncDelay = calcItemDelay(1 + i, fps, vizAnimation, 0, 0);
              const defHl = interpolate(
                frame,
                [defSyncDelay, defSyncDelay + HIGHLIGHT_IN, defSyncDelay + HIGHLIGHT_IN + HIGHLIGHT_HOLD, defSyncDelay + HIGHLIGHT_IN + HIGHLIGHT_HOLD + HIGHLIGHT_OUT],
                [0, 1, 1, 0],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
              );
              return (
                <div
                  key={i}
                  style={{
                    color: "var(--viz-text)",
                    fontSize: DEFAULT_TYPO.subtitle.size + 2,
                    fontWeight: "var(--viz-subtitle-weight)" as any,
                    lineHeight: 1.65,
                    background: defHl > 0 ? `${accentColor}${Math.round(defHl * 10).toString(16).padStart(2, "0")}` : "transparent",
                    borderRadius: 4,
                    padding: defHl > 0 ? "2px 4px" : 0,
                    marginTop: i > 0 ? 12 : 0,
                  }}
                >
                  {def.split("\\n").map((line, j) => (
                    <React.Fragment key={j}>
                      {j > 0 && <br />}
                      {line}
                    </React.Fragment>
                  ))}
                </div>
              );
            })}
          </div>
        )}

        {/* 예시 불릿 */}
        {exampleItems.length > 0 && (
          <div style={{ marginTop: 24, width: "100%", display: "flex", flexDirection: "column", gap: 12 }}>
            {exampleItems.map((ex, i) => {
              const exDelay = EXAMPLE_BASE + i * STAGGER;
              const exOpacity = interpolate(frame, [exDelay, exDelay + FADE_IN], [0, 1], {
                extrapolateLeft: "clamp", extrapolateRight: "clamp",
              });
              const exSlide = interpolate(frame, [exDelay, exDelay + FADE_IN], [15, 0], {
                extrapolateLeft: "clamp", extrapolateRight: "clamp",
              });

              const exSyncIdx = 1 + definitionItems.length + i;
              const exSyncDelay = calcItemDelay(exSyncIdx, fps, vizAnimation, 0, 0);
              const exHl = interpolate(
                frame,
                [exSyncDelay, exSyncDelay + HIGHLIGHT_IN, exSyncDelay + HIGHLIGHT_IN + HIGHLIGHT_HOLD, exSyncDelay + HIGHLIGHT_IN + HIGHLIGHT_HOLD + HIGHLIGHT_OUT],
                [0, 1, 1, 0],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
              );

              const color = DEFAULT_STYLE.colors[(i + 1) % DEFAULT_STYLE.colors.length];

              return (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 12,
                    opacity: exOpacity,
                    transform: `translateY(${exSlide}px) scale(${1 + exHl * 0.02})`,
                    transformOrigin: "left center",
                  }}
                >
                  <div
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      background: color,
                      marginTop: 10,
                      flexShrink: 0,
                    }}
                  />
                  <span
                    style={{
                      color: "var(--viz-subtitle)",
                      fontSize: DEFAULT_TYPO.label.size + 2,
                      fontWeight: "var(--viz-label-weight)" as any,
                      lineHeight: 1.5,
                    }}
                  >
                    {ex}
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
