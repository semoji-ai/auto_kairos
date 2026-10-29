// 세모지 모션 어휘 — 레퍼런스(NZsB8vnv1FU) 프레임 분석에서 뽑은 컴포넌트 모음.
import { RemotionMap } from "./map/RemotionMap";
import { lngLatToPixel, type CameraState } from "./map/cameraInterpolation";
import { KoreaIslands } from "./map/KoreaIslands";
import React from "react";
import {
  AbsoluteFill, Img, interpolate, spring, useCurrentFrame, useVideoConfig,
  staticFile, Easing, random, continueRender, delayRender,
} from "remotion";
import { z } from "zod";
import { num, col, flag, choice, def } from "./params/p";
import { prop, CAST, CastId } from "./lib/kit";
import { SemojiRig } from "./lib/semoji_rig";
/** 머리 꼭대기가 (x, headTop) 에 오게 세모지 캐스트 배치(s = 캔버스 px → 화면 px) */
const CastHead: React.FC<{ cast: CastId; x: number; headTop: number; s: number; seed?: string; flip?: boolean }> = ({ cast, x, headTop, s, seed, flip }) => {
  const R = CAST[cast], h = (R.feet[1] - R.top) * s;
  return <SemojiRig cast={cast} x={x} y={headTop + h} h={h} seed={seed ?? cast} flip={flip} />;
};

export const FPS = 30;
export const W = 1920;
export const H = 1080;
export const s2f = (s: number) => Math.round(s * FPS);
const CL = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

export const lerp = (f: number, a: number, b: number, v0: number, v1: number,
  e: (t: number) => number = Easing.out(Easing.cubic)) =>
  interpolate(f, [a, b], [v0, v1], { ...CL, easing: e });

export const popSpring = (f: number, at: number, fps = FPS, damping = 11, stiffness = 190) =>
  spring({ frame: f - at, fps, config: { damping, stiffness, mass: 0.7 } });

/** 선형 키프레임: 프레임 오프셋 배열 ks 에서 값 vs 를 보간 */
export const kf = (f: number, at: number, ks: number[], vs: number[], e: (t: number) => number = Easing.linear) =>
  interpolate(f - at, ks, vs, { ...CL, easing: e });
/** 변수 헬퍼: undefined 가 아닌 개별 prop 만 남긴다(스키마 기본값을 덮지 않게) */
const pick = <T extends Record<string, unknown>>(o: T): Partial<T> =>
  Object.fromEntries(Object.entries(o).filter(([, v]) => v !== undefined)) as Partial<T>;
/** 길이 변수 방어: 0·음수 → 최소값 */
const pos = (v: number, min = 0.001) => Math.max(min, v);
/** 키프레임 입력이 단조 증가가 되도록 보정(변수 극단값에서 interpolate 오류 방지) */
const inc = (ks: number[]) => ks.reduce<number[]>((a, v, i) => (a.push(i ? Math.max(v, a[i - 1] + 0.001) : v), a), []);
// 원형·사진 팝: 0.4→0.7→1.0→1.08→1.03→1.0 (6f) + 줌블러 6→0 (3f)   [ref 139.8s·392.5s]
// 변수: len(곡선 길이 f, 기본 5) · from(시작 크기 0.4) · over(오버슈트 0.08, 되돌이 1.03 = over×0.375) · blur(6) · blurLen(3)
export type PhotoPopO = { len?: number; from?: number; over?: number; blur?: number; blurLen?: number };
export const photoPop = (f: number, at: number, o: PhotoPopO = {}) => {
  const L = pos(o.len ?? 5), a = o.from ?? 0.4, ov = o.over ?? 0.08;
  return {
    s: kf(f, at, [0, 1, 2, 3, 4, 5].map((i) => (i * L) / 5), [a, a + (1 - a) * 0.5, 1.0, 1 + ov, 1 + ov * 0.375, 1.0]),
    blur: kf(f, at, [0, pos(o.blurLen ?? 3)], [o.blur ?? 6, 0]),
  };
};
// 텍스트 팝: 크게 나타나 줄어든다 1.25→1.15→1.08→1.0 (7f), 불투명 0.4→1 (2f), 가로블러 8→0 (3f)   [ref 228.05s]
// 변수: len(7) · from(1.25, 중간값은 (from-1)×0.6·0.32 비율) · op0(0.4) · opLen(2) · blur(8) · blurLen(3)
export type TextPopO = { len?: number; from?: number; op0?: number; opLen?: number; blur?: number; blurLen?: number };
export const textPop = (f: number, at: number, o: TextPopO = {}) => {
  const L = pos(o.len ?? 7), d = (o.from ?? 1.25) - 1;
  return {
    s: kf(f, at, [0, (2 * L) / 7, (5 * L) / 7, L], [1 + d, 1 + d * 0.6, 1 + d * 0.32, 1.0]),
    op: kf(f, at, [0, pos(o.opLen ?? 2)], [o.op0 ?? 0.4, 1]),
    blur: kf(f, at, [0, pos(o.blurLen ?? 3)], [o.blur ?? 8, 0]),
  };
};
export const EXPO_OUT = Easing.bezier(0.16, 1, 0.3, 1);
export const QUART_OUT = Easing.bezier(0.25, 1, 0.5, 1);
/** 한자만 명조로 감싼다 — 한글 손글씨 폰트는 한자를 빈 글리프로 갖고 있어 폴백이 안 된다 */
export const hz = (t: string) => t.split(/([\u3400-\u9FFF]+)/).map((p, i) => /[\u3400-\u9FFF]/.test(p) ? <span key={i} style={{ fontFamily: "'Songti SC','STSong',serif", fontWeight: 900 }}>{p}</span> : p);
export const src = (p: string) => (p.startsWith("http") ? p : staticFile(p));

// ── 폰트 ────────────────────────────────────────────────────────────────
const FONTS: [string, string][] = [
  ["Yeonsung", "fonts/BMYEONSUNG_ttf.ttf"],
  ["NeoHv", "fonts/NanumSquareNeoOTF-eHv.otf"],
  ["NeoEb", "fonts/NanumSquareNeoOTF-dEb.otf"],
  ["Jalnan", "fonts/Jalnan.ttf"],
  ["Jua", "fonts/BMJUA_otf.otf"],
  ["Dohyeon", "fonts/BMDOHYEON_otf.otf"],
  ["MyeongjoEB", "fonts/NanumMyeongjoExtraBold.ttf"],
];
if (typeof window !== "undefined" && typeof FontFace !== "undefined") {
  const h = delayRender("fonts", { timeoutInMilliseconds: 120000, retries: 2 });
  Promise.all(FONTS.map(([n, f]) => new FontFace(n, `url(${staticFile(f)})`).load()
    .then((ff) => (document.fonts as any).add(ff))))
    .then(() => continueRender(h)).catch(() => continueRender(h));
}

// ── 씬 래퍼: 전환 + 카메라 ─────────────────────────────────────────────
// 카메라는 기본 고정. 움직이는 샷은 moveF 프레임 안에 easeInOutCubic 으로 끝내고 정지한다
// (ref: 샷의 절반은 완전 정지, 나머지는 "풀백 리빌" 1.45~1.75→1.0 을 45~110f).
// whip: 나가기 6f(블러 0→200, x 0→-300, easeIn) + 들어오기 10f(블러 200→0, x +300→0, scale 1.1→1.0)
type Cam = { s0?: number; s1?: number; x0?: number; x1?: number; y0?: number; y1?: number; moveF?: number; delay?: number };
export const SceneParams = z.object({
  whipInLen: num(10, 1, 40, 1, "휩 입장 길이", "timing", "f"),
  whipOutLen: num(6, 1, 30, 1, "휩 퇴장 길이", "timing", "f"),
  whipDist: num(300, 0, 1200, 10, "휩 이동 거리", "motion", "px"),
  whipBlur: num(200, 0, 500, 10, "휩 모션블러 세기", "look", "px"),
  whipScale: num(1.1, 1, 1.6, 0.01, "휩 입장 시작 크기(배)", "motion"),
  dissolveLen: num(13, 1, 60, 1, "디졸브 길이", "timing", "f"),
  coverLen: num(18, 1, 60, 1, "커버 밀기 길이", "timing", "f"),
  zoomInLen: num(8, 1, 40, 1, "줌인 입장 길이", "timing", "f"),
  zoomInFrom: num(3, 1, 8, 0.1, "줌인 시작 배율(배)", "motion"),
  zoomInBlur: num(20, 0, 60, 1, "줌인 블러", "look", "px"),
  zoomThroughLen: num(4, 1, 20, 1, "줌스루 퇴장 길이", "timing", "f"),
  zoomThroughAmt: num(0.4, 0, 3, 0.05, "줌스루 확대량(배)", "motion"),
  zoomThroughRgb: num(8, 0, 40, 1, "줌스루 RGB 분리", "look", "px"),
});
export type SceneP = z.infer<typeof SceneParams>;
export const Scene: React.FC<{
  dur: number; enter?: "whip" | "cut" | "dissolve" | "cover" | "zoomIn"; exit?: "whip" | "cut" | "zoomThrough"; exitOrigin?: string;
  cam?: Cam; bg?: string; children: React.ReactNode; id: string; overlay?: React.ReactNode; p?: Partial<SceneP>;
}> = ({ dur, enter = "cut", exit = "cut", cam, bg, children, id, overlay, exitOrigin = "50% 50%", p: pp }) => {
  const P = def(SceneParams, pp);
  const f = useCurrentFrame();
  let tx = 0, blur = 0, op = 1, sc0 = 1;
  if (enter === "whip") {
    const L = P.whipInLen;
    tx = lerp(f, 0, L, P.whipDist, 0, EXPO_OUT); blur = lerp(f, 0, L, P.whipBlur, 0, EXPO_OUT); sc0 = lerp(f, 0, L, P.whipScale, 1, EXPO_OUT);
  }
  if (enter === "dissolve") op = lerp(f, 0, P.dissolveLen, 0, 1, Easing.linear);
  if (enter === "cover") tx = lerp(f, 0, P.coverLen, W, 0, QUART_OUT);
  // 줌 스루 [ref 227.0s]: 나가는 씬 3f 동안 scale 1→1.4 + RGB 분리 ±8px, 들어오는 씬 scale 3→1 (8f) + 블러 20→0
  let zs = 1, rgb = 0, zb = 0, origin = "50% 50%";
  const ZL = P.zoomThroughLen;
  if (exit === "zoomThrough" && f > dur - ZL) { const k = lerp(f, dur - ZL, dur, 0, 1, Easing.in(Easing.quad)); zs = 1 + P.zoomThroughAmt * k; rgb = P.zoomThroughRgb * k; origin = exitOrigin; }
  if (enter === "zoomIn") { zs = lerp(f, 0, P.zoomInLen, P.zoomInFrom, 1, EXPO_OUT); zb = lerp(f, 0, P.zoomInLen, P.zoomInBlur, 0, EXPO_OUT); }
  const WL = P.whipOutLen;
  if (exit === "whip" && f > dur - WL) {
    tx = lerp(f, dur - WL, dur, 0, -P.whipDist, Easing.in(Easing.quad)); blur = lerp(f, dur - WL, dur, 0, P.whipBlur, Easing.in(Easing.quad));
  }
  const c = cam || {};
  const mv = c.moveF ?? dur, dl = c.delay ?? 0;
  const p = lerp(f, dl, dl + mv, 0, 1, Easing.inOut(Easing.cubic));
  const sc = ((c.s0 ?? 1) + ((c.s1 ?? 1) - (c.s0 ?? 1)) * p) * sc0;
  const cx = (c.x0 ?? 0) + ((c.x1 ?? 0) - (c.x0 ?? 0)) * p;
  const cy = (c.y0 ?? 0) + ((c.y1 ?? 0) - (c.y0 ?? 0)) * p;
  const fid = `mb-${id}`;
  return (
    <AbsoluteFill style={{ transform: `translateX(${tx}px) scale(${zs})`, transformOrigin: origin, opacity: op, filter: [blur > 0.5 ? `url(#${fid})` : "", zb > 0.3 ? `blur(${zb}px)` : "", rgb > 0.3 ? `drop-shadow(${rgb}px 0 0 rgba(255,0,60,0.55)) drop-shadow(${-rgb}px 0 0 rgba(0,220,255,0.55))` : ""].join(" ") || undefined, overflow: "hidden", background: bg }}>
      <svg width={0} height={0} style={{ position: "absolute" }}>
        <filter id={fid} x="-20%" y="0%" width="140%" height="100%"><feGaussianBlur stdDeviation={`${blur / 3} 0`} /></filter>
      </svg>
      <AbsoluteFill style={{ transform: `translate(${cx}px,${cy}px) scale(${sc})`, transformOrigin: "50% 50%" }}>
        {children}
      </AbsoluteFill>
      {overlay}
    </AbsoluteFill>
  );
};

// ── 전체 화면 이미지(커버) ──────────────────────────────────────────────
export const Cover: React.FC<{ img: string; style?: React.CSSProperties }> = ({ img, style }) => (
  <Img src={src(img)} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", ...style }} />
);

// ── HUD: 로고 + 챕터 진행 바 ─────────────────────────────────────────────
export const HUDParams = z.object({
  fillDelay: num(6, 0, 30, 1, "채움 이동 지연", "timing", "f"),
  fillLen: num(13, 1, 40, 1, "채움 이동 길이", "timing", "f"),
  fontSize: num(24, 12, 48, 1, "챕터 글자 크기", "size", "px"),
  fillColor: col("#a9a6a4", "활성 칸 채움 색"),
  activeColor: col("#fff", "활성 글자 색"),
  idleColor: col("#8e8b88", "비활성 글자 색"),
});
export type HUDP = z.infer<typeof HUDParams>;
export const HUD: React.FC<{ chapters?: string[]; active?: number; changeAt?: number; showBar?: boolean; p?: Partial<HUDP> }> = ({ chapters = [], active = -1, changeAt = 0, showBar = true, p }) => {
  const P = def(HUDParams, p);
  const f = useCurrentFrame();
  const x0 = 287, x1 = 1790, n = chapters.length || 1;
  const cw = (x1 - x0) / n;
  const prev = Math.max(active - 1, 0);
  const k = lerp(f, changeAt + P.fillDelay, changeAt + P.fillDelay + P.fillLen, 0, 1, EXPO_OUT);
  const fillX = active < 0 ? 0 : (prev + (active - prev) * k) * cw;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <Img src={staticFile("ui/logo.png")} style={{ position: "absolute", left: 26, top: 22, width: 198, height: 118 }} />
      {showBar && chapters.length > 0 && (
        <div style={{ position: "absolute", left: x0, top: 46, width: x1 - x0, height: 67, borderRadius: 20, border: "4px solid rgba(178,176,174,0.95)", overflow: "hidden", background: "transparent" }}>
          {active >= 0 && <div style={{ position: "absolute", left: fillX - 4, top: -4, width: cw + 4, height: 75, borderRadius: 18, background: P.fillColor }} />}
          {chapters.map((c, i) => (
            <div key={c} style={{ position: "absolute", left: i * cw, width: cw, top: 0, height: 59, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "NeoEb", fontSize: P.fontSize, color: i === active ? P.activeColor : P.idleColor, textShadow: i === active ? "none" : "0 0 3px rgba(255,255,255,0.55)" }}>{c}</div>
          ))}
        </div>
      )}
    </AbsoluteFill>
  );
};

