import React from "react";
import { AbsoluteFill, Img, useCurrentFrame } from "remotion";
import { runGallery, Demo } from "./runner";
import { prop, propH } from "../lib/kit";
import { src, Starburst } from "../fx";
import { Shot } from "../lib/transitions";
import {
  Cut, CutImg,
  PinkColorWash, PinkColorWashParams, InPlaceSwap, InPlaceSwapParams, SlideCut, SlideCutParams,
  ZipperTransition, ZipperParams, TwirlLiquid, TwirlLiquidParams, SpectralZoomThrough, SpectralZoomThroughParams,
  GradientLightWash, GradientLightWashParams, ElevatorReveal, ElevatorRevealParams, CrashImpact, CrashImpactParams,
  CyanRingWipe, CyanRingWipeParams, InkBlobReveal, InkBlobRevealParams, TruckPushIn, TruckPushInParams,
  TiltUpSignReveal, TiltUpSignRevealParams, RackDefocus, RackDefocusParams, IsoBuildPullback, IsoBuildPullbackParams,
  BinocularPOV, BinocularPOVParams, WordCard, WordCardParams, IntroMontage, IntroMontageParams, OutroRecap, OutroRecapParams,
  GameshowDoors, GameshowDoorsParams, BookshelfRecap, BookshelfRecapParams, CrowdCreditCard, CrowdCreditCardParams,
  OTSSilhouette, OTSSilhouetteParams, NarratorInterrupt, NarratorInterruptParams,
} from "../lib/x_transitions";

// 도감 x_transitions: 분석만 있던 전환·카메라·구성 기법 데모. 효과는 대부분 6f 에 시작.
const A = 6;
const S = (img: string, pos?: string) => <Shot img={img} pos={pos} />;
const FAM = S("img/s01_family.jpg"), DOCK = S("img/s02_dock.jpg"), REST = S("img/s03_restaurant.jpg"), FACT = S("img/s05_factory.jpg"), CROWD = S("img/s06_crowd.jpg");
const PORT = S("real/port.jpg"), CHINA = S("real/chinatown.jpg"), JJ = S("real/jjajang.jpg"), MUSEUM = S("real/museum.jpg");

// 인물 컷(누끼 PNG / layers_vec 전체 프레임 PNG 는 bbox 로 잘라 씀)
const LV: [number, number] = [1920, 1097];
const WOO: Cut = { img: "img/s03_woo.png", size: [738, 1148] };
const WOO_BACK: Cut = { img: "img/s03_woo_back.png", size: [739, 1148] };
const KID: Cut = { img: "img/s06_kid.png", size: [709, 1010] };
const DOCK_L: Cut = { img: "layers_vec/s02_dock__dock_left.png", box: [342, 310, 747, 963], size: LV };
const DOCK_M: Cut = { img: "layers_vec/s02_dock__dock_mid.png", box: [773, 316, 1176, 955], size: LV };
const DOCK_R: Cut = { img: "layers_vec/s02_dock__dock_right.png", box: [1257, 371, 1690, 985], size: LV };
const C1: Cut = { img: "layers_vec/s06_crowd__crowd_1.png", box: [32, 146, 536, 1027], size: LV };
const C2: Cut = { img: "layers_vec/s06_crowd__crowd_2.png", box: [477, 174, 950, 1027], size: LV };
const C3: Cut = { img: "layers_vec/s06_crowd__crowd_3.png", box: [913, 152, 1395, 1027], size: LV };
const C4: Cut = { img: "layers_vec/s06_crowd__crowd_4.png", box: [1344, 175, 1855, 1026], size: LV };
const MOM: Cut = { img: "layers_vec/s01_family__family_mom.png", box: [222, 180, 656, 850], size: LV };
const DAD: Cut = { img: "layers_vec/s01_family__family_dad.png", box: [1227, 139, 1788, 873], size: LV };
const SON: Cut = { img: "layers_vec/s01_family__family_son.png", box: [646, 166, 1295, 911], size: LV };
const CAST = [WOO, C1, KID, DOCK_M, C2, MOM, DOCK_L, C3, DAD, DOCK_R, C4, SON];

