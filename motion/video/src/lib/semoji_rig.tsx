// 세모지 그림체 캐릭터 리그 — codex 이미지젠으로 부위별로 그린 투명 PNG(같은 1024×1536 캔버스, 같은 좌표)를 겹쳐 쓴다.
// 걷기 = 다리 포즈 그림 4장 교대(hold) + 패스 포즈에서 몸 들썩임 + 팔 흔들림(어깨 축 회전). 눈 깜빡임·입 벌림은 얼굴 패치 레이어 교체.
// 같은 PNG를 AE 레이어로도 쓴다(ae 생성기). 에셋: public/kit/<rig>/
import React from "react";
import { Img, staticFile, useCurrentFrame, random } from "remotion";
import { z } from "zod";
import { num, choice, def } from "../params/p";

/** 불규칙 입 교체: t(≥0) 에서 입이 벌어져 있는가 — 시드로 정한 min~max f 간격으로 개폐 교대(벌림부터) [설명형 레퍼런스 카툰 4~8f] */
export const talkOpenRandom = (t: number, seed: string | undefined, min: number, max: number) => {
  if (t < 0) return false;
  const lo = Math.max(1, Math.round(Math.min(min, max))), hi = Math.max(lo, Math.round(Math.max(min, max)));
  let c = 0, i = 0;
  while (i < 100000) { const len = lo + Math.floor(random(`${seed ?? "talk"}t${i}`) * (hi - lo + 1)); if (t < c + len) return i % 2 === 0; c += len; i++; }
  return false;
};

export type RigSpec = {
  dir: string; w: number; h: number;
  feet: [number, number];            // 캔버스에서 두 발 사이 바닥점
  top: number;                        // 머리 꼭대기 y (키 계산)
  shoulderR: [number, number]; shoulderL: [number, number];   // 화면 왼쪽 팔(=인물 오른팔), 화면 오른쪽 팔
  walk: string[];                     // 걷기 사이클 다리 포즈 순서
  pass: boolean[];                    // 몸이 올라가는 포즈(다리 교차)
};
export const WALKER1: RigSpec = {
  dir: "kit/walker1", w: 1024, h: 1536, feet: [509, 1433], top: 98,
  shoulderR: [362, 505], shoulderL: [656, 505],
  walk: ["legs_step_l", "legs_pass_r", "legs_step_r", "legs_pass_l"], pass: [false, true, false, true],
};

export const SemojiWalkerParams = z.object({
  cycle: num(16, 4, 60, 1, "걷기 사이클(다리 4포즈)", "timing", "f"),
  blinkEvery: num(80, 0, 300, 1, "눈 깜빡임 간격(0=없음)", "timing", "f"),
  blinkLen: num(4, 1, 12, 1, "눈 감는 길이", "timing", "f"),
  talkEvery: num(0, 0, 20, 1, "입 뻐끔 간격(0=없음)", "timing", "f"),
  talkMode: choice("fixed", ["fixed", "random"] as const, "입 뻐끔 방식(fixed=talkEvery 고정 · random=talkMin~talkMax 시드 랜덤)"),
  talkMin: num(4, 1, 30, 1, "random: 최소 간격", "timing", "f"),
  talkMax: num(8, 1, 30, 1, "random: 최대 간격", "timing", "f"),
  bob: num(4, 0, 30, 1, "패스 포즈 들썩임", "motion", "px"),
  armSwing: num(5, 0, 25, 0.5, "팔 흔들림", "motion", "°"),
});
export type SemojiWalkerP = z.infer<typeof SemojiWalkerParams>;

