// 도감 x_explainer — 설명형 편집 레퍼런스(여러 레퍼런스 중 하나, ref_explainer_editorial)의 '연출 기법'을 세모지 디자인(색·그림체·폰트)으로 옮긴 조합 컴포넌트.
// 타이밍·동작만 레퍼런스 실측(24f 원본 → 30f 환산값)을 따르고, 색·그림체·폰트는 세모지(플랫·외곽선 없음, 소품 키트 PNG, 세모지 캐스트).
// 모든 좌표는 화면(1920×1080) px. 난수는 remotion random(seed) 전용. 방사형 광선 금지.
import React, { useLayoutEffect, useMemo, useRef } from "react";
import { AbsoluteFill, Easing, Img, random, useCurrentFrame } from "remotion";
import { geoContains, geoOrthographic, geoPath, type GeoProjection } from "d3-geo";
import { z } from "zod";
import { W, H, lerp, EXPO_OUT, hz } from "../fx";
import { num, col, flag, choice, def } from "../params/p";
import { CAST, CastId, prop, propSize } from "./kit";
import { SemojiRig } from "./semoji_rig";
// Natural Earth 1:50m 육지(실제 데이터 — 손으로 그린 대륙 금지). 지도 데모 프로젝트 데이터 재사용(읽기 전용)
import LAND from "../data/ne_land50m.json";

type RN = React.ReactNode;
/** back-out(오버슈트) */
const BACK_OUT = Easing.bezier(0.34, 1.56, 0.64, 1);
const L = (f: number, a: number, b: number, v0: number, v1: number, e: (t: number) => number = Easing.linear) => lerp(f, a, Math.max(a + 0.001, b), v0, v1, e);

