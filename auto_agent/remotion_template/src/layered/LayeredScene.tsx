/**
 * LayeredScene — 분리된 레이어를 카메라와 함께 그린다.
 *
 * 파이썬 시제품(`scripts/render_camera.py`)을 옮긴 것이다. 그쪽은 프레임마다
 * SVG를 다시 그려 564프레임에 8분이 걸렸는데, 여기서는 브라우저가 그린다.
 *
 * 두 가지가 CSS로 공짜가 된다.
 *   - 발 축 까딱   transformOrigin "50% 100%" — 알파를 훑어 발을 찾을 필요가 없다
 *   - 벡터 확대    <img src=".svg">를 키우면 브라우저가 다시 그린다
 */
import React from "react";
import { AbsoluteFill, Audio, Img, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

export type Rect = [number, number, number, number];      // x, y, w, h — 씬 이미지 좌표

export type LayerSpec = {
  name: string;
  src: string;                    // public/ 기준 경로 (.png 또는 .svg)
  bbox?: Rect;                    // 없으면 배경판 — 화면 전체
  role?: "bg" | "person" | "prop";
  bob?: { amp: number; period: number; phase: number };   // 인물만
};

export type CameraKey = { t: number; rect: Rect; ease?: "linear" | "ease" | "70:30" };

export type LayeredSceneProps = {
  scene: { width: number; height: number };               // 씬 이미지 크기
  layers: LayerSpec[];                                    // 뒤 → 앞 순서
  camera?: CameraKey[];
  audioSrc?: string;
};

/** cubic-bezier(0.7, 0, 0.3, 1) — 느리게 떠나 빠르게 지나 느리게 멈춘다. */
const ease7030 = (u: number): number => {
  let lo = 0, hi = 1;
  for (let i = 0; i < 20; i++) {
    const m = (lo + hi) / 2;
    const x = 3 * (1 - m) ** 2 * m * 0.7 + 3 * (1 - m) * m * m * 0.3 + m ** 3;
    if (x < u) lo = m; else hi = m;
  }
  const m = (lo + hi) / 2;
  return 3 * (1 - m) * m * m + m ** 3;
};

const applyEase = (kind: CameraKey["ease"], u: number): number => {
  if (kind === "linear") return u;
  if (kind === "70:30") return ease7030(u);
  return u * u * (3 - 2 * u);                              // ease
};

/** 지금 시각의 화각. 키 사이를 이징으로 잇는다. */
const viewAt = (keys: CameraKey[], t: number, fallback: Rect): Rect => {
  if (!keys || keys.length === 0) return fallback;
  if (t <= keys[0].t) return keys[0].rect;
  for (let i = 1; i < keys.length; i++) {
    if (t <= keys[i].t) {
      const a = keys[i - 1], b = keys[i];
      const span = b.t - a.t;
      const u = span <= 0 ? 1 : applyEase(b.ease, (t - a.t) / span);
      return a.rect.map((v, k) => v + (b.rect[k] - v) * u) as Rect;
    }
  }
  return keys[keys.length - 1].rect;
};

export const LayeredScene: React.FC<LayeredSceneProps> = ({ scene, layers, camera, audioSrc }) => {
  const frame = useCurrentFrame();
  const { width: CW, height: CH, fps } = useVideoConfig();
  const t = frame / fps;

  const [vx, vy, vw] = viewAt(camera ?? [], t, [0, 0, scene.width, scene.height]);
  const s = CW / vw;                                       // 화면 배율

  return (
    <AbsoluteFill style={{ backgroundColor: "#000", overflow: "hidden" }}>
      {/* 카메라 — 씬 좌표계를 통째로 옮기고 키운다. 자식은 씬 좌표를 그대로 쓴다. */}
      <div style={{
        position: "absolute", left: 0, top: 0,
        width: scene.width, height: scene.height,
        transformOrigin: "0 0",
        transform: `scale(${s}) translate(${-vx}px, ${-vy}px)`,
      }}>
        {layers.map((L, i) => {
          const [bx, by, bw, bh] = L.bbox ?? [0, 0, scene.width, scene.height];
          // 발 축 까딱 — 아래가 붙어 있고 위로만 늘어난다. 축 계산이 필요 없다.
          let sy = 1;
          if (L.role === "person" && L.bob) {
            const e = (1 - Math.cos(2 * Math.PI * (t * L.bob.period) + L.bob.phase)) / 2;
            sy = 1 + L.bob.amp * e;
          }
          return (
            <Img
              key={`${L.name}-${i}`}
              src={staticFile(L.src)}
              style={{
                position: "absolute", left: bx, top: by, width: bw, height: bh,
                transformOrigin: "50% 100%",
                transform: sy === 1 ? undefined : `scaleY(${sy})`,
                zIndex: i,
              }}
            />
          );
        })}
      </div>
      {audioSrc && <Audio src={staticFile(audioSrc)} />}
    </AbsoluteFill>
  );
};
