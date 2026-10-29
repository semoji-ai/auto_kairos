// 세모지 배경 루프 & 미디어 처리 컴포넌트 — 레퍼런스 프레임 실측 기반.
// 전부 결정론적(remotion random(seed)). 방사형 줄무늬 광선 패턴은 쓰지 않는다.
import React from "react";
import { AbsoluteFill, Img, random, useCurrentFrame, interpolate } from "remotion";
import { z } from "zod";
import { W, H, FPS, lerp, kf, photoPop, src } from "../fx";
import { num, col, flag, choice, def } from "../params/p";
import { prop } from "./kit";

/** 개별 prop 중 넘어온 것(undefined 아님)만 골라 스키마 기본값 위에 얹는다 */
const pk = <T extends Record<string, any>>(o: T): Partial<T> => Object.fromEntries(Object.entries(o).filter(([, v]) => v !== undefined)) as Partial<T>;

const wrap = (v: number, m: number) => ((v % m) + m) % m;
const R = (seed: string) => random(seed);
const CL = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// 4각 반짝이 경로(작은 트윙클용)
const STAR4 = "M0,-50 C6,-8 8,-6 50,0 C8,6 6,8 0,50 C-6,8 -8,6 -50,0 C-8,-6 -6,-8 0,-50Z";

// ══ 공통: 출처 칩 ═══════════════════════════════════════════════════════════
// 우하단, 자막 띠(y≈938) 바로 위 y≈880~925, 70% 다크 칩 + 흰 글씨 22px
export const SourceChipParams = z.object({
  fadeDur: num(6, 0, 30, 1, "나타나는 시간", "timing", "f"),
  size: num(22, 12, 48, 1, "글자 크기", "size", "px"),
  height: num(45, 24, 90, 1, "칩 높이", "size", "px"),
  radius: num(6, 0, 30, 1, "모서리 둥글기", "size", "px"),
  bgAlpha: num(0.7, 0, 1, 0.05, "칩 배경 불투명도", "look"),
  textColor: col("#fff", "글자 색"),
});
export type SourceChipP = z.infer<typeof SourceChipParams>;
export const SourceChip: React.FC<{ text: string; right?: number; top?: number; size?: number; at?: number; p?: Partial<SourceChipP> }> = ({ text, right = 36, top = 880, size, at = 0, p }) => {
  const P = def(SourceChipParams, { ...pk({ size }), ...p });
  const f = useCurrentFrame();
  if (f < at) return null;
  return (
    <div style={{ position: "absolute", right, top, height: P.height, display: "flex", alignItems: "center", padding: "0 16px", borderRadius: P.radius, background: `rgba(0,0,0,${P.bgAlpha})`, color: P.textColor, fontFamily: "NeoEb", fontSize: P.size, whiteSpace: "nowrap", opacity: P.fadeDur > 0 ? lerp(f, at, at + P.fadeDur, 0, 1) : 1 }}>{text}</div>
  );
};

// ══ 1. MatrixRain ═══════════════════════════════════════════════════════════
// 검정 배경, 숫자·라틴 글리프 컬럼 낙하. 3 깊이 레이어(크기/블러/속도/불투명 차등), 머리 글리프는 흰빛.
const GLYPHS = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZ0123456789";
export const MatrixRainParams = z.object({
  speed: num(1, 0, 4, 0.05, "낙하 속도(배)", "motion", "배"),
  density: num(1, 0.1, 3, 0.05, "컬럼 밀도(배)", "size", "배"),
  glyphScale: num(1, 0.3, 3, 0.05, "글자 크기(배)", "size", "배"),
  trail: num(1, 0.2, 3, 0.05, "꼬리 길이(배)", "size", "배"),
  flipRate: num(1, 0.2, 5, 0.1, "글자 바뀌는 주기(배)", "timing", "배"),
  depthBlur: num(1, 0, 4, 0.1, "뒤 레이어 블러(배)", "look", "배"),
  backAlpha: num(1, 0, 2.5, 0.05, "뒤 레이어 밝기(배)", "look", "배"),
  glow: num(8, 0, 40, 1, "앞 레이어 글로우", "look", "px"),
  tailMin: num(0.08, 0, 1, 0.01, "꼬리 끝 최소 불투명도", "look"),
  color: col("#3FBF3F", "글자 색"),
  head: col("#E6FFE6", "머리 글자 색"),
  bg: col("#000", "배경색"),
});
export type MatrixRainP = z.infer<typeof MatrixRainParams>;
export const MatrixRain: React.FC<{ color?: string; head?: string; bg?: string; speed?: number; density?: number; seed?: string; p?: Partial<MatrixRainP> }> = ({ color, head, bg, speed, density, seed = "mx", p }) => {
  const P = def(MatrixRainParams, { ...pk({ color, head, bg, speed, density }), ...p });
  const f = useCurrentFrame();
  const layers = [
    { size: 16, blur: 1.8, v: 5, op: 0.35, cols: 72 },
    { size: 26, blur: 0.7, v: 9, op: 0.65, cols: 44 },
    { size: 40, blur: 0, v: 15, op: 1, cols: 24 },
  ].map((L, li) => ({ ...L, size: L.size * P.glyphScale, blur: L.blur * P.depthBlur, op: li === 2 ? L.op : Math.min(1, L.op * P.backAlpha) }));
  return (
    <AbsoluteFill style={{ background: P.bg, overflow: "hidden" }}>
      {layers.map((L, li) => {
        const cols = Math.max(1, Math.round(L.cols * P.density));
        const cw = W / cols;
        return (
          <AbsoluteFill key={li} style={{ opacity: L.op, filter: L.blur ? `blur(${L.blur}px)` : undefined }}>
            {Array.from({ length: cols }).map((_, c) => {
              const k = `${seed}${li}-${c}`;
              const len = Math.max(1, Math.round((8 + Math.floor(R(k + "l") * 18)) * P.trail));
              const vv = L.v * P.speed * (0.8 + R(k + "v") * 0.45);
              const period = H + len * L.size + 200 + R(k + "p") * 500;
              const headY = wrap(f * vv + R(k + "o") * period, period) - L.size;
              const x = (c + 0.2 + R(k + "x") * 0.6) * cw - L.size * 0.3;
              return (
                <div key={c} style={{ position: "absolute", left: x, top: headY - (len - 1) * L.size, display: "flex", flexDirection: "column", fontFamily: "Menlo, 'Courier New', monospace", fontWeight: 700, fontSize: L.size, lineHeight: `${L.size}px`, textShadow: li === 2 && P.glow > 0 ? `0 0 ${P.glow}px ${P.color}` : undefined }}>
                  {Array.from({ length: len }).map((__, j) => {
                    const d = len - 1 - j; // 0 = head
                    const rate = Math.max(1, Math.round((3 + Math.floor(R(`${k}r${j}`) * 8)) * P.flipRate));
                    const g = GLYPHS[Math.floor(R(`${k}g${j}-${Math.floor((f + j * 5) / rate)}`) * GLYPHS.length)];
                    return <span key={j} style={{ color: d === 0 ? P.head : P.color, opacity: d === 0 ? 1 : Math.max(P.tailMin, 1 - d / len) }}>{g}</span>;
                  })}
                </div>
              );
            })}
          </AbsoluteFill>
        );
      })}
    </AbsoluteFill>
  );
};

