// 도감 x_explainer 갤러리 — 설명형 편집 레퍼런스(여러 레퍼런스 중 하나)의 연출 기법(타이밍·동작)을 세모지 디자인으로.
// 데모 id 는 demo-<기법 id>. 01~04 = 신규 조합 컴포넌트(lib/x_explainer.tsx), 05~12 = 기존 세모지 기법에 추가한 옵션(기본값에서는 기존과 픽셀 동일, 여기서만 켠다).
import React from "react";
import { AbsoluteFill, Img } from "remotion";
import { z } from "zod";
import { runGallery, Demo } from "./runner";
import { W, H, src, Stamp, StampParams, MapRoute, MapRouteParams, PhotoFrame } from "../fx";
import { GlobeSpinScatter, GlobeSpinScatterParams, DashedColumnCompare, DashedColumnCompareParams, ChatParody, ChatParodyParams, MapStatOverlay, MapStatOverlayParams } from "../lib/x_explainer";
import { SpeechBubble, SpeechBubbleParams, BlurDimInterrupt, BlurDimInterruptParams, MouthSwap, MouthSwapParams, XRig, PropImg, CircuitBg } from "../lib/x_acting";
import { RackDefocus, RackDefocusParams } from "../lib/x_transitions";
import { BarChartV, BarChartVParams, BarChartH, BarChartHParams, GlowBg } from "../lib/charts";
import { SemojiRig, SemojiRigParams } from "../lib/semoji_rig";

type P = { p?: Record<string, any> };
/** 스키마 기본값만 바꾼 사본(옵션을 켠 데모의 슬라이더 초기값) */
const redef = <S extends z.ZodObject<any>>(s: S, d: Partial<z.infer<S>>): S =>
  s.extend(Object.fromEntries(Object.entries(d).map(([k, v]) => {
    const t: any = s.shape[k];
    return [k, t.unwrap().default(v).describe(t.description)];
  }))) as unknown as S;
const Bg: React.FC<{ c: string }> = ({ c }) => <AbsoluteFill style={{ background: c }} />;
const SAGE = "linear-gradient(180deg,#E6EFE4 0%,#C2CDC4 100%)";

