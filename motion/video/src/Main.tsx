import React from "react";
import { AbsoluteFill, Audio, Img, Sequence, staticFile, useCurrentFrame, interpolate, Easing } from "remotion";
import TL from "./timeline.json";
import {
  FPS, Scene, Cover, HUD, Subtitles, YearTag, ScrollLabel, PhotoFrame, Sticker, CircleImg, Stamp,
  Starburst, Annot, NameTag, QuoteBox, Rays, Sparkles, WaveBg, CloudBg, PaperOverlay, Grain, QSilhouette,
  lerp, popSpring, useShake, GLOW,
} from "./fx";
import REAL from "./real.json";
import LAYERS from "./layers.json";
import { QUART_OUT, HUD2 } from "./fx";
import { TypeCard, GlitchOverlay, AvatarPop, TermCard, ElbowCallout, MagnifierBox, FilmStrip } from "./fx";
import { LayeredCover, LayerSpec, Steam, Onoma, SmokeWipe, YellowBurst, FlickerLeak, Confetti, GlowPulse, FlipTurn, Spotlight, ArrowTag, IconPop, IconCaramel, IconSugar, EchoTitle, DashCircle, SweatDrop, MapRoute } from "./fx";
const LY = LAYERS as Record<string, LayerSpec>;

type Seg = { t0: number; dur: number; text: string; cs: number[] };
const SEGS = TL.segs as Record<string, Seg>;
const F = (s: number) => Math.round(s * FPS);
/** 나레이션 단어가 발화되는 전역 초 */
const cue = (id: string, needle?: string, nth = 0): number => {
  const s = SEGS[id];
  if (!needle) return s.t0;
  let i = -1;
  for (let k = 0; k <= nth; k++) i = s.text.indexOf(needle, i + 1);
  if (i < 0) throw new Error(`cue miss: ${id} / ${needle}`);
  return s.t0 + s.cs[i];
};
const end = (id: string) => SEGS[id].t0 + SEGS[id].dur;
const blk = (id: string) => TL.blocks.find((b) => b.id === id)!;

const CH = ["인천항의 작장면", "산동회관과 공화춘", "춘장, 그리고 지금"];
// 리뉴얼 HUD 라벨: 챕터의 대표 워드마크(빨간 세리프)
const CH_MARK = ["仁川港 인천항", "共和春 공화춘", "春醬 춘장"];

// 씬 구간(전역 초). 레퍼런스처럼 대부분 하드컷으로 맞붙이고, 디졸브만 13f 겹친다.
// 연기·노란 번·플리커 전환은 오버레이가 화면을 덮은 순간(컷 프레임)에 씬을 바꾼다.
const DIS = 13 / 30;
const T = {
  hook1: [0, cue("h2")],
  hook2: [cue("h2"), cue("h3")],
  but: [cue("h3"), cue("h3", "이")],
  hook3: [cue("h3", "이"), blk("sting").t0],
  sting: [blk("sting").t0, blk("card1").t0],
  card1: [blk("card1").t0, blk("card1").t1],
  port: [blk("card1").t1, cue("c1a", "바다")],
  map: [cue("c1a", "바다"), cue("c1b") + DIS],
  dock: [cue("c1b"), blk("card2").t0],
  card2: [blk("card2").t0, blk("card2").t1],
  shop: [blk("card2").t1, blk("card3").t0],
  card3: [blk("card3").t0, blk("card3").t1],
  factory: [blk("card3").t1, cue("c3b", "지금")],
  bowl: [cue("c3b", "지금"), cue("c5")],
  museum: [cue("c5"), cue("c4") - 0.6],
  crowd: [cue("c4") - 0.6, cue("c4", "짜장면")],
  film: [cue("c4", "짜장면"), blk("end").t0],
  end: [blk("end").t0, TL.total],
} as const;
// 전환 오버레이 시작 = 컷 시점 - 컷 프레임(연기 7f · 노란 번 7f · 플리커 14f)
const TR = { smoke: T.bowl[0] - 7 / 30, yellow: T.museum[0] - 7 / 30, flicker: T.crowd[0] - 14 / 30 };

