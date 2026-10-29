// 회전 지구본 + 히트맵 — d3-geo orthographic + Natural Earth 1:50m 육지(손그림 대륙 없음)
// 실측: 진입 아래 +600px→0 25f ease-out, 회전 초반 약 60°/s → 감속 후 목표 대륙에서 정지,
//       육지 #C6B9AC 바다 #453A41, 판화 해칭, 히트맵 색 번짐 10f.
import React, { useLayoutEffect, useRef } from "react";
import { Easing, useCurrentFrame } from "remotion";
import { geoOrthographic, geoPath, type GeoProjection } from "d3-geo";
import { z } from "zod";
import { num, col, def } from "../params/p";
import { PAL, lin, EXPO_OUT, rnd } from "./theme";
import COAST from "../data/ne_coast50m.json";
import LAND from "../data/ne_land50m.json";


export const EngravedGlobeParams = z.object({
  radius: num(430, 100, 900, 1, "지구본 반지름", "size", "px"),
  cx: num(960, 0, 1920, 1, "중심 X", "size", "px"),
  cy: num(470, 0, 1080, 1, "중심 Y", "size", "px"),
  riseLen: num(25, 1, 60, 1, "아래서 떠오르는 길이", "timing", "f"),
  riseDist: num(600, 0, 1200, 10, "떠오르는 거리", "motion", "px"),
  spinLen: num(150, 10, 400, 1, "회전→정지 길이", "timing", "f"),
  spinDeg: num(130, 0, 540, 1, "총 회전량", "motion", "°"),
  hatchOp: num(0.35, 0, 1, 0.01, "판화 해칭 세기", "look"),
  heatLen: num(10, 1, 40, 1, "히트맵 번짐 길이", "timing", "f"),
  heatBlur: num(9, 0, 30, 0.5, "히트맵 번짐 블러", "look", "px"),
  land: col(PAL.globeLand, "육지 색"),
  sea: col(PAL.globeSea, "바다 색"),
  line: col(PAL.outline, "해안선 색"),
  heat: col("#C21A12", "히트맵 색"),
});
export type EngravedGlobeP = z.infer<typeof EngravedGlobeParams>;

export type HeatSpot = { lon: number; lat: number; r: number; at: number; op?: number };
type Props = {
  at: number;
  target: [number, number]; // 정지 시 화면 중앙에 올 경위도
  tiltFrom?: number;
  zoom?: { at: number; len: number; to: number; dy?: number }; // 반지름 배율 줌(지구본 확대)
  heat?: HeatSpot[];
  overlay?: (proj: (lonlat: [number, number]) => { x: number; y: number; visible: boolean }) => React.ReactNode;
  p?: Partial<EngravedGlobeP>;
};

