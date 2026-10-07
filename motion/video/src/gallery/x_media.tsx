import React from "react";
import { AbsoluteFill, Img } from "remotion";
import { runGallery, Demo } from "./runner";
import { src, CloudBg } from "../fx";
import {
  RoughPhotoInset, RoughPhotoInsetParams, DarkVignettePortrait, DarkVignetteParams, PhotoIllustComposite, PhotoIllustParams,
  InstantMono, InstantMonoParams, FaceCoverBox, FaceCoverParams, TintFlash, TintFlashParams, CardSlideIn, CardSlideInParams,
  PhotoPanelSlideUp, PhotoPanelParams, WhiteStrokeCutout, WhiteStrokeCutoutParams, BoardingPassDrop, BoardingPassParams,
  XraySilhouette, XrayParams, ArchiveTitleBand, TitleBandParams, ArchiveNewsreel, NewsreelParams, NewspaperSlamStack, NewspaperStackParams,
  CardSwipeMontage, CardSwipeParams, DocZoomUnderline, DocZoomParams, BrushMaskQuote, BrushQuoteParams, ArchivalAdOnPaper, ArchivalAdParams,
  LanternSway, LanternSwayParams, SparkleDots, SparkleDotsParams, RepeatObjectWallpaper, WallpaperParams, SpiralTunnelBg, SpiralTunnelParams,
  FireBgLoop, FireBgParams, SpiralSuck, SpiralSuckParams, SkyGradientAscent, SkyAscentParams, SnowfallLoop, SnowfallParams, WaddleIn,
  LightningVersusSplit, LightningSplitParams, RippleRingsBg, RippleRingsParams, Pill, SweatDrop,
} from "../lib/x_media";

type PP = { p?: any };
const H0 = 1080;
const Char: React.FC<{ img: string; x: number; h: number; flip?: boolean; bottom?: number; filter?: string }> = ({ img, x, h, flip, bottom = 0, filter }) => (
  <Img src={src(img)} style={{ position: "absolute", left: x, bottom, height: h, transform: `translateX(-50%) scaleX(${flip ? -1 : 1})`, filter }} />
);
const Sub: React.FC<{ text: string }> = ({ text }) => (
  <div style={{ position: "absolute", left: 0, right: 0, top: 938, height: 82, background: "rgba(215,213,209,0.8)", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "NeoHv", fontSize: 40, color: "#111" }}>{text}</div>
);

const DOC_ROWS = [
  ["세모지", 643, true], ["가나다", 584], ["라마바", 539], ["사아자", 534, true], ["차카타", 526], ["파하", 516], ["알파", 509], ["베타", 495], ["감마", 492], ["델타", 491], ["엡실론", 488],
  ["업계 평균", 486, false, true], ["제타", 482], ["에타", 482], ["세타", 482], ["요타", 482], ["카파", 475], ["람다", 470], ["뮤", 465], ["뉴", 460], ["크시", 455], ["오미크론", 450],
].map(([label, value, hi, avg]) => ({ label: label as string, value: value as number, hi: !!hi, avg: !!avg }));

