import React from "react";
import { AbsoluteFill, Sequence, useCurrentFrame } from "remotion";
import { runGallery, Demo } from "./runner";
import { z } from "zod";
import { num } from "../params/p";
import {
  StampParams, StampP, SceneParams, SceneP, HUD2Params, HUD2P, SubtitlesParams, SubtitlesP, YearTagParams, YearTagP,
  ScrollLabelParams, ScrollLabelP, PhotoFrameParams, PhotoFrameP, StickerParams, StickerP, CircleImgParams, CircleImgP,
  StarburstParams, StarburstP, AnnotParams, AnnotP, NameTagParams, NameTagP, QuoteBoxParams, QuoteBoxP,
  SparklesParams, SparklesP, GlowPulseParams, GlowPulseP, WaveBgParams, WaveBgP, CloudBgParams, CloudBgP,
  PaperOverlayParams, PaperOverlayP, GrainParams, GrainP, QSilhouetteParams, QSilhouetteP, LayeredCoverParams, LayeredCoverP,
  SteamParams, SteamP, OnomaParams, OnomaP, FlickerLeakParams, FlickerLeakP, YellowBurstParams, YellowBurstP,
  SmokeWipeParams, SmokeWipeP, ConfettiParams, ConfettiP, FlipTurnParams, FlipTurnP, SpotlightParams, SpotlightP,
  ArrowTagParams, ArrowTagP, IconPopParams, IconPopP, EchoTitleParams, EchoTitleP, DashCircleParams, DashCircleP,
  SweatDropParams, SweatDropP, MapRouteParams, MapRouteP, TypeCardParams, TypeCardP, GlitchOverlayParams, GlitchOverlayP,
  AvatarPopParams, AvatarPopP, TermCardParams, TermCardP, ElbowCalloutParams, ElbowCalloutP, MagnifierBoxParams, MagnifierBoxP,
  FilmStripParams, FilmStripP, HUDParams, HUDP, ShakeParams, ShakeP,
} from "../fx";
import REAL from "../real.json";
import LAYERS from "../layers.json";
import {
  Scene, Cover, HUD2, Subtitles, YearTag, ScrollLabel, PhotoFrame, Sticker, CircleImg, Stamp, Starburst,
  Annot, NameTag, QuoteBox, Sparkles, GlowPulse, WaveBg, CloudBg, PaperOverlay, Grain, QSilhouette,
  LayeredCover, LayerSpec, Steam, Onoma, FlickerLeak, YellowBurst, SmokeWipe, Confetti, FlipTurn, Spotlight,
  ArrowTag, IconPop, IconCaramel, IconSugar, EchoTitle, DashCircle, SweatDrop, MapRoute, TypeCard,
  GlitchOverlay, AvatarPop, TermCard, ElbowCallout, MagnifierBox, FilmStrip, lerp,
} from "../fx";

// 코어 기법 도감: fx.tsx 컴포넌트를 한 기법씩 단독 시연한다. 효과는 대부분 6f 에 시작.
// ※ Rays(방사형 줄무늬 광선)는 사용 금지 기법이라 도감에 싣지 않는다.
const LY = LAYERS as Record<string, LayerSpec>;
const A_IMG = "img/s01_family.jpg";
const B_IMG = "img/s03_restaurant.jpg";
const BW = "grayscale(1) sepia(0.2) contrast(1.9) brightness(0.92)";

