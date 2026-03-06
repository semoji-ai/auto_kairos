import React from "react";
import { AbsoluteFill, Img, useCurrentFrame, interpolate, spring } from "remotion";
import { useDesignTokens } from "../contexts/DesignTokenContext";
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
 * 질문-답변 카드
 *
 * - items: [Q1, A1, Q2, A2, ...] 교대 배열
 * - 질문이 먼저 등장, 나레이션 싱크 시점에 답변 블러 해제
 */
export const SlideQna: React.FC<Props> = ({ data, durationInFrames, fps, vizAnimation }) => {
  const { STYLE, TYPO, VIZ_TITLE_FONT } = useDesignTokens();
  const frame = useCurrentFrame();
  const easingFn = resolveEasing(vizAnimation?.easing);

  const imagePath =
    typeof data.imagePath === "string" ? data.imagePath : undefined;
  const hasImage = !!imagePath;

  const items = data.items ?? [];

  // Q&A 쌍 파싱
  const pairs: { question: string; answer: string }[] = [];
  for (let i = 0; i < items.length; i += 2) {
    pairs.push({
      question: items[i] ?? "",
      answer: items[i + 1] ?? "",
    });
  }

  const hasSingle = pairs.length === 1;
  const accentColor = STYLE.colors[STYLE.accentIndex ?? 0];
  const grad = STYLE.gradients[0];

  // Background: large faded question mark
  const bg = (
    <AbsoluteFill
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        opacity: 0.04,
        overflow: "hidden",
      }}
    >
      <span
        style={{
          fontSize: 500,
          fontWeight: 900,
          color: STYLE.text,
          lineHeight: 1,
          userSelect: "none",
        }}
      >
        ?
      </span>
    </AbsoluteFill>
  );

  if (hasSingle) {
    // 단일 Q&A: 상단 질문 + 하단 답변 (풀사이즈)
    return (
      <VizShell
        title={data.title}
        source={data.source}
        durationInFrames={durationInFrames}
        vizAnimation={vizAnimation}
        background={bg}
        hideTitle={!data.title || data.title.trim() === ""}
      >
        <div style={{ flex: 1, display: "flex", flexDirection: "row" }}>
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
                  borderRadius: STYLE.cardRadius,
                  boxShadow: STYLE.cardShadow,
                }}
              />
            </div>
          )}
          <SingleQA
            question={pairs[0].question}
            answer={pairs[0].answer}
            qIndex={0}
            aIndex={1}
            fps={fps}
            vizAnimation={vizAnimation}
          />
        </div>
      </VizShell>
    );
  }

  // 멀티 Q&A: 카드 리스트
  return (
    <VizShell
      title={data.title}
      source={data.source}
      durationInFrames={durationInFrames}
      vizAnimation={vizAnimation}
      background={bg}
      hideTitle={!data.title || data.title.trim() === ""}
    >
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          gap: 20,
        }}
      >
        {pairs.map((pair, i) => (
          <MultiQACard
            key={i}
            question={pair.question}
            answer={pair.answer}
            qIndex={i * 2}
            aIndex={i * 2 + 1}
            pairIndex={i}
            fps={fps}
            vizAnimation={vizAnimation}
          />
        ))}
      </div>
    </VizShell>
  );
};

// ─── 단일 Q&A 레이아웃 ──────────────────────────────

