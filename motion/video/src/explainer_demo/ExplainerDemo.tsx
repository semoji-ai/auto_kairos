// 「후추 한 알이 금값이던 이유」 — 설명형 편집 레퍼런스(ref_explainer_editorial) 스타일 1분 테스트 (ref_explainer_editorial/analysis.md §14 A안)
import React from "react";
import { AbsoluteFill, Audio, Easing, Img, Sequence, staticFile, useCurrentFrame } from "remotion";
import "../fx"; // 폰트 로드(NeoEb·NeoHv·Jalnan·Dohyeon) 부수효과
import TL from "./timeline.json";
import { FPS, PAL, img, lin } from "./theme";
import { PirSubtitles, Parchment, SidePropPop, IconScatter, WipeBubble, PirStamp, FocusDim, CaricatureSlide, TornPhoto, BigWord, DimUnderlay } from "./kit";
import { EngravedGlobe } from "./Globe";
import { TornPaperWipe } from "./TornWipe";
import { LogoSting } from "./LogoSting";
import { OpsMap, BrushArrow, BrushLabel } from "./OpsMap";
import { SilhouetteParallax } from "./Silhouette";
import { IconBarChart } from "./Chart";
import { TalkingMascot } from "./Mascot";
import MAMLUK from "../data/mamluk_approx.json";
import type { CameraState } from "../map/cameraInterpolation";

export const EXPLAINER_DEMO_DUR = Math.round(TL.total * FPS);

// ── 장면 경계(프레임) — timeline.json 기준 ─────────────────────────────────────────────────────────
const S = {
  globe: 0, sting: 347, sil: 440, map: 590, chart: 838, skit: 1016, gama: 1254, photo: 1429, words: 1560, outro: 1662, end: EXPLAINER_DEMO_DUR,
};
const DISS = 15; // 디졸브 12f(24fps)=15f

/** 디졸브 입장 래퍼 */
const Fade: React.FC<{ len?: number; children: React.ReactNode; outAt?: number; outLen?: number }> = ({ len = DISS, children, outAt, outLen = DISS }) => {
  const f = useCurrentFrame();
  const o = lin(f, 0, len, 0, 1) * (outAt !== undefined ? lin(f, outAt, outAt + outLen, 1, 0) : 1);
  return <AbsoluteFill style={{ opacity: o }}>{children}</AbsoluteFill>;
};
/** 장면 기본 카메라: scale 1.00→1.03 (4~6s linear) */
const Drift: React.FC<{ dur: number; to?: number; children: React.ReactNode }> = ({ dur, to = 1.03, children }) => {
  const f = useCurrentFrame();
  return <AbsoluteFill style={{ transform: `scale(${lin(f, 0, dur, 1, to)})` }}>{children}</AbsoluteFill>;
};

// ── 1+2. 지구본(말라바르) + 히트맵·산포·좌우 소품 ────────────────────────────────────────────────────
const MALABAR: [number, number] = [76, 12];
// 서고츠산맥 해안(말라바르~카나라) 따라 흩뿌림: 경위도 + 화면 지터(px)
const PEPPER_PTS: [number, number, number, number][] = [
  [76.3, 9.6, -30, 20], [75.8, 11.2, -95, 0], [75.2, 12.8, -20, -40], [74.7, 14.4, -110, -30], [74.2, 16.0, -30, -70], [73.6, 17.8, -120, -60],
  [76.9, 8.4, 40, 50], [77.0, 10.8, 90, 10], [76.4, 12.6, 60, -40], [75.5, 15.2, 50, -80], [74.9, 17.0, 20, -120], [76.6, 14.0, 120, -30],
];
const GlobeScene: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ opacity: lin(f, 0, 8, 0, 1) }}>
      <Parchment />
      <EngravedGlobe at={0} target={MALABAR} tiltFrom={-28}
        zoom={{ at: 188, len: 40, to: 1.32, dy: 50 }}
        heat={[
          { lon: 75.9, lat: 11.0, r: 5, at: 200 }, { lon: 76.8, lat: 9.0, r: 4, at: 203 }, { lon: 75.0, lat: 14.0, r: 4.5, at: 206 },
          { lon: 74.3, lat: 16.8, r: 3.2, at: 209, op: 0.6 }, { lon: 77.6, lat: 11.8, r: 3.5, at: 212, op: 0.55 },
        ]}
        overlay={(proj) => (
          <>
            <IconScatter src={img("pepper_icon.png")} at={214} seed="mal" pts={PEPPER_PTS.map(([lo, la, dx, dy]) => { const q = proj([lo, la]); return { x: q.x + dx, y: q.y + dy }; })} p={{ size: 70, stagger: 1.5 }} />
            {(() => { const q = proj([58, 16]); return <BrushLabel text="말라바르" x={q.x} y={q.y + 30} at={151} p={{ size: 88, rot: -18 }} />; })()}
          </>
        )} />
      <SidePropPop src={img("pepper_sack.png")} x={250} y={560} w={360} at={262} />
      <SidePropPop src={img("gold_coins.png")} x={1668} y={580} w={380} at={276} />
    </AbsoluteFill>
  );
};

