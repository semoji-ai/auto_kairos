// 세모지 전환(transition) 라이브러리 — 레퍼런스 프레임 실측값 기반.
//
// 공통 API 규약
//   <X at={frame} from={<SceneA/>} to={<SceneB/>} ... />
//   - at   : 전환이 시작되는 (부모 시퀀스 기준) 프레임
//   - from : at 이전(및 전환 전반부)에 보이는 씬
//   - to   : 컷 이후 보이는 씬
//   - 각 컴포넌트 옆의 *_CUT 상수 = at 으로부터 A→B 가 실제로 바뀌는 오프셋,
//     *_LEN 상수 = 전환이 완전히 끝나는 오프셋.
// 모든 난수는 remotion random(seed) — 결정론적. 방사형 줄무늬 광선은 쓰지 않는다.
import React from "react";
import { AbsoluteFill, Easing, Img, random, useCurrentFrame } from "remotion";
import { z } from "zod";
import { W, H, lerp, kf, EXPO_OUT, QUART_OUT, src } from "../fx";
import { num, col, flag, choice, def } from "../params/p";
// 변수(파라미터): 각 전환은 <Name>Params 스키마를 내보내고 p?: Partial<...> 로 덮어쓴다.
// 컷/끝 오프셋이 변수에 따라 달라지는 전환은 <name>Timing(p) 헬퍼가 { cut, len } 을 계산한다
// (*_CUT / *_LEN 상수는 기본값 기준 그대로 유효).

type Node = React.ReactNode;
const IN_OUT_CUBIC = Easing.inOut(Easing.cubic);
const useSvgId = (p: string) => p + React.useId().replace(/[^a-zA-Z0-9]/g, "");
const clamp01 = (v: number) => Math.max(0, Math.min(1, v));
/** 개별 prop 중 undefined 가 아닌 것만 골라 P 에 반영 */
const pick = <T extends object>(o: T): Partial<T> => Object.fromEntries(Object.entries(o).filter(([, v]) => v !== undefined)) as Partial<T>;
const EASES = { cubic: Easing.inOut(Easing.cubic), quad: Easing.inOut(Easing.quad), sin: Easing.inOut(Easing.sin), expo: Easing.inOut(Easing.exp), linear: Easing.linear } as const;
const EASE_KEYS = ["cubic", "quad", "sin", "expo", "linear"] as const;

/** 전체 화면 사진 씬 (데모·실사용 공용) */
export const Shot: React.FC<{ img: string; pos?: string; style?: React.CSSProperties; children?: Node }> = ({ img, pos = "50% 50%", style, children }) => (
  <AbsoluteFill style={{ overflow: "hidden", background: "#111", ...style }}>
    <Img src={src(img)} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", objectPosition: pos }} />
    {children}
  </AbsoluteFill>
);

/** 4각 별 (Sparkles 와 같은 곡선형 4각) */
const Star4: React.FC<{ x: number; y: number; size: number; color?: string; style?: React.CSSProperties }> = ({ x, y, size, color = "#fff", style }) => (
  <svg width={size} height={size} viewBox="-50 -50 100 100" style={{ position: "absolute", left: x - size / 2, top: y - size / 2, overflow: "visible", ...style }}>
    <path d="M0,-50 C6,-8 8,-6 50,0 C8,6 6,8 0,50 C-6,8 -8,6 -50,0 C-8,-6 -6,-8 0,-50Z" fill={color} />
  </svg>
);