// ── 씬 전환 A→B 공통 ─────────────────────────────────────────────────────
const SA: React.FC<{ id: string; dur: number; exit?: "whip" | "cut" | "zoomThrough"; exitOrigin?: string; p?: Partial<SceneP> }> = ({ id, dur, exit, exitOrigin, p }) => (
  <Scene id={id} dur={dur} exit={exit} exitOrigin={exitOrigin} p={p}><Cover img={A_IMG} /></Scene>
);
const SB: React.FC<{ id: string; dur: number; enter?: "whip" | "cut" | "dissolve" | "cover" | "zoomIn"; p?: Partial<SceneP> }> = ({ id, dur, enter, p }) => (
  <Scene id={id} dur={dur} enter={enter} p={p}><Cover img={B_IMG} /></Scene>
);
/** A 를 aDur 동안, B 를 bFrom 부터 끝까지. aDur > bFrom 이면 겹친다(디졸브·커버) */
const AB = (o: { name: string; aDur: number; bFrom: number; dur: number; exit?: "whip" | "zoomThrough"; enter?: "whip" | "dissolve" | "cover" | "zoomIn"; exitOrigin?: string }) => ({
  name: o.name, dur: o.dur, schema: SceneParams,
  C: ({ p }: { p?: Partial<SceneP> }) => (
    <AbsoluteFill style={{ background: "#000" }}>
      <Sequence from={0} durationInFrames={o.aDur}><SA id={`a-${o.exit ?? "cut"}-${o.enter}`} dur={o.aDur} exit={o.exit} exitOrigin={o.exitOrigin} p={p} /></Sequence>
      <Sequence from={o.bFrom}><SB id={`b-${o.exit ?? "cut"}-${o.enter}`} dur={o.dur - o.bFrom} enter={o.enter} p={p} /></Sequence>
    </AbsoluteFill>
  ),
});

// 전환 오버레이 시연: cut 프레임에 A→B 하드컷, 오버레이는 그 위
const CutUnder: React.FC<{ cut: number; a?: string; b?: string; aStyle?: React.CSSProperties }> = ({ cut, a = A_IMG, b = B_IMG, aStyle }) => {
  const f = useCurrentFrame();
  return f < cut ? <Cover img={a} style={aStyle} /> : <Cover img={b} />;
};

const Dim: React.FC<{ img: string; k?: number; blur?: number; style?: React.CSSProperties }> = ({ img, k = 0.55, blur = 0, style }) => (
  <Cover img={img} style={{ filter: `brightness(${k})${blur ? ` blur(${blur}px)` : ""}`, transform: blur ? "scale(1.06)" : undefined, ...style }} />
);
const Paper: React.FC<{ bg?: string }> = ({ bg = "#EDE3D0" }) => (
  <AbsoluteFill style={{ background: bg }}><PaperOverlay strength={0.4} /></AbsoluteFill>
);
const FadeIn: React.FC<{ at?: number; children: React.ReactNode }> = ({ at = 6, children }) => {
  const f = useCurrentFrame();
  return <AbsoluteFill style={{ opacity: lerp(f, at, at + 10, 0, 1) }}>{children}</AbsoluteFill>;
};

// ── 개별 데모 ────────────────────────────────────────────────────────────
// 카메라 풀백은 Scene 의 cam prop(씬별 내용값)이라 fx 스키마가 없다 → 데모 전용 변수로 노출
const CamPullParams = z.object({
  s0: num(1.5, 1, 3, 0.05, "시작 배율(배)", "motion"),
  s1: num(1.0, 0.5, 2, 0.05, "끝 배율(배)", "motion"),
  y0: num(255, -600, 600, 5, "시작 세로 오프셋", "motion", "px"),
  moveF: num(55, 1, 90, 1, "카메라 이동 길이", "timing", "f"),
  delay: num(6, 0, 60, 1, "이동 시작 지연", "timing", "f"),
});
const DCamPull: React.FC<{ p?: Partial<z.infer<typeof CamPullParams>> }> = ({ p }) => (
  <Scene id="d-cam" dur={90} cam={{ s0: 1.5, s1: 1.0, y0: 255, y1: 0, moveF: 55, delay: 6, ...p }}>
    <LayeredCover spec={LY["s01_family"]} dur={90} />
  </Scene>
);

const DCover: React.FC = () => (
  <AbsoluteFill style={{ background: "#000" }}>
    <Sequence from={6}><Cover img={REAL.port.file} style={{ filter: BW, objectPosition: REAL.port.pos }} /></Sequence>
  </AbsoluteFill>
);

const CH_MARK = ["仁川港 인천항", "共和春 공화춘"];
const DHud2: React.FC<{ p?: Partial<HUD2P> }> = ({ p }) => {
  const f = useCurrentFrame();
  const i = f < 55 ? 0 : 1;
  return (
    <AbsoluteFill>
      <Dim img={B_IMG} k={0.8} />
      <HUD2 label={CH_MARK[i]} changeAt={i === 0 ? 6 : 55} p={p} />
    </AbsoluteFill>
  );
};

