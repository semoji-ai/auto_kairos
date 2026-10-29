// 세모지 차트·인포그래픽 확장(x_charts) — 도감 "분석만" 기법을 레퍼런스 프레임 대조 후 구현.
// 규약: 모든 컴포넌트는 `at`(시작 프레임) + `<Name>Params` zod 스키마(p?: Partial) — 기본값 = 레퍼런스 실측.
// 난수는 remotion random(seed)만. 방사형 광선 금지(글로우·링·파티클로 대체). 지도 데이터 = public/img/x/geo.json
//   (Natural Earth / us-atlas 를 d3-geo 로 1920×1080 에 미리 투영한 path 문자열).
import React from "react";
import { AbsoluteFill, Easing, Img, random, useCurrentFrame, delayRender, continueRender, staticFile } from "remotion";
import { z } from "zod";
import { W, H, lerp, kf, src, Stamp, Starburst, EXPO_OUT, QUART_OUT } from "../fx";
import { num, col, flag, def } from "../params/p";
import { ZigzagArrow, LogoChar, KitImg, KitTint, KitMul, CastFig, castOf } from "./charts";
import { KoreaIslands } from "../map/KoreaIslands";
import { prop, propH } from "./kit";
import { Teleport } from "./characters";
import { FLAGS } from "./backgrounds";

type RN = React.ReactNode;
type Pt = [number, number];
const TAU = Math.PI * 2;
const d1 = (v: number) => Math.max(1, v);
const E_IO = Easing.inOut(Easing.cubic);
const E_OUT = Easing.out(Easing.cubic);
const QUINT_OUT = Easing.bezier(0.22, 1, 0.36, 1);
/** 팝 스케일: from → over(len×0.6) → 1(len) */
const pop = (f: number, at: number, len: number, from = 0.3, over = 1.1) =>
  f < at ? 0 : kf(f, at, [0, Math.max(0.01, d1(len) * 0.6), d1(len)], [from, over, 1], Easing.out(Easing.quad));
/** 블러 해제 */
const unblur = (f: number, at: number, len: number, b = 8) => (f < at ? b : kf(f, at, [0, d1(len)], [b, 0]));
/** 글자 단위 타이핑 */
const typed = (s: string, f: number, at: number, per: number) => (f < at ? "" : Array.from(s).slice(0, Math.floor((f - at) / Math.max(0.2, per)) + 1).join(""));

/** 중심 기준 배치 래퍼(스케일·블러·불투명도) */
const At: React.FC<{ x: number; y: number; s?: number; sx?: number; sy?: number; blur?: number; op?: number; rot?: number; origin?: string; children: RN; style?: React.CSSProperties }> = ({ x, y, s = 1, sx = 1, sy = 1, blur = 0, op = 1, rot = 0, origin = "50% 50%", children, style }) => (
  <div style={{ position: "absolute", left: x, top: y, transform: `translate(-50%,-50%) rotate(${rot}deg) scale(${s * sx},${s * sy})`, transformOrigin: origin, filter: blur > 0.05 ? `blur(${blur}px)` : undefined, opacity: op, ...style }}>{children}</div>
);
/** 캡슐 라벨 */
const Pill: React.FC<{ text: RN; bg?: string; fg?: string; size?: number; font?: string; pad?: number }> = ({ text, bg = "#1E1E5A", fg = "#fff", size = 44, font = "NeoHv", pad }) => (
  <div style={{ background: bg, color: fg, fontFamily: font, fontSize: size, lineHeight: 1.1, padding: `${size * 0.3}px ${pad ?? size * 0.62}px`, borderRadius: 999, whiteSpace: "nowrap", boxShadow: "0 6px 12px rgba(0,0,0,0.22)", textAlign: "center" }}>{text}</div>
);

// ── 지도 데이터 로더 ─────────────────────────────────────────────────────
type GeoC = { name: string; d: string; c: Pt };
type Geo = { world: { land: string }; us: { states: (GeoC & { id: string })[]; nation: string }; eastasia: { countries: GeoC[] } };
let GEO: Geo | null = null;
let GEO_P: Promise<Geo> | null = null;
export const useGeo = (): Geo | null => {
  const [g, setG] = React.useState<Geo | null>(GEO);
  const [h] = React.useState(() => (GEO ? null : delayRender("x_charts geo")));
  React.useEffect(() => {
    if (GEO) { if (h !== null) continueRender(h); return; }
    GEO_P = GEO_P ?? fetch(staticFile("img/x/geo.json")).then((r) => r.json());
    GEO_P.then((j) => { GEO = j; setG(j); if (h !== null) continueRender(h); });
  }, []);
  return g;
};

// ── 공용 소품 — 세모지 키트 PNG(public/kit/props) ─────────────────────────────
const CAR = { w: 1337, h: 503, rear: 857 }; // car_body·car_wheel·xc_car_paint 같은 크롭 박스, 뒷바퀴 = 앞바퀴 +857px
/** 옆모습 자동차(세모지 car_body + 차체색 틴트 xc_car_paint + 바퀴 2). 박스 w × 0.47w, 타이어 바닥 = 0.93h. 기본 오른쪽을 봄 */
export const FlatCar: React.FC<{ color?: string; w?: number; flip?: boolean }> = ({ color = "#48B8E8", w = 380, flip }) => {
  const h = (w * 180) / 380, ch = (w * CAR.h) / CAR.w, k = w / CAR.w;
  const full: React.CSSProperties = { position: "absolute", left: 0, top: 0, width: w, height: ch };
  return (
    <div style={{ position: "relative", width: w, height: h }}>
      <div style={{ position: "absolute", left: 0, top: (h * 167) / 180 - ch, width: w, height: ch, transform: flip ? undefined : "scaleX(-1)", isolation: "isolate" }}>
        <Img src={prop("car_body")} style={full} />
        <Img src={prop("xc_car_paint")} style={full} />
        <div style={{ ...full, backgroundColor: color, mixBlendMode: "multiply", WebkitMaskImage: `url(${prop("xc_car_paint")})`, maskImage: `url(${prop("xc_car_paint")})`, WebkitMaskSize: "100% 100%", maskSize: "100% 100%" } as React.CSSProperties} />
        <Img src={prop("car_wheel")} style={full} />
        <Img src={prop("car_wheel")} style={{ ...full, left: CAR.rear * k }} />
      </div>
    </div>
  );
};
/** 원액 통(세모지 syrup_jug) — 라벨 글자는 검정 띠 위에 코드로. 높이 = propH */
export const Jug: React.FC<{ w?: number; label?: string }> = ({ w = 200, label = "SYRUP" }) => {
  const h = propH("syrup_jug", w);
  return (
    <div style={{ position: "relative", width: w, height: h }}>
      <Img src={prop("syrup_jug")} style={{ display: "block", width: w, height: h }} />
      {label && <div style={{ position: "absolute", left: 0, top: h * 0.6, width: w, transform: "translateY(-50%)", textAlign: "center", fontFamily: "Jua", fontSize: w * 0.15, color: "#E8E0CC", whiteSpace: "nowrap" }}>{label}</div>}
    </div>
  );
};
// ── geo.json 투영 복원(울릉도·독도 섬 형상 보강용) — d3 geoPath 경계 대조로 역산(오차 < 0.4px)
//   eastasia: geoMercator scale 1369.19, rotate[-140,0], translate[1198.955, 1619.19]
//   (world: geoEquirectangular scale 305.58, translate[960, 631.5] — 소축척이라 섬 보강 안 함)
const MERC_EA = { s: 1369.19, lon0: 140, tx: 1198.955, ty: 1619.19 };
const projEA = (ll: [number, number]): Pt => [MERC_EA.tx + MERC_EA.s * (((ll[0] - MERC_EA.lon0) * Math.PI) / 180), MERC_EA.ty - MERC_EA.s * Math.log(Math.tan(Math.PI / 4 + (ll[1] * Math.PI) / 360))];
/** 구형 컴퓨터(세모지 pc_icon 크롭 xc_pc, 색 곱하기 틴트) */
const PC = { w: 900, h: 854 };
const PCIcon: React.FC<{ w?: number; color?: string }> = ({ w = 200, color = "#b0d0cc" }) => (
  <KitMul id="xc_pc" w={w} h={(w * PC.h) / PC.w} color={color} lift={1.15} />
);
/** 태블릿(세모지 tablet_device 크롭 xc_tablet). w > h 면 90° 눕힘. bezel·screen 은 그림 고정(호환용) */
const Tablet: React.FC<{ w: number; h: number; bezel?: number; screen?: string }> = ({ w, h }) => {
  const land = w > h, iw = land ? h : w, ih = land ? w : h;
  return (
    <div style={{ position: "relative", width: w, height: h, filter: "drop-shadow(0 4px 6px rgba(0,0,0,0.25))" }}>
      <Img src={prop("xc_tablet")} style={{ position: "absolute", left: (w - iw) / 2, top: (h - ih) / 2, width: iw, height: ih, transform: land ? "rotate(90deg)" : undefined }} />
    </div>
  );
};

// ══ 1. MascotStepBars — 마스코트 + 계단식 막대 + 카메라 트럭 ═════════════════
// [ref2 34:16] 마스코트 걸어 들어옴 → 작은 막대 위로 점프 → 값 원 블러 팝 → 카메라 옆 이동+줌아웃 → 큰 막대로 순간이동
export const MascotStepBarsParams = z.object({
  walkDur: num(18, 4, 60, 1, "걸어 들어오는 시간", "timing", "f"),
  barGrow: num(12, 2, 40, 1, "막대 성장 시간", "timing", "f"),
  hopRise: num(5, 2, 20, 1, "점프 상승", "timing", "f"),
  hopFall: num(5, 2, 20, 1, "점프 하강", "timing", "f"),
  squash: num(3, 0, 10, 1, "착지 스쿼시", "timing", "f"),
  hopH: num(150, 20, 400, 5, "점프 높이", "motion", "px"),
  circleDelay: num(8, 0, 40, 1, "값 원 지연", "timing", "f"),
  circlePop: num(6, 2, 20, 1, "값 원 팝", "timing", "f"),
  truckDelay: num(26, 0, 90, 1, "카메라 이동 지연", "timing", "f"),
  truckDur: num(24, 6, 60, 1, "카메라 트럭 길이", "timing", "f"),
  zoomOut: num(1.3, 1, 2, 0.05, "줌아웃 배율", "motion"),
  circleD: num(250, 120, 400, 5, "값 원 지름", "size", "px"),
  candleOp: num(0.3, 0, 1, 0.05, "배경 캔들 불투명도", "look"),
  barColor: col("#6b6b6b", "막대 색"),
  circleColor: col("#3f9a3a", "값 원 색"),
  bg: col("#F6F3EC", "배경색"),
});
export type MascotStepBarsP = z.infer<typeof MascotStepBarsParams>;
export type StepBar = { x: number; w: number; h: number; value: string; label?: string };
export const MascotStepBars: React.FC<{ at: number; bars?: [StepBar, StepBar]; mascot?: RN; mascotH?: number; ground?: number; p?: Partial<MascotStepBarsP> }> = ({ at, bars, mascot, mascotH = 165, ground = 800, p }) => {
  const P = def(MascotStepBarsParams, p);
  const f = useCurrentFrame();
  const B: [StepBar, StepBar] = bars ?? [
    { x: 560, w: 170, h: 70, value: "시가총액\n6억 달러", label: "1986년" },
    { x: 2050, w: 230, h: 430, value: "시가총액\n3조 달러", label: "2024년" },
  ];
  const M = mascot ?? <LogoChar d={150} bg="#E2362B" text="MS" />;
  const xStand = B[0].x - B[0].w / 2 - 95;
  const hopAt = at + P.walkDur + 4, hopLen = P.hopRise + P.hopFall, hopEnd = hopAt + hopLen;
  const c1 = hopEnd + P.circleDelay, truck = c1 + P.truckDelay, tp = truck + P.truckDur + 6;
  // 마스코트 위치
  let mx = -120, foot = ground, sx = 1, sy = 1;
  if (f >= at && f < hopAt) {
    mx = lerp(f, at, at + P.walkDur, -120, xStand, Easing.linear);
    foot = ground - (f < at + P.walkDur ? Math.abs(Math.sin((f - at) * 0.55)) * 14 : 0);
  } else if (f >= hopAt) {
    const top0 = ground - B[0].h, peak = Math.min(ground, top0) - P.hopH;
    mx = lerp(f, hopAt, hopEnd, xStand, B[0].x, Easing.linear);
    foot = f < hopAt + P.hopRise ? lerp(f, hopAt, hopAt + P.hopRise, ground, peak, Easing.out(Easing.quad)) : lerp(f, hopAt + P.hopRise, hopEnd, peak, top0, Easing.in(Easing.quad));
    const g = f - hopEnd;
    if (g >= 0 && g < P.squash) { const k = 1 - g / P.squash; sy = 1 - 0.2 * k; sx = 1 + 0.15 * k; }
    if (f < hopEnd) { sy = 1.06; sx = 0.95; }
  }
  const mascotAt = (x: number, y: number, ax = 1, ay = 1) => (
    <div style={{ position: "absolute", left: x - mascotH / 2, top: y - mascotH, width: mascotH, height: mascotH, display: "flex", alignItems: "flex-end", justifyContent: "center", transformOrigin: "50% 100%", transform: `scale(${ax},${ay})` }}>{M}</div>
  );
  // 카메라
  const z = lerp(f, truck, truck + P.truckDur, 1, 1 / P.zoomOut, E_IO);
  const cx = lerp(f, truck, truck + P.truckDur, 960, (B[0].x + B[1].x) / 2, E_IO);
  const barH = (i: number) => (i === 0 ? lerp(f, at, at + P.barGrow, 0, B[0].h, E_OUT) : lerp(f, truck + P.truckDur * 0.3, truck + P.truckDur * 0.3 + P.barGrow, 0, B[1].h, E_OUT));
  const circle = (i: number, t: number) => {
    if (f < t) return null;
    const b = B[i], D = P.circleD;
    return (
      <At key={i} x={b.x + (i === 0 ? 320 : 290)} y={ground - b.h - (i === 0 ? 230 : 130)} s={pop(f, t, P.circlePop, 0.3, 1.08)} blur={unblur(f, t, P.circlePop, 14)} op={kf(f, t, [0, 3], [0.5, 1])}>
        <div style={{ width: D, height: D, borderRadius: "50%", background: P.circleColor, display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontFamily: "NeoHv", fontSize: D * 0.13, textAlign: "center", whiteSpace: "pre-line", lineHeight: 1.2 }}>{b.value}</div>
      </At>
    );
  };
  const candles = Array.from({ length: 12 }).map((_, i) => {
    const x = 120 + i * 210, hh = 90 + random(`msb-c${i}`) * 260, y = 300 + random(`msb-y${i}`) * 200;
    const up = random(`msb-u${i}`) > 0.4;
    return (<g key={i}><rect x={x + 22} y={y - 40} width={6} height={hh + 80} fill={up ? "#d8433a" : "#3a6fd8"} /><rect x={x} y={y} width={50} height={hh} fill={up ? "#d8433a" : "#3a6fd8"} /></g>);
  });
  return (
    <AbsoluteFill style={{ background: P.bg, backgroundImage: "linear-gradient(rgba(0,0,0,0.035) 2px, transparent 2px), linear-gradient(90deg, rgba(0,0,0,0.035) 2px, transparent 2px)", backgroundSize: "60px 60px" }}>
      <div style={{ position: "absolute", left: 0, top: 0, width: W, height: H, transformOrigin: "0 0", transform: `translate(${960 - cx * z}px, ${540 - 540 * z}px) scale(${z})` }}>
        <svg width={2800} height={H} style={{ position: "absolute", left: 0, top: 0, opacity: P.candleOp }}>{candles}</svg>
        <div style={{ position: "absolute", left: -2000, top: ground, width: 6800, height: 12, background: "#111" }} />
        {B.map((b, i) => (
          <React.Fragment key={i}>
            <div style={{ position: "absolute", left: b.x - b.w / 2, top: ground - barH(i), width: b.w, height: barH(i), background: P.barColor }} />
            {b.label && <div style={{ position: "absolute", left: b.x - 150, top: ground + 24, width: 300, textAlign: "center", fontFamily: "NeoHv", fontSize: 48, color: "#111", opacity: f >= at ? 1 : 0 }}>{b.label}</div>}
          </React.Fragment>
        ))}
        {circle(0, c1)}
        {f < tp ? mascotAt(mx, foot, sx, sy) : null}
        {f >= tp && <Teleport x={B[0].x} y={ground - B[0].h - mascotH / 2} w={mascotH} h={mascotH} at={tp} mode="out" seed="msb-o">{mascotAt(B[0].x, ground - B[0].h)}</Teleport>}
        {f >= tp + 6 && <Teleport x={B[1].x} y={ground - B[1].h - mascotH / 2} w={mascotH} h={mascotH} at={tp + 6} mode="in" seed="msb-i">{mascotAt(B[1].x, ground - B[1].h)}</Teleport>}
        {circle(1, tp + 20)}
      </div>
    </AbsoluteFill>
  );
};

