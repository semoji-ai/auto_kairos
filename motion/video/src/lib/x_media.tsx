// 사진·자료 처리 & 배경 루프(x_media) — 도감 "분석만" 항목을 레퍼런스 프레임 대조 후 구현.
// 전부 결정론적(remotion random(seed)). 방사형 줄무늬 광선은 쓰지 않는다(나선·동심 링·원형 글로우만).
import React from "react";
import { AbsoluteFill, Img, random, useCurrentFrame, interpolate, Easing } from "remotion";
import { z } from "zod";
import { W, H, lerp, kf, src, hz, EXPO_OUT, Starburst, SweatDrop } from "../fx";
import { num, col, flag, choice, def } from "../params/p";
import { SourceChip } from "./backgrounds";
import { HBlur, Pill, KitImg } from "./callouts";
import { prop, propH, propSize } from "./kit";

type RN = React.ReactNode;
const CL = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
/** 넘어온(undefined 아님) 개별 prop 만 */
const pk = <T extends Record<string, any>>(o: T): Partial<T> => Object.fromEntries(Object.entries(o).filter(([, v]) => v !== undefined)) as Partial<T>;
/** 0→1 진행도 */
const prog = (f: number, a: number, len: number, e: (t: number) => number = Easing.out(Easing.cubic)) =>
  interpolate(f, [a, a + Math.max(0.001, len)], [0, 1], { ...CL, easing: e });
const SINE_IO = Easing.inOut(Easing.sin);
const SINE_O = Easing.out(Easing.sin);
const mix = (a: number, b: number, t: number) => a + (b - a) * t;
const hex2rgb = (h: string) => {
  const m = h.replace("#", "");
  const v = m.length === 3 ? m.split("").map((c) => c + c).join("") : m.slice(0, 6);
  return [0, 2, 4].map((i) => parseInt(v.slice(i, i + 2), 16) || 0);
};
const mixHex = (a: string, b: string, t: number) => {
  const A = hex2rgb(a), B = hex2rgb(b);
  return `rgb(${A.map((v, i) => Math.round(mix(v, B[i], t))).join(",")})`;
};
/** 여러 색 정지점 사이 보간(t 0→1) */
const rampHex = (cs: string[], t: number) => {
  const u = Math.max(0, Math.min(0.9999, t)) * (cs.length - 1);
  const i = Math.floor(u);
  return mixHex(cs[i], cs[i + 1], u - i);
};
/** 4방향 드롭섀도 연쇄 = 두께 s 외곽선(누끼용) */
const strokeFilter = (s: number, c = "#fff") =>
  s <= 0 ? "" : [[s, 0], [-s, 0], [0, s], [0, -s]].map(([x, y]) => `drop-shadow(${x}px ${y}px 0 ${c})`).join(" ");

// ── 거친 가장자리 마스크(붓자국·거친 비네트): feTurbulence 변위 SVG 를 mask-image 로 ─────────
type RoughO = { inset?: number; scale?: number; freq?: number; seed?: number; blur?: number; ellipse?: boolean; bleed?: { l?: boolean; t?: boolean; r?: boolean; b?: boolean } };
export const roughMask = (w: number, h: number, o: RoughO = {}) => {
  const i = o.inset ?? 20, s = o.scale ?? 30, fq = o.freq ?? 0.03, bl = o.bleed || {};
  const x0 = bl.l ? -300 : i, y0 = bl.t ? -300 : i, x1 = bl.r ? w + 300 : w - i, y1 = bl.b ? h + 300 : h - i;
  const shape = o.ellipse
    ? `<ellipse cx='${w / 2}' cy='${h / 2}' rx='${w / 2 - i}' ry='${h / 2 - i}' fill='white'/>`
    : `<rect x='${x0}' y='${y0}' width='${x1 - x0}' height='${y1 - y0}' fill='white'/>`;
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='${w}' height='${h}' viewBox='0 0 ${w} ${h}'><defs><filter id='r' x='-20%' y='-20%' width='140%' height='140%'><feTurbulence type='fractalNoise' baseFrequency='${fq}' numOctaves='4' seed='${o.seed ?? 3}' result='n'/><feDisplacementMap in='SourceGraphic' in2='n' scale='${s}' xChannelSelector='R' yChannelSelector='G'/>${o.blur ? `<feGaussianBlur stdDeviation='${o.blur}'/>` : ""}</filter></defs><g filter='url(#r)'>${shape}</g></svg>`;
  return `url("data:image/svg+xml;utf8,${encodeURIComponent(svg)}")`;
};
const maskStyle = (m: string): React.CSSProperties => ({ WebkitMaskImage: m, maskImage: m, WebkitMaskSize: "100% 100%", maskSize: "100% 100%", WebkitMaskRepeat: "no-repeat", maskRepeat: "no-repeat" } as React.CSSProperties);

// ══ 리그: 플랫 손(피부 + 소매) ═══════════════════════════════════════════════
// 앵커 = 손바닥 중심. rot 0 이면 손가락이 위. grip 0→1 이면 손가락이 오므라든다.
export const FlatHand: React.FC<{ x: number; y: number; size: number; rot?: number; skin?: string; sleeve?: string; grip?: number; mirror?: boolean; bare?: boolean }> = ({ x, y, size, rot = 0, skin = "#F2C7A5", sleeve = "#2B2B2B", grip = 0, mirror, bare }) => {
  const s = size / 200, fl = 90 - grip * 45;
  return (
    <svg viewBox="0 0 200 330" width={200 * s} height={330 * s} style={{ position: "absolute", left: x - 100 * s, top: y - 150 * s, overflow: "visible", transformOrigin: `${100 * s}px ${150 * s}px`, transform: `rotate(${rot}deg) scaleX(${mirror ? -1 : 1})` }}>
      {!bare && <rect x={58} y={228} width={86} height={110} rx={10} fill={sleeve} />}
      {!bare && <rect x={64} y={210} width={74} height={28} rx={6} fill="#F4F4F4" />}
      {[56, 84, 112, 140].map((fx, i) => {
        const len = fl + (i === 1 || i === 2 ? 14 : 0);
        return <rect key={i} x={fx - 13} y={122 - len} width={26} height={len + 30} rx={13} fill={skin} />;
      })}
      <ellipse cx={100} cy={160} rx={56} ry={62} fill={skin} />
      <path d={`M60,185 L${22 + grip * 30},${128 + grip * 20}`} stroke={skin} strokeWidth={28} strokeLinecap="round" />
      <path d="M72,150 Q100,165 128,150" stroke="rgba(0,0,0,0.12)" strokeWidth={4} fill="none" />
    </svg>
  );
};

// ══ 1. 흑백 사진 인셋(거친 흰 비네트) ═══════════════════════════════════════
// ref1 1:30 — 가장자리가 거칠게 번진 흰 비네트 흑백 사진이 왼쪽 밖에서 ~15f ease-out 슬라이드인
export const RoughPhotoInsetParams = z.object({
  slideLen: num(15, 1, 60, 1, "슬라이드 길이", "timing", "f"),
  slideDist: num(1100, 0, 2400, 10, "슬라이드 거리(왼쪽 밖→제자리)", "motion", "px"),
  rot: num(0, -20, 20, 0.5, "기울기", "motion", "°"),
  inset: num(18, 0, 80, 1, "가장자리 안쪽 여백", "size", "px"),
  whiteEdge: num(46, 0, 160, 2, "흰 비네트 두께", "size", "px"),
  rough: num(24, 0, 90, 1, "가장자리 거칠기", "look", "px"),
  roughFreq: num(0.035, 0.005, 0.15, 0.005, "거칠기 촘촘함", "look"),
  bw: flag(true, "흑백", "look"),
  contrast: num(1.1, 0.5, 2, 0.05, "대비", "look"),
});
export type RoughPhotoInsetP = z.infer<typeof RoughPhotoInsetParams>;
export const RoughPhotoInset: React.FC<{ img: string; x: number; y: number; w: number; h: number; at: number; pos?: string; seed?: number; p?: Partial<RoughPhotoInsetP> }> = ({ img, x, y, w, h, at, pos = "50% 50%", seed = 7, p }) => {
  const P = def(RoughPhotoInsetParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const e = prog(f, at, P.slideLen);
  const m = roughMask(w, h, { inset: P.inset, scale: P.rough, freq: P.roughFreq, seed });
  return (
    <div style={{ position: "absolute", left: x, top: y, width: w, height: h, transform: `translateX(${-(1 - e) * P.slideDist}px) rotate(${P.rot}deg)`, ...maskStyle(m) }}>
      <Img src={src(img)} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: pos, filter: `${P.bw ? "grayscale(1)" : ""} contrast(${P.contrast})` }} />
      <div style={{ position: "absolute", inset: 0, boxShadow: `inset 0 0 ${P.whiteEdge}px ${P.whiteEdge * 0.45}px #fff` }} />
    </div>
  );
};

// ══ 2. 원형 다크 비네트 인물 ════════════════════════════════════════════════
// ref1 2:34 — 인물 둘레를 원형으로 어둡게 눌러 초점. 하드컷 진입(페이드 0).
export const DarkVignetteParams = z.object({
  fadeLen: num(0, 0, 30, 1, "비네트 나타나는 시간(0=컷)", "timing", "f"),
  cx: num(960, 0, 1920, 5, "원 중심 X", "motion", "px"),
  cy: num(470, 0, 1080, 5, "원 중심 Y", "motion", "px"),
  radius: num(540, 100, 1400, 10, "원 반지름", "size", "px"),
  feather: num(70, 0, 600, 5, "경계 부드러움", "size", "px"),
  darkness: num(0.93, 0, 1, 0.01, "바깥 어둡기", "look"),
  color: col("#000000", "비네트 색"),
});
export type DarkVignetteP = z.infer<typeof DarkVignetteParams>;
export const DarkVignettePortrait: React.FC<{ img?: string; pos?: string; at?: number; children?: RN; p?: Partial<DarkVignetteP> }> = ({ img, pos = "50% 30%", at = 0, children, p }) => {
  const P = def(DarkVignetteParams, p);
  const f = useCurrentFrame();
  const o = f < at ? 0 : P.fadeLen > 0 ? prog(f, at, P.fadeLen) : 1;
  const [r, g, b] = hex2rgb(P.color);
  const inner = Math.max(0, P.radius - P.feather);
  return (
    <AbsoluteFill>
      {img ? <Img src={src(img)} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: pos }} /> : children}
      <AbsoluteFill style={{ opacity: o, background: `radial-gradient(circle at ${P.cx}px ${P.cy}px, rgba(${r},${g},${b},0) ${inner}px, rgba(${r},${g},${b},${P.darkness}) ${P.radius}px)` }} />
    </AbsoluteFill>
  );
};

// ══ 3. 실사 + 일러스트 합성 ════════════════════════════════════════════════
// ref1 4:38 — 왼쪽 실사(오른쪽 가장자리 붓 마스크) + 오른쪽 일러스트, 배경은 같은 사진 블러+어둡게. 사진은 알파 8~10f.
// ref1 12:13 — backdrop: 실사 야경 전체 배경 위에 일러스트 인물 컷아웃.
export const PhotoIllustParams = z.object({
  mode: choice("split", ["split", "backdrop"] as const, "합성 방식(나란히/실사 배경)", "motion"),
  fadeLen: num(9, 0, 40, 1, "사진 알파 페이드", "timing", "f"),
  splitW: num(640, 200, 1400, 10, "실사 패널 폭", "size", "px"),
  illustH: num(860, 200, 1080, 10, "일러스트 높이", "size", "px"),
  illustX: num(1300, 0, 1920, 10, "일러스트 중심 X", "motion", "px"),
  rough: num(120, 0, 240, 2, "붓 경계 거칠기", "look", "px"),
  roughFreq: num(0.03, 0.003, 0.1, 0.001, "붓 결 촘촘함", "look"),
  bgBlur: num(14, 0, 60, 1, "배경 블러", "look", "px"),
  bgDim: num(0.55, 0, 1, 0.05, "배경 어둡기", "look"),
  photoGray: flag(false, "실사 흑백", "look"),
});
export type PhotoIllustP = z.infer<typeof PhotoIllustParams>;
export const PhotoIllustComposite: React.FC<{ photo: string; illust: string; at?: number; photoPos?: string; p?: Partial<PhotoIllustP> }> = ({ photo, illust, at = 0, photoPos = "50% 40%", p }) => {
  const P = def(PhotoIllustParams, p);
  const f = useCurrentFrame();
  const o = f < at ? 0 : P.fadeLen > 0 ? prog(f, at, P.fadeLen, Easing.linear) : 1;
  const gray = P.photoGray ? "grayscale(1)" : "";
  const il = <Img src={src(illust)} style={{ position: "absolute", height: P.illustH, left: P.illustX, bottom: 0, transform: "translateX(-50%)" }} />;
  if (P.mode === "backdrop")
    return (
      <AbsoluteFill style={{ background: "#111" }}>
        <Img src={src(photo)} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: photoPos, filter: `${gray} brightness(${1 - P.bgDim * 0.5})` }} />
        {il}
      </AbsoluteFill>
    );
  const m = roughMask(P.splitW, H, { inset: P.rough * 0.9, scale: P.rough, freq: P.roughFreq, seed: 11, bleed: { l: true, t: true, b: true } });
  return (
    <AbsoluteFill style={{ background: "#1a1a1a" }}>
      <Img src={src(photo)} style={{ position: "absolute", width: "110%", height: "110%", left: "-5%", top: "-5%", objectFit: "cover", filter: `blur(${P.bgBlur}px) ${gray} brightness(${1 - P.bgDim})` }} />
      {il}
      <div style={{ position: "absolute", left: 0, top: 0, width: P.splitW, height: H, opacity: o, ...maskStyle(m) }}>
        <Img src={src(photo)} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: photoPos, filter: gray }} />
      </div>
    </AbsoluteFill>
  );
};

// ══ 4. 과거 인물 즉시 흑백화 ═══════════════════════════════════════════════
// ref1 13:10(790s) — 과거 인물 패널을 컷과 함께 채도 0으로. 램프 0 = 하드 전환.
export const InstantMonoParams = z.object({
  rampLen: num(0, 0, 30, 1, "전환 길이(0=컷)", "timing", "f"),
  amount: num(1, 0, 1, 0.05, "흑백 정도", "look"),
  contrast: num(1.05, 0.5, 2, 0.05, "대비", "look"),
  brightness: num(1.05, 0.5, 1.5, 0.05, "밝기", "look"),
  sepia: num(0, 0, 1, 0.05, "세피아", "look"),
});
export type InstantMonoP = z.infer<typeof InstantMonoParams>;
export const InstantMono: React.FC<{ at: number; children: RN; style?: React.CSSProperties; p?: Partial<InstantMonoP> }> = ({ at, children, style, p }) => {
  const P = def(InstantMonoParams, p);
  const f = useCurrentFrame();
  const t = f < at ? 0 : P.rampLen > 0 ? prog(f, at, P.rampLen, Easing.linear) : 1;
  return (
    <div style={{ position: "absolute", inset: 0, ...style, filter: `grayscale(${P.amount * t}) sepia(${P.sepia * t}) contrast(${mix(1, P.contrast, t)}) brightness(${mix(1, P.brightness, t)})` }}>{children}</div>
  );
};

