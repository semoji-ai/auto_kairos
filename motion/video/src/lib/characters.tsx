// 세모지 캐릭터 연기 / FX 어휘 — 레퍼런스 프레임 실측 사양을 컴포넌트화.
// 모든 좌표는 화면(1920×1080) 기준 절대 px. 결정론(remotion random) 전용.
import React from "react";
import { AbsoluteFill, Img, Easing, random, useCurrentFrame } from "remotion";
import { z } from "zod";
import { W, H, lerp, kf, textPop, EXPO_OUT, QUART_OUT, hz, src, GLOW } from "../fx";
import { num, col, flag, choice, def } from "../params/p";
import { prop, propH, propSize, CAST, CastId } from "./kit";
import { SemojiRig, RigPose } from "./semoji_rig";

type Pt = [number, number];
type RN = React.ReactNode;
const INK = "#1a1a1a";
const EASY = Easing.bezier(0.33, 0, 0.67, 1);
const TAU = Math.PI * 2;

/** undefined 가 아닌 개별 prop 만 골라 변수(P)에 반영 */
const given = <T extends object>(o: T): Partial<T> => Object.fromEntries(Object.entries(o).filter(([, v]) => v !== undefined)) as Partial<T>;
/** photoPop 일반화: from → (from+1)/2 → 1 → 1+over → 1+over·0.375 → 1 (dur f), 줌블러 blur→0 (dur·0.6 f).
 *  기본(0.4, 0.08, 5, 6) = photoPop 과 같은 곡선 */
const popCurve = (f: number, at: number, from = 0.4, over = 0.08, dur = 5, blur = 6) => {
  const d = Math.max(0.5, dur);
  return {
    s: kf(f, at, [0, 1, 2, 3, 4, 5].map((k) => (k * d) / 5), [from, (from + 1) / 2, 1, 1 + over, 1 + over * 0.375, 1]),
    blur: kf(f, at, [0, d * 0.6], [blur, 0]),
  };
};
/** 착지 스쿼시 3f: sy [1-q, 1-q·ky, 1], sx [1+q·2/3, 1+q·4/15, 1] */
const landSquash = (g: number, q: number, ky: number) => ({ sy: [1 - q, 1 - q * ky, 1][g], sx: [1 + (q * 2) / 3, 1 + (q * 4) / 15, 1][g] });

/** 핑퐁 이지이지: period 프레임마다 a↔b 왕복 (LayeredCover 까딱과 동일 곡선) */
export const pingPong = (f: number, period: number, a: number, b: number, phase = 0) => {
  const k = Math.max(0, f + phase);
  const seg = Math.floor(k / period), t = (k % period) / period;
  const e = EASY(t);
  return a + (b - a) * (seg % 2 === 0 ? e : 1 - e);
};
/** 발밑(ground) 기준으로 scaleY 된 캐릭터 위의 한 점 y 를 따라간다 */
export const bobbedY = (y: number, ground: number, sy: number) => ground - (ground - y) * sy;

const Full: React.FC<{ children: RN; style?: React.CSSProperties }> = ({ children, style }) => (
  <svg width={W} height={H} style={{ position: "absolute", left: 0, top: 0, overflow: "visible", pointerEvents: "none", ...style }}>{children}</svg>
);
const Body: React.FC<{ img?: string; children?: RN; glow?: boolean }> = ({ img, children, glow }) =>
  img ? <Img src={src(img)} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "contain", filter: glow ? GLOW : undefined }} />
    : <div style={{ position: "absolute", inset: 0 }}>{children}</div>;

// ══ 1. 마스코트화: 흰 장갑 손 + 검정 막대 다리 + 흰 운동화 ═══════════════════════
export type HandPose = "idle" | "wave" | "surprised" | "point";
const GAX = 58 / 112, GAY = 120 / 128; // 손목(커프 아래 중앙) 앵커 비율

/** 만화 흰 장갑 SVG (손가락 위쪽, 손목 아래). 외곽선은 '두꺼운 검정 → 흰 채움' 2패스로 합집합 윤곽 */
export const GloveSvg: React.FC<{ pose: HandPose; spread?: number }> = ({ pose, spread }) => {
  const sp = spread ?? (pose === "surprised" ? 16 : pose === "wave" ? 5 : 0);
  const cuff = <rect x={30} y={92} width={44} height={22} rx={8} />;
  const shapes = pose === "point" ? (
    <>
      <rect x={30} y={42} width={48} height={54} rx={20} />
      <rect x={33} y={2} width={17} height={58} rx={8.5} />
      {cuff}
    </>
  ) : (
    <>
      <rect x={26} y={44} width={52} height={52} rx={22} />
      <rect x={28} y={12} width={16} height={48} rx={8} transform={`rotate(${-sp} 36 56)`} />
      <rect x={43} y={5} width={16} height={54} rx={8} />
      <rect x={58} y={12} width={16} height={48} rx={8} transform={`rotate(${sp} 66 56)`} />
      <rect x={16} y={46} width={17} height={40} rx={8.5} transform={`rotate(${-34 - sp} 28 84)`} />
      {cuff}
    </>
  );
  return (
    <svg viewBox="-6 -6 112 128" width="100%" height="100%" style={{ overflow: "visible", display: "block" }}>
      <g fill={INK} stroke={INK} strokeWidth={10} strokeLinejoin="round">{shapes}</g>
      <g fill="#fff">{shapes}</g>
      <g stroke={INK} strokeWidth={3.5} strokeLinecap="round" fill="none">
        <path d="M32,100 L72,100" />
        {pose === "point" ? <path d="M56,62 L76,62 M56,78 L76,78" /> : <path d="M43,62 L43,80 M58,62 L58,80" />}
      </g>
      {pose === "point" && <rect x={22} y={58} width={40} height={16} rx={8} fill="#fff" stroke={INK} strokeWidth={4} />}
    </svg>
  );
};

/** 손목 앵커 (x,y) 에 장갑을 놓는다. rot=0 이면 손가락이 위, 시계방향 + */
export const Glove: React.FC<{ x: number; y: number; size: number; rot: number; pose: HandPose; mirror?: boolean; spread?: number }> = ({ x, y, size, rot, pose, mirror, spread }) => {
  const w = size, h = (size * 128) / 112;
  return (
    <div style={{ position: "absolute", left: x - w * GAX, top: y - h * GAY, width: w, height: h, transformOrigin: `${GAX * 100}% ${GAY * 100}%`, transform: `rotate(${rot}deg) scaleX(${mirror ? -1 : 1})`, filter: "drop-shadow(0 3px 3px rgba(0,0,0,0.25))" }}>
      <GloveSvg pose={pose} spread={spread} />
    </div>
  );
};

/** 세모지 그림체 운동화(kit sneaker). 앵커 (x,y) = 발목(뒤꿈치 위) — 기존 SVG 와 같은 자리에 신발 몸통이 오도록 실측 오프셋 */
const Sneaker: React.FC<{ x: number; y: number; w: number; mirror?: boolean }> = ({ x, y, w: w0, mirror }) => {
  const w = w0 * 1.15; // 이미지 신발은 SVG 보다 납작해 살짝 키움
  return <Img src={prop("sneaker")} style={{ position: "absolute", left: x - w * 0.3, top: y - w * 0.4, width: w, height: propH("sneaker", w), transformOrigin: `${w * 0.3}px ${w * 0.4}px`, transform: `scaleX(${mirror ? -1 : 1})`, filter: "drop-shadow(0 0 1.5px rgba(26,26,26,0.55))" }} />;
};

const HAND: Record<HandPose, { fx: number; fy: number; rot: number }> = {
  idle: { fx: 0.97, fy: 0.62, rot: 150 },
  wave: { fx: 0.95, fy: 0.4, rot: 30 },
  surprised: { fx: 0.99, fy: 0.34, rot: 45 },
  point: { fx: 0.97, fy: 0.52, rot: 90 },
};

export type MascotProps = {
  /** 발바닥(지면) 중앙 */ x: number; y: number;
  /** 몸(이미지) 박스 크기 — 이미지 비율에 맞출 것 */ w: number; h: number;
  img?: string; children?: RN; glow?: boolean;
  /** 등장 팝 프레임(생략 시 처음부터) */ at?: number;
  l?: HandPose; r?: HandPose;
  /** 포즈 스왑 스케줄(하드 1f 스왑) */ poses?: { at: number; l?: HandPose; r?: HandPose }[];
  legLen?: number; handSize?: number;
  /** 손목을 몸 가장자리에서 안쪽으로(비율) — 이미지 가장자리에 투명 여백이 있을 때 */ handInset?: number;
  handDy?: number; legGap?: number; idle?: boolean; seed?: string; flip?: boolean;
  push?: { at: number; dx: number; dur?: number; pose?: HandPose };
  drop?: { at: number; dur?: number; from?: number };
  /** 연출 변수(MascotParams) */ p?: Partial<MascotP>;
};
export const MascotParams = z.object({
  popFrom: num(0.4, 0, 1, 0.05, "등장 팝 시작 크기(배)", "motion"),
  popOver: num(0.08, 0, 0.5, 0.01, "등장 팝 오버슈트", "motion"),
  popDur: num(5, 1, 20, 1, "등장 팝 길이", "timing", "f"),
  bobPeriod: num(20, 2, 60, 1, "몸 까딱 주기", "timing", "f"),
  bobAmp: num(0.02, 0, 0.15, 0.005, "몸 까딱 깊이(배)", "motion"),
  idleSwing: num(7, 0, 45, 1, "대기 손 흔들림", "motion", "°"),
  waveAmp: num(26, 0, 90, 1, "손 흔들기 각도", "motion", "°"),
  wavePeriod: num(12, 2, 40, 1, "손 흔들기 주기", "timing", "f"),
  jitter: num(7, 0, 30, 1, "놀람 손 떨림 폭", "motion", "px"),
  pointPoke: num(6, 0, 40, 1, "가리키기 찌르기 거리", "motion", "px"),
  squash: num(0.15, 0, 0.5, 0.01, "착지 스쿼시 세기", "motion"),
  handK: num(0.3, 0.1, 0.8, 0.01, "손 크기(몸 폭 비)", "size"),
  legK: num(0.28, 0, 1, 0.01, "다리 길이(몸 높이 비)", "size"),
  legGap: num(0.1, 0, 0.4, 0.01, "다리 간격(몸 폭 비)", "size"),
});
export type MascotP = z.infer<typeof MascotParams>;
/** 아무 이미지/로고/스크린샷을 마스코트로: 장갑 손(idle/wave/surprised/point), 막대 다리, 운동화.
 *  idle: 몸 전체 scaleY 1.0↔0.98 (20f), 두 손은 독립 위상으로 흔들림. */