// ══ 2. TicTacToeWin — 틱택토 승리선 ═══════════════════════════════════════
// [ref2 5:31] 태그 팝 4f → 승리 O 3개 검정→노랑 12f → 노란 대각선(약 20px) 7f → 팻말 든 캐릭터 하단에서 10f
export const TicTacToeWinParams = z.object({
  tagPop: num(4, 1, 20, 1, "태그 팝", "timing", "f"),
  colorDelay: num(4, 0, 30, 1, "색 전환 지연", "timing", "f"),
  colorDur: num(12, 1, 40, 1, "O 색 전환", "timing", "f"),
  lineDelay: num(6, 0, 40, 1, "승리선 지연", "timing", "f"),
  lineDur: num(7, 1, 30, 1, "승리선 드로우", "timing", "f"),
  riseDelay: num(6, 0, 40, 1, "캐릭터 등장 지연", "timing", "f"),
  riseDur: num(10, 2, 30, 1, "캐릭터 상승", "timing", "f"),
  cell: num(190, 100, 280, 5, "칸 크기", "size", "px"),
  lineW: num(20, 4, 50, 1, "승리선 두께", "size", "px"),
  ink: col("#2b2b2b", "말·격자 색"),
  win: col("#F2B600", "승리 색"),
  bg: col("#F6F3EC", "배경색"),
});
export type TicTacToeWinP = z.infer<typeof TicTacToeWinParams>;
export const TicTacToeWin: React.FC<{ at: number; board?: string; win?: [number, number, number]; tag?: string; sign?: string; img?: string; x0?: number; y0?: number; p?: Partial<TicTacToeWinP> }> = ({ at, board = "XXOOOXO  ", win = [2, 4, 6], tag = "Tic-Tac-Toe", sign = "O 승리!", img = "img/s06_kid.png", x0 = 330, y0 = 150, p }) => {
  const P = def(TicTacToeWinParams, p);
  const f = useCurrentFrame();
  const C = P.cell, S = C * 3;
  const cAt = at + P.tagPop + P.colorDelay, lAt = cAt + P.colorDur + P.lineDelay, rAt = lAt + P.lineDur + P.riseDelay;
  const winK = lerp(f, cAt, cAt + P.colorDur, 0, 1, Easing.linear);
  const mix = (a: string, b: string, t: number) => {
    const h = (s: string) => [1, 3, 5].map((i) => parseInt(s.slice(i, i + 2), 16));
    const A = h(a), Bc = h(b);
    return `rgb(${A.map((v, i) => Math.round(v + (Bc[i] - v) * t)).join(",")})`;
  };
  const center = (i: number): Pt => [x0 + (i % 3) * C + C / 2, y0 + Math.floor(i / 3) * C + C / 2];
  const a = center(win[0]), b = center(win[2]);
  const ext = 0.28, ax = a[0] + (a[0] - b[0]) * ext, ay = a[1] + (a[1] - b[1]) * ext, bx = b[0] + (b[0] - a[0]) * ext, by = b[1] + (b[1] - a[1]) * ext;
  const lp = lerp(f, lAt, lAt + P.lineDur, 0, 1, E_OUT);
  const sw = C * 0.11;
  const riseY = lerp(f, rAt, rAt + P.riseDur, 700, 0, E_OUT);
  return (
    <AbsoluteFill style={{ background: P.bg }}>
      <svg width={W} height={H} style={{ position: "absolute" }}>
        {[1, 2].map((k) => (<g key={k}><rect x={x0 + k * C - sw / 2} y={y0 - 10} width={sw} height={S + 20} rx={sw / 2} fill={P.ink} /><rect x={x0 - 10} y={y0 + k * C - sw / 2} width={S + 20} height={sw} rx={sw / 2} fill={P.ink} /></g>))}
        {Array.from(board.padEnd(9, " ").slice(0, 9)).map((ch, i) => {
          const [cx, cy] = center(i), r = C * 0.3, isWin = win.includes(i);
          const c = isWin && f >= cAt ? mix(P.ink, P.win, winK) : P.ink;
          if (ch === "O" || ch === "o") return <circle key={i} cx={cx} cy={cy} r={r} fill="none" stroke={c} strokeWidth={C * 0.1} />;
          if (ch === "X" || ch === "x") return <g key={i} stroke={c} strokeWidth={C * 0.1} strokeLinecap="round"><line x1={cx - r} y1={cy - r} x2={cx + r} y2={cy + r} /><line x1={cx + r} y1={cy - r} x2={cx - r} y2={cy + r} /></g>;
          return null;
        })}
        {f >= lAt && <line x1={ax} y1={ay} x2={ax + (bx - ax) * lp} y2={ay + (by - ay) * lp} stroke={P.win} strokeWidth={P.lineW} strokeLinecap="round" />}
      </svg>
      {f >= at && (
        <At x={x0 + S + 330} y={y0 + 50} s={pop(f, at, P.tagPop, 0.4, 1.1)}>
          <div style={{ background: P.win, color: "#fff", fontFamily: "NeoHv", fontSize: 54, padding: "10px 26px" }}>{tag}</div>
        </At>
      )}
      {f >= rAt && (
        <div style={{ position: "absolute", left: x0 + S + 210, top: 330 + riseY, width: 300, height: 760 }}>
          <div style={{ position: "absolute", left: 30, top: 0, width: 240, background: "#1d1d1d", color: "#fff", fontFamily: "NeoHv", fontSize: 44, textAlign: "center", padding: "8px 0", borderRadius: 8 }}>{sign}</div>
          <Img src={src(img)} style={{ position: "absolute", left: 0, top: 70, width: 300, height: 680, objectFit: "contain", objectPosition: "50% 0" }} />
        </div>
      )}
    </AbsoluteFill>
  );
};

// ══ 3. RoadLaneAnalogy — 도로 차선 증가 비유(카메라 풀백) ══════════════════════
// [ref2 57:20] 2차선 도로(측면 자동차) → 카메라 1.0→0.6 풀백하며 4차선·차량이 드러남. 차선 점선은 계속 흐름
export const RoadLaneAnalogyParams = z.object({
  pullDelay: num(20, 0, 120, 1, "풀백 시작 지연", "timing", "f"),
  pullDur: num(30, 6, 90, 1, "풀백 길이", "timing", "f"),
  zoomEnd: num(0.6, 0.3, 1, 0.02, "풀백 후 배율", "motion"),
  laneH: num(450, 250, 700, 10, "차선 높이", "size", "px"),
  dashSpeed: num(9, 0, 40, 1, "차선 점선 흐름 속도", "motion", "px/f"),
  carDrift: num(1.2, 0, 10, 0.1, "차량 전진 속도", "motion", "px/f"),
  carW: num(420, 200, 700, 10, "차량 폭", "size", "px"),
  road: col("#7b7b79", "노면 색"),
});
export type RoadLaneAnalogyP = z.infer<typeof RoadLaneAnalogyParams>;
export const RoadLaneAnalogy: React.FC<{ at: number; lanes?: number; cars?: { lane: number; x: number; color: string }[]; p?: Partial<RoadLaneAnalogyP> }> = ({ at, lanes = 4, cars, p }) => {
  const P = def(RoadLaneAnalogyParams, p);
  const f = useCurrentFrame();
  const L = P.laneH, N = Math.max(2, Math.round(lanes));
  const CARS = cars ?? [
    { lane: 0, x: 120, color: "#F5C12E" }, { lane: 1, x: 260, color: "#4DB6E8" },
    { lane: 2, x: 380, color: "#E8483F" }, { lane: 3, x: 80, color: "#F2D04A" }, { lane: 2, x: 1500, color: "#8BC34A" }, { lane: 0, x: 1350, color: "#E8483F" },
  ];
  const z = lerp(f, at + P.pullDelay, at + P.pullDelay + P.pullDur, 1, P.zoomEnd, E_IO);
  const t = Math.max(0, f - at);
  const worldTop = H - N * L;
  const dashOff = -((t * P.dashSpeed) % 160);
  return (
    <AbsoluteFill style={{ background: P.road, overflow: "hidden" }}>
      <div style={{ position: "absolute", left: 0, top: 0, width: W, height: H, transformOrigin: "50% 100%", transform: `scale(${z})` }}>
        <div style={{ position: "absolute", left: -W, top: worldTop - L, width: W * 3, height: N * L + L * 2, background: P.road }} />
        {Array.from({ length: N + 1 }).map((_, i) => {
          const y = H - i * L;
          const edge = i === 0 || i === N;
          return edge
            ? <div key={i} style={{ position: "absolute", left: -W, top: y - 9, width: W * 3, height: 18, background: "#f2f2f2" }} />
            : <div key={i} style={{ position: "absolute", left: -W + dashOff, top: y - 7, width: W * 3 + 160, height: 14, backgroundImage: "linear-gradient(90deg, #fff 0 90px, transparent 90px 160px)", backgroundSize: "160px 14px" }} />;
        })}
        {CARS.filter((c) => c.lane < N).map((c, i) => {
          const y = H - c.lane * L - L / 2;
          const x = c.x + t * P.carDrift * (1 + (i % 3) * 0.25);
          const bob = Math.sin((t + i * 7) * 0.9) * 2;
          return <div key={i} style={{ position: "absolute", left: x, top: y - (P.carW * 180) / 380 / 2 + bob }}><FlatCar color={c.color} w={P.carW} /></div>;
        })}
      </div>
    </AbsoluteFill>
  );
};

// ══ 4. SilhouettePriceCompare — 회색 실루엣 경쟁품 + 가격표 ═════════════════════
// [ref4-apple 01:10:47] 좌대 위 주인공 + 흰 가격표 팝(0.6→1.05→1, 블러) → 경쟁품 회색 실루엣 오른쪽 먼저·왼쪽 8f 뒤 → 회색 태그 팝
export const SilhouettePriceCompareParams = z.object({
  tagPop: num(6, 1, 20, 1, "가격표 팝", "timing", "f"),
  rivalDelay: num(30, 0, 120, 1, "실루엣 등장 지연", "timing", "f"),
  rivalGap: num(8, 0, 40, 1, "좌우 실루엣 간격", "timing", "f"),
  rivalPop: num(5, 1, 20, 1, "실루엣 팝", "timing", "f"),
  rivalTagDelay: num(24, 0, 90, 1, "경쟁 태그 지연", "timing", "f"),
  tilt: num(16, 0, 45, 1, "실루엣 원근 기울기", "motion", "°"),
  tagW: num(358, 200, 600, 2, "가격표 폭", "size", "px"),
  priceSize: num(72, 30, 140, 1, "가격 글자 크기", "size", "px"),
  silhouette: num(0.42, 0.1, 0.9, 0.01, "실루엣 밝기(0=검정)", "look"),
  pedestal: col("#8a6a4a", "좌대 색"),
  bg: col("#331c1b", "벽지 색"),
});
export type SilhouettePriceCompareP = z.infer<typeof SilhouettePriceCompareParams>;
export const SilhouettePriceCompare: React.FC<{ at: number; hero: string; price: string; rivals: { img: string; price: string }[]; p?: Partial<SilhouettePriceCompareP> }> = ({ at, hero, price, rivals, p }) => {
  const P = def(SilhouettePriceCompareParams, p);
  const f = useCurrentFrame();
  const pedTop = 600, pedW = 460;
  const rAt = (i: number) => at + P.rivalDelay + i * P.rivalGap; // i=0 오른쪽
  return (
    <AbsoluteFill style={{ background: P.bg, backgroundImage: `repeating-linear-gradient(90deg, rgba(255,255,255,0.05) 0 46px, rgba(0,0,0,0.12) 46px 58px, rgba(255,255,255,0) 58px 110px)` }}>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 35%, rgba(0,0,0,0.55) 100%)" }} />
      {/* 좌대 */}
      <div style={{ position: "absolute", left: 960 - pedW / 2, top: pedTop, width: pedW, height: H - pedTop, background: P.pedestal }} />
      <div style={{ position: "absolute", left: 960 - pedW / 2 - 20, top: pedTop - 26, width: pedW + 40, height: 30, background: "#a3825f" }} />
      <Img src={src(hero)} style={{ position: "absolute", left: 960 - 260, top: pedTop - 26 - 420, width: 520, height: 420, objectFit: "contain", objectPosition: "50% 100%" }} />
      {f >= at && (
        <At x={960} y={pedTop + 190} s={kf(f, at, [0, P.tagPop * 0.6, P.tagPop], [0.6, 1.05, 1])} blur={unblur(f, at, P.tagPop * 0.7, 10)}>
          <div style={{ width: P.tagW, height: P.tagW * 0.39, background: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "NeoHv", fontSize: P.priceSize, color: "#111", boxShadow: "0 6px 14px rgba(0,0,0,0.35)" }}>{price}</div>
        </At>
      )}
      {rivals.slice(0, 2).map((r, i) => {
        const t = rAt(i);
        if (f < t) return null;
        const side = i === 0 ? 1 : -1, x = 960 + side * 560, y = 560;
        return (
          <React.Fragment key={i}>
            <At x={x} y={y} s={pop(f, t, P.rivalPop, 0.3, 1.06)} blur={unblur(f, t, P.rivalPop, 16)} style={{ perspective: 900 }}>
              <div style={{ transform: `rotateY(${-side * P.tilt}deg)` }}>
                <Img src={src(r.img)} style={{ width: 400, height: 380, objectFit: "contain", filter: `brightness(0) invert(${P.silhouette})` }} />
              </div>
            </At>
            {f >= t + P.rivalTagDelay && (
              <At x={x + side * 20} y={y + 250} s={pop(f, t + P.rivalTagDelay, 6, 0.3, 1.1)} blur={unblur(f, t + P.rivalTagDelay, 4, 8)}>
                <div style={{ background: "#595755", border: "5px solid #fff", color: "#fff", fontFamily: "NeoHv", fontSize: 52, padding: "6px 26px" }}>{r.price}</div>
              </At>
            )}
          </React.Fragment>
        );
      })}
    </AbsoluteFill>
  );
};

// ══ 5. DDayEquation — D-DAY 달력 → 화살표 → 산출량 공식 ═════════════════════════
// [ref4-apple 00:30:38] 달력 팝 → 약 2.4s 뒤 흰 화살표(알파+왼→오 이동 12f) → 제품 실루엣 2개 동시 팝(0.3→1.1→1) → 결과 텍스트 블러 해제
export const DDayEquationParams = z.object({
  calPop: num(6, 1, 20, 1, "달력 팝", "timing", "f"),
  arrowDelay: num(72, 0, 150, 1, "화살표 지연(약 2.4s)", "timing", "f"),
  arrowDur: num(12, 2, 40, 1, "화살표 등장", "timing", "f"),
  arrowTravel: num(60, 0, 200, 5, "화살표 이동 거리", "motion", "px"),
  iconDelay: num(8, 0, 60, 1, "제품 아이콘 지연", "timing", "f"),
  iconPop: num(6, 1, 20, 1, "아이콘 팝", "timing", "f"),
  textDelay: num(10, 0, 60, 1, "결과 텍스트 지연", "timing", "f"),
  textBlur: num(6, 1, 20, 1, "텍스트 블러 해제", "timing", "f"),
  calW: num(360, 150, 600, 5, "달력 폭", "size", "px"),
  textSize: num(110, 40, 200, 2, "결과 글자 크기", "size", "px"),
  header: col("#e0303a", "달력 헤더 색"),
  icon: col("#b0d0cc", "아이콘 색"),
  bg: col("#6b8384", "배경색"),
  pattern: col("#4a5f60", "배경 패턴 색"),
});
export type DDayEquationP = z.infer<typeof DDayEquationParams>;
export const DDayEquation: React.FC<{ at: number; head?: string; days?: string; result?: string; count?: number; icon?: RN; p?: Partial<DDayEquationP> }> = ({ at, head = "D-DAY", days = "30일", result = "하루에 2대", count = 2, icon, p }) => {
  const P = def(DDayEquationParams, p);
  const f = useCurrentFrame();
  const aAt = at + P.arrowDelay, iAt = aAt + P.arrowDur + P.iconDelay, tAt = iAt + P.iconPop + P.textDelay;
  const cw = P.calW, ch = cw * 0.95;
  const pat = Array.from({ length: 6 }).flatMap((_, r) => Array.from({ length: 11 }).map((__, c) => (
    <KitTint key={`${r}-${c}`} id="xc_pc" w={150} h={(150 * PC.h) / PC.w} color={P.pattern} style={{ position: "absolute", left: c * 190 - (r % 2) * 95 - 40 + 5, top: r * 200 - 60 + 2 }} />
  )));
  return (
    <AbsoluteFill style={{ background: P.bg }}>
      {pat}
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0) 40%, rgba(0,0,0,0.45) 100%)" }} />
      {f >= at && (
        <At x={440} y={560} s={pop(f, at, P.calPop, 0.2, 1.12)} blur={unblur(f, at, P.calPop * 0.6, 10)}>
          {/* 세모지 탁상 달력(desk_calendar) — 헤더·날짜 글자는 코드. 헤더 색은 그림 고정(빨강) */}
          <div style={{ width: cw * 1.1, height: cw * 1.1 * (997 / 1139), position: "relative", filter: "drop-shadow(0 8px 10px rgba(0,0,0,0.3))" }}>
            <Img src={prop("desk_calendar")} style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }} />
            <div style={{ position: "absolute", left: "10.8%", top: "5.4%", width: "80.9%", height: "17.4%", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontFamily: "NeoHv", fontSize: ch * 0.15 }}>{head}</div>
            <div style={{ position: "absolute", left: "10.8%", top: "25%", width: "80.9%", height: "66%", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "NeoHv", fontSize: ch * 0.32, color: "#111" }}>{days}</div>
          </div>
        </At>
      )}
      {f >= aAt && (
        <div style={{ position: "absolute", left: 700 + lerp(f, aAt, aAt + P.arrowDur, -P.arrowTravel, 0, E_OUT), top: 530, opacity: lerp(f, aAt, aAt + P.arrowDur, 0, 1) }}>
          <svg width={180} height={60}><rect x={0} y={24} width={140} height={12} rx={6} fill="#fff" /><polygon points="130,6 178,30 130,54" fill="#fff" /></svg>
        </div>
      )}
      {Array.from({ length: count }).map((_, i) => f >= iAt && (
        <At key={i} x={980 + i * 230} y={560} s={pop(f, iAt, P.iconPop, 0.3, 1.1)} blur={unblur(f, iAt, P.iconPop, 12)}>
          {icon ?? <PCIcon w={220} color={P.icon} />}
        </At>
      ))}
      {f >= tAt && (
        <At x={1390} y={560} blur={unblur(f, tAt, P.textBlur, 14)} op={kf(f, tAt, [0, 3], [0.3, 1])} style={{ transform: "translate(0,-50%)" }}>
          <div style={{ fontFamily: "NeoHv", fontSize: P.textSize, color: "#fff", whiteSpace: "nowrap", textShadow: "0 4px 10px rgba(0,0,0,0.35)" }}>{result}</div>
        </At>
      )}
    </AbsoluteFill>
  );
};

