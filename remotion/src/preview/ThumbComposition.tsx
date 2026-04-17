/**
 * ThumbComposition — 스토리보드 썸네일용
 *
 * SceneRenderer(공통 렌더러)를 사용.
 * 스튜디오/씬에디터와 동일하게 맵/비디오 분기를 실제로 렌더한다.
 */
import React from "react";
import { AbsoluteFill } from "remotion";
import { DesignPresetProvider } from "../design";
import { useDesignPreset } from "../design";
import { buildFontFamily } from "../design/fonts";
import { SceneRendererInner } from "../components/SceneRenderer";
import { MapSceneRenderer } from "../map/MapSceneRenderer";
import type { SceneEntry, SceneManifest } from "../types/manifest";

interface Props {
  scene: SceneEntry;
  meta: SceneManifest["meta"];
}

const ThumbInner: React.FC<Props> = ({ scene, meta }) => {
  const preset = useDesignPreset();
  const fontFamily = buildFontFamily(preset);
  const fps = meta?.fps || 30;
  const durationInFrames = scene.audioDurationSec
    ? Math.max(Math.ceil(scene.audioDurationSec * fps), 1)
    : 150;

  // 맵 씬 → 실제 맵 렌더 (스토리보드와 스튜디오 결과 일치)
  if (scene.mapScene) {
    return (
      <AbsoluteFill style={{ backgroundColor: preset.colors.bg, fontFamily }}>
        <MapSceneRenderer
          data={scene.mapScene}
          durationInFrames={durationInFrames}
          fps={fps}
        />
      </AbsoluteFill>
    );
  }

  // 일반 씬 → 공통 렌더러
  // 비디오 씬: OffthreadVideo는 캔버스 썸네일 모드에서 렌더 불가 → videoAsset 제거 후 imagePath 폴백
  const thumbScene = scene.videoAsset
    ? { ...scene, videoPath: "", videoAsset: undefined }
    : scene;
  return <SceneRendererInner scene={thumbScene} fps={fps} />;
};

export const ThumbComposition: React.FC<Props> = ({ scene, meta }) => (
  <DesignPresetProvider meta={meta}>
    <ThumbInner scene={scene} meta={meta} />
  </DesignPresetProvider>
);
