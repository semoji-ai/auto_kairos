// 찢어진 종이 대각 와이프 — 실측(y7OMrkjkFPg 0:49.6~0:50.6): 24f(=30f), 우상→좌하로 찢긴 종이 가장자리가 내려오며
// 새 장면(양피지)이 덮는다. 가장자리에 밝은 섬유 띠 + 아래로 드리운 그림자.
import React from "react";
import { AbsoluteFill, Easing, useCurrentFrame } from "remotion";
import { z } from "zod";
import { num, col, def } from "../params/p";
import { lin, rnd } from "./theme";

export const TornPaperWipeParams = z.object({
  len: num(30, 4, 90, 1, "와이프 길이", "timing", "f"),
  angle: num(22, -60, 60, 1, "찢김선 기울기(+면 우측이 먼저)", "motion", "°"),
  jag: num(26, 0, 90, 1, "찢김 들쭉날쭉 크기", "size", "px"),
  rim: num(34, 0, 120, 1, "섬유 띠 두께", "size", "px"),
  shadow: num(0.45, 0, 1, 0.01, "그림자 세기", "look"),
  seed: num(3, 0, 99, 1, "찢김 모양 시드", "look"),
  rimColor: col("#EFE4D2", "섬유 띠 색"),
});
export type TornPaperWipeP = z.infer<typeof TornPaperWipeParams>;

const W = 1920, H = 1080;

/** 찢김선 폴리라인(회전 좌표계 x' 방향) — 큰 파형 + 잔 톱니 */
const edgePts = (seed: string, jag: number) => {
  const pts: [number, number][] = [];
  const N = 90;
  for (let i = 0; i <= N; i++) {
    const x = -600 + (i / N) * (W + 1200);
    const big = Math.sin(i * 0.23 + rnd(seed, 1) * 6) * jag * 0.9 + Math.sin(i * 0.071 + rnd(seed, 2) * 6) * jag * 1.4;
    const small = (rnd(seed, i + 10) - 0.5) * jag * 0.9;
    pts.push([x, big + small]);
  }
  return pts;
};

export const TornPaperWipe: React.FC<{ at: number; children: React.ReactNode; p?: Partial<TornPaperWipeP> }> = ({ at, children, p }) => {
  const P = def(TornPaperWipeParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  if (f >= at + P.len) return <AbsoluteFill>{children}</AbsoluteFill>;
  const k = lin(f, at, at + P.len, 0, 1, Easing.inOut(Easing.cubic));
  const th = (P.angle * Math.PI) / 180;
  // 진행 방향 = 찢김선 법선(아래쪽). 화면 대각 길이만큼 이동
  const diag = Math.hypot(W, H);
  const off = -diag * 0.5 + k * diag * 1.05;
  const seed = `tear${P.seed}`;
  const base = edgePts(seed, P.jag);
  const rim = edgePts(`${seed}r`, P.jag * 0.6);
  // 회전 좌표 → 화면 좌표 (중심 기준 회전 + 법선 방향 off 이동, 오른쪽이 먼저 내려오도록 x 에 따라 추가 지연)
  const tf = (x: number, y: number): [number, number] => {
    const lead = 0; // 기울기(angle>0)로 우측이 먼저 덮인다(우상→좌하)
    const yy = y + off + lead;
    return [W / 2 + (x - W / 2) * Math.cos(th) - yy * Math.sin(th), H / 2 + (x - W / 2) * Math.sin(th) + yy * Math.cos(th)];
  };
  const edge = base.map(([x, y]) => tf(x, y));
  const rimEdge = rim.map(([x, y], i) => tf(x, y + P.rim * (0.55 + 0.45 * rnd(seed, i + 300))));
  const top = [tf(W + 600, -3000), tf(-600, -3000)];
  const clip = `M${edge.map((q) => q.join(",")).join(" L")} L${top[0].join(",")} L${top[1].join(",")} Z`;
  const rimD = `M${edge.map((q) => q.join(",")).join(" L")} L${[...rimEdge].reverse().map((q) => q.join(",")).join(" L")} Z`;
  return (
    <AbsoluteFill>
      <svg width={W} height={H} style={{ position: "absolute", inset: 0, overflow: "visible" }}>
        <defs>
          <filter id="tearRim" x="-10%" y="-10%" width="120%" height="120%">
            <feTurbulence type="fractalNoise" baseFrequency="0.08 0.5" numOctaves={3} seed={P.seed} result="n" />
            <feDisplacementMap in="SourceGraphic" in2="n" scale={10} xChannelSelector="R" yChannelSelector="G" result="d" />
            <feDropShadow in="d" dx="-4" dy="10" stdDeviation="9" floodColor="#1a0e05" floodOpacity={P.shadow} />
          </filter>
        </defs>
        <path d={rimD} fill={P.rimColor} filter="url(#tearRim)" />
      </svg>
      <AbsoluteFill style={{ clipPath: `path('${clip}')` }}>{children}</AbsoluteFill>
    </AbsoluteFill>
  );
};