// ── HUD v2 (2026-09 리뉴얼): 좌상단 흰 원형 로고(지름 72) + 오른쪽 흰 라벨(높이 44, y 38~82)에
//    현재 챕터의 브랜드 워드마크(빨간 세리프). 챕터 바 없음. 훅 구간은 원형 로고만.
export const HUD2Params = z.object({
  wipeLen: num(8, 1, 40, 1, "라벨 와이프 길이", "timing", "f"),
  fontSize: num(32, 16, 60, 1, "라벨 글자 크기", "size", "px"),
  letterSpacing: num(3, -2, 16, 0.5, "자간", "size", "px"),
  textColor: col("#9A3B2E", "워드마크 색"),
  bgColor: col("#fff", "라벨 바탕 색"),
});
export type HUD2P = z.infer<typeof HUD2Params>;
export const HUD2: React.FC<{ label?: string; changeAt?: number; p?: Partial<HUD2P> }> = ({ label, changeAt = 0, p }) => {
  const P = def(HUD2Params, p);
  const f = useCurrentFrame();
  const k = lerp(f, changeAt, changeAt + P.wipeLen, 0, 100, EXPO_OUT);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {label && (
        <div style={{ position: "absolute", left: 66, top: 38, height: 44, background: P.bgColor, display: "flex", alignItems: "center", padding: "0 26px 0 44px", clipPath: `inset(0 ${100 - k}% 0 0)` }}>
          <div style={{ fontFamily: "MyeongjoEB", fontSize: P.fontSize, color: P.textColor, letterSpacing: P.letterSpacing, whiteSpace: "nowrap", lineHeight: 1 }}>{hz(label)}</div>
        </div>
      )}
      <Img src={staticFile("ui/logo_circle.png")} style={{ position: "absolute", left: 22, top: 23, width: 72, height: 72 }} />
    </AbsoluteFill>
  );
};

// ── 하단 자막 띠 ────────────────────────────────────────────────────────
export type Sub = { t0: number; t1: number; text: string };
export const SubtitlesParams = z.object({
  fontSize: num(50, 24, 80, 1, "자막 글자 크기", "size", "px"),
  borderW: num(3, 0, 12, 1, "카드 테두리 두께", "size", "px"),
  paperOp: num(0.35, 0, 1, 0.05, "종이 질감 세기", "look"),
  shadowOp: num(0.9, 0, 1, 0.05, "그림자 카드 불투명도", "look"),
  textColor: col("#1f1f1f", "글자 색"),
  cardColor: col("#FCF9F6", "카드 색"),
  borderColor: col("#777", "테두리 색"),
});
export type SubtitlesP = z.infer<typeof SubtitlesParams>;
export const Subtitles: React.FC<{ subs: Sub[]; p?: Partial<SubtitlesP> }> = ({ subs, p }) => {
  const P = def(SubtitlesParams, p);
  const f = useCurrentFrame();
  const t = f / FPS;
  const cur = subs.find((s) => t >= s.t0 && t < s.t1);
  if (!cur) return null;
  return (
    <>
      <div style={{ position: "absolute", left: 119, top: 912, width: 1690, height: 80, background: `rgba(24,24,24,${P.shadowOp})` }} />
      <div style={{ position: "absolute", left: 113, top: 905, width: 1690, height: 80, boxSizing: "border-box", border: `${P.borderW}px solid ${P.borderColor}`, background: P.cardColor, overflow: "hidden", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <svg width={1690} height={80} style={{ position: "absolute", left: 0, top: 0, opacity: P.paperOp, mixBlendMode: "multiply" }}>
          <filter id="subpaper"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={11} /><feColorMatrix values="0 0 0 0 0.93  0 0 0 0 0.91  0 0 0 0 0.9  0 0 0 -2.2 1.9" /></filter>
          <rect width="100%" height="100%" filter="url(#subpaper)" />
        </svg>
        <div style={{ position: "relative", fontFamily: "NeoHv", fontSize: P.fontSize, color: P.textColor, letterSpacing: -0.5 }}>{cur.text}</div>
      </div>
    </>
  );
};

// ── 연도 두루마리 태그 [ref 1:32 프레임 실측]: 왼쪽 화면 밖에서 태그 전체(글자·롤러 함께)가 16f 감속 슬라이드.
// 교체: 이전 태그는 제자리에 그대로 두고, 새 태그가 그 위로 같은 방식으로 들어와 덮는다 → 덮인 뒤(out) 이전 태그 제거.
export const YearTagParams = z.object({
  slideLen: num(16, 1, 40, 1, "슬라이드 입장 길이", "timing", "f"),
  fontSize: num(70, 30, 120, 1, "글자 크기", "size", "px"),
  charW: num(58, 30, 100, 1, "글자당 태그 폭", "size", "px"),
  skew: num(-5, -20, 20, 1, "글자 기울임", "motion", "°"),
  paperColor: col("#F7E1C4", "종이 색"),
  bandColor: col("#B03A2E", "띠·롤러 색"),
  textColor: col("#4B2420", "글자 색"),
});
export type YearTagP = z.infer<typeof YearTagParams>;
export const YearTag: React.FC<{ text: string; at: number; out?: number; top?: number; p?: Partial<YearTagP> }> = ({ text, at, out, top = 175, p }) => {
  const P = def(YearTagParams, p);
  const f = useCurrentFrame();
  if (f < at || (out !== undefined && f >= out)) return null;
  const full = 110 + text.length * P.charW;
  const x = lerp(f, at, at + P.slideLen, -(full + 40), 0, QUART_OUT);
  return (
    <div style={{ position: "absolute", left: 0, top, transform: `translateX(${x}px)`, display: "flex", alignItems: "center", filter: "drop-shadow(0 4px 6px rgba(0,0,0,0.35))" }}>
      <div style={{ width: full, background: P.paperColor, borderTop: `9px solid ${P.bandColor}`, borderBottom: `9px solid ${P.bandColor}`, padding: "10px 0 6px 50px", boxSizing: "border-box", fontFamily: "Yeonsung, 'Songti SC', serif", fontSize: P.fontSize, color: P.textColor, lineHeight: 1.15, WebkitTextStroke: `1.6px ${P.textColor}`, whiteSpace: "nowrap", boxShadow: `inset 0 0 0 3px ${P.paperColor}, inset 0 0 0 5px #D9A77E` }}>
        <span style={{ display: "inline-block", transform: `skewX(${P.skew}deg)` }}>{text}</span>
      </div>
      <div style={{ position: "relative", width: 28, height: 150, background: P.bandColor, borderRadius: 4 }}>
        <div style={{ position: "absolute", left: -3, top: -12, width: 34, height: 16, background: "#E3A33A", borderRadius: 5 }} />
        <div style={{ position: "absolute", left: -3, bottom: -12, width: 34, height: 16, background: "#E3A33A", borderRadius: 5 }} />
      </div>
    </div>
  );
};

// ── 가로 두루마리 라벨(중앙에서 펼쳐짐) ──────────────────────────────────
export const ScrollLabelParams = z.object({
  unrollDelay: num(3, 0, 20, 1, "펼침 시작 지연", "timing", "f"),
  unrollLen: num(11, 1, 40, 1, "펼침 길이", "timing", "f"),
  startW: num(0.06, 0, 1, 0.01, "접힌 폭 비율", "motion"),
  damping: num(11, 2, 40, 1, "팝 스프링 감쇠", "motion"),
  stiffness: num(190, 30, 500, 5, "팝 스프링 강성", "motion"),
  outLen: num(6, 1, 30, 1, "퇴장 길이", "timing", "f"),
  size: num(70, 30, 140, 1, "글자 크기", "size", "px"),
  color: col("#2E7D4F", "롤러·테두리 색"),
  paperColor: col("#F6E6C2", "종이 색"),
});
export type ScrollLabelP = z.infer<typeof ScrollLabelParams>;
export const ScrollLabel: React.FC<{ text: string; x: number; y: number; at: number; w?: number; color?: string; size?: number; sub?: string; out?: number; p?: Partial<ScrollLabelP> }> = ({ text, x, y, at, w = 420, color: color0, size: size0, sub, out, p }) => {
  const P = def(ScrollLabelParams, { ...pick({ color: color0, size: size0 }), ...p });
  const color = P.color, size = P.size;
  const f = useCurrentFrame();
  if (f < at || (out !== undefined && f > out + P.outLen)) return null;
  const k = lerp(f, at + P.unrollDelay, at + P.unrollDelay + P.unrollLen, P.startW, 1, Easing.out(Easing.cubic));
  const s = popSpring(f, at, FPS, P.damping, P.stiffness) * (out !== undefined ? lerp(f, out, out + P.outLen, 1, 0) : 1);
  const bw = w * k, h = 116;
  const rod = (side: "l" | "r") => (
    <div style={{ position: "absolute", top: -14, [side === "l" ? "left" : "right"]: -16, width: 30, height: h + 28, background: color, borderRadius: 6, boxShadow: "inset -6px 0 0 rgba(0,0,0,0.18)" }}>
      <div style={{ position: "absolute", left: -4, top: -10, width: 38, height: 14, background: "#6B3B22", borderRadius: 4 }} />
      <div style={{ position: "absolute", left: -4, bottom: -10, width: 38, height: 14, background: "#6B3B22", borderRadius: 4 }} />
    </div>
  );
  return (
    <div style={{ position: "absolute", left: x - bw / 2, top: y - h / 2, width: bw, height: h, transform: `scale(${s})`, filter: "drop-shadow(0 6px 8px rgba(0,0,0,0.35))" }}>
      <div style={{ position: "absolute", inset: 0, background: P.paperColor, boxShadow: `inset 0 0 0 6px ${P.paperColor}, inset 0 0 0 9px ${color}`, overflow: "hidden", display: "flex", alignItems: "center", justifyContent: "center", gap: 18 }}>
        {sub && <div style={{ fontFamily: "Yeonsung, 'Songti SC', serif", fontSize: 26, color: "#5a3a2a", writingMode: "vertical-rl", lineHeight: 1 }}>{hz(sub)}</div>}
        <div style={{ fontFamily: "Yeonsung, 'Songti SC', serif", fontSize: size, color: "#3A1F1A", whiteSpace: "nowrap", paddingTop: 8 }}>{text}</div>
      </div>
      {rod("l")}{rod("r")}
    </div>
  );
};

// ── 컬러 테두리 사진 프레임(어둡게→밝게 팝) ─────────────────────────────
// ── 컬러 테두리 사진 프레임: 사진 팝 곡선(0.4→1.08→1.0, 6f)+줌블러, 켄번스 없음(ref) ───
/** 사진 팝 곡선 공통 변수(PhotoFrame·Sticker·CircleImg) */
const photoPopShape = {
  popLen: num(5, 1, 30, 1, "팝 길이", "timing", "f"),
  popFrom: num(0.4, 0, 1.5, 0.05, "팝 시작 크기(배)", "motion"),
  popOver: num(0.08, 0, 0.5, 0.01, "오버슈트 크기(배)", "motion"),
};
const popBlurShape = {
  popBlur: num(6, 0, 40, 1, "팝 줌블러", "look", "px"),
  popBlurLen: num(3, 1, 20, 1, "줌블러 해제 길이", "timing", "f"),
};
const popO = (P: { popLen: number; popFrom: number; popOver: number; popBlur?: number; popBlurLen?: number }): PhotoPopO =>
  ({ len: P.popLen, from: P.popFrom, over: P.popOver, blur: P.popBlur, blurLen: P.popBlurLen });
export const PhotoFrameParams = z.object({
  ...photoPopShape, ...popBlurShape,
  rot: num(0, -30, 30, 0.5, "기울기", "motion", "°"),
  pad: num(8, 0, 40, 1, "컬러 테두리 두께", "size", "px"),
  innerBorder: num(4, 0, 20, 1, "흰 안쪽 테두리", "size", "px"),
  color: col("#2E5FB0", "테두리 색"),
});
export type PhotoFrameP = z.infer<typeof PhotoFrameParams>;
export const PhotoFrame: React.FC<{ img: string; x: number; y: number; w: number; h: number; at: number; color?: string; bw?: boolean; pos?: string; rot?: number; p?: Partial<PhotoFrameP> }> = ({ img, x, y, w, h, at, color, bw = false, pos = "50% 50%", rot, p }) => {
  const P = def(PhotoFrameParams, { ...pick({ color, rot }), ...p });
  const f = useCurrentFrame();
  if (f < at) return null;
  const { s, blur } = photoPop(f, at, popO(P));
  return (
    <div style={{ position: "absolute", left: x, top: y, width: w, height: h, transform: `scale(${s}) rotate(${P.rot}deg)`, filter: `blur(${blur}px) drop-shadow(0 8px 12px rgba(0,0,0,0.45))` }}>
      <div style={{ position: "absolute", inset: 0, borderRadius: 8, background: P.color, padding: P.pad }}>
        <div style={{ width: "100%", height: "100%", borderRadius: 4, border: `${P.innerBorder}px solid #fff`, overflow: "hidden", background: "#222" }}>
          <Img src={src(img)} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: pos, filter: bw ? "grayscale(1) contrast(1.08)" : undefined }} />
        </div>
      </div>
    </div>
  );
};

// ── 흰 글로우 스티커(누끼·사진 공통) ────────────────────────────────────
export const GLOW = "drop-shadow(0 0 5px #fff) drop-shadow(0 0 5px #fff) drop-shadow(0 0 16px rgba(255,255,255,0.9))";
export const StickerParams = z.object({
  slideLen: num(18, 1, 60, 1, "슬라이드 입장 길이", "timing", "f"),
  slideX: num(1150, 0, 2400, 10, "가로 슬라이드 거리", "motion", "px"),
  slideY: num(700, 0, 1400, 10, "세로 슬라이드 거리", "motion", "px"),
  ...photoPopShape,
  outLen: num(7, 1, 30, 1, "퇴장 길이", "timing", "f"),
  outBack: num(1.5, 0, 4, 0.1, "퇴장 백 이징 세기", "motion"),
  bob: num(0, 0, 0.1, 0.005, "까딱 세기(세로 비율)", "motion"),
  bobPeriod: num(9, 1, 40, 0.5, "까딱 속도(작을수록 빠름)", "timing", "f"),
  glow: flag(true, "흰 글로우 테두리", "look"),
});
export type StickerP = z.infer<typeof StickerParams>;
export const Sticker: React.FC<{ img: string; x: number; y: number; w: number; h?: number; at: number; from?: "bottom" | "left" | "right" | "pop" | "none"; glow?: boolean; bob?: number; out?: number; fit?: "contain" | "cover"; flip?: boolean; extraFilter?: string; p?: Partial<StickerP> }> = ({ img, x, y, w, h, at, from = "pop", glow, bob, out, fit = "contain", flip, extraFilter = "", p }) => {
  const P = def(StickerParams, { ...pick({ glow, bob }), ...p });
  const f = useCurrentFrame();
  if (f < at || (out !== undefined && f > out + P.outLen + 1)) return null;
  let tx = 0, ty = 0, s = 1;
  // 캐릭터 슬라이드인: 1000~1250px 을 18f easeOutQuart, 오버슈트 없음 [ref 519.6s]
  if (from === "bottom") ty = lerp(f, at, at + P.slideLen, P.slideY, 0, QUART_OUT);
  if (from === "left") tx = lerp(f, at, at + P.slideLen, -P.slideX, 0, QUART_OUT);
  if (from === "right") tx = lerp(f, at, at + P.slideLen, P.slideX, 0, QUART_OUT);
  if (from === "pop") s = photoPop(f, at, popO(P)).s;
  if (out !== undefined) s *= lerp(f, out, out + P.outLen, 1, 0, Easing.in(Easing.back(P.outBack)));
  const sy = 1 + P.bob * Math.sin((f - at) / pos(P.bobPeriod));
  return (
    <Img src={src(img)} style={{ position: "absolute", left: x, top: y, width: w, height: h, objectFit: fit, transform: `translate(${tx}px,${ty}px) scale(${s * (flip ? -1 : 1)},${s * sy})`, transformOrigin: "50% 100%", filter: (P.glow ? GLOW : "") + " " + extraFilter }} />
  );
};

// ── 원형 사진(흰 테두리 팝) ─────────────────────────────────────────────
// ── 원형 사진: 사진 팝 곡선 + 줌블러, 흰 링 10px ──────────────────────────
export const CircleImgParams = z.object({
  ...photoPopShape, ...popBlurShape,
  ringW: num(10, 0, 40, 1, "링 두께", "size", "px"),
  shadow: num(0.4, 0, 1, 0.05, "그림자 진하기", "look"),
  border: col("#fff", "링 색"),
});
export type CircleImgP = z.infer<typeof CircleImgParams>;
export const CircleImg: React.FC<{ img: string; x: number; y: number; d: number; at: number; pos?: string; border?: string; p?: Partial<CircleImgP> }> = ({ img, x, y, d, at, pos: opos = "50% 50%", border, p }) => {
  const P = def(CircleImgParams, { ...pick({ border }), ...p });
  const f = useCurrentFrame();
  if (f < at) return null;
  const { s, blur } = photoPop(f, at, popO(P));
  return (
    <div style={{ position: "absolute", left: x - d / 2, top: y - d / 2, width: d, height: d, borderRadius: "50%", overflow: "hidden", border: `${P.ringW}px solid ${P.border}`, transform: `scale(${s})`, filter: `blur(${blur}px)`, boxShadow: `0 10px 24px rgba(0,0,0,${P.shadow})`, background: "#ddd" }}>
      <Img src={src(img)} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: opos }} />
    </div>
  );
};

