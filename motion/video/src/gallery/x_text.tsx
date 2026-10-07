import React from "react";
import { AbsoluteFill, Img, useCurrentFrame } from "remotion";
import { runGallery, Demo } from "./runner";
import { src } from "../fx";
import {
  CalligraphySlam, CalligraphySlamParams, GlowCloudText, GlowCloudTextParams, SpecBandLabel, SpecBandLabelParams,
  TitleStripFlyoff, TitleStripFlyoffParams, CornerCharTiles, CornerCharTilesParams, WordWallpaper, WordWallpaperParams,
  DefinitionReveal, DefinitionRevealParams, YearChipRoll, YearChipRollParams, SageDateCard, SageDateCardParams,
  BrushHeadline, BrushHeadlineParams, FactPillStack, FactPillStackParams, HeadlineBandSlam, HeadlineBandSlamParams,
  TextBehindCharacter, TextBehindCharacterParams, HanjaMedallion, HanjaMedallionParams, SloganBanner, SloganBannerParams,
  LegacySubtitleBand, LegacySubtitleBandParams, SourceChipDrawOn, SourceChipDrawOnParams, TabbedChapterHUD, TabbedChapterHUDParams,
  HUDDarkInvert, HUDDarkInvertParams, LegacyFormat, LegacyFormatParams, EraPalette, EraPaletteParams, LegacyLogoIntro, LegacyLogoIntroParams,
} from "../lib/x_text";

type PP = { p?: any };
const Bg: React.FC<{ img: string; filter?: string; pos?: string }> = ({ img, filter, pos }) => (
  <Img src={src(img)} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", objectPosition: pos, filter }} />
);
const Char: React.FC<{ img: string; x: number; y: number; w: number; flip?: boolean }> = ({ img, x, y, w, flip }) => (
  <Img src={src(img)} style={{ position: "absolute", left: x, top: y, width: w, transform: flip ? "scaleX(-1)" : undefined }} />
);
const HUDBar = () => <TabbedChapterHUD chapters={["짜장면의 탄생", "공화춘", "춘장의 비밀", "짜장면 데이"]} active={1} />;

