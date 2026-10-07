// 울릉도·독도 섬 영역 오버레이 — 한반도 전도가 크게 보이는 지도에서 섬이 데이터 누락으로 빠지지 않게 좌표로 그린다(사용자 필수 규칙).
// 라벨은 강제가 아니다(labels/eastSea 기본 false) — 연출상 필요할 때만 켠다. 지구본·광역 소축척 지도엔 쓰지 않는다.
// 벡터 타일·Natural Earth 저해상도엔 독도가 안 보이거나 너무 작으므로 좌표로 직접 그리고 최소 크기를 보장한다.
import React from "react";

export const ULLEUNGDO: [number, number] = [130.8667, 37.4833];
export const DOKDO_EAST: [number, number] = [131.8694, 37.2414];   // 동도
export const DOKDO_WEST: [number, number] = [131.8639, 37.2422];   // 서도
export const EAST_SEA_LABEL: [number, number] = [131.2, 39.0];

type XY = { x: number; y: number } | null;
/** project: 경위도 → 화면 좌표(보이지 않으면 null, 예: 지구본 뒷면) */
export const KoreaIslands: React.FC<{
  project: (ll: [number, number]) => XY;
  pxPerDeg?: number;          // 1° 경도당 화면 px(섬 실제 크기 계산용). 모르면 생략 → 최소 크기
  labels?: boolean;           // 섬 이름 라벨
  eastSea?: boolean;          // "동해" 라벨
  land?: string; stroke?: string; labelColor?: string; labelStroke?: string;
  fontFamily?: string; labelSize?: number; opacity?: number;
}> = ({ project, pxPerDeg = 0, labels = false, eastSea = false, land = "#EAD9B6", stroke = "#9C8B6A", labelColor = "#3A2A1C", labelStroke = "#FFFFFF", fontFamily = "NeoHv, sans-serif", labelSize = 26, opacity = 1 }) => {
  const u = project(ULLEUNGDO), de = project(DOKDO_EAST), dw = project(DOKDO_WEST), es = project(EAST_SEA_LABEL);
  // 울릉도 실제 폭 ≈ 0.11° → 최소 반지름 7px, 독도는 점 두 개(최소 3.5px)
  const ur = Math.max(11, (pxPerDeg * 0.11) / 2);
  const dr = Math.max(5.5, pxPerDeg * 0.004);
  const lab = (t: string, p: XY, dx: number, dy: number, size = labelSize) => p && (
    <text x={p.x + dx} y={p.y + dy} fontFamily={fontFamily} fontSize={size} fill={labelColor} stroke={labelStroke} strokeWidth={size * 0.28} paintOrder="stroke" strokeLinejoin="round">{t}</text>
  );
  const gap = de && dw ? Math.max(dr * 2.4, Math.abs(de.x - dw.x)) : 0;
  return (
    <svg style={{ position: "absolute", left: 0, top: 0, overflow: "visible", pointerEvents: "none", opacity }} width={1} height={1}>
      {eastSea && es && <text x={es.x} y={es.y} fontFamily="Yeonsung, 'Songti SC', serif" fontSize={labelSize * 2.2} fill="#6FA3BD" textAnchor="middle" opacity={0.9}>동 해</text>}
      {u && <ellipse cx={u.x} cy={u.y} rx={ur} ry={ur * 0.85} fill={land} stroke={stroke} strokeWidth={1.5} />}
      {de && dw && (<>
        <circle cx={de.x + gap / 2} cy={de.y} r={dr} fill={land} stroke={stroke} strokeWidth={1.2} />
        <circle cx={de.x - gap / 2} cy={dw.y} r={dr * 1.1} fill={land} stroke={stroke} strokeWidth={1.2} />
      </>)}
      {labels && lab("울릉도", u, -ur - labelSize * 3.1, labelSize * 0.35)}
      {labels && lab("독도", de, dr * 2 + 6, labelSize * 0.35)}
    </svg>
  );
};
