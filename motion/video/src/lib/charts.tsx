// 세모지 인포그래픽 차트 모션 — 레퍼런스 프레임 실측 스펙 기반 컴포넌트 모음.
// 모든 컴포넌트: `at`(시작 프레임) + 결정적 props. 난수는 remotion random(seed)만 사용.
// 금지: 방사형 광선/선버스트 줄무늬 배경 → 부드러운 radial glow·링으로 대체.
import React from "react";
import { AbsoluteFill, Easing, Img, random, useCurrentFrame } from "remotion";
import { z } from "zod";
import { W, H, lerp, kf, photoPop, textPop, src, popSpring, hz } from "../fx";
import { num, col, flag, choice, def } from "../params/p";
import { prop, propH, CAST, CastId } from "./kit";
import { SemojiRig, RigPose } from "./semoji_rig";

// ── 공통 ────────────────────────────────────────────────────────────────
type P = [number, number];
const TAU = Math.PI * 2;
const SHADOW = "drop-shadow(0 10px 16px rgba(0,0,0,0.28))";
const E_PIE = Easing.bezier(0.3, 0, 0.2, 1);
const E_BAR = Easing.bezier(0.35, 0, 0.25, 1);
const E_INOUT = Easing.inOut(Easing.cubic);
const E_OUT = Easing.out(Easing.cubic);
/** back-out(오버슈트) — 막대 끝 아이콘 팝 */
const E_BACK = Easing.bezier(0.34, 1.56, 0.64, 1);
/** 이징 선택지: auto = 원래 구현값 */
const EASES = { snappy: E_PIE, bar: E_BAR, inout: E_INOUT, out: E_OUT, linear: Easing.linear } as const;
const EASE_OPTS = ["auto", "snappy", "bar", "inout", "out", "linear"] as const;
const pickEase = (k: string, auto: (t: number) => number) => (k === "auto" ? auto : EASES[k as keyof typeof EASES] ?? auto);
/** undefined 인 개별 prop 은 빼고 넘긴다(스키마 기본값 유지) */
const dfn = (o: Record<string, unknown>) => Object.fromEntries(Object.entries(o).filter(([, v]) => v !== undefined));
/** 길이(프레임) 0 방어 */
const d1 = (v: number) => Math.max(1, v);

/** 폴리라인 길이/점 샘플링 (화살촉이 머리를 따라가게) */
const segLens = (pts: P[]) => pts.slice(1).map((p, i) => Math.hypot(p[0] - pts[i][0], p[1] - pts[i][1]));
const pointAt = (pts: P[], t: number) => {
  const ls = segLens(pts);
  const total = ls.reduce((a, b) => a + b, 0);
  let d = Math.max(0, Math.min(1, t)) * total;
  for (let i = 0; i < ls.length; i++) {
    if (d <= ls[i] || i === ls.length - 1) {
      const k = ls[i] === 0 ? 0 : Math.min(1, d / ls[i]);
      const [a, b] = [pts[i], pts[i + 1]];
      return { x: a[0] + (b[0] - a[0]) * k, y: a[1] + (b[1] - a[1]) * k, ang: Math.atan2(b[1] - a[1], b[0] - a[0]) };
    }
    d -= ls[i];
  }
  return { x: pts[0][0], y: pts[0][1], ang: 0 };
};
const polyD = (pts: P[]) => pts.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");

/** 부드러운 radial glow 배경 (광선 금지) */
export const GlowBg: React.FC<{ color: string; glow?: string; cx?: string; cy?: string }> = ({ color, glow = "rgba(255,255,255,0.22)", cx = "50%", cy = "45%" }) => (
  <AbsoluteFill style={{ background: `radial-gradient(circle at ${cx} ${cy}, ${glow} 0%, rgba(255,255,255,0) 55%), ${color}` }} />
);

/** 이전 장면 딤 언더레이 */
export const DimUnderlay: React.FC<{ img: string; dim: number; blur?: number }> = ({ img, dim, blur = 0 }) => (
  <AbsoluteFill>
    <Img src={src(img)} style={{ width: "100%", height: "100%", objectFit: "cover", filter: blur ? `blur(${blur}px)` : undefined }} />
    <AbsoluteFill style={{ background: `rgba(0,0,0,${dim})` }} />
  </AbsoluteFill>
);

// ── 세모지 키트 소품(PNG) 헬퍼 ─────────────────────────────────────────────
const MASK = (u: string): React.CSSProperties => ({ WebkitMaskImage: `url(${u})`, maskImage: `url(${u})`, WebkitMaskSize: "100% 100%", maskSize: "100% 100%", WebkitMaskRepeat: "no-repeat", maskRepeat: "no-repeat" } as React.CSSProperties);
/** 키트 소품 PNG(public/kit/props/<id>.png) */
export const KitImg: React.FC<{ id: string; w: number; h?: number; style?: React.CSSProperties }> = ({ id, w, h, style }) => (
  <Img src={prop(id)} style={{ display: "block", width: w, height: h ?? propH(id, w), ...style }} />
);
/** 회색 아이콘 PNG 를 단색 틴트(mask-image + background-color). 숨은 Img 로 로딩 대기 */
export const KitTint: React.FC<{ id: string; w: number; h?: number; color: string; style?: React.CSSProperties }> = ({ id, w, h, color, style }) => (
  <div style={{ position: "relative", width: w, height: h ?? propH(id, w), ...style }}>
    <Img src={prop(id)} style={{ position: "absolute", left: 0, top: 0, width: 1, height: 1, opacity: 0 }} />
    <div style={{ position: "absolute", inset: 0, backgroundColor: color, ...MASK(prop(id)) }} />
  </div>
);
/** 밝은(회색·흰) 소품 PNG 에 색을 곱해 명암을 살린 틴트. lift: 곱하기 전 밝기 보정(회색 #D9 → 흰색 ≈ 1.18) */
export const KitMul: React.FC<{ id: string; w: number; h?: number; color: string; lift?: number; style?: React.CSSProperties }> = ({ id, w, h, color, lift = 1, style }) => {
  const hh = h ?? propH(id, w);
  return (
    <div style={{ position: "relative", width: w, height: hh, isolation: "isolate", ...style }}>
      <Img src={prop(id)} style={{ position: "absolute", left: 0, top: 0, width: w, height: hh, filter: lift !== 1 ? `brightness(${lift})` : undefined }} />
      <div style={{ position: "absolute", inset: 0, backgroundColor: color, mixBlendMode: "multiply", ...MASK(prop(id)) }} />
    </div>
  );
};

// ── 세모지 캐릭터(사람은 전부 SemojiRig 캐스트로) ─────────────────────────────────
export const CAST_IDS: CastId[] = ["walker1", "c2_boss", "c3_woman", "c4_elder", "c5_chef"];
/** seed 로 캐스트 한 명 고르기(결정적) */
export const castOf = (seed: string): CastId => CAST_IDS[Math.floor(random(seed) * CAST_IDS.length) % CAST_IDS.length];
/** 캔버스 px → 화면 px 배율 s 로, 머리 꼭대기가 (x, headTop) 에 오게 SemojiRig 배치(전신 — 아래는 부모가 자르거나 화면 밖) */
export const CastAtHead: React.FC<{ cast: CastId; x: number; headTop: number; s: number; flip?: boolean; seed?: string; pose?: RigPose; at?: number; p?: Record<string, number> }> = ({ cast, x, headTop, s, flip, seed, pose, at, p }) => {
  const R = CAST[cast], h = (R.feet[1] - R.top) * s;
  return <SemojiRig cast={cast} x={x} y={headTop + h} h={h} flip={flip} seed={seed ?? cast} pose={pose} at={at} p={p} />;
};
/** 박스(w×h) 안 전신 세모지 캐릭터 — 발 = 박스 아래 가운데, 키 = h */
export const CastFig: React.FC<{ cast: CastId; h: number; w?: number; walking?: boolean; flip?: boolean; seed?: string; at?: number; pose?: RigPose; style?: React.CSSProperties; p?: Record<string, number> }> = ({ cast, h, w, walking, flip, seed, at, pose, style, p }) => {
  const bw = w ?? h * 0.42;
  return (
    <div style={{ position: "relative", width: bw, height: h, ...style }}>
      <SemojiRig cast={cast} x={bw / 2} y={h} h={h} walking={walking} flip={flip} seed={seed ?? cast} at={at} pose={pose} p={p} />
    </div>
  );
};

/** 둥근 로고 캐릭터: 세모지 원판 마스코트(xc_logo_disc: 흰 링 + 발) 안쪽을 bg 색으로 곱하기 틴트 + 눈(xc_logo_eyes) + 로고 글자(코드).
 *  d = 원판 지름. 박스 d × 1.08d (발 포함), 원판 중심 (0.5d, 0.5d) */
const LG = { w: 966, h: 1068, cy: 482, r: 482, rin: 414 }; // xc_logo_disc 실측(px)
export const LogoChar: React.FC<{ d: number; bg: string; text: string; fg?: string; ring?: string }> = ({ d, bg, text, fg = "#fff", ring = "#fff" }) => {
  const k = d / LG.w, cy = LG.cy * k, rin = LG.rin * k;
  const white = /^#f{3}(f{3})?$/i.test(ring);
  return (
    <div style={{ position: "relative", width: d, height: d * 1.08, filter: "drop-shadow(0 6px 8px rgba(0,0,0,0.22))" }}>
      <div style={{ position: "absolute", left: 0, top: 0, width: d, height: LG.h * k, isolation: "isolate" }}>
        <Img src={prop("xc_logo_disc")} style={{ position: "absolute", left: 0, top: 0, width: d, height: LG.h * k }} />
        {!white && <div style={{ position: "absolute", left: 0, top: cy - d / 2, width: d, height: d, borderRadius: "50%", mixBlendMode: "multiply", background: `radial-gradient(circle closest-side, transparent ${rin - 1}px, ${ring} ${rin}px)` }} />}
        <div style={{ position: "absolute", left: d / 2 - rin, top: cy - rin, width: rin * 2, height: rin * 2, borderRadius: "50%", background: bg, mixBlendMode: "multiply" }} />
      </div>
      <Img src={prop("xc_logo_eyes")} style={{ position: "absolute", left: 0, top: -d * 0.13, width: d, height: LG.h * k }} />
      <div style={{ position: "absolute", left: 0, top: d * 0.42, width: d, textAlign: "center", fontFamily: "NeoHv", fontSize: d * (text.length > 2 ? 0.2 : 0.3), color: fg, lineHeight: 1.1 }}>{text}</div>
    </div>
  );
};