export const Mascot: React.FC<MascotProps> = (p) => {
  const P = def(MascotParams, { ...given({ legGap: p.legGap }), ...p.p });
  const f = useCurrentFrame();
  const { x, y, w, h, seed = "m" } = p;
  const legLen = p.legLen ?? h * P.legK;
  const hs = p.handSize ?? Math.max(64, w * P.handK);
  const inset = p.handInset ?? 0;
  if (p.drop ? f < p.drop.at : p.at !== undefined && f < p.at) return null;
  let tx = 0, ty = 0, sx = 1, sy = 1;
  const pop = !p.drop && p.at !== undefined ? popCurve(f, p.at, P.popFrom, P.popOver, P.popDur).s : 1;
  if (p.idle !== false) sy *= pingPong(f, P.bobPeriod, 1, 1 - P.bobAmp, Math.floor(random(seed + "ph") * P.bobPeriod));
  const sched = [...(p.poses ?? [])];
  if (p.push) { const s = p.push.pose ?? "surprised"; sched.push({ at: p.push.at, l: s, r: s }); }
  sched.sort((a, b) => a.at - b.at);
  let l: HandPose = p.l ?? "idle", r: HandPose = p.r ?? "idle";
  for (const q of sched) if (f >= q.at) { l = q.l ?? l; r = q.r ?? r; }
  if (p.drop) {
    const d = Math.max(1, p.drop.dur ?? 8), a = p.drop.at;
    ty = lerp(f, a, a + d, p.drop.from ?? -(y + 40), 0, Easing.out(Easing.quad));
    const g = f - a - d;
    if (g >= 0 && g < 3) { const q = landSquash(g, P.squash, 7 / 15); sy *= q.sy; sx *= q.sx; }
  }
  if (p.push) tx = lerp(f, p.push.at, p.push.at + Math.max(1, p.push.dur ?? 10), 0, p.push.dx, QUART_OUT);
  const lt = Math.max(7, w * 0.028), shoeW = Math.max(56, w * 0.2);
  const gap = P.legGap;
  const legTop = h * 0.94, footY = h + legLen - shoeW * 0.38;
  const hand = (side: "l" | "r", pose: HandPose) => {
    const q = HAND[pose], ph = random(`${seed}${side}`) * TAU;
    let rot = q.rot, dx = 0, dy = 0;
    if (pose === "idle") rot += P.idleSwing * Math.sin(f / 8 + ph);
    if (pose === "wave") rot += P.waveAmp * Math.sin((f / P.wavePeriod) * TAU + ph);
    if (pose === "surprised") { const st = Math.floor(f / 2); dx = (random(`${seed}${side}jx${st}`) - 0.5) * P.jitter; dy = (random(`${seed}${side}jy${st}`) - 0.5) * P.jitter; rot += dx; }
    if (pose === "point") dx = P.pointPoke * Math.max(0, Math.sin(f / 5 + ph));
    const wx = w * (q.fx - inset) + dx, wy = h * (q.fy + (p.handDy ?? 0)) + dy;
    return side === "r" ? <Glove key="r" x={wx} y={wy} size={hs} rot={rot} pose={pose} />
      : <Glove key="l" x={w - wx} y={wy} size={hs} rot={-rot} pose={pose} mirror />;
  };
  return (
    <div style={{ position: "absolute", left: x - w / 2, top: y - (h + legLen), width: w, height: h + legLen, transformOrigin: "50% 100%", transform: `translate(${tx}px,${ty}px) scale(${pop * sx * (p.flip ? -1 : 1)},${pop * sy})` }}>
      <svg width={w} height={h + legLen} style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}>
        {[0.5 - gap, 0.5 + gap].map((k, i) => <line key={i} x1={w * k} y1={legTop} x2={w * k} y2={footY} stroke={INK} strokeWidth={lt} strokeLinecap="round" />)}
      </svg>
      <Sneaker x={w * (0.5 - gap)} y={footY} w={shoeW} mirror />
      <Sneaker x={w * (0.5 + gap)} y={footY} w={shoeW} />
      <div style={{ position: "absolute", left: 0, top: 0, width: w, height: h }}><Body img={p.img} glow={p.glow}>{p.children}</Body></div>
      {hand("l", l)}{hand("r", r)}
    </div>
  );
};

/** 라이벌 등장: b 가 위에서 8f ease-out 낙하 + 2f 착지 스쿼시, 기존 a 는 +22%W 를 10f 밀려나며 손이 surprised 로 스왑 */
export const RivalEnterParams = z.object({
  pushDx: num(0.22 * W, -1200, 1200, 0.1, "밀려나는 거리", "motion", "px"),
  pushDelay: num(5, 0, 30, 1, "밀려남 지연", "timing", "f"),
  pushDur: num(10, 1, 40, 1, "밀려나는 시간", "timing", "f"),
  dropDur: num(8, 1, 40, 1, "낙하 시간", "timing", "f"),
  squash: num(0.15, 0, 0.5, 0.01, "착지 스쿼시 세기", "motion"),
  surprisePose: choice("surprised", ["surprised", "wave", "point", "idle"], "밀려날 때 손 포즈"),
});
export type RivalEnterP = z.infer<typeof RivalEnterParams>;
export const RivalEnter: React.FC<{ a: MascotProps; b: MascotProps; at: number; pushDx?: number; pushDelay?: number; p?: Partial<RivalEnterP> }> = ({ a, b, at, pushDx, pushDelay, p }) => {
  const P = def(RivalEnterParams, { ...given({ pushDx, pushDelay }), ...p });
  return (
    <>
      <Mascot {...a} push={{ at: at + P.pushDelay, dx: P.pushDx, dur: P.pushDur, pose: P.surprisePose }} />
      <Mascot {...b} drop={{ at, dur: P.dropDur }} p={{ squash: P.squash, ...b.p }} />
    </>
  );
};

