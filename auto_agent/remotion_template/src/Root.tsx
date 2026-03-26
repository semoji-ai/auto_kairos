import "./style.css";
import React from "react";
import { Composition, Folder, staticFile } from "remotion";
import { SceneEditor } from "./SceneEditor";
import { kairosVideoSchema, sceneEditorSchema } from "./types/schema";
import { SimpleVideo } from "./SimpleVideo";
import type { SceneManifest, SubtitleConfig } from "./types/manifest";

/**
 * 자막 기본 설정 - Studio Props Editor에서 직접 편집 가능
 */
const DEFAULT_SUBTITLE_CONFIG: SubtitleConfig = {
  visible: true,
  fontFamily: "'Noto Sans KR', 'Apple SD Gothic Neo', sans-serif",
  fontSize: 44,
  fontWeight: 700,
  color: "white",
  strokeColor: "#3D3B2F",
  strokeWidth: 0,
  keywordColor: "#F7D94C",
  keywordStrokeColor: "#5A4B00",
  bottomOffset: 80,
  maxWidth: "85%",
  lineHeight: 1.5,
};

/**
 * Studio에서 manifest가 없을 때 사용하는 최소 폴백
 */
const fallbackManifest: SceneManifest = {
  meta: {
    topic: "(No project loaded)",
    resolution: { width: 1920, height: 1080 },
    fps: 30,
    subtitleFont: "NotoSansKR",
    vizFont: "GriunPolFairness",
  },
  scenes: [
    {
      sceneNumber: 1,
      imagePath: "",
      audioPath: "",
      audioDurationSec: 5.0,
      subtitles: [
        {
          text: "대시보드에서 Studio를 시작하면 프로젝트가 자동으로 로드됩니다.",
          startSec: 0.5,
          endSec: 4.5,
        },
      ],
      visualization: {
        title: "Auto Agent",
        items: ["Dashboard → Studio 탭에서 시작"],
        values: [],
        unit: "",
        source: "",
      },
      kenBurns: { enabled: false, zoomFactor: 1.0 },
      transition: { type: "crossfade", durationFrames: 15 },
      overlays: [
        {
          type: "lottie" as const,
          assetId: "checkmark-success",
          position: "top-right" as const,
          scale: 0.6,
          enterFrame: 15,
        },
        {
          type: "lottie" as const,
          assetId: "trophy",
          position: "bottom-right" as const,
          scale: 0.5,
          enterFrame: 30,
        },
      ],
    },
  ],
  bgm: null,
};

/**
 * manifest.json에서 실제 프로젝트 데이터를 로드하는 공통 메타 함수
 *
 * Studio: public/manifest.json (대시보드가 자동 생성)
 * Render: --props 로 전달된 manifest (절대경로)
 */
async function loadManifest(
  propsManifest: SceneManifest,
): Promise<SceneManifest> {
  // CLI render: --props로 실제 프로젝트 데이터가 전달된 경우 (절대경로)
  if (propsManifest.meta.topic !== "(No project loaded)") {
    return propsManifest;
  }

  // Studio 모드: manifest.json 시도
  const manifestPaths = ["manifest.json"];
  for (const mPath of manifestPaths) {
    try {
      const url = staticFile(mPath);
      const resp = await fetch(url);
      if (resp.ok) {
        const data = await resp.json();
        if (data.manifest && data.manifest.meta) {
          return data.manifest as SceneManifest;
        }
        return data as SceneManifest;
      }
    } catch {
      // 파일 없음 → 다음 시도
    }
  }

  return propsManifest;
}

/**
 * 씬 수에 따라 총 duration 계산
 */
function calcTotalFrames(manifest: SceneManifest): number {
  const fps = manifest.meta.fps || 30;
  const totalFrames = manifest.scenes.reduce(
    (acc, s) => acc + Math.max(Math.ceil(s.audioDurationSec * fps) + 5, s.audioDurationSec > 0 ? 1 : 90),
    0,
  );
  return Math.max(totalFrames, 150);
}

/**
 * 씬별 Composition 등록에 사용할 씬 번호 배열
 */
const SCENE_SLOTS = Array.from({ length: 80 }, (_, i) => i + 1);

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* SimpleVideo — 기본 영상 컴포지션 */}
      <Composition
        id="SimpleVideo"
        component={SimpleVideo}
        schema={kairosVideoSchema}
        durationInFrames={150}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          manifest: fallbackManifest,
          subtitleConfig: DEFAULT_SUBTITLE_CONFIG,
        }}
        calculateMetadata={async ({ props }) => {
          const manifest = await loadManifest(props.manifest);
          const fps = manifest.meta.fps || 30;
          return {
            durationInFrames: calcTotalFrames(manifest),
            fps,
            width: manifest.meta.resolution?.width || 1920,
            height: manifest.meta.resolution?.height || 1080,
            props: {
              manifest,
              subtitleConfig: props.subtitleConfig,
            },
          };
        }}
      />

      {/* 씬별 개별 편집 컴포지션 */}
      <Folder name="Scenes">
        {SCENE_SLOTS.map((sceneNum) => (
          <Composition
            key={sceneNum}
            id={`Scene-${sceneNum}`}
            component={SceneEditor}
            schema={sceneEditorSchema}
            durationInFrames={150}
            fps={30}
            width={1920}
            height={1080}
            defaultProps={{
              manifest: fallbackManifest,
              sceneNumber: sceneNum,
              subtitleConfig: DEFAULT_SUBTITLE_CONFIG,
            }}
            calculateMetadata={async ({ props }) => {
              const manifest = await loadManifest(props.manifest);
              const fps = manifest.meta.fps || 30;
              const scene = manifest.scenes.find(
                (s) => s.sceneNumber === props.sceneNumber,
              );
              const duration = scene
                ? Math.ceil(scene.audioDurationSec * fps)
                : 1;
              return {
                durationInFrames: Math.max(duration, 1),
                fps,
                width: manifest.meta.resolution?.width || 1920,
                height: manifest.meta.resolution?.height || 1080,
                props: {
                  manifest,
                  sceneNumber: props.sceneNumber,
                  subtitleConfig: props.subtitleConfig,
                },
              };
            }}
          />
        ))}
      </Folder>
    </>
  );
};
