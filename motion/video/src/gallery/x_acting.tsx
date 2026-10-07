import React from "react";
import { AbsoluteFill, Img, useCurrentFrame } from "remotion";
import { runGallery, Demo } from "./runner";
import { W, H, src, Starburst, SweatDrop, Stamp, lerp } from "../fx";
import {
  MouthSwap, MouthSwapParams, GiantBlurEntry, GiantBlurEntryParams, FadeAccumulate, FadeAccumulateParams,
  ExpressionSwap, ExpressionSwapParams, RepeatGesture, RepeatGestureParams, ArmTween, ArmTweenParams,
  CostumeAdd, CostumeAddParams, MalletStrike, MalletStrikeParams, FaceBlur, FaceBlurParams,
  BoxingRound, BoxingRoundParams, WhackAMole, WhackAMoleParams, GlovePunchSwap, GlovePunchSwapParams, ThroneImg,
  BlurDimInterrupt, BlurDimInterruptParams, CircuitBg, SwordDuel, SwordDuelParams, 
  CreationHand, CreationHandParams, RopeSwing, RopeSwingParams, GrowthPot, GrowthPotParams,
  CrownKnockoff, CrownKnockoffParams, BrushDarkBg, OctopusMonster, OctopusMonsterParams, Marionette, MarionetteParams,
  BlobHead, BlobHeadParams, TreadmillWalk, TreadmillWalkParams, FlameSprite, FlameSpriteParams,
  WindLines, WindLinesParams, SaucePour, SaucePourParams, FlowerParticles, FlowerParticlesParams,
  TechAura, TechAuraParams, LaptopImg, ClappingHands, ClappingHandsParams, GlassCrack, GlassCrackParams,
  IdeaWarmBloom, IdeaWarmBloomParams, SpeechBubble, ElectricVortexSpawn, ElectricVortexParams,
  ConcentricDarkPulse, ConcentricDarkPulseParams, FloodRise, FloodRiseParams, ThoughtMaterialize, ThoughtMaterializeParams,
  SwirlBg, ColorDrain, ColorDrainParams, BurdenBallChain, BurdenBallChainParams,
  TechCircuitGlow, TechCircuitGlowParams, CarSideImg, CAR_WHEELS, PhotoFlameEyes, PhotoFlameEyesParams, EcgChestGlow, EcgChestGlowParams,
  XRig, XPose, PropImg, rigS, rigToScreen, handScreen, handPt, aimRot, 
} from "../lib/x_acting";
import { CastId, propH } from "../lib/kit";

type P = { p?: Record<string, any> };
type Pt = [number, number];
const Bg: React.FC<{ c: string }> = ({ c }) => <AbsoluteFill style={{ background: c }} />;
// 세모지 캐스트 4인 라인업(03·09·26 공용) — (x, 머리 꼭대기 y), 키 1000
const LINEUP: { c: CastId; x: number; top: number; pose: XPose }[] = [
  { c: "c5_chef", x: 330, top: 130, pose: { armL: "arm_raise_fist", face: "face_smile" } },
  { c: "c3_woman", x: 720, top: 170, pose: { face: "face_smile" } },
  { c: "walker1", x: 1180, top: 150, pose: { armR: "arm_raise_fist", face: "face_smile" } },
  { c: "c2_boss", x: 1600, top: 180, pose: {} },
];
const LH = 1000;
const lineupNode = (i: number) => { const m = LINEUP[i]; return <XRig key={m.c} cast={m.c} x={m.x} y={m.top + LH} h={LH} seed={`lu${i}`} pose={m.pose} />; };
const FACES: Pt[] = LINEUP.map((m) => [m.x, m.top + 125 * (LH / 1350)] as Pt).map(([x, y]) => [x, y + 40] as Pt);

