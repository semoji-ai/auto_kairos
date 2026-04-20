/**
 * EditorApp — 씬 에디터 DOM 진입점
 *
 * 대시보드에서 window.__SCENE_EDITOR_DATA__를 설정한 후
 * mountSceneEditor(rootEl)을 호출하면 React 트리를 마운트한다.
 */
import React from "react";
import { createRoot, Root } from "react-dom/client";
import { SceneEditorPanel } from "./SceneEditorPanel";
import type { SceneEntry, SceneManifest } from "../types/manifest";

interface EditorData {
  scene: SceneEntry;
  meta: SceneManifest["meta"];
  slug: string;
}

declare global {
  interface Window {
    __SCENE_EDITOR_DATA__?: EditorData;
    mountSceneEditor?: (el: HTMLElement) => void;
    unmountSceneEditor?: () => void;
  }
}

let currentRoot: Root | null = null;

function mount(el: HTMLElement) {
  const data = window.__SCENE_EDITOR_DATA__;
  if (!data) {
    el.innerHTML = '<div style="padding:24px;color:#666;text-align:center">씬 데이터 없음</div>';
    return;
  }

  if (currentRoot) {
    currentRoot.unmount();
  }

  currentRoot = createRoot(el);
  currentRoot.render(
    <SceneEditorPanel
      scene={data.scene}
      meta={data.meta}
      slug={data.slug}
      onSaved={() => {
        // HTMX로 스토리보드 새로고침
        const evt = new CustomEvent("scene-editor-saved", { detail: { sceneNumber: data.scene.sceneNumber } });
        document.dispatchEvent(evt);
      }}
    />
  );
}

function unmount() {
  if (currentRoot) {
    currentRoot.unmount();
    currentRoot = null;
  }
}

// 글로벌에 등록
window.mountSceneEditor = mount;
window.unmountSceneEditor = unmount;

// 자동 마운트: #scene-editor-root가 이미 있으면 즉시 마운트
const autoRoot = document.getElementById("scene-editor-root");
if (autoRoot && window.__SCENE_EDITOR_DATA__) {
  mount(autoRoot);
}
