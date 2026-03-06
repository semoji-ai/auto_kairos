import React from "react";
import { Composition, Folder, staticFile } from "remotion";
import { KairosVideo } from "./KairosVideo";
import { SceneEditor } from "./SceneEditor";
import { kairosVideoSchema, sceneEditorSchema, vizStillSchema, vizOnlySchema } from "./types/schema";
import { VizStill } from "./VizStill";
import { MapStill } from "./MapStill";
import { VizOnly } from "./VizOnly";
import { ZdogTest } from "./ZdogTest";
import { SvgCharacterTest } from "./SvgCharacterTest";
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
          text: "프로젝트를 로드하세요: python -m src.manuscript.remotion_bridge <output_dir> --studio",
          startSec: 0.5,
          endSec: 4.5,
        },
      ],
      visualization: {
        vizType: "slide_quote",
        title: "Auto Kairos",
        items: ["python -m src.manuscript.remotion_bridge\n<output_dir> --studio"],
        values: [],
        unit: "",
        source: "",
      },
      kenBurns: { enabled: false, zoomFactor: 1.0 },
      transition: { type: "crossfade", durationFrames: 15 },
    },
  ],
  bgm: null,
};

/**
 * manifest.json에서 실제 프로젝트 데이터를 로드하는 공통 메타 함수
 *
 * Studio: public/manifest.json (prepare_studio가 생성)
 * Render: --props 로 전달된 manifest (절대경로)
 */
async function loadManifest(
  propsManifest: SceneManifest,
): Promise<SceneManifest> {
  // CLI render: --props로 실제 프로젝트 데이터가 전달된 경우 (절대경로)
  if (propsManifest.meta.topic !== "(No project loaded)") {
    return propsManifest;
  }

  // Studio 모드: manifests/ 디렉토리 또는 manifest.json 시도
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
  const totalSec = manifest.scenes.reduce(
    (acc, s) => acc + s.audioDurationSec,
    0,
  );
  return Math.max(Math.ceil(totalSec * fps), 1);
}

/**
 * 씬별 Composition 등록에 사용할 씬 번호 배열 (최대 50)
 */
const SCENE_SLOTS = Array.from({ length: 80 }, (_, i) => i + 1);

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* 전체 영상 컴포지션 */}
      <Composition
        id="KairosVideo"
        component={KairosVideo}
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

      {/* 심플 Remotion 방식 영상 (커스텀 토큰 없음) */}
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

      {/* Creative Direction 테스트 컴포지션 — test_creative.json 로드 */}
      <Composition
        id="CreativeTest"
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
          try {
            const url = staticFile("test_creative.json");
            const resp = await fetch(url);
            if (resp.ok) {
              const data = await resp.json();
              const manifest = (data.manifest && data.manifest.meta)
                ? data.manifest as SceneManifest
                : data as SceneManifest;
              return {
                durationInFrames: calcTotalFrames(manifest),
                fps: manifest.meta.fps || 30,
                width: manifest.meta.resolution?.width || 1920,
                height: manifest.meta.resolution?.height || 1080,
                props: {
                  manifest,
                  subtitleConfig: data.subtitleConfig || props.subtitleConfig,
                },
              };
            }
          } catch { /* fallback */ }
          const manifest = await loadManifest(props.manifest);
          return {
            durationInFrames: calcTotalFrames(manifest),
            fps: manifest.meta.fps || 30,
            props: { manifest, subtitleConfig: props.subtitleConfig },
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

      {/* 시각화 전용 렌더링 (트랜지션/자막/오디오 없음) */}
      <Folder name="VizOnly">
        {SCENE_SLOTS.map((sceneNum) => (
          <Composition
            key={sceneNum}
            id={`VizOnly-${sceneNum}`}
            component={VizOnly}
            schema={vizOnlySchema}
            durationInFrames={150}
            fps={30}
            width={1920}
            height={1080}
            defaultProps={{
              manifest: fallbackManifest,
              sceneNumber: sceneNum,
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
                },
              };
            }}
          />
        ))}
      </Folder>

      {/* 시각화 스틸 이미지 렌더링용 */}
      <Composition
        id="VizStill"
        component={VizStill}
        schema={vizStillSchema}
        durationInFrames={150}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          vizData: {
            vizType: "slide_quote" as const,
            title: "VizStill",
            items: ["시각화 스틸 렌더링"],
            values: [],
            unit: "",
            source: "",
          },
        }}
      />
      {/* 맵 씬 렌더링용 (스틸/영상) — 600f(20s)까지 지원 */}
      <Composition
        id="MapStill"
        component={MapStill}
        durationInFrames={600}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          mapScene: {
            mapType: "location_reveal" as const,
            mapStyle: "modern_clean" as const,
            title: "MapStill Test",
            camera: {
              keyframes: [
                { frame: 0, center: [126.977, 37.566] as [number, number], zoom: 10 },
              ],
            },
          },
        }}
      />
      {/* Zdog 캐릭터 테스트 */}
      <Composition
        id="ZdogTest"
        component={ZdogTest}
        durationInFrames={150}
        fps={30}
        width={1920}
        height={1080}
      />
      {/* SVG 캐릭터 테스트 */}
      <Composition
        id="SvgCharacterTest"
        component={SvgCharacterTest}
        durationInFrames={300}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