// ══ 6. DeviceTessellation — 기기 외곽 타일 채움 ═══════════════════════════════
// [ref4-apple 02:28:48] 중앙 기준 태블릿 정지 → 크기·방향이 다른 태블릿이 화면 가장자리부터 슬라이드인(2~3f 간격) → 화면 전체를 덮음
export const DeviceTessellationParams = z.object({
  startDelay: num(8, 0, 60, 1, "채움 시작 지연", "timing", "f"),
  stagger: num(1.2, 0.2, 6, 0.1, "타일 간격", "timing", "f"),
  enterDur: num(6, 1, 20, 1, "타일 진입 길이", "timing", "f"),
  slide: num(420, 0, 900, 10, "슬라이드 거리", "motion", "px"),
  cols: num(8, 3, 14, 1, "가로 칸 수", "size"),
  rows: num(5, 2, 9, 1, "세로 칸 수", "size"),
  sizeMin: num(0.85, 0.3, 1.5, 0.05, "최소 크기(칸 대비)", "size"),
  sizeMax: num(1.4, 0.5, 2, 0.05, "최대 크기(칸 대비)", "size"),
  heroW: num(150, 60, 400, 5, "기준 태블릿 폭", "size", "px"),
  bezel: num(8, 2, 20, 1, "베젤 두께", "size", "px"),
  screen: col("#6E6E6E", "화면 색"),
  bg: col("#C99A45", "배경색"),
});
export type DeviceTessellationP = z.infer<typeof DeviceTessellationParams>;
export const DeviceTessellation: React.FC<{ at: number; seed?: string; p?: Partial<DeviceTessellationP> }> = ({ at, seed = "tess", p }) => {
  const P = def(DeviceTessellationParams, p);
  const f = useCurrentFrame();
  const C = Math.round(P.cols), R = Math.round(P.rows), cw = W / C, chh = H / R;
  type T = { x: number; y: number; w: number; h: number; dx: number; dy: number; d: number };
  const tiles: T[] = [];
  for (let r = 0; r < R; r++) for (let c = 0; c < C; c++) {
    const k = `${seed}-${r}-${c}`;
    const x = (c + 0.5) * cw + (random(k + "x") - 0.5) * cw * 0.35, y = (r + 0.5) * chh + (random(k + "y") - 0.5) * chh * 0.35;
    if (Math.hypot(x - 960, y - 540) < P.heroW * 0.9) continue;
    const s = P.sizeMin + random(k + "s") * (P.sizeMax - P.sizeMin), land = random(k + "o") > 0.55;
    const base = Math.min(cw, chh) * s;
    const w = land ? base * 1.3 : base, h = land ? base : base * 1.3;
    const el = x, er = W - x, et = y, eb = H - y, m = Math.min(el, er, et, eb);
    const [dx, dy] = m === el ? [-1, 0] : m === er ? [1, 0] : m === et ? [0, -1] : [0, 1];
    tiles.push({ x, y, w, h, dx, dy, d: m });
  }
  tiles.sort((a, b) => a.d - b.d);
  const t0 = at + P.startDelay;
  return (
    <AbsoluteFill style={{ background: P.bg }}>
      <At x={960} y={540}><Tablet w={P.heroW} h={P.heroW * 1.3} bezel={P.bezel} screen={P.screen} /></At>
      {tiles.map((t, i) => {
        const s = t0 + i * P.stagger;
        if (f < s) return null;
        const u = lerp(f, s, s + P.enterDur, 1, 0, EXPO_OUT);
        return <At key={i} x={t.x + t.dx * P.slide * u} y={t.y + t.dy * P.slide * u}><Tablet w={t.w} h={t.h} bezel={P.bezel} screen={P.screen} /></At>;
      })}
    </AbsoluteFill>
  );
};

// ══ 7. RecordMilestoneBadge — 기록 달성 원형 배지 스텝업 ════════════════════════
// [ref4-apple 02:42:52] 회색 원 안 숫자 팝 + 양옆 색종이 점 분수 → 단계마다 숫자·날짜 크로스페이드 10f → 왕관 부착 → '전세계 최초' 스타버스트 → 비교 원
export const RecordMilestoneBadgeParams = z.object({
  numPop: num(6, 1, 20, 1, "숫자 팝", "timing", "f"),
  crossfade: num(10, 1, 30, 1, "단계 교체 크로스페이드", "timing", "f"),
  burstDur: num(45, 10, 120, 1, "색종이 지속", "timing", "f"),
  burstN: num(70, 0, 200, 1, "색종이 개수(한쪽)", "size"),
  crownPop: num(6, 1, 20, 1, "왕관 팝", "timing", "f"),
  crownRot: num(15, -45, 45, 1, "왕관 기울기", "motion", "°"),
  circleD: num(560, 300, 800, 10, "원 지름", "size", "px"),
  numSize: num(110, 40, 180, 2, "숫자 크기", "size", "px"),
  circle: col("#D9D8D5", "원 색"),
  numColor: col("#4A4A4A", "숫자 색"),
  bg: col("#F4F1EA", "배경색"),
});
export type RecordMilestoneBadgeP = z.infer<typeof RecordMilestoneBadgeParams>;
export type Milestone = { at: number; value: string; date?: string; crown?: boolean; burst?: boolean; star?: string };
export const RecordMilestoneBadge: React.FC<{ title?: string; steps: Milestone[]; watermark?: RN; compare?: { at: number; text: string }; p?: Partial<RecordMilestoneBadgeP> }> = ({ title = "애플", steps, watermark, compare, p }) => {
  const P = def(RecordMilestoneBadgeParams, p);
  const f = useCurrentFrame();
  const D = P.circleD, cx = compare ? 800 : 960, cy = 560;
  const cur = steps.filter((s) => f >= s.at);
  const crownStep = steps.find((s) => s.crown);
  const starStep = steps.find((s) => s.star);
  const conf: RN[] = [];
  steps.filter((s) => s.burst && f >= s.at).forEach((s, si) => {
    const g = f - s.at;
    if (g > P.burstDur) return;
    [-1, 1].forEach((side) => {
      for (let i = 0; i < P.burstN; i++) {
        const k = `rmb${si}${side}${i}`, delay = random(k + "d") * 10;
        const t = g - delay;
        if (t < 0) continue;
        const vx = -side * (4 + random(k + "vx") * 16), vy = -(22 + random(k + "vy") * 26);
        const x = (side < 0 ? 60 : W - 60) + vx * t, y = H + 20 + vy * t + 0.9 * t * t;
        const cc = ["#7b2ff7", "#c21fbd", "#e0409a", "#3b1fa8", "#ff5fa2"][i % 5];
        const sz = 6 + random(k + "s") * 8;
        conf.push(<rect key={k} x={x} y={y} width={sz} height={sz} fill={cc} opacity={lerp(g, P.burstDur * 0.7, P.burstDur, 1, 0)} transform={`rotate(${t * 20 + i * 37} ${x} ${y})`} />);
      }
    });
  });
  return (
    <AbsoluteFill style={{ background: P.bg }}>
      <div style={{ position: "absolute", left: cx - D / 2, top: cy - D / 2, width: D, height: D, borderRadius: "50%", background: P.circle }} />
      <div style={{ position: "absolute", left: cx - D / 2, top: cy - D / 2, width: D, height: D, display: "flex", alignItems: "center", justifyContent: "center", opacity: 0.35 }}>{watermark ?? <div style={{ width: D * 0.55, height: D * 0.55, borderRadius: "50%", border: `${D * 0.05}px solid #fff` }} />}</div>
      <div style={{ position: "absolute", left: cx - 200, top: cy - D * 0.36, width: 400, textAlign: "center", fontFamily: "NeoHv", fontSize: 40, color: "#8c8b88" }}>{title}</div>
      {cur.map((s, i) => {
        const next = cur[i + 1];
        const op = (i === 0 ? 1 : lerp(f, s.at, s.at + P.crossfade, 0, 1)) * (next ? lerp(f, next.at, next.at + P.crossfade, 1, 0) : 1);
        if (op <= 0) return null;
        return (
          <React.Fragment key={i}>
            <div style={{ position: "absolute", left: cx - 300, top: cy - D * 0.2, width: 600, textAlign: "center", fontFamily: "NeoEb", fontSize: 34, color: "#8c8b88", opacity: op }}>{s.date}</div>
            <At x={cx} y={cy + 20} s={i === 0 ? pop(f, s.at, P.numPop, 0.4, 1.12) : 1} op={op}>
              <div style={{ fontFamily: "NeoHv", fontSize: P.numSize, color: P.numColor, whiteSpace: "nowrap" }}>{s.value}</div>
            </At>
          </React.Fragment>
        );
      })}
      {crownStep && f >= crownStep.at && (
        <At x={cx + D * 0.36} y={cy - D * 0.4} s={pop(f, crownStep.at + 4, P.crownPop, 0.2, 1.15)} rot={P.crownRot}>
          <KitImg id="crown" w={150} />
        </At>
      )}
      {starStep && <Starburst text={starStep.star!} x={cx - D * 0.62} y={cy - D * 0.42} w={330} h={220} at={starStep.at + 6} />}
      {compare && f >= compare.at && (
        <>
          <div style={{ position: "absolute", left: cx + D / 2 + 40, top: cy - 30, opacity: lerp(f, compare.at, compare.at + 8, 0, 1) }}>
            <svg width={160} height={60}><rect x={0} y={24} width={120} height={12} rx={6} fill="#4A4A4A" /><polygon points="112,6 158,30 112,54" fill="#4A4A4A" /></svg>
          </div>
          <At x={cx + D / 2 + 420} y={cy} s={pop(f, compare.at + 6, 6, 0.3, 1.08)} blur={unblur(f, compare.at + 6, 5, 10)}>
            <div style={{ width: 380, height: 380, borderRadius: "50%", background: "#F5C49A", display: "flex", alignItems: "center", justifyContent: "center", textAlign: "center", fontFamily: "NeoHv", fontSize: 50, color: "#5a3a22", whiteSpace: "pre-line", lineHeight: 1.2 }}>{compare.text}</div>
          </At>
        </>
      )}
      <svg width={W} height={H} style={{ position: "absolute", pointerEvents: "none" }}>{conf}</svg>
    </AbsoluteFill>
  );
};

// ══ 8. FlagMapStatLink — 국기 채움 지도 + 점선 연결 통계 ════════════════════════
// [ref4-apple 02:00:37] 성조기 텍스처 국토 실루엣 팝 → 수치 글자 타이핑(2f/자) → 흰 점선 좌→우 10f → 원판 아이콘 큰 상태에서 팝 → 두번째 수치 타이핑
export const FlagMapStatLinkParams = z.object({
  mapPop: num(6, 1, 20, 1, "지도 팝", "timing", "f"),
  typeDelay: num(4, 0, 40, 1, "첫 수치 타이핑 지연", "timing", "f"),
  typePer: num(2, 0.5, 8, 0.5, "타이핑 글자당", "timing", "f"),
  lineDelay: num(30, 0, 120, 1, "점선 지연", "timing", "f"),
  lineDur: num(10, 2, 40, 1, "점선 드로우", "timing", "f"),
  iconPop: num(6, 1, 20, 1, "아이콘 팝", "timing", "f"),
  iconFrom: num(1.4, 0.2, 2.5, 0.05, "아이콘 시작 크기", "motion"),
  dash: num(14, 4, 40, 1, "점선 대시 길이", "size", "px"),
  numSize: num(76, 30, 140, 2, "수치 글자 크기", "size", "px"),
  iconD: num(360, 150, 560, 10, "아이콘 지름", "size", "px"),
  bg: col("#4E7F8F", "배경색"),
});
export type FlagMapStatLinkP = z.infer<typeof FlagMapStatLinkParams>;
export const FlagMapStatLink: React.FC<{ at: number; left: string; right: string; icon?: RN; p?: Partial<FlagMapStatLinkP> }> = ({ at, left, right, icon, p }) => {
  const P = def(FlagMapStatLinkParams, p);
  const f = useCurrentFrame();
  const geo = useGeo();
  const lAt = at + P.mapPop + P.lineDelay, iAt = lAt + P.lineDur, t2 = iAt + P.iconPop + 4;
  const ms = 0.52, ox = -50, oy = 250; // nation path(1920 기준) → 좌측 박스
  const bx = 140 * ms + ox, by = 150 * ms + oy, bw = 1640 * ms, bh = 850 * ms;
  const stripes = Array.from({ length: 13 }).map((_, i) => <rect key={i} x={bx} y={by + (i * bh) / 13} width={bw} height={bh / 13 + 0.5} fill={i % 2 ? "#fff" : "#E0484F"} />);
  const cantonW = bw * 0.42, cantonH = (bh * 7) / 13;
  const stars: RN[] = [];
  for (let r = 0; r < 9; r++) for (let c = 0; c < 11; c++) if ((r + c) % 2 === 0) stars.push(<circle key={`${r}-${c}`} cx={bx + (c + 0.6) * (cantonW / 11.2)} cy={by + (r + 0.6) * (cantonH / 9.3)} r={4.5} fill="#fff" />);
  const x0 = 870, x1 = 1220, ly = 560;
  const lp = lerp(f, lAt, lAt + P.lineDur, 0, 1, Easing.linear);
  return (
    <AbsoluteFill style={{ background: P.bg }}>
      {geo && f >= at && (
        <svg width={W} height={H} style={{ position: "absolute", transformOrigin: `${bx + bw / 2}px ${by + bh / 2}px`, transform: `scale(${pop(f, at, P.mapPop, 0.4, 1.08)})` }}>
          <defs><clipPath id="xc-us"><path d={geo.us.nation} transform={`translate(${ox},${oy}) scale(${ms})`} /></clipPath></defs>
          <g clipPath="url(#xc-us)">{stripes}<rect x={bx} y={by} width={cantonW} height={cantonH} fill="#2E3E78" />{stars}</g>
        </svg>
      )}
      <div style={{ position: "absolute", left: 60, top: 170, fontFamily: "NeoHv", fontSize: P.numSize, color: "#111", whiteSpace: "nowrap" }}>{typed(left, f, at + P.mapPop + P.typeDelay, P.typePer)}</div>
      {f >= lAt && <svg width={W} height={H} style={{ position: "absolute" }}><line x1={x0} y1={ly} x2={x0 + (x1 - x0) * lp} y2={ly} stroke="#fff" strokeWidth={5} strokeDasharray={`${P.dash} ${P.dash * 0.7}`} /></svg>}
      {f >= iAt && (
        <At x={x1 + P.iconD / 2 + 40} y={ly} s={kf(f, iAt, [0, d1(P.iconPop)], [P.iconFrom, 1], E_OUT)} op={kf(f, iAt, [0, 2], [0.4, 1])} blur={unblur(f, iAt, P.iconPop * 0.6, 8)}>
          {icon ?? (
            <KitImg id="record_disc" w={P.iconD} style={{ filter: "drop-shadow(0 8px 12px rgba(0,0,0,0.25))" }} />
          )}
        </At>
      )}
      <div style={{ position: "absolute", left: 1150, top: 170, fontFamily: "NeoHv", fontSize: P.numSize, color: "#111", whiteSpace: "nowrap" }}>{typed(right, f, t2, P.typePer)}</div>
    </AbsoluteFill>
  );
};

// ══ 9. PictogramCrowdMarquee — 픽토그램 군중 행진 채움 ══════════════════════════
// [ref4-cocacola 00:00:01] 세계지도 위로 사람 픽토그램 행이 번갈아 방향으로 흘러 들어와 화면을 채움 → 라벨 칩 페이드아웃 → 병 실루엣 '?' 팝 → 말풍선
export const PictogramCrowdMarqueeParams = z.object({
  rows: num(5, 1, 9, 1, "행 수", "size"),
  personH: num(150, 50, 260, 2, "픽토그램 높이", "size", "px"),
  spacing: num(96, 40, 260, 1, "픽토그램 간격", "size", "px"),
  rowStagger: num(10, 0, 40, 1, "행 시작 간격", "timing", "f"),
  fillDur: num(32, 6, 90, 1, "한 행이 채워지는 시간", "timing", "f"),
  drift: num(1.5, 0, 10, 0.1, "채운 뒤 흐름 속도", "motion", "px/f"),
  chipFade: num(12, 1, 40, 1, "라벨 칩 페이드아웃", "timing", "f"),
  bottleDelay: num(58, 0, 150, 1, "병 등장 지연(첫 행 기준)", "timing", "f"),
  bottlePop: num(6, 1, 20, 1, "병 팝", "timing", "f"),
  bubbleDelay: num(12, 0, 60, 1, "말풍선 지연", "timing", "f"),
  person: col("#3a3a3a", "픽토그램 색"),
  land: col("#5DBB3F", "대륙 색"),
  bg: col("#c1e6f5", "바다 색"),
});
export type PictogramCrowdMarqueeP = z.infer<typeof PictogramCrowdMarqueeParams>;
export const PictogramCrowdMarquee: React.FC<{ at: number; chip?: [string, string, string]; bubble?: string; hero?: RN; p?: Partial<PictogramCrowdMarqueeP> }> = ({ at, chip = ["전 세계 ", "200개", " 국가"], bubble = "내 라이벌?", hero, p }) => {
  const P = def(PictogramCrowdMarqueeParams, p);
  const f = useCurrentFrame();
  const geo = useGeo();
  const R = Math.round(P.rows), top = 60, bot = H - 40, rowGap = (bot - top - P.personH) / Math.max(1, R - 1);
  const bAt = at + P.bottleDelay, bbAt = bAt + P.bottlePop + P.bubbleDelay;
  const rowsEl = Array.from({ length: R }).map((_, r) => {
    const s = at + r * P.rowStagger;
    if (f < s) return null;
    const dir = r % 2 === 0 ? 1 : -1;
    const t = f - s;
    const lead = -P.spacing + (W + P.spacing * 2) * Easing.out(Easing.quad)(Math.min(1, t / P.fillDur)) + t * P.drift;
    const y = top + r * rowGap;
    const items: RN[] = [];
    for (let k = 0; k < 60; k++) {
      const d = lead - k * P.spacing;
      if (d < -P.spacing) break;
      if (d > W + P.spacing) continue;
      const x = dir > 0 ? d : W - d;
      // 세모지 캐스트가 행 방향으로 걸어감(캐스트·seed = 행·순번). person 색 변수는 호환용(캐릭터 제 옷색)
      items.push(<CastFig key={k} cast={castOf(`pcm${r}-${k}`)} h={P.personH} walking flip={dir < 0} seed={`pcm${r}-${k}`} style={{ position: "absolute", left: x - (P.personH * 0.42) / 2, top: y }} />);
    }
    return <React.Fragment key={r}>{items}</React.Fragment>;
  });
  const bs = f >= bAt ? kf(f, bAt, [0, P.bottlePop * 0.6, P.bottlePop], [0.3, 1.05, 1]) : 0;
  const vblur = f >= bAt ? kf(f, bAt, [0, P.bottlePop], [18, 0]) : 0;
  return (
    <AbsoluteFill style={{ background: P.bg }}>
      {geo && <svg width={W} height={H} style={{ position: "absolute" }}><path d={geo.world.land} fill={P.land} /></svg>}
      {f < at + P.chipFade + 30 && (
        <At x={640} y={900} op={f < at ? 1 : lerp(f, at + 10, at + 10 + P.chipFade, 1, 0)}>
          <div style={{ background: "#1f2d5c", color: "#fff", fontFamily: "NeoHv", fontSize: 60, padding: "12px 34px", whiteSpace: "nowrap" }}>{chip[0]}<span style={{ color: "#F7D84A" }}>{chip[1]}</span>{chip[2]}</div>
        </At>
      )}
      {rowsEl}
      {f >= bAt && (
        <At x={1000} y={600} s={bs} sy={1 + vblur * 0.015} blur={0} style={{ filter: `blur(${vblur * 0.4}px)` }}>
          {hero ?? (
            <div style={{ position: "relative", width: 260, height: 650 }}>
              {/* 세모지 병 실루엣(bottle_silhouette_q) 검정 틴트 + 회색 '?' 코드 */}
              <KitTint id="bottle_silhouette_q" w={(650 * 374) / 1336} h={650} color="#111" style={{ position: "absolute", left: 130 - (650 * 374) / 1336 / 2, top: 0 }} />
              <div style={{ position: "absolute", left: 0, top: 650 * 0.63, width: 260, transform: "translateY(-62%)", textAlign: "center", fontFamily: "NeoHv", fontSize: 150, color: "#8a8a8a", lineHeight: 1 }}>?</div>
            </div>
          )}
        </At>
      )}
      {f >= bbAt && (
        <At x={1370} y={330} blur={unblur(f, bbAt, 5, 12)} op={kf(f, bbAt, [0, 3], [0.3, 1])}>
          <div style={{ position: "relative", background: "#fff", borderRadius: 60, padding: "26px 46px", fontFamily: "NeoHv", fontSize: 64, color: "#111", whiteSpace: "nowrap", boxShadow: "0 8px 16px rgba(0,0,0,0.2)" }}>
            {bubble}
            <div style={{ position: "absolute", left: 40, bottom: -36, width: 0, height: 0, borderTop: "40px solid #fff", borderLeft: "20px solid transparent", borderRight: "36px solid transparent" }} />
          </div>
        </At>
      )}
    </AbsoluteFill>
  );
};

