import React from "react";
import { AbsoluteFill, Img, useCurrentFrame } from "remotion";
import { runGallery, Demo } from "./runner";
import { W, H, src, photoPop } from "../fx";
import { Icon, IconName } from "../lib/callouts";
import { prop, propH } from "../lib/kit";
import {
  LoopArrow, LoopArrowParams, LabelChipSparkle, LabelChipSparkleParams, NumberedReasonTab, NumberedReasonTabParams,
  ClipboardSwingDrop, ClipboardSwingDropParams, OrangePillStack, OrangePillStackParams, FightingVsHud, FightingVsHudParams, PixelSeaBg,
  ProbabilityPill, ProbabilityPillParams, BigXStrike, BigXStrikeParams, CalendarTagSmoke, CalendarTagSmokeParams,
  HangingIconDrop, HangingIconDropParams, FeatheredSmokeBubble, FeatheredSmokeBubbleParams, ChecklistTick, ChecklistTickParams,
  QuestWindowDrop, QuestWindowDropParams, DiagonalTapeTags, DiagonalTapeTagsParams, LogoEdgeIconsGather, LogoEdgeIconsGatherParams,
  RippleRings, RippleRingsParams, ProductSpecPins, ProductSpecPinsParams, TcgCardMarquee, TcgCardMarqueeParams,
  HeadlineStripStack, HeadlineStripStackParams, MegaphoneCone, MegaphoneConeParams,
} from "../lib/x_callouts";

// 갤러리 섹션: x_callouts — 도감 "분석만" 콜아웃·라벨 기법 구현 데모
type PP = { p?: any };
const Flat: React.FC<{ c: string; children?: React.ReactNode }> = ({ c, children }) => <AbsoluteFill style={{ background: c }}>{children}</AbsoluteFill>;
const Photo: React.FC<{ img: string; dim?: number; blur?: number }> = ({ img, dim = 1, blur = 0 }) => (
  <Img src={src(img)} style={{ position: "absolute", inset: blur ? -30 : 0, width: blur ? W + 60 : W, height: blur ? H + 60 : H, objectFit: "cover", filter: `brightness(${dim})${blur ? ` blur(${blur}px)` : ""}` }} />
);
const Cut: React.FC<{ img: string; x: number; y: number; w: number; h: number; flip?: boolean }> = ({ img, x, y, w, h, flip }) => (
  <Img src={src(img)} style={{ position: "absolute", left: x, top: y, width: w, height: h, objectFit: "contain", transform: flip ? "scaleX(-1)" : undefined }} />
);
const Disc: React.FC<{ name: IconName; color: string; bg?: string }> = ({ name, color, bg = "#fff" }) => (
  <div style={{ width: "100%", height: "100%", borderRadius: "50%", background: bg, display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 8px 18px rgba(0,0,0,0.25)" }}><div style={{ width: "62%", height: "62%" }}><Icon name={name} color={color} /></div></div>
);
/** 사진 팝 카드(루프 화살표 뒤에 들어오는 사진) */
const PopPhoto: React.FC<{ img: string; x: number; y: number; w: number; h: number; at: number }> = ({ img, x, y, w, h, at }) => {
  const f = useCurrentFrame();
  if (f < at) return null;
  const { s, blur } = photoPop(f, at);
  return <Img src={src(img)} style={{ position: "absolute", left: x, top: y, width: w, height: h, objectFit: "cover", transform: `scale(${s})`, filter: `blur(${blur}px)`, boxShadow: "0 10px 20px rgba(0,0,0,0.3)" }} />;
};
/** 흐린 문서(서명 파문 데모용) — 세모지 그림체 서류 한 장(paper_sheet) + 제목·서명만 코드 */
const Doc: React.FC<{ x: number; y: number; w: number; h: number; title: string }> = ({ x, y, w, h, title }) => (
  <div style={{ position: "absolute", left: x, top: y, width: w, height: h, filter: "drop-shadow(0 10px 24px rgba(0,0,0,0.3))" }}>
    <Img src={prop("paper_sheet")} style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }} />
    <div style={{ position: "absolute", left: "19%", right: "19%", top: "4.5%", height: "9%", background: "#EDEBE6", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "NeoHv", fontSize: 34, color: "#222", whiteSpace: "nowrap" }}>{title}</div>
    <div style={{ position: "absolute", right: 60, bottom: 50, fontFamily: "Yeonsung", fontSize: 48, color: "#222", transform: "rotate(-8deg)" }}>정주영</div>
  </div>
);
/** 건물 마스코트 몸(오렌지 pill 데모용) — 세모지 그림체 빌딩(building_mascot_body), 간판 글자만 코드 */
const Building: React.FC<{ x: number; y: number }> = ({ x, y }) => (
  <div style={{ position: "absolute", left: x, top: y, width: 380, height: 620, filter: "drop-shadow(0 10px 20px rgba(0,0,0,0.3))" }}>
    <Img src={prop("building_mascot_body")} style={{ position: "absolute", left: 0, top: 0, width: 380, height: propH("building_mascot_body", 380) }} />
    <div style={{ position: "absolute", left: 380 * 0.22, width: 380 * 0.56, top: propH("building_mascot_body", 380) * 0.655, height: propH("building_mascot_body", 380) * 0.065, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "NeoHv", fontSize: 38, color: "#D93A2B" }}>SEMO</div>
  </div>
);
const Glove: React.FC<{ x: number; y: number; rot: number; v?: boolean }> = ({ x, y, rot, v }) => (
  <svg width={130} height={150} viewBox="0 0 100 115" style={{ position: "absolute", left: x, top: y, transform: `rotate(${rot}deg)` }}>
    {v ? <><rect x={30} y={4} width={16} height={56} rx={8} fill="#fff" stroke="#222" strokeWidth={4} transform="rotate(-12 38 40)" /><rect x={52} y={4} width={16} height={56} rx={8} fill="#fff" stroke="#222" strokeWidth={4} transform="rotate(12 60 40)" /></>
      : <rect x={40} y={0} width={18} height={60} rx={9} fill="#fff" stroke="#222" strokeWidth={4} />}
    <rect x={24} y={46} width={56} height={50} rx={22} fill="#fff" stroke="#222" strokeWidth={4} />
    <rect x={32} y={92} width={40} height={20} rx={4} fill="#fff" stroke="#222" strokeWidth={4} />
  </svg>
);

