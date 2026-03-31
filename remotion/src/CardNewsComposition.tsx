import React from "react";
import { AbsoluteFill, Img, useCurrentFrame, interpolate } from "remotion";

/**
 * 카드뉴스 컴포지션 — 정사각형 1080×1080
 * 1장 = 1프레임 (정적 이미지 export용)
 *
 * Props:
 * - backgroundImage: 배경 이미지
 * - title: 상단 제목
 * - body: 본문 텍스트
 * - pageNumber: 페이지 번호 (1~10)
 * - totalPages: 전체 페이지 수
 * - channelName: 채널명
 * - isCover: 커버 페이지 여부
 * - isCTA: CTA 페이지 여부
 */

interface CardNewsProps {
  backgroundImage?: string;
  title: string;
  body?: string;
  pageNumber: number;
  totalPages: number;
  channelName?: string;
  isCover?: boolean;
  isCTA?: boolean;
  accentColor?: string;
}

export const CardNewsComposition: React.FC<CardNewsProps> = ({
  backgroundImage,
  title,
  body = "",
  pageNumber,
  totalPages,
  channelName = "SEMOJI",
  isCover = false,
  isCTA = false,
  accentColor = "#FF6B35",
}) => {
  if (isCover) {
    return (
      <AbsoluteFill style={{ backgroundColor: "#1a1a2e" }}>
        {backgroundImage && (
          <AbsoluteFill>
            <Img
              src={backgroundImage}
              style={{ width: "100%", height: "100%", objectFit: "cover", opacity: 0.4 }}
            />
          </AbsoluteFill>
        )}
        <AbsoluteFill
          style={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            alignItems: "center",
            padding: 60,
          }}
        >
          <div
            style={{
              fontSize: 56,
              fontWeight: 900,
              color: "#FFFFFF",
              textAlign: "center",
              lineHeight: 1.3,
              wordBreak: "keep-all",
              fontFamily: "'Pretendard', 'Noto Sans KR', sans-serif",
              textShadow: "2px 2px 8px rgba(0,0,0,0.8)",
            }}
          >
            {title}
          </div>
          <div
            style={{
              marginTop: 30,
              fontSize: 24,
              color: accentColor,
              fontWeight: 600,
              fontFamily: "'Pretendard', 'Noto Sans KR', sans-serif",
            }}
          >
            @{channelName}
          </div>
        </AbsoluteFill>
      </AbsoluteFill>
    );
  }

  if (isCTA) {
    return (
      <AbsoluteFill
        style={{
          backgroundColor: accentColor,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          padding: 60,
        }}
      >
        <div style={{ fontSize: 48, fontWeight: 900, color: "#FFFFFF", textAlign: "center", fontFamily: "'Pretendard', sans-serif" }}>
          {title || "전체 영상 보러가기"}
        </div>
        <div style={{ marginTop: 24, fontSize: 28, color: "#FFFFFF", opacity: 0.9, fontFamily: "'Pretendard', sans-serif" }}>
          @{channelName}
        </div>
      </AbsoluteFill>
    );
  }

  // 본문 페이지
  return (
    <AbsoluteFill style={{ backgroundColor: "#FFFFFF" }}>
      {backgroundImage && (
        <AbsoluteFill>
          <Img
            src={backgroundImage}
            style={{ width: "100%", height: "100%", objectFit: "cover", opacity: 0.15 }}
          />
        </AbsoluteFill>
      )}
      <AbsoluteFill
        style={{
          display: "flex",
          flexDirection: "column",
          padding: 60,
        }}
      >
        {/* 상단 바 */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 30 }}>
          <div style={{ width: 60, height: 4, backgroundColor: accentColor, borderRadius: 2 }} />
          <div style={{ fontSize: 16, color: "#999", fontFamily: "'Pretendard', sans-serif" }}>
            {pageNumber}/{totalPages}
          </div>
        </div>

        {/* 제목 */}
        <div
          style={{
            fontSize: 36,
            fontWeight: 800,
            color: "#1a1a2e",
            lineHeight: 1.3,
            marginBottom: 24,
            wordBreak: "keep-all",
            fontFamily: "'Pretendard', 'Noto Sans KR', sans-serif",
          }}
        >
          {title}
        </div>

        {/* 본문 */}
        {body && (
          <div
            style={{
              fontSize: 24,
              fontWeight: 400,
              color: "#444",
              lineHeight: 1.6,
              flex: 1,
              wordBreak: "keep-all",
              fontFamily: "'Pretendard', 'Noto Sans KR', sans-serif",
            }}
          >
            {body}
          </div>
        )}

        {/* 하단 채널명 */}
        <div style={{ fontSize: 16, color: "#999", textAlign: "right", fontFamily: "'Pretendard', sans-serif" }}>
          @{channelName}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