// ══ 5. 사진 속 얼굴 가림 박스 → 이름표 ═════════════════════════════════════
// ref1 12:29(749s) — 다크 박스가 얼굴 자리에 먼저 깔리고, 사진이 어두워지며(주인공만 밝게) 박스에 이름이 뜬다.
export const FaceCoverParams = z.object({
  boxFade: num(3, 0, 20, 1, "박스 나타나는 시간", "timing", "f"),
  dimDelay: num(5, 0, 60, 1, "배경 어두워짐 지연", "timing", "f"),
  dimLen: num(6, 0, 30, 1, "배경 어두워지는 시간", "timing", "f"),
  labelDelay: num(14, 0, 60, 1, "이름 등장 지연", "timing", "f"),
  labelFade: num(4, 0, 20, 1, "이름 페이드", "timing", "f"),
  dim: num(0.55, 0, 1, 0.05, "배경 어둡기", "look"),
  radius: num(10, 0, 40, 1, "박스 모서리", "size", "px"),
  fontSize: num(46, 20, 100, 1, "이름 글자 크기", "size", "px"),
  boxColor: col("rgba(34,34,34,0.88)", "박스 색"),
  textColor: col("#ffffff", "글자 색"),
});
export type FaceCoverP = z.infer<typeof FaceCoverParams>;
export const FaceCoverBox: React.FC<{ img: string; pos?: string; at: number; boxes: { x: number; y: number; w: number; h: number; label: string }[]; focus?: [number, number, number, number]; p?: Partial<FaceCoverP> }> = ({ img, pos = "50% 50%", at, boxes, focus, p }) => {
  const P = def(FaceCoverParams, p);
  const f = useCurrentFrame();
  const bo = f < at ? 0 : P.boxFade > 0 ? prog(f, at, P.boxFade, Easing.linear) : 1;
  const d = P.dim * (f < at + P.dimDelay ? 0 : P.dimLen > 0 ? prog(f, at + P.dimDelay, P.dimLen) : 1);
  const lo = f < at + P.labelDelay ? 0 : P.labelFade > 0 ? prog(f, at + P.labelDelay, P.labelFade) : 1;
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <Img src={src(img)} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: pos }} />
      {focus ? <div style={{ position: "absolute", left: focus[0], top: focus[1], width: focus[2], height: focus[3], boxShadow: `0 0 0 4000px rgba(0,0,0,${d})` }} />
        : <AbsoluteFill style={{ background: `rgba(0,0,0,${d})` }} />}
      {boxes.map((b, i) => (
        <div key={i} style={{ position: "absolute", left: b.x, top: b.y, width: b.w, height: b.h, borderRadius: P.radius, background: P.boxColor, opacity: bo, display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 4px 10px rgba(0,0,0,0.35)" }}>
          <span style={{ opacity: lo, transform: `scale(${mix(0.85, 1, lo)})`, color: P.textColor, fontFamily: "Yeonsung", fontSize: P.fontSize, whiteSpace: "nowrap" }}>{hz(b.label)}</span>
        </div>
      ))}
    </AbsoluteFill>
  );
};

// ══ 6. 컬러 틴트 플래시(로고 월) ═══════════════════════════════════════════
// ref1 11:50(710~715s) 분석 기술: 핑크·보라·주황 틴트가 1~2f 씩 번쩍. (원본 대조 시 710~715s 구간은 느린 팬만 확인됨 → 기술 기반 재현)
export const TintFlashParams = z.object({
  count: num(6, 1, 30, 1, "번쩍임 횟수", "motion"),
  interval: num(9, 2, 60, 1, "번쩍임 간격", "timing", "f"),
  jitter: num(3, 0, 20, 1, "간격 흔들림", "timing", "f"),
  flashLen: num(2, 1, 8, 1, "한 번 길이", "timing", "f"),
  strength: num(0.55, 0, 1, 0.05, "틴트 세기", "look"),
  blend: choice("screen", ["screen", "overlay", "color", "multiply", "normal"] as const, "혼합 방식", "look"),
  c1: col("#FF4FA0", "틴트 색 1(핑크)"),
  c2: col("#8B4DFF", "틴트 색 2(보라)"),
  c3: col("#FF8A2A", "틴트 색 3(주황)"),
});
export type TintFlashP = z.infer<typeof TintFlashParams>;
export const TintFlash: React.FC<{ at: number; children?: RN; seed?: string; p?: Partial<TintFlashP> }> = ({ at, children, seed = "tf", p }) => {
  const P = def(TintFlashParams, p);
  const f = useCurrentFrame();
  const cols = [P.c1, P.c2, P.c3];
  let c: string | null = null, a = 0;
  for (let k = 0; k < P.count; k++) {
    const s = at + k * P.interval + Math.floor(random(`${seed}${k}`) * (P.jitter + 1));
    if (f >= s && f < s + P.flashLen) { c = cols[k % 3]; a = P.strength * (1 - ((f - s) / P.flashLen) * 0.5); }
  }
  return (
    <AbsoluteFill>
      {children}
      {c && <AbsoluteFill style={{ background: c, opacity: a, mixBlendMode: P.blend as any }} />}
    </AbsoluteFill>
  );
};

// ══ 7. 카드 슬라이드인(회전 겹침) ═════════════════════════════════════════
// ref1 8:29(508.75s) — 자격증 카드가 오른쪽에서 ~650px 15f sine in-out, 두 번째 카드는 20f 뒤 살짝 회전해 겹침
export type IdCardSpec = { title: string; name: string; color?: string; img?: string };
const IdCard: React.FC<{ c: IdCardSpec; w: number; h: number }> = ({ c, w, h }) => {
  const u = h / 280;
  const mk = `url(${prop("id_card")})`;
  return (
    <div style={{ width: w, height: h, position: "relative", isolation: "isolate" }}>
      {/* 세모지 그림체 신분증(id_card) — 글자·사진만 코드로 */}
      <Img src={prop("id_card")} style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }} />
      {c.color && <div style={{ position: "absolute", left: 0, top: 0, width: "100%", height: "15.6%", background: c.color, mixBlendMode: "color", WebkitMaskImage: mk, maskImage: mk, WebkitMaskSize: `${w}px ${h}px`, maskSize: `${w}px ${h}px`, WebkitMaskRepeat: "no-repeat", maskRepeat: "no-repeat" } as React.CSSProperties} />}
      <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: "15.6%", color: "#fff", fontFamily: "NeoHv", fontSize: 26 * u, display: "flex", alignItems: "center", justifyContent: "center", whiteSpace: "nowrap" }}>{c.title}</div>
      {c.img && (
        <div style={{ position: "absolute", left: "4.9%", top: "22.3%", width: "32.5%", height: "67.9%", borderRadius: 10 * u, background: "#D6E1F0", overflow: "hidden" }}>
          <Img src={src(c.img)} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "50% 15%" }} />
        </div>
      )}
      <div style={{ position: "absolute", left: "42.6%", top: "23.6%", width: "50%", height: "8.6%", background: "#F9F6F3", fontFamily: "NeoEb", fontSize: 26 * u, color: "#333", display: "flex", alignItems: "center", whiteSpace: "nowrap" }}>{c.name}</div>
    </div>
  );
};
export const CardSlideInParams = z.object({
  slideLen: num(15, 1, 60, 1, "슬라이드 길이", "timing", "f"),
  stagger: num(20, 0, 90, 1, "다음 카드 지연", "timing", "f"),
  slideDist: num(650, 0, 1600, 10, "슬라이드 거리(오른쪽에서)", "motion", "px"),
  rot1: num(0, -30, 30, 0.5, "첫 카드 기울기", "motion", "°"),
  rot2: num(-10, -30, 30, 0.5, "겹치는 카드 기울기", "motion", "°"),
  dx: num(110, -400, 400, 5, "겹침 가로 간격", "motion", "px"),
  dy: num(120, -400, 400, 5, "겹침 세로 간격", "motion", "px"),
  cardW: num(440, 150, 900, 10, "카드 폭", "size", "px"),
  cardH: num(280, 100, 600, 10, "카드 높이", "size", "px"),
  shadow: num(0.28, 0, 1, 0.02, "그림자 진하기", "look"),
});
export type CardSlideInP = z.infer<typeof CardSlideInParams>;
export const CardSlideIn: React.FC<{ cards: IdCardSpec[]; at: number; x: number; y: number; render?: (c: IdCardSpec, i: number) => RN; p?: Partial<CardSlideInP> }> = ({ cards, at, x, y, render, p }) => {
  const P = def(CardSlideInParams, p);
  const f = useCurrentFrame();
  return (
    <>
      {cards.map((c, i) => {
        const a = at + i * P.stagger;
        if (f < a) return null;
        const e = prog(f, a, P.slideLen, SINE_IO);
        return (
          <div key={i} style={{ position: "absolute", left: x + i * P.dx, top: y + i * P.dy, transform: `translateX(${(1 - e) * P.slideDist}px) rotate(${i === 0 ? P.rot1 : P.rot2}deg)`, filter: `drop-shadow(0 10px 14px rgba(0,0,0,${P.shadow}))` }}>
            {render ? render(c, i) : <IdCard c={c} w={P.cardW} h={P.cardH} />}
          </div>
        );
      })}
    </>
  );
};

// ══ 8. 사진 패널 슬라이드업 ════════════════════════════════════════════════
// ref1 5:26(325.6s) — 우측 절반 흑백 인물사진 패널 상단 924→150(774px) 14f sine-out, 오버슈트 없음. 이후 인용 문구 블러 페이드.
export const PhotoPanelParams = z.object({
  len: num(14, 1, 60, 1, "올라오는 길이", "timing", "f"),
  fromY: num(924, 0, 1300, 2, "시작 상단 Y", "motion", "px"),
  toY: num(150, 0, 1080, 2, "도착 상단 Y", "motion", "px"),
  textDelay: num(24, 0, 120, 1, "글자 등장 지연", "timing", "f"),
  textFade: num(8, 1, 40, 1, "글자 페이드", "timing", "f"),
  textBlur: num(12, 0, 40, 1, "글자 시작 블러", "look", "px"),
  bw: flag(true, "흑백", "look"),
  contrast: num(1.08, 0.5, 2, 0.02, "대비", "look"),
  panelBg: col("#222222", "패널 바탕색"),
});
export type PhotoPanelP = z.infer<typeof PhotoPanelParams>;
export const PhotoPanelSlideUp: React.FC<{ img: string; at: number; x?: number; w?: number; pos?: string; quote?: string; title?: string; p?: Partial<PhotoPanelP> }> = ({ img, at, x = 960, w = 960, pos = "50% 20%", quote, title, p }) => {
  const P = def(PhotoPanelParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const top = mix(P.fromY, P.toY, prog(f, at, P.len, SINE_O));
  const tA = at + P.len + P.textDelay;
  const to = f < tA ? 0 : prog(f, tA, P.textFade);
  return (
    <div style={{ position: "absolute", left: x, top, width: w, height: H - P.toY + 40, overflow: "hidden", background: P.panelBg }}>
      <Img src={src(img)} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: pos, filter: `${P.bw ? "grayscale(1)" : ""} contrast(${P.contrast})` }} />
      {(quote || title) && (
        <div style={{ position: "absolute", left: 0, right: 0, top: 470, textAlign: "center", opacity: to, filter: `blur(${(1 - to) * P.textBlur}px)`, color: "#161616", fontFamily: "Yeonsung", textShadow: "0 0 12px #fff, 0 0 6px #fff" }}>
          {quote && <div style={{ fontSize: 62 }}>“{quote}”</div>}
          {title && <div style={{ fontSize: 118, lineHeight: 1.1 }}>{hz(title)}</div>}
        </div>
      )}
    </div>
  );
};

// ══ 9. 흰 윤곽선 흑백 인물 컷아웃 + 로고·왕관 ══════════════════════════════
// ref4-apple 01:07:12 — 흐리고 어두운 같은 장면 배경(#1d1d1d) 위 오른쪽 55% 흑백 컷아웃(흰 선 ~8px), 왼쪽 열 로고→왕관→타이틀 순차
export const WhiteStrokeCutoutParams = z.object({
  logoDelay: num(10, 0, 120, 1, "로고 등장 지연", "timing", "f"),
  crownDelay: num(30, 0, 150, 1, "왕관 등장 지연", "timing", "f"),
  titleDelay: num(46, 0, 180, 1, "타이틀 등장 지연", "timing", "f"),
  cutoutX: num(830, 0, 1600, 10, "컷아웃 왼쪽 X", "motion", "px"),
  cutoutTop: num(115, 0, 800, 5, "컷아웃 위쪽 Y", "motion", "px"),
  colX: num(440, 100, 1000, 5, "왼쪽 열 중심 X", "motion", "px"),
  stroke: num(8, 0, 30, 1, "흰 윤곽선 두께", "size", "px"),
  logoSize: num(130, 40, 260, 2, "로고 글자 크기", "size", "px"),
  crownSize: num(180, 40, 400, 5, "왕관 크기", "size", "px"),
  titleSize: num(120, 40, 220, 2, "타이틀 크기", "size", "px"),
  bgBlur: num(18, 0, 60, 1, "배경 블러", "look", "px"),
  bgBright: num(0.22, 0, 1, 0.01, "배경 밝기", "look"),
  logoColor: col("#1F6FB5", "로고 색"),
  bw: flag(true, "인물 흑백", "look"),
});
export type WhiteStrokeCutoutP = z.infer<typeof WhiteStrokeCutoutParams>;
/** 세모지 그림체 왕관(kit crown). color 는 호환용(무시) */
export const Crown: React.FC<{ size: number; color?: string }> = ({ size }) => (
  <Img src={prop("crown")} style={{ display: "block", width: size, height: propH("crown", size) }} />
);
export const WhiteStrokeCutout: React.FC<{ img: string; bgImg?: string; logo: string; title: string; at: number; source?: string; p?: Partial<WhiteStrokeCutoutP> }> = ({ img, bgImg, logo, title, at, source, p }) => {
  const P = def(WhiteStrokeCutoutParams, p);
  const f = useCurrentFrame();
  const g = f - at;
  const logoO = g < P.logoDelay ? 0 : prog(f, at + P.logoDelay, 6);
  const cr = g < P.crownDelay ? 0 : kf(f, at + P.crownDelay, [0, 3, 5], [0.3, 1.12, 1], Easing.out(Easing.quad));
  const ti = g < P.titleDelay ? 0 : kf(f, at + P.titleDelay, [0, 2, 5, 7], [1.25, 1.15, 1.08, 1]);
  return (
    <AbsoluteFill style={{ background: "#1d1d1d", overflow: "hidden" }}>
      <Img src={src(bgImg || img)} style={{ position: "absolute", width: "120%", height: "120%", left: "-10%", top: "-10%", objectFit: "cover", filter: `blur(${P.bgBlur}px) grayscale(0.4) brightness(${P.bgBright})` }} />
      <Img src={src(img)} style={{ position: "absolute", left: P.cutoutX, top: P.cutoutTop, height: H - P.cutoutTop, filter: `${P.bw ? "grayscale(1) contrast(1.1)" : ""} ${strokeFilter(P.stroke)}` }} />
      <div style={{ position: "absolute", left: P.colX, top: 250, transform: "translateX(-50%)", display: "flex", flexDirection: "column", alignItems: "center", gap: 18 }}>
        <div style={{ opacity: logoO, fontFamily: "NeoHv", fontSize: P.logoSize, color: P.logoColor, letterSpacing: -2, lineHeight: 1 }}>{logo}</div>
        <div style={{ transform: `scale(${cr})`, opacity: cr > 0 ? 1 : 0 }}><Crown size={P.crownSize} /></div>
        <div style={{ opacity: ti > 0 ? 1 : 0, transform: `scale(${ti || 1})`, fontFamily: "NeoHv", fontSize: P.titleSize, color: "#fff", whiteSpace: "nowrap", lineHeight: 1 }}>{hz(title)}</div>
      </div>
      {source && <SourceChip text={source} at={at} />}
    </AbsoluteFill>
  );
};

