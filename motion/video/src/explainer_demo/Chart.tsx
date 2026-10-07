// 딤 오버레이 위 아이콘 막대그래프 — 실측(potato_0021_chart): 제목 위 중앙 흰 헤비 고딕(타자 1.5f/자),
// 출처 우상단, 막대 #C80000, 흰 축(화살표), 점선 격자, 막대 끝 판화 아이콘 4f(5f) 팝, 막대 12f(15f) ease-out 1f 스태거.
import React from "react";
import { Easing, Img, useCurrentFrame } from "remotion";
import { z } from "zod";
import { num, col, def } from "../params/p";
import { PAL, lin, BACK_OUT } from "./theme";

export const IconBarChartParams = z.object({
  titleSize: num(84, 30, 140, 1, "제목 크기", "size", "px"),
  perChar: num(1.5, 0, 6, 0.25, "제목 글자당 타자", "timing", "f"),
  barsAt: num(18, 0, 120, 1, "막대 시작(제목 뒤)", "timing", "f"),
  barLen: num(15, 1, 60, 1, "막대 자라는 길이", "timing", "f"),
  stagger: num(6, 0, 30, 0.5, "막대 스태거", "timing", "f"),
  iconPop: num(5, 1, 20, 1, "아이콘 팝 길이", "timing", "f"),
  barW: num(120, 20, 300, 1, "막대 폭", "size", "px"),
  iconSize: num(120, 30, 260, 1, "아이콘 크기", "size", "px"),
  labelSize: num(40, 16, 80, 1, "라벨 크기", "size", "px"),
  bar: col(PAL.red, "막대 색"),
});
export type IconBarChartP = z.infer<typeof IconBarChartParams>;

export const IconBarChart: React.FC<{ at: number; title: string; note?: string; bars: { label: string; v: number; icon: string }[]; max: number; p?: Partial<IconBarChartP> }> = ({ at, title, note, bars, max, p }) => {
  const P = def(IconBarChartParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const t = f - at;
  const nChars = Math.floor(t / Math.max(0.001, P.perChar)) + 1;
  const x0 = 250, x1 = 1760, y0 = 800, y1 = 250; // 축
  const slot = (x1 - x0 - 40) / bars.length;
  return (
    <div style={{ position: "absolute", inset: 0 }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 70, textAlign: "center", fontFamily: "NeoHv", fontSize: P.titleSize, color: "#fff", textShadow: "0 4px 10px rgba(0,0,0,0.35)" }}>
        {[...title].map((c, i) => <span key={i} style={{ visibility: i < nChars ? "visible" : "hidden" }}>{c}</span>)}
      </div>
      {note && <div style={{ position: "absolute", right: 150, top: 200, fontFamily: "NeoEb", fontSize: 30, color: "#fff", opacity: lin(t, 8, 14, 0, 0.95) }}>{note}</div>}
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0, opacity: lin(t, 4, 10, 0, 1) }}>
        {[0.25, 0.5, 0.75, 1].map((g) => <line key={g} x1={x0} x2={x1} y1={y0 - (y0 - y1) * g} y2={y0 - (y0 - y1) * g} stroke="#fff" strokeOpacity={0.7} strokeWidth={2} strokeDasharray="10 9" />)}
        <line x1={x0} y1={y0} x2={x1 + 10} y2={y0} stroke="#fff" strokeWidth={4} />
        <polygon points={`${x1 + 26},${y0} ${x1 + 6},${y0 - 10} ${x1 + 6},${y0 + 10}`} fill="#fff" />
        <line x1={x0} y1={y0} x2={x0} y2={y1 - 30} stroke="#fff" strokeWidth={4} />
        <polygon points={`${x0},${y1 - 46} ${x0 - 10},${y1 - 26} ${x0 + 10},${y1 - 26}`} fill="#fff" />
      </svg>
      {bars.map((b, i) => {
        const bt = P.barsAt + i * P.stagger;
        const k = lin(t, bt, bt + P.barLen, 0, 1, Easing.out(Easing.cubic));
        const hMax = ((y0 - y1) * b.v) / max;
        const hh = hMax * k;
        const cx = x0 + 40 + slot * (i + 0.5);
        const ik = lin(t, bt + P.barLen - 2, bt + P.barLen - 2 + P.iconPop, 0, 1, BACK_OUT);
        return (
          <React.Fragment key={i}>
            <div style={{ position: "absolute", left: cx - P.barW / 2, top: y0 - hh, width: P.barW, height: hh, background: P.bar }} />
            {ik > 0 && <Img src={b.icon} style={{ position: "absolute", left: cx - P.iconSize / 2, top: y0 - hMax - P.iconSize * 0.95, width: P.iconSize, height: P.iconSize, objectFit: "contain", transform: `scale(${ik})`, transformOrigin: "50% 100%" }} />}
            <div style={{ position: "absolute", left: cx - slot / 2, width: slot, top: y0 + 14, textAlign: "center", fontFamily: "NeoHv", fontSize: P.labelSize, color: "#fff", lineHeight: 1.1, opacity: lin(t, bt, bt + 5, 0, 1), whiteSpace: "pre-line" }}>{b.label}</div>
          </React.Fragment>
        );
      })}
    </div>
  );
};
