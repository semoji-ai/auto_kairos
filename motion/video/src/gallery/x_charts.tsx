import React from "react";
import { AbsoluteFill } from "remotion";
import { runGallery, Demo } from "./runner";
import { LogoChar } from "../lib/charts";
import * as X from "../lib/x_charts";

type PP<S> = { p?: Partial<S> };

const D01: React.FC<PP<X.MascotStepBarsP>> = ({ p }) => <X.MascotStepBars at={6} p={p} mascot={<LogoChar d={150} bg="#E2362B" text="짜장" />} />;
const D02: React.FC<PP<X.TicTacToeWinP>> = ({ p }) => <X.TicTacToeWin at={6} p={p} />;
const D03: React.FC<PP<X.RoadLaneAnalogyP>> = ({ p }) => <X.RoadLaneAnalogy at={0} p={p} />;
const D04: React.FC<PP<X.SilhouettePriceCompareP>> = ({ p }) => (
  <X.SilhouettePriceCompare at={6} p={p} hero="img/s05_bowl.png" price="$ 9,995"
    rivals={[{ img: "img/s05_chunjang.png", price: "$1,500" }, { img: "img/s05_bowl.png", price: "$2,000" }]} />
);
const D05: React.FC<PP<X.DDayEquationP>> = ({ p }) => <X.DDayEquation at={6} p={p} />;
const D06: React.FC<PP<X.DeviceTessellationP>> = ({ p }) => <X.DeviceTessellation at={6} p={p} />;
const D07: React.FC<PP<X.RecordMilestoneBadgeP>> = ({ p }) => (
  <X.RecordMilestoneBadge p={p} title="춘장상사" compare={{ at: 150, text: "코스피\n시가총액" }}
    steps={[
      { at: 6, value: "1조 달러", date: "2018년 8월 2일", burst: true },
      { at: 60, value: "2조 달러", date: "2020년 8월 19일", crown: true },
      { at: 110, value: "3조 달러", date: "2022년 1월 3일", star: "전세계\n최초" },
    ]} />
);
const D08: React.FC<PP<X.FlagMapStatLinkP>> = ({ p }) => <X.FlagMapStatLink at={6} p={p} left="2억 8,100만 명" right="3억 2천만 장 판매" />;
const D09: React.FC<PP<X.PictogramCrowdMarqueeP>> = ({ p }) => <X.PictogramCrowdMarquee at={6} p={p} />;
const D10: React.FC<PP<X.ProductAnchorValuePillP>> = ({ p }) => <X.ProductAnchorValuePill at={6} p={p} value="284,830L" />;
const D11: React.FC<PP<X.MapSpreadPullbackP>> = ({ p }) => <X.MapSpreadPullback at={6} p={p} />;
const RANK = ["짜장면", "짬뽕", "탕수육", "마라탕", "볶음밥", "냉면", "비빔밥", "김치찌개", "떡볶이", "라면"];
const D12: React.FC<PP<X.BottomUpRankStackP>> = ({ p }) => (
  <X.BottomUpRankStack at={6} p={p} title="외식 메뉴 순위"
    side={{ title: "중식 순위", rows: [{ label: "짜장면", color: "#c8102e", dot: "#1d2c6b" }, { label: "짬뽕", color: "#1d2c6b" }, { label: "탕수육" }, { label: "마라탕" }, { label: "볶음밥" }] }}
    rows={RANK.map((l) => (l === "짜장면" ? { label: l, color: "#c8102e", dot: "#1d2c6b" } : { label: l }))} />
);
const D13: React.FC<PP<X.EsportsVsScoreboardP>> = ({ p }) => <X.EsportsVsScoreboard at={6} p={p} />;
const D14: React.FC<PP<X.SegmentedThermometerDrainP>> = ({ p }) => <X.SegmentedThermometerDrain at={6} p={p} />;
const D15: React.FC<PP<X.HandHeldDocLineupP>> = ({ p }) => (
  <X.HandHeldDocLineup p={p} stamp={{ text: "실현 불가!", at: 140 }}
    cards={[{ at: 6, amount: "650억", by: "건설부" }, { at: 36, amount: "490억", by: "육군공병감실" }, { at: 66, amount: "330억", by: "재무부" }, { at: 96, amount: "280억", by: "현대건설" }, { at: 118, amount: "180억", by: "정부 예산" }]} />
);
const D16: React.FC<PP<X.ProportionRulerRoadP>> = ({ p }) => <X.ProportionRulerRoad at={6} p={p} />;
const D17: React.FC<PP<X.TunnelLengthCompareP>> = ({ p }) => <X.TunnelLengthCompare at={6} p={p} />;
const D18: React.FC<PP<X.MapLecturerCountryFillP>> = ({ p }) => <X.MapLecturerCountryFill at={6} p={p} />;
const D19: React.FC<PP<X.CorpLineageFlowP>> = ({ p }) => (
  <X.CorpLineageFlow p={p} nodes={[
    { at: 0, logo: <X.LogoMark name="한라그룹" shape="tri" /> },
    { at: 20, logo: <X.LogoMark name="DAEWOO" shape="shell" color="#1f4fa0" />, year: "1980년", child: { text: "한국중공업", at: 70 } },
    { at: 115, logo: <X.LogoMark name="두산" shape="circle" color="#2a62c9" />, year: "2001년" },
  ]} />
);
const D20: React.FC<PP<X.ElectionPosterDropRankP>> = ({ p }) => (
  <X.ElectionPosterDropRank at={6} p={p} source="출처: 가상 자료"
    posters={[
      { img: "real/chinatown.jpg", num: "2", name: "김짬뽕", color: "#2f8f4a", rank: 2, share: "33.8%", rankAt: 66 },
      { img: "real/jjajang.jpg", num: "1", name: "김짜장", color: "#3a2f8f", rank: 1, share: "42%", rankAt: 48 },
      { img: "real/zhajiang.jpg", num: "3", name: "정탕수", color: "#2c5fb0", rank: 3, share: "16.3%", rankAt: 84 },
    ]} />
);
const D21: React.FC<PP<X.SplitFlagExchangeP>> = ({ p }) => (
  <X.SplitFlagExchange p={p} items={[{ side: "right", lines: ["현대건설에게", "사업권 7개"], at: 6 }, { side: "left", lines: ["대북 사업", "5억 달러"], at: 56 }]} />
);
const D22: React.FC<PP<X.AlternatingPhotoTimelineP>> = ({ p }) => (
  <X.AlternatingPhotoTimeline at={6} p={p} items={[
    { img: "real/port.jpg", label: "개항(1883.01)", at: 16 }, { img: "real/chinatown.jpg", label: "차이나타운(1884.04)", at: 40 },
    { img: "real/museum.jpg", label: "공화춘(1905.03)", at: 64 }, { img: "real/jjajang.jpg", label: "짜장면(1948.10)", at: 88 }, { img: "real/ghc_now.jpg", label: "박물관(2012.04)", at: 112 },
  ]} />
);
const D23: React.FC<PP<X.VsBoxingGlovesP>> = ({ p }) => (
  <X.VsBoxingGloves at={6} p={p} logos={[<div style={{ fontFamily: "NeoHv", fontSize: 40, color: "#2e3fb0" }}>짜장</div>, <div style={{ fontFamily: "NeoHv", fontSize: 40, color: "#e02a2a" }}>짬뽕</div>]} />
);
const D24: React.FC<PP<X.FinTableRowAppendP>> = ({ p }) => (
  <X.FinTableRowAppend at={6} p={p} badge={{ text: "적자" }} stamp={{ text: "회계 기준 변경", at: 110 }}
    rows={[{ year: "2011", value: "(-)79" }, { year: "2012", value: "(-)350" }, { year: "2013", value: "(-)624" }, { year: "2014", value: "(-)280" }]} />
);
const D25: React.FC<PP<X.SignalWaveDiagramP>> = ({ p }) => (
  <X.SignalWaveDiagram at={6} p={p} tags={[
    { label: "A", color: "#E8452C", u: 0.12, to: [330, 640] }, { label: "B", color: "#2F6FD6", u: 0.42, to: [1180, 700] }, { label: "C", color: "#F2D21B", u: 0.72, to: [1620, 520] },
  ]} />
);
const D26: React.FC<PP<X.CandlestickGrowthP>> = ({ p }) => <X.CandlestickGrowth at={6} p={p} title="춘장기획" />;