/** (x, y) = 두 발 사이 바닥점(화면), h = 키(px). walking=false 면 서 있는 포즈 */
export const SemojiWalker: React.FC<{ x: number; y: number; h: number; at?: number; walking?: boolean; rig?: RigSpec; flip?: boolean; seed?: string; p?: Partial<SemojiWalkerP> }> = ({ x, y, h, at = 0, walking = true, rig = WALKER1, flip = false, seed = "w", p }) => {
  const P = def(SemojiWalkerParams, p);
  const f = useCurrentFrame();
  const t = Math.max(0, f - at);
  const s = h / (rig.feet[1] - rig.top);
  const step = Math.max(1, Math.round(P.cycle / 4));
  const k = Math.floor(t / step) % 4;
  const legs = walking ? rig.walk[k] : "legs_stand";
  const lift = walking && rig.pass[k] ? P.bob : 0;
  const sw = walking ? (k === 0 ? 1 : k === 2 ? -1 : 0) * P.armSwing : 0;
  const blinkOn = P.blinkEvery > 0 && (t + Math.floor(random(seed) * P.blinkEvery)) % P.blinkEvery < P.blinkLen;
  const talkOn = P.talkMode === "random" ? talkOpenRandom(t, seed, P.talkMin, P.talkMax) : P.talkEvery > 0 && Math.floor(t / P.talkEvery) % 2 === 1;
  const L = (name: string, extra?: React.CSSProperties) => (
    <Img key={name} src={staticFile(`${rig.dir}/${name}.png`)} style={{ position: "absolute", left: 0, top: 0, width: rig.w, height: rig.h, ...extra }} />
  );
  const arm = (name: string, pv: [number, number], a: number) =>
    L(name, { transformOrigin: `${pv[0]}px ${pv[1]}px`, transform: `rotate(${a}deg)` });
  return (
    <div style={{ position: "absolute", left: x - rig.feet[0] * s, top: y - rig.feet[1] * s, width: rig.w, height: rig.h, transformOrigin: "0 0", transform: `scale(${flip ? -s : s},${s})${flip ? ` translateX(${-rig.w}px)` : ""}` }}>
      <div style={{ position: "absolute", inset: 0, transform: `translateY(${-lift / s}px)` }}>
        {L(legs)}
        {arm("arm_r", rig.shoulderR, sw)}
        {arm("arm_l", rig.shoulderL, sw)}
        {L("torso")}
        {blinkOn && L("eyes_closed")}
        {talkOn && L("mouth_open")}
      </div>
    </div>
  );
};

