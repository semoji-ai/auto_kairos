// 작전 지도 스타일 — MapLibre(OpenFreeMap) + 설명형 편집 데모 전용 레이어 오버라이드 프리셋
// 실측(ww2_0030_map, ww2_0545): 양피지 위 사각 액자(여백 좌우 108·위아래 54, 1~2px 테두리), 바다 #585460 수채,
// 점령지 #780000 계열 사선 해칭 + 흰 글로우, 윤곽 #281B2E, 시안 #0494C8 브러시 화살표(흰 테두리 5px, 두께 30 테이퍼),
// 붓글씨 지명(빨강·흰, -30~+60° 기울임, 80~130px). 경로선 90f linear, 화살표 25f ease-in-out.
import React, { useCallback } from "react";
import { AbsoluteFill, Easing, useCurrentFrame } from "remotion";
import type maplibregl from "maplibre-gl";
import { z } from "zod";
import { num, col, def } from "../params/p";
import { RemotionMap } from "../map/RemotionMap";
import { applyLayerOverrides, type LayerOverride, type MapStyleConfig } from "../map/mapStyles";
import { lngLatToPixel, type CameraState } from "../map/cameraInterpolation";
import { PAL, lin, rnd } from "./theme";

// ── 지도 스타일 프리셋(mapStyles.ts 수정 없이 explainer_demo 쪽에 둔다) ─────────────────────────────────────
const HIDE = ["waterway*", "landcover*", "landuse*", "park*", "boundary*", "road*", "highway*", "tunnel*", "bridge*", "railway*", "aeroway*", "building*", "ferry*"];
export const OPS_MAP_STYLE: MapStyleConfig = {
  url: "https://tiles.openfreemap.org/styles/bright",
  layerOverrides: [
    { match: "background", paint: { "background-color": "#A39686" } },
    { match: "water", paint: { "fill-color": PAL.sea } },
    ...HIDE.map((m): LayerOverride => ({ match: m, layout: { visibility: "none" } })),
  ],
  description: "작전 지도: 회갈색 육지·슬레이트 바다·현대 요소 숨김",
  recommended: "교역로·전쟁 작전 지도",
};

export const OpsMapParams = z.object({
  marginX: num(108, 0, 400, 1, "액자 좌우 여백", "size", "px"),
  marginY: num(54, 0, 300, 1, "액자 위아래 여백", "size", "px"),
  frameW: num(2, 0, 10, 0.5, "액자 테두리", "size", "px"),
  coastW: num(2.6, 0, 10, 0.1, "해안선 두께", "size", "px"),
  washOp: num(0.5, 0, 1, 0.01, "수채 얼룩 세기", "look"),
  hatchOp: num(0.4, 0, 1, 0.01, "점령지 해칭 세기", "look"),
  rough: num(24, 0, 60, 1, "점령지 붓 번짐", "look", "px"),
  spreadLen: num(10, 1, 40, 1, "점령지 번짐 등장 길이", "timing", "f"),
  land: col("#A39686", "육지 색"),
  sea: col(PAL.sea, "바다 색"),
  coast: col(PAL.outline, "해안선 색"),
  occupied: col("#A00C0C", "점령지 색"),
});
export type OpsMapP = z.infer<typeof OpsMapParams>;