// 1. 루프 화살표 → ~15f 뒤 사진
const Loop: React.FC<PP> = ({ p }) => (
  <Flat c="#F4B7C0">
    <Cut img="img/s06_kid.png" x={120} y={260} w={600} h={820} />
    <LoopArrow x={760} y={470} at={6} p={p} />
    <PopPhoto img="real/jjajang.jpg" x={1160} y={250} w={620} h={560} at={21} />
  </Flat>
);
// 2. 라벨 칩 + 반짝이
const Chip: React.FC<PP> = ({ p }) => (
  <Flat c="#C0692F">
    <Cut img="img/s05_bowl.png" x={610} y={330} w={700} h={560} />
    <LabelChipSparkle text="광동요리" x={960} y={700} at={8} p={p} />
  </Flat>
);
// 3. 번호 사유 탭
const Tab: React.FC<PP> = ({ p }) => (
  <Flat c="#4A1418">
    <Photo img="img/s03_restaurant.jpg" dim={0.55} />
    <NumberedReasonTab items={[{ text: "1.비싼 가격대", at: 6 }, { text: "2.성능과 호환성 문제", at: 60 }, { text: "3.마케팅 실패", at: 100 }]} p={p} />
  </Flat>
);
// 4. 클립보드 스윙 드롭 + 줄 리빌 + 서명
const Clip: React.FC<PP> = ({ p }) => (
  <Flat c="#D0A060">
    <ClipboardSwingDrop title="파트너 사퇴서" x={W / 2} y={H / 2 + 20} at={6}
      lines={[{ text: "본인은 세모상사의", at: 34 }, { text: "공동 창업 파트너 지위를", at: 46 }, { text: "스스로 포기하며,", at: 58 }, { text: "지분 10%를 800달러에 양도합니다.", at: 70 }]}
      sign={{ at: 92 }} p={p} />
  </Flat>
);
// 5. 오렌지 pill 스택
const Pills: React.FC<PP> = ({ p }) => (
  <Flat c="#1D3F73">
    <Building x={1180} y={300} />
    <Glove x={1060} y={420} rot={-80} />
    <Glove x={1560} y={330} rot={10} v />
    <OrangePillStack x={235} y={205} items={[{ text: "복사기 기술", at: 6 }, { text: "컴퓨터 과학", at: 30 }, { text: "정보 기술", at: 52 }, { text: "전자 공학", at: 76 }]} p={p} />
  </Flat>
);
// 6. 격투게임 VS HUD
const Vs: React.FC<PP> = ({ p }) => (
  <AbsoluteFill>
    <PixelSeaBg />
    <Cut img="img/s03_woo.png" x={380} y={380} w={520} h={700} />
    <Cut img="img/s06_kid.png" x={1020} y={380} w={520} h={700} flip />
    <FightingVsHud at={0} left={{ name: "우사장", img: "img/s03_woo.png", hp: 0.95, sub: 0.8 }} right={{ name: "꼬마", img: "img/s06_kid.png", hp: 0.7, sub: 1 }} p={{ vsDelay: 15, ...p }} />
  </AbsoluteFill>
);
// 7. 확률 pill
const Prob: React.FC<PP> = ({ p }) => (
  <Flat c="#3E4B61">
    <div style={{ position: "absolute", left: 360, top: 160, width: 760, height: 760, borderRadius: "50%", background: "#55647C" }} />
    <Cut img="img/s03_woo.png" x={440} y={200} w={600} h={880} />
    <ProbabilityPill label="가게가 망하지 않을 확률" value="10%" x={740} y={800} at={6} out={80} p={p} />
    <ProbabilityPill label="가게가 살아날 확률" value="60%" x={740} y={800} at={100} p={p} />
  </Flat>
);
// 8. 대형 X
const XS: React.FC<PP> = ({ p }) => (
  <Flat c="#141414">
    <div style={{ position: "absolute", left: 300, top: 120, width: 1320, height: 840, background: "#EDEDED", borderRadius: 30 }} />
    <div style={{ position: "absolute", left: 380, top: 200, width: 700, height: 680, background: "#2A2A2A", borderRadius: 40 }} />
    <div style={{ position: "absolute", left: 420, top: 240, width: 620, height: 600, background: "linear-gradient(160deg,#9CC3E6,#E8EEF4)" }} />
    <BigXStrike x={960} y={540} at={6} target={<div style={{ width: 280, height: 280, borderRadius: 34, background: "linear-gradient(160deg,#E4453A,#9E1C22)", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "NeoHv", fontSize: 150, color: "#FFD7B0", boxShadow: "0 10px 20px rgba(0,0,0,0.35)" }}>Fx</div>} p={p} />
  </Flat>
);
// 9. 탁상달력 연도 태그
const Cal: React.FC<PP> = ({ p }) => (
  <Flat c="#EAE3E6">
    <Photo img="real/port.jpg" dim={0.9} />
    <CalendarTagSmoke year="1895년" at={8} p={p} />
  </Flat>
);
// 10. 매달린 아이콘 드롭
const Hang: React.FC<PP> = ({ p }) => (
  <Flat c="#D2172B">
    <div style={{ position: "absolute", left: 140, top: 180, fontFamily: "Jalnan", fontSize: 150, color: "#fff" }}>세모콜라</div>
    <HangingIconDrop x={1060} y={480} at={6} icon="calendar" label="19억 잔" p={p} />
    <HangingIconDrop x={1500} y={480} at={46} icon="stopwatch" label="2만 잔" p={p} />
  </Flat>
);
// 11. 연기 가장자리 말풍선
const Smoke: React.FC<PP> = ({ p }) => (
  <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 40%, #3a3a3a, #121212)" }}>
    <Cut img="img/s03_woo.png" x={60} y={180} w={640} h={900} />
    <FeatheredSmokeBubble lines={["세모식당이 품평회에서", "호평을 받긴 했지만", "그것만 가지고 장사가", "성공할 수는 없습니다."]} x={1290} y={460} at={6} out={110}
      next={<Img src={src("real/chinatown.jpg")} style={{ position: "absolute", left: 900, top: 200, width: 760, height: 520, objectFit: "cover", boxShadow: "0 10px 20px rgba(0,0,0,0.5)" }} />} p={p} />
  </AbsoluteFill>
);
// 12. 체크리스트
const Check: React.FC<PP> = ({ p }) => (
  <AbsoluteFill>
    <Photo img="img/s05_factory.jpg" dim={0.85} />
    <Cut img="img/s03_woo.png" x={160} y={220} w={600} h={860} />
    <ChecklistTick x={1220} y={150} at={0} items={[{ text: "화력 발전소", at: 12 }, { text: "비료 공장", at: 42 }, { text: "시멘트 공장", at: 72 }, { text: "노동력", at: 102 }]} stampAt={125} p={p} />
  </AbsoluteFill>
);
// 13. 퀘스트 창
const Quest: React.FC<PP> = ({ p }) => (
  <Flat c="#1F8A5A">
    {Array.from({ length: 12 }).map((_, i) => <div key={i} style={{ position: "absolute", left: i * 170, top: 0, width: 80, height: H, background: "rgba(0,0,0,0.12)" }} />)}
    <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: 200, background: "#6B3A1E" }} />
    <QuestWindowDrop at={6} region="중동 지역" quests={[{ text: "주베일 산업항 공사", done: true }, { text: "OO 해양 유조선 공사" }, { text: "OO 중공업 공사" }, { text: "OO 정박시설 공사" }, { text: "OO 해상 터미널 공사" }]}
      npc={{ title: "주베일 산업\n공업항 공사", img: "img/s03_woo.png", code: "9311 JUBAIL", desc: "육상과 해상에 걸쳐\n모든 공정을 종합한\n주베일 산업항 건설을\n완벽하게 수행해라!" }} p={p} />
  </Flat>
);
// 14. 대각 테이프 + 태그
const Tape: React.FC<PP> = ({ p }) => (
  <AbsoluteFill>
    <Photo img="img/s06_crowd.jpg" dim={0.7} />
    <DiagonalTapeTags at={6} tags={[{ text: "저 달러", at: 26, d: 520 }, { text: "저 금리", at: 36, d: 1020 }, { text: "저 유가", at: 46, d: 1520 }]} rider={{ img: "img/s05_bowl.png", at: 80, d: 1150, w: 360, h: 260 }} p={p} />
  </AbsoluteFill>
);
// 15. 로고 주위 아이콘 입장
const LogoG: React.FC<PP> = ({ p }) => (
  <Flat c="#F7F4EE">
    <LogoEdgeIconsGather logo={<div style={{ display: "flex", alignItems: "center", gap: 20 }}><div style={{ width: 0, height: 0, borderLeft: "70px solid transparent", borderRight: "70px solid transparent", borderBottom: "120px solid #2FA84F" }} /><span style={{ fontFamily: "NeoHv", fontSize: 150, color: "#1F4E9E" }}>세모중공</span></div>}
      icons={[
        { node: <Disc name="ship" color="#2A6F97" />, x: 200, y: 140, w: 420, h: 420, at: 6 },
        { node: <Disc name="truck" color="#C0392B" />, x: 1760, y: 150, w: 420, h: 420, at: 30 },
        { node: <Disc name="gear" color="#E8A21E" />, x: 1760, y: 930, w: 420, h: 420, at: 54 },
        { node: <Disc name="factory" color="#555" />, x: 160, y: 930, w: 420, h: 420, at: 78 },
      ]} p={p} />
  </Flat>
);
// 16. 서명 파문 링 (ripple-ring-marker 병합)
const Ripple: React.FC<PP> = ({ p }) => (
  <Flat c="#8B7658">
    <Doc x={640} y={60} w={640} h={900} title="정주영 회장 의장 복귀" />
    <RippleRings x={1120} y={870} at={8} p={p} />
    <RippleRings x={760} y={236} at={60} p={{ dot: false, maxD: 240, width: 4, color: "#B74E47", ...p }} />
  </Flat>
);
// 17. 제품 스펙 핀
const Spec: React.FC<PP> = ({ p }) => (
  <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 45%, #d8d8d8, #8f8f8f)" }}>
    <Cut img="img/s05_bowl.png" x={460} y={240} w={1000} h={760} />
    <ProductSpecPins title={{ text: "세모 짜장면 MD", at: 6 }} pins={[
      { pt: [1180, 520], label: [1480, 380], lines: ["수타 면발", "140가닥"], at: 20 },
      { pt: [760, 700], label: [380, 820], lines: ["6시간 볶은 춘장"], at: 50 },
      { pt: [980, 450], label: [900, 250], lines: ["LCD 급", "윤기"], at: 80, gold: true },
    ]} p={p} />
  </AbsoluteFill>
);
// 18. TCG 카드 마키
const Tcg: React.FC<PP> = ({ p }) => (
  <Flat c="#CBD5CD">
    <TcgCardMarquee startX={620} cards={[
      { name: "우사장의 세모상사", img: "img/s03_woo.png", lines: ["1949년 창업", "무역·잡화"] },
      { name: "김씨의 동아상사", lines: ["1948년 창업", "무역"] },
      { name: "박씨의 대한물산", lines: ["면직물", "수출"] },
      { name: "꼬마의 화신무역", img: "img/s06_kid.png", lines: ["백화점", "무역"] },
      { name: "이씨의 삼양상회", lines: ["식품", "유통"] },
    ]} p={p} />
  </Flat>
);
// 19. 헤드라인 종이띠
const Head: React.FC<PP> = ({ p }) => (
  <Flat c="#B9C7B8">
    <HeadlineStripStack at={6} items={[
      { title: "故 우사장 상속 유언장 없다, 그러나…", sub: "우 회장 측 1988년 날인 '상속재산분할협의서' 공개", x: 110, y: 220, rot: -0.8 },
      { title: "세모家 소송전, 우사장 '유언장' 존재 공방…있다 vs 없다", sub: "3차 변론서 유언장 존재설 제기돼 주목", x: 520, y: 470, rot: 0.6 },
      { title: "세모가 상속소송 내일 첫 공판..쟁점은 무엇?", sub: "양측 첫 법정 대결 재계 관심 집중", x: 150, y: 720, rot: -0.4 },
    ]} p={p} />
  </Flat>
);
// 20. 확성기 원뿔
const Mega: React.FC<PP> = ({ p }) => (
  <AbsoluteFill>
    <Photo img="img/s06_crowd.jpg" dim={0.55} blur={8} />
    <MegaphoneCone x={1560} y={840} at={6} lines={[
      { text: "우사장의 성공신화 조작!", at: 32, d: 560, off: -190, size: 60, color: "#fff" },
      { text: "3세 승계 부당!!", at: 44, d: 600, off: -50, size: 80, color: "#111", underline: "#D83A2E" },
      { text: "그룹 차원에서", at: 70, d: 620, off: 70, size: 60, color: "#fff" },
      { text: "추진하는 사업!!", at: 74, d: 520, off: 150, size: 60, color: "#fff" },
    ]} p={p} />
  </AbsoluteFill>
);