const DSubs: React.FC<{ p?: Partial<SubtitlesP> }> = ({ p }) => (
  <AbsoluteFill>
    <Cover img={B_IMG} />
    <Subtitles subs={[
      { t0: 0.2, t1: 1.9, text: "1883년, 제물포가 문을 열자" },
      { t0: 1.9, t1: 3.6, text: "산둥의 노동자들이 인천으로 몰려왔습니다" },
    ]} p={p} />
  </AbsoluteFill>
);

const DYearTag: React.FC<{ p?: Partial<YearTagP> }> = ({ p }) => (
  <AbsoluteFill>
    <Cover img={B_IMG} />
    <YearTag text="1900년대 초" at={6} out={60 + 16} p={p} />
    <YearTag text="1912년 무렵" at={60} p={p} />
  </AbsoluteFill>
);

const DScroll: React.FC<{ p?: Partial<ScrollLabelP> }> = ({ p }) => (
  <AbsoluteFill>
    <Dim img={B_IMG} k={0.75} />
    <ScrollLabel text="공화춘" sub="共和春" x={960} y={540} w={460} at={6} color="#2E7D4F" size={78} out={80} p={p} />
  </AbsoluteFill>
);

const DPhoto: React.FC<{ p?: Partial<PhotoFrameP> }> = ({ p }) => (
  <AbsoluteFill>
    <CloudBg base="#2E5F4A" line="#3C7058" />
    <PhotoFrame img={REAL.ghcNow.file} x={560} y={250} w={800} h={520} at={6} color="#2E7D4F" pos={REAL.ghcNow.pos} rot={3} p={p} />
  </AbsoluteFill>
);

const DSticker: React.FC<{ p?: Partial<StickerP> }> = ({ p }) => (
  <AbsoluteFill>
    <CloudBg base="#D9892B" line="#E39A3E" />
    <Sticker img="img/s05_chunjang.png" x={90} y={380} w={520} at={6} from="left" p={p} />
    <Sticker img="img/s06_kid.png" x={760} y={330} w={420} at={26} from="bottom" p={p} />
    <Sticker img="img/s05_bowl.png" x={1270} y={380} w={560} at={46} from="pop" p={p} />
  </AbsoluteFill>
);

const DCircle: React.FC<{ p?: Partial<CircleImgP> }> = ({ p }) => (
  <AbsoluteFill>
    <Dim img="img/s02_dock.jpg" k={0.7} />
    <CircleImg img={REAL.jjajang.file} x={1520} y={250} d={360} at={6} pos={REAL.jjajang.pos} p={p} />
  </AbsoluteFill>
);

const DStamp: React.FC<{ p?: Partial<StampP> }> = ({ p }) => (
  <AbsoluteFill>
    <Dim img={REAL.chinatown.file} k={0.42} blur={7} />
    <PhotoFrame img={REAL.ghcClosed.file} x={500} y={230} w={920} h={600} at={-10} color="#2E5FB0" pos={REAL.ghcClosed.pos} />
    <Stamp text="폐업" x={960} y={560} at={8} p={{ size: 150, ...p }} />
  </AbsoluteFill>
);

const DStarburst: React.FC<{ p?: Partial<StarburstP> }> = ({ p }) => (
  <AbsoluteFill>
    <CloudBg />
    <Sticker img="img/s05_bowl.png" x={430} y={300} w={640} at={-10} from="none" />
    <Starburst text={"짜장면!"} x={1360} y={400} w={500} h={340} at={6} size={80} p={p} />
  </AbsoluteFill>
);

const DAnnot: React.FC<{ p?: Partial<AnnotP> }> = ({ p }) => (
  <AbsoluteFill>
    <Cover img={A_IMG} />
    <Annot text="졸업식 날" x={260} y={230} at={6} size={80} rot={-6} p={p} />
    <Annot text="이삿날" x={760} y={150} at={18} size={80} rot={3} p={p} />
    <Annot text="비 오는 날" x={1240} y={230} at={30} size={80} rot={-4} p={p} />
  </AbsoluteFill>
);

const DNameTag: React.FC<{ p?: Partial<NameTagP> }> = ({ p }) => (
  <AbsoluteFill>
    <Cover img={B_IMG} />
    <Sticker img="img/s03_woo.png" x={120} y={380} w={430} at={-20} from="none" />
    <NameTag text="화교 우희광" x={150} y={320} at={6} p={p} />
  </AbsoluteFill>
);

