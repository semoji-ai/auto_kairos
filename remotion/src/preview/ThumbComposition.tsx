/**
 * ThumbComposition — 스토리보드 썸네일용 씬 렌더러
 *
 * SingleScenePlayer와 동일하지만 MapSceneRenderer 제외 (maplibre-gl 번들 회피).
 * 맵 씬은 prerenderedBg 이미지 또는 플레이스홀더를 표시.
 */
import React from "react";
import { AbsoluteFill, Img } from "remotion";
import { CreativeScene } from "../simple/CreativeScene";
import { MapSceneRenderer } from "../map/MapSceneRenderer";
import { DesignPresetProvider, useDesignPreset } from "../design";
import { buildFontFamily } from "../design/fonts";
import type { SceneEntry, SceneManifest } from "../types/manifest";

interface Props {
  scene: SceneEntry;
  meta: SceneManifest["meta"];
}

const resolveUrl = (path: string): string => {
  if (!path) return "";
  if (path.startsWith("http://") || path.startsWith("https://") || path.startsWith("/")) return path;
  return "/" + path;
};

/* ── 이미지 배경 ── */
const ImageBg: React.FC<{ src: string; opacity: number }> = ({ src, opacity }) => (
  <AbsoluteFill style={{ zIndex: 0, overflow: "hidden" }}>
    <Img src={resolveUrl(src)} style={{ width: "100%", height: "100%", objectFit: "cover", opacity }} />
  </AbsoluteFill>
);

/* ── Side 이미지 레이아웃 ── */
const SideLayout: React.FC<{
  src: string; placement: "left" | "right"; opacity: number; children: React.ReactNode;
}> = ({ src, placement, opacity, children }) => {
  const isLeft = placement === "left";
  return (
    <AbsoluteFill style={{ display: "flex", flexDirection: isLeft ? "row" : "row-reverse" }}>
      <div style={{
        flex: "0 0 40%", display: "flex", alignItems: "center",
        justifyContent: "center", padding: "40px 24px", position: "relative",
      }}>
        <Img src={resolveUrl(src)} style={{
          maxWidth: "100%", maxHeight: "80%", objectFit: "contain",
          opacity, borderRadius: 16, filter: "drop-shadow(0 4px 24px rgba(0,0,0,0.5))",
        }} />
      </div>
      <div style={{ flex: 1, position: "relative" }}>{children}</div>
    </AbsoluteFill>
  );
};

/* ── Center 이미지 레이아웃 ── */
const CenterLayout: React.FC<{
  src: string; opacity: number; children: React.ReactNode;
}> = ({ src, opacity, children }) => (
  <AbsoluteFill style={{ display: "flex", flexDirection: "column" }}>
    <div style={{
      flex: "0 0 45%", display: "flex", alignItems: "center",
      justifyContent: "center", padding: "16px 40px", position: "relative",
    }}>
      <Img src={resolveUrl(src)} style={{
        maxWidth: "70%", maxHeight: "100%", objectFit: "contain",
        opacity, borderRadius: 16, filter: "drop-shadow(0 8px 32px rgba(0,0,0,0.6))",
      }} />
    </div>
    <div style={{ flex: 1, position: "relative" }}>{children}</div>
  </AbsoluteFill>
);