export const DEMOS: Demo[] = [
  { name: "LoopArrow — 손글씨 루프 화살표(사진 앞 선행 드로우)", dur: 70, C: Loop, schema: LoopArrowParams },
  { name: "LabelChipSparkle — 라벨 칩 + 초록 반짝이 파티클", dur: 75, C: Chip, schema: LabelChipSparkleParams },
  { name: "NumberedReasonTab — 번호 사유 탭(좌측 도킹·하드컷 교체)", dur: 140, C: Tab, schema: NumberedReasonTabParams },
  { name: "ClipboardSwingDrop — 클립보드 문서 스윙 드롭·줄 리빌·서명", dur: 150, C: Clip, schema: ClipboardSwingDropParams },
  { name: "OrangePillStack — 오렌지 pill 세로 스택 목록", dur: 110, C: Pills, schema: OrangePillStackParams },
  { name: "FightingVsHud — 격투게임 VS 대결 HUD", dur: 90, C: Vs, schema: FightingVsHudParams },
  { name: "ProbabilityPill — 확률 수치 pill 라벨(시나리오 교체)", dur: 150, C: Prob, schema: ProbabilityPillParams },
  { name: "BigXStrike — 대형 X 표 스트라이크", dur: 75, C: XS, schema: BigXStrikeParams },
  { name: "CalendarTagSmoke — 탁상달력 연도 태그(연기 등장)", dur: 60, C: Cal, schema: CalendarTagSmokeParams },
  { name: "HangingIconDrop — 매달린 아이콘 드롭(끈+리본)+수치 라벨", dur: 110, C: Hang, schema: HangingIconDropParams },
  { name: "FeatheredSmokeBubble — 연기 가장자리 말풍선 → 다음 요소", dur: 140, C: Smoke, schema: FeatheredSmokeBubbleParams },
  { name: "ChecklistTick — 체크리스트 순차 체크 + APPROVED", dur: 150, C: Check, schema: ChecklistTickParams },
  { name: "QuestWindowDrop — 게임 퀘스트 창 드롭", dur: 75, C: Quest, schema: QuestWindowDropParams },
  { name: "DiagonalTapeTags — 대각 테이프 드로우 + 태그", dur: 120, C: Tape, schema: DiagonalTapeTagsParams },
  { name: "LogoEdgeIconsGather — 로고 주위 사업 아이콘 입장", dur: 110, C: LogoG, schema: LogoEdgeIconsGatherParams },
  { name: "RippleRings — 서명 파문 링 / 리플 링 마커", dur: 100, C: Ripple, schema: RippleRingsParams },
  { name: "ProductSpecPins — 제품 스펙 핀 콜아웃", dur: 115, C: Spec, schema: ProductSpecPinsParams },
  { name: "TcgCardMarquee — TCG 인물 카드 마키", dur: 150, C: Tcg, schema: TcgCardMarqueeParams },
  { name: "HeadlineStripStack — 기사 헤드라인 종이띠 스택", dur: 75, C: Head, schema: HeadlineStripStackParams },
  { name: "MegaphoneCone — 확성기 원뿔 텍스트", dur: 110, C: Mega, schema: MegaphoneConeParams },
];
export const GALLERY_DUR = Math.max(30, DEMOS.reduce((a, d) => a + d.dur, 0));
export const Gallery = runGallery(DEMOS);