const DQuote: React.FC<{ p?: Partial<QuoteBoxP> }> = ({ p }) => (
  <AbsoluteFill>
    <Cover img="img/s06_crowd.jpg" />
    <QuoteBox text={"부두의 한 끼에서\n국민 음식으로"} x={960} y={600} w={900} at={6} p={p} />
  </AbsoluteFill>
);

const DSparkles: React.FC<{ p?: Partial<SparklesP> }> = ({ p }) => (
  <AbsoluteFill>
    <CloudBg />
    <Sticker img="img/s05_bowl.png" x={610} y={240} w={700} at={-10} from="none" />
    <Sparkles at={6} pts={[[560, 330, 90], [1360, 290, 70], [1300, 760, 100], [620, 720, 60], [960, 200, 50]]} p={p} />
  </AbsoluteFill>
);

const DGlow: React.FC<{ p?: Partial<GlowPulseP> }> = ({ p }) => (
  <AbsoluteFill>
    <CloudBg />
    <GlowPulse x={960} y={560} at={6} r={560} p={p} />
    <Sticker img="img/s05_bowl.png" x={610} y={240} w={700} at={-10} from="none" />
  </AbsoluteFill>
);

const DWave: React.FC<{ p?: Partial<WaveBgP> }> = ({ p }) => (
  <AbsoluteFill style={{ background: "#000" }}><FadeIn><WaveBg p={p} /></FadeIn></AbsoluteFill>
);
const DCloud: React.FC<{ p?: Partial<CloudBgP> }> = ({ p }) => (
  <AbsoluteFill style={{ background: "#000" }}><FadeIn><CloudBg p={p} /></FadeIn></AbsoluteFill>
);

const DPaper: React.FC<{ p?: Partial<PaperOverlayP> }> = ({ p }) => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill>
      <Cover img={REAL.port.file} style={{ filter: BW, objectPosition: REAL.port.pos }} />
      <PaperOverlay p={{ ...p, strength: lerp(f, 6, 26, 0, p?.strength ?? 0.6) }} />
    </AbsoluteFill>
  );
};

// 그레인: 실사용 0.06 은 미리보기에서 안 보이므로 시연용으로 0→0.35 까지 올린다
const DGrain: React.FC<{ p?: Partial<GrainP> }> = ({ p }) => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill>
      <Cover img={B_IMG} />
      <Grain p={{ ...p, opacity: lerp(f, 6, 26, 0, p?.opacity ?? 0.35) }} />
    </AbsoluteFill>
  );
};

const DQSil: React.FC<{ p?: Partial<QSilhouetteP> }> = ({ p }) => (
  <AbsoluteFill>
    <WaveBg />
    <AbsoluteFill style={{ background: "radial-gradient(ellipse 38% 60% at 50% 30%, rgba(255,250,230,0.22), transparent 70%)" }} />
    <QSilhouette x={960} y={900} at={6} s={1.35} p={p} />
  </AbsoluteFill>
);

const DLayered: React.FC<{ p?: Partial<LayeredCoverP> }> = ({ p }) => (
  <AbsoluteFill style={{ background: "#000" }}><LayeredCover spec={LY["s02_dock"]} dur={150} p={p} /></AbsoluteFill>
);

const DSteam: React.FC<{ p?: Partial<SteamP> }> = ({ p }) => (
  <AbsoluteFill>
    <WaveBg />
    <Sticker img="img/s05_bowl.png" x={660} y={420} w={600} at={-10} from="none" />
    <Steam x={880} y={560} s={1.3} at={6} p={p} /><Steam x={1060} y={570} s={1.2} at={14} p={p} />
  </AbsoluteFill>
);

const DOnoma: React.FC<{ p?: Partial<OnomaP> }> = ({ p }) => (
  <AbsoluteFill>
    <Cover img="img/s02_dock.jpg" />
    <Onoma text="후루룩" x={560} y={250} at={6} life={40} size={64} p={p} />
    <Onoma text="꿀꺽꿀꺽" x={1300} y={300} at={30} life={40} size={60} rot={6} p={p} />
  </AbsoluteFill>
);