// ── 도장 꽝 ─────────────────────────────────────────────────────────────
export const StampParams = z.object({
  slamDur: num(5, 1, 20, 1, "내리꽂는 시간", "timing", "f"),
  startScale: num(2.6, 1, 5, 0.1, "시작 크기(배)", "motion"),
  wobble: num(0.05, 0, 0.2, 0.01, "착지 흔들림 세기", "motion"),
  wobbleDecay: num(3, 1, 10, 0.5, "흔들림 감쇠(f)", "timing", "f"),
  echoDur: num(8, 0, 20, 1, "잔상 링 시간", "timing", "f"),
  blinkDelay: num(8, 0, 30, 1, "깜빡임 시작 지연", "timing", "f"),
  blinkCount: num(3, 0, 8, 1, "깜빡임 횟수", "motion"),
  blinkPeriod: num(8, 2, 20, 1, "깜빡임 주기", "timing", "f"),
  blinkDim: num(0.55, 0, 1, 0.05, "깜빡일 때 불투명도", "look"),
  rot: num(-12, -45, 45, 1, "기울기", "motion", "°"),
  size: num(120, 40, 260, 2, "글자 크기", "size", "px"),
  color: col("#EC2D5C", "도장 색"),
  blink: flag(true, "슬램 후 깜빡임(끄면 그대로 유지)", "motion"),
  slamEase: choice("in", ["in", "expoOut"] as const, "슬램 이징(in=기존 가속 · expoOut=빠르게 붙고 감속)"),
});
export type StampP = z.infer<typeof StampParams>;
export const Stamp: React.FC<{ text: string; x: number; y: number; at: number; rot?: number; size?: number; color?: string; p?: Partial<StampP> }> = ({ text, x, y, at, rot, size, color, p }) => {
  const P = def(StampParams, { ...(rot !== undefined ? { rot } : {}), ...(size !== undefined ? { size } : {}), ...(color !== undefined ? { color } : {}), ...p });
  const f = useCurrentFrame();
  if (f < at) return null;
  const S = P.slamDur;
  const k = lerp(f, at, at + S, P.startScale, 1, P.slamEase === "expoOut" ? EXPO_OUT : Easing.in(Easing.quad));
  const settle = f > at + S ? 1 + P.wobble * Math.exp(-(f - at - S) / P.wobbleDecay) * Math.sin((f - at - S) * 1.6) : 1;
  const g0 = f - at - P.blinkDelay, half = P.blinkPeriod / 2;
  const op = lerp(f, at, at + 4, 0, 0.95) * (P.blink && g0 >= 0 && g0 < P.blinkCount * P.blinkPeriod && Math.floor(g0 / half) % 2 === 0 ? P.blinkDim : 1);
  const echo = P.echoDur > 0 && f >= at + S && f < at + S + P.echoDur;
  const sz = P.size, c = P.color;
  const box = (extra: React.CSSProperties) => (
    <div style={{ position: "absolute", left: 0, top: 0, transform: "translate(-50%,-50%)", border: `${sz * 0.12}px solid ${c}`, borderRadius: sz * 0.28, padding: `${sz * 0.08}px ${sz * 0.3}px ${sz * 0.02}px`, fontFamily: "Jalnan", fontSize: sz, color: c, whiteSpace: "nowrap", lineHeight: 1.1, ...extra }}>{text}</div>
  );
  return (
    <div style={{ position: "absolute", left: x, top: y, transform: `rotate(${P.rot}deg) scale(${k * settle})`, opacity: op, mixBlendMode: "multiply" }}>
      {echo && box({ transform: `translate(-50%,-50%) scale(${1 + (f - at - S) * 0.035})`, opacity: lerp(f, at + S, at + S + P.echoDur, 0.6, 0) })}
      {box({})}
    </div>
  );
};

// ── 노란 스타버스트 말풍선(보일링) ───────────────────────────────────────
// ── 스타버스트: 본체 3f 팝 + 고스트 에코(150%·50% → 100%·0, 13f), 테두리 보일링 [ref 394.1s·568.2s]
export const StarburstParams = z.object({
  popLen: num(3, 1, 20, 1, "본체 팝 길이", "timing", "f"),
  echoLen: num(13, 0, 40, 1, "고스트 에코 길이", "timing", "f"),
  echoScale: num(1.5, 1, 3, 0.05, "에코 시작 크기(배)", "motion"),
  echoOp: num(0.5, 0, 1, 0.05, "에코 시작 불투명도", "look"),
  spikes: num(18, 6, 40, 1, "가시 개수", "size"),
  innerR: num(0.72, 0.3, 1, 0.01, "가시 안쪽 반지름 비율", "size"),
  boilEvery: num(4, 1, 20, 1, "보일링 교체 간격", "timing", "f"),
  boilAmt: num(0.025, 0, 0.2, 0.005, "보일링 떨림 세기", "motion"),
  outLen: num(6, 1, 30, 1, "퇴장 길이", "timing", "f"),
  rot: num(-8, -45, 45, 1, "기울기", "motion", "°"),
  size: num(58, 20, 140, 1, "글자 크기", "size", "px"),
  color: col("#F7D84A", "말풍선 색"),
});
export type StarburstP = z.infer<typeof StarburstParams>;
export const Starburst: React.FC<{ text: string; x: number; y: number; w?: number; h?: number; at: number; rot?: number; size?: number; color?: string; out?: number; p?: Partial<StarburstP> }> = ({ text, x, y, w = 420, h = 280, at, rot: rot0, size: size0, color: color0, out, p }) => {
  const P = def(StarburstParams, { ...pick({ rot: rot0, size: size0, color: color0 }), ...p });
  const rot = P.rot, size = P.size, color = P.color;
  const f = useCurrentFrame();
  if (f < at || (out !== undefined && f > out + P.outLen)) return null;
  const body = kf(f, at, [0, P.popLen], [0, 1], Easing.out(Easing.quad)) * (out !== undefined ? lerp(f, out, out + P.outLen, 1, 0) : 1);
  const seed = Math.floor((f - at) / P.boilEvery);
  const N = Math.round(P.spikes), pts: string[] = [];
  for (let i = 0; i < N * 2; i++) {
    const a = (i / (N * 2)) * Math.PI * 2;
    const r = i % 2 === 0 ? 1 : P.innerR + 0.1 * random(`sb${i}`);
    const j = 1 + P.boilAmt * (random(`j${i}-${seed}`) - 0.5);
    pts.push(`${(0.5 + 0.5 * r * j * Math.cos(a)) * w},${(0.5 + 0.5 * r * j * Math.sin(a)) * h}`);
  }
  const shape = (extra: React.CSSProperties) => (
    <div style={{ position: "absolute", left: x - w / 2, top: y - h / 2, width: w, height: h, ...extra }}>
      <svg width={w} height={h} style={{ position: "absolute" }}><polygon points={pts.join(" ")} fill={color} /></svg>
      <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", textAlign: "center", fontFamily: "Jua", fontSize: size, color: "#1d1d1d", lineHeight: 1.05, whiteSpace: "pre-line" }}>{text}</div>
    </div>
  );
  const g = f - at, EL = P.echoLen;
  return (
    <>
      {EL > 0 && g < EL && shape({ transform: `scale(${lerp(f, at, at + EL, P.echoScale, 1)}) rotate(${rot}deg)`, opacity: lerp(f, at, at + EL, P.echoOp, 0) })}
      {shape({ transform: `scale(${body}) rotate(${rot}deg)`, filter: "drop-shadow(0 5px 6px rgba(0,0,0,0.3))" })}
    </>
  );
};

// ── 손글씨 주석(좌→우 와이프) ───────────────────────────────────────────
// ── 손글씨 주석: 텍스트 팝(크게→작게, 가로블러) ──────────────────────────
/** 텍스트 팝 곡선 공통 변수(Annot·Onoma) */
const textPopShape = {
  popLen: num(7, 1, 30, 1, "팝 길이", "timing", "f"),
  popFrom: num(1.25, 0.2, 3, 0.05, "팝 시작 크기(배)", "motion"),
  fadeLen: num(2, 1, 20, 1, "페이드인 길이", "timing", "f"),
  popBlur: num(8, 0, 40, 1, "가로 블러", "look", "px"),
};
const tpO = (P: { popLen: number; popFrom: number; fadeLen: number; popBlur: number }): TextPopO => ({ len: P.popLen, from: P.popFrom, opLen: P.fadeLen, blur: P.popBlur });
export const AnnotParams = z.object({
  ...textPopShape,
  strokeW: num(12, 0, 30, 1, "흰 외곽선 두께", "size", "px"),
  rot: num(-4, -30, 30, 1, "기울기", "motion", "°"),
  size: num(60, 24, 140, 1, "글자 크기", "size", "px"),
  color: col("#1b1b1b", "글자 색"),
});
export type AnnotP = z.infer<typeof AnnotParams>;
export const Annot: React.FC<{ text: string; x: number; y: number; at: number; size?: number; color?: string; rot?: number; p?: Partial<AnnotP> }> = ({ text, x, y, at, size, color, rot, p }) => {
  const P = def(AnnotParams, { ...pick({ size, color, rot }), ...p });
  const f = useCurrentFrame();
  if (f < at) return null;
  const { s, op, blur } = textPop(f, at, tpO(P));
  return (
    <div style={{ position: "absolute", left: x, top: y, transform: `rotate(${P.rot}deg) scale(${s})`, transformOrigin: "0% 50%", opacity: op, filter: `blur(${blur / 3}px) drop-shadow(0 3px 3px rgba(0,0,0,0.25))`, fontFamily: "Yeonsung, 'Songti SC', serif", fontSize: P.size, color: P.color, WebkitTextStroke: `${P.strokeW}px #fff`, paintOrder: "stroke fill", whiteSpace: "nowrap" }}>{text}</div>
  );
};

// ── 명찰(어두운 박스) ────────────────────────────────────────────────────
/** 필 스트레치(scaleX 0.3→1.06→1.0 + 가로블러) 공통 변수(NameTag·ElbowCallout) */
const stretchShape = {
  stretchLen: num(4, 1, 20, 1, "펼침 길이", "timing", "f"),
  stretchFrom: num(0.3, 0, 1, 0.05, "시작 가로 비율", "motion"),
  stretchOver: num(0.06, 0, 0.4, 0.01, "오버슈트 크기(배)", "motion"),
  stretchBlur: num(10, 0, 40, 1, "가로 블러", "look", "px"),
};
const stretch = (f: number, a: number, P: { stretchLen: number; stretchFrom: number; stretchOver: number; stretchBlur: number }, e: (t: number) => number = Easing.linear) => ({
  sx: kf(f, a, [0, P.stretchLen * 0.75, P.stretchLen], [P.stretchFrom, 1 + P.stretchOver, 1.0], e),
  blur: kf(f, a, [0, P.stretchLen], [P.stretchBlur, 0]),
});
export const NameTagParams = z.object({
  ...stretchShape,
  outLen: num(6, 1, 30, 1, "퇴장 페이드 길이", "timing", "f"),
  size: num(50, 20, 120, 1, "글자 크기", "size", "px"),
  bgColor: col("rgba(38,38,38,0.92)", "박스 색"),
  textColor: col("#fff", "글자 색"),
});
export type NameTagP = z.infer<typeof NameTagParams>;
export const NameTag: React.FC<{ text: string; x: number; y: number; at: number; size?: number; out?: number; p?: Partial<NameTagP> }> = ({ text, x, y, at, size, out, p }) => {
  const P = def(NameTagParams, { ...pick({ size }), ...p });
  const f = useCurrentFrame();
  if (f < at || (out !== undefined && f > out + P.outLen)) return null;
  const { sx, blur } = stretch(f, at, P, Easing.out(Easing.quad));
  const o = out !== undefined ? lerp(f, out, out + P.outLen, 1, 0) : 1;
  return (
    <div style={{ position: "absolute", left: x, top: y, transform: `scaleX(${sx})`, transformOrigin: "0% 50%", opacity: o, filter: `blur(${blur / 3}px)`, background: P.bgColor, color: P.textColor, fontFamily: "Yeonsung, 'Songti SC', serif", fontSize: P.size, padding: "10px 26px 4px", borderRadius: 999, boxShadow: "0 6px 10px rgba(0,0,0,0.35)", whiteSpace: "nowrap" }}>{hz(text)}</div>
  );
};