// ══ 2. 로고 얼굴 가면 ════════════════════════════════════════════════════════
/** 캐릭터 얼굴 위 흰 타원 가면(얼굴폭 ~90%) + 로고/텍스트. ground·bob* 을 캐릭터와 같게 주면 까딱을 따라간다 */
export const LogoFaceMaskParams = z.object({
  popFrom: num(0.4, 0, 1, 0.05, "팝 시작 크기(배)", "motion"),
  popOver: num(0.08, 0, 0.5, 0.01, "팝 오버슈트", "motion"),
  popDur: num(5, 1, 20, 1, "팝 길이", "timing", "f"),
  popBlur: num(6, 0, 30, 1, "팝 줌블러", "look", "px"),
  bobPeriod: num(10, 2, 60, 1, "까딱 주기", "timing", "f"),
  bobAmp: num(0.01, 0, 0.1, 0.005, "까딱 깊이(배)", "motion"),
  cover: num(0.9, 0.3, 1.5, 0.01, "가면 폭(얼굴 폭 비)", "size"),
  ratio: num(1.12, 0.6, 2, 0.01, "가면 세로비", "size"),
  rot: num(0, -45, 45, 1, "기울기", "motion", "°"),
  rim: num(0.025, 0, 0.1, 0.005, "테두리 두께(가면 폭 비)", "size"),
  bg: col("#ffffff", "가면 색"),
  rimColor: col("#d9d9d9", "테두리 색"),
  color: col("#D62828", "글자 색"),
});
export type LogoFaceMaskP = z.infer<typeof LogoFaceMaskParams>;
export const LogoFaceMask: React.FC<{
  cx: number; cy: number; faceW: number; at?: number; ground?: number; bobPeriod?: number; bobAmp?: number; bobPhase?: number;
  img?: string; text?: string; color?: string; font?: string; size?: number; children?: RN; ratio?: number; rot?: number; cover?: number; p?: Partial<LogoFaceMaskP>;
}> = ({ cx, cy, faceW, at = 0, ground, bobPeriod, bobAmp, bobPhase = 0, img, text, color, font = "Jalnan", size, children, ratio, rot, cover, p }) => {
  const P = def(LogoFaceMaskParams, { ...given({ bobPeriod, bobAmp, color, ratio, rot, cover }), ...p });
  const f = useCurrentFrame();
  if (f < at) return null;
  const { s, blur } = popCurve(f, at, P.popFrom, P.popOver, P.popDur, P.popBlur);
  const sy = ground !== undefined ? pingPong(f, P.bobPeriod, 1, 1 + P.bobAmp, bobPhase) : 1;
  const y = ground !== undefined ? bobbedY(cy, ground, sy) : cy;
  const mw = faceW * P.cover, mh = mw * P.ratio;
  return (
    <div style={{ position: "absolute", left: cx - mw / 2, top: y - mh / 2, width: mw, height: mh, borderRadius: "50%", background: P.bg, border: `${P.rim > 0 ? Math.max(3, mw * P.rim) : 0}px solid ${P.rimColor}`, boxSizing: "border-box", transform: `rotate(${P.rot}deg) scale(${s},${s * sy})`, filter: `blur(${blur}px) drop-shadow(0 4px 5px rgba(0,0,0,0.3))`, display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden" }}>
      {img ? <Img src={src(img)} style={{ width: "78%", height: "78%", objectFit: "contain" }} />
        : text ? <div style={{ fontFamily: font, fontSize: size ?? mw * 0.36, color: P.color, lineHeight: 1, whiteSpace: "nowrap", letterSpacing: -1 }}>{hz(text)}</div> : children}
    </div>
  );
};

// ══ 3. 감정 기호 ═══════════════════════════════════════════════════════════════
/** 빨간 핏줄 마크(💢형, ~60px): 0→1.3→1 팝(4f) 후 2~3f 마다 1.0↔1.14 맥동 */
export const AngerMarkParams = z.object({
  popDur: num(4, 1, 20, 1, "팝 길이", "timing", "f"),
  popPeak: num(1.3, 1, 3, 0.05, "팝 오버슈트(배)", "motion"),
  pulseAmp: num(0.14, 0, 0.6, 0.01, "맥동 크기(배)", "motion"),
  pulseHalf: num(2.5, 0.5, 15, 0.5, "맥동 반주기", "timing", "f"),
  size: num(60, 20, 240, 2, "크기", "size", "px"),
  rot: num(12, -90, 90, 1, "기울기", "motion", "°"),
  stroke: num(14, 2, 40, 1, "선 두께", "size"),
  outline: num(26, 0, 60, 1, "흰 외곽 두께", "size"),
  color: col("#E0292E", "핏줄 색"),
});
export type AngerMarkP = z.infer<typeof AngerMarkParams>;
export const AngerMark: React.FC<{ x: number; y: number; at: number; size?: number; color?: string; out?: number; rot?: number; p?: Partial<AngerMarkP> }> = ({ x, y, at, size: size0, color: color0, out, rot: rot0, p }) => {
  const P = def(AngerMarkParams, { ...given({ size: size0, color: color0, rot: rot0 }), ...p });
  const f = useCurrentFrame();
  if (f < at || (out !== undefined && f > out)) return null;
  const g = f - at, pd = P.popDur, size = P.size;
  const pop = kf(g, 0, [0, pd / 2, pd], [0, P.popPeak, 1]);
  const pulse = g >= pd && Math.floor((g - pd) / P.pulseHalf) % 2 === 0 ? 1 + P.pulseAmp : 1;
  const d = [[1, 1], [1, -1], [-1, 1], [-1, -1]].map(([a, b]) => `M${a * 9},${b * 40} Q${a * 9},${b * 9} ${a * 40},${b * 9}`).join(" ");
  return (
    <svg viewBox="-50 -50 100 100" width={size} height={size} style={{ position: "absolute", left: x - size / 2, top: y - size / 2, overflow: "visible", transform: `rotate(${P.rot}deg) scale(${pop * pulse})` }}>
      {P.outline > 0 && <path d={d} stroke="#fff" strokeWidth={P.outline} fill="none" strokeLinecap="round" />}
      <path d={d} stroke={P.color} strokeWidth={P.stroke} fill="none" strokeLinecap="round" />
    </svg>
  );
};

/** 놀람 선: 머리 옆 짧은 획 3~5개, 3f 드로우 팝 후 2f 마다 지터 */
export const SurpriseLinesParams = z.object({
  drawDur: num(3, 1, 20, 1, "획 뻗는 시간", "timing", "f"),
  jitter: num(6, 0, 30, 1, "지터 폭(px·°)", "motion"),
  jitterEvery: num(2, 1, 12, 1, "지터 간격", "timing", "f"),
  tilt: num(-35, -90, 90, 1, "획 방향(오른쪽 기준)", "motion", "°"),
  n: num(4, 1, 10, 1, "획 개수", "size"),
  len: num(50, 5, 200, 1, "획 길이", "size", "px"),
  gap: num(20, 0, 300, 1, "머리에서 떨어진 거리", "size", "px"),
  spread: num(70, 0, 180, 1, "획 부채꼴 각", "motion", "°"),
  width: num(9, 1, 40, 1, "획 두께", "size", "px"),
  color: col(INK, "획 색"),
});
export type SurpriseLinesP = z.infer<typeof SurpriseLinesParams>;
export const SurpriseLines: React.FC<{ x: number; y: number; at: number; side?: "left" | "right" | "both"; n?: number; len?: number; gap?: number; spread?: number; color?: string; width?: number; out?: number; p?: Partial<SurpriseLinesP> }> = ({ x, y, at, side = "right", n: n0, len: len0, gap: gap0, spread: spread0, color: color0, width: width0, out, p }) => {
  const P = def(SurpriseLinesParams, { ...given({ n: n0, len: len0, gap: gap0, spread: spread0, color: color0, width: width0 }), ...p });
  const { len, gap, spread, color, width } = P, n = Math.max(1, Math.round(P.n)), D = P.drawDur, J = P.jitter;
  const f = useCurrentFrame();
  if (f < at || (out !== undefined && f > out)) return null;
  const g = f - at, k = kf(g, 0, [0, D], [0, 1], Easing.out(Easing.quad)), st = Math.floor(g / Math.max(1, P.jitterEvery));
  const sides = side === "both" ? ["left", "right"] : [side];
  const white = color.toLowerCase() === "#fff" || color.toLowerCase() === "#ffffff";
  const lines = sides.flatMap((sd) => Array.from({ length: n }).map((_, i) => {
    const base = sd === "right" ? P.tilt : 180 - P.tilt;
    const a = ((base + (n === 1 ? 0 : (i / (n - 1) - 0.5) * spread) + (g >= D ? (random(`sl${sd}${i}${st}`) - 0.5) * J : 0)) * Math.PI) / 180;
    const jx = g >= D ? (random(`slx${sd}${i}${st}`) - 0.5) * J : 0, jy = g >= D ? (random(`sly${sd}${i}${st}`) - 0.5) * J : 0;
    const r0 = gap, r1 = gap + len * (i % 2 ? 0.8 : 1) * k;
    return `M${x + jx + Math.cos(a) * r0},${y + jy + Math.sin(a) * r0} L${x + jx + Math.cos(a) * r1},${y + jy + Math.sin(a) * r1}`;
  })).join(" ");
  return (
    <Full>
      {white && <path d={lines} stroke={INK} strokeWidth={width + 6} strokeLinecap="round" />}
      <path d={lines} stroke={color} strokeWidth={width} strokeLinecap="round" />
    </Full>
  );
};

/** 구름 생각 풍선: 꼬리 점 2개(선행 1f 스태거) → 본체 사진팝. tail = 머리 쪽 점 */
export const CloudBubbleParams = z.object({
  tailStagger: num(1, 0, 10, 1, "꼬리 점 스태거", "timing", "f"),
  bodyDelay: num(2, 0, 20, 1, "본체 팝 지연", "timing", "f"),
  popFrom: num(0.4, 0, 1, 0.05, "팝 시작 크기(배)", "motion"),
  popOver: num(0.08, 0, 0.5, 0.01, "팝 오버슈트", "motion"),
  popDur: num(5, 1, 20, 1, "팝 길이", "timing", "f"),
  fadeOut: num(5, 1, 30, 1, "사라지는 시간", "timing", "f"),
  bumps: num(10, 3, 24, 1, "구름 혹 개수", "size"),
  outline: num(11, 0, 30, 1, "외곽선 두께", "size", "px"),
  w: num(340, 120, 900, 5, "풍선 폭", "size", "px"),
  h: num(210, 80, 600, 5, "풍선 높이", "size", "px"),
  fill: col("#ffffff", "풍선 색"),
  ink: col("#2a2a2a", "외곽선 색"),
});
export type CloudBubbleP = z.infer<typeof CloudBubbleParams>;
export const CloudBubble: React.FC<{ x: number; y: number; at: number; text: string; w?: number; h?: number; tail?: Pt; size?: number; out?: number; seed?: string; font?: string; p?: Partial<CloudBubbleP> }> = ({ x, y, at, text, w: w0, h: h0, tail, size, out, seed = "cb", font = "Yeonsung, 'Songti SC', serif", p }) => {
  const P = def(CloudBubbleParams, { ...given({ w: w0, h: h0 }), ...p });
  const { w, h } = P, FO = P.fadeOut;
  const f = useCurrentFrame();
  if (f < at || (out !== undefined && f > out + FO)) return null;
  const o = out !== undefined ? lerp(f, out, out + FO, 1, 0) : 1;
  const b0 = at + P.bodyDelay, s = f < b0 ? 0 : popCurve(f, b0, P.popFrom, P.popOver, P.popDur).s;
  const rx = w * 0.36, ry = h * 0.3, br = Math.min(w, h) * 0.24, n = Math.max(3, Math.round(P.bumps));
  const bumps = Array.from({ length: n }).map((_, i) => { const a = (i / n) * TAU + 0.3; return { cx: x + Math.cos(a) * rx, cy: y + Math.sin(a) * ry, r: br * (0.85 + 0.3 * random(`${seed}${i}`)) }; });
  const shapes = <><ellipse cx={x} cy={y} rx={rx * 1.05} ry={ry * 1.1} />{bumps.map((b, i) => <circle key={i} {...b} />)}</>;
  const dots = tail ? [0.72, 0.42].map((t, i) => { const d0 = at + i * P.tailStagger; return { cx: tail[0] + (x - tail[0]) * (1 - t) * 0.85, cy: tail[1] + (y + ry - tail[1]) * (1 - t) * 0.85, r: Math.min(w, h) * (0.045 + 0.03 * i), s: f < d0 ? 0 : kf(f, d0, [0, 2, 3], [0, 1.2, 1]) }; }) : [];
  const tf = `translate(${x},${y}) scale(${s}) translate(${-x},${-y})`;
  return (
    <div style={{ position: "absolute", inset: 0, opacity: o, filter: "drop-shadow(0 4px 5px rgba(0,0,0,0.3))" }}>
      <Full>
        {dots.map((d, i) => <circle key={i} cx={d.cx} cy={d.cy} r={d.r * d.s} fill={P.fill} stroke={P.ink} strokeWidth={5} />)}
        <g transform={tf}>
          <g fill={P.ink} stroke={P.ink} strokeWidth={P.outline}>{shapes}</g>
          <g fill={P.fill}>{shapes}</g>
        </g>
      </Full>
      <div style={{ position: "absolute", left: x - w / 2, top: y - h / 2, width: w, height: h, transform: `scale(${s})`, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: font, fontSize: size ?? h * 0.34, color: "#1b1b1b", whiteSpace: "pre-line", textAlign: "center", lineHeight: 1.1 }}>{hz(text)}</div>
    </div>
  );
};

export const CloudBubblesParams = CloudBubbleParams.extend({
  dx: num(300, 0, 900, 5, "머리에서 좌우 거리", "motion", "px"),
  dy: num(-200, -600, 200, 5, "머리에서 위아래 거리", "motion", "px"),
  preOut: num(5, 0, 30, 1, "다음 풍선 전 사라짐", "timing", "f"),
});
export type CloudBubblesP = z.infer<typeof CloudBubblesParams>;
/** 생각 풍선 연속: 머리 위 좌/우 번갈아 팝. 같은 쪽 다음 풍선이 오면 5f 전에 이전 풍선이 사라진다(out 지정 시 우선) */
export const CloudBubbles: React.FC<{ head: Pt; items: { text: string; at: number; out?: number }[]; dx?: number; dy?: number; w?: number; h?: number; first?: "left" | "right"; p?: Partial<CloudBubblesP> }> = ({ head, items, dx, dy, w, h, first = "left", p }) => {
  const P = def(CloudBubblesParams, { ...given({ dx, dy, w, h }), ...p });
  const { dx: DX, dy: DY, preOut, ...bp } = P;
  return (
    <>
      {items.map((it, i) => {
        const sgn = (i % 2 === 0) === (first === "left") ? -1 : 1;
        const nx = items[i + 2];
        return <CloudBubble key={i} x={head[0] + sgn * DX} y={head[1] + DY} at={it.at} out={it.out ?? (nx ? nx.at - preOut : undefined)} text={it.text} tail={[head[0] + sgn * 50, head[1] - 10]} seed={`cbs${i}`} p={bp} />;
      })}
    </>
  );
};

/** 어지러움 소용돌이: 머리 위 납작한 나선이 회전 + 작은 별 2개 공전 */
export const DizzySwirlParams = z.object({
  popDur: num(5, 1, 20, 1, "팝 길이", "timing", "f"),
  popPeak: num(1.15, 1, 2, 0.05, "팝 오버슈트(배)", "motion"),
  speed: num(0.35, -1.5, 1.5, 0.01, "회전 속도(rad/f)", "motion"),
  starSpeed: num(1.4, 0, 4, 0.1, "별 공전 배속", "motion", "배"),
  turns: num(3, 1, 8, 0.5, "나선 감김 수", "size"),
  squash: num(0.42, 0.1, 1, 0.01, "납작함(세로 비)", "size"),
  r: num(70, 20, 300, 2, "반지름", "size", "px"),
  line: num(6, 1, 20, 1, "선 두께", "size", "px"),
  color: col("#333333", "나선 색"),
  starColor: col("#F5C518", "별 색"),
});
export type DizzySwirlP = z.infer<typeof DizzySwirlParams>;
export const DizzySwirl: React.FC<{ x: number; y: number; at: number; r?: number; color?: string; speed?: number; out?: number; p?: Partial<DizzySwirlP> }> = ({ x, y, at, r: r0, color: c0, speed: sp0, out, p }) => {
  const P = def(DizzySwirlParams, { ...given({ r: r0, color: c0, speed: sp0 }), ...p });
  const { r, color, speed } = P, sq = P.squash, pd = P.popDur;
  const f = useCurrentFrame();
  if (f < at || (out !== undefined && f > out)) return null;
  const g = f - at, s = kf(g, 0, [0, pd * 0.6, pd], [0, P.popPeak, 1]), rot = -g * speed;
  const pts: string[] = [];
  for (let i = 0; i <= 90; i++) { const t = i / 90, a = t * P.turns * TAU + rot, rr = r * t; pts.push(`${Math.cos(a) * rr},${Math.sin(a) * rr * sq}`); }
  const star = (k: number) => { const a = -g * speed * P.starSpeed + k * Math.PI; const sx = Math.cos(a) * r * 1.15, sy = Math.sin(a) * r * 1.15 * sq; const front = Math.sin(a) > 0; return <path key={k} d="M0,-14 L4,-4 L14,0 L4,4 L0,14 L-4,4 L-14,0 L-4,-4Z" transform={`translate(${sx},${sy - 6}) scale(${front ? 1.1 : 0.8})`} fill={P.starColor} stroke={INK} strokeWidth={2} opacity={front ? 1 : 0.7} />; };
  return (
    <svg viewBox={`${-r * 1.4} ${-r * 1.4 * 0.6} ${r * 2.8} ${r * 2.8 * 0.6}`} width={r * 2.8} height={r * 2.8 * 0.6} style={{ position: "absolute", left: x - r * 1.4, top: y - r * 1.4 * 0.6, overflow: "visible", transform: `scale(${s})` }}>
      <polyline points={pts.join(" ")} fill="none" stroke="#fff" strokeWidth={P.line + 7} strokeLinecap="round" strokeLinejoin="round" />
      <polyline points={pts.join(" ")} fill="none" stroke={color} strokeWidth={P.line} strokeLinecap="round" strokeLinejoin="round" />
      {star(0)}{star(1)}
    </svg>
  );
};

export const FallingBlocksParams = z.object({
  stagger: num(3, 0, 15, 0.5, "블록 스태거", "timing", "f"),
  gravity: num(4.5, 0.5, 20, 0.1, "중력(px/f²)", "motion"),
  dropRange: num(200, 0, 1000, 10, "낙하 시작 높이 편차", "motion", "px"),
  spin: num(90, 0, 360, 5, "낙하 중 회전 폭", "motion", "°"),
  bounce: num(10, 0, 40, 1, "착지 튐", "motion", "px"),
  n: num(18, 1, 60, 1, "블록 개수", "size"),
  size: num(46, 10, 150, 1, "블록 크기", "size", "px"),
  width: num(360, 60, 1600, 10, "쌓이는 폭", "size", "px"),
  color: col("#161616", "블록 색"),
});
export type FallingBlocksP = z.infer<typeof FallingBlocksParams>;
/** 검은 블록 잔해: 위에서 중력 낙하(회전) → 지면에 쌓임. 캐릭터 '앞'에 두면 앞, 먼저 렌더하면 뒤 */
export const FallingBlocks: React.FC<{ x: number; groundY: number; at: number; width?: number; n?: number; size?: number; stagger?: number; color?: string; seed?: string; p?: Partial<FallingBlocksP> }> = ({ x, groundY, at, width: w0, n: n0, size: s0, stagger: st0, color: c0, seed = "fb", p }) => {
  const P = def(FallingBlocksParams, { ...given({ width: w0, n: n0, size: s0, stagger: st0, color: c0 }), ...p });
  const { width, size, stagger, color } = P, n = Math.max(0, Math.round(P.n)), B = P.bounce;
  const f = useCurrentFrame();
  if (f < at) return null;
  const cols = Math.max(1, Math.floor(width / size)), heights = Array(cols).fill(0), G = Math.max(0.01, P.gravity);
  return (
    <>
      {Array.from({ length: n }).map((_, i) => {
        const c = Math.min(cols - 1, Math.floor(((random(`${seed}c${i}`) + random(`${seed}C${i}`)) / 2) * cols)), stack = heights[c]++;
        const sz = size * (0.8 + 0.35 * random(`${seed}s${i}`));
        const lx = x - width / 2 + (c + 0.5) * size + (random(`${seed}x${i}`) - 0.5) * 8;
        const ly = groundY - stack * size * 0.92 - sz / 2;
        const y0 = -sz - random(`${seed}y${i}`) * P.dropRange, a0 = at + i * stagger;
        if (f < a0) return null;
        const t = f - a0, tl = Math.max(0.01, Math.sqrt(Math.max(0, (2 * (ly - y0)) / G)));
        const landed = t >= tl, cy = landed ? ly - (t - tl < 3 ? [B, B * 0.4, 0][Math.floor(t - tl)] : 0) : y0 + 0.5 * G * t * t;
        const r0 = (random(`${seed}r${i}`) - 0.5) * P.spin, r1 = (random(`${seed}q${i}`) - 0.5) * 16;
        const rot = landed ? r1 : r0 + (r1 - r0) * (t / tl);
        return <div key={i} style={{ position: "absolute", left: lx - sz / 2, top: cy - sz / 2, width: sz, height: sz, background: color, transform: `rotate(${rot}deg)`, borderRadius: 3 }} />;
      })}
    </>
  );
};

// ══ 4. 연기 스왑 / 텔레포트 ═════════════════════════════════════════════════════
// 연기 뭉치: 원 합집합(어두운 외곽 → 밝은 채움 2패스) + 하이라이트 호. shrink(0→1) = 퍼프별 스태거로 쪼그라들며 흩어짐
const Puffs: React.FC<{ cx: number; cy: number; rx: number; ry: number; r: number; n: number; s: number; op: number; seed: string; g: number; drift?: number; ring?: boolean; shrink?: number; dark?: string; light?: string }> = ({ cx, cy, rx, ry, r, n, s, op, seed, g, drift = 0, ring, shrink = 0, dark = "#8E8781", light = "#D9D4CE" }) => {
  if (s <= 0.001 || op <= 0.001 || shrink >= 1) return null;
  const ps = Array.from({ length: n }).map((_, i) => {
    const a = (i / n) * TAU + random(`${seed}a${i}`) * 0.5, d = ring ? 1 : i === 0 ? 0 : 0.3 + 0.7 * Math.sqrt(random(`${seed}d${i}`));
    const k = Math.max(0, 1 - shrink * (1 + random(`${seed}k${i}`) * 0.8)), dd = 1 + drift + shrink * 0.5;
    return { x: cx + Math.cos(a) * rx * Math.max(d, 0.3 * shrink) * dd, y: cy + Math.sin(a) * ry * Math.max(d, 0.3 * shrink) * dd - shrink * r * 0.4, r: k * r * (0.75 + 0.5 * random(`${seed}r${i}`)) * (1 + 0.05 * Math.sin(g / 3 + i)) };
  }).filter((p) => p.r > 1);
  return (
    <Full style={{ opacity: op }}>
      <g transform={`translate(${cx},${cy}) scale(${s}) translate(${-cx},${-cy})`}>
        <g fill={dark}>{ps.map((p, i) => <circle key={i} cx={p.x} cy={p.y} r={p.r + 6} />)}</g>
        <g fill={light}>{ps.map((p, i) => <circle key={i} cx={p.x} cy={p.y} r={p.r} />)}</g>
        <g fill="none" stroke="#F6F3EF" strokeLinecap="round">{ps.map((p, i) => <path key={i} strokeWidth={p.r * 0.1} d={`M${p.x - p.r * 0.6},${p.y - p.r * 0.05} A${p.r * 0.62},${p.r * 0.62} 0 0 1 ${p.x - p.r * 0.05},${p.y - p.r * 0.6}`} />)}</g>
      </g>
    </Full>
  );
};

/** 제자리 연기 교체: 연기 뭉치가 3f 에 덮고 ~10f 유지(3f 에 a→b 교체) → 9f 퍼프별로 쪼그라들며 걷힘 */
export const SmokeSwapParams = z.object({
  popDur: num(3, 1, 15, 1, "연기 덮는 시간", "timing", "f"),
  popPeak: num(1.1, 1, 2, 0.01, "연기 오버슈트(배)", "motion"),
  swapAt: num(3, 0, 20, 1, "교체 시점", "timing", "f"),
  cover: num(10, 1, 40, 1, "연기 유지(걷힘 시작)", "timing", "f"),
  clearDur: num(9, 1, 40, 1, "걷히는 시간", "timing", "f"),
  n: num(15, 3, 40, 1, "연기 알 개수", "size"),
  puffK: num(0.28, 0.05, 0.8, 0.01, "연기 알 크기(비)", "size"),
  spreadK: num(0.4, 0.05, 1.2, 0.01, "퍼짐 반경(비)", "size"),
  dark: col("#8E8781", "연기 외곽 색"),
  light: col("#D9D4CE", "연기 채움 색"),
});
export type SmokeSwapP = z.infer<typeof SmokeSwapParams>;
export const SmokeSwap: React.FC<{ x: number; y: number; w: number; h: number; at: number; a: RN; b: RN; cover?: number; n?: number; seed?: string; p?: Partial<SmokeSwapP> }> = ({ x, y, w, h, at, a, b, cover: cv0, n: n0, seed = "ss", p }) => {
  const P = def(SmokeSwapParams, { ...given({ cover: cv0, n: n0 }), ...p });
  const pd = P.popDur, cover = Math.max(pd + 2.5, P.cover), n = Math.max(1, Math.round(P.n));
  const f = useCurrentFrame(), g = f - at;
  const s = g < 0 ? 0 : kf(g, 0, [0, pd, pd + 2, cover], [0, P.popPeak, 1, 1.03]);
  const shrink = g <= cover ? 0 : kf(g, cover, [0, P.clearDur], [0, 1], Easing.in(Easing.quad));
  return (
    <>
      {g < P.swapAt ? a : b}
      <Puffs cx={x} cy={y} rx={w * P.spreadK} ry={h * P.spreadK} r={Math.max(w, h) * P.puffK} n={n} s={s} op={1} seed={seed} g={g} shrink={shrink} dark={P.dark} light={P.light} />
    </>
  );
};

/** 텔레포트: 흰 4각 버스트 2f → 회색 연기 6f 부풀며 캐릭터 감쌈 → 12f 걷힘. in=나타남 / out=사라짐 */
export const TeleportParams = z.object({
  flashDur: num(2, 1, 10, 1, "흰 버스트 길이", "timing", "f"),
  flashSize: num(1.15, 0.3, 3, 0.05, "버스트 최대 크기(배)", "size"),
  growDur: num(6, 1, 30, 1, "연기 부푸는 시간", "timing", "f"),
  startScale: num(0.25, 0, 1, 0.05, "연기 시작 크기(배)", "motion"),
  clearAt: num(8, 1, 40, 1, "연기 걷힘 시작", "timing", "f"),
  clearDur: num(12, 1, 40, 1, "걷히는 시간", "timing", "f"),
  charFrom: num(0.85, 0.2, 1.5, 0.05, "등장 시 캐릭터 시작 크기(배)", "motion"),
  hideAt: num(5, 0, 30, 1, "사라짐: 캐릭터 숨는 시점", "timing", "f"),
  puffK: num(0.18, 0.05, 0.6, 0.01, "연기 알 크기(비)", "size"),
  dark: col("#8E8781", "연기 외곽 색"),
  light: col("#D9D4CE", "연기 채움 색"),
});
export type TeleportP = z.infer<typeof TeleportParams>;
export const Teleport: React.FC<{ x: number; y: number; w: number; h: number; at: number; mode?: "in" | "out"; children: RN; seed?: string; p?: Partial<TeleportP> }> = ({ x, y, w, h, at, mode = "in", children, seed = "tp", p }) => {
  const P = def(TeleportParams, p);
  const FD = Math.max(1, Math.round(P.flashDur)), CA = Math.max(FD, P.clearAt);
  const f = useCurrentFrame(), g = f - at;
  const big = Math.max(w, h);
  const cs = g < FD ? 0 : kf(g, FD, [0, P.growDur], [P.startScale, 1], EXPO_OUT);
  const cop = 1, drift = 0;
  const shrink = g <= CA ? 0 : kf(g, CA, [0, P.clearDur], [0, 1], Easing.in(Easing.quad));
  const showChar = mode === "in" ? g >= FD : g < P.hideAt;
  const cp = mode === "in" && g >= FD ? kf(g, FD, [0, 3], [P.charFrom, 1]) : 1;
  const fs = FD === 1 ? P.flashSize : kf(g, 0, [0, FD - 1], [0.7, P.flashSize]);
  const sk = { dark: P.dark, light: P.light };
  return (
    <>
      <Puffs cx={x} cy={y} rx={w * 0.55} ry={h * 0.5} r={big * P.puffK} n={14} s={cs} op={cop} seed={seed + "b"} g={g} drift={drift} shrink={shrink} ring {...sk} />
      {(g < 0 ? mode === "out" : showChar) && <div style={{ position: "absolute", left: 0, top: 0, width: W, height: H, transformOrigin: `${x}px ${y}px`, transform: `scale(${cp})` }}>{children}</div>}
      {mode === "out" && g >= FD && <Puffs cx={x} cy={y} rx={w * 0.25} ry={h * 0.3} r={big * P.puffK * (0.22 / 0.18)} n={9} s={cs} op={cop} seed={seed + "f"} g={g} drift={drift} shrink={shrink} {...sk} />}
      {g >= 0 && g < FD && (
        <svg width={big * 1.4} height={big * 1.4} viewBox="-50 -50 100 100" style={{ position: "absolute", left: x - big * 0.7, top: y - big * 0.7, transform: `scale(${fs})`, filter: "drop-shadow(0 0 12px rgba(255,255,255,0.9))" }}>
          <path d="M0,-50 C6,-8 8,-6 50,0 C8,6 6,8 0,50 C-6,8 -8,6 -50,0 C-8,-6 -6,-8 0,-50Z" fill="#fff" />
        </svg>
      )}
    </>
  );
};

// ══ 5. 포물선 점프 ════════════════════════════════════════════════════════════
/** 발밑 지점 pts 사이를 연속 홉: 상승 rise f, 총 dur f(8~16), 착지 2f 스쿼시(sy .85 sx 1.1) + 흰 먼지 타원 6f */
export const HopArcParams = z.object({
  dur: num(12, 2, 40, 1, "점프 한 번 길이", "timing", "f"),
  rise: num(5, 1, 30, 1, "상승 시간", "timing", "f"),
  gap: num(6, 0, 40, 1, "착지 후 다음 점프까지", "timing", "f"),
  height: num(160, 0, 600, 5, "점프 높이", "motion", "px"),
  stretch: num(0.06, 0, 0.3, 0.01, "공중 늘어남", "motion"),
  squash: num(0.15, 0, 0.5, 0.01, "착지 스쿼시 세기", "motion"),
  dust: flag(true, "착지 먼지 링"),
  dustDur: num(6, 1, 30, 1, "먼지 링 길이", "timing", "f"),
  dustSpread: num(0.85, 0.3, 3, 0.05, "먼지 링 퍼짐(몸 폭 비)", "size"),
  dustColor: col("#ffffff", "먼지 링 색"),
  face: flag(true, "진행 방향 보기"),
});
export type HopArcP = z.infer<typeof HopArcParams>;
export const HopArc: React.FC<{ pts: Pt[]; at: number; w: number; h: number; img?: string; children?: RN; dur?: number; rise?: number; gap?: number; height?: number; glow?: boolean; dust?: boolean; face?: boolean; p?: Partial<HopArcP> }> = ({ pts, at, w, h, img, children, dur: d0, rise: r0, gap: g0, height: h0, glow, dust: du0, face: fa0, p }) => {
  const P = def(HopArcParams, { ...given({ dur: d0, rise: r0, gap: g0, height: h0, dust: du0, face: fa0 }), ...p });
  const dur = Math.max(1, P.dur), rise = Math.min(Math.max(0.5, P.rise), dur - 0.5), { gap, height, dust, face } = P, DD = P.dustDur;
  const f = useCurrentFrame();
  let [x, y] = pts[0], sx = 1, sy = 1, dir = 1;
  const rings: RN[] = [];
  for (let i = 0; i < pts.length - 1; i++) {
    const s0 = at + i * (dur + gap), s1 = s0 + dur, [ax, ay] = pts[i], [bx, by] = pts[i + 1];
    if (f >= s0) dir = bx >= ax ? 1 : -1;
    if (f >= s0 && f < s1) {
      const t = f - s0, u = t / dur;
      const off = t < rise ? -height * (1 - (1 - t / rise) ** 2) : -height * (1 - ((t - rise) / (dur - rise)) ** 2);
      x = ax + (bx - ax) * u; y = ay + (by - ay) * u + off; sx = 1 - (P.stretch * 5) / 6; sy = 1 + P.stretch;
    } else if (f >= s1) {
      x = bx; y = by;
      const g = f - s1;
      if (g < 3) { const q = landSquash(g, P.squash, 8 / 15); sy = q.sy; sx = q.sx; }
      if (dust && g <= DD) {
        const rx = lerp(g, 0, DD, w * 0.3, w * P.dustSpread, Easing.out(Easing.quad));
        rings.push(<ellipse key={i} cx={bx} cy={by} rx={rx} ry={rx * 0.22} fill="none" stroke={P.dustColor} strokeWidth={lerp(g, 0, DD, 12, 2)} opacity={lerp(g, 0, DD, 1, 0)} />);
      }
    }
  }
  return (
    <>
      <Full>{rings}</Full>
      <div style={{ position: "absolute", left: x - w / 2, top: y - h, width: w, height: h, transformOrigin: "50% 100%", transform: `scale(${sx * (face ? dir : 1)},${sy})` }}>
        <Body img={img} glow={glow}>{children}</Body>
      </div>
    </>
  );
};

// ══ 6. 라이벌 전격 / 크랙 ══════════════════════════════════════════════════════
const zig = (a: Pt, b: Pt, n: number, amp: number, key: string, grow = 1) => {
  const dx = b[0] - a[0], dy = b[1] - a[1], len = Math.hypot(dx, dy) || 1, nx = -dy / len, ny = dx / len;
  const out: Pt[] = [];
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    if (t > grow) { const tp = grow; out.push([a[0] + dx * tp, a[1] + dy * tp]); break; }
    const j = i === 0 || i === n ? 0 : (random(`${key}-${i}`) - 0.5) * amp * 2;
    out.push([a[0] + dx * t + nx * j, a[1] + dy * t + ny * j]);
  }
  return out;
};
const pl = (p: Pt[]) => p.map((q) => q.join(",")).join(" ");

/** 두 점 사이 파랑-흰 전격(두께 ~60px + 글로우), 2~3f 마다 재생성. 시작 3f 소스에 주황 플래시 */
export const RivalBeamParams = z.object({
  grow: num(2, 1, 20, 1, "뻗는 시간", "timing", "f"),
  regen: num(2.5, 0.5, 12, 0.5, "모양 재생성 간격", "timing", "f"),
  jag: num(0.55, 0, 2, 0.05, "지그재그 세기(두께 비)", "motion"),
  segLen: num(60, 20, 300, 5, "꺾임 간격", "size", "px"),
  thick: num(60, 6, 200, 2, "전격 두께", "size", "px"),
  flashDur: num(3, 1, 12, 1, "소스 플래시 길이", "timing", "f"),
  outer: col("#3E8DFF", "바깥 색"),
  inner: col("#A9DCFF", "안쪽 색"),
  glow: col("#2F7BFF", "글로우 색"),
});
export type RivalBeamP = z.infer<typeof RivalBeamParams>;
export const RivalBeam: React.FC<{ from: Pt; to: Pt; at: number; out?: number; thick?: number; seed?: string; glow?: string; p?: Partial<RivalBeamP> }> = ({ from, to, at, out, thick: th0, seed = "rb", glow: gl0, p }) => {
  const P = def(RivalBeamParams, { ...given({ thick: th0, glow: gl0 }), ...p });
  const { thick, glow } = P, FD = Math.max(1, Math.round(P.flashDur)), fe = Math.max(0.01, FD - 1);
  const f = useCurrentFrame();
  if (f < at || (out !== undefined && f > out)) return null;
  const g = f - at, st = Math.floor(g / P.regen), grow = kf(g, 0, [0, P.grow], [0.15, 1]);
  const len = Math.hypot(to[0] - from[0], to[1] - from[1]), n = Math.max(6, Math.round(len / P.segLen));
  const main = zig(from, to, n, thick * P.jag, `${seed}${st}`, grow);
  const forks = [0.3, 0.62].map((t, k) => {
    const i = Math.min(main.length - 1, Math.floor(main.length * t)), p = main[i];
    if (!p || grow < t) return null;
    const side = random(`${seed}fs${k}${st}`) > 0.5 ? 1 : -1;
    const e: Pt = [p[0] + (to[0] - from[0]) * 0.12, p[1] + side * thick * (1.2 + random(`${seed}fl${k}${st}`))];
    return zig(p, e, 3, thick * 0.3, `${seed}f${k}${st}`);
  }).filter(Boolean) as Pt[][];
  const layer = (sw: number, c: string, op = 1) => (
    <g stroke={c} strokeWidth={sw} fill="none" strokeLinejoin="round" strokeLinecap="round" opacity={op}>
      <polyline points={pl(main)} />{forks.map((q, i) => <polyline key={i} points={pl(q)} strokeWidth={sw * 0.45} />)}
    </g>
  );
  return (
    <>
      <Full style={{ filter: `drop-shadow(0 0 ${thick * 0.25}px #7CC8FF) drop-shadow(0 0 ${thick * 0.55}px ${glow})` }}>
        {layer(thick, P.outer, 0.85)}{layer(thick * 0.55, P.inner)}{layer(thick * 0.24, "#fff")}
      </Full>
      {g < FD && <div style={{ position: "absolute", left: from[0] - thick * 2, top: from[1] - thick * 2, width: thick * 4, height: thick * 4, borderRadius: "50%", background: "radial-gradient(circle, #FFF3D0 0%, #FFB23E 35%, rgba(255,120,20,0.6) 55%, rgba(255,120,20,0) 72%)", opacity: kf(g, 0, [0, fe / 2, fe], [1, 0.75, 0.35]), transform: `scale(${1 + g * 0.25})` }} />}
    </>
  );
};

/** 원 둘레 작은 노란 지지직 크랙, 2f 마다 재생성 */
export const ElectricCrackParams = z.object({
  regen: num(2, 1, 12, 1, "재생성 간격", "timing", "f"),
  n: num(6, 1, 24, 1, "크랙 개수", "size"),
  len: num(0.25, 0.05, 1, 0.01, "크랙 길이(반지름 비)", "size"),
  jag: num(0.08, 0, 0.4, 0.01, "지그재그 세기(반지름 비)", "motion"),
  line: num(6, 1, 20, 1, "선 두께", "size", "px"),
  color: col("#FFE14D", "크랙 색"),
});
export type ElectricCrackP = z.infer<typeof ElectricCrackParams>;
export const ElectricCrack: React.FC<{ x: number; y: number; r: number; at: number; out?: number; n?: number; color?: string; seed?: string; p?: Partial<ElectricCrackP> }> = ({ x, y, r, at, out, n: n0, color: c0, seed = "ec", p }) => {
  const P = def(ElectricCrackParams, { ...given({ n: n0, color: c0 }), ...p });
  const n = Math.max(1, Math.round(P.n)), color = P.color;
  const f = useCurrentFrame();
  if (f < at || (out !== undefined && f > out)) return null;
  const st = Math.floor((f - at) / P.regen);
  const zz = Array.from({ length: n }).map((_, i) => {
    const a = (i / n) * TAU + random(`${seed}a${i}${st}`) * 0.9, l = r * (P.len + P.len * random(`${seed}l${i}${st}`));
    const p0: Pt = [x + Math.cos(a) * r * 1.02, y + Math.sin(a) * r * 1.02], p1: Pt = [x + Math.cos(a + 0.25) * (r + l), y + Math.sin(a + 0.25) * (r + l)];
    return zig(p0, p1, 4, r * P.jag, `${seed}z${i}${st}`);
  });
  return (
    <Full style={{ filter: "drop-shadow(0 0 6px rgba(255,220,60,0.9))" }}>
      {zz.map((q, i) => <polyline key={i} points={pl(q)} stroke={color} strokeWidth={P.line} fill="none" strokeLinejoin="round" strokeLinecap="round" />)}
      {zz.map((q, i) => <polyline key={`w${i}`} points={pl(q)} stroke="#fff" strokeWidth={2} fill="none" strokeLinejoin="round" />)}
    </Full>
  );
};

// ══ 7. 눈빛 광선 + 속도선 ══════════════════════════════════════════════════════
/** 가로 속도선 배경(등속 흐름) */
export const SpeedLinesParams = z.object({
  fadeIn: num(4, 1, 30, 1, "페이드인", "timing", "f"),
  speed: num(70, 0, 300, 1, "흐름 속도(px/f)", "motion"),
  speedVar: num(0.6, 0, 1.4, 0.05, "속도 편차", "motion"),
  n: num(28, 1, 120, 1, "선 개수", "size"),
  lenMin: num(200, 10, 1500, 10, "선 최소 길이", "size", "px"),
  lenVar: num(500, 0, 1500, 10, "선 길이 편차", "size", "px"),
  thickMin: num(3, 1, 30, 1, "선 최소 두께", "size", "px"),
  thickVar: num(7, 0, 40, 1, "선 두께 편차", "size", "px"),
  color: col("rgba(255,255,255,0.75)", "선 색"),
});
export type SpeedLinesP = z.infer<typeof SpeedLinesParams>;
export const SpeedLines: React.FC<{ at?: number; n?: number; color?: string; speed?: number; dir?: 1 | -1; bg?: string; seed?: string; p?: Partial<SpeedLinesP> }> = ({ at = 0, n: n0, color: c0, speed: sp0, dir = -1, bg, seed = "spd", p }) => {
  const P = def(SpeedLinesParams, { ...given({ n: n0, color: c0, speed: sp0 }), ...p });
  const n = Math.max(0, Math.round(P.n)), { color, speed } = P;
  const f = useCurrentFrame();
  if (f < at) return null;
  const g = f - at;
  return (
    <AbsoluteFill style={{ background: bg, opacity: lerp(f, at, at + P.fadeIn, 0, 1) }}>
      {Array.from({ length: n }).map((_, i) => {
        const len = P.lenMin + random(`${seed}l${i}`) * P.lenVar, th = P.thickMin + random(`${seed}t${i}`) * P.thickVar, span = W + len;
        const v = speed * (1 - P.speedVar / 2 + P.speedVar * random(`${seed}v${i}`));
        const px = ((((random(`${seed}x${i}`) * span + g * v * -dir) % span) + span) % span) - len;
        const x = dir < 0 ? W - px - len : px;
        return <div key={i} style={{ position: "absolute", left: x, top: random(`${seed}y${i}`) * H, width: len, height: th, borderRadius: th, background: color }} />;
      })}
    </AbsoluteFill>
  );
};

/** 두 눈 지점을 잇는 파란 사인파 광선, 위상 흐름 애니. 6f 에 걸쳐 a→b 로 뻗음 */
export const EyeBeamParams = z.object({
  grow: num(6, 1, 30, 1, "뻗는 시간", "timing", "f"),
  flow: num(0.8, -3, 3, 0.1, "물결 흐름 속도(rad/f)", "motion"),
  amp: num(18, 0, 80, 1, "물결 진폭", "motion", "px"),
  wave: num(80, 10, 400, 5, "물결 파장", "size", "px"),
  taper: num(40, 1, 300, 5, "양끝 가늘어짐 구간", "size", "px"),
  strands: num(2, 1, 5, 1, "가닥 수", "size"),
  width: num(10, 1, 40, 1, "광선 두께", "size", "px"),
  glow: num(8, 0, 40, 1, "글로우 반경", "look", "px"),
  color: col("#2E9BFF", "광선 색"),
  color2: col("#9ED3FF", "보조 가닥 색"),
});
export type EyeBeamP = z.infer<typeof EyeBeamParams>;
export const EyeBeam: React.FC<{ a: Pt; b: Pt; at: number; out?: number; amp?: number; wave?: number; color?: string; width?: number; strands?: number; flow?: number; speedLines?: boolean; p?: Partial<EyeBeamP> }> = ({ a, b, at, out, amp: am0, wave: wv0, color: c0, width: w0, strands: s0, flow: fl0, speedLines, p }) => {
  const P = def(EyeBeamParams, { ...given({ amp: am0, wave: wv0, color: c0, width: w0, strands: s0, flow: fl0 }), ...p });
  const { amp, wave, color, width, flow } = P, strands = Math.max(1, Math.round(P.strands)), TP = Math.max(1, P.taper);
  const f = useCurrentFrame();
  if (f < at || (out !== undefined && f > out)) return null;
  const g = f - at, grow = kf(g, 0, [0, P.grow], [0, 1], Easing.out(Easing.quad));
  const dx = b[0] - a[0], dy = b[1] - a[1], len = Math.hypot(dx, dy) || 1, ux = dx / len, uy = dy / len;
  const path = (ph: number) => {
    const pts: string[] = [];
    for (let s = 0; s <= len * grow; s += 5) {
      const env = Math.min(1, s / TP, (len - s) / TP);
      const o = amp * env * Math.sin((s / wave) * TAU - g * flow + ph);
      pts.push(`${a[0] + ux * s - uy * o},${a[1] + uy * s + ux * o}`);
    }
    return pts.join(" ");
  };
  return (
    <>
      {speedLines && <SpeedLines at={at} />}
      <Full style={{ filter: P.glow > 0 ? `drop-shadow(0 0 ${P.glow}px ${color}) drop-shadow(0 0 ${P.glow * 2.25}px ${color})` : undefined }}>
        {Array.from({ length: strands }).map((_, i) => <polyline key={i} points={path((i * TAU) / strands)} fill="none" stroke={i === 0 ? color : P.color2} strokeWidth={i === 0 ? width : width * 0.7} strokeLinecap="round" strokeLinejoin="round" />)}
        <polyline points={path(0)} fill="none" stroke="#fff" strokeWidth={width * 0.3} strokeLinecap="round" />
      </Full>
    </>
  );
};

// ══ 8. 전화 벨 ════════════════════════════════════════════════════════════════
/** 전화기 좌우 빨간 지그재그 '따르릉' 표시 — 4f/6f 교대로 모양이 바뀜, 전화기 흔들림 */
export const PhoneRingParams = z.object({
  cycle: num(20, 2, 80, 1, "벨 주기", "timing", "f"),
  ringOn: num(14, 1, 80, 1, "주기 중 울리는 구간", "timing", "f"),
  shake: num(7, 0, 40, 1, "전화기 흔들림", "motion", "°"),
  shakeSpeed: num(2.2, 0.1, 5, 0.1, "흔들림 빠르기(rad/f)", "motion"),
  fan: num(28, 0, 80, 1, "표시 부채꼴 각", "motion", "°"),
  teeth: num(4, 1, 12, 1, "지그재그 톱니 수", "size"),
  zig: num(9, 0, 40, 1, "지그재그 폭", "size", "px"),
  markLen: num(0.22, 0.05, 0.8, 0.01, "표시 길이(크기 비)", "size"),
  markW: num(7, 1, 24, 1, "표시 두께", "size", "px"),
  size: num(240, 80, 700, 5, "전화기 크기", "size", "px"),
  color: col("#E53935", "표시·글자 색"),
});
export type PhoneRingP = z.infer<typeof PhoneRingParams>;
export const PhoneRing: React.FC<{ x: number; y: number; at: number; size?: number; text?: string; color?: string; phone?: RN; out?: number; p?: Partial<PhoneRingP> }> = ({ x, y, at, size: sz0, text = "따르릉", color: c0, phone, out, p }) => {
  const P = def(PhoneRingParams, { ...given({ size: sz0, color: c0 }), ...p });
  const { size, color } = P, teeth = Math.max(1, Math.round(P.teeth));
  const f = useCurrentFrame();
  if (f < at || (out !== undefined && f > out)) return null;
  const g = f - at, st = Math.floor(g / 10) * 2 + (g % 10 >= 4 ? 1 : 0);
  const ring = g % Math.max(1, P.cycle) < P.ringOn;
  const rot = ring ? P.shake * Math.sin(g * P.shakeSpeed) : 0;
  const pw = size * 0.55, ph = size;
  const marks = ring ? [-1, 1].flatMap((sd) => [-P.fan, 0, P.fan].map((deg, i) => {
    const a = ((sd > 0 ? deg : 180 - deg) * Math.PI) / 180 + (random(`pr${sd}${i}${st}`) - 0.5) * 0.25;
    const r0 = pw * 0.62 + random(`pr0${sd}${i}${st}`) * 12, L = size * (P.markLen + 0.08 * random(`prl${sd}${i}${st}`));
    const amp = P.zig + random(`pra${sd}${i}${st}`) * P.zig * (2 / 3), pts: string[] = [];
    for (let k = 0; k <= teeth * 2; k++) { const r = r0 + (L * k) / (teeth * 2), o = k % 2 ? amp : -amp; pts.push(`${x + Math.cos(a) * r - Math.sin(a) * o},${y - ph * 0.1 + Math.sin(a) * r * 0.9 + Math.cos(a) * o}`); }
    return <polyline key={`${sd}${i}`} points={pts.join(" ")} fill="none" stroke={color} strokeWidth={P.markW} strokeLinejoin="round" strokeLinecap="round" />;
  })) : [];
  const tp = textPop(f, at);
  return (
    <>
      <div style={{ position: "absolute", left: x - pw / 2, top: y - ph / 2, width: pw, height: ph, transform: `rotate(${rot}deg)`, transformOrigin: "50% 90%" }}>
        {phone ?? (() => {
          // 세모지 그림체 스마트폰(smartphone_ringing): 이미지 폭의 23.7~98.7% 가 폰 몸통, 통화 버튼 원은 투명 구멍 → 초록 원을 뒤에 깐다
          const iw = ph * (836 / 1426), l = pw / 2 - 0.612 * iw;
          return (
            <>
              <div style={{ position: "absolute", left: l + 0.612 * iw - iw * 0.2, top: ph * 0.528 - iw * 0.2, width: iw * 0.4, height: iw * 0.4, borderRadius: "50%", background: "#2FBF4A" }} />
              <Img src={prop("smartphone_ringing")} style={{ position: "absolute", left: l, top: 0, width: iw, height: ph }} />
            </>
          );
        })()}
      </div>
      <Full>{marks}</Full>
      <div style={{ position: "absolute", left: x, top: y - ph / 2 - size * 0.32, transform: `translateX(-50%) scale(${tp.s}) rotate(${st % 2 ? -6 : 5}deg)`, opacity: tp.op, fontFamily: "Jalnan", fontSize: size * 0.24, color, WebkitTextStroke: `${size * 0.04}px #fff`, paintOrder: "stroke fill", whiteSpace: "nowrap" }}>{text}</div>
    </>
  );
};

// ══ 9. 숨은 실루엣 ════════════════════════════════════════════════════════════
/** 앞 캐릭터 뒤에서 반투명(50%) 검은 실루엣이 옆으로 천천히 스며 나온다 */
export const HiddenSilhouetteParams = z.object({
  dur: num(60, 1, 240, 1, "스며 나오는 시간", "timing", "f"),
  dx: num(170, -800, 800, 5, "옆으로 나오는 거리", "motion", "px"),
  reveal: num(3, 1, 20, 0.5, "드러나는 빠르기(배)", "motion", "배"),
  opacity: num(0.5, 0, 1, 0.05, "실루엣 불투명도", "look"),
  color: choice("dark", ["dark", "black"], "실루엣 톤", "look"),
  lift: num(0.12, 0, 1, 0.01, "dark 톤 밝기", "look"),
});
export type HiddenSilhouetteP = z.infer<typeof HiddenSilhouetteParams>;
export const HiddenSilhouette: React.FC<{ img: string; x: number; y: number; w: number; h?: number; at: number; dur?: number; dx?: number; opacity?: number; color?: "dark" | "black"; children?: RN; p?: Partial<HiddenSilhouetteP> }> = ({ img, x, y, w, h, at, dur: d0, dx: dx0, opacity: o0, color: c0, children, p }) => {
  const P = def(HiddenSilhouetteParams, { ...given({ dur: d0, dx: dx0, opacity: o0, color: c0 }), ...p });
  const { dx, opacity, color } = P;
  const f = useCurrentFrame();
  const k = lerp(f, at, at + Math.max(1, P.dur), 0, 1, Easing.inOut(Easing.sin));
  const hh = h ?? w * 1.4;
  return (
    <>
      {f >= at && <Img src={src(img)} style={{ position: "absolute", left: x - w / 2 + dx * k, top: y - hh, width: w, height: hh, objectFit: "contain", objectPosition: "50% 100%", filter: color === "black" ? "brightness(0)" : `brightness(0) invert(${P.lift})`, opacity: opacity * Math.min(1, k * P.reveal) }} />}
      {children}
    </>
  );
};

// ══ 10. 구석에서 들어오는 손가락 ══════════════════════════════════════════════════
/** 오른쪽 아래 화면 밖에서 대각선으로 ~10f 슬라이드인 → 한 번 톡 (tip = 손끝 좌표) */
export const FingerFromCornerParams = z.object({
  slide: num(10, 1, 40, 1, "슬라이드인 시간", "timing", "f"),
  dist: num(1400, 200, 2500, 10, "들어오는 거리", "motion", "px"),
  angle: num(-42, -180, 180, 1, "손가락 각도", "motion", "°"),
  tapDelay: num(4, 0, 30, 1, "도착 후 톡까지", "timing", "f"),
  tapDur: num(7, 2, 30, 1, "톡 길이", "timing", "f"),
  tapDepth: num(28, 0, 120, 1, "톡 깊이", "motion", "px"),
  outDur: num(8, 1, 30, 1, "퇴장 시간", "timing", "f"),
  scale: num(1, 0.3, 3, 0.05, "손 크기(배)", "size"),
  ripple: flag(true, "탭 물결 링"),
  rippleSize: num(1.3, 0.3, 4, 0.05, "물결 링 최대 크기(배)", "size"),
  skin: col("#F6C8A4", "피부 색"),
  sleeve: col("#2E5FB0", "소매 색"),
});
export type FingerFromCornerP = z.infer<typeof FingerFromCornerParams>;
export const FingerFromCorner: React.FC<{ tip: Pt; at: number; angle?: number; scale?: number; slide?: number; tapAt?: number; skin?: string; sleeve?: string; ripple?: boolean; out?: number; p?: Partial<FingerFromCornerP> }> = ({ tip, at, angle: an0, scale: sc0, slide: sl0, tapAt, skin: sk0, sleeve: sv0, ripple: rp0, out, p }) => {
  const P = def(FingerFromCornerParams, { ...given({ angle: an0, scale: sc0, slide: sl0, skin: sk0, sleeve: sv0, ripple: rp0 }), ...p });
  const { angle, scale, slide, skin, sleeve, ripple, dist } = P, TD = P.tapDur;
  const f = useCurrentFrame();
  if (f < at) return null;
  const a = (angle * Math.PI) / 180, ux = Math.sin(a), uy = -Math.cos(a); // 손가락 방향 단위벡터
  let k = lerp(f, at, at + slide, 1, 0, QUART_OUT);
  if (out !== undefined) k = Math.max(k, lerp(f, out, out + P.outDur, 0, 1, Easing.in(Easing.quad)));
  const ta = tapAt ?? at + slide + P.tapDelay, tg = f - ta;
  const tap = tg >= 0 && tg < TD ? kf(tg, 0, [0, (TD * 3) / 7, TD], [0, 1, 0]) * P.tapDepth : 0;
  const px = tip[0] - ux * (dist * k - tap), py = tip[1] - uy * (dist * k - tap);
  // 세모지 그림체 검지 손(hand_point_big): 손끝 = 이미지 (0.565, 0), 폭 260×scale. 소매 색은 아래 절반에 color 블렌드로 입힘
  const hw = 260 * scale * (tg >= 2 && tg < 4 ? 0.97 : 1), hh = propH("hand_point_big", hw), mk = `url(${prop("hand_point_big")})`;
  return (
    <>
      {ripple && tg >= 2 && tg < 14 && <div style={{ position: "absolute", left: tip[0] - 60, top: tip[1] - 60, width: 120, height: 120, borderRadius: "50%", border: `${lerp(tg, 2, 14, 10, 2)}px solid #fff`, transform: `scale(${lerp(tg, 2, 14, 0.3, P.rippleSize, Easing.out(Easing.quad))})`, opacity: lerp(tg, 2, 14, 1, 0), boxShadow: "0 0 8px rgba(0,0,0,0.3)" }} />}
      <div style={{ position: "absolute", left: px - 0.565 * hw, top: py, width: hw, height: hh, transformOrigin: `${0.565 * hw}px 0px`, transform: `rotate(${angle}deg)`, filter: "drop-shadow(-6px 10px 10px rgba(0,0,0,0.3))", isolation: "isolate" }}>
        <Img src={prop("hand_point_big")} style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }} />
        <div style={{ position: "absolute", left: 0, right: 0, top: "52%", bottom: 0, background: sleeve, mixBlendMode: "color", WebkitMaskImage: mk, maskImage: mk, WebkitMaskSize: `${hw}px ${hh}px`, maskSize: `${hw}px ${hh}px`, WebkitMaskPosition: `0 ${-0.52 * hh}px`, maskPosition: `0 ${-0.52 * hh}px`, WebkitMaskRepeat: "no-repeat", maskRepeat: "no-repeat" } as React.CSSProperties} />
      </div>
    </>
  );
};