const DFlicker: React.FC<{ p?: Partial<FlickerLeakP> }> = ({ p }) => (
  <AbsoluteFill><CutUnder cut={20} a="img/s06_crowd.jpg" b={REAL.chinatown.file} /><FlickerLeak at={6} p={p} /></AbsoluteFill>
);
const DYellow: React.FC<{ p?: Partial<YellowBurstP> }> = ({ p }) => (
  <AbsoluteFill><CutUnder cut={13} a="img/s05_factory.jpg" b={REAL.museum.file} /><YellowBurst at={6} p={p} /></AbsoluteFill>
);
const DSmoke: React.FC<{ p?: Partial<SmokeWipeP> }> = ({ p }) => (
  <AbsoluteFill><CutUnder cut={13} a="img/s05_factory.jpg" b={REAL.jjajang.file} /><SmokeWipe at={6} p={p} /></AbsoluteFill>
);
const DGlitch: React.FC<{ p?: Partial<GlitchOverlayP> }> = ({ p }) => (
  <AbsoluteFill><CutUnder cut={13} a="img/s05_factory.jpg" b={A_IMG} /><GlitchOverlay at={10} p={p} /></AbsoluteFill>
);

const DConfetti: React.FC<{ p?: Partial<ConfettiP> }> = ({ p }) => (
  <AbsoluteFill><Cover img="img/s06_crowd.jpg" /><Confetti at={6} y={1000} p={p} /></AbsoluteFill>
);

const DFlip: React.FC<{ p?: Partial<FlipTurnP> }> = ({ p }) => (
  <AbsoluteFill>
    <Cover img={B_IMG} />
    <FlipTurn back="img/s03_woo_back.png" front="img/s03_woo.png" x={745} y={300} w={430} at={6} flipAt={36} p={p} />
  </AbsoluteFill>
);

const DSpot: React.FC<{ p?: Partial<SpotlightP> }> = ({ p }) => (
  <AbsoluteFill>
    <LayeredCover spec={LY["s06_crowd"]} dur={80} />
    <Spotlight rect={[20, 120, 540, 900]} at={6} out={62} p={p} />
  </AbsoluteFill>
);

const DArrow: React.FC<{ p?: Partial<ArrowTagP> }> = ({ p }) => (
  <AbsoluteFill>
    <LayeredCover spec={LY["s06_crowd"]} dur={60} />
    <ArrowTag text="1900년대 부두 노동자" x={620} y={170} at={6} path="M640,245 Q520,215 420,262" head={[420, 262, 165]} size={46} p={p} />
  </AbsoluteFill>
);

const DIcon: React.FC<{ p?: Partial<IconPopP> }> = ({ p }) => (
  <AbsoluteFill>
    <Dim img="img/s05_factory.jpg" k={0.6} />
    <Sticker img="img/s05_chunjang.png" x={700} y={560} w={520} at={-10} from="none" />
    <IconPop icon={<IconCaramel />} label="캐러멜" x={1300} y={300} at={6} suckAt={48} to={[960, 800]} idx={0} p={p} />
    <IconPop icon={<IconSugar />} label="단맛" x={1580} y={420} at={16} suckAt={48} to={[960, 800]} idx={1} p={p} />
  </AbsoluteFill>
);

const DEcho: React.FC<{ p?: Partial<EchoTitleP> }> = ({ p }) => (
  <AbsoluteFill style={{ background: "#A9B7A1" }}>
    <PaperOverlay strength={0.45} />
    <EchoTitle text="세상의 모든 지식" x={960} y={440} at={6} size={130} color="#4F5E48" p={p} />
  </AbsoluteFill>
);

const DDash: React.FC<{ p?: Partial<DashCircleP> }> = ({ p }) => (
  <AbsoluteFill>
    <Cover img={B_IMG} />
    <DashCircle cx={958} cy={483} rx={290} ry={110} at={6} p={p} />
  </AbsoluteFill>
);

const DSweat: React.FC<{ p?: Partial<SweatDropP> }> = ({ p }) => (
  <AbsoluteFill>
    <CloudBg base="#6E8FA8" line="#7E9DB4" />
    <Sticker img="img/s06_kid.png" x={710} y={220} w={500} at={-10} from="none" />
    <SweatDrop x={1110} y={250} at={6} s={1.6} p={p} />
  </AbsoluteFill>
);