// 01 입 교체 — 세모지 캐스트 흉상(walker1 청년 · c4_elder 노인), 입 = mouth_open 패치 교체
const D01: React.FC<P> = ({ p }) => (
  <AbsoluteFill>
    <Bg c="linear-gradient(180deg,#CFE7F2,#A9D2E4)" />
    <div style={{ position: "absolute", left: 0, right: 0, top: 820, bottom: 0, background: "#5FA7B5" }} />
    <MouthSwap at={6} seed="d1" p={p} render={(o) => <XRig cast="walker1" x={640} y={1110} h={1700} bust seed="d1a" pose={{ mouth: o }} />} />
    <MouthSwap at={6} seed="d1b" p={p} render={(o) => <XRig cast="c4_elder" x={1300} y={1110} h={1640} bust seed="d1b" pose={{ mouth: o }} />} />
  </AbsoluteFill>
);
// 02 거대 블러 줌아웃 등장 — c2_boss 전신
const D02: React.FC<P> = ({ p }) => (
  <AbsoluteFill>
    <Img src={src("img/s03_restaurant.jpg")} style={{ position: "absolute", inset: 0, width: W, height: H, objectFit: "cover" }} />
    <GiantBlurEntry at={6} anchor={[960, 1060]} p={p}>
      <XRig cast="c2_boss" x={960} y={1060} h={900} seed="d2" pose={{ armL: "arm_out_side" }} />
    </GiantBlurEntry>
  </AbsoluteFill>
);
// 03 알파 페이드 누적 — 세모지 캐스트 4인
const D03: React.FC<P> = ({ p }) => (
  <AbsoluteFill>
    <Bg c="radial-gradient(ellipse at 50% 40%,#C02424,#8E1414)" />
    <FadeAccumulate at={6} p={p} items={LINEUP.map((_, i) => <AbsoluteFill key={i}>{lineupNode(i)}</AbsoluteFill>)} />
  </AbsoluteFill>
);
// 04 표정 스왑 — c5_chef(한 팔 주먹 치켜듦·한 팔 가드) 기본 → face_grit 하드 스왑, 웍 소품
const chef4 = (sw: boolean) => <XRig cast="c5_chef" x={1000} y={1110} h={1600} bust seed="d4" pose={{ armL: "arm_raise_fist", armR: "arm_guard_fist", face: sw ? "face_grit" : undefined }} p={{ blinkEvery: 0 }} />;
const D04: React.FC<P> = ({ p }) => (
  <AbsoluteFill>
    <Bg c="linear-gradient(180deg,#1b1b1b,#6b6b6b)" />
    <ExpressionSwap at={24} origin={[1000, 1500]} p={p} before={chef4(false)} after={chef4(true)} />
    <PropImg id="wok" x={640} y={900} w={680} ax={0.34} ay={0.36} rot={-6} />
    <FlameSprite x={640} y={890} w={420} h={330} seed="d4" />
    <SweatDrop x={1120} y={330} at={26} s={1.6} />
    <Starburst text={"아오오\n힘들어!!!"} x={1450} y={430} at={28} />
  </AbsoluteFill>
);
// 05 반복 팔 동작 — c3_woman · c5_chef 가 주먹 든 팔(arm_raise_fist)을 어깨 축으로 흔든다(주먹 이동 = amp px)
const fistRot = (c: CastId, h: number, amp: number, k: number) => (-(amp * k) / (400 * rigS(c, h))) * (180 / Math.PI);
const D05: React.FC<P> = ({ p }) => (
  <AbsoluteFill>
    <Bg c="radial-gradient(ellipse at 50% 40%,#B3282A,#7E1415)" />
    {[380, 1540].map((x) => <div key={x} style={{ position: "absolute", left: x - 110, top: 160, width: 220, height: 420, borderRadius: 90, background: "#C23A2A", border: "10px solid #E2B04A" }} />)}
    <RepeatGesture at={6} p={p} render={(k, P) => <XRig cast="c3_woman" x={720} y={1110} h={1550} bust seed="d5a" pose={{ armL: "arm_raise_fist", rotL: -fistRot("c3_woman", 1550, P.amp, k) }} />} />
    <RepeatGesture at={6} second p={p} render={(k, P) => <XRig cast="c5_chef" x={1220} y={1110} h={1500} bust seed="d5b" pose={{ armR: "arm_raise_fist", rotR: fistRot("c5_chef", 1500, P.amp, k), mouth: true }} />} />
  </AbsoluteFill>
);
// 06 팔 1축 트윈 + 스윙(뚜껑 들기) — c5_chef 주먹 든 팔(arm_raise_fist)을 어깨 축으로 내렸다 들어올리고, 클로슈 뚜껑(cloche_lid)이 주먹에 붙어 따라감
const D06: React.FC<P> = ({ p }) => {
  const o = { x: 600, y: 1600, h: 1560 };
  const LW = 600, sc = LW / 1402, KNOB: Pt = [700, 52];                 // cloche 크롭 1402×870, 손잡이
  const r0 = 118, per = 120 / (362 * rigS("c5_chef", o.h)) * (180 / Math.PI);   // 뚜껑이 접시에 얹힌 팔 각도, 들어올림 거리(px)→각도
  const rest = handScreen("c5_chef", o, "arm_raise_fist", "l", r0);
  const box: Pt = [rest[0] - KNOB[0] * sc, rest[1] - KNOB[1] * sc];
  return (
    <AbsoluteFill>
      <Bg c="#B8642E" />
      <ArmTween at={6} pivot={[1030, 900]} p={p} render={(s, P) => {
        const rot = r0 - (P.liftDist / 120) * per * s.k + s.swing * 0.5;
        const hp = handScreen("c5_chef", o, "arm_raise_fist", "l", rot);
        return (
          <>
            <XRig cast="c5_chef" {...o} seed="d6" pose={{ armL: "arm_raise_fist", rotL: rot, eyesClosed: true }} />
            <PropImg id="cloche_plate" x={box[0]} y={box[1]} w={LW} ax={0} ay={0}>
              <div style={{ position: "absolute", left: LW * 0.5, top: (790 / 870) * propH("cloche_plate", LW), transform: "translate(-50%,-50%)", fontFamily: "NeoHv", fontSize: 22, color: "#fff", whiteSpace: "nowrap" }}>광동요리</div>
            </PropImg>
            <PropImg id="cloche_lid" x={hp[0]} y={hp[1]} w={LW} ax={KNOB[0] / 1402} ay={KNOB[1] / 870} rot={-28 * s.k + s.swing} />
          </>
        );
      }} />
    </AbsoluteFill>
  );
};
// 07 의상·소품 추가 — c3_woman 팔짱 + crown / royal_cape(back·collar) PNG
const D07: React.FC<P> = ({ p }) => {
  const o = { x: 930, y: 1700, h: 1380 };
  const head = rigToScreen("c3_woman", o, [505, 150]), neck = rigToScreen("c3_woman", o, [505, 452]);
  return (
    <AbsoluteFill>
      <Bg c="radial-gradient(ellipse at 50% 40%,#B9704F,#9C5638)" />
      <CostumeAdd at={10} p={p} crown={{ x: head[0], y: head[1], w: 190 }} cape={{ x: neck[0], y: neck[1], w: 820 }} tag={{ text: "딤섬의 여왕", x: 1180, y: 420, from: [1060, 500] }}>
        <XRig cast="c3_woman" {...o} seed="d7" pose={{ armFold: true }} />
      </CostumeAdd>
    </AbsoluteFill>
  );
};
// 08 의사봉 — gavel_hammer / gavel_block PNG
const D08: React.FC<P> = ({ p }) => (
  <AbsoluteFill>
    <Bg c="#5B6C8E" />
    <div style={{ position: "absolute", left: 960 - 420, top: 540 - 420, width: 840, height: 840, borderRadius: "50%", background: "#7A8DB5" }} />
    <MalletStrike at={6} x={760} y={730} p={p} />
  </AbsoluteFill>
);
// 09 비핵심 인물 얼굴 블러 — 세모지 캐스트 4인(1·2·4번 얼굴 블러)
const D09: React.FC<P> = ({ p }) => {
  const f = useCurrentFrame();
  const s = 1 + 0.06 * (f / 90);
  const scene = (
    <AbsoluteFill>
      <Bg c="radial-gradient(ellipse at 50% 40%,#C02424,#8E1414)" />
      {LINEUP.map((_, i) => lineupNode(i))}
    </AbsoluteFill>
  );
  return (
    <AbsoluteFill style={{ transform: `scale(${s})` }}>
      {f < 6 ? scene : <FaceBlur p={p} faces={[FACES[0], FACES[1], FACES[3]].map(([x, y]) => ({ x, y }))}>{scene}</FaceBlur>}
      <div style={{ position: "absolute", left: 1700, top: 170, fontFamily: "Jalnan", fontSize: 64, color: "#fff", WebkitTextStroke: "3px #222", transform: "rotate(-8deg)" }}>OK!</div>
    </AbsoluteFill>
  );
};
// 10 복싱 라운드 — walker1 · c2_boss(반전) 가드 팔(arm_guard_fist) + 손에 boxing_glove_red/blue PNG(팔 레이어 안이라 팔을 따라감)
const glove = (c: CastId, side: "r" | "l", id: string) => { const [hx, hy] = handPt(c, "arm_guard_fist", side); return <PropImg id={id} x={hx + (side === "r" ? -75 : 75)} y={hy - 10} w={240} rot={side === "r" ? -75 : -105} flipX={side === "l"} />; };
const boxer = (c: CastId, x: number, id: string, flip: boolean) => (
  <XRig cast={c} x={x} y={1110} h={1500} bust flip={flip} seed={c} pose={{ armR: "arm_guard_fist", armL: "arm_guard_fist", face: "face_angry" }} itemR={glove(c, "r", id)} itemL={glove(c, "l", id)} />
);
const D10: React.FC<P> = ({ p }) => (
  <BoxingRound at={0} p={p} round="ROUND2" labels={[{ text: "하드웨어가\n먼저야!", x: 250, y: 250 }, { text: "제품 전략이\n먼저지!", x: 1680, y: 250 }]}
    left={boxer("walker1", 560, "boxing_glove_red", false)} right={boxer("c2_boss", 1360, "boxing_glove_blue", true)} />
);
// 11 두더지 뿅망치 — c3_woman 두 주먹 치켜듦 + face_sparkle·입 벌림, toy_hammer PNG
const D11: React.FC<P> = ({ p }) => (
  <WhackAMole at={6} p={p}
    char={<XRig cast="c3_woman" x={960} y={1720} h={1420} seed="d11" pose={{ armR: "arm_raise_fist", armL: "arm_raise_fist", rotR: -12, rotL: 12, face: "face_sparkle", mouth: true }} />}
    bubble={(a) => <Starburst text={"이 광고는\n꼭 내보내야 해!"} x={470} y={420} w={520} h={340} at={a} size={52} />} />
);
// 12 권투 글러브 펀치 교체 — throne PNG 위 앉은 c2_boss(legs_sit) → walker1(legs_sit, 웃음), 옆에 선 c4_elder(주먹)
const seat = (x: number, y: number, c: CastId, face?: string) => {
  const s = 0.5, h = (CAST_H[c]) * s, seatY = 930;          // 캔버스 엉덩이 높이 ≈ 930
  return (
    <AbsoluteFill>
      <ThroneImg x={x} y={y} w={420} />
      <XRig cast={c} x={x} y={y + (CAST_FEET[c] - seatY) * s} h={h} seed={c} pose={{ legs: "legs_sit", face }} />
    </AbsoluteFill>
  );
};
const CAST_H: Record<string, number> = { walker1: 1335, c2_boss: 1353 }, CAST_FEET: Record<string, number> = { walker1: 1433, c2_boss: 1442 };
const D12: React.FC<P> = ({ p }) => (
  <AbsoluteFill>
    <Bg c="#35404E" />
    <div style={{ position: "absolute", left: 300, top: 60, width: 960, height: 960, borderRadius: "50%", background: "#46546A" }} />
    <XRig cast="c4_elder" x={1520} y={1110} h={1450} bust seed="d12e" pose={{ armL: "arm_raise_fist", face: "face_smile" }} />
    <GlovePunchSwap at={10} x={760} y={520} p={p} oldNode={seat(760, 520, "c2_boss")} newNode={seat(760, 520, "walker1", "face_smile")} />
  </AbsoluteFill>
);
// 13 배경 블러·딤 인터럽트 — chips_box · cpu_chip PNG(글자는 코드) + walker1 손바닥 STOP(arm_palm_stop)
const D13: React.FC<P> = ({ p }) => (
  <BlurDimInterrupt at={8} p={p}
    bg={<AbsoluteFill><CircuitBg bg="#0B1440" period={30} />
      <PropImg id="chips_box" x={420} y={520} w={520}><div style={{ position: "absolute", left: "58%", top: "16%", transform: "translate(-50%,-50%) rotate(-4deg)", fontFamily: "NeoHv", fontSize: 76, color: "#2B6FD6" }}>CHIPS</div></PropImg>
      <PropImg id="cpu_chip" x={1330} y={470} w={500} style={{ filter: "drop-shadow(0 0 40px #29D3FF)" }}><div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "Jalnan", fontSize: 130, color: "#0B1440" }}>X86</div></PropImg></AbsoluteFill>}
    narrator={<XRig cast="walker1" x={760} y={1110} h={1500} bust seed="d13" pose={{ armR: "arm_palm_stop" }} />}
    bubble={{ x: 1180, y: 330, w: 420, h: 250, text: "CPU에서의\n아키텍처란?" }} />
);
// 14 칼싸움 — walker1(arm_raise_fist) · c2_boss(반전, arm_up_hang)의 주먹을 칼자루 쪽으로 겨누고(aimRot), sword PNG 를 손에서 충돌점으로
const D14: React.FC<P> = ({ p }) => {
  const clash: Pt = [960, 300];
  const L = { cast: "walker1" as CastId, arm: "arm_raise_fist", x: 420, flip: false, face: "face_angry" }, R = { cast: "c2_boss" as CastId, arm: "arm_up_hang", x: 1500, flip: true, face: "face_angry" };
  return (
    <SwordDuel at={6} clash={clash} p={p} render={(wl, wr) => {
      const draw = (c: typeof L, wob: number, dir: 1 | -1) => {
        const o = { x: c.x, y: 1110, h: 1450, bust: true, flip: c.flip };
        const grip: Pt = [clash[0] - dir * 300, clash[1] + 500];
        const rot = aimRot(c.cast, o, c.arm, "l", grip);
        const hp = handScreen(c.cast, o, c.arm, "l", c.flip ? -rot : rot);
        const ang = (Math.atan2(clash[1] - hp[1], clash[0] - hp[0]) * 180) / Math.PI - 90 + wob;
        return (
          <>
            <XRig cast={c.cast} {...o} seed={c.cast} pose={{ armL: c.arm, rotL: rot, face: c.face }} />
            <PropImg id="sword" x={hp[0]} y={hp[1]} w={250} ax={153 / 316} ay={176 / 1207} rot={ang} />
          </>
        );
      };
      return <>{draw(L, wl, 1)}{draw(R, -wr, -1)}</>;
    }} />
  );
};
// 15 천지창조 손 — c2_boss 몸 뒤로 기울임(tilt) + arm_reach 로 손끝 쪽을 겨눔, 관찰자 walker1 팔짱, creation_forearm/hand PNG
const D15: React.FC<P> = ({ p }) => {
  const o = { x: 1000, y: 1110, h: 1450, bust: true };
  return (
    <CreationHand at={6} tip={[640, 360]} p={p}
      other={<XRig cast="walker1" x={1620} y={1110} h={1400} bust seed="d15o" pose={{ armFold: true }} />}
      char={<XRig cast="c2_boss" {...o} tilt={-10} seed="d15" pose={{ armR: "arm_reach", rotR: 58, face: "face_worried", mouth: true }} />} />
  );
};
// 16 밧줄 건너뛰기 — c2_boss 전신 매달림(arm_up_hang 양팔을 안쪽으로 모아 한 점을 쥠 + legs_dangle). 손 잡는 점 = 로컬 (0,0)
const ropeChar = (() => {
  const h = 560, s = rigS("c2_boss", h), grip: Pt = [503, 112];     // 두 주먹(±8° 안쪽) 사이, 머리 위
  return <XRig cast="c2_boss" x={0} y={(1442 - grip[1]) * s} h={h} seed="d16" pose={{ armR: "arm_up_hang", armL: "arm_up_hang", rotR: 8, rotL: -8, legs: "legs_dangle", face: "face_grit" }} />;
})();
const D16: React.FC<P> = ({ p }) => <RopeSwing at={6} char={ropeChar} p={p} />;
// 17 화분 성장 — flower_pot(pot_leaves/pot_body) · office_building_small · watering_can PNG
const D17: React.FC<P> = ({ p }) => <GrowthPot at={6} p={p} />;
// 18 왕관 날아감 — c4_elder 흉상(웃는 눈) + crown PNG(글자 코드)
const D18: React.FC<P> = ({ p }) => (
  <AbsoluteFill>
    <BrushDarkBg />
    <CrownKnockoff at={16} x={960} y={290} w={240} text="명예회장" p={p}>
      <XRig cast="c4_elder" x={960} y={1110} h={1520} bust seed="d18" pose={{ face: "face_smile" }} />
    </CrownKnockoff>
  </AbsoluteFill>
);
// 19 은유 괴물 — octopus_body/tentacle · cargo_ship PNG
const D19: React.FC<P> = ({ p }) => (
  <AbsoluteFill>
    <Bg c="linear-gradient(180deg,#B6B2DA 0%,#D9D2EC 55%,#E6F4F7 72%,#BFE6EE 100%)" />
    <div style={{ position: "absolute", left: 0, right: 0, top: 740, bottom: 0, background: "linear-gradient(180deg,#CDEFF5,#9FD9E6)" }} />
    <OctopusMonster at={6} x={620} y={700} p={p} />
  </AbsoluteFill>
);
// 20 꼭두각시 — c2_boss 전신(arm_out_side 양팔 수평)
const D20: React.FC<P> = ({ p }) => (
  <AbsoluteFill>
    <Marionette at={8} bg="real/chinatown.jpg" x={1260} y={660} p={p} />
    <Stamp text="합병" x={420} y={640} at={-20} />
  </AbsoluteFill>
);
// 21 먹덩이 의인화 — c2_boss 흉상 몸 + inkblob_head PNG 머리
const D21: React.FC<P> = ({ p }) => <BlobHead at={6} x={900} y={1090} bg="real/port.jpg" p={p} />;
// 22 제자리 걷기 트랙
const D22: React.FC<P> = ({ p }) => <TreadmillWalk at={6} x0={360} p={p} milestones={[{ x: 330, label: "문산성 서당\n수송보통학교" }, { x: 1640, label: "중동중학교\n단기 속성과" }]} />;
// 23 불꽃 스프라이트 — c5_chef 두 팔 들기(arm_hold, 몸 앞) + wok PNG
const D23: React.FC<P> = ({ p }) => (
  <AbsoluteFill>
    <Bg c="radial-gradient(ellipse at 50% 40%,#A21C38,#5E0C1C)" />
    <div style={{ position: "absolute", left: 0, right: 0, top: 800, bottom: 0, background: "#9A9A9A" }} />
    <XRig cast="c5_chef" x={960} y={1080} h={1450} bust seed="d23" pose={{ armR: "arm_hold", armL: "arm_hold", face: "face_smile" }} />
    <PropImg id="wok" x={960} y={820} w={720} ax={0.34} ay={0.3} />
    <FlameSprite at={6} x={960} y={840} w={520} h={260} p={p} />
  </AbsoluteFill>
);
// 24 바람선 — tree_round PNG
const D24: React.FC<P> = ({ p }) => (
  <AbsoluteFill>
    <Bg c="linear-gradient(180deg,#7C8FD6 0%,#A9C3EC 60%,#E9F1FA 100%)" />
    <svg width={W} height={H} style={{ position: "absolute" }}>
      <path d="M0,700 L300,380 L560,640 L860,300 L1200,660 L1500,420 L1920,720 L1920,1080 L0,1080Z" fill="#8C8FD0" />
      <path d="M0,820 C500,760 1300,860 1920,800 L1920,1080 L0,1080Z" fill="#F4F7FC" />
    </svg>
    <PropImg id="tree_round" x={230} y={900} w={600} ax={0.5} ay={1} />
    <WindLines at={6} p={p} />
  </AbsoluteFill>
);
// 25 소스 붓기
const D25: React.FC<P> = ({ p }) => (
  <AbsoluteFill>
    <Bg c="radial-gradient(ellipse at 50% 40%,#FBE3C2,#F4B79A)" />
    <SaucePour at={6} x={900} y={500} p={p} />
  </AbsoluteFill>
);
// 26 꽃 파티클 — 세모지 캐스트 4인 머리 위
const HEADS: Pt[] = LINEUP.map((m) => [m.x, m.top + 20] as Pt);
const D26: React.FC<P> = ({ p }) => (
  <AbsoluteFill>
    <Bg c="#B8612F" />
    {LINEUP.map((_, i) => lineupNode(i))}
    <FlowerParticles at={6} heads={[HEADS[0], HEADS[2]]} p={p} />
    <FlowerParticles at={36} heads={[HEADS[1], HEADS[3]]} seed="f2" p={p} />
  </AbsoluteFill>
);
// 27 테크 오라 — c2_boss 양팔 벌려 손바닥 위(arm_out_side) + laptop PNG
const D27: React.FC<P> = ({ p }) => (
  <AbsoluteFill>
    <Bg c="radial-gradient(ellipse at 50% 60%,#16407A,#050F24)" />
    {Array.from({ length: 60 }, (_, i) => <div key={i} style={{ position: "absolute", left: (i * 331) % W, top: (i * 197) % H, width: 3, height: 3, borderRadius: 2, background: "#cfe" }} />)}
    <XRig cast="c2_boss" x={960} y={1110} h={1400} bust seed="d27" pose={{ armR: "arm_out_side", armL: "arm_out_side", rotR: -12, rotL: 12 }} />
    <TechAura at={6} x={960} y={790} p={{ ringR: 210, ...p }} object={<LaptopImg x={960} y={790} w={320} />} />
  </AbsoluteFill>
);
// 28 전경 박수 — c3_woman 두 팔로 held_box 들기(arm_hold) + clapping_palm PNG
const D28: React.FC<P> = ({ p }) => (
  <AbsoluteFill>
    <Bg c="linear-gradient(180deg,#8E9398,#5E6368)" />
    {Array.from({ length: 9 }, (_, i) => <div key={i} style={{ position: "absolute", left: i * 230 - 60, top: 140 + (i % 2) * 60, width: 260, height: 900, borderRadius: "130px 130px 0 0", background: i % 2 ? "#6E7378" : "#7B8085" }} />)}
    <XRig cast="c3_woman" x={960} y={1780} h={1450} seed="d28" pose={{ armR: "arm_hold", armL: "arm_hold", face: "face_smile" }}
      over={<PropImg id="held_box" x={505} y={760} w={330} />} />
    <ClappingHands at={6} p={p} />
  </AbsoluteFill>
);
// 29 유리 깨짐
const D29: React.FC<P> = ({ p }) => (
  <AbsoluteFill>
    <Bg c="radial-gradient(ellipse at 50% 50%,#D8283A 20%,#7A0E18 100%)" />
    <div style={{ position: "absolute", left: 700, top: 220, width: 900, height: 620, background: "#D9D9D9", border: "6px solid #222", boxShadow: "8px 8px 0 #111" }}>
      <div style={{ height: 44, background: "repeating-linear-gradient(0deg,#bbb 0 4px,#ddd 4px 8px)", borderBottom: "4px solid #222" }} />
      {Array.from({ length: 8 }, (_, i) => <div key={i} style={{ margin: "18px 30px", height: 28, width: 400 + (i % 3) * 120, background: i === 3 ? "#6E75C9" : "#EFEFEF", border: "2px solid #999" }} />)}
    </div>
    <GlassCrack at={6} x={1030} y={450} p={p} />
    <Stamp text="실패" x={1150} y={560} at={50} />
  </AbsoluteFill>
);
// 30 깨달음 웜 블룸 — c3_woman 턱 괴고 생각(arm_hand_chin)
const D30: React.FC<P> = ({ p }) => (
  <IdeaWarmBloom at={24} x={1300} y={900} p={p}
    next={<AbsoluteFill><Bg c="linear-gradient(180deg,#F2A541 0%,#F6C35B 40%,#8B5E4A 60%,#6E4A3E 100%)" /><svg width={W} height={H} style={{ position: "absolute" }}><path d="M860,650 L1060,650 L1500,1080 L420,1080Z" fill="#3A3A40" /><path d="M960,660 L960,1080" stroke="#fff" strokeWidth={10} strokeDasharray="40 40" /></svg></AbsoluteFill>}>
    <AbsoluteFill>
      <Bg c="#2A2A2A" />
      <XRig cast="c3_woman" x={760} y={1760} h={1450} seed="d30" pose={{ armL: "arm_hand_chin" }} />
      <SpeechBubble x={1180} y={260} w={440} h={220} text="소프트웨어가 답이다" />
    </AbsoluteFill>
  </IdeaWarmBloom>
);
// 31 전기 소용돌이 등장 (= 에너지 포탈 링) — dram_chip PNG(글자는 코드)
const Chip: React.FC<{ x: number; y: number; label: string }> = ({ x, y, label }) => (
  <PropImg id="dram_chip" x={x} y={y} w={500}>
    <div style={{ position: "absolute", left: "50%", top: "36%", transform: "translate(-50%,-50%)", fontFamily: "NeoHv", fontSize: 46, color: "#fff", whiteSpace: "nowrap" }}>{label}</div>
  </PropImg>
);
const D31: React.FC<P> = ({ p }) => {
  const f = useCurrentFrame();
  const rk = lerp(f, 32, 36, 0, 1);
  return (
    <AbsoluteFill>
      <Bg c="#C4CFC6" />
      <ElectricVortexSpawn at={6} x={960} y={560} r={150} p={p} object={<Chip x={960} y={570} label="256K DRAM" />} />
      {f >= 32 && <div style={{ position: "absolute", left: 960 - 140, top: 330 - 120 * (1 - rk), opacity: rk, background: "#E0283A", color: "#fff", fontFamily: "Jalnan", fontSize: 46, padding: "8px 36px", clipPath: "polygon(0 0,100% 0,92% 50%,100% 100%,0 100%,8% 50%)" }}>신상품</div>}
    </AbsoluteFill>
  );
};
// 32 동심원 암흑 펄스 — powder_pile PNG
const D32: React.FC<P> = ({ p }) => {
  const f = useCurrentFrame();
  const k = lerp(f, 50, 56, 0, 1);
  return (
    <AbsoluteFill>
      <ConcentricDarkPulse at={6} p={p} />
      {f >= 50 && <PropImg id="powder_pile" x={960} y={470} w={520} style={{ transform: `scale(${0.3 + 0.7 * k})`, filter: k < 1 ? `blur(${10 * (1 - k)}px)` : undefined }} />}
      {f >= 62 && <div style={{ position: "absolute", left: 960, top: 690, transform: "translateX(-50%)", background: "#8C2E36", color: "#fff", fontFamily: "NeoHv", fontSize: 48, padding: "6px 26px", borderRadius: 8 }}>코카인</div>}
    </AbsoluteFill>
  );
};
// 33 홍수 — walker1 3명(양 주먹 arm_raise_fist 펌프, face_angry), 가운데만 hard_hat PNG
const D33: React.FC<P> = ({ p }) => {
  const f = useCurrentFrame();
  const pump = (i: number) => Math.sin(((f + i * 3) / 6) * Math.PI);
  return (
    <FloodRise at={30} focus={[960, 420]} p={{ silAt: 45, ...p }}
      bg={<AbsoluteFill><Bg c="linear-gradient(180deg,#C9CED8,#A9B2C0)" />{Array.from({ length: 8 }, (_, i) => <div key={i} style={{ position: "absolute", left: i * 260 + 40, top: 80, width: 170, height: 300, background: "#E6EAF0", border: "8px solid #8D96A6" }} />)}</AbsoluteFill>}
      render={(bob, sil) => [560, 960, 1360].map((x, i) => (
        <div key={i} style={{ position: "absolute", inset: 0, filter: i !== 1 && sil > 0 ? `brightness(${1 - 0.75 * sil}) saturate(${1 - sil})` : undefined }}>
          <XRig cast="walker1" x={x} y={720 + bob * (i % 2 ? 1 : -1)} h={800} bust seed={`d33${i}`} pose={{ armR: "arm_raise_fist", armL: "arm_raise_fist", rotR: -10 + 10 * pump(i), rotL: 10 - 10 * pump(i), face: "face_angry" }}
            over={i === 1 ? <PropImg id="hard_hat" x={509} y={130} w={390} /> : undefined} />
        </div>
      ))} />
  );
};
// 34 떠오른 이미지 블러 물질화 — c3_woman 가리킴 + c2_boss 놀람(face_wide) + banknote_500 PNG
const D34: React.FC<P> = ({ p }) => (
  <AbsoluteFill>
    <SwirlBg />
    <XRig cast="c3_woman" x={400} y={1720} h={1400} seed="d34w" pose={{ armL: "arm_point", rotL: -28, face: "face_sparkle" }} />
    <XRig cast="c2_boss" x={1400} y={1110} h={1450} bust seed="d34" pose={{ face: "face_wide" }} />
    <div style={{ position: "absolute", left: 1640, top: 130, fontFamily: "Jalnan", fontSize: 90, color: "#fff" }}>!!</div>
    <ThoughtMaterialize at={6} p={p}>
      <PropImg id="banknote_500" x={880} y={330} w={440}>
        <div style={{ position: "absolute", left: "76%", top: "55%", transform: "translate(-50%,-50%)", fontFamily: "MyeongjoEB", fontSize: 30, color: "#5E6D5A", whiteSpace: "nowrap" }}>오백원</div>
      </PropImg>
    </ThoughtMaterialize>
  </AbsoluteFill>
);
// 35 컬러 드레인 — 세모지 캐스트 군중(크기·반전·seed 변주) + walker1(주먹 → 내리고 face_frown). 흑백화는 ColorDrain 필터가 캐릭터에 그대로 걸림
const FIST = (c: CastId) => (c === "c2_boss" ? "arm_up_hang" : "arm_raise_fist");     // c2_boss 는 raise_fist 그림이 없어 up_hang
const CAST5: CastId[] = ["c2_boss", "c3_woman", "c5_chef", "c4_elder", "walker1"];
const CROWD35 = Array.from({ length: 11 }, (_, i) => ({ c: CAST5[i % 5], x: -40 + i * 200, pose: (i % 3 === 0 ? { armL: FIST(CAST5[i % 5]) } : i % 3 === 1 ? { armR: FIST(CAST5[i % 5]) } : {}) as XPose }));
const D35: React.FC<P> = ({ p }) => {
  const f = useCurrentFrame(), down = f >= 10;
  return (
    <ColorDrain at={8} p={p}>
      <Bg c="linear-gradient(180deg,#8FD0EE,#C9E8F4)" />
      <svg width={W} height={H} style={{ position: "absolute" }}>{Array.from({ length: 10 }, (_, i) => <rect key={i} x={i * 200} y={300 + (i % 3) * 60} width={170} height={800} fill="#7F95A6" />)}<circle cx={1500} cy={200} r={90} fill="#fff" opacity={0.7} /></svg>
      {CROWD35.map((m, i) => <XRig key={i} cast={m.c} x={m.x} y={1180 + (i % 2) * 40} h={560 + (i % 3) * 30} flip={i % 2 === 1} seed={`c35${i}`} pose={m.pose} style={{ filter: `brightness(${0.8 + 0.05 * (i % 3)})` }} />)}
      <XRig cast="walker1" x={960} y={1110} h={1500} bust seed="d35" pose={down ? { face: "face_frown" } : { armL: "arm_raise_fist", mouth: true }} />
    </ColorDrain>
  );
};
// 36 족쇄 쇳덩이 — 배경 경영진 c2_boss · walker1 · c4_elder, money_sack · iron_ball · chain_link PNG
const D36: React.FC<P> = ({ p }) => (
  <BurdenBallChain at={6} p={p} bg={<AbsoluteFill><Bg c="radial-gradient(ellipse at 50% 30%,#3A3A3A,#141414)" />
    {([["c2_boss", 480], ["walker1", 960], ["c4_elder", 1440]] as [CastId, number][]).map(([c, x], i) => <XRig key={c} cast={c} x={x} y={1110} h={1350} bust seed={c} pose={{ face: i === 1 ? "face_grit" : undefined }} />)}</AbsoluteFill>} />
);
// 37 회로 부품 발광 — car_sedan_side PNG(왼쪽이 앞바퀴)
const CAR = { x: 420, y: 420, w: 1080 };
const D37: React.FC<P> = ({ p }) => (
  <TechCircuitGlow at={6} p={p} product={<CarSideImg {...CAR} />}
    parts={[["전륜구동", 0], ["후륜구동", 1]].map(([label, i]) => ({ x: CAR.x + CAR_WHEELS[i as number][0] * (CAR.w / 1430), y: CAR.y + CAR_WHEELS[i as number][1] * (CAR.w / 1430), r: 96, label: label as string }))} />
);
// 38 사진(배경) 앞 인물 눈에 불꽃 스티커 — c2_boss 흉상(face_angry), 눈 위치 = 캔버스 눈 좌표 → rigToScreen
const D38O = { x: 960, y: 1110, h: 1500, bust: true };
const D38: React.FC<P> = ({ p }) => {
  return (
    <AbsoluteFill>
      <Img src={src("real/museum.jpg")} style={{ position: "absolute", inset: 0, width: W, height: H, objectFit: "cover", filter: "blur(6px) brightness(0.7)" }} />
      <PhotoFlameEyes at={8} p={p} eyes={[rigToScreen("c2_boss", D38O, [461, 290]), rigToScreen("c2_boss", D38O, [543, 290])]}>
        <XRig cast="c2_boss" {...D38O} seed="d38" pose={{ face: "face_angry" }} />
      </PhotoFlameEyes>
    </AbsoluteFill>
  );
};
// 39 심전도 + 가슴 글로우 — c2_boss 고통(face_squint) + 가슴에 손(arm_hand_chest) + 이마 그늘(코드), lightning_heart PNG
const PAIN_O = { x: 620, y: 1110, h: 1450, bust: true };
const painOver = (
  <>
    <div style={{ position: "absolute", left: 360, top: 110, width: 300, height: 170, borderRadius: "150px 150px 20px 20px", background: "linear-gradient(180deg, rgba(79,99,201,0.85), rgba(79,99,201,0))" }} />
    <svg width={1024} height={1536} style={{ position: "absolute", left: 0, top: 0 }}>{[0, 1, 2].map((i) => <path key={i} d={`M${300 - i * 20},${170 + i * 36} l-50,-22`} stroke="#222" strokeWidth={9} strokeLinecap="round" />)}</svg>
  </>
);
const D39: React.FC<P> = ({ p }) => (
  <EcgChestGlow at={0} chest={rigToScreen("c2_boss", PAIN_O, [470, 640])} heart={[1240, 470]} p={p}
    char={<XRig cast="c2_boss" {...PAIN_O} seed="d39" pose={{ armL: "arm_hand_chest", face: "face_squint" }} over={painOver} />}
    bubble={(a) => <Starburst text="으..윽!" x={900} y={340} w={300} h={200} at={a} size={50} p={{ popLen: 5 }} />} />
);