// ══ 1. 회전 지구본 → 감속 정지 → 히트맵 번짐 + 아이콘 산포 [설명형 레퍼런스 #9·#10] ═══════════════════════════
//   진입: 아래 +riseDist → 0, 25f ease-out. 회전: ease-out cubic 으로 spinDeg 를 spinLen 동안(초반 1.5s ≈ 90°) → 목표 경위도 정지.
//   히트맵 10f 번짐(육지 안쪽만). 아이콘 15~20개 1f 스태거, 개당 4f back-out. 세모지 색: 바다 #8FBFD6 · 육지 #EAD9B6 · 외곽선 없음.
export const GlobeSpinScatterParams = z.object({
  radius: num(400, 120, 900, 1, "지구본 반지름", "size", "px"),
  cx: num(960, 0, 1920, 1, "중심 X", "size", "px"),
  cy: num(540, 0, 1080, 1, "중심 Y", "size", "px"),
  riseLen: num(25, 1, 60, 1, "아래서 떠오르는 길이(ease-out)", "timing", "f"),
  riseDist: num(700, 0, 1400, 10, "떠오르는 거리", "motion", "px"),
  spinLen: num(120, 10, 400, 1, "회전→정지 길이", "timing", "f"),
  spinDeg: num(120, 0, 540, 1, "총 회전량(초반 1.5s ≈ 90°)", "motion", "°"),
  tiltFrom: num(-20, -60, 60, 1, "시작 위도 기울기", "motion", "°"),
  heatAt: num(112, 0, 400, 1, "히트맵 시작(at 기준)", "timing", "f"),
  heatLen: num(10, 1, 40, 1, "히트맵 번짐 길이", "timing", "f"),
  heatOp: num(0.75, 0, 1, 0.01, "히트맵 불투명도", "look"),
  iconAt: num(120, 0, 400, 1, "아이콘 산포 시작(at 기준)", "timing", "f"),
  iconN: num(18, 1, 40, 1, "아이콘 개수", "size"),
  iconStagger: num(1, 0, 10, 0.25, "아이콘 스태거", "timing", "f"),
  iconPop: num(4, 1, 20, 1, "아이콘 팝(back-out)", "timing", "f"),
  iconSize: num(58, 16, 200, 1, "아이콘 크기", "size", "px"),
  spread: num(20, 1, 60, 0.5, "산포 반경(위경도)", "size", "°"),
  landOnly: flag(true, "아이콘은 육지 위에만", "motion"),
  shadow: flag(true, "바닥 그림자", "look"),
  sea: col("#8FBFD6", "바다 색"),
  land: col("#EAD9B6", "육지 색"),
  heat: col("#E8512A", "히트맵 색"),
});
export type GlobeSpinScatterP = z.infer<typeof GlobeSpinScatterParams>;
export type GlobeHeat = { lon: number; lat: number; r: number; dt?: number };
export const GlobeSpinScatter: React.FC<{
  at: number;
  /** 정지 시 화면 중앙에 올 경위도 */ target: [number, number];
  heat?: GlobeHeat[];
  /** 산포 아이콘(세모지 소품 id, 순환). 위치는 center 주변 spread° 안 시드 랜덤(landOnly=육지 점만) 또는 pts 지정 */
  icons?: string[]; center?: [number, number]; pts?: [number, number][];
  seed?: string;
  overlay?: (project: (ll: [number, number]) => { x: number; y: number; visible: boolean }) => RN;
  p?: Partial<GlobeSpinScatterP>;
}> = ({ at, target, heat = [], icons = [], center, pts, seed = "gss", overlay, p }) => {
  const P = def(GlobeSpinScatterParams, p);
  const f = useCurrentFrame();
  const t = f - at;
  const rise = L(t, 0, P.riseLen, P.riseDist, 0, Easing.out(Easing.cubic));
  const k = L(t, 0, P.spinLen, 0, 1, Easing.out(Easing.cubic));
  const lon = target[0] - P.spinDeg * (1 - k);
  const lat = P.tiltFrom + (target[1] - P.tiltFrom) * k;
  const R = P.radius, cy = P.cy + rise;
  const mk = (): GeoProjection => geoOrthographic().scale(R).translate([P.cx, cy]).rotate([-lon, -lat]).clipAngle(90).precision(0.4);
  const proj = mk();
  const sphereD = geoPath(proj)({ type: "Sphere" } as any) || "";
  const project = (ll: [number, number]) => {
    const r = proj.rotate(), d2r = Math.PI / 180;
    const vis = Math.cos(ll[1] * d2r) * Math.cos((ll[0] + r[0]) * d2r) * Math.cos(-r[1] * d2r) + Math.sin(ll[1] * d2r) * Math.sin(-r[1] * d2r) > 0;
    const xy = proj(ll) || [-9999, -9999];
    return { x: xy[0], y: xy[1], visible: vis };
  };
  // 육지는 2D 캔버스로 채운다(거대 단일 SVG 경로는 angle 렌더에서 일부 면이 빠지는 현상 실측 — 지도 데모 프로젝트 Globe 와 같은 처리)
  const cvs = useRef<HTMLCanvasElement>(null);
  useLayoutEffect(() => {
    const c = cvs.current; if (!c) return;
    const ctx = c.getContext("2d", { willReadFrequently: true }); if (!ctx) return;
    ctx.clearRect(0, 0, W, H);
    const cp = geoPath(mk(), ctx as any);
    ctx.beginPath(); cp(LAND as any); ctx.fillStyle = P.land; ctx.fill();
    ctx.save(); ctx.clip();
    for (let i = 0; i < heat.length; i++) {
      const h = heat[i], a = at + P.heatAt + (h.dt ?? 0);
      const hk = L(f, a, a + P.heatLen, 0, 1, EXPO_OUT);
      if (hk <= 0) continue;
      const q = project([h.lon, h.lat]);
      if (!q.visible) continue;
      const rr = ((h.r * Math.PI) / 180) * R * (0.3 + 0.7 * hk);
      const g = ctx.createRadialGradient(q.x, q.y, 0, q.x, q.y, rr);
      g.addColorStop(0, P.heat); g.addColorStop(0.55, P.heat); g.addColorStop(1, /^#[0-9a-f]{6}$/i.test(P.heat) ? `${P.heat}00` : "rgba(255,255,255,0)");
      ctx.globalAlpha = P.heatOp * hk; ctx.fillStyle = g; ctx.fillRect(q.x - rr, q.y - rr, rr * 2, rr * 2);
    }
    ctx.restore();
  });
  const cen = center ?? target;
  // 산포 위치: center 주변 원판 안 시드 랜덤(landOnly 면 육지 점만 채택). 프레임마다 다시 계산하지 않게 메모
  const spots: [number, number][] = useMemo(() => pts ?? (() => {
    const out: [number, number][] = [], n = Math.round(P.iconN), cosL = Math.max(0.3, Math.cos((cen[1] * Math.PI) / 180));
    for (let j = 0; out.length < n && j < n * 40; j++) {
      const a = random(`${seed}a${j}`) * Math.PI * 2, r = Math.sqrt(random(`${seed}r${j}`)) * P.spread;
      const ll: [number, number] = [cen[0] + (r * Math.cos(a)) / cosL, cen[1] + r * Math.sin(a)];
      if (P.landOnly && !geoContains(LAND as any, ll)) continue;
      if (out.some((q) => Math.hypot((q[0] - ll[0]) * cosL, q[1] - ll[1]) < P.spread * 0.22)) continue;   // 너무 겹치지 않게
      out.push(ll);
    }
    return out;
  })(), [pts, P.iconN, P.spread, P.landOnly, cen[0], cen[1], seed]);
  return (
    <>
      {P.shadow && <div style={{ position: "absolute", left: P.cx - R * 0.8, top: cy + R * 0.94, width: R * 1.6, height: R * 0.16, borderRadius: "50%", background: "rgba(40,60,70,0.16)", filter: "blur(10px)" }} />}
      <svg width={W} height={H} style={{ position: "absolute", left: 0, top: 0 }}><path d={sphereD} fill={P.sea} /></svg>
      <canvas ref={cvs} width={W} height={H} style={{ position: "absolute", left: 0, top: 0, width: W, height: H }} />
      {icons.length > 0 && spots.map((ll, i) => {
        const a = at + P.iconAt + i * P.iconStagger;
        if (f < a) return null;
        const q = project(ll);
        if (!q.visible) return null;
        const id = icons[i % icons.length], [iw, ih] = propSize(id), sz = P.iconSize * (0.85 + 0.3 * random(`${seed}s${i}`));
        const w = iw >= ih ? sz : (sz * iw) / ih, h = iw >= ih ? (sz * ih) / iw : sz;
        const s = L(f, a, a + P.iconPop, 0, 1, BACK_OUT);
        return <Img key={i} src={prop(id)} style={{ position: "absolute", left: q.x - w / 2, top: q.y - h / 2, width: w, height: h, transform: `rotate(${(random(`${seed}t${i}`) - 0.5) * 24}deg) scale(${s})`, filter: "drop-shadow(0 3px 3px rgba(0,0,0,0.22))" }} />;
      })}
      {/* 지구본은 소축척이라 울릉도·독도 오버레이 대상 아님 */}
      {overlay?.(project)}
    </>
  );
};

// ══ 2. 점선 세로 구분 N열 비교 [설명형 레퍼런스 #28] — 점선이 위→아래로 그려지고, 열 라벨 팝, 열마다 대상이 차례로 자란다 ══════
export type ColumnItem = { label: string; /** 세모지 소품 id */ prop?: string; /** 또는 세모지 캐스트 전신 */ cast?: CastId; /** 최대 크기 대비 비율 0..1 */ value: number; caption?: string };
export const DashedColumnCompareParams = z.object({
  cols: num(3, 2, 4, 1, "열 수(앞에서부터 사용)", "size"),
  lineLen: num(12, 1, 60, 1, "점선 그려지는 길이", "timing", "f"),
  labelAt: num(6, 0, 90, 1, "라벨 등장(at 기준)", "timing", "f"),
  labelStagger: num(4, 0, 30, 1, "라벨 스태거", "timing", "f"),
  growAt: num(18, 0, 120, 1, "첫 대상 성장 시작(at 기준)", "timing", "f"),
  growStagger: num(15, 0, 90, 1, "열 간 성장 간격(0.5s)", "timing", "f"),
  growLen: num(15, 1, 60, 1, "성장 길이", "timing", "f"),
  grow: choice("scale", ["scale", "height"] as const, "성장 방식(scale=크기 back-out · height=아래에서 솟음)"),
  maxH: num(520, 100, 800, 10, "최대 대상 높이", "size", "px"),
  baseY: num(900, 500, 1060, 5, "바닥선 y", "size", "px"),
  labelSize: num(64, 24, 120, 1, "라벨 글자", "size", "px"),
  dash: num(22, 4, 80, 1, "점선 조각 길이", "size", "px"),
  lineW: num(6, 1, 20, 0.5, "점선 두께", "size", "px"),
  lineColor: col("#5B5046", "점선 색"),
  textColor: col("#2B2420", "글자 색"),
});
export type DashedColumnCompareP = z.infer<typeof DashedColumnCompareParams>;
export const DashedColumnCompare: React.FC<{ at: number; items: ColumnItem[]; bg?: RN; p?: Partial<DashedColumnCompareP> }> = ({ at, items, bg, p }) => {
  const P = def(DashedColumnCompareParams, p);
  const f = useCurrentFrame();
  const n = Math.max(2, Math.min(4, Math.round(P.cols), items.length));
  const cw = W / n;
  const lk = L(f, at, at + P.lineLen, 0, 1, Easing.out(Easing.cubic));
  return (
    <AbsoluteFill>
      {bg ?? <AbsoluteFill style={{ background: "linear-gradient(180deg,#DDE8E0 0%,#C2CDC4 100%)" }} />}
      <div style={{ position: "absolute", left: 0, right: 0, top: P.baseY, height: 10, background: "rgba(60,50,40,0.18)", opacity: lk }} />
      <svg width={W} height={H} style={{ position: "absolute", left: 0, top: 0 }}>
        {Array.from({ length: n - 1 }, (_, i) => <line key={i} x1={cw * (i + 1)} x2={cw * (i + 1)} y1={40} y2={40 + (H - 80) * lk} stroke={P.lineColor} strokeWidth={P.lineW} strokeDasharray={`${P.dash} ${P.dash * 0.8}`} strokeLinecap="round" />)}
      </svg>
      {items.slice(0, n).map((it, i) => {
        const cx = cw * (i + 0.5);
        const la = at + P.labelAt + i * P.labelStagger, ls = L(f, la, la + 6, 0, 1, BACK_OUT);
        const ga = at + P.growAt + i * P.growStagger;
        const gk = L(f, ga, ga + P.growLen, 0, 1, P.grow === "scale" ? BACK_OUT : Easing.out(Easing.cubic));
        const hMax = P.maxH * Math.max(0.05, Math.min(1, it.value));
        let node: RN = null;
        if (it.prop) {
          const [iw, ih] = propSize(it.prop), h = hMax, w = Math.min(cw * 0.86, (h * iw) / ih), hh = (w * ih) / iw;
          node = <Img src={prop(it.prop)} style={{ position: "absolute", left: cx - w / 2, top: P.baseY - hh, width: w, height: hh, filter: "drop-shadow(0 8px 10px rgba(0,0,0,0.18))" }} />;
        } else if (it.cast) {
          node = <SemojiRig cast={it.cast} x={cx} y={P.baseY} h={hMax} seed={`dcc${i}`} />;
        }
        const scaleT = P.grow === "scale" ? `scale(${gk})` : undefined;
        const clip = P.grow === "height" ? `inset(${(1 - gk) * 100}% -50% 0 -50%)` : undefined;
        const capA = ga + P.growLen;
        return (
          <React.Fragment key={i}>
            {f >= la && <div style={{ position: "absolute", left: cx - cw / 2, width: cw, top: 70, textAlign: "center", fontFamily: "Jua", fontSize: P.labelSize, color: P.textColor, transform: `scale(${ls})`, whiteSpace: "nowrap" }}>{hz(it.label)}</div>}
            {f >= ga && <AbsoluteFill style={{ transformOrigin: `${cx}px ${P.baseY}px`, transform: scaleT, clipPath: clip }}>{node}</AbsoluteFill>}
            {it.caption && f >= capA && <div style={{ position: "absolute", left: cx - cw / 2, width: cw, top: P.baseY + 22, textAlign: "center", fontFamily: "NeoHv", fontSize: 50, color: P.textColor, opacity: L(f, capA, capA + 5, 0, 1) }}>{it.caption}</div>}
          </React.Fragment>
        );
      })}
    </AbsoluteFill>
  );
};

// ══ 3. 역사 인물 메신저 대화 패러디 [설명형 레퍼런스 #35] — 가상 메신저(실존 서비스 로고·이름·상표 없음) ═══════════════
//   메시지 1~1.3s 간격으로 아래에 추가, 위로 푸시업 4f. 상대 메시지 앞엔 입력 중(...) 표시. 타임스탬프·안읽음 숫자(상대 답장 오면 사라짐).
export type ChatMsg = { from: CastId; name: string; text: string; side: "left" | "right"; time?: string; /** 이전 메시지 대비 추가 지연(f) */ delay?: number };
export const ChatParodyParams = z.object({
  gap: num(34, 10, 120, 1, "메시지 간격(1~1.3s)", "timing", "f"),
  firstAt: num(12, 0, 120, 1, "첫 메시지(at 기준)", "timing", "f"),
  pushLen: num(4, 1, 20, 1, "푸시업 길이", "timing", "f"),
  typeLead: num(16, 0, 60, 1, "상대 입력 중(...) 선행 표시", "timing", "f"),
  fontSize: num(34, 20, 60, 1, "메시지 글자", "size", "px"),
  bubbleMax: num(540, 200, 760, 10, "말풍선 최대 폭", "size", "px"),
  avatar: num(84, 40, 140, 1, "프로필 지름", "size", "px"),
  showTime: flag(true, "타임스탬프", "look"),
  showUnread: flag(true, "안읽음 숫자(상대 답장 시 사라짐)", "look"),
  appBg: col("#BFD8E4", "대화창 배경"),
  mine: col("#F9D65C", "내 말풍선"),
  theirs: col("#FFFFFF", "상대 말풍선"),
  header: col("#F7F2E6", "상단 바"),
});
export type ChatParodyP = z.infer<typeof ChatParodyParams>;
/** 흉상 프로필: 세모지 캐스트 머리가 원 안에 오도록 SemojiRig(bust) 를 크롭 */
export const CastAvatar: React.FC<{ cast: CastId; d: number; bg?: string; seed?: string }> = ({ cast, d, bg = "#F3E6CC", seed }) => {
  const R = CAST[cast], s = (d * 1.05) / 420, headCy = R.top + 200;
  return (
    <div style={{ position: "relative", width: d, height: d, borderRadius: d * 0.38, overflow: "hidden", background: bg, flexShrink: 0 }}>
      <SemojiRig cast={cast} bust x={d / 2} y={d / 2 + (R.torsoBottom + 10 - headCy) * s} h={(R.feet[1] - R.top) * s} seed={seed ?? cast} p={{ bobEvery: 0, blinkEvery: 0 }} />
    </div>
  );
};
const textW = (t: string, fs: number) => [...t].reduce((a, c) => a + (/[\u0000-ÿ]/.test(c) ? 0.56 : 1) * fs, 0);
export const ChatParody: React.FC<{ at: number; title: string; msgs: ChatMsg[]; members?: number; x?: number; y?: number; w?: number; h?: number; bg?: RN; p?: Partial<ChatParodyP> }> = ({ at, title, msgs, members, x = 510, y = 40, w = 900, h = 1000, bg, p }) => {
  const P = def(ChatParodyParams, p);
  const f = useCurrentFrame();
  const fs = P.fontSize, lh = fs * 1.35, padX = 24, padY = 16, headH = 110;
  // 도착 시각
  const arr: number[] = [];
  msgs.forEach((m, i) => arr.push(i === 0 ? at + P.firstAt + (m.delay ?? 0) : arr[i - 1] + P.gap + (m.delay ?? 0)));
  const lines = (t: string) => t.split("\n").reduce((a, l) => a + Math.max(1, Math.ceil(textW(l, fs) / (P.bubbleMax - padX * 2))), 0);
  const showName = (i: number) => msgs[i].side === "left" && (i === 0 || msgs[i - 1].from !== msgs[i].from || msgs[i - 1].side !== "left");
  const rowH = (i: number) => (showName(i) ? 40 : 0) + lines(msgs[i].text) * lh + padY * 2 + 18;
  const typH = lh + padY * 2 + 18 + 40;
  const typeOn = (i: number) => msgs[i].side === "left" && P.typeLead > 0 && f >= arr[i] - P.typeLead && f < arr[i];
  // 푸시업: 이벤트별 높이 변화량 × (1 - 진행)
  let off = 0;
  msgs.forEach((m, i) => {
    const pk = (a: number) => 1 - L(f, a, a + P.pushLen, 0, 1, Easing.out(Easing.quad));
    if (f >= arr[i]) off += (rowH(i) - (m.side === "left" && P.typeLead > 0 ? typH : 0)) * pk(arr[i]);
    if (m.side === "left" && P.typeLead > 0 && f >= arr[i] - P.typeLead) off += typH * pk(arr[i] - P.typeLead);
  });
  const shown = msgs.map((_, i) => i).filter((i) => f >= arr[i]);
  const typing = msgs.map((_, i) => i).filter(typeOn)[0];
  const lastRead = (i: number) => msgs.some((m, j) => j > i && m.side === "left" && f >= arr[j]);
  const bubble = (i: number) => {
    const m = msgs[i], mine = m.side === "right", age = f - arr[i];
    const ek = L(age, 0, P.pushLen, 0, 1, Easing.out(Easing.quad));
    const meta = (
      <div style={{ display: "flex", flexDirection: "column", alignItems: mine ? "flex-end" : "flex-start", justifyContent: "flex-end", fontFamily: "NeoEb", fontSize: 20, color: "#55707E", padding: "0 10px 4px", whiteSpace: "nowrap", lineHeight: 1.2 }}>
        {mine && P.showUnread && !lastRead(i) && <span style={{ color: "#E0A020", fontFamily: "NeoHv", fontSize: 21 }}>1</span>}
        {P.showTime && <span>{m.time ?? ""}</span>}
      </div>
    );
    const body = (
      <div style={{ maxWidth: P.bubbleMax, background: mine ? P.mine : P.theirs, borderRadius: 22, borderTopLeftRadius: !mine && showName(i) ? 6 : 22, borderTopRightRadius: mine ? 6 : 22, padding: `${padY}px ${padX}px`, fontFamily: "NeoEb", fontSize: fs, lineHeight: `${lh}px`, color: "#1E1E1E", whiteSpace: "pre-wrap", wordBreak: "keep-all", boxShadow: "0 2px 0 rgba(0,0,0,0.06)" }}>{hz(m.text)}</div>
    );
    return (
      <div key={`m${i}`} style={{ display: "flex", flexDirection: mine ? "row-reverse" : "row", alignItems: "flex-start", gap: 14, marginBottom: 18, opacity: ek, transform: `translateY(${(1 - ek) * 20}px)` }}>
        {!mine && (showName(i) ? <CastAvatar cast={m.from} d={P.avatar} /> : <div style={{ width: P.avatar, flexShrink: 0 }} />)}
        <div style={{ display: "flex", flexDirection: "column", alignItems: mine ? "flex-end" : "flex-start" }}>
          {!mine && showName(i) && <div style={{ fontFamily: "NeoEb", fontSize: 26, color: "#2F4450", height: 40, lineHeight: "34px" }}>{hz(m.name)}</div>}
          <div style={{ display: "flex", flexDirection: mine ? "row-reverse" : "row", alignItems: "flex-end" }}>{body}{meta}</div>
        </div>
      </div>
    );
  };
  const typingRow = (i: number) => {
    const m = msgs[i], t = f - (arr[i] - P.typeLead);
    return (
      <div key={`t${i}`} style={{ display: "flex", alignItems: "flex-start", gap: 14, marginBottom: 18, opacity: L(t, 0, P.pushLen, 0, 1) }}>
        <CastAvatar cast={m.from} d={P.avatar} />
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ fontFamily: "NeoEb", fontSize: 26, color: "#2F4450", height: 40, lineHeight: "34px" }}>{hz(m.name)}</div>
          <div style={{ background: P.theirs, borderRadius: 22, borderTopLeftRadius: 6, padding: `${padY}px ${padX + 6}px`, height: lh, display: "flex", alignItems: "center", gap: 10, boxSizing: "content-box" }}>
            {[0, 1, 2].map((d) => <div key={d} style={{ width: 13, height: 13, borderRadius: 7, background: "#8FA3AD", transform: `translateY(${-6 * Math.max(0, Math.sin(((t - d * 4) / 12) * Math.PI * 2))}px)` }} />)}
          </div>
        </div>
      </div>
    );
  };
  return (
    <AbsoluteFill>
      {bg ?? <AbsoluteFill style={{ background: "linear-gradient(180deg,#E6EFE4 0%,#C2CDC4 100%)" }} />}
      <div style={{ position: "absolute", left: x, top: y, width: w, height: h, borderRadius: 40, overflow: "hidden", background: P.appBg, boxShadow: "0 18px 40px rgba(40,50,40,0.28)" }}>
        <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, top: headH, overflow: "hidden" }}>
          <div style={{ position: "absolute", left: 28, right: 28, bottom: 24, display: "flex", flexDirection: "column", transform: `translateY(${off}px)` }}>
            {shown.map(bubble)}
            {typing !== undefined && typingRow(typing)}
          </div>
        </div>
        <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: headH, background: P.header, display: "flex", alignItems: "center", padding: "0 34px", gap: 22, boxShadow: "0 2px 0 rgba(0,0,0,0.06)" }}>
          <svg width={30} height={40} viewBox="0 0 30 40"><path d="M24 4 L8 20 L24 36" stroke="#2F4450" strokeWidth={5} fill="none" strokeLinecap="round" strokeLinejoin="round" /></svg>
          <div style={{ fontFamily: "NeoHv", fontSize: 40, color: "#22313A", whiteSpace: "nowrap" }}>{hz(title)}</div>
          {members !== undefined && <div style={{ fontFamily: "NeoEb", fontSize: 30, color: "#7C8C94" }}>{members}</div>}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ══ 4. 지도 전력 통계 오버레이 [설명형 레퍼런스 5JTEU99XKb0 stats] — 배경 딤 6f → 제목 타자(1.5f/자) → 아이콘+큰 숫자 행 0.5s 간격 팝 ═══
