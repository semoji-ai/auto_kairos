// 세피아 종이 컷아웃 실루엣 + 원경 4겹 패럴랙스 + 팔다리 컷아웃 워크(12fps 투스)
// 실측(potato_0328): 외곽선 없음·2톤+종이 그레인, 원경일수록 채도·명도↓(=옅게), 인물은 진한 적갈색.
// 카메라 평행이동 2.7~4.8px/f, 컷아웃 애니메이션은 2프레임마다 갱신(12fps).
import React from "react";
import { AbsoluteFill, Img, useCurrentFrame } from "remotion";
import { z } from "zod";
import { num, col, def } from "../params/p";
import { lin } from "./theme";

export const SilhouetteParallaxParams = z.object({
  camSpeed: num(3.2, 0, 12, 0.1, "카메라 이동 속도(근경 기준)", "motion", "px/f"),
  onTwos: num(2, 1, 4, 1, "컷아웃 갱신 간격(투스)", "timing", "f"),
  stride: num(26, 4, 80, 1, "걸음 주기", "timing", "f"),
  legSwing: num(24, 0, 60, 1, "다리 스윙 각도", "motion", "°"),
  bob: num(5, 0, 20, 0.5, "몸 들썩임", "motion", "px"),
  grain: num(0.22, 0, 1, 0.01, "종이 그레인", "look"),
  sky: col("#F1DCC0", "하늘(양피지) 색"),
  glow: col("#FBEBD2", "지평선 빛 색"),
  figure: col("#6B3326", "인물·낙타 색"),
});
export type SilhouetteParallaxP = z.infer<typeof SilhouetteParallaxParams>;

export type SilLayer = { src: string; top: number; h: number; depth: number; op?: number }; // depth: 근경=1, 원경→0
export type Walker = { kind: "camel" | "merchant"; x0: number; baseY: number; h: number; speed: number; phase?: number; flip?: boolean };

// 낙타 몸통 이미지(1085×619) 기준 다리 관절 위치(비율)
const CAMEL_W = 1085, CAMEL_H = 619;
const HIPS = [
  { x: 0.2, y: 0.84, ph: 0 }, { x: 0.28, y: 0.86, ph: Math.PI },
  { x: 0.55, y: 0.84, ph: Math.PI * 0.5 }, { x: 0.63, y: 0.82, ph: Math.PI * 1.5 },
];

const CamelLegs: React.FC<{ w: number; t: number; P: SilhouetteParallaxP; phase: number }> = ({ w, t, P, phase }) => {
  const s = w / CAMEL_W;
  const Lu = 0.36 * CAMEL_H * s, Ll = 0.4 * CAMEL_H * s, th = 0.075 * CAMEL_H * s;
  return (
    <svg width={w} height={CAMEL_H * s * 2} style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}>
      {HIPS.map((hp, i) => {
        const ph = (t / P.stride) * Math.PI * 2 + hp.ph + phase;
        const a1 = Math.sin(ph) * P.legSwing;
        const knee = Math.max(0, Math.sin(ph + Math.PI / 2)) * P.legSwing * 1.2 * (i < 2 ? 1 : -1);
        const hx = hp.x * CAMEL_W * s, hy = hp.y * CAMEL_H * s - th;
        const r1 = (a1 * Math.PI) / 180, r2 = ((a1 - knee) * Math.PI) / 180;
        const kx = hx + Math.sin(r1) * Lu, ky = hy + Math.cos(r1) * Lu;
        const fx = kx + Math.sin(r2) * Ll, fy = ky + Math.cos(r2) * Ll;
        const back = i % 2 === 1; // 반대편 다리는 살짝 어둡게
        return (
          <g key={i} opacity={back ? 0.82 : 1}>
            <line x1={hx} y1={hy} x2={kx} y2={ky} stroke={P.figure} strokeWidth={th * 1.5} strokeLinecap="round" />
            <line x1={kx} y1={ky} x2={fx} y2={fy} stroke={P.figure} strokeWidth={th * 0.8} strokeLinecap="round" />
            <ellipse cx={fx + th * 0.3} cy={fy} rx={th * 0.8} ry={th * 0.4} fill={P.figure} />
          </g>
        );
      })}
    </svg>
  );
};