// ══ 10. ProductAnchorValuePill — 제품 앵커 수치 필 + 수요/공급 바 ═══════════════
// [ref4-cocacola 00:08:03] 제품 팝(0.2→1.25→1) → 빨간 캡슐이 제품 뒤에서 오른쪽으로 8f 늘어남(가로 모션블러) → 흰 수치 컷인 → 수요 바 20f 성장·공급 바 짧게 멈춤 → 땀방울
export const ProductAnchorValuePillParams = z.object({
  prodPop: num(6, 1, 20, 1, "제품 팝", "timing", "f"),
  pillDelay: num(10, 0, 60, 1, "캡슐 지연", "timing", "f"),
  pillGrow: num(8, 2, 30, 1, "캡슐 늘어남", "timing", "f"),
  textDelay: num(2, 0, 20, 1, "수치 컷인 지연", "timing", "f"),
  barDelay: num(24, 0, 90, 1, "수요/공급 바 지연", "timing", "f"),
  barDur: num(20, 4, 60, 1, "수요 바 성장", "timing", "f"),
  supplyRatio: num(0.45, 0.05, 1, 0.01, "공급/수요 비율", "motion"),
  pillW: num(1000, 400, 1500, 10, "캡슐 길이", "size", "px"),
  pillH: num(420, 150, 600, 10, "캡슐 높이", "size", "px"),
  textSize: num(130, 50, 220, 2, "수치 글자 크기", "size", "px"),
  pill: col("#eb1029", "캡슐 색"),
  demand: col("#2f6fd6", "수요 바 색"),
  supply: col("#3fae49", "공급 바 색"),
  bg: col("#ece4ea", "배경색"),
});
export type ProductAnchorValuePillP = z.infer<typeof ProductAnchorValuePillParams>;
export const ProductAnchorValuePill: React.FC<{ at: number; value: string; product?: RN; labels?: [string, string]; mapBg?: boolean; p?: Partial<ProductAnchorValuePillP> }> = ({ at, value, product, labels = ["수요량", "공급량"], mapBg = true, p }) => {
  const P = def(ProductAnchorValuePillParams, p);
  const f = useCurrentFrame();
  const geo = useGeo();
  const px = 520, py = 560, pAt = at + P.prodPop + P.pillDelay, tAt = pAt + P.pillGrow + P.textDelay, bAt = tAt + P.barDelay;
  const gw = f >= pAt ? lerp(f, pAt, pAt + P.pillGrow, P.pillH, P.pillW, E_OUT) : 0;
  const mblur = f >= pAt && f < pAt + P.pillGrow ? 10 : 0;
  const left = px - 40, top = py - P.pillH / 2;
  const dW = (P.pillW - P.pillH * 0.9) * 0.78;
  const bar = (i: number) => {
    const s = bAt + i * 4;
    if (f < s) return null;
    const full = i === 0 ? dW : dW * P.supplyRatio;
    const w = lerp(f, s, s + (i === 0 ? P.barDur : P.barDur * P.supplyRatio), 0, full, E_OUT);
    return (
      <div key={i} style={{ position: "absolute", left: left + P.pillH * 0.62, top: top + P.pillH * (0.56 + i * 0.2), height: P.pillH * 0.15, display: "flex", alignItems: "center", gap: 14, opacity: kf(f, s, [0, 3], [0, 1]) }}>
        <div style={{ width: 150, fontFamily: "NeoHv", fontSize: P.pillH * 0.085, color: "#fff" }}>{labels[i]}</div>
        <div style={{ width: w, height: P.pillH * 0.12, borderRadius: 999, background: i === 0 ? P.demand : P.supply }} />
      </div>
    );
  };
  const dropAt = bAt + P.barDur + 6;
  return (
    <AbsoluteFill style={{ background: P.bg }}>
      {mapBg && geo && <svg width={W} height={H} style={{ position: "absolute", filter: "blur(9px)", opacity: 0.55 }}><path d={geo.us.nation} fill="#8a8a8a" /></svg>}
      {f >= pAt && (
        <div style={{ position: "absolute", left, top, width: gw, height: P.pillH, background: P.pill, borderRadius: `0 ${P.pillH / 2}px ${P.pillH / 2}px 0`, filter: mblur ? `blur(${mblur}px)` : undefined }} />
      )}
      {f >= tAt && <div style={{ position: "absolute", left: left + P.pillH * 0.62, top: top + P.pillH * 0.1, fontFamily: "NeoHv", fontSize: P.textSize, color: "#fff", whiteSpace: "nowrap" }}>{value}</div>}
      {bar(0)}{bar(1)}
      {f >= dropAt && (
        <At x={left + P.pillW - 40} y={top + 20} s={pop(f, dropAt, 6, 0.3, 1.15)} rot={20}>
          <svg width={70} height={100} viewBox="0 0 70 100"><path d="M35,0 Q70,50 66,68 Q62,98 35,98 Q8,98 4,68 Q0,50 35,0Z" fill="#6ec6f2" /><ellipse cx={24} cy={66} rx={7} ry={12} fill="#fff" opacity={0.7} /></svg>
        </At>
      )}
      {f >= at && <At x={px} y={py} s={pop(f, at, P.prodPop, 0.2, 1.25)} blur={unblur(f, at, P.prodPop * 0.6, 10)}>{product ?? <Jug w={330} />}</At>}
    </AbsoluteFill>
  );
};

// ══ 11. MapSpreadPullback — 확산 풀백(아이콘 증식) + 레이더 파문 ═════════════════
// [ref4-cocacola 00:07:53] 출발지(조지아) 3x 확대 → 45f 풀백, 새로 화면에 들어온 주마다 아이콘 팝(2~3f 간격) → 출발지 빨간 동심원 3겹 호흡
export const MapSpreadPullbackParams = z.object({
  z0: num(3, 1, 6, 0.1, "시작 배율", "motion"),
  pullDelay: num(6, 0, 60, 1, "풀백 시작 지연", "timing", "f"),
  pullDur: num(45, 6, 120, 1, "풀백 길이", "timing", "f"),
  iconStagger: num(2.5, 0, 10, 0.5, "아이콘 팝 간격", "timing", "f"),
  iconPop: num(4, 1, 12, 1, "아이콘 팝", "timing", "f"),
  iconSize: num(44, 16, 100, 2, "아이콘 크기(1x)", "size", "px"),
  ringPeriod: num(20, 6, 60, 1, "파문 호흡 주기", "timing", "f"),
  ringR: num(200, 60, 400, 5, "파문 최대 반지름", "size", "px"),
  border: num(2, 0, 8, 0.5, "주 경계선 두께", "size", "px"),
  ring: col("#d2172b", "파문 색"),
  map: col("#8a8a8a", "지도 색"),
  bg: col("#ede6ea", "배경색"),
});
export type MapSpreadPullbackP = z.infer<typeof MapSpreadPullbackParams>;
export const MapSpreadPullback: React.FC<{ at: number; origin?: string; label?: string; icon?: RN; p?: Partial<MapSpreadPullbackP> }> = ({ at, origin = "Georgia", label = "애틀랜타", icon, p }) => {
  const P = def(MapSpreadPullbackParams, p);
  const f = useCurrentFrame();
  const geo = useGeo();
  if (!geo) return <AbsoluteFill style={{ background: P.bg }} />;
  const st = geo.us.states;
  const o = st.find((s) => s.name === origin) ?? st[0];
  const s0 = at + P.pullDelay, s1 = s0 + P.pullDur;
  const cam = (fr: number) => {
    const u = lerp(fr, s0, s1, 0, 1, E_IO);
    const z = P.z0 + (1 - P.z0) * u;
    return { z, cx: o.c[0] + (960 - o.c[0]) * u, cy: o.c[1] + (575 - o.c[1]) * u };
  };
  const vis = (c: Pt, fr: number) => { const k = cam(fr); const x = (c[0] - k.cx) * k.z + 960, y = (c[1] - k.cy) * k.z + 540; return x > 20 && x < W - 20 && y > 20 && y < H - 20; };
  // 각 주가 처음 화면에 들어오는 프레임 → 간격 보정
  const order = st.filter((s) => s !== o).map((s) => { let e = s1; for (let fr = s0; fr <= s1; fr++) if (vis(s.c, fr)) { e = fr; break; } return { s, e }; }).sort((a, b) => a.e - b.e);
  let last = -1e9;
  const popAt = new Map<string, number>();
  order.forEach(({ s, e }) => { const t = Math.max(e, last + P.iconStagger); popAt.set(s.id, t); last = t; });
  const k = cam(f);
  const I = P.iconSize;
  const iconEl = (c: Pt, s: number, key: string) => (
    <div key={key} style={{ position: "absolute", left: c[0], top: c[1], transform: `translate(-50%,-60%) scale(${s})` }}>{icon ?? <Jug w={I} />}</div>
  );
  const rEnd = s1 + 4;
  return (
    <AbsoluteFill style={{ background: P.bg, overflow: "hidden" }}>
      <div style={{ position: "absolute", left: 0, top: 0, width: W, height: H, transformOrigin: "0 0", transform: `translate(${960 - k.cx * k.z}px,${540 - k.cy * k.z}px) scale(${k.z})` }}>
        <svg width={W} height={H} style={{ position: "absolute", overflow: "visible" }}>
          {st.map((s) => <path key={s.id} d={s.d} fill={P.map} stroke="#fff" strokeWidth={P.border / k.z} strokeLinejoin="round" />)}
          {f >= rEnd && [1, 0.66, 0.33].map((r, i) => {
            const br = 0.85 + 0.15 * Math.sin(((f - rEnd) / P.ringPeriod) * TAU - i * 0.6);
            return <circle key={i} cx={o.c[0]} cy={o.c[1]} r={(P.ringR * r * br * lerp(f, rEnd, rEnd + 8, 0.3, 1, E_OUT)) / k.z} fill={P.ring} opacity={[0.25, 0.45, 0.8][i]} />;
          })}
        </svg>
        {f >= at && iconEl(o.c, 1, "o")}
        {st.filter((s) => s !== o).map((s) => { const t = popAt.get(s.id)!; return f >= t ? iconEl(s.c, kf(f, t, [0, P.iconPop], [0, 1], Easing.out(Easing.back(2))), s.id) : null; })}
        {label && <div style={{ position: "absolute", left: o.c[0] - 150, top: o.c[1] - I * 1.6 - 40, width: 300, textAlign: "center", fontFamily: "Yeonsung", fontSize: 30, color: "#333", opacity: lerp(f, s0, s0 + 10, 1, 0) }}>{label}</div>}
      </div>
    </AbsoluteFill>
  );
};

// ══ 12. BottomUpRankStack — 역순 순위 리스트 적층 ══════════════════════════════
// [ref4-cocacola 00:17:29] 검은 배경, 왼쪽 완성 목록 + 오른쪽은 최하위가 맨 아래에 먼저 생기고 윗순위가 그 위 칸에 1px 선→scaleY 3f 로 펼쳐지며 쌓임(12f 간격, 기존 행은 고정)
//   ※ 원본 대조: 기존 행이 밀려 올라가지 않는다(그러면 순서가 뒤집힘) — 하단 앵커 위로 적층
export const BottomUpRankStackParams = z.object({
  titleBlur: num(6, 1, 20, 1, "제목 블러 해제", "timing", "f"),
  firstDelay: num(10, 0, 60, 1, "첫 행 지연", "timing", "f"),
  rowGap: num(12, 2, 40, 1, "행 간격", "timing", "f"),
  unfold: num(3, 1, 12, 1, "행 펼침", "timing", "f"),
  rowW: num(640, 300, 900, 10, "행 폭", "size", "px"),
  rowH: num(62, 30, 110, 1, "행 높이", "size", "px"),
  pitch: num(80, 40, 140, 1, "행 피치", "size", "px"),
  hi: col("#c8102e", "강조 행 색"),
  bg: col("#000000", "배경색"),
});
export type BottomUpRankStackP = z.infer<typeof BottomUpRankStackParams>;
export type RankRow = { label: string; color?: string; dot?: string };
const Trophy: React.FC<{ s?: number }> = ({ s = 44 }) => (
  <KitImg id="trophy_icon" w={s} h={s} />
);
export const BottomUpRankStack: React.FC<{ at: number; title?: string; rows: RankRow[]; side?: { title: string; rows: RankRow[] }; p?: Partial<BottomUpRankStackP> }> = ({ at, title = "브랜드 순위", rows, side, p }) => {
  const P = def(BottomUpRankStackParams, p);
  const f = useCurrentFrame();
  const N = rows.length, baseY = 960;
  const rowEl = (r: RankRow, rank: number, key: string, x: number, y: number, sy = 1) => (
    <div key={key} style={{ position: "absolute", left: x, top: y - P.rowH / 2, width: P.rowW, height: P.rowH, transform: `scaleY(${Math.max(1 / P.rowH, sy)})`, borderRadius: P.rowH * 0.18, background: r.color ?? "#fff", display: "flex", alignItems: "center", gap: 18, paddingLeft: 12, boxSizing: "border-box" }}>
      <div style={{ width: P.rowH * 0.72, height: P.rowH * 0.72, borderRadius: "50%", background: r.dot ?? "#d8203a", color: "#fff", fontFamily: "NeoHv", fontSize: P.rowH * 0.42, display: "flex", alignItems: "center", justifyContent: "center" }}>{rank}</div>
      <div style={{ fontFamily: "NeoHv", fontSize: P.rowH * 0.5, color: r.color ? "#fff" : "#1a1a1a" }}>{r.label}</div>
    </div>
  );
  const head = (t: string, x: number, blur: number, op: number) => (
    <div style={{ position: "absolute", left: x, top: 90, display: "flex", alignItems: "center", gap: 14, filter: blur > 0.05 ? `blur(${blur}px)` : undefined, opacity: op }}>
      <Trophy /><div style={{ fontFamily: "NeoHv", fontSize: 54, color: "#fff" }}>{t}</div>
    </div>
  );
  const sx = side ? 1060 : 640, lx = 180;
  const rt = (i: number) => at + P.firstDelay + i * P.rowGap; // i = 등장 순서(0 = 최하위)
  return (
    <AbsoluteFill style={{ background: P.bg }}>
      {side && head(side.title, lx, 0, 1)}
      {side && side.rows.map((r, i) => rowEl(r, i + 1, `s${i}`, lx, 220 + i * P.pitch))}
      {f >= at && head(title, sx, unblur(f, at, P.titleBlur, 12), kf(f, at, [0, 3], [0.3, 1]))}
      {rows.map((r, idx) => {
        const i = N - 1 - idx; // 등장 순서
        const t = rt(i);
        if (f < t) return null;
        const sy = kf(f, t, [0, P.unfold], [0, 1], E_OUT);
        return rowEl(r, idx + 1, `r${idx}`, sx, baseY - i * P.pitch, sy);
      })}
    </AbsoluteFill>
  );
};