// 01 회전 지구본 → 화북 정지 → 히트맵 + 짜장면 그릇 산포
const D01: React.FC<P> = ({ p }) => (
  <AbsoluteFill>
    <Bg c="radial-gradient(ellipse at 50% 45%,#F7F1E3 0%,#E4DCC8 100%)" />
    <GlobeSpinScatter at={0} target={[117, 33]} p={p} icons={["icon_bowl"]} center={[116.5, 35.5]} seed="d01"
      heat={[{ lon: 118.3, lat: 36.4, r: 9 }, { lon: 116.4, lat: 39.6, r: 7, dt: 2 }, { lon: 113.8, lat: 34.6, r: 8, dt: 4 }, { lon: 120.5, lat: 31.5, r: 6, dt: 6 }]} />
  </AbsoluteFill>
);
// 02 점선 3열 비교 — 짜장면 한 그릇 값이 시대별로 자라는 돈더미(세모지 money_pile)
const D02: React.FC<P> = ({ p }) => (
  <DashedColumnCompare at={0} p={p} items={[
    { label: "1960년", prop: "coin_won", value: 0.22, caption: "15원" },
    { label: "1990년", prop: "banknote_won", value: 0.5, caption: "1,000원" },
    { label: "2024년", prop: "money_pile", value: 0.62, caption: "7,308원" },
    { label: "그리고…", prop: "money_sack", value: 0.9, caption: "?" },
  ]} />
);
// 03 가상 메신저 대화 패러디 — 개항기 제물포 상인 단톡방(세모지 캐스트 흉상 프로필)
const D03: React.FC<P> = ({ p }) => (
  <ChatParody at={0} p={p} title="제물포 상인 모임" members={4} msgs={[
    { from: "c5_chef", name: "왕서방", side: "left", text: "배 도착함 ㅋㅋ\n산둥에서 춘장 100독 실어옴", time: "오후 3:12" },
    { from: "c2_boss", name: "객주 김사장", side: "left", text: "100독??\n그걸 누가 다 먹어", time: "오후 3:12" },
    { from: "walker1", name: "나", side: "right", text: "저요", time: "오후 3:13" },
    { from: "c5_chef", name: "왕서방", side: "left", text: "국수에 비벼 먹으면 됨", time: "오후 3:13" },
    { from: "c4_elder", name: "최 영감", side: "left", text: "...그게 된다고?", time: "오후 3:14" },
    { from: "walker1", name: "나", side: "right", text: "30분 뒤 청관 거리 앞 집합", time: "오후 3:14" },
  ]} />
);
// 04 지도 전력 통계 오버레이 — 세모지 항로 지도(울릉도·독도 포함) 위 딤 → 제목 타자 → 아이콘+숫자 행 팝
const MAPBG = <MapRoute at={0} routeAt={-200} labelsAt={-200} p={{ camLen: 0 }} />;
const D04: React.FC<P> = ({ p }) => (
  <MapStatOverlay at={10} p={p} bg={MAPBG} title="산둥 → 인천, 사람과 물자" rows={[
    { icon: "junk_sailboat", label: "오간 정크선", value: "수백", unit: "척" },
    { icon: "icon_user", label: "조선 거주 화교(1910)", value: "약 1.2", unit: "만 명" },
    { icon: "wok", label: "청요리집", value: "수십", unit: "곳" },
  ]} />
);
// 05 말풍선 와이프 리빌 — SpeechBubble reveal="wipe"(좌→우 12f + 퇴장 3f) · 입은 MouthSwap talkMode="random"(4~8f)
const D05: React.FC<P> = ({ p }) => (
  <AbsoluteFill>
    <Bg c="linear-gradient(180deg,#CFE7F2,#A9D2E4)" />
    <div style={{ position: "absolute", left: 0, right: 0, top: 820, bottom: 0, background: "#5FA7B5" }} />
    <MouthSwap at={8} out={100} seed="x05" p={{ talkMode: "random" }} render={(o) => <XRig cast="c4_elder" x={620} y={1110} h={1640} bust seed="x05" pose={{ mouth: o }} />} />
    <SpeechBubble x={1260} y={330} w={560} h={260} text={"짜장면이\n뭔고?"} size={64} at={8} out={52} p={{ reveal: "wipe", ...p }} />
    <SpeechBubble x={1300} y={360} w={640} h={280} text={"춘장에 비빈\n국수라니!"} size={64} at={58} out={104} p={{ reveal: "wipe", ...p }} />
  </AbsoluteFill>
);
// 06 딤 컷어웨이 → 말풍선 wipe → 낙하 퇴장 + 딤 해제 (BlurDimInterrupt reveal="wipe", exit="drop")
const D06: React.FC<P> = ({ p }) => (
  <BlurDimInterrupt at={8} p={{ reveal: "wipe", exit: "drop", exitAt: 62, ...p }}
    bg={<AbsoluteFill><CircuitBg bg="#0B1440" period={30} />
      <PropImg id="chips_box" x={420} y={520} w={520}><div style={{ position: "absolute", left: "58%", top: "16%", transform: "translate(-50%,-50%) rotate(-4deg)", fontFamily: "NeoHv", fontSize: 76, color: "#2B6FD6" }}>CHIPS</div></PropImg>
      <PropImg id="cpu_chip" x={1330} y={470} w={500} style={{ filter: "drop-shadow(0 0 40px #29D3FF)" }}><div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "Jalnan", fontSize: 130, color: "#0B1440" }}>X86</div></PropImg></AbsoluteFill>}
    narrator={<XRig cast="walker1" x={760} y={1110} h={1500} bust seed="x06" pose={{ armR: "arm_palm_stop" }} />}
    bubble={{ x: 1180, y: 330, w: 420, h: 250, text: "CPU에서의\n아키텍처란?" }} />
);
// 07 직전 장면 디포커스 → 레이어 팝 → 낙하 퇴장 (RackDefocus exit="drop")
const D07: React.FC<P> = ({ p }) => (
  <RackDefocus at={6} p={{ exit: "drop", exitAt: 40, ...p }}
    backdrop={<Img src={src("img/s03_restaurant.jpg")} style={{ position: "absolute", inset: 0, width: W, height: H, objectFit: "cover" }} />}
    layer={<AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}><div style={{ display: "flex", alignItems: "center", background: "#D7182A", borderRadius: 120, padding: "20px 70px 10px 20px", gap: 30, boxShadow: "0 10px 20px rgba(0,0,0,0.3)" }}><Img src={src("img/s05_chunjang.png")} style={{ width: 220 }} /><span style={{ fontFamily: "NeoHv", fontSize: 110, color: "#fff" }}>284,830L</span></div></AbsoluteFill>} />
);
// 08 세로 막대 + 막대 끝 아이콘 팝(staggerF 1f · back-out 4f)
const D08: React.FC<P> = ({ p }) => (
  <AbsoluteFill>
    <GlowBg color="#F4ECDD" glow="rgba(255,255,255,0.6)" />
    <BarChartV at={4} title="1인당 연간 소비량" max={80} maxH={380} baseY={830} unit="그릇" p={{ staggerF: 1, ...p }}
      icons={["icon_bowl", "icon_bowl", "sugar_cubes_icon", "icon_bowl", "icon_bowl", "wok"]}
      groups={[
        { x: 520, caption: "2014년", bars: [{ label: "짜장면", value: 72, hi: true }, { label: "짬뽕", value: 41 }, { label: "탕수육", value: 23 }] },
        { x: 1400, caption: "2024년", bars: [{ label: "짜장면", value: 58, hi: true }, { label: "짬뽕", value: 49 }, { label: "마라탕", value: 37 }] },
      ]} />
  </AbsoluteFill>
);
// 09 가로 막대 + 막대 끝 아이콘 팝(행 1f 스태거 · 막대 15f)
const D09: React.FC<P> = ({ p }) => (
  <BarChartH at={4} title="짜장면 한 그릇 가격" subtitle="2024년 지역별 평균 (단위: 원)" unit="원" max={8000} ticks={[0, 2000, 4000, 6000, 8000]} winner={2} barMaxW={1060}
    p={{ rowStagger: 1, barDur: 15, ...p }} icons={["icon_bowl", "icon_bowl", "icon_bowl", "icon_bowl", "icon_bowl", "icon_bowl"]}
    rows={[{ label: "서울", value: 7308 }, { label: "경기", value: 6946 }, { label: "인천", value: 7523 }, { label: "부산", value: 6567 }, { label: "대구", value: 6417 }, { label: "광주", value: 6600 }]} />
);
// 10 지도 항로 붓 화살표(MapRoute stroke="brush": 30px 테이퍼 + 흰 테두리 5px, 25f ease-in-out)
const D10: React.FC<P> = ({ p }) => <MapRoute at={0} routeAt={20} labelsAt={6} p={{ stroke: "brush", ...p }} />;
// 11 불규칙 입 교체 — 왼쪽 fixed(talkEvery 5) vs 가운데·오른쪽 random(4~8f, 시드별 다름)
const Tag: React.FC<{ x: number; t: string }> = ({ x, t }) => <div style={{ position: "absolute", left: x - 200, width: 400, top: 60, textAlign: "center", fontFamily: "NeoHv", fontSize: 40, color: "#2B2420" }}>{t}</div>;
const D11: React.FC<P> = ({ p }) => (
  <AbsoluteFill>
    <Bg c={SAGE} />
    <SemojiRig cast="c2_boss" x={400} y={1110} h={1250} bust seed="x11a" p={{ talkEvery: 5 }} />
    <SemojiRig cast="c5_chef" x={960} y={1110} h={1250} bust seed="x11b" p={{ talkMode: "random", ...p }} />
    <SemojiRig cast="c3_woman" x={1520} y={1110} h={1250} bust seed="x11c" p={{ talkMode: "random", ...p }} />
    <Tag x={400} t="fixed (5f)" /><Tag x={960} t="random 4~8f" /><Tag x={1520} t="random 4~8f" />
  </AbsoluteFill>
);
// 12 기울어진 도장 유지 — Stamp 1.6→1.0 5f expo-out · -8° · 깜빡임 없음
const D12: React.FC<P> = ({ p }) => (
  <AbsoluteFill>
    <Img src={src("img/s03_restaurant.jpg")} style={{ position: "absolute", inset: 0, width: W, height: H, objectFit: "cover", filter: "blur(7px) brightness(0.58)" }} />
    <PhotoFrame img="img/s05_factory.jpg" x={500} y={230} w={920} h={600} at={-10} color="#2E5FB0" />
    <Stamp text="폐업" x={960} y={560} at={8} p={{ size: 150, rot: -8, startScale: 1.6, slamDur: 5, slamEase: "expoOut", blink: false, ...p }} />
  </AbsoluteFill>
);