export const SilhouetteParallax: React.FC<{ layers: SilLayer[]; walkers: Walker[]; front?: SilLayer[]; imgs: { camel: string; merchant: string }; p?: Partial<SilhouetteParallaxP> }> = ({ layers, walkers, front = [], imgs, p }) => {
  const P = def(SilhouetteParallaxParams, p);
  const f = useCurrentFrame();
  const ft = Math.floor(f / P.onTwos) * P.onTwos; // 컷아웃은 투스로
  const tile = (L: SilLayer, key: string) => {
    const aspect = 1536 / 450;
    const tw = L.h * (L.src.includes("sil_far") ? aspect : L.src.includes("sil_mid") ? 1536 / 722 : 1536 / 276);
    const off = ((f * P.camSpeed * L.depth) % tw + tw) % tw;
    const n = Math.ceil(1920 / tw) + 2;
    return (
      <div key={key} style={{ position: "absolute", left: 0, top: L.top, width: 1920, height: L.h, opacity: L.op ?? 1 }}>
        {Array.from({ length: n }).map((_, i) => (
          <Img key={i} src={L.src} style={{ position: "absolute", left: i * tw - off - 1, top: 0, width: tw + 2, height: L.h }} />
        ))}
      </div>
    );
  };
  return (
    <AbsoluteFill style={{ background: `linear-gradient(180deg, ${P.sky} 0%, ${P.glow} 58%, ${P.sky} 100%)` }}>
      <div style={{ position: "absolute", left: 1180, top: 170, width: 260, height: 260, borderRadius: "50%", background: "radial-gradient(circle, rgba(255,246,228,0.95) 0%, rgba(255,240,215,0.5) 45%, transparent 70%)" }} />
      {layers.map((L, i) => tile(L, `l${i}`))}
      {walkers.map((wk, i) => {
        const x = wk.x0 + wk.speed * f - P.camSpeed * 0 * f;
        const bob = Math.abs(Math.sin((ft / P.stride) * Math.PI * 2 + (wk.phase ?? 0))) * P.bob;
        if (wk.kind === "camel") {
          const w = wk.h * (CAMEL_W / CAMEL_H);
          return (
            <div key={i} style={{ position: "absolute", left: x, top: wk.baseY - wk.h * 1.52 - bob, width: w, height: wk.h, transform: wk.flip ? "scaleX(-1)" : undefined }}>
              <CamelLegs w={w} t={ft} P={P} phase={wk.phase ?? 0} />
              <Img src={imgs.camel} style={{ position: "absolute", left: 0, top: 0, width: w, height: wk.h }} />
            </div>
          );
        }
        const w = wk.h * (664 / 1204);
        const rot = Math.sin((ft / P.stride) * Math.PI * 2 + (wk.phase ?? 0)) * 2.5;
        return (
          <Img key={i} src={imgs.merchant} style={{ position: "absolute", left: x, top: wk.baseY - wk.h - bob * 0.6, height: wk.h, width: w, transform: `rotate(${rot}deg)`, transformOrigin: "50% 100%" }} />
        );
      })}
      {front.map((L, i) => tile(L, `f${i}`))}
      <svg width="100%" height="100%" style={{ position: "absolute", inset: 0, mixBlendMode: "multiply", opacity: P.grain }}>
        <filter id="silGrain"><feTurbulence type="fractalNoise" baseFrequency="0.7" numOctaves={2} seed={31} />
          <feColorMatrix values="0 0 0 0 0.5  0 0 0 0 0.4  0 0 0 0 0.3  0 0 0 -2.2 1.5" /></filter>
        <rect width="100%" height="100%" filter="url(#silGrain)" />
      </svg>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 45%, transparent 55%, rgba(90,50,20,0.35) 100%)", opacity: lin(f, 0, 1, 1, 1) }} />
    </AbsoluteFill>
  );
};
