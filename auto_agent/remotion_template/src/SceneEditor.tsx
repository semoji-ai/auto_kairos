import React from "react";
import { AbsoluteFill, Audio, Img, useCurrentFrame, interpolate } from "remotion";
import { staticFile } from "remotion";
import { DesignPresetProvider, useDesignPreset } from "./design";
import { CreativeScene } from "./simple/CreativeScene";
import { SubtitleOverlay } from "./components/SubtitleOverlay";
import type { SceneManifest, SubtitleConfig } from "./types/manifest";

const resolveAsset = (path: string): string =>
  path.startsWith("http://") || path.startsWith("https://")
    ? path
    : staticFile(path);

interface SceneOverride {
  headline?: string;
  layout?: string;
  reveal?: string;
  emphasis?: string;
  mood?: string;
  title?: string;
  items?: string;      // 쉼표 구분 문자열
  values?: string;     // 쉼표 구분 숫자
  unit?: string;
  source?: string;
  contentX?: number;
  contentY?: number;
}

interface Props {
  manifest: SceneManifest;
  sceneNumber: number;
  subtitleConfig: SubtitleConfig;
  override?: SceneOverride;
}

/** override props를 scene 데이터에 병합 */
function applyOverride(scene: any, override?: SceneOverride): any {
  if (!override) return scene;

  // 모든 필드가 기본값이면 오버라이드 없음
  const hasAnyOverride = (
    (override.headline && override.headline !== "") ||
    (override.layout && override.layout !== "") ||
    (override.title && override.title !== "") ||
    (override.items && override.items !== "") ||
    (override.values && override.values !== "") ||
    (override.unit && override.unit !== "") ||
    (override.source && override.source !== "") ||
    (override.contentX && override.contentX !== 0) ||
    (override.contentY && override.contentY !== 0)
  );
  if (!hasAnyOverride) return scene;

  const merged = JSON.parse(JSON.stringify(scene)); // deep clone
  const viz = merged.visualization || {};
  const creative = viz.creative || {};

  // creative 필드 오버라이드 (빈 문자열이면 skip)
  if (override.headline && override.headline !== "") creative.headline = override.headline;
  if (override.layout && override.layout !== "") creative.layout = override.layout;
  // reveal/emphasis/mood는 기본값과 다를 때만 적용
  const origCreative = (scene.visualization || {}).creative || {};
  if (override.reveal && override.reveal !== origCreative.reveal) creative.reveal = override.reveal;
  if (override.emphasis && override.emphasis !== origCreative.emphasis) creative.emphasis = override.emphasis;
  if (override.mood && override.mood !== origCreative.mood) creative.mood = override.mood;

  // visualization 필드 오버라이드 (빈 문자열이면 skip)
  if (override.title && override.title !== "") viz.title = override.title;
  if (override.unit && override.unit !== "") viz.unit = override.unit;
  if (override.source && override.source !== "") viz.source = override.source;

  // items/values: 쉼표 구분 문자열 → 배열 변환 (빈 문자열이면 skip)
  if (override.items && override.items !== "") {
    viz.items = override.items.split(",").map((s: string) => s.trim());
  }
  if (override.values && override.values !== "") {
    viz.values = override.values.split(",").map((s: string) => parseFloat(s.trim())).filter((n: number) => !isNaN(n));
  }

  viz.creative = creative;
  merged.visualization = viz;
  return merged;
}

export const SceneEditor: React.FC<Props> = ({ manifest, sceneNumber, subtitleConfig, override }) => {
  const scene = manifest.scenes.find((s) => s.sceneNumber === sceneNumber);
  const fps = manifest.meta.fps || 30;

  if (!scene) {
    return (
      <AbsoluteFill style={{ backgroundColor: "#111", color: "#666", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 24 }}>
        Scene {sceneNumber} not found in manifest
      </AbsoluteFill>
    );
  }

  const mergedScene = applyOverride(scene, override);
  const dur = Math.max(Math.ceil(mergedScene.audioDurationSec * fps) + 2, 1);

  return (
    <DesignPresetProvider meta={manifest.meta}>
      <SceneEditorInner scene={mergedScene} fps={fps} dur={dur} subtitleConfig={subtitleConfig} override={override} />
    </DesignPresetProvider>
  );
};