const DMap: React.FC<{ p?: Partial<MapRouteP> }> = ({ p }) => <MapRoute at={0} routeAt={20} labelsAt={6} p={p} />;

const DType: React.FC<{ p?: Partial<TypeCardP> }> = ({ p }) => (
  <AbsoluteFill style={{ background: "#1c1c1c" }}>
    <Sequence from={6}><TypeCard text="그러던 어느 날" dur={54} p={p} /></Sequence>
  </AbsoluteFill>
);

const DAvatar: React.FC<{ p?: Partial<AvatarPopP> }> = ({ p }) => (
  <AbsoluteFill>
    <MapRoute at={0} routeAt={-60} labelsAt={-60} />
    <AvatarPop at={6} pts={[[1235, 560], [1310, 520], [1265, 640], [1340, 600], [1215, 455], [1300, 440]]} p={p} />
  </AbsoluteFill>
);

const DTerm: React.FC<{ p?: Partial<TermCardP> }> = ({ p }) => (
  <AbsoluteFill>
    <Cover img="img/s02_dock.jpg" />
    <TermCard term="작장면(炸醬麵)" def="장(醬)을 볶아(炸) 국수(麵)에 비벼 먹는 산둥 요리" at={6} out={70} p={p} />
  </AbsoluteFill>
);

const DElbow: React.FC<{ p?: Partial<ElbowCalloutP> }> = ({ p }) => (
  <AbsoluteFill>
    <Cover img="img/s05_factory.jpg" />
    <CircleImg img={REAL.chunjang.file} x={1700} y={710} d={290} at={-10} pos={REAL.chunjang.pos} />
    <ElbowCallout from={[1555, 720]} mid={[1460, 720]} to={[1460, 845]} text="실제 춘장" at={6} p={p} />
  </AbsoluteFill>
);

const DMagnifier: React.FC<{ p?: Partial<MagnifierBoxP> }> = ({ p }) => (
  <AbsoluteFill>
    <Dim img={REAL.chinatown.file} k={0.42} blur={7} />
    <PhotoFrame img={REAL.ghcClosed.file} x={500} y={230} w={920} h={600} at={-10} color="#2E5FB0" pos={REAL.ghcClosed.pos} />
    <MagnifierBox img={REAL.ghcClosed.file} crop={{ cx: 0.5, cy: 0.2, zoom: 2.4 }} x={680} y={380} w={560} h={250} tag="옛 간판 共和春" at={6} out={62} p={p} />
  </AbsoluteFill>
);

const DFilm: React.FC<{ p?: Partial<FilmStripP> }> = ({ p }) => (
  <AbsoluteFill>
    <Paper />
    <AbsoluteFill style={{ background: "radial-gradient(ellipse 60% 55% at 50% 0%, rgba(255,250,235,0.9), transparent 70%)" }} />
    <FilmStrip speed={12} startX={300} p={p} frames={[{ img: REAL.port.file, label: "1883", bw: true }, { img: B_IMG, label: "1900년대" }, { img: "img/s05_factory.jpg", label: "1948" }, { img: REAL.ghcClosed.file, label: "1980년대" }, { img: A_IMG, label: "오늘" }]} />
  </AbsoluteFill>
);

