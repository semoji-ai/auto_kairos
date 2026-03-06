import React from "react";
import { AbsoluteFill, Img, useCurrentFrame, interpolate } from "remotion";
import { useDesignTokens } from "../contexts/DesignTokenContext";
import { useVizBackground } from "../contexts/VizBackgroundContext";
import { resolveAsset } from "../utils/resolveAsset";
import { resolveEasing } from "../utils/easingMap";
import { VIZ_STRINGS } from "./vizI18n";
import type { VizAnimationConfig } from "../types/manifest";

/** 출처/제목/차트 영역의 등장 프레임 상수 */
export const ANIM = {
  SOURCE_START: 8,
  SOURCE_END: 18,
  CONTENT_FADE_START: 8,
  CONTENT_FADE_END: 18,
} as const;

interface VizShellProps {
  title?: string;
  source?: string;
  children: React.ReactNode;
  /** 슬라이드 타입별 고유 배경 (AbsoluteFill 내부에 렌더) */
  background?: React.ReactNode;
  durationInFrames: number;
  vizAnimation?: VizAnimationConfig;
  /** 출처 접두어 오버라이드 */
  sourcePrefix?: string;
  /** 제목 영역 숨김 (SlideHighlight 등 자체 타이틀 처리 시) */
  hideTitle?: boolean;
}

/**
 * 시각화 컴포넌트 공통 래퍼
 *
 * 모든 viz 컴포넌트에서 반복되던 구조를 통합:
 * - 배경 + 폰트 + 패딩
 * - 출처 텍스트 (우상단)
 * - 제목 + 악센트 바
 * - 컨텐츠 영역 (children)
 * - 퇴장 애니메이션
 * - 세이프존 스페이서
 */
export const VizShell: React.FC<VizShellProps> = ({
  title,
  source,
  children,
  background,
  durationInFrames,
  vizAnimation,
  sourcePrefix = VIZ_STRINGS.source_prefix,
  hideTitle = false,
}) => {
  const { STYLE, TYPO, LAYOUT, VIZ_FONT, VIZ_TITLE_FONT } = useDesignTokens();
  const vizBgPath = useVizBackground();
  const frame = useCurrentFrame();

  const easingFn = resolveEasing(vizAnimation?.easing);
  const titleFadeIn = vizAnimation?.titleFadeIn ?? 15;
  const titleSlideUp = vizAnimation?.titleSlideUp ?? 10;

  // 퇴장 애니메이션
  const exitDuration = vizAnimation?.exitFadeOut ?? 0;
  const exitStart = durationInFrames - exitDuration;
  const exitOpacity =
    exitDuration > 0
      ? interpolate(frame, [exitStart, durationInFrames], [1, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        })
      : 1;
  const exitTransform =
    exitDuration > 0 && vizAnimation?.exitDirection
      ? (() => {
          const progress = interpolate(
            frame,
            [exitStart, durationInFrames],
            [0, 1],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
          );
          switch (vizAnimation.exitDirection) {
            case "down":
              return `translateY(${progress * 20}px)`;
            case "up":
              return `translateY(${-progress * 20}px)`;
            case "scale":
              return `scale(${1 - progress * 0.05})`;
            default:
              return "none";
          }
        })()
      : "none";

  // 출처 페이드인
  const sourceOpacity = interpolate(
    frame,
    [ANIM.SOURCE_START, ANIM.SOURCE_END],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  // 제목 페이드인 + 슬라이드업
  const titleOpacity = interpolate(frame, [0, titleFadeIn], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: easingFn,
  });
  const titleTranslateY = interpolate(
    frame,
    [0, titleFadeIn],
    [-titleSlideUp, 0],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: easingFn,
    },
  );

  const accentColor = STYLE.colors[STYLE.accentIndex ?? 0];

  return (
    <AbsoluteFill style={{ fontFamily: VIZ_FONT }}>
      {/* 레이어 0: 아트스타일 배경 이미지 (있으면) */}
      {vizBgPath ? (
        <>
          <AbsoluteFill>
            <Img
              src={resolveAsset(vizBgPath)}
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
              }}
            />
          </AbsoluteFill>
          {/* 반투명 오버레이: 가독성 보장 */}
          <AbsoluteFill
            style={{ background: `${STYLE.background}D0` }}
          />
        </>
      ) : (
        /* 기본: 단색 배경 */
        <AbsoluteFill style={{ background: STYLE.background }} />
      )}

      {/* 컴포넌트별 고유 배경 */}
      {background}

      {/* 메인 컨텐츠 */}
      <AbsoluteFill
        style={{
          padding: `${LAYOUT.topMargin}% ${LAYOUT.sidePadding}% 0`,
          flexDirection: "column",
          opacity: exitOpacity,
          transform: exitTransform !== "none" ? exitTransform : undefined,
        }}
      >
        {/* 출처 */}
        {source && (
          <div
            style={{
              position: "absolute",
              top: `${LAYOUT.topMargin + 1}%`,
              right: `${LAYOUT.sidePadding + 2}%`,
              color: STYLE.source,
              fontSize: TYPO.caption.size,
              opacity: sourceOpacity,
              zIndex: 2,
            }}
          >
            {sourcePrefix} {source}
          </div>
        )}

        {/* 제목 + 악센트 바 — 빈 제목이면 렌더링하지 않음 */}
        {!hideTitle && title && title.trim() !== "" && (
          <div
            style={{
              textAlign: "center",
              marginBottom: "2%",
              opacity: titleOpacity,
              transform: `translateY(${titleTranslateY}px)`,
            }}
          >
            <div
              style={{
                color: STYLE.text,
                fontSize: TYPO.title.size,
                fontWeight: TYPO.title.weight,
                fontFamily: VIZ_TITLE_FONT,
                letterSpacing: TYPO.title.letterSpacing,
              }}
            >
              {title}
            </div>
            <div
              style={{
                width: 60,
                height: 4,
                background: accentColor,
                borderRadius: 2,
                margin: "8px auto 0",
              }}
            />
          </div>
        )}

        {/* 컨텐츠 영역 */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}>
          {children}
        </div>

        {/* 세이프존 스페이서 (자막 오버레이와 겹침 방지) */}
        <div
          style={{ height: `${LAYOUT.safeZoneHeight}%`, flexShrink: 0 }}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
