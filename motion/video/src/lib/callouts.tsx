// 세모지 콜아웃·텍스트·레이아웃 어휘 — 레퍼런스 프레임 실측 사양으로 구현.
// 모든 위치는 1920×1080 절대 px, 모든 시간은 프레임(at 기준 오프셋). 결정론: remotion random(seed)만 사용.
// 규칙: 방사형 줄무늬 광선 금지 — 강조는 소프트 글로우 + 링.
import React from "react";
import { AbsoluteFill, Img, Easing, random, useCurrentFrame } from "remotion";
import { z } from "zod";
import { W, H, lerp, kf, photoPop, textPop, EXPO_OUT, QUART_OUT, hz, src, GlowPulse } from "../fx";
import { num, col, def } from "../params/p";
import { prop, propH, CAST, CastId } from "./kit";
import { SemojiRig } from "./semoji_rig";

export type P = [number, number];
/** undefined 인 키를 걸러낸다 — 기존 개별 prop 을 변수(P)에 합칠 때 사용 */
const defined = <T extends object>(o: T): Partial<T> => Object.fromEntries(Object.entries(o).filter(([, v]) => v !== undefined)) as Partial<T>;
/** 3키 팝 곡선: s0 → over → 1.0, 길이 dur(중간 키 = dur×m/n). 기본 pop5 = popK(f,at,0.3,1.1,5) */
const popK = (f: number, at: number, s0: number, over: number, dur: number, m = 3, n = 5, e: (t: number) => number = Easing.out(Easing.quad)) =>
  kf(f, at, [0, (dur * m) / n, dur], [s0, over, 1.0], e);

// ══ 공용 헬퍼 ════════════════════════════════════════════════════════════
export const polyLen = (pts: P[]) => pts.slice(1).reduce((a, p, i) => a + Math.hypot(p[0] - pts[i][0], p[1] - pts[i][1]), 0);
/** 폴리라인을 시작점부터 길이 l 까지만 잘라 반환(등속 드로우용) */
export const polyUpTo = (pts: P[], l: number): P[] => {
  if (l <= 0) return [pts[0], pts[0]];
  const out: P[] = [pts[0]];
  let rem = l;
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1], b = pts[i];
    const d = Math.hypot(b[0] - a[0], b[1] - a[1]);
    if (rem >= d) { out.push(b); rem -= d; } else {
      const t = d ? rem / d : 0;
      out.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]);
      return out;
    }
  }
  return out;
};
export const dOf = (pts: P[]) => pts.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
const useFid = (pre: string) => pre + React.useId().replace(/[^a-zA-Z0-9]/g, "");

/** 가로 방향 모션블러(SVG feGaussianBlur x만) */
export const HBlur: React.FC<{ amt: number; style?: React.CSSProperties; children: React.ReactNode }> = ({ amt, style, children }) => {
  const id = useFid("hb");
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

/** 기본 팝 0.3→1.1→1.0 (5f) */
const pop5 = (f: number, at: number) => kf(f, at, [0, 3, 5], [0.3, 1.1, 1.0], Easing.out(Easing.quad));

// ══ 아이콘 세트(플랫, viewBox 100) ═════════════════════════════════════════
export type IconName = "doc" | "phone" | "chip" | "cloud" | "gear" | "bulb" | "cart" | "user" | "money" | "globe" | "heart" | "star" | "truck" | "chart" | "lock" | "factory" | "bowl" | "ship" | "search" | "mail";
export const Icon: React.FC<{ name: IconName; color?: string; size?: number | string; accent?: string }> = ({ name, color = "#2B2B2B", size = "100%", accent = "#fff" }) => {
  const c = color, a = accent;
  const body: Record<IconName, React.ReactNode> = {
    doc: <><path d="M22,8 H62 L80,26 V92 H22 Z" fill={c} /><path d="M62,8 V26 H80" fill={a} opacity={0.5} />{[40, 54, 68].map((y) => <rect key={y} x={32} y={y} width={38} height={6} rx={3} fill={a} />)}</>,
    phone: <><rect x={28} y={6} width={44} height={88} rx={9} fill={c} /><rect x={33} y={16} width={34} height={62} rx={3} fill={a} /><circle cx={50} cy={86} r={3.5} fill={a} /></>,
    chip: <><rect x={24} y={24} width={52} height={52} rx={6} fill={c} /><rect x={36} y={36} width={28} height={28} rx={3} fill={a} />{[32, 44, 56, 68].map((p) => <g key={p} fill={c}><rect x={p - 2} y={10} width={4} height={14} /><rect x={p - 2} y={76} width={4} height={14} /><rect x={10} y={p - 2} width={14} height={4} /><rect x={76} y={p - 2} width={14} height={4} /></g>)}</>,
    cloud: <path d="M28,78 a18,18 0 0 1 -2,-36 a24,24 0 0 1 46,-6 a20,20 0 0 1 4,42 Z" fill={c} />,
    gear: <><g fill={c}>{Array.from({ length: 8 }).map((_, i) => <rect key={i} x={43} y={6} width={14} height={20} rx={3} transform={`rotate(${i * 45} 50 50)`} />)}<circle cx={50} cy={50} r={30} /></g><circle cx={50} cy={50} r={12} fill={a} /></>,
    bulb: <><circle cx={50} cy={40} r={28} fill={c} /><rect x={38} y={62} width={24} height={14} fill={c} /><rect x={40} y={80} width={20} height={8} rx={3} fill={c} /><path d="M42,40 q8,-12 16,0" stroke={a} strokeWidth={5} fill="none" strokeLinecap="round" /></>,
    cart: <><path d="M8,16 H22 L32,62 H78 L88,28 H26" stroke={c} strokeWidth={8} fill="none" strokeLinejoin="round" strokeLinecap="round" /><circle cx={38} cy={80} r={8} fill={c} /><circle cx={72} cy={80} r={8} fill={c} /></>,
    user: <><circle cx={50} cy={32} r={20} fill={c} /><path d="M14,94 a36,32 0 0 1 72,0 Z" fill={c} /></>,
    money: <><rect x={8} y={24} width={84} height={52} rx={6} fill={c} /><circle cx={50} cy={50} r={16} fill={a} /><text x={50} y={58} textAnchor="middle" fontFamily="NeoHv" fontSize={22} fill={c}>₩</text></>,
    globe: <><circle cx={50} cy={50} r={40} fill={c} /><g stroke={a} strokeWidth={4} fill="none"><ellipse cx={50} cy={50} rx={17} ry={40} /><path d="M10,50 H90 M16,30 H84 M16,70 H84" /></g></>,
    heart: <path d="M50,88 C20,66 8,50 8,34 a20,20 0 0 1 42,-10 a20,20 0 0 1 42,10 C92,50 80,66 50,88 Z" fill={c} />,
    star: <polygon points="50,6 62,38 96,38 68,58 79,92 50,72 21,92 32,58 4,38 38,38" fill={c} />,
    truck: <><rect x={6} y={26} width={56} height={44} rx={4} fill={c} /><path d="M62,40 H80 L94,56 V70 H62 Z" fill={c} /><circle cx={26} cy={76} r={10} fill={c} stroke={a} strokeWidth={4} /><circle cx={76} cy={76} r={10} fill={c} stroke={a} strokeWidth={4} /></>,
    chart: <><rect x={12} y={56} width={16} height={32} rx={3} fill={c} /><rect x={36} y={38} width={16} height={50} rx={3} fill={c} /><rect x={60} y={18} width={16} height={70} rx={3} fill={c} /><path d="M8,92 H92" stroke={c} strokeWidth={5} /></>,
    lock: <><path d="M30,46 V32 a20,20 0 0 1 40,0 V46" stroke={c} strokeWidth={9} fill="none" /><rect x={20} y={44} width={60} height={46} rx={8} fill={c} /><circle cx={50} cy={64} r={7} fill={a} /></>,
    factory: <><path d="M6,90 V46 L30,60 V46 L54,60 V46 L78,60 V14 H92 V90 Z" fill={c} />{[20, 44, 68].map((x) => <rect key={x} x={x} y={70} width={10} height={10} fill={a} />)}</>,
    bowl: <><path d="M8,46 H92 a42,40 0 0 1 -84,0 Z" fill={c} /><path d="M36,40 L70,6 M46,40 L80,10" stroke={c} strokeWidth={5} strokeLinecap="round" /><rect x={34} y={84} width={32} height={8} rx={3} fill={c} /></>,
    ship: <><path d="M6,62 H94 L80,88 H20 Z" fill={c} /><path d="M50,8 V58" stroke={c} strokeWidth={5} /><path d="M54,12 L82,54 H54 Z" fill={c} /><path d="M46,20 L24,54 H46 Z" fill={c} opacity={0.7} /></>,
    search: <><circle cx={42} cy={42} r={26} stroke={c} strokeWidth={10} fill="none" /><path d="M62,62 L88,88" stroke={c} strokeWidth={12} strokeLinecap="round" /></>,
    mail: <><rect x={8} y={20} width={84} height={60} rx={6} fill={c} /><path d="M12,26 L50,56 L88,26" stroke={a} strokeWidth={6} fill="none" strokeLinejoin="round" /></>,
  };
  if (name === "user") return <CastIcon size={size} />;
  const kid = KIT_ICON[name];
  if (kid) return <KitIcon id={kid} color={c} size={size} />;
  return <svg viewBox="0 0 100 100" width={size} height={size} style={{ display: "block" }}>{body[name]}</svg>;
};
/** 사람 아이콘 = 세모지 캐스트 흉상(인포그래픽 사람 형상 금지 규칙). 크기 모를 때도 맞도록 200×200 foreignObject 를 viewBox 로 스케일 */
export const CastIcon: React.FC<{ size?: number | string; cast?: CastId; seed?: string }> = ({ size = "100%", cast = "walker1", seed = "ci" }) => {
  const R = CAST[cast], bh = 196, h = (bh * (R.feet[1] - R.top)) / (R.torsoBottom + 10 - R.top);
  return (
    <svg viewBox="0 0 200 200" width={size} height={size} style={{ display: "block", overflow: "visible" }}>
      <foreignObject x={0} y={0} width={200} height={200}>
        <div style={{ position: "relative", width: 200, height: 200 }}><SemojiRig cast={cast} x={100} y={200} h={h} bust seed={seed} /></div>
      </foreignObject>
    </svg>
  );
};
/** 세모지 그림체 아이콘(public/kit/props/icon_*.png, 연회색 D9/BD) → color 로 틴트. 없는 이름(bulb·lock·search·mail)은 SVG 유지 */
const KIT_ICON: Partial<Record<IconName, string>> = {
  doc: "icon_doc", phone: "icon_phone", chip: "icon_chip", cloud: "icon_cloud", gear: "icon_gear", cart: "icon_cart",
  money: "icon_money", globe: "icon_globe", heart: "icon_heart", star: "icon_star", truck: "icon_truck", chart: "icon_chart", bowl: "icon_bowl",
  ship: "xm_icon_ship", factory: "xm_icon_factory",
};
/** 키트 소품 PNG 배치: 이미지 안의 앵커점(ax,ay: 0~1 비율)을 (x,y)에 두고 그 점을 축으로 회전·반전. h 는 원본 비율(propH) */
export const KitImg: React.FC<{ id: string; x: number; y: number; w: number; ax?: number; ay?: number; rot?: number; flip?: boolean; style?: React.CSSProperties }> = ({ id, x, y, w, ax = 0.5, ay = 0.5, rot = 0, flip, style }) => {
  const h = propH(id, w);
  return <Img src={prop(id)} style={{ position: "absolute", left: x - ax * w, top: y - ay * h, width: w, height: h, transformOrigin: `${ax * w}px ${ay * h}px`, transform: `rotate(${rot}deg) scaleX(${flip ? -1 : 1})`, ...style }} />;
};
/** 회색 키트 PNG 틴트: 알파 마스크로 color 를 채우고, 원본을 밝혀(D9→흰) multiply 로 겹쳐 안쪽 음영(BD)만 살린다 */
export const KitIcon: React.FC<{ id: string; color?: string; size?: number | string; shade?: boolean }> = ({ id, color = "#2B2B2B", size = "100%", shade = true }) => {
  const u = `url(${prop(id)})`;
  const m: React.CSSProperties = { WebkitMaskImage: u, maskImage: u, WebkitMaskSize: "contain", maskSize: "contain", WebkitMaskRepeat: "no-repeat", maskRepeat: "no-repeat", WebkitMaskPosition: "center", maskPosition: "center" } as React.CSSProperties;
  return (
    <div style={{ width: size, height: size, position: "relative", isolation: "isolate" }}>
      <div style={{ position: "absolute", inset: 0, background: color, ...m }} />
      {shade && <Img src={prop(id)} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "contain", mixBlendMode: "multiply", filter: "grayscale(1) brightness(1.18)" }} />}
    </div>
  );
};