const D01: React.FC<PP> = ({ p }) => (
  <AbsoluteFill>
    <Bg img="real/jjajang.jpg" filter="grayscale(0.2)" />
    <CalligraphySlam lines={["“짜장의 명가”", "공화춘 주방장"]} x={960} y={560} at={6} out={100} p={p} />
  </AbsoluteFill>
);
const D02: React.FC<PP> = ({ p }) => (
  <AbsoluteFill>
    <Bg img="real/port.jpg" filter="grayscale(1) contrast(1.1) brightness(0.8)" />
    <GlowCloudText lines={["1883년 제물포 개항", "모든 것의 시작"]} x={960} y={500} at={6} p={p} />
  </AbsoluteFill>
);
const D03: React.FC<PP> = ({ p }) => (
  <AbsoluteFill style={{ background: "#fff" }}>
    <Bg img="img/s05_factory.jpg" />
    <SpecBandLabel items={[{ lines: ["캐러멜 첨가", "검은 춘장"], at: 6 }, { lines: ["1948년", "대량 생산 시작"], at: 42 }]} x={1400} y={300} p={p} />
  </AbsoluteFill>
);
const D04: React.FC<PP> = ({ p }) => (
  <AbsoluteFill style={{ background: "#5B7F7C" }}>
    <TitleStripFlyoff img="img/s03_woo.png" imgPos="50% 8%" heading="구조조정 대상" name="우희광" title="공화춘 총주방장" newTitle="명예 고문" x={620} y={140} at={10} newAt={46} p={p} />
    <Char img="img/s03_woo_back.png" x={60} y={640} w={420} />
    <Char img="img/s03_woo_back.png" x={1340} y={640} w={420} flip />
  </AbsoluteFill>
);
const D05: React.FC<PP> = ({ p }) => (
  <AbsoluteFill style={{ background: "radial-gradient(circle at 50% 55%, #E03A8C 0%, #6B1C7A 45%, #22103A 100%)" }}>
    <Char img="img/s03_woo.png" x={700} y={180} w={540} />
    <CornerCharTiles chars={["비", "싼", "가", "격"]} at={6} p={p} />
  </AbsoluteFill>
);
const D06: React.FC<PP> = ({ p }) => <WordWallpaper word="PROJECT" at={6} compressAt={80} p={p} />;
const D07: React.FC<PP> = ({ p }) => (
  <DefinitionReveal title="춘장 春醬" lines={["콩을 **발효**시켜 만든", "중국식 **된장**으로", "짜장면 맛의 **핵심 재료**"]} at={6} p={p} />
);
const D08: React.FC<PP> = ({ p }) => (
  <YearChipRoll startYear={1948} p={p} segs={[
    { year: 1948, at: 6, items: [{ img: "img/s05_chunjang.png", label: "춘장", color: "#C9C27A" }] },
    { year: 1960, at: 40, items: [{ img: "img/s05_chunjang.png", label: "춘장", color: "#C9C27A" }, { img: "img/s05_bowl.png", label: "짜장면", color: "#B8D98A" }] },
    { year: 1974, at: 76, items: [{ img: "img/s05_bowl.png", label: "간짜장", color: "#C9B8E0" }, { img: "img/s05_bowl.png", label: "쟁반짜장", color: "#B8D98A" }, { img: "img/s05_chunjang.png", label: "춘장", color: "#C9C27A" }] },
  ]} />
);
const D09: React.FC<PP> = ({ p }) => (
  <AbsoluteFill>
    <Bg img="img/s02_dock.jpg" filter="grayscale(1)" />
    <SageDateCard text="1905년 4월" at={6} p={p} />
  </AbsoluteFill>
);
const D10: React.FC<PP> = ({ p }) => (
  <BrushHeadline text="화교 제한령 공포!" at={6} p={p}><Bg img="img/s01_family.jpg" /></BrushHeadline>
);
const D11: React.FC<PP> = ({ p }) => (
  <AbsoluteFill>
    <Bg img="real/chinatown.jpg" />
    <FactPillStack p={p} items={[{ text: "하루 판매량 600만 그릇", at: 6 }, { text: "전국 중식당 2만 4천 곳", at: 30 }, { text: "연간 매출 3조 원", at: 54 }, { text: "짜장면 가격 평균 7,000원", at: 78 }]} />
  </AbsoluteFill>
);
const D12: React.FC<PP> = ({ p }) => (
  <HeadlineBandSlam text="춘장 가격 폭락!" at={8} p={p}><Bg img="img/s05_factory.jpg" /></HeadlineBandSlam>
);
const D13: React.FC<PP> = ({ p }) => (
  <AbsoluteFill style={{ background: "#C2CCC3" }}>
    <TextBehindCharacter text="20억" img="img/s03_woo.png" at={6} fireAt={60} textY={360} charTop={300} charW={540} p={p} />
  </AbsoluteFill>
);
const D14: React.FC<PP> = ({ p }) => (
  <HanjaMedallion at={6} p={p} ribbon={{ text: "봄 춘 · 된장 장", x: 960, y: 250, at: 10 }}
    items={[{ hanja: "春", reading: ["봄", "춘"], x: 700, y: 580, at: 10 }, { hanja: "醬", reading: ["장", "장"], x: 1220, y: 580, at: 60 }]}>
    <Bg img="img/s03_restaurant.jpg" />
  </HanjaMedallion>
);
const D15: React.FC<PP> = ({ p }) => (
  <AbsoluteFill style={{ background: "#C2CCC3" }}>
    <SloganBanner lines={["짜장면 한 그릇으로", "하나 되자"]} x={1180} y={330} at={6} p={p} />
    <Char img="img/s03_woo.png" x={420} y={180} w={560} />
  </AbsoluteFill>
);
const D16: React.FC<PP> = ({ p }) => (
  <AbsoluteFill>
    <Bg img="img/s06_crowd.jpg" />
    <LegacySubtitleBand p={p} subs={[{ t0: 0.2, t1: 1.6, text: "짜장면 데이는 매년 4월 14일입니다." }, { t0: 1.6, t1: 3.4, text: "블랙데이라고도 불리죠." }]} />
  </AbsoluteFill>
);
const D17: React.FC<PP> = ({ p }) => (
  <AbsoluteFill>
    <Bg img="real/ghc_now.jpg" filter="grayscale(1) brightness(0.7)" />
    <SourceChipDrawOn text="출처 : GettyImages" at={8} p={p} />
  </AbsoluteFill>
);
const D18: React.FC<PP> = ({ p }) => (
  <AbsoluteFill>
    <Bg img="img/s03_restaurant.jpg" />
    <TabbedChapterHUD chapters={["전화위복", "해외진출 도전", "경부고속도로"]} active={0} activeAt={[[50, 1], [95, 2]]} p={p} />
  </AbsoluteFill>
);
const DarkCut: React.FC<{ from: number; to: number; children: React.ReactNode }> = ({ from, to, children }) => {
  const f = useCurrentFrame();
  return f >= from && f < to ? <AbsoluteFill>{children}</AbsoluteFill> : null;
};
const D19: React.FC<PP> = ({ p }) => (
  <AbsoluteFill>
    <Bg img="img/s02_dock.jpg" />
    {/* 45~95f 는 어두운 씬 */}
    <DarkCut from={45} to={95}><Bg img="img/s05_factory.jpg" filter="brightness(0.3) grayscale(0.6)" /></DarkCut>
    <HUDDarkInvert chapters={["몽헌의 죽음", "시숙부의 난", "시동생의 난", "현대그룹의 위기"]} active={2} darkCuts={[[45, 95]]} p={p} />
  </AbsoluteFill>
);
const D20: React.FC<PP> = ({ p }) => (
  <LegacyFormat p={p} chapters={["우희광", "공화춘 개업", "춘장의 변신", "짜장면 전성기", "오늘의 짜장면"]} segs={[
    { kind: "card", dur: 40, text: "1. 우희광", chapter: 0 },
    { kind: "year", dur: 50, text: "1905년", sub: "1905년," },
    { kind: "scene", dur: 60, sub: "인천 제물포에 한 식당이 문을 엽니다.", content: <Bg img="img/s03_restaurant.jpg" /> },
  ]} />
);
const D21: React.FC<PP> = ({ p }) => (
  <EraPalette p={p} eras={[{ at: 0, color: "sage" }, { at: 40, color: "cream" }, { at: 80, color: "bluegray" }, { at: 120, color: "crimson" }]}
    overlay={<><HUDBar /><LegacySubtitleBand subs={[{ t0: 0, t1: 6, text: "시대가 바뀌면 배경색도 바뀝니다." }]} p={{ bg: "#FFFFFF", alpha: 0.7 }} /></>}>
    <Char img="img/s06_kid.png" x={780} y={230} w={380} />
  </EraPalette>
);
const D22: React.FC<PP> = ({ p }) => <LegacyLogoIntro at={6} p={p} />;

