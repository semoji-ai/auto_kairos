import React from "react";
import { AbsoluteFill, Audio } from "remotion";
import { staticFile } from "remotion";
import { DesignPresetProvider } from "./design";
import { SceneRendererInner } from "./components/SceneRenderer";
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

  const merged = JSON.parse(JSON.stringify(scene));
  const viz = merged.visualization || {};
  const creative = viz.creative || {};

  if (override.headline && override.headline !== "") creative.headline = override.headline;
  if (override.layout && override.layout !== "") creative.layout = override.layout;
  const origCreative = (scene.visualization || {}).creative || {};
  if (override.reveal && override.reveal !== origCreative.reveal) creative.reveal = override.reveal;
  if (override.emphasis && override.emphasis !== origCreative.emphasis) creative.emphasis = override.emphasis;
  if (override.mood && override.mood !== origCreative.mood) creative.mood = override.mood;

  if (override.title && override.title !== "") viz.title = override.title;
  if (override.unit && override.unit !== "") viz.unit = override.unit;
  if (override.source && override.source !== "") viz.source = override.source;

  if (override.items && override.items !== "") {
    viz.items = override.items.split(",").map((s: string) => s.trim());
  }
  if (override.values && override.values !== "") {
    viz.values = override.values.split(",").map((s: string) => parseFloat(s.trim())).filter((n: number) => !isNaN(n));
  }

  // contentX/Y → creative에 주입 (CreativeScene에서 transform 적용 가능하도록)
  if (override.contentX && override.contentX !== 0) creative.contentOffsetX = override.contentX;
  if (override.contentY && override.contentY !== 0) creative.contentOffsetY = override.contentY;

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

  return (
    <DesignPresetProvider meta={manifest.meta}>
      {/* SceneRendererInner — 스토리보드/스튜디오/렌더링과 동일한 렌더러 */}
      <SceneRendererInner scene={mergedScene} fps={fps} />
      {/* 자막 오버레이 */}
      {subtitleConfig.visible !== false && mergedScene.subtitles?.length > 0 && (
        <SubtitleOverlay subtitles={mergedScene.subtitles} fps={fps} config={subtitleConfig} />
      )}
      {/* 오디오 */}
      {mergedScene.audioPath ? <Audio src={resolveAsset(mergedScene.audioPath)} /> : null}
    </DesignPresetProvider>
  );
};