const Place: React.FC<{ c: Cut; x: number; bottom: number; w: number }> = ({ c, x, bottom, w }) => (
  <div style={{ position: "absolute", left: x - w / 2, top: bottom - w * (c.box ? (c.box[3] - c.box[1]) / (c.box[2] - c.box[0]) : c.size![1] / c.size![0]) }}><CutImg c={c} w={w} /></div>
);
const Chip: React.FC<{ t: string; x: number; y: number; bg?: string; fg?: string; size?: number; rot?: number }> = ({ t, x, y, bg = "#2F6F8F", fg = "#fff", size = 40, rot = 0 }) => (
  <div style={{ position: "absolute", left: x, top: y, transform: `translate(-50%,-50%) rotate(${rot}deg)`, background: bg, color: fg, fontFamily: "NeoHv", fontSize: size, padding: "10px 24px 4px", borderRadius: 10, whiteSpace: "nowrap", boxShadow: "0 4px 8px rgba(0,0,0,0.2)" }}>{t}</div>
);

// ── 데모 ─────────────────────────────────────────────────────────────────
const DSwap: React.FC<{ p?: any }> = ({ p }) => (
  <InPlaceSwap at={30} p={p}
    base={<AbsoluteFill><Img src={src("layers_vec/s02_dock__bg.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover" }} /><Place c={WOO} x={760} bottom={1180} w={620} /></AbsoluteFill>}
    a={<AbsoluteFill><Chip t="한식 조리사 자격증" x={1380} y={300} bg="#fff" fg="#2B5B3F" rot={-4} /><Chip t="양식 조리사 자격증" x={1440} y={420} bg="#fff" fg="#2B5B3F" rot={6} /><div style={{ position: "absolute", left: 120, top: 380, fontFamily: "Jua", fontSize: 60, color: "#222" }}>쉽지 않긴 한데..<br />재밌네?</div></AbsoluteFill>}
    b={<Place c={{ img: "img/s05_bowl.png", size: [1122, 1063] }} x={420} bottom={980} w={560} />}
    labelA="자격증" labelB="대표 요리" labelX={1460} labelY={140} />
);
const PROJ: React.FC<{ rows: number; y0: number; bg: string }> = ({ rows, y0, bg }) => (
  <AbsoluteFill style={{ background: bg }}>
    {Array.from({ length: 6 }).map((_, i) => <div key={i} style={{ position: "absolute", left: (i * 331) % 1800, top: (i * 223) % 900, width: 260, height: 260, borderRadius: "50%", background: "rgba(255,255,255,0.35)", filter: "blur(20px)" }} />)}
    {Array.from({ length: rows }).map((_, r) => (
      <div key={r} style={{ position: "absolute", left: -60 + (r % 2) * 40, top: y0 + r * 92, display: "flex", gap: 22 }}>
        {Array.from({ length: 9 }).map((_, c) => <div key={c} style={{ background: "#fff", fontFamily: "NeoHv", fontSize: 50, padding: "8px 16px 0", color: "#111" }}>PROJECT</div>)}
      </div>
    ))}
  </AbsoluteFill>
);
const Sage: React.FC<{ children?: React.ReactNode }> = ({ children }) => <AbsoluteFill style={{ background: "#C3CBBF" }}>{children}</AbsoluteFill>;
const Driving: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: "#7FB7D9" }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 420, bottom: 0, background: "#4A5670" }} />
      {[0, 1, 2, 3].map((i) => { const k = ((f * 0.06 + i / 4) % 1); return <div key={i} style={{ position: "absolute", left: 960 - 8 - k * 30, top: 430 + k * k * 700, width: 16 + k * 60, height: 30 + k * 160, background: "#F2F2F2" }} />; })}
      <div style={{ position: "absolute", left: 0, top: 0, width: "100%", height: "100%", transform: `translateY(${Math.sin(f / 3) * 4}px)` }}>
        {/* 세모지 그림체 자동차 정면(carfront_glass → 운전자 → 유리 반사 → carfront_body, 같은 크롭 박스) */}
        <Img src={prop("carfront_glass")} style={{ position: "absolute", left: 460, top: 250, width: 1000, height: propH("carfront_glass", 1000) }} />
        <div style={{ position: "absolute", left: 860, top: 330, width: 200, height: 210 }}><CutImg c={DAD} w={200} /></div>
        <Img src={prop("carfront_glass")} style={{ position: "absolute", left: 460, top: 250, width: 1000, height: propH("carfront_glass", 1000), opacity: 0.3 }} />
        <Img src={prop("carfront_body")} style={{ position: "absolute", left: 460, top: 250, width: 1000, height: propH("carfront_body", 1000) }} />
      </div>
    </AbsoluteFill>
  );
};
const Stage: React.FC = () => (
  <div style={{ position: "absolute", inset: 0, width: 2600, background: "#56628C" }}>
    <div style={{ position: "absolute", left: 0, top: 0, width: 1700, height: 1080, overflow: "hidden" }}><Img src={src("layers_vec/s06_crowd__bg.jpg")} style={{ width: 1920, height: 1080, objectFit: "cover" }} /></div>
    <Place c={C1} x={260} bottom={1000} w={430} /><Place c={C2} x={700} bottom={1010} w={420} /><Place c={C3} x={1150} bottom={1000} w={430} />
    <div style={{ position: "absolute", left: 0, top: 820, width: 1700, height: 260, background: "#C8973F", borderRadius: "50% 50% 0 0 / 30% 30% 0 0" }} />
    <div style={{ position: "absolute", left: 1960, top: 240, width: 400, height: 680, background: "#AFC6E3", boxShadow: "0 0 0 18px #2C3558" }}>
      <div style={{ position: "absolute", left: 60, bottom: -10 }}><CutImg c={WOO} w={290} /></div>
    </div>
  </div>
);
const Ship: React.FC = () => {
  const f = useCurrentFrame();
  const x = -900 + f * 16;
  return (
    <AbsoluteFill>
      <Img src={src("real/port.jpg")} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", filter: "saturate(0.8) brightness(1.05)" }} />
      {/* 세모지 그림체 화물선(cargo_ship) */}
      <Img src={prop("cargo_ship")} style={{ position: "absolute", left: x, top: 790 - propH("cargo_ship", 1000), width: 1000, height: propH("cargo_ship", 1000) }} />
    </AbsoluteFill>
  );
};
const Endcard: React.FC = () => (
  <AbsoluteFill style={{ background: "#B0BCAA", alignItems: "center", justifyContent: "center", gap: 30 }}>
    <Img src={src("ui/logo_circle.png")} style={{ width: 260 }} />
    <div style={{ fontFamily: "NeoHv", fontSize: 64, color: "#1E1E1E" }}>구독 · 좋아요</div>
  </AbsoluteFill>
);