// ══ 2. MoneyRain ════════════════════════════════════════════════════════════
// 플랫 녹색 지폐 + 금화 낙하·텀블링(회전 + scaleX 플립), 루프. 배경 투명(오버레이).
// 세모지 지폐(banknote_won 크롭 xc_banknote 900×471)·동전(coin_won) PNG
const Bill: React.FC<{ w: number }> = ({ w }) => (
  <Img src={prop("xc_banknote")} style={{ display: "block", width: w, height: (w * 471) / 900 }} />
);
const Coin: React.FC<{ d: number }> = ({ d }) => (
  <Img src={prop("coin_won")} style={{ display: "block", width: d, height: d }} />
);
export const MoneyRainParams = z.object({
  n: num(42, 0, 150, 1, "지폐·동전 개수", "size"),
  coinRatio: num(0.35, 0, 1, 0.05, "동전 비율", "look"),
  speed: num(1, 0, 4, 0.05, "낙하 속도(배)", "motion", "배"),
  billSize: num(170, 40, 400, 5, "지폐 크기", "size", "px"),
  coinSize: num(70, 20, 200, 2, "동전 크기", "size", "px"),
  sway: num(40, 0, 200, 2, "좌우 흔들림", "motion", "px"),
  spin: num(1, 0, 5, 0.1, "회전 속도(배)", "motion", "배"),
  flipSpeed: num(1, 0, 5, 0.1, "뒤집힘 속도(배)", "motion", "배"),
  tumble: num(0.45, 0, 1, 0.05, "지폐 3D 텀블 세기", "motion"),
  farBlur: num(1.5, 0, 8, 0.1, "먼 것 블러", "look", "px"),
  shadow: num(0.25, 0, 1, 0.05, "그림자 진하기", "look"),
});
export type MoneyRainP = z.infer<typeof MoneyRainParams>;
export const MoneyRain: React.FC<{ n?: number; coinRatio?: number; speed?: number; seed?: string; at?: number; p?: Partial<MoneyRainP> }> = ({ n, coinRatio, speed, seed = "money", at = 0, p }) => {
  const P = def(MoneyRainParams, { ...pk({ n, coinRatio, speed }), ...p });
  const f = useCurrentFrame() - at;
  if (f < 0) return null;
  return (
    <AbsoluteFill style={{ pointerEvents: "none", overflow: "hidden" }}>
      {Array.from({ length: Math.round(P.n) }).map((_, i) => {
        const k = `${seed}${i}`;
        const coin = R(k + "c") < P.coinRatio;
        const depth = 0.55 + R(k + "d") * 0.75;
        const size = (coin ? P.coinSize : P.billSize) * depth;
        const period = H + 360;
        const v = (5 + R(k + "v") * 5) * depth * P.speed;
        const y = wrap(f * v + R(k + "o") * period, period) - 220;
        const x = R(k + "x") * (W + 100) - 50 + P.sway * Math.sin(f / (18 + R(k + "s") * 14) + i);
        const rot = R(k + "r") * 360 + f * P.spin * (coin ? 1.5 : 2 + R(k + "rv") * 3) * (i % 2 ? 1 : -1);
        const flip = Math.cos((f * P.flipSpeed) / (coin ? 5 + R(k + "f") * 5 : 12 + R(k + "f") * 10) + i * 1.7);
        const tilt = coin ? 1 : 1 - P.tumble + P.tumble * Math.abs(Math.cos((f * P.flipSpeed) / 15 + i)); // 지폐 3D 텀블(세로 압축)
        return (
          <div key={i} style={{ position: "absolute", left: x, top: y, transform: `translate(-50%,-50%) rotate(${rot}deg) scale(${flip}, ${tilt})`, filter: `${depth < 0.75 && P.farBlur > 0 ? `blur(${P.farBlur}px) ` : ""}drop-shadow(0 6px 6px rgba(0,0,0,${P.shadow}))`, zIndex: Math.round(depth * 100) }}>
            {coin ? <Coin d={size} /> : <Bill w={size} />}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// ══ 3. CodeScroll ═══════════════════════════════════════════════════════════
// 네이비 #1A2560 위에 옅은 연두 코드 줄이 대각선으로 천천히 흐른다(타일 루프).
const CODE_TOK = [
  "const data = await fetch(url);", "if (user.id !== null) {", "  return render(view);", "}", "for (let i = 0; i < n; i++) {",
  "  sum += arr[i] * 0.5;", "function update(state) {", "import { api } from './core';", "let x = Math.floor(y / 2);",
  "while (queue.length) {", "  node = queue.shift();", "export default App;", "try { save(db) } catch (e) {}", "  log('ok', ts);",
  "const key = hash(token);", "switch (mode) {", "  case 1: break;", "obj.map((v) => v + 1);", "0x3F 0xBF 0x3F 0xFF", "return new Promise(res);",
];
export const CodeScrollParams = z.object({
  vx: num(-0.9, -8, 8, 0.05, "가로 흐름 속도", "motion", "px/f"),
  vy: num(-0.55, -8, 8, 0.05, "세로 흐름 속도", "motion", "px/f"),
  size: num(24, 10, 60, 1, "글자 크기", "size", "px"),
  lineGap: num(1.7, 1, 3, 0.05, "줄 간격(배)", "size", "배"),
  brightRatio: num(0.08, 0, 1, 0.01, "강조 줄 비율", "look"),
  brightAlpha: num(0.42, 0, 1, 0.01, "강조 줄 불투명도", "look"),
  vignette: num(0.55, 0, 1, 0.05, "비네트 세기", "look"),
  bg: col("#1A2560", "배경색"),
  color: col("rgba(170,240,170,0.2)", "코드 글자 색"),
});
export type CodeScrollP = z.infer<typeof CodeScrollParams>;
export const CodeScroll: React.FC<{ bg?: string; color?: string; vx?: number; vy?: number; size?: number; seed?: string; p?: Partial<CodeScrollP> }> = ({ bg: bg0, color: color0, vx: vx0, vy: vy0, size: size0, seed = "code", p }) => {
  const P = def(CodeScrollParams, { ...pk({ bg: bg0, color: color0, vx: vx0, vy: vy0, size: size0 }), ...p });
  const { bg, color, vx, vy, size } = P;
  const f = useCurrentFrame();
  const TW = 820, lines = 28, lh = size * P.lineGap, TH = lines * lh;
  const ox = f * vx, oy = f * vy;
  // 강조 줄: 코드 색(rgba)의 알파만 바꾼다(rgba 가 아니면 강조 없음)
  const isRgba = /rgba\(/.test(color);
  const brightColor = isRgba ? color.replace(/[\d.]+\)$/, `${P.brightAlpha})`) : color;
  const bx = Math.floor(-ox / TW), by = Math.floor(-oy / TH);
  const sx = wrap(ox, TW) - TW, sy = wrap(oy, TH) - TH;
  const tiles: React.ReactNode[] = [];
  for (let ty = 0; ty < Math.ceil(H / TH) + 2; ty++)
    for (let tx = 0; tx < Math.ceil(W / TW) + 2; tx++) {
      const id = `${tx + bx}_${ty + by}`;
      tiles.push(
        <div key={`${tx}-${ty}`} style={{ position: "absolute", left: sx + tx * TW, top: sy + ty * TH, width: TW, height: TH, paddingLeft: 30 }}>
          {Array.from({ length: lines }).map((_, l) => {
            const ind = Math.floor(R(`${seed}${id}i${l}`) * 3) * 2;
            const bright = R(`${seed}${id}b${l}`) < P.brightRatio;
            return <div key={l} style={{ height: lh, whiteSpace: "pre", color: bright ? brightColor : color }}>{" ".repeat(ind) + CODE_TOK[Math.floor(R(`${seed}${id}t${l}`) * CODE_TOK.length)]}</div>;
          })}
        </div>,
      );
    }
  return (
    <AbsoluteFill style={{ background: bg, overflow: "hidden" }}>
      <AbsoluteFill style={{ fontFamily: "Menlo, 'Courier New', monospace", fontSize: size }}>{tiles}</AbsoluteFill>
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 50%, transparent 45%, rgba(8,12,40,${P.vignette}) 100%)` }} />
    </AbsoluteFill>
  );
};

// ══ 4. BokehDrift ═══════════════════════════════════════════════════════════
// 부드러운 컬러 원(Ø60~250) 위로 ~10px/s 상승, 알파 0.3↔0.7 약 2초 주기.
export const BokehDriftParams = z.object({
  n: num(26, 0, 90, 1, "보케 개수", "size"),
  pxPerSec: num(10, -150, 150, 1, "상승 속도", "motion", "px/s"),
  wander: num(14, 0, 80, 1, "좌우 흔들림", "motion", "px"),
  period: num(60, 6, 300, 1, "밝기 깜빡임 주기", "timing", "f"),
  minD: num(60, 10, 400, 2, "최소 지름", "size", "px"),
  maxD: num(250, 10, 600, 2, "최대 지름", "size", "px"),
  alpha: num(0.5, 0, 1, 0.05, "평균 불투명도", "look"),
  alphaAmp: num(0.2, 0, 0.5, 0.01, "깜빡임 폭", "look"),
  blur: num(1, 0, 4, 0.05, "블러(배)", "look", "배"),
  bg: col("#1E2442", "배경색"),
});
export type BokehDriftP = z.infer<typeof BokehDriftParams>;
export const BokehDrift: React.FC<{ bg?: string; colors?: string[]; n?: number; pxPerSec?: number; period?: number; seed?: string; p?: Partial<BokehDriftP> }> = ({ bg, colors = ["255,214,90", "255,140,190", "110,170,255", "70,215,200"], n, pxPerSec, period, seed = "bokeh", p }) => {
  const P = def(BokehDriftParams, { ...pk({ bg, n, pxPerSec, period }), ...p });
  const f = useCurrentFrame();
  const per = Math.max(1, P.period);
  return (
    <AbsoluteFill style={{ background: P.bg, overflow: "hidden" }}>
      {Array.from({ length: Math.round(P.n) }).map((_, i) => {
        const k = `${seed}${i}`;
        const d = Math.max(1, P.minD + R(k + "d") * (P.maxD - P.minD));
        const span = H + 300;
        const y = wrap(R(k + "y") * span - (f * P.pxPerSec * (0.7 + R(k + "v") * 0.6)) / FPS, span) - 150;
        const x = R(k + "x") * W + P.wander * Math.sin(f / 40 + i);
        const a = P.alpha + P.alphaAmp * Math.sin((2 * Math.PI * f) / (per * (0.85 + R(k + "p") * 0.3)) + R(k + "ph") * 6.28);
        const c = colors[i % colors.length];
        return <div key={i} style={{ position: "absolute", left: x - d / 2, top: y - d / 2, width: d, height: d, borderRadius: "50%", opacity: a, background: `radial-gradient(circle, rgba(${c},0.95) 0%, rgba(${c},0.8) 52%, rgba(${c},0) 72%)`, filter: `blur(${(2 + d * 0.035) * P.blur}px)`, mixBlendMode: "screen" }} />;
      })}
    </AbsoluteFill>
  );
};

// ══ 5. SpotlightCone ════════════════════════════════════════════════════════
// 위에서 떨어지는 단일 원뿔 조명(부드러운 가장자리) + 바닥 풀 + 떠다니는 트윙클. fog=true 면 하단 흰 안개 띠가 흐른다.
export const SpotlightConeParams = z.object({
  topW: num(130, 0, 900, 5, "빛 위쪽 폭", "size", "px"),
  botW: num(760, 50, 1900, 10, "빛 바닥 폭", "size", "px"),
  beamBlur: num(22, 0, 80, 1, "빛 가장자리 번짐", "look", "px"),
  beamTop: num(0.62, 0, 1, 0.02, "빛 위쪽 밝기", "look"),
  beamBottom: num(0.16, 0, 1, 0.02, "빛 아래쪽 밝기", "look"),
  pool: num(0.35, 0, 1, 0.05, "바닥 빛 웅덩이 밝기", "look"),
  breatheAmt: num(0.08, 0, 0.5, 0.01, "숨쉬기 세기", "motion"),
  breatheSlow: num(14, 1, 60, 1, "숨쉬기 느리기(클수록 느림)", "timing", "f"),
  sparkles: num(34, 0, 120, 1, "반짝이 개수", "size"),
  sparkleSize: num(1, 0.2, 4, 0.05, "반짝이 크기(배)", "size", "배"),
  sparkleRise: num(1, 0, 6, 0.1, "반짝이 상승 속도(배)", "motion", "배"),
  fog: flag(false, "바닥 안개", "look"),
  fogOpacity: num(0.55, 0, 1, 0.05, "안개 진하기", "look"),
  fogSpeed: num(1, 0, 6, 0.1, "안개 흐름 속도(배)", "motion", "배"),
  bg: col("#15121E", "배경색"),
});
export type SpotlightConeP = z.infer<typeof SpotlightConeParams>;
export const SpotlightCone: React.FC<{ x?: number; floorY?: number; topW?: number; botW?: number; bg?: string; color?: string; sparkles?: number; fog?: boolean; id?: string; children?: React.ReactNode; p?: Partial<SpotlightConeP> }> = ({ x = W / 2, floorY = 900, topW: topW0, botW: botW0, bg: bg0, color = "255,248,225", sparkles: sparkles0, fog: fog0, id = "spot", children, p }) => {
  const P = def(SpotlightConeParams, { ...pk({ topW: topW0, botW: botW0, bg: bg0, sparkles: sparkles0, fog: fog0 }), ...p });
  const { topW, botW, bg, fog } = P;
  const sparkles = Math.round(P.sparkles);
  const f = useCurrentFrame();
  const breathe = 1 - P.breatheAmt + P.breatheAmt * Math.sin(f / Math.max(0.5, P.breatheSlow));
  const poly = `${x - topW / 2},-40 ${x + topW / 2},-40 ${x + botW / 2},${floorY} ${x - botW / 2},${floorY}`;
  return (
    <AbsoluteFill style={{ background: `radial-gradient(ellipse at ${x}px ${floorY}px, #2a2438 0%, ${bg} 60%)`, overflow: "hidden" }}>
      <svg width={W} height={H} style={{ position: "absolute" }}>
        <defs>
          <filter id={`${id}-b`} x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation={P.beamBlur} /></filter>
          <linearGradient id={`${id}-g`} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={`rgb(${color})`} stopOpacity={P.beamTop} /><stop offset="1" stopColor={`rgb(${color})`} stopOpacity={P.beamBottom} /></linearGradient>
        </defs>
        <ellipse cx={x} cy={floorY} rx={botW * 0.55} ry={70} fill={`rgb(${color})`} opacity={P.pool * breathe} filter={`url(#${id}-b)`} />
      </svg>
      {children}
      <svg width={W} height={H} style={{ position: "absolute", mixBlendMode: "screen", opacity: breathe }}>
        <polygon points={poly} fill={`url(#${id}-g)`} filter={`url(#${id}-b)`} />
      </svg>
      {Array.from({ length: sparkles }).map((_, i) => {
        const k = `${id}sp${i}`;
        const u = R(k + "u");
        const yy = wrap(u * floorY - f * P.sparkleRise * (0.3 + R(k + "v") * 0.5), floorY);
        const half = (topW + (botW - topW) * (yy / floorY)) / 2;
        const xx = x + (R(k + "x") - 0.5) * 2 * half * 0.85 + 8 * Math.sin(f / 25 + i);
        const tw = Math.pow(Math.max(0, Math.sin(f / (5 + R(k + "t") * 9) + R(k + "p") * 6.28)), 3);
        const sz = (8 + R(k + "s") * 16) * P.sparkleSize;
        return <svg key={i} width={sz} height={sz} viewBox="-50 -50 100 100" style={{ position: "absolute", left: xx - sz / 2, top: yy - sz / 2, transform: `scale(${0.2 + tw}) rotate(${i * 20}deg)`, opacity: 0.25 + 0.75 * tw }}><path d={STAR4} fill={i % 3 ? "#fff" : "#FFE9A0"} /></svg>;
      })}
      {fog && <FogBand p={{ opacity: P.fogOpacity, speed: P.fogSpeed }} />}
    </AbsoluteFill>
  );
};
// 무대 안개: 하단 흰 안개 띠가 천천히 흐른다(3 레이어 패럴랙스, 루프)
export const FogBandParams = z.object({
  top: num(800, 300, 1080, 10, "안개 띠 높이(y)", "size", "px"),
  opacity: num(0.55, 0, 1, 0.05, "안개 진하기", "look"),
  speed: num(1, 0, 6, 0.1, "흐름 속도(배)", "motion", "배"),
  puffs: num(7, 1, 20, 1, "레이어당 안개 덩어리 수", "size"),
  blur: num(40, 0, 120, 2, "안개 블러", "look", "px"),
  floorGlow: num(0.35, 0, 1, 0.05, "바닥 흰빛 세기", "look"),
});
export type FogBandP = z.infer<typeof FogBandParams>;
export const FogBand: React.FC<{ top?: number; opacity?: number; speed?: number; seed?: string; p?: Partial<FogBandP> }> = ({ top: top0, opacity: op0, speed: sp0, seed = "fog", p }) => {
  const P = def(FogBandParams, { ...pk({ top: top0, opacity: op0, speed: sp0 }), ...p });
  const { top, opacity, speed } = P;
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ pointerEvents: "none", overflow: "hidden" }}>
      {[0, 1, 2].map((L) => {
        const v = (0.8 + L * 0.6) * speed;
        const span = W + 600;
        return Array.from({ length: Math.round(P.puffs) }).map((_, i) => {
          const k = `${seed}${L}-${i}`;
          const w = 500 + R(k + "w") * 500, h = 140 + R(k + "h") * 120;
          const xx = wrap(R(k + "x") * span + f * v, span) - 300;
          const yy = top + L * 60 + R(k + "y") * 80;
          return <div key={`${L}-${i}`} style={{ position: "absolute", left: xx - w / 2, top: yy, width: w, height: h, borderRadius: "50%", background: "rgba(255,255,255,0.9)", opacity: opacity * (0.45 + L * 0.2), filter: `blur(${P.blur}px)` }} />;
        });
      })}
      <div style={{ position: "absolute", left: 0, right: 0, top: top + 120, bottom: 0, background: `linear-gradient(rgba(255,255,255,0), rgba(255,255,255,${P.floorGlow}))` }} />
    </AbsoluteFill>
  );
};

// ══ 6. CrowdBokeh ═══════════════════════════════════════════════════════════
// 무대 보케 조명 + 하단 관객 실루엣(2열, 박자 들썩임, 일부 손 들고 폰 라이트)
export const CrowdBokehParams = z.object({
  bpm: num(120, 20, 240, 1, "박자(BPM)", "timing"),
  jump: num(1, 0, 5, 0.1, "관객 들썩임 세기(배)", "motion", "배"),
  sway: num(12, 0, 80, 1, "든 손 흔들림", "motion", "px"),
  armFront: num(0.25, 0, 1, 0.01, "손 든 비율(앞줄)", "motion"),
  armBack: num(0.22, 0, 1, 0.01, "손 든 비율(뒷줄)", "motion"),
  phone: num(0.6, 0, 1, 0.05, "폰 라이트 비율(손 든 사람 중)", "look"),
  lights: num(30, 0, 100, 1, "조명 보케 개수", "size"),
  lightMin: num(50, 10, 400, 2, "조명 최소 지름", "size", "px"),
  lightMax: num(250, 10, 600, 2, "조명 최대 지름", "size", "px"),
  lightBase: num(0.35, 0, 1, 0.05, "조명 기본 밝기", "look"),
  lightPulse: num(0.4, 0, 1, 0.05, "조명 박자 번쩍 폭", "look"),
  floorGlow: num(0.25, 0, 1, 0.05, "바닥 핑크 글로우", "look"),
});
export type CrowdBokehP = z.infer<typeof CrowdBokehParams>;
export const CrowdBokeh: React.FC<{ bg?: string; colors?: string[]; lights?: number; seed?: string; bpm?: number; p?: Partial<CrowdBokehP> }> = ({ bg = "linear-gradient(#2A0F3A 0%, #140820 60%, #07040c 100%)", colors = ["255,70,170", "80,200,255", "255,190,70", "170,110,255"], lights: lights0, seed = "crowd", bpm: bpm0, p }) => {
  const P = def(CrowdBokehParams, { ...pk({ lights: lights0, bpm: bpm0 }), ...p });
  const lights = Math.round(P.lights);
  const f = useCurrentFrame();
  const beat = (FPS * 60) / Math.max(1, P.bpm);
  // 관객: 세모지 뒷모습(crowd_back_a/b, 손 든 사람 = crowd_back_phone) — 역광이라 어둡게(뒷줄 조금 밝게). 머리 중심·반지름(px) 실측으로 배치
  const CROWD = { crowd_back_a: { w: 1211, h: 1177, hx: 605, hy: 330, hr: 272 }, crowd_back_b: { w: 1201, h: 1204, hx: 595, hy: 360, hr: 305 }, crowd_back_phone: { w: 960, h: 1215, hx: 468, hy: 480, hr: 215, px: 653, py: 128 } } as const;
  const row = (r: number) => {
    const n = r === 0 ? 26 : 19, sp = W / (n - 1), base = r === 0 ? 1000 : 1110, hr = r === 0 ? 30 : 42;
    return Array.from({ length: n }).map((_, i) => {
      const k = `${seed}r${r}h${i}`;
      const cx = i * sp + (R(k + "x") - 0.5) * sp * 0.5 - (r ? 0 : sp / 2);
      const ph = R(k + "p");
      const jump = Math.abs(Math.sin(Math.PI * (f / beat + ph))) * (r === 0 ? 5 : 8) * P.jump * (R(k + "j") < 0.6 ? 1 : 0.3);
      const hh = hr * (0.85 + R(k + "s") * 0.3);
      const cy = base - hh * 3.4 - jump;
      const arm = R(k + "a") < (r === 0 ? P.armFront : P.armBack);
      const sway = P.sway * Math.sin(f / (beat * 1.0) * Math.PI + ph * 6);
      const side = R(k + "sd") < 0.5 ? -1 : 1;
      const id = arm ? "crowd_back_phone" : R(k + "v") < 0.5 ? "crowd_back_a" : "crowd_back_b";
      const c = CROWD[id], sc = (hh * 1.25) / c.hr, iw = c.w * sc, ih = c.h * sc;
      const x0 = cx - c.hx * sc, y0 = cy - c.hy * sc;
      const flipX = side < 0 ? -1 : 1; // 폰 든 손 방향 = side
      const rot = arm && P.sway > 0 ? (sway / P.sway) * 5 : 0;
      const lit = arm && "px" in c && R(k + "ph") < P.phone;
      return (
        <div key={`${r}-${i}`} style={{ position: "absolute", left: x0, top: y0, width: iw, height: Math.max(ih, H - y0), transformOrigin: `${c.hx * sc}px ${ih}px`, transform: `scaleX(${flipX}) rotate(${rot}deg)` }}>
          <Img src={prop(id)} style={{ position: "absolute", left: 0, top: 0, width: iw, height: ih, filter: `brightness(${r === 0 ? 0.3 : 0.14}) saturate(0.6)` }} />
          <div style={{ position: "absolute", left: iw * 0.03, top: ih - 2, width: iw * 0.94, height: Math.max(0, H - y0 - ih + 2), background: r === 0 ? "#1B1228" : "#060409" }} />
          {lit && "px" in c && <div style={{ position: "absolute", left: (c.px - 58) * sc, top: (c.py - 105) * sc, width: 116 * sc, height: 210 * sc, borderRadius: 12 * sc, background: "#fff", boxShadow: "0 0 8px #fff, 0 0 18px rgba(255,255,255,0.8)" }} />}
        </div>
      );
    });
  };
  return (
    <AbsoluteFill style={{ background: bg, overflow: "hidden" }}>
      {Array.from({ length: lights }).map((_, i) => {
        const k = `${seed}L${i}`;
        const d = Math.max(1, P.lightMin + R(k + "d") * (P.lightMax - P.lightMin));
        const x = R(k + "x") * W, y = 80 + R(k + "y") * 620;
        const a = P.lightBase + P.lightPulse * Math.max(0, Math.sin((2 * Math.PI * f) / (beat * (2 + Math.floor(R(k + "b") * 3))) + R(k + "p") * 6.28));
        const c = colors[i % colors.length];
        return <div key={i} style={{ position: "absolute", left: x - d / 2, top: y - d / 2, width: d, height: d, borderRadius: "50%", opacity: a, mixBlendMode: "screen", background: `radial-gradient(circle, rgba(${c},0.9) 0%, rgba(${c},0.75) 50%, rgba(${c},0) 72%)`, filter: `blur(${3 + d * 0.03}px)` }} />;
      })}
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 100%, rgba(255,120,200,${P.floorGlow}) 0%, transparent 55%)` }} />
      {row(0)}{row(1)}
    </AbsoluteFill>
  );
};

// ══ 7. CloudDrift ═══════════════════════════════════════════════════════════
// 하늘색 배경 + 플랫 흰 구름 좌→우 ~5px/s (깊이별 0.6~1.4배)
const CloudShape: React.FC<{ w: number; seed: string; fill?: string; shade?: string }> = ({ w, seed, fill = "#fff", shade = "#E4F3FC" }) => {
  const nb = 3 + Math.floor(R(seed + "n") * 3);
  const h = w * 0.45;
  const bumps = Array.from({ length: nb }).map((_, i) => {
    const t = (i + 0.5) / nb;
    const r = (w / nb) * (0.62 + R(`${seed}r${i}`) * 0.45) * (1 - Math.abs(t - 0.5) * 0.6);
    return { cx: w * (0.12 + t * 0.76), r };
  });
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} style={{ overflow: "visible" }}>
      <g fill={shade} transform={`translate(0,${h * 0.06})`}>
        {bumps.map((b, i) => <circle key={i} cx={b.cx} cy={h * 0.78 - b.r * 0.55} r={b.r} />)}
        <rect x={w * 0.05} y={h * 0.55} width={w * 0.9} height={h * 0.3} rx={h * 0.15} />
      </g>
      <g fill={fill}>
        {bumps.map((b, i) => <circle key={i} cx={b.cx} cy={h * 0.78 - b.r * 0.55} r={b.r} />)}
        <rect x={w * 0.05} y={h * 0.55} width={w * 0.9} height={h * 0.3} rx={h * 0.15} />
      </g>
    </svg>
  );
};
export const CloudDriftParams = z.object({
  pxPerSec: num(5, -300, 300, 1, "흐름 속도", "motion", "px/s"),
  parallax: num(1, 0, 3, 0.05, "깊이별 속도 차(배)", "motion", "배"),
  n: num(9, 0, 30, 1, "구름 개수", "size"),
  scale: num(1, 0.3, 3, 0.05, "구름 크기(배)", "size", "배"),
  yRange: num(560, 0, 1000, 10, "구름 높이 분포 폭", "size", "px"),
  opacity: num(0.75, 0, 1, 0.05, "구름 불투명도(먼 구름)", "look"),
  fill: col("#fff", "구름 색"),
  shade: col("#E4F3FC", "구름 그림자 색"),
});
export type CloudDriftP = z.infer<typeof CloudDriftParams>;
export const CloudDrift: React.FC<{ sky?: string; pxPerSec?: number; n?: number; seed?: string; children?: React.ReactNode; p?: Partial<CloudDriftP> }> = ({ sky = "linear-gradient(#6EC1EE 0%, #A9DCF7 70%, #CBEBFB 100%)", pxPerSec, n, seed = "cloud", children, p }) => {
  const P = def(CloudDriftParams, { ...pk({ pxPerSec, n }), ...p });
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: sky, overflow: "hidden" }}>
      {Array.from({ length: Math.round(P.n) }).map((_, i) => {
        const k = `${seed}${i}`;
        const depth = 0.6 + R(k + "d") * 0.8;
        const w = (180 + depth * 260) * P.scale;
        const span = W + w + 200;
        const vDepth = 1 + (depth - 1) * P.parallax; // parallax=1 → depth 그대로
        const x = wrap(R(k + "x") * span + (f * P.pxPerSec * (P.parallax === 1 ? depth : vDepth)) / FPS, span) - w - 100;
        const y = 40 + R(k + "y") * P.yRange;
        return <div key={i} style={{ position: "absolute", left: x, top: y, opacity: Math.min(1, P.opacity + depth * 0.18), zIndex: Math.round(depth * 10) }}><CloudShape w={w} seed={k} fill={P.fill} shade={P.shade} /></div>;
      })}
      {children}
    </AbsoluteFill>
  );
};

// ══ 8. BlurFillPhoto ════════════════════════════════════════════════════════
// 16:9 가 아닌 이미지: 같은 이미지 1.3x + blur 30 + brightness .85 로 화면을 채우고 원본은 중앙(88% 폭 또는 맞춤).
// kenBurns: 전체 1.05→1.0 (4s linear). text: 2줄 굵은 검정 + 흰 8px 외곽 + 그림자.
export const BlurFillPhotoParams = z.object({
  widthPct: num(0.88, 0.2, 1, 0.01, "사진 폭(화면 대비)", "size"),
  maxHPct: num(0.9, 0.2, 1, 0.01, "사진 최대 높이(화면 대비)", "size"),
  kenBurns: flag(true, "켄번즈 줌", "motion"),
  kbFrom: num(1.05, 0.8, 1.5, 0.01, "켄번즈 시작 크기(배)", "motion", "배"),
  kbFrames: num(120, 1, 600, 1, "켄번즈 길이", "timing", "f"),
  pop: flag(false, "사진 팝 등장", "motion"),
  textDelay: num(6, 0, 60, 1, "글자 등장 지연", "timing", "f"),
  textSize: num(92, 30, 200, 2, "글자 크기", "size", "px"),
  bgScale: num(1.3, 1, 2, 0.05, "배경 확대(배)", "size", "배"),
  bgBlur: num(30, 0, 100, 1, "배경 블러", "look", "px"),
  bgBright: num(0.85, 0, 1.5, 0.05, "배경 밝기", "look"),
  shadow: num(0.45, 0, 1, 0.05, "사진 그림자 진하기", "look"),
});
export type BlurFillPhotoP = z.infer<typeof BlurFillPhotoParams>;
export const BlurFillPhoto: React.FC<{ img: string; ar?: number; widthPct?: number; maxHPct?: number; kenBurns?: boolean; kbFrames?: number; text?: [string, string?]; textY?: number; textSize?: number; at?: number; pop?: boolean; pos?: string; p?: Partial<BlurFillPhotoP> }> = ({ img, ar = 4 / 3, widthPct: wp0, maxHPct: mh0, kenBurns: kb0, kbFrames: kbf0, text, textY = 620, textSize: ts0, at = 0, pop: pop0, pos = "50% 50%", p }) => {
  const P = def(BlurFillPhotoParams, { ...pk({ widthPct: wp0, maxHPct: mh0, kenBurns: kb0, kbFrames: kbf0, textSize: ts0, pop: pop0 }), ...p });
  const f = useCurrentFrame();
  let w = W * P.widthPct, h = w / ar;
  if (h > H * P.maxHPct) { h = H * P.maxHPct; w = h * ar; }
  const kb = P.kenBurns ? interpolate(f - at, [0, Math.max(1, P.kbFrames)], [P.kbFrom, 1.0], CL) : 1;
  const pp = P.pop ? photoPop(f, at) : { s: 1, blur: 0 };
  return (
    <AbsoluteFill style={{ overflow: "hidden", background: "#000" }}>
      <AbsoluteFill style={{ transform: `scale(${kb})` }}>
        <Img src={src(img)} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", transform: `scale(${P.bgScale})`, filter: `blur(${P.bgBlur}px) brightness(${P.bgBright})` }} />
        <div style={{ position: "absolute", left: (W - w) / 2, top: (H - h) / 2, width: w, height: h, transform: `scale(${pp.s})`, filter: `blur(${pp.blur}px)`, boxShadow: `0 12px 40px rgba(0,0,0,${P.shadow})` }}>
          <Img src={src(img)} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: pos }} />
        </div>
      </AbsoluteFill>
      {text && <OutlineText lines={text} y={textY} size={P.textSize} at={at + P.textDelay} />}
    </AbsoluteFill>
  );
};
// 2줄 굵은 검정 텍스트 + 흰 8px 외곽 + 그림자 (textPop 등장)
// 팝 곡선 1.25→1.15→1.08→1.0 @ [0,2,5,7]f 를 "시작 크기"·"길이"로 재구성(기본값에서 같은 곡선)
export const OutlineTextParams = z.object({
  popDur: num(7, 1, 30, 1, "팝 길이", "timing", "f"),
  startScale: num(1.25, 0.3, 3, 0.05, "시작 크기(배)", "motion", "배"),
  fadeDur: num(2, 0, 15, 1, "나타나는 시간", "timing", "f"),
  fadeFrom: num(0.4, 0, 1, 0.05, "처음 불투명도", "look"),
  size: num(92, 30, 200, 2, "글자 크기", "size", "px"),
  strokeW: num(16, 0, 40, 1, "외곽선 두께", "size", "px"),
  shadow: num(0.45, 0, 1, 0.05, "그림자 진하기", "look"),
  color: col("#111", "글자 색"),
  stroke: col("#fff", "외곽선 색"),
});
export type OutlineTextP = z.infer<typeof OutlineTextParams>;
export const OutlineText: React.FC<{ lines: (string | undefined)[]; y: number; size?: number; at?: number; color?: string; stroke?: string; p?: Partial<OutlineTextP> }> = ({ lines, y, size: size0, at = 0, color: color0, stroke: stroke0, p }) => {
  const P = def(OutlineTextParams, { ...pk({ size: size0, color: color0, stroke: stroke0 }), ...p });
  const { size, color, stroke } = P;
  const f = useCurrentFrame();
  if (f < at) return null;
  const D = Math.max(1, P.popDur), ex = P.startScale - 1;
  const s = D === 7 && P.startScale === 1.25 ? kf(f, at, [0, 2, 5, 7], [1.25, 1.15, 1.08, 1.0]) : kf(f, at, [0, (2 * D) / 7, (5 * D) / 7, D], [P.startScale, 1 + ex * 0.6, 1 + ex * 0.32, 1.0]);
  const op = P.fadeDur > 0 ? kf(f, at, [0, P.fadeDur], [P.fadeFrom, 1]) : 1;
  return (
    <div style={{ position: "absolute", left: 0, right: 0, top: y, textAlign: "center", transform: `scale(${s})`, opacity: op, fontFamily: "NeoHv", fontSize: size, lineHeight: 1.18, color, WebkitTextStroke: `${P.strokeW}px ${stroke}`, paintOrder: "stroke fill", filter: `drop-shadow(0 6px 8px rgba(0,0,0,${P.shadow}))`, letterSpacing: -1 }}>
      {lines.filter(Boolean).map((l, i) => <div key={i}>{l}</div>)}
    </div>
  );
};

// ══ 9. Pillarbox ════════════════════════════════════════════════════════════
// 4:3 아카이브 영상/사진을 중앙에, 좌우 검정 바. 우하단 출처 칩(자막 띠 바로 위).
export const PillarboxParams = z.object({
  archive: flag(false, "아카이브 필름 룩", "look"),
  flicker: num(0.035, 0, 0.3, 0.005, "필름 밝기 깜빡임", "look"),
  sepia: num(0.25, 0, 1, 0.05, "세피아", "look"),
  contrast: num(1.1, 0.5, 2, 0.05, "대비", "look"),
  vignette: num(0.5, 0, 1, 0.05, "비네트 세기", "look"),
  kenBurns: flag(false, "켄번즈 줌", "motion"),
  kbTo: num(1.06, 0.8, 1.5, 0.01, "켄번즈 끝 크기(배)", "motion", "배"),
  kbFrames: num(150, 1, 600, 1, "켄번즈 길이", "timing", "f"),
  barColor: col("#000", "좌우 바 색"),
});
export type PillarboxP = z.infer<typeof PillarboxParams>;
export const Pillarbox: React.FC<{ img: string; source?: string; ar?: number; archive?: boolean; kenBurns?: boolean; pos?: string; p?: Partial<PillarboxP> }> = ({ img, source, ar = 4 / 3, archive: ar0, kenBurns: kb0, pos = "50% 50%", p }) => {
  const P = def(PillarboxParams, { ...pk({ archive: ar0, kenBurns: kb0 }), ...p });
  const { archive, kenBurns } = P;
  const f = useCurrentFrame();
  const w = H * ar;
  const flick = archive ? 1 + P.flicker * (R(`pb${f}`) - 0.5) * 2 : 1;
  const kb = kenBurns ? interpolate(f, [0, Math.max(1, P.kbFrames)], [1.0, P.kbTo], CL) : 1;
  return (
    <AbsoluteFill style={{ background: P.barColor }}>
      <div style={{ position: "absolute", left: (W - w) / 2, top: 0, width: w, height: H, overflow: "hidden" }}>
        <Img src={src(img)} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: pos, transform: `scale(${kb})`, filter: archive ? `grayscale(1) sepia(${P.sepia}) contrast(${P.contrast}) brightness(${flick})` : undefined }} />
        {archive && <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 50%, transparent 55%, rgba(0,0,0,${P.vignette}) 100%)` }} />}
      </div>
      {source && <SourceChip text={source} />}
    </AbsoluteFill>
  );
};