// ══ 13. EsportsVsScoreboard — 대진 배너 + 7세그 스코어보드 ══════════════════════
// [ref4-cocacola 00:20:40] 사진 하단 물결 와이프(4f) → 우주 배경 별 스트릭 6f → VS 배너 1.4→1 낙하 6f(블러) → 엠블럼 5f 슬라이드인 → 상단 탭 → 7세그 '0 0' 3f 페이드업
export const EsportsVsScoreboardParams = z.object({
  wipeDur: num(4, 1, 20, 1, "물결 와이프", "timing", "f"),
  warpDur: num(6, 0, 30, 1, "별 스트릭", "timing", "f"),
  bannerDrop: num(6, 1, 20, 1, "배너 낙하", "timing", "f"),
  bannerFrom: num(1.4, 1, 3, 0.05, "배너 시작 크기", "motion"),
  emblemSlide: num(5, 1, 20, 1, "엠블럼 슬라이드인", "timing", "f"),
  tabDelay: num(4, 0, 30, 1, "상단 탭 지연", "timing", "f"),
  digitDelay: num(22, 0, 90, 1, "숫자판 지연", "timing", "f"),
  digitFade: num(3, 1, 12, 1, "숫자판 페이드업", "timing", "f"),
  bannerW: num(1500, 900, 1900, 10, "배너 폭", "size", "px"),
  digitW: num(220, 100, 360, 5, "숫자 칸 폭", "size", "px"),
  left: col("#d8203a", "왼쪽 팀 색"),
  right: col("#13b5a0", "오른쪽 팀 색"),
  shield: col("#034994", "VS 방패 색"),
  bg: col("#002442", "우주 배경색"),
});
export type EsportsVsScoreboardP = z.infer<typeof EsportsVsScoreboardParams>;
const SEG: Record<string, string> = { "0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd", "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg", "-": "g" };
const Seg7: React.FC<{ ch: string; w: number; on?: string; off?: string }> = ({ ch, w, on = "#fff", off = "rgba(255,255,255,0.06)" }) => {
  const h = w * 1.32, t = w * 0.1, m = w * 0.16, L = SEG[ch] ?? "";
  const hs = (x: number, y: number) => `${x + t / 2},${y} ${x + t},${y - t / 2} ${x + (w - 2 * m) - t},${y - t / 2} ${x + (w - 2 * m) - t / 2},${y} ${x + (w - 2 * m) - t},${y + t / 2} ${x + t},${y + t / 2}`;
  const vs = (x: number, y: number, len: number) => `${x},${y + t / 2} ${x + t / 2},${y + t} ${x + t / 2},${y + len - t} ${x},${y + len - t / 2} ${x - t / 2},${y + len - t} ${x - t / 2},${y + t}`;
  const x0 = m, y0 = m, hh = (h - 2 * m) / 2, ww = w - 2 * m;
  const segs: Record<string, string> = { a: hs(x0, y0), g: hs(x0, y0 + hh), d: hs(x0, y0 + 2 * hh), f: vs(x0, y0, hh), b: vs(x0 + ww, y0, hh), e: vs(x0, y0 + hh, hh), c: vs(x0 + ww, y0 + hh, hh) };
  return (
    <div style={{ width: w, height: h, background: "#0b1a2e", border: "6px solid #fff", borderRadius: w * 0.1, boxSizing: "border-box", position: "relative" }}>
      <svg width={w} height={h} style={{ position: "absolute", left: -6, top: -6 }}>{Object.entries(segs).map(([k, pts]) => <polygon key={k} points={pts} fill={L.includes(k) ? on : off} />)}</svg>
    </div>
  );
};
export const EsportsVsScoreboard: React.FC<{ at: number; photo?: string; teams?: [string, string]; tab?: string; score?: [string, string]; stamp?: { text: string; at: number }; p?: Partial<EsportsVsScoreboardP> }> = ({ at, photo = "real/chunjang.jpg", teams = ["짜장면", "짬뽕"], tab = "중식대전쟁", score = ["0", "0"], stamp, p }) => {
  const P = def(EsportsVsScoreboardParams, p);
  const f = useCurrentFrame();
  const wEnd = at + P.wipeDur, bAt = wEnd + P.warpDur, dAt = bAt + P.bannerDrop + P.digitDelay;
  const g = Math.max(0, f - at);
  const stars = Array.from({ length: 70 }).map((_, i) => {
    const x = random(`evs-x${i}`) * W, y = random(`evs-y${i}`) * H, r = 1 + random(`evs-r${i}`) * 2.6;
    const tw = 0.5 + 0.5 * Math.sin(f * 0.2 + i);
    return <circle key={i} cx={(x - g * 0.3 + W) % W} cy={y} r={r} fill="#fff" opacity={0.35 + 0.5 * tw} />;
  });
  const warp = f >= wEnd && f < bAt + 4 ? Array.from({ length: 26 }).map((_, i) => {
    const t = (f - wEnd) / Math.max(1, P.warpDur + 4);
    const x = random(`wp-x${i}`) * W * 1.2 - 200 + t * 700, y = random(`wp-y${i}`) * H - 100 + t * 400, L = 90 + random(`wp-l${i}`) * 160;
    return <line key={i} x1={x} y1={y} x2={x + L} y2={y + L * 0.55} stroke="#fff" strokeWidth={3 + random(`wp-w${i}`) * 4} strokeLinecap="round" opacity={0.7 * (1 - t)} />;
  }) : null;
  const wave = (() => {
    const lv = lerp(f, at, wEnd, H + 60, -80, Easing.in(Easing.quad));
    const pts: string[] = ["0,0", `${W},0`];
    for (let x = W; x >= 0; x -= 40) pts.push(`${x},${lv + Math.sin(x / 90 + f) * 30}`);
    return `polygon(${pts.map((s) => s.split(",").map((v) => `${v}px`).join(" ")).join(",")})`;
  })();
  const BW = P.bannerW, by = 330;
  const bs = f >= bAt ? kf(f, bAt, [0, d1(P.bannerDrop)], [P.bannerFrom, 1], E_OUT) : 0;
  const bb = f >= bAt ? kf(f, bAt, [0, d1(P.bannerDrop)], [10, 0]) : 0;
  const eIn = (side: number) => (f >= bAt + 2 ? lerp(f, bAt + 2, bAt + 2 + P.emblemSlide, side * 500, 0, E_OUT) : side * 500);
  const ufoX = 250 + g * 1.2, moonX = 1560;
  return (
    <AbsoluteFill style={{ background: P.bg }}>
      <svg width={W} height={H} style={{ position: "absolute" }}>
        {stars}
      </svg>
      {/* 세모지 달(moon)·UFO(ufo) */}
      <KitImg id="moon" w={92} style={{ position: "absolute", left: moonX - 46, top: 200 - 46 }} />
      <KitImg id="ufo" w={190} style={{ position: "absolute", left: ufoX - 95, top: 820 + Math.sin(g * 0.1) * 12 - propH("ufo", 190) * 0.62, transform: "rotate(-12deg)" }} />
      <svg width={W} height={H} style={{ position: "absolute" }}>{warp}</svg>
      {f >= bAt && (
        <div style={{ position: "absolute", left: 960 - BW / 2, top: by - 70, width: BW, height: 140, transform: `scale(${bs})`, filter: bb > 0.1 ? `blur(${bb}px)` : undefined }}>
          <div style={{ position: "absolute", left: 60, top: 18, width: BW / 2 - 60, height: 104, background: P.left, borderRadius: "52px 0 0 52px", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "NeoHv", fontSize: 58, color: "#fff" }}>{teams[0]}</div>
          <div style={{ position: "absolute", left: BW / 2, top: 18, width: BW / 2 - 60, height: 104, background: P.right, borderRadius: "0 52px 52px 0", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "NeoHv", fontSize: 58, color: "#fff" }}>{teams[1]}</div>
          {/* 세모지 VS 방패(vs_shield_emblem) — 'VS' 코드. 방패 색은 그림 고정(남색) */}
          <div style={{ position: "absolute", left: BW / 2 - 85, top: -30, width: 170, height: 192 }}>
            <KitImg id="vs_shield_emblem" w={170} h={192} />
            <div style={{ position: "absolute", left: 0, top: 0, width: 170, height: 192, display: "flex", alignItems: "center", justifyContent: "center", paddingBottom: 18, boxSizing: "border-box", fontFamily: "NeoHv", fontSize: 66, color: "#fff" }}>VS</div>
          </div>
          {f >= bAt + P.tabDelay && <div style={{ position: "absolute", left: BW / 2 - 190, top: -84, width: 380, height: 64, background: "#12306a", clipPath: "polygon(8% 0, 92% 0, 100% 100%, 0 100%)", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "Jua", fontSize: 40, color: "#fff", opacity: kf(f, bAt + P.tabDelay, [0, 3], [0, 1]) }}>{tab}</div>}
        </div>
      )}
      {f >= bAt && [-1, 1].map((s) => (
        <div key={s} style={{ position: "absolute", left: 960 + s * (BW / 2 + 10) - 80 + eIn(s), top: by - 80, width: 160, height: 160, borderRadius: "50%", background: "#fff", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 6px 12px rgba(0,0,0,0.35)" }}>
          <div style={{ width: 96, height: 96, borderRadius: "50%", background: s < 0 ? P.left : P.right }} />
        </div>
      ))}
      {f >= dAt && [0, 1].map((i) => (
        <At key={i} x={960 + (i ? 1 : -1) * P.digitW * 0.75} y={720} s={kf(f, dAt, [0, d1(P.digitFade)], [0.5, 1])} op={kf(f, dAt, [0, d1(P.digitFade)], [0, 1])}>
          <Seg7 ch={score[i]} w={P.digitW} />
        </At>
      ))}
      {f < wEnd && <AbsoluteFill style={{ clipPath: f >= at ? wave : undefined }}><Img src={src(photo)} style={{ width: "100%", height: "100%", objectFit: "cover" }} /></AbsoluteFill>}
      {stamp && <Stamp text={stamp.text} x={1480} y={720} at={stamp.at} />}
    </AbsoluteFill>
  );
};

// ══ 14. SegmentedThermometerDrain — 세그먼트 온도계 배출 ═════════════════════════
// [ref4-cocacola 00:20:32] 5칸 온도계가 위 칸부터 원색→핑크→흰색으로 한 칸씩 빠짐(칸당 5f, 계단식 약 40f) + 스프레이 노즐에서 흰 점선 호가 0→250px 성장·흐름
export const SegmentedThermometerDrainParams = z.object({
  segDur: num(5, 1, 20, 1, "칸 탈색 시간", "timing", "f"),
  segGap: num(8, 1, 30, 1, "칸 간격", "timing", "f"),
  sprayDelay: num(0, -30, 60, 1, "스프레이 시작 지연", "timing", "f"),
  sprayDur: num(40, 6, 120, 1, "스프레이 성장 시간", "timing", "f"),
  sprayLen: num(250, 60, 600, 10, "스프레이 길이", "size", "px"),
  flow: num(2, 0, 10, 0.5, "점선 흐름 속도", "motion", "px/f"),
  thermoH: num(520, 300, 800, 10, "온도계 높이", "size", "px"),
  bulb: col("#8cc63f", "구근 색"),
  bg: col("#7794ba", "배경색"),
});
export type SegmentedThermometerDrainP = z.infer<typeof SegmentedThermometerDrainParams>;
export const SegmentedThermometerDrain: React.FC<{ at: number; colors?: string[]; can?: RN; p?: Partial<SegmentedThermometerDrainP> }> = ({ at, colors = ["#c0102a", "#e0371f", "#f08a1c", "#f5c518", "#d8e03a"], can, p }) => {
  const P = def(SegmentedThermometerDrainParams, p);
  const f = useCurrentFrame();
  const tx = 420, th = P.thermoH, tw = 84, top = 170, bulbR = 78;
  const segH = (th - 20) / colors.length;
  const mix = (a: string, b: string, t: number) => { const h = (s: string) => [1, 3, 5].map((i) => parseInt(s.slice(i, i + 2), 16)); const A = h(a), B = h(b); return `rgb(${A.map((v, i) => Math.round(v + (B[i] - v) * t)).join(",")})`; };
  const segColor = (i: number) => {
    const t0 = at + i * P.segGap;
    if (f < t0) return colors[i];
    const u = (f - t0) / d1(P.segDur);
    return u < 0.5 ? mix(colors[i], "#f4a6b4", u * 2) : mix("#f4a6b4", "#ffffff", Math.min(1, (u - 0.5) * 2));
  };
  const nz: Pt = [1250, 330];
  const sAt = at + P.sprayDelay;
  const grow = f >= sAt ? lerp(f, sAt, sAt + P.sprayDur, 0, P.sprayLen, E_OUT) : 0;
  const arc = `M${nz[0] - 20},${nz[1] - 6} Q${nz[0] - 170},${nz[1] - 120} ${nz[0] - 360},${nz[1] - 20}`;
  return (
    <AbsoluteFill style={{ background: P.bg, backgroundImage: "linear-gradient(rgba(40,60,100,0.35) 3px, transparent 3px), linear-gradient(90deg, rgba(40,60,100,0.35) 3px, transparent 3px)", backgroundSize: "120px 120px" }}>
      <div style={{ position: "absolute", left: tx - tw / 2 - 10, top: top - 10, width: tw + 20, height: th + 40, background: "#f7f7f7", borderRadius: tw }} />
      {colors.map((c, i) => <div key={i} style={{ position: "absolute", left: tx - tw / 2 + 6, top: top + 10 + i * segH, width: tw - 12, height: segH + 1, background: segColor(i), borderRadius: i === 0 ? `${tw}px ${tw}px 0 0` : 0 }} />)}
      <div style={{ position: "absolute", left: tx - bulbR - 10, top: top + th - 30, width: (bulbR + 10) * 2, height: (bulbR + 10) * 2, borderRadius: "50%", background: "#f7f7f7" }} />
      <div style={{ position: "absolute", left: tx - bulbR, top: top + th - 20, width: bulbR * 2, height: bulbR * 2, borderRadius: "50%", background: P.bulb }} />
      {can ?? (
        <>
          {/* 세모지 스프레이 캔(spray_can, 분사구 = nz) + 노즐 누르는 손(hand_press_nozzle, 검지 끝 = 캔 윗면) */}
          <KitImg id="spray_can" w={320} style={{ position: "absolute", left: nz[0] - 214 * (320 / 433), top: nz[1] - 43 * (320 / 433) }} />
          <KitImg id="hand_press_nozzle" w={560} style={{ position: "absolute", left: nz[0] - 5 - 45 * (560 / 1123), top: nz[1] - 25 - 930 * (560 / 1123) }} />
        </>
      )}
      {grow > 0 && (
        <svg width={W} height={H} style={{ position: "absolute" }}>
          <defs><mask id="xc-spray"><path d={arc} pathLength={P.sprayLen} stroke="#fff" strokeWidth={30} fill="none" strokeDasharray={`${grow} ${P.sprayLen * 3}`} /></mask></defs>
          <path d={arc} fill="none" stroke="#fff" strokeWidth={6} strokeLinecap="round" strokeDasharray="14 16" strokeDashoffset={-(f - sAt) * P.flow} mask="url(#xc-spray)" />
        </svg>
      )}
    </AbsoluteFill>
  );
};

// ══ 15. HandHeldDocLineup — 손에 든 서류 순차 라인업(견적 비교) ═══════════════════
// [ref4-hyundai 00:33:47] 화면 밖 손(소매 포함)이 서류 카드를 아래에서 들어올려(9f) 오른쪽으로 아크 이동(10f) → 다음 카드는 계단식으로 이어 세움 → 마지막 도장
export const HandHeldDocLineupParams = z.object({
  rise: num(9, 2, 30, 1, "들어올림", "timing", "f"),
  arc: num(10, 2, 30, 1, "아크 이동", "timing", "f"),
  arcDx: num(60, 0, 200, 5, "아크 이동 거리", "motion", "px"),
  arcLift: num(24, 0, 100, 2, "아크 높이", "motion", "px"),
  overshoot: num(0.06, 0, 0.3, 0.01, "오버슛", "motion"),
  handOut: num(14, 0, 60, 1, "손이 빠지는 지연", "timing", "f"),
  stepX: num(270, 100, 500, 5, "카드 가로 간격", "size", "px"),
  stepY: num(50, -100, 200, 5, "카드 세로 계단", "size", "px"),
  cardW: num(280, 150, 420, 5, "카드 폭", "size", "px"),
  amountSize: num(72, 30, 120, 2, "금액 글자 크기", "size", "px"),
  sleeve: col("#1f2a44", "소매 색"),
  skin: col("#F2C4A0", "손 색"),
  bg: col("#4A2E22", "배경색"),
});
export type HandHeldDocLineupP = z.infer<typeof HandHeldDocLineupParams>;
export type DocCard = { at: number; title?: string; amount: string; by?: string };
export const HandHeldDocLineup: React.FC<{ cards: DocCard[]; x0?: number; y0?: number; stamp?: { text: string; at: number }; p?: Partial<HandHeldDocLineupP> }> = ({ cards, x0 = 120, y0 = 150, stamp, p }) => {
  const P = def(HandHeldDocLineupParams, p);
  const f = useCurrentFrame();
  const cw = P.cardW, ch = cw * 1.36, HK = (cw * 1.45) / 1105; // 손 그림 배율(카드 폭 기준)
  return (
    <AbsoluteFill style={{ background: P.bg }}>
      {cards.map((c, i) => {
        if (f < c.at) return null;
        const tx = x0 + i * P.stepX, ty = y0 + i * P.stepY;
        const g = f - c.at;
        const x = g < P.rise ? tx - P.arcDx : lerp(f, c.at + P.rise, c.at + P.rise + P.arc, tx - P.arcDx, tx, Easing.out(Easing.back(1 + P.overshoot * 20)));
        const y = g < P.rise ? lerp(f, c.at, c.at + P.rise, H + 60, ty, E_OUT) : ty - Math.sin(Math.min(1, (g - P.rise) / d1(P.arc)) * Math.PI) * P.arcLift;
        const hand = lerp(f, c.at + P.rise + P.arc + P.handOut, c.at + P.rise + P.arc + P.handOut + 8, 0, 700, Easing.in(Easing.quad));
        return (
          <div key={i} style={{ position: "absolute", left: x, top: y, width: cw, height: ch, zIndex: i }}>
            {/* 세모지 손(hand_hold_bottom, 소매 오른쪽 아래) — 카드 뒤에서 아래 가장자리를 받쳐 듦. 손바닥 중심(500,420)px = 카드 아래 35% 지점 */}
            {hand < 700 && (
              <Img src={prop("hand_hold_bottom")} style={{ position: "absolute", left: cw * 0.35 - 500 * HK, top: ch - 30 - 420 * HK, width: 1105 * HK, height: 1104 * HK, transform: `translate(${hand * 0.35}px,${hand}px)` }} />
            )}
            <div style={{ position: "absolute", inset: 0, background: "#fbfaf7", boxShadow: "0 8px 16px rgba(0,0,0,0.35)", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "space-around", padding: "18px 0" }}>
              <div style={{ fontFamily: "NeoHv", fontSize: cw * 0.13, color: "#222" }}>{c.title ?? "견적서"}</div>
              <div style={{ fontFamily: "NeoHv", fontSize: P.amountSize, color: "#111" }}>{c.amount}</div>
              <div style={{ fontFamily: "NeoEb", fontSize: cw * 0.08, color: "#555" }}>{c.by}</div>
            </div>
          </div>
        );
      })}
      {stamp && <div style={{ position: "absolute", inset: 0, zIndex: 99 }}><Stamp text={stamp.text} x={x0 + (cards.length - 1.5) * P.stepX + P.cardW / 2} y={y0 + (cards.length - 1) * P.stepY + P.cardW * 0.7} at={stamp.at} /></div>}
    </AbsoluteFill>
  );
};

// ══ 16. ProportionRulerRoad — 도로 비율 눈금자 채움 ══════════════════════════════
// [ref4-hyundai 00:36:07] 도로 위 5등분 눈금자 → 굵은 바가 0→2/5 26f 성장, f24 화살촉 부착 → 담당자 pill 팝(+7f) → 다음 주체가 다른 색으로 나머지 채움
export const ProportionRulerRoadParams = z.object({
  fill1Dur: num(26, 4, 80, 1, "첫 구간 채움", "timing", "f"),
  headAt: num(24, 0, 80, 1, "화살촉 부착 시점", "timing", "f"),
  pillDelay: num(7, 0, 40, 1, "pill 지연", "timing", "f"),
  pillPop: num(6, 1, 20, 1, "pill 팝", "timing", "f"),
  fill2Delay: num(30, 0, 120, 1, "둘째 구간 지연", "timing", "f"),
  fill2Dur: num(20, 4, 80, 1, "둘째 구간 채움", "timing", "f"),
  frac: num(0.4, 0.05, 0.95, 0.05, "첫 구간 비율", "motion"),
  ticks: num(5, 2, 10, 1, "눈금 등분", "size"),
  barH: num(26, 6, 60, 1, "채움 바 두께", "size", "px"),
  c1: col("#37290D", "첫 구간 색"),
  c2: col("#1E1E5A", "둘째 구간 색"),
  road: col("#3E3A47", "도로 색"),
  bg: col("#CA8C4F", "흙 배경색"),
});
export type ProportionRulerRoadP = z.infer<typeof ProportionRulerRoadParams>;
export const ProportionRulerRoad: React.FC<{ at: number; labels?: [string, string?]; p?: Partial<ProportionRulerRoadP> }> = ({ at, labels = ["현대건설", "국내 건설업체 15곳"], p }) => {
  const P = def(ProportionRulerRoadParams, p);
  const f = useCurrentFrame();
  const x0 = 60, x1 = 1860, ry = 440, L = x1 - x0, T = Math.round(P.ticks);
  const e1 = x0 + L * P.frac;
  const w1 = f >= at ? lerp(f, at, at + P.fill1Dur, 0, L * P.frac, E_OUT) : 0;
  const p1 = at + P.fill1Dur + P.pillDelay;
  const s2 = at + P.fill1Dur + P.fill2Delay;
  const w2 = labels[1] && f >= s2 ? lerp(f, s2, s2 + P.fill2Dur, 0, x1 - e1, E_OUT) : 0;
  const p2 = s2 + P.fill2Dur + P.pillDelay;
  const head = (x: number, c: string) => <polygon points={`${x - 6},${ry - P.barH} ${x + P.barH * 1.4},${ry} ${x - 6},${ry + P.barH}`} fill={c} />;
  return (
    <AbsoluteFill style={{ background: P.bg }}>
      <div style={{ position: "absolute", left: 0, top: 540, width: W, height: 340, background: P.road, borderTop: "12px solid #efefef", borderBottom: "12px solid #efefef" }} />
      <div style={{ position: "absolute", left: 0, top: 710, width: W, height: 10, backgroundImage: "linear-gradient(90deg, #fff 0 70px, transparent 70px 120px)", backgroundSize: "120px 10px" }} />
      <svg width={W} height={H} style={{ position: "absolute" }}>
        <rect x={x0} y={ry - 2} width={L} height={4} fill="#fff" />
        {Array.from({ length: T + 1 }).map((_, i) => <rect key={i} x={x0 + (L * i) / T - 2} y={ry - 20} width={4} height={40} fill="#fff" />)}
        {w1 > 0 && <rect x={x0} y={ry - P.barH / 2} width={w1} height={P.barH} fill={P.c1} />}
        {f >= at + P.headAt && head(x0 + w1, P.c1)}
        {w2 > 0 && <rect x={e1 + P.barH * 1.4} y={ry - P.barH / 2} width={Math.max(0, w2 - P.barH * 1.4)} height={P.barH} fill={P.c2} />}
        {w2 > P.barH * 1.4 && head(Math.min(x1 - P.barH, e1 + w2), P.c2)}
      </svg>
      {f >= p1 && <At x={x0 + 220} y={ry - 110} s={pop(f, p1, P.pillPop, 0.3, 1.1)} blur={unblur(f, p1, P.pillPop * 0.6, 8)}><Pill text={labels[0]} bg={P.c1} size={54} /></At>}
      {labels[1] && f >= p2 && <At x={(e1 + x1) / 2} y={ry - 110} s={pop(f, p2, P.pillPop, 0.3, 1.1)} blur={unblur(f, p2, P.pillPop * 0.6, 8)}><Pill text={labels[1]} bg={P.c2} size={54} /></At>}
    </AbsoluteFill>
  );
};

// ══ 17. TunnelLengthCompare — 터널 단면 길이 비교(먼지 스폰) ═════════════════════
// [ref4-hyundai 00:37:07] 터널 입구 두 개 → 먼지 구름 퍼프(~10f) 속에서 표지판 카드 드롭(6f) → 네이비 길이 pill 팝 → 두 번째 터널 1.6s 스태거
export const TunnelLengthCompareParams = z.object({
  puffDur: num(10, 2, 40, 1, "먼지 퍼프 확산", "timing", "f"),
  puffTail: num(14, 0, 40, 1, "먼지 소멸 꼬리", "timing", "f"),
  signDelay: num(4, 0, 30, 1, "표지판 지연", "timing", "f"),
  signDrop: num(6, 1, 20, 1, "표지판 드롭", "timing", "f"),
  pillDelay: num(8, 0, 40, 1, "pill 지연", "timing", "f"),
  pillPop: num(6, 1, 20, 1, "pill 팝", "timing", "f"),
  stagger: num(48, 0, 120, 1, "두 번째 터널 스태거(1.6s)", "timing", "f"),
  puffR: num(170, 60, 400, 5, "먼지 반경", "size", "px"),
  pill: col("#1E1E5A", "pill 색"),
  portal: col("#3c4a5c", "터널 입구 색"),
  bg: col("#6f9cc2", "배경색"),
});
export type TunnelLengthCompareP = z.infer<typeof TunnelLengthCompareParams>;
const Puff: React.FC<{ x: number; y: number; at: number; dur: number; tail: number; r: number; seed: string }> = ({ x, y, at, dur, tail, r, seed }) => {
  const f = useCurrentFrame();
  const g = f - at;
  if (g < 0 || g > dur + tail) return null;
  const grow = kf(g, 0, [0, dur], [0.2, 1], E_OUT), op = kf(g, 0, [0, dur * 0.5, dur, dur + tail], [0.3, 1, 0.9, 0]);
  return (
    <svg width={W} height={H} style={{ position: "absolute", opacity: op }}>
      {Array.from({ length: 11 }).map((_, i) => {
        const a = random(`${seed}a${i}`) * TAU, d = random(`${seed}d${i}`) * r * 0.8 * grow;
        const cr = r * (0.3 + random(`${seed}r${i}`) * 0.3) * grow;
        return <circle key={i} cx={x + Math.cos(a) * d} cy={y + Math.sin(a) * d * 0.7 - g * 1.5} r={cr} fill={i % 3 ? "#c9c9c9" : "#a9a9a9"} />;
      })}
    </svg>
  );
};
export const TunnelLengthCompare: React.FC<{ at: number; items?: { name: string; sub?: string; value: string }[]; p?: Partial<TunnelLengthCompareP> }> = ({ at, items = [{ name: "당재터널", sub: "상행선", value: "692m" }, { name: "당재터널", sub: "하행선", value: "530m" }], p }) => {
  const P = def(TunnelLengthCompareParams, p);
  const f = useCurrentFrame();
  const xs = [560, 1360], base = 700;
  return (
    <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 55%, ${P.bg} 0%, ${P.bg} 45%, rgba(40,70,110,1) 110%)` }}>
      {[1.0, 1.35, 1.75].map((k, i) => <div key={i} style={{ position: "absolute", left: 960 - 520 * k, top: 620 - 420 * k, width: 1040 * k, height: 1040 * k, borderRadius: "50%", border: "40px solid rgba(255,255,255,0.05)", boxSizing: "border-box" }} />)}
      {xs.map((x, i) => (
        // 세모지 터널 입구(tunnel_portal 크롭 xc_tunnel, 900×690) — 바닥선 = 기존 SVG 도로 끝(base+120). 입구 색은 그림 고정
        <Img key={i} src={prop("xc_tunnel")} style={{ position: "absolute", left: x - 310, top: base + 120 - (620 * 690) / 900, width: 620, height: (620 * 690) / 900 }} />
      ))}
      {items.slice(0, 2).map((it, i) => {
        const t = at + i * P.stagger, sAt = t + P.signDelay, pAt = sAt + P.signDrop + P.pillDelay, x = xs[i];
        return (
          <React.Fragment key={i}>
            {f >= sAt && (
              <div style={{ position: "absolute", left: x - 130, top: lerp(f, sAt, sAt + P.signDrop, base - 80, base + 60, Easing.out(Easing.back(1.6))), opacity: kf(f, sAt, [0, 2], [0, 1]) }}>
                <div style={{ width: 260, background: "#fff", borderRadius: 6, padding: "12px 0", textAlign: "center", boxShadow: "0 6px 10px rgba(0,0,0,0.25)" }}>
                  <div style={{ fontFamily: "NeoHv", fontSize: 44, color: "#111" }}>{it.name}</div>
                  {it.sub && <div style={{ fontFamily: "NeoEb", fontSize: 24, color: "#444" }}>{it.sub}</div>}
                </div>
                <div style={{ width: 10, height: 90, background: "#ddd", margin: "0 auto" }} />
              </div>
            )}
            <Puff x={x} y={base + 90} at={t} dur={P.puffDur} tail={P.puffTail} r={P.puffR} seed={`tn${i}`} />
            {f >= pAt && <At x={x - 90} y={220} s={pop(f, pAt, P.pillPop, 0.3, 1.1)} blur={unblur(f, pAt, P.pillPop * 0.6, 8)}><Pill text={it.value} bg={P.pill} size={60} /></At>}
          </React.Fragment>
        );
      })}
    </AbsoluteFill>
  );
};

/** 세모지 지시봉(pointer_stick 1355×822: 손잡이 (1,773) → 끝 (1353,14)) 을 from(손잡이)→to(끝) 에 맞춰 회전·배율 */
const PointerStick: React.FC<{ from: Pt; to: Pt }> = ({ from, to }) => {
  const [hx, hy, tx, ty] = [1, 773, 1353, 14];
  const k = Math.hypot(to[0] - from[0], to[1] - from[1]) / Math.hypot(tx - hx, ty - hy);
  const rot = Math.atan2(to[1] - from[1], to[0] - from[0]) - Math.atan2(ty - hy, tx - hx);
  return <Img src={prop("pointer_stick")} style={{ position: "absolute", left: from[0] - hx * k, top: from[1] - hy * k, width: 1355 * k, height: 822 * k, transformOrigin: `${hx * k}px ${hy * k}px`, transform: `rotate(${rot}rad)` }} />;
};

// ══ 18. MapLecturerCountryFill — 지시봉 강의 + 국가 하이라이트 채움 ═══════════════
// [ref4-hyundai 00:45:22] 지도 앞 인물이 지시봉을 들고, 대상 국가가 노랗게 채워짐(8f) → 국가명 pill 팝 → 로고 팝 → 검정 캡션 α 0→1 12f
export const MapLecturerCountryFillParams = z.object({
  fillDelay: num(4, 0, 40, 1, "채움 지연", "timing", "f"),
  fillDur: num(8, 1, 30, 1, "국가 채움", "timing", "f"),
  gap: num(22, 4, 60, 1, "요소 간격(0.6~1s)", "timing", "f"),
  pillPop: num(6, 1, 20, 1, "pill·로고 팝", "timing", "f"),
  captionFade: num(12, 1, 40, 1, "캡션 페이드", "timing", "f"),
  zoom: num(1.35, 0.6, 3, 0.05, "지도 배율", "motion"),
  focusX: num(560, 200, 1400, 10, "대상국 화면 x", "motion", "px"),
  fill: col("#F2C230", "하이라이트 색"),
  ocean: col("#7AA7C6", "바다 색"),
  land: col("#4f7f3c", "육지 색"),
  pill: col("#1f1f5e", "pill 색"),
});
export type MapLecturerCountryFillP = z.infer<typeof MapLecturerCountryFillParams>;
export const MapLecturerCountryFill: React.FC<{ at: number; country?: string; name?: string; logo?: RN; caption?: string; lecturer?: string; p?: Partial<MapLecturerCountryFillP> }> = ({ at, country = "Japan", name = "일본", logo, caption = "엔지니어 기술 연수", lecturer = "img/s03_woo.png", p }) => {
  const P = def(MapLecturerCountryFillParams, p);
  const f = useCurrentFrame();
  const geo = useGeo();
  const tgt = geo?.eastasia.countries.find((c) => c.name === country);
  const cc: Pt = tgt ? tgt.c : [960, 540];
  const z = P.zoom, tx = P.focusX - cc[0] * z, ty = 560 - cc[1] * z;
  const fAt = at + P.fillDelay, pAt = fAt + P.fillDur + P.gap * 0.5, lAt = pAt + P.gap, cAt = lAt + P.gap;
  const sc = (pt: Pt): Pt => [pt[0] * z + tx, pt[1] * z + ty];
  const [sx, sy] = sc(cc);
  return (
    <AbsoluteFill style={{ background: P.ocean }}>
      {geo && (
        <svg width={W} height={H} style={{ position: "absolute" }}>
          <g transform={`translate(${tx},${ty}) scale(${z})`}>
            {geo.eastasia.countries.map((c) => <path key={c.name} d={c.d} fill={P.land} stroke={P.land} strokeWidth={1} />)}
            {tgt && f >= fAt && <path d={tgt.d} fill={P.fill} opacity={lerp(f, fAt, fAt + P.fillDur, 0, 1)} />}
          </g>
        </svg>
      )}
      {/* 한반도가 크게 보이는 동아시아 확대 지도 — 데이터(50m)에 빠진 울릉도·독도 섬 형상 보강(라벨 없음) */}
      <KoreaIslands project={(ll) => { const q = projEA(ll); return { x: q[0] * z + tx, y: q[1] * z + ty }; }} pxPerDeg={((MERC_EA.s * Math.PI) / 180) * z} land={P.land} stroke={P.land} />
      {f >= pAt && <At x={sx} y={sy - 330} s={pop(f, pAt, P.pillPop, 0.3, 1.1)} blur={unblur(f, pAt, P.pillPop * 0.6, 8)}><Pill text={name} bg={P.pill} size={52} /></At>}
      {f >= lAt && (
        <At x={sx} y={sy - 210} s={pop(f, lAt, P.pillPop, 0.3, 1.1)}>
          {logo ?? <div style={{ width: 200, height: 84, borderRadius: "50%", background: "#1d2c6b", border: "5px solid #fff", color: "#fff", fontFamily: "Yeonsung", fontSize: 42, display: "flex", alignItems: "center", justifyContent: "center" }}>Motor</div>}
        </At>
      )}
      {f >= cAt && (
        <At x={sx - 60} y={sy + 150} op={lerp(f, cAt, cAt + P.captionFade, 0.25, 1)}>
          <div style={{ background: `rgba(0,0,0,${lerp(f, cAt, cAt + P.captionFade, 0.35, 1)})`, color: "#fff", fontFamily: "Yeonsung", fontSize: 50, padding: "8px 22px", whiteSpace: "nowrap" }}>{caption}</div>
        </At>
      )}
      <PointerStick from={[1290, 720]} to={[1150, 170]} />
      <Img src={src(lecturer)} style={{ position: "absolute", left: 1180, top: 200, width: 640, height: 900, objectFit: "contain", objectPosition: "50% 100%" }} />
    </AbsoluteFill>
  );
};

// ══ 19. CorpLineageFlow — 기업 계보 플로차트 ══════════════════════════════════
// [ref4-hyundai 01:16:46] 원 로고 고정 → 다음 로고 opacity 0→1 10f + 연도 필 블러인, 연결 화살표 opacity 20%→100% 20f(드로우 아님) → 아래 화살표 fade 10f → 자식 필 blur+0.8→1 5f
export const CorpLineageFlowParams = z.object({
  logoFade: num(10, 1, 40, 1, "로고 페이드인", "timing", "f"),
  yearBlur: num(8, 1, 30, 1, "연도 필 블러인", "timing", "f"),
  arrowFade: num(20, 1, 60, 1, "연결 화살표 진해짐", "timing", "f"),
  arrowOp0: num(0.2, 0, 1, 0.05, "화살표 시작 불투명도", "look"),
  downFade: num(10, 1, 40, 1, "아래 화살표 페이드", "timing", "f"),
  childDelay: num(10, 0, 60, 1, "자식 필 지연", "timing", "f"),
  childPop: num(5, 1, 20, 1, "자식 필 팝", "timing", "f"),
  nodeGap: num(560, 250, 800, 10, "노드 간격", "size", "px"),
  pill: col("#1f2a6b", "필 색"),
  bg: col("#78A9D0", "배경색"),
});
export type CorpLineageFlowP = z.infer<typeof CorpLineageFlowParams>;
export type LineageNode = { at: number; logo: RN; year?: string; child?: { text: string; at: number } };
/** 기본 로고 마크(도형 + 이름) */
export const LogoMark: React.FC<{ name: string; color?: string; shape?: "tri" | "shell" | "circle" }> = ({ name, color = "#1f4fa0", shape = "circle" }) => (
  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
    <svg width={170} height={140} viewBox="0 0 170 140">
      {shape === "tri" && <><polygon points="20,130 70,20 110,130" fill="#e03a3e" /><polygon points="60,130 105,30 150,130" fill="#1f3f8f" /></>}
      {shape === "shell" && Array.from({ length: 7 }).map((_, i) => <ellipse key={i} cx={85} cy={80} rx={12 + i * 10} ry={58} fill="none" stroke={color} strokeWidth={9} opacity={1 - i * 0.05} transform={`rotate(${(i - 3) * 9} 85 130)`} />)}
      {shape === "circle" && <circle cx={85} cy={70} r={62} fill={color} />}
    </svg>
    <div style={{ fontFamily: "NeoHv", fontSize: 50, color: shape === "shell" ? color : "#111" }}>{name}</div>
  </div>
);
export const CorpLineageFlow: React.FC<{ nodes: LineageNode[]; x0?: number; y?: number; p?: Partial<CorpLineageFlowP> }> = ({ nodes, x0 = 330, y = 470, p }) => {
  const P = def(CorpLineageFlowParams, p);
  const f = useCurrentFrame();
  const arrow = (w: number) => <svg width={w} height={50}><rect x={0} y={18} width={w - 30} height={14} fill="#fff" /><polygon points={`${w - 36},0 ${w},25 ${w - 36},50`} fill="#fff" /></svg>;
  return (
    <AbsoluteFill style={{ background: P.bg }}>
      {nodes.map((n, i) => {
        const x = x0 + i * P.nodeGap;
        if (f < n.at) return null;
        const op = i === 0 ? 1 : lerp(f, n.at, n.at + P.logoFade, 0, 1);
        return (
          <React.Fragment key={i}>
            {i > 0 && <div style={{ position: "absolute", left: x - P.nodeGap + 150, top: y - 25, opacity: lerp(f, n.at, n.at + P.arrowFade, P.arrowOp0, 1) }}>{arrow(P.nodeGap - 300)}</div>}
            <At x={x} y={y} op={op}>{n.logo}</At>
            {n.year && <At x={x} y={y - 170} blur={i === 0 ? 0 : unblur(f, n.at, P.yearBlur, 10)} op={i === 0 ? 1 : kf(f, n.at, [0, 3], [0.2, 1])}><Pill text={n.year} bg={P.pill} size={36} /></At>}
            {n.child && f >= n.child.at && (
              <>
                <div style={{ position: "absolute", left: x - 12, top: y + 125, opacity: lerp(f, n.child.at, n.child.at + P.downFade, 0, 1) }}>
                  <svg width={24} height={70}><rect x={7} y={0} width={10} height={48} fill="#fff" /><polygon points="0,44 24,44 12,70" fill="#fff" /></svg>
                </div>
                {f >= n.child.at + P.childDelay && (
                  <At x={x} y={y + 250} s={kf(f, n.child.at + P.childDelay, [0, d1(P.childPop)], [0.8, 1], E_OUT)} blur={unblur(f, n.child.at + P.childDelay, P.childPop, 10)} op={kf(f, n.child.at + P.childDelay, [0, 2], [0.3, 1])}>
                    <Pill text={n.child.text} bg={P.pill} size={42} />
                  </At>
                )}
              </>
            )}
          </React.Fragment>
        );
      })}
    </AbsoluteFill>
  );
};

// ══ 20. ElectionPosterDropRank — 포스터 드롭 + 순위 필 ═════════════════════════
// [ref4-hyundai 01:28:10] 남색 배경에 포스터 3장이 위에서 드롭(스태거 3f, 각 24f quint-out) → 내레이션 시점마다 순위 필 blur+0.3→1 4f(1위 금색)
export const ElectionPosterDropRankParams = z.object({
  dropDur: num(24, 4, 60, 1, "포스터 드롭(quint-out)", "timing", "f"),
  stagger: num(3, 0, 20, 1, "포스터 스태거", "timing", "f"),
  pillPop: num(4, 1, 20, 1, "순위 필 팝", "timing", "f"),
  posterW: num(430, 250, 560, 5, "포스터 폭", "size", "px"),
  border: num(6, 0, 20, 1, "흰 테두리", "size", "px"),
  gap: num(120, 20, 300, 5, "포스터 간격", "size", "px"),
  gold: col("#E0B400", "1위 필 색"),
  bg: col("#242A45", "배경색"),
});
export type ElectionPosterDropRankP = z.infer<typeof ElectionPosterDropRankParams>;
export type Poster = { img: string; name?: string; num?: string; color?: string; rank?: number; share?: string; rankAt?: number; pos?: string };
export const ElectionPosterDropRank: React.FC<{ at: number; posters: Poster[]; source?: string; p?: Partial<ElectionPosterDropRankP> }> = ({ at, posters, source, p }) => {
  const P = def(ElectionPosterDropRankParams, p);
  const f = useCurrentFrame();
  const pw = P.posterW, ph = pw * 1.35, n = posters.length;
  const total = n * pw + (n - 1) * P.gap, left = 960 - total / 2, top = 150;
  return (
    <AbsoluteFill style={{ background: P.bg }}>
      {posters.map((po, i) => {
        const s = at + i * P.stagger;
        if (f < s) return null;
        const y = lerp(f, s, s + P.dropDur, -ph - 40, top, QUINT_OUT);
        const x = left + i * (pw + P.gap);
        return (
          <React.Fragment key={i}>
            <div style={{ position: "absolute", left: x, top: y, width: pw, height: ph, border: `${P.border}px solid #fff`, boxSizing: "border-box", overflow: "hidden", boxShadow: "0 10px 20px rgba(0,0,0,0.4)" }}>
              <Img src={src(po.img)} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: po.pos ?? "50% 30%" }} />
              {po.name && (
                <div style={{ position: "absolute", left: 0, bottom: 0, width: "100%", height: ph * 0.16, background: po.color ?? "#3a2f8f", display: "flex", alignItems: "center", gap: 14, paddingLeft: 14, boxSizing: "border-box" }}>
                  {po.num && <div style={{ width: ph * 0.11, height: ph * 0.11, borderRadius: 8, background: "#fff", color: po.color ?? "#3a2f8f", fontFamily: "NeoHv", fontSize: ph * 0.09, display: "flex", alignItems: "center", justifyContent: "center" }}>{po.num}</div>}
                  <div style={{ fontFamily: "NeoHv", fontSize: ph * 0.085, color: "#fff" }}>{po.name}</div>
                </div>
              )}
            </div>
            {po.rankAt !== undefined && f >= po.rankAt && (
              <At x={x + pw / 2} y={top + ph + 70} s={pop(f, po.rankAt, P.pillPop, 0.3, 1.08)} blur={unblur(f, po.rankAt, P.pillPop, 10)}>
                <div style={{ display: "flex", alignItems: "center", gap: 18, background: po.rank === 1 ? P.gold : "#e9e9ea", borderRadius: 999, padding: "8px 34px 8px 10px" }}>
                  <div style={{ width: 70, height: 70, borderRadius: "50%", background: "#fff", color: "#222", fontFamily: "NeoHv", fontSize: 34, display: "flex", alignItems: "center", justifyContent: "center" }}>{po.rank}위</div>
                  <div style={{ fontFamily: "NeoHv", fontSize: 50, color: po.rank === 1 ? "#fff" : "#333" }}>{po.share}</div>
                </div>
              </At>
            )}
          </React.Fragment>
        );
      })}
      {source && <div style={{ position: "absolute", right: 60, bottom: 50, fontFamily: "Yeonsung", fontSize: 30, color: "rgba(255,255,255,0.7)" }}>{source}</div>}
    </AbsoluteFill>
  );
};