// ── 인용 박스 ───────────────────────────────────────────────────────────
// ── 인용 박스: 다크 바 + 텍스트 블러 20→0(10f) + 따옴표가 바깥으로 벌어짐 [ref 373.7s]
export const QuoteBoxParams = z.object({
  fadeLen: num(5, 1, 30, 1, "박스 페이드인 길이", "timing", "f"),
  blurLen: num(10, 1, 40, 1, "글자 블러 해제 길이", "timing", "f"),
  blurFrom: num(20, 0, 60, 1, "글자 시작 블러", "look", "px"),
  quoteDelay: num(2, 0, 20, 1, "따옴표 등장 지연", "timing", "f"),
  spreadLen: num(10, 1, 40, 1, "따옴표 벌어짐 길이", "timing", "f"),
  spreadDist: num(40, 0, 200, 2, "따옴표 벌어짐 거리", "motion", "px"),
  fontSize: num(54, 24, 100, 1, "글자 크기", "size", "px"),
  quoteSize: num(150, 40, 300, 5, "따옴표 크기", "size", "px"),
  boxColor: col("rgba(43,43,43,0.8)", "박스 색"),
});
export type QuoteBoxP = z.infer<typeof QuoteBoxParams>;
export const QuoteBox: React.FC<{ text: string; x: number; y: number; at: number; w?: number; p?: Partial<QuoteBoxP> }> = ({ text, x, y, at, w = 1100, p }) => {
  const P = def(QuoteBoxParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const op = lerp(f, at, at + P.fadeLen, 0, 1);
  const tb = lerp(f, at, at + P.blurLen, P.blurFrom, 0, Easing.out(Easing.quad));
  const qd = P.quoteDelay;
  const spread = lerp(f, at + qd, at + qd + P.spreadLen, -P.spreadDist, 0, QUART_OUT);
  const q = (c: string, side: React.CSSProperties, dir: number) => <div style={{ position: "absolute", fontFamily: "Georgia, serif", fontSize: P.quoteSize, color: "#fff", lineHeight: 1, ...side, transform: `translateX(${-dir * spread}px)`, opacity: lerp(f, at + qd, at + qd + 6, 0, 1) }}>{c}</div>;
  return (
    <div style={{ position: "absolute", left: x - w / 2, top: y, width: w, opacity: op }}>
      <div style={{ background: P.boxColor, borderRadius: 18, padding: "34px 70px 26px", color: "#fff", fontFamily: "NeoHv", fontSize: P.fontSize, textAlign: "center", lineHeight: 1.3, whiteSpace: "pre-line" }}>
        <span style={{ filter: `blur(${tb}px)`, display: "inline-block" }}>{text}</span>
      </div>
      {q("“", { left: -46, top: -58 }, -1)}{q("”", { right: -46, top: -58 }, 1)}
    </div>
  );
};

// ── 방사형 광선 + 반짝이 ────────────────────────────────────────────────
export const Rays: React.FC<{ at?: number; color?: string; opacity?: number; cx?: string; cy?: string }> = ({ at = 0, color = "rgba(255,255,255,0.35)", opacity = 1, cx = "50%", cy = "50%" }) => {
  const f = useCurrentFrame();
  const op = lerp(f, at, at + 8, 0, opacity);
  const r = (f - at) * 0.25;
  return <AbsoluteFill style={{ opacity: op, background: `repeating-conic-gradient(from ${r}deg at ${cx} ${cy}, ${color} 0deg 5deg, transparent 5deg 15deg)`, WebkitMaskImage: `radial-gradient(circle at ${cx} ${cy}, #000 0%, #000 25%, transparent 75%)` }} />;
};

// ── 4각 금별 반짝이: 3~4f 스태거 팝 → 20f 주기 트윙클, #F5C518 [ref 355s·737s]
export const SparklesParams = z.object({
  stagger: num(4, 0, 20, 1, "스태거 간격", "timing", "f"),
  popLen: num(4, 1, 20, 1, "팝 길이", "timing", "f"),
  twinklePeriod: num(20, 2, 80, 1, "트윙클 주기", "timing", "f"),
  twinkleMin: num(0.35, 0, 1, 0.05, "트윙클 최소 크기(배)", "motion"),
  sizeMul: num(1, 0.2, 3, 0.05, "별 크기(배)", "size"),
  color: col("#F5C518", "별 색"),
});
export type SparklesP = z.infer<typeof SparklesParams>;
export const Sparkles: React.FC<{ pts: [number, number, number][]; at: number; color?: string; p?: Partial<SparklesP> }> = ({ pts, at, color, p }) => {
  const P = def(SparklesParams, { ...pick({ color }), ...p });
  const f = useCurrentFrame();
  if (f < at) return null;
  return (
    <AbsoluteFill>
      {pts.map(([x, y, sz0], i) => {
        const sz = sz0 * P.sizeMul;
        const a0 = at + i * P.stagger;
        if (f < a0) return null;
        const g = f - a0, PL = P.popLen;
        const pop = kf(f, a0, [0, PL], [0, 1], Easing.out(Easing.quad));
        const tw = g < PL ? 1 : P.twinkleMin + (1 - P.twinkleMin) * Math.abs(Math.sin(((g - PL) / P.twinklePeriod) * Math.PI));
        return (
          <svg key={i} width={sz} height={sz} viewBox="-50 -50 100 100" style={{ position: "absolute", left: x - sz / 2, top: y - sz / 2, transform: `scale(${pop * tw})` }}>
            <path d="M0,-50 C6,-8 8,-6 50,0 C8,6 6,8 0,50 C-6,8 -8,6 -50,0 C-8,-6 -6,-8 0,-50Z" fill={P.color} />
          </svg>
        );
      })}
    </AbsoluteFill>
  );
};

// ── 배경 패턴 ───────────────────────────────────────────────────────────
export const WaveBgParams = z.object({
  scale: num(1, 0.3, 4, 0.05, "물결 무늬 크기(배)", "size"),
  lineW: num(3, 0.5, 12, 0.5, "선 두께", "size", "px"),
  base: col("#1c1c1c", "바탕 색"),
  line: col("#2b2b2b", "선 색"),
});
export type WaveBgP = z.infer<typeof WaveBgParams>;
export const WaveBg: React.FC<{ base?: string; line?: string; p?: Partial<WaveBgP> }> = ({ base, line, p }) => {
  const P = def(WaveBgParams, { ...pick({ base, line }), ...p });
  const k = P.scale;
  return (
    <AbsoluteFill style={{ background: P.base }}>
      <svg width="100%" height="100%">
        <defs>
          <pattern id="seigaiha" width={80 * k} height={40 * k} patternUnits="userSpaceOnUse">
            {[0, 40, 80].map((cx) => [36, 27, 18, 9].map((r) => <circle key={`${cx}-${r}`} cx={cx * k} cy={40 * k} r={r * k} fill="none" stroke={P.line} strokeWidth={P.lineW} />))}
            {[40].map((cx) => [36, 27, 18, 9].map((r) => <circle key={`b${cx}-${r}`} cx={cx * k} cy={0} r={r * k} fill="none" stroke={P.line} strokeWidth={P.lineW} />))}
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#seigaiha)" />
      </svg>
    </AbsoluteFill>
  );
};

export const CloudBgParams = z.object({
  scale: num(1, 0.3, 4, 0.05, "구름 무늬 크기(배)", "size"),
  lineW: num(6, 1, 20, 0.5, "선 두께", "size", "px"),
  vignette: num(0.45, 0, 1, 0.05, "가장자리 어둡기", "look"),
  base: col("#B21F28", "바탕 색"),
  line: col("#C8353C", "선 색"),
});
export type CloudBgP = z.infer<typeof CloudBgParams>;
export const CloudBg: React.FC<{ base?: string; line?: string; p?: Partial<CloudBgP> }> = ({ base, line, p }) => {
  const P = def(CloudBgParams, { ...pick({ base, line }), ...p });
  const k = P.scale;
  return (
    <AbsoluteFill style={{ background: P.base }}>
      <svg width="100%" height="100%">
        <defs>
          <pattern id="clouds" width={260 * k} height={170 * k} patternUnits="userSpaceOnUse">
            <g transform={k === 1 ? undefined : `scale(${k})`}>
              {[[60, 60], [190, 140]].map(([x, y], i) => (
                <g key={i} fill="none" stroke={P.line} strokeWidth={P.lineW / k} strokeLinecap="round">
                  <path d={`M${x - 55},${y + 10} q15,-35 45,-18 q10,-30 40,-10 q25,-8 25,18`} />
                  <path d={`M${x - 20},${y + 10} a14,14 0 1,1 14,-14`} />
                  <path d={`M${x + 22},${y + 6} a10,10 0 1,0 -10,-10`} />
                  <path d={`M${x - 55},${y + 10} h110`} />
                </g>
              ))}
            </g>
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#clouds)" />
      </svg>
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 45%, transparent 40%, rgba(60,0,0,${P.vignette}) 100%)` }} />
    </AbsoluteFill>
  );
};

// ── 옛 종이 질감(흑백 사료 위) ───────────────────────────────────────────
export const PaperOverlayParams = z.object({
  strength: num(1, 0, 2, 0.05, "전체 세기(배)", "look"),
  fiberOp: num(0.55, 0, 1, 0.05, "얼룩 질감 불투명도", "look"),
  fiberFreq: num(0.012, 0.002, 0.08, 0.001, "얼룩 크기(작을수록 큼)", "size"),
  speckOp: num(0.8, 0, 1, 0.05, "잡티 불투명도", "look"),
  vignette: num(0.55, 0, 1, 0.05, "가장자리 번짐", "look"),
});
export type PaperOverlayP = z.infer<typeof PaperOverlayParams>;
export const PaperOverlay: React.FC<{ strength?: number; p?: Partial<PaperOverlayP> }> = ({ strength, p }) => {
  const P = def(PaperOverlayParams, { ...pick({ strength }), ...p });
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <svg width="100%" height="100%" style={{ position: "absolute", mixBlendMode: "multiply", opacity: P.fiberOp * P.strength }}>
        <filter id="paper"><feTurbulence type="fractalNoise" baseFrequency={String(P.fiberFreq)} numOctaves={4} seed={7} /><feColorMatrix values="0 0 0 0 0.93  0 0 0 0 0.88  0 0 0 0 0.78  0 0 0 -1.2 1.25" /></filter>
        <rect width="100%" height="100%" filter="url(#paper)" />
      </svg>
      <svg width="100%" height="100%" style={{ position: "absolute", mixBlendMode: "multiply", opacity: P.speckOp * P.strength }}>
        <filter id="specks"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={1} seed={3} /><feColorMatrix values="0 0 0 0 0.1  0 0 0 0 0.08  0 0 0 0 0.06  0 0 0 -9 5.6" /></filter>
        <rect width="100%" height="100%" filter="url(#specks)" />
      </svg>
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 50%, transparent 55%, rgba(80,60,40,${P.vignette}) 100%)` }} />
    </AbsoluteFill>
  );
};

// ── 전역 필름 그레인 ────────────────────────────────────────────────────
// ── 그레인: 레퍼런스는 프레임 간 차분이 0에 가까운 **정적 종이 질감** → 시드 고정 ──
export const GrainParams = z.object({
  opacity: num(0.06, 0, 1, 0.01, "그레인 불투명도", "look"),
  freq: num(0.85, 0.1, 3, 0.05, "입자 촘촘함", "size"),
  octaves: num(2, 1, 6, 1, "입자 디테일 단계", "look"),
  animate: flag(false, "프레임마다 입자 바뀜(무빙 그레인)", "look"),
});
export type GrainP = z.infer<typeof GrainParams>;
export const Grain: React.FC<{ opacity?: number; p?: Partial<GrainP> }> = ({ opacity, p }) => {
  const P = def(GrainParams, { ...pick({ opacity }), ...p });
  const f = useCurrentFrame();
  const seed = P.animate ? 4 + (f % 97) : 4;
  return (
    <AbsoluteFill style={{ pointerEvents: "none", mixBlendMode: "overlay", opacity: P.opacity }}>
      <svg width="100%" height="100%">
        <filter id="grain-static"><feTurbulence type="fractalNoise" baseFrequency={String(P.freq)} numOctaves={P.octaves} seed={seed} stitchTiles="stitch" /><feColorMatrix type="saturate" values="0" /></filter>
        <rect width="100%" height="100%" filter="url(#grain-static)" />
      </svg>
    </AbsoluteFill>
  );
};

// ── 물음표 실루엣 ───────────────────────────────────────────────────────
export const QSilhouetteParams = z.object({
  damping: num(11, 2, 40, 1, "팝 스프링 감쇠", "motion"),
  stiffness: num(190, 30, 500, 5, "팝 스프링 강성", "motion"),
  s: num(1, 0.3, 3, 0.05, "크기(배)", "size"),
  color: col("#141414", "실루엣 색"),
  markColor: col("#fff", "물음표 색"),
});
export type QSilhouetteP = z.infer<typeof QSilhouetteParams>;
export const QSilhouette: React.FC<{ x: number; y: number; at: number; s?: number; p?: Partial<QSilhouetteP> }> = ({ x, y, at, s, p }) => {
  const P = def(QSilhouetteParams, { ...pick({ s }), ...p });
  const f = useCurrentFrame();
  if (f < at) return null;
  const k = popSpring(f, at, FPS, P.damping, P.stiffness) * P.s;
  const fid = `${Math.round(x)}-${Math.round(y)}-${at}`;
  return (
    <div style={{ position: "absolute", left: x, top: y, transform: `translate(-50%,-100%) scale(${k})`, transformOrigin: "50% 100%" }}>
      {/* 정체를 숨긴 인물: 세모지 캐스트(c2_boss) 상반신을 color 단색 실루엣으로(SVG feFlood 필터) + '?' 코드. 박스 420×480, 가슴 아래는 잘림 */}
      <svg width={0} height={0} style={{ position: "absolute" }}><filter id={`qsil-${fid}`} colorInterpolationFilters="sRGB"><feFlood floodColor={P.color} /><feComposite in2="SourceAlpha" operator="in" /></filter></svg>
      <div style={{ position: "relative", width: 420, height: 480, overflow: "hidden" }}>
        <div style={{ position: "absolute", inset: 0, filter: `url(#qsil-${fid})` }}>
          <CastHead cast="c2_boss" x={210} headTop={8} s={0.75} seed="qsil" />
        </div>
        <div style={{ position: "absolute", left: 0, top: 8 + (250 - 89) * 0.75 - 95, width: 420, height: 190, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "Jalnan", fontSize: 170, lineHeight: 1, color: P.markColor }}>?</div>
      </div>
    </div>
  );
};

// ── 화면 흔들림 ─────────────────────────────────────────────────────────
export const ShakeParams = z.object({
  amp: num(14, 0, 80, 1, "흔들림 세기", "motion", "px"),
  len: num(10, 1, 60, 1, "흔들림 길이", "timing", "f"),
  hold: num(1, 1, 8, 1, "위치 유지 프레임(클수록 둔탁)", "timing", "f"),
});
export type ShakeP = z.infer<typeof ShakeParams>;
export const useShake = (at: number, amp = 14, len = 10, hold = 1) => {
  const f = useCurrentFrame();
  const L = pos(len, 1);
  if (f < at || f > at + L) return "translate(0,0)";
  const d = 1 - (f - at) / L;
  const q = hold > 1 ? at + Math.floor((f - at) / hold) * hold : f;
  return `translate(${(random(`sx${q}`) - 0.5) * amp * 2 * d}px,${(random(`sy${q}`) - 0.5) * amp * 2 * d}px)`;
};

export const useVC = useVideoConfig;

// ── 레이어 씬: 배경 + 인물 레이어(원위치) + 전경 ─────────────────────────
// 까딱: 10프레임마다 세로 100%↔101% 핑퐁, AE 이지이지. 발밑 기준(사용자 사양)
// 깜빡임: 인물별 2.2~4초 간격으로 감은 눈 에셋을 3프레임 스왑(가끔 두 번)
// 패럴랙스: drift(px)를 씬 길이에 걸쳐 배경 -0.45 · 인물 0 · 전경 +0.5 배로 흘린다
export type LayerChar = { png: string; bbox: number[]; closed?: string };
export type LayerSpec = { bg: string; ar: number; chars: LayerChar[]; fg?: string[] };
const EASY_EASE = Easing.bezier(0.33, 0, 0.67, 1);
type BlinkO = { every: number; jitter: number; len: number; twice: number };
const blinkClosed = (f: number, seed: string, o: BlinkO = { every: 120, jitter: 90, len: 3, twice: 0.2 }) => {
  // 결정론적 스케줄: 누적 간격으로 깜빡임 시작 프레임 목록
  let t = Math.round(random(seed + "o") * 60) + 30;
  let i = 0;
  const L = o.len, step = (g: number) => Math.max(1, g);
  while (t <= f) {
    const dt = f - t;
    if (dt < L) return true;
    if (random(`${seed}d${i}`) < o.twice && dt >= 2 * L && dt < 3 * L) return true; // 두 번 깜빡
    t += step(o.every + Math.round(random(`${seed}g${i}`) * o.jitter));
    i++;
  }
  return false;
};
export const LayeredCoverParams = z.object({
  bobFrames: num(10, 1, 60, 1, "까딱 반주기(한 번 늘거나 줄어드는 길이)", "timing", "f"),
  bobAmp: num(1, 0, 6, 0.1, "까딱 세기(세로 늘어남)", "motion", "%"),
  blink: flag(true, "눈 깜빡임", "motion"),
  blinkEvery: num(120, 10, 400, 5, "깜빡임 최소 간격", "timing", "f"),
  blinkJitter: num(90, 0, 300, 5, "깜빡임 간격 랜덤 폭", "timing", "f"),
  blinkLen: num(3, 1, 12, 1, "눈 감는 길이", "timing", "f"),
  blinkTwice: num(0.2, 0, 1, 0.05, "두 번 깜빡일 확률", "motion"),
  drift: num(0, -600, 600, 10, "패럴랙스 흐름 거리", "motion", "px"),
  bgPar: num(0.45, 0, 2, 0.05, "배경 패럴랙스 배율", "motion"),
  fgPar: num(0.5, 0, 2, 0.05, "전경 패럴랙스 배율", "motion"),
});
export type LayeredCoverP = z.infer<typeof LayeredCoverParams>;
export const LayeredCover: React.FC<{ spec: LayerSpec; start?: number; dur?: number; drift?: number; p?: Partial<LayeredCoverP> }> = ({ spec, start = 0, dur = 150, drift, p }) => {
  const P = def(LayeredCoverParams, { ...pick({ drift }), ...p });
  const f = useCurrentFrame();
  const h = W * spec.ar;
  const pr = lerp(f, 0, dur, 0, 1, Easing.inOut(Easing.sin));
  const d = P.drift * (pr - 0.5);
  const BF = Math.max(1, Math.round(P.bobFrames)), BA = P.bobAmp / 100;
  const bo: BlinkO = { every: P.blinkEvery, jitter: P.blinkJitter, len: P.blinkLen, twice: P.blinkTwice };
  const layer = (x: number): React.CSSProperties => ({ position: "absolute", inset: 0, width: "100%", height: "100%", transform: `translateX(${x}px)` });
  return (
    <div style={{ position: "absolute", left: 0, top: (H - h) / 2, width: W, height: h }}>
      <Img src={src(spec.bg)} style={{ ...layer(-d * P.bgPar), inset: -40, width: W + 80, height: h + 80, left: -40, top: -40 }} />
      {spec.chars.map((c, ci) => {
        const [x0, , x1, y1] = c.bbox;
        const k = Math.max(0, f - start) + Math.floor(random(`bob-${c.png}`) * BF * 2);
        const seg = Math.floor(k / BF), t = (k % BF) / BF;
        const e = EASY_EASE(t);
        const sy = 1 + BA * (seg % 2 === 0 ? e : 1 - e);
        const closed = P.blink && c.closed && blinkClosed(f, c.png, bo);
        const st: React.CSSProperties = { position: "absolute", inset: 0, width: "100%", height: "100%", transformOrigin: `${((x0 + x1) / 2) * 100}% ${y1 * 100}%`, transform: `scaleY(${sy})` };
        return (
          <React.Fragment key={c.png}>
            <Img src={src(c.png)} style={{ ...st, opacity: closed ? 0 : 1 }} />
            {c.closed && <Img src={src(c.closed)} style={{ ...st, opacity: closed ? 1 : 0 }} />}
          </React.Fragment>
        );
      })}
      {(spec.fg || []).map((g) => <Img key={g} src={src(g)} style={layer(d * P.fgPar)} />)}
    </div>
  );
};

