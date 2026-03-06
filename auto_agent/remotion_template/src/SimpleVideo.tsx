/**
 * SimpleVideo — 키네틱 타이포그래피 기반 미니멀 컴포지션
 *
 * 2컬러 시스템 (text + accent) + Pretendard 폰트
 * VizShell / DesignToken 없이 순수 Remotion 프리미티브만 사용
 */
import React, { useState, useEffect } from "react";
import {
  AbsoluteFill,
  Sequence,
  Audio,
  Img,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Easing,
  delayRender,
  continueRender,
} from "remotion";
import { SimpleScene } from "./simple/SimpleScene";
import { MapSceneRenderer } from "./map/MapSceneRenderer";
import type { SceneManifest, SubtitleConfig } from "./types/manifest";

const FONT = "'Pretendard', sans-serif";

const C = {
  bg: "#0A0A0A",
  text: "#F5F5F5",
  textMuted: "rgba(245,245,245,0.5)",
  accent: "#F59E0B",
} as const;

/* ---------- Font Loading ---------- */
const useFonts = () => {
  const [handle] = useState(() => delayRender("Loading Pretendard fonts"));
  useEffect(() => {
    const load = async () => {
      const defs = [
        { file: "fonts/Pretendard-Regular.otf", weight: "400" },
        { file: "fonts/Pretendard-Bold.otf", weight: "700" },
      ];
      await Promise.all(
        defs.map(async (d) => {
          const face = new FontFace(
            "Pretendard",
            `url('${staticFile(d.file)}')`,
            { weight: d.weight, style: "normal" },
          );
          const loaded = await face.load();
          document.fonts.add(loaded);
        }),
      );
      continueRender(handle);
    };
    load().catch(() => continueRender(handle));
  }, [handle]);
};

/* ---------- Main Composition ---------- */
interface Props {
  manifest: SceneManifest;
  subtitleConfig: SubtitleConfig;
}

export const SimpleVideo: React.FC<Props> = ({ manifest, subtitleConfig }) => {
  useFonts();
  const { fps } = useVideoConfig();
  const frame = useCurrentFrame();

  let offset = 0;
  const timing = manifest.scenes.map((scene) => {
    const dur = Math.max(Math.ceil(scene.audioDurationSec * fps), 1);
    const from = offset;
    offset += dur;
    return { scene, from, dur };
  });

  const sub = findSubtitle(timing, frame, fps);

  return (
    <AbsoluteFill style={{ backgroundColor: C.bg, fontFamily: FONT }}>
      {timing.map(({ scene, from, dur }) => {
        const hasImage = !!(scene.imagePath || scene.vizBackgroundPath);

        return (
          <Sequence
            key={scene.sceneNumber}
            from={from}
            durationInFrames={dur}
            layout="none"
          >
            <AbsoluteFill>
              {scene.mapScene ? (
                /* === 맵 씬: 맵만 전체 표시 (마커 포함) === */
                <FadeWrap duration={dur} fade={10}>
                  <MapSceneRenderer
                    data={scene.mapScene}
                    durationInFrames={dur}
                    fps={fps}
                  />
                </FadeWrap>
              ) : (
                /* === 일반 씬: 이미지 배경/에셋 + SimpleScene === */
                (() => {
                  const placement = scene.imageAsset?.placement ?? "background";
                  const imgOpacity = scene.imageAsset?.opacity ?? 0.4;
                  const imgSrc = scene.vizBackgroundPath || scene.imagePath;
                  const isSidePlacement = hasImage && (placement === "left" || placement === "right");

                  if (isSidePlacement) {
                    // left/right: flex row로 텍스트와 이미지를 나란히 배치
                    return (
                      <SideImageLayout
                        src={imgSrc}
                        placement={placement as "left" | "right"}
                        opacity={imgOpacity}
                        duration={dur}
                      >
                        <FadeWrap duration={dur} fade={10}>
                          <SimpleScene
                            data={scene.visualization}
                            sceneNumber={scene.sceneNumber}
                            durationInFrames={dur}
                            subtitles={scene.subtitles}
                            hasImageBackground={false}
                            imageAssetPlacement={placement}
                          />
                        </FadeWrap>
                      </SideImageLayout>
                    );
                  }

                  return (
                    <>
                      {hasImage && (
                        <ImageBackground
                          src={imgSrc}
                          duration={dur}
                          kenBurns={scene.kenBurns}
                          opacity={imgOpacity}
                        />
                      )}
                      <FadeWrap duration={dur} fade={10}>
                        <SimpleScene
                          data={scene.visualization}
                          sceneNumber={scene.sceneNumber}
                          durationInFrames={dur}
                          subtitles={scene.subtitles}
                          hasImageBackground={hasImage}
                          imageAssetPlacement={placement}
                        />
                      </FadeWrap>
                    </>
                  );
                })()
              )}
              {scene.audioPath ? (
                <Audio src={staticFile(scene.audioPath)} />
              ) : null}
            </AbsoluteFill>
          </Sequence>
        );
      })}

      {/* 자막 바 */}
      {sub && subtitleConfig.visible !== false && (
        <SubtitleBar text={sub} />
      )}
    </AbsoluteFill>
  );
};