type Region = { id: string; geojson: any; at: number };
/** 사각 액자 속 작전 지도. overlay 는 액자 좌표계(0..w, 0..h)의 px 변환 함수를 받는다 */
export const OpsMap: React.FC<{
  cam: CameraState;
  regions?: Region[];
  overlay?: (px: (ll: [number, number]) => { x: number; y: number }, box: { w: number; h: number }) => React.ReactNode;
  p?: Partial<OpsMapP>;
}> = ({ cam, regions = [], overlay, p }) => {
  const P = def(OpsMapParams, p);
  const w = 1920 - 2 * P.marginX, h = 1080 - 2 * P.marginY;
  const onReady = useCallback((map: maplibregl.Map) => {
    // OpenFreeMap 스타일이 globe 투영일 수 있음 → lngLatToPixel(메르카토르)과 맞추기 위해 강제
    try { (map as any).setProjection({ type: "mercator" }); } catch { /* 구버전 */ }
    applyLayerOverrides(map as any, [
      { match: "background", paint: { "background-color": P.land } },
      { match: "water", paint: { "fill-color": P.sea } },
      ...(OPS_MAP_STYLE.layerOverrides || []).filter((o) => o.layout),
    ]);
    // 해안선: water 폴리곤 윤곽
    try {
      map.addLayer({ id: "pir-coast-glow", type: "line", source: "openmaptiles", "source-layer": "water", paint: { "line-color": "#1a1420", "line-width": P.coastW * 3, "line-blur": 6, "line-opacity": 0.35 } } as any);
      map.addLayer({ id: "pir-coast", type: "line", source: "openmaptiles", "source-layer": "water", paint: { "line-color": P.coast, "line-width": P.coastW } } as any);
    } catch { /* 소스 없음 */ }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const px = (ll: [number, number]) => lngLatToPixel(ll, cam, w, h);
  const f = useCurrentFrame();
  // 점령지: Natural Earth 폴리곤을 화면 투영 → 붓 번짐(디스플레이스먼트) + 사선 해칭 + 흰 글로우, 번짐 등장 10f
  const ringD = (ring: [number, number][]) => "M" + ring.map((c) => { const q = px(c); return `${q.x.toFixed(1)},${q.y.toFixed(1)}`; }).join("L") + "Z";
  const geomD = (g: any): string => g.type === "Polygon" ? g.coordinates.map(ringD).join("") : g.type === "MultiPolygon" ? g.coordinates.map((pl: any) => pl.map(ringD).join("")).join("") : "";
  const regionSvg = regions.map((r) => {
    const d = (r.geojson.features || [r.geojson]).map((ft: any) => geomD(ft.geometry || ft)).join("");
    const k = lin(f, r.at, r.at + P.spreadLen, 0, 1, Easing.out(Easing.cubic));
    return (
      <g key={r.id} opacity={k}>
        <path d={d} fill="none" stroke="#FFF1E2" strokeWidth={14} opacity={0.55} filter="url(#opsGlow)" />
        <g filter="url(#opsRough)">
          <path d={d} fill={P.occupied} />
          <path d={d} fill="url(#opsHatch)" opacity={P.hatchOp} />
          <path d={d} fill="none" stroke={P.coast} strokeWidth={P.coastW} strokeLinejoin="round" />
        </g>
      </g>
    );
  });
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", left: P.marginX, top: P.marginY, width: w, height: h, overflow: "hidden", outline: `${P.frameW}px solid #1a1410` }}>
        <RemotionMap mapStyle={OPS_MAP_STYLE.url} cameraState={cam} onMapReady={onReady} width={w} height={h} />
        {/* 수채 얼룩 + 비네트 */}
        <svg width={w} height={h} style={{ position: "absolute", inset: 0, mixBlendMode: "multiply", opacity: P.washOp }}>
          <filter id="opsWash"><feTurbulence type="fractalNoise" baseFrequency="0.006" numOctaves={5} seed={12} />
            <feColorMatrix values="0 0 0 0 0.62  0 0 0 0 0.58  0 0 0 0 0.66  0 0 0 -1.4 1.2" /></filter>
          <rect width="100%" height="100%" filter="url(#opsWash)" />
        </svg>
        <div style={{ position: "absolute", inset: 0, background: "radial-gradient(ellipse at 50% 50%, transparent 55%, rgba(20,12,24,0.45) 100%)" }} />
        <svg width={w} height={h} style={{ position: "absolute", inset: 0 }}>
          <defs>
            <pattern id="opsHatch" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(40)"><line x1="0" y1="0" x2="0" y2="9" stroke="#3C0000" strokeWidth="2.2" /></pattern>
            <filter id="opsRough" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves={3} seed={7} result="n" /><feDisplacementMap in="SourceGraphic" in2="n" scale={P.rough} xChannelSelector="R" yChannelSelector="G" /></filter>
            <filter id="opsGlow" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="7" /></filter>
          </defs>
          {regionSvg}
        </svg>
        <div style={{ position: "absolute", inset: 0 }}>{overlay?.(px, { w, h })}</div>
      </div>
    </AbsoluteFill>
  );
};

// ── 브러시 화살표: 시안 두께 30 테이퍼 + 흰 테두리 5 · 진행형 그리기 ─────────────────────────────────
export const BrushArrowParams = z.object({
  len: num(75, 1, 240, 1, "그리는 길이", "timing", "f"),
  width: num(30, 4, 80, 1, "최대 두께", "size", "px"),
  tailW: num(0.25, 0, 1, 0.05, "꼬리 두께 비율", "size"),
  border: num(5, 0, 16, 0.5, "흰 테두리", "size", "px"),
  head: num(2.0, 1, 4, 0.1, "화살촉 크기(두께 배)", "size"),
  rough: num(4, 0, 20, 0.5, "붓 거칠기", "look", "px"),
  color: col(PAL.cyan, "화살표 색"),
});
export type BrushArrowP = z.infer<typeof BrushArrowParams>;

/** Catmull-Rom 스무딩 */
const smooth = (pts: { x: number; y: number }[], seg = 16) => {
  const out: { x: number; y: number }[] = [];
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(pts.length - 1, i + 2)];
    for (let s = 0; s < seg; s++) {
      const t = s / seg, t2 = t * t, t3 = t2 * t;
      out.push({
        x: 0.5 * (2 * p1.x + (-p0.x + p2.x) * t + (2 * p0.x - 5 * p1.x + 4 * p2.x - p3.x) * t2 + (-p0.x + 3 * p1.x - 3 * p2.x + p3.x) * t3),
        y: 0.5 * (2 * p1.y + (-p0.y + p2.y) * t + (2 * p0.y - 5 * p1.y + 4 * p2.y - p3.y) * t2 + (-p0.y + 3 * p1.y - 3 * p2.y + p3.y) * t3),
      });
    }
  }
  out.push(pts[pts.length - 1]);
  return out;
};