// ══ 10. 탑승권 소품 드롭 ═══════════════════════════════════════════════════
// ref4-apple 01:22:02 — 머스터드 배경, 탑승권 2장(앞 흰+오렌지 스텁 / 뒤 어긋난 장)이 위에서 ~10f 떨어지며 +6°→0°, 느린 푸시인, 손이 우하단에서 들어와 집어감
// 세모지 그림체 탑승권(boarding_pass_front) 위에 글자만 코드로 — 회색 자리표시 막대를 종이색으로 덮고 그 자리에 인쇄
const Ticket: React.FC<{ w: number; h: number; name: string; flight: string; dest: string; stub: string }> = ({ w, h, name, flight, dest, stub }) => {
  const k = h / 330, IW = 1434, IH = 637;
  const mk = `url(${prop("boarding_pass_front")})`;
  const F: React.FC<{ l: number; t: number; wd: number; ht: number; s: number; b?: boolean; c?: string; bg?: string; children: RN }> = ({ l, t, wd, ht, s, b, c = "#222", bg = "#F7F3EF", children }) => (
    <div style={{ position: "absolute", left: `${(l / IW) * 100}%`, top: `${(t / IH) * 100}%`, width: `${(wd / IW) * 100}%`, height: `${(ht / IH) * 100}%`, background: bg, display: "flex", alignItems: "center", fontFamily: b ? "NeoHv" : "NeoEb", fontSize: s * k, color: c, whiteSpace: "nowrap", lineHeight: 1, overflow: "hidden" }}>{children}</div>
  );
  return (
    <div style={{ width: w, height: h, position: "relative", isolation: "isolate" }}>
      <Img src={prop("boarding_pass_front")} style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }} />
      <div style={{ position: "absolute", left: 0, top: 0, width: "100%", height: `${(120 / IH) * 100}%`, background: stub, mixBlendMode: "color", WebkitMaskImage: mk, maskImage: mk, WebkitMaskSize: `${w}px ${h}px`, maskSize: `${w}px ${h}px`, WebkitMaskRepeat: "no-repeat", maskRepeat: "no-repeat" } as React.CSSProperties} />
      <F l={66} t={0} wd={940} ht={118} s={22} b c="#fff" bg="transparent"><span style={{ flex: 1 }}>SEMOJI AIR</span><span>BOARDING PASS</span></F>
      <F l={62} t={164} wd={948} ht={76} s={46} b>{name}</F>
      <F l={62} t={278} wd={448} ht={74} s={36}>{flight}</F>
      <F l={564} t={278} wd={446} ht={74} s={20} b>BOARDING&nbsp;&nbsp;<span style={{ fontFamily: "NeoEb", fontSize: 24 * k }}>9 : 30 PM</span></F>
      <F l={62} t={395} wd={448} ht={74} s={24} b>GATE&nbsp;&nbsp;<span style={{ fontFamily: "NeoEb", fontSize: 28 * k }}>D 09</span></F>
      <F l={564} t={395} wd={446} ht={74} s={24} b>SEAT NO.&nbsp;&nbsp;<span style={{ fontFamily: "NeoEb", fontSize: 28 * k }}>C 33</span></F>
      <F l={62} t={507} wd={948} ht={74} s={36} b>도착지 : {dest}</F>
      <F l={1104} t={166} wd={290} ht={62} s={24}>{flight}</F>
      <F l={1104} t={252} wd={290} ht={62} s={18} b>도착지 : {dest}</F>
      <F l={1104} t={337} wd={290} ht={62} s={16}>TERMINAL 01</F>
    </div>
  );
};
export const BoardingPassParams = z.object({
  dropLen: num(10, 1, 40, 1, "떨어지는 길이", "timing", "f"),
  dropFrom: num(800, 0, 1600, 10, "떨어지는 높이", "motion", "px"),
  rot0: num(6, -30, 30, 0.5, "착지 전 기울기", "motion", "°"),
  backRot: num(-4, -20, 20, 0.5, "뒷장 어긋남 각도", "motion", "°"),
  pushTo: num(1.05, 1, 1.4, 0.01, "푸시인 배율", "motion", "배"),
  pushLen: num(90, 1, 300, 1, "푸시인 길이", "timing", "f"),
  handAt: num(45, 0, 300, 1, "손 등장(착지 후)", "timing", "f"),
  handLen: num(12, 1, 40, 1, "손 들어오는 길이", "timing", "f"),
  grabHold: num(8, 0, 60, 1, "집은 뒤 멈춤", "timing", "f"),
  exitLen: num(12, 1, 40, 1, "집어가는 길이", "timing", "f"),
  ticketW: num(860, 300, 1400, 10, "탑승권 폭", "size", "px"),
  ticketH: num(330, 120, 600, 5, "탑승권 높이", "size", "px"),
  bg: col("#D09A40", "배경색"),
  stub: col("#F2A531", "스텁(오렌지) 색"),
  backColor: col("#4A4A4A", "뒷장 색"),
});
export type BoardingPassP = z.infer<typeof BoardingPassParams>;
export const BoardingPassDrop: React.FC<{ at: number; name: string; flight: string; dest: string; grab?: boolean; p?: Partial<BoardingPassP> }> = ({ at, name, flight, dest, grab = true, p }) => {
  const P = def(BoardingPassParams, p);
  const f = useCurrentFrame();
  const g = f - at;
  const e = prog(f, at, P.dropLen, Easing.out(Easing.cubic));
  const land = at + P.dropLen;
  const push = mix(1, P.pushTo, prog(f, land, P.pushLen, SINE_IO));
  const hA = land + P.handAt, gA = hA + P.handLen + P.grabHold;
  const he = prog(f, hA, P.handLen, Easing.out(Easing.cubic));
  const ex = grab ? prog(f, gA, P.exitLen, Easing.in(Easing.cubic)) : 0;
  const cx = W / 2, cy = 500;
  const tw = P.ticketW, th = P.ticketH;
  const hx = mix(W + 250, cx + tw * 0.28, he) + ex * 900, hy = mix(H + 300, cy + th * 0.42, he) + ex * 700;
  const ty = -(1 - e) * P.dropFrom + ex * 700, tx = ex * 900;
  return (
    <AbsoluteFill style={{ background: P.bg, overflow: "hidden" }}>
      <AbsoluteFill style={{ transform: `scale(${push})` }}>
        {g >= 0 && (
          <div style={{ position: "absolute", left: cx - tw / 2, top: cy - th / 2, width: tw, height: th, transform: `translate(${tx}px,${ty}px) rotate(${mix(P.rot0, 0, e)}deg)` }}>
            <div style={{ position: "absolute", inset: 0, transform: `translate(-14px,22px) rotate(${P.backRot}deg)`, background: P.backColor, WebkitMaskImage: `url(${prop("boarding_pass_back")})`, maskImage: `url(${prop("boarding_pass_back")})`, WebkitMaskSize: "100% 100%", maskSize: "100% 100%" } as React.CSSProperties} />
            <div style={{ position: "absolute", inset: 0, filter: "drop-shadow(0 8px 10px rgba(0,0,0,0.25))" }}><Ticket w={tw} h={th} name={name} flight={flight} dest={dest} stub={P.stub} /></div>
          </div>
        )}
        {/* 세모지 손: 다가올 땐 편 손(hand_open), 닿으면 집는 손(hand_grip) — 앵커 = 손바닥/집는 점 */}
        {f >= hA && (f >= hA + P.handLen
          ? <KitImg id="hand_grip" x={hx} y={hy} w={300} ax={0.35} ay={0.22} />
          : <KitImg id="hand_open" x={hx} y={hy} w={250} ax={0.45} ay={0.45} rot={-35} />)}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ══ 11. 엑스레이 실루엣 투시 ═══════════════════════════════════════════════
// ref4-apple 02:35:45(9345s 부근, 도감 표기 02:35:30) — 어두운 대리석 배경, 작은 전신 회색 투시체 → 몸통으로 푸시인,
// 분홍 병변 덩어리 5개가 차례로 팝 + ±5% 펄스, 마지막엔 옷 입은 인물로 디졸브(또는 얼굴로 틸트업)
const Marble: React.FC<{ seed?: number }> = ({ seed = 4 }) => (
  <svg width={W} height={H} style={{ position: "absolute", inset: 0 }}>
    <filter id="xmarble"><feTurbulence type="fractalNoise" baseFrequency="0.0035 0.006" numOctaves={5} seed={seed} />
      <feColorMatrix values="0 0 0 0.42 0  0 0 0 0.42 0  0 0 0 0.42 0  0 0 0 0 1" />
      <feComponentTransfer><feFuncR type="gamma" exponent={2.2} amplitude={1.1} /><feFuncG type="gamma" exponent={2.2} amplitude={1.1} /><feFuncB type="gamma" exponent={2.2} amplitude={1.1} /></feComponentTransfer>
    </filter>
    <rect width={W} height={H} filter="url(#xmarble)" />
  </svg>
);
const Cluster: React.FC<{ d: number; color: string }> = ({ d, color }) => {
  const r = d / 5.2;
  const pts: [number, number][] = [[0, 0], ...Array.from({ length: 6 }, (_, i) => [Math.cos((i * Math.PI) / 3) * r * 1.7, Math.sin((i * Math.PI) / 3) * r * 1.7] as [number, number]),
    ...Array.from({ length: 6 }, (_, i) => [Math.cos((i * Math.PI) / 3 + 0.5) * r * 3, Math.sin((i * Math.PI) / 3 + 0.5) * r * 3] as [number, number])];
  return <g>{pts.map(([x, y], i) => <g key={i}><circle cx={x} cy={y} r={r} fill={color} stroke="rgba(120,20,60,0.6)" strokeWidth={r * 0.18} /><circle cx={x - r * 0.25} cy={y - r * 0.25} r={r * 0.28} fill="rgba(255,255,255,0.35)" /></g>)}</g>;
};
export const XrayParams = z.object({
  zoomLen: num(24, 1, 90, 1, "몸통으로 푸시인 길이", "timing", "f"),
  clusterAt: num(20, 0, 120, 1, "병변 첫 등장(시작 후)", "timing", "f"),
  clusterStagger: num(8, 0, 40, 1, "병변 간격", "timing", "f"),
  clusterPop: num(5, 1, 20, 1, "병변 팝 길이", "timing", "f"),
  pulsePeriod: num(30, 4, 120, 1, "펄스 주기", "timing", "f"),
  endAt: num(100, 20, 400, 1, "마무리 시작(시작 후)", "timing", "f"),
  endLen: num(15, 1, 60, 1, "마무리 길이", "timing", "f"),
  endMode: choice("dissolve", ["dissolve", "tiltUp"] as const, "마무리(디졸브/얼굴로 틸트업)", "motion"),
  zoomFrom: num(0.42, 0.2, 1, 0.01, "시작 배율(전신)", "motion", "배"),
  pulse: num(0.05, 0, 0.3, 0.01, "펄스 세기(±)", "motion"),
  clusterD: num(90, 30, 200, 2, "병변 지름", "size", "px"),
  clusterN: num(5, 1, 5, 1, "병변 개수", "size"),
  bodyColor: col("#8C8C8C", "투시체 색"),
  bodyAlpha: num(0.8, 0, 1, 0.05, "투시체 불투명도", "look"),
  boneColor: col("#FFFFFF", "뼈 색"),
  clusterColor: col("#E0457B", "병변 색"),
});
export type XrayP = z.infer<typeof XrayParams>;
const CLUSTERS: [number, number][] = [[420, 470], [590, 560], [455, 720], [575, 860], [410, 980]];
export const XraySilhouette: React.FC<{ at: number; reveal?: RN; p?: Partial<XrayP> }> = ({ at, reveal, p }) => {
  const P = def(XrayParams, p);
  const f = useCurrentFrame();
  const g = f - at;
  const z = prog(f, at, P.zoomLen, Easing.inOut(Easing.cubic));
  const s = mix(P.zoomFrom, 1, z);
  let fy = mix(800, 760, z);
  const endT = prog(f, at + P.endAt, P.endLen, Easing.inOut(Easing.cubic));
  if (P.endMode === "tiltUp") fy = mix(fy, 330, endT);
  // 세모지 그림체 투시체(xray_body_silhouette) + 골격(xray_skeleton), 로컬 좌표 1000×1700(몸 y 20→1620)
  const BH = 1600, bw = BH * (478 / 1181), sw_ = BH * (459 / 1181);
  const mkB = `url(${prop("xray_body_silhouette")})`, mkS = `url(${prop("xray_skeleton")})`;
  const mask = (m: string): React.CSSProperties => ({ WebkitMaskImage: m, maskImage: m, WebkitMaskSize: "100% 100%", maskSize: "100% 100%", WebkitMaskRepeat: "no-repeat", maskRepeat: "no-repeat" } as React.CSSProperties);
  return (
    <AbsoluteFill style={{ background: "#0d0d0d", overflow: "hidden" }}>
      <Marble />
      <div style={{ position: "absolute", left: 0, top: 0, transformOrigin: "0 0", transform: `translate(960px,540px) scale(${s}) translate(-500px,${-fy}px)` }}>
        <div style={{ position: "absolute", left: 500 - bw / 2, top: 20, width: bw, height: BH, opacity: Math.min(1, P.bodyAlpha / 0.8), isolation: "isolate" }}>
          <Img src={prop("xray_body_silhouette")} style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }} />
          <div style={{ position: "absolute", inset: 0, background: P.bodyColor, mixBlendMode: "color", ...mask(mkB) }} />
        </div>
        <div style={{ position: "absolute", left: 500 - sw_ / 2, top: 20, width: sw_, height: BH, opacity: 0.6, isolation: "isolate" }}>
          <Img src={prop("xray_skeleton")} style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }} />
          <div style={{ position: "absolute", inset: 0, background: P.boneColor, mixBlendMode: "multiply", ...mask(mkS) }} />
        </div>
      <svg width={1000} height={1700} style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}>
        <g>
          {CLUSTERS.slice(0, Math.round(P.clusterN)).map(([x, y], i) => {
            const a = at + P.clusterAt + i * P.clusterStagger;
            if (f < a) return null;
            const pop = kf(f, a, [0, P.clusterPop * 0.6, P.clusterPop], [0, 1.12, 1], Easing.out(Easing.quad));
            const pu = 1 + P.pulse * Math.sin(((f - a) / P.pulsePeriod) * Math.PI * 2);
            return <g key={i} transform={`translate(${x} ${y}) scale(${pop * pu})`}><Cluster d={P.clusterD / Math.max(0.3, s) * 1.0} color={P.clusterColor} /></g>;
          })}
        </g>
      </svg>
      </div>
      {P.endMode === "dissolve" && reveal && g >= P.endAt && <AbsoluteFill style={{ opacity: endT }}>{reveal}</AbsoluteFill>}
    </AbsoluteFill>
  );
};

