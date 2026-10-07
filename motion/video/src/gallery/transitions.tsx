import React from "react";
import { AbsoluteFill, Img } from "remotion";
import type { z } from "zod";
import { runGallery, Demo } from "./runner";
import { src } from "../fx";
import {
  Shot, TheaterCurtain, CRTSwitch, SlatMosaic, NewspaperPullout, MagazineFlip, ArcWipeIris, IrisFeather,
  EnergySlash, WhiteDip, DipToBlack, OrangeFlare, MangaPanels, MANGA_DEFAULT_LAYOUT, SplitPanelWipe,
  VerticalPush, ParallaxPush, FireTransition, GrayscaleBeat, FocusPull, MagicMove,
  TheaterCurtainParams, CRTSwitchParams, SlatMosaicParams, NewspaperPulloutParams, MagazineFlipParams, ArcWipeIrisParams,
  IrisFeatherParams, EnergySlashParams, WhiteDipParams, DipToBlackParams, OrangeFlareParams, MangaPanelsParams,
  SplitPanelWipeParams, VerticalPushParams, ParallaxPushParams, FireTransitionParams, GrayscaleBeatParams, FocusPullParams, MagicMoveParams,
} from "../lib/transitions";

// 갤러리 섹션: 각 데모 = 씬 A(15f) → 전환 → 씬 B
const A0 = 15;
const S = (img: string, pos?: string) => <Shot img={img} pos={pos} />;
const FAM = S("img/s01_family.jpg"), DOCK = S("img/s02_dock.jpg"), REST = S("img/s03_restaurant.jpg"), FACT = S("img/s05_factory.jpg"), CROWD = S("img/s06_crowd.jpg");
const PORT = S("real/port.jpg"), CHINA = S("real/chinatown.jpg"), JJ = S("real/jjajang.jpg");
const Sticker = ({ img, x, y, w }: { img: string; x: number; y: number; w: number }) => (
  <Img src={src(img)} style={{ position: "absolute", left: x, top: y, width: w, filter: "drop-shadow(0 0 5px #fff) drop-shadow(0 0 5px #fff)" }} />
);
const Bullet = ({ items, color }: { items: string[]; color: string }) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 26 }}>
    {items.map((t) => <div key={t} style={{ background: "rgba(255,255,255,0.92)", borderRadius: 12, padding: "18px 28px 12px", fontFamily: "NeoHv", fontSize: 44, color }}>{t}</div>)}
  </div>
);

// 데모: C 는 { p } 로 변수를 받아 대표 전환 컴포넌트에 넘긴다(schema 가 있으면 도감 Param-<id> 슬라이더로 조절)
const D = <S extends z.ZodObject<any>>(name: string, dur: number, C: React.FC<{ p?: Partial<z.infer<S>> }>, schema?: S): Demo => ({ name, dur, C, schema });

