import React from "react";
import { AbsoluteFill, Img, useCurrentFrame } from "remotion";
import { runGallery, type Demo } from "./runner";
import { prop, propH } from "../lib/kit";
import { Cover, GLOW, Starburst, src } from "../fx";
import {
  Mascot, RivalEnter, LogoFaceMask, AngerMark, SurpriseLines, CloudBubbles, DizzySwirl, FallingBlocks,
  SmokeSwap, Teleport, HopArc, RivalBeam, ElectricCrack, EyeBeam, PhoneRing, HiddenSilhouette,
  FingerFromCorner, CrowdRise, WalkPath, StairPromotion, SlideInReframe, PoseSwap, pingPong,
  MascotParams, RivalEnterParams, LogoFaceMaskParams, AngerMarkParams, CloudBubblesParams, DizzySwirlParams,
  SmokeSwapParams, TeleportParams, HopArcParams, RivalBeamParams, EyeBeamParams, PhoneRingParams,
  HiddenSilhouetteParams, FingerFromCornerParams, CrowdRiseParams, WalkPathParams, StairPromotionParams,
  SlideInReframeParams, PoseSwapParams,
} from "../lib/characters";

type PP = { p?: Record<string, any> };

// 캐릭터 에셋 실측(원본 px): woo 738×1148 얼굴중심(282,238)·얼굴폭 300 / kid 709×1010 얼굴중심(360,390)·폭 540 (피부색 픽셀 실측)
const WOO = { img: "img/s03_woo.png", ar: 1148 / 738, face: [282 / 738, 238 / 1148], fw: 300 / 738 };
const KID = { img: "img/s06_kid.png", ar: 1010 / 709, face: [360 / 709, 390 / 1010], fw: 540 / 709 };

const Floor: React.FC<{ c?: string; y?: number }> = ({ c = "#EDE5D6", y = 860 }) => (
  <AbsoluteFill style={{ background: c }}>
    <div style={{ position: "absolute", left: 0, right: 0, top: y, bottom: 0, background: "rgba(0,0,0,0.06)" }} />
  </AbsoluteFill>
);
/** 발밑 기준 캐릭터(선택적 까딱) */
const Char: React.FC<{ c: typeof WOO; x: number; y: number; w: number; bob?: boolean; flip?: boolean; phase?: number }> = ({ c, x, y, w, bob = true, flip, phase = 0 }) => {
  const f = useCurrentFrame();
  const h = w * c.ar, sy = bob ? pingPong(f, 10, 1, 1.01, phase) : 1;
  return <Img src={src(c.img)} style={{ position: "absolute", left: x - w / 2, top: y - h, width: w, height: h, transformOrigin: "50% 100%", transform: `scale(${flip ? -1 : 1},${sy})`, filter: GLOW }} />;
};
const head = (c: typeof WOO, x: number, y: number, w: number): [number, number] => [x - w / 2 + c.face[0] * w, y - w * c.ar + c.face[1] * w * c.ar];

const LogoCard: React.FC = () => (
  <div style={{ position: "absolute", inset: 0, borderRadius: 26, background: "linear-gradient(135deg,#1E88E5,#1565C0)", border: "8px solid #fff", boxShadow: "0 6px 12px rgba(0,0,0,0.3)", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "Jalnan", fontSize: 110, color: "#fff" }}>AI</div>
);