export const DEMOS: Demo[] = [
  { name: "RoughPhotoInset — 거친 흰 비네트 흑백 사진 슬라이드인", dur: 75, schema: RoughPhotoInsetParams, C: ({ p }: PP) => (
    <AbsoluteFill>
      <Img src={src("real/port.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover", filter: "grayscale(1) brightness(0.9)" }} />
      <RoughPhotoInset img="real/chinatown.jpg" x={120} y={380} w={640} h={440} at={6} p={p} />
    </AbsoluteFill>
  ) },
  { name: "DarkVignettePortrait — 원형 다크 비네트 인물", dur: 60, schema: DarkVignetteParams, C: ({ p }: PP) => (
    <DarkVignettePortrait at={6} p={p}>
      <AbsoluteFill style={{ background: "#5a5a5a" }}><Char img="img/s03_woo.png" x={960} h={1000} /></AbsoluteFill>
    </DarkVignettePortrait>
  ) },
  { name: "PhotoIllustComposite — 실사(붓 경계) + 일러스트 합성", dur: 75, schema: PhotoIllustParams, C: ({ p }: PP) => (
    <PhotoIllustComposite photo="real/ghc_now.jpg" illust="img/s06_kid.png" at={6} p={p} />
  ) },
  { name: "InstantMono — 과거 인물 컷 흑백화", dur: 60, schema: InstantMonoParams, C: ({ p }: PP) => (
    <AbsoluteFill style={{ background: "#7a1c1c" }}>
      <InstantMono at={20} style={{ right: 960 }} p={p}>
        <AbsoluteFill style={{ background: "#D9C7A6" }}><Char img="img/s03_woo.png" x={480} h={900} /></AbsoluteFill>
      </InstantMono>
      <div style={{ position: "absolute", left: 960, top: 0, width: 960, height: H0 }}><Char img="img/s06_kid.png" x={480} h={860} /></div>
    </AbsoluteFill>
  ) },
  { name: "FaceCoverBox — 얼굴 가림 박스 → 이름표", dur: 75, schema: FaceCoverParams, C: ({ p }: PP) => (
    <FaceCoverBox img="img/s06_crowd.jpg" at={8} focus={[560, 150, 760, 700]} boxes={[{ x: 250, y: 200, w: 210, h: 120, label: "장씨" }, { x: 1560, y: 200, w: 210, h: 120, label: "후씨" }]} p={p} />
  ) },
  { name: "TintFlash — 로고 월 컬러 틴트 플래시(1~2f)", dur: 75, schema: TintFlashParams, C: ({ p }: PP) => (
    <TintFlash at={6} p={p}>
      <RepeatObjectWallpaper p={{ bg: "#6B4A2E", size: 120, speckle: 0 }} icon={<div style={{ fontFamily: "MyeongjoEB", fontSize: 90, color: "#E2B866", whiteSpace: "nowrap" }}>八仙</div>} />
    </TintFlash>
  ) },
  { name: "CardSlideIn — 자격증 카드 회전 겹침 슬라이드인", dur: 75, schema: CardSlideInParams, C: ({ p }: PP) => (
    <AbsoluteFill style={{ background: "#B9C7C9" }}>
      <Char img="img/s06_kid.png" x={620} h={940} />
      <CardSlideIn at={6} x={1230} y={170} p={p} cards={[{ title: "한식 조리사 자격증", name: "정지선", img: "img/s06_kid.png" }, { title: "양식 조리사 자격증", name: "정지선", color: "#3C6E62", img: "img/s06_kid.png" }]} />
    </AbsoluteFill>
  ) },
  { name: "PhotoPanelSlideUp — 흑백 인물사진 패널 슬라이드업", dur: 80, schema: PhotoPanelParams, C: ({ p }: PP) => (
    <AbsoluteFill style={{ background: "linear-gradient(180deg,#F5A0A8,#E86D7C)" }}>
      <Char img="img/s03_woo.png" x={480} h={950} />
      <PhotoPanelSlideUp img="img/s03_restaurant.jpg" at={6} quote="딤섬의 여왕" title="정지선 셰프" p={p} />
    </AbsoluteFill>
  ) },
  { name: "WhiteStrokeCutout — 흰 윤곽선 흑백 컷아웃 + 로고·왕관", dur: 90, schema: WhiteStrokeCutoutParams, C: ({ p }: PP) => (
    <WhiteStrokeCutout img="img/s03_woo.png" bgImg="img/s06_crowd.jpg" logo="SEMOJI" title="최연소CEO" at={6} source="출처 : 세모지 아카이브" p={p} />
  ) },
  { name: "BoardingPassDrop — 탑승권 드롭 + 손이 집어감", dur: 110, schema: BoardingPassParams, C: ({ p }: PP) => (
    <BoardingPassDrop at={6} name="존 스컬리" flight="CBX 63" dest="중국" p={p} />
  ) },
  { name: "XraySilhouette — 엑스레이 투시 + 병변 펄스", dur: 150, schema: XrayParams, C: ({ p }: PP) => (
    <XraySilhouette at={6} p={p} reveal={<AbsoluteFill style={{ background: "#1c1c1c" }}><Char img="img/s03_woo.png" x={960} h={1500} bottom={-500} /></AbsoluteFill>} />
  ) },
  { name: "ArchiveTitleBand — 사료 사진 반투명 띠 제목 + 화살표 팝", dur: 75, schema: TitleBandParams, C: ({ p }: PP) => (
    <ArchiveTitleBand img="real/port.jpg" title="제2차 긴급통화조치" from="원(圓)" to="환(圜)" at={6} source="출처: 우리역사넷" p={p} />
  ) },
  { name: "ArchiveNewsreel — 방송 아카이브 필름 인서트(로고·출처 유지)", dur: 75, schema: NewsreelParams, C: ({ p }: PP) => (
    <AbsoluteFill><ArchiveNewsreel img="real/chinatown.jpg" logo="아카이브TV" source="출처 : 국가기록원" at={6} p={p} /><Sub text="경부고속도로 준공 당시의 기록 영상입니다." /></AbsoluteFill>
  ) },
  { name: "NewspaperSlamStack — 신문 스택 슬램", dur: 130, schema: NewspaperStackParams, C: ({ p }: PP) => (
    <NewspaperSlamStack at={6} p={p} papers={[{ headline: "회장 의장 복귀", x: 1000, y: 470, rot: 0 }, { headline: "회장의 본심은 무엇?", x: 700, y: 400, rot: -6 }, { headline: "회장의 이상한 행보", x: 1300, y: 560, rot: 5 }]} />
  ) },
  { name: "CardSwipeMontage — 카드 결제 반복 몽타주", dur: 170, schema: CardSwipeParams, C: ({ p }: PP) => (
    <CardSwipeMontage at={6} p={p} cards={[{ name: "가나프랜지", color: "#4CB944" }, { name: "다라건설", color: "#7B4DB8" }, { name: "마바화학", color: "#D9443A" }]} />
  ) },
  { name: "DocZoomUnderline — 원문 문서 휩 줌인 + 빨간 밑줄", dur: 130, schema: DocZoomParams, C: ({ p }: PP) => (
    <DocZoomUnderline at={10} p={p} title={["J.D PARK", "2022년 기술", "경험 지수 조사"]} docTitle="Overall Innovation Ranking" rows={DOC_ROWS} marks={[0, 3]} />
  ) },
  { name: "BrushMaskQuote — 붓 마스크 인물 + 손글씨 타자 인용", dur: 120, schema: BrushQuoteParams, C: ({ p }: PP) => (
    <BrushMaskQuote char="img/s03_woo.png" photo="img/s01_family.jpg" photoPos="60% 30%" at={6} quote={"“그는 늘 자기 몫을\n챙겨왔습니다.\n\n한 푼도 안 주겠다는\n그런 욕심이…”"} p={p} />
  ) },
  { name: "ArchivalAdOnPaper — 옛 광고 클립 종이 배경 + 해시태그", dur: 75, schema: ArchivalAdParams, C: ({ p }: PP) => (
    <ArchivalAdOnPaper img="real/jjajang.jpg" tags={["#세계최초", "#전자동식폴더폰"]} at={6} p={p} />
  ) },
  { name: "LanternSway — 등롱 ±3° 흔들림", dur: 120, schema: LanternSwayParams, C: ({ p }: PP) => (
    <AbsoluteFill><CloudBg /><LanternSway p={p} /><Char img="img/s06_kid.png" x={960} h={620} bottom={60} /></AbsoluteFill>
  ) },
  { name: "SparkleDots — 흰 반짝이 점 명멸", dur: 90, schema: SparkleDotsParams, C: ({ p }: PP) => (
    <AbsoluteFill style={{ background: "radial-gradient(circle at 50% 50%, #6B4A2E, #3A2618)" }}>
      <Img src={src("img/s05_bowl.png")} style={{ position: "absolute", left: 660, top: 260, width: 600 }} />
      <SparkleDots rect={[760, 380, 420, 220]} at={6} p={p} />
    </AbsoluteFill>
  ) },
  { name: "RepeatObjectWallpaper — 반복 사과 벽지 배경", dur: 60, schema: WallpaperParams, C: ({ p }: PP) => (
    <AbsoluteFill>
      <RepeatObjectWallpaper p={p} />
      <Char img="img/s03_woo.png" x={960} h={900} />
      <div style={{ position: "absolute", left: 960, top: 640, transform: "translateX(-50%)" }}><Pill text="사과 프로젝트" color="#F0A020" size={70} /></div>
    </AbsoluteFill>
  ) },
  { name: "SpiralTunnelBg — 최면 소용돌이(나선 터널) 배경 + 푯말", dur: 90, schema: SpiralTunnelParams, C: ({ p }: PP) => (
    <SpiralTunnelBg p={p}>
      <Char img="img/s03_woo.png" x={1000} h={1000} />
      <div style={{ position: "absolute", left: 870, top: 560, padding: "20px 34px", background: "#fff", transform: "rotate(-8deg)", fontFamily: "NeoHv", fontSize: 70, color: "#111", textAlign: "center", lineHeight: 1.1, boxShadow: "0 8px 16px rgba(0,0,0,0.35)" }}>판매<br />실적</div>
    </SpiralTunnelBg>
  ) },
  { name: "FireBgLoop — 분노 불꽃 배경 루프", dur: 60, schema: FireBgParams, C: ({ p }: PP) => (
    <FireBgLoop p={p}><Char img="img/s03_woo.png" x={660} h={900} /><Char img="img/s06_kid.png" x={1260} h={860} flip /></FireBgLoop>
  ) },
  { name: "SpiralSuck — 어두운 나선 전환 + 사물 소용돌이 흡입", dur: 110, schema: SpiralSuckParams, C: ({ p }: PP) => (
    <SpiralSuck at={6} p={p} from={<Img src={src("img/s03_restaurant.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />}>
      <Char img="img/s03_woo.png" x={1450} h={1000} />
      <SweatDrop x={1600} y={260} at={80} />
    </SpiralSuck>
  ) },
  { name: "SkyGradientAscent — 하늘 그라디언트로 고도 상승", dur: 90, schema: SkyAscentParams, C: ({ p }: PP) => <SkyGradientAscent at={6} p={p} /> },
  { name: "SnowfallLoop — 3층 눈 내림 + 뒤뚱 워크인", dur: 120, schema: SnowfallParams, C: ({ p }: PP) => (
    <SnowfallLoop p={p}>
      <Img src={src("img/s05_bowl.png")} style={{ position: "absolute", left: 1150, top: 470, width: 480 }} />
      <WaddleIn img="img/s06_kid.png" x={480} ground={990} h={620} at={8} bubble="안녕~" />
    </SnowfallLoop>
  ) },
  { name: "LightningVersusSplit — 번개 지그재그 대결 분할", dur: 90, schema: LightningSplitParams, C: ({ p }: PP) => (
    <LightningVersusSplit at={6} p={p} leftSay="이 정도는 참여할게~" rightSay="절대로 안 돼!!" leftChar={<Char img="img/s03_woo.png" x={420} h={900} />} rightChar={<Char img="img/s06_kid.png" x={1500} h={860} flip />} />
  ) },
  { name: "RippleRingsBg — 최면 동심 물결 배경(보라 2톤)", dur: 90, schema: RippleRingsParams, C: ({ p }: PP) => (
    <RippleRingsBg p={p}><Char img="img/s03_woo.png" x={960} h={950} /></RippleRingsBg>
  ) },
];
export const GALLERY_DUR = Math.max(30, DEMOS.reduce((a, d) => a + d.dur, 0));
export const Gallery = runGallery(DEMOS);