// ══ 1. 콜아웃 커넥터 ══════════════════════════════════════════════════════
// 흰 그라데이션 띠 위 라벨(120px) → 빨강 박스(#F60000, 10px, r24) 하드 등장 → 10px 라운드캡 직각선 15f 드로우
// → 도착 시 부품 이미지 + 제목(80px) 팝 → 부제 줄 → 하단 흰 카드 3장 스태거 팝
export const CalloutConnectorParams = z.object({
  stripDur: num(6, 1, 30, 1, "라벨 띠 펼침 길이", "timing", "f"),
  boxDelay: num(8, 0, 40, 1, "빨강 박스 등장 지연", "timing", "f"),
  lineDelay: num(10, 0, 40, 1, "연결선 시작 지연", "timing", "f"),
  drawF: num(15, 1, 60, 1, "연결선 그리기 길이", "timing", "f"),
  subDelay: num(8, 0, 40, 1, "도착 후 부제 지연", "timing", "f"),
  subStagger: num(6, 0, 30, 1, "부제 줄 간격", "timing", "f"),
  cardStagger: num(5, 0, 30, 1, "카드 스태거 간격", "timing", "f"),
  lineWidth: num(10, 2, 30, 1, "선·박스 두께", "size", "px"),
  boxRadius: num(24, 0, 80, 2, "박스 모서리 둥글기", "size", "px"),
  labelSize: num(120, 40, 200, 2, "라벨 글자 크기", "size", "px"),
  titleSize: num(80, 30, 160, 2, "제목 글자 크기", "size", "px"),
  color: col("#F60000", "박스·선 색"),
  titleColor: col("#fff", "제목·부제 색"),
});
export type CalloutConnectorP = z.infer<typeof CalloutConnectorParams>;
export const CalloutConnector: React.FC<{
  at: number; label: string; labelX: number; labelY: number;
  box: [number, number, number, number]; path: P[];
  part?: { img: string; x: number; y: number; w: number; h: number };
  title: string; titleX: number; titleY: number; titleColor?: string; subs?: string[];
  cards?: { icon: IconName; text: string; color?: string }[]; cardsX?: number; cardsY?: number;
  color?: string; drawF?: number; p?: Partial<CalloutConnectorP>;
}> = ({ at, label, labelX, labelY, box, path, part, title, titleX, titleY, titleColor, subs = [], cards = [], cardsX = 700, cardsY = 820, color, drawF, p }) => {
  const P = def(CalloutConnectorParams, { ...defined({ titleColor, color, drawF }), ...p });
  const f = useCurrentFrame();
  if (f < at) return null;
  const stripK = lerp(f, at, at + P.stripDur, 0, 100, QUART_OUT);
  const lp = textPop(f, at + 1);
  const boxOn = f >= at + P.boxDelay;
  const L = polyLen(path);
  const l0 = at + P.lineDelay;
  const drawn = lerp(f, l0, l0 + P.drawF, 0, L, Easing.inOut(Easing.quad));
  const A = l0 + P.drawF;
  const subAt = A + P.subDelay;
  const cardAt = subAt + subs.length * P.subStagger + 6;
  const [bx, by, bw, bh] = box;
  const color_ = P.color, titleColor_ = P.titleColor;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {/* 라벨 띠 */}
      <div style={{ position: "absolute", left: 0, top: labelY - 90, width: 1100, height: 180, clipPath: `inset(0 ${100 - stripK}% 0 0)`, background: "linear-gradient(90deg, rgba(255,255,255,0.97) 0%, rgba(255,255,255,0.9) 55%, rgba(255,255,255,0) 100%)" }} />
      <div style={{ position: "absolute", left: labelX, top: labelY, transform: `translateY(-50%) scale(${lp.s})`, transformOrigin: "0% 50%", opacity: lp.op, fontFamily: "NeoHv", fontSize: P.labelSize, color: "#111", letterSpacing: -2, whiteSpace: "nowrap", lineHeight: 1 }}>{hz(label)}</div>
      <svg width={W} height={H} style={{ position: "absolute", left: 0, top: 0 }}>
        {boxOn && <rect x={bx} y={by} width={bw} height={bh} rx={P.boxRadius} fill="none" stroke={color_} strokeWidth={P.lineWidth} />}
        {f >= l0 && <path d={dOf(polyUpTo(path, drawn))} stroke={color_} strokeWidth={P.lineWidth} fill="none" strokeLinecap="round" strokeLinejoin="round" />}
      </svg>
      {part && f >= A && (() => { const p = photoPop(f, A); return <Img src={src(part.img)} style={{ position: "absolute", left: part.x, top: part.y, width: part.w, height: part.h, objectFit: "contain", transform: `scale(${p.s})`, filter: `blur(${p.blur}px) drop-shadow(0 10px 14px rgba(0,0,0,0.45))` }} />; })()}
      {f >= A && (() => { const t = textPop(f, A + 2); return <div style={{ position: "absolute", left: titleX, top: titleY, transform: `scale(${t.s})`, transformOrigin: "0% 50%", opacity: t.op, filter: `blur(${t.blur / 3}px) drop-shadow(0 4px 6px rgba(0,0,0,0.5))`, fontFamily: "NeoHv", fontSize: P.titleSize, color: titleColor_, whiteSpace: "nowrap" }}>{hz(title)}</div>; })()}
      {subs.map((s, i) => {
        const a = subAt + i * P.subStagger;
        if (f < a) return null;
        return <div key={i} style={{ position: "absolute", left: titleX, top: titleY + 110 + i * 60, opacity: lerp(f, a, a + 6, 0, 1), transform: `translateY(${lerp(f, a, a + 6, 16, 0, QUART_OUT)}px)`, fontFamily: "NeoEb", fontSize: 44, color: titleColor_, whiteSpace: "nowrap", textShadow: "0 3px 6px rgba(0,0,0,0.6)" }}>{hz(s)}</div>;
      })}
      {cards.map((c, i) => {
        const a = cardAt + i * P.cardStagger;
        if (f < a) return null;
        const s = pop5(f, a);
        return (
          <div key={i} style={{ position: "absolute", left: cardsX + i * 390, top: cardsY, width: 360, height: 150, transform: `scale(${s})`, background: "#fff", borderRadius: 20, boxShadow: "0 10px 24px rgba(0,0,0,0.35)", display: "flex", alignItems: "center", gap: 22, padding: "0 26px", boxSizing: "border-box" }}>
            <div style={{ width: 92, height: 92, flex: "none" }}><Icon name={c.icon} color={c.color || color_} /></div>
            <div style={{ fontFamily: "NeoHv", fontSize: 40, color: "#1a1a1a", lineHeight: 1.15, whiteSpace: "pre-line" }}>{c.text}</div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// ══ 2. 점선 경로 드로우 ════════════════════════════════════════════════════
// 양 끝 아이콘 스태거 팝(5f) → 대시 16/12(4px) 직각 다중 세그먼트를 등속 ~30px/f 로 그린다
export const DottedPathDrawParams = z.object({
  lineDelay: num(10, 0, 60, 1, "선 그리기 시작 지연", "timing", "f"),
  speed: num(30, 1, 200, 1, "그리기 속도(px/f)", "motion", "px"),
  endStagger: num(5, 0, 30, 1, "양 끝 아이콘 스태거", "timing", "f"),
  endOver: num(1.15, 1, 1.6, 0.01, "아이콘 오버슈트 크기(배)", "motion", "배"),
  dash: num(16, 1, 80, 1, "점선 길이", "size", "px"),
  gap: num(12, 0, 80, 1, "점선 간격", "size", "px"),
  width: num(4, 1, 20, 1, "선 두께", "size", "px"),
  endSize: num(150, 40, 300, 2, "끝 아이콘 크기", "size", "px"),
  color: col("#fff", "선 색"),
});
export type DottedPathDrawP = z.infer<typeof DottedPathDrawParams>;
export const DottedPathDraw: React.FC<{
  pts: P[]; at: number; lineAt?: number; color?: string; dash?: number; gap?: number; width?: number; speed?: number;
  ends?: [React.ReactNode, React.ReactNode]; endSize?: number; p?: Partial<DottedPathDrawP>;
}> = ({ pts, at, lineAt, color: color0, dash: dash0, gap: gap0, width: width0, speed: speed0, ends, endSize: endSize0, p }) => {
  const P = def(DottedPathDrawParams, { ...defined({ color: color0, dash: dash0, gap: gap0, width: width0, speed: speed0, endSize: endSize0 }), ...p });
  const { color, dash, gap, width, speed, endSize } = P;
  const f = useCurrentFrame();
  if (f < at) return null;
  const l0 = lineAt ?? at + P.lineDelay;
  const drawn = Math.max(0, (f - l0) * speed);
  const endPts = [pts[0], pts[pts.length - 1]];
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <svg width={W} height={H} style={{ position: "absolute" }}>
        {drawn > 0 && <path d={dOf(polyUpTo(pts, drawn))} stroke={color} strokeWidth={width} fill="none" strokeDasharray={`${dash} ${gap}`} strokeLinejoin="round" />}
      </svg>
      {ends && endPts.map(([x, y], i) => {
        const a = at + i * P.endStagger;
        if (f < a) return null;
        const s = kf(f, a, [0, 3, 5], [0.3, P.endOver, 1.0]);
        return <div key={i} style={{ position: "absolute", left: x - endSize / 2, top: y - endSize / 2, width: endSize, height: endSize, transform: `scale(${s})` }}>{ends[i]}</div>;
      })}
    </AbsoluteFill>
  );
};

// ══ 3. 회로 분기 ═════════════════════════════════════════════════════════
// 허브에서 흰 직각선(6px) 3가닥이 순차 드로우(7f, 4f 스태거) → 끝마다 아이콘 0.3→1.1→1 (5f)
export const CircuitBranchParams = z.object({
  branchDelay: num(6, 0, 30, 1, "허브 후 가지 시작 지연", "timing", "f"),
  drawF: num(7, 1, 40, 1, "가지 그리기 길이", "timing", "f"),
  stagger: num(4, 0, 20, 1, "가지 스태거 간격", "timing", "f"),
  popDur: num(5, 1, 20, 1, "팝 길이", "timing", "f"),
  popStart: num(0.3, 0, 1, 0.05, "팝 시작 크기(배)", "motion", "배"),
  popOver: num(1.1, 1, 1.6, 0.01, "오버슈트 크기(배)", "motion", "배"),
  lineWidth: num(6, 1, 24, 1, "선 두께", "size", "px"),
  hubSize: num(200, 60, 400, 2, "허브 크기", "size", "px"),
  iconSize: num(150, 40, 300, 2, "끝 아이콘 크기", "size", "px"),
  labelSize: num(36, 16, 80, 1, "라벨 글자 크기", "size", "px"),
  color: col("#fff", "선·라벨 색"),
});
export type CircuitBranchP = z.infer<typeof CircuitBranchParams>;
export const CircuitBranch: React.FC<{
  hub: P; at: number; hubNode?: React.ReactNode; hubSize?: number;
  branches: { pts: P[]; icon: React.ReactNode; label?: string }[];
  color?: string; drawF?: number; stagger?: number; iconSize?: number; p?: Partial<CircuitBranchP>;
}> = ({ hub, at, hubNode, hubSize: hubSize0, branches, color: color0, drawF: drawF0, stagger: stagger0, iconSize: iconSize0, p }) => {
  const P = def(CircuitBranchParams, { ...defined({ hubSize: hubSize0, color: color0, drawF: drawF0, stagger: stagger0, iconSize: iconSize0 }), ...p });
  const { hubSize, color, drawF, stagger, iconSize } = P;
  const pop = (f: number, a: number) => popK(f, a, P.popStart, P.popOver, P.popDur);
  const f = useCurrentFrame();
  if (f < at) return null;
  const hs = pop(f, at);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <svg width={W} height={H} style={{ position: "absolute" }}>
        {branches.map((b, i) => {
          const a = at + P.branchDelay + i * stagger;
          if (f < a) return null;
          const L = polyLen(b.pts);
          return <path key={i} d={dOf(polyUpTo(b.pts, lerp(f, a, a + drawF, 0, L, Easing.out(Easing.quad))))} stroke={color} strokeWidth={P.lineWidth} fill="none" strokeLinejoin="round" strokeLinecap="square" />;
        })}
      </svg>
      {hubNode && <div style={{ position: "absolute", left: hub[0] - hubSize / 2, top: hub[1] - hubSize / 2, width: hubSize, height: hubSize, transform: `scale(${hs})` }}>{hubNode}</div>}
      {branches.map((b, i) => {
        const a = at + P.branchDelay + i * stagger + drawF;
        if (f < a) return null;
        const [x, y] = b.pts[b.pts.length - 1];
        const s = pop(f, a);
        return (
          <div key={i} style={{ position: "absolute", left: x - iconSize / 2, top: y - iconSize / 2, width: iconSize, transform: `scale(${s})`, display: "flex", flexDirection: "column", alignItems: "center" }}>
            <div style={{ width: iconSize, height: iconSize }}>{b.icon}</div>
            {b.label && <div style={{ marginTop: 10, fontFamily: "NeoHv", fontSize: P.labelSize, color, whiteSpace: "nowrap" }}>{b.label}</div>}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// ══ 공용 pill ════════════════════════════════════════════════════════════
export const Pill: React.FC<{ text: string; color?: string; size?: number; fg?: string; style?: React.CSSProperties }> = ({ text, color = "#1FA3D6", size = 60, fg = "#fff", style }) => (
  <div style={{ background: color, color: fg, fontFamily: "NeoHv", fontSize: size, padding: `${size * 0.28}px ${size * 0.62}px ${size * 0.22}px`, borderRadius: 999, whiteSpace: "nowrap", boxShadow: "0 8px 16px rgba(0,0,0,0.28)", lineHeight: 1.1, ...style }}>{hz(text)}</div>
);
/** 중심 기준 팝 pill: scale + 가로블러 */
const PopPill: React.FC<{ text: string; x: number; y: number; f: number; at: number; color?: string; size?: number; ks?: number[]; vs?: number[]; blur0?: number }> = ({ text, x, y, f, at, color, size, ks = [0, 3, 5], vs = [0.3, 1.1, 1.0], blur0 = 14 }) => {
  if (f < at) return null;
  const s = kf(f, at, ks, vs, Easing.out(Easing.quad));
  const b = kf(f, at, [0, ks[ks.length - 1]], [blur0, 0]);
  return (
    <HBlur amt={b} style={{ position: "absolute", left: x, top: y, transform: `translate(-50%,-50%) scale(${s})`, opacity: kf(f, at, [0, 1], [0.5, 1]) }}>
      <Pill text={text} color={color} size={size} />
    </HBlur>
  );
};

// ══ 4. pill → 굵은 화살표 → pill ═════════════════════════════════════════
export const PillArrowPillParams = z.object({
  step: num(15, 1, 60, 1, "단계 간격(pill→화살표→pill)", "timing", "f"),
  arrowDur: num(10, 1, 40, 1, "화살표 펼침 길이", "timing", "f"),
  popDur: num(5, 1, 20, 1, "pill 팝 길이", "timing", "f"),
  popStart: num(0.3, 0, 1, 0.05, "pill 시작 크기(배)", "motion", "배"),
  popOver: num(1.1, 1, 1.6, 0.01, "오버슈트 크기(배)", "motion", "배"),
  blur0: num(14, 0, 60, 1, "가로 모션블러 세기", "look", "px"),
  spread: num(470, 150, 900, 10, "pill 좌우 거리", "size", "px"),
  size: num(64, 24, 140, 2, "pill 글자 크기", "size", "px"),
  arrowScale: num(1, 0.3, 2.5, 0.05, "화살표 크기(배)", "size", "배"),
  color: col("#1FA3D6", "pill 색"),
  arrowColor: col("#fff", "화살표 색"),
});
export type PillArrowPillP = z.infer<typeof PillArrowPillParams>;
export const PillArrowPill: React.FC<{ a: string; b: string; at: number; x?: number; y?: number; step?: number; color?: string; spread?: number; size?: number; p?: Partial<PillArrowPillP> }> = ({ a, b, at, x = W / 2, y = H / 2, step: step0, color: color0, spread: spread0, size: size0, p }) => {
  const P = def(PillArrowPillParams, { ...defined({ step: step0, color: color0, spread: spread0, size: size0 }), ...p });
  const { step, color, spread, size } = P;
  const f = useCurrentFrame();
  if (f < at) return null;
  const k = lerp(f, at + step, at + step + P.arrowDur, 0, 100, Easing.out(Easing.cubic));
  const pk = [0, (P.popDur * 3) / 5, P.popDur], pv = [P.popStart, P.popOver, 1.0];
  const as = P.arrowScale;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <PopPill text={a} x={x - spread} y={y} f={f} at={at} color={color} size={size} ks={pk} vs={pv} blur0={P.blur0} />
      {f >= at + step && (
        <svg width={280 * as} height={120 * as} viewBox="0 0 280 120" style={{ position: "absolute", left: x - 140 * as, top: y - 60 * as, clipPath: `inset(0 ${100 - k}% 0 0)`, filter: "drop-shadow(0 5px 6px rgba(0,0,0,0.35))" }}>
          <path d="M10,42 H186 V12 L270,60 L186,108 V78 H10 Z" fill={P.arrowColor} strokeLinejoin="round" />
        </svg>
      )}
      <PopPill text={b} x={x + spread} y={y} f={f} at={at + step * 2} color={color} size={size} ks={pk} vs={pv} blur0={P.blur0} />
    </AbsoluteFill>
  );
};

// ══ 5. pill 충돌 → 에너지 링 → 거대 텍스트 착지 ════════════════════════════
export const PillCollisionParams = z.object({
  approachDur: num(8, 1, 40, 1, "돌진 길이", "timing", "f"),
  startDist: num(720, 200, 1200, 10, "pill 시작 거리(중심→)", "motion", "px"),
  endDist: num(150, 0, 500, 5, "충돌 직전 거리", "motion", "px"),
  motionBlur: num(40, 0, 100, 1, "돌진 모션블러 세기", "look", "px"),
  ringDur: num(4, 1, 20, 1, "에너지 링 길이", "timing", "f"),
  ringR0: num(125, 20, 400, 5, "링 시작 반지름", "size", "px"),
  ringR1: num(190, 40, 600, 5, "링 끝 반지름", "size", "px"),
  burstDur: num(15, 1, 60, 1, "파편 흩어짐 길이", "timing", "f"),
  burstCount: num(14, 0, 40, 1, "파편 개수", "motion"),
  bigStart: num(1.5, 1, 3, 0.05, "거대 텍스트 시작 크기(배)", "motion", "배"),
  ghostDelay: num(15, 0, 60, 1, "착지 후 잔상 지연", "timing", "f"),
  pillSize: num(70, 30, 140, 2, "pill 글자 크기", "size", "px"),
  bigSize: num(240, 80, 400, 5, "거대 텍스트 크기", "size", "px"),
  color: col("#1FA3D6", "pill 색"),
  textColor: col("#1F4E9C", "거대 텍스트 색"),
  ringColor: col("#34D6F0", "링 색"),
});
export type PillCollisionP = z.infer<typeof PillCollisionParams>;
export const PillCollision: React.FC<{ left: string; right: string; big: string; at: number; x?: number; y?: number; color?: string; textColor?: string; ringColor?: string; bigSize?: number; p?: Partial<PillCollisionP> }> = ({ left, right, big, at, x = W / 2, y = H / 2, color: color0, textColor: textColor0, ringColor: ringColor0, bigSize: bigSize0, p }) => {
  const P = def(PillCollisionParams, { ...defined({ color: color0, textColor: textColor0, ringColor: ringColor0, bigSize: bigSize0 }), ...p });
  const { color, textColor, ringColor, bigSize } = P;
  const f = useCurrentFrame();
  const fid = useFid("sw");
  if (f < at) return null;
  const g = f - at;
  const ease = Easing.in(Easing.cubic);
  const AD = P.approachDur, RD = P.ringDur, BD = Math.max(1, P.burstDur);
  const d = lerp(f, at, at + AD, P.startDist, P.endDist, ease);
  const blur = lerp(f, at, at + AD, 0, P.motionBlur, ease);
  const R = at + AD + 1; // 링 시작
  const rg = f - R;
  const pill = (t: string, side: number) => (
    <HBlur amt={blur} style={{ position: "absolute", left: x + side * d, top: y, transform: "translate(-50%,-50%)" }}>
      <Pill text={t} color={color} size={P.pillSize} />
    </HBlur>
  );
  // 손그림 소용돌이 링: 20px 밴드 안에 불규칙 동심 스트로크 + 변위 필터
  const ringR = rg < 0 ? 0 : kf(rg, 0, [0, RD], [P.ringR0, P.ringR1], Easing.out(Easing.quad));
  const strands = Array.from({ length: 8 }).map((_, i) => ({ dr: -10 + i * 2.8 + (random(`st${i}`) - 0.5) * 2, w: 2.5 + random(`sw${i}`) * 3, dash: `${30 + random(`sd${i}`) * 120} ${10 + random(`sg${i}`) * 40}`, rot: random(`sr${i}`) * 360 + rg * (i % 2 ? 9 : -7) }));
  const bigAt = R + 2;
  const NB = Math.round(P.burstCount);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {g <= AD && pill(left, -1)}{g <= AD && pill(right, 1)}
      {g === AD && <div style={{ position: "absolute", left: x - 70, top: y - 70, width: 140, height: 140, borderRadius: "50%", background: "radial-gradient(circle, #fff 0%, #fff 40%, rgba(255,255,255,0) 72%)" }} />}
      <svg width={W} height={H} style={{ position: "absolute" }}>
        <filter id={fid} x="-20%" y="-20%" width="140%" height="140%"><feTurbulence type="fractalNoise" baseFrequency="0.06" numOctaves={2} seed={5} /><feDisplacementMap in="SourceGraphic" scale={18} /></filter>
        {rg >= 0 && rg <= RD && (
          <g style={{ filter: `drop-shadow(0 0 10px ${ringColor})` }}><g filter={`url(#${fid})`}>
            {strands.map((s, i) => <circle key={i} cx={x} cy={y} r={ringR + s.dr} stroke={ringColor} strokeWidth={s.w} fill="none" strokeDasharray={s.dash} transform={`rotate(${s.rot} ${x} ${y})`} strokeLinecap="round" />)}
            <circle cx={x} cy={y} r={ringR} stroke="#E8FCFF" strokeWidth={4} fill="none" opacity={0.8} />
          </g></g>
        )}
        {rg > RD && rg <= RD + BD && Array.from({ length: NB }).map((_, i) => {
          const k = (rg - RD) / BD;
          const a0 = (i / NB) * 360 + random(`fa${i}`) * 12;
          const span = 14 + random(`fs${i}`) * 10;
          const r = P.ringR1 + k * (70 + random(`fr${i}`) * 90);
          const rad = (v: number) => (v * Math.PI) / 180;
          const p1 = [x + r * Math.cos(rad(a0)), y + r * Math.sin(rad(a0))], p2 = [x + r * Math.cos(rad(a0 + span * (1 - 0.6 * k))), y + r * Math.sin(rad(a0 + span * (1 - 0.6 * k)))];
          return <path key={i} d={`M${p1[0]},${p1[1]} A${r},${r} 0 0 1 ${p2[0]},${p2[1]}`} stroke={ringColor} strokeWidth={10 * (1 - k) + 3} strokeDasharray="2 14" strokeLinecap="round" fill="none" opacity={1 - k} />;
        })}
      </svg>
      {f >= bigAt && (() => {
        const gb = f - bigAt;
        const bs = kf(gb, 0, [0, 3], [P.bigStart, 1.0], Easing.out(Easing.quad));
        const bo = kf(gb, 0, [0, 3], [0.5, 1]);
        const txt = (s: number, o: number) => <div style={{ position: "absolute", left: 0, width: W, top: y, transform: `translateY(-50%) scale(${s})`, transformOrigin: `${x}px 50%`, textAlign: "center", fontFamily: "NeoHv", fontSize: bigSize, color: textColor, opacity: o, lineHeight: 1, whiteSpace: "nowrap", letterSpacing: -6 }}>{hz(big)}</div>;
        const ghostG = gb - P.ghostDelay;
        return <>{ghostG >= 0 && ghostG < 5 && txt(1.1 + ghostG * 0.01, kf(ghostG, 0, [0, 1, 5], [0.55, 0.4, 0]))}{txt(bs, bo)}</>;
      })()}
    </AbsoluteFill>
  );
};

// ══ 6. 네온 타일 ═════════════════════════════════════════════════════════
// 240×240 타일 4모서리 꽝(1.8x α0.4 → 1.0, 6f, 5f 스태거, TL→TR→BL→BR) → 불규칙 네온 깜빡임(α0.6↔1, 2~8f)
export const NeonTilesParams = z.object({
  stagger: num(5, 0, 30, 1, "타일 스태거 간격", "timing", "f"),
  slamDur: num(6, 1, 30, 1, "꽝 착지 길이", "timing", "f"),
  slamScale: num(1.8, 1, 4, 0.05, "착지 시작 크기(배)", "motion", "배"),
  undershoot: num(0.96, 0.7, 1, 0.01, "착지 눌림 크기(배)", "motion", "배"),
  flickerDelay: num(8, 0, 60, 1, "깜빡임 시작 지연", "timing", "f"),
  flickerMin: num(2, 1, 30, 1, "깜빡임 최소 간격", "timing", "f"),
  flickerMax: num(8, 1, 60, 1, "깜빡임 최대 간격", "timing", "f"),
  offChance: num(0.35, 0, 1, 0.05, "꺼질 확률", "motion"),
  dimOpacity: num(0.6, 0, 1, 0.05, "꺼졌을 때 불투명도", "look"),
  glow: num(24, 0, 80, 1, "네온 글로우 세기", "look", "px"),
  margin: num(90, 0, 300, 5, "화면 가장자리 여백", "size", "px"),
  tile: num(240, 80, 420, 5, "타일 크기", "size", "px"),
  fontSize: num(170, 40, 300, 5, "글자 크기", "size", "px"),
});
export type NeonTilesP = z.infer<typeof NeonTilesParams>;
export const NeonTiles: React.FC<{ letters: string[]; at: number; colors?: string[]; margin?: number; tile?: number; stagger?: number; p?: Partial<NeonTilesP> }> = ({ letters, at, colors = ["#FF3B3B", "#2EE66B", "#3B7BFF", "#FF9A1F"], margin: margin0, tile: tile0, stagger: stagger0, p }) => {
  const P = def(NeonTilesParams, { ...defined({ margin: margin0, tile: tile0, stagger: stagger0 }), ...p });
  const { margin, tile, stagger } = P;
  const f = useCurrentFrame();
  if (f < at) return null;
  const corners: P[] = [[margin, margin], [W - margin - tile, margin], [margin, H - margin - tile], [W - margin - tile, H - margin - tile]];
  const SD = P.slamDur, fMin = Math.max(1, Math.round(P.flickerMin)), fSpan = Math.max(0, Math.round(P.flickerMax) - fMin) + 1;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {letters.slice(0, 4).map((l, i) => {
        const a = at + i * stagger;
        if (f < a) return null;
        const s = kf(f, a, [0, (SD * 2) / 3, SD], [P.slamScale, P.undershoot, 1.0], Easing.out(Easing.quad));
        let op = kf(f, a, [0, SD / 2, SD], [0.4, 0.75, 1.0]);
        if (f >= a + P.flickerDelay) {
          // 결정론 깜빡임 스케줄
          let t = a + P.flickerDelay, k = 0, on = true;
          while (t <= f) { const len = fMin + Math.floor(random(`nf${i}-${k}`) * fSpan); if (f < t + len) break; t += len; k++; }
          on = random(`no${i}-${k}`) > P.offChance;
          op = on ? 1 : P.dimOpacity;
        }
        const c = colors[i % colors.length];
        const [x, y] = corners[i];
        return (
          <div key={i} style={{ position: "absolute", left: x, top: y, width: tile, height: tile, transform: `scale(${s})`, opacity: op, borderRadius: 16, background: c, boxShadow: `0 0 ${P.glow}px ${c}, 0 0 ${P.glow * 2.5}px ${c}88`, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <div style={{ position: "absolute", inset: 14, borderRadius: 10, border: "6px solid rgba(255,255,255,0.95)", boxShadow: `inset 0 0 12px ${c}` }} />
            <div style={{ fontFamily: "NeoHv", fontSize: P.fontSize, color: "#fff", lineHeight: 1, marginTop: 10, textShadow: `0 0 18px #fff, 0 0 30px ${c}` }}>{l}</div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// ══ 7. A < B 비교 ════════════════════════════════════════════════════════
export const CompareABParams = z.object({
  signDelay: num(16, 0, 60, 1, "부등호 등장 지연", "timing", "f"),
  bDelay: num(22, 0, 80, 1, "B pill 등장 지연", "timing", "f"),
  popDur: num(6, 1, 20, 1, "pill 팝 길이", "timing", "f"),
  popStart: num(0.3, 0, 1, 0.05, "pill 시작 크기(배)", "motion", "배"),
  popOver: num(1.25, 1, 1.8, 0.01, "오버슈트 크기(배)", "motion", "배"),
  blur0: num(20, 0, 60, 1, "가로 모션블러 세기", "look", "px"),
  spread: num(420, 150, 900, 10, "pill 좌우 거리", "size", "px"),
  size: num(80, 24, 160, 2, "pill 글자 크기", "size", "px"),
  signSize: num(200, 60, 400, 5, "부등호 크기", "size", "px"),
  color: col("#E8521E", "pill 색"),
  signColor: col("#fff", "부등호 색"),
});
export type CompareABP = z.infer<typeof CompareABParams>;
export const CompareAB: React.FC<{ a: string; b: string; at: number; x?: number; y?: number; color?: string; spread?: number; size?: number; sign?: string; bDelay?: number; p?: Partial<CompareABP> }> = ({ a, b, at, x = W / 2, y = H / 2, color: color0, spread: spread0, size: size0, sign = "<", bDelay: bDelay0, p }) => {
  const P = def(CompareABParams, { ...defined({ color: color0, spread: spread0, size: size0, bDelay: bDelay0 }), ...p });
  const { color, spread, size, bDelay } = P;
  const f = useCurrentFrame();
  if (f < at) return null;
  const ks = [0, P.popDur / 2, P.popDur], vs = [P.popStart, P.popOver, 1.0];
  const ca = at + P.signDelay;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <PopPill text={a} x={x - spread} y={y} f={f} at={at} color={color} size={size} ks={ks} vs={vs} blur0={P.blur0} />
      {f >= ca && <div style={{ position: "absolute", left: x, top: y, transform: `translate(-50%,-52%) scale(${kf(f, ca, [0, 2, 3], [0.3, 1.2, 1.0])})`, fontFamily: "NeoHv", fontSize: P.signSize, color: P.signColor, lineHeight: 1, textShadow: "0 6px 10px rgba(0,0,0,0.35)" }}>{sign}</div>}
      <PopPill text={b} x={x + spread} y={y} f={f} at={at + bDelay} color={color} size={size} ks={ks} vs={vs} blur0={P.blur0} />
    </AbsoluteFill>
  );
};

// ══ 8. 타이틀 박스 ═══════════════════════════════════════════════════════
// 검정 그라데이션 박스(가운데 85% → 좌우 15% 구간에서 0) 가로 중앙→바깥 클립 8f easeOut, 1.3s 후 2줄 부제 박스 세로 중앙→바깥 10f
export const TitleBoxParams = z.object({
  openDur: num(8, 1, 40, 1, "제목 박스 펼침 길이", "timing", "f"),
  subDelay: num(39, 0, 120, 1, "부제 박스 등장 지연", "timing", "f"),
  subOpenDur: num(10, 1, 40, 1, "부제 박스 펼침 길이", "timing", "f"),
  w: num(1500, 600, 1920, 10, "박스 폭", "size", "px"),
  boxH: num(200, 80, 400, 5, "제목 박스 높이", "size", "px"),
  size: num(96, 30, 180, 2, "제목 글자 크기", "size", "px"),
  subSize: num(50, 20, 100, 2, "부제 글자 크기", "size", "px"),
  darkness: num(0.85, 0, 1, 0.05, "박스 어둡기(불투명도)", "look"),
  fadeEdge: num(15, 0, 50, 1, "좌우 페이드 폭(%)", "look", "%"),
});
export type TitleBoxP = z.infer<typeof TitleBoxParams>;
export const TitleBox: React.FC<{ title: string; sub?: [string, string] | string[]; at: number; subAt?: number; y?: number; w?: number; size?: number; subSize?: number; p?: Partial<TitleBoxP> }> = ({ title, sub, at, subAt, y = 380, w: w0, size: size0, subSize: subSize0, p }) => {
  const P = def(TitleBoxParams, { ...defined({ w: w0, size: size0, subSize: subSize0 }), ...p });
  const { w, size, subSize } = P;
  const f = useCurrentFrame();
  if (f < at) return null;
  const grad = `linear-gradient(90deg, rgba(0,0,0,0) 0%, rgba(0,0,0,${P.darkness}) ${P.fadeEdge}%, rgba(0,0,0,${P.darkness}) ${100 - P.fadeEdge}%, rgba(0,0,0,0) 100%)`;
  const k = lerp(f, at, at + P.openDur, 0, 50, Easing.out(Easing.cubic));
  const sa = subAt ?? at + P.subDelay;
  const k2 = lerp(f, sa, sa + P.subOpenDur, 0, 50, Easing.out(Easing.cubic));
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div style={{ position: "absolute", left: (W - w) / 2, top: y - P.boxH / 2, width: w, height: P.boxH, background: grad, clipPath: `inset(0 ${50 - k}% 0 ${50 - k}%)`, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "NeoHv", fontSize: size, color: "#fff", whiteSpace: "nowrap" }}>{hz(title)}</div>
      {sub && f >= sa && <div style={{ position: "absolute", left: (W - w * 0.85) / 2, top: y + 140, width: w * 0.85, height: 190, background: grad, clipPath: `inset(${50 - k2}% 0 ${50 - k2}% 0)`, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 6, fontFamily: "NeoEb", fontSize: subSize, color: "#fff", lineHeight: 1.25 }}>{sub.map((s, i) => <div key={i}>{hz(s)}</div>)}</div>}
    </AbsoluteFill>
  );
};

// ══ 9. 스크림 + 타자기 ═══════════════════════════════════════════════════
// 검정 70% 스크림 10f → 좌상단 제목(64px) 16f 페이드 → +20f 부제 1.4f/글자 타이핑 → Ø110 배지 15f 간격 팝
export const ScrimTypewriterParams = z.object({
  scrimDur: num(10, 1, 40, 1, "스크림 어두워지는 길이", "timing", "f"),
  scrimOpacity: num(0.7, 0, 1, 0.05, "스크림 어둡기", "look"),
  titleDelay: num(8, 0, 40, 1, "제목 등장 지연", "timing", "f"),
  titleFade: num(16, 1, 60, 1, "제목 페이드 길이", "timing", "f"),
  typeDelay: num(20, 0, 80, 1, "제목 후 타이핑 시작 지연", "timing", "f"),
  charF: num(1.4, 0.2, 8, 0.1, "글자당 타이핑 시간", "timing", "f"),
  badgeDelay: num(10, 0, 60, 1, "타이핑 후 배지 지연", "timing", "f"),
  badgeStagger: num(15, 0, 40, 1, "배지 스태거 간격", "timing", "f"),
  badgeOver: num(1.15, 1, 1.6, 0.01, "배지 오버슈트 크기(배)", "motion", "배"),
  titleSize: num(64, 24, 140, 2, "제목 글자 크기", "size", "px"),
  subSize: num(42, 16, 90, 1, "부제 글자 크기", "size", "px"),
  badgeSize: num(110, 40, 220, 2, "배지 지름", "size", "px"),
});
export type ScrimTypewriterP = z.infer<typeof ScrimTypewriterParams>;
export const ScrimTypewriter: React.FC<{ title: string; sub: string; at: number; badges?: { label: string; color: string }[]; x?: number; y?: number; p?: Partial<ScrimTypewriterP> }> = ({ title, sub, at, badges = [], x = 120, y = 140, p }) => {
  const P = def(ScrimTypewriterParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const cf = Math.max(0.1, P.charF);
  const tAt = at + P.titleDelay, sAt = tAt + P.typeDelay;
  const n = Math.max(0, Math.min(sub.length, Math.floor((f - sAt) / cf) + 1));
  const bAt = sAt + Math.ceil(sub.length * cf) + P.badgeDelay;
  const bs = P.badgeSize;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <AbsoluteFill style={{ background: "#000", opacity: lerp(f, at, at + P.scrimDur, 0, P.scrimOpacity, Easing.linear) }} />
      <div style={{ position: "absolute", left: x, top: y, opacity: lerp(f, tAt, tAt + P.titleFade, 0, 1, Easing.linear), fontFamily: "NeoHv", fontSize: P.titleSize, color: "#fff", whiteSpace: "nowrap" }}>{hz(title)}</div>
      {f >= sAt && <div style={{ position: "absolute", left: x, top: y + 100, maxWidth: 1400, fontFamily: "NeoEb", fontSize: P.subSize, color: "#E8E8E8", lineHeight: 1.5 }}>
        <span>{sub.slice(0, n)}</span>{n < sub.length && <span style={{ display: "inline-block", width: 4, height: P.subSize, marginLeft: 4, background: "#fff", verticalAlign: "-6px", opacity: Math.floor(f / 4) % 2 ? 1 : 0.2 }} /> }<span style={{ opacity: 0 }}>{sub.slice(n)}</span>
      </div>}
      {badges.map((b, i) => {
        const a = bAt + i * P.badgeStagger;
        if (f < a) return null;
        const s = kf(f, a, [0, 3, 5], [0, P.badgeOver, 1.0], Easing.out(Easing.quad));
        return <div key={i} style={{ position: "absolute", left: x + i * (bs + 40), top: y + 300, width: bs, height: bs, borderRadius: "50%", background: b.color, transform: `scale(${s})`, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "NeoHv", fontSize: 30, color: "#fff", boxShadow: "0 6px 14px rgba(0,0,0,0.45)", border: "4px solid rgba(255,255,255,0.9)", boxSizing: "border-box", textAlign: "center", lineHeight: 1.05 }}>{hz(b.label)}</div>;
      })}
    </AbsoluteFill>
  );
};

// ══ 10. 화이트보드 ═══════════════════════════════════════════════════════
export const WhiteboardParams = z.object({
  popDur: num(7, 1, 30, 1, "보드 팝 길이", "timing", "f"),
  startScale: num(0.6, 0, 1, 0.05, "보드 시작 크기(배)", "motion", "배"),
  popOver: num(1.03, 1, 1.3, 0.01, "보드 오버슈트 크기(배)", "motion", "배"),
  titleDelay: num(10, 0, 60, 1, "제목 쓰기 시작 지연", "timing", "f"),
  wipe: num(22, 1, 80, 1, "한 줄 쓰는 시간", "timing", "f"),
  titleRot: num(-1.5, -10, 10, 0.5, "제목 기울기", "motion", "°"),
  lineTilt: num(1.6, 0, 8, 0.1, "줄 기울기 흔들림 폭", "motion", "°"),
  titleSize: num(88, 30, 160, 2, "제목 글자 크기", "size", "px"),
  lineSize: num(62, 24, 120, 2, "본문 글자 크기", "size", "px"),
  lineGap: num(100, 40, 200, 2, "줄 간격", "size", "px"),
  frame: num(16, 0, 40, 1, "보드 테두리 두께", "size", "px"),
  titleColor: col("#D62828", "제목 마커 색"),
  inkColor: col("#1C1C1C", "본문 마커 색"),
});
export type WhiteboardP = z.infer<typeof WhiteboardParams>;
export const Whiteboard: React.FC<{ x: number; y: number; w: number; h: number; at: number; title: string; titleAt?: number; lines: { text: string; at: number }[]; wipe?: number; p?: Partial<WhiteboardP> }> = ({ x, y, w, h, at, title, titleAt, lines, wipe: wipe0, p }) => {
  const P = def(WhiteboardParams, { ...defined({ wipe: wipe0 }), ...p });
  const wipe = P.wipe;
  const f = useCurrentFrame();
  if (f < at) return null;
  const s = kf(f, at, [0, (P.popDur * 4) / 7, P.popDur], [P.startScale, P.popOver, 1.0], Easing.out(Easing.quad));
  const wipeK = (a: number, d: number) => lerp(f, a, a + d, 0, 100, Easing.inOut(Easing.sin));
  const ta = titleAt ?? at + P.titleDelay;
  return (
    <div style={{ position: "absolute", left: x, top: y, width: w, height: h, transform: `scale(${s})`, opacity: kf(f, at, [0, 3], [0, 1]) }}>
      <div style={{ position: "absolute", inset: 0, background: "#FBFBF8", border: `${P.frame}px solid #B9BEC4`, borderRadius: 14, boxShadow: "0 16px 30px rgba(0,0,0,0.35), inset 0 0 40px rgba(0,0,0,0.05)" }} />
      <div style={{ position: "absolute", left: w * 0.2, width: w * 0.6, bottom: -30, height: 22, background: "#9AA0A7", borderRadius: 6 }} />
      {[["#D62828", 0.26], ["#1C1C1C", 0.34], ["#1F5FBF", 0.4]].map(([c, p], i) => <div key={i} style={{ position: "absolute", left: w * (p as number), bottom: -22, width: 70, height: 14, borderRadius: 7, background: c as string }} />)}
      {f >= ta && <div style={{ position: "absolute", left: 70, top: 44, fontFamily: "Yeonsung", fontSize: P.titleSize, color: P.titleColor, whiteSpace: "nowrap", clipPath: `inset(-20px ${100 - wipeK(ta, wipe)}% -20px 0)`, transform: `rotate(${P.titleRot}deg)` }}>{hz(title)}</div>}
      {lines.map((l, i) => f >= l.at && (
        <div key={i} style={{ position: "absolute", left: 90, top: 190 + i * P.lineGap, fontFamily: "Yeonsung", fontSize: P.lineSize, color: P.inkColor, whiteSpace: "nowrap", clipPath: `inset(-20px ${100 - wipeK(l.at, wipe)}% -20px 0)`, transform: `rotate(${(random(`wb${i}`) - 0.5) * P.lineTilt}deg)` }}>{hz(l.text)}</div>
      ))}
    </div>
  );
};

// ══ 11. 빨간 박스 깜빡임 + 파란 pill ══════════════════════════════════════
// #E00000 6px 사각 테두리 16f ON / 12f OFF ×2 → 유지, 이후 오른쪽 파란 pill 3개 가로블러 스태거 팝
export const RedBoxBlinkParams = z.object({
  onF: num(16, 1, 60, 1, "켜짐 길이", "timing", "f"),
  offF: num(12, 0, 60, 1, "꺼짐 길이", "timing", "f"),
  blinks: num(2, 0, 8, 1, "깜빡임 횟수", "motion"),
  pillsDelay: num(60, 0, 150, 1, "pill 등장 지연", "timing", "f"),
  pillStagger: num(5, 0, 30, 1, "pill 스태거 간격", "timing", "f"),
  popOver: num(1.1, 1, 1.6, 0.01, "pill 오버슈트 크기(배)", "motion", "배"),
  blur0: num(16, 0, 60, 1, "pill 가로 모션블러", "look", "px"),
  lineWidth: num(6, 1, 24, 1, "박스 선 두께", "size", "px"),
  pillGap: num(120, 60, 250, 2, "pill 세로 간격", "size", "px"),
  pillSize: num(48, 20, 100, 2, "pill 글자 크기", "size", "px"),
  color: col("#E00000", "박스 색"),
  pillColor: col("#1FA3D6", "pill 색"),
});
export type RedBoxBlinkP = z.infer<typeof RedBoxBlinkParams>;
export const RedBoxBlink: React.FC<{ rect: [number, number, number, number]; at: number; pills?: string[]; pillsX?: number; pillsY?: number; pillGap?: number; pillsAt?: number; color?: string; pillColor?: string; p?: Partial<RedBoxBlinkP> }> = ({ rect, at, pills = [], pillsX, pillsY, pillGap: pillGap0, pillsAt, color: color0, pillColor: pillColor0, p }) => {
  const P = def(RedBoxBlinkParams, { ...defined({ pillGap: pillGap0, color: color0, pillColor: pillColor0 }), ...p });
  const { pillGap, color, pillColor } = P;
  const f = useCurrentFrame();
  if (f < at) return null;
  const g = f - at;
  const period = P.onF + P.offF;
  const on = Math.floor(g / period) >= P.blinks || g % period < P.onF;
  const [x, y, w, h] = rect;
  const pa = pillsAt ?? at + P.pillsDelay;
  const px = pillsX ?? x + w + 60, py = pillsY ?? y + 40;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {on && <div style={{ position: "absolute", left: x, top: y, width: w, height: h, border: `${P.lineWidth}px solid ${color}`, boxSizing: "border-box" }} />}
      {pills.map((t, i) => {
        const a = pa + i * P.pillStagger;
        if (f < a) return null;
        const s = kf(f, a, [0, 3, 5], [0.3, P.popOver, 1.0]);
        return <HBlur key={i} amt={kf(f, a, [0, 4], [P.blur0, 0])} style={{ position: "absolute", left: px, top: py + i * pillGap, transform: `scale(${s})`, transformOrigin: "0% 50%" }}><Pill text={t} color={pillColor} size={P.pillSize} /></HBlur>;
      })}
    </AbsoluteFill>
  );
};

// ══ 12. 손그림 동그라미 ══════════════════════════════════════════════════
// 빨간 마커가 약간 불규칙하게 1.15바퀴 겹쳐 도는 루프를 ~10f 에 스트로크 드로우
export const HandDrawnCircleParams = z.object({
  dur: num(10, 1, 60, 1, "그리기 길이", "timing", "f"),
  turns: num(1.15, 0.5, 3, 0.05, "감는 바퀴 수", "motion"),
  wobble: num(1, 0, 4, 0.1, "손떨림 세기(배)", "motion", "배"),
  flare: num(0.07, 0, 0.3, 0.01, "끝 벌어짐 비율", "motion"),
  width: num(9, 2, 30, 1, "마커 두께", "size", "px"),
  opacity: num(0.93, 0.1, 1, 0.01, "마커 불투명도", "look"),
  color: col("#E0201B", "마커 색"),
});
export type HandDrawnCircleP = z.infer<typeof HandDrawnCircleParams>;
export const HandDrawnCircle: React.FC<{ cx: number; cy: number; rx: number; ry: number; at: number; dur?: number; color?: string; width?: number; seed?: number; turns?: number; p?: Partial<HandDrawnCircleP> }> = ({ cx, cy, rx, ry, at, dur: dur0, color: color0, width: width0, seed = 1, turns: turns0, p }) => {
  const P = def(HandDrawnCircleParams, { ...defined({ dur: dur0, color: color0, width: width0, turns: turns0 }), ...p });
  const { dur, color, width, turns } = P;
  const f = useCurrentFrame();
  if (f < at) return null;
  const N = 90, pts: P[] = [];
  const t0 = -Math.PI * 0.62 + (random(`hc${seed}`) - 0.5) * 0.5;
  const ph = random(`hp${seed}`) * 6;
  for (let i = 0; i <= N; i++) {
    const u = i / N, th = t0 + u * Math.PI * 2 * turns;
    const wob = 1 + P.wobble * 0.035 * Math.sin(th * 3 + ph) + P.wobble * 0.02 * Math.sin(th * 5 + ph * 2) + P.flare * u; // 끝으로 갈수록 바깥으로 벌어져 겹침
    pts.push([cx + rx * wob * Math.cos(th) + 4 * u, cy + ry * wob * Math.sin(th) - 6 * u]);
  }
  const L = polyLen(pts);
  const k = lerp(f, at, at + dur, 0, L, Easing.out(Easing.quad));
  return (
    <svg width={W} height={H} style={{ position: "absolute", left: 0, top: 0, pointerEvents: "none" }}>
      <path d={dOf(polyUpTo(pts, k))} stroke={color} strokeWidth={width} fill="none" strokeLinecap="round" strokeLinejoin="round" opacity={P.opacity} />
    </svg>
  );
};

// ══ 13. 브라우저 목업 ════════════════════════════════════════════════════
export const CodeRainBg: React.FC<{ color?: string; base?: string; speed?: number }> = ({ color = "#35E07A", base = "#1A2560", speed = 1.2 }) => {
  const f = useCurrentFrame();
  const toks = ["<a href=", "</div>", "http://", "function()", "{ link: }", "var x=0;", "<html>", "GET /", "200 OK", "node.js", "=>", "return;", "<p>", "0x1F", "href", "www"];
  return (
    <AbsoluteFill style={{ background: base, overflow: "hidden" }}>
      <div style={{ position: "absolute", left: -600, top: -700, width: W + 1200, height: H + 1400, transform: `rotate(-24deg) translate(${(f * speed) % 600 - 300}px, ${(f * speed * 0.5) % 60}px)`, opacity: 0.13, fontFamily: "Menlo, monospace", fontSize: 26, color, lineHeight: "60px", whiteSpace: "nowrap" }}>
        {Array.from({ length: 42 }).map((_, r) => <div key={r}>{Array.from({ length: 30 }).map((__, c) => toks[Math.floor(random(`cr${r}-${c}`) * toks.length)]).join("  ")}</div>)}
      </div>
    </AbsoluteFill>
  );
};
const Cursor: React.FC<{ x: number; y: number; s?: number }> = ({ x, y, s = 1 }) => (
  <svg width={46} height={60} viewBox="0 0 46 60" style={{ position: "absolute", left: x - 4, top: y - 2, transform: `scale(${s})`, transformOrigin: "4px 2px", filter: "drop-shadow(0 3px 3px rgba(0,0,0,0.4))" }}>
    <path d="M4,2 L4,46 L15,36 L23,55 L31,51 L23,33 L38,33 Z" fill="#fff" stroke="#111" strokeWidth={3} strokeLinejoin="round" />
  </svg>
);
export const BrowserMockupParams = z.object({
  riseDist: num(200, 0, 600, 10, "창 떠오르는 거리", "motion", "px"),
  riseDur: num(6, 1, 30, 1, "창 떠오르는 길이", "timing", "f"),
  fadeDur: num(4, 1, 20, 1, "창 페이드인 길이", "timing", "f"),
  typeDelay: num(8, 0, 60, 1, "주소 타이핑 시작 지연", "timing", "f"),
  charF: num(4, 0.5, 12, 0.5, "글자당 타이핑 시간", "timing", "f"),
  contentDelay: num(6, 0, 60, 1, "타이핑 후 내용 등장 지연", "timing", "f"),
  nodeStagger: num(2, 0, 12, 1, "(그래프) 문서 노드 스태거", "timing", "f"),
  nodeOver: num(1.15, 1, 1.6, 0.01, "(그래프) 노드 오버슈트(배)", "motion", "배"),
  edgeDarken: num(15, 1, 60, 1, "(그래프) 링크 진해지는 길이", "timing", "f"),
  cursorDur: num(22, 1, 60, 1, "(쇼핑) 커서 이동 길이", "timing", "f"),
  clickDelay: num(32, 4, 120, 1, "(쇼핑) 내용 후 클릭 시점", "timing", "f"),
  rippleDur: num(14, 1, 40, 1, "(쇼핑) 클릭 파문 길이", "timing", "f"),
  rippleSize: num(80, 20, 200, 2, "(쇼핑) 클릭 파문 반지름", "size", "px"),
  radius: num(16, 0, 60, 1, "창 모서리 둥글기", "size", "px"),
});
export type BrowserMockupP = z.infer<typeof BrowserMockupParams>;
export const BrowserMockup: React.FC<{
  at: number; url: string; mode: "graph" | "shop"; x?: number; y?: number; w?: number; h?: number; tab?: string; typeAt?: number; contentAt?: number;
  shop?: { img: string; name: string; price: string }[]; p?: Partial<BrowserMockupP>;
}> = ({ at, url, mode, x = W / 2, y = H / 2 + 20, w = 1150, h = 800, tab = "새 탭", typeAt, contentAt, shop = [], p }) => {
  const P = def(BrowserMockupParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const ty = lerp(f, at, at + P.riseDur, P.riseDist, 0, Easing.out(Easing.cubic));
  const op = lerp(f, at, at + P.fadeDur, 0, 1);
  const ta = typeAt ?? at + P.typeDelay;
  const cf = Math.max(0.1, P.charF);
  const nChar = Math.max(0, Math.min(url.length, Math.floor((f - ta) / cf) + 1));
  const ca = contentAt ?? ta + url.length * cf + P.contentDelay;
  const cw = w, ch = h - 120;
  let content: React.ReactNode = null;
  if (mode === "graph") {
    const nodes: P[] = [[180, 150], [470, 110], [800, 170], [990, 330], [300, 360], [620, 330], [180, 560], [520, 560], [850, 540]];
    const edges: [number, number][] = [[0, 1], [1, 2], [2, 3], [0, 4], [4, 5], [1, 5], [5, 3], [4, 6], [6, 7], [5, 7], [7, 8], [3, 8]];
    const ea = ca + nodes.length * P.nodeStagger + 6;
    const eop = lerp(f, ea, ea + 4, 0, 0.5);
    const dk = lerp(f, ea + 8, ea + 8 + P.edgeDarken, 0, 1);
    const col = `rgb(${Math.round(150 * (1 - dk))},${Math.round(150 * (1 - dk))},${Math.round(150 * (1 - dk))})`;
    content = (
      <>
        <svg width={cw} height={ch} style={{ position: "absolute", left: 0, top: 0, opacity: dk > 0 ? 0.5 + 0.5 * dk : eop }}>
          {f >= ea && edges.map(([a, b], i) => {
            const [x1, y1] = nodes[a], [x2, y2] = nodes[b];
            const len = Math.hypot(x2 - x1, y2 - y1), ux = (x2 - x1) / len, uy = (y2 - y1) / len;
            const sx = x1 + ux * 62, sy = y1 + uy * 62, ex = x2 - ux * 62, ey = y2 - uy * 62;
            const ang = (Math.atan2(uy, ux) * 180) / Math.PI;
            return <g key={i}><path d={`M${sx},${sy} L${ex},${ey}`} stroke={col} strokeWidth={5} /><path d="M0,0 L-20,-11 L-20,11 Z" fill={col} transform={`translate(${ex},${ey}) rotate(${ang})`} /></g>;
          })}
        </svg>
        {nodes.map(([nx, ny], i) => {
          const a = ca + i * P.nodeStagger;
          if (f < a) return null;
          const s = kf(f, a, [0, 3, 5], [0, P.nodeOver, 1.0]);
          return <div key={i} style={{ position: "absolute", left: nx - 50, top: ny - 55, width: 100, height: 110, transform: `scale(${s})` }}><Icon name="doc" color={["#2F6BD8", "#E8521E", "#2FA84F"][i % 3]} /></div>;
        })}
      </>
    );
  } else {
    const click = ca + P.clickDelay;
    const mv = lerp(f, click - 2 - P.cursorDur, click - 2, 0, 1, Easing.inOut(Easing.cubic));
    const btn: P = [cw - 190, 80 + 110];
    const cx0 = cw * 0.45, cy0 = ch - 60;
    const cx = cx0 + (btn[0] - cx0) * mv, cy = cy0 + (btn[1] - cy0) * mv;
    const pressed = f >= click && f < click + 4;
    const added = f >= click + 2;
    content = (
      <>
        {shop.slice(0, 2).map((it, i) => {
          const a = ca + i * 5;
          if (f < a) return null;
          const on = i === 0 && added;
          return (
            <div key={i} style={{ position: "absolute", left: 40, top: 80 + i * 250, width: cw - 80, height: 220, opacity: lerp(f, a, a + 6, 0, 1), transform: `translateY(${lerp(f, a, a + 6, 20, 0, QUART_OUT)}px)`, borderBottom: "2px solid #E3E3E3", display: "flex", alignItems: "center", gap: 36 }}>
              <div style={{ width: 180, height: 180, borderRadius: 14, overflow: "hidden", background: "#eee", flex: "none" }}><Img src={src(it.img)} style={{ width: "100%", height: "100%", objectFit: "cover" }} /></div>
              <div style={{ flex: 1 }}>
                <div style={{ fontFamily: "NeoEb", fontSize: 44, color: "#222" }}>{hz(it.name)}</div>
                <div style={{ fontFamily: "NeoHv", fontSize: 50, color: "#E0301E", marginTop: 12 }}>{it.price}</div>
              </div>
              <div style={{ width: 170, height: 76, borderRadius: 12, background: on ? "#2FA84F" : "#1F6FE0", color: "#fff", fontFamily: "NeoHv", fontSize: 38, display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${i === 0 && pressed ? 0.9 : 1})`, flex: "none" }}>{on ? "담김 ✓" : "담기"}</div>
            </div>
          );
        })}
        {f >= click && f < click + P.rippleDur && (() => { const r = lerp(f, click, click + P.rippleDur, 10, P.rippleSize); return <div style={{ position: "absolute", left: btn[0] - r, top: btn[1] - r, width: r * 2, height: r * 2, borderRadius: "50%", border: `5px solid rgba(31,111,224,${lerp(f, click, click + P.rippleDur, 0.8, 0)})` }} />; })()}
        {f >= ca + 4 && <Cursor x={cx} y={cy} s={pressed ? 0.88 : 1} />}
        {added && <div style={{ position: "absolute", right: 40, top: 14, width: 60, height: 60 }}><Icon name="cart" color="#333" /><div style={{ position: "absolute", right: -12, top: -10, width: 34, height: 34, borderRadius: "50%", background: "#E0301E", color: "#fff", fontFamily: "NeoHv", fontSize: 22, display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${kf(f, click + 2, [0, 3, 5], [0, 1.3, 1])})` }}>1</div></div>}
      </>
    );
  }
  return (
    <div style={{ position: "absolute", left: x - w / 2, top: y - h / 2, width: w, height: h, transform: `translateY(${ty}px)`, opacity: op, borderRadius: P.radius, overflow: "hidden", background: "#fff", boxShadow: "0 30px 60px rgba(0,0,0,0.5)" }}>
      <div style={{ position: "absolute", left: 0, top: 0, width: w, height: 56, background: "#DEE1E6" }}>
        {["#FF5F57", "#FEBC2E", "#28C840"].map((c, i) => <div key={i} style={{ position: "absolute", left: 22 + i * 28, top: 20, width: 16, height: 16, borderRadius: "50%", background: c }} />)}
        <div style={{ position: "absolute", left: 120, top: 10, width: 280, height: 46, background: "#fff", borderRadius: "12px 12px 0 0", fontFamily: "NeoEb", fontSize: 22, color: "#333", display: "flex", alignItems: "center", paddingLeft: 20, boxSizing: "border-box" }}>{tab}<span style={{ marginLeft: "auto", marginRight: 16, color: "#888" }}>×</span></div>
      </div>
      <div style={{ position: "absolute", left: 0, top: 56, width: w, height: 64, background: "#fff", borderBottom: "1px solid #ddd", display: "flex", alignItems: "center", gap: 18, paddingLeft: 24, boxSizing: "border-box", fontFamily: "NeoEb", fontSize: 28, color: "#777" }}>
        <span>←</span><span>→</span><span>⟳</span>
        <div style={{ flex: 1, marginRight: 24, height: 44, borderRadius: 22, background: "#F1F3F4", display: "flex", alignItems: "center", paddingLeft: 22, fontFamily: "Menlo, monospace", fontSize: 26, color: "#202124" }}>
          {url.slice(0, nChar)}{f >= ta && f < ca + 20 && <span style={{ display: "inline-block", width: 2, height: 28, background: "#202124", marginLeft: 2, opacity: Math.floor(f / 5) % 2 ? 1 : 0 }} />}
        </div>
      </div>
      <div style={{ position: "absolute", left: 0, top: 120, width: cw, height: ch, background: mode === "graph" ? "#F7F8FB" : "#fff", overflow: "hidden" }}>{content}</div>
    </div>
  );
};

// ══ 14. 스크린샷 그리드 / 캐러셀 ══════════════════════════════════════════
const ShotCard: React.FC<{ img: string; label: string; w: number; h: number; style?: React.CSSProperties; tabColor?: string }> = ({ img, label, w, h, style, tabColor = "#2FA84F" }) => (
  <div style={{ position: "absolute", width: w, height: h, ...style }}>
    <div style={{ position: "absolute", inset: 0, border: "5px solid #fff", borderRadius: 4, overflow: "hidden", background: "#333", boxShadow: "0 8px 18px rgba(0,0,0,0.5)" }}><Img src={src(img)} style={{ width: "100%", height: "100%", objectFit: "cover" }} /></div>
    <div style={{ position: "absolute", left: 0, top: -Math.round(h * 0.2), background: tabColor, color: "#fff", fontFamily: "NeoHv", fontSize: Math.max(18, Math.round(h * 0.14)), padding: "4px 12px 2px", borderRadius: "6px 6px 0 0", whiteSpace: "nowrap" }}>{hz(label)}</div>
  </div>
);
export const ScreenshotGridParams = z.object({
  flashIn: num(4, 1, 20, 1, "흰 플래시 올라오는 길이", "timing", "f"),
  flashHold: num(6, 0, 30, 1, "흰 플래시 유지", "timing", "f"),
  flashOut: num(10, 1, 40, 1, "흰 플래시 빠지는 길이", "timing", "f"),
  cardsDelay: num(20, 0, 80, 1, "첫 카드 등장 지연", "timing", "f"),
  step: num(15, 0, 40, 1, "카드 스태거 간격", "timing", "f"),
  cardFade: num(7, 1, 30, 1, "카드 페이드 길이", "timing", "f"),
  cardStart: num(0.92, 0.3, 1.5, 0.01, "카드 시작 크기(배)", "motion", "배"),
  cols: num(4, 1, 8, 1, "열 개수", "size"),
  cw: num(220, 80, 500, 5, "카드 폭", "size", "px"),
  ch: num(150, 60, 400, 5, "카드 높이", "size", "px"),
  gap: num(44, 0, 120, 2, "카드 간격", "size", "px"),
  bg: col("#15181D", "배경 색"),
});
export type ScreenshotGridP = z.infer<typeof ScreenshotGridParams>;
export const ScreenshotGrid: React.FC<{ items: { img: string; label: string }[]; at: number; cols?: number; cw?: number; ch?: number; gap?: number; cy?: number; bg?: string; step?: number; p?: Partial<ScreenshotGridP> }> = ({ items, at, cols: cols0, cw: cw0, ch: ch0, gap: gap0, cy = H / 2, bg: bg0, step: step0, p }) => {
  const P = def(ScreenshotGridParams, { ...defined({ cols: cols0, cw: cw0, ch: ch0, gap: gap0, bg: bg0, step: step0 }), ...p });
  const { cw, ch, gap, bg, step } = P;
  const cols = Math.max(1, Math.round(P.cols));
  const f = useCurrentFrame();
  if (f < at) return null;
  const g = f - at;
  const FI = P.flashIn, FH = FI + P.flashHold;
  const white = g < FI ? g / FI : g < FH ? 1 : lerp(g, FH, FH + P.flashOut, 1, 0, Easing.linear);
  const rows = Math.ceil(items.length / cols);
  const gw = cols * cw + (cols - 1) * gap, gh = rows * ch + (rows - 1) * (gap + ch * 0.2);
  const x0 = (W - gw) / 2, y0 = cy - gh / 2;
  return (
    <AbsoluteFill>
      {g >= FI && <AbsoluteFill style={{ background: bg }} />}
      {items.map((it, i) => {
        const a = at + P.cardsDelay + i * step;
        if (f < a) return null;
        const c = i % cols, r = Math.floor(i / cols);
        return <ShotCard key={i} img={it.img} label={it.label} w={cw} h={ch} style={{ left: x0 + c * (cw + gap), top: y0 + r * (ch + gap + ch * 0.2), opacity: lerp(f, a, a + P.cardFade, 0, 1), transform: `scale(${lerp(f, a, a + P.cardFade, P.cardStart, 1)})` }} />;
      })}
      {white > 0 && <AbsoluteFill style={{ background: "#fff", opacity: white }} />}
    </AbsoluteFill>
  );
};
export const ScreenshotCarouselParams = z.object({
  speed: num(25, -200, 400, 1, "흐르는 속도(px/초)", "motion", "px"),
  startX: num(80, -1000, 1000, 10, "시작 위치 X", "motion", "px"),
  fadeStagger: num(3, 0, 20, 1, "카드 페이드 스태거", "timing", "f"),
  fadeDur: num(8, 1, 40, 1, "카드 페이드 길이", "timing", "f"),
  cw: num(400, 120, 800, 5, "카드 폭", "size", "px"),
  ch: num(300, 80, 600, 5, "카드 높이", "size", "px"),
  gap: num(30, 0, 150, 2, "카드 간격", "size", "px"),
});
export type ScreenshotCarouselP = z.infer<typeof ScreenshotCarouselParams>;
export const ScreenshotCarousel: React.FC<{ items: { img: string; label: string }[]; at?: number; y?: number; cw?: number; ch?: number; gap?: number; speed?: number; startX?: number; p?: Partial<ScreenshotCarouselP> }> = ({ items, at = 0, y = 390, cw: cw0, ch: ch0, gap: gap0, speed: speed0, startX: startX0, p }) => {
  const P = def(ScreenshotCarouselParams, { ...defined({ cw: cw0, ch: ch0, gap: gap0, speed: speed0, startX: startX0 }), ...p });
  const { cw, ch, gap, speed, startX } = P;
  const f = useCurrentFrame();
  const x0 = startX - Math.max(0, f - at) * (speed / 30);
  return (
    <AbsoluteFill>
      {items.map((it, i) => <ShotCard key={i} img={it.img} label={it.label} w={cw} h={ch} style={{ left: x0 + i * (cw + gap), top: y, opacity: lerp(f, at + i * P.fadeStagger, at + i * P.fadeStagger + P.fadeDur, 0, 1) }} />)}
    </AbsoluteFill>
  );
};

// ══ 15. 버전 스택(로고 연혁) ══════════════════════════════════════════════
// 새 카드(300)가 오른쪽에 슬라이드+크로스페이드 10f, 스택 전체 왼쪽 160px, 이전 카드 240·50% 겹침·채도/밝기 60%
// 끝: 옛 카드가 최신 카드 뒤로 빨려 들어감(24f easeIn) → 최신 카드 중앙 이동 + 소프트 글로우·링(광선 없음)
export const VersionStackParams = z.object({
  hold: num(36, 4, 120, 1, "버전 하나 머무는 시간", "timing", "f"),
  slideDur: num(10, 1, 40, 1, "새 카드 밀어넣기 길이", "timing", "f"),
  endDelay: num(6, 0, 60, 1, "마지막 후 마무리 지연", "timing", "f"),
  suckDur: num(24, 1, 60, 1, "옛 카드 빨려들기 길이", "timing", "f"),
  moveDur: num(20, 1, 60, 1, "최신 카드 중앙 이동 길이", "timing", "f"),
  slideIn: num(160, 0, 500, 5, "새 카드 들어오는 거리", "motion", "px"),
  stackStep: num(120, 20, 300, 5, "스택 카드 간격", "motion", "px"),
  endZoom: num(0.25, 0, 1, 0.05, "마무리 확대량(배)", "motion", "배"),
  cardSize: num(300, 120, 500, 5, "카드 크기", "size", "px"),
  shrink: num(60, 0, 200, 5, "이전 카드 축소량", "size", "px"),
  dim: num(0.6, 0, 1, 0.05, "이전 카드 채도 빼기", "look"),
  darken: num(0.4, 0, 1, 0.05, "이전 카드 어둡게", "look"),
  glowR: num(420, 0, 900, 10, "마무리 글로우 반지름", "look", "px"),
});
export type VersionStackP = z.infer<typeof VersionStackParams>;
export const VersionStack: React.FC<{ versions: { content: React.ReactNode; year: string }[]; at: number; hold?: number; cx?: number; cy?: number; endAt?: number; p?: Partial<VersionStackP> }> = ({ versions, at, hold: hold0, cx = 1350, cy = 470, endAt, p }) => {
  const P = def(VersionStackParams, { ...defined({ hold: hold0 }), ...p });
  const hold = P.hold, CS = P.cardSize;
  const f = useCurrentFrame();
  if (f < at) return null;
  const n = versions.length;
  let kk = 0;
  for (let i = 1; i < n; i++) kk += lerp(f, at + i * hold, at + i * hold + P.slideDur, 0, 1, Easing.out(Easing.cubic));
  const E = endAt ?? at + n * hold + P.endDelay;
  const suck = lerp(f, E, E + P.suckDur, 0, 1, Easing.in(Easing.cubic));
  const M0 = E + P.suckDur - 2;
  const mv = lerp(f, M0, M0 + P.moveDur, 0, 1, Easing.inOut(Easing.cubic));
  const newestX = cx + (W / 2 - cx) * mv;
  const newestS = 1 + P.endZoom * mv;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {mv > 0 && P.glowR > 0 && <GlowPulse x={W / 2} y={cy} at={M0 + 12} r={P.glowR} color="255,240,200" rings={2} />}
      {versions.map((v, i) => {
        const d = kk - i;
        if (d <= -1 || (i === 0 && f < at)) return null;
        const isNewest = i === n - 1 && d > -0.01;
        let x: number, size: number, op: number, fl = "", sc = 1;
        if (d < 0) { x = cx + P.slideIn * -d; size = CS; op = 1 + d; }
        else { const m = Math.min(d, 1); x = cx - P.stackStep * d - 40 * m; size = CS - P.shrink * m; op = 1; fl = `saturate(${1 - P.dim * m}) brightness(${1 - P.darken * m})`; }
        if (i === 0 && n > 0) sc = photoPop(f, at).s;
        if (suck > 0 && !isNewest) { x = x + (cx - x) * suck; sc *= 1 - 0.35 * suck; op *= 1 - suck; }
        if (isNewest && mv > 0) { x = newestX; sc = newestS; }
        return (
          <div key={i} style={{ position: "absolute", left: x - size / 2, top: cy - size / 2, width: size, zIndex: i + 1, transform: `scale(${sc})`, opacity: op, filter: fl || undefined }}>
            <div style={{ width: size, height: size, borderRadius: 24, background: "#fff", boxShadow: "0 12px 26px rgba(0,0,0,0.45)", overflow: "hidden", display: "flex", alignItems: "center", justifyContent: "center" }}>{v.content}</div>
            <div style={{ marginTop: 16, textAlign: "center", fontFamily: "NeoHv", fontSize: size > CS - 20 ? 44 : 34, color: "#fff", opacity: suck > 0 && !isNewest ? 0 : 1 }}>{v.year}</div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// ══ 16. 아이콘 행 그리드 ═════════════════════════════════════════════════
// Ø250 흰 원판(소프트 섀도) — 앞 아이콘 위치에서 가로블러와 함께 미끄러져 오며 0.5→1.1→1.0 (4f), 10~12f 스태거, 5+4 배치
export const IconRowGridParams = z.object({
  stagger: num(11, 0, 40, 1, "원판 스태거 간격", "timing", "f"),
  popDur: num(4, 1, 20, 1, "미끄러짐·팝 길이", "timing", "f"),
  slideFrom: num(320, 0, 800, 10, "행 첫 원판 미끄러지는 거리", "motion", "px"),
  startScale: num(0.5, 0, 1, 0.05, "시작 크기(배)", "motion", "배"),
  popOver: num(1.1, 1, 1.6, 0.01, "오버슈트 크기(배)", "motion", "배"),
  blur0: num(28, 0, 80, 1, "가로 모션블러 세기", "look", "px"),
  d: num(250, 80, 400, 5, "원판 지름", "size", "px"),
  gapX: num(70, 0, 200, 2, "원판 가로 간격", "size", "px"),
  iconRatio: num(0.56, 0.2, 0.9, 0.02, "아이콘 비율(원판 대비)", "size", "배"),
  labelSize: num(36, 14, 80, 1, "라벨 글자 크기", "size", "px"),
  labelColor: col("#222", "라벨 색"),
});
export type IconRowGridP = z.infer<typeof IconRowGridParams>;
export const IconRowGrid: React.FC<{ items: { icon: React.ReactNode; label?: string }[]; at: number; stagger?: number; perRow?: number[]; d?: number; gapX?: number; rowYs?: number[]; labelColor?: string; p?: Partial<IconRowGridP> }> = ({ items, at, stagger: stagger0, perRow = [5, 4], d: d0, gapX: gapX0, rowYs = [330, 720], labelColor: labelColor0, p }) => {
  const P = def(IconRowGridParams, { ...defined({ stagger: stagger0, d: d0, gapX: gapX0, labelColor: labelColor0 }), ...p });
  const { stagger, d, gapX, labelColor } = P;
  const PD = P.popDur;
  const f = useCurrentFrame();
  if (f < at) return null;
  const pos: P[] = [];
  let idx = 0;
  perRow.forEach((cnt, r) => {
    const rw = cnt * d + (cnt - 1) * gapX;
    for (let c = 0; c < cnt && idx < items.length; c++, idx++) pos.push([(W - rw) / 2 + d / 2 + c * (d + gapX), rowYs[r]]);
  });
  const rowStart = perRow.map((_, r) => perRow.slice(0, r).reduce((a, b) => a + b, 0));
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {items.map((it, i) => {
        const a = at + i * stagger;
        if (f < a || !pos[i]) return null;
        const to = pos[i];
        const from: P = i === 0 || rowStart.includes(i) ? [to[0] - P.slideFrom, to[1]] : pos[i - 1];
        const t = kf(f, a, [0, PD], [0, 1], Easing.out(Easing.cubic));
        const x = from[0] + (to[0] - from[0]) * t, y = from[1] + (to[1] - from[1]) * t;
        const s = kf(f, a, [0, PD / 2, PD], [P.startScale, P.popOver, 1.0]);
        return (
          <HBlur key={i} amt={kf(f, a, [0, PD], [P.blur0, 0])} style={{ position: "absolute", left: x - d / 2, top: y - d / 2, width: d, transform: `scale(${s})`, opacity: kf(f, a, [0, 1], [0.4, 1]), zIndex: 100 - i }}>
            <div style={{ width: d, height: d, borderRadius: "50%", background: "#fff", boxShadow: "0 14px 30px rgba(0,0,0,0.22)", display: "flex", alignItems: "center", justifyContent: "center" }}><div style={{ width: d * P.iconRatio, height: d * P.iconRatio }}>{it.icon}</div></div>
            {it.label && <div style={{ marginTop: 12, textAlign: "center", fontFamily: "NeoHv", fontSize: P.labelSize, color: labelColor, whiteSpace: "nowrap" }}>{hz(it.label)}</div>}
          </HBlur>
        );
      })}
    </AbsoluteFill>
  );
};

// ══ 17. 트리 드롭라인 ════════════════════════════════════════════════════
export const TreeDroplinesParams = z.object({
  riseDelay: num(12, 0, 60, 1, "뿌리 박스 상승 지연", "timing", "f"),
  riseDur: num(12, 1, 40, 1, "뿌리 박스 상승 길이", "timing", "f"),
  rise: num(60, 0, 200, 2, "뿌리 박스 상승 거리", "motion", "px"),
  lineDelay: num(26, 0, 80, 1, "줄기 시작 지연", "timing", "f"),
  trunkDur: num(6, 1, 30, 1, "줄기 내려오는 길이", "timing", "f"),
  barDur: num(8, 1, 30, 1, "가로대 펼침 길이", "timing", "f"),
  dropDur: num(5, 1, 30, 1, "가지 내려오는 길이", "timing", "f"),
  kidStagger: num(4, 0, 20, 1, "자식 pill 스태거", "timing", "f"),
  spacing: num(420, 150, 700, 10, "자식 가로 간격", "size", "px"),
  lineWidth: num(6, 1, 20, 1, "선 두께", "size", "px"),
  rootSize: num(64, 24, 120, 2, "뿌리 글자 크기", "size", "px"),
  kidSize: num(50, 20, 100, 2, "자식 pill 글자 크기", "size", "px"),
  lineColor: col("#fff", "선 색"),
  rootColor: col("#2B2B2B", "뿌리 박스 색"),
});
export type TreeDroplinesP = z.infer<typeof TreeDroplinesParams>;
export const TreeDroplines: React.FC<{ root: string; kids: { text: string; color?: string }[]; at: number; x?: number; y?: number; rise?: number; kidY?: number; spacing?: number; lineColor?: string; rootColor?: string; p?: Partial<TreeDroplinesP> }> = ({ root, kids, at, x = W / 2, y = 400, rise: rise0, kidY = 760, spacing: spacing0, lineColor: lineColor0, rootColor: rootColor0, p }) => {
  const P = def(TreeDroplinesParams, { ...defined({ rise: rise0, spacing: spacing0, lineColor: lineColor0, rootColor: rootColor0 }), ...p });
  const { rise, spacing, lineColor, rootColor } = P;
  const f = useCurrentFrame();
  if (f < at) return null;
  const ry = y - lerp(f, at + P.riseDelay, at + P.riseDelay + P.riseDur, 0, rise, Easing.inOut(Easing.cubic));
  const rh = 150;
  const top = y - rise + rh / 2; // 올라간 뒤 박스 하단
  const barY = (top + kidY - 50) / 2 + 10;
  const kx = kids.map((_, i) => x + (i - (kids.length - 1) / 2) * spacing);
  const L0 = at + P.lineDelay;
  const L1 = L0 + P.trunkDur, L2 = L1 + P.barDur, L3 = L2 + P.dropDur;
  const trunk = lerp(f, L0, L1, 0, 1);
  const bar = lerp(f, L1, L2, 0, 1, Easing.out(Easing.cubic));
  const drop = lerp(f, L2, L3, 0, 1);
  const half = (kx[kx.length - 1] - kx[0]) / 2;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <svg width={W} height={H} style={{ position: "absolute" }}>
        <g stroke={lineColor} strokeWidth={P.lineWidth} strokeLinecap="round" fill="none">
          {trunk > 0 && <path d={`M${x},${top} V${top + (barY - top) * trunk}`} />}
          {bar > 0 && <path d={`M${x - half * bar},${barY} H${x + half * bar}`} />}
          {drop > 0 && kx.map((k, i) => <path key={i} d={`M${k},${barY} V${barY + (kidY - 44 - barY) * drop}`} />)}
        </g>
      </svg>
      <div style={{ position: "absolute", left: x, top: ry, transform: `translate(-50%,-50%) scale(${pop5(f, at)})`, background: rootColor, color: "#fff", fontFamily: "NeoHv", fontSize: P.rootSize, padding: "36px 60px 30px", borderRadius: 22, whiteSpace: "nowrap", boxShadow: "0 10px 22px rgba(0,0,0,0.35)", border: "5px solid #fff" }}>{hz(root)}</div>
      {kids.map((k, i) => <PopPill key={i} text={k.text} x={kx[i]} y={kidY} f={f} at={L3 + i * P.kidStagger} color={k.color || "#1FA3D6"} size={P.kidSize} />)}
    </AbsoluteFill>
  );
};

// ══ 18. 방패 날개 ════════════════════════════════════════════════════════
export const ShieldWingsParams = z.object({
  shieldDelay: num(8, 0, 40, 1, "방패 출발 지연", "timing", "f"),
  shieldStagger: num(2, 0, 20, 1, "방패 스태거 간격", "timing", "f"),
  flyDur: num(8, 1, 40, 1, "방패 펼쳐지는 길이", "timing", "f"),
  spreadX: num(400, 100, 800, 10, "좌우 방패 거리", "motion", "px"),
  sideY: num(20, -200, 300, 5, "좌우 방패 세로 오프셋", "motion", "px"),
  dropY: num(340, 0, 600, 10, "아래 방패 거리", "motion", "px"),
  tilt: num(8, 0, 45, 1, "좌우 방패 기울기", "motion", "°"),
  startScale: num(0.5, 0, 1, 0.05, "방패 시작 크기(배)", "motion", "배"),
  shieldSize: num(240, 100, 400, 5, "방패 폭", "size", "px"),
  textSize: num(70, 30, 140, 2, "중앙 글자 크기", "size", "px"),
  glow: num(30, 0, 100, 1, "중앙 글로우 세기", "look", "px"),
  color: col("#2EC4E6", "방패·글로우 색"),
});
export type ShieldWingsP = z.infer<typeof ShieldWingsParams>;
export const ShieldWings: React.FC<{ text: string; at: number; x?: number; y?: number; shields: { label: string; icon?: IconName }[]; color?: string; p?: Partial<ShieldWingsP> }> = ({ text, at, x = W / 2, y = 430, shields, color: color0, p }) => {
  const P = def(ShieldWingsParams, { ...defined({ color: color0 }), ...p });
  const color = P.color;
  const f = useCurrentFrame();
  if (f < at) return null;
  const offs: [number, number, number][] = [[-P.spreadX, P.sideY, -P.tilt], [P.spreadX, P.sideY, P.tilt], [0, P.dropY, 0]];
  const sw = P.shieldSize, sh = (sw * 13) / 12, s0 = P.startScale;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {shields.slice(0, 3).map((s, i) => {
        const a = at + P.shieldDelay + i * P.shieldStagger;
        if (f < a) return null;
        const k = lerp(f, a, a + P.flyDur, 0, 1, EXPO_OUT);
        const [dx, dy, rot] = offs[i];
        return (
          <div key={i} style={{ position: "absolute", left: x + dx * k - sw / 2, top: y + dy * k - sh / 2, width: sw, height: sh, transform: `scale(${s0 + (1 - s0) * k}) rotate(${rot * k}deg)`, opacity: 0.5 + 0.5 * k, filter: `drop-shadow(0 0 16px ${color}aa)` }}>
            <svg viewBox="0 0 100 108" width={sw} height={sh} style={{ position: "absolute" }}>
              <path d="M50,3 L94,18 V52 C94,80 74,98 50,105 C26,98 6,80 6,52 V18 Z" fill={color} stroke="#fff" strokeWidth={4} strokeLinejoin="round" />
              <path d="M50,12 L85,24 V52 C85,74 69,88 50,95" fill="none" stroke="rgba(255,255,255,0.45)" strokeWidth={3} />
            </svg>
            <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 4, paddingBottom: 20 }}>
              {s.icon && <div style={{ width: 80, height: 80 }}><Icon name={s.icon} color="#fff" accent={color} /></div>}
              <div style={{ fontFamily: "NeoHv", fontSize: 36, color: "#fff", whiteSpace: "nowrap" }}>{hz(s.label)}</div>
            </div>
          </div>
        );
      })}
      <div style={{ position: "absolute", left: x, top: y, transform: `translate(-50%,-50%) scale(${pop5(f, at)})`, background: "#0E2A3A", border: `5px solid ${color}`, color: "#fff", fontFamily: "NeoHv", fontSize: P.textSize, padding: "30px 56px 24px", borderRadius: 24, whiteSpace: "nowrap", boxShadow: `0 0 ${P.glow}px ${color}, 0 0 ${(P.glow * 8) / 3}px ${color}88`, textShadow: `0 0 14px ${color}`, zIndex: 10 }}>{hz(text)}</div>
    </AbsoluteFill>
  );
};

// ══ 19. 맵 핀 ════════════════════════════════════════════════════════════
export const MapPinParams = z.object({
  popDur: num(7, 1, 30, 1, "핀 꽂힘 길이", "timing", "f"),
  startScale: num(0, 0, 1, 0.05, "핀 시작 크기(배)", "motion", "배"),
  popOver: num(1.3, 1, 2, 0.01, "오버슈트 크기(배)", "motion", "배"),
  d: num(130, 50, 300, 2, "핀 원 지름", "size", "px"),
  tail: num(34, 0, 100, 1, "핀 꼬리 길이", "size", "px"),
  border: num(7, 0, 24, 1, "핀 테두리 두께", "size", "px"),
  labelSize: num(30, 14, 70, 1, "라벨 글자 크기", "size", "px"),
  color: col("#fff", "핀 색"),
});
export type MapPinP = z.infer<typeof MapPinParams>;
export const MapPin: React.FC<{ img: string; x: number; y: number; at: number; d?: number; color?: string; label?: string; pos?: string; p?: Partial<MapPinP> }> = ({ img, x, y, at, d: d0, color: color0, label, pos = "50% 30%", p }) => {
  const P = def(MapPinParams, { ...defined({ d: d0, color: color0 }), ...p });
  const { d, color, tail } = P;
  const f = useCurrentFrame();
  if (f < at) return null;
  const s = kf(f, at, [0, (P.popDur * 4) / 7, P.popDur], [P.startScale, P.popOver, 1.0], Easing.out(Easing.quad));
  return (
    <div style={{ position: "absolute", left: x - d / 2, top: y - d - tail, width: d, height: d + tail, transform: `scale(${s})`, transformOrigin: "50% 100%", filter: "drop-shadow(0 8px 10px rgba(0,0,0,0.4))" }}>
      <svg width={d} height={d + tail} style={{ position: "absolute" }}><path d={`M${d / 2 - 22},${d - 12} L${d / 2},${d + tail} L${d / 2 + 22},${d - 12} Z`} fill={color} /></svg>
      <div style={{ position: "absolute", left: 0, top: 0, width: d, height: d, borderRadius: "50%", border: `${P.border}px solid ${color}`, boxSizing: "border-box", overflow: "hidden", background: "#ccc" }}><Img src={src(img)} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: pos }} /></div>
      {label && <div style={{ position: "absolute", left: "50%", top: -58, transform: "translateX(-50%)", background: "#222", color: "#fff", fontFamily: "NeoHv", fontSize: P.labelSize, padding: "6px 16px 4px", borderRadius: 8, whiteSpace: "nowrap" }}>{hz(label)}</div>}
    </div>
  );
};

// ══ 20. 메달리언 트리 ════════════════════════════════════════════════════
export const MedallionTreeParams = z.object({
  stagger: num(30, 0, 80, 1, "메달 스태거 간격", "timing", "f"),
  popDur: num(8, 1, 30, 1, "메달 팝 길이", "timing", "f"),
  popOver: num(1.08, 1, 1.5, 0.01, "메달 오버슈트 크기(배)", "motion", "배"),
  lineDelay: num(24, 0, 80, 1, "마지막 메달 후 배선 지연", "timing", "f"),
  lineStagger: num(10, 0, 40, 1, "배선 스태거 간격", "timing", "f"),
  lineDur: num(12, 1, 60, 1, "배선 그리기 길이", "timing", "f"),
  concDelay: num(4, 0, 40, 1, "배선 후 결론 지연", "timing", "f"),
  d: num(230, 80, 400, 5, "메달 지름", "size", "px"),
  ring: num(12, 0, 40, 1, "메달 색 테두리 두께", "size", "px"),
  lineWidth: num(5, 1, 20, 1, "배선 두께", "size", "px"),
  busGap: num(16, 0, 60, 1, "평행 배선 간격", "size", "px"),
  dotR: num(11, 0, 40, 1, "합류점 반지름", "size", "px"),
  nameSize: num(40, 16, 80, 1, "이름 글자 크기", "size", "px"),
  concSize: num(60, 24, 120, 2, "결론 글자 크기", "size", "px"),
});
export type MedallionTreeP = z.infer<typeof MedallionTreeParams>;
export const MedallionTree: React.FC<{ items: { img: string; name: string; color: string; x: number; y: number; pos?: string }[]; center: P; at: number; stagger?: number; d?: number; lineAt?: number; conclusion?: string; midY?: number; p?: Partial<MedallionTreeP> }> = ({ items, center, at, stagger: stagger0, d: d0, lineAt, conclusion, midY, p }) => {
  const P = def(MedallionTreeParams, { ...defined({ stagger: stagger0, d: d0 }), ...p });
  const { stagger, d } = P;
  const f = useCurrentFrame();
  if (f < at) return null;
  const la = lineAt ?? at + (items.length - 1) * stagger + P.lineDelay;
  const my = midY ?? (items[0].y + d / 2 + 70 + center[1]) / 2;
  const concAt = la + (items.length - 1) * P.lineStagger + P.lineDur + P.concDelay;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <svg width={W} height={H} style={{ position: "absolute" }}>
        {items.map((it, i) => {
          const a = la + i * P.lineStagger;
          if (f < a) return null;
          // 번들 배선: 바깥 항목일수록 낮은 가로선 + 중심 근처에서 16px 간격 평행 세로선 → 교차 없음
          const n = items.length, rel = i - (n - 1) / 2;
          const ex = center[0] + rel * P.busGap, hy = my + (Math.abs(rel) - 0.5) * 22;
          const pts: P[] = [[it.x, it.y + d / 2 + 70], [it.x, hy], [ex, hy], [ex, center[1]]];
          return <path key={i} d={dOf(polyUpTo(pts, lerp(f, a, a + P.lineDur, 0, polyLen(pts), Easing.inOut(Easing.quad))))} stroke={it.color} strokeWidth={P.lineWidth} fill="none" strokeLinejoin="round" strokeLinecap="round" />;
        })}
        {f >= la + P.lineDur && P.dotR > 0 && <circle cx={center[0]} cy={center[1]} r={kf(f, la + P.lineDur, [0, 3, 5], [0, (P.dotR * 14) / 11, P.dotR])} fill="#fff" />}
      </svg>
      {items.map((it, i) => {
        const a = at + i * stagger;
        if (f < a) return null;
        const s = kf(f, a, [0, (P.popDur * 5) / 8, P.popDur], [0, P.popOver, 1.0], Easing.out(Easing.quad));
        return (
          <React.Fragment key={i}>
            <div style={{ position: "absolute", left: it.x - d / 2, top: it.y - d / 2, width: d, height: d, borderRadius: "50%", background: it.color, transform: `scale(${s})`, boxShadow: "0 10px 22px rgba(0,0,0,0.35)", padding: P.ring, boxSizing: "border-box" }}>
              <div style={{ width: "100%", height: "100%", borderRadius: "50%", overflow: "hidden", background: "#eee" }}><Img src={src(it.img)} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: it.pos || "50% 50%" }} /></div>
            </div>
            <div style={{ position: "absolute", left: it.x - 200, width: 400, top: it.y + d / 2 + 14, textAlign: "center", opacity: lerp(f, a + 6, a + 14, 0, 1), fontFamily: "NeoHv", fontSize: P.nameSize, color: "#fff", whiteSpace: "nowrap" }}>{hz(it.name)}</div>
          </React.Fragment>
        );
      })}
      {conclusion && f >= concAt && <div style={{ position: "absolute", left: 0, width: W, top: center[1] + 30, textAlign: "center", opacity: lerp(f, concAt, concAt + 6, 0, 1, Easing.linear) }}><span style={{ display: "inline-block", background: "#fff", color: "#1a1a1a", fontFamily: "NeoHv", fontSize: P.concSize, padding: "18px 48px 12px", borderRadius: 16 }}>{hz(conclusion)}</span></div>}
    </AbsoluteFill>
  );
};

// ══ 21. 퍼즐 결합 ════════════════════════════════════════════════════════
export const PuzzleJoinParams = z.object({
  dur: num(26, 1, 90, 1, "조각 합쳐지는 길이", "timing", "f"),
  travel: num(620, 0, 1200, 10, "조각 출발 거리", "motion", "px"),
  ringDur: num(18, 1, 60, 1, "결합 링 퍼짐 길이", "timing", "f"),
  ringR0: num(30, 0, 200, 5, "링 시작 반지름", "size", "px"),
  ringR1: num(230, 50, 600, 10, "링 끝 반지름", "size", "px"),
  ringW: num(12, 1, 40, 1, "링 시작 두께", "size", "px"),
  S: num(320, 120, 500, 5, "조각 크기", "size", "px"),
  knob: num(0.17, 0.05, 0.3, 0.01, "요철 크기(조각 대비)", "size", "배"),
  labelSize: num(62, 20, 120, 2, "글자 크기", "size", "px"),
  leftColor: col("#E5484D", "왼쪽 조각 색"),
  rightColor: col("#2F7BE0", "오른쪽 조각 색"),
  ringColor: col("#34D6F0", "링 색"),
});
export type PuzzleJoinP = z.infer<typeof PuzzleJoinParams>;
export const PuzzleJoin: React.FC<{ left: string; right: string; at: number; x?: number; y?: number; S?: number; colors?: [string, string]; dur?: number; ringColor?: string; p?: Partial<PuzzleJoinP> }> = ({ left, right, at, x = W / 2, y = H / 2, S: S0, colors, dur: dur0, ringColor: ringColor0, p }) => {
  const P = def(PuzzleJoinParams, { ...defined({ S: S0, dur: dur0, ringColor: ringColor0, leftColor: colors?.[0], rightColor: colors?.[1] }), ...p });
  const { S, dur, ringColor } = P;
  const f = useCurrentFrame();
  if (f < at) return null;
  const r = S * P.knob, c = S / 2;
  const redD = `M0,0 H${S} V${c - 0.7 * r} A${r},${r} 0 1 1 ${S},${c + 0.7 * r} V${S} H0 Z`;
  const blueD = `M0,0 H${S} V${S} H0 V${c + 0.7 * r} A${r},${r} 0 1 0 0,${c - 0.7 * r} Z`;
  const k = lerp(f, at, at + dur, 1, 0, Easing.out(Easing.cubic));
  const off = P.travel * k;
  const J = at + dur, RD = P.ringDur;
  const piece = (d: string, col: string, label: string, lx: number, knobPad: number) => (
    <svg width={S + knobPad} height={S} viewBox={`0 0 ${S + knobPad} ${S}`} style={{ position: "absolute", overflow: "visible" }}>
      <path d={d} fill={col} stroke="#fff" strokeWidth={6} strokeLinejoin="round" style={{ filter: "drop-shadow(0 10px 14px rgba(0,0,0,0.35))" }} />
      <text x={lx} y={c + 22} textAnchor="middle" fontFamily="NeoHv" fontSize={P.labelSize} fill="#fff">{label}</text>
    </svg>
  );
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div style={{ position: "absolute", left: x - S - off, top: y - S / 2, width: S, height: S }}>{piece(redD, P.leftColor, left, c, 0)}</div>
      <div style={{ position: "absolute", left: x + off, top: y - S / 2, width: S, height: S }}>{piece(blueD, P.rightColor, right, c + r * 0.6, 0)}</div>
      {f >= J && f < J + RD && (() => { const rr = lerp(f, J, J + RD, P.ringR0, P.ringR1, Easing.out(Easing.cubic)); return <div style={{ position: "absolute", left: x - rr, top: y - rr, width: rr * 2, height: rr * 2, borderRadius: "50%", border: `${lerp(f, J, J + RD, P.ringW, 2)}px solid ${ringColor}`, opacity: lerp(f, J, J + RD, 1, 0), boxShadow: `0 0 18px ${ringColor}` }} />; })()}
    </AbsoluteFill>
  );
};
