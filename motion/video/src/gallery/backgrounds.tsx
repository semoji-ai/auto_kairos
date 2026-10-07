import React from "react";
import { AbsoluteFill, Img } from "remotion";
import { runGallery, type Demo } from "./runner";
import { src, GLOW, photoPop } from "../fx";
import {
  MatrixRain, MoneyRain, CodeScroll, BokehDrift, SpotlightCone, CrowdBokeh, CloudDrift, BlurFillPhoto,
  Pillarbox, CaptureScroll, PixelateAvatar, LightningFlash, CartoonZaps, FlagWave, InstaCard, TonalWordmark, OutlineText,
  MatrixRainParams, MoneyRainParams, CodeScrollParams, BokehDriftParams, SpotlightConeParams, CrowdBokehParams, CloudDriftParams,
  BlurFillPhotoParams, PillarboxParams, CaptureScrollParams, PixelateAvatarParams, LightningFlashParams, FlagWaveParams,
  InstaCardParams, TonalWordmarkParams,
} from "../lib/backgrounds";
import { useCurrentFrame } from "remotion";
import { z } from "zod";

/** 데모가 개별 prop 으로 바꿔 쓴 값을 스키마 기본값으로 반영 → Param-<id> 슬라이더가 데모 모습 그대로에서 출발한다(범위·라벨 유지) */
const redef = <S extends z.ZodObject<any>>(schema: S, over: Partial<z.infer<S>>): S =>
  schema.extend(Object.fromEntries(Object.entries(over).map(([k, v]) => {
    const t: any = schema.shape[k];
    return [k, t.unwrap().default(v).describe(t.description)];
  }))) as unknown as S;

// 중앙 제목 칩(데모용)
const Chip: React.FC<{ text: string; y?: number; dark?: boolean }> = ({ text, y = 440, dark = true }) => (
  <div style={{ position: "absolute", left: 0, right: 0, top: y, display: "flex", justifyContent: "center" }}>
    <div style={{ background: dark ? "rgba(0,0,0,0.65)" : "rgba(255,255,255,0.9)", color: dark ? "#fff" : "#111", fontFamily: "NeoHv", fontSize: 72, padding: "18px 48px", borderRadius: 18 }}>{text}</div>
  </div>
);
const PopImg: React.FC<{ img: string; x: number; y: number; w: number; at?: number; glow?: boolean }> = ({ img, x, y, w, at = 0, glow = true }) => {
  const f = useCurrentFrame();
  if (f < at) return null;
  const { s } = photoPop(f, at);
  return <Img src={src(img)} style={{ position: "absolute", left: x, top: y, width: w, transform: `scale(${s})`, transformOrigin: "50% 100%", filter: glow ? GLOW : undefined }} />;
};

const CAPTURE = [
  ["real/jjajang.jpg", "짜장면 한 그릇에 담긴 130년의 역사"], ["real/chinatown.jpg", "인천 차이나타운은 어떻게 생겨났을까?"],
  ["real/chunjang.jpg", "춘장은 원래 검은색이 아니었다"], ["real/port.jpg", "제물포 개항, 모든 것의 시작"],
  ["img/s03_restaurant.jpg", "공화춘, 짜장면의 원조 논쟁"], ["real/museum.jpg", "짜장면 박물관에 가보았다"],
  ["real/zhajiang.jpg", "중국 작장면 vs 한국 짜장면"], ["img/s05_factory.jpg", "캐러멜 춘장 공장의 비밀"],
  ["real/ghc_now.jpg", "공화춘 건물은 지금 어떻게 됐을까"], ["img/s02_dock.jpg", "부두 노동자들의 한 끼"],
  ["img/s01_family.jpg", "화교 가족의 100년 이야기"], ["real/ghc_closed.jpg", "문을 닫은 원조 식당"],
  ["img/s06_crowd.jpg", "짜장면 데이는 왜 4월 14일?"], ["real/jjajang.jpg", "짜장면 가격 변천사 1960~2025"],
  ["real/port.jpg", "인천항 100년 타임랩스"], ["real/chinatown.jpg", "차이나타운 골목 투어"],
  ["img/s03_restaurant.jpg", "중식당 메뉴판의 역사"], ["real/zhajiang.jpg", "베이징 작장면 먹어보기"],
  ["img/s05_factory.jpg", "춘장 공장 견학기"], ["real/museum.jpg", "박물관 속 그 시절 배달통"],
].map(([img, title]) => ({ img, title }));

