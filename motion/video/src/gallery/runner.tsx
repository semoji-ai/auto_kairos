import React from "react";
import { AbsoluteFill, Sequence } from "remotion";
import type { z } from "zod";
/** 갤러리 데모: schema 가 있으면 C 는 { p } 로 변수를 받는다 (도감 Param-<id> 컴포지션에서 슬라이더로 조절) */
export type Demo = { name: string; /** 미리보기 id 를 직접 줄 때(없으면 group-NN) */ id?: string; dur: number; C: React.FC<any>; schema?: z.ZodObject<any> };
// 갤러리 공통 러너: DEMOS 를 순서대로 이어 붙이고 좌상단에 기법 이름을 띄운다
export const runGallery = (demos: Demo[]) => {
  const G: React.FC = () => {
    let t = 0;
    return (
      <AbsoluteFill style={{ background: "#1c1c1c" }}>
        {demos.map((d, i) => {
          const from = t; t += d.dur;
          return (
            <Sequence key={i} from={from} durationInFrames={d.dur} name={d.name}>
              <AbsoluteFill style={{ overflow: "hidden" }}><d.C /></AbsoluteFill>
              <div style={{ position: "absolute", left: 20, bottom: 20, background: "rgba(0,0,0,0.75)", color: "#fff", fontFamily: "NeoEb", fontSize: 28, padding: "6px 16px", borderRadius: 8 }}>{i + 1}. {d.name}</div>
            </Sequence>
          );
        })}
      </AbsoluteFill>
    );
  };
  return G;
};
