/**
 * SingleScenePlayer — @remotion/player용 씬 1개 렌더 컴포넌트
 *
 * SceneRenderer(공통 렌더러)를 사용.
 * 맵 씬은 MapSceneRenderer(lazy)로 처리.
 */
import React, { lazy, Suspense } from "react";
import { AbsoluteFill } from "remotion";
import { DesignPresetProvider, useDesignPreset } from "../design";
import { buildFontFamily } from "../design/fonts";
import { SceneRendererInner } from "../components/SceneRenderer";
import type { SceneEntry, SceneManifest } from "../types/manifest";

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

const SingleSceneInner: React.FC<Props> = ({ scene, meta }) => {
  const preset = useDesignPreset();
  const fontFamily = buildFontFamily(preset);
  const fps = meta?.fps || 30;
  const durationInFrames = scene.audioDurationSec
    ? Math.max(Math.ceil(scene.audioDurationSec * fps), 150)
    : 150;

  // 맵 씬 → MapSceneRenderer
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

  // 일반 씬 → 공통 렌더러
  return <SceneRendererInner scene={scene} fps={fps} />;
};

export const SingleScenePlayer: React.FC<Props> = ({ scene, meta }) => (
  <DesignPresetProvider meta={meta}>
    <SingleSceneInner scene={scene} meta={meta} />
  </DesignPresetProvider>
);
