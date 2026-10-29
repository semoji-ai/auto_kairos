// 자체 엠블럼 로고 스팅(해골 + 교차 향신료 저울 + 후추 덩굴 + 리본 + 적색 타이틀)
// 실측(y7OMrkjkFPg 0:50.2~0:55.7, 5.5s): 해골 위에서 10f(12f) → 소품 교차 8f+세틀 8f(10f+10f) → 리본·잎 24f(30f)
// → 적색 타이틀 하드 팝 → 흩어짐 12f(15f). 축약판 기본 99f(3.3s).
import React from "react";
import { AbsoluteFill, Easing, Img, useCurrentFrame } from "remotion";
import { z } from "zod";
import { num, col, def } from "../params/p";
import { PAL, lin, img, BACK_OUT, EXPO_OUT } from "./theme";

export const LogoStingParams = z.object({
  skullAt: num(4, 0, 60, 1, "해골 낙하 시작", "timing", "f"),
  skullLen: num(12, 1, 40, 1, "해골 낙하 길이", "timing", "f"),
  crossAt: num(14, 0, 90, 1, "저울 교차 시작", "timing", "f"),
  crossLen: num(10, 1, 40, 1, "저울 교차 길이", "timing", "f"),
  settleLen: num(10, 0, 40, 1, "저울 세틀 길이", "timing", "f"),
  ribbonAt: num(24, 0, 90, 1, "리본·덩굴 시작", "timing", "f"),
  ribbonLen: num(24, 1, 60, 1, "리본·덩굴 길이", "timing", "f"),
  titleAt: num(50, 0, 120, 1, "타이틀 하드 팝", "timing", "f"),
  scatterLen: num(15, 1, 40, 1, "흩어짐 길이", "timing", "f"),
  scatterDist: num(260, 0, 900, 10, "흩어짐 거리", "motion", "px"),
  crossRot: num(3, 0, 20, 0.5, "세틀 흔들림 각도", "motion", "°"),
  titleSize: num(190, 60, 320, 1, "타이틀 크기", "size", "px"),
  titleOp: num(0.92, 0, 1, 0.01, "타이틀 불투명도", "look"),
  titleColor: col(PAL.redTitle, "타이틀 색"),
});
export type LogoStingP = z.infer<typeof LogoStingParams>;

export const LogoSting: React.FC<{ dur: number; title?: string; ribbon?: string; p?: Partial<LogoStingP> }> = ({ dur, title = "지식항해단", ribbon = "SPICE · SEA · HISTORY", p }) => {
  const P = def(LogoStingParams, p);
  const f = useCurrentFrame();
  const sc0 = dur - P.scatterLen;
  const sk = lin(f, sc0, dur, 0, 1, Easing.in(Easing.cubic)); // 흩어짐 0→1
  const fade = 1 - sk;
  const out = (dx: number, dy: number, rot = 0) => `translate(${dx * sk * P.scatterDist}px, ${dy * sk * P.scatterDist}px) rotate(${rot * sk}deg) scale(${1 + 0.15 * sk})`;
  const cx = 960, cy = 450;
  // 해골: 위에서 낙하 + 착지 튐
  const skY = lin(f, P.skullAt, P.skullAt + P.skullLen, -760, 0, Easing.out(Easing.quad));
  const skB = f > P.skullAt + P.skullLen ? Math.sin((f - P.skullAt - P.skullLen) * 0.9) * 10 * Math.exp(-(f - P.skullAt - P.skullLen) / 4) : 0;
  // 저울: 양쪽에서 회전해 들어와 교차 → 세틀(살짝 넘어갔다 돌아옴)
  const ck = lin(f, P.crossAt, P.crossAt + P.crossLen, 0, 1, EXPO_OUT);
  const settle = f > P.crossAt + P.crossLen ? Math.sin(((f - P.crossAt - P.crossLen) / Math.max(1, P.settleLen)) * Math.PI) * P.crossRot * lin(f, P.crossAt + P.crossLen, P.crossAt + P.crossLen + P.settleLen, 1, 0) : 0;
  const rk = lin(f, P.ribbonAt, P.ribbonAt + P.ribbonLen, 0, 1, EXPO_OUT);
  const sprigK = lin(f, P.ribbonAt, P.ribbonAt + P.ribbonLen * 0.7, 0, 1, BACK_OUT);
  const showTitle = f >= P.titleAt;
  return (
    <AbsoluteFill style={{ opacity: fade }}>
      {/* 덩굴(좌·우 반전) */}
      {f >= P.ribbonAt && [-1, 1].map((s) => (
        <Img key={s} src={img("emb_sprig.png")} style={{ position: "absolute", left: cx + s * 330 - 150, top: cy - 250, width: 300,
          transform: `${out(s * 1.2, -0.3, s * 30)} scaleX(${s === -1 ? -1 : 1}) rotate(${(1 - sprigK) * 40}deg) scale(${sprigK})`, transformOrigin: "50% 90%" }} />
      ))}
      {/* 교차 저울 */}
      {f >= P.crossAt && (
        <div style={{ position: "absolute", left: cx - 430, top: cy - 230, width: 860, height: 603, transform: out(0, 0.9), opacity: lin(f, P.crossAt, P.crossAt + 3, 0, 1) }}>
          <div style={{ position: "absolute", inset: 0, transform: `translateY(${(1 - ck) * 220}px) rotate(${settle}deg) scale(${0.62 + 0.38 * ck})`, transformOrigin: "50% 62%" }}>
            <Img src={img("emb_scales.png")} style={{ width: "100%", height: "100%" }} />
          </div>
        </div>
      )}
      {/* 해골 */}
      {f >= P.skullAt && (
        <Img src={img("emb_skull.png")} style={{ position: "absolute", left: cx - 150, top: cy - 205 + skY + skB, width: 300, transform: out(0, -1.3), filter: "drop-shadow(0 4px 6px rgba(40,20,0,0.25))" }} />
      )}
      {/* 리본 */}
      {f >= P.ribbonAt && (
        <div style={{ position: "absolute", left: cx - 420, top: cy + 300, width: 840, height: 164, transform: `${out(0, 1.4)} scaleX(${rk})`, opacity: lin(f, P.ribbonAt, P.ribbonAt + 4, 0, 1) }}>
          <Img src={img("emb_ribbon.png")} style={{ width: "100%", height: "100%" }} />
          <div style={{ position: "absolute", left: 0, right: 0, top: 44, textAlign: "center", fontFamily: "'Times New Roman',Georgia,serif", fontSize: 40, letterSpacing: 7, color: "#3A2A1C", opacity: lin(f, P.ribbonAt + P.ribbonLen * 0.5, P.ribbonAt + P.ribbonLen, 0, 1) }}>{ribbon}</div>
        </div>
      )}
      {/* 적색 타이틀 하드 팝(애니메이션 없음) */}
      {showTitle && (
        <div style={{ position: "absolute", left: 0, right: 0, top: cy - P.titleSize * 0.6, textAlign: "center", fontFamily: "Dohyeon", fontSize: P.titleSize, letterSpacing: -4,
          color: P.titleColor, opacity: P.titleOp, mixBlendMode: "multiply", transform: out(0, 0), whiteSpace: "nowrap" }}>{title}</div>
      )}
    </AbsoluteFill>
  );
};
