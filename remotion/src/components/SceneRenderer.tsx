/**
 * SceneRenderer — 공통 씬 렌더러
 *
 * 스토리보드(ThumbComposition), 스튜디오(SingleScenePlayer),
 * Remotion Studio(SimpleVideo) 모두 이 컴포넌트를 사용.
 * 수정은 여기서만 하면 3뷰가 동일하게 반영됨.
 */
import React from "react";
import { AbsoluteFill, Img, OffthreadVideo, staticFile, useVideoConfig } from "remotion";
import { CreativeScene } from "../simple/CreativeScene";
import { useDesignPreset } from "../design";
import { DEFAULT_PRESET } from "../design/defaults";
import { buildFontFamily, usePresetFonts } from "../design/fonts";

/** URL/절대경로면 그대로, 상대경로면 staticFile() 사용 (Remotion Studio 호환) */
export const resolveUrl = (path: string): string => {
  if (!path) return "";
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  // /background/... → staticFile("background/...") (Remotion Studio에서 public/ 기준)
  if (path.startsWith("/background/")) return staticFile(path.slice(1));
  // /output/... → 대시보드 StaticFiles 마운트 (절대경로 그대로)
  if (path.startsWith("/")) return path;
  // 상대경로 → staticFile
  return staticFile(path);
};

/** v5 플랫 스키마 → visualization 블록 조립 (v4 호환) */
export const resolveVisualization = (scene: any): any => {
  // v4: scene.visualization이 이미 있으면 그대로 반환 + top-level 보조 필드 병합
  if (scene.visualization && (scene.visualization.items || scene.visualization.creative)) {
    const viz = { ...scene.visualization };
    // top-level images/itemIcons/itemFlags는 visualization에 없을 수 있으므로 병합
    if (scene.images && !viz.images) viz.images = scene.images;
    if (scene.itemIcons && !viz.itemIcons) viz.itemIcons = scene.itemIcons;
    if (scene.itemFlags && !viz.itemFlags) viz.itemFlags = scene.itemFlags;
    return viz;
  }
  // v5 플랫: 최상위 필드에서 visualization 조립
  const viz: any = {};
  for (const k of ["layout", "headline", "items", "values", "unit", "source",
                     "icons", "flags", "chartConfig", "title", "chartStyle",
                     "orientation", "withPortrait", "portraitPlacement", "itemIcons",
                     "itemFlags", "logoMap", "images"]) {
    if (scene[k] != null) viz[k] = scene[k];
  }
  if (scene.mood || scene.motion) {
    viz.mood = scene.mood;
    viz.motionPreset = scene.motion;
  }
  if (scene.sceneType) viz.layout = scene.sceneType;
  if (scene.motionPreset) viz.motionPreset = scene.motionPreset;
  if (scene.mood) viz.mood = scene.mood;
  return Object.keys(viz).length > 0 ? viz : (scene.visualization || {});
};

/* ── 이미지 배경 ── */
export const ImageBg: React.FC<{
  src: string; opacity: number;
  offsetX?: number; offsetY?: number; scale?: number;
  fit?: "cover" | "contain" | "fill";
}> = ({ src, opacity, offsetX = 50, offsetY = 50, scale = 1.0, fit = "contain" }) => (
  <AbsoluteFill style={{ zIndex: 0, overflow: "hidden" }}>
    <Img src={resolveUrl(src)} style={{
      width: "100%", height: "100%", objectFit: fit, opacity,
      objectPosition: `${offsetX}% ${offsetY}%`,
      transform: scale !== 1.0 ? `scale(${scale})` : undefined,
      transformOrigin: `${offsetX}% ${offsetY}%`,
    }} />
  </AbsoluteFill>
);

/* ── 비디오 배경 ── */
export const VideoBg: React.FC<{
  src: string;
  opacity: number;
  startSec?: number;
  endSec?: number;
  volume?: number;
}> = ({ src, opacity, startSec = 0, volume = 0 }) => {
  const { fps } = useVideoConfig();
  const startFrom = Math.round(startSec * fps);
  return (
    <AbsoluteFill style={{ zIndex: 0, overflow: "hidden" }}>
      <OffthreadVideo
        src={resolveUrl(src)}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          opacity,
        }}
        startFrom={startFrom}
        volume={volume}
        muted={volume === 0}
        playbackRate={1}
        pauseWhenBuffering
      />
    </AbsoluteFill>
  );
};