// ══ 10. CaptureScroll ═══════════════════════════════════════════════════════
// 크림 종이 위 웹/채널 페이지 캡처: 0.3s 홀드 → ease-in 으로 등속 ~9px/f 까지 가속하며 위로 스크롤.
// 새로 들어오는 줄의 썸네일은 blur→sharp.
export type CaptureItem = { img: string; title: string; meta?: string };
export const CaptureScrollParams = z.object({
  hold: num(9, 0, 90, 1, "스크롤 전 정지", "timing", "f"),
  ramp: num(18, 0, 90, 1, "가속 구간", "timing", "f"),
  vmax: num(9, 0, 40, 0.5, "최고 스크롤 속도", "motion", "px/f"),
  cols: num(4, 1, 8, 1, "썸네일 열 수", "size"),
  pageW: num(1500, 800, 1900, 10, "페이지 폭", "size", "px"),
  radius: num(18, 0, 60, 1, "페이지 모서리 둥글기", "size", "px"),
  thumbBlur: num(14, 0, 40, 1, "새 줄 썸네일 블러", "look", "px"),
  shadow: num(0.25, 0, 1, 0.05, "페이지 그림자 진하기", "look"),
  bg: col("#F3ECDD", "종이 배경색"),
});
export type CaptureScrollP = z.infer<typeof CaptureScrollParams>;
export const CaptureScroll: React.FC<{ items: CaptureItem[]; channel?: string; handle?: string; avatar?: string; bg?: string; hold?: number; ramp?: number; vmax?: number; cols?: number; p?: Partial<CaptureScrollP> }> = ({ items, channel = "세모지", handle = "@semoji · 구독자 52만명", avatar, bg: bg0, hold: hold0, ramp: ramp0, vmax: vmax0, cols: cols0, p }) => {
  const P = def(CaptureScrollParams, { ...pk({ bg: bg0, hold: hold0, ramp: ramp0, vmax: vmax0, cols: cols0 }), ...p });
  const { bg, hold, ramp, vmax } = P;
  const cols = Math.max(1, Math.round(P.cols));
  const f = useCurrentFrame();
  const t = Math.max(0, f - hold);
  const scroll = t < ramp ? (vmax * t * t) / (2 * ramp) : (vmax * ramp) / 2 + vmax * (t - ramp);
  const PW = P.pageW, px = (W - PW) / 2, pad = 40, gap = 26;
  const tw = (PW - pad * 2 - gap * (cols - 1)) / cols, th = tw * 9 / 16, rowH = th + 110;
  const headerH = 300;
  const rows = Math.ceil(items.length / cols);
  const pageTop = 70 - scroll;
  return (
    <AbsoluteFill style={{ background: bg, overflow: "hidden" }}>
      <div style={{ position: "absolute", left: px, top: pageTop, width: PW, height: headerH + rows * rowH + 60, background: "#fff", borderRadius: P.radius, boxShadow: `0 16px 50px rgba(80,60,30,${P.shadow})`, overflow: "hidden" }}>
        {/* 브라우저 바 */}
        <div style={{ height: 56, background: "#EFEFEF", display: "flex", alignItems: "center", gap: 10, padding: "0 20px" }}>
          {["#FF5F57", "#FEBC2E", "#28C840"].map((c) => <div key={c} style={{ width: 16, height: 16, borderRadius: 8, background: c }} />)}
          <div style={{ marginLeft: 20, flex: 1, height: 34, borderRadius: 17, background: "#fff", fontFamily: "NeoEb", fontSize: 18, color: "#777", display: "flex", alignItems: "center", paddingLeft: 20 }}>youtube.com/@semoji/videos</div>
        </div>
        {/* 채널 헤더 */}
        <div style={{ height: 244 - 56, display: "flex", alignItems: "center", gap: 28, padding: "0 40px", borderBottom: "2px solid #eee" }}>
          <div style={{ width: 120, height: 120, borderRadius: 60, overflow: "hidden", background: "#E5532A", flexShrink: 0 }}>{avatar && <Img src={src(avatar)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />}</div>
          <div>
            <div style={{ fontFamily: "NeoHv", fontSize: 44, color: "#111" }}>{channel}</div>
            <div style={{ fontFamily: "NeoEb", fontSize: 22, color: "#666", marginTop: 6 }}>{handle}</div>
          </div>
          <div style={{ marginLeft: "auto", background: "#111", color: "#fff", fontFamily: "NeoEb", fontSize: 24, padding: "12px 28px", borderRadius: 30 }}>구독</div>
        </div>
        <div style={{ height: 56, display: "flex", gap: 40, padding: "0 40px", alignItems: "center", fontFamily: "NeoEb", fontSize: 22, color: "#666" }}>
          {["홈", "동영상", "Shorts", "재생목록", "커뮤니티"].map((x) => <div key={x} style={{ color: x === "동영상" ? "#111" : undefined, borderBottom: x === "동영상" ? "3px solid #111" : undefined, paddingBottom: 6 }}>{x}</div>)}
        </div>
        {items.map((it, i) => {
          const r = Math.floor(i / cols), c = i % cols;
          const top = headerH + r * rowH;
          const screenY = pageTop + top;
          const initiallyVisible = 70 + top < H - 260;
          const blur = initiallyVisible ? 0 : interpolate(screenY, [H - 300, H - 40], [0, P.thumbBlur], CL);
          return (
            <div key={i} style={{ position: "absolute", left: pad + c * (tw + gap), top, width: tw }}>
              <div style={{ width: tw, height: th, borderRadius: 12, overflow: "hidden", background: "#ddd" }}>
                <Img src={src(it.img)} style={{ width: "100%", height: "100%", objectFit: "cover", filter: blur > 0.3 ? `blur(${blur}px)` : undefined, transform: blur > 0.3 ? "scale(1.06)" : undefined }} />
              </div>
              <div style={{ fontFamily: "NeoHv", fontSize: 24, color: "#111", marginTop: 12, lineHeight: 1.25, height: 60, overflow: "hidden" }}>{it.title}</div>
              <div style={{ fontFamily: "NeoEb", fontSize: 18, color: "#777", marginTop: 4 }}>{it.meta ?? `조회수 ${10 + Math.floor(R("cv" + i) * 190)}만회 · ${1 + Math.floor(R("cm" + i) * 11)}개월 전`}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ══ 11. PixelateAvatar ══════════════════════════════════════════════════════
// 원형 사진 Ø280, 모자이크(~16px 블록: 작은 크기로 렌더 → image-rendering:pixelated 로 확대),
// 한쪽 절반 RGB 분리, 사진 팝 등장, 인증 배지 + 라벨 칩.
export const PixelateAvatarParams = z.object({
  d: num(280, 80, 700, 2, "사진 지름", "size", "px"),
  block: num(16, 2, 120, 1, "모자이크 블록 크기", "size", "px"),
  split: choice("right", ["left", "right", "none"] as const, "RGB 분리 쪽", "look"),
  splitPx: num(9, 0, 60, 1, "RGB 분리 거리", "motion", "px"),
  jitterEvery: num(3, 1, 30, 1, "RGB 떨림 주기", "timing", "f"),
  jitterAmt: num(0.4, 0, 1.5, 0.05, "RGB 떨림 세기", "motion"),
  border: num(8, 0, 30, 1, "흰 테두리 두께", "size", "px"),
  verified: flag(true, "인증 배지", "look"),
  badgeDelay: num(5, 0, 40, 1, "배지 등장 지연", "timing", "f"),
  labelDelay: num(6, 0, 40, 1, "라벨 등장 지연", "timing", "f"),
});
export type PixelateAvatarP = z.infer<typeof PixelateAvatarParams>;
export const PixelateAvatar: React.FC<{ img: string; x: number; y: number; at?: number; d?: number; block?: number; split?: "left" | "right" | "none"; splitPx?: number; verified?: boolean; label?: string; pos?: string; id?: string; p?: Partial<PixelateAvatarP> }> = ({ img, x, y, at = 0, d: d0, block: block0, split: split0, splitPx: sp0, verified: ver0, label, pos = "50% 50%", id = "pxa", p }) => {
  const P = def(PixelateAvatarParams, { ...pk({ d: d0, block: block0, split: split0, splitPx: sp0, verified: ver0 }), ...p });
  const { d, block, split, splitPx, verified } = P;
  const bd = P.border;
  const f = useCurrentFrame();
  if (f < at) return null;
  const { s, blur } = photoPop(f, at);
  const n = Math.max(2, Math.round(d / Math.max(1, block)));
  const jit = split !== "none" ? splitPx * (1 - P.jitterAmt / 2 + P.jitterAmt * R(`${id}j${Math.floor(f / Math.max(1, P.jitterEvery))}`)) : 0;
  // 모자이크: canvas 없이 SVG 필터로 — 블록마다 중앙 1점만 샘플(feFlood+feTile) → dilate 로 블록 채움.
  // (작게 렌더 후 image-rendering:pixelated 확대는 Chrome 이 transform 시 원본에서 직접 리샘플해 모자이크가 안 생김 → 폐기)
  const b = Math.max(4, Math.round(d / n));
  const mosaic = () => (
    <Img src={src(img)} style={{ position: "absolute", left: 0, top: 0, width: d, height: d, objectFit: "cover", objectPosition: pos, filter: `url(#${id}-px)` }} />
  );
  return (
    <div style={{ position: "absolute", left: x - d / 2, top: y - d / 2, width: d, height: d, transform: `scale(${s})`, filter: `blur(${blur}px)` }}>
      <svg width={0} height={0} style={{ position: "absolute" }}>
        <filter id={`${id}-px`} x="0" y="0" width="100%" height="100%" primitiveUnits="userSpaceOnUse">
          <feFlood x={Math.floor(b / 2) - 1} y={Math.floor(b / 2) - 1} width={2} height={2} floodColor="#000" />
          <feComposite width={b} height={b} />
          <feTile result="grid" />
          <feComposite in="SourceGraphic" in2="grid" operator="in" />
          <feMorphology operator="dilate" radius={b / 2} />
        </filter>
        <filter id={`${id}-rgb`} x="-10%" y="0" width="120%" height="100%" colorInterpolationFilters="sRGB">
          <feColorMatrix in="SourceGraphic" type="matrix" values="1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0" result="r" />
          <feOffset in="r" dx={-jit} result="r2" />
          <feColorMatrix in="SourceGraphic" type="matrix" values="0 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 1 0" result="gb" />
          <feOffset in="gb" dx={jit} result="gb2" />
          <feBlend in="r2" in2="gb2" mode="screen" />
        </filter>
      </svg>
      <div style={{ position: "absolute", inset: 0, borderRadius: "50%", overflow: "hidden", border: `${bd}px solid #fff`, boxShadow: "0 10px 24px rgba(0,0,0,0.4)", background: "#222", boxSizing: "border-box" }}>
        <div style={{ position: "absolute", left: -bd, top: -bd, width: d, height: d }}>
          {mosaic()}
          {split !== "none" && (
            <div style={{ position: "absolute", inset: 0, clipPath: split === "right" ? `inset(0 0 0 ${d / 2}px)` : `inset(0 ${d / 2}px 0 0)`, filter: `url(#${id}-rgb)` }}>{mosaic()}</div>
          )}
        </div>
      </div>
      {verified && (
        <svg width={d * 0.26} height={d * 0.26} viewBox="-50 -50 100 100" style={{ position: "absolute", right: d * 0.02, bottom: d * 0.04, filter: "drop-shadow(0 3px 4px rgba(0,0,0,0.35))", transform: `scale(${kf(f, at + P.badgeDelay, [0, 3, 5], [0, 1.2, 1])})` }}>
          <path d={Array.from({ length: 24 }).map((_, i) => { const a = (i / 24) * Math.PI * 2, r = i % 2 ? 42 : 48; return `${i ? "L" : "M"}${r * Math.cos(a)},${r * Math.sin(a)}`; }).join(" ") + "Z"} fill="#1D9BF0" stroke="#fff" strokeWidth={5} />
          <path d="M-19,1 L-6,14 L20,-14" fill="none" stroke="#fff" strokeWidth={10} strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )}
      {label && (
        <div style={{ position: "absolute", left: "50%", top: d + 18, transform: `translateX(-50%) scaleX(${kf(f, at + P.labelDelay, [0, 3, 4], [0.3, 1.06, 1])})`, background: "rgba(30,30,30,0.9)", color: "#fff", fontFamily: "NeoEb", fontSize: 30, padding: "8px 24px", borderRadius: 999, whiteSpace: "nowrap", opacity: f < at + P.labelDelay ? 0 : 1 }}>{label}</div>
      )}
    </div>
  );
};

// ══ 12. LightningFlash (+ CartoonZaps) ══════════════════════════════════════
// 어두운 폭풍 하늘 + 사실적 흰 번개(폴리라인 + 글로우) 1~2f 번쩍, interval 간격(지터).
const boltPath = (seed: string, x0: number, y1: number) => {
  const pts: [number, number][] = [[x0, -20]];
  let x = x0, y = -20;
  const branches: [number, number][][] = [];
  let i = 0;
  while (y < y1) {
    y += 28 + R(`${seed}y${i}`) * 50;
    x += (R(`${seed}x${i}`) - 0.5) * 90;
    pts.push([x, y]);
    if (R(`${seed}b${i}`) < 0.16 && y < y1 * 0.8) {
      const br: [number, number][] = [[x, y]];
      let bx = x, by = y;
      const dir = R(`${seed}bd${i}`) < 0.5 ? -1 : 1;
      for (let j = 0; j < 5; j++) { bx += dir * (15 + R(`${seed}bx${i}-${j}`) * 45); by += 20 + R(`${seed}by${i}-${j}`) * 40; br.push([bx, by]); }
      branches.push(br);
    }
    i++;
  }
  return { main: pts, branches };
};
export const LightningFlashParams = z.object({
  interval: num(45, 6, 240, 1, "번개 간격", "timing", "f"),
  jitter: num(0.4, 0, 0.9, 0.05, "번개 타이밍 흔들림(간격 대비)", "timing"),
  flashLen: num(2, 1, 12, 1, "번쩍 길이", "timing", "f"),
  flash: num(0.45, 0, 1, 0.05, "화면 번쩍 세기(첫 프레임)", "look"),
  afterglow: num(0.22, 0, 1, 0.02, "잔광 세기", "look"),
  boltW: num(6, 1, 20, 0.5, "번개 굵기", "size", "px"),
  boltLen: num(620, 200, 1080, 10, "번개 최소 길이", "size", "px"),
  cloudSpeed: num(0.4, -5, 5, 0.1, "먹구름 흐름", "motion", "px/f"),
  rain: flag(true, "비", "look"),
  rainN: num(90, 0, 400, 5, "빗줄기 개수", "size"),
  rainSpeed: num(55, 0, 150, 1, "빗줄기 낙하 속도", "motion", "px/f"),
  rainAlpha: num(0.35, 0, 1, 0.05, "빗줄기 불투명도", "look"),
});
export type LightningFlashP = z.infer<typeof LightningFlashParams>;
export const LightningFlash: React.FC<{ interval?: number; flashLen?: number; seed?: string; rain?: boolean; children?: React.ReactNode; p?: Partial<LightningFlashP> }> = ({ interval: iv0, flashLen: fl0, seed = "bolt", rain: rain0, children, p }) => {
  const P = def(LightningFlashParams, { ...pk({ interval: iv0, flashLen: fl0, rain: rain0 }), ...p });
  const { flashLen, rain } = P;
  const interval = Math.max(1, P.interval);
  const f = useCurrentFrame();
  const k = Math.floor(f / interval);
  const strikeAt = k * interval + Math.floor(R(`${seed}t${k}`) * interval * P.jitter) + 6;
  const g = f - strikeAt;
  const on = g >= 0 && g < flashLen;
  const bx = 300 + R(`${seed}x${k}`) * (W - 600);
  const bolt = boltPath(`${seed}${k}`, bx, P.boltLen + R(`${seed}l${k}`) * 200);
  const toStr = (p: [number, number][]) => p.map((q) => q.join(",")).join(" ");
  const flashA = on ? (g === 0 ? P.flash : P.afterglow) : 0;
  return (
    <AbsoluteFill style={{ background: "linear-gradient(#141926 0%, #232B3D 55%, #2E3648 100%)", overflow: "hidden" }}>
      {/* 먹구름 덩어리 */}
      {Array.from({ length: 12 }).map((_, i) => {
        const w = 500 + R(`${seed}cw${i}`) * 500;
        const x = wrap(R(`${seed}cx${i}`) * (W + 800) + f * P.cloudSpeed, W + 800) - 400;
        const y = -120 + R(`${seed}cy${i}`) * 380;
        return <div key={i} style={{ position: "absolute", left: x - w / 2, top: y, width: w, height: w * 0.45, borderRadius: "50%", background: i % 2 ? "#39415A" : "#1C2233", opacity: 0.85, filter: "blur(30px)" }} />;
      })}
      {on && <div style={{ position: "absolute", left: bx - 500, top: -300, width: 1000, height: 700, borderRadius: "50%", background: "radial-gradient(circle, rgba(200,215,255,0.7), rgba(200,215,255,0) 65%)" }} />}
      {rain && (
        <svg width={W} height={H} style={{ position: "absolute", opacity: P.rainAlpha }}>
          {Array.from({ length: Math.round(P.rainN) }).map((_, i) => {
            const x = wrap(R(`${seed}rx${i}`) * (W + 300) - f * 14, W + 300);
            const y = wrap(R(`${seed}ry${i}`) * (H + 200) + f * P.rainSpeed, H + 200) - 100;
            return <line key={i} x1={x} y1={y} x2={x - 10} y2={y + 42} stroke="#A9B8D6" strokeWidth={2} />;
          })}
        </svg>
      )}
      {on && (
        <svg width={W} height={H} style={{ position: "absolute", filter: "drop-shadow(0 0 6px #fff) drop-shadow(0 0 16px #B8CCFF) drop-shadow(0 0 40px #7FA2FF)" }}>
          {bolt.branches.map((b, i) => <polyline key={i} points={toStr(b)} fill="none" stroke="#fff" strokeWidth={(P.boltW * 2.5) / 6} strokeLinejoin="round" opacity={g === 0 ? 0.9 : 0.6} />)}
          <polyline points={toStr(bolt.main)} fill="none" stroke="#fff" strokeWidth={g === 0 ? P.boltW : (P.boltW * 2) / 3} strokeLinejoin="round" />
        </svg>
      )}
      {children}
      <AbsoluteFill style={{ background: "#E8EEFF", opacity: flashA, pointerEvents: "none", mixBlendMode: "screen" }} />
    </AbsoluteFill>
  );
};
// 만화 번개 외곽선: 건물(rect) 주변에 노란 지그재그 번개가 period(8~10f)마다 위치를 바꿔가며 깜빡인다
export const CartoonZapsParams = z.object({
  period: num(9, 2, 40, 1, "깜빡임 주기", "timing", "f"),
  onRatio: num(0.7, 0.1, 1, 0.05, "켜져 있는 비율", "timing"),
  n: num(6, 0, 24, 1, "번개 개수", "size"),
  scale: num(1, 0.2, 4, 0.05, "번개 크기(배)", "size", "배"),
  offset: num(18, -60, 120, 1, "테두리에서 떨어진 거리", "size", "px"),
  outline: num(13, 0, 30, 1, "검정 외곽선 두께", "size", "px"),
  stroke: num(7, 1, 20, 1, "노란 선 두께", "size", "px"),
  color: col("#FFE14A", "번개 색"),
});
export type CartoonZapsP = z.infer<typeof CartoonZapsParams>;
export const CartoonZaps: React.FC<{ rect: [number, number, number, number]; period?: number; n?: number; color?: string; at?: number; seed?: string; p?: Partial<CartoonZapsP> }> = ({ rect, period: per0, n: n0, color: col0, at = 0, seed = "zap", p }) => {
  const P = def(CartoonZapsParams, { ...pk({ period: per0, n: n0, color: col0 }), ...p });
  const period = Math.max(1, Math.round(P.period)), n = Math.round(P.n), color = P.color;
  const f = useCurrentFrame();
  if (f < at || n <= 0) return null;
  const g = f - at;
  const cyc = Math.floor(g / period);
  if (g % period >= Math.ceil(period * P.onRatio)) return null;
  const [rx, ry, rw, rh] = rect;
  const cx = rx + rw / 2, cy = ry + rh / 2;
  return (
    <svg width={W} height={H} style={{ position: "absolute", left: 0, top: 0, pointerEvents: "none", overflow: "visible" }}>
      {Array.from({ length: n }).map((_, i) => {
        const k = `${seed}${cyc}-${i}`;
        const a = ((i + R(k + "a") * 0.7) / n) * Math.PI * 2;
        // 사각형 둘레 위 점
        const dx = Math.cos(a), dy = Math.sin(a);
        const t = Math.min(rw / 2 / Math.abs(dx || 1e-6), rh / 2 / Math.abs(dy || 1e-6));
        const px = cx + dx * t, py = cy + dy * t;
        const ang = (Math.atan2(dy, dx) * 180) / Math.PI;
        const sc = (0.8 + R(k + "s") * 0.5) * P.scale;
        const d = "M0,-14 L40,-22 L32,-6 L70,-12 L56,4 L100,0 L50,16 L60,4 L20,12 L28,-2 Z";
        return (
          <g key={i} transform={`translate(${px + dx * P.offset},${py + dy * P.offset}) rotate(${ang}) scale(${sc})`}>
            <path d={d} fill="none" stroke="#1a1a1a" strokeWidth={P.outline} strokeLinejoin="round" />
            <path d={d} fill="none" stroke={color} strokeWidth={P.stroke} strokeLinejoin="round" />
          </g>
        );
      })}
    </svg>
  );
};

// ══ 13. FlagWave ════════════════════════════════════════════════════════════
// 사인 변형 세로 슬라이스로 펄럭이는 플랫 깃발 루프 + 다음 깃발로 크로스페이드.
const star = (cx: number, cy: number, r: number, rot = 0) => Array.from({ length: 10 }).map((_, i) => { const a = -Math.PI / 2 + (i * Math.PI) / 5 + rot; const rr = i % 2 ? r * 0.382 : r; return `${i ? "L" : "M"}${cx + rr * Math.cos(a)},${cy + rr * Math.sin(a)}`; }).join(" ") + "Z";
const trigram = (pattern: number[], ang: number, d: number) => {
  const cx = 150 + d * Math.cos((ang * Math.PI) / 180), cy = 100 + d * Math.sin((ang * Math.PI) / 180);
  return (
    <g transform={`translate(${cx},${cy}) rotate(${ang + 90})`}>
      {pattern.map((solid, i) => {
        const y = -14 + i * 11;
        return solid ? <rect key={i} x={-25} y={y} width={50} height={8} fill="#000" /> : <g key={i}><rect x={-25} y={y} width={22.5} height={8} fill="#000" /><rect x={2.5} y={y} width={22.5} height={8} fill="#000" /></g>;
      })}
    </g>
  );
};
export const FLAGS: Record<string, React.ReactNode> = {
  kr: (
    <>
      <rect width={300} height={200} fill="#fff" />
      <g transform="rotate(33.69 150 100)">
        <circle cx={150} cy={100} r={50} fill="#0047A0" />
        <path d="M100,100 A50,50 0 0,1 200,100 A25,25 0 0,0 150,100 A25,25 0 0,1 100,100 Z" fill="#CD2E3A" />
      </g>
      {trigram([1, 1, 1], 213.69, 88)}{trigram([0, 1, 0], 326.31, 88)}{trigram([0, 0, 0], 33.69, 88)}{trigram([1, 0, 1], 146.31, 88)}
    </>
  ),
  cn: (
    <>
      <rect width={300} height={200} fill="#DE2910" />
      <path d={star(50, 50, 30)} fill="#FFDE00" />
      {[[100, 20], [120, 40], [120, 70], [100, 90]].map(([x, y], i) => <path key={i} d={star(x, y, 10, Math.atan2(50 - y, 50 - x) + Math.PI / 2)} fill="#FFDE00" />)}
    </>
  ),
  tw3: (
    <>
      <rect width={100} height={200} fill="#2E5FB0" /><rect x={100} width={100} height={200} fill="#fff" /><rect x={200} width={100} height={200} fill="#D9352B" />
    </>
  ),
};
export const FlagWaveParams = z.object({
  hold: num(60, 1, 300, 1, "깃발 유지 시간", "timing", "f"),
  xfade: num(15, 0, 120, 1, "다음 깃발 전환 길이", "timing", "f"),
  amp: num(30, 0, 150, 1, "펄럭임 진폭", "motion", "px"),
  waveSpeed: num(0.2, 0, 1.5, 0.01, "펄럭임 속도", "motion"),
  waves: num(7, 0, 30, 0.5, "물결 촘촘함", "motion"),
  shade: num(0.18, 0, 0.6, 0.01, "주름 음영 세기", "look"),
  w: num(840, 200, 1700, 10, "깃발 폭", "size", "px"),
  slices: num(96, 8, 300, 1, "세로 조각 수(부드러움)", "size"),
  pole: flag(true, "깃대", "look"),
});
export type FlagWaveP = z.infer<typeof FlagWaveParams>;
export const FlagWave: React.FC<{ flags?: (keyof typeof FLAGS | React.ReactNode)[]; x?: number; y?: number; w?: number; hold?: number; xfade?: number; amp?: number; slices?: number; pole?: boolean; p?: Partial<FlagWaveP> }> = ({ flags = ["kr", "cn"], x = 560, y = 250, w: w0, hold: hold0, xfade: xf0, amp: amp0, slices: sl0, pole: pole0, p }) => {
  const P = def(FlagWaveParams, { ...pk({ w: w0, hold: hold0, xfade: xf0, amp: amp0, slices: sl0, pole: pole0 }), ...p });
  const { w, amp, pole } = P;
  const hold = Math.max(1, P.hold), xfade = Math.max(0, P.xfade), slices = Math.max(1, Math.round(P.slices));
  const f = useCurrentFrame();
  const h = (w * 2) / 3, sw = w / slices;
  const cyc = hold + xfade;
  const idx = Math.floor(f / cyc) % flags.length;
  const local = f % cyc;
  const nxt = (idx + 1) % flags.length;
  const mix = flags.length > 1 && xfade > 0 ? interpolate(local, [hold, cyc], [0, 1], CL) : 0;
  const content = (fl: keyof typeof FLAGS | React.ReactNode) => (typeof fl === "string" ? FLAGS[fl] : fl);
  const flagSvg = (fl: keyof typeof FLAGS | React.ReactNode) => <svg width={w} height={h} viewBox="0 0 300 200" preserveAspectRatio="none" style={{ position: "absolute", top: 0 }}>{content(fl)}</svg>;
  return (
    <div style={{ position: "absolute", left: x, top: y, width: w, height: h + amp * 2 }}>
      {pole && (
        <>
          <div style={{ position: "absolute", left: -22, top: -30, width: 16, height: h + 520, background: "linear-gradient(90deg,#8d8d8d,#e0e0e0,#7a7a7a)", borderRadius: 6 }} />
          <div style={{ position: "absolute", left: -30, top: -52, width: 32, height: 32, borderRadius: 16, background: "radial-gradient(circle at 35% 35%, #FFE680, #C99A0A)" }} />
        </>
      )}
      {Array.from({ length: slices }).map((_, i) => {
        const u = i / slices;
        const ph = f * P.waveSpeed - u * P.waves;
        const dy = amp * Math.pow(u, 0.7) * Math.sin(ph);
        const shade = P.shade * Math.pow(u, 0.5) * Math.cos(ph);
        return (
          <div key={i} style={{ position: "absolute", left: i * sw, top: amp + dy, width: sw + 1, height: h, overflow: "hidden" }}>
            <div style={{ position: "absolute", left: -i * sw, top: 0, width: w, height: h }}>
              <div style={{ position: "absolute", inset: 0, opacity: 1 - mix }}>{flagSvg(flags[idx])}</div>
              {mix > 0 && <div style={{ position: "absolute", inset: 0, opacity: mix }}>{flagSvg(flags[nxt])}</div>}
            </div>
            <div style={{ position: "absolute", inset: 0, background: shade > 0 ? `rgba(255,255,255,${shade})` : `rgba(0,0,0,${-shade * 1.4})` }} />
          </div>
        );
      })}
    </div>
  );
};

// ══ 14. InstaCard ═══════════════════════════════════════════════════════════
// 흰 카드: 좌측 흑백 게시물 사진 + 우측 캡션 컬럼. 배경은 같은 사진을 강하게 블러 + 비네트. 우하단 출처 칩.
export const InstaCardParams = z.object({
  bw: flag(true, "게시물 사진 흑백", "look"),
  cardW: num(1360, 800, 1900, 10, "카드 폭", "size", "px"),
  cardH: num(700, 400, 1000, 10, "카드 높이", "size", "px"),
  photoW: num(700, 200, 1200, 10, "사진 칸 폭", "size", "px"),
  radius: num(14, 0, 60, 1, "카드 모서리 둥글기", "size", "px"),
  bgBlur: num(40, 0, 120, 2, "배경 블러", "look", "px"),
  bgBright: num(0.75, 0, 1.5, 0.05, "배경 밝기", "look"),
  vignette: num(0.65, 0, 1, 0.05, "비네트 세기", "look"),
  shadow: num(0.5, 0, 1, 0.05, "카드 그림자 진하기", "look"),
});
export type InstaCardP = z.infer<typeof InstaCardParams>;
export const InstaCard: React.FC<{ img: string; user?: string; caption?: string; likes?: string; source?: string; bw?: boolean; at?: number; avatar?: string; pos?: string; p?: Partial<InstaCardP> }> = ({ img, user = "semoji.official", caption = "", likes = "좋아요 1,284개", source, bw: bw0, at = 0, avatar, pos = "50% 50%", p }) => {
  const P = def(InstaCardParams, { ...pk({ bw: bw0 }), ...p });
  const bw = P.bw;
  const f = useCurrentFrame();
  const { s, blur } = photoPop(f, at);
  const CW = P.cardW, CH = P.cardH, PW = Math.min(P.photoW, P.cardW - 100);
  const ico = (d: string, k: number) => <svg key={k} width={40} height={40} viewBox="0 0 24 24"><path d={d} fill="none" stroke="#111" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" /></svg>;
  return (
    <AbsoluteFill style={{ overflow: "hidden", background: "#000" }}>
      <Img src={src(img)} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", transform: "scale(1.2)", filter: `blur(${P.bgBlur}px) brightness(${P.bgBright})` }} />
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 50%, transparent 30%, rgba(0,0,0,${P.vignette}) 100%)` }} />
      {f >= at && (
        <div style={{ position: "absolute", left: (W - CW) / 2, top: 90, width: CW, height: CH, background: "#fff", borderRadius: P.radius, overflow: "hidden", display: "flex", transform: `scale(${s})`, filter: `blur(${blur}px)`, boxShadow: `0 20px 60px rgba(0,0,0,${P.shadow})` }}>
          <div style={{ width: PW, height: CH, background: "#111", flexShrink: 0 }}>
            <Img src={src(img)} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: pos, filter: bw ? "grayscale(1) contrast(1.1)" : undefined }} />
          </div>
          <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
            <div style={{ height: 96, display: "flex", alignItems: "center", gap: 18, padding: "0 28px", borderBottom: "1px solid #e6e6e6" }}>
              <div style={{ width: 56, height: 56, borderRadius: 28, padding: 3, background: "linear-gradient(45deg,#F9CE34,#EE2A7B,#6228D7)" }}>
                <div style={{ width: "100%", height: "100%", borderRadius: "50%", border: "3px solid #fff", overflow: "hidden", background: "#ddd", boxSizing: "border-box" }}>{avatar && <Img src={src(avatar)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />}</div>
              </div>
              <div style={{ fontFamily: "NeoHv", fontSize: 26, color: "#111" }}>{user}</div>
              <div style={{ fontFamily: "NeoEb", fontSize: 24, color: "#0095F6" }}>· 팔로우</div>
              <div style={{ marginLeft: "auto", fontFamily: "NeoHv", fontSize: 30, color: "#111", letterSpacing: 2 }}>···</div>
            </div>
            <div style={{ flex: 1, padding: "26px 28px", fontFamily: "NeoEb", fontSize: 27, lineHeight: 1.55, color: "#222", whiteSpace: "pre-line" }}>
              <span style={{ fontFamily: "NeoHv", color: "#111" }}>{user} </span>{caption}
            </div>
            <div style={{ borderTop: "1px solid #e6e6e6", padding: "18px 28px 26px" }}>
              <div style={{ display: "flex", gap: 22 }}>
                {ico("M12 21s-7.5-4.6-9.3-9.2C1.4 8.3 3.6 4.5 7.3 4.5c2 0 3.5 1.1 4.7 2.7 1.2-1.6 2.7-2.7 4.7-2.7 3.7 0 5.9 3.8 4.6 7.3C19.5 16.4 12 21 12 21z", 0)}
                {ico("M20.5 11.5a8.5 8.5 0 1 1-3.4-6.8A8.5 8.5 0 0 1 20.5 11.5zM20.5 20.5l-2-4", 1)}
                {ico("M22 3L2 10l8 3 3 8 9-18zM10 13l6-6", 2)}
              </div>
              <div style={{ fontFamily: "NeoHv", fontSize: 24, color: "#111", marginTop: 12 }}>{likes}</div>
            </div>
          </div>
        </div>
      )}
      {source && <SourceChip text={source} />}
    </AbsoluteFill>
  );
};

// ══ 15. TonalWordmark ═══════════════════════════════════════════════════════
// 배경보다 살짝 밝은 톤온톤 거대 워드마크(~300px)가 콘텐츠 뒤에서 천천히 흐른다(루프).
export const TonalWordmarkParams = z.object({
  size: num(300, 60, 700, 5, "글자 크기", "size", "px"),
  pxPerSec: num(12, -300, 300, 1, "흐름 속도", "motion", "px/s"),
  rows: num(1, 1, 6, 1, "줄 수", "size"),
  rowGap: num(1.05, 0.6, 2, 0.05, "줄 간격(배)", "size", "배"),
  tracking: num(-4, -40, 60, 1, "자간", "size", "px"),
  rowShift: num(200, 0, 1000, 10, "줄마다 엇갈림", "motion", "px"),
  bg: col("#C8412F", "배경색"),
  tone: col("rgba(255,255,255,0.08)", "워드마크 색(톤온톤)"),
});
export type TonalWordmarkP = z.infer<typeof TonalWordmarkParams>;
export const TonalWordmark: React.FC<{ text: string; bg?: string; tone?: string; size?: number; pxPerSec?: number; y?: number; rows?: number; font?: string; children?: React.ReactNode; p?: Partial<TonalWordmarkP> }> = ({ text, bg: bg0, tone: tone0, size: size0, pxPerSec: v0, y = 390, rows: rows0, font = "Jalnan", children, p }) => {
  const P = def(TonalWordmarkParams, { ...pk({ bg: bg0, tone: tone0, size: size0, pxPerSec: v0, rows: rows0 }), ...p });
  const { bg, tone, size, pxPerSec } = P;
  const rows = Math.max(1, Math.round(P.rows));
  const f = useCurrentFrame();
  const unit = `${text} `;
  return (
    <AbsoluteFill style={{ background: bg, overflow: "hidden" }}>
      {Array.from({ length: rows }).map((_, r) => {
        const dir = r % 2 ? 1 : -1;
        const shift = (f * pxPerSec) / FPS;
        return (
          <div key={r} style={{ position: "absolute", top: y + (r - (rows - 1) / 2) * size * P.rowGap - size / 2, left: 0, whiteSpace: "nowrap", fontFamily: font, fontSize: size, lineHeight: 1, color: tone, letterSpacing: P.tracking, transform: `translateX(${dir < 0 ? -shift - r * P.rowShift : shift - 2000})` }}>
            {unit.repeat(8)}
          </div>
        );
      })}
      {children}
    </AbsoluteFill>
  );
};