export const DEMOS: Demo[] = [
  { name: "CalligraphySlam — 붓글씨 대형 타이틀 슬램·역슬램 퇴장", dur: 120, C: D01, schema: CalligraphySlamParams },
  { name: "GlowCloudText — 흑백 사진 위 흰 글로우 구름 텍스트", dur: 75, C: D02, schema: GlowCloudTextParams },
  { name: "SpecBandLabel — 그라데이션 밴드 스펙 라벨(2단 누적)", dur: 90, C: D03, schema: SpecBandLabelParams },
  { name: "TitleStripFlyoff — 포스터 직함 떼어 날리기", dur: 90, C: D04, schema: TitleStripFlyoffParams },
  { name: "CornerCharTiles — 네 모서리 빨간 글자 타일", dur: 75, C: D05, schema: CornerCharTilesParams },
  { name: "WordWallpaper — 반복 단어 월페이퍼 → 압축", dur: 120, C: D06, schema: WordWallpaperParams },
  { name: "DefinitionReveal — 정의문 줄단위 블러 상승", dur: 150, C: D07, schema: DefinitionRevealParams },
  { name: "YearChipRoll — 연도 칩 고속 롤 + 라인업 하드스왑", dur: 120, C: D08, schema: YearChipRollParams },
  { name: "SageDateCard — 세이지 연월 타이핑 카드", dur: 70, C: D09, schema: SageDateCardParams },
  { name: "BrushHeadline — 붓글씨 헤드라인 블러 인 + 배경 암부", dur: 80, C: D10, schema: BrushHeadlineParams },
  { name: "FactPillStack — 네이비 팩트 필 누적", dur: 120, C: D11, schema: FactPillStackParams },
  { name: "HeadlineBandSlam — 헤드라인 밴드 가로 스트레치 슬램", dur: 75, C: D12, schema: HeadlineBandSlamParams },
  { name: "TextBehindCharacter — 인물 뒤 대형 수치 → 연기 → 불꽃", dur: 150, C: D13, schema: TextBehindCharacterParams },
  { name: "HanjaMedallion — 배경 디포커스 + 한자 메달리온", dur: 120, C: D14, schema: HanjaMedallionParams },
  { name: "SloganBanner — 사선 구호 배너", dur: 70, C: D15, schema: SloganBannerParams },
  { name: "LegacySubtitleBand — 구 포맷 반투명 자막 띠(하드 교체)", dur: 100, C: D16, schema: LegacySubtitleBandParams },
  { name: "SourceChipDrawOn — 출처 칩 드로우온(화살표→상자→글자)", dur: 60, C: D17, schema: SourceChipDrawOnParams },
  { name: "TabbedChapterHUD — 탭형 챕터 바(활성 칸 하드 교체)", dur: 130, C: D18, schema: TabbedChapterHUDParams },
  { name: "HUDDarkInvert — 어두운 컷에서 HUD 다크 반전", dur: 130, C: D19, schema: HUDDarkInvertParams },
  { name: "LegacyFormat — 초기 포맷(챕터카드·세이지 연도·탭바·자막띠)", dur: 150, C: D20, schema: LegacyFormatParams },
  { name: "EraPalette — 시대별 배경 팔레트 전환", dur: 160, C: D21, schema: EraPaletteParams },
  { name: "LegacyLogoIntro — 구포맷 채널 로고 스탬프 인트로", dur: 75, C: D22, schema: LegacyLogoIntroParams },
];
export const GALLERY_DUR = Math.max(30, DEMOS.reduce((a, d) => a + d.dur, 0));
export const Gallery = runGallery(DEMOS);