/* ── 맵 씬 플레이스홀더 ── */
const MapPlaceholder: React.FC<{ data: any; bg?: string }> = ({ data, bg }) => (
  <AbsoluteFill style={{
    backgroundColor: "#1a1a2e",
    display: "flex", flexDirection: "column",
    alignItems: "center", justifyContent: "center",
    position: "relative", overflow: "hidden",
  }}>
    {bg && <Img src={resolveUrl(bg)} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", opacity: 0.6 }} />}
    <div style={{ position: "relative", zIndex: 1, textAlign: "center", color: "#fff" }}>
      <div style={{ fontSize: 48, marginBottom: 16 }}>🗺</div>
      <div style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>{data?.title || "Map Scene"}</div>
      <div style={{ fontSize: 18, opacity: 0.6 }}>{data?.mapType || ""} · {data?.mapStyle || ""}</div>
    </div>
  </AbsoluteFill>
);

/** v5 플랫 스키마 → visualization 블록 조립 (v4 호환) */
const resolveVisualization = (scene: any): any => {
  // v4: scene.visualization이 이미 있으면 그대로
  if (scene.visualization && (scene.visualization.items || scene.visualization.creative)) {
    return scene.visualization;
  }
  // v5 플랫: 최상위 필드에서 visualization 조립
  const viz: any = {};
  for (const k of ["layout", "headline", "items", "values", "unit", "source",
                     "icons", "flags", "chartConfig", "title"]) {
    if (scene[k] != null) viz[k] = scene[k];
  }
  if (scene.mood || scene.motion) {
    viz.mood = scene.mood;
    viz.motionPreset = scene.motion;
  }
  // sceneType/motionPreset from manifest
  if (scene.sceneType) viz.layout = scene.sceneType;
  if (scene.motionPreset) viz.motionPreset = scene.motionPreset;
  if (scene.mood) viz.mood = scene.mood;
  return Object.keys(viz).length > 0 ? viz : (scene.visualization || {});
};

/* ── 메인 컴포넌트 ── */
const ThumbInner: React.FC<Props> = ({ scene, meta }) => {
  const preset = useDesignPreset();
  const fontFamily = buildFontFamily(preset);

  const fps = meta?.fps || 30;
  const vizData = resolveVisualization(scene);

  // 디버그
  if (typeof console !== "undefined") {
    console.log(`[Thumb #${scene.sceneNumber}]`, {
      accent: preset.colors.accent,
      artStyle: preset.artStyle,
      metaArtStyle: meta?.artStyle,
    });
  }

  const defaultBg = preset.defaultBackground;

  // ── 맵 씬 ──
  if (scene.mapScene) {
    const dur = Math.ceil((scene.audioDurationSec || 5) * fps);
    return (
      <MapSceneRenderer
        data={scene.mapScene}
        durationInFrames={dur}
        fps={fps}
      />
    );
  }

  // ── 일반 씬 ──
  const hasImage = !!(scene.imagePath || scene.vizBackgroundPath || defaultBg);
  const placement = scene.imageAsset?.placement ?? "background";
  const defaultOpacity = (placement === "background") ? 0.35 : 1.0;
  const imgOpacity = scene.imageAsset?.opacity ?? defaultOpacity;
  const imgSrc = scene.vizBackgroundPath || scene.imagePath || defaultBg || "";
  const isFullscreen = hasImage && placement === "fullscreen";
  const isCenter = hasImage && placement === "center";
  const isSide = hasImage && (placement === "left" || placement === "right");

  if (isFullscreen) {
    return (
      <AbsoluteFill style={{ backgroundColor: preset.colors.bg, fontFamily }}>
        <ImageBg src={imgSrc} opacity={imgOpacity >= 0.8 ? imgOpacity : 0.9} />
        <CreativeScene
          data={vizData}
          subtitles={scene.subtitles}
          fps={fps}
          hasImageBackground={true}
          imageAssetPlacement="fullscreen"
        />
      </AbsoluteFill>
    );
  }

  if (isCenter) {
    return (
      <AbsoluteFill style={{ backgroundColor: preset.colors.bg, fontFamily }}>
        <CenterLayout src={imgSrc} opacity={imgOpacity}>
          <CreativeScene
            data={vizData}
            subtitles={scene.subtitles}
            fps={fps}
            hasImageBackground={false}
            imageAssetPlacement="center"
          />
        </CenterLayout>
      </AbsoluteFill>
    );
  }

  if (isSide) {
    return (
      <AbsoluteFill style={{ backgroundColor: preset.colors.bg, fontFamily }}>
        <SideLayout src={imgSrc} placement={placement as "left" | "right"} opacity={imgOpacity}>
          <CreativeScene
            data={vizData}
            subtitles={scene.subtitles}
            fps={fps}
            hasImageBackground={false}
            imageAssetPlacement={placement}
          />
        </SideLayout>
      </AbsoluteFill>
    );
  }

  return (
    <AbsoluteFill style={{ backgroundColor: preset.colors.bg, fontFamily }}>
      {hasImage && <ImageBg src={imgSrc} opacity={imgOpacity} />}
      <CreativeScene
        data={scene.visualization}
        subtitles={scene.subtitles}
        fps={fps}
        hasImageBackground={hasImage}
        imageAssetPlacement={placement}
      />
    </AbsoluteFill>
  );
};

export const ThumbComposition: React.FC<Props> = ({ scene, meta }) => (
  <DesignPresetProvider meta={meta}>
    <ThumbInner scene={scene} meta={meta} />
  </DesignPresetProvider>
);
