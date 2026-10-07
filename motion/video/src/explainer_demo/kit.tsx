// 설명형 편집 레퍼런스(ref_explainer_editorial) 오마주 — 공용 소형 컴포넌트(자막·양피지·소품 팝·산포·말풍선·도장·딤·캐리커처·찢긴 사진·대형 단어)
// 모든 수치 기본값 = analysis.md 실측(24f 원본 → 30f 환산).
import React from "react";
import { AbsoluteFill, Easing, Img, useCurrentFrame } from "remotion";
import { z } from "zod";
import { num, col, flag, def } from "../params/p";
import { PAL, FPS, lin, BACK_OUT, EXPO_OUT, rnd } from "./theme";

// ── 1. 자막: 글자폭 흰 박스 · h57 · 하단 100px · 검정 2px · 하드섀도(-5,+5) · 하드 교체 ─────────────
export type PSub = { t0: number; t1: number; text: string };
export const PirSubtitlesParams = z.object({
  fontSize: num(37, 24, 60, 1, "글자 크기", "size", "px"),
  boxH: num(57, 30, 100, 1, "박스 높이", "size", "px"),
  bottom: num(100, 0, 300, 1, "화면 하단에서 박스 하단까지", "size", "px"),
  padX: num(16, 0, 60, 1, "좌우 여백", "size", "px"),
  border: num(2, 0, 8, 0.5, "테두리 두께", "size", "px"),
  shadowX: num(-5, -20, 20, 1, "하드섀도 X", "look", "px"),
  shadowY: num(5, -20, 20, 1, "하드섀도 Y", "look", "px"),
  firstFade: num(6, 0, 30, 1, "영상 첫 자막 페이드", "timing", "f"),
  boxColor: col("#FFFFFF", "박스 색"),
  textColor: col("#000000", "글자 색"),
});
export type PirSubtitlesP = z.infer<typeof PirSubtitlesParams>;
export const PirSubtitles: React.FC<{ subs: PSub[]; p?: Partial<PirSubtitlesP> }> = ({ subs, p }) => {
  const P = def(PirSubtitlesParams, p);
  const f = useCurrentFrame();
  const t = f / FPS;
  const i = subs.findIndex((s) => t >= s.t0 && t < s.t1);
  if (i < 0) return null;
  const cur = subs[i];
  const op = i === 0 ? lin(f, cur.t0 * FPS, cur.t0 * FPS + P.firstFade, 0, 1) : 1;
  return (
    <div style={{ position: "absolute", left: 0, right: 0, bottom: P.bottom, display: "flex", justifyContent: "center", opacity: op }}>
      <div style={{
        height: P.boxH, boxSizing: "border-box", padding: `0 ${P.padX}px`, background: P.boxColor, border: `${P.border}px solid #000`,
        boxShadow: `${P.shadowX}px ${P.shadowY}px 0 #000`, display: "flex", alignItems: "center",
        fontFamily: "NeoEb", fontSize: P.fontSize, color: P.textColor, whiteSpace: "nowrap", letterSpacing: -0.3, lineHeight: 1,
      }}>{cur.text}</div>
    </div>
  );
};

