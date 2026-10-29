// 설명형 편집 레퍼런스(ref_explainer_editorial) 오마주 룩 — ref_explainer_editorial/analysis.md §1 팔레트·§4 전환 실측값(24f→30f 환산)
import { Easing, interpolate, staticFile } from "remotion";

export const PAL = {
  parchment: "#F2DFCA",
  parchmentDark: "#E4CCB0",
  red: "#C80000",
  redTitle: "#B80000",
  redShadow: "#A21608",
  occupied: "#780000",
  sea: "#585460",
  seaDeep: "#443E50",
  outline: "#281B2E",
  cyan: "#0494C8",
  chartDim: "#787068",
  globeLand: "#C6B9AC",
  globeSea: "#453A41",
  sepia1: "#6B4A33",
  sepia2: "#8E6F55",
  sepia3: "#C9AE8F",
  ink: "#1A1410",
} as const;

export const FPS = 30;
export const CL = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
export const lin = (f: number, a: number, b: number, v0: number, v1: number, e: (t: number) => number = Easing.linear) =>
  interpolate(f, [a, Math.max(a + 0.001, b)], [v0, v1], { ...CL, easing: e });
export const BACK_OUT = Easing.bezier(0.34, 1.56, 0.64, 1);
export const EXPO_OUT = Easing.bezier(0.16, 1, 0.3, 1);
export const img = (name: string) => staticFile(`explainer_demo/img/${name}`);

/** 결정적 의사난수(시드 문자열 + 인덱스) */
export const rnd = (seed: string, i: number) => {
  let h = 2166136261;
  const s = `${seed}:${i}`;
  for (let k = 0; k < s.length; k++) { h ^= s.charCodeAt(k); h = Math.imul(h, 16777619); }
  return ((h >>> 0) % 100000) / 100000;
};