// ── 4. 세피아 실루엣 캐러밴 ────────────────────────────────────────────────────────────────────────
const SilScene: React.FC = () => (
  <Fade len={12}>
    <SilhouetteParallax
      imgs={{ camel: img("camel_body.png"), merchant: img("merchant.png") }}
      layers={[
        { src: img("sil_far.png"), top: 395, h: 330, depth: 0.12, op: 0.75 },
        { src: img("sil_mid.png"), top: 395, h: 490, depth: 0.4 },
      ]}
      walkers={[
        { kind: "merchant", x0: 560, baseY: 905, h: 330, speed: 1.9, phase: 0.6 },
        { kind: "camel", x0: 60, baseY: 905, h: 260, speed: 1.9, phase: 0 },
        { kind: "camel", x0: -470, baseY: 905, h: 245, speed: 1.9, phase: 1.7 },
      ]}
      front={[{ src: img("sil_near.png"), top: 800, h: 290, depth: 1 }]}
    />
  </Fade>
);

// ── 5+6. 작전 지도 교역로 → 딤 막대그래프 ─────────────────────────────────────────────────────────
const ROUTE_SEA: [number, number][] = [[75.4, 11.4], [66, 13.2], [55, 13.4], [47.5, 12.4], [43.6, 12.7], [40.5, 16.8], [37.6, 21.5], [35.2, 25.2], [34.3, 26.1]];
const ROUTE_NILE: [number, number][] = [[34.3, 26.1], [32.8, 26.1], [31.6, 28.2], [31.2, 30.0], [30.2, 31.1]];
const ROUTE_MED: [number, number][] = [[29.9, 31.4], [25.5, 33.8], [20.5, 36.2], [18.6, 39.6], [15.5, 42.4], [12.6, 45.2]];
const MapScene: React.FC = () => {
  const f = useCurrentFrame();
  const cam: CameraState = { center: [43.6 + f * 0.003, 30.4], zoom: 3.52 + f * 0.00025, bearing: 0, pitch: 0 };
  const base = S.map;
  const A = (at: number) => at - base; // 절대 프레임 → 시퀀스 로컬
  return (
    <Fade>
      <Parchment />
      <OpsMap cam={cam} regions={[{ id: "mamluk", geojson: MAMLUK, at: 0 }]}
        overlay={(px, box) => {
          const P = (ll: [number, number][]) => ll.map(px);
          const q = (ll: [number, number]) => px(ll);
          const ven = q([12.34, 45.44]), alx = q([29.92, 31.2]), cal = q([75.78, 11.25]);
          return (
            <>
              <BrushArrow id="sea" pts={P(ROUTE_SEA)} at={A(600)} w={box.w} h={box.h} p={{ len: 70 }} />
              <BrushArrow id="nile" pts={P(ROUTE_NILE)} at={A(668)} w={box.w} h={box.h} p={{ len: 40, width: 24 }} />
              <BrushArrow id="med" pts={P(ROUTE_MED)} at={A(740)} w={box.w} h={box.h} p={{ len: 60 }} />
              {[ven, alx, cal].map((c, i) => (
                <div key={i} style={{ position: "absolute", left: c.x - 11, top: c.y - 11, width: 22, height: 22, borderRadius: 11, background: PAL.red, border: "4px solid #fff", boxShadow: "0 2px 4px rgba(0,0,0,.5)",
                  opacity: lin(f, [A(598), A(740), A(598)][i], [A(598), A(740), A(598)][i] + 4, 0, 1) }} />
              ))}
              <BrushLabel text="말라바르" x={cal.x + 30} y={cal.y - 90} at={A(598)} p={{ size: 70, rot: -8, color: "#fff", glow: 4 }} />
              <BrushLabel text="맘루크" x={q([28.5, 26.0]).x} y={q([28.5, 26.0]).y} at={A(658)} p={{ size: 112, rot: -16, spacing: 0.2 }} />
              <BrushLabel text="베네치아" x={ven.x + 10} y={ven.y - 70} at={A(712)} p={{ size: 92, rot: -12 }} />
              <BrushLabel text="알렉산드리아" x={alx.x - 150} y={alx.y - 55} at={A(743)} p={{ size: 54, rot: -6, color: "#fff", glow: 4 }} />
              <SidePropPop src={img("dhow.png")} x={q([62, 16.5]).x} y={q([62, 16.5]).y - 30} w={170} at={A(606)} />
              <SidePropPop src={img("gold_coins.png")} x={q([35.8, 29.3]).x} y={q([35.8, 29.3]).y} w={150} at={A(672)} />
              <SidePropPop src={img("pepper_sack.png")} x={ven.x + 150} y={ven.y + 40} w={150} at={A(722)} />
            </>
          );
        }} />
      <Sequence from={S.chart - base} layout="none">
        <DimUnderlay at={0} p={{ multiply: false, alpha: 0.8, color: "#5E5750" }} />
        <IconBarChart at={8} title="후추 값이 불어나는 길" note="※ 단계 개념도 · 실제 가격 비율 아님" max={6.2}
          p={{ barsAt: 22, stagger: 14 }}
          bars={[
            { label: "말라바르\n농가", v: 0.8, icon: img("pepper_icon.png") },
            { label: "아랍·인도\n상인", v: 1.6, icon: img("dhow.png") },
            { label: "맘루크\n세관", v: 2.6, icon: img("gold_coins.png") },
            { label: "베네치아\n상인", v: 3.8, icon: img("pepper_sack.png") },
            { label: "유럽\n시장", v: 5.2, icon: img("gold_coins.png") },
          ]} />
      </Sequence>
    </Fade>
  );
};

