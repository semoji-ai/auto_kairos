// 도감 x_transitions — "분석만" 이던 전환·카메라·구성 기법을 컴포넌트로 구현.
// 규약: 각 컴포넌트 = <Name>Params(zod) + p?: Partial<…> → def() 로 합침. 기본값 = 레퍼런스 실측값.
// 모든 난수는 remotion random(seed). 방사형 줄무늬 광선/선버스트는 쓰지 않는다(원형 글로우·링·나선으로 대체).
import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, random, useCurrentFrame } from "remotion";
import { z } from "zod";
import { W, H, src, hz, SweatDrop } from "../fx";
import { num, col, flag, choice, def } from "../params/p";
import { HBlur, KitImg } from "./callouts";
import { prop, propH, propSize } from "./kit";

type Node = React.ReactNode;
const LIN = Easing.linear;
const IO = Easing.inOut(Easing.cubic);
const OUT = Easing.out(Easing.cubic);
const QUART_OUT = Easing.bezier(0.25, 1, 0.5, 1);
const clamp01 = (v: number) => Math.max(0, Math.min(1, v));
/** 안전한 보간: 구간 길이 0 이하도 허용, 기본 선형 */
const L = (f: number, a: number, b: number, v0: number, v1: number, e: (t: number) => number = LIN) =>
  b <= a ? (f < a ? v0 : v1) : interpolate(f, [a, b], [v0, v1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: e });
