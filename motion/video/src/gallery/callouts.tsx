import React from "react";
import { AbsoluteFill, Img } from "remotion";
import { runGallery, Demo } from "./runner";
import { W, H, src } from "../fx";
import {
  CalloutConnector, DottedPathDraw, CircuitBranch, PillArrowPill, PillCollision, NeonTiles, CompareAB, TitleBox,
  ScrimTypewriter, Whiteboard, RedBoxBlink, HandDrawnCircle, BrowserMockup, CodeRainBg, ScreenshotGrid, ScreenshotCarousel,
  VersionStack, IconRowGrid, TreeDroplines, ShieldWings, MapPin, MedallionTree, PuzzleJoin, Icon, IconName,
  CalloutConnectorParams, DottedPathDrawParams, CircuitBranchParams, PillArrowPillParams, PillCollisionParams, NeonTilesParams, CompareABParams,
  TitleBoxParams, ScrimTypewriterParams, WhiteboardParams, RedBoxBlinkParams, HandDrawnCircleParams, BrowserMockupParams, ScreenshotGridParams,
  ScreenshotCarouselParams, VersionStackParams, IconRowGridParams, TreeDroplinesParams, ShieldWingsParams, MapPinParams, MedallionTreeParams, PuzzleJoinParams,
} from "../lib/callouts";
type DP = { p?: any };