// ── 7. 마스코트 콩트 ─────────────────────────────────────────────────────────────────────────────
const SKULL_ASPECT = 821 / 1103, GULL_ASPECT = 1059 / 912;
const SKULL_MOUTHS = [0, 1, 2].map((i) => ({ src: img(`skull_mouth${i}.png`), x: 0.655, y: [0.468, 0.463, 0.458][i], w: [0.15, 0.145, 0.145][i] }));
const GULL_MOUTHS = [{ src: "", x: 0, y: 0, w: 0 }, { src: img("gull_beak_open.png"), x: 0.5, y: 0, w: 1 }];
const SkitScene: React.FC<{ base: number; outro?: boolean }> = ({ base, outro }) => {
  const A = (at: number) => at - base;
  const f = useCurrentFrame();
  if (outro) {
    return (
      <Fade len={12}>
        <Parchment />
        <TalkingMascot body={img("skull_nav.png")} aspect={SKULL_ASPECT} x={400} bottom={-60} w={560} at={0} mouths={SKULL_MOUTHS} talk={[[A(1672), A(1712)]]} seed="so" />
        <TalkingMascot body={img("gull.png")} aspect={GULL_ASPECT} x={1530} bottom={-30} w={600} at={4} mouths={GULL_MOUTHS} talk={[[A(1722), A(1748)]]} seed="go" />
        <WipeBubble text="다음 항해에서 만나요!" x={470} y={330} at={A(1672)} tail="left" />
        <WipeBubble text="끼룩!" x={1560} y={560} at={A(1722)} tail="right" />
        <SidePropPop src={img("chest.png")} x={960} y={640} w={440} at={A(1700)} p={{ len: 8 }} />
      </Fade>
    );
  }
  return (
    <AbsoluteFill>
      <Parchment />
      <TalkingMascot body={img("skull_nav.png")} aspect={SKULL_ASPECT} x={400} bottom={-60} w={560} at={0} mouths={SKULL_MOUTHS}
        talk={[[A(1020), A(1066)], [A(1170), A(1230)]]} seed="s1" />
      <TalkingMascot body={img("gull.png")} aspect={GULL_ASPECT} x={1530} bottom={-30} w={600} at={3} mouths={GULL_MOUTHS}
        talk={[[A(1078), A(1110)], [A(1122), A(1150)]]} seed="g1" />
      <SidePropPop src={img("pepper_sack.png")} x={960} y={470} w={300} at={4} p={{ bob: 6 }} />
      <div style={{ position: "absolute", left: 0, right: 0, top: 650, textAlign: "center", fontFamily: "NeoHv", fontSize: 76, color: "#111", opacity: lin(f, 6, 9, 0, 1) }}>후추 한 줌</div>
      <WipeBubble text="후추 한 줌에 집 한 채??" x={470} y={300} at={A(1020)} out={A(1112)} tail="left" />
      <WipeBubble text="그건 과장이고!" x={1440} y={370} at={A(1078)} out={A(1160)} tail="right" />
      <WipeBubble text="비싸긴 엄청 비쌌지" x={1400} y={250} at={A(1122)} out={A(1160)} tail="right" p={{ fontSize: 40 }} />
      <WipeBubble text="인도로 직접 가면 되잖아?" x={500} y={300} at={A(1170)} tail="left" />
    </AbsoluteFill>
  );
};