// ══ 11. 군중 솟아오름 ═════════════════════════════════════════════════════════
const CROWD_CAST: CastId[] = ["walker1", "c2_boss", "c3_woman", "c4_elder", "c5_chef"];
const CROWD_COLS = ["#E57373", "#64B5F6", "#FFD54F", "#81C784", "#BA68C8", "#FF8A65", "#4DD0E1", "#F06292"];
/** 반투명(70%) 세모지 캐스트 군중(환호 포즈, colors = 인물 둘레 색 글로우) 한 줄이 아래에서 10~12f ease-out 으로 솟고 이후 까딱 */
export const CrowdRiseParams = z.object({
  rise: num(11, 1, 40, 1, "솟아오르는 시간", "timing", "f"),
  stagger: num(1.5, 0, 10, 0.1, "사람 간 스태거", "timing", "f"),
  bob: num(10, 0, 50, 1, "까딱 높이", "motion", "px"),
  bobSlow: num(5, 1, 20, 0.5, "까딱 느림(클수록 느림)", "timing"),
  armWave: num(12, 0, 60, 1, "팔 흔들기", "motion", "°"),
  n: num(10, 1, 30, 1, "인원 수", "size"),
  height: num(380, 100, 900, 10, "실루엣 높이", "size", "px"),
  sizeVar: num(0.3, 0, 1, 0.05, "키 편차(배)", "size"),
  scatter: num(60, 0, 300, 5, "가로 흩어짐", "size", "px"),
  opacity: num(0.7, 0, 1, 0.05, "불투명도", "look"),
});
export type CrowdRiseP = z.infer<typeof CrowdRiseParams>;
export const CrowdRise: React.FC<{ at: number; n?: number; y?: number; x0?: number; x1?: number; height?: number; opacity?: number; colors?: string[]; rise?: number; stagger?: number; seed?: string; p?: Partial<CrowdRiseP> }> = ({ at, n: n0, y = H + 30, x0 = -40, x1 = W + 40, height: h0, opacity: o0, colors = CROWD_COLS, rise: r0, stagger: s0, seed = "cr", p }) => {
  const P = def(CrowdRiseParams, { ...given({ n: n0, height: h0, opacity: o0, rise: r0, stagger: s0 }), ...p });
  const { height, opacity, rise, stagger } = P, n = Math.max(1, Math.round(P.n));
  const f = useCurrentFrame();
  if (f < at) return null;
  return (
    <>
      {Array.from({ length: n }).map((_, i) => {
        const a0 = at + Math.round(i * stagger * (random(`${seed}o${i}`) + 0.5)), g = f - a0;
        if (g < 0) return null;
        const sc = 1 - P.sizeVar / 2 + P.sizeVar * random(`${seed}s${i}`), hh = height * sc, ww = hh * (200 / 380);
        const cx = x0 + ((i + 0.5) / n) * (x1 - x0) + (random(`${seed}x${i}`) - 0.5) * P.scatter;
        const ty = lerp(g, 0, rise, hh + 60, 0, QUART_OUT), ph = random(`${seed}p${i}`) * TAU;
        const bob = g > rise ? Math.sin((g - rise) / P.bobSlow + ph) * P.bob : 0;
        const pose = Math.floor(random(`${seed}q${i}`) * 4), wv = P.armWave * Math.sin(g / 4 + ph);
        // 세모지 캐스트 군중(인포그래픽 실루엣 금지): 사람마다 캐스트·좌우반전·seed 다르게, 환호 포즈 = 팔 들기(없으면 팔 회전), 팔 흔들기 = rotR/rotL
        const cast = CROWD_CAST[Math.floor(random(`${seed}c${i}`) * CROWD_CAST.length)];
        const up = CAST[cast].extras.includes("arm_raise_fist") ? "arm_raise_fist" : "arm_up_hang";
        const pz: RigPose = pose === 0 ? { armR: up, armL: up, rotR: wv * 0.4, rotL: -wv * 0.4, face: CAST[cast].extras.includes("face_smile") ? "face_smile" : undefined }
          : pose === 1 ? { armR: up, rotR: wv * 0.5 } : pose === 2 ? { armL: up, rotL: -wv * 0.5 } : { rotR: wv * 0.3, rotL: -wv * 0.3 };
        const col = colors[i % colors.length];
        return (
          <div key={i} style={{ position: "absolute", left: 0, top: 0, transform: `translateY(${ty + bob}px)`, opacity, filter: `drop-shadow(0 0 6px ${col})` }}>
            <SemojiRig cast={cast} x={cx} y={y} h={hh} pose={pz} flip={random(`${seed}f${i}`) < 0.5} seed={`${seed}${i}`} />
          </div>
        );
      })}
    </>
  );
};

