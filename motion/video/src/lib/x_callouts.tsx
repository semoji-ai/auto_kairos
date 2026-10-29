// 도감 "분석만" 콜아웃·라벨 기법 구현 (x_callouts) — ref1 / ref4(apple·hyundai·samsung·cocacola) 프레임 대조 실측
import React from "react";
import { AbsoluteFill, Img, useCurrentFrame, Easing, random } from "remotion";
import { z } from "zod";
import { num, col, flag, def } from "../params/p";
import { W, H, lerp, kf, src, hz, QUART_OUT } from "../fx";
import { prop, propH } from "./kit";
import { KitImg } from "./callouts";
import { SemojiRig } from "./semoji_rig";

type RN = React.ReactNode;
type Pt = [number, number];
const pos = (v: number, m = 0.001) => Math.max(m, v);
const TAU = Math.PI * 2;
/** undefined 가 아닌 개별 prop 만 남긴다(스키마 기본값을 덮지 않게) */
const pick = <T extends Record<string, unknown>>(o: T): Partial<T> =>
  Object.fromEntries(Object.entries(o).filter(([, v]) => v !== undefined)) as Partial<T>;
/** 팝 곡선 from → 1+over → 1 (len f) */
const popK = (f: number, at: number, len: number, from: number, over: number) =>
  kf(f, at, [0, pos(len) * 0.65, pos(len)], [from, 1 + over, 1], Easing.out(Easing.quad));

/** 가로 모션블러(SVG feGaussianBlur x만) */
const HBlurBox: React.FC<{ amt: number; style?: React.CSSProperties; children: RN }> = ({ amt, style, children }) => {
  const id = "xhb" + React.useId().replace(/[^a-zA-Z0-9]/g, "");
  const fl = [amt > 0.3 ? `url(#${id})` : "", style?.filter || ""].join(" ").trim();
  return (
    <div style={{ ...style, filter: fl || undefined }}>
      <svg width={0} height={0} style={{ position: "absolute" }}>
        <filter id={id} x="-60%" y="-10%" width="220%" height="120%"><feGaussianBlur stdDeviation={`${amt} 0`} /></filter>
      </svg>
      {children}
    </div>
  );
};

// ══ 1. 손글씨 루프 화살표 ═══════════════════════════════════════════════════
// ref1 5:26 — 사진이 들어오기 ~15f 전, 검정 루프 화살표가 3~4f 만에 모션블러를 끌며 그려지고 이후 보일링(떨림)
const LOOP_D = "M10,205 C70,200 128,188 160,160 C196,128 184,86 152,94 C116,103 118,192 186,196 C252,200 306,122 380,96";
export const LoopArrowParams = z.object({
  drawLen: num(4, 1, 30, 1, "그리기 길이", "timing", "f"),
  drawBlur: num(5, 0, 20, 0.5, "그리는 동안 블러", "look", "px"),
  boilEvery: num(4, 1, 20, 1, "보일링 교체 간격", "timing", "f"),
  boilRot: num(1.6, 0, 10, 0.1, "보일링 흔들림 각도", "motion", "°"),
  boilMove: num(3, 0, 20, 0.5, "보일링 흔들림 거리", "motion", "px"),
  headLen: num(46, 10, 120, 1, "화살촉 길이", "size", "px"),
  scale: num(0.6, 0.2, 3, 0.05, "크기(배)", "size"),
  width: num(17, 2, 40, 0.5, "선 두께(뷰박스 단위)", "size", "px"),
  color: col("#1d1d1d", "선 색"),
});
export type LoopArrowP = z.infer<typeof LoopArrowParams>;
export const LoopArrow: React.FC<{ x: number; y: number; at: number; rot?: number; flip?: boolean; out?: number; p?: Partial<LoopArrowP> }> = ({ x, y, at, rot = 0, flip, out, p }) => {
  const P = def(LoopArrowParams, p);
  const f = useCurrentFrame();
  if (f < at || (out !== undefined && f >= out)) return null;
  const t = kf(f, at, [0, P.drawLen], [0, 1], Easing.out(Easing.quad));
  const head = kf(f, at + P.drawLen * 0.75, [0, pos(P.drawLen * 0.25)], [0, 1]);
  const bs = Math.floor((f - at) / P.boilEvery);
  const done = t >= 1;
  const br = done ? (random(`la-r${bs}`) - 0.5) * 2 * P.boilRot : 0;
  const bx = done ? (random(`la-x${bs}`) - 0.5) * 2 * P.boilMove : 0, by = done ? (random(`la-y${bs}`) - 0.5) * 2 * P.boilMove : 0;
  const tip: Pt = [380, 96], ang = Math.atan2(96 - 112, 380 - 300), L = P.headLen;
  const h1: Pt = [tip[0] - L * Math.cos(ang - 0.6), tip[1] - L * Math.sin(ang - 0.6)];
  const h2: Pt = [tip[0] - L * Math.cos(ang + 0.6), tip[1] - L * Math.sin(ang + 0.6)];
  const blur = P.drawBlur * (1 - t);
  return (
    <svg width={400 * P.scale} height={240 * P.scale} viewBox="0 0 400 240" style={{ position: "absolute", left: x, top: y, overflow: "visible", transform: `translate(${bx}px,${by}px) rotate(${rot + br}deg) scaleX(${flip ? -1 : 1})`, filter: blur > 0.2 ? `blur(${blur}px)` : undefined }}>
      <path d={LOOP_D} pathLength={1} fill="none" stroke={P.color} strokeWidth={P.width} strokeLinecap="round" strokeLinejoin="round" strokeDasharray="1 1" strokeDashoffset={1 - t} />
      {head > 0 && <path d={`M${h1[0]},${h1[1]} L${tip[0]},${tip[1]} L${h2[0]},${h2[1]}`} pathLength={1} fill="none" stroke={P.color} strokeWidth={P.width} strokeLinecap="round" strokeLinejoin="round" strokeDasharray="1 1" strokeDashoffset={1 - head} />}
    </svg>
  );
};