// ── 8. 바스쿠 다가마: 항로 지도 + 포커스 딤 + 캐리커처 + 도장 ─────────────────────────────────────
const GAMA_ROUTE: [number, number][] = [[-9.1, 38.7], [-16, 28], [-23, 14], [-24, -2], [-21, -18], [-10, -30], [4, -35.6], [18.5, -36.2], [27, -34.2], [35, -25], [40.7, -15], [40.1, -3.2], [52, 4], [65, 9.5], [75.4, 11.3]];
const GamaScene: React.FC = () => {
  const f = useCurrentFrame();
  const base = S.gama;
  const A = (at: number) => at - base;
  const cam: CameraState = { center: [32 + f * 0.006, -3], zoom: 2.78, bearing: 0, pitch: 0 };
  const map = (
    <AbsoluteFill>
      <Parchment />
      <OpsMap cam={cam}
        overlay={(px, box) => {
          const lis = px([-9.14, 38.72]), cape = px([18.47, -34.36]), cal = px([75.78, 11.25]);
          return (
            <>
              <BrushArrow id="gama" pts={GAMA_ROUTE.map(px)} at={A(1262)} w={box.w} h={box.h} ease="linear" p={{ len: 150, width: 26 }} />
              <SidePropPop src={img("carrack.png")} x={lis.x - 30} y={lis.y - 70} w={170} at={A(1260)} />
              <BrushLabel text="희망봉" x={cape.x - 190} y={cape.y - 20} at={A(1353)} p={{ size: 80, rot: -8 }} />
              <BrushLabel text="캘리컷" x={cal.x - 20} y={cal.y + 70} at={A(1392)} p={{ size: 78, rot: -10 }} />
              <BrushLabel text="리스본" x={lis.x + 20} y={lis.y + 60} at={A(1262)} p={{ size: 60, rot: -8, color: "#fff", glow: 4 }} />
            </>
          );
        }} />
      <BrushLabel text="1498" x={1580} y={180} at={A(1256)} p={{ size: 130, rot: -6, spacing: 0.02 }} />
    </AbsoluteFill>
  );
  const dropOut = A(1392);
  const dropK = lin(f, dropOut, dropOut + 8, 0, 1, Easing.in(Easing.quad));
  return (
    <AbsoluteFill>
      <FocusDim at={A(1296)} out={dropOut} bg={map}>
        <AbsoluteFill style={{ transform: `translateY(${dropK * 1100}px)` }}>
          <CaricatureSlide src={img("dagama.png")} side="left" at={A(1298)} w={610} name="바스쿠 다가마" nameY={800} />
          <PirStamp lines={["희망봉 우회"]} x={1240} y={430} at={A(1350)} p={{ size: 130 }} />
        </AbsoluteFill>
      </FocusDim>
    </AbsoluteFill>
  );
};

// ── 9. 실사 후추 사진 켄번스 + 대형 단어 ─────────────────────────────────────────────────────────────
const PhotoScene: React.FC = () => {
  const f = useCurrentFrame();
  const A = (at: number) => at - S.photo;
  const strike = lin(f, A(1470), A(1480), 0, 1, Easing.out(Easing.cubic));
  return (
    <Fade>
      <Parchment />
      <TornPhoto src={staticFile("explainer_demo/real/tellicherry_peppercorns.jpg")} x={1240} y={470} w={1080} h={720} at={0} pos="50% 45%" p={{ enterLen: 1 }} />
      <div style={{ position: "absolute", left: 1500, top: 816, fontFamily: "NeoEb", fontSize: 20, color: "#6b5a48" }}>Tellicherry Black Peppercorns · Misterneedlemouse / CC0</div>
      <BigWord lines={["검은 황금"]} x={380} y={330} at={A(1436)} p={{ size: 104 }} />
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {strike > 0.01 && <line x1={130} y1={338} x2={130 + 500 * strike} y2={338 - 20 * strike} stroke={PAL.red} strokeWidth={14} strokeLinecap="round" />}
      </svg>
      <BigWord lines={["[식탁 위]", "[양념]"]} x={380} y={600} at={A(1528)} p={{ size: 104 }} />
    </Fade>
  );
};
const WordsScene: React.FC = () => (
  <Fade>
    <Parchment />
    <SidePropPop src={img("pepper_icon.png")} x={960} y={300} w={190} at={8} />
    <BigWord lines={["작은 열매 한 알이", "[세계 지도]를 다시 그리다"]} y={620} at={10} p={{ size: 96, perChar: 1.25 }} />
  </Fade>
);