// ── 2. 양피지 바탕: #F2DFCA + 얼룩(저주파 노이즈) + 가장자리 번짐 + 정적 종이 그레인 ─────────────────
export const ParchmentParams = z.object({
  base: col(PAL.parchment, "바탕색"),
  stainOp: num(0.35, 0, 1, 0.01, "얼룩 세기", "look"),
  stainFreq: num(0.004, 0.001, 0.03, 0.001, "얼룩 크기(작을수록 큼)", "size"),
  grainOp: num(0.18, 0, 1, 0.01, "종이 결 세기", "look"),
  vignette: num(0.22, 0, 1, 0.01, "가장자리 번짐", "look"),
  seed: num(5, 0, 99, 1, "무늬 시드", "look"),
});
export type ParchmentP = z.infer<typeof ParchmentParams>;
export const Parchment: React.FC<{ p?: Partial<ParchmentP> }> = ({ p }) => {
  const P = def(ParchmentParams, p);
  const id = `parch${P.seed}`;
  return (
    <AbsoluteFill style={{ background: P.base }}>
      <svg width="100%" height="100%" style={{ position: "absolute", mixBlendMode: "multiply", opacity: P.stainOp }}>
        <filter id={`${id}s`}><feTurbulence type="fractalNoise" baseFrequency={P.stainFreq} numOctaves={4} seed={P.seed} />
          <feColorMatrix values="0 0 0 0 0.86  0 0 0 0 0.74  0 0 0 0 0.6  0 0 0 -1.6 1.25" /></filter>
        <rect width="100%" height="100%" filter={`url(#${id}s)`} />
      </svg>
      <svg width="100%" height="100%" style={{ position: "absolute", mixBlendMode: "multiply", opacity: P.grainOp }}>
        <filter id={`${id}g`}><feTurbulence type="fractalNoise" baseFrequency="0.75" numOctaves={2} seed={P.seed + 3} />
          <feColorMatrix values="0 0 0 0 0.55  0 0 0 0 0.45  0 0 0 0 0.35  0 0 0 -2.4 1.6" /></filter>
        <rect width="100%" height="100%" filter={`url(#${id}g)`} />
      </svg>
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 48%, transparent 58%, rgba(120,80,40,${P.vignette}) 100%)` }} />
    </AbsoluteFill>
  );
};

// ── 3. 좌우 소품 팝: 0.6→1.0 · 6f back-out (흰 스티커 테두리는 에셋 자체) ────────────────────────────
export const SidePropPopParams = z.object({
  len: num(6, 1, 30, 1, "팝 길이", "timing", "f"),
  from: num(0.6, 0, 1, 0.05, "시작 크기(배)", "motion"),
  shadow: num(0.25, 0, 1, 0.05, "그림자 불투명도", "look"),
  bob: num(0, 0, 20, 1, "둥실 진폭", "motion", "px"),
});
export type SidePropPopP = z.infer<typeof SidePropPopParams>;
export const SidePropPop: React.FC<{ src: string; x: number; y: number; w: number; at: number; out?: number; rot?: number; p?: Partial<SidePropPopP> }> = ({ src, x, y, w, at, out, rot = 0, p }) => {
  const P = def(SidePropPopParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const s = lin(f, at, at + P.len, P.from, 1, BACK_OUT);
  const o = out !== undefined ? lin(f, out, out + 4, 1, 0) : 1;
  const by = P.bob ? Math.sin((f - at) / 18) * P.bob : 0;
  return (
    <Img src={src} style={{ position: "absolute", left: x - w / 2, top: y + by, width: w, transform: `translateY(-50%) rotate(${rot}deg) scale(${s * (0.6 + 0.4 * o)})`, opacity: o,
      filter: `drop-shadow(0 6px 8px rgba(40,20,10,${P.shadow}))` }} />
  );
};

// ── 4. 아이콘 산포: 15~20개 · 1f 스태거 · 개당 4f back-out ─────────────────────────────────────────
export const IconScatterParams = z.object({
  stagger: num(1.25, 0, 10, 0.25, "개당 등장 간격", "timing", "f"),
  popLen: num(5, 1, 20, 1, "개당 팝 길이", "timing", "f"),
  size: num(78, 20, 240, 1, "아이콘 크기", "size", "px"),
  sizeJitter: num(0.25, 0, 1, 0.05, "크기 흔들림", "size"),
  rotJitter: num(18, 0, 90, 1, "회전 흔들림", "motion", "°"),
});
export type IconScatterP = z.infer<typeof IconScatterParams>;
export const IconScatter: React.FC<{ src: string; pts: { x: number; y: number }[]; at: number; seed?: string; out?: number; p?: Partial<IconScatterP> }> = ({ src, pts, at, seed = "sc", out, p }) => {
  const P = def(IconScatterParams, p);
  const f = useCurrentFrame();
  const o = out !== undefined ? lin(f, out, out + 6, 1, 0) : 1;
  return (
    <>
      {pts.map((pt, i) => {
        const t0 = at + i * P.stagger;
        if (f < t0) return null;
        const s = lin(f, t0, t0 + P.popLen, 0, 1, BACK_OUT);
        const sz = P.size * (1 + (rnd(seed, i) - 0.5) * 2 * P.sizeJitter);
        const r = (rnd(seed, i + 99) - 0.5) * 2 * P.rotJitter;
        return <Img key={i} src={src} style={{ position: "absolute", left: pt.x - sz / 2, top: pt.y - sz / 2, width: sz, height: sz, objectFit: "contain", opacity: o,
          transform: `rotate(${r}deg) scale(${s})`, filter: "drop-shadow(0 3px 3px rgba(30,15,5,0.35))" }} />;
      })}
    </>
  );
};

// ── 5. 와이프 말풍선: 좌→우 폭 와이프 12f ease-out · 퇴장 3f 축소·페이드 · 흰 둥근 사각 검정 3px · 헤비 고딕 45px ──
export const WipeBubbleParams = z.object({
  wipeLen: num(12, 1, 40, 1, "와이프 길이", "timing", "f"),
  outLen: num(3, 1, 20, 1, "퇴장 길이", "timing", "f"),
  fontSize: num(45, 20, 90, 1, "글자 크기", "size", "px"),
  border: num(4, 0, 10, 0.5, "외곽선 두께", "size", "px"),
  radius: num(26, 0, 60, 1, "모서리 둥글기", "size", "px"),
  padX: num(30, 0, 80, 1, "좌우 여백", "size", "px"),
  padY: num(16, 0, 60, 1, "상하 여백", "size", "px"),
  tailLen: num(46, 0, 120, 1, "꼬리 길이", "size", "px"),
  fill: col("#FFFFFF", "말풍선 색"),
});
export type WipeBubbleP = z.infer<typeof WipeBubbleParams>;
export const WipeBubble: React.FC<{ text: string; x: number; y: number; at: number; out?: number; tail?: "left" | "right" | "none"; p?: Partial<WipeBubbleP> }> = ({ text, x, y, at, out, tail = "left", p }) => {
  const P = def(WipeBubbleParams, p);
  const f = useCurrentFrame();
  if (f < at || (out !== undefined && f > out + P.outLen)) return null;
  const k = lin(f, at, at + P.wipeLen, 0, 1, Easing.out(Easing.cubic));
  const ko = out !== undefined ? lin(f, out, out + P.outLen, 1, 0) : 1;
  const tailX = tail === "left" ? "24%" : "76%";
  return (
    <div style={{ position: "absolute", left: x, top: y, transform: `translate(-50%,-100%) scale(${0.85 + 0.15 * ko})`, opacity: ko, transformOrigin: `${tailX} 100%` }}>
      <div style={{ clipPath: `inset(-20px ${(1 - k) * 100}% -${P.tailLen + 20}px -20px)` }}>
        <div style={{ position: "relative", background: P.fill, border: `${P.border}px solid #000`, borderRadius: P.radius, padding: `${P.padY}px ${P.padX}px`,
          fontFamily: "Jalnan", fontSize: P.fontSize, color: "#111", whiteSpace: "nowrap", lineHeight: 1.15, boxShadow: "0 3px 0 rgba(0,0,0,0.12)" }}>
          {text}
          {tail !== "none" && (
            <svg width={P.tailLen} height={P.tailLen + 4} style={{ position: "absolute", left: `calc(${tailX} - ${P.tailLen / 2}px)`, top: `calc(100% - ${P.border + 1}px)`, overflow: "visible" }}>
              <path d={tail === "left" ? `M${P.tailLen * 0.15} 0 Q${P.tailLen * 0.35} ${P.tailLen * 0.6} ${P.tailLen * 0.05} ${P.tailLen} Q${P.tailLen * 0.7} ${P.tailLen * 0.6} ${P.tailLen * 0.75} 0`
                : `M${P.tailLen * 0.85} 0 Q${P.tailLen * 0.65} ${P.tailLen * 0.6} ${P.tailLen * 0.95} ${P.tailLen} Q${P.tailLen * 0.3} ${P.tailLen * 0.6} ${P.tailLen * 0.25} 0`}
                fill={P.fill} stroke="#000" strokeWidth={P.border} strokeLinejoin="round" />
              <rect x={P.tailLen * 0.12} y={-P.border - 2} width={P.tailLen * 0.76} height={P.border + 2} fill={P.fill} />
            </svg>
          )}
        </div>
      </div>
    </div>
  );
};

