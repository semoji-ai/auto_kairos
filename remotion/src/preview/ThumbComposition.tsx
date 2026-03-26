/**
 * ThumbComposition — 스토리보드 썸네일용
 *
 * SceneRenderer(공통 렌더러)를 사용.
 * 맵 씬만 플레이스홀더로 대체 (maplibre-gl 번들 회피).
 */
import React from "react";
import { AbsoluteFill, Img } from "remotion";
import { DesignPresetProvider } from "../design";
import { SceneRendererInner, resolveUrl } from "../components/SceneRenderer";
import type { SceneEntry, SceneManifest } from "../types/manifest";

interface Props {
  scene: SceneEntry;
  meta: SceneManifest["meta"];
}

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

const ThumbInner: React.FC<Props> = ({ scene, meta }) => {
  // 맵 씬 → 플레이스홀더
  if (scene.mapScene) {
    const bgPath = scene.mapScene.prerenderedBg?.imagePath;
    return <MapPlaceholder data={scene.mapScene} bg={bgPath} />;
  }
  // 일반 씬 → 공통 렌더러
  return <SceneRendererInner scene={scene} fps={meta?.fps || 30} />;
};

export const ThumbComposition: React.FC<Props> = ({ scene, meta }) => (
  <DesignPresetProvider meta={meta}>
    <ThumbInner scene={scene} meta={meta} />
  </DesignPresetProvider>
);