// 갤러리 섹션: 콜아웃·텍스트·레이아웃 기법 — 좌하단에 기법 이름 라벨
const Flat: React.FC<{ c: string; children?: React.ReactNode }> = ({ c, children }) => <AbsoluteFill style={{ background: c }}>{children}</AbsoluteFill>;
const Photo: React.FC<{ img: string; dim?: number }> = ({ img, dim = 1 }) => <Img src={src(img)} style={{ position: "absolute", inset: 0, width: W, height: H, objectFit: "cover", filter: `brightness(${dim})` }} />;
const Disc: React.FC<{ name: IconName; color: string; bg?: string }> = ({ name, color, bg = "#fff" }) => (
  <div style={{ width: "100%", height: "100%", borderRadius: "50%", background: bg, display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 8px 18px rgba(0,0,0,0.35)" }}><div style={{ width: "58%", height: "58%" }}><Icon name={name} color={color} /></div></div>
);
const IMGS = ["real/chinatown.jpg", "real/chunjang.jpg", "real/ghc_closed.jpg", "real/ghc_now.jpg", "real/jjajang.jpg", "real/museum.jpg", "real/port.jpg", "real/zhajiang.jpg"];
const Logo: React.FC<{ v: number }> = ({ v }) => {
  const st: React.CSSProperties[] = [
    { fontFamily: "Yeonsung", fontSize: 64, color: "#7a2a1a" },
    { fontFamily: "Jalnan", fontSize: 56, color: "#C0392B", border: "5px solid #C0392B", padding: "8px 14px 2px", borderRadius: 10 },
    { fontFamily: "NeoHv", fontSize: 58, color: "#fff", background: "#1F6FE0", padding: "16px 20px 10px", borderRadius: 999 },
    { fontFamily: "Jua", fontSize: 66, color: "#E8521E" },
    { fontFamily: "NeoHv", fontSize: 62, color: "#111", letterSpacing: -3 },
  ];
  return <div style={{ ...st[v], whiteSpace: "nowrap", lineHeight: 1.1 }}>세모장</div>;
};

const D = {
  connector: ({ p }: DP) => (
    <Flat c="#222">
      <Photo img="img/s05_factory.jpg" dim={0.5} />
      <CalloutConnector p={p} at={6} label="춘장 공장" labelX={70} labelY={600} box={[60, 50, 470, 350]} path={[[650, 600], [720, 600], [720, 225], [530, 225]]}
        part={{ img: "img/s05_chunjang.png", x: 880, y: 120, w: 380, h: 320 }} title="춘장(春醬)" titleX={1290} titleY={160}
        subs={["콩을 발효시킨 검은 된장", "캐러멜을 넣어 단맛을 더했다"]}
        cards={[{ icon: "factory", text: "대량 생산" }, { icon: "truck", text: "전국 유통" }, { icon: "bowl", text: "짜장면 붐" }]} cardsX={760} cardsY={830} />
    </Flat>
  ),
  dotted: ({ p }: DP) => (
    <Flat c="#2A6F97">
      <DottedPathDraw p={p} at={6} pts={[[260, 820], [260, 520], [960, 520], [960, 260], [1660, 260]]} ends={[<Disc name="ship" color="#2A6F97" />, <Disc name="factory" color="#C0392B" />]} endSize={170} />
      <DottedPathDraw at={50} color="#111" dash={10} gap={8} width={5} pts={[[500, 900], [1400, 900], [1400, 700]]} />
      <div style={{ position: "absolute", left: 180, top: 930, fontFamily: "NeoHv", fontSize: 40, color: "#fff" }}>산둥 → 인천 → 서울</div>
    </Flat>
  ),
  circuit: ({ p }: DP) => (
    <Flat c="#15324A">
      <CircuitBranch p={p} at={6} hub={[480, 540]} hubNode={<Disc name="chip" color="#15324A" />} hubSize={220}
        branches={[
          { pts: [[590, 540], [900, 540], [900, 230], [1350, 230]], icon: <Disc name="phone" color="#1F6FE0" />, label: "스마트폰" },
          { pts: [[590, 540], [1350, 540]], icon: <Disc name="cloud" color="#2FA84F" />, label: "클라우드" },
          { pts: [[590, 540], [900, 540], [900, 850], [1350, 850]], icon: <Disc name="truck" color="#E8521E" />, label: "자율주행" },
        ]} iconSize={160} />
    </Flat>
  ),
  pillArrow: ({ p }: DP) => (<Flat c="#F1EEE6"><PillArrowPill p={p} at={8} a="밀가루 수입" b="분식 장려" /><div style={{ position: "absolute", left: 0, width: W, top: 250, textAlign: "center", fontFamily: "NeoHv", fontSize: 64, color: "#333" }}>1960년대 식량 정책</div></Flat>),
  collision: ({ p }: DP) => (<Flat c="#F3F1EC"><PillCollision p={p} at={10} left="중국 짜장" right="한국 입맛" big="짜장면" /></Flat>),
  neon: ({ p }: DP) => (
    <Flat c="#0E1016">
      <NeonTiles p={p} at={8} letters={["짜", "장", "면", "!"]} />
      <div style={{ position: "absolute", left: 0, width: W, top: 470, textAlign: "center", fontFamily: "NeoHv", fontSize: 110, color: "#fff" }}>대한민국 대표 외식</div>
    </Flat>
  ),
  compare: ({ p }: DP) => (<Flat c="#2B2B2B"><Photo img="real/jjajang.jpg" dim={0.35} /><CompareAB p={p} at={8} a="짬뽕" b="짜장면" /><div style={{ position: "absolute", left: 0, width: W, top: 720, textAlign: "center", fontFamily: "NeoEb", fontSize: 48, color: "#fff" }}>배달 주문 수 (2024)</div></Flat>),
  titleBox: ({ p }: DP) => (<Flat c="#222"><Photo img="real/chinatown.jpg" dim={0.8} /><TitleBox p={{ subDelay: 38, ...p }} at={8} title="제3장 · 인천 차이나타운" sub={["1883년 개항과 함께 청국 조계가 설치되고", "산둥 출신 화교들이 모여 살기 시작했다"]} /></Flat>),
  scrim: ({ p }: DP) => (
    <Flat c="#222">
      <Photo img="real/port.jpg" />
      <ScrimTypewriter p={p} at={6} title="인천항, 1883" sub="개항 이후 인천은 청·일·서양 상인이 몰려드는 국제 무역항이 되었다." badges={[{ label: "청", color: "#D62828" }, { label: "일본", color: "#2FA84F" }, { label: "서양", color: "#1F6FE0" }]} />
    </Flat>
  ),
  whiteboard: ({ p }: DP) => (
    <Flat c="#C9CFC7">
      <Whiteboard x={260} y={110} w={1400} h={800} p={{ titleDelay: 8, ...p }} at={4} title="짜장면 성공 요인" lines={[{ text: "① 싼 가격 — 서민 음식", at: 40 }, { text: "② 빠른 조리 — 배달 가능", at: 66 }, { text: "③ 달콤한 춘장(春醬)", at: 92 }]} />
    </Flat>
  ),
  redBox: ({ p }: DP) => (<Flat c="#222"><Photo img="real/ghc_now.jpg" dim={0.9} /><RedBoxBlink at={6} rect={[1170, 400, 400, 560]} pills={["공화춘 건물", "1908년 개업", "현 짜장면박물관"]} pillsX={560} pillsY={470} pillGap={130} p={{ pillsDelay: 58, ...p }} /></Flat>),
  handCircle: ({ p }: DP) => (
    <Flat c="#F4F1EA">
      <div style={{ position: "absolute", left: 360, top: 220, width: 1200, height: 640, overflow: "hidden", borderRadius: 12, boxShadow: "0 10px 30px rgba(0,0,0,0.3)" }}><Img src={src("real/museum.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover" }} /></div>
      <HandDrawnCircle p={p} at={14} cx={960} cy={540} rx={240} ry={170} />
      <HandDrawnCircle at={44} cx={560} cy={380} rx={140} ry={100} seed={3} color="#1F6FE0" p={p && { ...p, color: "#1F6FE0" }} />
    </Flat>
  ),
  browserGraph: ({ p }: DP) => (<><CodeRainBg /><BrowserMockup p={p} at={4} mode="graph" url="www.hyperlink.net" tab="하이퍼링크" /></>),
  browserShop: ({ p }: DP) => (<Flat c="#E9EEF3"><BrowserMockup p={p} at={4} mode="shop" url="shop.semo.kr" tab="세모마켓" shop={[{ img: "real/jjajang.jpg", name: "옛날 짜장면 2인분", price: "7,900원" }, { img: "real/chunjang.jpg", name: "사자표 춘장 300g", price: "3,200원" }]} /></Flat>),
  shotGrid: ({ p }: DP) => (<Flat c="#333"><Photo img="img/s03_restaurant.jpg" /><ScreenshotGrid p={p} at={4} cw={330} ch={225} items={IMGS.map((img, i) => ({ img, label: ["1905", "1930", "1948", "1960", "1970", "1985", "2006", "2024"][i] }))} /></Flat>),
  carousel: ({ p }: DP) => (<Flat c="#15181D"><ScreenshotCarousel p={p} at={0} items={IMGS.map((img, i) => ({ img, label: ["차이나타운", "춘장", "공화춘 폐업", "공화춘 현재", "짜장면", "박물관", "인천항", "자장몐"][i] }))} /></Flat>),
  versions: ({ p }: DP) => (<Flat c="#20242C"><VersionStack p={p} at={4} hold={32} versions={[1965, 1978, 1992, 2008, 2024].map((y, i) => ({ year: String(y), content: <Logo v={i} /> }))} /></Flat>),
  iconGrid: ({ p }: DP) => (
    <Flat c="#EDEAE3">
      <IconRowGrid p={p} at={6} items={(["bowl", "truck", "money", "phone", "user", "heart", "star", "chart", "globe"] as IconName[]).map((n, i) => ({ icon: <Icon name={n} color={["#E8521E", "#1F6FE0", "#2FA84F", "#D62828", "#7A4DD8"][i % 5]} />, label: ["음식", "배달", "가격", "주문", "손님", "추억", "맛집", "매출", "세계화"][i] }))} rowYs={[300, 700]} />
    </Flat>
  ),
  tree: ({ p }: DP) => (<Flat c="#2F4858"><TreeDroplines p={p} at={6} root="산둥 화교" kids={[{ text: "요릿집" }, { text: "호떡집", color: "#2FA84F" }, { text: "잡화상", color: "#E8521E" }]} /></Flat>),
  shields: ({ p }: DP) => (<Flat c="#0B1A26"><ShieldWings p={p} at={8} text="식품 안전 인증" shields={[{ label: "원산지", icon: "globe" }, { label: "위생", icon: "heart" }, { label: "품질", icon: "star" }]} /></Flat>),
  mapPin: ({ p }: DP) => (
    <Flat c="#9CC7DD">
      <svg width={W} height={H} style={{ position: "absolute" }}><path d="M420,80 L900,120 L1100,300 L1250,260 L1500,420 L1440,700 L1200,900 L900,980 L620,860 L520,620 L380,420 Z" fill="#EAD9B6" stroke="#CDB98F" strokeWidth={5} /></svg>
      <MapPin p={p} at={8} img="img/s03_woo.png" x={760} y={420} label="인천" />
      <MapPin p={p} at={24} img="img/s06_kid.png" x={1120} y={560} label="서울" />
      <MapPin p={p} at={40} img="real/ghc_now.jpg" x={940} y={820} label="군산" />
    </Flat>
  ),
  medallion: ({ p }: DP) => (
    <Flat c="#1E2A36">
      <MedallionTree p={p} at={6} stagger={22} center={[960, 800]} conclusion="모두 짜장면으로" items={[
        { img: "real/zhajiang.jpg", name: "자장몐", color: "#D62828", x: 360, y: 250 },
        { img: "real/chunjang.jpg", name: "춘장", color: "#E8A21E", x: 760, y: 250 },
        { img: "real/chinatown.jpg", name: "화교", color: "#2FA84F", x: 1160, y: 250 },
        { img: "img/s06_crowd.jpg", name: "서민", color: "#1F6FE0", x: 1560, y: 250 },
      ]} />
    </Flat>
  ),
  puzzle: ({ p }: DP) => (<Flat c="#F1EEE6"><PuzzleJoin p={p} at={8} left="춘장" right="면" /><div style={{ position: "absolute", left: 0, width: W, top: 820, textAlign: "center", fontFamily: "NeoHv", fontSize: 60, color: "#333" }}>완벽한 조합</div></Flat>),
};

export const DEMOS: Demo[] = [
  { name: "CalloutConnector", dur: 120, C: D.connector, schema: CalloutConnectorParams },
  { name: "DottedPathDraw", dur: 100, C: D.dotted, schema: DottedPathDrawParams },
  { name: "CircuitBranch", dur: 70, C: D.circuit, schema: CircuitBranchParams },
  { name: "PillArrowPill", dur: 80, C: D.pillArrow, schema: PillArrowPillParams },
  { name: "PillCollision", dur: 80, C: D.collision, schema: PillCollisionParams },
  { name: "NeonTiles", dur: 100, C: D.neon, schema: NeonTilesParams },
  { name: "CompareAB", dur: 80, C: D.compare, schema: CompareABParams },
  { name: "TitleBox", dur: 100, C: D.titleBox, schema: TitleBoxParams },
  { name: "ScrimTypewriter", dur: 150, C: D.scrim, schema: ScrimTypewriterParams },
  { name: "Whiteboard", dur: 140, C: D.whiteboard, schema: WhiteboardParams },
  { name: "RedBoxBlink", dur: 110, C: D.redBox, schema: RedBoxBlinkParams },
  { name: "HandDrawnCircle", dur: 80, C: D.handCircle, schema: HandDrawnCircleParams },
  { name: "BrowserMockup · graph", dur: 150, C: D.browserGraph, schema: BrowserMockupParams },
  { name: "BrowserMockup · shop", dur: 150, C: D.browserShop, schema: BrowserMockupParams },
  { name: "ScreenshotGrid", dur: 150, C: D.shotGrid, schema: ScreenshotGridParams },
  { name: "ScreenshotCarousel", dur: 120, C: D.carousel, schema: ScreenshotCarouselParams },
  { name: "VersionStack", dur: 240, C: D.versions, schema: VersionStackParams },
  { name: "IconRowGrid", dur: 130, C: D.iconGrid, schema: IconRowGridParams },
  { name: "TreeDroplines", dur: 80, C: D.tree, schema: TreeDroplinesParams },
  { name: "ShieldWings", dur: 70, C: D.shields, schema: ShieldWingsParams },
  { name: "MapPin", dur: 80, C: D.mapPin, schema: MapPinParams },
  { name: "MedallionTree", dur: 190, C: D.medallion, schema: MedallionTreeParams },
  { name: "PuzzleJoin", dur: 80, C: D.puzzle, schema: PuzzleJoinParams },
];
export const GALLERY_DUR = Math.max(30, DEMOS.reduce((a, d) => a + d.dur, 0));
export const Gallery = runGallery(DEMOS);
