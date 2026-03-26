/**
 * SingleScenePlayer — @remotion/player용 씬 1개 렌더 컴포넌트
 *
 * 실제 SimpleVideo와 동일한 렌더링 파이프라인 사용:
 * VideoThemeProvider → CreativeScene (레이아웃/모션/스타일링 그대로)
 * 폼에서 scene 속성을 바꾸면 Player가 즉시 반영 (WYSIWYG)
 */
import React, { lazy, Suspense } from "react";
import { AbsoluteFill, Img } from "remotion";
import { CreativeScene } from "../simple/CreativeScene";
import { DesignPresetProvider, useDesignPreset } from "../design";
import { buildFontFamily } from "../design/fonts";
import type { SceneEntry, SceneManifest } from "../types/manifest";

// MapSceneRenderer를 lazy import (maplibre-gl 번들 문제 회피)
const MapSceneRenderer = lazy(() =>
  import("../map/MapSceneRenderer").then((m) => ({ default: m.MapSceneRenderer }))
);

const MapFallback = () => (
  <AbsoluteFill style={{ backgroundColor: "#1a1a2e", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: 24 }}>
    Map Loading...
  </AbsoluteFill>
);

interface Props {
  scene: SceneEntry;
  meta: SceneManifest["meta"];
}

/** URL이면 그대로, 상대경로면 그대로 */
const resolveUrl = (path: string): string => {
  if (!path) return "";
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  return path;
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

/* ── Inner 컴포넌트: DesignPresetContext에서 색상/폰트를 읽는다 ── */
/** v5 플랫 스키마 → visualization 블록 조립 */
const resolveVisualization = (scene: any): any => {
  if (scene.visualization && (scene.visualization.items || scene.visualization.creative)) {
    return scene.visualization;
  }
  const viz: any = {};
  for (const k of ["layout", "headline", "items", "values", "unit", "source",
                     "icons", "flags", "chartConfig", "title"]) {
    if (scene[k] != null) viz[k] = scene[k];
  }
  if (scene.sceneType) viz.layout = scene.sceneType;
  if (scene.motionPreset) viz.motionPreset = scene.motionPreset;
  if (scene.mood) viz.mood = scene.mood;
  return Object.keys(viz).length > 0 ? viz : (scene.visualization || {});
};

const SingleSceneInner: React.FC<Props> = ({ scene, meta }) => {
  const preset = useDesignPreset();
  const fontFamily = buildFontFamily(preset);

  const fps = meta?.fps || 30;
  const vizData = resolveVisualization(scene);
  const durationInFrames = scene.audioDurationSec
    ? Math.max(Math.ceil(scene.audioDurationSec * fps), 1)
    : 150;

  // ── 맵 씬 ──
  if (scene.mapScene) {
    return (
      <AbsoluteFill style={{ backgroundColor: preset.colors.bg, fontFamily }}>
        <Suspense fallback={<MapFallback />}>
          <MapSceneRenderer
            data={scene.mapScene}
            durationInFrames={durationInFrames}
            fps={fps}
          />
        </Suspense>
      </AbsoluteFill>
    );
  }

  // ── 일반 씬 ──
  const defaultBg = preset.defaultBackground;
  const hasImage = !!(scene.imagePath || scene.vizBackgroundPath || defaultBg);
  const placement = scene.imageAsset?.placement ?? "background";
  const defaultOpacity = (placement === "background") ? 0.35 : 1.0;
  const imgOpacity = scene.imageAsset?.opacity ?? defaultOpacity;
  const imgSrc = scene.vizBackgroundPath || scene.imagePath || defaultBg;

  const creativeEl = (
    <div style={{ width: "100%", height: "100%", position: "relative" }}>
      <CreativeScene
        data={vizData}
        subtitles={scene.subtitles || []}
        fps={fps}
        hasImageBackground={hasImage && (placement === "background" || placement === "fullscreen")}
        imageAssetPlacement={placement}
      />
    </div>
  );

  // quote_portrait: 이미지를 CreativeScene 내부에서 처리
  const vizLayout = vizData?.layout || scene.visualization?.creative?.layout || "";
  if (vizLayout === "quote_portrait") {
    const qpViz = { ...vizData, imageSrc: hasImage ? resolveUrl(imgSrc) : "", imageAssetPlacement: placement };
    return (
      <AbsoluteFill style={{ backgroundColor: preset.colors.bg, fontFamily }}>
        {defaultBg && <ImageBg src={defaultBg} opacity={0.15} />}
        <CreativeScene
          data={qpViz}
          subtitles={scene.subtitles || []}
          fps={fps}
          hasImageBackground={false}
          imageAssetPlacement={placement}
        />
      </AbsoluteFill>
    );
  }

  let content: React.ReactNode;

  if (hasImage && placement === "fullscreen") {
    content = (<><ImageBg src={imgSrc} opacity={imgOpacity >= 0.8 ? imgOpacity : 0.9} />{creativeEl}</>);
  } else if (hasImage && placement === "center") {
    content = <CenterLayout src={imgSrc} opacity={imgOpacity}>{creativeEl}</CenterLayout>;
  } else if (hasImage && (placement === "left" || placement === "right")) {
    content = <SideLayout src={imgSrc} placement={placement} opacity={imgOpacity}>{creativeEl}</SideLayout>;
  } else {
    content = (<>{hasImage && <ImageBg src={imgSrc} opacity={imgOpacity} />}{creativeEl}</>);
  }

  return (
    <AbsoluteFill style={{ backgroundColor: preset.colors.bg, fontFamily }}>
      {content}
    </AbsoluteFill>
  );
};

export const SingleScenePlayer: React.FC<Props> = ({ scene, meta }) => {
  return (
    <DesignPresetProvider meta={meta}>
      <SingleSceneInner scene={scene} meta={meta} />
    </DesignPresetProvider>
  );
};