export const DEMOS: Demo[] = [
  AB({ name: "Scene — 휩 입장(가로 모션블러 슬라이드)", aDur: 6, bFrom: 6, dur: 45, enter: "whip" }),
  AB({ name: "Scene — 디졸브 입장(13f 크로스페이드)", aDur: 19, bFrom: 6, dur: 45, enter: "dissolve" }),
  AB({ name: "Scene — 커버 입장(오른쪽에서 밀고 들어옴)", aDur: 24, bFrom: 6, dur: 50, enter: "cover" }),
  AB({ name: "Scene — 줌인 입장(3배→1배 + 블러)", aDur: 6, bFrom: 6, dur: 45, enter: "zoomIn" }),
  AB({ name: "Scene — 휩 퇴장(A가 왼쪽으로 쓸려 나감)", aDur: 24, bFrom: 24, dur: 60, exit: "whip", enter: "whip" }),
  AB({ name: "Scene — 줌스루 퇴장(→줌인 연결)", aDur: 24, bFrom: 24, dur: 60, exit: "zoomThrough", exitOrigin: "49% 75%", enter: "zoomIn" }),
  { name: "Scene cam — 풀백 리빌(1.5→1.0)", dur: 90, C: DCamPull, schema: CamPullParams },
  { name: "Cover — 전체 화면 사진", dur: 60, C: DCover },
  { name: "HUD2 — 챕터 라벨 와이프·교체", dur: 100, C: DHud2, schema: HUD2Params },
  { name: "Subtitles — 종이 카드 자막", dur: 110, C: DSubs, schema: SubtitlesParams },
  { name: "YearTag — 연도 두루마리 입장·덮어쓰기 교체", dur: 110, C: DYearTag, schema: YearTagParams },
  { name: "ScrollLabel — 가로 두루마리 펼침", dur: 100, C: DScroll, schema: ScrollLabelParams },
  { name: "PhotoFrame — 컬러 테두리 사진 팝", dur: 60, C: DPhoto, schema: PhotoFrameParams },
  { name: "Sticker — 누끼 스티커 (왼쪽·아래·팝)", dur: 100, C: DSticker, schema: StickerParams },
  { name: "CircleImg — 원형 사진 팝", dur: 60, C: DCircle, schema: CircleImgParams },
  { name: "Stamp — 도장 꽝 + 깜빡임", dur: 75, C: DStamp, schema: StampParams },
  { name: "Starburst — 스타버스트 말풍선(고스트 에코)", dur: 70, C: DStarburst, schema: StarburstParams },
  { name: "Annot — 손글씨 주석 텍스트 팝", dur: 70, C: DAnnot, schema: AnnotParams },
  { name: "NameTag — 명찰 필 스트레치", dur: 60, C: DNameTag, schema: NameTagParams },
  { name: "QuoteBox — 인용 박스(블러 해제·따옴표 벌어짐)", dur: 70, C: DQuote, schema: QuoteBoxParams },
  { name: "Sparkles — 4각 금별 반짝이", dur: 90, C: DSparkles, schema: SparklesParams },
  { name: "GlowPulse — 원형 글로우 + 링 펄스", dur: 80, C: DGlow, schema: GlowPulseParams },
  { name: "WaveBg — 청해파 물결 배경", dur: 60, C: DWave, schema: WaveBgParams },
  { name: "CloudBg — 구름 문양 배경", dur: 60, C: DCloud, schema: CloudBgParams },
  { name: "PaperOverlay — 흑백 사료 옛 종이 질감", dur: 60, C: DPaper, schema: PaperOverlayParams },
  { name: "Grain — 필름 그레인(시연용 과장)", dur: 60, C: DGrain, schema: GrainParams },
  { name: "QSilhouette — 물음표 실루엣 팝", dur: 60, C: DQSil, schema: QSilhouetteParams },
  { name: "LayeredCover — 레이어 씬 까딱·눈깜빡임", dur: 150, C: DLayered, schema: LayeredCoverParams },
  { name: "Steam — 김 모락모락", dur: 100, C: DSteam, schema: SteamParams },
  { name: "Onoma — 의성어 효과 텍스트", dur: 80, C: DOnoma, schema: OnomaParams },
  { name: "FlickerLeak — 컬러 플리커 라이트릭 전환", dur: 40, C: DFlicker, schema: FlickerLeakParams },
  { name: "YellowBurst — 노란 번 전환", dur: 40, C: DYellow, schema: YellowBurstParams },
  { name: "SmokeWipe — 만화 연기 와이프 전환", dur: 52, C: DSmoke, schema: SmokeWipeParams },
  { name: "Confetti — 색종이 버스트", dur: 80, C: DConfetti, schema: ConfettiParams },
  { name: "FlipTurn — 뒷모습→앞모습 뒤집기", dur: 70, C: DFlip, schema: FlipTurnParams },
  { name: "Spotlight — 주인공 스포트라이트 딤", dur: 80, C: DSpot, schema: SpotlightParams },
  { name: "ArrowTag — 이름표 + 곡선 화살표", dur: 60, C: DArrow, schema: ArrowTagParams },
  { name: "IconPop — 재료 아이콘 팝 → 빨려 들어감", dur: 80, C: DIcon, schema: IconPopParams },
  { name: "EchoTitle — 에코 줌 타이틀", dur: 60, C: DEcho, schema: EchoTitleParams },
  { name: "DashCircle — 점선 원 하이라이트", dur: 50, C: DDash, schema: DashCircleParams },
  { name: "SweatDrop — 땀방울 루프", dur: 75, C: DSweat, schema: SweatDropParams },
  { name: "MapRoute — 지도 항로 드로우", dur: 80, C: DMap, schema: MapRouteParams },
  { name: "TypeCard — 타자 인터스티셜", dur: 60, C: DType, schema: TypeCardParams },
  { name: "GlitchOverlay — 글리치 컷 전환", dur: 36, C: DGlitch, schema: GlitchOverlayParams },
  { name: "AvatarPop — 아바타 순차 팝", dur: 70, C: DAvatar, schema: AvatarPopParams },
  { name: "TermCard — 용어 설명 카드 펼침", dur: 90, C: DTerm, schema: TermCardParams },
  { name: "ElbowCallout — 꺾은선 콜아웃", dur: 50, C: DElbow, schema: ElbowCalloutParams },
  { name: "MagnifierBox — 돋보기 확대 박스", dur: 75, C: DMagnifier, schema: MagnifierBoxParams },
  { name: "FilmStrip — 필름스트립 리캡", dur: 120, C: DFilm, schema: FilmStripParams },
];