export const EngravedGlobe: React.FC<Props> = ({ at, target, tiltFrom = -35, zoom, heat = [], overlay, p }) => {
  const P = def(EngravedGlobeParams, p);
  const f = useCurrentFrame();
  const t = f - at;
  const rise = lin(t, 0, P.riseLen, P.riseDist, 0, Easing.out(Easing.cubic));
  const k = lin(t, 0, P.spinLen, 0, 1, Easing.out(Easing.cubic));
  const lon = target[0] - P.spinDeg * (1 - k);
  const lat = tiltFrom + (target[1] - tiltFrom) * k;
  const zk = zoom ? lin(f, zoom.at, zoom.at + zoom.len, 0, 1, Easing.inOut(Easing.cubic)) : 0;
  const R = P.radius * (1 + ((zoom?.to ?? 1) - 1) * zk);
  const cy = P.cy + rise + (zoom?.dy ?? 0) * zk;
  const mk = (): GeoProjection => geoOrthographic().scale(R).translate([P.cx, cy]).rotate([-lon, -lat]).clipAngle(90).precision(0.4);
  const proj = mk();
  const path = geoPath(proj);
  const coastParts = (COAST as any).geometries.map((g: any) => path(g) || "").filter(Boolean) as string[];
  const landD = path(LAND as any) || "";
  const sphereD = path({ type: "Sphere" } as any) || "";
  const project = (ll: [number, number]) => {
    const r = proj.rotate();
    const vis = Math.cos(((ll[1]) * Math.PI) / 180) * Math.cos(((ll[0] + r[0]) * Math.PI) / 180) * Math.cos((-r[1] * Math.PI) / 180) + Math.sin((ll[1] * Math.PI) / 180) * Math.sin((-r[1] * Math.PI) / 180) > 0;
    const xy = proj(ll) || [-9999, -9999];
    return { x: xy[0], y: xy[1], visible: vis };
  };
  // 육지 채우기는 캔버스로: 거대 단일 SVG 경로는 Chrome(angle)에서 일부 면(인도 등)이 빠지는 현상 실측 → 2D 캔버스는 정상
  const cvs = useRef<HTMLCanvasElement>(null);
  useLayoutEffect(() => {
    const c = cvs.current; if (!c) return;
    const ctx = c.getContext("2d", { willReadFrequently: true }); if (!ctx) return; // CPU 래스터 강제(GPU 경로 채우기 누락 회피)
    ctx.clearRect(0, 0, 1920, 1080);
    const cp = geoPath(mk(), ctx as any); // 새 투영 인스턴스(스트림 캐시·클립 상태 공유 방지)
    ctx.beginPath(); cp(LAND as any); ctx.fillStyle = P.land; ctx.fill();
    // 판화 해칭(38° 사선)
    const pc = document.createElement("canvas"); pc.width = 7; pc.height = 7;
    const pctx = pc.getContext("2d")!; pctx.strokeStyle = "#2A2024"; pctx.lineWidth = 1.3; pctx.beginPath(); pctx.moveTo(0, 0); pctx.lineTo(0, 7); pctx.stroke();
    const pat = ctx.createPattern(pc, "repeat")!;
    if ((pat as any).setTransform) (pat as any).setTransform(new DOMMatrix().rotate(38));
    ctx.save(); ctx.clip();
    // 종이 얼룩(저주파 명암) — 결정적 블롭
    for (let i = 0; i < 28; i++) {
      const bx = rnd("gtex", i) * 1920, by = rnd("gtex", i + 50) * 1080, br = 60 + rnd("gtex", i + 99) * 160;
      const g = ctx.createRadialGradient(bx, by, 0, bx, by, br);
      g.addColorStop(0, "rgba(90,70,60,0.16)"); g.addColorStop(1, "rgba(90,70,60,0)");
      ctx.fillStyle = g; ctx.fillRect(bx - br, by - br, br * 2, br * 2);
    }
    ctx.globalAlpha = P.hatchOp; ctx.fillStyle = pat; ctx.fillRect(0, 0, 1920, 1080); ctx.globalAlpha = 1;
    // 히트맵: 육지 안쪽만, 방사 그라디언트로 번짐
    for (const h of heat) {
      const hk = lin(f, h.at, h.at + P.heatLen, 0, 1, EXPO_OUT);
      if (hk <= 0) continue;
      const c = project([h.lon, h.lat]);
      if (!c.visible) continue;
      const rr = (h.r * Math.PI / 180) * R * (0.35 + 0.65 * hk) + P.heatBlur * 2;
      const g = ctx.createRadialGradient(c.x, c.y, 0, c.x, c.y, rr);
      g.addColorStop(0, P.heat); g.addColorStop(0.62, P.heat); g.addColorStop(1, "rgba(194,26,18,0)");
      ctx.globalAlpha = (h.op ?? 0.85) * hk; ctx.fillStyle = g; ctx.fillRect(c.x - rr, c.y - rr, rr * 2, rr * 2);
    }
    ctx.restore();
  });
  return (
    <>
      <svg width={1920} height={1080} style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}>
        <defs>
          <pattern id="gHatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(38)">
            <line x1="0" y1="0" x2="0" y2="7" stroke="#2A2024" strokeWidth="1.3" />
          </pattern>
          <pattern id="gHatch2" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(-50)">
            <line x1="0" y1="0" x2="0" y2="5" stroke="#1A1216" strokeWidth="1" />
          </pattern>
          <radialGradient id="gShade" cx="42%" cy="38%" r="65%">
            <stop offset="0%" stopColor="#fff" stopOpacity="0.10" />
            <stop offset="70%" stopColor="#000" stopOpacity="0" />
            <stop offset="100%" stopColor="#000" stopOpacity="0.55" />
          </radialGradient>
          <filter id="gTex"><feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves={4} seed={21} />
            <feColorMatrix values="0 0 0 0 0.55  0 0 0 0 0.5  0 0 0 0 0.5  0 0 0 0.9 -0.2" /></filter>
          <radialGradient id="gHeatGrad"><stop offset="0%" stopColor={P.heat} stopOpacity={1} /><stop offset="62%" stopColor={P.heat} stopOpacity={0.9} /><stop offset="100%" stopColor={P.heat} stopOpacity={0} /></radialGradient>
          <clipPath id="gLandClip"><path d={landD} /></clipPath>
          <clipPath id="gSphereClip"><path d={sphereD} /></clipPath>
          <filter id="gDrop" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="14" stdDeviation="16" floodColor="#3A2410" floodOpacity="0.35" /></filter>
        </defs>
        <g filter="url(#gDrop)"><path d={sphereD} fill={P.sea} /></g>
        <path d={sphereD} fill="url(#gHatch2)" opacity={P.hatchOp * 0.5} />
      </svg>
      <canvas ref={cvs} width={1920} height={1080} style={{ position: "absolute", left: 0, top: 0, width: 1920, height: 1080 }} />
      <svg width={1920} height={1080} style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}>
        {coastParts.map((d, i) => <path key={i} d={d} fill="none" stroke={P.line} strokeWidth={1.6} strokeLinejoin="round" />)}
        <path d={sphereD} fill="url(#gShade)" />
        <path d={sphereD} fill="none" stroke={P.line} strokeWidth={3} />
      </svg>
      {/* 지구본은 소축척이라 울릉도·독도 오버레이 대상 아님(한반도 전도가 크게 나오는 지도만 섬 형상 보강) */}
      {overlay?.(project)}
    </>
  );
};