const pick = <T extends object>(o: T): Partial<T> => Object.fromEntries(Object.entries(o).filter(([, v]) => v !== undefined)) as Partial<T>;
const useId = (p: string) => p + React.useId().replace(/[^a-zA-Z0-9]/g, "");
const rgba = (hex: string, a: number) => {
  const h = hex.replace("#", "");
  const n = parseInt(h.length === 3 ? h.split("").map((c) => c + c).join("") : h.slice(0, 6), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
};

// ═══════════════════════════════════════════════════════════════════════════
// 공용 리그: 누끼/레이어 인물 잘라 쓰기 + 단색 실루엣
// ═══════════════════════════════════════════════════════════════════════════
/** 인물 컷: img(투명 PNG) + 선택적 bbox(원본 px) + 원본 크기. layers_vec 처럼 전체 프레임 PNG 는 box 로 잘라 쓴다 */
export type Cut = { img: string; box?: [number, number, number, number]; size?: [number, number] };
export const cutAR = (c: Cut) => (c.box ? (c.box[3] - c.box[1]) / (c.box[2] - c.box[0]) : c.size ? c.size[1] / c.size[0] : 1.5);
/** 폭 w 로 컷을 그린다(높이 = w×비율). color 를 주면 그 색의 단색 실루엣(마스크) */
export const CutImg: React.FC<{ c: Cut; w: number; color?: string; style?: React.CSSProperties }> = ({ c, w, color, style }) => {
  const h = w * cutAR(c);
  let iw = w, ih = h, ox = 0, oy = 0;
  if (c.box && c.size) {
    const k = w / (c.box[2] - c.box[0]);
    iw = c.size[0] * k; ih = c.size[1] * k; ox = -c.box[0] * k; oy = -c.box[1] * k;
  }
  const url = `url(${src(c.img)})`;
  return (
    <div style={{ position: "relative", width: w, height: h, overflow: "hidden", ...style }}>
      {color ? (
        <div style={{ position: "absolute", inset: 0, background: color, WebkitMaskImage: url, maskImage: url, WebkitMaskSize: `${iw}px ${ih}px`, maskSize: `${iw}px ${ih}px`, WebkitMaskPosition: `${ox}px ${oy}px`, maskPosition: `${ox}px ${oy}px`, WebkitMaskRepeat: "no-repeat", maskRepeat: "no-repeat" } as React.CSSProperties} />
      ) : (
        <Img src={src(c.img)} style={{ position: "absolute", left: ox, top: oy, width: iw, height: ih, maxWidth: "none" }} />
      )}
    </div>
  );
};

/** RGB 채널 분리 래퍼(SVG 필터). d = 빨강 +d / 파랑 -d 가로 오프셋(px) */
export const RGBSplit: React.FC<{ d: number; dy?: number; children: Node; style?: React.CSSProperties }> = ({ d, dy = 0, children, style }) => {
  const id = useId("rgb");
  const on = Math.abs(d) > 0.3 || Math.abs(dy) > 0.3;
  return (
    <AbsoluteFill style={{ ...style, filter: on ? `url(#${id})` : undefined }}>
      <svg width={0} height={0} style={{ position: "absolute" }}>
        <filter id={id} x="-5%" y="-5%" width="110%" height="110%" colorInterpolationFilters="sRGB">
          <feColorMatrix in="SourceGraphic" type="matrix" values="1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0" result="r" />
          <feOffset in="r" dx={d} dy={dy} result="ro" />
          <feColorMatrix in="SourceGraphic" type="matrix" values="0 0 0 0 0  0 1 0 0 0  0 0 0 0 0  0 0 0 1 0" result="g" />
          <feColorMatrix in="SourceGraphic" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 1 0 0  0 0 0 1 0" result="b" />
          <feOffset in="b" dx={-d} dy={-dy} result="bo" />
          <feBlend in="ro" in2="g" mode="screen" result="rg" />
          <feBlend in="rg" in2="bo" mode="screen" />
        </filter>
      </svg>
      {children}
    </AbsoluteFill>
  );
};

/** 액체 왜곡 래퍼(feTurbulence + feDisplacementMap). amt = 변위(px) */
const Liquid: React.FC<{ amt: number; freq?: number; seed?: number; children: Node; style?: React.CSSProperties }> = ({ amt, freq = 0.004, seed = 3, children, style }) => {
  const id = useId("lq");
  return (
    <AbsoluteFill style={{ ...style, filter: amt > 0.5 ? `url(#${id})` : style?.filter }}>
      <svg width={0} height={0} style={{ position: "absolute" }}>
        <filter id={id} x="-10%" y="-10%" width="120%" height="120%">
          <feTurbulence type="fractalNoise" baseFrequency={freq} numOctaves={2} seed={seed} result="n" />
          <feDisplacementMap in="SourceGraphic" in2="n" scale={amt} xChannelSelector="R" yChannelSelector="G" />
        </filter>
      </svg>
      {children}
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 1. 핑크 컬러 워시 [ref1 11:56] — 사진이 분홍으로 씻김(3f) → 금빛 플레어(5f) → 컷 → 새 사진이 분홍 틴트에서 원색(6f)
// ═══════════════════════════════════════════════════════════════════════════
export const PinkColorWashParams = z.object({
  pinkIn: num(3, 1, 20, 1, "분홍 번지는 시간", "timing", "f"),
  pinkHold: num(3, 0, 20, 1, "분홍 유지", "timing", "f"),
  flareLen: num(5, 0, 20, 1, "금빛 플레어 시간", "timing", "f"),
  tintOut: num(6, 1, 30, 1, "새 사진 원색 복귀", "timing", "f"),
  pinkAmt: num(0.8, 0, 1, 0.05, "분홍 세기", "look"),
  flareAmt: num(0.85, 0, 1, 0.05, "플레어 세기", "look"),
  pink: col("#F0B8C8", "분홍 색"),
  flare: col("#FFB43C", "플레어 색"),
});
export type PinkColorWashP = z.infer<typeof PinkColorWashParams>;
export const pinkWashTiming = (p?: Partial<PinkColorWashP>) => { const P = def(PinkColorWashParams, p); const cut = P.pinkIn + P.pinkHold + P.flareLen; return { cut, len: cut + P.tintOut }; };
export const PinkColorWash: React.FC<{ at: number; from: Node; to: Node; p?: Partial<PinkColorWashP> }> = ({ at, from, to, p }) => {
  const P = def(PinkColorWashParams, p);
  const f = useCurrentFrame(), g = f - at;
  const { cut, len } = pinkWashTiming(P);
  const f0 = P.pinkIn + P.pinkHold;
  const pink = g < 0 ? 0 : g < cut ? L(g, 0, P.pinkIn, 0, 1) * L(g, f0, cut, 1, 0.3) : L(g, cut, len, 0.75, 0, Easing.out(Easing.quad));
  const flare = g < f0 || g >= cut ? 0 : Math.sin(Math.PI * clamp01((g - f0 + 1) / (P.flareLen + 1))) ;
  return (
    <AbsoluteFill>
      {g < cut ? from : to}
      {pink > 0 && <AbsoluteFill style={{ background: P.pink, mixBlendMode: "color", opacity: pink * P.pinkAmt }} />}
      {pink > 0 && <AbsoluteFill style={{ background: P.pink, mixBlendMode: "screen", opacity: pink * P.pinkAmt * 0.45 }} />}
      {flare > 0 && (
        <>
          <AbsoluteFill style={{ background: P.flare, mixBlendMode: "color", opacity: flare * P.flareAmt * 0.8 }} />
          <AbsoluteFill style={{ background: `radial-gradient(ellipse 55% 70% at 62% 30%, ${rgba("#FFF4C8", 1)} 0%, ${rgba(P.flare, 0.7)} 45%, ${rgba(P.flare, 0)} 100%)`, mixBlendMode: "screen", opacity: flare * P.flareAmt }} />
        </>
      )}
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 2. 제자리 장면 교체 [ref1 8:31·6:37] — 인물(base)은 그대로, 오버레이 a 4f 페이드아웃 → b 1f 등장 → 곧바로 풀백.
//    섹션 라벨은 같은 자리에서 5f 크로스페이드.
// ═══════════════════════════════════════════════════════════════════════════
export const InPlaceSwapParams = z.object({
  fadeOut: num(4, 1, 20, 1, "기존 오버레이 페이드아웃", "timing", "f"),
  popIn: num(1, 1, 10, 1, "새 소품 등장 시간", "timing", "f"),
  pullFrom: num(1.15, 1, 1.8, 0.01, "풀백 시작 크기(배)", "motion"),
  pullLen: num(24, 1, 90, 1, "풀백 시간", "timing", "f"),
  labelFade: num(5, 1, 20, 1, "섹션 라벨 크로스페이드", "timing", "f"),
  labelSize: num(62, 24, 120, 1, "라벨 글자 크기", "size", "px"),
  labelBg: col("#3B2B2B", "라벨 바탕"),
});
export type InPlaceSwapP = z.infer<typeof InPlaceSwapParams>;
export const InPlaceSwap: React.FC<{ at: number; base: Node; a?: Node; b?: Node; labelA?: string; labelB?: string; labelX?: number; labelY?: number; origin?: string; p?: Partial<InPlaceSwapP> }> = ({ at, base, a, b, labelA, labelB, labelX = 1440, labelY = 170, origin = "50% 45%", p }) => {
  const P = def(InPlaceSwapParams, p);
  const f = useCurrentFrame(), g = f - at;
  const sw = P.fadeOut;
  const aOp = L(g, 0, sw, 1, 0);
  const bOp = L(g, sw, sw + P.popIn, 0, 1);
  const s = b ? (g < sw ? P.pullFrom : L(g, sw, sw + P.pullLen, P.pullFrom, 1, OUT)) : 1;
  const lab = (t: string, op: number) => (
    <div style={{ position: "absolute", left: labelX, top: labelY, transform: "translate(-50%,-50%)", opacity: op, background: P.labelBg, color: "#fff", fontFamily: "NeoHv", fontSize: P.labelSize, padding: "10px 34px 4px", borderRadius: 14, whiteSpace: "nowrap", boxShadow: "0 0 0 4px rgba(255,255,255,0.15)" }}>{t}</div>
  );
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ transform: `scale(${s})`, transformOrigin: origin }}>
        {base}
        {b && bOp > 0 && <AbsoluteFill style={{ opacity: bOp }}>{b}</AbsoluteFill>}
      </AbsoluteFill>
      {a && aOp > 0 && <AbsoluteFill style={{ opacity: aOp }}>{a}</AbsoluteFill>}
      {labelA && lab(labelA, L(g, 0, P.labelFade, 1, 0))}
      {labelB && lab(labelB, L(g, 0, P.labelFade, 0, 1))}
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 3. 캐릭터 슬라이드 컷 [ref1 3:42] — 하드컷 직후(≈10f) 인물이 화면 밖에서 흰 잔상과 함께 미끄러져 들어와(15f) 씬을 연다.
//    char 는 최종 위치에 배치된 전체 화면 레이어(이 레이어 전체를 밀어 넣는다).
// ═══════════════════════════════════════════════════════════════════════════
export const SlideCutParams = z.object({
  delay: num(10, 0, 40, 1, "컷 후 진입 지연", "timing", "f"),
  slideLen: num(15, 3, 40, 1, "미끄러져 들어오는 시간", "timing", "f"),
  dist: num(700, 100, 1920, 10, "진입 거리", "motion", "px"),
  blur: num(24, 0, 80, 1, "이동 블러", "look", "px"),
  streak: flag(true, "흰 잔상 띠", "look"),
  dir: choice("left", ["left", "right"] as const, "진입 방향"),
});
export type SlideCutP = z.infer<typeof SlideCutParams>;
export const SlideCut: React.FC<{ at: number; from?: Node; to: Node; char: Node; edgeY?: number; p?: Partial<SlideCutP> }> = ({ at, from, to, char, edgeY = 470, p }) => {
  const P = def(SlideCutParams, p);
  const f = useCurrentFrame(), g = f - at;
  const s0 = P.delay, s1 = P.delay + P.slideLen;
  const sg = P.dir === "left" ? -1 : 1;
  const k = L(g, s0, s1, 1, 0, QUART_OUT);
  const vel = Math.abs(L(g + 1, s0, s1, 1, 0, QUART_OUT) - k);
  const streakOp = P.streak ? L(g, s0 - 3, s0, 0, 1) * L(g, s0 + 3, s0 + 8, 1, 0) : 0;
  return (
    <AbsoluteFill>
      {g < 0 && from ? from : to}
      {g >= s0 - 3 && (
        <>
          {streakOp > 0 && <div style={{ position: "absolute", top: edgeY - 140, height: 280, width: 90, [P.dir === "left" ? "left" : "right"]: -30, background: "#fff", borderRadius: 60, filter: "blur(10px)", opacity: streakOp }} />}
          {g >= s0 && (
            <HBlur amt={vel * P.blur * 4} style={{ position: "absolute", inset: 0, transform: `translateX(${sg * P.dist * k}px)` }}>
              <AbsoluteFill>{char}</AbsoluteFill>
            </HBlur>
          )}
        </>
      )}
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 4. 지퍼 잠금/열림 [ref4-apple 1:45:17] — 두 톱니 줄이 위에서 Λ 로 모여 슬라이더가 내려가며 닫힘(28f, 이전 레이어를 쓸어냄)
//    → 크림 배경 위 중앙 세로 지퍼 유지(≈45f) → 슬라이더가 다시 내려가며 V 로 열려 뒤 레이어 리빌(28f)
// ═══════════════════════════════════════════════════════════════════════════
export const ZipperParams = z.object({
  closeLen: num(28, 8, 80, 1, "닫히는 시간", "timing", "f"),
  hold: num(45, 0, 120, 1, "닫힌 지퍼 유지", "timing", "f"),
  openLen: num(28, 8, 80, 1, "열리는 시간", "timing", "f"),
  curve: num(1.7, 1, 3, 0.05, "현수선 휨(지수)", "motion"),
  spread: num(3, 1, 6, 0.1, "벌어짐 폭(배)", "motion"),
  teeth: num(14, 6, 30, 1, "지퍼 폭", "size", "px"),
  teethColor: col("#C9C9C9", "톱니 색"),
  edgeColor: col("#6E6E6E", "톱니 외곽 색"),
  bg: col("#F1EEE9", "크림 배경"),
});
export type ZipperP = z.infer<typeof ZipperParams>;
export const zipperTiming = (p?: Partial<ZipperP>) => { const P = def(ZipperParams, p); return { closed: P.closeLen, open: P.closeLen + P.hold, len: P.closeLen + P.hold + P.openLen }; };
export const ZipperTransition: React.FC<{ at: number; from: Node; to: Node; mid?: Node; x?: number; p?: Partial<ZipperP> }> = ({ at, from, to, mid, x = W / 2, p }) => {
  const P = def(ZipperParams, p);
  const f = useCurrentFrame(), g = f - at;
  const { closed, open, len } = zipperTiming(P);
  // 반폭 함수: hw(u) = A·u^k·W  (u = 슬라이더로부터의 세로 거리/H)
  const legs = (y0: number, A: number, dir: 1 | -1) => {
    const pts: [number, number][] = [];
    const yEnd = dir === 1 ? H + 60 : -60;
    const n = 48;
    for (let i = 0; i <= n; i++) {
      const y = y0 + ((yEnd - y0) * i) / n;
      const u = Math.abs(y - y0) / H;
      pts.push([Math.min(W * 2, A * Math.pow(u, P.curve) * W), y]);
    }
    return pts;
  };
  let phase: "pre" | "close" | "hold" | "open" | "post" = g < 0 ? "pre" : g < closed ? "close" : g < open ? "hold" : g < len ? "open" : "post";
  const bgLayer = <AbsoluteFill style={{ background: P.bg }}>{mid}</AbsoluteFill>;
  if (phase === "pre") return <AbsoluteFill>{from}</AbsoluteFill>;
  if (phase === "post") return <AbsoluteFill>{to}</AbsoluteFill>;
  let ys = 0, pts: [number, number][] = [], dir: 1 | -1 = 1, line: [number, number] = [0, 0];
  if (phase === "close") {
    const t = IO(clamp01(g / closed));
    ys = L(t, 0, 1, -700, H + 160); dir = 1;
    pts = legs(ys, P.spread * Math.pow(1 - t, 1.2), 1);
    line = [-20, ys];
  } else if (phase === "hold") {
    ys = H + 160; line = [-20, H + 20];
  } else {
    const t = IO(clamp01((g - open) / P.openLen));
    ys = L(t, 0, 1, -160, H + 700); dir = -1;
    pts = legs(ys, P.spread * Math.pow(t, 1.2), -1);
    line = [ys, H + 20];
  }
  const poly = pts.length ? [...pts.map(([hw, y]) => `${x - hw}px ${y}px`), ...pts.slice().reverse().map(([hw, y]) => `${x + hw}px ${y}px`)].join(",") : "";
  const leftD = pts.map(([hw, y], i) => `${i ? "L" : "M"}${(x - hw).toFixed(1)},${y.toFixed(1)}`).join(" ");
  const rightD = pts.map(([hw, y], i) => `${i ? "L" : "M"}${(x + hw).toFixed(1)},${y.toFixed(1)}`).join(" ");
  const T = P.teeth;
  const track = (d: string, k: string) => (
    <g key={k}>
      <path d={d} fill="none" stroke={P.edgeColor} strokeWidth={T + 3} strokeLinecap="round" />
      <path d={d} fill="none" stroke={P.teethColor} strokeWidth={T} strokeDasharray="4 3" />
    </g>
  );
  const inner = phase === "close" ? from : phase === "open" ? to : null;
  return (
    <AbsoluteFill>
      {bgLayer}
      {inner && poly && <AbsoluteFill style={{ clipPath: `polygon(${poly})` }}>{inner}</AbsoluteFill>}
      <svg width={W} height={H} style={{ position: "absolute", overflow: "visible" }}>
        {pts.length > 0 && track(leftD, "l")}
        {pts.length > 0 && track(rightD, "r")}
        {line[1] > line[0] && (
          <g>
            <line x1={x} y1={line[0]} x2={x} y2={line[1]} stroke={P.edgeColor} strokeWidth={T * 1.3 + 3} />
            <line x1={x - T * 0.3} y1={line[0]} x2={x - T * 0.3} y2={line[1]} stroke={P.teethColor} strokeWidth={T * 0.7} strokeDasharray="4 3" />
            <line x1={x + T * 0.3} y1={line[0]} x2={x + T * 0.3} y2={line[1]} stroke={P.teethColor} strokeWidth={T * 0.7} strokeDasharray="4 3" strokeDashoffset={3.5} />
          </g>
        )}
      </svg>
      {/* 세모지 그림체 지퍼 슬라이더(zipper_slider: 몸통 중심 0.71,0.27 + 아래로 늘어진 손잡이). 닫힐 때(아래로 이동)는 손잡이가 위로 끌리도록 180° */}
      {phase !== "hold" && ys > -100 && ys < H + 100 && <KitImg id="zipper_slider" x={x} y={ys} w={T * 6} ax={0.71} ay={0.27} rot={dir === 1 ? 180 : 0} />}
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 5·6. 연도 카드 탈출 — 텍스트 기울기+확대+색분리 후
//   TwirlLiquid [ref4-cocacola 18:44]: 화면 전체 소용돌이 액체(빨·청록·노·파) 10f → 새 영상이 왜곡에서 풀림 10f
//   SpectralZoomThrough [ref4-samsung 40:50·52:02]: 청·주황·노 색분리 60px, 하드컷 → 새 장면 방사 줌블러 12f + RGB 잔존 16f
// ═══════════════════════════════════════════════════════════════════════════
const YearCardText: React.FC<{ text: string; size: number; rot: number; s: number; split: number; colors: string[]; x?: number; y?: number }> = ({ text, size, rot, s, split, colors, x = W / 2, y = H / 2 }) => {
  const t = (c: string, dx: number, dy: number, blend?: React.CSSProperties["mixBlendMode"]) => (
    <div style={{ position: "absolute", left: x + dx, top: y + dy, transform: `translate(-50%,-50%) rotate(${rot}deg) scale(${s})`, fontFamily: "NeoHv", fontSize: size, color: c, whiteSpace: "nowrap", mixBlendMode: blend }}>{text}</div>
  );
  const n = colors.length;
  return (
    <AbsoluteFill>
      {split > 0.5 && colors.map((c, i) => <React.Fragment key={i}>{t(c, split * ((i + 1) / n) * (i % 2 ? -1 : 1), split * 0.35 * ((i + 1) / n) * (i % 2 ? 1 : -1))}</React.Fragment>)}
      {t("#111", 0, 0)}
    </AbsoluteFill>
  );
};
/** 소용돌이 스미어: 굵은 나선 띠 여러 개(직선 광선 아님) + 액체 변위 */
const SwirlSmear: React.FC<{ g: number; colors: string[]; turns: number; amt: number; op: number }> = ({ g, colors, turns, amt, op }) => {
  const arms = colors.length;
  const paths = colors.map((c, i) => {
    const pts: string[] = [];
    for (let j = 0; j <= 60; j++) {
      const th = (j / 60) * Math.PI * 2 * turns + (i / arms) * Math.PI * 2 + g * 0.22;
      const r = 20 + (j / 60) * 1500;
      pts.push(`${j ? "L" : "M"}${(W / 2 + Math.cos(th) * r).toFixed(1)},${(H / 2 + Math.sin(th) * r * 0.8).toFixed(1)}`);
    }
    return <path key={i} d={pts.join(" ")} fill="none" stroke={c} strokeWidth={170 + 60 * Math.sin(g / 3 + i)} strokeLinecap="round" />;
  });
  return (
    <Liquid amt={amt} freq={0.003} style={{ opacity: op }}>
      <svg width={W} height={H} style={{ position: "absolute", filter: "blur(6px)" }}>
        <rect width={W} height={H} fill="#F4F1EA" />
        {paths}
      </svg>
    </Liquid>
  );
};
export const TwirlLiquidParams = z.object({
  hold: num(6, 0, 60, 1, "연도 카드 정지", "timing", "f"),
  tiltLen: num(8, 2, 30, 1, "텍스트 기울며 커지는 시간", "timing", "f"),
  rot: num(-20, -60, 60, 1, "텍스트 기울기", "motion", "°"),
  scale: num(1.8, 1, 5, 0.05, "텍스트 최종 크기(배)", "motion"),
  split: num(20, 0, 80, 1, "RGB 분리", "look", "px"),
  smearLen: num(10, 2, 30, 1, "소용돌이 스미어", "timing", "f"),
  settleLen: num(10, 2, 30, 1, "새 영상 왜곡 풀림", "timing", "f"),
  turns: num(1.2, 0.3, 3, 0.1, "나선 감김 수", "motion"),
  distort: num(90, 0, 300, 5, "액체 변위", "motion", "px"),
  size: num(96, 40, 200, 2, "연도 글자 크기", "size", "px"),
  bg: col("#C3CBBF", "카드 배경(세이지)"),
});
export type TwirlLiquidP = z.infer<typeof TwirlLiquidParams>;
export const twirlTiming = (p?: Partial<TwirlLiquidP>) => { const P = def(TwirlLiquidParams, p); const cut = P.hold + P.tiltLen + P.smearLen; return { cut, len: cut + P.settleLen }; };
export const TwirlLiquid: React.FC<{ at: number; text: string; to: Node; colors?: string[]; p?: Partial<TwirlLiquidP> }> = ({ at, text, to, colors = ["#E8262B", "#29C6E8", "#FFD23A", "#2F4FE0", "#FFFFFF"], p }) => {
  const P = def(TwirlLiquidParams, p);
  const f = useCurrentFrame(), g = f - at;
  const t0 = P.hold, t1 = t0 + P.tiltLen, { cut, len } = twirlTiming(P);
  const e = Easing.in(Easing.quad);
  const card = (
    <AbsoluteFill style={{ background: P.bg }}>
      <YearCardText text={text} size={P.size} rot={L(g, t0, t1, 0, P.rot, e)} s={L(g, t0, t1, 1, P.scale, e)} split={L(g, t0, t1, 0, P.split, e)} colors={["#FF2A3A", "#1FD6F0"]} />
    </AbsoluteFill>
  );
  if (g < t1) return card;
  if (g < cut) {
    const k = clamp01((g - t1 + 1) / P.smearLen);
    return (
      <AbsoluteFill>
        <Liquid amt={P.distort * k}>{card}</Liquid>
        <SwirlSmear g={g} colors={colors} turns={P.turns} amt={P.distort * (0.6 + k)} op={Math.min(1, k * 2.2)} />
      </AbsoluteFill>
    );
  }
  const k = 1 - clamp01((g - cut) / P.settleLen);
  const ke = Easing.in(Easing.quad)(k);
  return (
    <AbsoluteFill>
      <Liquid amt={P.distort * 1.6 * ke} freq={0.0035}>
        <AbsoluteFill style={{ transform: `rotate(${-25 * ke}deg) scale(${1 + 0.35 * ke})` }}>{to}</AbsoluteFill>
      </Liquid>
      {g < len && <SwirlSmear g={g} colors={colors} turns={P.turns} amt={P.distort * 1.4} op={ke * 0.75} />}
    </AbsoluteFill>
  );
};

export const SpectralZoomThroughParams = z.object({
  hold: num(6, 0, 60, 1, "날짜 카드 정지", "timing", "f"),
  tiltLen: num(9, 2, 30, 1, "기울며 확대 시간", "timing", "f"),
  rot: num(-12, -60, 60, 1, "텍스트 기울기", "motion", "°"),
  scale: num(3.5, 1, 8, 0.1, "텍스트 최종 크기(배)", "motion"),
  split: num(60, 0, 150, 1, "색분리 오프셋", "look", "px"),
  zoomLen: num(12, 2, 40, 1, "방사 줌블러 해제", "timing", "f"),
  zoomAmt: num(0.35, 0, 1, 0.01, "줌블러 강도(확대 배)", "motion"),
  rgbHold: num(16, 0, 40, 1, "RGB 분리 잔존", "timing", "f"),
  rgbAmt: num(24, 0, 80, 1, "새 장면 RGB 분리", "look", "px"),
  size: num(96, 40, 200, 2, "날짜 글자 크기", "size", "px"),
  c1: col("#2B5BFF", "분리색 1(파랑)"),
  c2: col("#FF8A1E", "분리색 2(주황)"),
  c3: col("#FFD400", "분리색 3(노랑)"),
  bg: col("#C3CBBF", "카드 배경(세이지)"),
});
export type SpectralZoomThroughP = z.infer<typeof SpectralZoomThroughParams>;
export const spectralTiming = (p?: Partial<SpectralZoomThroughP>) => { const P = def(SpectralZoomThroughParams, p); const cut = P.hold + P.tiltLen + 1; return { cut, len: cut + Math.max(P.zoomLen, P.rgbHold) }; };
export const SpectralZoomThrough: React.FC<{ at: number; text: string; to: Node; p?: Partial<SpectralZoomThroughP> }> = ({ at, text, to, p }) => {
  const P = def(SpectralZoomThroughParams, p);
  const f = useCurrentFrame(), g = f - at;
  const t0 = P.hold, t1 = t0 + P.tiltLen, { cut } = spectralTiming(P);
  const e = Easing.in(Easing.cubic);
  if (g < cut) {
    return (
      <AbsoluteFill style={{ background: P.bg }}>
        <YearCardText text={text} size={P.size} rot={L(g, t0, t1, 0, P.rot, e)} s={L(g, t0, t1, 1, P.scale, e)} split={L(g, t0, t1, 0, P.split, e)} colors={[P.c1, P.c2, P.c3]} />
      </AbsoluteFill>
    );
  }
  const kz = 1 - Easing.out(Easing.cubic)(clamp01((g - cut) / P.zoomLen));
  const kr = 1 - Easing.out(Easing.quad)(clamp01((g - cut) / Math.max(1, P.rgbHold)));
  const N = 6;
  return (
    <RGBSplit d={P.rgbAmt * kr} dy={P.rgbAmt * 0.3 * kr}>
      <AbsoluteFill style={{ background: "#111" }}>{to}</AbsoluteFill>
      {kz > 0.02 && Array.from({ length: N }).map((_, i) => (
        <AbsoluteFill key={i} style={{ transform: `scale(${1 + P.zoomAmt * kz * ((i + 1) / N)})`, opacity: 0.42 * kz * (1 - i / (N + 1)) }}>{to}</AbsoluteFill>
      ))}
    </RGBSplit>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 7. 파스텔 그라디언트 광원 워시 [ref4-cocacola 19:19·24:25] — 한쪽 가장자리에서 크림→핑크 빛이 6f 확산(글자 검정→빨강 4f)
//    → 10f 유지 → 하드컷 → 새 장면 위 과노출 파스텔이 12f 동안 걷힘. 깜빡임 없음.
// ═══════════════════════════════════════════════════════════════════════════
export const GradientLightWashParams = z.object({
  spreadLen: num(6, 1, 30, 1, "빛 확산 시간", "timing", "f"),
  hold: num(10, 0, 40, 1, "과노출 유지", "timing", "f"),
  redLen: num(4, 1, 20, 1, "글자 빨개지는 시간", "timing", "f"),
  outLen: num(12, 1, 40, 1, "새 장면 워시 걷힘", "timing", "f"),
  amt: num(0.92, 0, 1, 0.02, "워시 세기", "look"),
  side: choice("left", ["left", "right"] as const, "빛 들어오는 쪽"),
  cream: col("#FFF8D0", "크림"),
  pink: col("#F6C0D0", "핑크"),
  red: col("#E0453A", "글자 바뀌는 색"),
});
export type GradientLightWashP = z.infer<typeof GradientLightWashParams>;
export const gradientWashTiming = (p?: Partial<GradientLightWashP>) => { const P = def(GradientLightWashParams, p); const cut = P.spreadLen + P.hold; return { cut, len: cut + P.outLen }; };
export const GradientLightWash: React.FC<{ at: number; from: Node; fg?: (textColor: string, k: number) => Node; to: Node; p?: Partial<GradientLightWashP> }> = ({ at, from, fg, to, p }) => {
  const P = def(GradientLightWashParams, p);
  const f = useCurrentFrame(), g = f - at;
  const { cut, len } = gradientWashTiming(P);
  const ox = P.side === "left" ? "0%" : "100%";
  if (g < cut) {
    const r = L(g, 0, P.spreadLen, 0, 2600, OUT);
    const k = L(g, 0, P.redLen, 0, 1);
    const tc = k <= 0 ? "#111111" : interpolateHex("#111111", P.red, k);
    return (
      <AbsoluteFill>
        {from}
        {g >= 0 && <AbsoluteFill style={{ opacity: P.amt, background: `radial-gradient(circle ${r}px at ${ox} 45%, ${P.cream} 0%, ${rgba(P.cream, 0.95)} 35%, ${P.pink} 72%, ${rgba(P.pink, 0)} 100%)` }} />}
        {fg && fg(tc, k)}
      </AbsoluteFill>
    );
  }
  const k = 1 - Easing.out(Easing.quad)(clamp01((g - cut) / P.outLen));
  return (
    <AbsoluteFill>
      {to}
      {g < len && <AbsoluteFill style={{ opacity: P.amt * k, background: `linear-gradient(${P.side === "left" ? 100 : 260}deg, ${P.cream} 0%, #FFF1B0 40%, ${P.pink} 100%)` }} />}
    </AbsoluteFill>
  );
};
const interpolateHex = (a: string, b: string, k: number) => {
  const pa = parseInt(a.slice(1, 7), 16), pb = parseInt(b.slice(1, 7), 16);
  const c = [16, 8, 0].map((s) => Math.round(((pa >> s) & 255) * (1 - k) + ((pb >> s) & 255) * k));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
};

// ═══════════════════════════════════════════════════════════════════════════
// 8. 엘리베이터 문 열림 리빌 [ref4-hyundai 28:11] — 중앙 슬릿 → 9f 완개(easeInOut) + 10f 미세 푸시인 1.0→1.05
//    → 인물이 걸어 나와 오른쪽 +420px, 45f 선형(바운스 6px/12f). 층 표시등 상단.
// ═══════════════════════════════════════════════════════════════════════════
export const ElevatorRevealParams = z.object({
  openLen: num(9, 2, 40, 1, "문 열리는 시간", "timing", "f"),
  pushTo: num(1.05, 1, 1.4, 0.01, "개방 후 푸시인(배)", "motion"),
  pushLen: num(10, 1, 60, 1, "푸시인 시간", "timing", "f"),
  walkDelay: num(22, 0, 90, 1, "개방 후 걸어나오기 지연", "timing", "f"),
  walkDx: num(420, -900, 900, 10, "걸어나가는 거리", "motion", "px"),
  walkLen: num(45, 5, 120, 1, "걷는 시간", "timing", "f"),
  bobAmp: num(6, 0, 30, 1, "걸음 바운스", "motion", "px"),
  bobPeriod: num(12, 4, 40, 1, "걸음 주기", "timing", "f"),
  personW: num(300, 120, 600, 5, "인물 폭", "size", "px"),
  wall: col("#D3E1DA", "벽 색"),
  door: col("#CFCFCB", "문 색"),
  inside: col("#8FA8A0", "엘리베이터 안 색"),
});
export type ElevatorRevealP = z.infer<typeof ElevatorRevealParams>;
export const ElevatorReveal: React.FC<{ at: number; person: Cut; floor?: string; p?: Partial<ElevatorRevealP> }> = ({ at, person, floor = "7", p }) => {
  const P = def(ElevatorRevealParams, p);
  const f = useCurrentFrame(), g = f - at;
  const ox = 690, oy = 150, ow = 540, oh = 820; // 문 개구부
  const open = L(g, 0, P.openLen, 0, 1, IO);
  const push = L(g, P.openLen, P.openLen + P.pushLen, 1, P.pushTo, OUT);
  const w0 = P.openLen + P.walkDelay;
  const walking = g >= w0;
  const wx = L(g, w0, w0 + P.walkLen, 0, P.walkDx);
  const bob = walking && g < w0 + P.walkLen ? -Math.abs(Math.sin(((g - w0) / P.bobPeriod) * Math.PI)) * P.bobAmp : 0;
  const pw = P.personW, ph = pw * cutAR(person);
  const personEl = <div style={{ position: "absolute", left: ox + ow / 2 - pw / 2 + wx, top: oy + oh + 20 - ph + bob }}><CutImg c={person} w={pw} /></div>;
  const dw = (ow / 2) * open;
  return (
    <AbsoluteFill style={{ background: P.wall, transform: `scale(${push})`, transformOrigin: "50% 55%" }}>
      {/* 바닥 띠 */}
      <div style={{ position: "absolute", left: 0, right: 0, top: 820, height: 26, background: "#B9C9C1" }} />
      <div style={{ position: "absolute", left: 0, right: 0, top: 846, bottom: 0, background: "#E4ECE8" }} />
      {/* 옆 엘리베이터(좌·우) */}
      {[-560, 560].map((dx) => (
        <div key={dx} style={{ position: "absolute", left: ox + dx + 40, top: oy, width: ow - 80, height: oh, background: P.door, boxShadow: "0 0 0 22px #ECEEEA", borderLeft: "2px solid #B7B7B2" }}>
          <div style={{ position: "absolute", left: "50%", top: 0, bottom: 0, width: 3, background: "#B0B0AB" }} />
        </div>
      ))}
      {/* 개구부 틀 */}
      <div style={{ position: "absolute", left: ox - 30, top: oy - 30, width: ow + 60, height: oh + 30, background: "#F2F2EF", boxShadow: "inset 0 0 0 3px #D4D4CF" }} />
      {/* 호출 버튼 · 층 표시 */}
      <div style={{ position: "absolute", left: ox - 90, top: 480, width: 26, height: 70, borderRadius: 6, background: "#E8E8E4", boxShadow: "inset 0 0 0 2px #B5B5B0" }}>
        {[16, 44].map((y) => <div key={y} style={{ position: "absolute", left: 7, top: y - 6, width: 12, height: 12, borderRadius: 6, background: "#9A9A96" }} />)}
      </div>
      <div style={{ position: "absolute", left: ox + ow / 2 - 60, top: oy - 110, width: 120, height: 56, borderRadius: 8, background: "#2F3432", color: "#FFB23E", fontFamily: "NeoHv", fontSize: 38, display: "flex", alignItems: "center", justifyContent: "center", gap: 10 }}>
        <span style={{ fontSize: 26 }}>▲</span>{floor}
      </div>
      {/* 안 */}
      <div style={{ position: "absolute", left: ox, top: oy, width: ow, height: oh, background: P.inside, overflow: "hidden" }}>
        <div style={{ position: "absolute", left: 0, right: 0, top: oh * 0.6, height: 10, background: "rgba(255,255,255,0.35)" }} />
      </div>
      {!walking && <div style={{ position: "absolute", left: ox, top: oy, width: ow, height: oh, overflow: "hidden" }}><div style={{ position: "absolute", left: -ox, top: -oy, width: W, height: H }}>{personEl}</div></div>}
      {/* 문짝 */}
      <div style={{ position: "absolute", left: ox, top: oy, width: ow, height: oh, overflow: "hidden" }}>
        <div style={{ position: "absolute", left: -dw, top: 0, width: ow / 2, height: oh, background: P.door, borderRight: "2px solid #A9A9A4" }} />
        <div style={{ position: "absolute", left: ow / 2 + dw, top: 0, width: ow / 2, height: oh, background: P.door, borderLeft: "2px solid #A9A9A4" }} />
      </div>
      {walking && personEl}
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 9. 충돌 임팩트 줌 + 유리 균열 [ref4-hyundai 1:46:50] — 급줌 1.0→2.5 + 방향블러 4f → 블러 홀드 3f
//    → 6f 줌아웃 복귀와 동시에 흑백 + 깨진 유리(불규칙 균열선) + 하단 회색 연기
// ═══════════════════════════════════════════════════════════════════════════
export const CrashImpactParams = z.object({
  zoomTo: num(2.5, 1, 5, 0.05, "급줌 배율", "motion"),
  zoomLen: num(4, 1, 20, 1, "급줌 시간", "timing", "f"),
  hold: num(3, 0, 20, 1, "블러 홀드", "timing", "f"),
  backLen: num(6, 1, 30, 1, "줌아웃 복귀", "timing", "f"),
  blur: num(30, 0, 100, 1, "방향 블러", "look", "px"),
  cracks: num(11, 3, 24, 1, "균열 가지 수", "size"),
  crackLen: num(5, 1, 20, 1, "균열 그려지는 시간", "timing", "f"),
  smoke: flag(true, "하단 회색 연기", "look"),
  gray: num(1, 0, 1, 0.05, "흑백 정도", "look"),
});
export type CrashImpactP = z.infer<typeof CrashImpactParams>;
export const CrashImpact: React.FC<{ at: number; children: Node; origin?: [number, number]; seed?: string; p?: Partial<CrashImpactP> }> = ({ at, children, origin = [960, 520], seed = "crash", p }) => {
  const P = def(CrashImpactParams, p);
  const f = useCurrentFrame(), g = f - at;
  const z1 = P.zoomLen, z2 = z1 + P.hold, z3 = z2 + P.backLen;
  const s = g < 0 ? 1 : g < z1 ? L(g, 0, z1, 1, P.zoomTo, Easing.in(Easing.quad)) : g < z2 ? P.zoomTo : L(g, z2, z3, P.zoomTo, 1, OUT);
  const bl = g < 0 ? 0 : g < z1 ? L(g, 0, z1, 0, P.blur) : g < z2 ? P.blur : L(g, z2, z3, P.blur, 0);
  const after = g >= z2;
  const gray = after ? L(g, z2, z3, 0.6, 1) * P.gray : 0;
  // 균열: 충격점에서 뻗는 지그재그 가지 + 불규칙 동심 고리
  const [cx, cy] = [origin[0] + 60, origin[1] + 120];
  const branches = Array.from({ length: Math.round(P.cracks) }).map((_, i) => {
    const a0 = (i / P.cracks) * Math.PI * 2 + random(`${seed}a${i}`) * 0.5;
    const pts: [number, number][] = [[cx, cy]];
    let a = a0, x = cx, y = cy;
    const segs = 5 + Math.floor(random(`${seed}n${i}`) * 4);
    for (let j = 0; j < segs; j++) {
      a += (random(`${seed}t${i}-${j}`) - 0.5) * 0.9;
      const l = 60 + random(`${seed}l${i}-${j}`) * 140;
      x += Math.cos(a) * l; y += Math.sin(a) * l;
      pts.push([x, y]);
    }
    return pts;
  });
  const ring = (r: number, k: string) => Array.from({ length: 13 }).map((_, j) => {
    const a = (j / 12) * Math.PI * 2;
    const rr = r * (0.8 + random(`${seed}${k}${j % 12}`) * 0.4);
    return `${j ? "L" : "M"}${(cx + Math.cos(a) * rr).toFixed(1)},${(cy + Math.sin(a) * rr * 0.8).toFixed(1)}`;
  }).join(" ");
  const draw = L(g, z2, z2 + P.crackLen, 0, 1, OUT);
  const d = (pts: [number, number][]) => pts.map((q, i) => `${i ? "L" : "M"}${q[0].toFixed(1)},${q[1].toFixed(1)}`).join(" ");
  return (
    <AbsoluteFill style={{ overflow: "hidden", background: "#222" }}>
      <HBlur amt={bl} style={{ position: "absolute", inset: 0, transform: `scale(${s})`, transformOrigin: `${origin[0]}px ${origin[1]}px`, filter: `grayscale(${gray}) contrast(${1 - gray * 0.1}) blur(${bl * 0.08}px)` }}>
        <AbsoluteFill>{children}</AbsoluteFill>
      </HBlur>
      {after && (
        <svg width={W} height={H} style={{ position: "absolute", filter: "drop-shadow(0 0 2px rgba(0,0,0,0.6))" }}>
          {branches.map((pts, i) => <path key={i} d={d(pts)} fill="none" stroke="#F4F4F4" strokeWidth={3.5 - (i % 3) * 0.8} strokeLinejoin="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - draw} />)}
          {[150, 330].map((r, i) => <path key={r} d={ring(r, `r${i}`)} fill="none" stroke="#EDEDED" strokeWidth={2.4} pathLength={1} strokeDasharray={1} strokeDashoffset={1 - draw} opacity={0.85} />)}
        </svg>
      )}
      {after && P.smoke && (
        <AbsoluteFill style={{ opacity: L(g, z2, z3 + 6, 0, 0.9) }}>
          {Array.from({ length: 12 }).map((_, i) => {
            const r = 160 + random(`${seed}sr${i}`) * 140;
            const x = (i / 11) * W + Math.sin((g + i * 7) / 18) * 30;
            return <div key={i} style={{ position: "absolute", left: x - r, top: H - 60 - r * 0.5 - random(`${seed}sy${i}`) * 60, width: r * 2, height: r, borderRadius: "50%", background: "rgba(150,150,150,0.7)", filter: "blur(28px)" }} />;
          })}
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 10. 시안 에너지 링 와이프 [ref4-samsung 19:22·20:40] — f0~1 사선 광선 2~3줄 → f2~11 발광 링 회전·확대
//     → 플랫 시안 #B8F7F5 2f → 새 장면 위 링 수축(1.0→0.4)+페이드 7f. ※ 링 안 방사형 쐐기는 쓰지 않음(링+사선만).
// ═══════════════════════════════════════════════════════════════════════════
export const CyanRingWipeParams = z.object({
  beamLen: num(2, 1, 10, 1, "사선 광선 번쩍", "timing", "f"),
  ringLen: num(9, 2, 30, 1, "링 회전·확대", "timing", "f"),
  flatLen: num(2, 0, 10, 1, "플랫 시안 홀드", "timing", "f"),
  shrinkLen: num(7, 1, 30, 1, "새 장면 위 링 수축", "timing", "f"),
  ringW: num(30, 6, 80, 1, "링 굵기", "size", "px"),
  glow: num(26, 0, 80, 1, "블룸", "look", "px"),
  beams: num(3, 1, 5, 1, "사선 광선 수", "size"),
  angle: num(-38, -80, 80, 1, "사선 각도", "motion", "°"),
  color: col("#5FE6F2", "링 색"),
  flat: col("#B8F7F5", "플랫 시안"),
});
export type CyanRingWipeP = z.infer<typeof CyanRingWipeParams>;
export const cyanRingTiming = (p?: Partial<CyanRingWipeP>) => { const P = def(CyanRingWipeParams, p); const cut = P.beamLen + P.ringLen + P.flatLen; return { cut, len: cut + P.shrinkLen }; };
export const CyanRingWipe: React.FC<{ at: number; from: Node; to: Node; cx?: number; cy?: number; p?: Partial<CyanRingWipeP> }> = ({ at, from, to, cx = W / 2, cy = H / 2, p }) => {
  const P = def(CyanRingWipeParams, p);
  const f = useCurrentFrame(), g = f - at;
  const r0 = P.beamLen, r1 = r0 + P.ringLen, { cut, len } = cyanRingTiming(P);
  const id = useId("cr");
  if (g < 0) return <AbsoluteFill>{from}</AbsoluteFill>;
  const ringSvg = (R: number, rot: number, op: number) => (
    <svg width={W} height={H} style={{ position: "absolute", overflow: "visible", opacity: op }}>
      <defs>
        <filter id={id} x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation={P.glow / 2} result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
      </defs>
      <g filter={`url(#${id})`} transform={`rotate(${rot} ${cx} ${cy})`}>
        <circle cx={cx} cy={cy} r={R} fill="none" stroke={P.color} strokeWidth={P.ringW} strokeDasharray={`${R * 1.6} ${R * 0.22}`} />
        <circle cx={cx} cy={cy} r={R} fill="none" stroke="#FFFFFF" strokeWidth={P.ringW * 0.25} strokeDasharray={`${R * 1.6} ${R * 0.22}`} />
        <line x1={cx - R * 1.15} y1={cy + R * 0.9} x2={cx + R * 1.15} y2={cy - R * 0.9} stroke={P.color} strokeWidth={P.ringW * 0.45} />
        <line x1={cx - R * 1.15} y1={cy + R * 0.9} x2={cx + R * 1.15} y2={cy - R * 0.9} stroke="#FFFFFF" strokeWidth={P.ringW * 0.12} />
      </g>
    </svg>
  );
  if (g < cut) {
    const beamOp = g < r0 + 2 ? 1 - clamp01((g - r0) / 2) : 0;
    const k = clamp01((g - r0) / P.ringLen);
    const tint = L(g, r0, r1, 0, 0.55);
    const R = 260 + 900 * Easing.in(Easing.quad)(k);
    const rad = (P.angle * Math.PI) / 180;
    return (
      <AbsoluteFill>
        {g < r1 ? from : <AbsoluteFill style={{ background: P.flat }} />}
        {g < r1 && tint > 0 && <AbsoluteFill style={{ background: P.flat, opacity: tint }} />}
        {beamOp > 0 && (
          <svg width={W} height={H} style={{ position: "absolute", filter: `drop-shadow(0 0 10px ${P.color}) drop-shadow(0 0 20px ${P.color})`, opacity: beamOp }}>
            {Array.from({ length: Math.round(P.beams) }).map((_, i) => {
              const off = (i - (P.beams - 1) / 2) * 140 + g * 60;
              const nx = -Math.sin(rad) * off, ny = Math.cos(rad) * off;
              return <line key={i} x1={cx + nx - Math.cos(rad) * 1400} y1={cy + ny - Math.sin(rad) * 1400} x2={cx + nx + Math.cos(rad) * 1400} y2={cy + ny + Math.sin(rad) * 1400} stroke="#E9FFFF" strokeWidth={i === 1 ? 7 : 4} />;
            })}
          </svg>
        )}
        {g >= r0 && g < r1 && ringSvg(R, g * 14, 1)}
      </AbsoluteFill>
    );
  }
  const k = clamp01((g - cut) / P.shrinkLen);
  return (
    <AbsoluteFill>
      {to}
      {g < len && <AbsoluteFill style={{ background: P.flat, opacity: 0.5 * (1 - k) }} />}
      {g < len && ringSvg(420 * L(k, 0, 1, 1, 0.4, OUT), 40 + g * 10, 1 - k)}
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 11. 먹물 방울 흩어짐 리빌 [ref4-samsung 52:24] — f0 하드컷 전면 커버(#3E3841 셰이딩 구체)
//     → 24f 동안 방울이 바깥으로 흩어지며 축소(1.0→0.2)·페이드, 중앙부터 개방. 가장자리 잔여 ≈f30.
// ═══════════════════════════════════════════════════════════════════════════
export const InkBlobRevealParams = z.object({
  n: num(55, 10, 120, 1, "방울 개수", "size"),
  dMin: num(60, 20, 300, 5, "방울 최소 지름", "size", "px"),
  dMax: num(260, 60, 600, 5, "방울 최대 지름", "size", "px"),
  coverScale: num(1.9, 1, 4, 0.05, "시작 때 방울 부풀림(배)", "size"),
  len: num(24, 6, 60, 1, "흩어지는 시간", "timing", "f"),
  tail: num(8, 0, 30, 1, "가장자리 잔여 추가 시간", "timing", "f"),
  spread: num(650, 100, 1500, 10, "흩어지는 거리", "motion", "px"),
  endScale: num(0.2, 0, 1, 0.05, "끝 크기(배)", "motion"),
  color: col("#3E3841", "방울 색"),
});
export type InkBlobRevealP = z.infer<typeof InkBlobRevealParams>;
export const InkBlobReveal: React.FC<{ at: number; from?: Node; to: Node; seed?: string; p?: Partial<InkBlobRevealP> }> = ({ at, from, to, seed = "ink", p }) => {
  const P = def(InkBlobRevealParams, p);
  const f = useCurrentFrame(), g = f - at;
  if (g < 0) return <AbsoluteFill>{from}</AbsoluteFill>;
  const N = Math.round(P.n);
  const hi = interpolateHex(P.color, "#8A8290", 0.45);
  return (
    <AbsoluteFill>
      {to}
      {g < 1 && <AbsoluteFill style={{ background: P.color }} />}
      {Array.from({ length: N }).map((_, i) => {
        // 격자 + 지터 로 전면을 고르게 덮는다
        const cols = Math.ceil(Math.sqrt(N * (W / H)));
        const rows = Math.ceil(N / cols);
        const bx = ((i % cols) + 0.5 + (random(`${seed}x${i}`) - 0.5) * 0.9) * (W / cols);
        const by = (Math.floor(i / cols) + 0.5 + (random(`${seed}y${i}`) - 0.5) * 0.9) * (H / rows);
        const d0 = P.dMin + random(`${seed}d${i}`) * (P.dMax - P.dMin);
        const dx = bx - W / 2, dy = by - H / 2, dist = Math.hypot(dx, dy) || 1;
        const edge = dist / Math.hypot(W / 2, H / 2); // 0 중앙 → 1 가장자리
        const life = P.len + P.tail * edge;
        const t = clamp01(g / life);
        const e = Easing.out(Easing.quad)(t);
        const x = bx + (dx / dist) * P.spread * e * (0.6 + edge * 0.6);
        const y = by + (dy / dist) * P.spread * e * (0.6 + edge * 0.6);
        const s = L(t, 0, 1, P.coverScale, P.endScale, Easing.in(Easing.quad));
        const op = t < 0.55 ? 1 : 1 - (t - 0.55) / 0.45;
        if (op <= 0) return null;
        const d = d0 * s;
        return <div key={i} style={{ position: "absolute", left: x - d / 2, top: y - d / 2, width: d, height: d * (0.9 + random(`${seed}r${i}`) * 0.2), borderRadius: "50%", opacity: op, background: `radial-gradient(circle at 35% 30%, ${hi} 0%, ${P.color} 45%, ${interpolateHex(P.color, "#000000", 0.25)} 100%)` }} />;
      })}
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 12. 가로 팬 → 문 안 인물 푸시인 [ref4-apple 1:21:56] — 오른쪽 트럭 15f(무대 ~500px, easeInOut, 전경 블러 인물은 더 빨리 빠짐)
//     → 끊김 없이 푸시인 1.0→1.8 ≈39f(1.3s) 로 문틀이 화면 폭 ~70% 될 때까지.
// ═══════════════════════════════════════════════════════════════════════════
export const TruckPushInParams = z.object({
  pan: num(500, 0, 1500, 10, "가로 이동 거리", "motion", "px"),
  panLen: num(15, 1, 60, 1, "가로 트럭 시간", "timing", "f"),
  pushTo: num(1.8, 1, 4, 0.05, "푸시인 배율", "motion"),
  pushLen: num(39, 1, 120, 1, "푸시인 시간", "timing", "f"),
  center: num(0.6, 0, 1, 0.05, "목표를 화면 중앙으로 끄는 정도", "motion"),
  fgSpeed: num(1.7, 1, 4, 0.1, "전경 이동 배속", "motion", "배"),
  fgBlur: num(8, 0, 30, 1, "전경 블러", "look", "px"),
});
export type TruckPushInP = z.infer<typeof TruckPushInParams>;
/** stage: 가로로 넓은 무대(폭 W+pan 이상, 좌상단 기준). target = 무대 좌표의 푸시 목표(문 중심). fg: 전경 레이어(화면 좌표) */
export const TruckPushIn: React.FC<{ at: number; stage: Node; target: [number, number]; fg?: Node; p?: Partial<TruckPushInP> }> = ({ at, stage, target, fg, p }) => {
  const P = def(TruckPushInParams, p);
  const f = useCurrentFrame(), g = f - at;
  const e1 = L(g, 0, P.panLen, 0, 1, IO);
  const e2 = L(g, P.panLen, P.panLen + P.pushLen, 0, 1, IO);
  const camX = P.pan * e1;
  const s = 1 + (P.pushTo - 1) * e2;
  const tx = target[0] - camX, ty = target[1];
  const cxOff = (W / 2 - tx) * P.center * e2, cyOff = (H / 2 - ty) * P.center * e2;
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <div style={{ position: "absolute", inset: 0, transformOrigin: `${tx}px ${ty}px`, transform: `translate(${cxOff}px,${cyOff}px) scale(${s})` }}>
        <div style={{ position: "absolute", left: -camX, top: 0, width: W + P.pan + 200, height: H }}>{stage}</div>
      </div>
      {fg && (
        <div style={{ position: "absolute", inset: 0, transform: `translateX(${-camX * P.fgSpeed}px) scale(${1 + (s - 1) * 1.3})`, transformOrigin: `${tx}px ${ty}px`, filter: `blur(${P.fgBlur}px)` }}>{fg}</div>
      )}
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 13. 카메라 틸트업 표지판 리빌 [ref4-apple 1:27:50] — Y자 갈림길 + 노을 하늘(#F5C13A→#E8736A).
//     도로가 1.5s 동안 ≈80px 아래로 흐르고(틸트업) 하늘이 노랑→분홍, 초록 표지판이 위에서 드롭(f6→f18, 2번 +10f, 미세 바운스)
//     → 인물 뒷모습 하단에서 등장 → 한 표지판에 빨간 동심원 강조.
// ═══════════════════════════════════════════════════════════════════════════
export type RoadSign = { text: string; sub?: string; subColor?: string; dir: "left" | "right" };
export const TiltUpSignRevealParams = z.object({
  tilt: num(80, 0, 400, 5, "도로 흐름(틸트) 거리", "motion", "px"),
  tiltLen: num(45, 5, 150, 1, "틸트 시간", "timing", "f"),
  signAt: num(6, 0, 60, 1, "첫 표지판 드롭 시작", "timing", "f"),
  dropLen: num(12, 3, 40, 1, "표지판 드롭 시간", "timing", "f"),
  stagger: num(10, 0, 40, 1, "표지판 간격", "timing", "f"),
  bounce: num(0.12, 0, 0.5, 0.01, "착지 바운스", "motion"),
  personAt: num(40, 0, 150, 1, "뒷모습 등장", "timing", "f"),
  circleAt: num(70, 0, 170, 1, "동심원 강조 시작", "timing", "f"),
  skyTop: col("#F5C13A", "하늘 위(노랑)"),
  skyBot: col("#E8736A", "하늘 아래(분홍)"),
  signColor: col("#2F7D3E", "표지판 색"),
  ringColor: col("#E0302A", "동심원 색"),
});
export type TiltUpSignRevealP = z.infer<typeof TiltUpSignRevealParams>;
export const TiltUpSignReveal: React.FC<{ at: number; signs: RoadSign[]; person?: Cut; highlight?: number; p?: Partial<TiltUpSignRevealP> }> = ({ at, signs, person, highlight = 0, p }) => {
  const P = def(TiltUpSignRevealParams, p);
  const f = useCurrentFrame(), g = f - at;
  const k = L(g, 0, P.tiltLen, 0, 1, IO);
  const dy = P.tilt * k;
  const hz0 = 560; // 지평선
  const poleX = 1000;
  const back = Easing.bezier(0.3, 1.6 + P.bounce * 4, 0.5, 1);
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <AbsoluteFill style={{ background: `linear-gradient(180deg, ${P.skyTop} 0%, #F1A24A 55%, ${P.skyBot} 100%)` }} />
      <AbsoluteFill style={{ background: `linear-gradient(180deg, ${P.skyBot} 0%, #EE8A6A 50%, ${P.skyTop} 100%)`, opacity: k * 0.85 }} />
      <div style={{ position: "absolute", inset: 0, transform: `translateY(${dy}px)` }}>
        <svg width={W} height={H + 400} style={{ position: "absolute", top: 0 }}>
          <path d={`M0,${hz0} L0,${hz0 - 30} Q160,${hz0 - 70} 300,${hz0 - 40} T620,${hz0 - 50} T900,${hz0 - 35} T1250,${hz0 - 60} T1560,${hz0 - 30} T1920,${hz0 - 55} L1920,${hz0} Z`} fill="#5B2E3C" />
          <rect x={0} y={hz0} width={W} height={H + 400 - hz0} fill="#C99A86" />
          {/* Y 갈림길 */}
          <path d={`M700,${H + 400} L850,${hz0 + 300} Q870,${hz0 + 150} 420,${hz0 + 34} L250,${hz0 + 6} L690,${hz0 + 6} Q960,${hz0 + 110} 1230,${hz0 + 6} L1670,${hz0 + 6} L1500,${hz0 + 34} Q1050,${hz0 + 150} 1070,${hz0 + 300} L1220,${H + 400} Z`} fill="#3B3A40" stroke="#F4EFEA" strokeWidth={8} strokeLinejoin="round" />
          <path d={`M960,${hz0 + 10} L960,${hz0 + 60}`} stroke="#F4EFEA" strokeWidth={3} />
          {Array.from({ length: 30 }).map((_, i) => <circle key={i} cx={(i * 263) % W} cy={hz0 + 40 + ((i * 97) % 400)} r={3 + (i % 3)} fill="rgba(90,50,40,0.18)" />)}
        </svg>
        {/* 기둥 */}
        <div style={{ position: "absolute", left: poleX - 7, top: 180, width: 14, height: hz0 - 180 + 20, background: "linear-gradient(90deg,#8E8E93,#C9C9CD,#8E8E93)" }} />
      </div>
      {/* 표지판(월드에 부착되지만 위에서 떨어진다) */}
      {signs.map((s, i) => {
        const t0 = P.signAt + i * P.stagger;
        if (g < t0) return null;
        const sy = L(g, t0, t0 + P.dropLen, -420, 0, back);
        const x = poleX + (s.dir === "left" ? -330 : 20), y = 160 + i * 130 + dy;
        const sw = 310, sh = 96;
        const ring = i === highlight && g >= P.circleAt;
        return (
          <div key={i} style={{ position: "absolute", left: x, top: y + sy, width: sw, height: sh }}>
            <div style={{ position: "absolute", inset: 0, background: P.signColor, border: "5px solid #fff", borderRadius: 10, boxShadow: "0 5px 0 rgba(0,0,0,0.25)", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", paddingLeft: s.dir === "left" ? 40 : 0, paddingRight: s.dir === "right" ? 40 : 0, boxSizing: "border-box" }}>
              <div style={{ fontFamily: "NeoHv", fontSize: 38, color: "#fff", lineHeight: 1, paddingTop: 6 }}>{s.text}</div>
              {s.sub && <div style={{ fontFamily: "NeoHv", fontSize: 24, color: s.subColor || "#FF5A4A", lineHeight: 1.1 }}>{s.sub}</div>}
            </div>
            <div style={{ position: "absolute", top: sh / 2 - 18, [s.dir === "left" ? "left" : "right"]: 14, width: 0, height: 0, borderTop: "18px solid transparent", borderBottom: "18px solid transparent", [s.dir === "left" ? "borderRight" : "borderLeft"]: "26px solid #fff" } as React.CSSProperties} />
            {ring && [0, 1, 2].map((j) => {
              const ph = ((g - P.circleAt + j * 7) % 21) / 21;
              const r = 50 + ph * 110;
              return <div key={j} style={{ position: "absolute", left: sw / 2 - r, top: sh / 2 - r, width: r * 2, height: r * 2, borderRadius: "50%", border: `5px solid ${P.ringColor}`, opacity: 1 - ph }} />;
            })}
          </div>
        );
      })}
      {person && g >= P.personAt && (() => {
        const pw = 560, ph = pw * cutAR(person);
        const y = L(g, P.personAt, P.personAt + 16, H + 40, H - ph * 0.55, OUT);
        return <div style={{ position: "absolute", left: 520, top: y }}><CutImg c={person} w={pw} /></div>;
      })()}
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 14. 직전 장면 디포커스 백드롭 [ref4-cocacola 8:03·6:09·28:53] — 컷 없이 직전 장면을 가우시안 0→14px(8f, ease-out)
//     밝기·채도 유지 → 블러 직후 새 레이어 팝(0.2→1.25→1.0, 6f) 또는 위에서 드롭.
// ═══════════════════════════════════════════════════════════════════════════
export const RackDefocusParams = z.object({
  blur: num(14, 0, 40, 1, "배경 블러", "look", "px"),
  blurLen: num(8, 1, 30, 1, "블러 시간", "timing", "f"),
  push: num(1.03, 1, 1.2, 0.01, "배경 미세 확대(배)", "motion"),
  popDelay: num(0, -8, 20, 1, "블러 끝 → 레이어 등장", "timing", "f"),
  popLen: num(6, 2, 20, 1, "팝 길이", "timing", "f"),
  popFrom: num(0.2, 0, 1, 0.05, "팝 시작 크기", "motion"),
  popOver: num(1.25, 1, 1.6, 0.01, "팝 오버슈트", "motion"),
  entry: choice("pop", ["pop", "drop"] as const, "레이어 등장 방식"),
  dropDist: num(700, 100, 1200, 10, "드롭 거리", "motion", "px"),
  exit: choice("none", ["none", "drop"] as const, "레이어 퇴장(none · drop=아래로 낙하 + 블러 해제)"),
  exitAt: num(40, 0, 300, 1, "drop: 퇴장 시작(at 기준)", "timing", "f"),
  exitLen: num(8, 1, 30, 1, "drop: 낙하 길이", "timing", "f"),
  exitDist: num(1100, 100, 1600, 10, "drop: 낙하 거리", "motion", "px"),
  exitBlur: num(10, 0, 40, 1, "drop: 세로 모션블러", "look", "px"),
  undimLen: num(10, 1, 40, 1, "drop: 배경 블러 해제 길이", "timing", "f"),
});
export type RackDefocusP = z.infer<typeof RackDefocusParams>;
export const RackDefocus: React.FC<{ at: number; backdrop: Node; layer: Node; origin?: string; p?: Partial<RackDefocusP> }> = ({ at, backdrop, layer, origin = "50% 50%", p }) => {
  const P = def(RackDefocusParams, p);
  const f = useCurrentFrame(), g = f - at;
  const b = L(g, 0, P.blurLen, 0, P.blur, OUT);
  const s = L(g, 0, P.blurLen, 1, P.push, OUT);
  const t0 = P.blurLen + P.popDelay;
  const pop = P.entry === "pop" ? L(g, t0, t0 + P.popLen * 0.6, P.popFrom, P.popOver, Easing.out(Easing.quad)) * (g < t0 + P.popLen * 0.6 ? 1 : L(g, t0 + P.popLen * 0.6, t0 + P.popLen, 1, 1 / P.popOver, Easing.inOut(Easing.quad))) : 1;
  const dy = P.entry === "drop" ? L(g, t0, t0 + P.popLen * 1.6, -P.dropDist, 0, Easing.bezier(0.3, 1.25, 0.5, 1)) : 0;
  if (P.exit === "drop" && g >= P.exitAt) {
    // 낙하 퇴장 [설명형 레퍼런스 #5]: 레이어 아래로 ease-in(세로 모션블러) + 배경 블러·확대 해제
    const u = L(g, P.exitAt, P.exitAt + P.exitLen, 0, 1, Easing.in(Easing.quad));
    const r = L(g, P.exitAt, P.exitAt + P.undimLen, 1, 0, OUT);
    const vb = P.exitBlur * Math.sin(Math.PI * Math.min(1, u)) + (u > 0 ? 1 : 0), fid = `rdDrop${at}`;
    return (
      <AbsoluteFill style={{ overflow: "hidden" }}>
        <AbsoluteFill style={{ filter: b * r > 0.2 ? `blur(${b * r}px)` : undefined, transform: `scale(${1 + (s - 1) * r})` }}>{backdrop}</AbsoluteFill>
        {g >= t0 && u < 1 && (
          <AbsoluteFill style={{ transform: `translateY(${dy + P.exitDist * u}px) scale(${pop})`, transformOrigin: origin, filter: vb > 0.3 ? `url(#${fid})` : undefined }}>
            <svg width={0} height={0} style={{ position: "absolute" }}><filter id={fid} x="-5%" y="-30%" width="110%" height="160%"><feGaussianBlur stdDeviation={`0 ${vb.toFixed(2)}`} /></filter></svg>
            {layer}
          </AbsoluteFill>
        )}
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <AbsoluteFill style={{ filter: b > 0.2 ? `blur(${b}px)` : undefined, transform: `scale(${s})` }}>{backdrop}</AbsoluteFill>
      {g >= t0 && <AbsoluteFill style={{ transform: `translateY(${dy}px) scale(${pop})`, transformOrigin: origin }}>{layer}</AbsoluteFill>}
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 15. 아이소메트릭 빌드업 풀백 [ref4-hyundai 1:12:34] — scale 1.8→1.0 약 60f easeInOut + 좌상향 팬.
//     풀백 중 요소 팝(0.6→1.0, 6f)·크레인 수직 상승·컨테이너 드롭(8f), 스태거 4f → 연도칩 팝.
// ═══════════════════════════════════════════════════════════════════════════
export type IsoItem = { kind: "box" | "crane" | "ship" | "drop"; gx: number; gy: number; w: number; d: number; h: number; color: string; top?: string };
const ISO_T = 46;
const iso = (gx: number, gy: number, gz: number): [number, number] => [(gx - gy) * ISO_T * 0.866, (gx + gy) * ISO_T * 0.5 - gz * ISO_T];
const shade = (hex: string, k: number) => interpolateHex(hex, k < 0 ? "#000000" : "#FFFFFF", Math.abs(k));
const IsoBox: React.FC<{ gx: number; gy: number; gz?: number; w: number; d: number; h: number; color: string; top?: string }> = ({ gx, gy, gz = 0, w, d, h, color, top }) => {
  const P = (x: number, y: number, z: number) => iso(gx + x, gy + y, gz + z).map((v) => v.toFixed(1)).join(",");
  return (
    <g>
      <polygon points={[P(0, d, 0), P(w, d, 0), P(w, d, h), P(0, d, h)].join(" ")} fill={shade(color, -0.12)} />
      <polygon points={[P(w, 0, 0), P(w, d, 0), P(w, d, h), P(w, 0, h)].join(" ")} fill={shade(color, -0.28)} />
      <polygon points={[P(0, 0, h), P(w, 0, h), P(w, d, h), P(0, d, h)].join(" ")} fill={top || shade(color, 0.15)} />
    </g>
  );
};
/** 아이소 소품 스프라이트: 이미지의 (0.5, ay) = 바닥 중심을 (x,y) 에. s = 팝 배율, sy = 세로(상승) 배율, tint = 흰 컨테이너 색 입힘(multiply) */
const IsoSprite: React.FC<{ id: string; x: number; y: number; w: number; ay: number; s?: number; sy?: number; tint?: string }> = ({ id, x, y, w, ay, s = 1, sy = 1, tint }) => {
  const h = propH(id, w), mk = `url(${prop(id)})`;
  return (
    <div style={{ position: "absolute", left: x - w / 2, top: y - ay * h, width: w, height: h, transformOrigin: `50% ${ay * 100}%`, transform: `scale(${s},${s * sy})`, isolation: "isolate" }}>
      <Img src={prop(id)} style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }} />
      {tint && <div style={{ position: "absolute", inset: 0, background: tint, mixBlendMode: "multiply", WebkitMaskImage: mk, maskImage: mk, WebkitMaskSize: "100% 100%", maskSize: "100% 100%" } as React.CSSProperties} />}
    </div>
  );
};
export const DEFAULT_PORT: IsoItem[] = (() => {
  const items: IsoItem[] = [];
  items.push({ kind: "box", gx: -2, gy: -6, w: 7, d: 3, h: 2.2, color: "#E9DCC4", top: "#5E7FD6" }); // 창고
  const cc = ["#E0473A", "#4A6FD0", "#F2C230", "#EDEDED", "#E0473A", "#4A6FD0"];
  for (let i = 0; i < 12; i++) items.push({ kind: "drop", gx: -1 + (i % 6) * 1.2, gy: -1.6 + Math.floor(i / 6) * 1.1, w: 1, d: 0.9, h: 0.8, color: cc[i % 6] });
  for (let i = 0; i < 3; i++) items.push({ kind: "crane", gx: 8 + i * 2.6, gy: -3.5 + i * 0.4, w: 0.5, d: 3.2, h: 5.2, color: "#E4442F" });
  for (let i = 0; i < 8; i++) items.push({ kind: "drop", gx: 8.5 + (i % 4) * 1.2, gy: 1.2 + Math.floor(i / 4) * 1.1, w: 1, d: 0.9, h: 0.8, color: cc[(i + 2) % 6] });
  items.push({ kind: "ship", gx: 7, gy: 5.5, w: 9, d: 2.2, h: 1.1, color: "#3B3F4A" });
  return items;
})();
export const IsoBuildPullbackParams = z.object({
  s0: num(1.8, 1, 4, 0.05, "시작 확대(배)", "motion"),
  len: num(60, 10, 180, 1, "풀백 시간", "timing", "f"),
  panX: num(260, -800, 800, 10, "시작 팬 X", "motion", "px"),
  panY: num(180, -800, 800, 10, "시작 팬 Y", "motion", "px"),
  popLen: num(6, 2, 20, 1, "요소 팝", "timing", "f"),
  dropLen: num(8, 2, 30, 1, "컨테이너 드롭", "timing", "f"),
  riseLen: num(10, 2, 30, 1, "크레인 상승", "timing", "f"),
  stagger: num(3, 0, 12, 0.5, "요소 스태거", "timing", "f"),
  chipAt: num(66, 0, 180, 1, "연도칩 팝", "timing", "f"),
  sea: col("#3FA9AE", "바다 색"),
  quay: col("#D9DBE0", "부두 색"),
});
export type IsoBuildPullbackP = z.infer<typeof IsoBuildPullbackParams>;
export const IsoBuildPullback: React.FC<{ at: number; items?: IsoItem[]; chip?: string; p?: Partial<IsoBuildPullbackP> }> = ({ at, items = DEFAULT_PORT, chip = "3년", p }) => {
  const P = def(IsoBuildPullbackParams, p);
  const f = useCurrentFrame(), g = f - at;
  const k = L(g, 0, P.len, 0, 1, IO);
  const s = P.s0 + (1 - P.s0) * k;
  const px = P.panX * (1 - k), py = P.panY * (1 - k);
  const order = items.map((it, i) => ({ it, i })).sort((a, b) => (a.it.gx + a.it.gy) - (b.it.gx + b.it.gy));
  const ox = 820, oy = 470;
  const quay = [iso(-5, -9, 0), iso(15, -9, 0), iso(15, 3.4, 0), iso(-5, 3.4, 0)].map((q) => `${q[0]},${q[1]}`).join(" ");
  const road = [iso(-5, -2.8, 0.01), iso(15, -2.8, 0.01), iso(15, -2.1, 0.01), iso(-5, -2.1, 0.01)].map((q) => `${q[0]},${q[1]}`).join(" ");
  const chipS = L(g, P.chipAt, P.chipAt + 4, 0.3, 1.1, OUT) * L(g, P.chipAt + 4, P.chipAt + 6, 1, 1 / 1.1);
  return (
    <AbsoluteFill style={{ background: P.sea, overflow: "hidden" }}>
      <svg width={W} height={H} style={{ position: "absolute", transform: `translate(${px}px,${py}px) scale(${s})`, transformOrigin: "55% 50%" }}>
        <g transform={`translate(${ox},${oy})`}>
          {Array.from({ length: 14 }).map((_, i) => <path key={i} d={`M${-900 + (i * 173) % 1800},${250 + (i * 71) % 400} q30,-10 60,0`} stroke="rgba(255,255,255,0.35)" strokeWidth={4} fill="none" />)}
          <polygon points={quay} fill={P.quay} />
          <polygon points={road} fill="#55575E" />
        </g>
      </svg>
      {/* 세모지 그림체 아이소 소품(iso_warehouse·iso_container·iso_crane·iso_ship)을 같은 아이소 좌표에 배치(svg 와 같은 변환) */}
      <div style={{ position: "absolute", left: 0, top: 0, width: W, height: H, transform: `translate(${px}px,${py}px) scale(${s})`, transformOrigin: "55% 50%" }}>
        <div style={{ position: "absolute", left: ox, top: oy }}>
          {order.map(({ it, i }) => {
            const t0 = 6 + i * P.stagger;
            if (g < t0) return null;
            const [bx, by] = iso(it.gx + it.w / 2, it.gy + it.d / 2, 0);
            const foot = (it.w + it.d) * ISO_T * 0.866; // 바닥 마름모 가로폭
            if (it.kind === "drop") {
              const z = L(g, t0, t0 + P.dropLen, 4, 0, Easing.bezier(0.5, 0, 0.8, 1));
              return <IsoSprite key={i} id="iso_container" x={bx} y={by - z * ISO_T} w={foot * 1.15} ay={0.6} tint={it.color} />;
            }
            if (it.kind === "crane") {
              const k2 = L(g, t0, t0 + P.riseLen, 0.2 / it.h, 1, OUT);
              const [cx, cy] = iso(it.gx + 1, it.gy + it.d / 2, 0);
              return <IsoSprite key={i} id="iso_crane" x={cx} y={cy} w={foot * 1.25} ay={0.86} sy={k2} />;
            }
            const pk = L(g, t0, t0 + P.popLen, 0.6, 1, Easing.out(Easing.back(2)));
            return it.kind === "ship"
              ? <IsoSprite key={i} id="iso_ship" x={bx} y={by} w={foot * 1.05} ay={0.62} s={pk} />
              : <IsoSprite key={i} id="iso_warehouse" x={bx} y={by} w={foot * 0.9} ay={0.72} s={pk} />;
          })}
        </div>
      </div>
      {g >= P.chipAt && <div style={{ position: "absolute", left: 60, top: 150, transform: `scale(${chipS})`, transformOrigin: "0 50%", background: "#1F2A6B", color: "#fff", fontFamily: "NeoHv", fontSize: 58, padding: "12px 36px 4px", borderRadius: 40, boxShadow: "0 0 0 5px #fff" }}>{chip}</div>}
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 16. 쌍안경 마스크 시점 [ref4-hyundai 1:55:59] — 두 원(지름 975, 겹침 316, x146–1780 / y45–1020) 소프트 브라운 비네트,
//     바깥 순흑. 챕터카드에서 하드컷, 안에서 장면이 등속 이동·미세 팬.
// ═══════════════════════════════════════════════════════════════════════════
export const BinocularPOVParams = z.object({
  d: num(975, 400, 1400, 5, "원 지름", "size", "px"),
  overlap: num(316, 0, 900, 2, "원 겹침", "size", "px"),
  cy: num(532, 300, 780, 2, "원 중심 높이", "size", "px"),
  vignette: num(46, 0, 160, 2, "테두리 비네트 두께", "look", "px"),
  vigColor: col("#6B4A2A", "비네트 색"),
  sway: num(6, 0, 40, 1, "미세 흔들림", "motion", "px"),
  swayPeriod: num(70, 10, 240, 1, "흔들림 주기", "timing", "f"),
});
export type BinocularPOVP = z.infer<typeof BinocularPOVParams>;
export const BinocularPOV: React.FC<{ at?: number; from?: Node; children: Node; p?: Partial<BinocularPOVP> }> = ({ at = 0, from, children, p }) => {
  const P = def(BinocularPOVParams, p);
  const f = useCurrentFrame(), g = f - at;
  const id = useId("bino");
  if (g < 0) return <AbsoluteFill>{from}</AbsoluteFill>;
  const r = P.d / 2, D = P.d - P.overlap;
  const c1 = W / 2 - D / 2, c2 = W / 2 + D / 2, cy = P.cy;
  const hy = Math.sqrt(Math.max(0, r * r - (D / 2) * (D / 2)));
  const path = D < P.d ? `M${W / 2},${cy - hy} A${r},${r} 0 1 0 ${W / 2},${cy + hy} A${r},${r} 0 1 0 ${W / 2},${cy - hy} Z` : `M${c1 - r},${cy} a${r},${r} 0 1 0 ${2 * r},0 a${r},${r} 0 1 0 ${-2 * r},0 M${c2 - r},${cy} a${r},${r} 0 1 0 ${2 * r},0 a${r},${r} 0 1 0 ${-2 * r},0`;
  const sx = Math.sin((g / P.swayPeriod) * Math.PI * 2) * P.sway, sy = Math.cos((g / P.swayPeriod) * Math.PI * 1.3) * P.sway * 0.5;
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <svg width={0} height={0} style={{ position: "absolute" }}><defs><clipPath id={id}><path d={path} /></clipPath></defs></svg>
      <AbsoluteFill style={{ clipPath: `url(#${id})` }}>
        <AbsoluteFill style={{ transform: `translate(${sx}px,${sy}px) scale(1.02)` }}>{children}</AbsoluteFill>
        <svg width={W} height={H} style={{ position: "absolute", filter: `blur(${P.vignette * 0.45}px)` }}>
          <path d={path} fill="none" stroke={P.vigColor} strokeWidth={P.vignette * 2} opacity={0.85} />
        </svg>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 17. 단어 카드 [ref2 117s~] — 연녹회 #D9E3D6 배경에 접속어 한 단어(‘그런데’)만 ≈0.5s.
// ═══════════════════════════════════════════════════════════════════════════
export const WordCardParams = z.object({
  hold: num(15, 3, 60, 1, "카드 길이", "timing", "f"),
  size: num(110, 40, 240, 2, "글자 크기", "size", "px"),
  bg: col("#D9E3D6", "배경"),
  color: col("#1F1F1F", "글자 색"),
});
export type WordCardP = z.infer<typeof WordCardParams>;
export const WordCard: React.FC<{ text: string; at?: number; from?: Node; to?: Node; p?: Partial<WordCardP> }> = ({ text, at = 0, from, to, p }) => {
  const P = def(WordCardParams, p);
  const f = useCurrentFrame(), g = f - at;
  if (g < 0) return <AbsoluteFill>{from}</AbsoluteFill>;
  if (g >= P.hold) return <AbsoluteFill>{to}</AbsoluteFill>;
  return (
    <AbsoluteFill style={{ background: P.bg, alignItems: "center", justifyContent: "center" }}>
      <div style={{ fontFamily: "NeoHv", fontSize: P.size, color: P.color, paddingTop: P.size * 0.1 }}>{text}</div>
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 18. 실사 클립 몽타주 인트로 [ref1 0:00–0:27] — 실사 클립 하드컷 연결, 후반 구간은 ≈5f 마다 컷. 좌상단 TOP10 배지.
// ═══════════════════════════════════════════════════════════════════════════
export const IntroMontageParams = z.object({
  slowHold: num(20, 4, 90, 1, "앞 구간 컷 길이", "timing", "f"),
  fastHold: num(5, 2, 20, 1, "빠른 구간 컷 길이", "timing", "f"),
  fastFrom: num(3, 0, 20, 1, "빠른 구간 시작 클립 번호", "timing"),
  kenBurns: num(0.06, 0, 0.3, 0.01, "클립 줌(배)", "motion"),
  badge: flag(true, "TOP10 배지", "look"),
  badgeColor: col("#E50914", "배지 색"),
});
export type IntroMontageP = z.infer<typeof IntroMontageParams>;
export const IntroMontage: React.FC<{ clips: string[]; at?: number; chip?: string; p?: Partial<IntroMontageP> }> = ({ clips, at = 0, chip = "비영어권 프로그램", p }) => {
  const P = def(IntroMontageParams, p);
  const f = useCurrentFrame();
  let g = Math.max(0, f - at), idx = 0, t0 = 0;
  // 클립별 길이: fastFrom 이전은 slowHold, 이후 fastHold. 끝나면 처음부터 반복
  const lens = clips.map((_, i) => (i < P.fastFrom ? P.slowHold : P.fastHold));
  const total = lens.reduce((a, b) => a + b, 0) || 1;
  g = g % total;
  while (idx < clips.length - 1 && g >= t0 + lens[idx]) { t0 += lens[idx]; idx++; }
  const lt = (g - t0) / lens[idx];
  return (
    <AbsoluteFill style={{ background: "#000", overflow: "hidden" }}>
      <Img src={src(clips[idx])} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", transform: `scale(${1 + P.kenBurns * lt})` }} />
      {P.badge && (
        <div style={{ position: "absolute", left: 200, top: 30, display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{ width: 66, height: 66, background: P.badgeColor, color: "#fff", fontFamily: "NeoHv", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", lineHeight: 0.9 }}>
            <span style={{ fontSize: 17 }}>TOP</span><span style={{ fontSize: 34 }}>10</span>
          </div>
          <div style={{ background: "#141414", color: "#fff", fontFamily: "NeoHv", fontSize: 30, padding: "12px 20px 6px", borderRadius: 4 }}>{chip} <span style={{ color: P.badgeColor }}>▼</span></div>
        </div>
      )}
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 19. 아웃트로 리캡 구성 [ref1 13:45 = 824.9–857.6s] — 라이트릭 번 → 하늘 배경 두루마리 라벨·메달리온·이름·브래킷 결론
//     → 하드컷 붉은 배경 인물 누적(인물당 10f 팝, 간격 누적) → 엔드카드. 데모는 시간 압축 기본값.
// ═══════════════════════════════════════════════════════════════════════════
export type RecapItem = { label: string; img: Cut; name: string; color: string };
export const OutroRecapParams = z.object({
  burnLen: num(10, 0, 40, 1, "라이트릭 번", "timing", "f"),
  labelStagger: num(5, 0, 30, 1, "라벨 스태거", "timing", "f"),
  medAt: num(22, 0, 120, 1, "메달리온 시작", "timing", "f"),
  medStagger: num(5, 0, 30, 1, "메달리온 스태거", "timing", "f"),
  bracketAt: num(50, 0, 200, 1, "브래킷 결론", "timing", "f"),
  cutAt: num(84, 10, 400, 1, "붉은 배경 하드컷", "timing", "f"),
  castEvery: num(9, 2, 120, 1, "인물 누적 간격", "timing", "f"),
  castPop: num(10, 2, 30, 1, "인물 등장 길이", "timing", "f"),
  endAt: num(150, 20, 900, 1, "엔드카드", "timing", "f"),
  sky: col("#CFE6F7", "리캡 하늘"),
  red: col("#B21F28", "붉은 배경"),
});
export type OutroRecapP = z.infer<typeof OutroRecapParams>;
export const OutroRecap: React.FC<{ at?: number; from?: Node; items: RecapItem[]; conclusion: string; cast: Cut[]; endcard?: Node; p?: Partial<OutroRecapP> }> = ({ at = 0, from, items, conclusion, cast, endcard, p }) => {
  const P = def(OutroRecapParams, p);
  const f = useCurrentFrame(), g = f - at;
  if (g < P.burnLen && from) {
    const k = clamp01(g / Math.max(1, P.burnLen));
    return (
      <AbsoluteFill>
        {from}
        <AbsoluteFill style={{ background: "radial-gradient(ellipse 70% 80% at 30% 40%, #FFF5D8 0%, #FFB04A 45%, rgba(255,120,40,0) 100%)", mixBlendMode: "screen", opacity: k }} />
        <AbsoluteFill style={{ background: "#FFF3DF", opacity: Math.max(0, k * 1.4 - 0.4) }} />
      </AbsoluteFill>
    );
  }
  if (g >= P.endAt && endcard) return <AbsoluteFill>{endcard}</AbsoluteFill>;
  if (g >= P.cutAt) {
    const n = cast.length, cw = Math.min(300, (W - 200) / Math.max(1, n) * 1.25);
    return (
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 45%, ${shade(P.red, 0.08)} 0%, ${P.red} 60%, ${shade(P.red, -0.25)} 100%)` }}>
        {Array.from({ length: 7 }).map((_, i) => <div key={i} style={{ position: "absolute", left: 120 + i * 280, top: 0, width: 4, height: 40 + (i % 2) * 30, background: "#E7B64A" }}><div style={{ position: "absolute", left: -16, bottom: -24, width: 36, height: 30, borderRadius: 14, background: "#D8342E", boxShadow: "inset 0 0 0 3px #E7B64A" }} /></div>)}
        {cast.map((c, i) => {
          const t0 = P.cutAt + 4 + i * P.castEvery;
          if (g < t0) return null;
          const k = L(g, t0, t0 + P.castPop, 0, 1, Easing.out(Easing.back(1.6)));
          const x = W / 2 + (i - (n - 1) / 2) * (cw * 0.78);
          const h = cw * cutAR(c);
          return <div key={i} style={{ position: "absolute", left: x - cw / 2, top: 1000 - h + (1 - k) * 80, opacity: clamp01(k * 2), zIndex: i % 2 ? 2 : 1 }}><CutImg c={c} w={cw} /></div>;
        })}
      </AbsoluteFill>
    );
  }
  const n = items.length, gap = 1500 / Math.max(1, n), x0 = W / 2 - (gap * (n - 1)) / 2;
  const bk = L(g, P.bracketAt, P.bracketAt + 8, 0, 1, OUT);
  return (
    <AbsoluteFill style={{ background: `linear-gradient(180deg, ${P.sky} 0%, #EAF4FB 100%)` }}>
      {Array.from({ length: 6 }).map((_, i) => <div key={i} style={{ position: "absolute", left: ((i * 397 + g * 1.2) % 2300) - 300, top: 120 + (i * 151) % 700, width: 380, height: 110, borderRadius: 60, background: "rgba(255,255,255,0.7)", filter: "blur(6px)" }} />)}
      {items.map((it, i) => {
        const x = x0 + i * gap;
        const tl = P.burnLen + i * P.labelStagger, tm = P.medAt + i * P.medStagger;
        const ls = L(g, tl, tl + 5, 0.3, 1, Easing.out(Easing.back(2)));
        const ms = L(g, tm, tm + 6, 0.3, 1, Easing.out(Easing.back(2)));
        return (
          <React.Fragment key={i}>
            {g >= tl && <div style={{ position: "absolute", left: x, top: 170, transform: `translate(-50%,-50%) scale(${ls})`, background: "#F6E6C2", border: `5px solid ${it.color}`, borderLeftWidth: 16, borderRightWidth: 16, fontFamily: "Yeonsung, serif", fontSize: 44, color: "#3A1F1A", padding: "10px 26px 4px", whiteSpace: "nowrap" }}>{hz(it.label)}</div>}
            {g >= tm && (
              <div style={{ position: "absolute", left: x - 140, top: 250, width: 280, height: 280, borderRadius: "50%", background: it.color, overflow: "hidden", transform: `scale(${ms})`, boxShadow: "0 0 0 8px #fff" }}>
                <div style={{ position: "absolute", left: 20, top: 30 }}><CutImg c={it.img} w={240} /></div>
              </div>
            )}
            {g >= tm + 8 && <div style={{ position: "absolute", left: x, top: 590, transform: "translateX(-50%)", fontFamily: "NeoHv", fontSize: 48, color: "#222", whiteSpace: "nowrap", opacity: L(g, tm + 8, tm + 12, 0, 1) }}>{it.name}</div>}
          </React.Fragment>
        );
      })}
      {g >= P.bracketAt && (
        <>
          <svg width={W} height={H} style={{ position: "absolute" }}>
            <path d={`M${x0},660 L${x0},720 L${x0 + gap * (n - 1)},720 L${x0 + gap * (n - 1)},660 M${W / 2},720 L${W / 2},760`} fill="none" stroke="#2F5DAA" strokeWidth={8} pathLength={1} strokeDasharray={1} strokeDashoffset={1 - bk} />
          </svg>
          <div style={{ position: "absolute", left: W / 2, top: 800, transform: `translate(-50%,-50%) scale(${L(g, P.bracketAt + 6, P.bracketAt + 11, 0.3, 1, Easing.out(Easing.back(2)))})`, fontFamily: "NeoHv", fontSize: 64, color: "#1C1C1C", background: "rgba(255,255,255,0.85)", padding: "10px 40px 2px", borderRadius: 14, opacity: g >= P.bracketAt + 6 ? 1 : 0 }}>{conclusion}</div>
        </>
      )}
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 20. 게임쇼 번호문 순차 공개 [ref4-apple 1:24:41] — 빨간 커튼 무대 + 금테 문 4개(≈300×470, 금색 번호판), 가운데 위 원형 엠블럼,
//     아래 관객 실루엣, 스포트라이트 빔 좌우 흔들림. 문 열림 = 빨간 문짝이 오른쪽 끝에서 왼쪽으로 가로 와이프 12f, 스태거 19f.
//     앞 장면에서 세로+가로 모션블러 휩 6f 로 진입.
// ═══════════════════════════════════════════════════════════════════════════
export const GameshowDoorsParams = z.object({
  whipLen: num(6, 0, 20, 1, "휩 진입", "timing", "f"),
  firstAt: num(14, 0, 90, 1, "첫 문 열림", "timing", "f"),
  openLen: num(12, 2, 40, 1, "문 와이프 시간", "timing", "f"),
  stagger: num(19, 0, 60, 1, "문 사이 간격", "timing", "f"),
  doorW: num(300, 150, 420, 5, "문 폭", "size", "px"),
  doorH: num(470, 250, 700, 5, "문 높이", "size", "px"),
  sway: num(14, 0, 40, 1, "스포트라이트 흔들림 각", "motion", "°"),
  swayPeriod: num(90, 20, 300, 1, "흔들림 주기", "timing", "f"),
  curtain: col("#A3162B", "커튼 색"),
  door: col("#D51E4B", "문짝 색"),
  gold: col("#E8B33A", "금테 색"),
});
export type GameshowDoorsP = z.infer<typeof GameshowDoorsParams>;
export const GameshowDoors: React.FC<{ at?: number; from?: Node; people: Cut[]; emblem?: string; p?: Partial<GameshowDoorsP> }> = ({ at = 0, from, people, emblem = "히든\n직원", p }) => {
  const P = def(GameshowDoorsParams, p);
  const f = useCurrentFrame(), g = f - at;
  if (g < 0) return <AbsoluteFill>{from}</AbsoluteFill>;
  const n = people.length, gap = Math.min(110, (W - 160 - n * P.doorW) / Math.max(1, n - 1));
  const x0 = W / 2 - (n * P.doorW + (n - 1) * gap) / 2, y0 = 250;
  const whip = P.whipLen > 0 ? 1 - clamp01(g / P.whipLen) : 0;
  const stage = (
    <AbsoluteFill style={{ background: `repeating-linear-gradient(90deg, ${shade(P.curtain, -0.25)} 0px, ${P.curtain} 40px, ${shade(P.curtain, 0.1)} 60px, ${shade(P.curtain, -0.25)} 100px)` }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: 70, background: `radial-gradient(circle at 50% 0%, ${shade(P.curtain, 0.1)} 0 55px, transparent 56px) 0 0 / 120px 70px repeat-x, ${shade(P.curtain, -0.2)}` }} />
      {/* 스포트라이트(원뿔 2개) */}
      {[[260, 1], [W - 260, -1]].map(([x, sg], i) => {
        const a = sg * 22 + Math.sin((g / P.swayPeriod) * Math.PI * 2 + i * 1.7) * P.sway;
        return <div key={i} style={{ position: "absolute", left: x - 110, top: -40, width: 220, height: 1100, transformOrigin: "50% 0%", transform: `rotate(${a}deg)`, background: "linear-gradient(180deg, rgba(255,250,230,0.55), rgba(255,250,230,0))", clipPath: "polygon(42% 0, 58% 0, 100% 100%, 0 100%)", mixBlendMode: "screen" }} />;
      })}
      {people.map((c, i) => {
        const x = x0 + i * (P.doorW + gap);
        const t0 = P.firstAt + i * P.stagger;
        const k = L(g, t0, t0 + P.openLen, 0, 1, IO);
        const pw = P.doorW * 0.86;
        return (
          <React.Fragment key={i}>
            <div style={{ position: "absolute", left: x + P.doorW / 2 - 34, top: y0 - 70, width: 68, height: 52, borderRadius: 10, background: P.gold, boxShadow: "inset 0 0 0 4px #FFE08A", fontFamily: "NeoHv", fontSize: 40, color: P.curtain, display: "flex", alignItems: "center", justifyContent: "center", paddingTop: 5, boxSizing: "border-box" }}>{i + 1}</div>
            <div style={{ position: "absolute", left: x, top: y0, width: P.doorW, height: P.doorH, borderRadius: "22px 22px 6px 6px", background: "#2A1A1E", boxShadow: `0 0 0 10px ${P.gold}, 0 0 0 14px #9A6A12`, overflow: "hidden" }}>
              <div style={{ position: "absolute", left: (P.doorW - pw) / 2, bottom: -10 }}><CutImg c={c} w={pw} /></div>
              <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: P.doorW * (1 - k), background: `linear-gradient(90deg, ${P.door}, ${shade(P.door, 0.12)} 50%, ${P.door})`, boxShadow: "inset 0 0 0 10px rgba(0,0,0,0.12)" }} />
            </div>
          </React.Fragment>
        );
      })}
      {/* 엠블럼 */}
      <div style={{ position: "absolute", left: W / 2 - 80, top: 60, width: 160, height: 160, borderRadius: "50%", background: shade(P.curtain, -0.1), boxShadow: `0 0 0 8px ${P.gold}, 0 0 0 12px #9A6A12`, display: "flex", alignItems: "center", justifyContent: "center", textAlign: "center", fontFamily: "NeoHv", fontSize: 40, lineHeight: 1.05, color: "#FFE08A", whiteSpace: "pre-line", paddingTop: 6, boxSizing: "border-box" }}>{emblem}</div>
      {/* 관객 실루엣 — 세모지 그림체 뒷모습 군중(crowd_back_a/b/phone)을 어둡게 눌러 무대 앞 실루엣으로 */}
      {Array.from({ length: 16 }).map((_, i) => {
        const x = 30 + i * 124 + (i % 2) * 20, y = 120 + (i % 3) * 18;
        const id = ["crowd_back_a", "crowd_back_b", "crowd_back_a", "crowd_back_phone", "crowd_back_b"][i % 5];
        const cw = 210 * (id === "crowd_back_phone" ? 0.82 : 1);
        return <Img key={i} src={prop(id)} style={{ position: "absolute", left: x - cw / 2, top: H - 260 + y - 50, width: cw, height: propH(id, cw), filter: "brightness(0.22) saturate(0.4)", transform: i % 2 ? "scaleX(-1)" : undefined }} />;
      })}
    </AbsoluteFill>
  );
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <AbsoluteFill style={{ transform: `translate(${whip * 260}px, ${-whip * 180}px)`, filter: whip > 0.02 ? `blur(${whip * 22}px)` : undefined }}>{stage}</AbsoluteFill>
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 21. 백과사전 책장 시리즈 리캡 [ref4-apple 2:52:07] — 와인색 책장 + 초록 책등 15권(금박 번호) + 느린 드리프트(-20px/s·미세 줌).
//     라벨 = 검정 라운드 pill(흰 굵은 글씨) + 가는 검정 수직 리더선이 책 위→pill 로 5f 드로우, pill 0.3→1.1→1.0 5f 팝,
//     VO 싱크 스태거 ≈1~1.5s, 높이 지그재그.
// ═══════════════════════════════════════════════════════════════════════════
export type ShelfLabel = { text: string; book: number };
export const BookshelfRecapParams = z.object({
  books: num(15, 3, 30, 1, "책 권수", "size"),
  drift: num(-20, -80, 80, 1, "드리프트 속도", "motion", "px/s"),
  zoom: num(0.03, 0, 0.2, 0.005, "드리프트 미세 줌(배)", "motion"),
  firstAt: num(8, 0, 60, 1, "첫 라벨", "timing", "f"),
  stagger: num(30, 3, 90, 1, "라벨 간격", "timing", "f"),
  lineLen: num(5, 1, 20, 1, "리더선 드로우", "timing", "f"),
  popLen: num(5, 1, 20, 1, "pill 팝", "timing", "f"),
  labelSize: num(30, 16, 60, 1, "라벨 글자 크기", "size", "px"),
  wood: col("#8A3040", "책장 목재"),
  back: col("#6E2334", "책장 안쪽"),
  spine: col("#6F6A3A", "책등 색"),
  gold: col("#D9B75A", "금박"),
});
export type BookshelfRecapP = z.infer<typeof BookshelfRecapParams>;
export const BookshelfRecap: React.FC<{ at?: number; labels: ShelfLabel[]; fg?: Node; p?: Partial<BookshelfRecapP> }> = ({ at = 0, labels, fg, p }) => {
  const P = def(BookshelfRecapParams, p);
  const f = useCurrentFrame(), g = f - at;
  const n = Math.round(P.books), bw = 92, gap = 6, bh = 360, bx0 = W / 2 - (n * bw + (n - 1) * gap) / 2 + 40, by = 700 - bh;
  const t = Math.max(0, g) / 30;
  const heights = [120, 210, 70, 180, 100, 240, 140];
  return (
    <AbsoluteFill style={{ background: P.back, overflow: "hidden" }}>
      <AbsoluteFill style={{ transform: `translateX(${P.drift * t}px) scale(${1 + P.zoom * Math.min(1, t / 5)})`, transformOrigin: "50% 60%" }}>
        {/* 선반 */}
        {[140, 700].map((y) => <div key={y} style={{ position: "absolute", left: -200, right: -200, top: y, height: 44, background: `linear-gradient(180deg, ${shade(P.wood, 0.1)}, ${shade(P.wood, -0.2)})` }} />)}
        {[40, W - 80].map((x) => <div key={x} style={{ position: "absolute", left: x, top: 0, bottom: 0, width: 60, background: shade(P.wood, -0.05) }} />)}
        {/* 윗칸 장식 책 — 세모지 그림체 책 묶음(book_spine_set) */}
        {Array.from({ length: 5 }).map((_, i) => <Img key={i} src={prop("book_spine_set")} style={{ position: "absolute", left: 360 + i * 175, top: 140 - propH("book_spine_set", 172), width: 172, height: propH("book_spine_set", 172), transform: i % 2 ? "scaleX(-1)" : undefined }} />)}
        {/* 책등 */}
        {Array.from({ length: n }).map((_, i) => (
          <div key={i} style={{ position: "absolute", left: bx0 + i * (bw + gap), top: by, width: bw, height: bh, overflow: "hidden", isolation: "isolate", borderRadius: "6px 6px 2px 2px" }}>
            {/* 세모지 그림체 책등: book_spine_set 의 키 큰 초록 책 앞면(x 24.5~44.5%, y 5~97%)만 잘라 씀 + spine 색 color 블렌드 */}
            <Img src={prop("book_spine_set")} style={{ position: "absolute", left: -0.245 * (bw / 0.2), top: -0.05 * (bh / 0.92), width: bw / 0.2, height: bh / 0.92 }} />
            <div style={{ position: "absolute", inset: 0, background: P.spine, mixBlendMode: "color", opacity: 0.6 }} />
            <div style={{ position: "absolute", left: 0, right: 0, top: bh * 0.4, textAlign: "center", fontFamily: "NeoHv", fontSize: 34, color: P.gold }}>{i + 1}</div>
          </div>
        ))}
        {/* 라벨 */}
        {labels.map((lb, i) => {
          const t0 = P.firstAt + i * P.stagger;
          if (g < t0) return null;
          const x = bx0 + (lb.book - 1) * (bw + gap) + bw / 2;
          const py = by - heights[i % heights.length];
          const lk = L(g, t0, t0 + P.lineLen, 0, 1, OUT);
          const ps = kfv(g - t0 - P.lineLen, [0, P.popLen * 0.6, P.popLen], [0.3, 1.1, 1]);
          return (
            <React.Fragment key={i}>
              <div style={{ position: "absolute", left: x - 2, top: by + 20 - (by + 20 - py) * lk, width: 4, height: (by + 20 - py) * lk, background: "#111" }} />
              {g >= t0 + P.lineLen && <div style={{ position: "absolute", left: x, top: py, transform: `translate(-50%,-100%) scale(${ps})`, transformOrigin: "50% 100%", background: "#111", color: "#fff", fontFamily: "NeoHv", fontSize: P.labelSize, padding: "10px 22px 4px", borderRadius: 16, whiteSpace: "pre", textAlign: "center", lineHeight: 1.1, boxShadow: "0 0 0 3px rgba(255,255,255,0.8)" }}>{lb.text}</div>}
            </React.Fragment>
          );
        })}
      </AbsoluteFill>
      {fg}
    </AbsoluteFill>
  );
};
const kfv = (g: number, ks: number[], vs: number[]) => (g <= ks[0] ? vs[0] : interpolate(g, ks, vs, { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));

// ═══════════════════════════════════════════════════════════════════════════
// 22. 군중 프레임 크레딧 엔드카드 [ref4-cocacola 32:32 · ref4-hyundai 2:05:36] — 세이지 배경, 좌·우 세로 기둥 군중(미세 까딱),
//     가운데 크림 종이(모서리 꽃장식)에 필기체 제목 + 이름 N열. 수 초 정지.
// ═══════════════════════════════════════════════════════════════════════════
export const CrowdCreditCardParams = z.object({
  leftW: num(0.3, 0, 0.6, 0.01, "왼쪽 군중 폭(화면 비)", "size"),
  rightW: num(0.15, 0, 0.5, 0.01, "오른쪽 군중 폭(화면 비)", "size"),
  personW: num(210, 100, 400, 5, "군중 인물 폭", "size", "px"),
  cardW: num(540, 300, 900, 10, "종이 폭", "size", "px"),
  cardH: num(560, 250, 900, 10, "종이 높이", "size", "px"),
  cols: num(3, 1, 4, 1, "이름 열 수", "size"),
  nameSize: num(26, 16, 60, 1, "이름 글자 크기", "size", "px"),
  bobAmp: num(0.012, 0, 0.05, 0.002, "인물 까딱(배)", "motion"),
  fadeIn: num(8, 0, 30, 1, "등장 페이드", "timing", "f"),
  bg: col("#B0BCAA", "배경 세이지"),
  paper: col("#F4F1E4", "종이 색"),
  flower: col("#F2B8C6", "꽃 색"),
});
export type CrowdCreditCardP = z.infer<typeof CrowdCreditCardParams>;
export const CrowdCreditCard: React.FC<{ at?: number; title?: string; sub?: string; names: string[]; crowd: Cut[]; p?: Partial<CrowdCreditCardP> }> = ({ at = 0, title = "세상의 모든지식", sub = "멤버십 후원자", names, crowd, p }) => {
  const P = def(CrowdCreditCardParams, p);
  const f = useCurrentFrame(), g = f - at;
  const op = P.fadeIn > 0 ? L(g, 0, P.fadeIn, 0, 1) : 1;
  const lw = P.leftW * W, rw = P.rightW * W;
  const cardX = lw + 30, rx0 = cardX + P.cardW + 30;
  const column = (x0: number, wReg: number, off: number) => {
    if (wReg < 40) return null;
    const per = Math.max(1, Math.round(wReg / (P.personW * 0.7)));
    const out: React.ReactNode[] = [];
    let k = 0;
    for (let row = 0; row < 5; row++) {
      for (let c = 0; c < per; c++) {
        const cut = crowd[(k + off) % crowd.length];
        const pw = P.personW * (0.9 + 0.2 * random(`cw${off}-${k}`));
        const x = x0 + (per === 1 ? wReg / 2 : (c + 0.5 + (row % 2) * 0.3) * (wReg / per)) - pw / 2;
        const y = -80 + row * 250 + random(`cy${off}-${k}`) * 40;
        const bob = 1 + P.bobAmp * Math.sin((g + k * 11) / 9);
        out.push(<div key={`${off}-${k}`} style={{ position: "absolute", left: x, top: y, transform: `scaleY(${bob})`, transformOrigin: "50% 100%" }}><CutImg c={cut} w={pw} /></div>);
        k++;
      }
    }
    return <div style={{ position: "absolute", left: 0, top: 0, width: W, height: H, clipPath: `inset(0 ${W - x0 - wReg}px 0 ${Math.max(0, x0 - 20)}px)` }}>{out}</div>;
  };
  const cols = Math.round(P.cols);
  return (
    <AbsoluteFill style={{ background: P.bg, opacity: op }}>
      {column(0, lw, 0)}
      {column(rx0, rw, 3)}
      <div style={{ position: "absolute", left: cardX, top: (H - P.cardH) / 2 - 40, width: P.cardW, height: P.cardH, background: P.paper, borderRadius: 12, boxShadow: "0 8px 18px rgba(0,0,0,0.18)" }}>
        {/* 세모지 그림체 꽃(blossom_corner) 모서리 장식 */}
        {([[P.cardW - 5, 15, 115, 10], [P.cardW - 70, -20, 72, 40], [15, P.cardH - 15, 100, -20], [85, P.cardH + 10, 66, 0]] as const).map(([bx, by, d, r], i) => <KitImg key={i} id="blossom_corner" x={bx} y={by} w={d} rot={r} />)}
        <div style={{ position: "absolute", left: 0, right: 0, top: 40, textAlign: "center", fontFamily: "Yeonsung, serif", fontSize: 48, color: "#9A8A55" }}>{title}</div>
        <div style={{ position: "absolute", left: 0, right: 0, top: 104, textAlign: "center", fontFamily: "NeoEb", fontSize: 20, color: "#B09A70" }}>{sub}</div>
        <div style={{ position: "absolute", left: 40, right: 40, top: 150, display: "grid", gridTemplateColumns: `repeat(${cols}, 1fr)`, rowGap: 12, columnGap: 14 }}>
          {names.map((nm, i) => <div key={i} style={{ fontFamily: "NeoHv", fontSize: P.nameSize, color: "#1E1E1E", whiteSpace: "nowrap", overflow: "hidden" }}>{nm}</div>)}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 23. 어깨너머 검정 실루엣 전경 [ref4-hyundai 42:17] — 청자를 우측 전경 검정 뒷모습(#111, 화면 높이 ~80%, 우측 1/3)으로 크게,
//     화자는 좌측 소형(≈1:1.8). 회색 원형 스포트 비네트 배경. 정적, 말풍선만 팝.
// ═══════════════════════════════════════════════════════════════════════════
export const OTSSilhouetteParams = z.object({
  silH: num(0.8, 0.4, 1.3, 0.01, "실루엣 높이(화면 비)", "size"),
  silX: num(0.72, 0.4, 0.95, 0.01, "실루엣 중심 X(화면 비)", "size"),
  ratio: num(1.8, 1, 3, 0.05, "실루엣:화자 크기비", "size"),
  speakerX: num(0.3, 0.05, 0.6, 0.01, "화자 중심 X(화면 비)", "size"),
  bubbleAt: num(10, 0, 120, 1, "말풍선 팝", "timing", "f"),
  silColor: col("#111111", "실루엣 색"),
  bg: col("#5E5E5E", "배경"),
  spot: col("#8C8C8C", "스포트 색"),
});
export type OTSSilhouetteP = z.infer<typeof OTSSilhouetteParams>;
export const OTSSilhouette: React.FC<{ at?: number; speaker: Cut; listener: Cut; bubble?: Node; p?: Partial<OTSSilhouetteP> }> = ({ at = 0, speaker, listener, bubble, p }) => {
  const P = def(OTSSilhouetteParams, p);
  const f = useCurrentFrame(), g = f - at;
  const lh = H * P.silH * 1.25, lw = lh / cutAR(listener);
  const sh = (H * P.silH) / P.ratio * 1.25, sw = sh / cutAR(speaker);
  return (
    <AbsoluteFill style={{ background: `radial-gradient(circle at 38% 52%, ${P.spot} 0 30%, ${shade(P.spot, -0.12)} 30% 45%, ${P.bg} 45%)` }}>
      <div style={{ position: "absolute", left: P.speakerX * W - sw / 2, top: H * 0.2 }}><CutImg c={speaker} w={sw} /></div>
      <div style={{ position: "absolute", left: P.silX * W - lw / 2, top: H * (1 - P.silH) }}><CutImg c={listener} w={lw} color={P.silColor} /></div>
      {g >= P.bubbleAt && bubble}
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// 24. '잠깐!!' 내레이터 실루엣 끼어들기 [ref4-samsung 1:32:40·1:35:20] — 배경 블러 12f → 노란 12각 스파이크(#F5C242 ≈620px)
//     '잠깐!!' 팝 5f → 0.8s 홀드 → 회전하며 페이드 6f → 채널 마스코트 실루엣(#2E2E33) 아래→위 18f(quart-out),
//     머리에 '세모지' 세로쓰기·가슴 '구독♥좋아요', 땀방울·'머쓱;;', 좌상단 작은 스티커 말풍선.
// ═══════════════════════════════════════════════════════════════════════════
export const NarratorInterruptParams = z.object({
  blur: num(14, 0, 40, 1, "배경 블러", "look", "px"),
  blurLen: num(12, 1, 40, 1, "배경 블러 시간", "timing", "f"),
  burstD: num(620, 200, 1000, 10, "스파이크 지름", "size", "px"),
  spikes: num(12, 6, 24, 1, "스파이크 각 수", "size"),
  popLen: num(5, 1, 20, 1, "'잠깐' 팝", "timing", "f"),
  burstHold: num(24, 0, 90, 1, "'잠깐' 홀드", "timing", "f"),
  burstOut: num(6, 1, 20, 1, "회전 페이드", "timing", "f"),
  slideLen: num(18, 3, 60, 1, "실루엣 올라오기", "timing", "f"),
  silW: num(660, 200, 900, 10, "실루엣 폭", "size", "px"),
  burst: col("#F5C242", "스파이크 색"),
  silColor: col("#2E2E33", "실루엣 색"),
});
export type NarratorInterruptP = z.infer<typeof NarratorInterruptParams>;
export const NarratorInterrupt: React.FC<{ at?: number; backdrop: Node; mascot: Cut; head?: [number, number]; text?: string; name?: string; chest?: string; aside?: string; sticker?: Node; p?: Partial<NarratorInterruptP> }> = ({ at = 0, backdrop, mascot, head = [0.38, 0.2], text = "잠깐!!", name = "세모지", chest = "구독♥좋아요", aside = "머쓱;;", sticker, p }) => {
  const P = def(NarratorInterruptParams, p);
  const f = useCurrentFrame(), g = f - at;
  const b = L(g, 0, P.blurLen, 0, P.blur, OUT);
  const t0 = Math.round(P.blurLen * 0.4), t1 = t0 + P.popLen + P.burstHold, t2 = t1 + P.burstOut;
  const bs = kfv(g - t0, [0, P.popLen * 0.6, P.popLen], [0.2, 1.12, 1]);
  const bOut = L(g, t1, t2, 1, 0);
  const bRot = L(g, t1, t2, -6, 40, Easing.in(Easing.quad));
  const N = Math.round(P.spikes) * 2;
  const pts = Array.from({ length: N }).map((_, i) => { const a = (i / N) * Math.PI * 2; const r = i % 2 ? 0.7 : 1; return `${(Math.cos(a) * r * 50).toFixed(2)},${(Math.sin(a) * r * 44).toFixed(2)}`; }).join(" ");
  const s0 = t2 - 2;
  const sw = P.silW, shh = sw * cutAR(mascot);
  const sy = L(g, s0, s0 + P.slideLen, H + 20, H - shh * 0.78, QUART_OUT);
  const after = g >= s0 + P.slideLen;
  const hx = W * 0.68 - sw / 2 + head[0] * sw, hy = sy + head[1] * shh;
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <AbsoluteFill style={{ filter: b > 0.3 ? `blur(${b}px)` : undefined, transform: `scale(${1 + b * 0.002})` }}>{backdrop}</AbsoluteFill>
      {g >= t0 && g < t2 && (
        <div style={{ position: "absolute", left: W / 2 - P.burstD / 2 - 120, top: H * 0.42 - P.burstD * 0.44, width: P.burstD, height: P.burstD * 0.88, opacity: bOut, transform: `scale(${bs}) rotate(${bRot}deg)` }}>
          <svg viewBox="-50 -44 100 88" width="100%" height="100%" style={{ position: "absolute" }}><polygon points={pts} fill={P.burst} /></svg>
          <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "Jua", fontSize: P.burstD * 0.18, color: "#1B1B1B", transform: "rotate(-6deg)" }}>{text}</div>
        </div>
      )}
      {g >= s0 && (
        <>
          <div style={{ position: "absolute", left: W * 0.68 - sw / 2, top: sy }}><CutImg c={mascot} w={sw} color={P.silColor} /></div>
          <div style={{ position: "absolute", left: hx - 30, top: hy - 70, width: 60, writingMode: "vertical-rl", fontFamily: "Yeonsung, serif", fontSize: 50, color: "#6E6E78", textAlign: "center" }}>{name}</div>
          <div style={{ position: "absolute", left: W * 0.68 - 140, top: sy + shh * 0.62, width: 280, textAlign: "center", fontFamily: "NeoEb", fontSize: 34, color: "#55555E" }}>{chest}</div>
          {after && <SweatDrop x={hx - 170} y={hy - 70} at={at + s0 + P.slideLen} s={1.3} />}
          {after && <div style={{ position: "absolute", left: hx - 330, top: hy + 40, fontFamily: "Jua", fontSize: 50, color: "#2A2A2A", opacity: L(g, s0 + P.slideLen + 4, s0 + P.slideLen + 8, 0, 1) }}>{aside}</div>}
          {after && sticker && <div style={{ position: "absolute", left: 30, top: 130, transform: `scale(${L(g, s0 + P.slideLen + 6, s0 + P.slideLen + 11, 0.3, 1, Easing.out(Easing.back(2)))})`, transformOrigin: "0 0" }}>{sticker}</div>}
        </>
      )}
    </AbsoluteFill>
  );
};
