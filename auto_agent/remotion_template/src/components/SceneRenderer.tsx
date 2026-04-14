/**
 * SceneRenderer — 공통 씬 렌더러
 *
 * 스토리보드(ThumbComposition), 스튜디오(SingleScenePlayer),
 * Remotion Studio(SimpleVideo) 모두 이 컴포넌트를 사용.
 * 수정은 여기서만 하면 3뷰가 동일하게 반영됨.
 */
import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { CreativeScene } from "../simple/CreativeScene";
import { useDesignPreset } from "../design";
import { DEFAULT_PRESET } from "../design/defaults";
import { buildFontFamily } from "../design/fonts";

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
  // v4: scene.visualization이 이미 있으면 그대로
  if (scene.visualization && (scene.visualization.items || scene.visualization.creative)) {
    return scene.visualization;
  }
  // v5 플랫: 최상위 필드에서 visualization 조립
  const viz: any = {};
  for (const k of ["layout", "headline", "items", "values", "unit", "source",
                     "icons", "flags", "chartConfig", "title", "chartStyle",
                     "orientation", "withPortrait", "portraitPlacement", "itemIcons",
                     "itemFlags", "logoMap"]) {
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
export const ImageBg: React.FC<{ src: string; opacity: number }> = ({ src, opacity }) => (
  <AbsoluteFill style={{ zIndex: 0, overflow: "hidden" }}>
    <Img src={resolveUrl(src)} style={{ width: "100%", height: "100%", objectFit: "cover", opacity }} />
  </AbsoluteFill>
);

/* ── Side 이미지 레이아웃 ── */
const SideLayout: React.FC<{
  src: string; placement: "left" | "right"; opacity: number; defaultBg?: string; mood?: string; children: React.ReactNode;
}> = ({ src, placement, opacity, defaultBg, mood, children }) => {
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
      {/* mood 그라데이션 배경 */}
      <div style={{ position: "absolute", inset: 0, background: moodGradient, zIndex: 0 }} />
      {/* 전체 배경 텍스처 */}
      {defaultBg && <ImageBg src={defaultBg} opacity={0.15} />}
      <AbsoluteFill style={{ display: "flex", flexDirection: isLeft ? "row" : "row-reverse" }}>
        {/* 이미지 영역 — 세로 꽉 채움 */}
        <div style={{
          flex: "0 0 40%", position: "relative", overflow: "hidden",
        }}>
          {hasSrc ? (
            <Img src={resolveUrl(src)} style={{
              width: "100%", height: "100%", objectFit: "cover",
              objectPosition: "center top", opacity,
            }} />
          ) : (
            <div style={{ width: "100%", height: "100%", display: "flex",
                          alignItems: "center", justifyContent: "center",
                          backgroundColor: "rgba(255,255,255,0.06)" }}>
              <div style={{ fontSize: 80, opacity: 0.2 }}>👤</div>
            </div>
          )}
          {/* 그라데이션 페이드 */}
          <div style={{
            position: "absolute", inset: 0,
            background: isLeft
              ? `linear-gradient(to right, transparent 80%, ${bgColor} 100%)`
              : `linear-gradient(to left, transparent 80%, ${bgColor} 100%)`,
          }} />
        </div>
        {/* 콘텐츠 영역 — 투명: CreativeScene의 MoodBackground가 배경 담당 */}
        <div style={{ flex: 1, position: "relative", display: "flex", alignItems: "center" }}>{children}</div>
      </AbsoluteFill>
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
  const fontFamily = buildFontFamily(preset);
  const vizData = resolveVisualization(scene);

  const defaultBg = preset.defaultBackground;
  const sceneImage = scene.imagePath || scene.vizBackgroundPath || "";
  const hasSceneImage = !!sceneImage;
  const hasAnyImage = hasSceneImage || !!defaultBg;
  const placement = scene.imageAsset?.placement ?? "background";
  const defaultOpacity = (placement === "background") ? 0.35 : 1.0;
  const imgOpacity = scene.imageAsset?.opacity ?? defaultOpacity;
  const imgSrc = sceneImage || defaultBg || "";

  // ── fullscreen ──
  if (hasAnyImage && placement === "fullscreen") {
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

  // ── center ──
  if (hasSceneImage && placement === "center") {
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

  // ── side (left/right) — 이미지 없어도 placement가 side면 진입 (placeholder 표시) ──
  if (placement === "left" || placement === "right") {
    return (
      <AbsoluteFill style={{ fontFamily }}>
        <SideLayout src={hasSceneImage ? imgSrc : ""} placement={placement} opacity={imgOpacity} defaultBg={defaultBg} mood={scene.mood || vizData?.mood}>
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

  // ── background (기본) ──
  return (
    <AbsoluteFill style={{ backgroundColor: preset.colors.bg, fontFamily }}>
      {hasAnyImage && <ImageBg src={imgSrc} opacity={imgOpacity} />}
      <CreativeScene
        data={vizData}
        subtitles={scene.subtitles}
        fps={fps}
        hasImageBackground={hasAnyImage}
        imageAssetPlacement={placement}
      />
    </AbsoluteFill>
  );
};
