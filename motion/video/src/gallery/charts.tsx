import React from "react";
import { AbsoluteFill, Img } from "remotion";
import { z } from "zod";
import { src } from "../fx";
import { runGallery, Demo } from "./runner";
import {
  GlowBg, PieSweep, BarChartH, BarChartV, LineChart, Podium, TimelineBar, ZigzagArrow,
  CounterBadge, StatGauge, WaterfallStairs, MoneyTitle, DiscPie3D, AgileRings,
  PieSweepParams, PieSweepP, BarChartHParams, BarChartHP, BarChartVParams, BarChartVP, LineChartParams, LineChartP,
  PodiumParams, PodiumP, TimelineBarParams, TimelineBarP, ZigzagArrowParams, ZigzagArrowP, CounterBadgeParams, CounterBadgeP,
  StatGaugeParams, StatGaugeP, WaterfallStairsParams, WaterfallStairsP, MoneyTitleParams, MoneyTitleP,
  DiscPie3DParams, DiscPie3DP, AgileRingsParams, AgileRingsP,
} from "../lib/charts";

/** 데모마다 기본값이 스키마 기본과 다른 키는 스키마 기본을 데모 값으로 바꿔 둔다(Param-<id> 초기 화면 = 데모 화면) */
const redef = <S extends z.ZodObject<any>>(s: S, d: Partial<z.infer<S>>): S =>
  s.extend(Object.fromEntries(Object.entries(d).map(([k, v]) => {
    const t: any = s.shape[k];
    return [k, t.unwrap().default(v).describe(t.description)];
  }))) as unknown as S;

const Head: React.FC<{ text: string; color?: string; y?: number }> = ({ text, color = "#fff", y = 60 }) => (
  <div style={{ position: "absolute", top: y, width: "100%", textAlign: "center", fontFamily: "Jua", fontSize: 64, color }}>{text}</div>
);

const DPie1: React.FC<{ p?: Partial<PieSweepP> }> = ({ p }) => (
  <AbsoluteFill>
    <GlowBg color="#38AF45" />
    <Head text="국내 짜장면 시장 점유율" />
    <PieSweep at={6} x={960} y={590} r={330} pct={0.62} base="#32322F" wedge="#F0F000" fadeBase
      icon={<Img src={src("img/s05_bowl.png")} style={{ width: 170 }} />} iconSize={170} label="62%"
      second={{ pct: 0.21, color: "#EC4B1E", delay: 16, label: "21%" }} p={p} />
  </AbsoluteFill>
);

const DPie2: React.FC<{ p?: Partial<PieSweepP> }> = ({ p }) => (
  <AbsoluteFill>
    <GlowBg color="#009EE1" />
    <Head text="전 세계 춘장 소비의 절반이 한국" />
    <PieSweep at={6} x={1060} y={600} r={320} pct={0.48} long globe wedge="#F8C900" wedgeText="48%"
      sticker={{ img: "img/s05_chunjang.png", side: "left", delay: 10, w: 420 }} p={p} />
  </AbsoluteFill>
);

const DBarH: React.FC<{ p?: Partial<BarChartHP> }> = ({ p }) => (
  <BarChartH at={4} title="짜장면 한 그릇 가격" subtitle="2024년 지역별 평균 (단위: 원)" unit="원" max={8000}
    ticks={[0, 2000, 4000, 6000, 8000]} winner={2}
    rows={[{ label: "서울", value: 7308 }, { label: "경기", value: 6946 }, { label: "인천", value: 7523 }, { label: "부산", value: 6567 }, { label: "대구", value: 6417 }, { label: "광주", value: 6600 }]} p={p} />
);

const DBarV: React.FC<{ p?: Partial<BarChartVP> }> = ({ p }) => (
  <AbsoluteFill>
    <GlowBg color="#F4ECDD" glow="rgba(255,255,255,0.6)" />
    <BarChartV at={4} title="1인당 연간 소비량" max={80} maxH={380} baseY={830} unit="그릇"
      mascot={<Img src={src("img/s06_kid.png")} style={{ height: 150 }} />}
      groups={[
        { x: 520, caption: "2014년", bars: [{ label: "짜장면", value: 72, hi: true }, { label: "짬뽕", value: 41 }, { label: "탕수육", value: 23 }] },
        { x: 1400, caption: "2024년", bars: [{ label: "짜장면", value: 58, hi: true }, { label: "짬뽕", value: 49 }, { label: "마라탕", value: 37 }] },
      ]} p={p} />
  </AbsoluteFill>
);