// ══ 21. SplitFlagExchange — 분할 국기 교환 화살표 ═══════════════════════════════
// [ref4-hyundai 01:44:07] 좌우 50:50 국기 패널 → 네이비 2줄 필 blur-in 8f + 흰 화살표 opacity 6f(←가 먼저, →는 나중)
export const SplitFlagExchangeParams = z.object({
  pillBlur: num(8, 1, 30, 1, "필 블러인", "timing", "f"),
  arrowDelay: num(2, 0, 30, 1, "화살표 지연", "timing", "f"),
  arrowFade: num(6, 1, 20, 1, "화살표 페이드", "timing", "f"),
  arrowSlide: num(24, 0, 100, 2, "화살표 이동 거리", "motion", "px"),
  pillW: num(480, 250, 800, 10, "필 폭", "size", "px"),
  textSize: num(52, 24, 90, 1, "필 글자 크기", "size", "px"),
  pill: col("#26275e", "필 색"),
  dim: num(0.08, 0, 0.6, 0.01, "배경 어둡게", "look"),
});
export type SplitFlagExchangeP = z.infer<typeof SplitFlagExchangeParams>;
const StarFlag: React.FC = () => (
  <svg width="100%" height="100%" viewBox="0 0 300 200" preserveAspectRatio="xMidYMid slice"><rect width={300} height={200} fill="#A8192E" /><circle cx={150} cy={100} r={62} fill="#d9d9d9" /><polygon points="150,44 163,84 205,84 171,108 184,148 150,124 116,148 129,108 95,84 137,84" fill="#A8192E" /></svg>
);
export const SplitFlagExchange: React.FC<{ left?: RN; right?: RN; items: { side: "left" | "right"; lines: string[]; at: number }[]; p?: Partial<SplitFlagExchangeP> }> = ({ left, right, items, p }) => {
  const P = def(SplitFlagExchangeParams, p);
  const f = useCurrentFrame();
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", left: 0, top: 0, width: 960, height: H, overflow: "hidden", background: "#bdbdbd" }}>{left ?? <svg width="100%" height="100%" viewBox="0 0 300 200" preserveAspectRatio="xMidYMid slice">{FLAGS.kr}</svg>}</div>
      <div style={{ position: "absolute", left: 960, top: 0, width: 960, height: H, overflow: "hidden" }}>{right ?? <StarFlag />}</div>
      <AbsoluteFill style={{ background: `rgba(0,0,0,${P.dim})` }} />
      {items.map((it, i) => {
        if (f < it.at) return null;
        const cx = it.side === "left" ? 480 : 1440, dir = it.side === "right" ? -1 : 1;
        const aAt = it.at + P.arrowDelay;
        return (
          <React.Fragment key={i}>
            <At x={cx} y={540} blur={unblur(f, it.at, P.pillBlur, 16)} op={kf(f, it.at, [0, P.pillBlur * 0.6], [0.2, 1])}>
              <div style={{ width: P.pillW, background: P.pill, opacity: 0.94, borderRadius: 999, padding: "26px 0", textAlign: "center", fontFamily: "NeoHv", fontSize: P.textSize, color: "#fff", lineHeight: 1.3 }}>{it.lines.map((l, k) => <div key={k}>{l}</div>)}</div>
            </At>
            {f >= aAt && (
              <div style={{ position: "absolute", left: 960 - 110 + dir * lerp(f, aAt, aAt + P.arrowFade, -P.arrowSlide, 0, E_OUT) + (dir < 0 ? 120 : -120), top: 540 - 22 + (dir < 0 ? -40 : 40), opacity: lerp(f, aAt, aAt + P.arrowFade, 0, 1), transform: dir < 0 ? "scaleX(-1)" : undefined }}>
                <svg width={220} height={44}><rect x={0} y={16} width={180} height={12} rx={6} fill="#fff" /><polygon points="172,0 220,22 172,44" fill="#fff" /></svg>
              </div>
            )}
          </React.Fragment>
        );
      })}
    </AbsoluteFill>
  );
};