// ── 김: 반투명 흰 쐐기형 연기가 위로 넓어지며 흩어진다, 45f 루프, 알파 0.3→0.6→0 [ref 812s]
export const SteamParams = z.object({
  period: num(45, 6, 150, 1, "김 한 줄기 수명(루프)", "timing", "f"),
  n: num(3, 1, 10, 1, "김 줄기 수", "size"),
  rise: num(150, 0, 500, 5, "올라가는 높이", "motion", "px"),
  widen: num(70, 0, 200, 2, "퍼지는 폭", "size", "px"),
  sway: num(10, 0, 60, 1, "좌우 흔들림", "motion", "px"),
  blur: num(7, 0, 30, 0.5, "번짐", "look", "px"),
  peakOp: num(0.6, 0, 1, 0.05, "최대 불투명도", "look"),
  color: col("#fff", "김 색"),
});
export type SteamP = z.infer<typeof SteamParams>;
export const Steam: React.FC<{ x: number; y: number; s?: number; at?: number; n?: number; p?: Partial<SteamP> }> = ({ x, y, s = 1, at = 0, n, p }) => {
  const P = def(SteamParams, { ...pick({ n }), ...p });
  const f = useCurrentFrame();
  if (f < at) return null;
  const N = Math.max(1, Math.round(P.n)), T = pos(P.period, 1), pk = P.peakOp;
  return (
    <div style={{ position: "absolute", left: x - 70 * s, top: y - 220 * s, width: 140 * s, height: 220 * s, filter: `blur(${P.blur * s}px)` }}>
      {Array.from({ length: N }).map((_, i) => {
        const ph = ((f - at + i * (T / N)) % T) / T;
        const op = kf(ph, 0, [0, 0.25, 0.6, 1], [0, pk, (pk * 0.35) / 0.6, 0]);
        const w = (34 + P.widen * ph) * s, hh = (60 + 60 * ph) * s;
        const cx = 70 * s + Math.sin((f - at) / 11 + i * 2) * P.sway * s;
        return <div key={i} style={{ position: "absolute", left: cx - w / 2, top: 220 * s - 50 * s - ph * P.rise * s - hh / 2, width: w, height: hh, borderRadius: "50% 50% 45% 45%", background: P.color, opacity: op }} />;
      })}
    </div>
  );
};

// ── 효과 텍스트(의성어): 흰 채움 + 검정 외곽 6px, 크게→작게 팝 [ref 228.05s] ─────────
export const OnomaParams = z.object({
  ...textPopShape,
  life: num(40, 4, 150, 1, "표시 시간", "timing", "f"),
  outLen: num(6, 1, 30, 1, "퇴장 페이드 길이", "timing", "f"),
  wobAmt: num(2.5, 0, 20, 0.5, "흔들림 각도", "motion", "°"),
  wobSpeed: num(2.5, 0.5, 20, 0.5, "흔들림 속도(작을수록 빠름)", "timing", "f"),
  strokeW: num(12, 0, 30, 1, "외곽선 두께", "size", "px"),
  rot: num(-8, -45, 45, 1, "기울기", "motion", "°"),
  size: num(64, 24, 160, 1, "글자 크기", "size", "px"),
  fill: col("#fff", "글자 색"),
  stroke: col("#161616", "외곽선 색"),
});
export type OnomaP = z.infer<typeof OnomaParams>;
export const Onoma: React.FC<{ text: string; x: number; y: number; at: number; life?: number; size?: number; rot?: number; p?: Partial<OnomaP> }> = ({ text, x, y, at, life, size, rot, p }) => {
  const P = def(OnomaParams, { ...pick({ life, size, rot }), ...p });
  const f = useCurrentFrame();
  if (f < at || f > at + P.life) return null;
  const { s, op, blur } = textPop(f, at, tpO(P));
  const out = lerp(f, at + P.life - P.outLen, at + P.life, 1, 0);
  const wob = P.wobAmt * Math.sin((f - at) / P.wobSpeed);
  return (
    <div style={{ position: "absolute", left: x, top: y, transform: `scale(${s}) rotate(${P.rot + wob}deg)`, opacity: op * out, filter: `blur(${blur / 3}px)`, fontFamily: "Yeonsung, 'Songti SC', serif", fontSize: P.size, color: P.fill, WebkitTextStroke: `${P.strokeW}px ${P.stroke}`, paintOrder: "stroke fill", whiteSpace: "nowrap" }}>{text}</div>
  );
};

// ── 전환 오버레이 1: 컬러 플리커 라이트릭 19f (ref 303.3·410.5·593.0s 동일 템플릿) ─────
// 핑크 f0-2 → 원본 f3 → 핑크 f4-5 → 원본 f6 → 웜화이트 f7-12 감쇠 → f13 재상승 → f14 핑크화이트 피크(여기서 컷)
// → f15-17 오렌지 과노출 감쇠 → f18 정상.  컷 시점 = at + 14
export const FlickerLeakParams = z.object({
  intensity: num(1, 0, 1.5, 0.05, "빛 세기(배)", "look"),
  cx: num(80, 0, 100, 1, "빛 중심 가로 위치", "motion", "%"),
  cy: num(40, 0, 100, 1, "빛 중심 세로 위치", "motion", "%"),
  spread: num(45, 0, 100, 1, "빛 코어 크기", "size", "%"),
  pink: col("#F078AA", "핑크 플리커 색"),
  warm: col("#F8F0D4", "웜화이트 색"),
  peak: col("#FFD7E6", "피크(컷) 색"),
  orange: col("#F7AA5A", "오렌지 과노출 색"),
});
export type FlickerLeakP = z.infer<typeof FlickerLeakParams>;
export const FlickerLeak: React.FC<{ at: number; p?: Partial<FlickerLeakP> }> = ({ at, p }) => {
  const P = def(FlickerLeakParams, p);
  const f = useCurrentFrame();
  const g = f - at;
  if (g < 0 || g > 18) return null;
  const pink = P.pink, warm = P.warm, orange = P.orange;
  let col = pink, a = 0;
  if (g <= 2) { col = pink; a = [0.55, 0.42, 0.28][g]; }
  else if (g === 3 || g === 6) a = 0;
  else if (g <= 5) { col = pink; a = 0.45; }
  else if (g <= 12) { col = warm; a = kf(g, 7, [0, 5], [0.75, 0.35]); }
  else if (g === 13) { col = warm; a = 0.6; }
  else if (g === 14) { col = P.peak; a = 0.92; }
  else { col = orange; a = kf(g, 15, [0, 3], [0.6, 0]); }
  return <AbsoluteFill style={{ background: `radial-gradient(ellipse at ${P.cx}% ${P.cy}%, ${col} 0%, ${col} ${P.spread}%, transparent 110%)`, mixBlendMode: "screen", opacity: Math.min(1, a * P.intensity), pointerEvents: "none" }} />;
};

// ── 전환 오버레이 2: 노란 번 27f — 우측에서 번져 6f 램프 → 크림 3f(컷) → 18f 웜틴트 감쇠 [ref 360.05·824.9s]
export const YellowBurstParams = z.object({
  rampLen: num(6, 1, 30, 1, "번지는 길이", "timing", "f"),
  holdTo: num(9, 1, 40, 1, "꽉 찬 상태 유지(컷 지점까지)", "timing", "f"),
  fadeLen: num(18, 1, 60, 1, "웜틴트 감쇠 길이", "timing", "f"),
  reach: num(170, 50, 300, 5, "번짐 반경", "size", "%"),
  tailOp: num(0.85, 0, 1, 0.05, "감쇠 시작 불투명도", "look"),
  cy: num(50, 0, 100, 1, "번짐 시작 세로 위치", "motion", "%"),
  core: col("#fff8e0", "중심 크림 색"),
  mid: col("#fff4a0", "노랑 색"),
  edge: col("#ffb000", "가장자리 주황 색"),
});
export type YellowBurstP = z.infer<typeof YellowBurstParams>;
export const YellowBurst: React.FC<{ at: number; p?: Partial<YellowBurstP> }> = ({ at, p }) => {
  const P = def(YellowBurstParams, p);
  const f = useCurrentFrame();
  const g = f - at, HT = P.holdTo;
  if (g < 0 || g > HT + P.fadeLen) return null;
  const r = kf(g, 0, [0, P.rampLen], [0, P.reach], Easing.out(Easing.quad));
  const a = g <= HT ? 1 : kf(g, HT, [0, P.fadeLen], [P.tailOp, 0]);
  return <AbsoluteFill style={{ background: `radial-gradient(circle at 100% ${P.cy}%, ${P.core} 0%, ${P.mid} ${r * 0.45}%, ${P.edge} ${r * 0.8}%, transparent ${r}%)`, opacity: a, mixBlendMode: g <= HT ? "normal" : "screen", pointerEvents: "none" }} />;
};

// ── 전환 오버레이 3: 만화 연기 40f — 하단에서 5f 덮고 5f 홀드(컷) → 15f 걷힘 → 잔여 15f [ref 490.83s]
export const SmokeWipeParams = z.object({
  inLen: num(5, 1, 30, 1, "덮는 길이", "timing", "f"),
  holdLen: num(5, 0, 30, 1, "덮은 채 유지(컷)", "timing", "f"),
  outLen: num(15, 1, 60, 1, "걷히는 길이", "timing", "f"),
  tailLen: num(15, 1, 60, 1, "잔여 페이드 길이", "timing", "f"),
  puffs: num(22, 6, 40, 1, "연기 덩어리 수", "size"),
  puffSize: num(260, 80, 500, 10, "연기 덩어리 크기", "size", "px"),
  wobble: num(0.15, 0, 0.5, 0.01, "몽글거림 세기", "motion"),
  color: col("#A8A29E", "연기 색"),
  highlight: col("#EDEBE8", "하이라이트 선 색"),
});
export type SmokeWipeP = z.infer<typeof SmokeWipeParams>;
export const SmokeWipe: React.FC<{ at: number; p?: Partial<SmokeWipeP> }> = ({ at, p }) => {
  const P = def(SmokeWipeParams, p);
  const f = useCurrentFrame();
  const g = f - at;
  const t1 = P.inLen, t2 = t1 + P.holdLen, t3 = t2 + P.outLen, END = t3 + P.tailLen;
  if (g < 0 || g > END) return null;
  const rise = g <= t1 ? kf(g, 0, [0, t1], [1300, 0], QUART_OUT) : g <= t2 ? 0 : kf(g, t2, [0, P.outLen], [0, -1500], Easing.in(Easing.quad));
  const fadeTail = kf(g, t3, [0, P.tailLen], [1, 0]);
  const puffs = Array.from({ length: Math.round(P.puffs) }).map((_, i) => ({ x: (i % 6) * 380 - 60 + random(`px${i}`) * 120, y: Math.floor(i / 6) * 330 + random(`py${i}`) * 120, r: P.puffSize + random(`pr${i}`) * 180 }));
  return (
    <AbsoluteFill style={{ transform: `translateY(${rise}px)`, opacity: g > t3 ? fadeTail : 1, pointerEvents: "none" }}>
      <svg width={W} height={H + 600} style={{ position: "absolute", top: -100 }}>
        {puffs.map((pf, i) => (
          <g key={i} transform={`translate(${pf.x},${pf.y}) scale(${1 + P.wobble * Math.sin(g / 6 + i)})`}>
            <circle r={pf.r} fill={P.color} />
            <path d={`M${-pf.r * 0.55},${-pf.r * 0.35} a${pf.r * 0.6},${pf.r * 0.6} 0 0 1 ${pf.r * 0.7},${-pf.r * 0.3}`} stroke={P.highlight} strokeWidth={14} fill="none" strokeLinecap="round" />
          </g>
        ))}
      </svg>
    </AbsoluteFill>
  );
};

// ── 색종이 버스트: 40개 4색, 하단 중앙에서 위로 터져 scaleX 플립하며 낙하, 60f [ref 317.3s] ─
export const ConfettiParams = z.object({
  n: num(40, 1, 200, 1, "색종이 개수", "size"),
  spread: num(1.6, 0, 6.28, 0.05, "퍼지는 각도 폭(rad)", "motion"),
  speed: num(38, 0, 120, 1, "최소 발사 속도", "motion", "px/f"),
  speedRand: num(26, 0, 100, 1, "속도 랜덤 폭", "motion", "px/f"),
  gravity: num(0.9, 0, 4, 0.05, "중력", "motion"),
  size: num(15, 4, 60, 1, "색종이 크기", "size", "px"),
  flipSpeed: num(3, 0.5, 20, 0.5, "뒤집힘 주기(작을수록 빠름)", "timing", "f"),
  spin: num(9, 0, 40, 1, "회전 속도", "motion", "°/f"),
  fadeAt: num(50, 1, 150, 1, "페이드 시작", "timing", "f"),
  life: num(70, 2, 200, 1, "수명", "timing", "f"),
});
export type ConfettiP = z.infer<typeof ConfettiParams>;
export const Confetti: React.FC<{ at: number; x?: number; y?: number; n?: number; p?: Partial<ConfettiP> }> = ({ at, x = W / 2, y = H * 0.85, n, p }) => {
  const P = def(ConfettiParams, { ...pick({ n }), ...p });
  const f = useCurrentFrame();
  const g = f - at;
  if (g < 0 || g > P.life) return null;
  const cols = ["#2FE0E0", "#3848E0", "#8A2BE2", "#E0209A", "#F5C518"];
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {Array.from({ length: Math.round(P.n) }).map((_, i) => {
        const ang = -Math.PI / 2 + (random(`ca${i}`) - 0.5) * P.spread;
        const v = P.speed + random(`cv${i}`) * P.speedRand;
        const t = g;
        const px = x + Math.cos(ang) * v * t * 0.9 + Math.sin(t / 5 + i) * 12;
        const py = y + Math.sin(ang) * v * t * 0.9 + P.gravity * t * t;
        const sz = P.size + random(`cs${i}`) * P.size;
        const flip = Math.cos(t / P.flipSpeed + i);
        return <div key={i} style={{ position: "absolute", left: px, top: py, width: sz, height: sz * 0.7, background: cols[i % cols.length], transform: `rotate(${i * 37 + t * P.spin}deg) scaleX(${flip})`, opacity: kf(g, 0, inc([0, Math.min(P.fadeAt, P.life - 0.001), P.life]), [1, 1, 0]) }} />;
      })}
    </AbsoluteFill>
  );
};

// ══ 추가 모션그래픽 기법 ══════════════════════════════════════════════════