const D1: React.FC<PP> = ({ p }) => (
  <>
    <Floor />
    <Mascot x={620} y={880} w={420} h={352} img="img/s05_chunjang.png" at={0} l="idle" r="idle" seed="a" handInset={0.07}
      poses={[{ at: 20, r: "wave" }, { at: 45, l: "point", r: "idle" }, { at: 70, l: "surprised", r: "surprised" }]} p={p} />
    <Mascot x={1300} y={880} w={340} h={340} at={6} l="wave" r="point" seed="b"><LogoCard /></Mascot>
  </>
);
const D2: React.FC<PP> = ({ p }) => (
  <>
    <Floor />
    <RivalEnter at={20} a={{ x: 960, y: 880, w: 380, h: 318, img: "img/s05_chunjang.png", r: "wave", seed: "ra" }}
      b={{ x: 960, y: 880, w: 400, h: 379, img: "img/s05_bowl.png", l: "point", r: "idle", seed: "rb" }} p={p} />
  </>
);
const D3: React.FC<PP> = ({ p }) => {
  const x = 960, y = 1000, w = 400, [hx, hy] = head(WOO, x, y, w);
  return (
    <>
      <Cover img="layers_vec/s02_dock__bg.jpg" />
      <Char c={WOO} x={x} y={y} w={w} />
      <LogoFaceMask cx={hx} cy={hy} faceW={WOO.fw * w} ground={y} at={10} text="淸" color="#C62828" p={p} />
    </>
  );
};
const D4: React.FC<PP> = ({ p }) => {
  const [ax, ay] = head(WOO, 620, 980, 360), [bx, by] = head(KID, 1320, 1000, 380);
  return (
    <>
      <Floor c="#E7EEF3" />
      <Char c={WOO} x={620} y={980} w={360} />
      <AngerMark x={ax + 95} y={ay - 95} at={8} p={p} />
      <Char c={KID} x={1320} y={1000} w={380} phase={4} />
      <SurpriseLines x={bx} y={by - 40} at={20} side="both" gap={170} n={3} len={55} />
    </>
  );
};
const D5: React.FC<PP> = ({ p }) => {
  const x = 960, y = 1040, w = 330, [hx, hy] = head(WOO, x, y, w);
  return (
    <>
      <Floor c="#F1E9DA" />
      <Char c={WOO} x={x} y={y} w={w} />
      <CloudBubbles head={[hx, hy - 110]} items={[{ text: "짜장?", at: 5 }, { text: "山東", at: 30 }, { text: "돈!", at: 55 }]} p={p} />
    </>
  );
};
const D6: React.FC<PP> = ({ p }) => {
  const x = 960, y = 980, w = 360, [hx, hy] = head(WOO, x, y, w);
  return (
    <>
      <Floor c="#DDE3E8" />
      <FallingBlocks x={x} groundY={y - 10} at={10} width={620} n={26} />
      <Char c={WOO} x={x} y={y} w={w} />
      <DizzySwirl x={hx} y={hy - 170} at={4} r={110} p={p} />
    </>
  );
};
const D7: React.FC<PP> = ({ p }) => (
  <>
    <Floor c="#EDE5D6" />
    <SmokeSwap x={960} y={650} w={440} h={640} at={25}
      a={<Char c={WOO} x={960} y={960} w={360} />} b={<Char c={KID} x={960} y={960} w={440} />} p={p} />
  </>
);
const D8: React.FC<PP> = ({ p }) => (
  <>
    <Floor c="#E9E2F0" />
    <Teleport x={600} y={690} w={380} h={540} at={8} mode="in" p={p}><Char c={KID} x={600} y={960} w={380} /></Teleport>
    <Teleport x={1320} y={700} w={360} h={560} at={32} mode="out" p={p}><Char c={WOO} x={1320} y={980} w={360} /></Teleport>
  </>
);
const D9: React.FC<PP> = ({ p }) => (
  <>
    <Floor c="#8FC3A3" y={900} />
    <HopArc pts={[[300, 920], [760, 900], [1180, 920], [1620, 900]]} at={8} w={300} h={284} img="img/s05_bowl.png" dur={12} gap={8} height={220} glow p={p} />
  </>
);
const D10: React.FC<PP> = ({ p }) => (
  <>
    <AbsoluteFill style={{ background: "#1d2433" }} />
    <Mascot x={380} y={900} w={380} h={318} img="img/s05_chunjang.png" r="point" seed="p" />
    <Mascot x={1540} y={900} w={400} h={379} img="img/s05_bowl.png" l="surprised" r="surprised" seed="q" />
    <RivalBeam from={[620, 690]} to={[1290, 690]} at={10} p={p} />
    <ElectricCrack x={1540} y={690} r={220} at={14} />
  </>
);
const D11: React.FC<PP> = ({ p }) => {
  const [ax, ay] = head(WOO, 480, 1100, 420), [bx, by] = head(KID, 1460, 1120, 440);
  return (
    <>
      <AbsoluteFill style={{ background: "#27496d" }} />
      <EyeBeam a={[ax + 20, ay - 5]} b={[bx - 60, by - 10]} at={0} speedLines p={p} />
      <EyeBeam a={[ax + 20, ay - 5]} b={[bx - 60, by - 10]} at={0} amp={10} wave={60} color="#6FD0FF" width={6} strands={1} flow={-1.1} />
      <Char c={WOO} x={480} y={1100} w={420} />
      <Char c={KID} x={1460} y={1120} w={440} flip />
    </>
  );
};
const D12: React.FC<PP> = ({ p }) => (
  <>
    <Floor c="#F5EFE4" />
    <PhoneRing x={960} y={560} at={5} size={300} p={p} />
  </>
);
const D13: React.FC<PP> = ({ p }) => (
  <>
    <Cover img="layers_vec/s02_dock__bg.jpg" />
    <HiddenSilhouette img="img/s06_kid.png" x={960} y={1010} w={360} h={513} at={10} dur={70} dx={230} p={p}>
      <Char c={WOO} x={960} y={1020} w={380} />
    </HiddenSilhouette>
  </>
);
const D14: React.FC<PP> = ({ p }) => (
  <>
    <Floor c="#EDE5D6" />
    <Img src={src("img/s05_chunjang.png")} style={{ position: "absolute", left: 560, top: 200, width: 700, filter: GLOW }} />
    <FingerFromCorner tip={[930, 500]} at={8} p={p} />
  </>
);
const D15: React.FC<PP> = ({ p }) => (
  <>
    <Cover img="layers_vec/s06_crowd__bg.jpg" />
    <CrowdRise at={10} n={11} p={p} />
  </>
);
// 세모지 그림체 벽돌 건물(kit building_brick) — 캐릭터를 가리는 occluder
const Building: React.FC<{ x: number; y: number }> = ({ x, y }) => (
  <Img src={prop("building_brick")} style={{ position: "absolute", left: x - 20, top: y - propH("building_brick", 300), width: 300, height: propH("building_brick", 300) }} />
);
const D16: React.FC<PP> = ({ p }) => (
  <>
    <Floor c="#F3EEE4" y={1000} />
    <WalkPath y={860} x0={200} at={6} w={170} h={264} img={WOO.img} startLabel="1890 출생"
      stops={[{ x: 560, label: "1904", sub: "인천 도착" }, { x: 1320, label: "1912", sub: "공화춘 개업" }, { x: 1680, label: "1948", sub: "짜장면" }]}
      occluders={<Building x={830} y={880} />} p={p} />
  </>
);
const D17: React.FC<PP> = ({ p }) => (
  <>
    <Floor c="#E4ECF2" y={940} />
    <StairPromotion x0={300} y0={960} at={8} w={150} h={214} img={KID.img}
      steps={[{ flag: "1995", sub: "입사" }, { flag: "2001", sub: "대리" }, { flag: "2006", sub: "과장" }, { flag: "2012", sub: "부장" }, { flag: "2020", sub: "사장" }]} p={p} />
  </>
);
const D18: React.FC<PP> = ({ p }) => (
  <SlideInReframe at={12} p={p} char={<Char c={WOO} x={1300} y={1100} w={420} />}>
    <Cover img="layers_vec/s02_dock__bg.jpg" style={{ left: -90, top: -90, width: 1920 + 180, height: 1080 + 180 }} />
  </SlideInReframe>
);
const D19: React.FC<PP> = ({ p }) => (
  <>
    <Floor c="#EFE3D0" />
    <PoseSwap x={960} y={1000} w={400} h={622} poses={[
      { at: 0, img: "img/s03_woo_back.png" },
      { at: 20, img: "img/s03_woo.png", effect: (a) => <Starburst text="짠!" x={1300} y={300} at={a} w={320} h={220} /> },
      { at: 50, img: "img/s03_woo_back.png" },
    ]} p={p} />
  </>
);