// ── 6. 도장: 1.6→1.0 5f expo-out · -8° 유지 · 착지 후 1f 튐 · #C80000 이중 테두리 거친 잉크 ──────────────
export const PirStampParams = z.object({
  slamLen: num(5, 1, 20, 1, "내리꽂기 길이", "timing", "f"),
  from: num(1.6, 1, 4, 0.05, "시작 크기(배)", "motion"),
  bump: num(0.04, 0, 0.2, 0.01, "착지 튐", "motion"),
  rot: num(-8, -45, 45, 1, "기울기", "motion", "°"),
  size: num(120, 30, 260, 1, "글자 크기", "size", "px"),
  rough: num(5, 0, 20, 0.5, "잉크 거칠기", "look", "px"),
  inkOp: num(0.92, 0, 1, 0.01, "잉크 불투명도", "look"),
  color: col(PAL.red, "도장 색"),
});
export type PirStampP = z.infer<typeof PirStampParams>;
export const PirStamp: React.FC<{ lines: string[]; x: number; y: number; at: number; out?: number; p?: Partial<PirStampP> }> = ({ lines, x, y, at, out, p }) => {
  const P = def(PirStampParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const s = lin(f, at, at + P.slamLen, P.from, 1, EXPO_OUT);
  const bump = f === at + P.slamLen + 1 ? 1 + P.bump : 1;
  const o = (out !== undefined ? lin(f, out, out + 4, 1, 0) : 1) * lin(f, at, at + 2, 0, 1);
  const fid = `stampR${Math.round(x)}${Math.round(y)}`;
  const c = P.color, sz = P.size;
  return (
    <div style={{ position: "absolute", left: x, top: y, transform: `translate(-50%,-50%) rotate(${P.rot}deg) scale(${s * bump})`, opacity: o * P.inkOp, filter: `url(#${fid}) drop-shadow(0 0 1px rgba(0,0,0,0.2))` }}>
      <svg width={0} height={0} style={{ position: "absolute" }}>
        <filter id={fid} x="-10%" y="-10%" width="120%" height="120%">
          <feTurbulence type="fractalNoise" baseFrequency="0.045" numOctaves={2} seed={4} result="n" />
          <feDisplacementMap in="SourceGraphic" in2="n" scale={P.rough} xChannelSelector="R" yChannelSelector="G" result="d" />
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={1} seed={8} result="sp" />
          <feColorMatrix in="sp" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -3 2.1" result="holes" />
          <feComposite in="d" in2="holes" operator="in" />
        </filter>
      </svg>
      <div style={{ border: `${sz * 0.075}px solid ${c}`, padding: sz * 0.06, background: "transparent" }}>
        <div style={{ border: `${sz * 0.035}px solid ${c}`, padding: `${sz * 0.1}px ${sz * 0.22}px ${sz * 0.06}px`, textAlign: "center" }}>
          {lines.map((l, i) => (
            <div key={i} style={{ fontFamily: "Jalnan", fontSize: i === 0 ? sz : sz * 0.52, color: c, lineHeight: 1.12, whiteSpace: "nowrap" }}>{l}</div>
          ))}
        </div>
      </div>
    </div>
  );
};

// ── 7. 포커스 딤 컷어웨이: 밝기 45% · 블러 6px · 6f ease-out, 해제 10f ────────────────────────────────
export const FocusDimParams = z.object({
  inLen: num(6, 1, 30, 1, "딤 들어가는 길이", "timing", "f"),
  outLen: num(10, 1, 30, 1, "딤 해제 길이", "timing", "f"),
  bright: num(0.45, 0, 1, 0.01, "배경 밝기", "look"),
  blur: num(6, 0, 30, 0.5, "배경 블러", "look", "px"),
});
export type FocusDimP = z.infer<typeof FocusDimParams>;
export const FocusDim: React.FC<{ at: number; out?: number; bg: React.ReactNode; children?: React.ReactNode; p?: Partial<FocusDimP> }> = ({ at, out, bg, children, p }) => {
  const P = def(FocusDimParams, p);
  const f = useCurrentFrame();
  let k = lin(f, at, at + P.inLen, 0, 1, Easing.out(Easing.cubic));
  if (out !== undefined) k *= lin(f, out, out + P.outLen, 1, 0);
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ filter: k > 0.001 ? `brightness(${1 - (1 - P.bright) * k}) blur(${P.blur * k}px)` : undefined }}>{bg}</AbsoluteFill>
      {children}
    </AbsoluteFill>
  );
};