// ── 부드러운 원형 글로우 + 퍼지는 링 펄스 (방사형 줄무늬 광선 대체) ─────────────
export const GlowPulseParams = z.object({
  fadeLen: num(10, 1, 40, 1, "글로우 페이드인", "timing", "f"),
  glowOp: num(0.75, 0, 1, 0.05, "글로우 중심 불투명도", "look"),
  glowMid: num(0.35, 0, 1, 0.05, "글로우 중간(38%) 불투명도", "look"),
  breathe: num(0.03, 0, 0.2, 0.005, "숨쉬기 크기 변화(배)", "motion"),
  breathePeriod: num(18, 2, 80, 1, "숨쉬기 속도(작을수록 빠름)", "timing", "f"),
  rings: num(2, 0, 8, 1, "링 개수", "size"),
  ringStagger: num(7, 0, 30, 1, "링 스태거 간격", "timing", "f"),
  ringLen: num(26, 2, 80, 1, "링 퍼짐 길이", "timing", "f"),
  ringW: num(14, 1, 40, 1, "링 시작 두께", "size", "px"),
  ringOp: num(0.8, 0, 1, 0.05, "링 시작 불투명도", "look"),
  r: num(520, 100, 1200, 10, "글로우 반지름", "size", "px"),
});
export type GlowPulseP = z.infer<typeof GlowPulseParams>;
export const GlowPulse: React.FC<{ x: number; y: number; at: number; r?: number; color?: string; rings?: number; p?: Partial<GlowPulseP> }> = ({ x, y, at, r: r0, color = "255,236,180", rings: rings0, p }) => {
  const P = def(GlowPulseParams, { ...pick({ r: r0, rings: rings0 }), ...p });
  const r = P.r, RL = P.ringLen;
  const f = useCurrentFrame();
  if (f < at) return null;
  const breathe = 1 + P.breathe * Math.sin((f - at) / P.breathePeriod);
  const op = lerp(f, at, at + P.fadeLen, 0, 1);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div style={{ position: "absolute", left: x - r, top: y - r, width: r * 2, height: r * 2, borderRadius: "50%", opacity: op, transform: `scale(${breathe})`, background: `radial-gradient(circle, rgba(${color},${P.glowOp}) 0%, rgba(${color},${P.glowMid}) 38%, rgba(${color},0) 70%)` }} />
      {Array.from({ length: Math.round(P.rings) }).map((_, i) => {
        const g = f - at - i * P.ringStagger;
        if (g < 0 || g > RL) return null;
        const rr = lerp(g, 0, RL, 60, r * 0.95, Easing.out(Easing.cubic));
        return <div key={i} style={{ position: "absolute", left: x - rr, top: y - rr, width: rr * 2, height: rr * 2, borderRadius: "50%", border: `${lerp(g, 0, RL, P.ringW, 2)}px solid rgba(255,255,255,${lerp(g, 0, RL, P.ringOp, 0)})` }} />;
      })}
    </AbsoluteFill>
  );
};

// ── 뒷모습→앞모습 뒤집기 턴 [ref 271.2s]: 뒤 scaleX 1→0 (4f easeIn) → 앞 0→1 (4f easeOut) ──
export const FlipTurnParams = z.object({
  slideLen: num(18, 1, 60, 1, "슬라이드 입장 길이", "timing", "f"),
  slideDist: num(1150, 0, 2400, 10, "슬라이드 거리", "motion", "px"),
  flipHalf: num(4, 1, 20, 1, "뒤집기 반쪽 길이(접힘·펼침 각각)", "timing", "f"),
  outLen: num(7, 1, 30, 1, "퇴장 길이", "timing", "f"),
  outBack: num(1.5, 0, 4, 0.1, "퇴장 백 이징 세기", "motion"),
  glow: flag(true, "흰 글로우 테두리", "look"),
});
export type FlipTurnP = z.infer<typeof FlipTurnParams>;
export const FlipTurn: React.FC<{ back: string; front: string; x: number; y: number; w: number; at: number; flipAt: number; out?: number; p?: Partial<FlipTurnP> }> = ({ back, front, x, y, w, at, flipAt, out, p }) => {
  const P = def(FlipTurnParams, p);
  const f = useCurrentFrame();
  if (f < at || (out !== undefined && f > out + P.outLen + 1)) return null;
  const tx = lerp(f, at, at + P.slideLen, -P.slideDist, 0, QUART_OUT);
  const FH = P.flipHalf;
  const sb = f < flipAt ? 1 : lerp(f, flipAt, flipAt + FH, 1, 0, Easing.in(Easing.quad));
  const sf = f < flipAt + FH ? 0 : lerp(f, flipAt + FH, flipAt + 2 * FH, 0, 1, Easing.out(Easing.quad));
  const so = out !== undefined ? lerp(f, out, out + P.outLen, 1, 0, Easing.in(Easing.back(P.outBack))) : 1;
  const st = (sx: number): React.CSSProperties => ({ position: "absolute", left: x, top: y, width: w, transform: `translateX(${tx}px) scale(${sx * so},${so})`, transformOrigin: "50% 100%", filter: P.glow ? GLOW : undefined });
  return <>{sb > 0.01 && <Img src={src(back)} style={st(sb)} />}{sf > 0.01 && <Img src={src(front)} style={st(sf)} />}</>;
};

// ── 스포트라이트 딤 [ref 751s]: 주인공 사각형만 밝고 나머지 55% 어둡게, 6f 페이드 ──────
export const SpotlightParams = z.object({
  fadeLen: num(6, 1, 30, 1, "딤 페이드인 길이", "timing", "f"),
  outLen: num(6, 1, 30, 1, "딤 페이드아웃 길이", "timing", "f"),
  dim: num(0.5, 0, 1, 0.05, "주변 어둡기", "look"),
  radius: num(36, 0, 300, 2, "밝은 영역 모서리 둥글기", "size", "px"),
  soft: num(0, 0, 200, 2, "경계 부드러움", "look", "px"),
});
export type SpotlightP = z.infer<typeof SpotlightParams>;
export const Spotlight: React.FC<{ rect: [number, number, number, number]; at: number; out?: number; radius?: number; p?: Partial<SpotlightP> }> = ({ rect, at, out, radius, p }) => {
  const P = def(SpotlightParams, { ...pick({ radius }), ...p });
  const f = useCurrentFrame();
  if (f < at || (out !== undefined && f > out + P.outLen)) return null;
  const op = lerp(f, at, at + P.fadeLen, 0, 1) * (out !== undefined ? lerp(f, out, out + P.outLen, 1, 0) : 1);
  const [x, y, w, h] = rect;
  return <div style={{ position: "absolute", left: x, top: y, width: w, height: h, borderRadius: P.radius, boxShadow: P.soft > 0 ? `0 0 ${P.soft}px 4000px rgba(0,0,0,${P.dim})` : `0 0 0 4000px rgba(0,0,0,${P.dim})`, opacity: op, pointerEvents: "none" }} />;
};

// ── 이름표 + 곡선 화살표 [ref 751s]: 박스 4f → 글자 와이프 6f(+3f) → 화살표 드로우 10f(+5f) ──
export const ArrowTagParams = z.object({
  boxLen: num(4, 1, 20, 1, "박스 페이드인 길이", "timing", "f"),
  textDelay: num(3, 0, 20, 1, "글자 와이프 지연", "timing", "f"),
  textLen: num(6, 1, 30, 1, "글자 와이프 길이", "timing", "f"),
  arrowDelay: num(5, 0, 30, 1, "화살표 드로우 지연", "timing", "f"),
  arrowLen: num(10, 1, 40, 1, "화살표 드로우 길이", "timing", "f"),
  outLen: num(6, 1, 30, 1, "퇴장 페이드 길이", "timing", "f"),
  lineW: num(5, 1, 20, 0.5, "화살표 두께", "size", "px"),
  size: num(54, 20, 120, 1, "글자 크기", "size", "px"),
  boxColor: col("#302e2f", "박스 색"),
  lineColor: col("#fff", "화살표 색"),
});
export type ArrowTagP = z.infer<typeof ArrowTagParams>;
export const ArrowTag: React.FC<{ text: string; x: number; y: number; at: number; path: string; head: [number, number, number]; size?: number; out?: number; p?: Partial<ArrowTagP> }> = ({ text, x, y, at, path, head, size, out, p }) => {
  const P = def(ArrowTagParams, { ...pick({ size }), ...p });
  const f = useCurrentFrame();
  if (f < at || (out !== undefined && f > out + P.outLen)) return null;
  const o = out !== undefined ? lerp(f, out, out + P.outLen, 1, 0) : 1;
  const box = lerp(f, at, at + P.boxLen, 0, 1);
  const tk = lerp(f, at + P.textDelay, at + P.textDelay + P.textLen, 0, 100);
  const ak = lerp(f, at + P.arrowDelay, at + P.arrowDelay + P.arrowLen, 0, 1, Easing.out(Easing.quad));
  const [hx, hy, ha] = head;
  return (
    <AbsoluteFill style={{ opacity: o, pointerEvents: "none" }}>
      <svg width={W} height={H} style={{ position: "absolute" }}>
        <path d={path} pathLength={1} stroke={P.lineColor} strokeWidth={P.lineW} fill="none" strokeLinecap="round" strokeDasharray={1} strokeDashoffset={1 - ak} style={{ filter: "drop-shadow(0 2px 3px rgba(0,0,0,0.5))" }} />
        {ak > 0.97 && <path d="M-16,-11 L0,0 L-16,11" transform={`translate(${hx},${hy}) rotate(${ha})`} stroke={P.lineColor} strokeWidth={P.lineW} fill="none" strokeLinecap="round" strokeLinejoin="round" />}
      </svg>
      <div style={{ position: "absolute", left: x, top: y, opacity: box, background: P.boxColor, borderRadius: 8, padding: "12px 28px 6px", boxShadow: "0 6px 12px rgba(0,0,0,0.4)" }}>
        <div style={{ fontFamily: "Yeonsung, 'Songti SC', serif", fontSize: P.size, color: "#fff", whiteSpace: "nowrap", clipPath: `inset(0 ${100 - tk}% 0 0)` }}>{text}</div>
      </div>
    </AbsoluteFill>
  );
};

// ── 재료 아이콘: 순차 팝(0.2→1.1→1.0, 6f, 블러) → 중심으로 빨려 들어감(8f, 3f 스태거) [ref 766~771s] ──
export const IconPopParams = z.object({
  popLen: num(6, 1, 30, 1, "팝 길이", "timing", "f"),
  popFrom: num(0.2, 0, 1.5, 0.05, "팝 시작 크기(배)", "motion"),
  popOver: num(0.1, 0, 0.5, 0.01, "오버슈트 크기(배)", "motion"),
  popBlur: num(6, 0, 40, 1, "팝 블러", "look", "px"),
  suckLen: num(8, 1, 40, 1, "빨려 들어가는 길이", "timing", "f"),
  suckStagger: num(3, 0, 20, 1, "빨려 들어감 스태거", "timing", "f"),
  suckShrink: num(0.8, 0, 1, 0.05, "빨려 들며 줄어듦(비율)", "motion"),
  size: num(190, 60, 400, 5, "아이콘 크기", "size", "px"),
  labelSize: num(40, 16, 80, 1, "라벨 글자 크기", "size", "px"),
});
export type IconPopP = z.infer<typeof IconPopParams>;
export const IconPop: React.FC<{ icon: React.ReactNode; label: string; x: number; y: number; at: number; suckAt?: number; to?: [number, number]; idx?: number; size?: number; p?: Partial<IconPopP> }> = ({ icon, label, x, y, at, suckAt, to, idx = 0, size: size0, p }) => {
  const P = def(IconPopParams, { ...pick({ size: size0 }), ...p });
  const size = P.size, PL = P.popLen;
  const f = useCurrentFrame();
  if (f < at) return null;
  let s = kf(f, at, [0, (PL * 2) / 3, PL], [P.popFrom, 1 + P.popOver, 1.0]);
  const blur = kf(f, at, [0, PL / 2], [P.popBlur, 0]);
  let dx = 0, dy = 0, op = 1;
  if (suckAt !== undefined && to) {
    const a0 = suckAt + idx * P.suckStagger;
    if (f > a0 + P.suckLen) return null;
    const k = lerp(f, a0, a0 + P.suckLen, 0, 1, Easing.in(Easing.cubic));
    dx = (to[0] - x) * k; dy = (to[1] - y) * k; s *= 1 - P.suckShrink * k; op = 1 - k;
  }
  return (
    <div style={{ position: "absolute", left: x - size / 2, top: y - size / 2, width: size, transform: `translate(${dx}px,${dy}px) scale(${s})`, opacity: op, filter: `blur(${blur}px) drop-shadow(0 6px 8px rgba(0,0,0,0.35))`, display: "flex", flexDirection: "column", alignItems: "center" }}>
      <div style={{ width: size, height: size }}>{icon}</div>
      <div style={{ marginTop: -6, background: "#1f1f1f", color: "#fff", fontFamily: "Yeonsung, 'Songti SC', serif", fontSize: P.labelSize, padding: "6px 20px 0", borderRadius: 8 }}>{label}</div>
    </div>
  );
};
/** 세모지 캐러멜 방울(caramel_drop_icon) — 부모 박스에 맞춤 */
export const IconCaramel = () => (
  <Img src={prop("caramel_drop_icon")} style={{ width: "100%", height: "100%", objectFit: "contain", padding: "4%", boxSizing: "border-box" }} />
);
/** 세모지 각설탕 3개(sugar_cubes_icon) — 부모 박스에 맞춤 */
export const IconSugar = () => (
  <Img src={prop("sugar_cubes_icon")} style={{ width: "100%", height: "100%", objectFit: "contain", padding: "6%", boxSizing: "border-box" }} />
);

// ── 에코 줌 타이틀 [ref 817.3s]: scale 1.8→1.0 (30f easeOutCubic) + 잔상 2장(4f·8f 지연, α.4/.2) ──
export const EchoTitleParams = z.object({
  zoomLen: num(30, 2, 90, 1, "줌 길이", "timing", "f"),
  zoomFrom: num(1.8, 0.2, 5, 0.05, "시작 크기(배)", "motion"),
  fadeLen: num(4, 1, 30, 1, "본체 페이드인", "timing", "f"),
  echoGap: num(4, 0, 20, 1, "잔상 간격", "timing", "f"),
  echoOp: num(0.4, 0, 1, 0.05, "첫 잔상 불투명도(둘째는 절반)", "look"),
  echoFade: num(10, 1, 40, 1, "잔상 사라짐 길이", "timing", "f"),
  size: num(120, 30, 260, 2, "글자 크기", "size", "px"),
  color: col("#2f3b2c", "글자 색"),
});
export type EchoTitleP = z.infer<typeof EchoTitleParams>;
export const EchoTitle: React.FC<{ text: string; x: number; y: number; at: number; size?: number; color?: string; font?: string; stroke?: string; p?: Partial<EchoTitleP> }> = ({ text, x, y, at, size, color, font = "Yeonsung", stroke, p }) => {
  const P = def(EchoTitleParams, { ...pick({ size, color }), ...p });
  const f = useCurrentFrame();
  if (f < at) return null;
  const ZL = P.zoomLen, EF = Math.min(P.echoFade, ZL);
  const layer = (d: number, a: number, key: string) => {
    const g = f - at - d;
    if (g < 0) return null;
    const sc = lerp(g, 0, ZL, P.zoomFrom, 1, Easing.out(Easing.cubic));
    const op = key === "m" ? lerp(g, 0, P.fadeLen, 0, 1) : a * lerp(g, ZL - EF, ZL, 1, 0);
    return <div key={key} style={{ position: "absolute", left: 0, right: 0, top: y, transform: `translateX(${x - W / 2}px) scale(${sc})`, textAlign: "center", fontFamily: font, fontSize: P.size, color: P.color, opacity: op, whiteSpace: "nowrap", WebkitTextStroke: stroke }}>{text}</div>;
  };
  return <>{layer(P.echoGap * 2, P.echoOp / 2, "e2")}{layer(P.echoGap, P.echoOp, "e1")}{layer(0, 1, "m")}</>;
};

