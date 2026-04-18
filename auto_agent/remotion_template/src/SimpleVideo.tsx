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
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
} from "remotion";
import { CanvasScene } from "./simple/CanvasScene";
import { MapSceneRenderer } from "./map/MapSceneRenderer";
import { SceneRendererInner, TextureOverlay } from "./components/SceneRenderer";
import { SubtitleOverlay } from "./components/SubtitleOverlay";
import { DesignPresetProvider, useDesignPreset } from "./design";
import { buildFontFamily } from "./design/fonts";
import type { SceneManifest, SubtitleConfig } from "./types/manifest";

/** staticFile 대체: 절대 URL이면 그대로, 상대경로면 staticFile() 사용 */
const resolveAsset = (path: string): string =>
  path.startsWith("http://") || path.startsWith("https://")
    ? path
    : staticFile(path);

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
  const fontFamily = buildFontFamily(preset);
  const { fps } = useVideoConfig();
  const frame = useCurrentFrame();

  let offset = 0;
  const timing = manifest.scenes.map((scene) => {
    // scene timing authority: audioDurationSec를 프레임으로만 올림하여 사용
    const minFrames = scene.audioDurationSec > 0 ? 1 : 90;
    const dur = Math.max(Math.ceil(scene.audioDurationSec * fps), minFrames);
    const from = offset;
    offset += dur;
    return { scene, from, dur };
  });

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
      {timing.map(({ scene, from, dur }) => (
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
            {/* 자막 — Sequence 안에서 SubtitleOverlay 사용 (subtitleConfig 반영) */}
            {subtitleConfig.visible !== false && scene.subtitles?.length > 0 && (
              <SubtitleOverlay subtitles={scene.subtitles} fps={fps} config={subtitleConfig} />
            )}
            {/* topLayer 텍스처 — 자막 위에 렌더 (preset.texture.topLayer:true 시) */}
            {(() => {
              const tc = (preset as any).texture as { src: string; blendMode?: string; opacity?: number; topLayer?: boolean } | undefined;
              return tc?.topLayer ? <TextureOverlay src={tc.src} blendMode={tc.blendMode} opacity={tc.opacity} /> : null;
            })()}
            {scene.audioPath ? (
              <Audio src={resolveAsset(scene.audioPath)} />
            ) : null}
          </AbsoluteFill>
        </Sequence>
      ))}

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