/* ---------- Image Background with Ken Burns ---------- */
const ImageBackground: React.FC<{
  src: string;
  duration: number;
  opacity?: number;
  kenBurns?: { enabled: boolean; zoomFactor: number; zoomDirection?: "in" | "out"; panX?: number; panY?: number };
}> = ({ src, duration, opacity = 0.35, kenBurns }) => {
  const frame = useCurrentFrame();
  const progress = duration > 0 ? frame / duration : 0;

  const zoomEnabled = kenBurns?.enabled !== false;
  const zoomFactor = kenBurns?.zoomFactor ?? 1.15;
  const zoomIn = kenBurns?.zoomDirection !== "out";

  const scale = zoomEnabled
    ? interpolate(progress, [0, 1], zoomIn ? [1, zoomFactor] : [zoomFactor, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 1;

  const panX = zoomEnabled ? interpolate(progress, [0, 1], [0, kenBurns?.panX ?? 2], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  }) : 0;
  const panY = zoomEnabled ? interpolate(progress, [0, 1], [0, kenBurns?.panY ?? -1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  }) : 0;

  return (
    <AbsoluteFill style={{ zIndex: 0, overflow: "hidden" }}>
      <Img
        src={staticFile(src)}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `scale(${scale}) translate(${panX}%, ${panY}%)`,
          opacity,
        }}
      />
    </AbsoluteFill>
  );
};

/* ---------- Side Image Layout (left/right — flex row) ---------- */
const SideImageLayout: React.FC<{
  src: string;
  placement: "left" | "right";
  opacity: number;
  duration: number;
  children: React.ReactNode;
}> = ({ src, placement, opacity, duration, children }) => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const isRight = placement === "right";

  const imageEl = (
    <div
      style={{
        flex: "0 0 40%",
        display: "flex",
        alignItems: "center",
        justifyContent: isRight ? "flex-start" : "flex-end",
        padding: "40px 24px",
        opacity: fadeIn,
      }}
    >
      <Img
        src={staticFile(src)}
        style={{
          maxWidth: "100%",
          maxHeight: "80%",
          objectFit: "contain",
          opacity,
          borderRadius: 16,
          filter: "drop-shadow(0 4px 24px rgba(0,0,0,0.5))",
        }}
      />
    </div>
  );

  const contentEl = (
    <div style={{ flex: "0 0 60%", position: "relative", height: "100%" }}>
      {children}
    </div>
  );

  return (
    <AbsoluteFill
      style={{
        display: "flex",
        flexDirection: isRight ? "row" : "row-reverse",
        alignItems: "stretch",
      }}
    >
      {contentEl}
      {imageEl}
    </AbsoluteFill>
  );
};

/* ---------- Map Title ---------- */
const MapTitle: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 15, 20], [0, 0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  if (!text) return null;
  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-start",
        alignItems: "center",
        pointerEvents: "none",
        zIndex: 10,
      }}
    >
      <div
        style={{
          marginTop: 60,
          fontSize: 42,
          fontWeight: 700,
          color: C.text,
          fontFamily: FONT,
          textAlign: "center",
          opacity,
          textShadow: "0 2px 24px rgba(0,0,0,0.9)",
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};

/* ---------- helpers ---------- */
const FadeWrap: React.FC<{
  duration: number;
  fade: number;
  children: React.ReactNode;
}> = ({ duration, fade, children }) => {
  const f = useCurrentFrame();
  const opacity = interpolate(
    f,
    [0, fade, Math.max(duration - fade, fade + 1), duration],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  return <AbsoluteFill style={{ opacity }}>{children}</AbsoluteFill>;
};

/* ---------- Subtitle Bar ---------- */
const SubtitleBar: React.FC<{ text: string }> = ({ text }) => {
  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          marginBottom: 40,
          width: 990,
          display: "flex",
          alignItems: "stretch",
        }}
      >
        {/* 좌측 악센트 바 */}
        <div
          style={{
            width: 5,
            backgroundColor: C.accent,
            borderRadius: "4px 0 0 4px",
            flexShrink: 0,
          }}
        />
        {/* 텍스트 영역 */}
        <div
          style={{
            flex: 1,
            backgroundColor: "rgba(255, 255, 255, 0.8)",
            padding: "14px 28px",
            borderRadius: "0 8px 8px 0",
            textAlign: "center",
          }}
        >
          <span
            style={{
              fontSize: 36,
              fontWeight: 600,
              color: "#111111",
              fontFamily: FONT,
              lineHeight: 1.5,
              letterSpacing: "0.01em",
            }}
          >
            {text}
          </span>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// WhisperX 타임스탬프가 실제 발화보다 약간 늦게 잡힘 → 자막을 앞당김
const SUBTITLE_OFFSET_SEC = 0.3;

function findSubtitle(
  timing: Array<{ scene: any; from: number; dur: number }>,
  frame: number,
  fps: number,
): string | null {
  for (const { scene, from, dur } of timing) {
    if (frame >= from && frame < from + dur) {
      const t = (frame - from) / fps + SUBTITLE_OFFSET_SEC;
      for (const s of scene.subtitles ?? []) {
        if (t >= s.startSec && t <= s.endSec) return s.text;
      }
    }
  }
  return null;
}