export const DEMOS: Demo[] = [
  { name: "MascotStepBars — 마스코트 막대 점프 + 카메라 트럭 + 순간이동", dur: 150, C: D01, schema: X.MascotStepBarsParams },
  { name: "TicTacToeWin — 틱택토 승리선 + 팻말 캐릭터", dur: 90, C: D02, schema: X.TicTacToeWinParams },
  { name: "RoadLaneAnalogy — 도로 차선 증가 비유(풀백)", dur: 100, C: D03, schema: X.RoadLaneAnalogyParams },
  { name: "SilhouettePriceCompare — 회색 실루엣 경쟁품 + 가격표", dur: 110, C: D04, schema: X.SilhouettePriceCompareParams },
  { name: "DDayEquation — D-DAY 달력 → 화살표 → 산출량", dur: 150, C: D05, schema: X.DDayEquationParams },
  { name: "DeviceTessellation — 기기 타일 가장자리부터 채움", dur: 90, C: D06, schema: X.DeviceTessellationParams },
  { name: "RecordMilestoneBadge — 기록 원형 배지 스텝업", dur: 180, C: D07, schema: X.RecordMilestoneBadgeParams },
  { name: "FlagMapStatLink — 국기 채움 지도 + 점선 통계", dur: 120, C: D08, schema: X.FlagMapStatLinkParams },
  { name: "PictogramCrowdMarquee — 픽토그램 군중 행진 + 병 팝", dur: 150, C: D09, schema: X.PictogramCrowdMarqueeParams },
  { name: "ProductAnchorValuePill — 제품 앵커 수치 캡슐 + 수요/공급 바", dur: 120, C: D10, schema: X.ProductAnchorValuePillParams },
  { name: "MapSpreadPullback — 지도 확산 풀백 + 레이더 파문", dur: 110, C: D11, schema: X.MapSpreadPullbackParams },
  { name: "BottomUpRankStack — 역순 순위 리스트 적층", dur: 150, C: D12, schema: X.BottomUpRankStackParams },
  { name: "EsportsVsScoreboard — VS 배너 + 7세그 스코어보드", dur: 110, C: D13, schema: X.EsportsVsScoreboardParams },
  { name: "SegmentedThermometerDrain — 세그먼트 온도계 배출 + 스프레이", dur: 90, C: D14, schema: X.SegmentedThermometerDrainParams },
  { name: "HandHeldDocLineup — 손에 든 견적서 라인업", dur: 170, C: D15, schema: X.HandHeldDocLineupParams },
  { name: "ProportionRulerRoad — 도로 비율 눈금자 채움", dur: 120, C: D16, schema: X.ProportionRulerRoadParams },
  { name: "TunnelLengthCompare — 터널 길이 비교(먼지 스폰)", dur: 110, C: D17, schema: X.TunnelLengthCompareParams },
  { name: "MapLecturerCountryFill — 지시봉 강의 + 국가 채움", dur: 120, C: D18, schema: X.MapLecturerCountryFillParams },
  { name: "CorpLineageFlow — 기업 계보 플로차트", dur: 160, C: D19, schema: X.CorpLineageFlowParams },
  { name: "ElectionPosterDropRank — 포스터 드롭 + 순위 필", dur: 120, C: D20, schema: X.ElectionPosterDropRankParams },
  { name: "SplitFlagExchange — 분할 국기 교환 화살표", dur: 110, C: D21, schema: X.SplitFlagExchangeParams },
  { name: "AlternatingPhotoTimeline — 교차 사진 타임라인", dur: 150, C: D22, schema: X.AlternatingPhotoTimelineParams },
  { name: "VsBoxingGloves — VS 로봇팔 복싱 글러브", dur: 90, C: D23, schema: X.VsBoxingGlovesParams },
  { name: "FinTableRowAppend — 실적표 행 추가 + 적자 배지 + 도장", dur: 150, C: D24, schema: X.FinTableRowAppendParams },
  { name: "SignalWaveDiagram — 신호 파형 드로우 + 태그 + 번개선", dur: 150, C: D25, schema: X.SignalWaveDiagramParams },
  { name: "CandlestickGrowth — 캔들 순차 성장 + 떡상 화살표", dur: 130, C: D26, schema: X.CandlestickGrowthParams },
];
export const GALLERY_DUR = Math.max(30, DEMOS.reduce((a, d) => a + d.dur, 0));
export const Gallery = runGallery(DEMOS);