export const DEMOS: Demo[] = [
  { name: "Mascot (손 포즈 idle→wave→point→surprised)", dur: 95, C: D1, schema: MascotParams },
  { name: "RivalEnter (낙하 + 밀려남)", dur: 60, C: D2, schema: RivalEnterParams },
  { name: "LogoFaceMask (까딱 추종)", dur: 50, C: D3, schema: LogoFaceMaskParams },
  { name: "AngerMark + SurpriseLines", dur: 55, C: D4, schema: AngerMarkParams },
  { name: "CloudBubbles (좌우 교대)", dur: 80, C: D5, schema: CloudBubblesParams },
  { name: "DizzySwirl + FallingBlocks", dur: 90, C: D6, schema: DizzySwirlParams },
  { name: "SmokeSwap", dur: 60, C: D7, schema: SmokeSwapParams },
  { name: "Teleport in / out", dur: 64, C: D8, schema: TeleportParams },
  { name: "HopArc (연속 점프)", dur: 80, C: D9, schema: HopArcParams },
  { name: "RivalBeam + ElectricCrack", dur: 55, C: D10, schema: RivalBeamParams },
  { name: "EyeBeam + SpeedLines", dur: 50, C: D11, schema: EyeBeamParams },
  { name: "PhoneRing", dur: 50, C: D12, schema: PhoneRingParams },
  { name: "HiddenSilhouette", dur: 90, C: D13, schema: HiddenSilhouetteParams },
  { name: "FingerFromCorner", dur: 45, C: D14, schema: FingerFromCornerParams },
  { name: "CrowdRise", dur: 60, C: D15, schema: CrowdRiseParams },
  { name: "WalkPath (건물 뒤 통과)", dur: 290, C: D16, schema: WalkPathParams },
  { name: "StairPromotion", dur: 95, C: D17, schema: StairPromotionParams },
  { name: "SlideInReframe", dur: 50, C: D18, schema: SlideInReframeParams },
  { name: "PoseSwap (+효과 1f 후)", dur: 75, C: D19, schema: PoseSwapParams },
];
export const GALLERY_DUR = Math.max(30, DEMOS.reduce((a, d) => a + d.dur, 0));
export const Gallery = runGallery(DEMOS);