// ── 점선 원 하이라이트: 스트로크 드로우 10f [ref 438~458s] ─────────────────────────
export const DashCircleParams = z.object({
  drawLen: num(10, 1, 60, 1, "그려지는 길이", "timing", "f"),
  outLen: num(6, 1, 30, 1, "퇴장 페이드 길이", "timing", "f"),
  dashes: num(28, 4, 80, 1, "점선 조각 수", "size"),
  dashRatio: num(0.6, 0.05, 1, 0.05, "조각 길이 비율(나머지는 틈)", "size"),
  lineW: num(6, 1, 24, 0.5, "선 두께", "size", "px"),
  color: col("#fff", "선 색"),
});
export type DashCircleP = z.infer<typeof DashCircleParams>;
export const DashCircle: React.FC<{ cx: number; cy: number; rx: number; ry: number; at: number; color?: string; out?: number; p?: Partial<DashCircleP> }> = ({ cx, cy, rx, ry, at, color, out, p }) => {
  // 점선을 개별 호 조각으로 그리고, 12시부터 시계방향으로 조각이 차례로 나타나게 한다(마스크·pathLength 미사용 — 헤드리스 렌더 호환)
  const P = def(DashCircleParams, { ...pick({ color }), ...p });
  const f = useCurrentFrame();
  if (f < at || (out !== undefined && f > out + P.outLen)) return null;
  const k = lerp(f, at, at + P.drawLen, 0, 1, Easing.out(Easing.quad));
  const o = out !== undefined ? lerp(f, out, out + P.outLen, 1, 0) : 1;
  const N = Math.round(P.dashes), pt = (a: number) => [cx + rx * Math.sin(a), cy - ry * Math.cos(a)];
  const segs = [];
  for (let i = 0; i < N; i++) {
    const a0 = (i / N) * Math.PI * 2, a1 = ((i + P.dashRatio) / N) * Math.PI * 2;
    const show = Math.min(1, Math.max(0, k * N - i));
    if (show <= 0) break;
    const am = a0 + (a1 - a0) * show;
    const d = Array.from({ length: 5 }).map((_, j) => pt(a0 + ((am - a0) * j) / 4)).map((p_, j) => `${j ? "L" : "M"}${p_[0].toFixed(1)},${p_[1].toFixed(1)}`).join(" ");
    segs.push(<path key={i} d={d} stroke={P.color} strokeWidth={P.lineW} strokeLinecap="round" fill="none" />);
  }
  return (
    <svg width={W} height={H} style={{ position: "absolute", left: 0, top: 0, opacity: o, pointerEvents: "none", filter: "drop-shadow(0 2px 3px rgba(0,0,0,0.5))" }}>{segs}</svg>
  );
};

// ── 땀방울 루프: 3f 페이드인 + 8px 낙하, 12f 유지, 3f 페이드, 30f 주기 [ref 568.8s] ─────
export const SweatDropParams = z.object({
  period: num(30, 4, 120, 1, "반복 주기", "timing", "f"),
  fadeIn: num(3, 1, 20, 1, "페이드인", "timing", "f"),
  hold: num(12, 0, 60, 1, "유지", "timing", "f"),
  fadeOut: num(3, 1, 20, 1, "페이드아웃", "timing", "f"),
  fall: num(10, 0, 80, 1, "낙하 거리(크기 1 기준)", "motion", "px"),
  s: num(1, 0.3, 4, 0.05, "크기(배)", "size"),
  color: col("#BFE6F5", "물방울 색"),
});
export type SweatDropP = z.infer<typeof SweatDropParams>;
export const SweatDrop: React.FC<{ x: number; y: number; at: number; s?: number; p?: Partial<SweatDropP> }> = ({ x, y, at, s: s0, p }) => {
  const P = def(SweatDropParams, { ...pick({ s: s0 }), ...p });
  const s = P.s;
  const f = useCurrentFrame();
  if (f < at) return null;
  const T = pos(P.period, 1);
  const g = (f - at) % T;
  const t1 = P.fadeIn, t2 = t1 + P.hold, t3 = t2 + P.fadeOut;
  const op = kf(g, 0, inc([0, t1, t2, t3, Math.max(T, t3 + 0.001)]), [0, 1, 1, 0, 0]);
  const dy = kf(g, 0, [0, t3], [0, P.fall * s]);
  return (
    <svg width={34 * s} height={48 * s} viewBox="0 0 34 48" style={{ position: "absolute", left: x, top: y + dy, opacity: op }}>
      <path d="M17,2 C17,2 3,22 3,31 a14,14 0 0 0 28,0 C31,22 17,2 17,2Z" fill={P.color} stroke="#8CCBE6" strokeWidth={2} />
      <path d="M10,28 a8,8 0 0 0 4,9" stroke="#fff" strokeWidth={3} fill="none" strokeLinecap="round" />
    </svg>
  );
};

// ── 지도: 산둥→인천 항로 — MapLibre(OpenFreeMap 벡터타일, semoji 스타일) 실제 지도 위에 오버레이 ─────
// 좌표는 전부 경위도. lngLatToPixel 로 화면 좌표를 구한다(AE 프리렌더 배경과 같은 투영)
export const MAP_PLACES = {
  chefoo: [121.39, 37.54] as [number, number],      // 산둥 옌타이(지부)
  incheon: [126.62, 37.46] as [number, number],     // 인천(제물포)
  shandongLabel: [118.6, 36.3] as [number, number],
  qingLabel: [116.4, 39.9] as [number, number],
  joseonLabel: [127.8, 38.9] as [number, number],
  seaLabel: [123.6, 36.2] as [number, number],
  routeCtrl: [124.0, 38.5] as [number, number],     // 항로 곡선 조절점
};
export const MapRouteParams = z.object({
  routeLen: num(36, 2, 120, 1, "항로 드로우 길이", "timing", "f"),
  labelStagger: num(1, 0, 4, 0.05, "라벨 스태거(배)", "timing"),
  dotLen: num(6, 1, 30, 1, "항구 점 팝 길이", "timing", "f"),
  camLen: num(90, 0, 300, 1, "카메라 푸시인 길이", "timing", "f"),
  boatRock: num(4, 0, 20, 0.5, "배 흔들림 각도", "motion", "°"),
  zoom0: num(5.9, 3, 9, 0.05, "시작 줌", "motion"),
  zoom1: num(6.2, 3, 9, 0.05, "끝 줌", "motion"),
  centerLng: num(123.4, 110, 135, 0.1, "지도 중심 경도(독도가 화면 안에)", "motion", "°"),
  centerLat: num(37.4, 30, 45, 0.1, "지도 중심 위도", "motion", "°"),
  routeW: num(9, 2, 30, 1, "항로 두께", "size", "px"),
  dotR: num(13, 4, 40, 1, "항구 점 크기", "size", "px"),
  routeColor: col("#C0392B", "항로·점 색"),
  seaColor: col("#8FBFD6", "바다 색"),
  landColor: col("#EAD9B6", "육지 색"),
  stroke: choice("line", ["line", "brush"] as const, "항로 선(line=기존 · brush=붓 화살표 테이퍼+흰 테두리)"),
  brushW: num(30, 6, 80, 1, "brush: 최대 두께", "size", "px"),
  brushTail: num(0.25, 0, 1, 0.05, "brush: 꼬리 두께 비율", "size"),
  brushBorder: num(5, 0, 16, 0.5, "brush: 흰 테두리", "size", "px"),
  brushHead: num(2, 1, 4, 0.1, "brush: 화살촉(두께 배)", "size"),
  brushLen: num(25, 2, 120, 1, "brush: 드로우 길이(ease-in-out)", "timing", "f"),
});
export type MapRouteP = z.infer<typeof MapRouteParams>;
/** 붓 화살표 외곽: 폴리라인 pts 의 앞 k(0..1)만큼, 꼬리 가늘고(tail) 머리 쪽 굵은 테이퍼 몸통 + 삼각 화살촉 [설명형 레퍼런스 브러시 화살표] */
export const brushArrowShape = (pts: { x: number; y: number }[], k: number, width: number, tail = 0.25, head = 2) => {
  const cum = [0];
  for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y));
  const L = cum[cum.length - 1] * Math.max(0, Math.min(1, k));
  const vis: { x: number; y: number; d: number }[] = [];
  for (let i = 0; i < pts.length; i++) {
    if (cum[i] <= L) vis.push({ ...pts[i], d: cum[i] });
    else { const a = pts[i - 1], b = pts[i], r = (L - cum[i - 1]) / Math.max(0.001, cum[i] - cum[i - 1]); vis.push({ x: a.x + (b.x - a.x) * r, y: a.y + (b.y - a.y) * r, d: L }); break; }
  }
  if (vis.length < 2 || L < 1) return null;
  const headLen = Math.min(L * 0.5, width * head * 0.9), bodyEnd = L - headLen;
  const left: string[] = [], right: string[] = [];
  let last = vis[0];
  for (let i = 0; i < vis.length; i++) {
    const q = vis[i];
    if (q.d > bodyEnd && i > 0) break;
    const nx = vis[Math.min(i + 1, vis.length - 1)], pv = vis[Math.max(i - 1, 0)];
    const tx = nx.x - pv.x, ty = nx.y - pv.y, tl = Math.hypot(tx, ty) || 1;
    const hw = (width / 2) * (tail + (1 - tail) * Math.min(1, (q.d / Math.max(1, L)) * 1.6));
    left.push(`${(q.x - (ty / tl) * hw).toFixed(1)},${(q.y + (tx / tl) * hw).toFixed(1)}`);
    right.push(`${(q.x + (ty / tl) * hw).toFixed(1)},${(q.y - (tx / tl) * hw).toFixed(1)}`);
    last = q;
  }
  const tip = vis[vis.length - 1], dx = tip.x - last.x, dy = tip.y - last.y, dl = Math.hypot(dx, dy) || 1, hw = (width * head) / 2;
  return {
    body: `M${left.join(" L")} L${right.reverse().join(" L")} Z`,
    head: dl > 0.5 ? `${(last.x - (dy / dl) * hw).toFixed(1)},${(last.y + (dx / dl) * hw).toFixed(1)} ${tip.x.toFixed(1)},${tip.y.toFixed(1)} ${(last.x + (dy / dl) * hw).toFixed(1)},${(last.y - (dx / dl) * hw).toFixed(1)}` : null,
  };
};
/** 붓 화살표 SVG 조각(흰 테두리 → 색 몸통) */
export const BrushArrowSvg: React.FC<{ shape: ReturnType<typeof brushArrowShape>; color: string; border: number }> = ({ shape, color, border }) => shape ? (
  <g>
    {border > 0 && <path d={shape.body} fill="#fff" stroke="#fff" strokeWidth={border * 2} strokeLinejoin="round" />}
    {border > 0 && shape.head && <polygon points={shape.head} fill="#fff" stroke="#fff" strokeWidth={border * 2} strokeLinejoin="round" />}
    <path d={shape.body} fill={color} />
    {shape.head && <polygon points={shape.head} fill={color} />}
  </g>
) : null;
export const mapRouteCamera = (f: number, P: MapRouteP): CameraState => ({
  center: [P.centerLng, P.centerLat], bearing: 0, pitch: 0,
  zoom: P.camLen > 0 ? lerp(f, 0, P.camLen, P.zoom0, P.zoom1, Easing.inOut(Easing.cubic)) : P.zoom1,
});
export const MapRoute: React.FC<{ at: number; routeAt: number; labelsAt: number; p?: Partial<MapRouteP> }> = ({ at, routeAt, labelsAt, p }) => {
  const P = def(MapRouteParams, p);
  const f = useCurrentFrame();
  const cam = mapRouteCamera(f, P);
  const px = (ll: [number, number]) => lngLatToPixel(ll, cam, W, H);
  const brush = P.stroke === "brush";
  const k = lerp(f, routeAt, routeAt + (brush ? P.brushLen : P.routeLen), 0, 1, Easing.inOut(Easing.cubic));
  // 항로: 경위도 2차 베지어를 샘플 → 화면 좌표 폴리라인
  const pts = Array.from({ length: 41 }, (_, i) => {
    const t = i / 40, a = MAP_PLACES.chefoo, c = MAP_PLACES.routeCtrl, b = MAP_PLACES.incheon;
    return px([(1 - t) ** 2 * a[0] + 2 * (1 - t) * t * c[0] + t * t * b[0], (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * c[1] + t * t * b[1]]);
  });
  const d = pts.map((q, i) => `${i ? "L" : "M"}${q.x.toFixed(1)},${q.y.toFixed(1)}`).join(" ");
  const bi = Math.min(40, Math.round(k * 40)), boat = pts[bi];
  const ls = P.labelStagger;
  const lab = (t: string, ll: [number, number], dx: number, dy: number, dl: number, big = false) => {
    const a = labelsAt + dl * ls;
    if (f < a) return null;
    const { s, op } = textPop(f, a);
    const q = px(ll);
    return <div style={{ position: "absolute", left: q.x + dx, top: q.y + dy, transform: `translate(-50%,-50%) scale(${s})`, opacity: op, fontFamily: big ? "Yeonsung, 'Songti SC', serif" : "NeoHv", fontSize: big ? 64 : 40, color: big ? "#4B2420" : "#fff", background: big ? "transparent" : "#302e2f", padding: big ? 0 : "6px 18px 2px", borderRadius: 8, WebkitTextStroke: big ? "10px #fff" : undefined, paintOrder: "stroke fill", whiteSpace: "nowrap" }}>{hz(t)}</div>;
  };
  const onReady = React.useCallback((map: any) => {
    try { map.setPaintProperty("background", "background-color", P.landColor); map.setPaintProperty("water", "fill-color", P.seaColor); } catch { /* 스타일에 레이어 없음 */ }
  }, [P.landColor, P.seaColor]);
  const sea = px(MAP_PLACES.seaLabel);
  return (
    <AbsoluteFill style={{ background: P.seaColor }}>
      <RemotionMap mapStyle="semoji" cameraState={cam} onMapReady={onReady} width={W} height={H}>
        <svg width={W} height={H} style={{ position: "absolute" }}>
          <text x={sea.x} y={sea.y} fontFamily="Yeonsung, 'Songti SC', serif" fontSize={70} fill="#6FA3BD" textAnchor="middle">황 해</text>
          {brush
            ? <BrushArrowSvg shape={brushArrowShape(pts, k, P.brushW, P.brushTail, P.brushHead)} color={P.routeColor} border={P.brushBorder} />
            : <path d={d} pathLength={1} stroke={P.routeColor} strokeWidth={P.routeW} fill="none" strokeLinecap="round" strokeDasharray={1} strokeDashoffset={1 - k} />}
          {[MAP_PLACES.chefoo, MAP_PLACES.incheon].map((ll, i) => { const q = px(ll); return <circle key={i} cx={q.x} cy={q.y} r={lerp(f, labelsAt + i * 6 * ls, labelsAt + i * 6 * ls + P.dotLen, 0, P.dotR, EXPO_OUT)} fill={P.routeColor} stroke="#fff" strokeWidth={5} />; })}
        </svg>
        {f >= routeAt && !brush && (
          // 세모지 정크선(junk_sailboat) — 바닥(선체 아래) 피벗 흔들림, 박스 90×70 → 그림 높이 92
          <Img src={prop("junk_sailboat")} style={{ position: "absolute", left: boat.x - 45, top: boat.y + 4 - 92, width: 90, height: 92, transformOrigin: "50% 100%", transform: `rotate(${Math.sin(f / 5) * P.boatRock}deg)` }} />
        )}
        {/* 필수: 울릉도·독도 + 동해 표기 */}
        <KoreaIslands project={(ll) => px(ll)} pxPerDeg={(Math.pow(2, cam.zoom) * 512) / 360} land={P.landColor} labelSize={24} />
        {lab("산둥(山東)", MAP_PLACES.shandongLabel, 0, 0, 0, true)}
        {lab("인천", MAP_PLACES.incheon, 0, -66, 6)}
        {lab("청(淸)", MAP_PLACES.qingLabel, 0, 0, 10, true)}
        {lab("조선", MAP_PLACES.joseonLabel, 0, 0, 14, true)}
      </RemotionMap>
    </AbsoluteFill>
  );
};

// ══ ref2(MS편) 추가 기법 ═══════════════════════════════════════════════════

// ── 타자 인터스티셜 [ref2 5:32 "그러던 어느 날"]: 세이지 #C2CDC4, 검정 굵게 150px, 글자당 2f ──
export const TypeCardParams = z.object({
  charFrames: num(2, 1, 12, 1, "글자당 프레임", "timing", "f"),
  fadeLen: num(6, 1, 30, 1, "끝 페이드아웃", "timing", "f"),
  fontSize: num(150, 40, 260, 2, "글자 크기", "size", "px"),
  bg: col("#C2CDC4", "바탕 색"),
  color: col("#111", "글자 색"),
});
export type TypeCardP = z.infer<typeof TypeCardParams>;
export const TypeCard: React.FC<{ text: string; dur: number; p?: Partial<TypeCardP> }> = ({ text, dur, p }) => {
  const P = def(TypeCardParams, p);
  const f = useCurrentFrame();
  const n = Math.min(text.length, Math.floor(f / pos(P.charFrames, 1)) + 1);
  return (
    <AbsoluteFill style={{ background: P.bg, opacity: lerp(f, dur - P.fadeLen, dur, 1, 0) }}>
      <div style={{ position: "absolute", top: 440, width: "100%", textAlign: "center", fontFamily: "NeoHv", fontSize: P.fontSize, color: P.color }}>
        <span>{text.slice(0, n)}</span><span style={{ opacity: 0 }}>{text.slice(n)}</span>
      </div>
    </AbsoluteFill>
  );
};

// ── 글리치 전환 [ref2 31:36]: 나가는 씬 RGB 분리·가로 슬라이스 밀림 3f → 블록 노이즈 3f → 새 씬 1f 글리치 ──
export const GlitchOverlayParams = z.object({
  len: num(7, 1, 30, 1, "글리치 전체 길이", "timing", "f"),
  blockAt: num(3, 0, 30, 1, "블록 노이즈 시작", "timing", "f"),
  blockLen: num(3, 0, 30, 1, "블록 노이즈 길이", "timing", "f"),
  bands: num(9, 0, 40, 1, "가로 띠 개수", "size"),
  bandShift: num(160, 0, 600, 10, "띠 밀림 폭", "motion", "px"),
  bandOp: num(0.28, 0, 1, 0.02, "띠 불투명도", "look"),
  blocks: num(40, 0, 150, 1, "노이즈 블록 개수", "size"),
  blockOp: num(0.85, 0, 1, 0.05, "블록 불투명도", "look"),
});
export type GlitchOverlayP = z.infer<typeof GlitchOverlayParams>;
export const GlitchOverlay: React.FC<{ at: number; p?: Partial<GlitchOverlayP> }> = ({ at, p }) => {
  const P = def(GlitchOverlayParams, p);
  const f = useCurrentFrame();
  const g = f - at;
  if (g < 0 || g > P.len) return null;
  const bands = Array.from({ length: Math.round(P.bands) }).map((_, i) => ({ y: random(`gy${i}-${g}`) * H, h: 30 + random(`gh${i}-${g}`) * 60, dx: (random(`gx${i}-${g}`) - 0.5) * P.bandShift }));
  const blocks = g >= P.blockAt && g < P.blockAt + P.blockLen ? Array.from({ length: Math.round(P.blocks) }).map((_, i) => ({ x: random(`bx${i}-${g}`) * W, y: random(`by${i}-${g}`) * H, w: 40 + random(`bw${i}-${g}`) * 220, h: 20 + random(`bh${i}-${g}`) * 90, c: ["#ff2d6a", "#28e0ff", "#f5f5f5", "#1a1a1a", "#7a4dff"][i % 5] })) : [];
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {bands.map((b, i) => <div key={i} style={{ position: "absolute", left: b.dx, top: b.y, width: W, height: b.h, background: i % 2 ? `rgba(40,224,255,${P.bandOp})` : `rgba(255,45,106,${P.bandOp})`, mixBlendMode: "screen" }} />)}
      {blocks.map((b, i) => <div key={`b${i}`} style={{ position: "absolute", left: b.x, top: b.y, width: b.w, height: b.h, background: b.c, opacity: P.blockOp }} />)}
    </AbsoluteFill>
  );
};