export const BrushArrow: React.FC<{ pts: { x: number; y: number }[]; at: number; id: string; w?: number; h?: number; ease?: "linear" | "inOut"; p?: Partial<BrushArrowP> }> = ({ pts, at, id, w = 1920, h = 1080, ease = "inOut", p }) => {
  const P = def(BrushArrowParams, p);
  const f = useCurrentFrame();
  if (f < at || pts.length < 2) return null;
  const k = lin(f, at, at + P.len, 0, 1, ease === "linear" ? Easing.linear : Easing.inOut(Easing.cubic));
  const sm = smooth(pts);
  const cum = [0];
  for (let i = 1; i < sm.length; i++) cum.push(cum[i - 1] + Math.hypot(sm[i].x - sm[i - 1].x, sm[i].y - sm[i - 1].y));
  const L = cum[cum.length - 1] * k;
  const vis: { x: number; y: number; d: number }[] = [];
  for (let i = 0; i < sm.length; i++) {
    if (cum[i] <= L) vis.push({ ...sm[i], d: cum[i] });
    else {
      const a = sm[i - 1], b = sm[i], r = (L - cum[i - 1]) / Math.max(0.001, cum[i] - cum[i - 1]);
      vis.push({ x: a.x + (b.x - a.x) * r, y: a.y + (b.y - a.y) * r, d: L });
      break;
    }
  }
  if (vis.length < 2) return null;
  const headLen = P.width * P.head * 0.9;
  const bodyEnd = Math.max(0, L - headLen);
  const left: string[] = [], right: string[] = [];
  let last = vis[0];
  for (let i = 0; i < vis.length; i++) {
    const q = vis[i];
    if (q.d > bodyEnd && i > 0) break;
    const nx = vis[Math.min(i + 1, vis.length - 1)], pv = vis[Math.max(i - 1, 0)];
    const tx = nx.x - pv.x, ty = nx.y - pv.y, tl = Math.hypot(tx, ty) || 1;
    const u = cum[cum.length - 1] > 0 ? q.d / Math.max(1, L) : 0;
    const hw = (P.width / 2) * (P.tailW + (1 - P.tailW) * Math.min(1, u * 1.6)) * (1 + (rnd(id, i) - 0.5) * 0.08);
    left.push(`${q.x - (ty / tl) * hw},${q.y + (tx / tl) * hw}`);
    right.push(`${q.x + (ty / tl) * hw},${q.y - (tx / tl) * hw}`);
    last = q;
  }
  const tip = vis[vis.length - 1];
  const dx = tip.x - last.x, dy = tip.y - last.y, dl = Math.hypot(dx, dy) || 1;
  const hw = (P.width * P.head) / 2;
  const headPts = `${last.x - (dy / dl) * hw},${last.y + (dx / dl) * hw} ${tip.x},${tip.y} ${last.x + (dy / dl) * hw},${last.y - (dx / dl) * hw}`;
  const body = `M${left.join(" L")} L${right.reverse().join(" L")} Z`;
  return (
    <svg width={w} height={h} style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}>
      <defs>
        <filter id={`ba-${id}`} x="-5%" y="-5%" width="110%" height="110%">
          <feTurbulence type="fractalNoise" baseFrequency="0.05" numOctaves={2} seed={5} result="n" />
          <feDisplacementMap in="SourceGraphic" in2="n" scale={P.rough} xChannelSelector="R" yChannelSelector="G" />
        </filter>
      </defs>
      <g filter={`url(#ba-${id})`}>
        <path d={body} fill="#fff" stroke="#fff" strokeWidth={P.border * 2} strokeLinejoin="round" />
        {dl > 0.5 && <polygon points={headPts} fill="#fff" stroke="#fff" strokeWidth={P.border * 2} strokeLinejoin="round" />}
        <path d={body} fill={P.color} />
        {dl > 0.5 && <polygon points={headPts} fill={P.color} />}
      </g>
    </svg>
  );
};

