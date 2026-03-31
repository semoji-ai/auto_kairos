import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  Sequence,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
} from "remotion";

/**
 * 숏폼 컴포지션 — 세로형 1080×1920 (9:16)
 *
 * 레이아웃:
 * - 상단 블랙: 제목 (크게, 노란색)
 * - 중앙: 16:9 이미지 (전체 레이아웃 센터, 110%)
 * - 이미지 아래: 자막 (TTS 원고 그대로, 큰 폰트)
 * - 하단: 채널명
 */

interface ShortScene {
  image: string;
  subtitle: string;
  durationInFrames: number;
  audioUrl?: string;
}

interface ShortsProps {
  scenes: ShortScene[];
  fixedTitle?: string;
  channelName?: string;
  ttsPlaybackRate?: number;
  imageScale?: number;
}

// 1080px 너비의 16:9 이미지 높이 = 608px
// 전체 1920에서 센터 배치 → 이미지 top = (1920 - 608) / 2 = 656
const IMAGE_W = 1080;
const IMAGE_H = 608;
const IMAGE_TOP = (1920 - IMAGE_H) / 2; // 656 — 정확히 센터

export const ShortsComposition: React.FC<ShortsProps> = ({
  scenes,
  fixedTitle = "",
  channelName = "",
  ttsPlaybackRate = 1.0,
  imageScale = 1.1,
}) => {
  let currentFrame = 0;

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      {/* 씬별 시퀀스 */}
      {scenes.map((scene, i) => {
        const from = currentFrame;
        currentFrame += scene.durationInFrames;

        return (
          <Sequence key={i} from={from} durationInFrames={scene.durationInFrames}>
            {/* 이미지 — 전체 레이아웃 센터 */}
            <div
              style={{
                position: "absolute",
                top: IMAGE_TOP,
                left: 0,
                right: 0,
                height: IMAGE_H,
                overflow: "hidden",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <SlowZoomImage image={scene.image} imageScale={imageScale} />
            </div>

            {/* 자막 — 이미지 바로 아래, TTS 원고 그대로, 큰 폰트 */}
            {scene.subtitle && (
              <div
                style={{
                  position: "absolute",
                  top: IMAGE_TOP + IMAGE_H + 20,
                  left: 30,
                  right: 30,
                  textAlign: "center",
                }}
              >
                <div
                  style={{
                    fontSize: 72,
                    fontWeight: 800,
                    color: "#FFFFFF",
                    lineHeight: 1.5,
                    wordBreak: "keep-all",
                    fontFamily: "'Pretendard', 'Noto Sans KR', sans-serif",
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {scene.subtitle}
                </div>
              </div>
            )}

            {/* 오디오 */}
            {scene.audioUrl && (
              <Audio
                src={scene.audioUrl.startsWith("http") ? scene.audioUrl : staticFile(scene.audioUrl)}
                playbackRate={ttsPlaybackRate}
              />
            )}
          </Sequence>
        );
      })}

      {/* 상단 블랙 — 고정 제목 (2배 크기, 노란색, 센터) */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: IMAGE_TOP,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "0 40px",
        }}
      >
        {fixedTitle && (
          <div
            style={{
              fontSize: 100,
              fontWeight: 900,
              color: "#FFD700",
              textAlign: "center",
              lineHeight: 1.3,
              wordBreak: "keep-all",
              fontFamily: "'Pretendard', 'Noto Sans KR', sans-serif",
              whiteSpace: "pre-wrap",
            }}
          >
            {fixedTitle}
          </div>
        )}
      </div>

      {/* 하단 — 채널명 */}
      <div
        style={{
          position: "absolute",
          bottom: 60,
          left: 0,
          right: 0,
          textAlign: "center",
        }}
      >
        {channelName && (
          <div
            style={{
              fontSize: 36,
              fontWeight: 600,
              color: "#FFFFFF",
              opacity: 0.5,
              fontFamily: "'Pretendard', 'Noto Sans KR', sans-serif",
            }}
          >
            {channelName}
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};

const SlowZoomImage: React.FC<{ image: string; imageScale: number }> = ({
  image,
  imageScale,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const scale = interpolate(frame, [0, fps * 5], [imageScale, imageScale + 0.03], {
    extrapolateRight: "clamp",
  });

  return (
    <Img
      src={image.startsWith("http") ? image : staticFile(image)}
      style={{
        width: "100%",
        height: "auto",
        transform: `scale(${scale})`,
      }}
    />
  );
};