// ══ 22. AlternatingPhotoTimeline — 교차 사진 타임라인 ═════════════════════════════
// [ref4-hyundai 01:58:15] 굵은 하늘색 레일 좌→우 wipe 6f → 핀 선 드로우 → 사진 카드 핀 기준 0.3→1.1→1 8f, 레일 위/아래 교대
export const AlternatingPhotoTimelineParams = z.object({
  railWipe: num(6, 1, 30, 1, "레일 wipe", "timing", "f"),
  pinDraw: num(4, 1, 20, 1, "핀 선 드로우", "timing", "f"),
  cardPop: num(8, 1, 20, 1, "카드 팝", "timing", "f"),
  railH: num(70, 20, 140, 2, "레일 두께", "size", "px"),
  pinLen: num(80, 20, 200, 2, "핀 길이", "size", "px"),
  cardW: num(330, 160, 500, 5, "카드 폭", "size", "px"),
  labelSize: num(38, 18, 70, 1, "라벨 크기", "size", "px"),
  rail: col("#5A9BD5", "레일 색"),
  bg: col("#1d4a80", "배경색"),
});
export type AlternatingPhotoTimelineP = z.infer<typeof AlternatingPhotoTimelineParams>;
export type TLItem = { img: string; label: string; at: number; pos?: string };
export const AlternatingPhotoTimeline: React.FC<{ at: number; items: TLItem[]; watermark?: RN; y?: number; p?: Partial<AlternatingPhotoTimelineP> }> = ({ at, items, watermark, y = 560, p }) => {
  const P = def(AlternatingPhotoTimelineParams, p);
  const f = useCurrentFrame();
  const x0 = 50, x1 = 1870, n = items.length;
  const rw = f >= at ? lerp(f, at, at + P.railWipe, 0, x1 - x0, E_OUT) : 0;
  const cw = P.cardW, ch = cw * 0.62;
  return (
    <AbsoluteFill style={{ background: P.bg }}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: 0.35 }}>{watermark ?? <div style={{ width: 1100, height: 700, borderRadius: "50%", border: "70px solid #7f9cc4", transform: "rotate(-8deg)" }} />}</AbsoluteFill>
      <div style={{ position: "absolute", left: x0, top: y - P.railH / 2, width: rw, height: P.railH, borderRadius: P.railH, background: P.rail }} />
      {items.map((it, i) => {
        if (f < it.at) return null;
        const x = x0 + 170 + (i * (x1 - x0 - 340)) / Math.max(1, n - 1), up = i % 2 === 0, dir = up ? -1 : 1;
        const pl = lerp(f, it.at, it.at + P.pinDraw, 0, P.pinLen, E_OUT);
        const cAt = it.at + P.pinDraw;
        const s = f >= cAt ? kf(f, cAt, [0, P.cardPop * 0.6, P.cardPop], [0.3, 1.1, 1], Easing.out(Easing.quad)) : 0;
        const pinY = y + dir * P.pinLen;
        return (
          <React.Fragment key={i}>
            <div style={{ position: "absolute", left: x - 3, top: up ? y - pl : y, width: 6, height: pl, background: "#fff" }} />
            <div style={{ position: "absolute", left: x - 14, top: y - 14, width: 28, height: 28, borderRadius: "50%", background: "#fff", border: `6px solid ${P.rail}`, boxSizing: "border-box" }} />
            {s > 0 && (
              <div style={{ position: "absolute", left: x - cw / 2, top: up ? pinY - ch - P.labelSize * 1.3 : pinY, width: cw, transformOrigin: up ? "50% 100%" : "50% 0", transform: `scale(${s})` }}>
                {up && <div style={{ fontFamily: "NeoHv", fontSize: P.labelSize, color: "#fff", textAlign: "left", whiteSpace: "nowrap", marginBottom: 6 }}>{it.label}</div>}
                <div style={{ width: cw, height: ch, border: "6px solid #fff", boxSizing: "border-box", overflow: "hidden", background: "#fff" }}><Img src={src(it.img)} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: it.pos ?? "50% 50%" }} /></div>
                {!up && <div style={{ fontFamily: "NeoHv", fontSize: P.labelSize, color: "#fff", textAlign: "left", whiteSpace: "nowrap", marginTop: 6 }}>{it.label}</div>}
              </div>
            )}
          </React.Fragment>
        );
      })}
    </AbsoluteFill>
  );
};

// ══ 23. VsBoxingGloves — VS 로봇팔 복싱 글러브 ═════════════════════════════════
// [ref4-samsung 00:32:20] 노랑 배경 + 주황 불꽃 실루엣 루프(≈10f 형태 교체) → 파랑·빨강 글러브(로봇팔)가 ±15px 반위상 보빙(20f) → 중앙 흰 뾰족 버스트 + 'VS'
export const VsBoxingGlovesParams = z.object({
  enterDur: num(8, 1, 30, 1, "글러브 진입", "timing", "f"),
  burstPop: num(5, 1, 20, 1, "VS 버스트 팝", "timing", "f"),
  bobPeriod: num(20, 6, 60, 1, "보빙 주기", "timing", "f"),
  bobAmp: num(15, 0, 60, 1, "보빙 폭", "motion", "px"),
  flameEvery: num(10, 2, 30, 1, "불꽃 형태 교체", "timing", "f"),
  gloveSize: num(600, 300, 900, 10, "글러브 크기", "size", "px"),
  vsSize: num(130, 60, 220, 2, "VS 글자 크기", "size", "px"),
  left: col("#2e3fb0", "왼쪽 글러브 색"),
  right: col("#e02a2a", "오른쪽 글러브 색"),
  flame: col("#F59A3A", "불꽃 색"),
  bg: col("#FBD27D", "배경색"),
});
export type VsBoxingGlovesP = z.infer<typeof VsBoxingGlovesParams>;
/** 세모지 복싱 글러브 — 오른쪽으로 뻗는 방향(커프 왼쪽). color 가 붉은 계열이면 빨강(xc_glove_red), 아니면 파랑(boxing_glove_blue 좌우반전). 커프 로고는 코드 */
const isWarm = (c: string) => { const m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})/i.exec(c); if (!m) return false; const [r, g, b] = [1, 2, 3].map((i) => parseInt(m[i], 16)); return r > b && r > g; };
const Glove: React.FC<{ color: string; size: number; logo?: RN; flip?: boolean }> = ({ color, size, logo, flip }) => {
  const red = isWarm(color);
  return (
    <div style={{ position: "relative", width: size, height: size * 0.87 }}>
      <Img src={prop(red ? "xc_glove_red" : "boxing_glove_blue")} style={{ position: "absolute", inset: 0, width: size, height: size * 0.87, objectFit: "contain", transform: red ? undefined : "scaleX(-1)", filter: "drop-shadow(0 10px 12px rgba(0,0,0,0.2))" }} />
      {logo && <div style={{ position: "absolute", left: size * 0.02, top: size * 0.3, width: size * 0.2, height: size * 0.26, display: "flex", alignItems: "center", justifyContent: "center", transform: flip ? "scaleX(-1)" : undefined }}>{logo}</div>}
    </div>
  );
};
/** 세모지 로봇팔 마디(robot_arm_segment 1454×701: 관절 A (216,530) → B (1320,194)). 관절 A 를 p 에 두고 q 쪽으로 회전, 배율 k */
const ARM = { w: 1454, h: 701, ax: 216, ay: 530, bx: 1320, by: 194 };
const ArmSeg: React.FC<{ p: Pt; q: Pt; k: number }> = ({ p, q, k }) => {
  const rot = Math.atan2(q[1] - p[1], q[0] - p[0]) - Math.atan2(ARM.by - ARM.ay, ARM.bx - ARM.ax);
  return <Img src={prop("robot_arm_segment")} style={{ position: "absolute", left: p[0] - ARM.ax * k, top: p[1] - ARM.ay * k, width: ARM.w * k, height: ARM.h * k, transformOrigin: `${ARM.ax * k}px ${ARM.ay * k}px`, transform: `rotate(${rot}rad)` }} />;
};
export const VsBoxingGloves: React.FC<{ at: number; logos?: [RN, RN]; seed?: string; p?: Partial<VsBoxingGlovesP> }> = ({ at, logos, seed = "vsg", p }) => {
  const P = def(VsBoxingGlovesParams, p);
  const f = useCurrentFrame();
  const g = Math.max(0, f - at), S = P.gloveSize;
  const cyc = Math.floor(g / P.flameEvery);
  const flamePath = (k: string, cx: number, base: number, w: number, hmax: number) => {
    const n = 7, pts: string[] = [`M${cx - w / 2},${base}`];
    for (let i = 0; i < n; i++) {
      const x0 = cx - w / 2 + (i / n) * w, x1 = cx - w / 2 + ((i + 1) / n) * w, h = hmax * (0.45 + 0.55 * random(`${k}${i}`)) * (1 - Math.abs(i - n / 2 + 0.5) / n);
      const lean = (random(`${k}l${i}`) - 0.5) * 60;
      pts.push(`Q${x0 + lean},${base - h * 0.6} ${(x0 + x1) / 2 + lean},${base - h} Q${x1},${base - h * 0.5} ${x1},${base - h * 0.15}`);
    }
    pts.push(`L${cx + w / 2},${base} Z`);
    return pts.join(" ");
  };
  const ent = (side: number) => (f >= at ? lerp(f, at, at + P.enterDur, side * 900, 0, EXPO_OUT) : side * 900);
  const bob = (side: number) => Math.sin((g / P.bobPeriod) * TAU + (side > 0 ? Math.PI : 0)) * P.bobAmp * -side;
  const burst = (() => {
    const n = 14, pts: string[] = [];
    for (let i = 0; i < n * 2; i++) { const a = (i / (n * 2)) * TAU, r = i % 2 ? 0.55 + 0.1 * random(`${seed}b${i}`) : 0.85 + 0.15 * random(`${seed}B${i}`); pts.push(`${Math.cos(a) * r * 200},${Math.sin(a) * r * 170}`); }
    return pts.join(" ");
  })();
  const bs = pop(f, at + P.enterDur - 2, P.burstPop, 0.2, 1.15);
  return (
    <AbsoluteFill style={{ background: P.bg }}>
      <svg width={W} height={H} style={{ position: "absolute" }}>
        <path d={flamePath(`${seed}f${cyc}`, 960, H + 40, 1500, 900)} fill={P.flame} />
        <path d={flamePath(`${seed}g${cyc}`, 960, H + 40, 1000, 620)} fill="#F7B24E" />
      </svg>
      {/* 로봇팔: 팔꿈치(960±820, 760)에 두 마디의 관절을 겹치고 어깨(화면 아래)·손목(글러브 커프) 쪽으로 회전 */}
      {[-1, 1].map((s) => {
        const x = 960 + s * 470 + ent(s) + bob(s);
        const el: Pt = [960 + s * 820 + ent(s), 760];
        return (
          <React.Fragment key={s}>
            <ArmSeg p={el} q={[960 + s * 900 + ent(s), H + 60]} k={0.3} />
            <ArmSeg p={el} q={[x + s * 180, 560]} k={0.3} />
          </React.Fragment>
        );
      })}
      {[-1, 1].map((s) => (
        <div key={s} style={{ position: "absolute", left: 960 + s * 470 + ent(s) + bob(s) - S / 2, top: 400 - S * 0.43, transform: `${s > 0 ? "scaleX(-1) " : ""}rotate(12deg)` }}>
          <Glove color={s < 0 ? P.left : P.right} size={S} logo={logos?.[s < 0 ? 0 : 1]} flip={s > 0} />
        </div>
      ))}
      {bs > 0 && (
        <At x={960} y={290} s={bs}>
          <div style={{ position: "relative", width: 420, height: 360 }}>
            <svg width={420} height={360} viewBox="-210 -180 420 360" style={{ position: "absolute" }}><polygon points={burst} fill="#fff" /></svg>
            <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "NeoHv", fontSize: P.vsSize, color: "#111" }}>VS</div>
          </div>
        </At>
      )}
    </AbsoluteFill>
  );
};

