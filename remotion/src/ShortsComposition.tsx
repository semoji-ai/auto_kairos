import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from "remotion";

/**
 * 숏폼 컴포지션 — 세로형 1080×1920 (9:16)
 * 핵심 씬 3~5개를 60초 이내로 연결
 *
 * Props:
 * - scenes: 씬 배열 [{image, narration, subtitle, duration}]
 * - audioUrl: TTS 오디오 (선택)
 * - channelName: 채널명 (상단)
 * - ctaText: CTA 문구 (마지막)
 */

interface ShortScene {
  image: string;
  subtitle: string;
  durationInFrames: number;
}

interface ShortsProps {
  scenes: ShortScene[];
  audioUrl?: string;
  channelName?: string;
  ctaText?: string;
}

const SubtitleOverlay: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 5], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        bottom: 150,
        left: 40,
        right: 40,
        textAlign: "center",
        opacity,
      }}
    >
      <div
        style={{
          fontSize: 48,
          fontWeight: 800,
          color: "#FFFFFF",
          textShadow: "3px 3px 6px rgba(0,0,0,0.9), -1px -1px 3px rgba(0,0,0,0.9)",
          lineHeight: 1.4,
          wordBreak: "keep-all",
          fontFamily: "'Pretendard', 'Noto Sans KR', sans-serif",
          padding: "8px 16px",
          backgroundColor: "rgba(0,0,0,0.4)",
          borderRadius: 8,
          display: "inline-block",
        }}
      >
        {text}
      </div>
    </div>
  );
};

const SceneSlide: React.FC<{
  image: string;
  subtitle: string;
}> = ({ image, subtitle }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // 줌 인 애니메이션
  const scale = interpolate(frame, [0, fps * 3], [1, 1.08], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill>
      <Img
        src={image}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `scale(${scale})`,
        }}
      />
      {subtitle && <SubtitleOverlay text={subtitle} />}
    </AbsoluteFill>
  );
};

export const ShortsComposition: React.FC<ShortsProps> = ({
  scenes,
  audioUrl,
  channelName = "",
  ctaText = "전체 영상은 채널에서!",
}) => {
  const { fps } = useVideoConfig();
  let currentFrame = 0;

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      {/* 씬별 시퀀스 */}
      {scenes.map((scene, i) => {
        const from = currentFrame;
        currentFrame += scene.durationInFrames;

        return (
          <Sequence key={i} from={from} durationInFrames={scene.durationInFrames}>
            <SceneSlide image={scene.image} subtitle={scene.subtitle} />
          </Sequence>
        );
      })}

      {/* 채널명 (상단 고정) */}
      {channelName && (
        <div
          style={{
            position: "absolute",
            top: 60,
            left: 0,
            right: 0,
            textAlign: "center",
            fontSize: 28,
            fontWeight: 600,
            color: "#FFFFFF",
            textShadow: "2px 2px 4px rgba(0,0,0,0.8)",
            fontFamily: "'Pretendard', 'Noto Sans KR', sans-serif",
            opacity: 0.8,
          }}
        >
          @{channelName}
        </div>
      )}

      {/* 오디오 */}
      {audioUrl && <Audio src={audioUrl} />}
    </AbsoluteFill>
  );
};