// ══ 2. 라벨 칩 + 반짝이 파티클 ═══════════════════════════════════════════════
// ref1 13:28 — 접시 위 검정 둥근 칩(~100×30) 팝, 초록 발광 파티클이 칩 주변에서 떠올라 흩어짐
export const LabelChipSparkleParams = z.object({
  popLen: num(10, 1, 30, 1, "칩 팝 길이", "timing", "f"),
  popFrom: num(0.3, 0, 1, 0.05, "칩 시작 크기(배)", "motion"),
  count: num(34, 0, 80, 1, "파티클 개수", "size"),
  life: num(34, 4, 120, 1, "파티클 수명", "timing", "f"),
  emitSpan: num(20, 0, 90, 1, "파티클 방출 기간", "timing", "f"),
  rise: num(170, 0, 400, 5, "파티클 상승 거리", "motion", "px"),
  spread: num(300, 0, 800, 5, "파티클 퍼짐 폭", "motion", "px"),
  dot: num(18, 2, 40, 1, "파티클 크기", "size", "px"),
  fontSize: num(26, 10, 80, 1, "글자 크기", "size", "px"),
  chipColor: col("#141414", "칩 색"),
  sparkColor: col("#62E24A", "파티클 색"),
});
export type LabelChipSparkleP = z.infer<typeof LabelChipSparkleParams>;
export const LabelChipSparkle: React.FC<{ text: string; x: number; y: number; at: number; seed?: string; p?: Partial<LabelChipSparkleP> }> = ({ text, x, y, at, seed = "lcs", p }) => {
  const P = def(LabelChipSparkleParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const s = popK(f, at, P.popLen, P.popFrom, 0.1);
  const n = Math.round(P.count);
  return (
    <>
      {Array.from({ length: n }).map((_, i) => {
        const a0 = at + random(`${seed}t${i}`) * P.emitSpan, g = f - a0;
        if (g < 0 || g > P.life) return null;
        const u = g / P.life;
        const dx = (random(`${seed}x${i}`) - 0.5) * P.spread * (0.4 + u);
        const dy = P.dot - P.rise * (0.3 + 0.7 * random(`${seed}r${i}`)) * Easing.out(Easing.quad)(u) + (random(`${seed}y${i}`) - 0.3) * 30;
        const sz = P.dot * (0.5 + random(`${seed}s${i}`)) * (u < 0.15 ? u / 0.15 : 1);
        const op = u > 0.6 ? 1 - (u - 0.6) / 0.4 : 1;
        const tw = 0.6 + 0.4 * Math.abs(Math.sin(g * 0.5 + i));
        return <div key={i} style={{ position: "absolute", left: x + dx - sz / 2, top: y + dy - sz / 2, width: sz, height: sz, borderRadius: "50%", background: P.sparkColor, opacity: op * tw, boxShadow: `0 0 ${sz}px ${P.sparkColor}` }} />;
      })}
      <div style={{ position: "absolute", left: x, top: y, transform: `translate(-50%,-50%) scale(${s})`, background: P.chipColor, color: "#fff", fontFamily: "NeoEb", fontSize: P.fontSize, padding: `${P.fontSize * 0.35}px ${P.fontSize * 0.9}px ${P.fontSize * 0.25}px`, borderRadius: 999, whiteSpace: "nowrap", lineHeight: 1.1, boxShadow: "0 2px 4px rgba(0,0,0,0.3)" }}>{text}</div>
    </>
  );
};

// ══ 3. 번호 사유 탭(좌측 도킹) ═══════════════════════════════════════════════
// ref4-apple 1:10:45 — 왼쪽 끝에 붙은 반쪽 pill(#3a3a3a, r≈40) 이 ~10f quart-out 으로 밀려 들어옴, 항목 교체는 하드컷
export const NumberedReasonTabParams = z.object({
  slideLen: num(10, 1, 40, 1, "슬라이드인 길이", "timing", "f"),
  slideEach: flag(false, "항목마다 슬라이드(끄면 하드컷)"),
  top: num(195, 0, 900, 1, "위치 y(위)", "size", "px"),
  height: num(120, 40, 260, 1, "탭 높이", "size", "px"),
  minW: num(425, 100, 1200, 5, "탭 최소 너비", "size", "px"),
  radius: num(40, 0, 120, 1, "오른쪽 모서리 반지름", "size", "px"),
  fontSize: num(60, 20, 120, 1, "글자 크기", "size", "px"),
  shadow: num(5, 0, 20, 0.5, "글자 그림자", "look", "px"),
  bg: col("#3a3a3a", "탭 색"),
  color: col("#ffffff", "글자 색"),
});
export type NumberedReasonTabP = z.infer<typeof NumberedReasonTabParams>;
export const NumberedReasonTab: React.FC<{ items: { text: string; at: number }[]; out?: number; p?: Partial<NumberedReasonTabP> }> = ({ items, out, p }) => {
  const P = def(NumberedReasonTabParams, p);
  const f = useCurrentFrame();
  const idx = items.reduce((a, it, i) => (f >= it.at ? i : a), -1);
  if (idx < 0 || (out !== undefined && f >= out)) return null;
  const it = items[idx], a0 = idx === 0 || P.slideEach ? it.at : items[0].at;
  const e = kf(f, a0, [0, P.slideLen], [0, 1], QUART_OUT);
  return (
    <div style={{ position: "absolute", left: 0, top: P.top, height: P.height, minWidth: P.minW, boxSizing: "border-box", transform: `translateX(${-100 * (1 - e)}%)`, background: P.bg, borderRadius: `0 ${P.radius}px ${P.radius}px 0`, display: "flex", alignItems: "center", padding: `0 ${P.radius + 10}px 0 ${P.fontSize * 0.45}px`, fontFamily: "NeoHv", fontSize: P.fontSize, color: P.color, whiteSpace: "nowrap", textShadow: `0 ${P.shadow}px ${P.shadow}px rgba(0,0,0,0.55)`, lineHeight: 1 }}>
      <span style={{ paddingTop: P.fontSize * 0.1 }}>{hz(it.text)}</span>
    </div>
  );
};

// ══ 4. 클립보드 문서 스윙 드롭 + 줄별 리빌 + 손 서명 ════════════════════════════
// ref4-apple 27:23~27:40 — 위쪽 클립을 축으로 -70°→+10°→-5°→0° (22f) 떨어져 정착, 느린 푸시인 1.0→1.08,
// 본문 줄은 아래→위 마스크+블러 해제 ~9f, 마지막에 펜 쥔 손이 오른쪽 아래에서 들어와 서명
const SIGN_D = "M0,30 C12,6 22,4 20,26 C18,44 30,40 40,18 C46,6 52,10 50,30 C62,12 72,8 80,24 C88,40 100,30 112,14 C118,6 126,16 140,20";
export const ClipboardSwingDropParams = z.object({
  dropLen: num(22, 4, 60, 1, "드롭 길이", "timing", "f"),
  startRot: num(-70, -180, 180, 1, "시작 각도", "motion", "°"),
  overRot: num(10, -45, 45, 1, "넘침 각도", "motion", "°"),
  backRot: num(-5, -30, 30, 1, "되돌이 각도", "motion", "°"),
  pushTo: num(1.08, 1, 1.5, 0.01, "푸시인 최종 배율", "motion"),
  pushLen: num(90, 0, 300, 1, "푸시인 길이", "timing", "f"),
  lineLen: num(9, 1, 30, 1, "줄 리빌 길이", "timing", "f"),
  lineBlur: num(6, 0, 20, 0.5, "줄 리빌 블러", "look", "px"),
  handLen: num(10, 1, 40, 1, "손 슬라이드인 길이", "timing", "f"),
  signLen: num(22, 2, 80, 1, "서명 그리기 길이", "timing", "f"),
  w: num(560, 200, 900, 5, "클립보드 너비", "size", "px"),
  h: num(720, 250, 1000, 5, "클립보드 높이", "size", "px"),
  board: col("#2a2a2c", "판 색"),
  paper: col("#f7f5f0", "종이 색"),
  ink: col("#1a1a1a", "서명 잉크 색"),
});
export type ClipboardSwingDropP = z.infer<typeof ClipboardSwingDropParams>;
export const ClipboardSwingDrop: React.FC<{ title: string; lines?: { text: string; at: number }[]; x: number; y: number; at: number; sign?: { at: number }; signLabel?: string; p?: Partial<ClipboardSwingDropP> }> = ({ title, lines = [], x, y, at, sign, signLabel = "서명 :", p }) => {
  const P = def(ClipboardSwingDropParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const L = P.dropLen;
  const rot = kf(f, at, [0, L * 0.55, L * 0.8, L], [P.startRot, P.overRot, P.backRot, 0], Easing.inOut(Easing.sin));
  const dy = kf(f, at, [0, L * 0.55], [-(y + P.h + 200), 0], Easing.out(Easing.quad));
  const push = P.pushLen > 0 ? lerp(f, at + L, at + L + P.pushLen, 1, P.pushTo, Easing.inOut(Easing.cubic)) : 1;
  const w = P.w, h = P.h, pad = w * 0.06;
  // 서명 위치(보드 로컬)
  const sx = w * 0.42, sy = h * 0.8;
  const st = sign ? kf(f, sign.at + P.handLen, [0, P.signLen], [0, 1], Easing.inOut(Easing.sin)) : 0;
  const handIn = sign ? kf(f, sign.at, [0, P.handLen], [0, 1], QUART_OUT) : 0;
  // 펜 끝 = 서명 경로를 따라감(근사: 가로 진행 + 약한 사인)
  const penX = sx + 140 * st, penY = sy + 20 + Math.sin(st * 14) * 10;
  return (
    <div style={{ position: "absolute", left: x - w / 2, top: y - h / 2, width: w, height: h, transform: `scale(${push})`, transformOrigin: "50% 50%" }}>
      <div style={{ position: "absolute", inset: 0, transform: `translateY(${dy}px) rotate(${rot}deg)`, transformOrigin: "50% 0%" }}>
        {/* 세모지 그림체 클립보드(clipboard_board): 이미지 x 23.8~100%·y 13~100% 가 판(위 클립은 판 밖으로 돌출) → w×h 에 맞춤. board/paper 색은 에셋 고정 */}
        <Img src={prop("clipboard_board")} style={{ position: "absolute", left: -0.238 * (w / 0.762), top: -0.13 * (h / 0.87), width: w / 0.762, height: h / 0.87, filter: "drop-shadow(0 16px 28px rgba(0,0,0,0.3))" }} />
        <div style={{ position: "absolute", left: pad, top: pad * 1.3, right: pad, bottom: pad }}>
          <div style={{ position: "absolute", left: 0, right: 0, top: h * 0.07, textAlign: "center", fontFamily: "NeoHv", fontSize: w * 0.085, color: "#2a2a2a" }}>{hz(title)}</div>
          {lines.map((ln, i) => {
            if (f < ln.at) return null;
            const u = kf(f, ln.at, [0, P.lineLen], [0, 1], Easing.out(Easing.cubic));
            return (
              <div key={i} style={{ position: "absolute", left: w * 0.06, right: w * 0.06, top: h * 0.2 + i * w * 0.075, height: w * 0.07, overflow: "hidden" }}>
                <div style={{ transform: `translateY(${(1 - u) * 100}%)`, filter: `blur(${P.lineBlur * (1 - u)}px)`, fontFamily: "NeoEb", fontSize: w * 0.045, color: "#333", whiteSpace: "nowrap" }}>{hz(ln.text)}</div>
              </div>
            );
          })}
        </div>
        <div style={{ position: "absolute", left: sx - w * 0.2, top: sy - w * 0.01, fontFamily: "NeoHv", fontSize: w * 0.045, color: "#222" }}>{signLabel}</div>
        <div style={{ position: "absolute", left: sx, top: sy + w * 0.055, width: w * 0.32, height: 3, background: "#cfcac0" }} />
        {sign && st > 0 && (
          <svg width={150} height={60} viewBox="-5 0 150 50" style={{ position: "absolute", left: sx, top: sy - 6, overflow: "visible" }}>
            <path d={SIGN_D} pathLength={1} fill="none" stroke={P.ink} strokeWidth={4} strokeLinecap="round" strokeLinejoin="round" strokeDasharray="1 1" strokeDashoffset={1 - st} />
          </svg>
        )}
      </div>
      {sign && handIn > 0 && (
        <div style={{ position: "absolute", left: penX, top: penY, transform: `translate(${(1 - handIn) * 700}px,${(1 - handIn) * 500}px)` }}>
          {/* 세모지 그림체 펜 쥔 손(hand_pen): 펜 끝 = 이미지 (0.02, 0.97) */}
          <KitImg id="hand_pen" x={0} y={0} w={420} ax={0.02} ay={0.97} />
        </div>
      )}
    </div>
  );
};
// ══ 5. 오렌지 pill 세로 스택 목록 ═════════════════════════════════════════════
// ref4-apple 50:08 — 작게 블러+글로우 → 0.4→1.08→1.0 ~6f, 어절 싱크 스태거, 쌓이면 유지
// 크기는 1080p 원본 재실측: pill ≈480×120(r≈34), 글자 ≈80px, 세로 간격 ≈155, 좌상단 x≈235·y≈205 (분석 문서 수치는 절반 스케일)
export const OrangePillStackParams = z.object({
  popLen: num(6, 1, 30, 1, "팝 길이", "timing", "f"),
  popFrom: num(0.4, 0, 1, 0.05, "시작 크기(배)", "motion"),
  popOver: num(0.08, 0, 0.4, 0.01, "오버슈트", "motion"),
  blur: num(8, 0, 30, 0.5, "등장 블러", "look", "px"),
  glow: num(26, 0, 80, 1, "등장 글로우", "look", "px"),
  gap: num(155, 30, 300, 1, "세로 간격", "size", "px"),
  height: num(120, 24, 240, 1, "pill 높이", "size", "px"),
  radius: num(34, 0, 120, 1, "모서리 반지름", "size", "px"),
  fontSize: num(80, 14, 160, 1, "글자 크기", "size", "px"),
  fill: col("#F0A830", "채움 색"),
  edge: col("#C9730E", "아래 테두리 색"),
});
export type OrangePillStackP = z.infer<typeof OrangePillStackParams>;
export const OrangePillStack: React.FC<{ items: { text: string; at: number }[]; x: number; y: number; p?: Partial<OrangePillStackP> }> = ({ items, x, y, p }) => {
  const P = def(OrangePillStackParams, p);
  const f = useCurrentFrame();
  return (
    <>
      {items.map((it, i) => {
        if (f < it.at) return null;
        const s = popK(f, it.at, P.popLen, P.popFrom, P.popOver);
        const u = kf(f, it.at, [0, P.popLen], [1, 0]);
        return (
          <div key={i} style={{ position: "absolute", left: x, top: y + i * P.gap, height: P.height, transform: `scale(${s})`, transformOrigin: "0% 50%", filter: `blur(${P.blur * u}px)`, background: P.fill, borderRadius: P.radius, boxShadow: `0 ${P.height * 0.08}px 0 ${P.edge}, inset 0 -${P.height * 0.08}px 0 ${P.edge}, 0 0 ${P.glow * u}px ${P.glow * u * 0.5}px rgba(255,210,110,${0.9 * u})`, padding: `0 ${P.height * 0.3}px`, display: "flex", alignItems: "center", fontFamily: "Jalnan", fontSize: P.fontSize, color: "#fff", whiteSpace: "nowrap", textShadow: "0 2px 2px rgba(150,80,0,0.35)" }}>
            <span style={{ paddingTop: P.fontSize * 0.08 }}>{hz(it.text)}</span>
          </div>
        );
      })}
    </>
  );
};

// ══ 6. 격투게임 VS 대결 HUD ═══════════════════════════════════════════════
// ref4-apple 1:41:17 — 원형 초상(좌 초록 링·우 빨강 링) + 사선 체력바 2단 + 네이비 팔각 VS 배지(HUD 뒤 ~9f 하드 등장) + 픽셀 배경·눈송이
export const FightingVsHudParams = z.object({
  vsDelay: num(9, 0, 60, 1, "VS 배지 지연", "timing", "f"),
  barIn: num(0, 0, 40, 1, "체력바 채움 길이(0=처음부터)", "timing", "f"),
  portrait: num(140, 60, 300, 2, "초상 지름", "size", "px"),
  topBarLen: num(560, 100, 800, 5, "상단 체력바 길이", "size", "px"),
  topBarH: num(40, 10, 90, 1, "상단 체력바 높이", "size", "px"),
  subBarLen: num(300, 50, 700, 5, "하단 게이지 길이", "size", "px"),
  subBarH: num(35, 8, 80, 1, "하단 게이지 높이", "size", "px"),
  slant: num(22, 0, 80, 1, "바 사선 폭", "motion", "px"),
  nameSize: num(48, 16, 100, 1, "이름 글자 크기", "size", "px"),
  snowSpeed: num(1.6, 0, 10, 0.1, "픽셀 눈 낙하 속도", "motion", "px/f"),
  snowCount: num(60, 0, 200, 1, "픽셀 눈 개수", "size"),
  badge: col("#1E2A44", "VS 배지 색"),
  leftRing: col("#39B54A", "왼쪽 링 색"),
  rightRing: col("#E23A2E", "오른쪽 링 색"),
});
export type FightingVsHudP = z.infer<typeof FightingVsHudParams>;
/** 픽셀 하늘·바다·구름 배경 (도트 느낌의 블록 구름 + 수평 밴드) */
export const PixelSeaBg: React.FC = () => {
  const bands = ["#20A8E0", "#3CB8EA", "#5BC8F0", "#86D8F4"];
  const cloud = (cx: number, cy: number, k: number, key: string) => (
    <g key={key} fill="#fff">
      {[[0, 0, 12, 3], [2, -2, 8, 2], [4, -3, 4, 1], [-2, 1, 16, 2]].map(([dx, dy, w, h], i) => <rect key={i} x={cx + dx * k} y={cy + dy * k} width={w * k} height={h * k} />)}
    </g>
  );
  return (
    <AbsoluteFill>
      <svg width={W} height={H} shapeRendering="crispEdges">
        {bands.map((c, i) => <rect key={i} x={0} y={i * 110} width={W} height={110} fill={c} />)}
        {cloud(1180, 360, 22, "c1")}{cloud(80, 390, 18, "c2")}{cloud(1500, 250, 14, "c3")}
        <rect x={0} y={470} width={W} height={H - 470} fill="#2C6FC0" />
        {Array.from({ length: 9 }).map((_, i) => <rect key={i} x={0} y={500 + i * 64} width={W} height={10} fill={i % 2 ? "#3A80CE" : "#2563B0"} />)}
        {Array.from({ length: 40 }).map((_, i) => <rect key={"w" + i} x={random(`wx${i}`) * W} y={520 + random(`wy${i}`) * 520} width={30 + random(`ww${i}`) * 60} height={6} fill="#5B9BE0" />)}
      </svg>
    </AbsoluteFill>
  );
};
const octagon = (w: number, h: number, c: number) => `polygon(${c}px 0, ${w - c}px 0, ${w}px ${c}px, ${w}px ${h - c}px, ${w - c}px ${h}px, ${c}px ${h}px, 0 ${h - c}px, 0 ${c}px)`;
export const FightingVsHud: React.FC<{ left: { name: string; img?: string; hp?: number; sub?: number }; right: { name: string; img?: string; hp?: number; sub?: number }; at: number; snow?: boolean; p?: Partial<FightingVsHudP> }> = ({ left, right, at, snow = true, p }) => {
  const P = def(FightingVsHudParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const cy = 265, D = P.portrait, fill = P.barIn > 0 ? kf(f, at, [0, P.barIn], [0, 1], Easing.out(Easing.cubic)) : 1;
  const side = (s: typeof left, dir: 1 | -1, ring: string) => {
    const px = dir === 1 ? 275 : W - 275, inner = px + dir * (D / 2 + 6);
    const bar = (len: number, bh: number, y: number, frac: number, bg: string, key: string) => {
      const x0 = dir === 1 ? inner : inner - len, sl = P.slant;
      // 중앙으로 갈수록 좁아지는 평행사변형(바깥 모서리 수직, 안쪽 모서리 사선)
      const poly = dir === 1 ? `polygon(0 0, 100% 0, calc(100% - ${sl}px) 100%, 0 100%)` : `polygon(0 0, 100% 0, 100% 100%, ${sl}px 100%)`;
      const fw = len * frac * fill;
      return (
        <div key={key} style={{ position: "absolute", left: x0, top: y, width: len, height: bh, clipPath: poly, background: "#10151f" }}>
          <div style={{ position: "absolute", top: 3, bottom: 3, [dir === 1 ? "left" : "right"]: 0, width: fw, background: bg } as React.CSSProperties} />
        </div>
      );
    };
    return (
      <React.Fragment key={dir}>
        {bar(P.topBarLen, P.topBarH, cy - P.topBarH - 4, s.hp ?? 1, "linear-gradient(180deg,#8BE05A,#2E9E3A)", "t")}
        {bar(P.subBarLen, P.subBarH, cy + 2, s.sub ?? 1, dir === 1 ? "linear-gradient(90deg,#F7E23A,#F08A1C)" : "linear-gradient(270deg,#F7E23A,#F08A1C)", "s")}
        <div style={{ position: "absolute", left: px - D / 2, top: cy - D / 2, width: D, height: D, borderRadius: "50%", background: "#fff", border: `${D * 0.07}px solid ${ring}`, boxSizing: "border-box", overflow: "hidden", boxShadow: "0 4px 10px rgba(0,0,0,0.35)" }}>
          {s.img && <Img src={src(s.img)} style={{ width: "100%", height: "140%", objectFit: "cover", objectPosition: "50% 0%" }} />}
        </div>
        <div style={{ position: "absolute", left: px, top: cy + D / 2 + 4, transform: `translateX(${dir === 1 ? "-20%" : "-80%"})`, fontFamily: "NeoHv", fontSize: P.nameSize, color: "#111", WebkitTextStroke: `${P.nameSize * 0.16}px #fff`, paintOrder: "stroke fill", whiteSpace: "nowrap" }}>{hz(s.name)}</div>
      </React.Fragment>
    );
  };
  const n = Math.round(P.snowCount);
  return (
    <AbsoluteFill>
      {snow && Array.from({ length: n }).map((_, i) => {
        const sz = 5 + Math.round(random(`sn${i}`) * 3) * 2;
        const yy = ((random(`sy${i}`) * H + (f - at) * P.snowSpeed * (0.6 + random(`sv${i}`) * 0.8)) % (H + 20)) - 10;
        const xx = random(`sx${i}`) * W + Math.sin((f + i * 13) / 18) * 6;
        return <div key={i} style={{ position: "absolute", left: Math.round(xx / 4) * 4, top: Math.round(yy / 4) * 4, width: sz, height: sz, background: "#fff", opacity: 0.85 }} />;
      })}
      {side(left, 1, P.leftRing)}
      {side(right, -1, P.rightRing)}
      {f >= at + P.vsDelay && (
        <div style={{ position: "absolute", left: W / 2 - 90, top: 120, width: 180, height: 140, clipPath: octagon(180, 140, 30), background: P.badge, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "NeoHv", fontSize: 96, color: "#fff", letterSpacing: -4, paddingTop: 10, boxSizing: "border-box" }}>VS</div>
      )}
    </AbsoluteFill>
  );
};

// ══ 7. 확률 수치 pill 라벨 ════════════════════════════════════════════════
// ref4-apple 1:41:47 — 네이비 pill(1080p 재실측 ≈680×92, #2B3F7A, 라벨 ≈50px) + 아래로 겹치는 빨강 %(≈78px, 흰 외곽), 팝 0.4→1.08→1.0, 퇴장=가로블러+페이드 8f
export const ProbabilityPillParams = z.object({
  popLen: num(5, 1, 20, 1, "팝 길이", "timing", "f"),
  popFrom: num(0.4, 0, 1, 0.05, "팝 시작 크기(배)", "motion"),
  popOver: num(0.08, 0, 0.4, 0.01, "팝 오버슈트", "motion"),
  popBlur: num(10, 0, 40, 1, "등장 가로블러", "look", "px"),
  outLen: num(8, 1, 30, 1, "퇴장 길이", "timing", "f"),
  outBlur: num(30, 0, 80, 1, "퇴장 가로블러", "look", "px"),
  pillW: num(680, 120, 1200, 5, "pill 너비", "size", "px"),
  pillH: num(92, 24, 200, 1, "pill 높이", "size", "px"),
  labelSize: num(50, 12, 100, 1, "라벨 글자 크기", "size", "px"),
  valueSize: num(78, 16, 200, 1, "% 글자 크기", "size", "px"),
  pill: col("#2B3F7A", "pill 색"),
  value: col("#E0302A", "% 색"),
});
export type ProbabilityPillP = z.infer<typeof ProbabilityPillParams>;
export const ProbabilityPill: React.FC<{ label: string; value: string; x: number; y: number; at: number; out?: number; p?: Partial<ProbabilityPillP> }> = ({ label, value, x, y, at, out, p }) => {
  const P = def(ProbabilityPillParams, p);
  const f = useCurrentFrame();
  if (f < at || (out !== undefined && f >= out + P.outLen)) return null;
  const s = popK(f, at, P.popLen, P.popFrom, P.popOver);
  const inB = kf(f, at, [0, P.popLen * 0.6], [P.popBlur, 0]);
  const o = out !== undefined ? kf(f, out, [0, P.outLen], [0, 1]) : 0;
  return (
    <HBlurBox amt={inB + P.outBlur * o} style={{ position: "absolute", left: x, top: y, transform: `translate(-50%,-50%) scale(${s})`, opacity: 1 - o }}>
      <div style={{ width: P.pillW, height: P.pillH, borderRadius: P.pillH / 2, background: P.pill, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "NeoHv", fontSize: P.labelSize, color: "#fff", whiteSpace: "nowrap", boxShadow: "0 4px 8px rgba(0,0,0,0.3)" }}>{hz(label)}</div>
      <div style={{ textAlign: "center", marginTop: -P.valueSize * 0.28, fontFamily: "NeoHv", fontSize: P.valueSize, color: P.value, WebkitTextStroke: `${P.valueSize * 0.14}px #fff`, paintOrder: "stroke fill", lineHeight: 1 }}>{value}</div>
    </HBlurBox>
  );
};

// ══ 8. 대형 X 표 스트라이크 ═══════════════════════════════════════════════
// ref4-apple 1:59:38 — 대상 팝 0.2→1.15→1.0(6f, 블러) → ~15f 유지 → X(두 막대 동시) 반투명 회색 α0.35·1.3배에서 4f 슬램 → 다음 프레임 불투명 확정
//                      확정 직후 더 큰 반투명 고스트 X 가 잠시 남았다 사라짐(프레임 대조)
export const BigXStrikeParams = z.object({
  popLen: num(6, 1, 20, 1, "대상 팝 길이", "timing", "f"),
  popFrom: num(0.2, 0, 1, 0.05, "대상 시작 크기(배)", "motion"),
  popOver: num(0.15, 0, 0.5, 0.01, "대상 오버슈트", "motion"),
  popBlur: num(10, 0, 40, 1, "대상 팝 블러", "look", "px"),
  hold: num(15, 0, 90, 1, "X 까지 유지", "timing", "f"),
  slamLen: num(4, 1, 20, 1, "X 슬램 길이", "timing", "f"),
  slamFrom: num(1.3, 1, 3, 0.05, "X 시작 크기(배)", "motion"),
  ghostOp: num(0.35, 0, 1, 0.05, "슬램 중 불투명도", "look"),
  echoLen: num(10, 0, 40, 1, "고스트 잔상 길이", "timing", "f"),
  echoScale: num(1.3, 1, 2.5, 0.05, "고스트 잔상 크기(배)", "motion"),
  armLen: num(420, 100, 1000, 5, "X 막대 길이", "size", "px"),
  armThick: num(80, 10, 200, 1, "X 막대 두께", "size", "px"),
  color: col("#111111", "X 확정 색"),
  ghost: col("#8a8a8a", "X 슬램 중 색"),
});
export type BigXStrikeP = z.infer<typeof BigXStrikeParams>;
export const BigXStrike: React.FC<{ x: number; y: number; at: number; target?: RN; xAt?: number; out?: number; p?: Partial<BigXStrikeP> }> = ({ x, y, at, target, xAt, out, p }) => {
  const P = def(BigXStrikeParams, p);
  const f = useCurrentFrame();
  if (f < at || (out !== undefined && f >= out)) return null;
  const tS = target ? popK(f, at, P.popLen, P.popFrom, P.popOver) : 1;
  const tB = kf(f, at, [0, P.popLen], [P.popBlur, 0]);
  const X0 = xAt ?? (target ? at + P.popLen + P.hold : at), g = f - X0;
  const X = (sc: number, c: string, op: number, key: string) => (
    <div key={key} style={{ position: "absolute", left: 0, top: 0, transform: `scale(${sc})`, opacity: op }}>
      {[45, -45].map((r) => <div key={r} style={{ position: "absolute", left: -P.armLen / 2, top: -P.armThick / 2, width: P.armLen, height: P.armThick, background: c, transform: `rotate(${r}deg)` }} />)}
    </div>
  );
  return (
    <div style={{ position: "absolute", left: x, top: y }}>
      {target && <div style={{ position: "absolute", left: 0, top: 0, transform: `translate(-50%,-50%) scale(${tS})`, filter: tB > 0.2 ? `blur(${tB}px)` : undefined }}>{target}</div>}
      {g >= 0 && g < P.slamLen && X(lerp(f, X0, X0 + P.slamLen, P.slamFrom, 1, Easing.in(Easing.quad)), P.ghost, P.ghostOp, "slam")}
      {g >= P.slamLen && P.echoLen > 0 && g < P.slamLen + P.echoLen && X(lerp(f, X0 + P.slamLen, X0 + P.slamLen + P.echoLen, 1.05, P.echoScale), P.ghost, lerp(f, X0 + P.slamLen, X0 + P.slamLen + P.echoLen, P.ghostOp, 0), "echo")}
      {g >= P.slamLen && X(1, P.color, 1, "x")}
    </div>
  );
};

// ══ 9. 탁상달력 연도 태그(연기 등장) ══════════════════════════════════════════
// ref4-cocacola 7:58 — 좌상단(1080p 재실측 x≈80,y≈230, ~240px, 연도 ≈62px) 흰 만화 연기 퍼프 12f 가 커졌다 흩어지는 사이 달력(빨간 머리+링, 크림 본문, 빨간 연도)이 나타나 고정
export const CalendarTagSmokeParams = z.object({
  puffLen: num(12, 2, 40, 1, "연기 퍼프 전체 길이", "timing", "f"),
  peakAt: num(4, 1, 20, 1, "연기 최대 시점(=태그 교체)", "timing", "f"),
  puffScale: num(1.5, 0.5, 4, 0.05, "연기 크기(태그 대비)", "size"),
  puffs: num(9, 3, 24, 1, "연기 덩어리 수", "size"),
  size: num(240, 50, 500, 1, "달력 크기", "size", "px"),
  yearSize: num(62, 10, 160, 1, "연도 글자 크기", "size", "px"),
  outLen: num(10, 1, 40, 1, "퇴장 블러 길이", "timing", "f"),
  head: col("#d2172b", "달력 머리 색"),
  body: col("#fff5e6", "달력 본문 색"),
  smoke: col("#ffffff", "연기 색"),
});
export type CalendarTagSmokeP = z.infer<typeof CalendarTagSmokeParams>;
/** 흰 만화 연기 퍼프(원 합집합 + 연회색 외곽): g 0→peak 커지고 → life 까지 흩어지며 사라짐 */
export const SmokePuff: React.FC<{ cx: number; cy: number; r: number; g: number; peak: number; life: number; n?: number; color?: string; seed?: string }> = ({ cx, cy, r, g, peak, life, n = 9, color = "#fff", seed = "sp" }) => {
  if (g < 0 || g > life) return null;
  const grow = g < peak ? Easing.out(Easing.quad)(g / peak) : 1;
  const fade = g < peak ? 0 : (g - peak) / pos(life - peak);
  const ps = Array.from({ length: n }).map((_, i) => {
    const a = (i / n) * TAU + random(`${seed}a${i}`) * 0.6, d = i === 0 ? 0 : 0.45 + 0.35 * random(`${seed}d${i}`);
    const k = Math.max(0, 1 - fade * (0.8 + 0.6 * random(`${seed}k${i}`)));
    return { x: cx + Math.cos(a) * r * d * (1 + fade * 0.6), y: cy + Math.sin(a) * r * d * (1 + fade * 0.6), rr: r * (0.42 + 0.2 * random(`${seed}r${i}`)) * grow * k };
  }).filter((q) => q.rr > 0.5);
  return (
    <svg width={W} height={H} style={{ position: "absolute", left: 0, top: 0, overflow: "visible", pointerEvents: "none" }}>
      {ps.map((q, i) => <circle key={"o" + i} cx={q.x} cy={q.y} r={q.rr + 3} fill="#cfcac4" />)}
      {ps.map((q, i) => <circle key={"i" + i} cx={q.x} cy={q.y} r={q.rr} fill={color} />)}
    </svg>
  );
};
/** 세모지 그림체 탁상달력(desk_calendar) + 연도 글자만 코드. head 는 글자색, body 는 호환용(에셋 고정) */
export const DeskCalendar: React.FC<{ year: string; size: number; yearSize: number; head: string; body: string }> = ({ year, size, yearSize, head }) => (
  <div style={{ position: "relative", width: size, height: propH("desk_calendar", size), filter: "drop-shadow(0 4px 8px rgba(0,0,0,0.25))" }}>
    <Img src={prop("desk_calendar")} style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }} />
    <div style={{ position: "absolute", left: "9%", right: "2%", top: "22%", bottom: "14%", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "NeoHv", fontSize: Math.min(yearSize, (size * 0.8) / Math.max(1, year.length * 0.66)), color: head, letterSpacing: -1, whiteSpace: "nowrap" }}>{year}</div>
  </div>
);
export const CalendarTagSmoke: React.FC<{ year: string; at: number; x?: number; y?: number; out?: number; seed?: string; p?: Partial<CalendarTagSmokeP> }> = ({ year, at, x = 80, y = 230, out, seed = "cts", p }) => {
  const P = def(CalendarTagSmokeParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const g = f - at, S = P.size;
  const o = out !== undefined ? kf(f, out, [0, P.outLen], [0, 1]) : 0;
  if (o >= 1) return null;
  return (
    <>
      {g >= P.peakAt && (
        <div style={{ position: "absolute", left: x, top: y, filter: o > 0 ? `blur(${o * 14}px)` : undefined, opacity: 1 - o }}>
          <DeskCalendar year={year} size={S} yearSize={P.yearSize} head={P.head} body={P.body} />
        </div>
      )}
      <SmokePuff cx={x + S / 2} cy={y + S * 0.42} r={S * 0.5 * P.puffScale} g={g} peak={P.peakAt} life={P.puffLen} n={Math.round(P.puffs)} color={P.smoke} seed={seed} />
    </>
  );
};

// ══ 10. 매달린 아이콘 드롭(끈+리본) ═══════════════════════════════════════════
// ref4-cocacola 17:22 — 흰 라인 아이콘(1080p 재실측 ~250px)이 흰 끈+리본 매듭에 매달려 위에서 ~10f 낙하, 오버슈트(~30px) → 감쇠 바운스 2회(~15f) 정지,
//                       아래 라벨은 가로선이 먼저 벌어지고 텍스트가 나옴(4~5f)
export const HangingIconDropParams = z.object({
  dropLen: num(10, 2, 40, 1, "낙하 길이", "timing", "f"),
  over: num(30, 0, 120, 1, "오버슈트 거리", "motion", "px"),
  settleLen: num(15, 2, 60, 1, "감쇠 바운스 길이", "timing", "f"),
  bounces: num(2, 0, 6, 0.5, "바운스 횟수", "motion"),
  swing: num(4, 0, 30, 0.5, "진자 흔들림 각도", "motion", "°"),
  labelDelay: num(24, 0, 90, 1, "라벨 지연(낙하 시작 기준)", "timing", "f"),
  labelLen: num(5, 1, 20, 1, "라벨 펼침 길이", "timing", "f"),
  size: num(250, 40, 500, 2, "아이콘 크기", "size", "px"),
  stroke: num(5, 1, 16, 0.5, "아이콘 선 두께", "size", "px"),
  labelW: num(190, 40, 600, 2, "라벨 너비", "size", "px"),
  labelH: num(66, 16, 200, 1, "라벨 높이", "size", "px"),
  labelSize: num(44, 10, 120, 1, "라벨 글자 크기", "size", "px"),
  line: col("#ffffff", "끈·아이콘 색"),
  labelText: col("#d2172b", "라벨 글자 색"),
});
export type HangingIconDropP = z.infer<typeof HangingIconDropParams>;
/** 흰 라인 아이콘(viewBox 100) */
export const LineIcon: React.FC<{ kind: "calendar" | "stopwatch" | "clock" | "bottle"; color: string; sw: number }> = ({ kind, color, sw }) => {
  const s = { fill: "none", stroke: color, strokeWidth: sw, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  if (kind === "calendar") return (
    <svg viewBox="0 0 100 100" width="100%" height="100%" style={{ overflow: "visible" }}>
      <rect x={10} y={18} width={80} height={72} rx={8} {...s} /><line x1={10} y1={38} x2={90} y2={38} {...s} />
      <line x1={30} y1={8} x2={30} y2={26} {...s} /><line x1={70} y1={8} x2={70} y2={26} {...s} />
      {[0, 1, 2, 3].map((c) => [0, 1, 2].map((r) => <rect key={`${c}${r}`} x={20 + c * 16} y={46 + r * 13} width={9} height={7} fill={color} />))}
    </svg>
  );
  if (kind === "stopwatch" || kind === "clock") return (
    <svg viewBox="0 0 100 100" width="100%" height="100%" style={{ overflow: "visible" }}>
      <circle cx={50} cy={56} r={38} {...s} />{kind === "stopwatch" && <><rect x={42} y={4} width={16} height={10} rx={2} fill={color} /><line x1={50} y1={14} x2={50} y2={18} {...s} /><line x1={80} y1={22} x2={86} y2={16} {...s} /></>}
      {Array.from({ length: 12 }).map((_, i) => { const a = (i / 12) * TAU; return <line key={i} x1={50 + Math.cos(a) * 30} y1={56 + Math.sin(a) * 30} x2={50 + Math.cos(a) * 34} y2={56 + Math.sin(a) * 34} stroke={color} strokeWidth={sw * 0.5} />; })}
      <line x1={50} y1={56} x2={50} y2={32} {...s} /><line x1={50} y1={56} x2={64} y2={62} {...s} />
    </svg>
  );
  return (
    <svg viewBox="0 0 100 100" width="100%" height="100%" style={{ overflow: "visible" }}>
      <path d="M42,6 H58 V24 C58,34 70,38 70,52 V90 C70,94 66,96 62,96 H38 C34,96 30,94 30,90 V52 C30,38 42,34 42,24 Z" {...s} />
    </svg>
  );
};
export const HangingIconDrop: React.FC<{ x: number; y: number; at: number; icon?: "calendar" | "stopwatch" | "clock" | "bottle"; node?: RN; label?: string; ropeTop?: number; p?: Partial<HangingIconDropP> }> = ({ x, y, at, icon = "calendar", node, label, ropeTop = 0, p }) => {
  const P = def(HangingIconDropParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const S = P.size, g = f - at, y0 = -S * 1.4;
  let cy: number, ang = 0;
  if (g < P.dropLen) cy = y0 + (y + P.over - y0) * Easing.in(Easing.quad)(g / P.dropLen);
  else {
    const u = g - P.dropLen, per = P.settleLen / pos(P.bounces, 0.25);
    const env = Math.exp((-u / pos(P.settleLen)) * 3);
    cy = y + P.over * env * Math.cos((u / per) * TAU);
    ang = P.swing * env * Math.sin((u / per) * TAU * 0.5 + 0.4);
  }
  const top = cy - S / 2, knot = top - S * 0.06;
  const la = at + P.labelDelay, lu = label ? kf(f, la, [0, P.labelLen * 0.45, P.labelLen], [0, 1, 1]) : 0, lh = label ? kf(f, la + P.labelLen * 0.45, [0, P.labelLen * 0.55], [0, 1]) : 0;
  return (
    <>
      <div style={{ position: "absolute", left: x - 1, top: ropeTop, width: 2, height: Math.max(0, knot - ropeTop), background: P.line }} />
      <div style={{ position: "absolute", left: x, top: knot, transform: `rotate(${ang}deg)`, transformOrigin: "50% 0%" }}>
        <svg width={S * 0.5} height={S * 0.3} viewBox="-25 -12 50 30" style={{ position: "absolute", left: -S * 0.25, top: -S * 0.12, overflow: "visible" }}>
          <path d="M0,0 C-10,-12 -22,-8 -18,0 C-16,6 -6,4 0,0 C6,4 16,6 18,0 C22,-8 10,-12 0,0 Z M0,0 L-8,14 M0,0 L8,14" fill="none" stroke={P.line} strokeWidth={2.5} strokeLinecap="round" />
        </svg>
        <div style={{ position: "absolute", left: -S / 2, top: S * 0.06, width: S, height: S }}>{node ?? <LineIcon kind={icon} color={P.line} sw={P.stroke} />}</div>
      </div>
      {label && lu > 0 && (
        <div style={{ position: "absolute", left: x - (P.labelW / 2) * lu, top: y + S / 2 + S * 0.25, width: P.labelW * lu, height: Math.max(3, P.labelH * lh), marginTop: (P.labelH * (1 - lh)) / 2, background: "#fff", overflow: "hidden", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "Yeonsung", fontSize: P.labelSize, color: P.labelText, whiteSpace: "nowrap" }}>
          <span style={{ opacity: lh, paddingTop: 3 }}>{hz(label)}</span>
        </div>
      )}
    </>
  );
};

// ══ 11. 연기 가장자리 말풍선(어두운 장면) ═════════════════════════════════════
// ref4-hyundai 54:47 — 가장자리 ~40px 페더의 흰 구름, 대사 줄이 위→아래 블러 해제로 차례로(~9f 간격),
//                      퇴장: 블러↑+α 1→0 ≈10f, 동시에 다음 요소 오른쪽 슬라이드인
export const FeatheredSmokeBubbleParams = z.object({
  inLen: num(8, 1, 30, 1, "구름 등장 길이", "timing", "f"),
  lineStagger: num(9, 0, 40, 1, "줄 간격", "timing", "f"),
  lineLen: num(6, 1, 30, 1, "줄 리빌 길이", "timing", "f"),
  lineBlur: num(8, 0, 30, 0.5, "줄 리빌 블러", "look", "px"),
  feather: num(80, 0, 200, 1, "가장자리 페더", "look", "px"),
  outLen: num(10, 1, 40, 1, "퇴장 길이", "timing", "f"),
  outBlur: num(24, 0, 80, 1, "퇴장 블러", "look", "px"),
  nextLen: num(12, 1, 40, 1, "다음 요소 슬라이드인 길이", "timing", "f"),
  nextDist: num(900, 100, 2000, 10, "다음 요소 이동 거리", "motion", "px"),
  fontSize: num(56, 16, 120, 1, "글자 크기", "size", "px"),
  cloud: col("#ffffff", "구름 색"),
  ink: col("#1a1a1a", "글자 색"),
});
export type FeatheredSmokeBubbleP = z.infer<typeof FeatheredSmokeBubbleParams>;
export const FeatheredSmokeBubble: React.FC<{ lines: string[]; x: number; y: number; w?: number; h?: number; at: number; out?: number; next?: RN; font?: string; p?: Partial<FeatheredSmokeBubbleP> }> = ({ lines, x, y, w = 900, h = 520, at, out, next, font = "Yeonsung, 'Songti SC', serif", p }) => {
  const P = def(FeatheredSmokeBubbleParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const inU = kf(f, at, [0, P.inLen], [0, 1], Easing.out(Easing.quad));
  const o = out !== undefined ? kf(f, out, [0, P.outLen], [0, 1], Easing.in(Easing.quad)) : 0;
  const nx = out !== undefined && next ? kf(f, out, [0, P.nextLen], [1, 0], QUART_OUT) : 1;
  const F = P.feather;
  return (
    <>
      {o < 1 && (
        <div style={{ position: "absolute", left: x - w / 2, top: y - h / 2, width: w, height: h, opacity: inU * (1 - o), transform: `scale(${(0.9 + 0.1 * inU) * (1 + 0.12 * o)})`, filter: o > 0 ? `blur(${o * P.outBlur}px)` : undefined }}>
          <div style={{ position: "absolute", left: F / 2, top: F / 2, right: F / 2, bottom: F / 2, borderRadius: "50%", background: P.cloud, filter: `blur(${F / 2}px)` }} />
          <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
            {lines.map((ln, i) => {
              const la = at + P.inLen * 0.5 + i * P.lineStagger;
              const u = kf(f, la, [0, P.lineLen], [0, 1]);
              return <div key={i} style={{ opacity: u, filter: `blur(${P.lineBlur * (1 - u)}px)`, fontFamily: font, fontSize: P.fontSize, color: P.ink, lineHeight: 1.25, whiteSpace: "nowrap" }}>{hz(ln)}</div>;
            })}
          </div>
        </div>
      )}
      {out !== undefined && next && f >= out && <div style={{ position: "absolute", inset: 0, transform: `translateX(${nx * P.nextDist}px)` }}>{next}</div>}
    </>
  );
};

// ══ 12. 체크리스트 순차 체크 + APPROVED 도장 ═════════════════════════════════
// ref4-hyundai 1:06:14 — 클립보드(우측) 항목 4줄 간격 ~100px(1080p 실측: 보드 ≈460×700), 체크 2f 드로우(거의 컷), 내레이션 싱크, 완료 시 초록 테두리 APPROVED 팝
export const ChecklistTickParams = z.object({
  tickLen: num(2, 1, 20, 1, "체크 드로우 길이", "timing", "f"),
  stampLen: num(5, 1, 20, 1, "도장 팝 길이", "timing", "f"),
  stampFrom: num(1.8, 1, 4, 0.05, "도장 시작 크기(배)", "motion"),
  stampRot: num(-10, -45, 45, 1, "도장 기울기", "motion", "°"),
  w: num(520, 200, 900, 5, "보드 너비", "size", "px"),
  h: num(740, 300, 1000, 5, "보드 높이", "size", "px"),
  gap: num(100, 40, 200, 1, "항목 간격", "size", "px"),
  fontSize: num(56, 16, 100, 1, "항목 글자 크기", "size", "px"),
  check: col("#3DBE5A", "체크 색"),
  stamp: col("#2FA84F", "도장 색"),
});
export type ChecklistTickP = z.infer<typeof ChecklistTickParams>;
export const ChecklistTick: React.FC<{ items: { text: string; at: number }[]; x: number; y: number; at: number; stampAt?: number; stampText?: string; p?: Partial<ChecklistTickP> }> = ({ items, x, y, at, stampAt, stampText = "APPROVED", p }) => {
  const P = def(ChecklistTickParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const { w, h } = P, bx = w * 0.14, box = P.fontSize * 0.8;
  const ss = stampAt !== undefined && f >= stampAt ? kf(f, stampAt, [0, P.stampLen], [P.stampFrom, 1], Easing.in(Easing.quad)) : 0;
  return (
    <div style={{ position: "absolute", left: x, top: y, width: w, height: h }}>
      <div style={{ position: "absolute", inset: 0, background: "#232326", borderRadius: 16, boxShadow: "0 10px 20px rgba(0,0,0,0.3)" }} />
      <div style={{ position: "absolute", left: w * 0.05, right: w * 0.05, top: w * 0.07, bottom: w * 0.05, background: "#fbfaf6", borderRadius: 4 }} />
      <div style={{ position: "absolute", left: w * 0.33, top: -w * 0.04, width: w * 0.34, height: w * 0.11, background: "#b5b5ba", borderRadius: 8 }} />
      {items.map((it, i) => {
        const cy = w * 0.2 + i * P.gap + box / 2;
        const t = kf(f, it.at, [0, P.tickLen], [0, 1]);
        return (
          <React.Fragment key={i}>
            <div style={{ position: "absolute", left: bx, top: cy - box / 2, width: box, height: box, border: "3px solid #9a9a9a", boxSizing: "border-box", borderRadius: 3 }} />
            {t > 0 && (
              <svg width={box * 1.5} height={box * 1.3} viewBox="0 0 30 26" style={{ position: "absolute", left: bx - box * 0.05, top: cy - box * 0.85, overflow: "visible" }}>
                <path d="M3,14 L11,22 L28,3" pathLength={1} fill="none" stroke={P.check} strokeWidth={5} strokeLinecap="round" strokeLinejoin="round" strokeDasharray="1 1" strokeDashoffset={1 - t} />
              </svg>
            )}
            <div style={{ position: "absolute", left: bx + box * 1.45, top: cy - P.fontSize * 0.55, fontFamily: "NeoHv", fontSize: P.fontSize, color: "#222", whiteSpace: "nowrap" }}>{hz(it.text)}</div>
          </React.Fragment>
        );
      })}
      {ss > 0 && (
        <div style={{ position: "absolute", left: w / 2, top: h * 0.82, transform: `translate(-50%,-50%) rotate(${P.stampRot}deg) scale(${ss})`, border: `${P.fontSize * 0.14}px solid ${P.stamp}`, borderRadius: 10, padding: "8px 18px 2px", fontFamily: "NeoHv", fontSize: P.fontSize * 1.05, color: P.stamp, letterSpacing: 2, whiteSpace: "nowrap", mixBlendMode: "multiply" }}>{stampText}</div>
      )}
    </div>
  );
};

// ══ 13. 게임 퀘스트 창 드롭 ═══════════════════════════════════════════════
// ref4-hyundai 1:20:06 — 2단 패널(좌 퀘스트 목록·체크 / 우 NPC 카드) ~1300×840, 화면 위(-900)에서 ~18f ease-out 드롭, 오버슈트 없음
export const QuestWindowDropParams = z.object({
  dropLen: num(18, 2, 60, 1, "드롭 길이", "timing", "f"),
  dropFrom: num(-900, -1600, 0, 10, "시작 위치 y(오프셋)", "motion", "px"),
  w: num(1300, 600, 1800, 10, "창 너비", "size", "px"),
  h: num(840, 400, 1000, 10, "창 높이", "size", "px"),
  fontSize: num(34, 14, 70, 1, "본문 글자 크기", "size", "px"),
  frame: col("#1F5D45", "창 테두리 색"),
  tabDone: col("#8BC34A", "완료 탭 색"),
  region: col("#3E6FA8", "지역 헤더 색"),
  card: col("#5AA7DB", "NPC 카드 색"),
});
export type QuestWindowDropP = z.infer<typeof QuestWindowDropParams>;
export const QuestWindowDrop: React.FC<{ at: number; title?: string; tabs?: string[]; active?: number; region?: string; quests: { text: string; done?: boolean }[]; npc: { title: string; img?: string; code?: string; desc: string }; x?: number; y?: number; p?: Partial<QuestWindowDropP> }> = ({ at, title = "퀘스트", tabs = ["시작가능", "진행중", "완료"], active = 2, region = "지역", quests, npc, x, y, p }) => {
  const P = def(QuestWindowDropParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const { w, h } = P, X = x ?? (W - w) / 2, Y = y ?? (H - h) / 2 - 20;
  const dy = kf(f, at, [0, P.dropLen], [P.dropFrom - Y, 0], Easing.out(Easing.cubic));
  const fs = P.fontSize, hh = h * 0.09;
  return (
    <div style={{ position: "absolute", left: X, top: Y, width: w, height: h, transform: `translateY(${dy}px)`, filter: "drop-shadow(0 14px 18px rgba(0,0,0,0.35))" }}>
      <div style={{ position: "absolute", inset: 0, background: P.frame, borderRadius: 18 }} />
      <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: hh, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "NeoHv", fontSize: fs * 1.25, color: "#fff" }}>{title}</div>
      <div style={{ position: "absolute", left: 18, right: 18, top: hh, bottom: 18, background: "#EDEAE0", borderRadius: 10 }}>
        <div style={{ position: "absolute", left: 16, top: 14, display: "flex", gap: 10 }}>
          {tabs.map((t, i) => <div key={i} style={{ padding: `${fs * 0.2}px ${fs * 0.55}px ${fs * 0.1}px`, borderRadius: 8, background: i === active ? P.tabDone : "#8f8f8f", color: "#fff", fontFamily: "NeoHv", fontSize: fs * 0.8 }}>{t}</div>)}
        </div>
        <div style={{ position: "absolute", left: 16, top: fs * 2.1, width: "50%", bottom: 16, background: "#fff", borderRadius: 8, overflow: "hidden" }}>
          <div style={{ background: P.region, color: "#fff", fontFamily: "NeoHv", fontSize: fs * 0.85, padding: `${fs * 0.3}px ${fs * 0.5}px ${fs * 0.2}px` }}>■ {hz(region)}</div>
          {quests.map((q, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, padding: `${fs * 0.35}px ${fs * 0.5}px`, background: i === 0 ? "#DDE8F4" : "transparent", fontFamily: "NeoEb", fontSize: fs * 0.85, color: "#333" }}>
              <span style={{ width: fs * 0.9, color: "#6DB33F", fontFamily: "NeoHv" }}>{q.done ? "✔" : ""}</span>{hz(q.text)}
            </div>
          ))}
        </div>
        <div style={{ position: "absolute", left: "calc(50% + 32px)", right: 16, top: fs * 2.1, bottom: 16, background: "#fff", borderRadius: 8, overflow: "hidden" }}>
          <div style={{ position: "relative", height: "42%", background: P.card }}>
            <div style={{ position: "absolute", left: fs * 0.6, top: fs * 0.6, width: "55%", fontFamily: "NeoHv", fontSize: fs * 1.05, color: "#fff", lineHeight: 1.15 }}>{hz(npc.title)}</div>
            {npc.code && <div style={{ position: "absolute", left: fs * 0.6, bottom: fs * 0.5, fontFamily: "NeoEb", fontSize: fs * 0.55, color: "#fff", opacity: 0.85 }}>{npc.code}</div>}
            {npc.img && <Img src={src(npc.img)} style={{ position: "absolute", right: 10, bottom: 0, height: "95%", objectFit: "contain" }} />}
          </div>
          <div style={{ padding: `${fs * 0.7}px ${fs * 0.7}px`, fontFamily: "NeoEb", fontSize: fs * 0.9, color: "#333", lineHeight: 1.4, whiteSpace: "pre-line" }}>{hz(npc.desc)}</div>
        </div>
      </div>
    </div>
  );
};

// ══ 14. 대각 테이프 드로우 + 태그 ═══════════════════════════════════════════
// ref4-hyundai 1:37:42 — 흰 띠(#F9F7F3, 두께 ~155, ~19°) 가 둥근 붓끝 선단으로 ~11f 에 화면 횡단(ease-out), 이후 미세 드리프트,
//                        금색 태그(#D09B1F) 띠와 같은 각도로 0.3→1.1→1.0 ~4f, ~10f 스태거, 마지막에 이미지가 띠를 따라 미끄러져 들어옴
export const DiagonalTapeTagsParams = z.object({
  drawLen: num(11, 2, 40, 1, "띠 횡단 길이", "timing", "f"),
  angle: num(19, -60, 60, 0.5, "띠 각도", "motion", "°"),
  thick: num(155, 30, 400, 1, "띠 두께", "size", "px"),
  tipBlur: num(10, 0, 40, 0.5, "선단 블러", "look", "px"),
  drift: num(0.25, 0, 3, 0.05, "드리프트 속도(띠 방향)", "motion", "px/f"),
  tagLen: num(4, 1, 20, 1, "태그 팝 길이", "timing", "f"),
  tagFrom: num(0.3, 0, 1, 0.05, "태그 시작 크기(배)", "motion"),
  tagOver: num(0.1, 0, 0.4, 0.01, "태그 오버슈트", "motion"),
  tagSize: num(76, 16, 160, 1, "태그 글자 크기", "size", "px"),
  riderLen: num(14, 2, 60, 1, "이미지 슬라이드 길이", "timing", "f"),
  band: col("#F9F7F3", "띠 색"),
  tag: col("#D09B1F", "태그 색"),
});
export type DiagonalTapeTagsP = z.infer<typeof DiagonalTapeTagsParams>;
export const DiagonalTapeTags: React.FC<{ at: number; start?: Pt; length?: number; tags: { text: string; at: number; d: number }[]; rider?: { img: string; at: number; d: number; w: number; h: number; off?: number }; p?: Partial<DiagonalTapeTagsP> }> = ({ at, start = [-60, 200], length = 2400, tags, rider, p }) => {
  const P = def(DiagonalTapeTagsParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const t = kf(f, at, [0, P.drawLen], [0, 1], Easing.out(Easing.cubic));
  const s = length * t, T = P.thick;
  const dr = Math.max(0, f - at - P.drawLen) * P.drift;
  return (
    <div style={{ position: "absolute", left: start[0], top: start[1], width: 0, height: 0, transform: `rotate(${P.angle}deg) translateX(${dr}px)`, transformOrigin: "0 0" }}>
      <div style={{ position: "absolute", left: -T, top: -T / 2, width: s + T, height: T, background: P.band, borderRadius: t < 1 ? `0 ${T / 2}px ${T / 2}px 0` : 0, boxShadow: "0 4px 10px rgba(0,0,0,0.15)", filter: t < 1 && P.tipBlur > 0 ? `blur(${P.tipBlur * (1 - t) * 0.6}px)` : undefined }} />
      {tags.map((tg, i) => {
        if (f < tg.at) return null;
        const k = popK(f, tg.at, P.tagLen, P.tagFrom, P.tagOver);
        return <div key={i} style={{ position: "absolute", left: tg.d, top: 0, transform: `translate(-50%,-50%) scale(${k})`, background: P.tag, color: "#fff", fontFamily: "NeoHv", fontSize: P.tagSize, padding: `${P.tagSize * 0.22}px ${P.tagSize * 0.35}px ${P.tagSize * 0.1}px`, borderRadius: P.tagSize * 0.14, whiteSpace: "nowrap", lineHeight: 1.1 }}>{hz(tg.text)}</div>;
      })}
      {rider && f >= rider.at && (() => {
        const u = kf(f, rider.at, [0, P.riderLen], [0, 1], QUART_OUT);
        const d = -rider.w + (rider.d + rider.w) * u;
        return <Img src={src(rider.img)} style={{ position: "absolute", left: d - rider.w / 2, top: (rider.off ?? -T / 2) - rider.h, width: rider.w, height: rider.h, objectFit: "contain", filter: u < 1 ? `blur(${(1 - u) * 6}px)` : undefined }} />;
      })()}
    </div>
  );
};

// ══ 15. 로고 주위 사업 아이콘 입장 ═════════════════════════════════════════
// ref4-hyundai 1:37:32 — 크림 배경 중앙 로고 고정, 아이콘마다 가장 가까운 화면 가장자리에서 ~10f quart-out 슬라이드, 내레이션 스태거, 최종 위치는 절반쯤 프레임에 걸침
export const LogoEdgeIconsGatherParams = z.object({
  slideLen: num(10, 1, 40, 1, "슬라이드 길이", "timing", "f"),
  logoLen: num(6, 1, 30, 1, "로고 팝 길이", "timing", "f"),
  blur: num(10, 0, 40, 1, "슬라이드 모션블러", "look", "px"),
  margin: num(40, 0, 400, 5, "화면 밖 시작 여유", "motion", "px"),
});
export type LogoEdgeIconsGatherP = z.infer<typeof LogoEdgeIconsGatherParams>;
export const LogoEdgeIconsGather: React.FC<{ logo: RN; logoAt?: number; icons: { node: RN; x: number; y: number; w: number; h: number; at: number; from?: "left" | "right" | "top" | "bottom" }[]; p?: Partial<LogoEdgeIconsGatherP> }> = ({ logo, logoAt, icons, p }) => {
  const P = def(LogoEdgeIconsGatherParams, p);
  const f = useCurrentFrame();
  const ls = logoAt === undefined ? 1 : f < logoAt ? 0 : popK(f, logoAt, P.logoLen, 0.4, 0.08);
  return (
    <>
      {icons.map((ic, i) => {
        if (f < ic.at) return null;
        const dl = ic.x, dr = W - ic.x, dt = ic.y, db = H - ic.y;
        const from = ic.from ?? (["left", "right", "top", "bottom"] as const)[[dl, dr, dt, db].indexOf(Math.min(dl, dr, dt, db))];
        const u = kf(f, ic.at, [0, P.slideLen], [1, 0], QUART_OUT);
        const off = from === "left" ? [-(ic.x + ic.w / 2 + P.margin), 0] : from === "right" ? [W - ic.x + ic.w / 2 + P.margin, 0] : from === "top" ? [0, -(ic.y + ic.h / 2 + P.margin)] : [0, H - ic.y + ic.h / 2 + P.margin];
        const hor = from === "left" || from === "right";
        return (
          <HBlurBox key={i} amt={hor ? P.blur * u : 0} style={{ position: "absolute", left: ic.x - ic.w / 2, top: ic.y - ic.h / 2, width: ic.w, height: ic.h, transform: `translate(${off[0] * u}px,${off[1] * u}px)`, filter: !hor && u > 0.02 ? `blur(${P.blur * u * 0.5}px)` : undefined }}>
            {ic.node}
          </HBlurBox>
        );
      })}
      {ls > 0 && <div style={{ position: "absolute", left: W / 2, top: H / 2, transform: `translate(-50%,-50%) scale(${ls})` }}>{logo}</div>}
    </>
  );
};

// ══ 16. 서명 파문 링 / 리플 링 마커 ═════════════════════════════════════════
// ref4-hyundai 1:42:26 — 빨간 점 팝 ~3f → 동심원 3개 ~4f 간격 확장(지름 40→420, 선폭 6) ~15f ease-out → 호 조각으로 트림되며 소멸 ~10f
// (ripple-ring-marker 병합: ref4-samsung 3:28 — 점 없이 최대 지름 ~240, 선폭 4, #B74E47 → dot=false·maxD 240·width 4)
export const RippleRingsParams = z.object({
  dot: flag(true, "가운데 점 표시"),
  dotLen: num(3, 1, 20, 1, "점 팝 길이", "timing", "f"),
  dotD: num(34, 4, 120, 1, "점 지름", "size", "px"),
  rings: num(3, 1, 8, 1, "링 개수", "size"),
  ringStagger: num(4, 0, 20, 1, "링 간격", "timing", "f"),
  expandLen: num(15, 2, 60, 1, "확장 길이", "timing", "f"),
  trimLen: num(10, 1, 40, 1, "트림 소멸 길이", "timing", "f"),
  trim: flag(true, "호 조각 트림(끄면 알파 페이드)"),
  startD: num(40, 0, 300, 1, "시작 지름", "size", "px"),
  maxD: num(420, 60, 1200, 5, "최대 지름", "size", "px"),
  width: num(6, 1, 20, 0.5, "선 두께", "size", "px"),
  color: col("#D0302A", "링 색"),
});
export type RippleRingsP = z.infer<typeof RippleRingsParams>;
export const RippleRings: React.FC<{ x: number; y: number; at: number; seed?: string; p?: Partial<RippleRingsP> }> = ({ x, y, at, seed = "rr", p }) => {
  const P = def(RippleRingsParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const n = Math.round(P.rings), r0 = at + (P.dot ? P.dotLen : 0);
  const lastEnd = r0 + (n - 1) * P.ringStagger + P.expandLen + P.trimLen;
  if (f > lastEnd + 1) return null;
  const R = P.maxD / 2 + P.width;
  const dotS = P.dot ? kf(f, at, [0, P.dotLen * 0.6, P.dotLen], [0, 1.2, 1]) * kf(f, lastEnd - P.trimLen, [0, P.trimLen], [1, 0]) : 0;
  return (
    <svg width={R * 2} height={R * 2} style={{ position: "absolute", left: x - R, top: y - R, overflow: "visible" }}>
      {dotS > 0 && <circle cx={R} cy={R} r={(P.dotD / 2) * dotS} fill={P.color} />}
      {Array.from({ length: n }).map((_, i) => {
        const a = r0 + i * P.ringStagger;
        if (f < a) return null;
        const d = lerp(f, a, a + P.expandLen, P.startD, P.maxD * (1 - i * 0.12), Easing.out(Easing.cubic));
        const u = kf(f, a + P.expandLen, [0, P.trimLen], [0, 1]);
        if (u >= 1) return null;
        const r = d / 2, C = TAU * r;
        if (!P.trim) return <circle key={i} cx={R} cy={R} r={r} fill="none" stroke={P.color} strokeWidth={P.width} opacity={1 - Math.max(u, kf(f, a, [0, P.expandLen], [0, 0.4]))} />;
        const seg = C / 3, dash = seg * Math.pow(1 - u, 1 + random(`${seed}${i}`));
        return <circle key={i} cx={R} cy={R} r={r} fill="none" stroke={P.color} strokeWidth={P.width} strokeLinecap="round" strokeDasharray={`${Math.max(0.01, dash)} ${seg - dash + 0.01}`} transform={`rotate(${random(`${seed}o${i}`) * 360 + u * 60} ${R} ${R})`} />;
      })}
    </svg>
  );
};

// ══ 17. 제품 스펙 핀 콜아웃 ═══════════════════════════════════════════════
// ref4-hyundai 2:00:22 — 제목 필(상단 중앙) blur-in ~6f, 스펙 라벨(네이비 #2B2A7A 사각, 흰 2줄) blur+scale 0.8→1 ~5f,
//                        흰 선+점(~12px)으로 부위 연결, 내레이션 순 스태거, 강조 라벨은 금색 텍스트
export const ProductSpecPinsParams = z.object({
  titleLen: num(6, 1, 30, 1, "제목 블러인 길이", "timing", "f"),
  labelLen: num(5, 1, 30, 1, "라벨 등장 길이", "timing", "f"),
  labelFrom: num(0.8, 0, 1, 0.05, "라벨 시작 크기(배)", "motion"),
  blur: num(12, 0, 40, 1, "등장 블러", "look", "px"),
  lineLen: num(4, 1, 30, 1, "지시선 드로우 길이", "timing", "f"),
  dotD: num(30, 4, 80, 1, "점 지름", "size", "px"),
  lineW: num(5, 1, 16, 0.5, "지시선 두께", "size", "px"),
  fontSize: num(56, 14, 120, 1, "라벨 글자 크기", "size", "px"),
  titleSize: num(64, 16, 140, 1, "제목 글자 크기", "size", "px"),
  label: col("#2B2A7A", "라벨 색"),
  gold: col("#F2C94C", "강조 글자 색"),
});
export type ProductSpecPinsP = z.infer<typeof ProductSpecPinsParams>;
export const ProductSpecPins: React.FC<{ title?: { text: string; at: number; y?: number }; pins: { pt: Pt; label: Pt; lines: string[]; at: number; gold?: boolean }[]; p?: Partial<ProductSpecPinsP> }> = ({ title, pins, p }) => {
  const P = def(ProductSpecPinsParams, p);
  const f = useCurrentFrame();
  const tu = title && f >= title.at ? kf(f, title.at, [0, P.titleLen], [0, 1]) : 0;
  return (
    <>
      {pins.map((pn, i) => {
        if (f < pn.at) return null;
        const u = kf(f, pn.at, [0, P.labelLen], [0, 1], Easing.out(Easing.quad));
        const lt = kf(f, pn.at, [0, P.lineLen], [0, 1]);
        const [px, py] = pn.pt, [lx, ly] = pn.label;
        const ex = lx + (px - lx) * lt, ey = ly + (py - ly) * lt;
        return (
          <React.Fragment key={i}>
            <svg width={W} height={H} style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}>
              <line x1={lx} y1={ly} x2={ex} y2={ey} stroke="#fff" strokeWidth={P.lineW} />
              {lt >= 1 && <circle cx={px} cy={py} r={P.dotD / 2} fill="#fff" />}
            </svg>
            <div style={{ position: "absolute", left: lx, top: ly, transform: `translate(-50%,-50%) scale(${P.labelFrom + (1 - P.labelFrom) * u})`, opacity: Math.min(1, u * 2), filter: `blur(${P.blur * (1 - u)}px)`, background: P.label, padding: `${P.fontSize * 0.25}px ${P.fontSize * 0.35}px ${P.fontSize * 0.15}px`, fontFamily: "NeoHv", fontSize: P.fontSize, color: pn.gold ? P.gold : "#fff", textAlign: "center", lineHeight: 1.1, whiteSpace: "nowrap", boxShadow: "0 4px 8px rgba(0,0,0,0.3)" }}>
              {pn.lines.map((l, j) => <div key={j}>{hz(l)}</div>)}
            </div>
          </React.Fragment>
        );
      })}
      {title && tu > 0 && (
        <div style={{ position: "absolute", left: W / 2, top: title.y ?? 80, transform: `translate(-50%,-50%) scale(${1.1 - 0.1 * tu})`, opacity: tu, filter: `blur(${P.blur * (1 - tu)}px)`, background: P.label, borderRadius: 999, padding: `${P.titleSize * 0.3}px ${P.titleSize * 0.8}px ${P.titleSize * 0.18}px`, fontFamily: "NeoHv", fontSize: P.titleSize, color: "#fff", whiteSpace: "nowrap" }}>{hz(title.text)}</div>
      )}
    </>
  );
};

// ══ 18. TCG 인물 카드 마키 ════════════════════════════════════════════════
// ref4-samsung 13:08 — 카드 ≈540×750, 테두리 색 갈색/보라/겨자/빨강/파랑 순환, 상단 이름 띠+★★★, 하단 설명 2줄, 간격 ≈90,
//                      왼쪽 선형 스크롤 ≈230px/s(7.7px/f), 첫 카드는 오른쪽 밖에서 진입. 얼굴 모르는 인물은 흰 실루엣+'?'
export const TcgCardMarqueeParams = z.object({
  speed: num(7.7, 0, 40, 0.1, "스크롤 속도", "motion", "px/f"),
  cardW: num(540, 200, 900, 5, "카드 너비", "size", "px"),
  cardH: num(750, 300, 1000, 5, "카드 높이", "size", "px"),
  gap: num(90, 0, 300, 1, "카드 간격", "size", "px"),
  border: num(22, 4, 60, 1, "테두리 두께", "size", "px"),
  nameSize: num(30, 12, 70, 1, "이름 글자 크기", "size", "px"),
  starColor: col("#F26A1B", "별 색"),
});
export type TcgCardMarqueeP = z.infer<typeof TcgCardMarqueeParams>;
const TCG_COLS = ["#7A4A2A", "#5B2A8E", "#B7A73A", "#B8322A", "#2F63B0"];
const shade = (hex: string, k: number) => { const n = parseInt(hex.slice(1), 16); const c = (s: number) => Math.max(0, Math.min(255, Math.round(((n >> s) & 255) * k))); return `rgb(${c(16)},${c(8)},${c(0)})`; };
export const TcgCard: React.FC<{ name: string; img?: string; lines?: string[]; color: string; w: number; h: number; border: number; nameSize: number; stars?: number; starColor: string }> = ({ name, img, lines = [], color, w, h, border, nameSize, stars = 3, starColor }) => (
  <div style={{ position: "relative", width: w, height: h, background: color, borderRadius: 10, boxShadow: "0 10px 20px rgba(0,0,0,0.25)" }}>
    <div style={{ position: "absolute", left: border, right: border, top: border, height: h * 0.1, background: shade(color, 0.72), display: "flex", alignItems: "center", paddingLeft: 16, fontFamily: "NeoHv", fontSize: nameSize, color: "#fff", whiteSpace: "nowrap", overflow: "hidden", textShadow: "0 2px 2px rgba(0,0,0,0.35)" }}>{hz(name)}</div>
    <div style={{ position: "absolute", right: border + 10, top: border + h * 0.1 + 6, fontSize: nameSize * 0.9, color: starColor, letterSpacing: 2, fontFamily: "sans-serif" }}>{"★".repeat(stars)}</div>
    <div style={{ position: "absolute", left: border * 2, right: border * 2, top: border + h * 0.18, height: h * 0.5, background: shade(color, 0.7), border: `6px solid ${shade(color, 0.5)}`, boxSizing: "border-box", overflow: "hidden" }}>
      {img ? <Img src={src(img)} style={{ position: "absolute", left: "10%", width: "80%", bottom: 0, height: "100%", objectFit: "contain", objectPosition: "50% 100%" }} /> : (
        // 세모지 그림체 인물 흉상(c2_boss 정장 기업가) — 사진 없을 때 자리표시
        <SemojiRig cast="c2_boss" x={(w - border * 4) / 2 - 6} y={h * 0.5 - 8} h={h * 0.5 * 1.5} bust seed={name} />
      )}
    </div>
    <div style={{ position: "absolute", left: border * 2, right: border * 2, top: border + h * 0.72, bottom: border * 1.5, background: shade(color, 1.2), padding: "10px 14px", boxSizing: "border-box" }}>
      {(lines.length ? lines : ["", ""]).slice(0, 2).map((l, i) => (
        <div key={i} style={{ fontFamily: "NeoEb", fontSize: nameSize * 0.72, color: "#fff", height: nameSize * 1.1, lineHeight: `${nameSize * 1.1}px`, borderBottom: `3px solid ${shade(color, 0.8)}`, whiteSpace: "nowrap", overflow: "hidden" }}>{hz(l)}</div>
      ))}
    </div>
  </div>
);
export const TcgCardMarquee: React.FC<{ cards: { name: string; img?: string; lines?: string[]; stars?: number }[]; at?: number; top?: number; startX?: number; colors?: string[]; p?: Partial<TcgCardMarqueeP> }> = ({ cards, at = 0, top, startX = W, colors = TCG_COLS, p }) => {
  const P = def(TcgCardMarqueeParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const Y = top ?? (H - P.cardH) / 2 - 20, step = P.cardW + P.gap, shift = (f - at) * P.speed;
  return (
    <>
      {cards.map((c, i) => {
        const x = startX + i * step - shift;
        if (x > W + 10 || x < -P.cardW - 10) return null;
        return <div key={i} style={{ position: "absolute", left: x, top: Y }}><TcgCard name={c.name} img={c.img} lines={c.lines} stars={c.stars} color={colors[i % colors.length]} w={P.cardW} h={P.cardH} border={P.border} nameSize={P.nameSize} starColor={P.starColor} /></div>;
      })}
    </>
  );
};

// ══ 19. 기사 헤드라인 종이띠 스택 ═════════════════════════════════════════
// ref4-samsung 35:10 — 실제 기사 제목을 흰 종이띠(+하드 그림자 4px 연회색)로 재조판, 2~3줄 엇갈림(x ≈40), -1°~+1° 기울기, 순차 팝 ≈8f 간격
export const HeadlineStripStackParams = z.object({
  stagger: num(8, 0, 40, 1, "순차 간격", "timing", "f"),
  popLen: num(5, 1, 20, 1, "팝 길이", "timing", "f"),
  popFrom: num(1.15, 0.3, 2, 0.05, "팝 시작 크기(배)", "motion"),
  popBlur: num(8, 0, 30, 0.5, "팝 가로블러", "look", "px"),
  height: num(70, 30, 160, 1, "띠 높이", "size", "px"),
  fontSize: num(40, 14, 80, 1, "제목 글자 크기", "size", "px"),
  subSize: num(17, 8, 40, 1, "부제 글자 크기", "size", "px"),
  shadow: num(4, 0, 20, 0.5, "그림자 오프셋", "size", "px"),
  paper: col("#FFFFFF", "띠 색"),
  ink: col("#1a1a1a", "글자 색"),
});
export type HeadlineStripStackP = z.infer<typeof HeadlineStripStackParams>;
export const HeadlineStripStack: React.FC<{ items: { title: string; sub?: string; x: number; y: number; rot?: number }[]; at: number; p?: Partial<HeadlineStripStackP> }> = ({ items, at, p }) => {
  const P = def(HeadlineStripStackParams, p);
  const f = useCurrentFrame();
  return (
    <>
      {items.map((it, i) => {
        const a = at + i * P.stagger;
        if (f < a) return null;
        const s = kf(f, a, [0, P.popLen], [P.popFrom, 1], Easing.out(Easing.cubic)), op = kf(f, a, [0, 2], [0.3, 1]), b = kf(f, a, [0, P.popLen * 0.6], [P.popBlur, 0]);
        return (
          <HBlurBox key={i} amt={b} style={{ position: "absolute", left: it.x, top: it.y, transform: `rotate(${it.rot ?? 0}deg) scale(${s})`, transformOrigin: "0% 50%", opacity: op }}>
            <div style={{ minHeight: P.height, boxSizing: "border-box", background: P.paper, padding: `${P.height * 0.16}px ${P.fontSize * 0.5}px ${P.height * 0.1}px`, boxShadow: `${P.shadow}px ${P.shadow}px 0 rgba(0,0,0,0.16)`, color: P.ink, whiteSpace: "nowrap" }}>
              <div style={{ fontFamily: "NeoEb", fontSize: P.fontSize, lineHeight: 1.25 }}>{hz(it.title)}</div>
              {it.sub && <div style={{ fontFamily: "NeoEb", fontSize: P.subSize, color: "#666", marginTop: 4 }}>- {hz(it.sub)}</div>}
            </div>
          </HBlurBox>
        );
      })}
    </>
  );
};

// ══ 20. 확성기 원뿔 텍스트 ═══════════════════════════════════════════════
// ref4-samsung 1:26:00 — 확성기 팝 → ~12f 뒤 입구에서 노란 원뿔(#F4D35E, 길이 ~900, -25°)이 펼쳐지고, 원뿔 축을 따라 기울어진 주장 문구가 순차 팝
export const MegaphoneConeParams = z.object({
  popLen: num(5, 1, 20, 1, "확성기 팝 길이", "timing", "f"),
  coneDelay: num(12, 0, 60, 1, "원뿔 지연", "timing", "f"),
  coneLen: num(8, 1, 40, 1, "원뿔 펼침 길이", "timing", "f"),
  angle: num(-25, -80, 80, 1, "원뿔 기울기(위쪽 −)", "motion", "°"),
  length: num(1000, 200, 1800, 10, "원뿔 길이", "size", "px"),
  mouth: num(240, 40, 600, 5, "입구 폭", "size", "px"),
  spread: num(820, 100, 1600, 10, "끝 폭", "size", "px"),
  size: num(330, 80, 700, 5, "확성기 크기", "size", "px"),
  textLen: num(5, 1, 20, 1, "문구 팝 길이", "timing", "f"),
  cone: col("#F4D35E", "원뿔 색"),
  rim: col("#2F3E8C", "확성기 테두리 색"),
});
export type MegaphoneConeP = z.infer<typeof MegaphoneConeParams>;
export const MegaphoneCone: React.FC<{ x: number; y: number; at: number; lines: { text: string; at: number; d: number; off?: number; size?: number; color?: string; underline?: string }[]; p?: Partial<MegaphoneConeP> }> = ({ x, y, at, lines, p }) => {
  const P = def(MegaphoneConeParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const ms = popK(f, at, P.popLen, 0.4, 0.08);
  const ca = at + P.coneDelay, cu = f < ca ? 0 : kf(f, ca, [0, P.coneLen], [0, 1], Easing.out(Easing.cubic));
  const L = P.length, m = P.mouth / 2, s = P.spread / 2, S = P.size;
  // 원뿔: 로컬 좌표에서 입구(0,0) → 왼쪽(-L)으로 펼쳐지고, 전체를 angle 만큼 회전(왼쪽 위로 향함)
  return (
    <>
      <div style={{ position: "absolute", left: x, top: y, width: 0, height: 0, transform: `rotate(${-P.angle}deg)` }}>
        {cu > 0 && (
          <div style={{ position: "absolute", left: 0, top: 0, transform: `scale(${cu})`, transformOrigin: "0 0" }}>
            <svg width={L} height={s * 2} viewBox={`${-L} ${-s} ${L} ${s * 2}`} style={{ position: "absolute", left: -L, top: -s, overflow: "visible" }}>
              <polygon points={`0,${-m} ${-L},${-s} ${-L},${s} 0,${m}`} fill={P.cone} />
              {Array.from({ length: 5 }).map((_, i) => <circle key={i} cx={-20 - i * 18} cy={(i % 2 ? -1 : 1) * (m + 14 + i * 6)} r={4} fill="#fff" opacity={0.8} />)}
            </svg>
            {lines.map((ln, i) => {
              if (f < ln.at) return null;
              const k = popK(f, ln.at, P.textLen, 0.5, 0.08), b = kf(f, ln.at, [0, P.textLen], [8, 0]);
              const sz = ln.size ?? 56;
              return (
                <div key={i} style={{ position: "absolute", left: -ln.d, top: ln.off ?? 0, transform: `translate(-50%,-50%) rotate(${P.angle > 0 ? 0 : 0}deg) scale(${k})`, filter: b > 0.2 ? `blur(${b}px)` : undefined, fontFamily: "NeoHv", fontSize: sz, color: ln.color ?? "#fff", whiteSpace: "nowrap", lineHeight: 1.1, textAlign: "center" }}>
                  {hz(ln.text)}
                  {ln.underline && <div style={{ height: sz * 0.12, background: ln.underline, borderRadius: 99, marginTop: 2, transform: `scaleX(${kf(f, ln.at + P.textLen, [0, 5], [0, 1])})`, transformOrigin: "0 50%" }} />}
                </div>
              );
            })}
          </div>
        )}
      </div>
      <div style={{ position: "absolute", left: x, top: y, width: 0, height: 0, transform: `rotate(${-P.angle}deg) scale(${ms})` }}>
        {/* 세모지 그림체 확성기(megaphone) 좌우 반전 — 나팔 입구 중심(반전 후 0.1, 0.41)이 원뿔 입구(0,0). rim 색은 color 블렌드로 입힘 */}
        {(() => {
          const mw = S * 1.5, mh = propH("megaphone", mw), mk = `url(${prop("megaphone")})`;
          return (
            <div style={{ position: "absolute", left: -0.1 * mw, top: -0.41 * mh, width: mw, height: mh, transform: "scaleX(-1)", isolation: "isolate" }}>
              <Img src={prop("megaphone")} style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }} />
              <div style={{ position: "absolute", inset: 0, background: P.rim, mixBlendMode: "color", WebkitMaskImage: mk, maskImage: mk, WebkitMaskSize: "100% 100%", maskSize: "100% 100%" } as React.CSSProperties} />
            </div>
          );
        })()}
      </div>
    </>
  );
};