const Seq: React.FC<{ k: keyof typeof T; children: (at: (s: number) => number, dur: number) => React.ReactNode }> = ({ k, children }) => {
  const [a, b] = T[k];
  const from = F(a), dur = Math.max(1, F(b) - F(a));
  return <Sequence from={from} durationInFrames={dur} name={k}>{children((s) => F(s) - from, dur)}</Sequence>;
};

const Sfx: React.FC<{ at: number; src: string; vol?: number }> = ({ at, src, vol = 0.5 }) => (
  <Sequence from={F(at)} durationInFrames={F(4)}><Audio src={staticFile(`audio/${src}`)} volume={vol} /></Sequence>
);

export const ChapterCard: React.FC<{ n: number; title: string }> = ({ n, title }) => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: "#F7F5F0" }}>
      <div style={{ position: "absolute", top: 490, width: "100%", textAlign: "center", fontFamily: "NeoHv", fontSize: 76, color: "#1a1a1a" }}>{n}. {title}</div>
    </AbsoluteFill>
  );
};

export const StingCard: React.FC<{ dur: number }> = ({ dur }) => {
  const f = useCurrentFrame();
  const k = lerp(f, 0, 10, 0, 1, Easing.out(Easing.cubic));
  // HUD 로고 자리(26,22,198x118)에서 가운데 큰 로고(455,112,1005x588)로 날아온다
  const x = 26 + (455 - 26) * k, y = 22 + (112 - 22) * k, w = 198 + (1005 - 198) * k, h = 118 + (588 - 118) * k;
  const sub = popSpring(f, 12), like = popSpring(f, 18);
  return (
    <AbsoluteFill style={{ background: "#F9F7F3" }}>
      <Img src={staticFile("ui/sting_logo.png")} style={{ position: "absolute", left: x, top: y, width: w, height: h }} />
      <Img src={staticFile("ui/sting_sub.png")} style={{ position: "absolute", left: 395, top: 832, width: 440, height: 173, transform: `scale(${sub})` }} />
      <Img src={staticFile("ui/sting_like.png")} style={{ position: "absolute", left: 1040, top: 820, width: 520, height: 190, transform: `scale(${like})`, mixBlendMode: "multiply" }} />
    </AbsoluteFill>
  );
};

// 산동회관 → 공화춘 간판: Y축 3D 카드 플립 [ref 792s] — 0→90° (4f) 에서 글자 교체, -90→0° (5f)
export const Signboard: React.FC<{ flipAt: number }> = ({ flipAt }) => {
  const f = useCurrentFrame();
  const ry = f < flipAt ? 0 : f < flipAt + 4 ? lerp(f, flipAt, flipAt + 4, 0, 90, Easing.in(Easing.quad)) : lerp(f, flipAt + 4, flipAt + 9, -90, 0, Easing.out(Easing.back(1.4)));
  const text = f < flipAt + 4 ? "山東會館" : "共和春";
  const glow = f >= flipAt + 4 ? lerp(f, flipAt + 9, flipAt + 24, 1, 0.35) : 0;
  return (
    <div style={{ position: "absolute", left: 745, top: 432, width: 425, height: 104, perspective: 1200 }}>
      <div style={{ position: "absolute", inset: f >= flipAt ? -14 : 0, display: "flex", alignItems: "center", justifyContent: "center", transform: `rotateY(${ry}deg)`, background: f >= flipAt ? "#2B2B2B" : "transparent", border: f >= flipAt ? "5px solid #D4A537" : "none", boxShadow: f >= flipAt + 4 ? `0 0 ${30 * glow}px rgba(255,220,120,${glow})` : undefined }}>
        <div style={{ fontFamily: "'Songti SC','STSong',serif", fontWeight: 900, fontSize: 78, letterSpacing: 14, color: "#E8BE4A", textShadow: `0 0 ${24 * glow}px rgba(255,220,120,${glow})` }}>{text}</div>
      </div>
    </div>
  );
};