//   숫자 70px 흰 NeoHv + 작은 단위(세모지 노랑). 아이콘 = 세모지 소품 키트(흰 원 배지).
export type StatRow = { icon: string; value: string; unit?: string; label?: string };
export const MapStatOverlayParams = z.object({
  dimLen: num(6, 1, 30, 1, "배경 딤 길이", "timing", "f"),
  bright: num(0.45, 0, 1, 0.01, "배경 밝기", "look"),
  blur: num(3, 0, 20, 0.5, "배경 블러", "look", "px"),
  perChar: num(1.5, 0, 6, 0.25, "제목 글자당 타자", "timing", "f"),
  rowsAt: num(8, 0, 120, 1, "첫 행(제목 끝 기준)", "timing", "f"),
  rowGap: num(15, 0, 60, 1, "행 간격(0.5s)", "timing", "f"),
  popLen: num(6, 1, 30, 1, "행 팝(back-out)", "timing", "f"),
  titleSize: num(72, 30, 140, 1, "제목 크기", "size", "px"),
  numSize: num(70, 30, 160, 1, "숫자 크기", "size", "px"),
  unitSize: num(36, 16, 80, 1, "단위 크기", "size", "px"),
  labelSize: num(40, 16, 80, 1, "항목 이름 크기", "size", "px"),
  iconSize: num(96, 30, 200, 1, "아이콘 배지 지름", "size", "px"),
  rowH: num(130, 60, 240, 1, "행 높이", "size", "px"),
  accent: col("#F6C43A", "단위·밑줄 색"),
});
export type MapStatOverlayP = z.infer<typeof MapStatOverlayParams>;
export const MapStatOverlay: React.FC<{ at: number; title: string; rows: StatRow[]; bg?: RN; x?: number; y?: number; out?: number; p?: Partial<MapStatOverlayP> }> = ({ at, title, rows, bg, x = 960, y = 250, out, p }) => {
  const P = def(MapStatOverlayParams, p);
  const f = useCurrentFrame();
  const k = L(f, at, at + P.dimLen, 0, 1, Easing.out(Easing.cubic)) * (out !== undefined ? L(f, out, out + 8, 1, 0) : 1);
  const ta = at + P.dimLen, nChars = f < ta ? 0 : Math.floor((f - ta) / Math.max(0.001, P.perChar)) + 1;
  const titleEnd = ta + [...title].length * P.perChar;
  const o = out !== undefined ? L(f, out, out + 6, 1, 0) : 1;
  return (
    <AbsoluteFill>
      {bg && <AbsoluteFill style={{ filter: k > 0.001 ? `brightness(${1 - (1 - P.bright) * k}) blur(${P.blur * k}px)` : undefined }}>{bg}</AbsoluteFill>}
      {!bg && <AbsoluteFill style={{ background: `rgba(20,24,28,${(1 - P.bright) * k})` }} />}
      <div style={{ position: "absolute", left: 0, right: 0, top: y - P.titleSize, textAlign: "center", fontFamily: "Yeonsung", fontSize: P.titleSize, color: "#fff", textShadow: "0 4px 10px rgba(0,0,0,0.45)", whiteSpace: "nowrap", opacity: o }}>
        {[...title].map((c, i) => <span key={i} style={{ visibility: i < nChars ? "visible" : "hidden" }}>{hz(c)}</span>)}
      </div>
      <div style={{ position: "absolute", left: x - 260, top: y + 18, width: 520 * L(f, titleEnd - 2, titleEnd + 6, 0, 1, Easing.out(Easing.cubic)), height: 8, borderRadius: 4, background: P.accent, opacity: o }} />
      {rows.map((r, i) => {
        const a = titleEnd + P.rowsAt + i * P.rowGap;
        if (f < a) return null;
        const s = L(f, a, a + P.popLen, 0, 1, BACK_OUT), [iw, ih] = propSize(r.icon), isz = P.iconSize * 0.72;
        const w = iw >= ih ? isz : (isz * iw) / ih, h = iw >= ih ? (isz * ih) / iw : isz;
        return (
          <div key={i} style={{ position: "absolute", left: x - 360, top: y + 70 + i * P.rowH, width: 720, height: P.rowH, display: "flex", alignItems: "center", gap: 28, transformOrigin: `${P.iconSize / 2}px 50%`, transform: `scale(${s})`, opacity: o }}>
            <div style={{ width: P.iconSize, height: P.iconSize, borderRadius: "50%", background: "#fff", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, boxShadow: "0 5px 10px rgba(0,0,0,0.3)" }}>
              <Img src={prop(r.icon)} style={{ width: w, height: h }} />
            </div>
            {r.label && <div style={{ fontFamily: "NeoEb", fontSize: P.labelSize, color: "#fff", textShadow: "0 3px 6px rgba(0,0,0,0.5)", whiteSpace: "nowrap", flex: 1 }}>{hz(r.label)}</div>}
            <div style={{ whiteSpace: "nowrap", textShadow: "0 4px 8px rgba(0,0,0,0.5)" }}>
              <span style={{ fontFamily: "NeoHv", fontSize: P.numSize, color: "#fff" }}>{r.value}</span>
              {r.unit && <span style={{ fontFamily: "NeoEb", fontSize: P.unitSize, color: P.accent, marginLeft: 8 }}>{r.unit}</span>}
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