// ═══════════════════════════════════════════════════════════════════════════
// 1. 극장 커튼 — 3f 지연 → 19f 낙하(가속·감속 + 바닥 근처 3f 걸림) → 22f 완전 덮음(컷)
//    → 10f 상승(감속) → 발랑스(상단 띠) 12f 잔류 후 소멸. 총 ~56f
// ═══════════════════════════════════════════════════════════════════════════
export const CURTAIN_CUT = 33;
export const CURTAIN_LEN = 56;
export const TheaterCurtainParams = z.object({
  delay: num(3, 0, 30, 1, "낙하 시작 지연", "timing", "f"),
  dropDur: num(16, 2, 60, 1, "커튼 낙하 시간", "timing", "f"),
  hitch: num(16, 0, 80, 1, "바닥 걸림 튕김 높이", "motion", "px"),
  hold: num(22, 2, 90, 1, "덮은 채 머무는 시간(중간에 컷)", "timing", "f"),
  riseDur: num(10, 2, 60, 1, "커튼 상승 시간", "timing", "f"),
  scallop: num(58, 0, 160, 2, "밑단 물결 깊이", "size", "px"),
  sway: num(0.35, 0, 2, 0.05, "흔들림 속도", "motion"),
  highlight: col("#BA2A29", "커튼 밝은 색"),
  shadow: col("#8A1F1C", "커튼 그림자 색"),
});
export type TheaterCurtainP = z.infer<typeof TheaterCurtainParams>;
/** 커튼 타이밍: covered = 완전히 덮는 오프셋, cut = A→B 오프셋, len = 끝 */
export const curtainTiming = (p?: Partial<TheaterCurtainP>) => {
  const P = def(TheaterCurtainParams, p);
  const covered = P.delay + P.dropDur + 3;
  const cut = covered + Math.floor(P.hold / 2);
  const riseAt = covered + P.hold;
  return { covered, cut, riseAt, riseEnd: riseAt + P.riseDur, len: riseAt + P.riseDur + 2 };
};
const PLEAT = W / 8;
const curtainY = (g: number, P: TheaterCurtainP, T: ReturnType<typeof curtainTiming>) => {
  const top = -(H + 140);
  const d0 = P.delay, d1 = P.delay + P.dropDur;
  if (g < d0) return top;
  if (g < d1) return lerp(g, d0, d1, top, -70, Easing.inOut(Easing.quad));
  if (g < T.covered) return kf(g, d1, [0, 1, 2, 3], [-70, -70 - P.hitch, -34 * (P.hitch / 16), 0]); // 걸림(hitch)
  if (g < T.riseAt) return 0;
  return lerp(g, T.riseAt, T.riseEnd, 0, top - 60, Easing.out(Easing.sin));
};
const CurtainSheet: React.FC<{ id: string; sway: number; highlight: string; shadow: string; scallop?: number }> = ({ id, sway, highlight, shadow, scallop = 58 }) => {
  // 하단: 주름마다 아래로 볼록한 물결(스캘럽). 주름 경계점은 H+16 까지 내려와 완전 덮음 보장
  let d = `M0,-20 L${W},-20 L${W},${H + 16}`;
  for (let i = 7; i >= 0; i--) {
    const x0 = i * PLEAT, x1 = (i + 1) * PLEAT;
    const dip = scallop + 10 * Math.sin(i * 1.7 + sway);
    d += ` Q${(x0 + x1) / 2 + 14 * Math.sin(sway + i)},${H + 16 + dip} ${x0},${H + 16}`;
  }
  d += " Z";
  return (
    <svg width={W} height={H + 120} style={{ position: "absolute", left: 0, top: 0, overflow: "visible", filter: "drop-shadow(0 10px 14px rgba(0,0,0,0.45))" }}>
      <defs>
        <linearGradient id={`${id}g`} x1="0" x2="1" y1="0" y2="0">
          <stop offset="0" stopColor="#6A1614" />
          <stop offset="0.16" stopColor={shadow} />
          <stop offset="0.46" stopColor={highlight} />
          <stop offset="0.58" stopColor="#C8403A" />
          <stop offset="0.8" stopColor={shadow} />
          <stop offset="1" stopColor="#6A1614" />
        </linearGradient>
        <pattern id={`${id}p`} x="0" y="0" width={PLEAT} height={40} patternUnits="userSpaceOnUse">
          <rect width={PLEAT} height={40} fill={`url(#${id}g)`} />
        </pattern>
        <linearGradient id={`${id}v`} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor="rgba(0,0,0,0.35)" /><stop offset="0.25" stopColor="rgba(0,0,0,0)" />
          <stop offset="0.85" stopColor="rgba(0,0,0,0)" /><stop offset="1" stopColor="rgba(0,0,0,0.25)" />
        </linearGradient>
      </defs>
      <path d={d} fill={`url(#${id}p)`} />
      <path d={d} fill={`url(#${id}v)`} />
    </svg>
  );
};
const Valance: React.FC<{ id: string }> = ({ id }) => {
  // 상단 띠: 짙은 빨강 + 스와그(아래로 늘어진 반원) + 금색 트림
  const n = 6, sw = W / n, hh = 120;
  let d = `M0,0 L${W},0 L${W},${hh}`;
  for (let i = n - 1; i >= 0; i--) d += ` Q${(i + 0.5) * sw},${hh + 70} ${i * sw},${hh}`;
  d += " Z";
  let trim = `M${W},${hh - 4}`;
  for (let i = n - 1; i >= 0; i--) trim += ` Q${(i + 0.5) * sw},${hh + 62} ${i * sw},${hh - 4}`;
  return (
    <svg width={W} height={hh + 80} style={{ position: "absolute", left: 0, top: 0, filter: "drop-shadow(0 8px 10px rgba(0,0,0,0.5))" }}>
      <defs>
        <linearGradient id={`${id}vg`} x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#6E1715" /><stop offset="0.6" stopColor="#9A2422" /><stop offset="1" stopColor="#7C1B19" /></linearGradient>
      </defs>
      <path d={d} fill={`url(#${id}vg)`} />
      <path d={trim} stroke="#D9A23A" strokeWidth={8} fill="none" />
      <rect x={0} y={18} width={W} height={6} fill="#D9A23A" opacity={0.85} />
    </svg>
  );
};
export const TheaterCurtain: React.FC<{ at: number; from: Node; to: Node; highlight?: string; shadow?: string; p?: Partial<TheaterCurtainP> }> = ({ at, from, to, highlight, shadow, p }) => {
  const P = def(TheaterCurtainParams, { ...pick({ highlight, shadow }), ...p });
  const T = curtainTiming(P);
  const f = useCurrentFrame();
  const g = f - at;
  const id = useSvgId("cur");
  const y = curtainY(g, P, T);
  const showCurtain = g >= P.delay && g < T.riseEnd + 1;
  const sway = g * P.sway;
  return (
    <AbsoluteFill>
      {g < T.cut ? from : to}
      {showCurtain && (
        <div style={{ position: "absolute", left: 0, top: 0, transform: `translateY(${y}px)` }}>
          <CurtainSheet id={id} sway={sway} highlight={P.highlight} shadow={P.shadow} scallop={P.scallop} />
        </div>
      )}
      {g >= P.delay && g < T.len && <div style={{ position: "absolute", left: 0, top: 0, transform: `translateY(${g > T.len - 2 ? -60 : 0}px)` }}><Valance id={id} /></div>}
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 2. CRT 전원 전환 — 15fps(2f 홀드) 구동.
//    OFF 6f: scaleY 0.9→0.55→0.3→0.15 + 백색화 / HOLD 6f: 검정 + 3px 가로선 + 4각 별 펄스
//    ON 4f: 새 씬 scaleY 0.15→0.4→0.75→1.0.   컷 = at+12, 끝 = at+16
// ═══════════════════════════════════════════════════════════════════════════
export const CRT_CUT = 12;
export const CRT_LEN = 16;
export const CRTSwitchParams = z.object({
  offDur: num(6, 1, 30, 1, "꺼짐(세로 압축) 시간", "timing", "f"),
  holdDur: num(6, 1, 40, 1, "검은 화면 + 별 유지", "timing", "f"),
  onDur: num(4, 1, 30, 1, "켜짐(세로 펼침) 시간", "timing", "f"),
  minScaleY: num(0.15, 0.01, 0.9, 0.01, "최대 압축 시 세로 크기(배)", "motion"),
  white: num(0.92, 0, 1, 0.02, "백색화 최대 세기", "look"),
  brightBoost: num(0.4, 0, 1.5, 0.05, "포즈당 밝기 증가", "look"),
  pulsePeriod: num(2, 1, 10, 1, "별 깜빡임 반주기", "timing", "f"),
  pulseDim: num(0.62, 0.1, 1, 0.02, "별 작아질 때 크기(배)", "motion"),
  starSize: num(60, 0, 300, 2, "별 크기", "size", "px"),
  lineWidth: num(3, 0, 20, 1, "가로선 두께", "size", "px"),
  lineColor: col("#FFFFFF", "가로선 색"),
});
export type CRTSwitchP = z.infer<typeof CRTSwitchParams>;
export const crtTiming = (p?: Partial<CRTSwitchP>) => {
  const P = def(CRTSwitchParams, p);
  return { cut: P.offDur + P.holdDur, len: P.offDur + P.holdDur + P.onDur };
};
export const CRTSwitch: React.FC<{ at: number; from: Node; to: Node; starSize?: number; p?: Partial<CRTSwitchP> }> = ({ at, from, to, starSize, p }) => {
  const P = def(CRTSwitchParams, { ...pick({ starSize }), ...p });
  const { cut, len } = crtTiming(P);
  const f = useCurrentFrame();
  const g = f - at;
  if (g < 0) return <AbsoluteFill>{from}</AbsoluteFill>;
  if (g >= len) return <AbsoluteFill>{to}</AbsoluteFill>;
  const wk = P.white / 0.92;
  // 기준 곡선 [0.9,0.55,0.3,0.15] 을 "압축 비율"로 바꿔 최대 압축(minScaleY)에 맞춰 늘인다
  const sq = (v: number) => 1 - ((1 - v) / 0.85) * (1 - P.minScaleY);
  const tube = (node: Node, sy: number, white: number, bright: number) => (
    <AbsoluteFill style={{ background: "#000" }}>
      <AbsoluteFill style={{ transform: `scaleY(${sy})`, filter: `brightness(${bright}) contrast(${1 + white * 0.4})` }}>
        {node}
        <AbsoluteFill style={{ background: "#fff", opacity: white }} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
  if (g < P.offDur) {
    // 15fps 풍: 포즈 시작 = [0, 2/6, 4/6, 5/6] × offDur (기본 6f → 앞 두 포즈 2f, 마지막 두 포즈 1f)
    const pose = P.offDur === 6 ? [0, 0, 1, 1, 2, 3][g] : [2 / 6, 4 / 6, 5 / 6].filter((t) => g >= t * P.offDur).length;
    const sy = P.minScaleY === 0.15 ? [0.9, 0.55, 0.3, 0.15][pose] : sq([0.9, 0.55, 0.3, 0.15][pose]);
    const white = [0.15, 0.4, 0.7, 0.92][pose] * wk;
    return tube(from, sy, white, 1 + pose * P.brightBoost);
  }
  if (g < cut) {
    const pulse = Math.floor((g - P.offDur) / P.pulsePeriod) % 2 === 0 ? 1 : P.pulseDim;
    const h = P.holdDur;
    const lineA = kf(g, P.offDur, [0, (4 / 6) * h, h], [1, 0.8, 0.35]);
    const lw = P.lineWidth;
    return (
      <AbsoluteFill style={{ background: "#000" }}>
        {lw > 0 && <div style={{ position: "absolute", left: 0, top: H / 2 - lw / 2, width: W, height: lw, background: P.lineColor, opacity: lineA, boxShadow: `0 0 ${lw * 4}px ${lw}px rgba(255,255,255,0.6)` }} />}
        {P.starSize > 0 && <Star4 x={W / 2} y={H / 2} size={P.starSize} style={{ transform: `scale(${pulse})`, filter: "drop-shadow(0 0 10px #fff) drop-shadow(0 0 24px rgba(200,230,255,0.9))" }} />}
      </AbsoluteFill>
    );
  }
  const k = P.onDur === 4 ? g - cut : Math.min(3, Math.floor(((g - cut) * 4) / P.onDur));
  const sy = P.minScaleY === 0.15 ? [0.15, 0.4, 0.75, 1.0][k] : sq([0.15, 0.4, 0.75, 1.0][k]);
  return tube(to, sy, [0.7, 0.35, 0.1, 0][k] * wk, 1 + [0.6, 0.3, 0.1, 0][k] * (P.brightBoost / 0.4));
};

// ═══════════════════════════════════════════════════════════════════════════
// 3. 슬랫 모자이크 — at 에서 크림 배경으로 하드컷, 480px 세로 슬랫 4장이 아래/위 교대로
//    11~14f ease-out 슬라이드인, 시작 스태거 8f.  컷 = at, 끝 = at+37
// ═══════════════════════════════════════════════════════════════════════════
export const SLAT_CUT = 0;
export const SLAT_LEN = 37;
export const SlatMosaicParams = z.object({
  stagger: num(8, 0, 30, 1, "슬랫 시작 스태거 간격", "timing", "f"),
  slideDur: num(12, 1, 40, 1, "슬라이드인 시간(기준, 슬랫마다 −1~+2f)", "timing", "f"),
  travel: num(1, 0.1, 2, 0.05, "들어오는 거리(화면 높이 배)", "motion", "배"),
  alternate: flag(true, "위/아래 교대로 들어오기"),
  gap: num(6, 0, 80, 1, "슬랫 사이 간격", "size", "px"),
  labelSize: num(48, 0, 120, 2, "라벨 글자 크기", "size", "px"),
  bg: col("#F3ECDD", "배경 색"),
});
export type SlatMosaicP = z.infer<typeof SlatMosaicParams>;
const SLAT_JIT = [0, -1, 2, 1];
export const slatTiming = (p?: Partial<SlatMosaicP>, n = 4) => {
  const P = def(SlatMosaicParams, p);
  const len = Math.max(...Array.from({ length: n }).map((_, i) => i * P.stagger + Math.max(1, P.slideDur + SLAT_JIT[i % 4])));
  return { cut: 0, len };
};
export const SlatMosaic: React.FC<{ at: number; from: Node; imgs: string[]; bg?: string; stagger?: number; gap?: number; labels?: string[]; p?: Partial<SlatMosaicP> }> = ({ at, from, imgs, bg, stagger, gap, labels, p }) => {
  const P = def(SlatMosaicParams, { ...pick({ bg, stagger, gap }), ...p });
  const f = useCurrentFrame();
  const g = f - at;
  if (g < 0) return <AbsoluteFill>{from}</AbsoluteFill>;
  const n = imgs.length, sw = W / n;
  return (
    <AbsoluteFill style={{ background: P.bg }}>
      {imgs.map((im, i) => {
        const a = i * P.stagger, d = Math.max(1, P.slideDur + SLAT_JIT[i % 4]);
        if (g < a) return null;
        const dir = !P.alternate || i % 2 === 0 ? 1 : -1; // 짝수: 아래에서, 홀수: 위에서
        const ty = lerp(g, a, a + d, dir * H * P.travel, 0, QUART_OUT);
        return (
          <div key={i} style={{ position: "absolute", left: i * sw + P.gap / 2, top: 0, width: Math.max(0, sw - P.gap), height: H, overflow: "hidden", transform: `translateY(${ty}px)` }}>
            <Img src={src(im)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
            {labels?.[i] && P.labelSize > 0 && <div style={{ position: "absolute", left: 0, right: 0, bottom: 70, textAlign: "center", fontFamily: "NeoHv", fontSize: P.labelSize, color: "#fff", textShadow: "0 3px 8px rgba(0,0,0,0.7)" }}>{labels[i]}</div>}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 4. 신문 풀아웃 — 현재 씬에 흰 종이 테두리 20px(3f) → scale 1→k, 회전 0→−3°→+2° (12f ease-out)
//    로 빠지며 나무 책상 위 신문 1면의 사진이 된다. 이후 미세 흔들림 루프.
//    컷 개념 없음(같은 씬이 사진으로 축소). 끝 = at+15
// ═══════════════════════════════════════════════════════════════════════════
export const NEWS_LEN = 15;
const WoodDesk: React.FC<{ id: string }> = ({ id }) => (
  <svg width={W + 800} height={H + 800} style={{ position: "absolute", left: -400, top: -400 }}>
    <defs>
      <filter id={`${id}w`} x="0" y="0" width="100%" height="100%">
        <feTurbulence type="fractalNoise" baseFrequency="0.0025 0.055" numOctaves={3} seed={11} />
        <feColorMatrix values="0 0 0 0 0.16  0 0 0 0 0.09  0 0 0 0 0.05  1.9 0 0 0 -0.62" />
      </filter>
      <filter id={`${id}w2`} x="0" y="0" width="100%" height="100%">
        <feTurbulence type="fractalNoise" baseFrequency="0.006 0.16" numOctaves={2} seed={5} />
        <feColorMatrix values="0 0 0 0 0.55  0 0 0 0 0.38  0 0 0 0 0.24  1.6 0 0 0 -0.78" />
      </filter>
    </defs>
    <rect width="100%" height="100%" fill="#5A3A26" />
    <rect width="100%" height="100%" filter={`url(#${id}w)`} />
    <rect width="100%" height="100%" filter={`url(#${id}w2)`} />
    {[0, 1, 2, 3].map((i) => <rect key={i} x={0} y={i * 520 + 140} width="100%" height={3} fill="#3A2416" opacity={0.7} />)}
  </svg>
);
const TextBars: React.FC<{ x: number; y: number; w: number; rows: number; seed: string; lh?: number }> = ({ x, y, w, rows, seed, lh = 26 }) => (
  <>
    {Array.from({ length: rows }).map((_, i) => (
      <div key={i} style={{ position: "absolute", left: x, top: y + i * lh, width: w * (i === rows - 1 ? 0.55 : 0.86 + 0.14 * random(`${seed}${i}`)), height: lh * 0.42, background: "#6d665c", opacity: 0.55, borderRadius: 2 }} />
    ))}
  </>
);
export const NewspaperPulloutParams = z.object({
  k: num(0.38, 0.15, 0.9, 0.01, "사진 최종 크기(배)", "size", "배"),
  border: num(20, 0, 80, 1, "흰 종이 테두리 두께", "size", "px"),
  borderDur: num(3, 1, 20, 1, "테두리 생기는 시간", "timing", "f"),
  pullDur: num(12, 2, 60, 1, "빠지며 축소되는 시간", "timing", "f"),
  tiltA: num(-3, -20, 20, 0.5, "첫 기울기", "motion", "°"),
  tiltB: num(2, -20, 20, 0.5, "착지 기울기", "motion", "°"),
  settle: num(0.35, 0, 3, 0.05, "착지 후 흔들림 세기", "motion", "°"),
  sepia: num(0.25, 0, 1, 0.05, "사진 세피아 세기", "look"),
  dust: num(26, 0, 80, 1, "먼지 개수", "look"),
});
export type NewspaperPulloutP = z.infer<typeof NewspaperPulloutParams>;
export const newsTiming = (p?: Partial<NewspaperPulloutP>) => {
  const P = def(NewspaperPulloutParams, p);
  return { cut: 0, len: P.borderDur + P.pullDur };
};
export const NewspaperPullout: React.FC<{ at: number; from: Node; headline: string; sub?: string; masthead?: string; k?: number; p?: Partial<NewspaperPulloutP> }> = ({ at, from, headline, sub = "", masthead = "NEWS", k: kProp, p: pp }) => {
  const P = def(NewspaperPulloutParams, { ...pick({ k: kProp }), ...pp });
  const k = P.k;
  const f = useCurrentFrame();
  const g = f - at;
  const id = useSvgId("np");
  if (g < 0) return <AbsoluteFill>{from}</AbsoluteFill>;
  const px = 1010, py = 648, photoRot = 2;
  const b0 = P.borderDur, e = P.borderDur + P.pullDur, tm = b0 + P.pullDur / 3;
  const border = lerp(g, 0, b0, 0, P.border, Easing.out(Easing.quad));
  const p = lerp(g, b0, e, 0, 1, EXPO_OUT);
  const s = Math.exp(Math.log(1 / k) * (1 - p));
  const apparent = g < b0 ? 0 : g < tm ? lerp(g, b0, tm, 0, P.tiltA, Easing.out(Easing.quad)) : lerp(g, tm, e, P.tiltA, P.tiltB, Easing.inOut(Easing.sin));
  const settle = g > e ? P.settle * Math.sin((g - e) / 13) : 0;
  const camRot = apparent - photoRot + settle;
  const breathe = g > e ? 1 + 0.004 * Math.sin((g - e) / 17) : 1;
  const tx = (W / 2 - px) * (1 - p), ty = (H / 2 - py) * (1 - p);
  const paper = (st: React.CSSProperties) => <div style={{ position: "absolute", background: "#EFE9DC", boxShadow: "0 18px 40px rgba(0,0,0,0.55)", ...st }} />;
  const dustOp = lerp(g, 6, 16, 0, 1);
  return (
    <AbsoluteFill style={{ background: "#3d2718", overflow: "hidden" }}>
      <AbsoluteFill style={{ transformOrigin: `${px}px ${py}px`, transform: `translate(${tx}px,${ty}px) rotate(${camRot}deg) scale(${s * breathe})` }}>
        <WoodDesk id={id} />
        {/* 뒤에 깔린 다른 신문 +3° */}
        {paper({ left: 170, top: 90, width: 1180, height: 1300, transform: "rotate(3deg)", background: "#E2D9C4" })}
        {/* 본 신문 */}
        <div style={{ position: "absolute", left: 330, top: 10, width: 1270, height: 1300, background: "#EFE9DC", transform: "rotate(-1.2deg)", boxShadow: "0 20px 44px rgba(0,0,0,0.6)" }}>
          <div style={{ position: "absolute", left: 40, right: 40, top: 22, textAlign: "center", fontFamily: "Georgia, 'Times New Roman', serif", fontWeight: 900, fontSize: 118, letterSpacing: 18, color: "#1b1a18", lineHeight: 1 }}>{masthead}</div>
          <div style={{ position: "absolute", left: 40, right: 40, top: 150, height: 5, background: "#1b1a18" }} />
          <div style={{ position: "absolute", left: 40, right: 40, top: 160, height: 2, background: "#1b1a18" }} />
          <div style={{ position: "absolute", left: 40, right: 40, top: 176, display: "flex", justifyContent: "space-between", fontFamily: "Georgia, serif", fontSize: 20, color: "#3a372f" }}><span>VOL. 1938</span><span>SEMOJI DAILY</span><span>PRICE 5 JEON</span></div>
          <div style={{ position: "absolute", left: 40, right: 40, top: 214, height: 2, background: "#1b1a18" }} />
          <div style={{ position: "absolute", left: 40, right: 40, top: 232, textAlign: "center", fontFamily: "NeoHv", fontSize: 46, color: "#141312", lineHeight: 1.15, whiteSpace: "pre-line" }}>{headline}</div>
          {sub && <div style={{ position: "absolute", left: 40, right: 40, top: 346, textAlign: "center", fontFamily: "NeoEb", fontSize: 28, color: "#3b372f" }}>{sub}</div>}
          <TextBars x={42} y={430} w={250} rows={17} seed="L" />
          <TextBars x={1022} y={430} w={210} rows={17} seed="R" />
          <div style={{ position: "absolute", left: 42, top: 908, width: 1190, height: 2, background: "#1b1a18" }} />
          <TextBars x={42} y={928} w={370} rows={12} seed="A" />
          <TextBars x={440} y={928} w={370} rows={12} seed="B" />
          <TextBars x={840} y={928} w={390} rows={12} seed="C" />
        </div>
      </AbsoluteFill>
      {/* 사진(=나가는 씬) — 카메라와 같은 변환을 받도록 같은 컨테이너 규칙으로 따로 렌더 */}
      <AbsoluteFill style={{ transformOrigin: `${px}px ${py}px`, transform: `translate(${tx}px,${ty}px) rotate(${camRot}deg) scale(${s * breathe})` }}>
        <div style={{ position: "absolute", left: px - W / 2, top: py - H / 2, width: W, height: H, transform: `rotate(${photoRot}deg) scale(${k})`, boxShadow: p > 0.05 ? `0 ${14 / k}px ${30 / k}px rgba(0,0,0,${0.35 * p})` : undefined, overflow: "hidden", background: "#fff" }}>
          <AbsoluteFill style={{ filter: `sepia(${P.sepia * p}) contrast(${1 + 0.05 * p})` }}>{from}</AbsoluteFill>
          <AbsoluteFill style={{ boxShadow: `inset 0 0 0 ${border / 1}px #fff` }} />
        </div>
      </AbsoluteFill>
      {/* 느린 먼지 */}
      <AbsoluteFill style={{ opacity: dustOp, pointerEvents: "none" }}>
        {Array.from({ length: P.dust }).map((_, i) => {
          const x0 = random(`dx${i}`) * W, y0 = random(`dy${i}`) * H;
          const x = x0 + Math.sin((g + i * 13) / 40) * 30 + g * 0.25 * (random(`dv${i}`) - 0.5);
          const y = y0 - g * (0.2 + 0.4 * random(`du${i}`));
          const r = 1.5 + 3 * random(`dr${i}`);
          return <div key={i} style={{ position: "absolute", left: x, top: y, width: r * 2, height: r * 2, borderRadius: "50%", background: "#fff6e2", opacity: 0.25 + 0.4 * random(`do${i}`), filter: r > 3.5 ? "blur(1.5px)" : undefined }} />;
        })}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 5. 매거진 플립 — 나가는 씬이 표지로 축소(6f) → 표지가 왼쪽 책등 축 Y회전 15f
//    → 속지 4장 각 6f 넘김 → target 페이지 착지(at+45). 끝 ≈ at+50
// ═══════════════════════════════════════════════════════════════════════════
export const MAG_LAND = 45;
export const MAG_LEN = 50;
const PW = 640, PH = 860, PT = (H - PH) / 2;
const pageBase: React.CSSProperties = { position: "absolute", inset: 0, background: "#FBF8F1", overflow: "hidden" };
const MagPage: React.FC<{ i: number; side: "L" | "R" }> = ({ i, side }) => {
  const imgs = ["real/port.jpg", "real/chinatown.jpg", "real/museum.jpg", "real/jjajang.jpg", "real/ghc_now.jpg", "real/zhajiang.jpg", "real/ghc_closed.jpg", "real/chunjang.jpg"];
  const cols = ["#E5532A", "#1E9BD7", "#6DB33F", "#F4B400", "#8A2BE2", "#EC2D5C"];
  const c = cols[(i * 2 + (side === "L" ? 0 : 1)) % cols.length];
  const im = imgs[(i * 2 + (side === "L" ? 0 : 1)) % imgs.length];
  const big = (i + (side === "L" ? 1 : 0)) % 2 === 0;
  return (
    <div style={pageBase}>
      <div style={{ position: "absolute", left: 44, top: 40, width: 150, height: 14, background: c }} />
      <div style={{ position: "absolute", left: 44, top: 66, fontFamily: "NeoHv", fontSize: 44, color: "#1b1b1b" }}>{["기획", "탐방", "인터뷰", "역사", "맛집", "특집", "현장", "기록"][(i * 2 + (side === "L" ? 0 : 1)) % 8]}</div>
      <div style={{ position: "absolute", left: 44, right: 44, top: 140, height: big ? 420 : 260, overflow: "hidden", borderRadius: 4 }}>
        <Img src={src(im)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      </div>
      <TextBars x={44} y={big ? 590 : 430} w={552} rows={big ? 9 : 15} seed={`mp${i}${side}`} lh={26} />
      <div style={{ position: "absolute", bottom: 20, [side === "L" ? "left" : "right"]: 36, fontFamily: "Georgia, serif", fontSize: 18, color: "#777" }}>{i * 2 + (side === "L" ? 2 : 3)}</div>
    </div>
  );
};
export const MagazineFlipParams = z.object({
  introDur: num(6, 1, 30, 1, "씬→표지 축소 시간", "timing", "f"),
  coverDur: num(15, 2, 60, 1, "표지 넘김 시간", "timing", "f"),
  pageDur: num(6, 1, 30, 1, "속지 한 장 넘김 시간", "timing", "f"),
  pages: num(4, 0, 12, 1, "넘기는 속지 수", "motion", "장"),
  startZoom: num(1.35, 1, 2.5, 0.05, "시작 확대(배)", "motion", "배"),
  perspective: num(2600, 600, 8000, 100, "원근 깊이(작을수록 과장)", "motion", "px"),
  bg: col("#2E3138", "배경 색"),
});
export type MagazineFlipP = z.infer<typeof MagazineFlipParams>;
/** land = 목표 페이지 착지 오프셋, len = 끝 */
export const magTiming = (p?: Partial<MagazineFlipP>) => {
  const P = def(MagazineFlipParams, p);
  const land = P.introDur + P.coverDur + P.pages * P.pageDur;
  return { cut: land, land, len: land + 5 };
};
export const MagazineFlip: React.FC<{ at: number; from: Node; target: Node; targetLeft?: Node; title?: string; bg?: string; pages?: number; coverLines?: string[]; p?: Partial<MagazineFlipP> }> = ({ at, from, target, targetLeft, title = "SEMOJI", bg: bgProp, pages: pagesProp, coverLines = ["특집: 짜장면의 탄생", "인천 차이나타운 100년"], p }) => {
  const P = def(MagazineFlipParams, { ...pick({ bg: bgProp, pages: pagesProp }), ...p });
  const pages = Math.round(P.pages), bg = P.bg;
  const f = useCurrentFrame();
  const g = f - at;
  if (g < 0) return <AbsoluteFill>{from}</AbsoluteFill>;
  const i0 = P.introDur, c1 = P.introDur + P.coverDur, pd = P.pageDur;
  const intro = lerp(g, 0, i0, 0, 1, Easing.out(Easing.cubic));
  const coverA = lerp(g, i0, c1, 0, -180, IN_OUT_CUBIC);
  const shift = lerp(g, i0, c1, -PW / 2, 0, IN_OUT_CUBIC);
  const leafAngle = (k: number) => (k === 0 ? coverA : lerp(g, c1 + (k - 1) * pd, c1 + k * pd, 0, -180, Easing.inOut(Easing.quad)));
  const cover = (
    <div style={{ ...pageBase, background: "#111" }}>
      <div style={{ position: "absolute", left: -(PH * 16 / 9 - PW) / 2, top: 0, width: PH * 16 / 9, height: PH }}>
        <div style={{ width: W, height: H, transform: `scale(${PH / H})`, transformOrigin: "0 0" }}>{from}</div>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 26, textAlign: "center", fontFamily: "Georgia, serif", fontWeight: 900, fontSize: 112, letterSpacing: 6, color: "#fff", textShadow: "0 4px 12px rgba(0,0,0,0.5)" }}>{title}</div>
      {coverLines.map((t, i) => <div key={i} style={{ position: "absolute", left: 36, bottom: 60 + i * 64, fontFamily: "NeoHv", fontSize: 40, color: i === 0 ? "#F7D84A" : "#fff", textShadow: "0 3px 8px rgba(0,0,0,0.7)" }}>{t}</div>)}
    </div>
  );
  const leaves = Array.from({ length: pages + 1 }).map((_, k) => {
    const a = leafAngle(k);
    const flipping = a < -0.5 && a > -179.5;
    const flipped = a <= -179.5;
    const z = flipping ? 200 : flipped ? 100 + k : 50 - k;
    const shade = Math.sin((-a * Math.PI) / 180);
    const front = k === 0 ? cover : <MagPage i={k} side="R" />;
    const back = k === pages ? (targetLeft ?? <MagPage i={k + 1} side="L" />) : <MagPage i={k + 1} side="L" />;
    return (
      <div key={k} style={{ position: "absolute", left: W / 2, top: PT, width: PW, height: PH, transformOrigin: "0% 50%", transform: `rotateY(${a}deg)`, transformStyle: "preserve-3d", zIndex: z }}>
        <div style={{ position: "absolute", inset: 0, backfaceVisibility: "hidden", WebkitBackfaceVisibility: "hidden" }}>
          {front}
          <div style={{ position: "absolute", inset: 0, background: `linear-gradient(90deg, rgba(0,0,0,${0.25 + 0.35 * shade}) 0%, rgba(0,0,0,${0.35 * shade}) 40%, rgba(0,0,0,0) 100%)` }} />
        </div>
        <div style={{ position: "absolute", inset: 0, transform: "rotateY(180deg)", backfaceVisibility: "hidden", WebkitBackfaceVisibility: "hidden" }}>
          {back}
          <div style={{ position: "absolute", inset: 0, background: `linear-gradient(270deg, rgba(0,0,0,${0.25 + 0.35 * shade}) 0%, rgba(0,0,0,${0.3 * shade}) 40%, rgba(0,0,0,0) 100%)` }} />
        </div>
      </div>
    );
  });
  const openK = lerp(g, i0, i0 + 6, 0, 1);
  return (
    <AbsoluteFill style={{ background: bg }}>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 55%, rgba(255,255,255,0.10) 0%, rgba(0,0,0,0.35) 90%)" }} />
      <AbsoluteFill style={{ transform: `translateX(${shift}px) scale(${P.startZoom - (P.startZoom - 1) * intro})`, perspective: P.perspective, perspectiveOrigin: `${W / 2}px ${H / 2}px` }}>
        {/* 오른쪽 바닥: 목표 페이지 */}
        <div style={{ position: "absolute", left: W / 2, top: PT, width: PW, height: PH, boxShadow: "0 20px 40px rgba(0,0,0,0.5)", zIndex: 1 }}>
          <div style={pageBase}>{target}</div>
          <div style={{ position: "absolute", inset: 0, background: "linear-gradient(90deg, rgba(0,0,0,0.28) 0%, rgba(0,0,0,0) 12%)" }} />
        </div>
        {/* 왼쪽 바닥(책 뒤표지 안쪽) — 표지가 열리면 보인다 */}
        <div style={{ position: "absolute", left: W / 2 - PW, top: PT, width: PW, height: PH, background: "#E9E4D8", opacity: openK, boxShadow: "0 20px 40px rgba(0,0,0,0.5)", zIndex: 1 }} />
        {leaves}
      </AbsoluteFill>
      {g < i0 && <AbsoluteFill style={{ opacity: 1 - intro, transform: `scale(${1 - 0.25 * intro})` }}>{from}</AbsoluteFill>}
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 6. 아크 와이프 아이리스 — 2겹 초승달(외곽 링 #78B898, 안쪽 #58A878)이 왼쪽에서 13f easeInOut
//    으로 화면을 덮음(컷) → 밝은 링 1회 더 통과 9f → center 에 원형 마스크 r 0→radius 6f ease-out
//    + 반투명 흰 링(α0.25). 반투명 원판은 오브젝트 배경으로 남는다.   컷 = at+13, 끝 = at+28
// ═══════════════════════════════════════════════════════════════════════════
export const ARC_CUT = 13;
export const ARC_LEN = 28;
export const ArcWipeIrisParams = z.object({
  wipeDur: num(13, 2, 60, 1, "초승달 덮는 시간", "timing", "f"),
  ringDur: num(9, 1, 40, 1, "밝은 링 통과 시간", "timing", "f"),
  irisDur: num(6, 1, 40, 1, "원 마스크 열리는 시간", "timing", "f"),
  radius: num(520, 40, 1200, 10, "원 마스크 반지름", "size", "px"),
  lag: num(150, 0, 600, 10, "두 겹 초승달 간격", "size", "px"),
  ringWidth: num(130, 0, 400, 5, "통과 링 두께", "size", "px"),
  haloOpacity: num(0.25, 0, 1, 0.05, "반투명 원판·링 불투명도", "look"),
  objectDelay: num(3, 0, 20, 1, "오브젝트 팝 지연", "timing", "f"),
  objectStart: num(0.4, 0, 1, 0.05, "오브젝트 시작 크기(배)", "motion", "배"),
  overshoot: num(1.06, 1, 1.5, 0.01, "오브젝트 오버슈트 크기(배)", "motion", "배"),
  outer: col("#78B898", "바깥 초승달 색"),
  inner: col("#58A878", "안쪽 초승달 색"),
  ringColor: col("#9ED3B6", "통과 링 색"),
});
export type ArcWipeIrisP = z.infer<typeof ArcWipeIrisParams>;
export const arcTiming = (p?: Partial<ArcWipeIrisP>) => {
  const P = def(ArcWipeIrisParams, p);
  return { cut: P.wipeDur, len: P.wipeDur + P.ringDur + P.irisDur };
};
export const ArcWipeIris: React.FC<{ at: number; from: Node; reveal?: Node; object?: Node; center?: [number, number]; radius?: number; outer?: string; inner?: string; ringColor?: string; p?: Partial<ArcWipeIrisP> }> = ({ at, from, reveal, object, center = [1500, 520], radius, outer, inner, ringColor, p }) => {
  const P = def(ArcWipeIrisParams, { ...pick({ radius, outer, inner, ringColor }), ...p });
  const { cut } = arcTiming(P);
  const f = useCurrentFrame();
  const g = f - at;
  const id = useSvgId("arc");
  if (g < 0) return <AbsoluteFill>{from}</AbsoluteFill>;
  const R = 1500;
  const ring1 = cut + P.ringDur, iris1 = ring1 + P.irisDur, objAt = ring1 + P.objectDelay;
  const cx = lerp(g, 0, cut, -R - 40, W / 2 + 60, Easing.inOut(Easing.quad));
  const lag = P.lag;
  const ringCx = lerp(g, cut, ring1, -R - 80, W + 80 - R, Easing.inOut(Easing.sin));
  const ringOp = g < cut ? 0 : kf(g, cut, [0, (7 / 9) * P.ringDur, P.ringDur], [1, 1, 0]);
  const [ox, oy] = center;
  const r = lerp(g, ring1, iris1, 0, P.radius, EXPO_OUT);
  const halo = `rgba(255,255,255,${P.haloOpacity})`;
  return (
    <AbsoluteFill>
      {g < cut && from}
      <svg width={W} height={H} style={{ position: "absolute", inset: 0 }}>
        <defs>
          <clipPath id={`${id}c`}><circle cx={ox} cy={oy} r={Math.max(0.01, r)} /></clipPath>
        </defs>
        {g < cut ? (
          <>
            <circle cx={cx} cy={H / 2} r={R} fill={P.outer} />
            <circle cx={cx - lag} cy={H / 2} r={R} fill={P.inner} />
          </>
        ) : <rect width={W} height={H} fill={P.inner} />}
        {ringOp > 0 && P.ringWidth > 0 && <circle cx={ringCx} cy={H / 2} r={R} fill="none" stroke={P.ringColor} strokeWidth={P.ringWidth} opacity={ringOp} />}
        {g >= ring1 && (
          <>
            {reveal ? null : <circle cx={ox} cy={oy} r={r} fill={halo} />}
            <circle cx={ox} cy={oy} r={r + 22} fill="none" stroke={halo} strokeWidth={28} />
          </>
        )}
      </svg>
      {reveal && g >= ring1 && <AbsoluteFill style={{ clipPath: `circle(${r}px at ${ox}px ${oy}px)` }}>{reveal}</AbsoluteFill>}
      {object && g >= objAt && <AbsoluteFill style={{ transformOrigin: `${ox}px ${oy}px`, transform: `scale(${kf(g, objAt, [0, 3, 5], [P.objectStart, P.overshoot, 1])})` }}>{object}</AbsoluteFill>}
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 7. 아이리스 페더 — at 에서 어두운 새 씬이 부드러운 원형 마스크(r≈280, feather≈80)로 16f 페이드인,
//    바깥은 ~20% 밝기. openAt 을 주면 openDur(기본 60f) 동안 비네트가 물러나며 완전 개방.
//    컷 = at (A 는 at 에 사라짐)
// ═══════════════════════════════════════════════════════════════════════════
export const IrisFeatherParams = z.object({
  fadeIn: num(16, 1, 60, 1, "원 마스크 페이드인 시간", "timing", "f"),
  r: num(280, 20, 1000, 10, "밝은 원 반지름", "size", "px"),
  feather: num(80, 0, 500, 5, "가장자리 부드러움", "size", "px"),
  outside: num(0.2, 0, 1, 0.05, "바깥 밝기", "look"),
  openDur: num(60, 1, 180, 1, "완전 개방 시간", "timing", "f"),
  openEase: choice("cubic", EASE_KEYS, "개방 이징", "motion"),
});
export type IrisFeatherP = z.infer<typeof IrisFeatherParams>;
export const IrisFeather: React.FC<{ at: number; from?: Node; to: Node; cx: number; cy: number; r?: number; feather?: number; outside?: number; openAt?: number; openDur?: number; fadeIn?: number; p?: Partial<IrisFeatherP> }> = ({ at, from, to, cx, cy, r: rProp, feather: fProp, outside: oProp, openAt, openDur: odProp, fadeIn: fiProp, p }) => {
  const P = def(IrisFeatherParams, { ...pick({ r: rProp, feather: fProp, outside: oProp, openDur: odProp, fadeIn: fiProp }), ...p });
  const { r, feather, outside, openDur, fadeIn } = P;
  const f = useCurrentFrame();
  const g = f - at;
  if (g < 0) return <AbsoluteFill>{from}</AbsoluteFill>;
  const op = lerp(g, 0, fadeIn, 0, 1, Easing.inOut(Easing.sin));
  const ok = openAt !== undefined ? lerp(f, openAt, openAt + openDur, 0, 1, EASES[P.openEase]) : 0;
  const rr = r + (2300 - r) * ok, ff = feather + 500 * ok;
  const outB = outside + (1 - outside) * ok;
  const mask = `radial-gradient(circle at ${cx}px ${cy}px, #000 ${rr}px, transparent ${rr + ff}px)`;
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <AbsoluteFill style={{ opacity: op * (ok > 0.999 ? 0 : 1), filter: `brightness(${outB})` }}>{to}</AbsoluteFill>
      <AbsoluteFill style={{ opacity: op, WebkitMaskImage: mask, maskImage: mask }}>{to}</AbsoluteFill>
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 8. 에너지 슬래시 — 민트 #B5F5F0 광선 3~4줄이 대각으로 베며 10f 굵어짐 → 민트 풀 플래시 2f(컷)
//    → 중앙에서 찢긴 가장자리 구멍이 3f 확장하며 새 씬 노출 → 남은 광선이 점선 조각으로 부서지며 10f 페이드.
//    컷 = at+10, 끝 = at+25
// ═══════════════════════════════════════════════════════════════════════════
export const SLASH_CUT = 10;
export const SLASH_LEN = 25;
const BEAMS = [{ off: -300, s: 0, w: 70 }, { off: -70, s: 2, w: 130 }, { off: 150, s: 3, w: 90 }, { off: 360, s: 5, w: 56 }];
const jaggedHole = (R: number, cx: number, cy: number, seed: string) => {
  // 불규칙 다중 스케일 노이즈 가장자리(찢긴 종이/폭발 테두리). 규칙적 스파이크 없음
  const N = 72, pts: string[] = [];
  for (let i = 0; i < N; i++) {
    const a = (i / N) * Math.PI * 2;
    const n1 = random(`${seed}a${i}`), n2 = random(`${seed}b${Math.floor(i / 4)}`), n3 = random(`${seed}c${Math.floor(i / 12)}`);
    const k = 0.78 + 0.12 * n1 + 0.1 * n2 + 0.08 * n3 * Math.sin(a * 3 + n3 * 6);
    pts.push(`${cx + Math.cos(a) * R * k * 1.15},${cy + Math.sin(a) * R * k * 0.9}`);
  }
  return pts.join(" ");
};
export const EnergySlashParams = z.object({
  chargeDur: num(10, 2, 40, 1, "광선 굵어지는 시간(=컷)", "timing", "f"),
  drawDur: num(3, 1, 20, 1, "광선 그어지는 시간", "timing", "f"),
  beamStagger: num(1, 0, 3, 0.1, "광선 시작 스태거(배)", "timing", "배"),
  flashHold: num(2, 1, 20, 1, "풀 플래시 유지", "timing", "f"),
  holeDur: num(3, 1, 20, 1, "찢긴 구멍 확장 시간", "timing", "f"),
  fadeDur: num(12, 1, 60, 1, "잔여 광선 페이드 시간", "timing", "f"),
  beamWidth: num(1, 0.2, 4, 0.05, "광선 굵기(배)", "size", "배"),
  glow: num(10, 0, 40, 1, "광선 글로우 블러", "look", "px"),
  dashSpeed: num(60, 0, 200, 5, "점선 조각 흐르는 속도", "motion", "px/f"),
  angle: num(-28, -90, 90, 1, "광선 각도", "motion", "°"),
  color: col("#B5F5F0", "광선·플래시 색"),
});
export type EnergySlashP = z.infer<typeof EnergySlashParams>;
export const slashTiming = (p?: Partial<EnergySlashP>) => {
  const P = def(EnergySlashParams, p);
  const holeAt = P.chargeDur + P.flashHold;
  return { cut: P.chargeDur, holeAt, len: holeAt + 1 + P.fadeDur };
};
export const EnergySlash: React.FC<{ at: number; from: Node; to: Node; color?: string; angle?: number; p?: Partial<EnergySlashP> }> = ({ at, from, to, color: cProp, angle: aProp, p }) => {
  const P = def(EnergySlashParams, { ...pick({ color: cProp, angle: aProp }), ...p });
  const { cut, holeAt: h0, len: LEN } = slashTiming(P);
  const color = P.color, angle = P.angle;
  const f = useCurrentFrame();
  const g = f - at;
  const id = useSvgId("es");
  if (g < 0) return <AbsoluteFill>{from}</AbsoluteFill>;
  if (g > LEN) return <AbsoluteFill>{to}</AbsoluteFill>;
  const L = 2800;
  const h1 = h0 + P.holeDur, r0 = h0 + 1; // 구멍 완성 / 잔여 광선 시작
  const R = lerp(g, h0, h1, 0, 1500, Easing.out(Easing.quad));
  const hole = jaggedHole(R, W / 2, H / 2, "hole");
  const flashOp = g < cut ? 0 : g < h1 ? 1 : 0;
  return (
    <AbsoluteFill>
      {g < cut ? from : to}
      <svg width={W} height={H} style={{ position: "absolute", inset: 0, overflow: "visible" }}>
        <defs>
          <mask id={`${id}m`} maskUnits="userSpaceOnUse" x={0} y={0} width={W} height={H}>
            <rect width={W} height={H} fill="#fff" />
            {g >= h0 && <polygon points={hole} fill="#000" />}
          </mask>
          <filter id={`${id}glow`} x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation={P.glow} result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
        </defs>
        {/* 슬래시 광선: 한쪽에서 3f 만에 가로질러 그어지고 10f 동안 굵어짐 */}
        {g < h0 && (
          <g transform={`translate(${W / 2},${H / 2}) rotate(${angle})`} filter={`url(#${id}glow)`}>
            {BEAMS.map((b, i) => {
              const s0 = Math.min(cut - 1, b.s * P.beamStagger);
              if (g < s0) return null;
              const len = lerp(g, s0, s0 + P.drawDur, 0, L, Easing.out(Easing.quad));
              const w = lerp(g, s0, cut, 3, b.w * P.beamWidth, Easing.in(Easing.quad));
              return (
                <g key={i}>
                  <rect x={-L / 2} y={b.off - w / 2} width={len} height={w} fill={color} opacity={0.9} />
                  <rect x={-L / 2} y={b.off - w * 0.18} width={len} height={w * 0.36} fill="#fff" />
                </g>
              );
            })}
          </g>
        )}
        {/* 풀 플래시 + 찢긴 구멍 */}
        {flashOp > 0 && (
          <g mask={`url(#${id}m)`}>
            <rect width={W} height={H} fill={color} />
            <rect width={W} height={H} fill="#fff" opacity={g < h0 ? 0.35 : 0} />
          </g>
        )}
        {g >= h0 && g < h1 + 1 && <polygon points={hole} fill="none" stroke="#fff" strokeWidth={lerp(g, h0, h1, 26, 8)} strokeLinejoin="miter" opacity={g < h1 ? 1 : 0.5} />}
        {/* 잔여 광선 → 점선 조각 페이드 */}
        {g >= r0 && (
          <g transform={`translate(${W / 2},${H / 2}) rotate(${angle})`} opacity={lerp(g, r0, LEN, 1, 0, Easing.in(Easing.quad))}>
            {BEAMS.map((b, i) => {
              const w = lerp(g, r0, LEN, b.w * P.beamWidth * 0.35, 3);
              return <line key={i} x1={-L / 2} y1={b.off} x2={L / 2} y2={b.off} stroke={i % 2 ? "#fff" : color} strokeWidth={w} strokeDasharray={`${lerp(g, r0, LEN, 220, 40)} ${lerp(g, r0, LEN, 40, 110)}`} strokeDashoffset={-(g - r0) * P.dashSpeed * (i % 2 ? 1 : -1)} strokeLinecap="round" />;
            })}
          </g>
        )}
      </svg>
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 9. 화이트 딥: 흰색으로 4f → 부드러운 빛 덩어리와 함께 6f 홀드(컷=at+4) → 10f 디졸브. 끝 = at+20
//    딥 투 블랙: 2f 어두워짐 → 2f 검정(컷=at+2) → 4f 페이드인. 끝 = at+8
// ═══════════════════════════════════════════════════════════════════════════
export const WHITEDIP_CUT = 4;
export const WHITEDIP_LEN = 20;
export const WhiteDipParams = z.object({
  inDur: num(4, 1, 30, 1, "하얘지는 시간(=컷)", "timing", "f"),
  hold: num(6, 0, 40, 1, "흰 화면 유지", "timing", "f"),
  outDur: num(10, 1, 60, 1, "새 씬 디졸브 시간", "timing", "f"),
  blobs: num(1, 0, 2, 0.05, "빛 덩어리 세기(배)", "look", "배"),
  blobDrift: num(26, 0, 120, 2, "빛 덩어리 흔들림 거리", "motion", "px"),
  blobBlur: num(20, 0, 80, 1, "빛 덩어리 블러", "look", "px"),
  tint: col("#FFFFFF", "딥 색"),
});
export type WhiteDipP = z.infer<typeof WhiteDipParams>;
export const whiteDipTiming = (p?: Partial<WhiteDipP>) => {
  const P = def(WhiteDipParams, p);
  return { cut: P.inDur, len: P.inDur + P.hold + P.outDur };
};
export const WhiteDip: React.FC<{ at: number; from: Node; to: Node; tint?: string; p?: Partial<WhiteDipP> }> = ({ at, from, to, tint: tProp, p }) => {
  const P = def(WhiteDipParams, { ...pick({ tint: tProp }), ...p });
  const { cut, len } = whiteDipTiming(P);
  const h1 = cut + P.hold;
  const f = useCurrentFrame();
  const g = f - at;
  const a = g < 0 ? 0 : g < cut ? lerp(g, 0, cut, 0, 1, Easing.in(Easing.quad)) : g < h1 ? 1 : lerp(g, h1, len, 1, 0, Easing.inOut(Easing.sin));
  // 빛 덩어리: 딥 절반 지점에서 나타나 끝 4f 전에 사라짐(기본 at+2 .. at+16, 키 [0,3,10,14])
  const bs = cut / 2, span = len - 4 - bs;
  const blobs = P.blobs > 0 && span > 0 && g >= bs && g < bs + span;
  const kk = span / 14;
  return (
    <AbsoluteFill>
      {g < cut ? from : to}
      {a > 0 && <AbsoluteFill style={{ background: P.tint, opacity: a }} />}
      {blobs && (
        <AbsoluteFill style={{ opacity: Math.min(1, a * kf(g, bs, [0, 3 * kk, 10 * kk, 14 * kk], [0, 1, 1, 0]) * P.blobs), mixBlendMode: "multiply" }}>
          {[[520, 380, 420, "255,226,190"], [1380, 620, 520, "210,232,255"], [980, 260, 300, "255,214,232"], [760, 820, 360, "240,240,210"]].map(([x, y, r, c], i) => {
            const dx = Math.sin((g + i * 5) / 6) * P.blobDrift, dy = Math.cos((g + i * 3) / 7) * P.blobDrift * (18 / 26);
            const rr = (r as number) * (1 + 0.05 * Math.sin(g / 4 + i));
            return <div key={i} style={{ position: "absolute", left: (x as number) - rr + dx, top: (y as number) - rr + dy, width: rr * 2, height: rr * 2, borderRadius: "50%", background: `radial-gradient(circle, rgba(${c},0.6) 0%, rgba(${c},0) 70%)`, filter: `blur(${P.blobBlur}px)` }} />;
          })}
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};
export const BLACKDIP_CUT = 2;
export const BLACKDIP_LEN = 8;
export const DipToBlackParams = z.object({
  inDur: num(2, 1, 30, 1, "어두워지는 시간(=컷)", "timing", "f"),
  startDark: num(0.45, 0, 1, 0.05, "첫 프레임 어둡기", "look"),
  hold: num(2, 0, 40, 1, "검정 유지", "timing", "f"),
  outDur: num(4, 1, 60, 1, "새 씬 페이드인 시간", "timing", "f"),
  color: col("#000000", "딥 색"),
});
export type DipToBlackP = z.infer<typeof DipToBlackParams>;
export const blackDipTiming = (p?: Partial<DipToBlackP>) => {
  const P = def(DipToBlackParams, p);
  return { cut: P.inDur, len: P.inDur + P.hold + P.outDur };
};
export const DipToBlack: React.FC<{ at: number; from: Node; to: Node; p?: Partial<DipToBlackP> }> = ({ at, from, to, p }) => {
  const P = def(DipToBlackParams, p);
  const { cut, len } = blackDipTiming(P);
  const h1 = cut + P.hold;
  const f = useCurrentFrame();
  const g = f - at;
  const a = g < 0 ? 0 : g < cut ? lerp(g, 0, cut, P.startDark, 1) : g < h1 ? 1 : lerp(g, h1, len, 1, 0, Easing.out(Easing.quad));
  return (
    <AbsoluteFill>
      {g < cut ? from : to}
      {a > 0 && <AbsoluteFill style={{ background: P.color, opacity: a }} />}
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 10. 오렌지 플레어 — 오른쪽에서 주황/분홍 빛이 부풀어 화면 ~60% 를 씻으며 10f 크로스.
//     FlickerLeak 보다 부드러움(깜빡임 없음). 컷(크로스 중심) = at+5, 끝 = at+10(+꼬리 6f)
// ═══════════════════════════════════════════════════════════════════════════
export const FLARE_CUT = 5;
export const FLARE_LEN = 16;
export const OrangeFlareParams = z.object({
  crossDur: num(10, 2, 60, 1, "크로스 디졸브 시간(컷=절반)", "timing", "f"),
  tail: num(6, 0, 40, 1, "빛 꼬리 시간", "timing", "f"),
  growDur: num(6, 1, 30, 1, "빛 부풀어 오르는 시간", "timing", "f"),
  reachStart: num(25, 0, 100, 1, "빛 시작 크기", "size", "%"),
  reach: num(62, 10, 150, 1, "빛 최대 크기", "size", "%"),
  intensity: num(1, 0, 1, 0.05, "빛 세기", "look"),
  afterglow: num(0.55, 0, 1, 0.05, "크로스 끝 잔광 세기", "look"),
  y: num(46, 0, 100, 1, "빛 세로 위치", "motion", "%"),
  tintMix: num(0.45, 0, 1, 0.05, "주황 소프트라이트 세기", "look"),
});
export type OrangeFlareP = z.infer<typeof OrangeFlareParams>;
export const flareTiming = (p?: Partial<OrangeFlareP>) => {
  const P = def(OrangeFlareParams, p);
  return { cut: P.crossDur / 2, len: P.crossDur + P.tail };
};
export const OrangeFlare: React.FC<{ at: number; from: Node; to: Node; p?: Partial<OrangeFlareP> }> = ({ at, from, to, p }) => {
  const P = def(OrangeFlareParams, p);
  const f = useCurrentFrame();
  const g = f - at;
  if (g < 0) return <AbsoluteFill>{from}</AbsoluteFill>;
  const c = P.crossDur, e = c + Math.max(0.01, P.tail);
  const x = lerp(g, 0, c, 0, 1, Easing.inOut(Easing.sin));
  const peak = P.intensity * kf(g, 0, [0, c / 2, c, e], [0, 1, P.afterglow, 0], Easing.inOut(Easing.sin));
  const reach = lerp(g, 0, P.growDur, P.reachStart, P.reach, Easing.out(Easing.quad));
  return (
    <AbsoluteFill>
      {from}
      <AbsoluteFill style={{ opacity: x }}>{to}</AbsoluteFill>
      <AbsoluteFill style={{ mixBlendMode: "screen", opacity: peak, background: `radial-gradient(ellipse ${reach * 1.4}% ${reach * 1.6}% at 104% ${P.y}%, rgba(255,246,228,1) 0%, rgba(255,180,90,0.95) 30%, rgba(255,120,150,0.4) 62%, rgba(255,110,140,0) 100%)` }} />
      <AbsoluteFill style={{ mixBlendMode: "soft-light", opacity: peak * P.tintMix, background: "linear-gradient(270deg, rgba(255,150,70,1) 0%, rgba(255,120,160,0.6) 45%, rgba(0,0,0,0) 75%)" }} />
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 11. 만화 패널 — at 에 어두운 캔버스 배경으로 컷, ~10° 기울어진 평행사변형 흑백 패널(흰 테두리 6px)
//     이 서로 다른 화면 가장자리에서 8f easeOut 으로 들어옴, 스태거 9f. 마지막 패널만 컬러.
//     컷 = at, 끝 = at + (n-1)*stagger + 8
// ═══════════════════════════════════════════════════════════════════════════
export type MangaPanel = { img: string; pts: [number, number][]; from: "left" | "right" | "top" | "bottom"; pos?: string };
export const MANGA_DEFAULT_LAYOUT: Omit<MangaPanel, "img">[] = [
  { pts: [[40, 40], [1060, 40], [980, 500], [40, 500]], from: "left" },
  { pts: [[1100, 40], [1880, 40], [1880, 500], [1020, 500]], from: "top" },
  { pts: [[40, 540], [660, 540], [572, 1040], [40, 1040]], from: "bottom" },
  { pts: [[700, 540], [1260, 540], [1172, 1040], [612, 1040]], from: "bottom" },
  { pts: [[1300, 540], [1880, 540], [1880, 1040], [1212, 1040]], from: "right" },
];
export const MangaPanelsParams = z.object({
  stagger: num(9, 0, 40, 1, "패널 스태거 간격", "timing", "f"),
  slide: num(8, 1, 40, 1, "패널 날아드는 시간", "timing", "f"),
  travel: num(1, 0.1, 2, 0.05, "날아드는 거리(화면 배)", "motion", "배"),
  border: num(12, 0, 40, 1, "흰 테두리 두께(보이는 폭은 절반)", "size", "px"),
  contrast: num(1.35, 0.5, 3, 0.05, "흑백 패널 대비", "look"),
  shadow: num(0.6, 0, 1, 0.05, "패널 그림자 진하기", "look"),
  colorLast: flag(true, "마지막 패널만 컬러", "look"),
  bg: col("#26231F", "캔버스 배경 색"),
});
export type MangaPanelsP = z.infer<typeof MangaPanelsParams>;
export const mangaTiming = (p?: Partial<MangaPanelsP>, n = 5) => {
  const P = def(MangaPanelsParams, p);
  return { cut: 0, len: (n - 1) * P.stagger + P.slide };
};
export const MangaPanels: React.FC<{ at: number; from: Node; panels: MangaPanel[]; stagger?: number; slide?: number; colorLast?: boolean; p?: Partial<MangaPanelsP> }> = ({ at, from, panels, stagger: sProp, slide: slProp, colorLast: clProp, p: pp }) => {
  const P = def(MangaPanelsParams, { ...pick({ stagger: sProp, slide: slProp, colorLast: clProp }), ...pp });
  const { stagger, slide, colorLast } = P;
  const f = useCurrentFrame();
  const g = f - at;
  const id = useSvgId("mg");
  if (g < 0) return <AbsoluteFill>{from}</AbsoluteFill>;
  return (
    <AbsoluteFill style={{ background: P.bg }}>
      <svg width={W} height={H} style={{ position: "absolute", inset: 0 }}>
        <defs>
          <filter id={`${id}cv`}><feTurbulence type="fractalNoise" baseFrequency="0.55 0.5" numOctaves={2} seed={9} /><feColorMatrix values="0 0 0 0 0.55  0 0 0 0 0.5  0 0 0 0 0.44  0 0 0 0.55 -0.2" /></filter>
          <filter id={`${id}cv2`}><feTurbulence type="fractalNoise" baseFrequency="0.008" numOctaves={3} seed={2} /><feColorMatrix values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.9 -0.25" /></filter>
          {panels.map((p, i) => <clipPath key={i} id={`${id}c${i}`}><polygon points={p.pts.map((q) => q.join(",")).join(" ")} /></clipPath>)}
        </defs>
        <rect width={W} height={H} filter={`url(#${id}cv)`} />
        <rect width={W} height={H} filter={`url(#${id}cv2)`} />
        {panels.map((p, i) => {
          const a = i * stagger;
          if (g < a) return null;
          const k = lerp(g, a, a + slide, 1, 0, Easing.out(Easing.cubic));
          const kt = k * P.travel;
          const dx = p.from === "left" ? -W * kt : p.from === "right" ? W * kt : 0;
          const dy = p.from === "top" ? -H * kt : p.from === "bottom" ? H * kt : 0;
          const xs = p.pts.map((q) => q[0]), ys = p.pts.map((q) => q[1]);
          const bx = Math.min(...xs), by = Math.min(...ys), bw = Math.max(...xs) - bx, bh = Math.max(...ys) - by;
          const color = colorLast && i === panels.length - 1;
          return (
            <g key={i} transform={`translate(${dx},${dy})`} style={{ filter: `drop-shadow(0 10px 14px rgba(0,0,0,${P.shadow}))` }}>
              <g clipPath={`url(#${id}c${i})`}>
                <image href={src(p.img)} x={bx} y={by} width={bw} height={bh} preserveAspectRatio="xMidYMid slice" style={{ filter: color ? "saturate(1.15)" : `grayscale(1) contrast(${P.contrast}) brightness(1.05)` }} />
              </g>
              <polygon points={p.pts.map((q) => q.join(",")).join(" ")} fill="none" stroke="#fff" strokeWidth={P.border} clipPath={`url(#${id}c${i})`} />
            </g>
          );
        })}
      </svg>
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 12. 분할 패널 와이프 — 왼쪽 패널(#009DE0) x=0 에서 폭 0→960, 18f easeInOutCubic
//     → rightAt(기본 at+60) 에 오른쪽 패널(#32973C) x=968 폭 0→952, 16f. 가려지지 않은 이전 씬은 35% 로 어둡게.
//     각 패널: 상단 흰 타이틀 박스 + content 슬롯(패널 좌상단 기준 좌표). 컷 없음(오버레이형)
// ═══════════════════════════════════════════════════════════════════════════
export type SplitSide = { title: string; content?: Node; color?: string };
export const SplitPanelWipeParams = z.object({
  leftDur: num(18, 1, 60, 1, "왼쪽 패널 펼침 시간", "timing", "f"),
  rightDelay: num(60, 0, 200, 1, "오른쪽 패널 등장 지연", "timing", "f"),
  rightDur: num(16, 1, 60, 1, "오른쪽 패널 펼침 시간", "timing", "f"),
  titleDelay: num(10, 0, 40, 1, "타이틀 박스 지연", "timing", "f"),
  titleDur: num(8, 1, 30, 1, "타이틀 박스 펼침 시간", "timing", "f"),
  dim: num(0.35, 0, 1, 0.05, "이전 씬 어둡기(밝기)", "look"),
  gap: num(8, 0, 80, 1, "두 패널 사이 틈", "size", "px"),
  leftColor: col("#009DE0", "왼쪽 패널 색"),
  rightColor: col("#32973C", "오른쪽 패널 색"),
});
export type SplitPanelWipeP = z.infer<typeof SplitPanelWipeParams>;
export const SplitPanelWipe: React.FC<{ at: number; from: Node; left: SplitSide; right?: SplitSide; rightAt?: number; p?: Partial<SplitPanelWipeP> }> = ({ at, from, left, right, rightAt, p }) => {
  const P = def(SplitPanelWipeParams, p);
  const f = useCurrentFrame();
  const g = f - at;
  const ra = rightAt ?? at + P.rightDelay;
  const dim = lerp(g, 0, P.leftDur, 1, P.dim, Easing.out(Easing.quad));
  const panel = (x: number, fullW: number, wv: number, side: SplitSide, def: string, t0: number) => {
    if (wv <= 0.5) return null;
    const c = side.color ?? def;
    const tk = lerp(f, t0 + P.titleDelay, t0 + P.titleDelay + P.titleDur, 0, 1, EXPO_OUT);
    return (
      <div style={{ position: "absolute", left: x, top: 0, width: wv, height: H, overflow: "hidden", background: c, boxShadow: "8px 0 20px rgba(0,0,0,0.3)" }}>
        <div style={{ position: "absolute", left: 0, top: 0, width: fullW, height: H }}>
          <div style={{ position: "absolute", left: 60, right: 60, top: 70, height: 120, background: "#fff", borderRadius: 14, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "NeoHv", fontSize: 60, color: c, transform: `scaleX(${0.3 + 0.7 * tk})`, opacity: tk, boxShadow: "0 8px 16px rgba(0,0,0,0.25)" }}>{side.title}</div>
          <div style={{ position: "absolute", left: 60, right: 60, top: 230, bottom: 60 }}>{side.content}</div>
        </div>
      </div>
    );
  };
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ filter: g >= 0 ? `brightness(${dim})` : undefined }}>{from}</AbsoluteFill>
      {g >= 0 && panel(0, W / 2, lerp(g, 0, P.leftDur, 0, W / 2, IN_OUT_CUBIC), left, P.leftColor, at)}
      {right && f >= ra && panel(W / 2 + P.gap, W / 2 - P.gap, lerp(f, ra, ra + P.rightDur, 0, W / 2 - P.gap, IN_OUT_CUBIC), right, P.rightColor, ra)}
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 13a. 버티컬 푸시 — 새 씬이 아래에서 밀고 올라와 옛 씬을 위로 밀어냄, 10f. 컷 = 진행 50%
// ═══════════════════════════════════════════════════════════════════════════
export const VerticalPushParams = z.object({
  dur: num(10, 1, 60, 1, "밀어내는 시간(컷=절반)", "timing", "f"),
  dir: choice("up", ["up", "down"] as const, "미는 방향", "motion"),
  ease: choice("cubic", EASE_KEYS, "이징", "motion"),
  outTravel: num(1, 0, 1.5, 0.05, "옛 씬 밀려나는 거리(화면 배)", "motion", "배"),
});
export type VerticalPushP = z.infer<typeof VerticalPushParams>;
export const VerticalPush: React.FC<{ at: number; from: Node; to: Node; dur?: number; dir?: "up" | "down"; p?: Partial<VerticalPushP> }> = ({ at, from, to, dur: dProp, dir: drProp, p: pp }) => {
  const P = def(VerticalPushParams, { ...pick({ dur: dProp, dir: drProp }), ...pp });
  const { dur, dir } = P;
  const f = useCurrentFrame();
  const g = f - at;
  if (g < 0) return <AbsoluteFill>{from}</AbsoluteFill>;
  if (g >= dur) return <AbsoluteFill>{to}</AbsoluteFill>;
  const p = lerp(g, 0, dur, 0, 1, EASES[P.ease]);
  const s = dir === "up" ? -1 : 1;
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ transform: `translateY(${s * p * H * P.outTravel}px)` }}>{from}</AbsoluteFill>
      <AbsoluteFill style={{ transform: `translateY(${-s * (1 - p) * H}px)` }}>{to}</AbsoluteFill>
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 13b. 패럴랙스 푸시 — 새 씬 가장자리가 20f 동안 오른쪽→왼쪽으로 화면을 가로지르고(easeInOutSine),
//      레이어마다 이동량이 다르다: 배경 ~740px(최고 ~58px/f), 전경 ~1530px(최고 ~120px/f).
//      layers 는 뒤→앞 순서. speeds 생략 시 [0.385, …, 0.8] (×W 이동량)
// ═══════════════════════════════════════════════════════════════════════════
export const ParallaxPushParams = z.object({
  dur: num(20, 2, 90, 1, "가로지르는 시간", "timing", "f"),
  bgSpeed: num(0.385, 0, 1.5, 0.005, "배경 이동량(화면 폭 배)", "motion", "배"),
  fgSpeed: num(0.8, 0, 2, 0.01, "전경 이동량(화면 폭 배)", "motion", "배"),
  ease: choice("sin", EASE_KEYS, "이징", "motion"),
});
export type ParallaxPushP = z.infer<typeof ParallaxPushParams>;
export const ParallaxPush: React.FC<{ at: number; fromLayers: Node[]; toLayers: Node[]; dur?: number; speeds?: number[]; p?: Partial<ParallaxPushP> }> = ({ at, fromLayers, toLayers, dur: dProp, speeds, p: pp }) => {
  const P = def(ParallaxPushParams, { ...pick({ dur: dProp }), ...pp });
  const f = useCurrentFrame();
  const g = f - at;
  const p = lerp(g, 0, P.dur, 0, 1, EASES[P.ease]);
  const sp = (n: number, i: number) => speeds?.[i] ?? (n === 1 ? P.bgSpeed : P.bgSpeed + (P.fgSpeed - P.bgSpeed) * (i / (n - 1)));
  const edge = W * (1 - p); // 새 씬 배경의 왼쪽 경계
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      {/* 옛 씬: 배경은 경계 왼쪽만 보임 */}
      <AbsoluteFill style={{ clipPath: `inset(0 ${W - edge}px 0 0)` }}>
        <AbsoluteFill style={{ transform: `translateX(${-p * W * sp(fromLayers.length, 0)}px)` }}>{fromLayers[0]}</AbsoluteFill>
      </AbsoluteFill>
      <AbsoluteFill style={{ clipPath: `inset(0 0 0 ${edge}px)` }}>
        <AbsoluteFill style={{ transform: `translateX(${(1 - p) * W * sp(toLayers.length, 0)}px)` }}>{toLayers[0]}</AbsoluteFill>
      </AbsoluteFill>
      {/* 전경 레이어: 잘리지 않고 빠르게 이동 */}
      {fromLayers.slice(1).map((l, i) => <AbsoluteFill key={`a${i}`} style={{ transform: `translateX(${-p * W * sp(fromLayers.length, i + 1)}px)` }}>{l}</AbsoluteFill>)}
      {toLayers.slice(1).map((l, i) => <AbsoluteFill key={`b${i}`} style={{ transform: `translateX(${(1 - p) * W * sp(toLayers.length, i + 1)}px)` }}>{l}</AbsoluteFill>)}
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 13c. 불꽃 전환 — 주황 #F26A0F / 노랑 #F7C21A 날카로운 불꽃 덩어리가 좌하단에서 대각으로 3f 덮음
//      → 12f 일렁임(2f 마다 형태 재추첨, 컷 = at+9) → 6f 번아웃 리빌(뒤 가장자리가 우상단으로 빠짐)
//      + 불씨. 끝 = at+21 (불씨 꼬리 +10f)
// ═══════════════════════════════════════════════════════════════════════════
export const FIRE_CUT = 9;
export const FIRE_LEN = 21;
const flameMass = (trail: number, lead: number, seed: string, amp: number, trailAmp: number) => {
  // 회전 좌표계(u: 진행 방향, v: 수직). 앞/뒤 가장자리에 뾰족한 불꽃 혀
  const v0 = -1700, v1 = 1700, step = 64;
  const lp: string[] = [], tp: string[] = [];
  for (let v = v0, i = 0; v <= v1; v += step, i++) {
    lp.push(`${lead},${v}`);
    lp.push(`${lead + amp * (0.25 + 0.75 * random(`${seed}l${i}`))},${v + step * (0.3 + 0.4 * random(`${seed}lv${i}`))}`);
  }
  for (let v = v1, i = 0; v >= v0; v -= step, i++) {
    tp.push(`${trail},${v}`);
    tp.push(`${trail - trailAmp * (0.2 + 0.8 * random(`${seed}t${i}`))},${v - step * (0.3 + 0.4 * random(`${seed}tv${i}`))}`);
  }
  return [...lp, ...tp].join(" ");
};
export const FireTransitionParams = z.object({
  coverDur: num(3, 1, 20, 1, "불꽃이 덮는 시간", "timing", "f"),
  holdDur: num(12, 2, 60, 1, "일렁임 유지(중간에 컷)", "timing", "f"),
  burnDur: num(6, 1, 30, 1, "번아웃 리빌 시간", "timing", "f"),
  flicker: num(2, 1, 10, 1, "불꽃 형태 재추첨 주기", "timing", "f"),
  angle: num(38, 0, 80, 1, "진행 각도", "motion", "°"),
  tongue: num(1, 0, 3, 0.05, "불꽃 혀 길이(배)", "size", "배"),
  jitter: num(60, 0, 200, 5, "층 경계 흔들림", "motion", "px"),
  embers: num(34, 0, 120, 1, "불씨 개수", "look"),
  emberLife: num(10, 1, 40, 1, "불씨 생존 시간", "timing", "f"),
  orange: col("#F26A0F", "주황(외곽) 색"),
  yellow: col("#F7C21A", "노랑 띠 색"),
  deep: col("#E4540A", "짙은 주황 띠 색"),
});
export type FireTransitionP = z.infer<typeof FireTransitionParams>;
/** 불꽃 타이밍: burnAt = 번아웃 시작, len = 불꽃 끝(불씨 꼬리는 +emberLife+2f) */
export const fireTiming = (p?: Partial<FireTransitionP>) => {
  const P = def(FireTransitionParams, p);
  const burnAt = P.coverDur + P.holdDur;
  return { cut: P.coverDur + Math.floor(P.holdDur / 2), burnAt, len: burnAt + P.burnDur };
};
export const FireTransition: React.FC<{ at: number; from: Node; to: Node; orange?: string; yellow?: string; p?: Partial<FireTransitionP> }> = ({ at, from, to, orange: oProp, yellow: yProp, p }) => {
  const P = def(FireTransitionParams, { ...pick({ orange: oProp, yellow: yProp }), ...p });
  const { cut, burnAt, len } = fireTiming(P);
  const orange = P.orange, yellow = P.yellow;
  const FA = (P.angle * Math.PI) / 180;
  const FU = W * Math.cos(FA) + H * Math.sin(FA); // 화면의 대각 진행축 길이
  const f = useCurrentFrame();
  const g = f - at;
  if (g < 0) return <AbsoluteFill>{from}</AbsoluteFill>;
  if (g > len + P.emberLife + 2) return <AbsoluteFill>{to}</AbsoluteFill>;
  const lead = lerp(g, 0, P.coverDur, -320, FU + 420, Easing.out(Easing.quad)) + (g > burnAt ? (g - burnAt) * 200 : 0);
  const trail = g < burnAt ? -900 : lerp(g, burnAt, len, -250, FU + 700, Easing.in(Easing.quad));
  const fl = Math.floor(g / P.flicker); // 2f 마다 형태 재추첨
  const jit = (i: number) => (random(`fj${i}-${fl}`) - 0.5) * P.jitter; // 2f 마다 층 경계도 흔들림
  // 주황 외곽 → 노랑 띠 → 다시 짙은 주황 → 노랑 심지: 평면 단색 덩어리가 되지 않도록 띠를 교차
  const tg = P.tongue;
  const layers: [number, number, string, number][] = [[0, 0, orange, 230 * tg], [170 + jit(1), 200 + jit(2), yellow, 180 * tg], [420 + jit(3), 520 + jit(4), P.deep, 200 * tg], [700 + jit(5), 820 + jit(6), yellow, 170 * tg]];
  const embers = g >= burnAt - 2 ? Array.from({ length: P.embers }).map((_, i) => {
    const x = random(`ex${i}`) * W, y = random(`ey${i}`) * H;
    const u = x * Math.cos(FA) + (H - y) * Math.sin(FA);
    // 뒤 가장자리가 지나간 뒤 태어나 10f 생존
    const born = burnAt + clamp01(u / FU) * P.burnDur;
    const t = g - born;
    if (t < 0 || t > P.emberLife) return null;
    const r = 3 + 5 * random(`er${i}`);
    return <div key={i} style={{ position: "absolute", left: x + t * 3 * (random(`evx${i}`) - 0.3), top: y - t * (5 + 6 * random(`evy${i}`)), width: r * 2, height: r * 2, borderRadius: "50%", background: i % 3 ? orange : yellow, opacity: 1 - t / P.emberLife, boxShadow: `0 0 ${r * 2}px ${orange}` }} />;
  }) : null;
  return (
    <AbsoluteFill>
      {g < cut ? from : to}
      {g <= len && (
        <svg width={W} height={H} style={{ position: "absolute", inset: 0 }}>
          <g transform={`translate(0,${H}) rotate(${(-FA * 180) / Math.PI})`}>
            {layers.map(([ti, li, c, amp], i) => (
              <polygon key={i} points={flameMass(trail + ti, lead - li, `fl${i}-${fl}`, amp, amp * 0.8)} fill={c} strokeLinejoin="miter" />
            ))}
          </g>
        </svg>
      )}
      <AbsoluteFill style={{ pointerEvents: "none" }}>{embers}</AbsoluteFill>
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 13d. 그레이스케일 비트 — 화면 전체 채도가 ~10f 만에 0 으로, hold 동안 유지 후 ~10f 복귀 (래퍼)
// ═══════════════════════════════════════════════════════════════════════════
export const GrayscaleBeatParams = z.object({
  ramp: num(10, 1, 40, 1, "흑백으로 빠지는 시간", "timing", "f"),
  hold: num(20, 0, 120, 1, "흑백 유지", "timing", "f"),
  back: num(10, 1, 40, 1, "색 복귀 시간", "timing", "f"),
  amount: num(1, 0, 1, 0.05, "채도 빼는 양", "look"),
  contrast: num(0.08, 0, 0.5, 0.01, "추가 대비", "look"),
});
export type GrayscaleBeatP = z.infer<typeof GrayscaleBeatParams>;
export const GrayscaleBeat: React.FC<{ at: number; hold?: number; ramp?: number; children: Node; p?: Partial<GrayscaleBeatP> }> = ({ at, hold: hProp, ramp: rProp, children, p }) => {
  // 복귀 시간은 기존 동작대로 ramp 를 따르되, p.back 으로 따로 줄 수 있다
  const P = def(GrayscaleBeatParams, { ...pick({ hold: hProp, ramp: rProp }), ...p });
  const { hold, ramp } = P;
  const back = p?.back !== undefined ? p.back : rProp !== undefined || p?.ramp !== undefined ? ramp : P.back;
  const f = useCurrentFrame();
  const g = f - at;
  const k = P.amount * (g < 0 ? 0 : g < ramp ? lerp(g, 0, ramp, 0, 1, Easing.out(Easing.quad)) : g < ramp + hold ? 1 : lerp(g, ramp + hold, ramp + hold + back, 1, 0, Easing.inOut(Easing.sin)));
  return <AbsoluteFill style={{ filter: k > 0.001 ? `saturate(${1 - k}) contrast(${1 + P.contrast * k})` : undefined }}>{children}</AbsoluteFill>;
};

// ═══════════════════════════════════════════════════════════════════════════
// 13e. 포커스 풀 — A 가 선명→흐림(0→maxBlur) 으로 빠지고 B 가 흐림→선명으로 들어오는 8f 크로스. 컷 = 50%
// ═══════════════════════════════════════════════════════════════════════════
export const FocusPullParams = z.object({
  dur: num(8, 1, 60, 1, "크로스 시간(컷=절반)", "timing", "f"),
  maxBlur: num(24, 0, 100, 1, "최대 블러", "look", "px"),
  blurSpeed: num(1.6, 1, 4, 0.1, "블러 도달 속도(배)", "timing", "배"),
  zoom: num(0.03, 0, 0.3, 0.005, "초점 이동 줌 양", "motion"),
  ease: choice("sin", EASE_KEYS, "이징", "motion"),
});
export type FocusPullP = z.infer<typeof FocusPullParams>;
export const FocusPull: React.FC<{ at: number; from: Node; to: Node; dur?: number; maxBlur?: number; p?: Partial<FocusPullP> }> = ({ at, from, to, dur: dProp, maxBlur: mbProp, p: pp }) => {
  const P = def(FocusPullParams, { ...pick({ dur: dProp, maxBlur: mbProp }), ...pp });
  const { dur, maxBlur } = P;
  const f = useCurrentFrame();
  const g = f - at;
  if (g < 0) return <AbsoluteFill>{from}</AbsoluteFill>;
  if (g >= dur) return <AbsoluteFill>{to}</AbsoluteFill>;
  const p = lerp(g, 0, dur, 0, 1, EASES[P.ease]);
  const zm = P.zoom;
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <AbsoluteFill style={{ filter: `blur(${maxBlur * Math.min(1, p * P.blurSpeed)}px)`, transform: `scale(${1 + zm * p})` }}>{from}</AbsoluteFill>
      <AbsoluteFill style={{ opacity: p, filter: `blur(${maxBlur * Math.min(1, (1 - p) * P.blurSpeed)}px)`, transform: `scale(${1 + zm - zm * p})` }}>{to}</AbsoluteFill>
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 13f. 매직 무브 — hero 한 요소가 유지된 채 heroFrom→heroTo 로 19f easeInOut 이동(기본 스케일 −10%),
//      나머지(from/to)는 3~4f 블러 디졸브. 컷(블러 디졸브) = at..at+4, 끝 = at+dur
//      heroFrom/heroTo: hero 박스 중심 이동량(px)과 스케일. hero 는 원래 위치(0,0 이동) 기준으로 그린다
// ═══════════════════════════════════════════════════════════════════════════
export type MoveKey = { x: number; y: number; s: number };
export const MagicMoveParams = z.object({
  dur: num(19, 1, 90, 1, "히어로 이동 시간", "timing", "f"),
  dissolve: num(4, 1, 30, 1, "배경 블러 디졸브 시간", "timing", "f"),
  dx: num(-390, -1200, 1200, 10, "히어로 가로 이동", "motion", "px"),
  dy: num(0, -700, 700, 10, "히어로 세로 이동", "motion", "px"),
  scale: num(0.9, 0.2, 2.5, 0.05, "히어로 도착 크기(배)", "size", "배"),
  blur: num(14, 0, 60, 1, "디졸브 블러", "look", "px"),
  ease: choice("cubic", EASE_KEYS, "이징", "motion"),
});
export type MagicMoveP = z.infer<typeof MagicMoveParams>;
export const MagicMove: React.FC<{ at: number; from: Node; to: Node; hero: Node; heroFrom?: MoveKey; heroTo?: MoveKey; origin?: string; dur?: number; dissolve?: number; p?: Partial<MagicMoveP> }> = ({ at, from, to, hero, heroFrom = { x: 0, y: 0, s: 1 }, heroTo: htProp, origin = "50% 50%", dur: dProp, dissolve: dsProp, p: pp }) => {
  const P = def(MagicMoveParams, { ...(htProp ? { dx: htProp.x, dy: htProp.y, scale: htProp.s } : {}), ...pick({ dur: dProp, dissolve: dsProp }), ...pp });
  const { dur, dissolve } = P;
  const heroTo: MoveKey = { x: P.dx, y: P.dy, s: P.scale };
  const f = useCurrentFrame();
  const g = f - at;
  const p = lerp(g, 0, dur, 0, 1, EASES[P.ease]);
  const d = lerp(g, 0, dissolve, 0, 1, Easing.linear);
  const x = heroFrom.x + (heroTo.x - heroFrom.x) * p, y = heroFrom.y + (heroTo.y - heroFrom.y) * p;
  const s = heroFrom.s + (heroTo.s - heroFrom.s) * p;
  const bl = P.blur;
  return (
    <AbsoluteFill>
      {d < 1 && <AbsoluteFill style={{ opacity: 1 - d, filter: d > 0 ? `blur(${bl * d}px)` : undefined }}>{from}</AbsoluteFill>}
      {d > 0 && <AbsoluteFill style={{ opacity: d, filter: d < 1 ? `blur(${bl * (1 - d)}px)` : undefined }}>{to}</AbsoluteFill>}
      <AbsoluteFill style={{ transform: `translate(${x}px,${y}px) scale(${s})`, transformOrigin: origin }}>{hero}</AbsoluteFill>
    </AbsoluteFill>
  );
};
