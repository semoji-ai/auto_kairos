import React from "react";
import {
  AbsoluteFill,
  Img,
  staticFile,
  useCurrentFrame,
  interpolate,
  Easing,
  continueRender,
  delayRender,
} from "remotion";

/**
 * 세모지 애니메이팅 — 레이어 분리 + feet-bob.
 *
 * 배경(인물 없음) 위에 크로마키로 따낸 캐릭터를 올리고,
 * 캐릭터의 "발 위치"를 앵커(transform-origin: bottom)로 고정한 채
 * 세로 사이즈를 100%↔(max_scale)로 ease-in-out 왔다갔다 시킨다.
 * 스프라이트 포즈 교체가 아니라 단순 scaleY bob.
 *
 * 씬별 `layers.json`을 calculateMetadata에서 읽어 자동 구성한다.
 */

export type FeetBobMotion = {
  type: "feet_bob";
  max_scale: number; // 1.01 = 101%
  period_frames: number; // 20 = 10프레임 반주기
  phase_offset_frames?: number; // 캐릭터별 위상차(선택)
};

export type LayerCharacter = {
  name: string;
  src: string; // sceneDir 기준 상대경로 (크로마 제거된 투명 PNG)
  height_pct: number; // 화면 높이 대비 %
  bottom_pct: number; // 발 위치(하단에서 %)
  x_pct: number; // 가로 중심 위치 %
  motion?: FeetBobMotion;
};

export type SceneLayers = {
  scene_number: number;
  canvas: { width: number; height: number };
  fps: number;
  duration_frames?: number;
  background: { src: string } | null;
  characters: LayerCharacter[];
};

export type SemojiLayerSceneProps = {
  sceneDir: string; // 예: "images/scene_005" (staticFile 기준)
  layers?: SceneLayers; // calculateMetadata가 주입
};

const bobScaleY = (
  frame: number,
  motion: FeetBobMotion | undefined
): number => {
  if (!motion || motion.type !== "feet_bob") return 1;
  const period = motion.period_frames || 20;
  const half = period / 2;
  const phase = motion.phase_offset_frames || 0;
  const t = (((frame + phase) % period) + period) % period;
  return interpolate(t, [0, half, period], [1, motion.max_scale || 1.01, 1], {
    easing: Easing.inOut(Easing.ease),
    extrapolateRight: "clamp",
  });
};

export const SemojiLayerScene: React.FC<SemojiLayerSceneProps> = ({
  sceneDir,
  layers,
}) => {
  const frame = useCurrentFrame();
  if (!layers) return <AbsoluteFill style={{ backgroundColor: "#000" }} />;

  return (
    <AbsoluteFill style={{ backgroundColor: "#000000" }}>
      {layers.background ? (
        <Img
          src={staticFile(`${sceneDir}/${layers.background.src}`)}
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
        />
      ) : null}

      {layers.characters.map((c, i) => (
        <Img
          key={`${c.name}-${i}`}
          src={staticFile(`${sceneDir}/${c.src}`)}
          style={{
            position: "absolute",
            left: `${c.x_pct}%`,
            bottom: `${c.bottom_pct}%`,
            height: `${c.height_pct}%`,
            transform: `translateX(-50%) scaleY(${bobScaleY(frame, c.motion)})`,
            transformOrigin: "bottom center", // 발 앵커
          }}
        />
      ))}
    </AbsoluteFill>
  );
};

/**
 * sceneDir/layers.json 을 읽어 width/height/fps/duration + layers prop 구성.
 * Remotion Composition 의 calculateMetadata 에서 사용.
 */
export const calcSemojiLayerMetadata = async ({
  props,
}: {
  props: SemojiLayerSceneProps;
}) => {
  const handle = delayRender("loading layers.json");
  const res = await fetch(staticFile(`${props.sceneDir}/layers.json`));
  const layers = (await res.json()) as SceneLayers;
  continueRender(handle);
  const fps = layers.fps || 30;
  return {
    width: layers.canvas?.width || 1920,
    height: layers.canvas?.height || 1080,
    fps,
    durationInFrames: layers.duration_frames || fps * 4,
    props: { ...props, layers },
  };
};