/** 검정 리본 배너(접힌 꼬리). drop: 위에서 떨어지는 프레임 수. typing: 음절당 2f 타이핑 */
export const RibbonParams = z.object({
  drop: num(8, 0, 40, 1, "떨어지는 시간", "timing", "f"),
  dropPad: num(60, 0, 600, 10, "낙하 시작 높이 여백", "motion", "px"),
  typeRate: num(2, 1, 8, 1, "타이핑 음절당 프레임", "timing", "f"),
  h: num(96, 40, 200, 2, "리본 높이", "size", "px"),
  size: num(54, 20, 120, 1, "글자 크기", "size", "px"),
  color: col("#1b1b1b", "리본 색"),
  tail: col("#333", "꼬리 색"),
  fold: col("#000", "접힘 그림자 색"),
  fg: col("#fff", "글자 색"),
});
export type RibbonP = z.infer<typeof RibbonParams>;
export const Ribbon: React.FC<{ text: string; x: number; y: number; at: number; h?: number; w?: number; size?: number; color?: string; tail?: string; fold?: string; fg?: string; drop?: number; typing?: boolean; p?: Partial<RibbonP> }> = ({ text, x, y, at, h: h0, w, size: size0, color: color0, tail: tail0, fold: fold0, fg: fg0, drop: drop0, typing = false, p }) => {
  const P = def(RibbonParams, { ...dfn({ h: h0, size: size0, color: color0, tail: tail0, fold: fold0, fg: fg0, drop: drop0 }), ...p });
  const { h, size, color, tail, fold, fg, drop } = P;
  const f = useCurrentFrame();
  if (f < at) return null;
  const bw = w ?? Math.max(360, [...text].length * size * 0.98 + 120);
  const tw = h * 0.75, d = h * 0.3;
  const dy = drop > 0 ? lerp(f, at, at + drop, -(y + h + P.dropPad), 0, E_OUT) : 0;
  const chars = [...text];
  const shown = typing ? chars.slice(0, Math.min(chars.length, Math.floor((f - at - drop) / d1(P.typeRate)) + 1)).join("") : text;
  const L = tw, R = tw + bw;
  const tailL = `0,${d} ${tw * 1.6},${d} ${tw * 1.6},${d + h} 0,${d + h} ${tw * 0.42},${d + h / 2}`;
  const tailR = `${R + tw},${d} ${R - tw * 0.6},${d} ${R - tw * 0.6},${d + h} ${R + tw},${d + h} ${R + tw - tw * 0.42},${d + h / 2}`;
  return (
    <div style={{ position: "absolute", left: x - bw / 2 - tw, top: y + dy, width: bw + 2 * tw, height: h + d, filter: SHADOW }}>
      <svg width={bw + 2 * tw} height={h + d} style={{ position: "absolute" }}>
        <polygon points={tailL} fill={tail} />
        <polygon points={tailR} fill={tail} />
        <polygon points={`${L},${h} ${L + tw * 0.6},${h} ${L + tw * 0.6},${h + d}`} fill={fold} />
        <polygon points={`${R},${h} ${R - tw * 0.6},${h} ${R - tw * 0.6},${h + d}`} fill={fold} />
        <rect x={L} y={0} width={bw} height={h} fill={color} />
      </svg>
      <div style={{ position: "absolute", left: L, top: 0, width: bw, height: h, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "NeoHv", fontSize: size, color: fg, whiteSpace: "nowrap" }}>
        <span style={{ visibility: "hidden", position: "absolute" }}>{text}</span>
        <span style={{ width: bw - 40, textAlign: "center" }}>{shown}</span>
      </div>
    </div>
  );
};

/** 손그림 빨간 원 스트로크 드로잉 */
export const HandCircleParams = z.object({
  dur: num(10, 1, 60, 1, "그리는 시간", "timing", "f"),
  sweep: num(1.12, 0.2, 2, 0.02, "감는 바퀴 수", "motion", "바퀴"),
  startAng: num(-111.6, -180, 180, 0.1, "시작 각도", "motion", "°"),
  wobble: num(0.035, 0, 0.2, 0.005, "손떨림 세기", "motion"),
  flare: num(0.05, 0, 0.3, 0.01, "끝 벌어짐", "motion"),
  sw: num(9, 1, 40, 1, "선 두께", "size", "px"),
  color: col("#E3261E", "선 색"),
});
export type HandCircleP = z.infer<typeof HandCircleParams>;
export const HandCircle: React.FC<{ cx: number; cy: number; rx: number; ry: number; at: number; dur?: number; color?: string; sw?: number; seed?: string; p?: Partial<HandCircleP> }> = ({ cx, cy, rx, ry, at, dur: dur0, color: color0, sw: sw0, seed = "hc", p: pp }) => {
  const P = def(HandCircleParams, { ...dfn({ dur: dur0, color: color0, sw: sw0 }), ...pp });
  const { dur, color, sw } = P;
  const f = useCurrentFrame();
  if (f < at) return null;
  const pts: P[] = [];
  const N = 80, a0 = (P.startAng * Math.PI) / 180, sweep = TAU * P.sweep;
  const ph = random(seed) * TAU;
  for (let i = 0; i <= N; i++) {
    const t = i / N, a = a0 + sweep * t;
    const wob = 1 + P.wobble * Math.sin(3 * a + ph) + P.flare * t; // 끝으로 갈수록 바깥으로 벌어짐(손그림)
    pts.push([cx + rx * wob * Math.cos(a), cy + ry * wob * Math.sin(a)]);
  }
  const p = lerp(f, at, at + d1(dur), 0, 1, Easing.inOut(Easing.quad));
  return (
    <svg width={W} height={H} style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}>
      <path d={polyD(pts)} pathLength={1} fill="none" stroke={color} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" strokeDasharray="1 1" strokeDashoffset={1 - p} />
    </svg>
  );
};

// ── 1. PieSweep ─────────────────────────────────────────────────────────
const wedgeD = (c: number, r: number, a0: number, a1: number) => {
  const s = a1 - a0;
  if (s <= 0.0005) return "";
  if (s >= 0.9995) return `M${c},${c - r} A${r},${r} 0 1 1 ${c},${c + r} A${r},${r} 0 1 1 ${c},${c - r} Z`;
  const pt = (a: number) => `${c + r * Math.sin(a * TAU)},${c - r * Math.cos(a * TAU)}`;
  return `M${c},${c} L${pt(a0)} A${r},${r} 0 ${s > 0.5 ? 1 : 0} 1 ${pt(a1)} Z`;
};

/** 기본 지구본 오브젝트 (globe→pie 변형용) — 세모지 지구본(xc_globe_sphere: globe 의 구만 원형 크롭 + 키잉으로 빠진 대륙 초록 메움) */
export const Globe: React.FC<{ d: number }> = ({ d }) => (
  <Img src={prop("xc_globe_sphere")} style={{ display: "block", width: d, height: d }} />
);

export type PieSecond = { pct: number; color: string; delay?: number; label?: string; labelColor?: string };
export const PieSweepParams = z.object({
  sweepDur: num(24, 1, 120, 1, "쐐기 스윕 길이 (long 모드 기본 48)", "timing", "f"),
  ease: choice("auto", EASE_OPTS, "스윕 이징 (auto=원래값)", "motion"),
  fadeIn: num(8, 1, 30, 1, "원 페이드인 길이", "timing", "f"),
  globeHold: num(6, 0, 30, 1, "지구본 팝 후 스윕까지 정지", "timing", "f"),
  globeOvershoot: num(1.1, 1, 1.6, 0.01, "지구본 팝 오버슈트(배)", "motion", "배"),
  secondDur: num(24, 1, 90, 1, "두번째 쐐기 스윕 길이", "timing", "f"),
  iconDelay: num(6, 0, 30, 1, "스윕 끝→아이콘 등장 지연", "timing", "f"),
  iconOvershoot: num(1.15, 1, 1.6, 0.01, "아이콘 오버슈트(배)", "motion", "배"),
  labelFade: num(8, 1, 30, 1, "라벨 페이드 길이", "timing", "f"),
  r: num(300, 80, 540, 5, "원 반지름", "size", "px"),
  base: col("#32322F", "원 바탕 색"),
  wedge: col("#F0F000", "쐐기 색"),
});
export type PieSweepP = z.infer<typeof PieSweepParams>;
export const PieSweep: React.FC<{
  at: number; x: number; y: number; r?: number; pct: number;
  base?: string; wedge?: string; long?: boolean; fadeBase?: boolean;
  second?: PieSecond; icon?: React.ReactNode; iconSize?: number; label?: string; labelColor?: string;
  globe?: React.ReactNode | true; wedgeText?: string; wedgeTextColor?: string;
  sticker?: { img: string; side?: "left" | "right"; delay?: number; w?: number };
  p?: Partial<PieSweepP>;
}> = ({ at, x, y, r: r0, pct, base: base0, wedge: wedge0, long = false, fadeBase = false, second, icon, iconSize = 150, label, labelColor = "#1b1b1b", globe, wedgeText, wedgeTextColor = "#1b1b1b", sticker, p: pp }) => {
  const P = def(PieSweepParams, { ...(long ? { sweepDur: 48 } : {}), ...dfn({ r: r0, base: base0, wedge: wedge0 }), ...pp });
  const { r, base, wedge } = P;
  const f = useCurrentFrame();
  if (f < at) return null;
  const pad = 30, S = 2 * (r + pad), c = r + pad;
  // 시작 타이밍: 원 페이드 8f / 지구본 팝 5f + 홀드 6f
  const sweepAt = at + (globe ? 5 + P.globeHold : fadeBase ? P.fadeIn : 0);
  const dur = d1(P.sweepDur);
  const p = lerp(f, sweepAt, sweepAt + dur, 0, pct, pickEase(P.ease, long ? E_INOUT : E_PIE));
  const endAt = sweepAt + dur;
  const baseOp = fadeBase ? lerp(f, at, at + d1(P.fadeIn), 0, 1, Easing.linear) : 1;
  const gS = globe ? kf(f, at, [0, 3, 5], [0.3, P.globeOvershoot, 1.0], E_OUT) : 1;
  // 두번째 쐐기
  const s2At = endAt + (second?.delay ?? 20);
  const d2 = d1(P.secondDur);
  const p2 = second ? lerp(f, s2At, s2At + d2, 0, second.pct, pickEase(P.ease, E_PIE)) : 0;
  const clipId = `pw-${at}-${x}-${y}`;
  // 아이콘/라벨 위치: 쐐기 중앙 각
  const mid = (pct / 2) * TAU;
  const ix = c + r * 0.55 * Math.sin(mid), iy = c - r * 0.55 * Math.cos(mid);
  const iconAt = endAt + P.iconDelay;
  const iS = kf(f, iconAt, [0, 4, 7], [0, P.iconOvershoot, 1.0], E_OUT);
  const lblAt = icon ? iconAt + 7 : iconAt;
  const lf = d1(P.labelFade);
  const lblOp = lerp(f, lblAt, lblAt + lf, 0, 1, Easing.linear);
  const mid2 = (pct + (second?.pct ?? 0) / 2) * TAU;
  const lbl2Op = second ? lerp(f, s2At + d2 + 6, s2At + d2 + 6 + lf, 0, 1, Easing.linear) : 0;
  const st = sticker ? photoPop(f, endAt + (sticker.delay ?? 14)) : null;
  const stW = sticker?.w ?? r * 1.25;
  return (
    <div style={{ position: "absolute", left: x - c, top: y - c, width: S, height: S }}>
      <div style={{ position: "absolute", inset: 0, filter: SHADOW }}>
        {globe ? (
          <div style={{ position: "absolute", left: pad, top: pad, width: 2 * r, height: 2 * r, transform: `scale(${gS})` }}>
            {globe === true ? <Globe d={2 * r} /> : globe}
          </div>
        ) : (
          <svg width={S} height={S} style={{ position: "absolute", opacity: baseOp }}><circle cx={c} cy={c} r={r} fill={base} /></svg>
        )}
        <svg width={S} height={S} style={{ position: "absolute" }}>
          <defs><clipPath id={clipId}><path d={wedgeD(c, r + 1, 0, p)} /></clipPath></defs>
          <g clipPath={`url(#${clipId})`}>
            <circle cx={c} cy={c} r={r + 1} fill={wedge} />
            {wedgeText && (
              <text x={ix} y={iy + r * 0.1} textAnchor="middle" fontFamily="NeoHv" fontSize={r * 0.34} fill={wedgeTextColor}>{wedgeText}</text>
            )}
          </g>
          {second && <path d={wedgeD(c, r + 1, pct, pct + p2)} fill={second.color} />}
        </svg>
      </div>
      {icon && f >= iconAt && (
        <div style={{ position: "absolute", left: ix - iconSize / 2, top: iy - iconSize / 2 - (label ? r * 0.1 : 0), width: iconSize, height: iconSize, transform: `scale(${iS})`, display: "flex", alignItems: "center", justifyContent: "center", filter: "drop-shadow(0 6px 8px rgba(0,0,0,0.3))" }}>{icon}</div>
      )}
      {label && (
        <div style={{ position: "absolute", left: ix - 150, top: iy + (icon ? iconSize * 0.42 : -r * 0.14) - (label ? r * 0.1 : 0), width: 300, textAlign: "center", fontFamily: "NeoHv", fontSize: r * 0.2, color: labelColor, opacity: lblOp }}>{label}</div>
      )}
      {second?.label && (
        <div style={{ position: "absolute", left: c + r * 0.62 * Math.sin(mid2) - 150, top: c - r * 0.62 * Math.cos(mid2) - r * 0.12, width: 300, textAlign: "center", fontFamily: "NeoHv", fontSize: r * 0.17, color: second.labelColor ?? "#fff", opacity: lbl2Op }}>{second.label}</div>
      )}
      {sticker && st && f >= endAt + (sticker.delay ?? 14) && (
        <Img src={src(sticker.img)} style={{ position: "absolute", width: stW, left: sticker.side === "left" ? c - r - stW * 0.25 : c + r - stW * 0.75, top: c - stW * 0.3, transform: `scale(${st.s}) rotate(${sticker.side === "left" ? -6 : 6}deg)`, filter: `blur(${st.blur}px) drop-shadow(0 0 5px #fff) drop-shadow(0 0 5px #fff) drop-shadow(0 12px 14px rgba(0,0,0,0.3))` }} />
      )}
    </div>
  );
};