// ── 오디오 ──────────────────────────────────────────────────────────────────────────────────────
const SFX: [number, string, number][] = [
  [214, "pop", 0.35], [262, "pop", 0.4], [276, "pop", 0.4], [347, "shutter", 0.35], [S.sting + 16, "thud", 0.4], [S.sting + 50, "sparkle", 0.4],
  [600, "pen", 0.3], [606, "pop", 0.35], [658, "punch", 0.25], [672, "pop", 0.35], [712, "pen", 0.3], [722, "pop", 0.35],
  [S.chart + 30, "pop", 0.3], [S.chart + 44, "pop", 0.3], [S.chart + 58, "pop", 0.3], [S.chart + 72, "pop", 0.3], [S.chart + 86, "pop", 0.3],
  [1020, "click", 0.4], [1078, "click", 0.4], [1122, "click", 0.4], [1170, "click", 0.4],
  [1260, "pop", 0.35], [1298, "boing", 0.25], [1350, "thud", 0.55], [1436, "click", 0.3], [1470, "pen", 0.35], [1528, "click", 0.3],
  [1672, "click", 0.4], [1700, "sparkle", 0.4], [1722, "click", 0.4],
];

export const ExplainerDemo: React.FC = () => {
  const f = useCurrentFrame();
  const segs = TL.segs as Record<string, { t0: number; dur: number }>;
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <Sequence from={S.globe} durationInFrames={S.sting + 30 - S.globe}><Drift dur={S.sting + 30}><GlobeScene /></Drift></Sequence>
      <Sequence from={S.sting} durationInFrames={S.sil + 12 - S.sting}>
        <TornPaperWipe at={0}><Parchment /><LogoSting dur={S.sil + 6 - S.sting} /></TornPaperWipe>
      </Sequence>
      <Sequence from={S.sil} durationInFrames={S.map + DISS - S.sil}><SilScene /></Sequence>
      <Sequence from={S.map} durationInFrames={S.skit - S.map}><MapScene /></Sequence>
      <Sequence from={S.skit} durationInFrames={S.gama - S.skit}><Drift dur={S.gama - S.skit} to={1.02}><SkitScene base={S.skit} /></Drift></Sequence>
      <Sequence from={S.gama} durationInFrames={S.photo + DISS - S.gama}><GamaScene /></Sequence>
      <Sequence from={S.photo} durationInFrames={S.words + DISS - S.photo}><Drift dur={S.words + DISS - S.photo}><PhotoScene /></Drift></Sequence>
      <Sequence from={S.words} durationInFrames={S.outro + DISS - S.words}><Drift dur={S.outro + DISS - S.words}><WordsScene /></Drift></Sequence>
      <Sequence from={S.outro} durationInFrames={S.end - S.outro}><SkitScene base={S.outro} outro /></Sequence>
      <PirSubtitles subs={TL.subs} />
      <AbsoluteFill style={{ background: "#000", opacity: lin(f, S.end - 10, S.end, 0, 1), pointerEvents: "none" }} />
      {/* 오디오: 내레이션 + BGM(-16dB 가량) + 효과음 */}
      {Object.entries(segs).map(([id, s]) => (
        <Sequence key={id} from={Math.round(s.t0 * FPS)} durationInFrames={Math.ceil(s.dur * FPS) + 2} layout="none"><Audio src={staticFile(`explainer_demo/vo/${id}.mp3`)} /></Sequence>
      ))}
      <Audio src={staticFile("audio/bgm.mp3")} volume={(fr) => 0.13 * lin(fr, 0, 20, 0, 1) * lin(fr, S.end - 45, S.end, 1, 0)} />
      {SFX.map(([at, n, v], i) => (
        <Sequence key={`sfx${i}`} from={at} durationInFrames={45} layout="none"><Audio src={staticFile(`audio/${n}.wav`)} volume={v} /></Sequence>
      ))}
    </AbsoluteFill>
  );
};