// ══ 12. 사료 사진 반투명 띠 제목 ═══════════════════════════════════════════
// ref4-hyundai 00:23:35 — 흑백 사료 위 전폭 반투명 검정 띠, 흰 제목 + 노랑 키워드, 화살표 회색 외곽→흰 채움 ~6f → 결과어 1.25→1 가로블러 팝 ~7f
export const TitleBandParams = z.object({
  arrowAt: num(12, 0, 120, 1, "화살표 채움 시작", "timing", "f"),
  arrowFill: num(6, 1, 30, 1, "화살표 채움 길이", "timing", "f"),
  resultAt: num(22, 0, 150, 1, "결과어 팝 시작", "timing", "f"),
  resultLen: num(7, 1, 30, 1, "결과어 팝 길이", "timing", "f"),
  resultFrom: num(1.25, 1, 2, 0.01, "결과어 시작 크기", "motion", "배"),
  resultBlur: num(8, 0, 40, 1, "결과어 가로블러", "look", "px"),
  bandTop: num(290, 0, 900, 5, "띠 위쪽 Y", "motion", "px"),
  bandH: num(260, 60, 700, 5, "띠 높이", "size", "px"),
  x: num(50, 0, 800, 5, "글자 왼쪽 X", "motion", "px"),
  titleSize: num(70, 30, 140, 1, "제목 크기", "size", "px"),
  kwSize: num(76, 30, 160, 1, "키워드 크기", "size", "px"),
  bandAlpha: num(0.5, 0, 1, 0.02, "띠 불투명도", "look"),
  kwColor: col("#F8E550", "키워드 색"),
  bw: flag(true, "사진 흑백", "look"),
});
export type TitleBandP = z.infer<typeof TitleBandParams>;
export const ArchiveTitleBand: React.FC<{ img: string; title: string; from: string; to?: string; at: number; source?: string; pos?: string; p?: Partial<TitleBandP> }> = ({ img, title, from, to, at, source, pos = "50% 40%", p }) => {
  const P = def(TitleBandParams, p);
  const f = useCurrentFrame();
  const g = f - at;
  const fill = prog(f, at + P.arrowAt, P.arrowFill, Easing.linear);
  const rA = at + P.resultAt;
  const rs = kf(f, rA, [0, (2 * P.resultLen) / 7, (5 * P.resultLen) / 7, P.resultLen], [P.resultFrom, 1 + (P.resultFrom - 1) * 0.6, 1 + (P.resultFrom - 1) * 0.32, 1]);
  const rb = kf(f, rA, [0, Math.max(1, P.resultLen * 0.45)], [P.resultBlur, 0]);
  const aw = P.kwSize * 1.9, ah = P.kwSize * 0.9;
  return (
    <AbsoluteFill style={{ background: "#111" }}>
      <Img src={src(img)} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: pos, filter: P.bw ? "grayscale(1) contrast(1.05)" : undefined }} />
      {g >= 0 && (
        <div style={{ position: "absolute", left: 0, right: 0, top: P.bandTop, height: P.bandH, background: `rgba(0,0,0,${P.bandAlpha})`, padding: `${P.bandH * 0.1}px ${P.x}px`, boxSizing: "border-box" }}>
          <div style={{ fontFamily: "NeoHv", fontSize: P.titleSize, color: "#fff", lineHeight: 1.2 }}>{hz(title)}</div>
          <div style={{ display: "flex", alignItems: "center", gap: P.kwSize * 0.4, marginTop: P.bandH * 0.05 }}>
            <span style={{ fontFamily: "NeoHv", fontSize: P.kwSize, color: P.kwColor }}>{hz(from)}</span>
            {to !== undefined && (
              <svg width={aw} height={ah} viewBox="0 0 190 90" style={{ overflow: "visible" }}>
                <defs><clipPath id="tbclip"><rect x={0} y={0} width={190 * fill} height={90} /></clipPath></defs>
                <path d="M4,28 L110,28 L110,4 L186,45 L110,86 L110,62 L4,62 Z" fill="none" stroke="#9A9A9A" strokeWidth={5} strokeLinejoin="round" />
                <path d="M4,28 L110,28 L110,4 L186,45 L110,86 L110,62 L4,62 Z" fill="#fff" clipPath="url(#tbclip)" />
              </svg>
            )}
            {to !== undefined && (
              <HBlur amt={f >= rA ? rb : 0} style={{ opacity: f >= rA ? 1 : 0, transform: `scale(${f >= rA ? rs : 1})`, transformOrigin: "0% 50%" }}>
                <span style={{ fontFamily: "NeoHv", fontSize: P.kwSize, color: P.kwColor, whiteSpace: "nowrap" }}>{hz(to)}</span>
              </HBlur>
            )}
          </div>
        </div>
      )}
      {source && <SourceChip text={source} at={at} />}
    </AbsoluteFill>
  );
};

// ══ 13. 방송 아카이브 영상 인서트 ══════════════════════════════════════════
// ref4-hyundai 00:35:20 / 00:57:40 — 저해상 흑백 뉴스필름을 전폭 크롭(또는 블러 채움), 우상단 방송 로고 유지 + 우하단 출처 칩
export const NewsreelParams = z.object({
  fit: choice("crop", ["crop", "blurFill"] as const, "맞춤(전폭 크롭/블러 채움)", "motion"),
  weave: num(1.5, 0, 10, 0.1, "필름 흔들림", "motion", "px"),
  ar: num(1.333, 1, 2.4, 0.01, "원본 화면비", "size"),
  logoSize: num(34, 14, 80, 1, "방송 로고 크기", "size", "px"),
  grain: num(0.14, 0, 0.6, 0.01, "필름 그레인", "look"),
  flicker: num(0.07, 0, 0.4, 0.01, "밝기 깜빡임", "look"),
  scan: num(0.08, 0, 0.4, 0.01, "주사선", "look"),
  vignette: num(0.4, 0, 1, 0.02, "비네트", "look"),
  logoOpacity: num(0.85, 0, 1, 0.05, "로고 불투명도", "look"),
  bw: flag(true, "흑백", "look"),
});
export type NewsreelP = z.infer<typeof NewsreelParams>;
export const ArchiveNewsreel: React.FC<{ img: string; logo?: string; source?: string; at?: number; pos?: string; p?: Partial<NewsreelP> }> = ({ img, logo = "아카이브TV", source, at = 0, pos = "50% 50%", p }) => {
  const P = def(NewsreelParams, p);
  const f = useCurrentFrame();
  const fl = 1 + (random(`nf${f}`) - 0.5) * 2 * P.flicker;
  const wx = (random(`nwx${f}`) - 0.5) * 2 * P.weave, wy = (random(`nwy${f}`) - 0.5) * 2 * P.weave;
  const look = `${P.bw ? "grayscale(1)" : ""} contrast(1.18) brightness(${fl})`;
  const boxW = P.fit === "crop" ? W : H * P.ar;
  return (
    <AbsoluteFill style={{ background: "#000", overflow: "hidden" }}>
      {P.fit === "blurFill" && <Img src={src(img)} style={{ position: "absolute", width: "120%", height: "120%", left: "-10%", top: "-10%", objectFit: "cover", filter: `blur(30px) ${look} brightness(0.6)` }} />}
      <div style={{ position: "absolute", left: (W - boxW) / 2, top: 0, width: boxW, height: H, overflow: "hidden", transform: `translate(${wx}px,${wy}px)` }}>
        <Img src={src(img)} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: pos, filter: `${look} blur(0.6px)` }} />
        <svg width={boxW} height={H} style={{ position: "absolute", inset: 0, opacity: P.grain, mixBlendMode: "overlay" }}>
          <filter id={`ng${f % 12}`}><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={f % 12} /><feColorMatrix type="saturate" values="0" /></filter>
          <rect width={boxW} height={H} filter={`url(#ng${f % 12})`} />
        </svg>
        <AbsoluteFill style={{ background: `repeating-linear-gradient(0deg, rgba(0,0,0,${P.scan}) 0 2px, transparent 2px 4px)` }} />
        <AbsoluteFill style={{ background: `radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(0,0,0,${P.vignette}) 100%)` }} />
      </div>
      <div style={{ position: "absolute", right: (W - boxW) / 2 + 60, top: 140, opacity: P.logoOpacity, display: "flex", alignItems: "center", gap: 10, color: "#fff", fontFamily: "NeoHv", fontSize: P.logoSize, textShadow: "0 0 6px rgba(0,0,0,0.6)" }}>
        <div style={{ width: P.logoSize * 0.9, height: P.logoSize * 0.9, borderRadius: "50%", border: `${P.logoSize * 0.14}px solid #fff` }} />{logo}
      </div>
      {source && f >= at && <SourceChip text={source} at={at} />}
    </AbsoluteFill>
  );
};