export const DEMOS: Demo[] = [
  { name: "GlobeSpinScatter — 회전 지구본 감속 정지 + 히트맵 + 아이콘 산포", id: "demo-globe-spin-scatter", dur: 190, C: D01, schema: GlobeSpinScatterParams },
  { name: "DashedColumnCompare — 점선 N열 비교(대상 성장)", id: "demo-dashed-column-compare", dur: 110, C: D02, schema: DashedColumnCompareParams },
  { name: "ChatParody — 역사 인물 메신저 대화 패러디", id: "demo-chat-parody", dur: 250, C: D03, schema: ChatParodyParams },
  { name: "MapStatOverlay — 지도 딤 + 타자 제목 + 통계 행 팝", id: "demo-map-stat-overlay", dur: 130, C: D04, schema: MapStatOverlayParams },
  { name: "SpeechBubble — 와이프 리빌 말풍선(reveal=wipe)", id: "demo-wipe-reveal-bubble", dur: 115, C: D05, schema: redef(SpeechBubbleParams, { reveal: "wipe" }) },
  { name: "BlurDimInterrupt — wipe 말풍선 + 낙하 퇴장(exit=drop)", id: "demo-dim-cutaway-drop-exit", dur: 100, C: D06, schema: redef(BlurDimInterruptParams, { reveal: "wipe", exit: "drop", exitAt: 62 }) },
  { name: "RackDefocus — 레이어 낙하 퇴장(exit=drop)", id: "demo-rack-defocus-drop-exit", dur: 70, C: D07, schema: redef(RackDefocusParams, { exit: "drop", exitAt: 40 }) },
  { name: "BarChartV — 막대 끝 아이콘 팝(icons · staggerF)", id: "demo-bar-end-icon-pop", dur: 130, C: D08, schema: redef(BarChartVParams, { staggerF: 1, maxH: 380 }) },
  { name: "BarChartH — 막대 끝 아이콘 팝(icons)", id: "demo-bar-end-icon-pop-h", dur: 100, C: D09, schema: redef(BarChartHParams, { rowStagger: 1, barDur: 15 }) },
  { name: "MapRoute — 붓 화살표 항로(stroke=brush)", id: "demo-brush-arrow-route", dur: 80, C: D10, schema: redef(MapRouteParams, { stroke: "brush" }) },
  { name: "SemojiRig — 불규칙 입 교체(talkMode=random)", id: "demo-random-mouth-talk", dur: 90, C: D11, schema: redef(SemojiRigParams, { talkMode: "random" }) },
  { name: "Stamp — 기울어진 도장 유지(blink 끔 · expoOut)", id: "demo-tilted-stamp-hold", dur: 75, C: D12, schema: redef(StampParams, { rot: -8, startScale: 1.6, slamDur: 5, slamEase: "expoOut", blink: false, size: 150 }) },
];
export const GALLERY_DUR = Math.max(30, DEMOS.reduce((a, d) => a + d.dur, 0));
export const Gallery = runGallery(DEMOS);