export const Main: React.FC = () => {
  const f = useCurrentFrame();
  const t = f / FPS;
  const inCh = (i: number) => t >= [blk("card1").t0, blk("card2").t0, blk("card3").t0][i];
  const active = inCh(2) ? 2 : inCh(1) ? 1 : inCh(0) ? 0 : -1;
  const changeAt = F([blk("card1").t0, blk("card2").t0, blk("card3").t0][Math.max(0, active)]);
  const inSting = t >= T.sting[0] && t < T.sting[1];
  const bgmVol = (fr: number) => {
    const tt = fr / FPS;
    const v = 0.11;
    return interpolate(tt, [0, 1, TL.total - 2.5, TL.total], [0, v, v, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  };

  return (
    <AbsoluteFill style={{ background: "#000" }}>
      {/* ── 훅 1: 졸업식 가족 ───────────────────────────── */}
      <Seq k="hook1">{(at, dur) => (
        <Scene id="hook1" dur={dur} exit="zoomThrough" exitOrigin="49% 75%" cam={{ s0: 1.5, s1: 1.0, y0: 255, y1: 0, moveF: 55 }} overlay={<><Annot text="졸업식 날" x={260} y={230} at={at(cue("h1a"))} size={80} rot={-6} /><Annot text="이삿날" x={760} y={150} at={at(cue("h1b"))} size={80} rot={3} /><Annot text="비 오는 날" x={1240} y={230} at={at(cue("h1c", "비"))} size={80} rot={-4} /></>}>
          <LayeredCover spec={LY["s01_family"]} dur={dur} />
          <Steam x={475} y={760} s={1.3} /><Steam x={1425} y={765} s={1.3} />
          <Onoma text="후루룩~" x={1010} y={250} size={52} at={at(cue("h1a")) + 8} life={36} />
        </Scene>)}
      </Seq>

      {/* ── 훅 2: 짜장면 등장 ──────────────────────────── */}
      <Seq k="hook2">{(at, dur) => (
        <Scene id="hook2" dur={dur} enter="zoomIn">
          <CloudBg />
          <GlowPulse x={960} y={560} at={at(cue("h2", "짜장면")) - 6} r={560} />
          <Sticker img="img/s05_bowl.png" x={610} y={240} w={700} at={0} from="none" />
          <Sparkles at={at(cue("h2", "짜장면"))} pts={[[560, 330, 90], [1360, 290, 70], [1300, 760, 100], [620, 720, 60], [960, 200, 50]]} />
          <Starburst text={"짜장면!"} x={1480} y={330} w={440} h={300} at={at(cue("h2", "짜장면")) + 4} size={72} />
        </Scene>)}
      </Seq>

      <Seq k="but">{(at, dur) => <TypeCard text="그런데" dur={dur} />}</Seq>

      {/* ── 훅 3: 물음표 실루엣 ─────────────────────────── */}
      <Seq k="hook3">{(at, dur) => (
        <Scene id="hook3" dur={dur}>
          <WaveBg />
          <AbsoluteFill style={{ background: "radial-gradient(ellipse 38% 60% at 50% 30%, rgba(255,250,230,0.22), transparent 70%)" }} />
          <QSilhouette x={960} y={900} at={at(cue("h3", "누가"))} s={1.35} />
          <Sticker img="img/s05_bowl.png" x={760} y={640} w={400} at={at(cue("h3", "짜장면")) - 2} from="bottom" />
        </Scene>)}
      </Seq>

      {/* ── 스팅: 세모지 로고 ───────────────────────────── */}
      <Seq k="sting">{(at, dur) => <StingCard dur={dur} />}</Seq>

      {/* ── 챕터 1 ─────────────────────────────────────── */}
      <Seq k="card1">{() => <ChapterCard n={1} title={CH[0]} />}</Seq>
      <Seq k="port">{(at, dur) => (
        <Scene id="port" dur={dur} overlay={<><Credit text={REAL.port.credit} /><YearTag text="1883년" at={at(cue("c1a", "1883"))} /></>}>
          <Cover img={REAL.port.file} style={{ filter: "grayscale(1) sepia(0.2) contrast(1.9) brightness(0.92)", objectPosition: REAL.port.pos }} />
          <PaperOverlay strength={0.55} />
          <Annot text="제물포(인천항) 개항" x={130} y={330} at={at(cue("c1a", "인천항")) + 4} size={62} />
        </Scene>)}
      </Seq>
      <Seq k="dock">{(at, dur) => (
        <Scene id="dock" dur={dur} enter="dissolve" overlay={<><Badge /><Credit text={REAL.zhajiang.credit} /></>}>
          <LayeredCover spec={LY["s02_dock"]} dur={dur} />
          <Onoma text="후루룩" x={560} y={250} at={at(cue("c1b")) + 10} life={34} size={52} />
          <Onoma text="꿀꺽꿀꺽" x={1400} y={300} at={at(cue("c1b", "음식")) } life={34} size={48} rot={6} />
          <ScrollLabel text="작장면" sub="炸醬麵" x={960} y={235} w={470} at={at(cue("c1b", "작장면")) - 3} color="#C9562C" />
          <TermCard term="작장면(炸醬麵)" def="장(醬)을 볶아(炸) 국수(麵)에 비벼 먹는 산둥 요리" at={at(cue("c1b", "볶은")) - 2} />
          <CircleImg img={REAL.zhajiang.file} x={1600} y={560} d={330} at={at(cue("c1b", "볶은")) - 4} pos={REAL.zhajiang.pos} />
          <NameTag text="산둥식 작장면(오늘날)" x={1420} y={330} at={at(cue("c1b", "볶은")) + 2} size={32} />
        </Scene>)}
      </Seq>

      <Seq k="map">{(at, dur) => (
        <Scene id="map" dur={dur} enter="cover">
          <MapRoute at={0} routeAt={at(cue("c1a", "산둥")) - 4} labelsAt={6} />
          <AvatarPop at={at(cue("c1a", "몰려")) - 4} pts={[[1470, 580], [1545, 540], [1500, 660], [1575, 620], [1455, 495], [1540, 470]]} />
        </Scene>)}
      </Seq>

      {/* ── 챕터 2 ─────────────────────────────────────── */}
      <Seq k="card2">{() => <ChapterCard n={2} title={CH[1]} />}</Seq>
      <Seq k="shop">{(at, dur) => (
        <Scene id="shop" dur={dur} overlay={<><Badge /><YearTag text="1900년대 초" at={at(cue("c2a"))} out={at(cue("c2b", "공화국")) + 16} /><YearTag text="1912년 무렵" at={at(cue("c2b", "공화국"))} />{f - F(T.shop[0]) > at(cue("c2b", "공화춘")) + 6 && <Credit text={REAL.ghcNow.credit} />}</>}>
          <Cover img="img/s03_restaurant.jpg" />
          <Signboard flipAt={at(cue("c2b", "이름을"))} />
          <GlowPulse x={958} y={483} at={at(cue("c2b", "공화춘")) - 2} r={420} rings={1} />
          <FlipTurn back="img/s03_woo_back.png" front="img/s03_woo.png" x={70} y={380} w={430} at={at(cue("c2a", "화교")) - 18} flipAt={at(cue("c2a", "우희광")) - 4} out={at(cue("c2b", "공화춘")) - 4} />
          <NameTag text="화교 우희광" x={130} y={330} at={at(cue("c2a", "우희광")) + 4} out={at(cue("c2b", "공화춘")) - 4} />
          <Annot text="중화민국 수립!" x={1270} y={640} at={at(cue("c2b", "공화국")) + 4} size={60} rot={-5} />
          <ScrollLabel text="공화춘" sub="共和春" x={760} y={770} w={440} at={at(cue("c2b", "공화춘"))} color="#2E7D4F" size={78} />
          <PhotoFrame img={REAL.ghcNow.file} x={1150} y={560} w={560} h={340} at={at(cue("c2b", "공화춘")) + 6} color="#2E7D4F" pos={REAL.ghcNow.pos} rot={3} />
          <Sparkles at={at(cue("c2b", "공화춘")) + 3} pts={[[560, 380, 80], [1290, 330, 90], [500, 700, 60], [1080, 520, 70]]} />
        </Scene>)}
      </Seq>

      {/* ── 챕터 3 ─────────────────────────────────────── */}
      <Seq k="card3">{() => <ChapterCard n={3} title={CH[2]} />}</Seq>
      <Seq k="factory">{(at, dur) => (
        <Scene id="factory" dur={dur} cam={{ s0: 1.6, s1: 1.0, x0: -64, x1: 0, y0: 32, y1: 0, moveF: 60 }} overlay={<><Badge /><YearTag text="1948년" at={at(cue("c3a", "1948"))} /><Credit text={REAL.chunjang.credit} /></>}>
          <LayeredCover spec={LY["s05_factory"]} dur={dur} />
          <Steam x={1020} y={650} s={1.4} n={4} /><Steam x={1480} y={660} s={1.2} />
          <Onoma text="휘휘~" x={330} y={520} at={at(cue("c3a", "춘장")) + 4} life={40} size={54} />
          <NameTag text="화교 왕송산" x={330} y={330} at={at(cue("c3a", "왕송산"))} />
          <CircleImg img={REAL.chunjang.file} x={1700} y={710} d={290} at={at(cue("c3a", "춘장"))} pos={REAL.chunjang.pos} />
          <ElbowCallout from={[1555, 720]} mid={[1460, 720]} to={[1460, 845]} text="실제 춘장" at={at(cue("c3a", "춘장")) + 8} />
          <IconPop icon={<IconCaramel />} label="캐러멜" x={1560} y={225} at={at(cue("c3b", "캐러멜")) - 2} suckAt={at(cue("c3b", "나오면서"))} to={[1150, 820]} idx={0} />
          <IconPop icon={<IconSugar />} label="단맛" x={1770} y={330} at={at(cue("c3b", "달콤한")) - 2} suckAt={at(cue("c3b", "나오면서"))} to={[1150, 820]} idx={1} />
          <SweatDrop x={870} y={100} at={at(cue("c3a", "춘장"))} s={1.3} />
        </Scene>)}
      </Seq>
      <Seq k="bowl">{(at, dur) => (
        <Scene id="bowl" dur={dur} overlay={<><Credit text={REAL.jjajang.credit} /></>}>
          <CloudBg base="#D9892B" line="#E39A3E" />
          <GlowPulse x={920} y={560} at={0} r={600} rings={0} />
          <PhotoFrame img={REAL.jjajang.file} x={1230} y={260} w={560} h={400} at={at(cue("c3b", "아는"))} color="#B3212B" pos={REAL.jjajang.pos} rot={4} />
          <Sticker img="img/s05_chunjang.png" x={150} y={360} w={520} at={3} from="left" />
          <Sticker img="img/s05_bowl.png" x={600} y={300} w={640} at={at(cue("c3b", "짜장면")) - 3} from="pop" />
          <Annot text="지금의 그 맛!" x={660} y={170} at={at(cue("c3b", "자리")) - 4} size={80} rot={-4} />
        </Scene>)}
      </Seq>
      <Seq k="museum">{(at, dur) => (
        <Scene id="museum" dur={dur} overlay={<><YearTag text="1980년대" at={at(cue("c5", "1980"))} /><Credit text={"Lawinc82 · Jjw · 이강철 / Wikimedia Commons (CC BY-SA)"} /></>}>
          <Cover img={REAL.chinatown.file} style={{ filter: "blur(7px) brightness(0.42) saturate(0.8)", transform: "scale(1.06)" }} />
          <div style={{ position: "absolute", top: 165, width: "100%", textAlign: "center", fontFamily: "NeoHv", fontSize: 58, color: "#fff", textShadow: "0 3px 8px rgba(0,0,0,0.6)", clipPath: `inset(0 ${100 - lerp(f - F(T.museum[0]), 6, 16, 0, 100)}% 0 0)` }}>옛 공화춘 건물</div>
          <PhotoFrame img={REAL.ghcClosed.file} x={170} y={270} w={760} h={520} at={at(cue("c5")) + 4} color="#2E5FB0" pos={REAL.ghcClosed.pos} />
          <MagnifierBox img={REAL.ghcClosed.file} crop={{ cx: 0.5, cy: 0.2, zoom: 2.4 }} x={560} y={330} w={560} h={250} tag="옛 간판 共和春" at={at(cue("c5")) + 12} out={at(cue("c5", "닫았")) - 3} />
          <Stamp text="폐업" x={550} y={560} at={at(cue("c5", "닫았"))} size={130} />
          <PhotoFrame img={REAL.museum.file} x={990} y={270} w={760} h={520} at={at(cue("c5", "짜장면박물관")) - 2} color="#D98A1F" pos={REAL.museum.pos} />
          <ScrollLabel text="짜장면박물관" x={1370} y={830} w={520} at={at(cue("c5", "짜장면박물관"))} color="#D98A1F" size={64} />
        </Scene>)}
      </Seq>

      {/* ── 클로징 ─────────────────────────────────────── */}
      <Seq k="crowd">{(at, dur) => (
        <Scene id="crowd" dur={dur} overlay={<><Confetti at={at(cue("c4", "국민"))} y={1000} /><QuoteBox text={"부두의 한 끼에서\n국민 음식으로"} x={960} y={650} w={900} at={at(cue("c4", "부두")) + 6} /></>}>
          <LayeredCover spec={LY["s06_crowd"]} dur={dur} />
          <Spotlight rect={[20, 120, 540, 900]} at={6} out={at(cue("c4", "국민")) - 2} />
          <ArrowTag text="1900년대 부두 노동자" x={620} y={170} at={10} out={at(cue("c4", "국민")) - 2} path="M640,245 Q520,215 420,262" head={[420, 262, 165]} size={46} />
        </Scene>)}
      </Seq>

      <Seq k="film">{(at, dur) => (
        <Scene id="film" dur={dur} overlay={<><Starburst text={"백 년의\n이야기!"} x={1560} y={210} w={380} h={290} at={at(cue("c4", "백 년")) - 2} size={56} /></>}>
          <AbsoluteFill style={{ background: "#EDE3D0" }} />
          <PaperOverlay strength={0.4} />
          <AbsoluteFill style={{ background: "radial-gradient(ellipse 60% 55% at 50% 0%, rgba(255,250,235,0.9), transparent 70%)" }} />
          <FilmStrip speed={12} startX={120} frames={[{ img: REAL.port.file, label: "1883", bw: true }, { img: "img/s03_restaurant.jpg", label: "1900년대" }, { img: "img/s05_factory.jpg", label: "1948" }, { img: REAL.ghcClosed.file, label: "1980년대" }, { img: "img/s01_family.jpg", label: "오늘" }]} />
        </Scene>)}
      </Seq>

      {/* ── 엔드카드 [ref 857.6s]: 세이지 그린 + 종이 질감, 좌측 카드, 우측 55% 비움(엔드스크린), HUD·자막 없음 ── */}
      <Seq k="end">{(at, dur) => <EndCard dur={dur} />}</Seq>

      {/* ── HUD·자막·질감 ──────────────────────────────── */}
      {!inSting && t < T.end[0] && <HUD2 label={active >= 0 ? CH_MARK[active] : undefined} changeAt={changeAt} />}
      {!inSting && t >= T.card1[1] && t < T.end[0] && <div style={{ position: "absolute", right: 42, top: 1022, fontFamily: "NeoEb", fontSize: 24, color: "#fff", textShadow: "0 2px 4px rgba(0,0,0,0.75)" }}>내용출처 : 한국민족문화대백과사전 · 짜장면박물관</div>}
      <Subtitles subs={TL.subs} />
      <Grain opacity={0.06} />
      <GlitchOverlay at={F(T.hook3[0]) - 3} /><SmokeWipe at={F(TR.smoke)} /><YellowBurst at={F(TR.yellow)} /><FlickerLeak at={F(TR.flicker)} />

      {/* ── 오디오 ─────────────────────────────────────── */}
      <Audio src={staticFile("audio/bgm.mp3")} volume={bgmVol} />
      {Object.entries(SEGS).map(([id, s]) => (
        <Sequence key={id} from={F(s.t0)} durationInFrames={F(s.dur) + 3}><Audio src={staticFile(`audio/vo/${id}.mp3`)} volume={1} /></Sequence>
      ))}
      <Sfx at={cue("h1a")} src="pen.wav" vol={0.25} />
      <Sfx at={cue("h2", "짜장면")} src="sparkle.wav" vol={0.35} />
      <Sfx at={cue("h3", "누가")} src="boing.wav" vol={0.3} />
      <Sfx at={T.sting[0] + 0.4} src="click.wav" vol={0.5} />
      {[blk("card1").t0, blk("card2").t0, blk("card3").t0].map((x) => <Sfx key={x} at={x} src="shutter.wav" vol={0.18} />)}
      <Sfx at={T.but[0]} src="pen.wav" vol={0.2} /><Sfx at={T.hook3[0] - 0.1} src="click.wav" vol={0.4} /><Sfx at={TR.smoke} src="whoosh.wav" vol={0.25} /><Sfx at={TR.yellow} src="sparkle.wav" vol={0.25} /><Sfx at={TR.flicker} src="sparkle.wav" vol={0.3} /><Sfx at={cue("c4", "국민")} src="pop.wav" vol={0.35} />
      <Sfx at={cue("c1b", "작장면")} src="pop.wav" vol={0.4} />
      <Sfx at={cue("c2b", "이름을")} src="whoosh.wav" vol={0.3} />
      <Sfx at={cue("c2b", "공화춘")} src="sparkle.wav" vol={0.35} />
      <Sfx at={cue("c5", "닫았")} src="punch.wav" vol={0.55} />
      <Sfx at={cue("c4", "백 년")} src="pop.wav" vol={0.4} />
      <Sfx at={T.map[0]} src="whoosh.wav" vol={0.3} /><Sfx at={cue("c1a", "산둥") - 0.1} src="pen.wav" vol={0.2} />
      <Sfx at={cue("c2a", "우희광") - 0.15} src="whoosh.wav" vol={0.2} />
      <Sfx at={cue("c3b", "캐러멜")} src="pop.wav" vol={0.35} /><Sfx at={cue("c3b", "달콤한")} src="pop.wav" vol={0.35} /><Sfx at={cue("c3b", "나오면서")} src="whoosh.wav" vol={0.3} />
      <Sfx at={T.end[0]} src="sparkle.wav" vol={0.25} />
    </AbsoluteFill>
  );
};

export const Credit: React.FC<{ text?: string }> = ({ text }) => text ? (
  <div style={{ position: "absolute", left: 118, top: 1026, fontFamily: "NeoEb", fontSize: 17, color: "rgba(255,255,255,0.95)", textShadow: "0 1px 3px rgba(0,0,0,0.85)" }}>이미지 출처 : {text}</div>
) : null;

const CREDITS = [
  "1890년 제물포 — Wikimedia Commons (퍼블릭 도메인)",
  "공화춘(2007) — Lawinc82 · CC BY-SA 3.0",
  "짜장면박물관 — Mobius6 · Jjw · CC BY-SA 4.0",
  "인천 차이나타운 — 이강철 · CC BY-SA 4.0",
  "짜장면 — KFoodaddict · CC BY 2.0",
  "춘장 — 우정사업본부 · CC BY 2.0 KR",
  "산둥식 작장면 — Battlesnake1 · CC0",
  "인물·장면 일러스트 — AI 재현",
];
export const EndCard: React.FC<{ dur: number }> = ({ dur }) => {
  const f = useCurrentFrame();
  const black = lerp(f, dur - 24, dur, 0, 1);
  return (
    <AbsoluteFill style={{ background: "#A9B7A1" }}>
      <PaperOverlay strength={0.45} />
      <div style={{ position: "absolute", left: 90, top: 110, width: 780, height: 800, background: "#FBF6EA", borderRadius: 24, boxShadow: "0 14px 30px rgba(0,0,0,0.25)", transform: `translateY(${lerp(f, 0, 14, 40, 0, QUART_OUT)}px)`, opacity: lerp(f, 0, 8, 0, 1) }}>
        <div style={{ position: "absolute", left: 30, top: 24, fontSize: 40, color: "#C98A9A" }}>✿</div>
        <div style={{ position: "absolute", right: 34, bottom: 20, fontSize: 40, color: "#C98A9A" }}>✿</div>
        <div style={{ position: "absolute", top: 250, left: 0, right: 0, textAlign: "center", fontFamily: "Yeonsung, 'Songti SC', serif", fontSize: 34, color: "#5d6b56", opacity: lerp(f, 22, 30, 0, 1) }}>자료 출처</div>
        {CREDITS.map((c, i) => (
          <div key={c} style={{ position: "absolute", top: 310 + i * 52, left: 0, right: 0, textAlign: "center", fontFamily: "NeoEb", fontSize: 25, color: "#2b2b2b", opacity: lerp(f, 26 + i * 3, 32 + i * 3, 0, 1) }}>{c}</div>
        ))}
      </div>
      <EchoTitle text="세상의 모든 지식" x={480} y={170} at={4} size={86} color="#4F5E48" />
      <AbsoluteFill style={{ background: "#000", opacity: black }} />
    </AbsoluteFill>
  );
};

const Badge: React.FC = () => (
  <div style={{ position: "absolute", right: 36, top: 150, fontFamily: "NeoEb", fontSize: 22, color: "#fff", background: "rgba(0,0,0,0.5)", padding: "5px 14px", borderRadius: 20 }}>일러스트 재현</div>
);
