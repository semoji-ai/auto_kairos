/**
 * ThumbMount — 스토리보드 썸네일 마운트 진입점
 *
 * window.mountSceneThumb(el, scene, meta) → Thumbnail으로 특정 프레임 정적 렌더
 */
import React from "react";
import { createRoot, Root } from "react-dom/client";
import { Thumbnail } from "@remotion/player";
import { ThumbComposition } from "./ThumbComposition";
import type { SceneEntry, SceneManifest } from "../types/manifest";

declare global {
  interface Window {
    mountSceneThumb?: (el: HTMLElement, scene: SceneEntry, meta: SceneManifest["meta"]) => void;
  }
}

const roots = new Map<HTMLElement, Root>();

function mountSceneThumb(
  el: HTMLElement,
  scene: SceneEntry,
  meta: SceneManifest["meta"],
) {
  // 기존 root 정리
  const existing = roots.get(el);
  if (existing) existing.unmount();

  const fps = meta?.fps || 30;
  const duration = scene.audioDurationSec
    ? Math.max(Math.ceil(scene.audioDurationSec * fps), 1)
    : 150;
  // duration - 1 프레임 — 모든 애니메이션 완료 상태
  const frameNumber = Math.max(duration - 1, 1);

  const root = createRoot(el);
  roots.set(el, root);

  root.render(
    <Thumbnail
      component={ThumbComposition}
      inputProps={{ scene, meta }}
      durationInFrames={duration}
      fps={fps}
      compositionWidth={meta?.resolution?.width || 1920}
      compositionHeight={meta?.resolution?.height || 1080}
      style={{ width: "100%", aspectRatio: "16/9" }}
      frameToDisplay={frameNumber}
      renderLoading={() => (
        <div style={{
          width: "100%", aspectRatio: "16/9", background: "#111",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 10, color: "#555",
        }}>
          Loading...
        </div>
      )}
    />
  );
}

// 글로벌에 등록
window.mountSceneThumb = mountSceneThumb;