export const DEMOS: Demo[] = [
  { name: "MatrixRain (green)", dur: 90, C: ({ p }) => <MatrixRain p={p} />, schema: MatrixRainParams },
  { name: "MatrixRain (teal)", dur: 75, C: ({ p }) => <MatrixRain color="#2FD6C8" head="#E6FFFB" bg="#01080A" seed="mxt" p={p} />, schema: redef(MatrixRainParams, { color: "#2FD6C8", head: "#E6FFFB", bg: "#01080A" }) },
  { name: "MoneyRain", dur: 90, schema: MoneyRainParams, C: ({ p }) => (
    <AbsoluteFill style={{ background: "#F4E3B5" }}>
      <PopImg img="img/s05_bowl.png" x={660} y={300} w={600} />
      <MoneyRain p={p} />
    </AbsoluteFill>
  ) },
  { name: "CodeScroll", dur: 90, schema: CodeScrollParams, C: ({ p }) => <AbsoluteFill><CodeScroll p={p} /><Chip text="데이터로 본 짜장면" /></AbsoluteFill> },
  { name: "BokehDrift", dur: 90, schema: BokehDriftParams, C: ({ p }) => <AbsoluteFill><BokehDrift p={p} /><PopImg img="img/s06_kid.png" x={780} y={230} w={380} /></AbsoluteFill> },
  { name: "SpotlightCone", dur: 90, schema: SpotlightConeParams, C: ({ p }) => <SpotlightCone x={960} p={p}><PopImg img="img/s03_woo.png" x={780} y={330} w={360} glow={false} /></SpotlightCone> },
  { name: "SpotlightCone + fog", dur: 90, schema: redef(SpotlightConeParams, { fog: true, bg: "#0F1420" }), C: ({ p }) => <SpotlightCone x={960} fog id="spotfog" bg="#0F1420" color="220,235,255" p={p}><PopImg img="img/s06_kid.png" x={790} y={330} w={340} glow={false} /></SpotlightCone> },
  { name: "CrowdBokeh", dur: 90, schema: CrowdBokehParams, C: ({ p }) => <CrowdBokeh p={p} /> },
  { name: "CloudDrift", dur: 90, schema: CloudDriftParams, C: ({ p }) => <CloudDrift p={p}><PopImg img="img/s06_kid.png" x={790} y={380} w={340} /></CloudDrift> },
  { name: "BlurFillPhoto (4:3 + text)", dur: 120, schema: BlurFillPhotoParams, C: ({ p }) => <BlurFillPhoto img="real/museum.jpg" ar={4 / 3} text={["짜장면 박물관", "옛 공화춘 건물"]} textY={640} p={p} /> },
  { name: "BlurFillPhoto (small 3:2)", dur: 90, schema: redef(BlurFillPhotoParams, { widthPct: 0.6, pop: true }), C: ({ p }) => <BlurFillPhoto img="real/chunjang.jpg" ar={764 / 510} widthPct={0.6} pop p={p} /> },
  { name: "Pillarbox (archive)", dur: 90, schema: redef(PillarboxParams, { archive: true }), C: ({ p }) => <Pillarbox img="real/chinatown.jpg" archive source="출처: 인천광역시 시립박물관" p={p} /> },
  { name: "CaptureScroll", dur: 150, schema: CaptureScrollParams, C: ({ p }) => <CaptureScroll items={CAPTURE} avatar="img/s06_kid.png" p={p} /> },
  { name: "PixelateAvatar", dur: 90, schema: PixelateAvatarParams, C: ({ p }) => (
    <AbsoluteFill style={{ background: "#2B2F3A" }}>
      <PixelateAvatar img="img/s03_woo.png" x={660} y={440} at={3} label="익명 제보자 A" pos="50% 20%" id="pa1" p={p} />
      <PixelateAvatar img="real/jjajang.jpg" x={1260} y={440} at={10} split="left" verified={false} label="@jjajang_lover" id="pa2" />
    </AbsoluteFill>
  ) },
  { name: "LightningFlash + CartoonZaps", dur: 120, schema: redef(LightningFlashParams, { interval: 40 }), C: ({ p }) => (
    <LightningFlash interval={40} p={p}>
      <div style={{ position: "absolute", left: 610, top: 400, width: 700, height: 425, border: "8px solid #fff", boxShadow: "0 10px 30px rgba(0,0,0,0.6)", overflow: "hidden" }}>
        <Img src={src("real/ghc_closed.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      </div>
      <CartoonZaps rect={[610, 400, 700, 425]} period={9} />
    </LightningFlash>
  ) },
  { name: "FlagWave (kr → cn)", dur: 150, schema: FlagWaveParams, C: ({ p }) => (
    <AbsoluteFill style={{ background: "linear-gradient(#8FD0F2, #D6EEF9)" }}>
      <FlagWave flags={["kr", "cn"]} x={560} y={200} w={840} hold={60} xfade={15} p={p} />
    </AbsoluteFill>
  ) },
  { name: "InstaCard", dur: 90, schema: InstaCardParams, C: ({ p }) => (
    <InstaCard img="real/ghc_now.jpg" user="incheon_history" avatar="real/chinatown.jpg"
      caption={"1908년 문을 연 공화춘.\n지금은 짜장면 박물관이 되어\n그 시절 주방을 그대로 보여준다.\n#차이나타운 #짜장면박물관"}
      source="출처: Instagram @incheon_history" p={p} />
  ) },
  { name: "TonalWordmark", dur: 90, schema: redef(TonalWordmarkParams, { rows: 2 }), C: ({ p }) => (
    <TonalWordmark text="JJAJANG" rows={2} y={470} p={p}>
      <PopImg img="img/s05_bowl.png" x={710} y={220} w={500} />
      <OutlineText lines={["짜장면의 탄생"]} y={740} size={84} at={6} />
    </TonalWordmark>
  ) },
];
export const GALLERY_DUR = Math.max(30, DEMOS.reduce((a, d) => a + d.dur, 0));
export const Gallery = runGallery(DEMOS);
