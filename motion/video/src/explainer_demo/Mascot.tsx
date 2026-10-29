// 마스코트 콩트 — 실측: 입 모양 4~8f 불규칙 교체, 아이들 루프 1~1.5s, 포즈 하드 스왑, 좌우 1/3 배치, 아래서 올라옴.
// 몸통(굵은 외곽선 플랫) + 입 레이어(별도 투명 PNG) 합성.
import React from "react";
import { Easing, Img, useCurrentFrame } from "remotion";
import { z } from "zod";
import { num, def } from "../params/p";
import { lin, rnd } from "./theme";

export const TalkingMascotParams = z.object({
  mouthMin: num(4, 1, 20, 1, "입 교체 최소 간격", "timing", "f"),
  mouthMax: num(8, 1, 30, 1, "입 교체 최대 간격", "timing", "f"),
  idlePeriod: num(38, 10, 120, 1, "아이들 루프 주기", "timing", "f"),
  idleAmp: num(5, 0, 30, 0.5, "아이들 들썩임", "motion", "px"),
  squash: num(0.012, 0, 0.08, 0.001, "아이들 찌부 세기", "motion"),
  enterLen: num(9, 1, 40, 1, "아래서 등장 길이", "timing", "f"),
  enterDist: num(420, 0, 1200, 10, "등장 거리", "motion", "px"),
  talkHop: num(6, 0, 30, 0.5, "말할 때 살짝 튐", "motion", "px"),
});
export type TalkingMascotP = z.infer<typeof TalkingMascotParams>;

export type MouthLayer = { src: string; x: number; y: number; w: number }; // 몸통 폭 대비 비율(0..1)
export const TalkingMascot: React.FC<{
  body: string; aspect: number; x: number; bottom: number; w: number; at: number;
  mouths?: MouthLayer[]; // [0]=닫힘(없으면 몸통 그대로)
  talk?: [number, number][]; seed?: string; flip?: boolean; p?: Partial<TalkingMascotP>;
}> = ({ body, aspect, x, bottom, w, at, mouths = [], talk = [], seed = "m", flip, p }) => {
  const P = def(TalkingMascotParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const enter = lin(f, at, at + P.enterLen, P.enterDist, 0, Easing.out(Easing.back(1.4)));
  const ph = ((f - at) / P.idlePeriod) * Math.PI * 2;
  const bob = Math.sin(ph) * P.idleAmp;
  const sq = 1 + Math.sin(ph) * P.squash;
  const win = talk.find(([a, b]) => f >= a && f < b);
  // 불규칙 입 교체: 구간 시작부터 [min,max] 랜덤 간격으로 상태 인덱스 결정
  let mi = 0;
  if (win && mouths.length > 1) {
    let t = win[0], k = 0;
    while (t <= f) { const step = P.mouthMin + Math.floor(rnd(seed, k) * (P.mouthMax - P.mouthMin + 1)); if (t + step > f) break; t += step; k++; }
    mi = k % 2 === 0 ? 1 + Math.floor(rnd(seed, k + 50) * (mouths.length - 1)) : 0;
  }
  const hop = win ? -Math.abs(Math.sin(((f - win[0]) / 7) * Math.PI)) * P.talkHop * (f - win[0] < 7 ? 1 : 0) : 0;
  const h = w / aspect;
  return (
    <div style={{ position: "absolute", left: x - w / 2, bottom: bottom - enter - bob + hop * -1, width: w, height: h, transform: `scaleY(${sq}) scaleX(${(flip ? -1 : 1) * (2 - sq)})`, transformOrigin: "50% 100%" }}>
      <Img src={body} style={{ position: "absolute", inset: 0, width: w, height: h }} />
      {mouths[mi] && mouths[mi].src && (
        <Img src={mouths[mi].src} style={{ position: "absolute", left: mouths[mi].x * w - (mouths[mi].w * w) / 2, top: mouths[mi].y * h, width: mouths[mi].w * w }} />
      )}
    </div>
  );
};
