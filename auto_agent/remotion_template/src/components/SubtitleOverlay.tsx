import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import type { SubtitleEntry, SubtitleConfig } from "../types/manifest";

interface Props {
  subtitles: SubtitleEntry[];
  fps: number;
  config: SubtitleConfig;
}

/**
 * 유튜브 교양 스타일 자막
 * - SubtitleConfig로 폰트/크기/색상/위치 전부 제어
 * - 키워드 하이라이트
 */
export const SubtitleOverlay: React.FC<Props> = ({ subtitles, fps, config }) => {
  const frame = useCurrentFrame();
  const currentTimeSec = frame / fps;

  // 마지막 자막은 씬 끝까지 유지 (오디오+2프레임 여유분 커버)
  const activeSub = subtitles.find(
    (s, i) => currentTimeSec >= s.startSec && (
      i === subtitles.length - 1
        ? currentTimeSec <= s.endSec + 1  // 마지막 자막: 1초 여유
        : currentTimeSec < s.endSec
    ),
  );

  if (!activeSub) return null;

  const subStartFrame = Math.floor(activeSub.startSec * fps);
  const fadeInProgress = interpolate(
    frame,
    [subStartFrame, subStartFrame + 5],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const baseStyle: React.CSSProperties = {
    fontSize: config.fontSize,
    fontWeight: config.fontWeight,
    fontFamily: config.fontFamily,
    color: config.color,
    WebkitTextStroke: `${config.strokeWidth}px ${config.strokeColor}`,
    textShadow: "2px 2px 6px rgba(0, 0, 0, 0.6), 0 0 12px rgba(0, 0, 0, 0.3)",
    paintOrder: "stroke fill",
    letterSpacing: "0.02em",
  };

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: config.bottomOffset,
      }}
    >
      <div
        style={{
          opacity: fadeInProgress,
          transform: `translateY(${interpolate(fadeInProgress, [0, 1], [8, 0])}px)`,
          maxWidth: config.maxWidth,
          textAlign: "center",
          lineHeight: config.lineHeight,
          backgroundColor: "rgba(0, 0, 0, 0.8)",
          padding: `${Math.round(config.fontSize * 0.2)}px ${Math.round(config.fontSize * 0.5)}px`,
          borderRadius: 50,
        }}
      >
        {activeSub.words && activeSub.words.length > 0
          ? renderWordsHighlight(activeSub.words, currentTimeSec, baseStyle, config)
          : renderTextWithKeywords(activeSub.text, activeSub.keywords, baseStyle, config)}
      </div>
    </AbsoluteFill>
  );
};

function renderWordsHighlight(
  words: { word: string; start: number; end: number }[],
  currentTimeSec: number,
  baseStyle: React.CSSProperties,
  config: SubtitleConfig,
): React.ReactNode {
  return (
    <span style={baseStyle}>
      {words.map((w, i) => {
        const isPast = currentTimeSec >= w.end;
        const isCurrent = currentTimeSec >= w.start && currentTimeSec < w.end;
        return (
          <React.Fragment key={i}>
            <span
              style={{
                color: isCurrent ? config.keywordColor : isPast ? config.color : config.color,
                opacity: isCurrent || isPast ? 1 : 0.5,
                WebkitTextStroke: isCurrent
                  ? `${config.strokeWidth}px ${config.keywordStrokeColor}`
                  : `${config.strokeWidth}px ${config.strokeColor}`,
                transition: "color 0.1s, opacity 0.1s",
              }}
            >
              {w.word}
            </span>
            {i < words.length - 1 ? " " : ""}
          </React.Fragment>
        );
      })}
    </span>
  );
}

function renderTextWithKeywords(
  text: string,
  keywords: string[] | undefined,
  baseStyle: React.CSSProperties,
  config: SubtitleConfig,
): React.ReactNode {
  if (!keywords || keywords.length === 0) {
    return <span style={baseStyle}>{text}</span>;
  }

  const pattern = new RegExp(`(${keywords.map(escapeRegex).join("|")})`, "g");
  const parts = text.split(pattern);

  return (
    <span style={baseStyle}>
      {parts.map((part, i) =>
        keywords.some((k) => k === part) ? (
          <span
            key={i}
            style={{
              color: config.keywordColor,
              WebkitTextStroke: `${config.strokeWidth}px ${config.keywordStrokeColor}`,
            }}
          >
            {part}
          </span>
        ) : (
          <React.Fragment key={i}>{part}</React.Fragment>
        ),
      )}
    </span>
  );
}

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