/* ── Side 이미지 레이아웃 ── */
const SideLayout: React.FC<{
  src: string; placement: "left" | "right"; opacity: number; defaultBg?: string; mood?: string;
  offsetX?: number; offsetY?: number; scale?: number;
  children: React.ReactNode;
}> = ({ src, placement, opacity, defaultBg, mood, offsetX = 50, offsetY = 50, scale = 1.0, children }) => {
  const preset = useDesignPreset();
  const bgColor = preset.colors?.bg || "#0A0A0A";
  const isLeft = placement === "left";
  const hasSrc = !!src;
  // mood gradient: accent 색상 기반으로 직접 생성 (DEFAULT_PRESET 다크 그라데이션은 너무 어두움)
  const moodKey = mood || "dramatic";
  const moodEntry = preset.moods?.[moodKey as keyof typeof preset.moods]
    ?? DEFAULT_PRESET.moods[moodKey as keyof typeof DEFAULT_PRESET.moods];
  const accentRgb = moodEntry?.accentRgb ?? "245,158,11";
  const moodGradient = `radial-gradient(ellipse 90% 70% at 50% 40%, rgba(${accentRgb},0.45) 0%, rgba(${accentRgb},0.12) 60%, ${bgColor} 100%)`;
  return (
    <AbsoluteFill>
      {/* mood 그라데이션 배경 — disableSpotlight 프리셋이면 단색만 */}
      <div style={{ position: "absolute", inset: 0, background: preset.disableSpotlight ? bgColor : moodGradient, zIndex: 0 }} />
      {/* 전체 배경 텍스처 */}
      {defaultBg && <ImageBg src={defaultBg} opacity={0.15} />}
      <AbsoluteFill style={{ display: "flex", flexDirection: isLeft ? "row" : "row-reverse" }}>
        {/* 이미지 영역 — 세로 꽉 채움 */}
        <div style={{
          flex: "0 0 40%", position: "relative", overflow: "hidden",
          WebkitMaskImage: isLeft
            ? `linear-gradient(to right, black 65%, transparent 100%)`
            : `linear-gradient(to left, black 65%, transparent 100%)`,
          maskImage: isLeft
            ? `linear-gradient(to right, black 65%, transparent 100%)`
            : `linear-gradient(to left, black 65%, transparent 100%)`,
        }}>
          {hasSrc ? (
            <Img src={resolveUrl(src)} style={{
              width: "100%", height: "100%", objectFit: "cover",
              objectPosition: `${offsetX}% ${offsetY}%`, opacity,
              transform: scale !== 1.0 ? `scale(${scale})` : undefined,
              transformOrigin: `${offsetX}% ${offsetY}%`,
            }} />
          ) : (
            <div style={{ width: "100%", height: "100%", display: "flex",
                          alignItems: "center", justifyContent: "center",
                          backgroundColor: "rgba(255,255,255,0.06)" }}>
              <div style={{ fontSize: 80, opacity: 0.2 }}>👤</div>
            </div>
          )}
        </div>
        {/* 콘텐츠 영역 — 투명: CreativeScene의 MoodBackground가 배경 담당 */}
        <div style={{ flex: 1, position: "relative", display: "flex", alignItems: "center" }}>{children}</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/* ── Center 이미지 레이아웃 ── */
const CenterLayout: React.FC<{
  src: string; opacity: number;
  offsetX?: number; offsetY?: number; scale?: number;
  children: React.ReactNode;
}> = ({ src, opacity, offsetX = 50, offsetY = 50, scale = 1.0, children }) => (
  <AbsoluteFill style={{ display: "flex", flexDirection: "column" }}>
    <div style={{
      flex: "0 0 45%", display: "flex", alignItems: "center",
      justifyContent: "center", padding: "16px 40px", position: "relative",
    }}>
      <Img src={resolveUrl(src)} style={{
        maxWidth: "70%", maxHeight: "100%", objectFit: "contain",
        opacity, borderRadius: 16, filter: "drop-shadow(0 8px 32px rgba(0,0,0,0.6))",
        objectPosition: `${offsetX}% ${offsetY}%`,
        transform: scale !== 1.0 ? `scale(${scale})` : undefined,
      }} />
    </div>
    <div style={{ flex: 1, position: "relative" }}>{children}</div>
  </AbsoluteFill>
);

/* ── 텍스처 오버레이 (최상위 레이어) ── */
export const TextureOverlay: React.FC<{ src: string; blendMode?: string; opacity?: number }> = ({
  src, blendMode = "multiply", opacity = 0.2,
}) => (
  <AbsoluteFill style={{ pointerEvents: "none" }}>
    <Img
      src={resolveUrl(src)}
      style={{
        width: "100%", height: "100%",
        objectFit: "cover",
        mixBlendMode: blendMode as React.CSSProperties["mixBlendMode"],
        opacity,
      }}
    />
  </AbsoluteFill>
);

/* ── 공통 인터페이스 ── */
export interface SceneRendererProps {
  scene: any;
  fps?: number;
}

/**
 * SceneRendererInner — DesignPresetProvider 안에서 호출됨.
 * 모든 이미지/레이아웃 분기를 여기서 통합 처리.
 */
export const SceneRendererInner: React.FC<SceneRendererProps> = ({ scene, fps = 30 }) => {
  const preset = useDesignPreset();
  usePresetFonts();
  const fontFamily = buildFontFamily(preset);
  const vizData = resolveVisualization(scene);

  const defaultBg = preset.defaultBackground;
  const textureCfg = (preset as any).texture as { src: string; blendMode?: string; opacity?: number; topLayer?: boolean } | undefined;
  // topLayer:true면 SimpleVideo 레벨에서 자막 위에 렌더 — SceneRenderer 내부에서는 스킵
  const renderTextureHere = textureCfg && !textureCfg.topLayer;
  const sceneLayout = scene.layout || scene.sceneType || "";
  const isPersonCard = sceneLayout === "person_card";
  // person_card 레이아웃은 이미지를 카드 내부에서 소비 — 배경으로 쓰지 않음
  // imageAsset.source === "none" 이면 이미지 없음 처리 (imagePath가 남아있어도 무시)
  const isImageSourceNone = (scene.imageAsset as any)?.source === "none";
  const sceneImage = (!isPersonCard && !isImageSourceNone && (scene.imagePath || scene.vizBackgroundPath)) || "";
  const hasSceneImage = !!sceneImage;
  // source:none이면 defaultBg도 사용하지 않음
  const effectiveDefaultBg = isImageSourceNone ? "" : (defaultBg || "");
  // videoAsset 읽기
  const videoPath = scene.videoPath || "";
  const videoAssetCfg = scene.videoAsset as {
    placement?: string;
    startSec?: number;
    endSec?: number;
    opacity?: number;
    volume?: number;
  } | undefined;
  const hasVideo = !!videoPath && !!videoAssetCfg;
  const videoPlacement = videoAssetCfg?.placement ?? "background";
  const videoOpacity = videoAssetCfg?.opacity ?? 0.7;
  const videoStartSec = videoAssetCfg?.startSec ?? 0;
  const videoEndSec = videoAssetCfg?.endSec;
  const videoVolume = videoAssetCfg?.volume ?? 0;
  const hasAnyImage = hasSceneImage || !!effectiveDefaultBg;
  const placement = scene.imageAsset?.placement ?? "background";
  // quote는 레거시 — build_manifest에서 quote_portrait로 정규화됨. 렌더러는 둘 다 동일 처리
  const isQuoteLayout = (
    ["quote", "quote_portrait"].includes(vizData?.layout) ||
    ["quote", "quote_portrait"].includes(vizData?.creative?.layout) ||
    ["quote", "quote_portrait"].includes(scene.visualization?.layout) ||
    ["quote", "quote_portrait"].includes(scene.layout) ||
    ["quote", "quote_portrait"].includes(scene.sceneType)
  );
  const defaultOpacity = (placement === "background")
    ? (isQuoteLayout ? 1.0 : (!hasSceneImage && preset.defaultBgOpacity != null ? preset.defaultBgOpacity : 0.35))
    : 1.0;
  const imgOpacity = scene.imageAsset?.opacity ?? defaultOpacity;
  const imgOffsetX = scene.imageAsset?.offsetX ?? 50;
  const imgOffsetY = scene.imageAsset?.offsetY ?? 50;
  const imgScale   = scene.imageAsset?.scale   ?? 1.0;
  const imgFit     = scene.imageAsset?.fit     ?? "contain";
  const imgSrc = sceneImage || effectiveDefaultBg || "";

  // ── 비디오 우선 — videoAsset이 있으면 placement 분기 전에 먼저 처리 ──
  if (hasVideo) {
    return (
      <AbsoluteFill style={{ backgroundColor: preset.colors.bg, fontFamily }}>
        <VideoBg
          src={videoPath}
          opacity={videoOpacity}
          startSec={videoStartSec}
          endSec={videoEndSec}
          volume={videoVolume}
        />
        {videoPlacement !== "fullscreen" && (
          <CreativeScene
            data={vizData}
            subtitles={scene.subtitles}
            fps={fps}
            hasImageBackground={true}
            imageAssetPlacement={placement}
          />
        )}
        {renderTextureHere && <TextureOverlay src={textureCfg.src} blendMode={textureCfg.blendMode} opacity={textureCfg.opacity} />}
      </AbsoluteFill>
    );
  }

  // ── fullscreen ──
  if (hasAnyImage && placement === "fullscreen") {
    return (
      <AbsoluteFill style={{ backgroundColor: preset.colors.bg, fontFamily }}>
        <ImageBg src={imgSrc} opacity={imgOpacity >= 0.8 ? imgOpacity : 0.9} offsetX={imgOffsetX} offsetY={imgOffsetY} scale={imgScale} fit={imgFit} />
        <CreativeScene
          data={vizData}
          subtitles={scene.subtitles}
          fps={fps}
          hasImageBackground={true}
          imageAssetPlacement="fullscreen"
        />
        {renderTextureHere && <TextureOverlay src={textureCfg.src} blendMode={textureCfg.blendMode} opacity={textureCfg.opacity} />}
      </AbsoluteFill>
    );
  }

  // ── center ──
  if (hasSceneImage && placement === "center") {
    return (
      <AbsoluteFill style={{ backgroundColor: preset.colors.bg, fontFamily }}>
        <CenterLayout src={imgSrc} opacity={imgOpacity} offsetX={imgOffsetX} offsetY={imgOffsetY} scale={imgScale}>
          <CreativeScene
            data={vizData}
            subtitles={scene.subtitles}
            fps={fps}
            hasImageBackground={false}
            imageAssetPlacement="center"
          />
        </CenterLayout>
        {renderTextureHere && <TextureOverlay src={textureCfg.src} blendMode={textureCfg.blendMode} opacity={textureCfg.opacity} />}
      </AbsoluteFill>
    );
  }

  // ── side (left/right) — 이미지 없어도 placement가 side면 진입 (placeholder 표시) ──
  if (placement === "left" || placement === "right") {
    const sideVizData = vizData?.creative
      ? { ...vizData, creative: { ...vizData.creative, portraitPlacement: placement, withPortrait: true } }
      : vizData;
    return (
      <AbsoluteFill style={{ fontFamily }}>
        <SideLayout src={hasSceneImage ? imgSrc : ""} placement={placement} opacity={imgOpacity} defaultBg={effectiveDefaultBg} mood={scene.mood || vizData?.mood} offsetX={imgOffsetX} offsetY={imgOffsetY} scale={imgScale}>
          <CreativeScene
            data={sideVizData}
            subtitles={scene.subtitles}
            fps={fps}
            hasImageBackground={false}
            imageAssetPlacement={placement}
          />
        </SideLayout>
        {renderTextureHere && <TextureOverlay src={textureCfg.src} blendMode={textureCfg.blendMode} opacity={textureCfg.opacity} />}
      </AbsoluteFill>
    );
  }

  // ── background (기본) ──
  return (
    <AbsoluteFill style={{ backgroundColor: preset.colors.bg, fontFamily }}>
      {hasAnyImage && <ImageBg src={imgSrc} opacity={imgOpacity} offsetX={imgOffsetX} offsetY={imgOffsetY} scale={imgScale} fit={imgFit} />}
      <CreativeScene
        data={vizData}
        subtitles={scene.subtitles}
        fps={fps}
        hasImageBackground={hasAnyImage}
        imageAssetPlacement={placement}
      />
      {renderTextureHere && <TextureOverlay src={textureCfg.src} blendMode={textureCfg.blendMode} opacity={textureCfg.opacity} />}
    </AbsoluteFill>
  );
};