// ── Main.tsx 전용 부품 + 구 HUD·흔들림 (도감 미리보기용) ─────────────────────
import { ChapterCard, StingCard, Signboard, Credit, EndCard } from "../Main";
import { HUD, useShake as useShakeFx, Cover as CoverFx } from "../fx";
const DSign: React.FC = () => <AbsoluteFill><CoverFx img="img/s03_restaurant.jpg" /><Signboard flipAt={20} /></AbsoluteFill>;
const DChapter: React.FC = () => <ChapterCard n={2} title="산동회관과 공화춘" />;
const DSting: React.FC = () => <StingCard dur={51} />;
const DEnd: React.FC = () => <EndCard dur={126} />;
const DCredit: React.FC = () => <AbsoluteFill><CoverFx img="img/s05_factory.jpg" /><Credit text="우정사업본부 / CC BY 2.0 KR" />
  <div style={{ position: "absolute", right: 42, top: 1022, fontFamily: "NeoEb", fontSize: 24, color: "#fff", textShadow: "0 2px 4px rgba(0,0,0,0.75)" }}>내용출처 : 한국민족문화대백과사전 · 짜장면박물관</div></AbsoluteFill>;
const DHud: React.FC<{ p?: Partial<HUDP> }> = ({ p }) => { const f = useCurrentFrame(); const a = f < 45 ? 0 : 1;
  return <AbsoluteFill><CoverFx img="img/s02_dock.jpg" /><HUD chapters={["인천항의 작장면", "산동회관과 공화춘", "춘장, 그리고 지금"]} active={a} changeAt={45} p={p} /></AbsoluteFill>; };
const DShake: React.FC<{ p?: Partial<ShakeP> }> = ({ p }) => { const t = useShakeFx(20, p?.amp ?? 16, p?.len ?? 12, p?.hold ?? 1); return <AbsoluteFill style={{ transform: t }}><CoverFx img="img/s05_factory.jpg" /></AbsoluteFill>; };
DEMOS.push(
  { name: "Signboard — 간판 Y축 카드 플립(山東會館→共和春)", dur: 60, C: DSign },
  { name: "ChapterCard — 챕터 카드", dur: 48, C: DChapter },
  { name: "StingCard — 로고 스팅", dur: 51, C: DSting },
  { name: "EndCard — 엔드카드(자료 출처·검정 페이드)", dur: 126, C: DEnd },
  { name: "Credit — 이미지 출처·내용출처 표기", dur: 45, C: DCredit },
  { name: "HUD — 구 챕터 진행바(필 이동)", dur: 80, C: DHud, schema: HUDParams },
  { name: "useShake — 임팩트 화면 흔들림", dur: 45, C: DShake, schema: ShakeParams },
);
export const GALLERY_DUR = Math.max(30, DEMOS.reduce((a, d) => a + d.dur, 0));
export const Gallery = runGallery(DEMOS);