// ══ 14. 신문 스택 슬램 ═════════════════════════════════════════════════════
// ref4-hyundai 01:42:33 — 크고 반투명한 신문이 scale 2.2→1, 불투명 40→100%, 회전 유지, ~20f expo-out 으로 목재 책상 위에 쌓임, 스태거 ~40f
export const WoodBg: React.FC<{ base?: string; grain?: string }> = ({ base = "#8F6B47", grain = "#A07A52" }) => (
  <AbsoluteFill style={{ background: base }}>
    <svg width={W} height={H} style={{ position: "absolute", inset: 0 }}>
      {Array.from({ length: 13 }, (_, i) => {
        const y = i * 90 + random(`wd${i}`) * 40, a = 18 + random(`wa${i}`) * 22, ph = random(`wp${i}`) * 6;
        const d = Array.from({ length: 25 }, (_, k) => `${k ? "L" : "M"}${k * 80},${(y + Math.sin(k * 0.45 + ph) * a).toFixed(1)}`).join(" ");
        return <path key={i} d={d} stroke={grain} strokeWidth={10 + random(`ww${i}`) * 16} fill="none" opacity={0.55} strokeLinecap="round" />;
      })}
    </svg>
  </AbsoluteFill>
);
/** 세모지 그림체 신문(kit newspaper) — 폭 w 에 맞춰 위에서부터 h 만큼 보이게 자르고, 제호 칸(두 굵은 줄 사이)에 헤드라인만 코드로 */
export const Newspaper: React.FC<{ headline: string; w: number; h: number }> = ({ headline, w, h }) => {
  const ih = propH("newspaper", w), u = w / 620;
  return (
    <div style={{ width: w, height: h, position: "relative", overflow: "hidden", borderRadius: 4 * u }}>
      <Img src={prop("newspaper")} style={{ position: "absolute", left: 0, top: 0, width: w, height: ih }} />
      <div style={{ position: "absolute", left: w * 0.06, right: w * 0.06, top: ih * 0.075, height: ih * 0.14, display: "flex", alignItems: "center", fontFamily: "NeoHv", fontSize: 42 * u, color: "#222", whiteSpace: "nowrap" }}>{hz(headline)}</div>
    </div>
  );
};
export const NewspaperStackParams = z.object({
  len: num(20, 1, 60, 1, "슬램 길이", "timing", "f"),
  stagger: num(40, 0, 120, 1, "다음 신문 지연", "timing", "f"),
  from: num(2.2, 1, 4, 0.05, "시작 크기", "motion", "배"),
  op0: num(0.4, 0, 1, 0.05, "시작 불투명도", "look"),
  paperW: num(620, 200, 1200, 10, "신문 폭", "size", "px"),
  paperH: num(460, 150, 900, 10, "신문 높이", "size", "px"),
  shadow: num(0.35, 0, 1, 0.05, "그림자 진하기", "look"),
  woodBase: col("#8F6B47", "책상 색"),
  woodGrain: col("#A07A52", "나뭇결 색"),
});
export type NewspaperStackP = z.infer<typeof NewspaperStackParams>;
export const NewspaperSlamStack: React.FC<{ papers: { headline: string; x: number; y: number; rot: number }[]; at: number; p?: Partial<NewspaperStackP> }> = ({ papers, at, p }) => {
  const P = def(NewspaperStackParams, p);
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <WoodBg base={P.woodBase} grain={P.woodGrain} />
      {papers.map((pp, i) => {
        const a = at + i * P.stagger;
        if (f < a) return null;
        const e = prog(f, a, P.len, EXPO_OUT);
        return (
          <div key={i} style={{ position: "absolute", left: pp.x - P.paperW / 2, top: pp.y - P.paperH / 2, transform: `scale(${mix(P.from, 1, e)}) rotate(${pp.rot}deg)`, opacity: mix(P.op0, 1, e), filter: `drop-shadow(0 ${10 * e}px ${18 * e}px rgba(0,0,0,${P.shadow * e}))` }}>
            <Newspaper headline={pp.headline} w={P.paperW} h={P.paperH} />
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// ══ 15. 카드 결제 몽타주 ═══════════════════════════════════════════════════
// ref4-hyundai 01:50:36 — 서류 콜라주 + 단말기 고정, 손+회사 카드가 좌하단에서 ~20f ease-out, 탭하면 '구매 완료' 컷 + 영수증 ~6f, 손 퇴장 ~6f, 사이클 ~55f
export const CardSwipeParams = z.object({
  cycle: num(55, 20, 150, 1, "카드 한 장 사이클", "timing", "f"),
  enterLen: num(20, 1, 60, 1, "카드 들어오는 길이", "timing", "f"),
  exitLen: num(6, 1, 30, 1, "카드 나가는 길이", "timing", "f"),
  receiptLen: num(6, 1, 30, 1, "영수증 나오는 길이", "timing", "f"),
  termX: num(1180, 400, 1700, 10, "단말기 중심 X", "motion", "px"),
  termY: num(420, 200, 800, 10, "단말기 중심 Y", "motion", "px"),
  cardW: num(520, 200, 900, 10, "카드 폭", "size", "px"),
  cardH: num(300, 100, 600, 10, "카드 높이", "size", "px"),
  bg: col("#243A5E", "배경색"),
  termColor: col("#4B4E52", "단말기 색"),
  screenColor: col("#1B2238", "화면 색"),
});
export type CardSwipeP = z.infer<typeof CardSwipeParams>;
export const CardSwipeMontage: React.FC<{ cards: { name: string; color: string }[]; at: number; screenText?: string; docTitle?: string; p?: Partial<CardSwipeP> }> = ({ cards, at, screenText = "구매\n완료", docTitle = "세모지상사\n주식", p }) => {
  const P = def(CardSwipeParams, p);
  const f = useCurrentFrame();
  const g = f - at;
  const c = Math.max(0, Math.min(cards.length - 1, Math.floor(g / P.cycle)));
  const gc = g - c * P.cycle;
  const TH = 640, TW = TH * (752 / 1287), tx = P.termX - TW / 2, ty = P.termY - TH / 2;
  const tapX = P.termX - 330, tapY = P.termY - 60;
  const e = prog(gc, 0, P.enterLen, Easing.out(Easing.cubic));
  const x = gc >= P.cycle - P.exitLen ? prog(gc, P.cycle - P.exitLen, P.exitLen, Easing.in(Easing.cubic)) : 0;
  const t = g < 0 ? 0 : e * (1 - x);
  const cx = mix(tapX - 900, tapX, t), cy = mix(tapY + 700, tapY, t);
  const lastExit = c === cards.length - 1 && gc >= P.cycle;
  const showText = g >= 0 && (gc >= P.enterLen || (c > 0 && gc < P.enterLen - 6));
  const rc = gc >= P.enterLen ? prog(gc, P.enterLen, P.receiptLen) : c > 0 && gc < P.enterLen - 6 ? 1 : 0;
  const card = cards[c];
  return (
    <AbsoluteFill style={{ background: P.bg, overflow: "hidden" }}>
      {/* 세모지 그림체 서류 콜라주·서류 한 장·단말기·영수증·카드·손(뒤 집는 손 + 카드 앞 엄지) */}
      <KitImg id="paper_docs_collage" x={250} y={500} w={760} rot={-6} style={{ filter: "drop-shadow(0 6px 14px rgba(0,0,0,0.25))" }} />
      <KitImg id="paper_docs_collage" x={1680} y={860} w={640} rot={-14} flip style={{ filter: "drop-shadow(0 6px 14px rgba(0,0,0,0.25))" }} />
      <KitImg id="paper_sheet" x={1680} y={320} w={600} rot={8} style={{ filter: "drop-shadow(0 6px 14px rgba(0,0,0,0.25))" }} />
      <div style={{ position: "absolute", left: 1480, top: 110, transform: "rotate(12deg)", fontFamily: "NeoHv", fontSize: 64, color: "#111", whiteSpace: "pre", textAlign: "center", lineHeight: 1.15 }}>{docTitle}</div>
      {/* 영수증 */}
      <div style={{ position: "absolute", left: P.termX - 140, top: ty + TH - 30, width: 280, height: 170, overflow: "hidden" }}>
        <Img src={prop("receipt_strip")} style={{ position: "absolute", left: 0, top: 170 - propH("receipt_strip", 280), width: 280, height: propH("receipt_strip", 280), transform: `translateY(${-(1 - rc) * 170}px)`, filter: "drop-shadow(0 4px 8px rgba(0,0,0,0.2))" }} />
      </div>
      <div style={{ position: "absolute", left: tx, top: ty, width: TW, height: TH, filter: "drop-shadow(0 16px 30px rgba(0,0,0,0.4))" }}>
        <Img src={prop("card_terminal")} style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }} />
        <div style={{ position: "absolute", left: "15.5%", top: "8%", width: "69%", height: "29%", borderRadius: 10, background: showText ? P.screenColor : "transparent", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontFamily: "NeoHv", fontSize: 60, whiteSpace: "pre", textAlign: "center", lineHeight: 1.15 }}>{showText ? screenText : ""}</div>
      </div>
      {g >= 0 && !lastExit && card && (
        <>
          <KitImg id="hand_pinch_back" x={cx - P.cardW * 0.36} y={cy + P.cardH * 0.08} w={460} ax={0.8} ay={0.2} />
          <div style={{ position: "absolute", left: cx - P.cardW / 2, top: cy - P.cardH / 2, width: P.cardW, height: P.cardH, transform: "rotate(-4deg)", filter: "drop-shadow(0 10px 20px rgba(0,0,0,0.3))", isolation: "isolate" }}>
            <Img src={prop("credit_card")} style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }} />
            <div style={{ position: "absolute", inset: 0, background: card.color, mixBlendMode: "color", WebkitMaskImage: `url(${prop("credit_card")})`, maskImage: `url(${prop("credit_card")})`, WebkitMaskSize: "100% 100%", maskSize: "100% 100%" } as React.CSSProperties} />
            <div style={{ position: "absolute", right: 34, top: 22, fontFamily: "NeoHv", fontSize: 46, color: "#fff" }}>{card.name}</div>
          </div>
          <KitImg id="hand_thumb_front" x={cx - P.cardW * 0.5 - 20} y={cy + P.cardH * 0.2} w={230} ax={0.02} ay={0.5} rot={-4} />
        </>
      )}
    </AbsoluteFill>
  );
};

// ══ 16. 원문 문서 줌인 + 빨간 밑줄 ═════════════════════════════════════════
// ref4-hyundai 02:04:56 — 좌측 썸네일(~290×390)이 ~14f 확대(가로 모션블러, 옆 제목은 블러아웃) → 느린 세로 스크롤,
// 빨간 밑줄(#E53935 ~4px) 행마다 좌→우 ~4f, 스태거 ~8f, 대상 행 막대 금색 #C9A227
export type DocRow = { label: string; value: number; hi?: boolean; avg?: boolean };
export const DocZoomParams = z.object({
  zoomLen: num(14, 1, 60, 1, "확대 길이", "timing", "f"),
  ulAt: num(12, 0, 120, 1, "첫 밑줄(확대 후)", "timing", "f"),
  ulLen: num(4, 1, 30, 1, "밑줄 긋는 길이", "timing", "f"),
  ulStagger: num(8, 0, 60, 1, "밑줄 간격", "timing", "f"),
  scrollLen: num(120, 1, 400, 1, "스크롤 길이", "timing", "f"),
  scrollPx: num(160, 0, 1500, 10, "스크롤 거리", "motion", "px"),
  zoomBlur: num(30, 0, 120, 2, "확대 모션블러", "look", "px"),
  thumbX: num(60, 0, 1500, 5, "썸네일 X", "motion", "px"),
  thumbY: num(60, 0, 900, 5, "썸네일 Y", "motion", "px"),
  thumbW: num(290, 100, 900, 5, "썸네일 폭", "size", "px"),
  zoomScale: num(1.3, 0.5, 3, 0.05, "확대 후 배율", "size", "배"),
  ulWidth: num(4, 1, 16, 1, "밑줄 두께", "size", "px"),
  ulColor: col("#E53935", "밑줄 색"),
  hiColor: col("#C9A227", "강조 막대 색"),
  barColor: col("#2F7D86", "막대 색"),
  bg: col("#8E8E8E", "확대 전 배경"),
});
export type DocZoomP = z.infer<typeof DocZoomParams>;
const PW = 1100, ROW = 50, HEAD = 200;
const DocPage: React.FC<{ title: string; rows: DocRow[]; P: DocZoomP }> = ({ title, rows, P }) => {
  const max = Math.max(...rows.map((r) => r.value));
  return (
    <div style={{ width: PW, height: HEAD + rows.length * ROW + 80, background: "#fff", position: "relative" }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 60, textAlign: "center", fontFamily: "NeoHv", fontSize: 40, color: "#333" }}>{title}</div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 120, textAlign: "center", fontFamily: "NeoEb", fontSize: 22, color: "#666" }}>(1,000점 만점 기준)</div>
      {rows.map((r, i) => {
        const y = HEAD + i * ROW;
        return (
          <React.Fragment key={i}>
            <div style={{ position: "absolute", left: 0, width: 240, top: y + 8, textAlign: "right", fontFamily: "NeoEb", fontSize: 24, color: "#333" }}>{r.label}</div>
            <div style={{ position: "absolute", left: 260, top: y + 8, height: 30, width: (r.value / max) * 700, background: r.hi ? P.hiColor : r.avg ? "#B5B5B5" : P.barColor }} />
            <div style={{ position: "absolute", left: 272 + (r.value / max) * 700, top: y + 10, fontFamily: "NeoEb", fontSize: 22, color: "#333" }}>{r.value}</div>
          </React.Fragment>
        );
      })}
    </div>
  );
};
export const DocZoomUnderline: React.FC<{ at: number; title: string[]; docTitle: string; rows: DocRow[]; marks: number[]; p?: Partial<DocZoomP> }> = ({ at, title, docTitle, rows, marks, p }) => {
  const P = def(DocZoomParams, p);
  const f = useCurrentFrame();
  const z = prog(f, at, P.zoomLen, Easing.inOut(Easing.cubic));
  const zEnd = at + P.zoomLen;
  const ts = P.thumbW / PW;
  const sc = mix(ts, P.zoomScale, z);
  const scroll = P.scrollPx * prog(f, zEnd, P.scrollLen, SINE_IO);
  const left = mix(P.thumbX, 60, z), top = mix(P.thumbY, 20, z) - scroll;
  const mb = Math.sin(Math.PI * z) * P.zoomBlur;
  const page = <DocPage title={docTitle} rows={rows} P={P} />;
  return (
    <AbsoluteFill style={{ background: "#fff", overflow: "hidden" }}>
      <AbsoluteFill style={{ background: P.bg, opacity: 1 - z }}>
        <div style={{ position: "absolute", left: 0, top: 0, transform: "scale(1.9)", transformOrigin: "0 0", filter: "blur(16px)", opacity: 0.45 }}>{page}</div>
        <div style={{ position: "absolute", left: 820, top: 250, filter: `blur(${z * 20}px)`, fontFamily: "NeoHv", color: "#fff", textAlign: "center", width: 900 }}>
          {title.map((t, i) => <div key={i} style={{ fontSize: i === 0 ? 110 : 76, lineHeight: 1.2 }}>{hz(t)}</div>)}
        </div>
      </AbsoluteFill>
      <HBlur amt={mb} style={{ position: "absolute", left, top, transform: `scale(${sc})`, transformOrigin: "0 0", boxShadow: z < 0.9 ? `0 6px 20px rgba(0,0,0,${0.3 * (1 - z)})` : undefined }}>
        {page}
        {marks.map((ri, k) => {
          const a = zEnd + P.ulAt + k * P.ulStagger;
          const w = prog(f, a, P.ulLen, Easing.linear);
          const r = rows[ri];
          if (!r || w <= 0) return null;
          const full = 280 + (r.value / Math.max(...rows.map((q) => q.value))) * 700 + 60;
          return <div key={k} style={{ position: "absolute", left: 20, top: HEAD + ri * ROW + 42, width: full * w, height: P.ulWidth / P.zoomScale * 1.3, background: P.ulColor }} />;
        })}
      </HBlur>
    </AbsoluteFill>
  );
};

// ══ 17. 붓자국 마스크 인물 + 손글씨 타자 인용 ═══════════════════════════════
// ref4-samsung 00:56:03 — 캐릭터 옆 크림 종이 카드(알파 ~8f), 손글씨 인용 1글자/≈3f, 실사 인물은 거친 붓 마스크로 알파 ~20f + 블러→선명
export const BrushQuoteParams = z.object({
  cardFade: num(8, 0, 40, 1, "종이 카드 페이드", "timing", "f"),
  typeAt: num(10, 0, 120, 1, "타자 시작", "timing", "f"),
  perChar: num(3, 1, 12, 0.5, "글자당 프레임", "timing", "f"),
  photoAt: num(4, 0, 120, 1, "사진 등장", "timing", "f"),
  photoFade: num(20, 1, 60, 1, "사진 알파 길이", "timing", "f"),
  cardW: num(620, 300, 1100, 10, "카드 폭", "size", "px"),
  cardH: num(600, 200, 900, 10, "카드 높이", "size", "px"),
  textSize: num(40, 20, 80, 1, "글자 크기", "size", "px"),
  brush: num(60, 0, 160, 2, "붓 가장자리 거칠기", "look", "px"),
  photoBlur: num(8, 0, 30, 1, "사진 시작 블러", "look", "px"),
  cardColor: col("#F3DFC4", "카드 색"),
  textColor: col("#5A3A22", "글자 색"),
  bg: col("#C9D5CE", "배경색"),
});
export type BrushQuoteP = z.infer<typeof BrushQuoteParams>;
export const BrushMaskQuote: React.FC<{ char: string; photo: string; quote: string; at: number; photoPos?: string; p?: Partial<BrushQuoteP> }> = ({ char, photo, quote, at, photoPos = "50% 20%", p }) => {
  const P = def(BrushQuoteParams, p);
  const f = useCurrentFrame();
  const g = f - at;
  const co = g < 0 ? 0 : P.cardFade > 0 ? prog(f, at, P.cardFade, Easing.linear) : 1;
  const chars = Array.from(quote);
  const n = g < P.typeAt ? 0 : Math.min(chars.length, Math.floor((g - P.typeAt) / P.perChar) + 1);
  const po = g < P.photoAt ? 0 : prog(f, at + P.photoAt, P.photoFade, Easing.inOut(Easing.quad));
  const pw = 560, ph = 860;
  const m = roughMask(pw, ph, { inset: P.brush * 0.9, scale: P.brush, freq: 0.03, seed: 5, bleed: { t: true } });
  return (
    <AbsoluteFill style={{ background: P.bg }}>
      <Img src={src(char)} style={{ position: "absolute", left: 80, bottom: 0, height: 900 }} />
      <div style={{ position: "absolute", left: 560, top: 150, width: P.cardW, height: P.cardH, background: P.cardColor, borderRadius: 14, opacity: co, padding: "44px 46px", boxSizing: "border-box", fontFamily: "Yeonsung", fontSize: P.textSize, color: P.textColor, whiteSpace: "pre-wrap", lineHeight: 1.45 }}>
        {hz(chars.slice(0, n).join(""))}
      </div>
      <div style={{ position: "absolute", left: 1260, top: 120, width: pw, height: ph, opacity: po, filter: `blur(${(1 - po) * P.photoBlur}px)`, ...maskStyle(m) }}>
        <Img src={src(photo)} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: photoPos }} />
      </div>
    </AbsoluteFill>
  );
};