const D = (name: string, dur: number, schema: Demo["schema"], C: React.FC<{ p?: any }>): Demo => ({ name, dur, C, schema });

export const DEMOS: Demo[] = [
  D("PinkColorWash — 핑크 컬러 워시 디졸브", 60, PinkColorWashParams, ({ p }) => <PinkColorWash at={A + 10} from={REST} to={CHINA} p={p} />),
  D("InPlaceSwap — 제자리 장면 교체(오버레이 교체+풀백)", 90, InPlaceSwapParams, DSwap),
  D("SlideCut — 캐릭터가 밀고 들어오는 씬 전환", 70, SlideCutParams, ({ p }) => (
    <SlideCut at={A + 8} from={FAM} to={REST} p={p} char={<Place c={DOCK_M} x={420} bottom={1080} w={520} />} />
  )),
  D("ZipperTransition — 지퍼 잠금/열림(압축 은유)", 135, ZipperParams, ({ p }) => (
    <ZipperTransition at={A} p={p} from={<PROJ rows={11} y0={-20} bg="#F7E6A0" />} to={<PROJ rows={2} y0={430} bg="#F9DC7A" />} />
  )),
  D("TwirlLiquid — 연도 카드 트월 리퀴드 전환", 60, TwirlLiquidParams, ({ p }) => <TwirlLiquid at={A} text="2009년" to={JJ} p={p} />),
  D("GradientLightWash — 파스텔 그라디언트 광원 워시", 60, GradientLightWashParams, ({ p }) => (
    <GradientLightWash at={A + 8} p={p} from={<Sage />} to={FAM}
      fg={(c) => <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}><div style={{ fontFamily: "NeoHv", fontSize: 96, color: c }}>1985년</div></AbsoluteFill>} />
  )),
  D("ElevatorReveal — 엘리베이터 문 열림 리빌", 110, ElevatorRevealParams, ({ p }) => <ElevatorReveal at={A + 6} person={C2} p={p} />),
  D("CrashImpact — 충돌 임팩트 줌 + 유리 균열", 60, CrashImpactParams, ({ p }) => <CrashImpact at={A + 12} origin={[960, 520]} p={p}><Driving /></CrashImpact>),
  D("CyanRingWipe — 시안 에너지 링 와이프", 50, CyanRingWipeParams, ({ p }) => <CyanRingWipe at={A + 6} from={FACT} to={PORT} p={p} />),
  D("SpectralZoomThrough — 날짜카드 스펙트럼 틸트 줌스루", 60, SpectralZoomThroughParams, ({ p }) => <SpectralZoomThrough at={A} text="1993년 6월 7일" to={MUSEUM} p={p} />),
  D("InkBlobReveal — 먹물 방울 흩어짐 리빌", 50, InkBlobRevealParams, ({ p }) => <InkBlobReveal at={A + 6} from={FACT} to={CROWD} p={p} />),
  D("TruckPushIn — 가로 팬 → 문 안 인물 푸시인", 80, TruckPushInParams, ({ p }) => (
    <TruckPushIn at={A} p={p} stage={<Stage />} target={[2160, 560]} fg={<Place c={KID} x={380} bottom={1250} w={520} />} />
  )),
  D("TiltUpSignReveal — 카메라 틸트업 갈림길 표지판", 120, TiltUpSignRevealParams, ({ p }) => (
    <TiltUpSignReveal at={A} p={p} person={WOO_BACK} highlight={0}
      signs={[{ text: "하드웨어 부문", sub: "Canon", dir: "left" }, { text: "소프트웨어 부문", sub: "NeXT", dir: "right", subColor: "#F6C43A" }]} />
  )),
  D("RackDefocus — 직전 장면 디포커스 백드롭 + 레이어 팝", 60, RackDefocusParams, ({ p }) => (
    <RackDefocus at={A + 6} p={p} backdrop={PORT}
      layer={<AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}><div style={{ display: "flex", alignItems: "center", background: "#D7182A", borderRadius: 120, padding: "20px 70px 10px 20px", gap: 30, boxShadow: "0 10px 20px rgba(0,0,0,0.3)" }}><Img src={src("img/s05_chunjang.png")} style={{ width: 220 }} /><span style={{ fontFamily: "NeoHv", fontSize: 110, color: "#fff" }}>284,830L</span></div></AbsoluteFill>} />
  )),
  D("IsoBuildPullback — 아이소메트릭 빌드업 풀백", 100, IsoBuildPullbackParams, ({ p }) => <IsoBuildPullback at={A} p={p} />),
  D("BinocularPOV — 쌍안경 마스크 시점", 90, BinocularPOVParams, ({ p }) => (
    <BinocularPOV at={A + 12} p={p} from={<AbsoluteFill style={{ background: "#F6F3EC", alignItems: "center", justifyContent: "center", fontFamily: "NeoHv", fontSize: 80, color: "#1c1c1c" }}>4. 현대그룹의 위기</AbsoluteFill>}><Ship /></BinocularPOV>
  )),
  D("WordCard — 단어 카드(짧은 인터스티셜)", 45, WordCardParams, ({ p }) => <WordCard at={A + 6} text="그런데" from={FAM} to={REST} p={p} />),
  D("IntroMontage — 실사 클립 몽타주 인트로", 120, IntroMontageParams, ({ p }) => (
    <IntroMontage p={p} clips={["real/chinatown.jpg", "real/jjajang.jpg", "real/port.jpg", "real/museum.jpg", "real/zhajiang.jpg", "real/chunjang.jpg", "real/ghc_now.jpg", "real/ghc_closed.jpg", "img/s03_restaurant.jpg", "img/s05_factory.jpg", "img/s06_crowd.jpg", "img/s02_dock.jpg"]} />
  )),
  D("OutroRecap — 아웃트로 리캡(번→요약→인물 누적→엔드카드)", 180, OutroRecapParams, ({ p }) => (
    <OutroRecap at={A} p={p} from={REST} conclusion="화교 출신의 요리사"
      items={[{ label: "아서원", img: WOO, name: "유방녕", color: "#2F5DAA" }, { label: "홍보석", img: DOCK_M, name: "여경래", color: "#B3262E" }, { label: "호화대반점", img: C2, name: "이연복", color: "#2F8A4A" }, { label: "팔선", img: DOCK_L, name: "후덕죽", color: "#E08A1E" }]}
      cast={[C1, DOCK_M, C3, WOO, C4]} endcard={<Endcard />} />
  )),
  D("GameshowDoors — 게임쇼 번호문 순차 공개", 110, GameshowDoorsParams, ({ p }) => <GameshowDoors at={0} p={p} people={[C1, C2, C3, C4]} />),
  D("BookshelfRecap — 백과사전 책장 시리즈 리캡", 170, BookshelfRecapParams, ({ p }) => (
    <BookshelfRecap at={0} p={p} labels={[{ text: "개인용 컴퓨터 시대", book: 3 }, { text: "MP3 신드롬", book: 7 }, { text: "스마트폰\n전성시대", book: 9 }, { text: "태블릿PC의\n대중화", book: 12 }, { text: "무선이어폰 열풍", book: 14 }]} />
  )),
  D("CrowdCreditCard — 군중 프레임 후원자 크레딧 엔딩", 90, CrowdCreditCardParams, ({ p }) => (
    <CrowdCreditCard at={0} p={p} crowd={CAST} names={["오늘참좋다", "전윤기", "서봉석", "hye eun Gil", "J go", "락마", "이일환", "김하늘", "박세모", "최지식", "정다운", "한결"]} />
  )),
  D("OTSSilhouette — 어깨너머 검정 실루엣 전경", 70, OTSSilhouetteParams, ({ p }) => (
    <OTSSilhouette at={0} p={p} speaker={DOCK_L} listener={WOO_BACK} bubble={<Starburst text={"우리 동료가\n되라~!!"} x={880} y={260} w={380} h={270} at={10} size={44} />} />
  )),
  D("NarratorInterrupt — '잠깐!!' 내레이터 실루엣 끼어들기", 120, NarratorInterruptParams, ({ p }) => (
    <NarratorInterrupt at={A} p={p} backdrop={MUSEUM} mascot={WOO}
      sticker={<div style={{ display: "flex", alignItems: "center", gap: 8, background: "#fff", borderRadius: 18, padding: "8px 18px", boxShadow: "0 3px 6px rgba(0,0,0,0.2)" }}><Img src={src("img/s05_chunjang.png")} style={{ width: 90 }} /><span style={{ fontFamily: "Jua", fontSize: 30 }}>머쓱타드..</span></div>} />
  )),
];
export const GALLERY_DUR = Math.max(30, DEMOS.reduce((a, d) => a + d.dur, 0));
export const Gallery = runGallery(DEMOS);