export const DEMOS: Demo[] = [
  { name: "MouthSwap — 말하는 입 불규칙 교체(4~6f)", dur: 90, C: D01, schema: MouthSwapParams },
  { name: "GiantBlurEntry — 거대 블러 줌아웃 등장", dur: 60, C: D02, schema: GiantBlurEntryParams },
  { name: "FadeAccumulate — 알파 페이드 누적 · 겹쳤다 분리", dur: 120, C: D03, schema: FadeAccumulateParams },
  { name: "ExpressionSwap — 표정 하드 스왑(> <)", dur: 80, C: D04, schema: ExpressionSwapParams },
  { name: "RepeatGesture — 반복 팔 동작(두 인물 엇갈림)", dur: 90, C: D05, schema: RepeatGestureParams },
  { name: "ArmTween — 팔 1축 트윈 + 스윙(뚜껑 들기)", dur: 90, C: D06, schema: ArmTweenParams },
  { name: "CostumeAdd — 왕관·망토 추가 + 네임태그", dur: 75, C: D07, schema: CostumeAddParams },
  { name: "MalletStrike — 의사봉 정지→내리치기", dur: 80, C: D08, schema: MalletStrikeParams },
  { name: "FaceBlur — 비핵심 인물 얼굴 블러", dur: 90, C: D09, schema: FaceBlurParams },
  { name: "BoxingRound — 복싱 링 라이벌 + ROUND 표기", dur: 100, C: D10, schema: BoxingRoundParams },
  { name: "WhackAMole — 두더지 구멍 + 뿅망치", dur: 90, C: D11, schema: WhackAMoleParams },
  { name: "GlovePunchSwap — 글러브 펀치로 인물 교체", dur: 100, C: D12, schema: GlovePunchSwapParams },
  { name: "BlurDimInterrupt — 배경 블러·딤 + 해설 인물 STOP", dur: 90, C: D13, schema: BlurDimInterruptParams },
  { name: "SwordDuel — 불꽃 배경 칼싸움 + 스파크", dur: 100, C: D14, schema: SwordDuelParams },
  { name: "CreationHand — 천지창조 손 패러디", dur: 80, C: D15, schema: CreationHandParams },
  { name: "RopeSwing — 밧줄 건너뛰기(카메라 추적)", dur: 150, C: D16, schema: RopeSwingParams },
  { name: "GrowthPot — 화분 성장 은유", dur: 90, C: D17, schema: GrowthPotParams },
  { name: "CrownKnockoff — 왕관 흔들리다 날아감", dur: 70, C: D18, schema: CrownKnockoffParams },
  { name: "OctopusMonster — 은유 괴물(문어) + 라벨", dur: 80, C: D19, schema: OctopusMonsterParams },
  { name: "Marionette — 꼭두각시 조종자(권력 구슬)", dur: 90, C: D20, schema: MarionetteParams },
  { name: "BlobHead — 먹덩이 얼굴 의인화", dur: 80, C: D21, schema: BlobHeadParams },
  { name: "TreadmillWalk — 걷기 + 발자국·이정표 트랙", dur: 150, C: D22, schema: TreadmillWalkParams },
  { name: "FlameSprite — 불꽃 스프라이트 루프", dur: 60, C: D23, schema: FlameSpriteParams },
  { name: "WindLines — 바람선 스크리블", dur: 60, C: D24, schema: WindLinesParams },
  { name: "SaucePour — 뚜껑 튀고 소스 붓기", dur: 70, C: D25, schema: SaucePourParams },
  { name: "FlowerParticles — 머리 위 꽃 파티클 팝", dur: 60, C: D26, schema: FlowerParticlesParams },
  { name: "TechAura — 홀로그램 테크 오라", dur: 80, C: D27, schema: TechAuraParams },
  { name: "ClappingHands — 전경 박수 손 루프", dur: 60, C: D28, schema: ClappingHandsParams },
  { name: "GlassCrack — 유리 깨짐 크랙 하드컷", dur: 90, C: D29, schema: GlassCrackParams },
  { name: "IdeaWarmBloom — 깨달음 웜 블룸 → 하드컷", dur: 60, C: D30, schema: IdeaWarmBloomParams },
  { name: "ElectricVortexSpawn — 전기 소용돌이 링 등장", dur: 60, C: D31, schema: ElectricVortexParams },
  { name: "ConcentricDarkPulse — 동심원 암흑 펄스", dur: 90, C: D32, schema: ConcentricDarkPulseParams },
  { name: "FloodRise — 홍수 줌아웃 + 수위 상승", dur: 110, C: D33, schema: FloodRiseParams },
  { name: "ThoughtMaterialize — 떠오른 이미지 블러 물질화", dur: 60, C: D34, schema: ThoughtMaterializeParams },
  { name: "ColorDrain — 컬러 드레인(점진 흑백화)", dur: 60, C: D35, schema: ColorDrainParams },
  { name: "BurdenBallChain — 돈자루 + 족쇄 쇳덩이 슬램", dur: 60, C: D36, schema: BurdenBallChainParams },
  { name: "TechCircuitGlow — 회로 배경 부품 발광(전→후)", dur: 100, C: D37, schema: TechCircuitGlowParams },
  { name: "PhotoFlameEyes — 사진 눈에 불꽃 스티커", dur: 60, C: D38, schema: PhotoFlameEyesParams },
  { name: "EcgChestGlow — 심전도 배경 + 가슴 통증 글로우", dur: 90, C: D39, schema: EcgChestGlowParams },
];
export const GALLERY_DUR = Math.max(30, DEMOS.reduce((a, d) => a + d.dur, 0));
export const Gallery = runGallery(DEMOS);