// ══ 24. FinTableRowAppend — 연도 실적표 행 추가 + 적자/흑자 배지 ═════════════════════
// [ref4-samsung 01:32:25] 좌 로고 / 우 연파랑 패널 표 → 행이 페이드+아래→위 12px 6f 로 하나씩 추가 → 원형 배지 0→1.1→1 5f → 빨간 도장 -12° 슬램
export const FinTableRowAppendParams = z.object({
  rowFade: num(6, 1, 20, 1, "행 페이드", "timing", "f"),
  rowRise: num(12, 0, 60, 1, "행 상승 거리", "motion", "px"),
  rowGap: num(10, 1, 40, 1, "행 간격", "timing", "f"),
  badgeDelay: num(12, 0, 60, 1, "배지 지연", "timing", "f"),
  badgePop: num(5, 1, 20, 1, "배지 팝", "timing", "f"),
  rowH: num(74, 30, 120, 1, "행 높이", "size", "px"),
  textSize: num(46, 20, 80, 1, "행 글자 크기", "size", "px"),
  badgeD: num(140, 60, 240, 2, "배지 지름", "size", "px"),
  posScale: num(1.2, 1, 1.6, 0.05, "흑자 강조 배율", "motion"),
  neg: col("#E0263F", "음수 색"),
  posC: col("#1d2f7a", "양수 색"),
  panel: col("#C9E3EA", "표 패널 색"),
});
export type FinTableRowAppendP = z.infer<typeof FinTableRowAppendParams>;
export type FinRow = { year: string; value: string; neg?: boolean };
export const FinTableRowAppend: React.FC<{ at: number; title?: string; logo?: RN; rows: FinRow[]; badge?: { text: string; color?: string }; stamp?: { text: string; at: number }; p?: Partial<FinTableRowAppendP> }> = ({ at, title = "바이오로직스", logo, rows, badge, stamp, p }) => {
  const P = def(FinTableRowAppendParams, p);
  const f = useCurrentFrame();
  const px = 900, tx = 1080, tw = 640, ty = 330;
  const bAt = at + rows.length * P.rowGap + P.badgeDelay;
  return (
    <AbsoluteFill style={{ background: "#E6F0F2" }}>
      <div style={{ position: "absolute", left: px, top: 0, width: W - px, height: H, background: P.panel }} />
      <div style={{ position: "absolute", left: 0, top: 0, width: px, height: H, display: "flex", alignItems: "center", justifyContent: "center" }}>{logo ?? <div style={{ fontFamily: "NeoHv", fontSize: 96, color: "#1b3f94", fontStyle: "italic" }}>BIO·A</div>}</div>
      <div style={{ position: "absolute", left: tx + tw / 2 - 220, top: 120, width: 440, padding: "18px 0", background: "#f4f7f8", textAlign: "center", fontFamily: "NeoHv", fontSize: 50, color: "#223", boxShadow: "0 4px 10px rgba(0,0,0,0.12)" }}>{title}</div>
      {rows.map((r, i) => {
        const t = at + i * P.rowGap;
        if (f < t) return null;
        const y = ty + i * P.rowH + lerp(f, t, t + P.rowFade, P.rowRise, 0, E_OUT);
        const neg = r.neg ?? r.value.includes("-");
        return (
          <div key={i} style={{ position: "absolute", left: tx, top: y, width: tw, height: P.rowH, borderBottom: "3px solid rgba(255,255,255,0.9)", display: "flex", alignItems: "center", justifyContent: "space-between", opacity: lerp(f, t, t + P.rowFade, 0, 1) }}>
            <div style={{ fontFamily: "NeoHv", fontSize: P.textSize, color: "#222" }}>{r.year}</div>
            <div style={{ fontFamily: "NeoHv", fontSize: P.textSize, color: neg ? P.neg : P.posC, transform: neg ? undefined : `scale(${P.posScale})`, transformOrigin: "100% 50%" }}>{r.value}</div>
          </div>
        );
      })}
      {badge && f >= bAt && (
        <At x={tx + tw + 70} y={ty + (rows.length - 0.5) * P.rowH} s={kf(f, bAt, [0, P.badgePop * 0.6, P.badgePop], [0, 1.1, 1])}>
          <div style={{ width: P.badgeD, height: P.badgeD, borderRadius: "50%", background: badge.color ?? P.neg, color: "#fff", fontFamily: "NeoHv", fontSize: P.badgeD * 0.3, display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 6px 12px rgba(0,0,0,0.2)" }}>{badge.text}</div>
        </At>
      )}
      {stamp && <Stamp text={stamp.text} x={tx + tw / 2} y={ty + rows.length * P.rowH * 0.5} at={stamp.at} rot={-12} size={100} />}
    </AbsoluteFill>
  );
};

// ══ 25. SignalWaveDiagram — 신호 파형 드로우 다이어그램 ═════════════════════════════
// [ref4-samsung 01:09:20] 갈색 사인파가 끝 흰 화살표와 함께 왼→오 1.8s linear 드로우 → 파형 위 A/B/C 원형 태그 0.6s 스태거 팝 → 각 사용자에게 지그재그 번개선 6f 드로우
export const SignalWaveDiagramParams = z.object({
  drawDur: num(54, 6, 150, 1, "파형 드로우(1.8s)", "timing", "f"),
  tagStagger: num(18, 0, 60, 1, "태그 스태거(0.6s)", "timing", "f"),
  tagPop: num(5, 1, 20, 1, "태그 팝", "timing", "f"),
  zigDelay: num(24, 0, 90, 1, "연결선 지연", "timing", "f"),
  zigDur: num(6, 1, 30, 1, "연결선 드로우", "timing", "f"),
  amp: num(80, 20, 200, 2, "진폭", "size", "px"),
  cycles: num(12, 2, 30, 1, "파형 주기 수", "size"),
  stroke: num(8, 2, 20, 1, "파형 두께", "size", "px"),
  tagD: num(90, 40, 160, 2, "태그 지름", "size", "px"),
  zigW: num(4, 1, 12, 0.5, "연결선 두께", "size", "px"),
  wave: col("#6B3A1F", "파형 색"),
  bg: col("#a8e0e2", "배경색"),
});
export type SignalWaveDiagramP = z.infer<typeof SignalWaveDiagramParams>;
export type WaveTag = { label: string; color: string; u: number; to: Pt; user?: RN };
export const SignalWaveDiagram: React.FC<{ at: number; tags: WaveTag[]; label?: string; p?: Partial<SignalWaveDiagramP> }> = ({ at, tags, label = "TDMA", p }) => {
  const P = def(SignalWaveDiagramParams, p);
  const f = useCurrentFrame();
  const x0 = 180, x1 = 1520, wy = 220;
  const prog = f >= at ? lerp(f, at, at + P.drawDur, 0, 1, Easing.linear) : 0;
  const N = 400, pts: string[] = [];
  const yAt = (u: number) => wy + Math.sin(u * P.cycles * TAU) * P.amp;
  for (let i = 0; i <= N * prog; i++) { const u = i / N; pts.push(`${(x0 + (x1 - x0) * u).toFixed(1)},${yAt(u).toFixed(1)}`); }
  const hx = x0 + (x1 - x0) * prog;
  const tAt = (i: number) => at + P.drawDur + 4 + i * P.tagStagger;
  const zAt = tAt(tags.length - 1) + P.zigDelay;
  const zig = (a: Pt, b: Pt, k: number) => { const out: Pt[] = []; const n = 8; for (let i = 0; i <= n; i++) { const t = i / n; const nx = -(b[1] - a[1]), ny = b[0] - a[0], l = Math.hypot(nx, ny) || 1; const j = i === 0 || i === n ? 0 : (i % 2 ? 1 : -1) * 18; out.push([a[0] + (b[0] - a[0]) * t + (nx / l) * j, a[1] + (b[1] - a[1]) * t + (ny / l) * j]); } return out.map((q) => q.join(",")).join(" "); };
  return (
    <AbsoluteFill style={{ background: P.bg }}>
      <svg width={W} height={H} style={{ position: "absolute" }}>
        <ellipse cx={500} cy={1150} rx={900} ry={330} fill="#8cc34a" /><ellipse cx={1500} cy={1180} rx={900} ry={360} fill="#7fb542" />
        {pts.length > 1 && <polyline points={pts.join(" ")} fill="none" stroke={P.wave} strokeWidth={P.stroke} strokeLinejoin="round" />}
        {prog > 0 && prog < 1.001 && <polygon points={`${hx + 34},${yAt(prog)} ${hx - 4},${yAt(prog) - 18} ${hx - 4},${yAt(prog) + 18}`} fill="#fff" />}
        {prog >= 1 && <polygon points={`${x1 + 50},${wy} ${x1 + 12},${wy - 18} ${x1 + 12},${wy + 18}`} fill="#fff" />}
        {prog >= 1 && <line x1={x1} y1={wy} x2={x1 + 20} y2={wy} stroke="#fff" strokeWidth={6} />}
        {tags.map((t, i) => {
          if (f < zAt) return null;
          const a: Pt = [x0 + (x1 - x0) * t.u, yAt(t.u) + P.tagD * 0.5];
          return <polyline key={i} points={zig(a, t.to, i)} fill="none" stroke={t.color} strokeWidth={P.zigW} pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - lerp(f, zAt + i * 3, zAt + i * 3 + P.zigDur, 0, 1)} />;
        })}
      </svg>
      {/* 세모지 송신탑(antenna_tower) — 기존 선화 자리(960, 560~860) */}
      <KitImg id="antenna_tower" w={(310 * 481) / 1411} h={310} style={{ position: "absolute", left: 960 - (310 * 481) / 1411 / 2, top: 552 }} />
      <div style={{ position: "absolute", left: 960 - 90, top: 870, width: 180, background: "#5b3a1e", color: "#fff", fontFamily: "NeoHv", fontSize: 44, textAlign: "center", padding: "6px 0" }}>{label}</div>
      {tags.map((t, i) => (
        <React.Fragment key={i}>
          {t.user ?? (
            // 세모지 캐스트 사용자 + 발밑 원판 = 태그 색(누가 어느 신호인지)
            <div style={{ position: "absolute", left: t.to[0] - 60, top: t.to[1], width: 120, height: 270 }}>
              <div style={{ position: "absolute", left: 60 - 62, top: 252, width: 124, height: 30, borderRadius: "50%", background: t.color, opacity: 0.9 }} />
              <CastFig cast={(["c3_woman", "c2_boss", "walker1"] as const)[i % 3]} h={260} w={120} seed={`swd${i}`} style={{ position: "absolute", left: 0, top: 0 }} />
            </div>
          )}
          {f >= tAt(i) && <At x={x0 + (x1 - x0) * t.u} y={yAt(t.u)} s={pop(f, tAt(i), P.tagPop, 0.2, 1.15)}><div style={{ width: P.tagD, height: P.tagD, borderRadius: "50%", background: t.color, border: "5px solid #fff", boxSizing: "border-box", color: "#fff", fontFamily: "NeoHv", fontSize: P.tagD * 0.5, display: "flex", alignItems: "center", justifyContent: "center" }}>{t.label}</div></At>}
        </React.Fragment>
      ))}
    </AbsoluteFill>
  );
};

// ══ 26. CandlestickGrowth — 캔들차트 순차 성장 + 떡상 화살표 ═══════════════════════
// [ref4-samsung 01:27:40] 배경 디포커스 12f → 격자 위 캔들이 6f 간격으로 scaleY 0→1 5f 성장 + 얇은 추세선 → 굵은 초록 지그재그 화살표 10f 드로우 → '떡상' 필 팝
export const CandlestickGrowthParams = z.object({
  bgBlurDur: num(12, 1, 40, 1, "배경 디포커스", "timing", "f"),
  bgBlur: num(10, 0, 30, 1, "배경 블러 세기", "look", "px"),
  stagger: num(6, 1, 30, 1, "캔들 간격", "timing", "f"),
  grow: num(5, 1, 20, 1, "캔들 성장", "timing", "f"),
  arrowDelay: num(10, 0, 60, 1, "화살표 지연", "timing", "f"),
  arrowDur: num(10, 2, 40, 1, "화살표 드로우", "timing", "f"),
  labelPop: num(6, 1, 20, 1, "라벨 팝", "timing", "f"),
  candleW: num(44, 10, 90, 1, "캔들 폭", "size", "px"),
  arrowW: num(14, 4, 40, 1, "화살표 두께", "size", "px"),
  trendW: num(2, 0, 8, 0.5, "추세선 두께", "size", "px"),
  candle: col("#E0105A", "캔들 색"),
  arrow: col("#3E8E4A", "화살표 색"),
});
export type CandlestickGrowthP = z.infer<typeof CandlestickGrowthParams>;
export const CandlestickGrowth: React.FC<{ at: number; bg?: string; values?: number[]; label?: string; ticks?: string[]; title?: string; p?: Partial<CandlestickGrowthP> }> = ({ at, bg = "real/museum.jpg", values = [8, 22, 20, 40, 34, 60, 55, 82, 76, 100], label = "떡상", ticks = ["9일", "10일", "11일", "12일"], title, p }) => {
  const P = def(CandlestickGrowthParams, p);
  const f = useCurrentFrame();
  const gx = 560, gy = 150, gw = 900, gh = 760, n = values.length;
  const cAt = at + P.bgBlurDur;
  const vy = (v: number) => gy + gh - 60 - (v / 100) * (gh - 160);
  const cx = (i: number) => gx + 70 + (i * (gw - 140)) / Math.max(1, n - 1);
  const shown = values.map((_, i) => f >= cAt + i * P.stagger);
  const trend = values.map((v, i) => [cx(i), vy(v) + 30] as Pt).filter((_, i) => shown[i]);
  const aAt = cAt + (n - 1) * P.stagger + P.grow + P.arrowDelay, lAt = aAt + P.arrowDur;
  return (
    <AbsoluteFill>
      <Img src={src(bg)} style={{ position: "absolute", width: "100%", height: "100%", objectFit: "cover", filter: `blur(${f >= at ? lerp(f, at, at + P.bgBlurDur, 0, P.bgBlur) : 0}px)`, transform: "scale(1.04)" }} />
      <AbsoluteFill style={{ background: `rgba(210,225,215,${f >= at ? lerp(f, at, at + P.bgBlurDur, 0, 0.45) : 0})` }} />
      {f >= at && (
        <div style={{ position: "absolute", left: gx, top: gy, width: gw, height: gh, opacity: lerp(f, at, at + P.bgBlurDur, 0, 1), backgroundImage: "linear-gradient(rgba(255,255,255,0.75) 2px, transparent 2px), linear-gradient(90deg, rgba(255,255,255,0.75) 2px, transparent 2px)", backgroundSize: "60px 60px", background: "rgba(255,255,255,0.35)" }}>
          <div style={{ position: "absolute", inset: 0, backgroundImage: "linear-gradient(rgba(255,255,255,0.8) 2px, transparent 2px), linear-gradient(90deg, rgba(255,255,255,0.8) 2px, transparent 2px)", backgroundSize: "60px 60px" }} />
        </div>
      )}
      {title && f >= at && <div style={{ position: "absolute", left: gx + gw / 2 - 150, top: gy - 20, width: 300, background: "#fff", textAlign: "center", fontFamily: "NeoHv", fontSize: 48, padding: "4px 0" }}>{title}</div>}
      <svg width={W} height={H} style={{ position: "absolute" }}>
        {values.map((v, i) => {
          const t = cAt + i * P.stagger;
          if (f < t) return null;
          const prev = i ? values[i - 1] : 0;
          const top = vy(v), bot = vy(Math.max(0, prev - 6));
          const s = kf(f, t, [0, P.grow], [0, 1], E_OUT);
          const hh = (bot - top) * s;
          return <g key={i}><rect x={cx(i) - 2} y={bot - hh - 18 * s} width={4} height={hh + 36 * s} fill={P.candle} /><rect x={cx(i) - P.candleW / 2} y={bot - hh} width={P.candleW} height={Math.max(2, hh)} fill={P.candle} /></g>;
        })}
        {trend.length > 1 && P.trendW > 0 && <path d={trend.map((q, i) => (i === 0 ? `M${q[0]},${q[1]}` : `Q${(trend[i - 1][0] + q[0]) / 2},${q[1] + 50} ${q[0]},${q[1]}`)).join(" ")} fill="none" stroke={P.candle} strokeWidth={P.trendW} />}
      </svg>
      {ticks.map((t, i) => f >= at && <div key={i} style={{ position: "absolute", left: gx + 80 + (i * (gw - 160)) / Math.max(1, ticks.length - 1) - 50, top: gy + gh + 10, width: 100, textAlign: "center", fontFamily: "NeoEb", fontSize: 30, color: "#3b5f9a" }}>{t}</div>)}
      {f >= aAt && <ZigzagArrow at={aAt} pts={[[300, 780], [470, 640], [590, 720], [800, 520], [920, 590], [1120, 380]]} color={P.arrow} width={P.arrowW} dur={P.arrowDur} flash={false} />}
      {f >= lAt && <At x={420} y={520} s={pop(f, lAt, P.labelPop, 0.3, 1.1)} blur={unblur(f, lAt, P.labelPop * 0.6, 8)}><div style={{ background: "#5cbf6a", color: "#fff", fontFamily: "NeoHv", fontSize: 64, padding: "6px 30px", borderRadius: 8 }}>{label}</div></At>}
    </AbsoluteFill>
  );
};