// ── 8. 캐리커처 슬라이드인 + 이름표(흰 볼드 검정 외곽선) ────────────────────────────────────────────
export const CaricatureSlideParams = z.object({
  len: num(11, 1, 40, 1, "슬라이드 길이", "timing", "f"),
  dist: num(700, 0, 1600, 10, "들어오는 거리", "motion", "px"),
  nameSize: num(64, 20, 140, 1, "이름표 크기", "size", "px"),
  nameStroke: num(10, 0, 30, 1, "이름표 외곽선", "size", "px"),
  nameDelay: num(8, 0, 40, 1, "이름표 지연", "timing", "f"),
});
export type CaricatureSlideP = z.infer<typeof CaricatureSlideParams>;
export const CaricatureSlide: React.FC<{ src: string; side: "left" | "right"; at: number; w: number; name?: string; nameY?: number; x?: number; p?: Partial<CaricatureSlideP> }> = ({ src, side, at, w, name, nameY = 820, x, p }) => {
  const P = def(CaricatureSlideParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const d = lin(f, at, at + P.len, P.dist, 0, EXPO_OUT) * (side === "left" ? -1 : 1);
  const X = x ?? (side === "left" ? 40 : 1920 - 40 - w);
  const nk = lin(f, at + P.nameDelay, at + P.nameDelay + 5, 0, 1, BACK_OUT);
  return (
    <>
      <Img src={src} style={{ position: "absolute", left: X + d, bottom: 0, width: w, filter: "drop-shadow(0 0 0 #000)" }} />
      {name && f >= at + P.nameDelay && (
        <div style={{ position: "absolute", left: X + w * (side === "left" ? 0.08 : 0.35), top: nameY, transform: `scale(${nk})`, transformOrigin: "0 50%",
          fontFamily: "Jalnan", fontSize: P.nameSize, color: "#fff", WebkitTextStroke: `${P.nameStroke}px #000`, paintOrder: "stroke fill", whiteSpace: "nowrap" }}>{name}</div>
      )}
    </>
  );
};

// ── 9. 찢긴 종이 테두리 사진 + 켄번스 1~2%/s (음식은 원색 유지) ──────────────────────────────────────
export const TornPhotoParams = z.object({
  kenBurns: num(0.015, 0, 0.1, 0.001, "켄번스 확대 속도(초당)", "motion"),
  edge: num(22, 0, 60, 1, "찢김 테두리 폭", "size", "px"),
  rough: num(14, 0, 40, 1, "찢김 거칠기", "look", "px"),
  sepia: num(0, 0, 1, 0.05, "세피아", "look"),
  enterLen: num(15, 1, 40, 1, "등장 디졸브", "timing", "f"),
  rot: num(-1.5, -15, 15, 0.5, "기울기", "motion", "°"),
});
export type TornPhotoP = z.infer<typeof TornPhotoParams>;
export const TornPhoto: React.FC<{ src: string; x: number; y: number; w: number; h: number; at: number; pos?: string; p?: Partial<TornPhotoP> }> = ({ src, x, y, w, h, at, pos = "50% 50%", p }) => {
  const P = def(TornPhotoParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const t = (f - at) / FPS;
  const fid = `torn${Math.round(x)}`;
  return (
    <div style={{ position: "absolute", left: x - w / 2, top: y - h / 2, width: w, height: h, opacity: lin(f, at, at + P.enterLen, 0, 1), transform: `rotate(${P.rot}deg)` }}>
      <svg width={0} height={0} style={{ position: "absolute" }}>
        <filter id={fid} x="-5%" y="-5%" width="110%" height="110%">
          <feTurbulence type="fractalNoise" baseFrequency="0.06" numOctaves={3} seed={9} result="n" />
          <feDisplacementMap in="SourceGraphic" in2="n" scale={P.rough} xChannelSelector="R" yChannelSelector="G" />
        </filter>
      </svg>
      {/* 흰 종이 가장자리(찢긴 면) */}
      <div style={{ position: "absolute", inset: -P.edge, background: "#F7F0E4", filter: `url(#${fid}) drop-shadow(-4px 6px 6px rgba(40,20,10,0.35))` }} />
      <div style={{ position: "absolute", inset: 0, overflow: "hidden", filter: `url(#${fid})` }}>
        <Img src={src} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: pos, transform: `scale(${1 + P.kenBurns * t})`, filter: P.sepia ? `sepia(${P.sepia})` : undefined }} />
      </div>
    </div>
  );
};

