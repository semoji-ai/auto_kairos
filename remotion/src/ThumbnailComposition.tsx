import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";

/**
 * 썸네일 컴포지션 — 배경 이미지 + 오버레이 텍스트
 *
 * Props:
 * - backgroundImage: 배경 이미지 경로 (project 내 상대경로)
 * - title: 오버레이 제목 텍스트
 * - subtitle: 부제목 (선택)
 * - channelName: 채널명 (하단)
 * - titlePosition: "center" | "bottom-left" | "bottom-center"
 * - fontSize: 제목 폰트 크기 (기본 72)
 * - fontColor: 제목 색상 (기본 white)
 * - shadowColor: 텍스트 그림자 (기본 rgba(0,0,0,0.8))
 */

interface ThumbnailProps {
  backgroundImage: string;
  title: string;
  subtitle?: string;
  channelName?: string;
  titlePosition?: "center" | "bottom-left" | "bottom-center";
  fontSize?: number;
  fontColor?: string;
  shadowColor?: string;
  overlayOpacity?: number;
}

export const ThumbnailComposition: React.FC<ThumbnailProps> = ({
  backgroundImage,
  title,
  subtitle = "",
  channelName = "",
  titlePosition = "bottom-left",
  fontSize = 72,
  fontColor = "#FFFFFF",
  shadowColor = "rgba(0,0,0,0.8)",
  overlayOpacity = 0.3,
}) => {
  const positionStyles: Record<string, React.CSSProperties> = {
    center: {
      justifyContent: "center",
      alignItems: "center",
      textAlign: "center" as const,
    },
    "bottom-left": {
      justifyContent: "flex-end",
      alignItems: "flex-start",
      padding: "60px 80px",
    },
    "bottom-center": {
      justifyContent: "flex-end",
      alignItems: "center",
      padding: "60px 80px",
      textAlign: "center" as const,
    },
  };

  return (
    <AbsoluteFill>
      {/* 배경 이미지 */}
      {backgroundImage ? (
        <AbsoluteFill>
          <Img
            src={backgroundImage}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
            }}
          />
        </AbsoluteFill>
      ) : (
        <AbsoluteFill style={{ backgroundColor: "#1a1a2e" }} />
      )}

      {/* 어두운 오버레이 (텍스트 가독성) */}
      <AbsoluteFill
        style={{
          background: `linear-gradient(transparent 30%, rgba(0,0,0,${overlayOpacity}) 70%, rgba(0,0,0,${overlayOpacity + 0.3}) 100%)`,
        }}
      />

      {/* 텍스트 오버레이 */}
      <AbsoluteFill
        style={{
          display: "flex",
          flexDirection: "column",
          ...positionStyles[titlePosition],
        }}
      >
        {/* 제목 */}
        <div
          style={{
            fontSize,
            fontWeight: 900,
            color: fontColor,
            textShadow: `3px 3px 6px ${shadowColor}, -1px -1px 3px ${shadowColor}`,
            lineHeight: 1.2,
            maxWidth: "85%",
            wordBreak: "keep-all",
            fontFamily: "'Pretendard', 'Noto Sans KR', sans-serif",
          }}
        >
          {title}
        </div>

        {/* 부제목 */}
        {subtitle && (
          <div
            style={{
              fontSize: fontSize * 0.45,
              fontWeight: 600,
              color: fontColor,
              textShadow: `2px 2px 4px ${shadowColor}`,
              marginTop: 16,
              opacity: 0.9,
              fontFamily: "'Pretendard', 'Noto Sans KR', sans-serif",
            }}
          >
            {subtitle}
          </div>
        )}

        {/* 채널명 */}
        {channelName && (
          <div
            style={{
              fontSize: fontSize * 0.3,
              fontWeight: 500,
              color: fontColor,
              textShadow: `1px 1px 3px ${shadowColor}`,
              marginTop: 12,
              opacity: 0.7,
              fontFamily: "'Pretendard', 'Noto Sans KR', sans-serif",
            }}
          >
            {channelName}
          </div>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