const DLine1: React.FC<{ p?: Partial<LineChartP> }> = ({ p }) => (
  <LineChart at={6} underlay="img/s03_restaurant.jpg" title="짜장면 가격 추이" years={["1960", "1980", "2000", "2020", "2024"]}
    values={[15, 350, 3000, 5500, 7300]} min={0} max={8000} axis="draw" dot="big"
    pills={[{ idx: 0, text: "15원", delay: 4 }, { idx: 4, text: "7,300원", delay: 44, color: "#E69131" }]}
    stamp={{ text: "487배", x: 1180, y: 330, delay: 24 }} p={p} />
);

const DLine2: React.FC<{ p?: Partial<LineChartP> }> = ({ p }) => (
  <AbsoluteFill style={{ background: "#1F2A44" }}>
    <LineChart at={6} years={["2019", "2020", "2021", "2022", "2023"]} values={[40, 55, 52, 78, 92]} min={0} max={100}
      axis="fade" dot="small" lineColor="#fff" lineW={10} box={[260, 170, 1680, 700]}
      pills={[{ idx: 0, text: "40만 명", delay: 3 }, { idx: 4, text: "92만 명", delay: 36, color: "#F08A24" }]}
      crowd={{ delay: 2 }} title="차이나타운 방문객" p={p} />
  </AbsoluteFill>
);

const DPodium: React.FC<{ p?: Partial<PodiumP> }> = ({ p }) => (
  <Podium at={4} underlay="real/chinatown.jpg" title="중식 프랜차이즈 매출 순위"
    items={[
      { name: "홍콩반점", logo: "홍콩", color: "#E53935", h: 520, rank: 1 },
      { name: "짬뽕지존", logo: "지존", color: "#1E88E5", h: 400, rank: 2 },
      { name: "보배반점", logo: "보배", color: "#F2B705", h: 300, rank: 3 },
    ]} p={p} />
);

const DTimeline: React.FC<{ p?: Partial<TimelineBarP> }> = ({ p }) => (
  <TimelineBar at={6} wordmark="共和春" bg="#F3C623" y={560}
    nodes={[{ x: 300, label: "1905" }, { x: 960, label: "1948" }, { x: 1620, label: "2012" }]} p={p} />
);

const DZigUp: React.FC<{ p?: Partial<ZigzagArrowP> }> = ({ p }) => (
  <AbsoluteFill>
    <GlowBg color="#FFF4E0" glow="rgba(255,255,255,0.8)" />
    <Head text="매출 급상승" color="#E0161E" y={880} />
    <ZigzagArrow at={10} dir="up" p={p} />
  </AbsoluteFill>
);

const DZigDown: React.FC<{ p?: Partial<ZigzagArrowP> }> = ({ p }) => (
  <AbsoluteFill>
    <GlowBg color="#2A2F3A" glow="rgba(120,140,190,0.35)" />
    <Head text="가맹점 폐업 속출" y={60} />
    <ZigzagArrow at={10} dir="down" p={p} />
  </AbsoluteFill>
);

const DCounter: React.FC<{ p?: Partial<CounterBadgeP> }> = ({ p }) => (
  <AbsoluteFill>
    <GlowBg color="#5CC6D0" />
    <CounterBadge at={6} x={960} y={540} n={9} label="주문 폭주!" iconBg="#FEE500"
      icon={<div style={{ fontFamily: "NeoHv", fontSize: 44, color: "#3A1D1D" }}>배달</div>} p={p} />
  </AbsoluteFill>
);

const DGauge: React.FC<{ p?: Partial<StatGaugeP> }> = ({ p }) => (
  <AbsoluteFill>
    <GlowBg color="#F2F2F2" glow="rgba(255,255,255,0.9)" />
    <Head text="짜장면을 선택하는 이유" color="#222" />
    <StatGauge at={6} x={550} y={260} pct={0.82} label="저렴한 가격" icon="₩" p={p} />
    <StatGauge at={16} x={550} y={450} pct={0.64} label="빠른 배달" icon="배" iconBg="#F08A24" p={p} />
    <StatGauge at={26} x={550} y={640} pct={0.47} label="추억의 맛" icon="맛" iconBg="#73AF03" p={p} />
  </AbsoluteFill>
);

const DStairs: React.FC<{ p?: Partial<WaterfallStairsP> }> = ({ p }) => (
  <AbsoluteFill>
    <GlowBg color="#FBF6EA" glow="rgba(255,255,255,0.9)" />
    <Head text="짜장면이 식탁에 오기까지" color="#333" />
    <WaterfallStairs at={8} x0={330} y0={300} dx={300} dy={140} bw={200} bh={56} labels={["밀 수입", "제면", "춘장", "조리", "배달"]}
      mascot={<Img src={src("img/s06_kid.png")} style={{ height: 150 }} />} mascotW={110} mascotH={150} p={p} />
  </AbsoluteFill>
);