// ══ 18. 실사 광고 클립 종이 배경 삽입 ══════════════════════════════════════
// ref4-samsung 01:10:10 — 크림 종이 배경 중앙 박스(≈1050×590, 그림자 없음)에 옛 광고 재생 + 박스 우상단 옆 해시태그 캡션. 하드컷.
export const ArchivalAdParams = z.object({
  tagDelay: num(6, 0, 90, 1, "해시태그 등장 지연", "timing", "f"),
  tagStagger: num(4, 0, 30, 1, "해시태그 줄 간격(시간)", "timing", "f"),
  kenBurns: num(1.05, 1, 1.3, 0.01, "영상 줌(느린 확대)", "motion", "배"),
  kbLen: num(150, 10, 600, 5, "줌 길이", "timing", "f"),
  boxW: num(1050, 400, 1700, 10, "박스 폭", "size", "px"),
  boxH: num(590, 200, 1000, 10, "박스 높이", "size", "px"),
  boxCy: num(470, 200, 800, 5, "박스 중심 Y", "motion", "px"),
  tagSize: num(34, 14, 70, 1, "해시태그 크기", "size", "px"),
  bg: col("#FEF9F6", "종이 배경색"),
  tagColor: col("#111111", "해시태그 색"),
  shadow: flag(false, "박스 그림자", "look"),
});
export type ArchivalAdP = z.infer<typeof ArchivalAdParams>;
export const ArchivalAdOnPaper: React.FC<{ img: string; tags: string[]; at: number; pos?: string; p?: Partial<ArchivalAdP> }> = ({ img, tags, at, pos = "50% 50%", p }) => {
  const P = def(ArchivalAdParams, p);
  const f = useCurrentFrame();
  const g = f - at;
  if (g < 0) return <AbsoluteFill style={{ background: P.bg }} />;
  const kb = mix(1, P.kenBurns, prog(f, at, P.kbLen, Easing.linear));
  const bx = (W - P.boxW) / 2, by = P.boxCy - P.boxH / 2;
  return (
    <AbsoluteFill style={{ background: P.bg }}>
      <div style={{ position: "absolute", left: bx, top: by, width: P.boxW, height: P.boxH, overflow: "hidden", boxShadow: P.shadow ? "0 10px 30px rgba(0,0,0,0.25)" : undefined }}>
        <Img src={src(img)} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: pos, transform: `scale(${kb})` }} />
      </div>
      <div style={{ position: "absolute", left: bx + P.boxW + 28, top: by + 30, fontFamily: "Yeonsung", fontSize: P.tagSize, color: P.tagColor, lineHeight: 1.5 }}>
        {tags.map((t, i) => (g >= P.tagDelay + i * P.tagStagger ? <div key={i}>{hz(t)}</div> : null))}
      </div>
    </AbsoluteFill>
  );
};