// ══ 범용 세모지 캐릭터 리그 ═══════════════════════════════════════════════════
// 모든 캐릭터(CAST)가 같은 캔버스·같은 좌표의 부위 PNG를 가진다. 포즈 = 그림 교체(hold), 팔 = 어깨 축 회전, 표정 = 얼굴 패치.
//  armR/armL: "arm"(기본) 또는 추가 포즈 이름(예 "arm_raise_fist"). 인물의 오른팔 = 화면 왼쪽(_r).
//  legs: "legs_stand" | "legs_sit" | "legs_dangle" | 걷기면 walking=true.  face: "face_angry" 등(없으면 기본). "arms_folded" 는 armFold=true.
//  bust=true 면 허리 아래를 그리지 않는다(상반신 데모).
import { CAST, CastId, RigJson } from "./kit";
import { interpolate } from "remotion";
/** 몸 앞을 가로지르는 팔 포즈 — 몸통 위에 그린다(아래에 그리면 가려짐) */
export const FRONT_ARMS = new Set(["arm_guard_fist", "arm_hold", "arm_hand_chest", "arm_hand_chin"]);
const isFront = (n?: string) => !!n && FRONT_ARMS.has(n);
export type RigPose = { armR?: string; armL?: string; rotR?: number; rotL?: number; legs?: string; face?: string; armFold?: boolean };
export const SemojiRigParams = z.object({
  bobEvery: num(10, 2, 40, 1, "까딱 간격(0=없음)", "timing", "f"),
  bobAmp: num(1, 0, 5, 0.1, "까딱 세기(ScaleY %)", "motion", "%"),
  blinkEvery: num(90, 0, 300, 1, "눈 깜빡임 간격(0=없음)", "timing", "f"),
  talkEvery: num(0, 0, 20, 1, "입 뻐끔 간격(0=없음)", "timing", "f"),
  talkMode: choice("fixed", ["fixed", "random"] as const, "입 뻐끔 방식(fixed=talkEvery 고정 · random=talkMin~talkMax 시드 랜덤)"),
  talkMin: num(4, 1, 30, 1, "random: 최소 간격", "timing", "f"),
  talkMax: num(8, 1, 30, 1, "random: 최대 간격", "timing", "f"),
});
export type SemojiRigP = z.infer<typeof SemojiRigParams>;
export const SemojiRig: React.FC<{ cast: CastId | RigJson; x: number; y: number; h: number; pose?: RigPose; bust?: boolean; walking?: boolean; flip?: boolean; at?: number; seed?: string; style?: React.CSSProperties; p?: Partial<SemojiRigP & SemojiWalkerP> }> = ({ cast, x, y, h, pose = {}, bust = false, walking = false, flip = false, at = 0, seed = "rig", style, p }) => {
  const R: RigJson = typeof cast === "string" ? CAST[cast] : cast;
  const P = { ...def(SemojiRigParams, p), ...def(SemojiWalkerParams, p) };
  const f = useCurrentFrame();
  const t = Math.max(0, f - at);
  if (walking) {
    return <SemojiWalker x={x} y={y} h={h} at={at} flip={flip} seed={seed} p={P} rig={{ dir: R.dir, w: R.w, h: R.h, feet: [R.feet[0], R.feet[1]], top: R.top, shoulderR: [R.shoulderR[0], R.shoulderR[1]], shoulderL: [R.shoulderL[0], R.shoulderL[1]], walk: ["legs_step_l", "legs_pass_r", "legs_step_r", "legs_pass_l"], pass: [false, true, false, true] }} />;
  }
  const s = h / (R.feet[1] - R.top);
  const ph = Math.floor(random(seed) * 10);
  const k = P.bobEvery > 0 ? ((t + ph) % (2 * P.bobEvery)) / P.bobEvery : 0;       // 10f 핑퐁 이지이지
  const e = k < 1 ? k : 2 - k, ee = e * e * (3 - 2 * e);
  const sy = 1 + (P.bobAmp / 100) * ee;
  const blinkOn = P.blinkEvery > 0 && (t + Math.floor(random(seed + "b") * P.blinkEvery)) % P.blinkEvery < 4;
  const talkOn = P.talkMode === "random" ? talkOpenRandom(t, seed, P.talkMin, P.talkMax) : P.talkEvery > 0 && Math.floor(t / P.talkEvery) % 2 === 1;
  const img = (name: string, extra?: React.CSSProperties) => <Img key={name} src={staticFile(`${R.dir}/${name}.png`)} style={{ position: "absolute", left: 0, top: 0, width: R.w, height: R.h, ...extra }} />;
  const armName = (n: string | undefined, side: "r" | "l") => (!n || n === "arm" ? `arm_${side}` : `${n}_${side}`);
  const arm = (n: string | undefined, side: "r" | "l", rot = 0) => {
    const pv = side === "r" ? R.shoulderR : R.shoulderL;
    return img(armName(n, side), { transformOrigin: `${pv[0]}px ${pv[1]}px`, transform: `rotate(${rot}deg)` });
  };
  const clipBottom = bust ? R.torsoBottom + 10 : R.h;
  const ay = bust ? clipBottom : R.feet[1];   // 화면 (x, y) 에 오는 캔버스 점: 발(전신) 또는 몸통 아래(흉상)
  return (
    <div style={{ position: "absolute", left: x - R.feet[0], top: y - ay, width: R.w, height: clipBottom, overflow: "hidden", transformOrigin: `${R.feet[0]}px ${ay}px`, transform: `scale(${flip ? -s : s},${s * sy})`, ...style }}>
      {!bust && img(pose.legs ?? "legs_stand")}
      {!pose.armFold && !isFront(pose.armR) && arm(pose.armR, "r", pose.rotR)}
      {!pose.armFold && !isFront(pose.armL) && arm(pose.armL, "l", pose.rotL)}
      {img("torso")}
      {!pose.armFold && isFront(pose.armR) && arm(pose.armR, "r", pose.rotR)}
      {!pose.armFold && isFront(pose.armL) && arm(pose.armL, "l", pose.rotL)}
      {pose.face && img(pose.face)}
      {!pose.face && blinkOn && img("eyes_closed")}
      {!pose.face && talkOn && img("mouth_open")}
      {pose.armFold && img("arms_folded")}
    </div>
  );
};
/** 두 포즈 사이 팔 회전을 키로 보간할 때 쓰는 도우미 */
export const rotKey = (f: number, ks: number[], vs: number[]) => interpolate(f, ks, vs, { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
