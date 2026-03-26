/**
 * SimpleVideo — 키네틱 타이포그래피 기반 미니멀 컴포지션
 *
 * 2컬러 시스템 (text + accent) + Pretendard 폰트
 * VizShell / DesignToken 없이 순수 Remotion 프리미티브만 사용
 */
import React, { useEffect } from "react";
import {
  AbsoluteFill,
  Sequence,
  Audio,
  Img,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
} from "remotion";

/** staticFile 대체: 절대 URL이면 그대로, 상대경로면 staticFile() 사용 */
const resolveAsset = (path: string): string =>
  path.startsWith("http://") || path.startsWith("https://")
    ? path
    : staticFile(path);
import { CreativeScene } from "./simple/CreativeScene";
import { CanvasScene } from "./simple/CanvasScene";
import { MapSceneRenderer } from "./map/MapSceneRenderer";
import { SceneRendererInner } from "./components/SceneRenderer";
import { DesignPresetProvider, useDesignPreset } from "./design";
import { usePresetFonts, buildFontFamily } from "./design/fonts";
import type { PresetColors } from "./design/types";
import type { SceneManifest, SubtitleConfig } from "./types/manifest";

/* ---------- Main Composition ---------- */
interface Props {
  manifest: SceneManifest;
  subtitleConfig: SubtitleConfig;
}

export const SimpleVideo: React.FC<Props> = ({ manifest, subtitleConfig }) => {
  return (
    <DesignPresetProvider meta={manifest.meta}>
      <SimpleVideoInner manifest={manifest} subtitleConfig={subtitleConfig} />
    </DesignPresetProvider>
  );
};

const SimpleVideoInner: React.FC<Props> = ({ manifest, subtitleConfig }) => {
  const preset = useDesignPreset();
  usePresetFonts();
  const fontFamily = buildFontFamily(preset);
  const { fps } = useVideoConfig();
  const frame = useCurrentFrame();

  let offset = 0;
  const timing = manifest.scenes.map((scene) => {
    // MP3 인코딩 패딩 + ffprobe 반올림 오차 보상: 2프레임 여유
    // TTS 있으면 TTS 길이 + 5프레임 여유, 없으면 최소 3초 (90프레임)
    const minFrames = scene.audioDurationSec > 0 ? 1 : 90;
    const dur = Math.max(Math.ceil(scene.audioDurationSec * fps) + 7, minFrames);
    const from = offset;
    offset += dur;
    return { scene, from, dur };
  });

  const sub = findSubtitle(timing, frame, fps);

  // ── postMessage 브릿지: 현재 씬 번호를 부모(대시보드)에 전달 ──
  useEffect(() => {
    if (typeof window === "undefined" || window === window.parent) return;
    const current = timing.find(
      (t) => frame >= t.from && frame < t.from + t.dur
    );
    if (current) {
      try {
        window.parent.postMessage(
          { type: "remotion-scene", sceneNumber: current.scene.sceneNumber },
          "*"
        );
      } catch (_) {
        /* cross-origin 차단 시 무시 */
      }
    }
  }, [frame, timing]);

  return (
    <AbsoluteFill style={{ backgroundColor: preset.colors.bg, fontFamily }}>
      {timing.map(({ scene, from, dur }) => {
        const defaultBg = preset.defaultBackground;
        const hasImage = !!(scene.imagePath || scene.vizBackgroundPath || defaultBg);

        return (
          <Sequence
            key={scene.sceneNumber}
            name={`S${scene.sceneNumber} - ${scene.visualization?.creative?.headline?.replace(/\{\{|\}\}/g, '').replace(/\n/g, ' ').slice(0, 30) || scene.visualization?.title || `Scene ${scene.sceneNumber}`}`}
            from={from}
            durationInFrames={dur}
            layout="none"
          >
            <AbsoluteFill>
              {(scene as any)._canvas?.layers ? (
                <CanvasScene
                  canvas={(scene as any)._canvas}
                  durationInFrames={dur}
                />
              ) : scene.mapScene ? (
                <FadeWrap duration={dur} fade={10}>
                  <MapSceneRenderer
                    data={scene.mapScene}
                    durationInFrames={dur}
                    fps={fps}
                  />
                </FadeWrap>
              ) : (
                <FadeWrap duration={dur} fade={10}>
                  <SceneRendererInner scene={scene} fps={fps} />
                </FadeWrap>
              )}
              {scene.audioPath ? (
                <Audio src={resolveAsset(scene.audioPath)} />
              ) : null}
            </AbsoluteFill>
          </Sequence>
        );
      })}

      {/* 자막 바 */}
      {sub && subtitleConfig.visible !== false && (
        <SubtitleBar text={sub} theme={preset.colors} />
      )}

      {/* BGM */}
      {manifest.bgm && manifest.bgm.path && (
        <Audio
          src={resolveAsset(manifest.bgm.path)}
          volume={manifest.bgm.volume ?? 0.15}
          loop
        />
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
        src={resolveAsset(src)}
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
        src={resolveAsset(src)}
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

/* ---------- Center Image Layout ---------- */
const CenterImageLayout: React.FC<{
  src: string;
  opacity: number;
  duration: number;
  children: React.ReactNode;
}> = ({ src, opacity, duration, children }) => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {/* 상단: 콘텐츠 */}
      <div style={{ flex: "0 0 35%", width: "100%", position: "relative" }}>
        {children}
      </div>
      {/* 중앙: 이미지 */}
      <div
        style={{
          flex: "0 0 45%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "16px 40px",
          opacity: fadeIn,
        }}
      >
        <Img
          src={resolveAsset(src)}
          style={{
            maxWidth: "70%",
            maxHeight: "100%",
            objectFit: "contain",
            opacity,
            borderRadius: 16,
            filter: "drop-shadow(0 8px 32px rgba(0,0,0,0.6))",
          }}
        />
      </div>
      {/* 하단 여백 (자막 영역) */}
      <div style={{ flex: "0 0 20%" }} />
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
          fontFamily: "inherit",
          textAlign: "center",
          opacity,
          color: "#FFFFFF",
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
const SubtitleBar: React.FC<{ text: string; theme: PresetColors }> = ({ text, theme }) => {
  const isDark = theme.bg === "#0A0A0A";
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
            backgroundColor: theme.accent,
            borderRadius: "4px 0 0 4px",
            flexShrink: 0,
          }}
        />
        {/* 텍스트 영역 */}
        <div
          style={{
            flex: 1,
            backgroundColor: isDark ? "rgba(255,255,255,0.8)" : "rgba(255,255,255,0.95)",
            padding: "14px 28px",
            borderRadius: "0 8px 8px 0",
            textAlign: "center",
            boxShadow: isDark ? undefined : "0 2px 8px rgba(0,0,0,0.06)",
          }}
        >
          <span
            style={{
              fontSize: 36,
              fontWeight: 600,
              color: isDark ? "#111111" : "#1A1A2E",
              fontFamily: "inherit",
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

function findSubtitle(
  timing: Array<{ scene: any; from: number; dur: number }>,
  frame: number,
  fps: number,
): string | null {
  for (const { scene, from, dur } of timing) {
    if (frame >= from && frame < from + dur) {
      const t = (frame - from) / fps;
      const subs = scene.subtitles ?? [];
      for (let i = 0; i < subs.length; i++) {
        const s = subs[i];
        // 마지막 자막은 씬 끝까지 유지
        const isLast = i === subs.length - 1;
        if (t >= s.startSec && (isLast || t < s.endSec)) return s.text;
      }
    }
  }
  return null;
}