// ── 붓글씨 지명: 빨강(흰 글로우) 또는 흰(검정 외곽) · 기울임 · 먹 번짐 거칠기 ────────────────────────────
export const BrushLabelParams = z.object({
  size: num(96, 30, 200, 1, "글자 크기", "size", "px"),
  rot: num(-12, -60, 60, 1, "기울기", "motion", "°"),
  rough: num(7, 0, 30, 0.5, "붓 거칠기", "look", "px"),
  glow: num(10, 0, 40, 1, "흰 글로우", "look", "px"),
  popLen: num(6, 1, 30, 1, "등장 길이", "timing", "f"),
  spacing: num(0.12, -0.2, 1, 0.01, "자간(em)", "size"),
  color: col(PAL.red, "글자 색"),
});
export type BrushLabelP = z.infer<typeof BrushLabelParams>;
export const BrushLabel: React.FC<{ text: string; x: number; y: number; at: number; out?: number; p?: Partial<BrushLabelP> }> = ({ text, x, y, at, out, p }) => {
  const P = def(BrushLabelParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const k = lin(f, at, at + P.popLen, 0, 1, Easing.out(Easing.cubic));
  const o = out !== undefined ? lin(f, out, out + 6, 1, 0) : 1;
  const fid = `bl${Math.round(x)}${Math.round(y)}`;
  return (
    <div style={{ position: "absolute", left: x, top: y, transform: `translate(-50%,-50%) rotate(${P.rot}deg) scale(${1.25 - 0.25 * k})`, opacity: k * o, whiteSpace: "nowrap" }}>
      <svg width={0} height={0} style={{ position: "absolute" }}>
        <filter id={fid} x="-10%" y="-20%" width="120%" height="140%">
          <feTurbulence type="fractalNoise" baseFrequency="0.09 0.03" numOctaves={3} seed={17} result="n" />
          <feDisplacementMap in="SourceGraphic" in2="n" scale={P.rough} xChannelSelector="R" yChannelSelector="G" />
        </filter>
      </svg>
      <div style={{ fontFamily: "Dohyeon", fontSize: P.size, letterSpacing: `${P.spacing}em`, color: P.color, filter: `url(#${fid}) drop-shadow(0 0 ${P.glow * 0.4}px #fff) drop-shadow(0 0 ${P.glow}px rgba(255,245,235,0.9))` }}>{text}</div>
    </div>
  );
};