// ══ 12. 인생 경로 타임라인 ═══════════════════════════════════════════════════════
export type WalkStop = { x: number; label?: string; sub?: string; hold?: number };
/** 캐릭터가 ~6px/f 로 걸어가며(스텝 까딱) 빨간 8px 선이 따라 그려지고, 정지점마다 빨간 링 노드(Ø40)가 3f 팝 + 라벨.
 *  occluders 는 캐릭터 위에 그려져 '건물 뒤로 지나감'을 만든다 */
export const WalkPathParams = z.object({
  speed: num(6, 0.5, 40, 0.5, "걷는 속도(px/f)", "motion"),
  hold: num(16, 0, 90, 1, "정지점 머무름", "timing", "f"),
  stepLen: num(38, 5, 200, 1, "보폭", "motion", "px"),
  bounce: num(8, 0, 40, 1, "걸음 튐 높이", "motion", "px"),
  sway: num(3, 0, 20, 0.5, "걸음 기울기", "motion", "°"),
  nodePop: num(1.2, 1, 2, 0.05, "노드 팝 오버슈트(배)", "motion"),
  lineW: num(8, 1, 30, 1, "선 두께", "size", "px"),
  node: num(40, 10, 120, 2, "노드 지름", "size", "px"),
  nodeRing: num(8, 1, 30, 1, "노드 링 두께", "size", "px"),
  labelSize: num(40, 16, 100, 1, "라벨 크기", "size", "px"),
  lineColor: col("#E53935", "선·노드 색"),
  glow: flag(true, "캐릭터 흰 외곽광", "look"),
});
export type WalkPathP = z.infer<typeof WalkPathParams>;
export const WalkPath: React.FC<{ y: number; x0: number; stops: WalkStop[]; at: number; w: number; h: number; img?: string; children?: RN; speed?: number; hold?: number; stepLen?: number; lineColor?: string; occluders?: RN; startLabel?: string; glow?: boolean; p?: Partial<WalkPathP> }> = ({ y, x0, stops, at, w, h, img, children, speed: sp0, hold: ho0, stepLen: sl0, lineColor: lc0, occluders, startLabel, glow: gl0, p }) => {
  const P = def(WalkPathParams, { ...given({ speed: sp0, hold: ho0, stepLen: sl0, lineColor: lc0, glow: gl0 }), ...p });
  const { hold, lineColor, glow } = P, speed = Math.max(0.1, P.speed), stepLen = Math.max(1, P.stepLen), NS = P.node, LW = P.lineW;
  const f = useCurrentFrame();
  let t = at, pos = x0;
  const segs: { t0: number; t1: number; a: number; b: number }[] = [], arrive: number[] = [];
  for (const s of stops) { const dt = Math.abs(s.x - pos) / speed; segs.push({ t0: t, t1: t + dt, a: pos, b: s.x }); arrive.push(t + dt); t += dt + (s.hold ?? hold); pos = s.x; }
  let cx = x0, moving = false, dir = 1;
  for (const sg of segs) {
    if (f >= sg.t0) { dir = sg.b >= sg.a ? 1 : -1; cx = f >= sg.t1 ? sg.b : sg.a + (sg.b - sg.a) * ((f - sg.t0) / (sg.t1 - sg.t0)); moving = f < sg.t1; }
  }
  const dist = Math.abs(cx - x0), ph = (dist / stepLen) * Math.PI;
  const dy = moving ? -Math.abs(Math.sin(ph)) * P.bounce : 0, rot = moving ? Math.sin(ph) * P.sway : 0;
  const node = (nx: number, a: number, label?: string, sub?: string, k?: number) => {
    if (f < a) return null;
    const s = kf(f, a, [0, 2, 3], [0, P.nodePop, 1]), tp = textPop(f, a + 1);
    return (
      <React.Fragment key={k}>
        <div style={{ position: "absolute", left: nx - NS / 2, top: y - NS / 2, width: NS, height: NS, borderRadius: "50%", background: "#fff", border: `${P.nodeRing}px solid ${lineColor}`, boxSizing: "border-box", transform: `scale(${s})` }} />
        {label && f >= a + 1 && <div style={{ position: "absolute", left: nx, top: y + NS / 2 + 14, transform: `translateX(-50%) scale(${tp.s})`, opacity: tp.op, textAlign: "center", whiteSpace: "nowrap" }}>
          <div style={{ fontFamily: "NeoHv", fontSize: P.labelSize, color: "#1b1b1b" }}>{hz(label)}</div>
          {sub && <div style={{ fontFamily: "NeoEb", fontSize: (P.labelSize * 7) / 10, color: "#555", marginTop: 4 }}>{hz(sub)}</div>}
        </div>}
      </React.Fragment>
    );
  };
  return (
    <>
      {f >= at && <div style={{ position: "absolute", left: Math.min(x0, cx), top: y - LW / 2, width: Math.abs(cx - x0), height: LW, background: lineColor, borderRadius: LW / 2 }} />}
      {node(x0, at, startLabel, undefined, -1)}
      {stops.map((s, i) => node(s.x, Math.ceil(arrive[i]), s.label, s.sub, i))}
      <div style={{ position: "absolute", left: cx - w / 2, top: y - h - 6 + dy, width: w, height: h, transformOrigin: "50% 100%", transform: `rotate(${rot}deg) scaleX(${dir})` }}>
        <Body img={img} glow={glow}>{children}</Body>
      </div>
      {occluders}
    </>
  );
};