// ══ 19. 등롱 흔들림 ═════════════════════════════════════════════════════════
// ref1 13:59(839~857s) — 상단에 매달린 붉은 등롱·매듭 장식이 ±3°, 약 2초(60f) 주기로 흔들림
export const LanternSwayParams = z.object({
  period: num(60, 10, 240, 1, "흔들림 주기", "timing", "f"),
  amp: num(3, 0, 20, 0.5, "흔들림 각도(±)", "motion", "°"),
  phaseSpread: num(1.2, 0, 6.3, 0.1, "등롱마다 위상 차", "motion"),
  n: num(7, 1, 16, 1, "등롱 개수", "size"),
  size: num(110, 30, 300, 2, "등롱 크기", "size", "px"),
  sizeVar: num(0.3, 0, 0.8, 0.05, "크기 차이", "size"),
  cordLen: num(60, 0, 400, 5, "줄 길이", "size", "px"),
  color: col("#D8232A", "등롱 색"),
  rib: col("#A5161C", "살 색"),
  gold: col("#E8B64A", "장식 금색"),
});
export type LanternSwayP = z.infer<typeof LanternSwayParams>;
/** 세모지 그림체 홍등(xm_lantern_red). color/rib/gold 는 호환용 — 줄·매듭만 코드 색 사용 */
export const Lantern: React.FC<{ size: number; color: string; rib: string; gold: string }> = ({ size }) => (
  <Img src={prop("xm_lantern_red")} style={{ display: "block", width: size, height: size * (1467 / 904) }} />
);
export const LanternSway: React.FC<{ y0?: number; x0?: number; x1?: number; p?: Partial<LanternSwayP> }> = ({ y0 = 0, x0 = 120, x1 = 1800, p }) => {
  const P = def(LanternSwayParams, p);
  const f = useCurrentFrame();
  const n = Math.round(P.n);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {Array.from({ length: n }, (_, i) => {
        const x = n === 1 ? (x0 + x1) / 2 : x0 + ((x1 - x0) * i) / (n - 1);
        const sz = P.size * (i % 2 ? 1 - P.sizeVar : 1);
        const cl = P.cordLen * (i % 2 ? 1.6 : 1);
        const rot = P.amp * Math.sin((f / P.period) * Math.PI * 2 + i * P.phaseSpread);
        return (
          <div key={i} style={{ position: "absolute", left: x, top: y0, transformOrigin: "0 0", transform: `rotate(${rot}deg)` }}>
            <div style={{ position: "absolute", left: -2, top: 0, width: 4, height: cl, background: P.gold }} />
            <div style={{ position: "absolute", left: -9, top: cl * 0.45, width: 18, height: 18, background: P.color, transform: "rotate(45deg)" }} />
            <div style={{ position: "absolute", left: -sz / 2, top: cl }}><Lantern size={sz} color={P.color} rib={P.rib} gold={P.gold} /></div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// ══ 20. 반짝이 점 명멸 ═════════════════════════════════════════════════════
// ref1 12:35–12:57 — 항아리 표면 등 영역에 흰 점 8~15개(6~12px)가 약 1초(30f) 주기로 무작위 명멸
export const SparkleDotsParams = z.object({
  period: num(30, 4, 120, 1, "명멸 주기", "timing", "f"),
  n: num(12, 1, 60, 1, "점 개수", "size"),
  sizeMin: num(6, 1, 40, 1, "최소 크기", "size", "px"),
  sizeMax: num(12, 1, 60, 1, "최대 크기", "size", "px"),
  glow: num(8, 0, 40, 1, "글로우", "look", "px"),
  peak: num(1, 0, 1, 0.05, "최대 밝기", "look"),
  color: col("#FFFFFF", "점 색"),
});
export type SparkleDotsP = z.infer<typeof SparkleDotsParams>;
export const SparkleDots: React.FC<{ rect: [number, number, number, number]; at?: number; seed?: string; p?: Partial<SparkleDotsP> }> = ({ rect, at = 0, seed = "sd", p }) => {
  const P = def(SparkleDotsParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const g = f - at;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {Array.from({ length: Math.round(P.n) }, (_, k) => {
        const ph = random(`${seed}p${k}`);
        const tt = g / P.period + ph;
        const cyc = Math.floor(tt), u = tt - cyc;
        const x = rect[0] + random(`${seed}x${k}_${cyc}`) * rect[2], y = rect[1] + random(`${seed}y${k}_${cyc}`) * rect[3];
        const s = mix(P.sizeMin, P.sizeMax, random(`${seed}s${k}_${cyc}`));
        const o = Math.pow(Math.sin(Math.PI * u), 2) * P.peak;
        return <div key={k} style={{ position: "absolute", left: x - s / 2, top: y - s / 2, width: s, height: s, borderRadius: "50%", background: P.color, opacity: o, boxShadow: `0 0 ${P.glow}px ${P.glow / 3}px ${P.color}` }} />;
      })}
    </AbsoluteFill>
  );
};

// ══ 21. 반복 오브젝트 벽지 ═════════════════════════════════════════════════
// ref4-apple 00:59:50 — 연분홍 #f8dede 위 사과 ~110px 엇갈린 격자(가로 ~200, 세로 ~170, 행마다 반 칸), 정적
/** 세모지 그림체 사과(kit apple_icon) */
export const AppleIcon: React.FC<{ size: number }> = ({ size }) => (
  <Img src={prop("apple_icon")} style={{ display: "block", width: size, height: size, objectFit: "contain" }} />
);
export const WallpaperParams = z.object({
  driftX: num(0, -10, 10, 0.1, "가로 흐름 속도", "motion", "px/f"),
  driftY: num(0, -10, 10, 0.1, "세로 흐름 속도", "motion", "px/f"),
  rowShift: num(0.5, 0, 1, 0.05, "행마다 어긋남(칸)", "motion"),
  rot: num(0, -45, 45, 1, "오브젝트 기울기", "motion", "°"),
  size: num(150, 20, 400, 2, "오브젝트 크기", "size", "px"),
  dx: num(270, 40, 800, 5, "가로 간격", "size", "px"),
  dy: num(230, 40, 800, 5, "세로 간격", "size", "px"),
  bg: col("#F8DEDE", "배경색"),
  speckle: num(0.06, 0, 0.3, 0.01, "종이 얼룩 질감", "look"),
});
export type WallpaperP = z.infer<typeof WallpaperParams>;
export const RepeatObjectWallpaper: React.FC<{ img?: string; icon?: RN; p?: Partial<WallpaperP> }> = ({ img, icon, p }) => {
  const P = def(WallpaperParams, p);
  const f = useCurrentFrame();
  const ox = ((f * P.driftX) % (P.dx * 2) + P.dx * 2) % (P.dx * 2), oy = ((f * P.driftY) % (P.dy * 2) + P.dy * 2) % (P.dy * 2);
  const cols = Math.ceil(W / P.dx) + 4, rows = Math.ceil(H / P.dy) + 4;
  const obj = img ? <Img src={src(img)} style={{ width: P.size, height: P.size, objectFit: "contain" }} /> : icon || <AppleIcon size={P.size} />;
  return (
    <AbsoluteFill style={{ background: P.bg, overflow: "hidden" }}>
      {P.speckle > 0 && (
        <svg width={W} height={H} style={{ position: "absolute", inset: 0, opacity: P.speckle }}>
          <filter id="wpsp"><feTurbulence type="fractalNoise" baseFrequency="0.012" numOctaves={3} seed={9} /><feColorMatrix values="0 0 0 0 0.6  0 0 0 0 0.3  0 0 0 0 0.3  0 0 0 1.4 -0.5" /></filter>
          <rect width={W} height={H} filter="url(#wpsp)" />
        </svg>
      )}
      {Array.from({ length: rows }, (_, r) => Array.from({ length: cols }, (_, c) => {
        const x = (c - 2) * P.dx + (r % 2) * P.dx * P.rowShift + ox, y = (r - 2) * P.dy + oy;
        return <div key={`${r}_${c}`} style={{ position: "absolute", left: x, top: y, transform: `rotate(${P.rot}deg)` }}>{obj}</div>;
      }))}
    </AbsoluteFill>
  );
};

// ══ 22. 최면 소용돌이(나선 터널) 배경 ══════════════════════════════════════
// ref4-apple 01:16:45(4606s) — 보라·자주·핑크 나선이 가운데로 빨려드는 터널 모양으로 천천히 회전. 방사형 광선 아님.
export const SpiralTunnelParams = z.object({
  speed: num(1.5, -10, 10, 0.1, "회전 속도", "motion", "°/f"),
  arms: num(2, 1, 6, 1, "나선 팔 개수", "size"),
  turns: num(4, 1, 16, 0.5, "감긴 횟수", "size"),
  tight: num(1.6, 0.6, 3, 0.05, "중심 조임(터널감)", "size"),
  cx: num(960, 0, 1920, 5, "중심 X", "motion", "px"),
  cy: num(540, 0, 1080, 5, "중심 Y", "motion", "px"),
  colorA: col("#C02A7A", "나선 색(자주)"),
  colorHi: col("#FF5FAE", "나선 밝은 색(핑크)"),
  colorB: col("#5A1A6A", "바탕 색(보라)"),
  colorCore: col("#140414", "중심 색"),
});
export type SpiralTunnelP = z.infer<typeof SpiralTunnelParams>;
export const SpiralTunnelBg: React.FC<{ children?: RN; id?: string; p?: Partial<SpiralTunnelP> }> = ({ children, id = "st", p }) => {
  const P = def(SpiralTunnelParams, p);
  const f = useCurrentFrame();
  const arms = Math.round(P.arms), T = P.turns * Math.PI * 2, R = 1500, N = 260;
  const band = (ph: number) => {
    const pts: string[] = [];
    for (let i = 0; i <= N; i++) { const th = (i / N) * T, r = R * Math.pow(th / T, P.tight); pts.push(`${(Math.cos(th + ph) * r).toFixed(1)},${(Math.sin(th + ph) * r).toFixed(1)}`); }
    // 바깥 끝은 화면 밖 큰 원호로 닫는다(현(chord)으로 닫으면 화면을 가로지르는 이음새가 생김)
    for (let j = 0; j <= 12; j++) { const a = T + ph + (j / 12) * (Math.PI / arms); pts.push(`${(Math.cos(a) * 4200).toFixed(1)},${(Math.sin(a) * 4200).toFixed(1)}`); }
    for (let i = N; i >= 0; i--) { const th = (i / N) * T, r = R * Math.pow(th / T, P.tight); pts.push(`${(Math.cos(th + ph + Math.PI / arms) * r).toFixed(1)},${(Math.sin(th + ph + Math.PI / arms) * r).toFixed(1)}`); }
    return "M" + pts.join(" L") + "Z";
  };
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <svg width={W} height={H} style={{ position: "absolute", inset: 0 }}>
        <defs>
          <radialGradient id={`${id}a`} cx={0} cy={0} r={1100} gradientUnits="userSpaceOnUse">
            <stop offset="0" stopColor={P.colorCore} /><stop offset="0.25" stopColor={P.colorA} /><stop offset="0.5" stopColor={P.colorHi} /><stop offset="1" stopColor={P.colorA} />
          </radialGradient>
          <radialGradient id={`${id}b`} cx={0} cy={0} r={1100} gradientUnits="userSpaceOnUse">
            <stop offset="0" stopColor={P.colorCore} /><stop offset="0.4" stopColor={P.colorB} /><stop offset="1" stopColor={P.colorB} />
          </radialGradient>
        </defs>
        <g transform={`translate(${P.cx} ${P.cy})`}>
          <rect x={-3000} y={-3000} width={6000} height={6000} fill={`url(#${id}b)`} />
          <g transform={`rotate(${f * P.speed})`}>
            {Array.from({ length: arms }, (_, k) => <path key={k} d={band((2 * Math.PI * k) / arms)} fill={`url(#${id}a)`} />)}
          </g>
        </g>
      </svg>
      {children}
    </AbsoluteFill>
  );
};

// ══ 23. 분노 불꽃 배경 루프 ════════════════════════════════════════════════
// ref4-apple 00:37:10 — 배경 전체를 #f05030 위 짙은 빨강·주황·노랑 만화 불꽃 혀로, 아래→위로 일렁이는 ~12–15f 루프(블러 약간)
const flamePath = (w: number, h: number, sway: number) =>
  `M${-w / 2},0 C${-w / 2},${-h * 0.45} ${-w * 0.05},${-h * 0.5} ${sway * w},${-h} C${w * 0.2},${-h * 0.62} ${w / 2},${-h * 0.42} ${w / 2},0 Q0,${h * 0.22} ${-w / 2},0Z`;
export const FireBgParams = z.object({
  loop: num(14, 4, 60, 1, "일렁임 루프", "timing", "f"),
  rise: num(1, 0, 4, 0.05, "위로 흐르는 속도(배)", "motion", "배"),
  sway: num(0.25, 0, 0.8, 0.01, "불꽃 끝 휘어짐", "motion"),
  flick: num(0.18, 0, 0.6, 0.01, "크기 떨림", "motion"),
  tongueW: num(230, 60, 600, 5, "불꽃 폭", "size", "px"),
  tongueH: num(360, 80, 900, 5, "불꽃 높이", "size", "px"),
  blur: num(3, 0, 20, 0.5, "블러", "look", "px"),
  bg: col("#F05030", "바탕색"),
  dark: col("#D8261B", "바깥 불꽃(짙은 빨강)"),
  orange: col("#F59A23", "가운데 불꽃(주황)"),
  yellow: col("#FBD23C", "안쪽 불꽃(노랑)"),
});
export type FireBgP = z.infer<typeof FireBgParams>;
export const FireBgLoop: React.FC<{ children?: RN; seed?: string; p?: Partial<FireBgP> }> = ({ children, seed = "fb", p }) => {
  const P = def(FireBgParams, p);
  const f = useCurrentFrame();
  const gapX = P.tongueW * 1.1, gapY = P.tongueH * 0.75;
  const rows = Math.ceil(H / gapY) + 3, cols = Math.ceil(W / gapX) + 2;
  const off = ((f * P.rise * gapY) / (P.loop * 3)) % gapY;
  const items: RN[] = [];
  for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
    const key = `${r}_${c}`;
    const jx = (random(`${seed}x${key}`) - 0.5) * gapX * 0.6, jy = (random(`${seed}y${key}`) - 0.5) * gapY * 0.4;
    const ph = random(`${seed}p${key}`) * Math.PI * 2;
    const k = 1 + P.flick * Math.sin((f / P.loop) * Math.PI * 2 + ph);
    const sw = P.sway * Math.sin((f / P.loop) * Math.PI * 2 + ph * 1.3) * (random(`${seed}d${key}`) > 0.5 ? 1 : -1);
    const x = c * gapX + (r % 2) * gapX * 0.5 + jx - gapX * 0.5, y = (r - 1) * gapY + jy - off + P.tongueH * 0.6;
    const w = P.tongueW * (0.75 + random(`${seed}w${key}`) * 0.5), h = P.tongueH * (0.75 + random(`${seed}h${key}`) * 0.5) * k;
    items.push(
      <g key={key} transform={`translate(${x.toFixed(1)} ${y.toFixed(1)})`}>
        <path d={flamePath(w, h, sw)} fill={P.dark} />
        <path d={flamePath(w * 0.62, h * 0.62, sw * 1.2)} fill={P.orange} transform={`translate(0 ${-h * 0.02})`} />
        <path d={flamePath(w * 0.3, h * 0.32, sw * 1.4)} fill={P.yellow} />
      </g>,
    );
  }
  return (
    <AbsoluteFill style={{ background: P.bg, overflow: "hidden" }}>
      <svg width={W} height={H} style={{ position: "absolute", inset: 0, filter: P.blur > 0 ? `blur(${P.blur}px)` : undefined }}>{items}</svg>
      {children}
    </AbsoluteFill>
  );
};

// ══ 24. 최면 나선 + 소용돌이 흡입 ══════════════════════════════════════════
// ref4-apple 02:21:03 — 원래 배경이 20f 디졸브로 짙은 회색 나선(#1A1A1A/#2A2A2A)으로, 사물 6개가 회전(±90°)+1.0→0.1 로 중심(≈520,330)에 ~40f ease-in 흡입
/** 세모지 그림체 구형 휴대폰(kit phone_bar_dark / phone_bar_light 번갈아) — 높이 size */
export const OldPhoneIcon: React.FC<{ size: number; v?: number }> = ({ size, v = 0 }) => {
  const id = v % 3 === 1 ? "phone_bar_dark" : "phone_bar_light";
  const [a, b] = propSize(id);
  return <Img src={prop(id)} style={{ display: "block", height: size, width: (size * a) / b }} />;
};
export const SpiralSuckParams = z.object({
  dissolveLen: num(20, 0, 60, 1, "배경 디졸브 길이", "timing", "f"),
  suckDelay: num(20, 0, 120, 1, "흡입 시작(디졸브 후)", "timing", "f"),
  suckLen: num(40, 4, 150, 1, "흡입 길이", "timing", "f"),
  spin: num(90, 0, 720, 5, "사물 회전(±)", "motion", "°"),
  orbit: num(160, 0, 720, 5, "빨려들며 도는 각도", "motion", "°"),
  scaleTo: num(0.1, 0, 1, 0.01, "끝 크기", "motion", "배"),
  cx: num(520, 0, 1920, 5, "흡입 중심 X", "motion", "px"),
  cy: num(330, 0, 1080, 5, "흡입 중심 Y", "motion", "px"),
  objSize: num(200, 40, 500, 5, "사물 크기", "size", "px"),
  n: num(6, 1, 12, 1, "사물 개수", "size"),
  spiralSpeed: num(1.2, -10, 10, 0.1, "나선 회전 속도", "motion", "°/f"),
  c1: col("#2A2A2A", "나선 밝은 색"),
  c2: col("#1A1A1A", "나선 어두운 색"),
});
export type SpiralSuckP = z.infer<typeof SpiralSuckParams>;
export const SpiralSuck: React.FC<{ at: number; from?: RN; objects?: string[]; children?: RN; p?: Partial<SpiralSuckP> }> = ({ at, from, objects, children, p }) => {
  const P = def(SpiralSuckParams, p);
  const f = useCurrentFrame();
  const dz = f < at ? 0 : P.dissolveLen > 0 ? prog(f, at, P.dissolveLen, Easing.linear) : 1;
  const sA = at + P.dissolveLen + P.suckDelay;
  const e = prog(f, sA, P.suckLen, Easing.in(Easing.cubic));
  const n = Math.round(P.n);
  return (
    <AbsoluteFill style={{ overflow: "hidden", background: P.c2 }}>
      <SpiralTunnelBg id="ssk" p={{ speed: P.spiralSpeed, arms: 1, turns: 7, tight: 1, cx: P.cx, cy: P.cy, colorA: P.c1, colorHi: P.c1, colorB: P.c2, colorCore: P.c2 }} />
      {from && <AbsoluteFill style={{ opacity: 1 - dz }}>{from}</AbsoluteFill>}
      {f >= at && e < 1 && Array.from({ length: n }, (_, i) => {
        const a0 = (i / n) * Math.PI * 2 + random(`ssa${i}`) * 0.6, r0 = 300 + random(`ssr${i}`) * 180;
        const r = r0 * (1 - e), a = a0 + (P.orbit * Math.PI / 180) * e;
        const x = P.cx + Math.cos(a) * r * 1.25, y = P.cy + Math.sin(a) * r * 0.85;
        const rot = (i % 2 ? 1 : -1) * P.spin * e + (random(`ssq${i}`) - 0.5) * 50;
        const s = mix(1, P.scaleTo, e);
        return (
          <div key={i} style={{ position: "absolute", left: x, top: y, transform: `translate(-50%,-50%) rotate(${rot}deg) scale(${s})`, opacity: (e > 0.9 ? (1 - e) / 0.1 : 1) * Math.min(1, dz * 1.5), filter: "drop-shadow(0 6px 8px rgba(0,0,0,0.5))" }}>
            {objects && objects.length ? <Img src={src(objects[i % objects.length])} style={{ height: P.objSize }} /> : <OldPhoneIcon size={P.objSize} v={i} />}
          </div>
        );
      })}
      {children}
    </AbsoluteFill>
  );
};

// ══ 25. 하늘 그라디언트 고도 상승 ══════════════════════════════════════════
// ref4-cocacola 00:19:20 — 로켓은 고정, 하늘만 핑크→노을→보라 황혼→딥틸(~30f), 구름층은 아래로 밀려나며 흰→하늘색 림, 연기 기둥은 길어짐, 동심원 글로우 링
export const SkyAscentParams = z.object({
  len: num(30, 4, 240, 1, "하늘색 변화 길이", "timing", "f"),
  rocketLen: num(30, 1, 120, 1, "로켓 내려오는 길이", "timing", "f"),
  cloudDrop: num(420, 0, 1000, 10, "구름 내려가는 거리", "motion", "px"),
  rocketFrom: num(-600, -1200, 0, 10, "로켓 시작 Y(위 밖)", "motion", "px"),
  rocketY: num(20, -300, 600, 5, "로켓 도착 위쪽 Y", "motion", "px"),
  rocketH: num(620, 200, 1000, 10, "로켓 높이", "size", "px"),
  ringGap: num(170, 40, 400, 5, "동심원 간격", "size", "px"),
  ringAlpha: num(0.07, 0, 0.3, 0.01, "동심원 진하기", "look"),
  c0: col("#E8406A", "하늘 1(핑크)"),
  c1: col("#F08A4B", "하늘 2(노을)"),
  c2: col("#6A4A8A", "하늘 3(황혼)"),
  c3: col("#1F4A5A", "하늘 4(딥틸)"),
  cloudRim: col("#BFEAF0", "구름 끝 색"),
});
export type SkyAscentP = z.infer<typeof SkyAscentParams>;
/** space_shuttle 이미지 안 노즐 x 비율(좌 부스터·주엔진·우 부스터) — 이미지가 좌우 비대칭이라 실측 */
const SHUTTLE_NOZZLES = [0.27, 0.53, 0.87];
/** 세모지 그림체 우주왕복선(kit space_shuttle) + 코드 불꽃(효과) — 높이 h, 폭 = 원본 비율 */
export const Shuttle: React.FC<{ h: number; flame?: number }> = ({ h, flame = 1 }) => {
  const [a, b] = propSize("space_shuttle"), w = (h * a) / b;
  return (
    <div style={{ position: "relative", width: w, height: h }}>
      <svg viewBox="0 0 100 100" width={w} height={h * 0.25} style={{ position: "absolute", left: 0, top: h * 0.95, overflow: "visible" }} preserveAspectRatio="none">
        {SHUTTLE_NOZZLES.map((x, i) => <path key={i} d={`M${x * 100 - 7},0 Q${x * 100},${(i === 1 ? 55 : 75) * flame} ${x * 100 + 7},0Z`} fill={i === 1 ? "#FFE08A" : "#FFB347"} />)}
      </svg>
      <Img src={prop("space_shuttle")} style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }} />
    </div>
  );
};
const Clouds: React.FC<{ color: string; rim: string; y: number }> = ({ color, rim, y }) => (
  <svg width={W} height={600} style={{ position: "absolute", left: 0, top: y }}>
    {[[40, 220, 200], [260, 170, 170], [470, 240, 150], [1450, 230, 160], [1650, 170, 190], [1880, 220, 170], [980, 330, 140], [1200, 300, 150], [760, 300, 150]].map(([x, yy, r], i) => (
      <g key={i}><circle cx={x} cy={yy} r={r + 10} fill={rim} /><circle cx={x} cy={yy + 8} r={r} fill={color} /></g>
    ))}
    <rect x={0} y={300} width={W} height={400} fill={color} />
  </svg>
);
export const SkyGradientAscent: React.FC<{ at: number; rocket?: RN; children?: RN; p?: Partial<SkyAscentP> }> = ({ at, rocket, children, p }) => {
  const P = def(SkyAscentParams, p);
  const f = useCurrentFrame();
  const t = prog(f, at, P.len, Easing.inOut(Easing.quad));
  const re = prog(f, at, P.rocketLen, Easing.out(Easing.cubic));
  const sky = rampHex([P.c0, P.c1, P.c2, P.c3], t);
  const skyLow = rampHex([P.c0, P.c1, P.c2, P.c3], Math.max(0, t - 0.12));
  const ry = mix(P.rocketFrom, P.rocketY, re);
  const smokeTop = ry + P.rocketH * 0.9;
  // 기본 로켓(키트 이미지)은 두 부스터 중점을 화면 중앙에 두고 연기 기둥을 부스터에 맞춘다
  const rw = (P.rocketH * propSize("space_shuttle")[0]) / propSize("space_shuttle")[1];
  const rLeft = rocket ? 960 - P.rocketH / 4 : 960 - ((SHUTTLE_NOZZLES[0] + SHUTTLE_NOZZLES[2]) / 2) * rw;
  const smokeX = (d: number) => rocket ? 960 + d * P.rocketH * 0.2 : rLeft + SHUTTLE_NOZZLES[d < 0 ? 0 : 2] * rw;
  return (
    <AbsoluteFill style={{ background: `linear-gradient(180deg, ${sky} 0%, ${skyLow} 100%)`, overflow: "hidden" }}>
      <svg width={W} height={H} style={{ position: "absolute", inset: 0 }}>
        {Array.from({ length: 12 }, (_, i) => <circle key={i} cx={960} cy={540} r={(12 - i) * P.ringGap} fill={`rgba(255,255,255,${P.ringAlpha * (i % 2)})`} />)}
        {Array.from({ length: 40 }, (_, i) => <circle key={"s" + i} cx={random(`sx${i}`) * W} cy={random(`sy${i}`) * H} r={1.5 + random(`sr${i}`) * 2.5} fill="#fff" opacity={Math.max(0, t - 0.6) * 2.2} />)}
      </svg>
      {[-1, 1].map((d) => (
        <div key={d} style={{ position: "absolute", left: smokeX(d) - 22, top: smokeTop, width: 44, height: Math.max(0, H - smokeTop + 200), background: "linear-gradient(180deg, rgba(255,255,255,0.95), rgba(220,245,250,0.9))", borderRadius: 22 }} />
      ))}
      <Clouds color={mixHex("#FFFFFF", "#E6F7FA", t)} rim={mixHex("#FFFFFF", P.cloudRim, t)} y={H * 0.62 + t * P.cloudDrop} />
      <div style={{ position: "absolute", left: rLeft, top: ry }}>{rocket || <Shuttle h={P.rocketH} flame={0.7 + 0.3 * Math.sin(f * 1.7)} />}</div>
      {children}
    </AbsoluteFill>
  );
};

// ══ 26. 눈 내림 파티클 루프 + 뒤뚱 워크인 리그 ═════════════════════════════
// ref4-cocacola 00:23:37 — 청록 #1a9a82 + 설원, 눈송이 3층(반지름 3/6/10, 낙하 1.5/2.5/4px/f, 좌우 흔들림 ~8px, 큰 눈 블러),
// 캐릭터가 왼쪽 밖에서 ~15f 뒤뚱 입장(±5° 기울임 + scaleY 까딱) 후 정지·말풍선 팝
export const SnowfallParams = z.object({
  v1: num(1.5, 0, 10, 0.1, "작은 눈 낙하 속도", "motion", "px/f"),
  v2: num(2.5, 0, 10, 0.1, "중간 눈 낙하 속도", "motion", "px/f"),
  v3: num(4, 0, 12, 0.1, "큰 눈 낙하 속도", "motion", "px/f"),
  sway: num(8, 0, 40, 1, "좌우 흔들림", "motion", "px"),
  swayPeriod: num(60, 10, 240, 1, "흔들림 주기", "timing", "f"),
  r1: num(3, 1, 20, 0.5, "작은 눈 반지름", "size", "px"),
  r2: num(6, 1, 30, 0.5, "중간 눈 반지름", "size", "px"),
  r3: num(10, 1, 40, 0.5, "큰 눈 반지름", "size", "px"),
  density: num(1, 0.1, 4, 0.1, "눈 양(배)", "size", "배"),
  bigBlur: num(1.5, 0, 8, 0.1, "큰 눈 블러", "look", "px"),
  bg: col("#1A9A82", "배경색"),
  ground: flag(true, "설원·나무 배경", "look"),
});
export type SnowfallP = z.infer<typeof SnowfallParams>;
export const SnowfallLoop: React.FC<{ children?: RN; seed?: string; p?: Partial<SnowfallP> }> = ({ children, seed = "sn", p }) => {
  const P = def(SnowfallParams, p);
  const f = useCurrentFrame();
  const layers = [[P.r1, P.v1, 60, 0], [P.r2, P.v2, 34, 0], [P.r3, P.v3, 14, P.bigBlur]] as const;
  const flakes = (li: number, front: boolean) => {
    const [r, v, n0, bl] = layers[li];
    return Array.from({ length: Math.round(n0 * P.density) }, (_, i) => {
      const k = `${seed}${li}_${i}`;
      const x0 = random(`${k}x`) * (W + 100) - 50, y0 = random(`${k}y`) * (H + 60);
      const y = ((y0 + f * v * (0.85 + random(`${k}v`) * 0.3)) % (H + 60)) - 30;
      const x = x0 + P.sway * Math.sin((f / P.swayPeriod) * Math.PI * 2 + random(`${k}p`) * 6.28);
      return <circle key={k} cx={x} cy={y} r={r} fill="#fff" opacity={front ? 0.95 : 0.85} style={bl ? { filter: `blur(${bl}px)` } : undefined} />;
    });
  };
  return (
    <AbsoluteFill style={{ background: P.bg, overflow: "hidden" }}>
      {P.ground && (
        <svg width={W} height={H} style={{ position: "absolute", inset: 0 }}>
          <path d="M-50,700 C300,420 700,480 1100,640 L1100,1100 L-50,1100Z" fill="rgba(255,255,255,0.14)" />
          {[[120, 520, 260], [300, 600, 200], [1650, 560, 240]].map(([x, y, h], i) => (
            <g key={i}><path d={`M${x},${y - h} L${x - h * 0.4},${y} L${x + h * 0.4},${y}Z`} fill={i % 2 ? "#2F9E57" : "#1E7C45"} /><path d={`M${x},${y - h} L${x - h * 0.16},${y - h * 0.6} L${x + h * 0.16},${y - h * 0.6}Z`} fill="#F4F6F2" /></g>
          ))}
          <path d="M-50,860 C400,780 900,900 1300,820 C1600,760 1800,800 1980,780 L1980,1100 L-50,1100Z" fill="#F4F6F2" />
        </svg>
      )}
      <svg width={W} height={H} style={{ position: "absolute", inset: 0 }}>{flakes(0, false)}{flakes(1, false)}</svg>
      {children}
      <svg width={W} height={H} style={{ position: "absolute", inset: 0 }}>{flakes(2, true)}</svg>
    </AbsoluteFill>
  );
};
export const WaddleInParams = z.object({
  len: num(15, 1, 90, 1, "걸어 들어오는 길이", "timing", "f"),
  stepPeriod: num(6, 2, 30, 1, "한 걸음 길이", "timing", "f"),
  tilt: num(5, 0, 25, 0.5, "뒤뚱 기울임(±)", "motion", "°"),
  bob: num(0.04, 0, 0.2, 0.005, "까딱 세기(scaleY)", "motion"),
  waveAmp: num(3, 0, 15, 0.5, "정지 후 흔들기 각도", "motion", "°"),
  wavePeriod: num(16, 4, 60, 1, "흔들기 주기", "timing", "f"),
  bubbleDelay: num(6, 0, 60, 1, "말풍선 지연(정지 후)", "timing", "f"),
});
export type WaddleInP = z.infer<typeof WaddleInParams>;
/** 리그: 이미지 캐릭터가 화면 밖에서 뒤뚱뒤뚱 걸어 들어와 멈추고 흔들며 말풍선을 띄운다 */
export const WaddleIn: React.FC<{ img: string; x: number; ground: number; h: number; at: number; fromX?: number; bubble?: string; p?: Partial<WaddleInP> }> = ({ img, x, ground, h, at, fromX = -400, bubble, p }) => {
  const P = def(WaddleInParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const e = prog(f, at, P.len, Easing.out(Easing.quad));
  const walking = f < at + P.len;
  const ph = ((f - at) / P.stepPeriod) * Math.PI;
  const rot = walking ? P.tilt * Math.sin(ph) : P.waveAmp * Math.sin(((f - at - P.len) / P.wavePeriod) * Math.PI * 2);
  const sy = walking ? 1 - P.bob * Math.abs(Math.sin(ph)) : 1;
  const bA = at + P.len + P.bubbleDelay;
  const cx = mix(fromX, x, e);
  return (
    <>
      <Img src={src(img)} style={{ position: "absolute", left: cx, top: ground - h, height: h, transform: `translateX(-50%) rotate(${rot}deg) scaleY(${sy})`, transformOrigin: "50% 100%" }} />
      {bubble && f >= bA && <Starburst text={bubble} x={x + h * 0.3} y={ground - h * 1.02} w={300} h={180} at={bA} size={48} color="#fff" p={{ popLen: 3, rot: -4 }} />}
    </>
  );
};

// ══ 27. 번개 지그재그 대결 분할 ════════════════════════════════════════════
// ref4-hyundai 00:42:26 — 좌 레드 #C0616B / 우 블루 #5F6BA8, 검정 번개(폭 ~40px, 3~4꺾임)가 위→아래로 가름(원본은 우상→좌하 기울기).
// 번개·배경 하드 등장 후 인물이 각 측면에서 ~8f 슬라이드인, 말풍선 버스트 2f 팝, 정적 홀드
export const LightningSplitParams = z.object({
  slideLen: num(8, 1, 40, 1, "인물 슬라이드 길이", "timing", "f"),
  bubbleDelay: num(14, 0, 120, 1, "왼쪽 말풍선 지연", "timing", "f"),
  bubble2Delay: num(40, 0, 180, 1, "오른쪽 말풍선 지연", "timing", "f"),
  bubblePop: num(2, 1, 10, 1, "말풍선 팝 길이", "timing", "f"),
  slideDist: num(320, 0, 1000, 10, "슬라이드 거리", "motion", "px"),
  topX: num(0.58, 0, 1, 0.01, "번개 위쪽 X(비율)", "motion"),
  botX: num(0.44, 0, 1, 0.01, "번개 아래쪽 X(비율)", "motion"),
  zig: num(95, 0, 300, 5, "꺾임 폭", "motion", "px"),
  kinks: num(4, 1, 10, 1, "꺾임 수", "size"),
  boltW: num(40, 4, 120, 2, "번개 폭", "size", "px"),
  flash: flag(true, "진입 흰 플래시(슬래시 대용)", "look"),
  left: col("#C0616B", "왼쪽 색"),
  right: col("#5F6BA8", "오른쪽 색"),
  bolt: col("#111111", "번개 색"),
});
export type LightningSplitP = z.infer<typeof LightningSplitParams>;
export const LightningVersusSplit: React.FC<{ at: number; leftChar?: RN; rightChar?: RN; leftSay?: string; rightSay?: string; p?: Partial<LightningSplitP> }> = ({ at, leftChar, rightChar, leftSay, rightSay, p }) => {
  const P = def(LightningSplitParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const k = Math.round(P.kinks) * 2;
  const pts: [number, number][] = Array.from({ length: k + 1 }, (_, i) => {
    const t = i / k;
    const x = mix(P.topX * W, P.botX * W, t) + (i === 0 || i === k ? 0 : (i % 2 ? 1 : -1) * P.zig);
    return [x, mix(-30, H + 30, t)];
  });
  const line = pts.map((q) => q.join(",")).join(" ");
  const e = prog(f, at + 1, P.slideLen, Easing.out(Easing.cubic));
  const fl = P.flash ? 1 - prog(f, at, 4, Easing.linear) : 0;
  return (
    <AbsoluteFill style={{ background: P.right, overflow: "hidden" }}>
      <svg width={W} height={H} style={{ position: "absolute", inset: 0 }}>
        <polygon points={`-10,-40 ${line} -10,${H + 40}`} fill={P.left} />
        <polyline points={line} fill="none" stroke={P.bolt} strokeWidth={P.boltW} strokeLinejoin="miter" strokeMiterlimit={10} />
      </svg>
      {leftChar && <AbsoluteFill style={{ transform: `translateX(${-(1 - e) * P.slideDist}px)` }}>{leftChar}</AbsoluteFill>}
      {rightChar && <AbsoluteFill style={{ transform: `translateX(${(1 - e) * P.slideDist}px)` }}>{rightChar}</AbsoluteFill>}
      {leftSay && <Starburst text={leftSay} x={560} y={600} w={360} h={250} at={at + P.bubbleDelay} size={46} rot={-10} p={{ popLen: P.bubblePop }} />}
      {rightSay && <Starburst text={rightSay} x={1370} y={420} w={330} h={240} at={at + P.bubble2Delay} size={46} rot={-6} p={{ popLen: P.bubblePop }} />}
      {fl > 0 && <AbsoluteFill style={{ background: "#fff", opacity: fl }} />}
    </AbsoluteFill>
  );
};

// ══ 28. 최면 동심 물결 배경 ════════════════════════════════════════════════
// ref4-hyundai 01:00:50 / 01:04:20 — 보라 2톤(#7B6FD6/#A89CF0 · #4F42B5/#8680ED) 굵은(~80–90px) 일렁이는 동심 링, 하드컷 진입, 매우 느린 회전/확장
export const RippleRingsParams = z.object({
  speed: num(0.2, -2, 2, 0.01, "회전 속도", "motion", "rev/s"),
  expand: num(0.6, -5, 5, 0.05, "퍼져나가는 속도", "motion", "px/f"),
  wobble: num(45, 0, 200, 1, "일렁임 세기", "motion", "px"),
  wobbleSpeed: num(0.03, 0, 0.3, 0.005, "일렁임 속도", "motion"),
  drift: num(0.14, 0, 1, 0.01, "링마다 중심 밀림(비율)", "motion"),
  cx: num(720, -200, 2100, 5, "중심 X", "motion", "px"),
  cy: num(260, -200, 1300, 5, "중심 Y", "motion", "px"),
  bandW: num(80, 20, 300, 2, "밴드 폭", "size", "px"),
  colorA: col("#7B6FD6", "색 1(보라)"),
  colorB: col("#A89CF0", "색 2(라벤더)"),
});
export type RippleRingsP = z.infer<typeof RippleRingsParams>;
export const RippleRingsBg: React.FC<{ children?: RN; p?: Partial<RippleRingsP> }> = ({ children, p }) => {
  const P = def(RippleRingsParams, p);
  const f = useCurrentFrame();
  const bw = P.bandW, shift = (((f * P.expand) % (2 * bw)) + 2 * bw) % (2 * bw);
  const N = Math.ceil(2600 / bw) + 2, rotA = (f / 30) * P.speed * Math.PI * 2 * 0.15, wt = f * P.wobbleSpeed;
  const paths: RN[] = [];
  for (let i = N; i >= 0; i--) {
    const r = i * bw + shift;
    if (r < 2) continue;
    const q = r / bw;
    const ox = P.cx + q * bw * P.drift * 0.9, oy = P.cy + q * bw * P.drift * 0.6;
    const amp = P.wobble * Math.min(1, r / 500);
    const M = 96, pts: [number, number][] = [];
    for (let j = 0; j < M; j++) {
      const a = (j / M) * Math.PI * 2;
      const rr = r * (1 + 0.18 * Math.sin(a * 1 + 0.7)) + amp * (0.55 * Math.sin(3 * a + wt + q * 0.25) + 0.45 * Math.sin(5 * a - 1.3 - wt * 0.7 + q * 0.4));
      pts.push([ox + Math.cos(a + rotA) * rr * 1.15, oy + Math.sin(a + rotA) * rr]);
    }
    const d = pts.map((pt, j) => {
      const nx = pts[(j + 1) % M];
      const mx = (pt[0] + nx[0]) / 2, my = (pt[1] + nx[1]) / 2;
      return `${j ? "" : `M${((pts[M - 1][0] + pt[0]) / 2).toFixed(1)},${((pts[M - 1][1] + pt[1]) / 2).toFixed(1)} `}Q${pt[0].toFixed(1)},${pt[1].toFixed(1)} ${mx.toFixed(1)},${my.toFixed(1)}`;
    }).join(" ") + "Z";
    paths.push(<path key={i} d={d} fill={i % 2 ? P.colorA : P.colorB} />);
  }
  return (
    <AbsoluteFill style={{ background: P.colorA, overflow: "hidden" }}>
      <svg width={W} height={H} style={{ position: "absolute", inset: 0 }}>{paths}</svg>
      {children}
    </AbsoluteFill>
  );
};

// 데모·외부용 재노출
export { Pill, SweatDrop };