const DMoney: React.FC<{ p?: Partial<MoneyTitleP> }> = ({ p }) => (
  <AbsoluteFill>
    <GlowBg color="#FFF7E6" glow="rgba(255,236,180,0.9)" />
    <MoneyTitle at={6} text="20,000달러" y={560} p={p} />
  </AbsoluteFill>
);

const DDisc: React.FC<{ p?: Partial<DiscPie3DP> }> = ({ p }) => (
  <AbsoluteFill>
    <GlowBg color="#EAF6FA" glow="rgba(255,255,255,0.9)" />
    <Head text="배달 앱 시장 점유율" color="#222" />
    <DiscPie3D at={4} x={960} y={680} comp={0.28} compStart={-0.08} mainLabel="72%" compLabel="28%" mainLabelAt={[-230, 40]}
      hero={{ img: "img/s06_kid.png", h: 300, dx: -110, dy: -50 }}
      rival={{ img: "img/s03_woo.png", h: 300, dx: 250, dy: 10, delay: 40 }} p={p} />
  </AbsoluteFill>
);

const DAgile: React.FC<{ p?: Partial<AgileRingsP> }> = ({ p }) => (
  <AbsoluteFill>
    <GlowBg color="#F7F7F4" glow="rgba(255,255,255,0.9)" />
    <Head text="애자일 메뉴 개발 사이클" color="#222" />
    <AgileRings at={6} items={[
      { label: "기획", caption: "고객 인터뷰", c1: "#E53935", c2: "#FB8C00" },
      { label: "시식", caption: "소량 테스트", c1: "#FDD835", c2: "#43A047" },
      { label: "개선", caption: "레시피 수정", c1: "#1E88E5", c2: "#00ACC1" },
      { label: "출시", caption: "전 매장 확대", c1: "#8E24AA", c2: "#E53935" },
    ]} p={p} />
  </AbsoluteFill>
);


export const DEMOS: Demo[] = [
  { name: "PieSweep 기본 + 2nd wedge", dur: 120, C: DPie1, schema: redef(PieSweepParams, { r: 330 }) },
  { name: "PieSweep 지구본→파이 + 스티커", dur: 130, C: DPie2, schema: redef(PieSweepParams, { r: 320, sweepDur: 48, wedge: "#F8C900" }) },
  { name: "BarChartH 격자+리본+손그림원", dur: 150, C: DBarH, schema: BarChartHParams },
  { name: "BarChartV 2그룹 + 마스코트", dur: 140, C: DBarV, schema: redef(BarChartVParams, { maxH: 380 }) },
  { name: "LineChart 축드로잉·도장", dur: 150, C: DLine1, schema: LineChartParams },
  { name: "LineChart 페이드축·군중", dur: 140, C: DLine2, schema: redef(LineChartParams, { axisW: 24, lineColor: "#fff", lineW: 10 }) },
  { name: "Podium 순위 상승", dur: 110, C: DPodium, schema: PodiumParams },
  { name: "TimelineBar 모션블러", dur: 100, C: DTimeline, schema: TimelineBarParams },
  { name: "ZigzagArrow 상승", dur: 60, C: DZigUp, schema: ZigzagArrowParams },
  { name: "ZigzagArrow 하락+번개", dur: 60, C: DZigDown, schema: redef(ZigzagArrowParams, { color: "#fff", flash: true }) },
  { name: "CounterBadge 카운트→캡슐", dur: 140, C: DCounter, schema: CounterBadgeParams },
  { name: "StatGauge 전기 스파크", dur: 100, C: DGauge, schema: StatGaugeParams },
  { name: "WaterfallStairs 점프", dur: 120, C: DStairs, schema: redef(WaterfallStairsParams, { bw: 200, bh: 56 }) },
  { name: "MoneyTitle 3D 숫자", dur: 90, C: DMoney, schema: MoneyTitleParams },
  { name: "DiscPie3D 경쟁자 고스트", dur: 100, C: DDisc, schema: DiscPie3DParams },
  { name: "AgileRings 링 순차팝", dur: 110, C: DAgile, schema: AgileRingsParams },
];
export const GALLERY_DUR = Math.max(30, DEMOS.reduce((a, d) => a + d.dur, 0));
export const Gallery = runGallery(DEMOS);