const SceneEditorInner: React.FC<{
  scene: any;
  fps: number;
  dur: number;
  subtitleConfig: SubtitleConfig;
  override?: SceneOverride;
}> = ({ scene, fps, dur, subtitleConfig, override }) => {
  const preset = useDesignPreset();
  const hasImage = !!(scene.imagePath || scene.vizBackgroundPath || preset.defaultBackground);

  const placement = scene.imageAsset?.placement ?? "background";
  const defaultOpacity = placement === "background" ? 0.35 : 1.0;
  const imgOpacity = scene.imageAsset?.opacity ?? defaultOpacity;
  const imgSrc = scene.vizBackgroundPath || scene.imagePath || preset.defaultBackground;
  const isSidePlacement = hasImage && (placement === "left" || placement === "right");
  const isFullscreen = hasImage && placement === "fullscreen";
  const isCenter = hasImage && placement === "center";

  // 위치 오프셋
  const offsetX = override?.contentX ?? 0;
  const offsetY = override?.contentY ?? 0;
  const contentTransform = (offsetX !== 0 || offsetY !== 0)
    ? `translate(${offsetX}px, ${offsetY}px)`
    : undefined;

  const creativeScene = (hasImageBg: boolean, assetPlacement: string) => (
    <div style={{ width: "100%", height: "100%", transform: contentTransform }}>
      <CreativeScene
        data={scene.visualization}
        subtitles={scene.subtitles}
        fps={fps}
        hasImageBackground={hasImageBg}
        imageAssetPlacement={assetPlacement as any}
      />
    </div>
  );

  return (
    <AbsoluteFill style={{ backgroundColor: preset.colors.bg }}>
      {scene.mapScene ? (
        <AbsoluteFill style={{ backgroundColor: "#111", color: "#666", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 24 }}>
          Map scenes — use SimpleVideo
        </AbsoluteFill>
      ) : (
        <>
          {isFullscreen && imgSrc ? (
            <>
              <ImageBackground src={imgSrc} duration={dur} kenBurns={scene.kenBurns} opacity={imgOpacity >= 0.8 ? imgOpacity : 0.9} />
              <FadeWrap duration={dur} fade={10}>
                {creativeScene(true, "fullscreen")}
              </FadeWrap>
            </>
          ) : isCenter && imgSrc ? (
            <CenterImageLayout src={imgSrc} opacity={imgOpacity} duration={dur}>
              <FadeWrap duration={dur} fade={10}>
                {creativeScene(false, "center")}
              </FadeWrap>
            </CenterImageLayout>
          ) : isSidePlacement && imgSrc ? (
            <SideImageLayout src={imgSrc} placement={placement as "left" | "right"} opacity={imgOpacity} duration={dur}>
              <FadeWrap duration={dur} fade={10}>
                {creativeScene(false, placement)}
              </FadeWrap>
            </SideImageLayout>
          ) : (
            <>
              {hasImage && imgSrc && (
                <ImageBackground src={imgSrc} duration={dur} kenBurns={scene.kenBurns} opacity={imgOpacity} />
              )}
              <FadeWrap duration={dur} fade={10}>
                {creativeScene(!!imgSrc, placement)}
              </FadeWrap>
            </>
          )}
        </>
      )}

      {subtitleConfig.visible !== false && scene.subtitles?.length > 0 && (
        <SubtitleOverlay subtitles={scene.subtitles} fps={fps} config={subtitleConfig} />
      )}

      {scene.audioPath ? <Audio src={resolveAsset(scene.audioPath)} /> : null}
    </AbsoluteFill>
  );
};

/* ---------- ImageBackground ---------- */
const ImageBackground: React.FC<{
  src: string; duration: number; opacity?: number;
  kenBurns?: { enabled: boolean; zoomFactor: number; zoomDirection?: "in" | "out"; panX?: number; panY?: number };
}> = ({ src, duration, opacity = 0.35, kenBurns }) => {
  const frame = useCurrentFrame();
  const progress = duration > 0 ? frame / duration : 0;
  const zoomEnabled = kenBurns?.enabled !== false;
  const zoomFactor = kenBurns?.zoomFactor ?? 1.15;
  const zoomIn = kenBurns?.zoomDirection !== "out";
  const scale = zoomEnabled
    ? interpolate(progress, [0, 1], zoomIn ? [1, zoomFactor] : [zoomFactor, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
    : 1;
  const panX = zoomEnabled ? interpolate(progress, [0, 1], [0, kenBurns?.panX ?? 2], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 0;
  const panY = zoomEnabled ? interpolate(progress, [0, 1], [0, kenBurns?.panY ?? -1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 0;
  return (
    <AbsoluteFill style={{ zIndex: 0, overflow: "hidden" }}>
      <Img src={resolveAsset(src)} style={{
        width: "100%", height: "100%", objectFit: "cover",
        transform: `scale(${scale}) translate(${panX}%, ${panY}%)`, opacity,
      }} />
    </AbsoluteFill>
  );
};

/* ---------- FadeWrap ---------- */
const FadeWrap: React.FC<{ duration: number; fade: number; children: React.ReactNode }> = ({ duration, fade, children }) => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, fade], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const fadeOut = interpolate(frame, [duration - fade, duration], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return <AbsoluteFill style={{ opacity: Math.min(fadeIn, fadeOut) }}>{children}</AbsoluteFill>;
};

/* ---------- SideImageLayout ---------- */
const SideImageLayout: React.FC<{
  src: string; placement: "left" | "right"; opacity: number; duration: number; children: React.ReactNode;
}> = ({ src, placement, opacity, duration, children }) => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 15], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const isRight = placement === "right";
  const imageEl = (
    <div style={{ flex: "0 0 40%", display: "flex", alignItems: "center", justifyContent: isRight ? "flex-start" : "flex-end", padding: "40px 24px", opacity: fadeIn }}>
      <Img src={resolveAsset(src)} style={{ maxWidth: "100%", maxHeight: "80%", objectFit: "contain", opacity, borderRadius: 16, filter: "drop-shadow(0 4px 24px rgba(0,0,0,0.5))" }} />
    </div>
  );
  return (
    <AbsoluteFill style={{ flexDirection: "row", display: "flex" }}>
      {isRight ? <>{children}{imageEl}</> : <>{imageEl}{children}</>}
    </AbsoluteFill>
  );
};

/* ---------- CenterImageLayout ---------- */
const CenterImageLayout: React.FC<{
  src: string; opacity: number; duration: number; children: React.ReactNode;
}> = ({ src, opacity, duration, children }) => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 15], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ zIndex: 0, display: "flex", alignItems: "center", justifyContent: "center", opacity: fadeIn }}>
        <Img src={resolveAsset(src)} style={{ maxWidth: "60%", maxHeight: "60%", objectFit: "contain", opacity, borderRadius: 16, filter: "drop-shadow(0 8px 32px rgba(0,0,0,0.4))" }} />
      </AbsoluteFill>
      <AbsoluteFill style={{ zIndex: 1 }}>{children}</AbsoluteFill>
    </AbsoluteFill>
  );
};