// ── 10. 양피지 대형 단어: 검정 헤비 고딕 100px · 소프트 그림자 · 글자 타자 1.5f/자 ────────────────────
export const BigWordParams = z.object({
  size: num(100, 40, 220, 1, "글자 크기", "size", "px"),
  perChar: num(1.5, 0, 6, 0.25, "글자당 타자 간격", "timing", "f"),
  shadow: num(0.35, 0, 1, 0.05, "소프트 그림자", "look"),
  color: col("#111111", "글자 색"),
  accent: col(PAL.red, "강조 색"),
});
export type BigWordP = z.infer<typeof BigWordParams>;
/** lines: "[강조]" 대괄호로 감싼 부분은 강조색 */
export const BigWord: React.FC<{ lines: string[]; x?: number; y: number; at: number; out?: number; p?: Partial<BigWordP> }> = ({ lines, x = 960, y, at, out, p }) => {
  const P = def(BigWordParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const o = out !== undefined ? lin(f, out, out + 6, 1, 0) : 1;
  let n = Math.floor((f - at) / Math.max(0.001, P.perChar)) + 1;
  return (
    <div style={{ position: "absolute", left: x, top: y, transform: "translate(-50%,-50%)", textAlign: "center", opacity: o,
      fontFamily: "NeoHv", fontSize: P.size, lineHeight: 1.18, color: P.color, textShadow: `0 6px 14px rgba(60,30,10,${P.shadow})`, whiteSpace: "nowrap" }}>
      {lines.map((l, li) => {
        const parts = l.split(/(\[[^\]]+\])/);
        return (
          <div key={li}>
            {parts.map((pt, pi) => {
              const acc = pt.startsWith("[");
              const txt = acc ? pt.slice(1, -1) : pt;
              return [...txt].map((ch, ci) => {
                n -= 1;
                return <span key={`${pi}-${ci}`} style={{ color: acc ? P.accent : undefined, visibility: n >= 0 ? "visible" : "hidden" }}>{ch}</span>;
              });
            })}
          </div>
        );
      })}
    </div>
  );
};

// ── 11. 딤 오버레이(차트 밑): #787068 α0.85 · 15f ───────────────────────────────────────────────────
export const DimUnderlayParams = z.object({
  len: num(15, 1, 40, 1, "딤 인 길이", "timing", "f"),
  color: col(PAL.chartDim, "딤 색"),
  alpha: num(0.85, 0, 1, 0.01, "딤 불투명도", "look"),
  multiply: flag(true, "곱하기 합성", "look"),
});
export type DimUnderlayP = z.infer<typeof DimUnderlayParams>;
export const DimUnderlay: React.FC<{ at: number; p?: Partial<DimUnderlayP> }> = ({ at, p }) => {
  const P = def(DimUnderlayParams, p);
  const f = useCurrentFrame();
  return <AbsoluteFill style={{ background: P.color, opacity: P.alpha * lin(f, at, at + P.len, 0, 1), mixBlendMode: P.multiply ? "multiply" : undefined }} />;
};