// ── 2. BarChartH ────────────────────────────────────────────────────────
export type HRow = { label: string; value: number };
export const BarChartHParams = z.object({
  rowDelay: num(14, 0, 60, 1, "첫 행 등장 지연", "timing", "f"),
  rowStagger: num(4, 0, 20, 1, "행 스태거 간격", "timing", "f"),
  barDelay: num(3, 0, 20, 1, "라벨 팝→막대 시작 지연", "timing", "f"),
  barDur: num(21, 1, 90, 1, "막대 자라는 시간", "timing", "f"),
  ease: choice("auto", EASE_OPTS, "막대 이징 (auto=원래값)", "motion"),
  popOvershoot: num(1.12, 1, 1.6, 0.01, "라벨 알약 오버슈트(배)", "motion", "배"),
  circleDelay: num(30, 0, 120, 1, "손그림 원 등장 지연", "timing", "f"),
  circleDur: num(11, 1, 60, 1, "손그림 원 그리는 시간", "timing", "f"),
  pitch: num(94, 50, 160, 1, "행 간격", "size", "px"),
  barH: num(50, 10, 90, 1, "막대 두께", "size", "px"),
  pillW: num(320, 160, 360, 5, "라벨 알약 폭", "size", "px"),
  bar: col("#BDBBB7", "막대 색"),
  winBar: col("#94BD29", "1위 막대 색"),
  bg: col("#F9F7F1", "배경 색"),
  iconPop: num(4, 1, 20, 1, "막대 끝 아이콘 팝 길이(icons 있을 때)", "timing", "f"),
  iconSize: num(84, 20, 200, 1, "막대 끝 아이콘 크기", "size", "px"),
});
export type BarChartHP = z.infer<typeof BarChartHParams>;
export const BarChartH: React.FC<{
  at: number; title: string; subtitle?: string; rows: HRow[]; winner: number; max: number;
  ticks?: number[]; unit?: string; top?: number; pitch?: number; barX?: number; barMaxW?: number; circleDelay?: number;
  /** 행별 막대 끝 아이콘(세모지 소품 id → kit prop()) — 막대가 다 자란 순간 back-out 팝 */
  icons?: (string | undefined)[];
  p?: Partial<BarChartHP>;
}> = ({ at, title, subtitle, rows, winner, max, ticks, unit = "", top = 290, pitch: pitch0, barX = 520, barMaxW = 1220, circleDelay: circleDelay0, icons, p: pp }) => {
  const P = def(BarChartHParams, { ...dfn({ pitch: pitch0, circleDelay: circleDelay0 }), ...pp });
  const { pitch, circleDelay, barH, pillW } = P;
  const f = useCurrentFrame();
  const tks = ticks ?? [0, max * 0.25, max * 0.5, max * 0.75, max];
  const pillX = 150, pillH = 68;
  const rowsAt = at + P.rowDelay;
  const barEnd = P.barDelay + d1(P.barDur);
  const gridTop = top - 60, gridBot = top + (rows.length - 1) * pitch + 70;
  const lastEnd = rowsAt + (rows.length - 1) * P.rowStagger + barEnd;
  const subOp = lerp(f, at + 8, at + 13, 0, 1, Easing.linear);
  const gridOp = lerp(f, at, at + 8, 0, 1, Easing.linear);
  return (
    <AbsoluteFill style={{ background: P.bg }}>
      {/* 격자 종이 */}
      <svg width={W} height={H} style={{ position: "absolute", opacity: gridOp }}>
        {Array.from({ length: 49 }, (_, i) => (
          <line key={i} x1={i * 40} x2={i * 40} y1={0} y2={H} stroke="rgba(0,0,0,0.045)" strokeWidth={2} />
        ))}
        {tks.map((t, i) => {
          const gx = barX + (t / max) * barMaxW;
          return (
            <g key={`t${i}`}>
              <line x1={gx} x2={gx} y1={gridTop} y2={gridBot} stroke="rgba(0,0,0,0.13)" strokeWidth={3} strokeDasharray={i ? "10 8" : undefined} />
              <text x={gx} y={gridBot + 44} textAnchor="middle" fontFamily="NeoEb" fontSize={30} fill="#8a877f">{Math.round(t).toLocaleString()}{unit}</text>
            </g>
          );
        })}
        <line x1={barX} x2={barX} y1={gridTop} y2={gridBot} stroke="#55524b" strokeWidth={5} />
      </svg>
      <Ribbon text={title} x={W / 2} y={40} at={at} drop={8} size={54} h={100} />
      {subtitle && (
        <div style={{ position: "absolute", top: 162, width: W, textAlign: "center", fontFamily: "NeoEb", fontSize: 34, color: "#6b675e", opacity: subOp }}>{subtitle}</div>
      )}
      {rows.map((r, i) => {
        const ra = rowsAt + i * P.rowStagger;
        if (f < ra) return null;
        const cy = top + i * pitch;
        const win = i === winner;
        const ps = kf(f, ra, [0, 3, 6], [0.3, P.popOvershoot, 1.0], E_OUT);
        const bw = lerp(f, ra + P.barDelay, ra + barEnd, 0, (r.value / max) * barMaxW, pickEase(P.ease, E_BAR));
        const vOp = lerp(f, ra + barEnd - 8, ra + barEnd, 0, 1, Easing.linear);
        return (
          <React.Fragment key={i}>
            <div style={{ position: "absolute", left: pillX, top: cy - pillH / 2, width: pillW, height: pillH, borderRadius: pillH / 2, background: win ? "#73AF03" : "#8F8D88", color: "#fff", fontFamily: "NeoHv", fontSize: 36, display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${ps})`, boxShadow: "0 5px 8px rgba(0,0,0,0.18)" }}>{r.label}</div>
            <div style={{ position: "absolute", left: barX, top: cy - barH / 2, width: bw, height: barH, borderRadius: "0 12px 12px 0", background: win ? P.winBar : P.bar, boxShadow: "0 4px 6px rgba(0,0,0,0.12)" }} />
            <div style={{ position: "absolute", left: barX + bw + 18 + (icons?.[i] ? P.iconSize + 6 : 0), top: cy - 26, fontFamily: "NeoHv", fontSize: 44, color: win ? "#5E8F00" : "#77746d", opacity: vOp, whiteSpace: "nowrap" }}>{r.value.toLocaleString()}{unit}</div>
            {icons?.[i] && f >= ra + barEnd && (
              <Img src={prop(icons[i]!)} style={{ position: "absolute", left: barX + bw + 8, top: cy - P.iconSize / 2, width: P.iconSize, height: P.iconSize, objectFit: "contain", transformOrigin: "20% 50%", transform: `scale(${lerp(f, ra + barEnd, ra + barEnd + P.iconPop, 0, 1, E_BACK)})`, filter: "drop-shadow(0 4px 5px rgba(0,0,0,0.2))" }} />
            )}
          </React.Fragment>
        );
      })}
      <HandCircle cx={pillX + pillW / 2} cy={top + winner * pitch} rx={pillW / 2 + 42} ry={pillH / 2 + 26} at={lastEnd + circleDelay} dur={P.circleDur} />
    </AbsoluteFill>
  );
};

// ── 3. BarChartV ────────────────────────────────────────────────────────
export type VBar = { label: string; value: number; hi?: boolean };
export type VGroup = { x: number; caption?: string; bars: VBar[]; delay?: number };
export const BarChartVParams = z.object({
  ribbonDrop: num(9, 0, 40, 1, "제목 리본 낙하 시간", "timing", "f"),
  groupDelay: num(12, 0, 60, 1, "첫 그룹 등장 지연", "timing", "f"),
  groupStagger: num(45, 0, 150, 1, "그룹 간 간격", "timing", "f"),
  growDur: num(15, 1, 60, 1, "막대 자라는 시간", "timing", "f"),
  ease: choice("auto", EASE_OPTS, "막대 이징 (auto=원래값)", "motion"),
  mascotOvershoot: num(1.15, 1, 1.6, 0.01, "마스코트 팝 오버슈트(배)", "motion", "배"),
  maxH: num(420, 100, 700, 10, "최대 막대 높이", "size", "px"),
  barW: num(130, 30, 260, 2, "막대 폭", "size", "px"),
  gap: num(44, 0, 150, 2, "막대 간격", "size", "px"),
  hiColor: col("#FB0000", "강조 막대 색"),
  color: col("#555", "막대 색"),
  textColor: col("#1b1b1b", "글자·기준선 색"),
  staggerF: num(0, 0, 20, 1, "그룹 안 막대 스태거(0=동시, 기존)", "timing", "f"),
  iconPop: num(4, 1, 20, 1, "막대 끝 아이콘 팝 길이(icons 있을 때)", "timing", "f"),
  iconSize: num(110, 20, 260, 1, "막대 끝 아이콘 크기", "size", "px"),
});
export type BarChartVP = z.infer<typeof BarChartVParams>;
export const BarChartV: React.FC<{
  at: number; title: string; groups: VGroup[]; baseY?: number; max: number; maxH?: number; barW?: number; gap?: number;
  hiColor?: string; color?: string; mascot?: React.ReactNode; mascotSize?: number; unit?: string; textColor?: string;
  /** 막대별 끝 아이콘(그룹 순서대로 이어 센 막대 인덱스, 세모지 소품 id → kit prop()) — 막대가 다 자란 순간 back-out 팝 */
  icons?: (string | undefined)[];
  p?: Partial<BarChartVP>;
}> = ({ at, title, groups, baseY = 860, max, maxH: maxH0, barW: barW0, gap: gap0, hiColor: hi0, color: color0, mascot, mascotSize = 150, unit = "", textColor: tc0, icons, p: pp }) => {
  const P = def(BarChartVParams, { ...dfn({ maxH: maxH0, barW: barW0, gap: gap0, hiColor: hi0, color: color0, textColor: tc0 }), ...pp });
  const { maxH, barW, gap, hiColor, color, textColor } = P;
  const f = useCurrentFrame();
  if (f < at) return null;
  const gd = d1(P.growDur);
  return (
    <AbsoluteFill>
      <Ribbon text={title} x={W / 2} y={60} at={at} drop={P.ribbonDrop} />
      {groups.map((g, gi) => {
        const ga = at + P.groupDelay + (g.delay ?? gi * P.groupStagger);
        if (f < ga) return null;
        const n = g.bars.length, totalW = n * barW + (n - 1) * gap;
        const x0 = g.x - totalW / 2;
        const gOp = lerp(f, ga, ga + 4, 0, 1, Easing.linear);
        return (
          <React.Fragment key={gi}>
            <div style={{ position: "absolute", left: x0 - 30, top: baseY, width: totalW + 60, height: 8, borderRadius: 4, background: textColor, opacity: gOp }} />
            {g.bars.map((b, i) => {
              const bs = ga + i * P.staggerF;
              const bh = lerp(f, bs, bs + gd, 0, (b.value / max) * maxH, pickEase(P.ease, E_OUT));
              const bx = x0 + i * (barW + gap);
              const vOp = lerp(f, bs + gd - 4, bs + gd + 2, 0, 1, Easing.linear);
              const ms = kf(f, bs + gd, [0, 4, 7], [0, P.mascotOvershoot, 1.0], E_OUT);
              const icon = icons?.[groups.slice(0, gi).reduce((a, q) => a + q.bars.length, 0) + i];
              const iconUp = icon ? P.iconSize * 0.96 : 0;
              return (
                <React.Fragment key={i}>
                  <div style={{ position: "absolute", left: bx, top: baseY - bh, width: barW, height: bh, background: b.hi ? hiColor : color, borderRadius: "10px 10px 0 0" }} />
                  {icon && f >= bs + gd && (
                    <Img src={prop(icon)} style={{ position: "absolute", left: bx + barW / 2 - P.iconSize / 2, top: baseY - bh - P.iconSize, width: P.iconSize, height: P.iconSize, objectFit: "contain", objectPosition: "50% 100%", transformOrigin: "50% 100%", transform: `scale(${lerp(f, bs + gd, bs + gd + P.iconPop, 0, 1, E_BACK)})`, filter: "drop-shadow(0 4px 5px rgba(0,0,0,0.2))" }} />
                  )}
                  <div style={{ position: "absolute", left: bx - 40, top: baseY - bh - 64 - (b.hi && mascot ? mascotSize * 0.98 : 0) - iconUp, width: barW + 80, textAlign: "center", fontFamily: "NeoHv", fontSize: 46, color: b.hi ? hiColor : textColor, opacity: vOp }}>{b.value.toLocaleString()}{unit}</div>
                  <div style={{ position: "absolute", left: bx - 40, top: baseY + 20, width: barW + 80, textAlign: "center", fontFamily: "NeoEb", fontSize: 32, color: textColor, opacity: gOp }}>{b.label}</div>
                  {b.hi && mascot && f >= bs + gd && (
                    <div style={{ position: "absolute", left: bx + barW / 2 - mascotSize / 2, top: baseY - bh - mascotSize, width: mascotSize, height: mascotSize, transform: `scale(${ms})`, transformOrigin: "50% 100%", display: "flex", alignItems: "flex-end", justifyContent: "center" }}>{mascot}</div>
                  )}
                </React.Fragment>
              );
            })}
            {g.caption && (
              <div style={{ position: "absolute", left: g.x - 300, top: baseY + 70, width: 600, textAlign: "center", fontFamily: "Jua", fontSize: 44, color: textColor, opacity: gOp }}>{g.caption}</div>
            )}
          </React.Fragment>
        );
      })}
    </AbsoluteFill>
  );
};

// ── 4. LineChart ────────────────────────────────────────────────────────
export type LPill = { idx: number; text: string; delay: number; color?: string };
/** 군중 줄(세모지 캐스트 상반신): 아래에서 솟아오른 뒤 둥실. color·alt 는 호환용(캐릭터는 제 옷색) */
export const CrowdRowParams = z.object({
  rise: num(11, 1, 60, 1, "솟아오르는 시간", "timing", "f"),
  riseDist: num(260, 0, 600, 10, "솟아오르는 거리", "motion", "px"),
  bobAmp: num(6, 0, 40, 1, "둥실 흔들림 폭", "motion", "px"),
  bobPeriod: num(9, 1, 40, 1, "둥실 주기(느림)", "timing", "f"),
  n: num(15, 1, 40, 1, "사람 수", "size"),
  color: col("#F08A24", "실루엣 색"),
  alt: col("#F6A445", "실루엣 보조 색"),
});
export type CrowdRowP = z.infer<typeof CrowdRowParams>;
export const CrowdRow: React.FC<{ at: number; color?: string; alt?: string; y?: number; n?: number; rise?: number; p?: Partial<CrowdRowP> }> = ({ at, color: color0, alt: alt0, y = H, n: n0, rise: rise0, p: pp }) => {
  const P = def(CrowdRowParams, { ...dfn({ color: color0, alt: alt0, n: n0, rise: rise0 }), ...pp });
  const { color, alt } = P;
  const n = Math.max(1, Math.round(P.n)), rise = d1(P.rise);
  const f = useCurrentFrame();
  if (f < at) return null;
  const up = lerp(f, at, at + rise, P.riseDist, 0, E_OUT);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {Array.from({ length: n }, (_, i) => {
        const sz = 0.8 + 0.35 * random(`cr-s${i}`);
        const px = (i + 0.5) * (W / n) + (random(`cr-x${i}`) - 0.5) * 40;
        const bob = f > at + rise ? Math.sin((f - at - rise) / d1(P.bobPeriod) + random(`cr-p${i}`) * TAU) * P.bobAmp : 0;
        const head = 70 * sz;
        const top = y - 170 * sz + up + bob + (i % 2 ? 26 : 0);
        // 세모지 캐스트(머리 폭 ≈ 250 캔버스 px 가 head×1.35 가 되게) — 몸은 화면 아래로 잘림. 캐스트·반전은 seed 로 변주
        return <CastAtHead key={i} cast={castOf(`cr-c${i}`)} x={px} headTop={top} s={(head * 1.35) / 250} flip={random(`cr-f${i}`) < 0.5} seed={`cr${i}`} />;
      })}
    </AbsoluteFill>
  );
};

export const LineChartParams = z.object({
  axisV: num(14, 1, 60, 1, "세로축 그리는 시간", "timing", "f"),
  axisH: num(14, 1, 60, 1, "가로축 그리는 시간", "timing", "f"),
  axisFade: num(6, 1, 30, 1, "축 페이드 길이 (fade 모드)", "timing", "f"),
  labelStagger: num(2, 0, 12, 1, "연도 라벨 스태거", "timing", "f"),
  dotDelay: num(4, 0, 30, 1, "축 완성→첫 점 지연", "timing", "f"),
  lineDelay: num(10, 0, 40, 1, "첫 점→선 드로잉 지연", "timing", "f"),
  lineDur: num(22, 1, 90, 1, "선 그리는 시간", "timing", "f"),
  ease: choice("auto", EASE_OPTS, "선 이징 (auto=원래값)", "motion"),
  dotOvershoot: num(1.2, 1, 1.8, 0.01, "점 팝 오버슈트(배)", "motion", "배"),
  pillOvershoot: num(1.12, 1, 1.6, 0.01, "말풍선 오버슈트(배)", "motion", "배"),
  axisW: num(17, 2, 40, 1, "축 두께 (fade 모드 기본 24)", "size", "px"),
  lineW: num(11, 2, 30, 1, "선 두께", "size", "px"),
  lineColor: col("#E69131", "선 색"),
  dim: num(0.65, 0, 1, 0.05, "배경 사진 어둡게", "look"),
});
export type LineChartP = z.infer<typeof LineChartParams>;
export const LineChart: React.FC<{
  at: number; years: string[]; values: number[]; min: number; max: number;
  underlay?: string; axis?: "draw" | "fade"; dot?: "big" | "small"; lineColor?: string; lineW?: number;
  pills?: LPill[]; stamp?: { text: string; x: number; y: number; delay: number; color?: string };
  crowd?: { delay: number }; box?: [number, number, number, number]; title?: string;
  p?: Partial<LineChartP>;
}> = ({ at, years, values, min, max, underlay, axis = "draw", dot = "big", lineColor: lc0, lineW: lw0, pills = [], stamp, crowd, box = [260, 200, 1680, 820], title, p: pp }) => {
  const P = def(LineChartParams, { ...(axis === "fade" ? { axisW: 24 } : {}), ...dfn({ lineColor: lc0, lineW: lw0 }), ...pp });
  const { lineColor, lineW } = P;
  const f = useCurrentFrame();
  const [x0, y0, x1, y1] = box; // 좌상(x0,y0) ~ 원점(x0,y1) ~ 우하(x1,y1)
  const Lv = y1 - y0, Lh = x1 - x0;
  const axW = P.axisW;
  const aV = d1(P.axisV), aH = d1(P.axisH);
  const axEnd = at + (axis === "draw" ? aV + aH : P.axisFade);
  // 축: 한 패스, 세로 14f ease-in → 가로 14f ease-out
  const axLen = axis === "draw"
    ? (f < at + aV ? lerp(f, at, at + aV, 0, Lv, Easing.in(Easing.quad)) : lerp(f, at + aV, at + aV + aH, Lv, Lv + Lh, Easing.out(Easing.quad)))
    : Lv + Lh;
  const axOp = axis === "fade" ? lerp(f, at, at + d1(P.axisFade), 0, 1, Easing.linear) : 1;
  const n = years.length;
  const px = (i: number) => x0 + 90 + (i / Math.max(1, n - 1)) * (Lh - 180);
  const py = (v: number) => y1 - 60 - ((v - min) / (max - min)) * (Lv - 120);
  const pts: P[] = values.map((v, i) => [px(i), py(v)]);
  const dotAt = axEnd + P.dotDelay;
  const lineAt = dotAt + P.lineDelay;
  const ld = d1(P.lineDur);
  const lp = lerp(f, lineAt, lineAt + ld, 0, 1, pickEase(P.ease, E_OUT));
  const head = pointAt(pts, lp);
  const endAt = lineAt + ld;
  const dS = kf(f, dotAt, [0, 3, 5], [0, P.dotOvershoot, 1], E_OUT);
  const eS = kf(f, endAt, [0, 2, 4], [0, P.dotOvershoot, 1], E_OUT);
  const dotD = dot === "big" ? 64 : 18;
  const dotC = dot === "big" ? lineColor : "#fff";
  return (
    <AbsoluteFill>
      {underlay && <DimUnderlay img={underlay} dim={P.dim} />}
      {title && <div style={{ position: "absolute", left: x0, top: y0 - 130, fontFamily: "NeoHv", fontSize: 58, color: "#fff", opacity: lerp(f, at, at + 8, 0, 1, Easing.linear) }}>{title}</div>}
      <svg width={W} height={H} style={{ position: "absolute", opacity: axOp }}>
        {years.map((yl, i) => {
          const ya = axEnd + i * P.labelStagger;
          const op = lerp(f, ya, ya + 5, 0, 1, Easing.linear);
          return (
            <g key={i} opacity={op}>
              <line x1={px(i)} x2={px(i)} y1={y0 + 20} y2={y1} stroke="rgba(255,255,255,0.45)" strokeWidth={3} strokeDasharray="12 10" />
              <text x={px(i)} y={y1 + 62} textAnchor="middle" fontFamily="NeoHv" fontSize={40} fill="#fff">{yl}</text>
            </g>
          );
        })}
        {f >= at && <path d={`M${x0},${y0} L${x0},${y1} L${x1},${y1}`} fill="none" stroke="#fff" strokeWidth={axW} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={`${axLen} ${Lv + Lh + 10}`} />}
        {f >= lineAt && <path d={polyD(pts)} pathLength={1} fill="none" stroke={lineColor} strokeWidth={lineW} strokeLinecap="round" strokeLinejoin="round" strokeDasharray="1 1" strokeDashoffset={1 - lp} />}
        {f >= dotAt && <circle cx={pts[0][0]} cy={pts[0][1]} r={(dotD / 2) * dS} fill={dotC} stroke={dot === "big" ? "#fff" : "none"} strokeWidth={6} />}
        {f >= lineAt && f < endAt && <circle cx={head.x} cy={head.y} r={lineW * 0.9} fill={lineColor} />}
        {f >= endAt && <circle cx={pts[n - 1][0]} cy={pts[n - 1][1]} r={(dot === "big" ? 22 : 11) * eS} fill={dot === "big" ? lineColor : "#fff"} stroke="#fff" strokeWidth={dot === "big" ? 6 : 0} />}
      </svg>
      {pills.map((p, i) => {
        const pa = dotAt + p.delay;
        if (f < pa) return null;
        const t = textPop(f, pa);
        const s = kf(f, pa, [0, 3, 5], [0.3, P.pillOvershoot, 1], E_OUT);
        const [qx, qy] = pts[p.idx];
        return (
          <div key={i} style={{ position: "absolute", left: qx - 150, top: qy - 118, width: 300, display: "flex", justifyContent: "center", transform: `scale(${s})`, transformOrigin: "50% 100%", opacity: t.op }}>
            <div style={{ background: p.color ?? "#fff", color: p.color ? "#fff" : "#1b1b1b", fontFamily: "NeoHv", fontSize: 44, padding: "10px 28px", borderRadius: 40, boxShadow: "0 6px 10px rgba(0,0,0,0.3)", whiteSpace: "nowrap" }}>{p.text}</div>
          </div>
        );
      })}
      {crowd && <CrowdRow at={endAt + crowd.delay} />}
      {stamp && <StampSlam text={stamp.text} x={stamp.x} y={stamp.y} at={endAt + stamp.delay} color={stamp.color} />}
    </AbsoluteFill>
  );
};

/** 빨간 도장 슬램 (2.4→1.0 4f + 흔들림 정착) */
export const StampSlamParams = z.object({
  slamDur: num(4, 1, 20, 1, "내리꽂는 시간", "timing", "f"),
  startScale: num(2.4, 1, 5, 0.1, "시작 크기(배)", "motion", "배"),
  wobble: num(0.06, 0, 0.3, 0.01, "착지 흔들림 세기", "motion"),
  wobbleDecay: num(3, 0.5, 12, 0.5, "흔들림 감쇠", "timing", "f"),
  rot: num(-10, -45, 45, 1, "기울기", "motion", "°"),
  size: num(96, 30, 220, 2, "글자 크기", "size", "px"),
  color: col("#E3261E", "도장 색"),
});
export type StampSlamP = z.infer<typeof StampSlamParams>;
export const StampSlam: React.FC<{ text: string; x: number; y: number; at: number; color?: string; rot?: number; size?: number; p?: Partial<StampSlamP> }> = ({ text, x, y, at, color: c0, rot: r0, size: s0, p: pp }) => {
  const P = def(StampSlamParams, { ...dfn({ color: c0, rot: r0, size: s0 }), ...pp });
  const { color, rot, size } = P;
  const f = useCurrentFrame();
  if (f < at) return null;
  const S = d1(P.slamDur);
  const k = lerp(f, at, at + S, P.startScale, 1, Easing.in(Easing.quad));
  const g = f - at - S;
  const settle = g > 0 ? 1 + P.wobble * Math.exp(-g / Math.max(0.1, P.wobbleDecay)) * Math.sin(g * 1.7) : 1;
  const op = lerp(f, at, at + 3, 0, 0.95, Easing.linear);
  return (
    <div style={{ position: "absolute", left: x, top: y, transform: `translate(-50%,-50%) rotate(${rot}deg) scale(${k * settle})`, opacity: op, border: `${size * 0.11}px solid ${color}`, borderRadius: size * 0.22, padding: `${size * 0.1}px ${size * 0.32}px ${size * 0.04}px`, fontFamily: "Jalnan", fontSize: size, color, whiteSpace: "nowrap", lineHeight: 1.1, background: "rgba(255,255,255,0.08)" }}>{text}</div>
  );
};

// ── 5. Podium ───────────────────────────────────────────────────────────
export type PodiumItem = { name: string; logo: string; color: string; h: number; rank: number };
export const PodiumParams = z.object({
  ribbonDrop: num(6, 0, 40, 1, "제목 리본 낙하 시간", "timing", "f"),
  rowDelay: num(14, 0, 60, 1, "1위 막대 등장 지연", "timing", "f"),
  stagger: num(14, 0, 60, 1, "순위 간 간격", "timing", "f"),
  firstRise: num(14, 1, 60, 1, "1위 솟는 시간", "timing", "f"),
  rise: num(12, 1, 60, 1, "2·3위 솟는 시간", "timing", "f"),
  riseExtra: num(260, 0, 800, 10, "화면 아래 출발 여백", "motion", "px"),
  overshoot: num(12, 0, 80, 1, "착지 오버슈트 높이", "motion", "px"),
  barW: num(300, 120, 520, 5, "막대 폭", "size", "px"),
  gap: num(60, 0, 200, 5, "막대 간격", "size", "px"),
  dim: num(0.25, 0, 1, 0.05, "배경 사진 어둡게", "look"),
  ribbonColor: col("#6E6E6E", "리본 색"),
});
export type PodiumP = z.infer<typeof PodiumParams>;
export const Podium: React.FC<{ at: number; title: string; items: PodiumItem[]; underlay?: string; barW?: number; gap?: number; baseY?: number; p?: Partial<PodiumP> }> = ({ at, title, items, underlay, barW: bw0, gap: gap0, baseY = H, p: pp }) => {
  const P = def(PodiumParams, { ...dfn({ barW: bw0, gap: gap0 }), ...pp });
  const { barW, gap } = P;
  const f = useCurrentFrame();
  // 배치: 2위-1위-3위 (가운데가 1위)
  const order = [...items].sort((a, b) => a.rank - b.rank);
  const slots = order.length === 3 ? [1, 0, 2] : order.map((_, i) => i);
  const n = order.length, totalW = n * barW + (n - 1) * gap, xs0 = W / 2 - totalW / 2;
  return (
    <AbsoluteFill>
      {underlay && <DimUnderlay img={underlay} dim={P.dim} />}
      <Ribbon text={title} x={W / 2} y={70} at={at} drop={P.ribbonDrop} typing color={P.ribbonColor} tail="#555" fold="#3a3a3a" />
      {order.map((it, k) => {
        const ra = at + P.rowDelay + k * P.stagger; // 1위 → +14f 2위 → +28f 3위
        if (f < ra) return null;
        const dur = d1(k === 0 ? P.firstRise : P.rise);
        const total = it.h + P.riseExtra;
        const o = P.overshoot;
        let dy: number;
        if (f < ra + dur) dy = lerp(f, ra, ra + dur, total, -o, E_OUT);
        else dy = kf(f, ra + dur, [0, 1, 2], [-o, o * 0.25, 0]); // 1~2f 작은 바운스
        const bx = xs0 + slots[k] * (barW + gap);
        const d = barW * 0.78;
        return (
          <div key={it.name} style={{ position: "absolute", left: bx, top: baseY - it.h + dy, width: barW }}>
            <div style={{ position: "absolute", left: (barW - d) / 2, top: -d * 1.08 + 8 }}><LogoChar d={d} bg={it.color} text={it.logo} /></div>
            <div style={{ position: "absolute", left: 0, top: 0, width: barW, height: it.h + 40, borderRadius: "18px 18px 0 0", background: it.color, boxShadow: "0 -4px 14px rgba(0,0,0,0.25)", filter: "brightness(0.92)" }}>
              <div style={{ marginTop: 26, textAlign: "center", fontFamily: "NeoHv", fontSize: 96, color: "rgba(255,255,255,0.95)" }}>{it.rank}</div>
              <div style={{ textAlign: "center", fontFamily: "NeoEb", fontSize: 40, color: "#fff" }}>{it.name}</div>
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// ── 6. TimelineBar ──────────────────────────────────────────────────────
export type TNode = { x: number; label: string };
export const TimelineBarParams = z.object({
  firstLine: num(11, 0, 60, 1, "첫 노드→선 시작 지연", "timing", "f"),
  segDur: num(12, 1, 60, 1, "구간 선 그리는 시간", "timing", "f"),
  segGap: num(12, 0, 60, 1, "구간 사이 쉼", "timing", "f"),
  nodePop: num(3, 1, 15, 1, "노드 팝 길이", "timing", "f"),
  markFade: num(10, 1, 40, 1, "배경 워드마크 페이드", "timing", "f"),
  tailMax: num(280, 0, 600, 10, "모션블러 꼬리 최대 길이", "motion", "px"),
  tailK: num(0.5, 0, 1.5, 0.05, "모션블러 꼬리 비율", "motion", "배"),
  thick: num(38, 4, 100, 1, "선 두께", "size", "px"),
  nodeD: num(50, 16, 140, 2, "노드 지름", "size", "px"),
  labelSize: num(64, 20, 140, 2, "라벨 크기", "size", "px"),
  bg: col("#F3C623", "배경 색"),
  lineColor: col("#141414", "선 색"),
  labelColor: col("#141414", "라벨 색"),
  mark: col("rgba(0,0,0,0.07)", "워드마크 색"),
});
export type TimelineBarP = z.infer<typeof TimelineBarParams>;
export const TimelineBar: React.FC<{ at: number; nodes: TNode[]; y?: number; wordmark?: string; bg?: string; mark?: string; lineColor?: string; labelColor?: string; segGap?: number; p?: Partial<TimelineBarP> }> = ({ at, nodes, y = 560, wordmark, bg: bg0, mark: mark0, lineColor: lc0, labelColor: lb0, segGap: sg0, p: pp }) => {
  const P = def(TimelineBarParams, { ...dfn({ bg: bg0, mark: mark0, lineColor: lc0, labelColor: lb0, segGap: sg0 }), ...pp });
  const { bg, mark, lineColor, labelColor, segGap } = P;
  const sd = d1(P.segDur), np = d1(P.nodePop);
  const f = useCurrentFrame();
  // 노드 i 등장 시각: 첫 노드 at, 선 at+11부터 12f, 끝노드 = 선 끝
  const nodeAt = (i: number) => (i === 0 ? at : at + P.firstLine + (i - 1) * (sd + segGap) + sd);
  const lineAt = (i: number) => at + P.firstLine + i * (sd + segGap);
  return (
    <AbsoluteFill style={{ background: bg }}>
      {wordmark && (
        <div style={{ position: "absolute", width: W, top: H / 2 - 260, textAlign: "center", fontFamily: "NeoHv", fontSize: 440, color: mark, letterSpacing: -10, whiteSpace: "nowrap", opacity: lerp(f, at, at + d1(P.markFade), 0, 1, Easing.linear) }}>{hz(wordmark)}</div>
      )}
      <svg width={W} height={H} style={{ position: "absolute" }}>
        <defs>
          <linearGradient id="tl-blur" x1="0" x2="1" y1="0" y2="0">
            <stop offset="0" stopColor={lineColor} stopOpacity={0.7} />
            <stop offset="1" stopColor={lineColor} stopOpacity={0} />
          </linearGradient>
        </defs>
        {nodes.slice(1).map((nd, i) => {
          const la = lineAt(i);
          if (f < la) return null;
          const xa = nodes[i].x, xb = nd.x;
          const p = lerp(f, la, la + sd, 0, 1, Easing.out(Easing.quad));
          const hx = xa + (xb - xa) * p;
          // 헤드 모션블러 꼬리: 속도(1-p)에 비례, 드로잉 끝나면 사라짐
          const tail = f < la + sd ? Math.min(P.tailMax, (xb - xa) * (1 - p) * P.tailK) : 0;
          const th = P.thick;
          return (
            <g key={i}>
              <rect x={xa} y={y - th / 2} width={hx - xa} height={th} fill={lineColor} />
              {tail > 4 && <rect x={hx} y={y - th / 2} width={tail} height={th} fill="url(#tl-blur)" style={{ filter: "blur(5px)" }} />}
            </g>
          );
        })}
      </svg>
      {nodes.map((nd, i) => {
        const na = nodeAt(i);
        if (f < na) return null;
        const s = kf(f, na, [0, np], [0, 1], E_OUT);
        const ls = kf(f, na, [0, np], [0.5, 1], E_OUT);
        const lo = kf(f, na, [0, np], [0, 1]);
        const nD = P.nodeD;
        return (
          <React.Fragment key={i}>
            <div style={{ position: "absolute", left: nd.x - nD / 2, top: y - nD / 2, width: nD, height: nD, borderRadius: "50%", background: "#fff", border: `7px solid ${lineColor}`, boxSizing: "border-box", transform: `scale(${s})`, opacity: s }} />
            <div style={{ position: "absolute", left: nd.x - 200, top: y + nD / 2 + 21, width: 400, textAlign: "center", fontFamily: "NeoHv", fontSize: P.labelSize, color: labelColor, transform: `scale(${ls})`, opacity: lo, transformOrigin: "50% 0" }}>{nd.label}</div>
          </React.Fragment>
        );
      })}
    </AbsoluteFill>
  );
};

// ── 7. ZigzagArrow ──────────────────────────────────────────────────────
export const ZigzagArrowParams = z.object({
  dur: num(14, 1, 60, 1, "화살표 그리는 시간", "timing", "f"),
  ease: choice("inout", ["inout", "out", "snappy", "linear"], "드로잉 이징", "motion"),
  headScale: num(2.6, 1, 6, 0.1, "화살촉 크기(선 두께 배)", "size", "배"),
  width: num(22, 4, 60, 1, "선 두께", "size", "px"),
  flash: flag(false, "번개 섬광 (하락 모드 기본 켬)", "look"),
  flashAt: num(0.55, 0, 1, 0.05, "섬광 위치(진행 비율)", "timing"),
  flashLen: num(3, 1, 12, 1, "섬광 길이", "timing", "f"),
  flashOp: num(0.55, 0, 1, 0.05, "섬광 첫 프레임 밝기", "look"),
  color: col("#E0161E", "화살표 색 (하락 모드 기본 흰색)"),
});
export type ZigzagArrowP = z.infer<typeof ZigzagArrowParams>;
export const ZigzagArrow: React.FC<{ at: number; dir?: "up" | "down"; pts?: P[]; color?: string; width?: number; dur?: number; flash?: boolean; p?: Partial<ZigzagArrowP> }> = ({ at, dir = "up", pts, color, width: w0, dur: dur0, flash, p: pp }) => {
  const P = def(ZigzagArrowParams, { ...(dir === "down" ? { color: "#fff", flash: true } : {}), ...dfn({ color, width: w0, dur: dur0, flash }), ...pp });
  const { width } = P;
  const dur = d1(P.dur);
  const f = useCurrentFrame();
  if (f < at) return null;
  const P0: P[] = pts ?? (dir === "up"
    ? [[-120, 1010], [520, 640], [780, 800], [1230, 360], [1450, 520], [2060, -110]]
    : [[-120, 90], [560, 470], [820, 330], [1260, 760], [1480, 610], [2060, 1180]]);
  const c = P.color;
  const p = lerp(f, at, at + dur, 0, 1, P.ease === "inout" ? Easing.inOut(Easing.quad) : EASES[P.ease]);
  const hd = pointAt(P0, p);
  const hs = width * P.headScale;
  const fl = P.flash;
  // 번개 섬광 스프라이트: 드로잉 중간 3f
  const fa = at + Math.round(dur * P.flashAt);
  const showFlash = fl && f >= fa && f < fa + P.flashLen;
  const fp = pointAt(P0, P.flashAt);
  return (
    <AbsoluteFill>
      {showFlash && <AbsoluteFill style={{ background: `rgba(255,255,255,${f === fa ? P.flashOp : (P.flashOp * 0.25) / 0.55})` }} />}
      <svg width={W} height={H} style={{ position: "absolute", overflow: "visible", filter: dir === "up" ? "drop-shadow(0 8px 10px rgba(0,0,0,0.3))" : "drop-shadow(0 0 10px rgba(255,255,255,0.7))" }}>
        <path d={polyD(P0)} pathLength={1} fill="none" stroke={c} strokeWidth={width} strokeLinejoin="miter" strokeLinecap="butt" strokeDasharray="1 1" strokeDashoffset={1 - p} />
        <polygon points={`${hs},0 ${-hs * 0.55},${-hs * 0.8} ${-hs * 0.25},0 ${-hs * 0.55},${hs * 0.8}`} fill={c} transform={`translate(${hd.x},${hd.y}) rotate(${(hd.ang * 180) / Math.PI})`} />
        {showFlash && (
          <polygon transform={`translate(${fp.x + 40},${fp.y - 150}) scale(${f === fa ? 1.4 : 1.1})`} fill="#fff" points="0,0 70,0 34,86 92,86 -18,250 18,120 -36,120" style={{ filter: "drop-shadow(0 0 18px #fff)" }} />
        )}
      </svg>
    </AbsoluteFill>
  );
};

// ── 8. CounterBadge ─────────────────────────────────────────────────────
export const CounterBadgeParams = z.object({
  startDelay: num(10, 0, 60, 1, "첫 카운트 전 대기", "timing", "f"),
  firstIv: num(11, 1, 30, 1, "첫 카운트 간격", "timing", "f"),
  accel: num(2, 0, 6, 0.5, "간격 가속(매 단계 감소)", "timing", "f"),
  minIv: num(2, 1, 15, 1, "최소 카운트 간격", "timing", "f"),
  maxSteps: num(12, 1, 40, 1, "최대 카운트 단계 수", "motion"),
  badgePop: num(0.3, 0, 1, 0.05, "배지 숫자 팝 세기", "motion", "배"),
  chipDelay: num(8, 0, 40, 1, "카운트 끝→캡슐 등장 지연", "timing", "f"),
  expandDelay: num(6, 0, 30, 1, "캡슐 펼침 지연", "timing", "f"),
  expandDur: num(9, 1, 40, 1, "캡슐 펼치는 시간", "timing", "f"),
  labelDelay: num(8, 0, 30, 1, "펼침 시작→라벨 지연", "timing", "f"),
  scale: num(1.8, 0.5, 3, 0.05, "전체 크기(배)", "size", "배"),
  pillW: num(360, 150, 700, 5, "캡슐 폭", "size", "px"),
  badge: num(45, 20, 100, 1, "빨간 배지 지름", "size", "px"),
  iconBg: col("#FEE500", "아이콘 배경 색"),
});
export type CounterBadgeP = z.infer<typeof CounterBadgeParams>;
export const CounterBadge: React.FC<{ at: number; x: number; y: number; n: number; label: string; icon?: React.ReactNode; iconBg?: string; scale?: number; pillW?: number; badge?: number; p?: Partial<CounterBadgeP> }> = ({ at, x, y, n, label, icon, iconBg: ib0, scale: sc0, pillW: pw0, badge: bd0, p: pp }) => {
  const P = def(CounterBadgeParams, { ...dfn({ iconBg: ib0, scale: sc0, pillW: pw0, badge: bd0 }), ...pp });
  const { iconBg, scale, pillW, badge } = P;
  const f = useCurrentFrame();
  if (f < at) return null;
  const g = f - at;
  // 가속되는 카운트: 11f → 9f → 7f … 최소 2f. N이 크면 12단계로 뭉쳐서 증가
  const K = Math.max(1, Math.min(n, Math.round(P.maxSteps)));
  const steps: number[] = [];
  let t = P.startDelay, iv = P.firstIv;
  for (let k = 1; k <= K; k++) { t += iv; steps.push(t); iv = Math.max(P.minIv, iv - P.accel); }
  const k = steps.filter((s) => g >= s).length;
  const val = Math.round((n * k) / K);
  const last = k > 0 ? steps[k - 1] : -99;
  const bPop = k > 0 ? 1 + P.badgePop * Math.max(0, 1 - (g - last) / 4) : kf(f, at + steps[0] - 3, [0, 3], [0, 1], E_OUT);
  const countEnd = at + steps[K - 1];
  const IS = 150, chipH = 96, gapX = 26;
  const chipAt = countEnd + P.chipDelay, expAt = chipAt + P.expandDelay;
  const cS = kf(f, chipAt, [0, 3, 5], [0, 1.15, 1], E_OUT);
  const cw = lerp(f, expAt, expAt + d1(P.expandDur), chipH, pillW, E_OUT);
  const effW = IS + (f >= chipAt ? (gapX + cw) * Math.min(1, cS) : 0);
  const left = -effW / 2; // 그룹 재중앙정렬
  const iconS = kf(f, at, [0, 3, 5], [0.3, 1.1, 1], E_OUT);
  const lblAt = expAt + P.labelDelay;
  const tp = textPop(f, lblAt);
  return (
    <div style={{ position: "absolute", left: x, top: y, transform: `scale(${scale})` }}>
      <div style={{ position: "absolute", left, top: -IS / 2, width: IS, height: IS, transform: `scale(${iconS})` }}>
        <div style={{ width: IS, height: IS, borderRadius: IS * 0.24, background: iconBg, boxShadow: "0 8px 14px rgba(0,0,0,0.25)", display: "flex", alignItems: "center", justifyContent: "center" }}>{icon}</div>
        {f >= at + steps[0] - 3 && (
          <div style={{ position: "absolute", right: -badge * 0.35, top: -badge * 0.35, width: badge, height: badge, borderRadius: "50%", background: "#F2291E", color: "#fff", fontFamily: "NeoHv", fontSize: badge * (val >= 100 ? 0.42 : val >= 10 ? 0.52 : 0.62), display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${bPop})`, border: "3px solid #fff", boxSizing: "border-box", boxShadow: "0 3px 5px rgba(0,0,0,0.3)" }}>{val}</div>
        )}
      </div>
      {f >= chipAt && (
        <div style={{ position: "absolute", left: left + IS + gapX, top: -chipH / 2, width: cw, height: chipH, borderRadius: chipH / 2, background: "#fff", boxShadow: "0 8px 14px rgba(0,0,0,0.25)", transform: `scale(${cS})`, transformOrigin: `${chipH / 2}px 50%`, overflow: "hidden", display: "flex", alignItems: "center", justifyContent: "center" }}>
          {f >= lblAt && <div style={{ fontFamily: "NeoHv", fontSize: 40, color: "#1b1b1b", whiteSpace: "nowrap", transform: `scale(${tp.s})`, opacity: tp.op, filter: `blur(${tp.blur * 0.3}px)` }}>{label}</div>}
        </div>
      )}
    </div>
  );
};

// ── 9. StatGauge ────────────────────────────────────────────────────────
export const Spark: React.FC<{ x: number; y: number; seed: string; size?: number; color?: string }> = ({ x, y, seed, size = 34, color = "#BFF3FF" }) => {
  const arms = 5;
  const paths: string[] = [];
  for (let a = 0; a < arms; a++) {
    const base = (a / arms) * TAU + random(`${seed}-a${a}`) * 0.9;
    let d = "M0,0";
    for (let s = 1; s <= 3; s++) {
      const rr = (size / 3) * s * (0.7 + 0.5 * random(`${seed}-r${a}-${s}`));
      const aa = base + (random(`${seed}-j${a}-${s}`) - 0.5) * 0.9;
      d += ` L${(rr * Math.cos(aa)).toFixed(1)},${(rr * Math.sin(aa)).toFixed(1)}`;
    }
    paths.push(d);
  }
  return (
    <svg width={size * 3} height={size * 3} viewBox={`${-size * 1.5} ${-size * 1.5} ${size * 3} ${size * 3}`} style={{ position: "absolute", left: x - size * 1.5, top: y - size * 1.5, overflow: "visible", filter: "drop-shadow(0 0 6px #fff) drop-shadow(0 0 10px #6fdcff)" }}>
      {paths.map((d, i) => <path key={i} d={d} fill="none" stroke={i % 2 ? "#fff" : color} strokeWidth={3.5} strokeLinejoin="round" strokeLinecap="round" />)}
      <circle r={size * 0.28} fill="#fff" />
    </svg>
  );
};

export const StatGaugeParams = z.object({
  dropDur: num(10, 1, 40, 1, "떨어져 들어오는 시간", "timing", "f"),
  dropDist: num(260, 0, 800, 10, "떨어지는 거리", "motion", "px"),
  fillDelay: num(22, 0, 80, 1, "게이지 채움 시작 지연", "timing", "f"),
  fillDur: num(12, 1, 90, 1, "게이지 채우는 시간", "timing", "f"),
  ease: choice("linear", ["linear", "out", "inout", "snappy", "bar"], "채움 이징", "motion"),
  sparkSize: num(34, 0, 100, 1, "스파크 크기", "size", "px"),
  barH: num(40, 8, 90, 1, "게이지 두께", "size", "px"),
  w: num(820, 400, 1400, 10, "전체 폭", "size", "px"),
  color: col("#1DA1E6", "게이지 색"),
  sparkColor: col("#BFF3FF", "스파크 색"),
});
export type StatGaugeP = z.infer<typeof StatGaugeParams>;
export const StatGauge: React.FC<{ at: number; x: number; y: number; pct: number; label: string; icon?: React.ReactNode; iconBg?: string; w?: number; color?: string; valueText?: string; dark?: boolean; p?: Partial<StatGaugeP> }> = ({ at, x, y, pct, label, icon, iconBg = "#1DA1E6", w: w0, color: c0, valueText, dark = false, p: pp }) => {
  const P = def(StatGaugeParams, { ...dfn({ w: w0, color: c0 }), ...pp });
  const { w, color } = P;
  const f = useCurrentFrame();
  if (f < at) return null;
  const dy = lerp(f, at, at + d1(P.dropDur), -P.dropDist, 0, E_OUT);
  const op = lerp(f, at, at + 4, 0, 1, Easing.linear);
  const fillAt = at + P.fillDelay, fd = d1(P.fillDur);
  const fp = lerp(f, fillAt, fillAt + fd, 0, pct, EASES[P.ease]);
  const barX = 130, barY = 62, barH = P.barH, barW = w - barX;
  const filling = f >= fillAt && f < fillAt + fd + 2;
  const vOp = lerp(f, fillAt + fd - 2, fillAt + fd + 4, 0, 1, Easing.linear);
  return (
    <div style={{ position: "absolute", left: x, top: y + dy, width: w, height: 110, opacity: op }}>
      <div style={{ position: "absolute", left: 0, top: 4, width: 104, height: 104, borderRadius: "50%", background: iconBg, border: "6px solid #fff", boxSizing: "border-box", boxShadow: "0 6px 10px rgba(0,0,0,0.25)", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "NeoHv", fontSize: 44, color: "#fff" }}>{icon}</div>
      <div style={{ position: "absolute", left: barX, top: 0, fontFamily: "NeoHv", fontSize: 40, color: dark ? "#fff" : "#1b1b1b", whiteSpace: "nowrap" }}>{label}</div>
      <div style={{ position: "absolute", right: 0, top: 0, fontFamily: "NeoHv", fontSize: 40, color, opacity: vOp }}>{valueText ?? `${Math.round(pct * 100)}%`}</div>
      <div style={{ position: "absolute", left: barX, top: barY, width: barW, height: barH, borderRadius: barH / 2, background: dark ? "#4a4a4a" : "#D6D6D6", overflow: "hidden" }}>
        <div style={{ width: barW * fp, height: barH, background: color, borderRadius: barH / 2 }} />
      </div>
      {filling && P.sparkSize > 0 && <Spark x={barX + barW * fp} y={barY + barH / 2} seed={`sg${x}${y}-${f}`} size={P.sparkSize} color={P.sparkColor} />}
    </div>
  );
};

// ── 10. WaterfallStairs ─────────────────────────────────────────────────
export const WaterfallStairsParams = z.object({
  step: num(15, 1, 60, 1, "블록 간 등장 간격", "timing", "f"),
  hop: num(15, 1, 60, 1, "점프 체공 시간", "timing", "f"),
  jumpH: num(150, 0, 500, 5, "점프 높이", "motion", "px"),
  landSX: num(1.14, 1, 1.6, 0.01, "착지 찌그러짐 가로(배)", "motion", "배"),
  landSY: num(0.8, 0.4, 1, 0.01, "착지 찌그러짐 세로(배)", "motion", "배"),
  blockOvershoot: num(1.12, 1, 1.6, 0.01, "블록 팝 오버슈트(배)", "motion", "배"),
  arrowDur: num(7, 1, 30, 1, "연결 화살표 그리는 시간", "timing", "f"),
  arrowW: num(5, 1, 20, 1, "화살표 두께", "size", "px"),
  bw: num(140, 60, 360, 2, "블록 폭", "size", "px"),
  bh: num(40, 20, 120, 2, "블록 높이", "size", "px"),
  arrowColor: col("#3a3a3a", "화살표 색"),
});
export type WaterfallStairsP = z.infer<typeof WaterfallStairsParams>;
export const WaterfallStairs: React.FC<{ at: number; labels: string[]; colors?: string[]; x0?: number; y0?: number; dx?: number; dy?: number; bw?: number; bh?: number; step?: number; hop?: number; mascot?: React.ReactNode; mascotW?: number; mascotH?: number; arrowColor?: string; p?: Partial<WaterfallStairsP> }> = ({ at, labels, colors = ["#E0412B", "#43A047", "#1DA1E0", "#F2B705", "#B3123A"], x0 = 380, y0 = 330, dx = 260, dy = 130, bw: bw0, bh: bh0, step: st0, hop: hop0, mascot, mascotW = 110, mascotH = 140, arrowColor: ac0, p: pp }) => {
  const P = def(WaterfallStairsParams, { ...dfn({ bw: bw0, bh: bh0, step: st0, hop: hop0, arrowColor: ac0 }), ...pp });
  const { bw, bh, step, arrowColor } = P;
  const hop = d1(P.hop), ad = d1(P.arrowDur);
  const f = useCurrentFrame();
  if (f < at) return null;
  const bx = (i: number) => x0 + i * dx, by = (i: number) => y0 + i * dy;
  const bAt = (i: number) => at + i * step;
  // 마스코트 위치: i 블록 위로 hop
  let mx = bx(0) + bw / 2, my = by(0), sx = 1, sy = 1;
  for (let i = 1; i < labels.length; i++) {
    const ha = bAt(i) + 1;
    if (f >= ha) {
      const t = Math.min(1, (f - ha) / hop);
      const ax = bx(i - 1) + bw / 2, ay = by(i - 1), cx = bx(i) + bw / 2, cy = by(i);
      mx = ax + (cx - ax) * t;
      my = ay + (cy - ay) * t - P.jumpH * 4 * t * (1 - t);
      const land = f - (ha + hop);
      if (land >= 0 && land < 2) { sx = P.landSX; sy = P.landSY; }
      else if (land >= 2 && land < 4) { sx = 0.96; sy = 1.05; }
    }
  }
  const m0 = f - at;
  if (m0 < 2) { sx = P.landSX; sy = P.landSY; }
  const mOp = kf(f, at, [0, 3], [0, 1]);
  return (
    <AbsoluteFill>
      <svg width={W} height={H} style={{ position: "absolute" }}>
        {labels.slice(1).map((_, j) => {
          const i = j + 1;
          const a0 = bAt(i) - ad;
          if (f < a0) return null;
          const p = lerp(f, a0, a0 + ad, 0, 1, Easing.out(Easing.quad));
          const sx0 = bx(i - 1) + bw * 0.3, sy0 = by(i - 1) + bh + 4, ex = bx(i) - 12, ey = by(i) + bh / 2;
          const pts: P[] = [[sx0, sy0], [sx0, ey], [ex, ey]];
          const hd = pointAt(pts, p);
          return (
            <g key={i}>
              <path d={polyD(pts)} pathLength={1} fill="none" stroke={arrowColor} strokeWidth={P.arrowW} strokeDasharray="1 1" strokeDashoffset={1 - p} strokeLinejoin="round" />
              <polygon points="10,0 -8,-9 -8,9" fill={arrowColor} transform={`translate(${hd.x},${hd.y}) rotate(${(hd.ang * 180) / Math.PI})`} />
            </g>
          );
        })}
      </svg>
      {labels.map((l, i) => {
        const ba = bAt(i);
        if (f < ba) return null;
        const s = kf(f, ba, [0, 3, 5], [0.3, P.blockOvershoot, 1], E_OUT);
        return (
          <div key={i} style={{ position: "absolute", left: bx(i), top: by(i), width: bw, height: bh, borderRadius: 10, background: colors[i % colors.length], color: "#fff", fontFamily: "NeoHv", fontSize: bh * 0.55, display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${s})`, boxShadow: "0 5px 8px rgba(0,0,0,0.22)", whiteSpace: "nowrap" }}>{l}</div>
        );
      })}
      <div style={{ position: "absolute", left: mx - mascotW / 2, top: my - mascotH + 4, width: mascotW, height: mascotH, transform: `scale(${sx},${sy})`, transformOrigin: "50% 100%", opacity: mOp, display: "flex", alignItems: "flex-end", justifyContent: "center" }}>
        {mascot ?? <LogoChar d={mascotW * 0.9} bg="#E0412B" text="세모" />}
      </div>
    </AbsoluteFill>
  );
};

// ── 11. MoneyTitle ──────────────────────────────────────────────────────
/** 지폐·동전 더미 — 세모지 money_pile(초록 지폐 면이 키잉으로 빠진 것을 메운 xc_money_pile 1000×585).
 *  박스 w × 0.36w(기존 SVG 와 같은 바닥선), 그림 폭 0.62w 가운데·바닥 정렬(제목과 겹치지 않게) */
export const MoneyPile: React.FC<{ w?: number }> = ({ w = 1000 }) => {
  const iw = w * 0.62, ih = (iw * 585) / 1000;
  return (
    <div style={{ position: "relative", width: w, height: w * 0.36 }}>
      <Img src={prop("xc_money_pile")} style={{ position: "absolute", left: (w - iw) / 2, bottom: w * 0.005, width: iw, height: ih }} />
    </div>
  );
};

export const MoneyTitleParams = z.object({
  pile: flag(true, "돈더미 표시", "look"),
  pileRise: num(11, 1, 40, 1, "돈더미 솟는 시간", "timing", "f"),
  pileDist: num(420, 0, 800, 10, "돈더미 솟는 거리", "motion", "px"),
  pileBack: num(1.6, 0, 4, 0.1, "돈더미 튕김 세기", "motion"),
  titleDelay: num(9, 0, 40, 1, "돈더미→숫자 등장 지연", "timing", "f"),
  popDur: num(4, 2, 20, 1, "숫자 팝 길이", "timing", "f"),
  popStart: num(0.3, 0, 1, 0.05, "숫자 시작 크기(배)", "motion", "배"),
  popOvershoot: num(1.12, 1, 1.6, 0.01, "숫자 오버슈트(배)", "motion", "배"),
  size: num(210, 60, 400, 5, "숫자 크기", "size", "px"),
  depth: num(18, 0, 60, 1, "입체 두께(겹 수)", "size", "px"),
  face: col("#FA9C00", "앞면 색"),
  side: col("#EB8000", "옆면 색"),
});
export type MoneyTitleP = z.infer<typeof MoneyTitleParams>;
export const MoneyTitle: React.FC<{ at: number; text: string; x?: number; y?: number; size?: number; face?: string; side?: string; depth?: number; pile?: boolean; titleDelay?: number; p?: Partial<MoneyTitleP> }> = ({ at, text, x = W / 2, y = 400, size: sz0, face: fc0, side: sd0, depth: dp0, pile: pl0, titleDelay: td0, p: pp }) => {
  const P = def(MoneyTitleParams, { ...dfn({ size: sz0, face: fc0, side: sd0, depth: dp0, pile: pl0, titleDelay: td0 }), ...pp });
  const { size, face, side, pile, titleDelay } = P;
  const depth = Math.max(0, Math.round(P.depth));
  const f = useCurrentFrame();
  if (f < at) return null;
  const pileY = lerp(f, at, at + d1(P.pileRise), P.pileDist, 0, Easing.out(Easing.back(P.pileBack)));
  const ta = at + (pile ? titleDelay : 0);
  const pd = Math.max(2, P.popDur);
  const s = kf(f, ta, [0, pd / 2, pd], [P.popStart, P.popOvershoot, 1.0], E_OUT);
  const layer = (dx: number, dy: number, color: string, k: string, extra: React.CSSProperties = {}) => (
    <div key={k} style={{ position: "absolute", left: dx, top: dy, width: "100%", textAlign: "center", fontFamily: "NeoHv", fontSize: size, color, whiteSpace: "nowrap", lineHeight: 1, ...extra }}>{text}</div>
  );
  return (
    <AbsoluteFill>
      {pile && (
        <div style={{ position: "absolute", left: x - 500, top: H - 380 + pileY, filter: "drop-shadow(0 8px 10px rgba(0,0,0,0.2))" }}><MoneyPile /></div>
      )}
      {f >= ta && (
        <div style={{ position: "absolute", left: x - 1000, top: y - size / 2, width: 2000, height: size + depth, transform: `scale(${s})`, filter: "drop-shadow(0 14px 12px rgba(0,0,0,0.3))" }}>
          {Array.from({ length: depth }, (_, i) => layer((depth - i) * 0.35, depth - i, i === 0 ? "#B85F00" : side, `d${i}`, i === 0 ? { WebkitTextStroke: `10px #B85F00` } : { WebkitTextStroke: `10px ${side}` }))}
          {layer(0, 0, face, "face", { WebkitTextStroke: `10px ${face}` })}
          {layer(0, 0, face, "face2", { backgroundImage: `linear-gradient(180deg, #FFC04A 0%, ${face} 55%)`, WebkitBackgroundClip: "text", backgroundClip: "text", WebkitTextFillColor: "transparent" })}
        </div>
      )}
    </AbsoluteFill>
  );
};

// ── 12. DiscPie3D ───────────────────────────────────────────────────────
export const DiscPie3DParams = z.object({
  rivalFade: num(10, 1, 40, 1, "경쟁자 고스트→선명 시간", "timing", "f"),
  rivalStartOp: num(0.4, 0, 1, 0.05, "경쟁자 시작 불투명도", "look"),
  rx: num(440, 150, 800, 10, "원판 가로 반지름", "size", "px"),
  ry: num(170, 40, 400, 5, "원판 세로 반지름(기울기)", "size", "px"),
  depth: num(40, 0, 150, 2, "원판 두께", "size", "px"),
  edgeW: num(4, 0, 16, 1, "경계선 두께", "size", "px"),
  mainLabelSize: num(64, 20, 140, 2, "주 라벨 크기", "size", "px"),
  compLabelSize: num(52, 20, 140, 2, "경쟁 라벨 크기", "size", "px"),
  main: col("#29C5E6", "주 영역 색"),
  mainSide: col("#1B97B3", "주 영역 옆면 색"),
  compColor: col("#F28C28", "경쟁 영역 색"),
  compSide: col("#C0650F", "경쟁 영역 옆면 색"),
});
export type DiscPie3DP = z.infer<typeof DiscPie3DParams>;
export const DiscPie3D: React.FC<{
  at: number; x?: number; y?: number; rx?: number; ry?: number; depth?: number; comp: number; compStart?: number;
  main?: string; mainSide?: string; compColor?: string; compSide?: string;
  hero?: { img: string; h: number; dx: number; dy?: number }; rival?: { img: string; h: number; dx: number; dy?: number; delay: number; flip?: boolean };
  mainLabel?: string; compLabel?: string; mainLabelAt?: P; compLabelAt?: P;
  p?: Partial<DiscPie3DP>;
}> = ({ mainLabelAt, compLabelAt, at, x = W / 2, y = 660, rx: rx0, ry: ry0, depth: dp0, comp, compStart = -0.1, main: m0, mainSide: ms0, compColor: cc0, compSide: cs0, hero, rival, mainLabel, compLabel, p: pv }) => {
  const P = def(DiscPie3DParams, { ...dfn({ rx: rx0, ry: ry0, depth: dp0, main: m0, mainSide: ms0, compColor: cc0, compSide: cs0 }), ...pv });
  const { rx, ry, depth, main, mainSide, compColor, compSide } = P;
  const f = useCurrentFrame();
  if (f < at) return null;
  const pp = photoPop(f, at);
  // 각도: 0 = 오른쪽, 시계방향(y 아래) 라디안
  const a0 = compStart * TAU, a1 = a0 + comp * TAU;
  const ep = (a: number, dz = 0): P => [rx * Math.cos(a), ry * Math.sin(a) + dz];
  const arcPts = (s: number, e: number, dz = 0, N = 48) => Array.from({ length: N + 1 }, (_, i) => ep(s + ((e - s) * i) / N, dz));
  const sector = [[0, 0] as P, ...arcPts(a0, a1)];
  const sideBand = (s: number, e: number) => {
    const ss = Math.max(s, 0), ee = Math.min(e, Math.PI);
    if (ee <= ss) return "";
    return polyD([...arcPts(ss, ee), ...arcPts(ee, ss, depth)]) + " Z";
  };
  const rf = d1(P.rivalFade);
  const rv = rival ? kf(f, at + rival.delay, [0, rf], [P.rivalStartOp, 1]) : 1;
  const rvGray = rival ? kf(f, at + rival.delay, [0, rf], [1, 0]) : 0;
  const lc = (a: number, k = 0.55): P => ep(a, 0).map((v) => v * k) as P;
  const mMid = a1 + ((1 - comp) * TAU) / 2, cMid = (a0 + a1) / 2;
  const [mlx, mly] = mainLabelAt ?? lc(mMid), [clx, cly] = compLabelAt ?? lc(cMid);
  return (
    <div style={{ position: "absolute", left: x, top: y, transform: `scale(${pp.s})`, filter: `blur(${pp.blur}px)` }}>
      <svg width={2 * rx + 40} height={2 * ry + depth + 40} viewBox={`${-rx - 20} ${-ry - 20} ${2 * rx + 40} ${2 * ry + depth + 40}`} style={{ position: "absolute", left: -rx - 20, top: -ry - 20, overflow: "visible", filter: SHADOW }}>
        <path d={sideBand(0, Math.PI)} fill={mainSide} />
        <path d={sideBand(a0, a1)} fill={compSide} />
        {a1 > TAU && <path d={sideBand(0, a1 - TAU)} fill={compSide} />}
        <ellipse cx={0} cy={0} rx={rx} ry={ry} fill={main} />
        <path d={polyD(sector) + " Z"} fill={compColor} />
        <path d={polyD([[0, 0], ep(a0)])} stroke="rgba(255,255,255,0.7)" strokeWidth={P.edgeW} />
        <path d={polyD([[0, 0], ep(a1)])} stroke="rgba(255,255,255,0.7)" strokeWidth={P.edgeW} />
      </svg>
      {mainLabel && <div style={{ position: "absolute", left: mlx - 150, top: mly - 10, width: 300, textAlign: "center", fontFamily: "NeoHv", fontSize: P.mainLabelSize, color: "#fff", textShadow: "0 3px 0 rgba(0,0,0,0.2)" }}>{mainLabel}</div>}
      {compLabel && <div style={{ position: "absolute", left: clx - 150 + 40, top: cly + 10, width: 300, textAlign: "center", fontFamily: "NeoHv", fontSize: P.compLabelSize, color: "#fff", textShadow: "0 3px 0 rgba(0,0,0,0.2)" }}>{compLabel}</div>}
      {hero && <Img src={src(hero.img)} style={{ position: "absolute", left: hero.dx - hero.h * 0.36, top: (hero.dy ?? 0) - hero.h, height: hero.h, filter: "drop-shadow(0 0 4px #fff) drop-shadow(0 0 4px #fff) drop-shadow(0 10px 10px rgba(0,0,0,0.3))" }} />}
      {rival && <Img src={src(rival.img)} style={{ position: "absolute", left: rival.dx - rival.h * 0.33, top: (rival.dy ?? 0) - rival.h, height: rival.h, opacity: rv, transform: rival.flip ? "scaleX(-1)" : undefined, filter: `grayscale(${rvGray}) drop-shadow(0 0 4px #fff) drop-shadow(0 10px 10px rgba(0,0,0,${0.3 * rv}))` }} />}
    </div>
  );
};

// ── 13. AgileRings ──────────────────────────────────────────────────────
export type Ring = { label: string; caption: string; c1: string; c2: string };
export const AgileRingsParams = z.object({
  arrowDur: num(14, 1, 60, 1, "무지개 화살표 뻗는 시간", "timing", "f"),
  ringDelay: num(10, 0, 60, 1, "첫 링 등장 지연", "timing", "f"),
  every: num(15, 0, 60, 1, "링 스태거 간격", "timing", "f"),
  damping: num(9, 1, 40, 1, "링 스프링 감쇠(낮을수록 출렁)", "motion"),
  stiffness: num(220, 20, 600, 10, "링 스프링 강성", "motion"),
  captionDelay: num(6, 0, 40, 1, "링→캡션 지연", "timing", "f"),
  captionDur: num(8, 1, 30, 1, "캡션 등장 길이", "timing", "f"),
  captionRise: num(16, 0, 80, 1, "캡션 떠오르는 거리", "motion", "px"),
  d: num(240, 80, 400, 5, "링 지름", "size", "px"),
  stroke: num(48, 4, 120, 1, "링 두께", "size", "px"),
  arrowH: num(84, 20, 200, 2, "화살표 두께", "size", "px"),
  labelSize: num(40, 16, 90, 1, "링 글자 크기", "size", "px"),
});
export type AgileRingsP = z.infer<typeof AgileRingsParams>;
export const AgileRings: React.FC<{ at: number; items: Ring[]; y?: number; d?: number; stroke?: number; x0?: number; x1?: number; every?: number; p?: Partial<AgileRingsP> }> = ({ at, items, y = 470, d: d0, stroke: st0, x0 = 90, x1 = 1830, every: ev0, p: pp }) => {
  const P = def(AgileRingsParams, { ...dfn({ d: d0, stroke: st0, every: ev0 }), ...pp });
  const { d, stroke, every } = P;
  const f = useCurrentFrame();
  if (f < at) return null;
  const aw = lerp(f, at, at + d1(P.arrowDur), 0, 1, E_OUT);
  const ah = P.arrowH, head = 90;
  const n = items.length;
  const cx = (i: number) => x0 + 190 + (i * (x1 - x0 - 190 - 250)) / Math.max(1, n - 1);
  const r = Math.max(0, (d - stroke) / 2);
  return (
    <AbsoluteFill>
      <svg width={W} height={H} style={{ position: "absolute", filter: SHADOW }}>
        <defs>
          <linearGradient id="ag-rain" x1="0" x2="1" y1="0" y2="0">
            {["#E53935", "#FB8C00", "#FDD835", "#43A047", "#1E88E5", "#8E24AA"].map((c, i) => <stop key={i} offset={i / 5} stopColor={c} />)}
          </linearGradient>
          <clipPath id="ag-clip"><rect x={0} y={0} width={x0 + (x1 - x0 + 20) * aw} height={H} /></clipPath>
        </defs>
        <path clipPath="url(#ag-clip)" fill="url(#ag-rain)" d={`M${x0},${y - ah / 2} L${x1 - head},${y - ah / 2} L${x1 - head},${y - ah / 2 - 40} L${x1},${y} L${x1 - head},${y + ah / 2 + 40} L${x1 - head},${y + ah / 2} L${x0},${y + ah / 2} Z`} />
      </svg>
      {items.map((it, i) => {
        const ra = at + P.ringDelay + i * every;
        if (f < ra) return null;
        const s = popSpring(f, ra, 30, P.damping, P.stiffness);
        const ca = ra + P.captionDelay, cd = d1(P.captionDur);
        const cOp = lerp(f, ca, ca + cd, 0, 1, Easing.linear);
        const cY = lerp(f, ca, ca + cd, P.captionRise, 0, E_OUT);
        const x = cx(i);
        return (
          <React.Fragment key={i}>
            <div style={{ position: "absolute", left: x - d / 2, top: y - d / 2, width: d, height: d, transform: `scale(${s})`, filter: SHADOW }}>
              <svg width={d} height={d} style={{ position: "absolute" }}>
                <circle cx={d / 2} cy={d / 2} r={d / 2 - 2} fill="#fff" />
                <path d={`M${d / 2 - r},${d / 2} A${r},${r} 0 0 1 ${d / 2 + r},${d / 2}`} fill="none" stroke={it.c1} strokeWidth={stroke} />
                <path d={`M${d / 2 + r},${d / 2} A${r},${r} 0 0 1 ${d / 2 - r},${d / 2}`} fill="none" stroke={it.c2} strokeWidth={stroke} />
              </svg>
              <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "NeoHv", fontSize: P.labelSize, color: "#222", whiteSpace: "nowrap" }}>{it.label}</div>
            </div>
            <div style={{ position: "absolute", left: x - 170, top: y + d / 2 + 40 + cY, width: 340, display: "flex", justifyContent: "center", opacity: cOp }}>
              <div style={{ background: "#8A8A8A", color: "#fff", fontFamily: "NeoEb", fontSize: 32, padding: "10px 26px", borderRadius: 32, whiteSpace: "nowrap" }}>{it.caption}</div>
            </div>
          </React.Fragment>
        );
      })}
    </AbsoluteFill>
  );
};