// ── 아바타 순차 팝 [ref2 19:05]: 원형 유저 아이콘, 0→1.15→1.0 (5f), 7f 스태거 ──────────────
export const AvatarPopParams = z.object({
  stagger: num(7, 0, 30, 1, "스태거 간격", "timing", "f"),
  popLen: num(5, 1, 30, 1, "팝 길이", "timing", "f"),
  popOver: num(0.15, 0, 0.6, 0.01, "오버슈트 크기(배)", "motion"),
  d: num(76, 20, 240, 2, "아바타 지름", "size", "px"),
  ringW: num(5, 0, 20, 0.5, "흰 테두리 두께", "size", "px"),
});
export type AvatarPopP = z.infer<typeof AvatarPopParams>;
export const AvatarPop: React.FC<{ pts: [number, number][]; at: number; d?: number; colors?: string[]; p?: Partial<AvatarPopP> }> = ({ pts, at, d: d0, colors = ["#E5532A", "#F4B400", "#1E9BD7"], p }) => {
  const P = def(AvatarPopParams, { ...pick({ d: d0 }), ...p });
  const d = P.d, PL = P.popLen;
  const f = useCurrentFrame();
  return (
    <>
      {pts.map(([x, y], i) => {
        const a = at + i * P.stagger;
        if (f < a) return null;
        const s = kf(f, a, [0, PL * 0.6, PL], [0, 1 + P.popOver, 1.0]);
        return (
          // 색 원판·흰 링은 코드, 안의 인물은 세모지 캐스트(SemojiRig) 얼굴·어깨 크롭
          <div key={i} style={{ position: "absolute", left: x - d / 2, top: y - d / 2, width: d, height: d, transform: `scale(${s})`, filter: "drop-shadow(0 3px 4px rgba(0,0,0,0.3))" }}>
            <div style={{ position: "absolute", left: d * 0.02, top: d * 0.02, width: d * 0.96, height: d * 0.96, borderRadius: "50%", background: colors[i % colors.length], border: `${(P.ringW * d) / 100}px solid #fff`, boxSizing: "border-box", overflow: "hidden" }}>
              {/* 세모지 캐스트 얼굴·어깨(순번마다 다른 캐스트) */}
              <CastHead cast={(["walker1", "c3_woman", "c2_boss", "c5_chef", "c4_elder"] as CastId[])[i % 5]} x={d * 0.48} headTop={d * 0.1} s={(d * 0.52) / 250} seed={`av${i}`} />
            </div>
          </div>
        );
      })}
    </>
  );
};

// ── 용어 설명 카드 [ref2 11:08]: 자막 위 1584×180 종이 카드, 가운데 세로 슬릿에서 좌우로 펼침 16f ──
export const TermCardParams = z.object({
  openLen: num(16, 1, 60, 1, "펼침 길이", "timing", "f"),
  closeLen: num(8, 1, 40, 1, "접힘 길이", "timing", "f"),
  radius: num(24, 0, 90, 1, "모서리 둥글기", "size", "px"),
  termSize: num(46, 20, 90, 1, "용어 글자 크기", "size", "px"),
  defSize: num(50, 20, 90, 1, "설명 글자 크기", "size", "px"),
  cardColor: col("#FCFAF4", "카드 색"),
  termColor: col("#80B404", "용어 색"),
});
export type TermCardP = z.infer<typeof TermCardParams>;
export const TermCard: React.FC<{ term: string; def: string; at: number; out?: number; p?: Partial<TermCardP> }> = ({ term, def: defText, at, out, p }) => {
  const P = def(TermCardParams, p);
  const f = useCurrentFrame();
  if (f < at || (out !== undefined && f > out + P.closeLen)) return null;
  const k = lerp(f, at, at + P.openLen, 0, 50, QUART_OUT) - (out !== undefined ? lerp(f, out, out + P.closeLen, 0, 50, Easing.in(Easing.quad)) : 0);
  return (
    <div style={{ position: "absolute", left: 158, top: 735, width: 1584, height: 180, borderRadius: P.radius, background: P.cardColor, boxShadow: "0 10px 24px rgba(0,0,0,0.3)", clipPath: `inset(0 ${50 - k}% 0 ${50 - k}% round ${P.radius}px)`, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 8 }}>
      <div style={{ fontFamily: "NeoHv", fontSize: P.termSize, color: P.termColor }}>{hz(term)}</div>
      <div style={{ fontFamily: "NeoHv", fontSize: P.defSize, color: "#1a1a1a" }}>{hz(defText)}</div>
    </div>
  );
};

// ── 엘보 리더라인 콜아웃 [ref2 91:44·138:52]: 직각 꺾은선 9f 드로우 → 끝에서 pill scaleX 0.3→1 (4f)+가로블러 ──
export const ElbowCalloutParams = z.object({
  drawLen: num(9, 1, 40, 1, "꺾은선 드로우 길이", "timing", "f"),
  ...stretchShape,
  lineW: num(8, 1, 24, 0.5, "선 두께", "size", "px"),
  dotR: num(9, 0, 30, 1, "시작점 크기", "size", "px"),
  fontSize: num(40, 16, 90, 1, "글자 크기", "size", "px"),
  color: col("#6DB33F", "선·알약 색"),
});
export type ElbowCalloutP = z.infer<typeof ElbowCalloutParams>;
export const ElbowCallout: React.FC<{ from: [number, number]; mid: [number, number]; to: [number, number]; text: string; at: number; color?: string; side?: "left" | "right"; p?: Partial<ElbowCalloutP> }> = ({ from, mid, to, text, at, color: color0, side = "left", p }) => {
  const P = def(ElbowCalloutParams, { ...pick({ color: color0 }), ...p });
  const color = P.color;
  const f = useCurrentFrame();
  if (f < at) return null;
  const k = lerp(f, at, at + P.drawLen, 0, 1, Easing.inOut(Easing.cubic));
  const pa = at + P.drawLen;
  const st = stretch(f, pa, P);
  const sx = f < pa ? 0 : st.sx;
  const blur = f < pa ? 0 : st.blur;
  return (
    <>
      <svg width={W} height={H} style={{ position: "absolute", left: 0, top: 0, pointerEvents: "none" }}>
        <path d={`M${from[0]},${from[1]} L${mid[0]},${mid[1]} L${to[0]},${to[1]}`} pathLength={1} stroke={color} strokeWidth={P.lineW} fill="none" strokeLinecap="round" strokeLinejoin="round" strokeDasharray={1} strokeDashoffset={1 - k} />
        <circle cx={from[0]} cy={from[1]} r={k > 0 ? P.dotR : 0} fill={color} />
      </svg>
      {f >= pa && (
        <div style={{ position: "absolute", top: to[1] - 34, [side === "left" ? "right" : "left"]: side === "left" ? W - to[0] : to[0], transform: `scaleX(${sx})`, transformOrigin: side === "left" ? "100% 50%" : "0% 50%", filter: `blur(${blur / 3}px)`, background: color, color: "#fff", fontFamily: "NeoHv", fontSize: P.fontSize, padding: "12px 30px 10px", borderRadius: 999, whiteSpace: "nowrap", boxShadow: "0 6px 10px rgba(0,0,0,0.3)" } as React.CSSProperties}>{text}</div>
      )}
    </>
  );
};

// ── 돋보기 콜아웃 박스 [ref2 10:34]: 가로선 → 세로 펼침 5f(오버슈트), 태그 +4f, 역순 퇴장. 초록 #7BB200 테두리 14px ──
export const MagnifierBoxParams = z.object({
  openLen: num(5, 1, 30, 1, "세로 펼침 길이", "timing", "f"),
  openFrom: num(0.02, 0, 1, 0.01, "시작 세로 비율", "motion"),
  openOver: num(0.06, 0, 0.4, 0.01, "오버슈트 크기(배)", "motion"),
  tagDelay: num(4, 0, 30, 1, "태그 등장 지연", "timing", "f"),
  tagLen: num(4, 1, 20, 1, "태그 펼침 길이", "timing", "f"),
  outLen: num(5, 1, 30, 1, "퇴장 길이", "timing", "f"),
  borderW: num(14, 0, 40, 1, "테두리 두께", "size", "px"),
  tagSize: num(40, 16, 90, 1, "태그 글자 크기", "size", "px"),
  color: col("#7BB200", "테두리·태그 색"),
});
export type MagnifierBoxP = z.infer<typeof MagnifierBoxParams>;
export const MagnifierBox: React.FC<{ img: string; crop: { cx: number; cy: number; zoom: number }; x: number; y: number; w: number; h: number; tag: string; at: number; out?: number; p?: Partial<MagnifierBoxP> }> = ({ img, crop, x, y, w, h, tag, at, out, p }) => {
  const P = def(MagnifierBoxParams, p);
  const f = useCurrentFrame();
  if (f < at || (out !== undefined && f > out + P.outLen)) return null;
  const OL = P.openLen, TL = P.tagLen, ta = at + P.tagDelay;
  let sy = kf(f, at, [0, OL * 0.4, OL * 0.8, OL], [P.openFrom, 0.6, 1 + P.openOver, 1.0]);
  if (out !== undefined && f >= out) sy = lerp(f, out, out + P.outLen, 1, P.openFrom, Easing.in(Easing.quad));
  const tagS = f < ta || (out !== undefined && f >= out) ? 0 : kf(f, ta, [0, TL * 0.75, TL], [0.3, 1 + P.openOver, 1.0]);
  return (
    <div style={{ position: "absolute", left: x, top: y, width: w, height: h }}>
      <div style={{ position: "absolute", inset: 0, transform: `scaleY(${sy})`, border: `${P.borderW}px solid ${P.color}`, borderRadius: 10, backgroundColor: "#FCFAF4", backgroundImage: `url(${src(img)})`, backgroundSize: `${crop.zoom * 100}% auto`, backgroundPosition: `${crop.cx * 100}% ${crop.cy * 100}%`, boxShadow: "0 12px 24px rgba(0,0,0,0.4)" }} />
      {tagS > 0 && <div style={{ position: "absolute", left: "50%", top: -34, transform: `translateX(-50%) scaleX(${tagS})`, background: P.color, color: "#fff", fontFamily: "NeoHv", fontSize: P.tagSize, padding: "10px 28px 8px", borderRadius: 999, whiteSpace: "nowrap" }}>{hz(tag)}</div>}
    </div>
  );
};

// ── 필름스트립 리캡 [ref2 엔딩 9276s]: 검정 띠 560px, 스프로킷 구멍, 프레임 330×320, 우→좌 등속 5.7px/f ──
export const FilmStripParams = z.object({
  speed: num(5.7, -30, 30, 0.1, "흐르는 속도(음수=반대)", "motion", "px/f"),
  frameW: num(360, 120, 800, 10, "프레임 폭", "size", "px"),
  gap: num(40, 0, 200, 2, "프레임 간격", "size", "px"),
  labelSize: num(46, 16, 100, 1, "라벨 글자 크기", "size", "px"),
  stripColor: col("#141414", "필름 색"),
  holeColor: col("#EDE7DA", "구멍 색"),
});
export type FilmStripP = z.infer<typeof FilmStripParams>;
export const FilmStrip: React.FC<{ frames: { img: string; label: string; bw?: boolean }[]; y?: number; speed?: number; startX?: number; p?: Partial<FilmStripP> }> = ({ frames, y = 250, speed, startX = 700, p }) => {
  const P = def(FilmStripParams, { ...pick({ speed }), ...p });
  const f = useCurrentFrame();
  const fw = P.frameW, gap = P.gap, hh = 560;
  const x0 = startX - f * P.speed;
  const total = frames.length * (fw + gap) + 400;
  return (
    <div style={{ position: "absolute", left: x0, top: y, width: total, height: hh, background: P.stripColor, boxShadow: "0 14px 30px rgba(0,0,0,0.5)" }}>
      {Array.from({ length: Math.ceil(total / 60) }).map((_, i) => (
        <React.Fragment key={i}>
          <div style={{ position: "absolute", left: i * 60 + 18, top: 20, width: 30, height: 38, borderRadius: 6, background: P.holeColor }} />
          <div style={{ position: "absolute", left: i * 60 + 18, bottom: 20, width: 30, height: 38, borderRadius: 6, background: P.holeColor }} />
        </React.Fragment>
      ))}
      {frames.map((fr, i) => (
        <div key={i} style={{ position: "absolute", left: 200 + i * (fw + gap), top: 86, width: fw, height: 330, overflow: "hidden", borderRadius: 6, background: "#333" }}>
          <Img src={src(fr.img)} style={{ width: "100%", height: "100%", objectFit: "cover", filter: fr.bw ? "grayscale(1) contrast(1.2)" : undefined }} />
          <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: 60, background: "linear-gradient(transparent, rgba(0,0,0,0.75))" }} />
          <div style={{ position: "absolute", left: 16, bottom: 8, fontFamily: "Yeonsung, 'Songti SC', serif", fontSize: P.labelSize, color: "#fff" }}>{fr.label}</div>
        </div>
      ))}
    </div>
  );
};
