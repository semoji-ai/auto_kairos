// 세모지 에셋 키트 쇼케이스 — 캐스트 5명(부위 리그)과 포즈·표정 교체, 걷기
import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { runGallery, Demo } from "./runner";
import { SemojiRig, SemojiRigParams, RigPose } from "../lib/semoji_rig";
import { CAST } from "../lib/kit";

type P = { p?: Record<string, any> };
const Bg: React.FC = () => <AbsoluteFill style={{ background: "#C4CFC6" }} />;
const IDS = ["walker1", "c2_boss", "c3_woman", "c4_elder", "c5_chef"] as const;

// 01 캐스트 라인업: 까딱까딱 + 깜빡임 + 말하기
const D01: React.FC<P> = ({ p }) => (
  <AbsoluteFill><Bg />
    {IDS.map((id, i) => <SemojiRig key={id} cast={id} x={250 + i * 355} y={1010} h={760} seed={id} p={{ talkEvery: i % 2 ? 5 : 0, ...p }} />)}
  </AbsoluteFill>
);
// 02 포즈 퍼레이드: 캐릭터마다 가진 추가 포즈를 20f 간격으로 교체
const D02: React.FC<P> = ({ p }) => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill><Bg />
      {IDS.map((id, i) => {
        const ex = CAST[id].extras;
        const cur = ex.length ? ex[Math.floor(f / 20) % ex.length] : "";
        const pose: RigPose = cur.startsWith("arm_") ? { armR: cur } : cur === "arms_folded" ? { armFold: true } : cur.startsWith("face_") ? { face: cur } : cur.startsWith("legs_") ? { legs: cur } : {};
        return <SemojiRig key={id} cast={id} x={250 + i * 355} y={1010} h={760} seed={id} pose={pose} p={p} />;
      })}
    </AbsoluteFill>
  );
};
// 03 걷기(전원)
const D03: React.FC<P> = ({ p }) => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill><Bg />
      <div style={{ position: "absolute", left: 0, right: 0, top: 980, bottom: 0, background: "#1E7A45" }} />
      {IDS.map((id, i) => <SemojiRig key={id} cast={id} x={-200 + i * 330 + f * 5} y={1010} h={680} walking seed={id} p={p} />)}
    </AbsoluteFill>
  );
};
// 04 흉상(상반신) 대화
const D04: React.FC<P> = ({ p }) => (
  <AbsoluteFill><Bg />
    <SemojiRig cast="c2_boss" x={620} y={1080} h={1500} bust seed="b1" pose={{ armR: "arm_out_side" }} p={{ talkEvery: 5, ...p }} />
    <SemojiRig cast="c3_woman" x={1320} y={1080} h={1500} bust seed="b2" pose={{ armFold: true, face: "face_smile" }} p={p} />
  </AbsoluteFill>
);

export const DEMOS: Demo[] = [
  { name: "SemojiRig — 캐스트 5명 라인업(까딱·깜빡·말하기)", dur: 90, C: D01, schema: SemojiRigParams },
  { name: "SemojiRig — 포즈·표정 교체 퍼레이드", dur: 280, C: D02, schema: SemojiRigParams },
  { name: "SemojiRig — 전원 걷기", dur: 90, C: D03, schema: SemojiRigParams },
  { name: "SemojiRig — 흉상 대화(bust)", dur: 90, C: D04, schema: SemojiRigParams },
];
export const GALLERY_DUR = Math.max(30, DEMOS.reduce((a, d) => a + d.dur, 0));
export const Gallery = runGallery(DEMOS);