const SingleQA: React.FC<{
  question: string;
  answer: string;
  qIndex: number;
  aIndex: number;
  fps: number;
  vizAnimation?: VizAnimationConfig;
}> = ({ question, answer, qIndex, aIndex, fps, vizAnimation }) => {
  const { STYLE, TYPO, VIZ_TITLE_FONT } = useDesignTokens();
  const frame = useCurrentFrame();
  const easingFn = resolveEasing(vizAnimation?.easing);
  const accentColor = STYLE.colors[STYLE.accentIndex ?? 0];
  const grad = STYLE.gradients[0];

  // 질문 등장
  const Q_START = 5;
  const Q_FADE = 14;
  const qOpacity = interpolate(frame, [Q_START, Q_START + Q_FADE], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const qSlide = interpolate(frame, [Q_START, Q_START + Q_FADE], [-25, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easingFn,
  });

  // 물음표 pulse
  const qMarkScale = interpolate(frame, [Q_START + 8, Q_START + 16, Q_START + 20], [0.9, 1.1, 1.0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  // 답변: 나레이션 싱크 시점에 공개
  const aSyncDelay = calcItemDelay(aIndex, fps, vizAnimation, 0, 0);
  const answerVisible = frame >= aSyncDelay && aSyncDelay > 0;

  // 블러 해제 + spring 등장 (base: 반투명+약한 블러로 "티저" 효과)
  const aBlur = answerVisible
    ? interpolate(frame, [aSyncDelay, aSyncDelay + 10], [5, 0], {
        extrapolateLeft: "clamp", extrapolateRight: "clamp",
      })
    : 5;
  const aOpacity = answerVisible
    ? interpolate(frame, [aSyncDelay, aSyncDelay + 12], [0.35, 1], {
        extrapolateLeft: "clamp", extrapolateRight: "clamp",
      })
    : 0.35;
  const aSpring = aSyncDelay > 0
    ? spring({ frame: frame - aSyncDelay, fps, config: { damping: 14, stiffness: 180, mass: 0.8 } })
    : 0;
  const aSlide = answerVisible ? (1 - aSpring) * 15 : 15;

  // 답변 하이라이트
  const HIGHLIGHT_IN = 8;
  const HIGHLIGHT_HOLD = 20;
  const HIGHLIGHT_OUT = 12;
  const aHl = interpolate(
    frame,
    [aSyncDelay, aSyncDelay + HIGHLIGHT_IN, aSyncDelay + HIGHLIGHT_IN + HIGHLIGHT_HOLD, aSyncDelay + HIGHLIGHT_IN + HIGHLIGHT_HOLD + HIGHLIGHT_OUT],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  return (
    <div
      style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        gap: 32,
        maxWidth: "85%",
        margin: "0 auto",
      }}
    >
      {/* 질문 영역 */}
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          gap: 20,
          opacity: qOpacity,
          transform: `translateX(${qSlide}px)`,
          width: "100%",
        }}
      >
        {/* Q 마크 */}
        <div
          style={{
            width: 56,
            height: 56,
            borderRadius: "50%",
            background: `linear-gradient(135deg, ${grad[0]}, ${grad[1]})`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "white",
            fontSize: 28,
            fontWeight: 800,
            flexShrink: 0,
            transform: `scale(${qMarkScale})`,
            boxShadow: `0 4px 12px ${grad[0]}40`,
          }}
        >
          Q
        </div>
        <div
          style={{
            flex: 1,
            background: STYLE.cardBg,
            borderRadius: STYLE.cardRadius,
            padding: "24px 28px",
            boxShadow: STYLE.cardShadow,
            borderTop: `4px solid ${accentColor}`,
          }}
        >
          <span
            style={{
              color: STYLE.text,
              fontSize: TYPO.title.size - 4,
              fontWeight: TYPO.title.weight,
              fontFamily: VIZ_TITLE_FONT,
              lineHeight: 1.5,
            }}
          >
            {question}
          </span>
        </div>
      </div>

      {/* 답변 영역 */}
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          gap: 20,
          width: "100%",
          opacity: aOpacity,
          transform: `translateY(${aSlide}px)`,
          filter: `blur(${aBlur}px)`,
        }}
      >
        <div style={{ width: 56, flexShrink: 0 }} /> {/* 들여쓰기 spacer */}
        <div
          style={{
            flex: 1,
            background: answerVisible
              ? `linear-gradient(135deg, ${accentColor}08, ${STYLE.cardBg})`
              : STYLE.cardBg,
            borderRadius: STYLE.cardRadius,
            padding: "24px 28px",
            boxShadow: `0 4px ${16 + aHl * 16}px rgba(61,59,47,${0.06 + aHl * 0.1})`,
            borderLeft: `4px solid ${accentColor}`,
          }}
        >
          <div
            style={{
              color: accentColor,
              fontSize: TYPO.label.size - 2,
              fontWeight: TYPO.title.weight,
              marginBottom: 8,
              opacity: answerVisible ? 1 : 0,
            }}
          >
            A
          </div>
          <span
            style={{
              color: STYLE.text,
              fontSize: TYPO.subtitle.size + 2,
              fontWeight: TYPO.subtitle.weight,
              lineHeight: 1.6,
            }}
          >
            {answer}
          </span>
        </div>
      </div>
    </div>
  );
};