// ══ 13. 승진 계단 ═════════════════════════════════════════════════════════════
/** 아이소메트릭 계단 + 단마다 흰 깃발(연도/직함). 캐릭터가 every f 마다 한 칸 점프컷 + 미세 스쿼시 */
export const StairPromotionParams = z.object({
  every: num(15, 1, 60, 1, "한 칸 오르는 간격", "timing", "f"),
  squash: num(0.1, 0, 0.4, 0.01, "착지 스쿼시 세기", "motion"),
  flagPop: num(1.12, 1, 2, 0.01, "깃발 팝(배)", "motion"),
  flagWave: num(2, 0, 15, 0.5, "깃발 펄럭임", "motion", "°"),
  stepW: num(240, 60, 600, 5, "계단 폭", "size", "px"),
  stepH: num(110, 20, 300, 5, "계단 높이", "size", "px"),
  depth: num(110, 0, 300, 5, "계단 깊이", "size", "px"),
  top: col("#F4F0E8", "윗면 색"),
  front: col("#D6CCBC", "앞면 색"),
  side: col("#B3A794", "옆면 색"),
  hilite: col("#FFF6D6", "현재 칸 색"),
  accent: col("#E53935", "도달 깃발 글자 색"),
});
export type StairPromotionP = z.infer<typeof StairPromotionParams>;
export const StairPromotion: React.FC<{ x0: number; y0: number; steps: { flag: string; sub?: string }[]; at: number; w: number; h: number; img?: string; children?: RN; stepW?: number; stepH?: number; depth?: number; every?: number; top?: string; front?: string; side?: string; accent?: string; glow?: boolean; p?: Partial<StairPromotionP> }> = ({ x0, y0, steps, at, w, h, img, children, stepW: sw0, stepH: sh0, depth: dp0, every: ev0, top: tp0, front: fr0, side: sd0, accent: ac0, glow = true, p }) => {
  const P = def(StairPromotionParams, { ...given({ stepW: sw0, stepH: sh0, depth: dp0, every: ev0, top: tp0, front: fr0, side: sd0, accent: ac0 }), ...p });
  const { stepW, stepH, depth, top, front, side, accent } = P, every = Math.max(1, P.every), Q = P.squash;
  const f = useCurrentFrame();
  const n = steps.length, ddx = depth * 0.866, ddy = -depth * 0.5;
  const cur = Math.max(0, Math.min(n - 1, Math.floor((f - at) / every)));
  const tt = f < at ? 99 : (f - at) - cur * every;
  const sq = tt < 3 && cur > 0 ? { sy: [1 - Q, 1 + Q * 0.4, 1][tt], sx: [1 + Q * 0.6, 1 - Q * 0.2, 1][tt] } : { sy: 1, sx: 1 };
  const cols = steps.map((_, i) => ({ l: x0 + i * stepW, r: x0 + (i + 1) * stepW, t: y0 - (i + 1) * stepH }));
  const c = cols[cur], chx = c.l + stepW * 0.58 + ddx * 0.4, chy = c.t + ddy * 0.4;
  return (
    <>
      <Full>
        {cols.map((q, i) => (
          <g key={i} stroke="#6d6253" strokeWidth={3} strokeLinejoin="round">
            <polygon points={`${q.r},${q.t} ${q.r + ddx},${q.t + ddy} ${q.r + ddx},${y0 + ddy} ${q.r},${y0}`} fill={side} />
            <rect x={q.l} y={q.t} width={stepW} height={y0 - q.t} fill={front} />
            <polygon points={`${q.l},${q.t} ${q.r},${q.t} ${q.r + ddx},${q.t + ddy} ${q.l + ddx},${q.t + ddy}`} fill={i === cur ? P.hilite : top} />
          </g>
        ))}
      </Full>
      {cols.map((q, i) => {
        const px = q.l + 20 + ddx * 0.8, py = q.t + ddy * 0.8, on = i <= cur && f >= at;
        const wv = Math.sin(f / 6 + i) * P.flagWave;
        return (
          <React.Fragment key={i}>
            <div style={{ position: "absolute", left: px - 3, top: py - 190, width: 6, height: 190, background: "#4a4036", borderRadius: 3 }} />
            <div style={{ position: "absolute", left: px - 160, top: py - 186, width: 157, height: 84, background: "#fff", border: "3px solid #4a4036", borderRadius: 4, boxSizing: "border-box", transformOrigin: "100% 50%", transform: `skewY(${wv}deg) scale(${on && i === cur && tt < 4 ? kf(tt, 0, [0, 2, 4], [1, P.flagPop, 1]) : 1})`, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", boxShadow: "0 3px 5px rgba(0,0,0,0.2)" }}>
              <div style={{ fontFamily: "NeoHv", fontSize: 32, color: on ? accent : "#333", lineHeight: 1 }}>{hz(steps[i].flag)}</div>
              {steps[i].sub && <div style={{ fontFamily: "NeoEb", fontSize: 20, color: "#444", marginTop: 4, whiteSpace: "nowrap" }}>{hz(steps[i].sub!)}</div>}
            </div>
          </React.Fragment>
        );
      })}
      <div style={{ position: "absolute", left: chx - w / 2, top: chy - h, width: w, height: h, transformOrigin: "50% 100%", transform: `scale(${sq.sx},${sq.sy})` }}>
        <Body img={img} glow={glow}>{children}</Body>
      </div>
    </>
  );
};

// ══ 14. 슬라이드인 + 리프레임 카메라 ══════════════════════════════════════════════
/** 래퍼: 캐릭터가 화면 밖에서 16~18f ease-out 슬라이드인, 동시에 부모 카메라가 9f 동안 +4.5% 줌 & y −70px(콘텐츠 이동).
 *  주의: 줌 4.5% 만으로는 −70px 이동의 아래 가장자리를 못 덮는다 → 배경은 ~90px 블리드로 크게 깔 것 */
export const SlideInReframeParams = z.object({
  slide: num(17, 1, 60, 1, "슬라이드인 시간", "timing", "f"),
  dist: num(1150, 0, 2400, 10, "슬라이드 거리", "motion", "px"),
  from: choice("right", ["right", "left"], "들어오는 방향"),
  camDur: num(9, 1, 60, 1, "카메라 리프레임 시간", "timing", "f"),
  zoom: num(0.045, -0.2, 0.5, 0.005, "카메라 줌(배)", "motion"),
  dy: num(-70, -300, 300, 5, "카메라 세로 이동", "motion", "px"),
});
export type SlideInReframeP = z.infer<typeof SlideInReframeParams>;
export const SlideInReframe: React.FC<{ at: number; char: RN; children?: RN; from?: "left" | "right"; slide?: number; dist?: number; zoom?: number; dy?: number; camDur?: number; origin?: string; p?: Partial<SlideInReframeP> }> = ({ at, char, children, from: fr0, slide: sl0, dist: di0, zoom: zo0, dy: dy0, camDur: cd0, origin = "50% 50%", p }) => {
  const P = def(SlideInReframeParams, { ...given({ from: fr0, slide: sl0, dist: di0, zoom: zo0, dy: dy0, camDur: cd0 }), ...p });
  const { from, slide, dist, zoom, dy, camDur } = P;
  const f = useCurrentFrame();
  const k = lerp(f, at, at + camDur, 0, 1, Easing.inOut(Easing.cubic));
  const tx = lerp(f, at, at + slide, from === "right" ? dist : -dist, 0, QUART_OUT);
  return (
    <AbsoluteFill style={{ transformOrigin: origin, transform: `translateY(${dy * k}px) scale(${1 + zoom * k})` }}>
      {children}
      {f >= at && <AbsoluteFill style={{ transform: `translateX(${tx}px)` }}>{char}</AbsoluteFill>}
    </AbsoluteFill>
  );
};

// ══ 15. 포즈 스왑 ═════════════════════════════════════════════════════════════
/** 지정 프레임에 포즈 이미지를 1f 하드 스왑. effect(fireAt) 는 스왑 1f 뒤에 발사할 이펙트를 돌려준다 */
export const PoseSwapParams = z.object({
  effectDelay: num(1, 0, 20, 1, "스왑 후 이펙트 지연", "timing", "f"),
  bob: flag(true, "까딱"),
  bobPeriod: num(10, 2, 60, 1, "까딱 주기", "timing", "f"),
  bobAmp: num(0.01, 0, 0.1, 0.005, "까딱 깊이(배)", "motion"),
  glow: flag(true, "흰 외곽광", "look"),
});
export type PoseSwapP = z.infer<typeof PoseSwapParams>;
export const PoseSwap: React.FC<{ x: number; y: number; w: number; h: number; poses: { at: number; img: string; flip?: boolean; effect?: (fireAt: number) => RN }[]; glow?: boolean; bob?: boolean; p?: Partial<PoseSwapP> }> = ({ x, y, w, h, poses, glow: gl0, bob: bo0, p: pp }) => {
  const P = def(PoseSwapParams, { ...given({ glow: gl0, bob: bo0 }), ...pp });
  const f = useCurrentFrame();
  let cur = -1;
  poses.forEach((p, i) => { if (f >= p.at) cur = i; });
  const sy = P.bob ? pingPong(f, P.bobPeriod, 1, 1 + P.bobAmp) : 1;
  return (
    <>
      {cur >= 0 && <Img src={src(poses[cur].img)} style={{ position: "absolute", left: x - w / 2, top: y - h, width: w, height: h, objectFit: "contain", objectPosition: "50% 100%", transformOrigin: "50% 100%", transform: `scale(${poses[cur].flip ? -1 : 1},${sy})`, filter: P.glow ? GLOW : undefined }} />}
      {poses.map((p, i) => (p.effect ? <React.Fragment key={i}>{p.effect(p.at + P.effectDelay)}</React.Fragment> : null))}
    </>
  );
};