export const DEMOS: Demo[] = [
  D("극장 커튼 TheaterCurtain", 95, ({ p }) => <TheaterCurtain at={A0} from={FAM} to={DOCK} p={p} />, TheaterCurtainParams),
  D("CRT 전원 CRTSwitch", 55, ({ p }) => <CRTSwitch at={A0} from={DOCK} to={REST} p={p} />, CRTSwitchParams),
  D("슬랫 모자이크 SlatMosaic", 80, ({ p }) => <SlatMosaic at={A0} from={REST} imgs={["img/s01_family.jpg", "img/s02_dock.jpg", "img/s05_factory.jpg", "img/s06_crowd.jpg"]} labels={["가족", "부두", "공장", "군중"]} p={p} />, SlatMosaicParams),
  D("신문 풀아웃 NewspaperPullout", 85, ({ p }) => <NewspaperPullout at={A0} from={CROWD} headline={"인천 부두에 몰려든 산둥 노동자들\n청요리 집이 늘어나다"} sub="1920년대 제물포 풍경" p={p} />, NewspaperPulloutParams),
  D("매거진 플립 MagazineFlip", 80, ({ p }) => (
    <MagazineFlip at={A0 - 5} from={CHINA} p={p} target={
      <AbsoluteFill style={{ background: "#FBF8F1" }}>
        <div style={{ position: "absolute", left: 44, top: 40, fontFamily: "NeoHv", fontSize: 58, color: "#C0392B" }}>짜장면의 탄생</div>
        <div style={{ position: "absolute", left: 44, right: 44, top: 130, height: 520, overflow: "hidden", borderRadius: 6 }}><Img src={src("real/jjajang.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover" }} /></div>
        <div style={{ position: "absolute", left: 44, right: 44, top: 680, fontFamily: "NeoEb", fontSize: 30, color: "#333", lineHeight: 1.5 }}>공화춘에서 시작된 한 그릇의 역사 — 춘장과 캐러멜의 만남</div>
      </AbsoluteFill>
    } />
  ), MagazineFlipParams),
  D("아크 와이프 아이리스 ArcWipeIris", 75, ({ p }) => <ArcWipeIris at={A0} from={FACT} center={[1300, 540]} p={{ radius: 440, ...p }} object={<Sticker img="img/s06_kid.png" x={1300 - 230} y={540 - 330} w={460} />} />, ArcWipeIrisParams),
  D("아이리스 페더 IrisFeather", 140, ({ p }) => <IrisFeather at={A0} from={DOCK} to={<Shot img="img/s06_crowd.jpg" style={{ filter: "brightness(0.75)" }} />} cx={960} cy={470} openAt={A0 + 50} p={p} />, IrisFeatherParams),
  D("에너지 슬래시 EnergySlash", 60, ({ p }) => <EnergySlash at={A0} from={REST} to={FACT} p={p} />, EnergySlashParams),
  D("화이트 딥 WhiteDip", 50, ({ p }) => <WhiteDip at={A0} from={FAM} to={PORT} p={p} />, WhiteDipParams),
  D("딥 투 블랙 DipToBlack", 40, ({ p }) => <DipToBlack at={A0} from={PORT} to={CROWD} p={p} />, DipToBlackParams),
  D("오렌지 플레어 OrangeFlare", 45, ({ p }) => <OrangeFlare at={A0} from={CROWD} to={CHINA} p={p} />, OrangeFlareParams),
  D("만화 패널 MangaPanels", 95, ({ p }) => (
    <MangaPanels at={A0} from={CHINA} p={p} panels={MANGA_DEFAULT_LAYOUT.map((l, i) => ({ ...l, img: ["img/s02_dock.jpg", "img/s06_crowd.jpg", "img/s01_family.jpg", "img/s05_factory.jpg", "img/s03_restaurant.jpg"][i] }))} />
  ), MangaPanelsParams),
  D("분할 패널 와이프 SplitPanelWipe", 135, ({ p }) => (
    <SplitPanelWipe at={A0} from={REST} p={p}
      left={{ title: "청요리", content: <Bullet color="#007BB0" items={["산둥식 면 요리", "고급 연회 음식", "화교 운영"]} /> }}
      right={{ title: "짜장면", content: <Bullet color="#257A2E" items={["한국식 개량", "캐러멜 춘장", "서민 음식"]} /> }} />
  ), SplitPanelWipeParams),
  D("버티컬 푸시 VerticalPush", 40, ({ p }) => <VerticalPush at={A0} from={PORT} to={JJ} p={p} />, VerticalPushParams),
  D("패럴랙스 푸시 ParallaxPush", 55, ({ p }) => (
    <ParallaxPush at={A0} p={p}
      fromLayers={[DOCK, <Sticker key="w" img="img/s03_woo.png" x={1150} y={120} w={620} />]}
      toLayers={[REST, <Sticker key="k" img="img/s06_kid.png" x={700} y={150} w={620} />]} />
  ), ParallaxPushParams),
  D("불꽃 전환 FireTransition", 60, ({ p }) => <FireTransition at={A0} from={FACT} to={CROWD} p={p} />, FireTransitionParams),
  D("그레이스케일 비트 GrayscaleBeat", 65, ({ p }) => <GrayscaleBeat at={A0} hold={20} p={p}>{CHINA}</GrayscaleBeat>, GrayscaleBeatParams),
  D("포커스 풀 FocusPull", 40, ({ p }) => <FocusPull at={A0} from={FAM} to={REST} p={p} />, FocusPullParams),
  D("매직 무브 MagicMove", 60, ({ p }) => (
    <MagicMove at={A0} from={REST} to={FACT} origin="1300px 560px" p={p}
      hero={<Sticker img="img/s05_bowl.png" x={1300 - 260} y={560 - 250} w={520} />} />
  ), MagicMoveParams),
];
export const GALLERY_DUR = Math.max(30, DEMOS.reduce((a, d) => a + d.dur, 0));
export const Gallery = runGallery(DEMOS);