// ─── 멀티 Q&A 카드 ──────────────────────────────────

const MultiQACard: React.FC<{
  question: string;
  answer: string;
  qIndex: number;
  aIndex: number;
  pairIndex: number;
  fps: number;
  vizAnimation?: VizAnimationConfig;
}> = ({ question, answer, qIndex, aIndex, pairIndex, fps, vizAnimation }) => {
  const { STYLE, TYPO } = useDesignTokens();
  const frame = useCurrentFrame();
  const accentColor = STYLE.colors[STYLE.accentIndex ?? 0];
  const color = STYLE.colors[pairIndex % STYLE.colors.length];

  const ENTRANCE_BASE = 8;
  const STAGGER = 8;
  const FADE_IN = 12;

  const entranceDelay = ENTRANCE_BASE + pairIndex * STAGGER;
  const cardOpacity = interpolate(frame, [entranceDelay, entranceDelay + FADE_IN], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const cardSlide = interpolate(frame, [entranceDelay, entranceDelay + FADE_IN], [-20, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  // 답변 공개 (base: 반투명+약한 블러로 "티저" 효과)
  const aSyncDelay = calcItemDelay(aIndex, fps, vizAnimation, 0, 0);
  const answerVisible = frame >= aSyncDelay && aSyncDelay > 0;
  const aBlur = answerVisible
    ? interpolate(frame, [aSyncDelay, aSyncDelay + 8], [4, 0], {
        extrapolateLeft: "clamp", extrapolateRight: "clamp",
      })
    : 4;
  const aOpacity = answerVisible
    ? interpolate(frame, [aSyncDelay, aSyncDelay + 10], [0.3, 1], {
        extrapolateLeft: "clamp", extrapolateRight: "clamp",
      })
    : 0.3;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 8,
        width: "85%",
        opacity: cardOpacity,
        transform: `translateY(${cardSlide}px)`,
      }}
    >
      {/* 질문 */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          background: STYLE.cardBg,
          borderRadius: STYLE.cardRadius,
          padding: "14px 20px",
          borderLeft: `4px solid ${color}`,
          boxShadow: STYLE.cardShadow,
        }}
      >
        <span style={{ color, fontSize: TYPO.label.size, fontWeight: 800 }}>Q</span>
        <span style={{ color: STYLE.text, fontSize: TYPO.label.size + 2, fontWeight: TYPO.label.weight, lineHeight: 1.4 }}>
          {question}
        </span>
      </div>

      {/* 답변 */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          background: answerVisible ? `${accentColor}06` : STYLE.cardBg,
          borderRadius: STYLE.cardRadius,
          padding: "14px 20px",
          marginLeft: 32,
          borderLeft: `4px solid ${accentColor}30`,
          opacity: aOpacity,
          filter: `blur(${aBlur}px)`,
        }}
      >
        <span style={{ color: accentColor, fontSize: TYPO.label.size, fontWeight: 800 }}>A</span>
        <span style={{ color: STYLE.text, fontSize: TYPO.label.size, fontWeight: TYPO.subtitle.weight, lineHeight: 1.5 }}>
          {answer}
        </span>
      </div>
    </div>
  );
};
