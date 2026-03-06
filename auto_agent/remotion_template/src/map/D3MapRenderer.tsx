import React, { useEffect, useMemo, useState } from "react";
import { delayRender, continueRender, staticFile } from "remotion";
import { geoMercator, geoPath } from "d3-geo";
import type { CameraState } from "./cameraInterpolation";
import type { RouteData, TerritoryData } from "../types/manifest";
import { useMapTheme } from "./MapThemeContext";

/* ── D3 스타일 테마 ──────────────────────────── */

export interface D3StyleTheme {
  /** 바다/배경색 */
  ocean: string;
  /** 육지 채움색 */
  land: string;
  /** 육지 테두리색 */
  landStroke: string;
  /** 육지 테두리 두께 */
  landStrokeWidth: number;
  /** 국경선 색 */
  borderStroke: string;
  /** 국경선 두께 */
  borderStrokeWidth: number;
  /** 국경선 대시 (없으면 실선) */
  borderDash?: string;
  /** 도/시 경계선 (admin-1) */
  adminStroke?: string;
  adminStrokeWidth?: number;
  /** 해안선 */
  coastlineStroke?: string;
  coastlineStrokeWidth?: number;
  /** 강 */
  riverStroke?: string;
  riverStrokeWidth?: number;
  riverOpacity?: number;
  /** 호수 */
  lakeFill?: string;
  lakeStroke?: string;
  lakeStrokeWidth?: number;
  /** 도시 라벨 색 */
  cityLabelColor?: string;
  /** 도시 라벨 후광(halo) 색 */
  cityLabelHalo?: string;
  /** 전체 CSS 필터 (세피아 등) */
  cssFilter?: string;
}

export const D3_THEMES: Record<string, D3StyleTheme> = {
  vintage_parchment: {
    ocean: "#D4C5A9",
    land: "#F5E6C8",
    landStroke: "#5E4830",
    landStrokeWidth: 1.8,
    borderStroke: "#3E2E18",
    borderStrokeWidth: 1.0,
    borderDash: "4,2",
    adminStroke: "#7A6A4C",
    adminStrokeWidth: 0.7,
    coastlineStroke: "#5E4830",
    coastlineStrokeWidth: 1.2,
    riverStroke: "#7A6A4C",
    riverStrokeWidth: 1.0,
    riverOpacity: 0.6,
    lakeFill: "#CFC0A6",
    lakeStroke: "#7A6A4C",
    lakeStrokeWidth: 0.6,
    cityLabelColor: "#5A4A3A",
    cityLabelHalo: "#F5E6C8",
  },
  minimal_light: {
    ocean: "#E8EDF2",
    land: "#FAFAFA",
    landStroke: "#708090",
    landStrokeWidth: 1.2,
    borderStroke: "#7A8898",
    borderStrokeWidth: 0.8,
    adminStroke: "#8A96A8",
    adminStrokeWidth: 0.6,
    coastlineStroke: "#708090",
    coastlineStrokeWidth: 0.8,
    riverStroke: "#7888A0",
    riverStrokeWidth: 0.7,
    riverOpacity: 0.55,
    lakeFill: "#C8D4E0",
    lakeStroke: "#7888A0",
    lakeStrokeWidth: 0.5,
    cityLabelColor: "#5A6470",
    cityLabelHalo: "#FAFAFA",
  },
  dark_elegant: {
    ocean: "#1A1A2E",
    land: "#2D2D44",
    landStroke: "#7272A0",
    landStrokeWidth: 1.2,
    borderStroke: "#8282B2",
    borderStrokeWidth: 0.8,
    borderDash: "3,2",
    adminStroke: "#60608A",
    adminStrokeWidth: 0.6,
    coastlineStroke: "#7272A0",
    coastlineStrokeWidth: 1.0,
    riverStroke: "#60608A",
    riverStrokeWidth: 0.7,
    riverOpacity: 0.55,
    lakeFill: "#22223A",
    lakeStroke: "#60608A",
    lakeStrokeWidth: 0.5,
    cityLabelColor: "#9898B8",
    cityLabelHalo: "#2D2D44",
  },
  blueprint: {
    ocean: "#0F2942",
    land: "#1B3A5C",
    landStroke: "#3A6FA5",
    landStrokeWidth: 1.0,
    borderStroke: "#5A8FBF",
    borderStrokeWidth: 0.6,
    adminStroke: "#2A5A85",
    adminStrokeWidth: 0.3,
    coastlineStroke: "#3A6FA5",
    coastlineStrokeWidth: 0.7,
    riverStroke: "#2A5A85",
    riverStrokeWidth: 0.5,
    riverOpacity: 0.5,
    lakeFill: "#143252",
    lakeStroke: "#2A5A85",
    lakeStrokeWidth: 0.3,
    cityLabelColor: "#7AB0DA",
    cityLabelHalo: "#1B3A5C",
  },
  warm_earth: {
    ocean: "#E8DDD3",
    land: "#F0E8DE",
    landStroke: "#706048",
    landStrokeWidth: 1.2,
    borderStroke: "#806848",
    borderStrokeWidth: 0.6,
    adminStroke: "#8A7A60",
    adminStrokeWidth: 0.4,
    coastlineStroke: "#706048",
    coastlineStrokeWidth: 0.8,
    riverStroke: "#8A7A60",
    riverStrokeWidth: 0.6,
    riverOpacity: 0.55,
    lakeFill: "#D5CCC0",
    lakeStroke: "#8A7A60",
    lakeStrokeWidth: 0.4,
    cityLabelColor: "#6A5A4A",
    cityLabelHalo: "#F0E8DE",
  },
};

export type D3ThemeName = keyof typeof D3_THEMES;

/* ── GeoJSON 데이터 로딩 ────────────────────── */

type GeoJSONData = GeoJSON.FeatureCollection;

function useGeoJSON(path: string): GeoJSONData | null {
  const [data, setData] = useState<GeoJSONData | null>(null);
  const [handle] = useState(() => delayRender(`Loading GeoJSON: ${path}`));

  useEffect(() => {
    const url = staticFile(path);
    fetch(url)
      .then((res) => res.json())
      .then((json: GeoJSONData) => {
        setData(json);
        continueRender(handle);
      })
      .catch((err) => {
        console.error("GeoJSON load failed:", path, err);
        continueRender(handle);
      });
  }, [path, handle]);

  return data;
}

/* ── 경로 SVG (테마 기반 glow/dash) ──────────── */

interface RoutePathSVGProps {
  routeRender: { d: string; totalLength: number; dashOffset: number };
  route: { data: RouteData; progress: number };
}

const RoutePathSVG: React.FC<RoutePathSVGProps> = ({ routeRender, route }) => {
  let rt;
  try {
    // eslint-disable-next-line react-hooks/rules-of-hooks
    rt = useMapTheme().route;
  } catch {
    rt = null;
  }

  const color = route.data.color ?? rt?.defaultColor ?? "#FF6B6B";
  const width = route.data.width ?? rt?.defaultWidth ?? 4;
  const cap = rt?.lineCap ?? "round";
  const join = rt?.lineJoin ?? "round";
  const opacity = rt?.opacity ?? 0.9;

  // dash 스타일: 테마 dashArray + trim dashoffset 조합
  const isDashed = rt?.style === "dashed" && rt.dashArray;
  // glow: 아래에 넓은 반투명 stroke 추가
  const hasGlow = rt?.style === "glow" && rt.glow;

  return (
    <>
      {/* glow 레이어 */}
      {hasGlow && (
        <path
          d={routeRender.d}
          fill="none"
          stroke={rt!.glow!.color}
          strokeWidth={rt!.glow!.width}
          strokeLinecap={cap}
          strokeLinejoin={join}
          strokeOpacity={rt!.glow!.opacity * route.progress}
          strokeDasharray={routeRender.totalLength}
          strokeDashoffset={routeRender.dashOffset}
        />
      )}
      {/* 메인 경로 */}
      <path
        d={routeRender.d}
        fill="none"
        stroke={color}
        strokeWidth={width}
        strokeLinecap={cap}
        strokeLinejoin={join}
        strokeOpacity={opacity}
        strokeDasharray={isDashed ? rt!.dashArray : routeRender.totalLength}
        strokeDashoffset={isDashed ? undefined : routeRender.dashOffset}
        style={
          isDashed
            ? {
                // dash 스타일은 clip-path로 트림 효과 근사
                clipPath: `inset(0 ${(1 - route.progress) * 100}% 0 0)`,
              }
            : undefined
        }
      />
    </>
  );
};

/* ── D3 맵 렌더러 ────────────────────────────── */

interface D3MapRendererProps {
  /** D3 스타일 테마명 */
  theme: D3ThemeName | D3StyleTheme;
  /** MapLibre 호환 카메라 상태 */
  cameraState: CameraState;
  /** 경로 데이터 (RouteAnimation용) */
  route?: {
    data: RouteData;
    /** 0~1 진행률 — 경로가 점진적으로 그려짐 */
    progress: number;
  };
  /** 영역 데이터 (TerritoryOverlay용) */
  territories?: {
    data: TerritoryData;
    opacity: number;
  }[];
  width?: number;
  height?: number;
  children?: React.ReactNode;
}

/**
 * D3.js 기반 SVG 맵 렌더러.
 *
 * MapLibre와 달리 타일 서버 없이 로컬 GeoJSON으로 렌더링.
 * 완전한 스타일 제어 가능 — 색상, 선, 채움, 폰트 모두 커스텀.
 * SVG 기반이라 delayRender가 타일 로딩에 필요 없음 (GeoJSON 로딩만).
 *
 * MapLibre 카메라 시스템(center, zoom)과 호환:
 * zoom → D3 scale 변환: scale = 256 * 2^zoom / (2π)
 */
export const D3MapRenderer: React.FC<D3MapRendererProps> = ({
  theme,
  cameraState,
  route,
  territories,
  width = 1920,
  height = 1080,
  children,
}) => {
  const themeConfig: D3StyleTheme =
    typeof theme === "string" ? D3_THEMES[theme] ?? D3_THEMES.vintage_parchment : theme;

  // GeoJSON 데이터 로드 — 50m 글로벌 국가별 폴리곤 (모든 지역 커버)
  const countriesData = useGeoJSON("geojson/natural-earth/ne_50m_admin_0_countries.geojson");
  const landData = null; // countriesData로 대체
  const borderData = useGeoJSON(
    "geojson/natural-earth/ne_50m_admin_0_boundary_lines_land.geojson",
  );
  const adminData = useGeoJSON(
    "geojson/natural-earth/ne_50m_admin_1_states_provinces_lines.geojson",
  );
  const coastlineData = null;
  const riverData = null;
  const lakeData = null;

  // MapLibre zoom → D3 scale 변환
  // MapLibre GL JS는 tileSize=512 기준: worldSize = 512 * 2^zoom
  // D3 geoMercator scale = worldSize / (2π)
  const scale = useMemo(() => {
    return (512 * Math.pow(2, cameraState.zoom)) / (2 * Math.PI);
  }, [cameraState.zoom]);

  // D3 메르카토르 투영 설정
  const projection = useMemo(() => {
    return geoMercator()
      .center(cameraState.center)
      .scale(scale)
      .translate([width / 2, height / 2]);
  }, [cameraState.center[0], cameraState.center[1], scale, width, height]);

  // SVG path 생성기
  const pathGen = useMemo(() => geoPath(projection), [projection]);

  // 경로: 전체 SVG path + stroke-dashoffset 트림 방식
  const routeRender = useMemo(() => {
    if (!route?.data?.coordinates || route.data.coordinates.length < 2) return null;
    const coords = route.data.coordinates;

    // 전체 경로 path (고정 — 프레임마다 변하지 않음)
    const lineGeoJSON: GeoJSON.Feature = {
      type: "Feature",
      properties: {},
      geometry: { type: "LineString", coordinates: coords },
    };
    const d = pathGen(lineGeoJSON);
    if (!d) return null;

    // 투영된 화면 좌표로 전체 path 길이 근사 계산
    let totalLength = 0;
    for (let i = 1; i < coords.length; i++) {
      const p0 = projection(coords[i - 1] as [number, number]);
      const p1 = projection(coords[i] as [number, number]);
      if (p0 && p1) {
        const dx = p1[0] - p0[0];
        const dy = p1[1] - p0[1];
        totalLength += Math.sqrt(dx * dx + dy * dy);
      }
    }

    // dashoffset: totalLength → 0 (진행률에 따라 reveal)
    const dashOffset = totalLength * (1 - route.progress);

    return { d, totalLength, dashOffset };
  }, [route, pathGen, projection]);

  return (
    <div
      style={{
        position: "relative",
        width,
        height,
        overflow: "hidden",
        filter: themeConfig.cssFilter || undefined,
      }}
    >
      <svg width={width} height={height} style={{ display: "block" }}>
        {/* 바다/배경 */}
        <rect width={width} height={height} fill={themeConfig.ocean} />

        {/* 국가별 폴리곤 — 인접국 구분을 위해 명도 변주 */}
        {countriesData?.features.map((feature, i) => {
          // 국가 인덱스 기반 명도 변주 (base land color ± offset)
          const offsets = [0, 0.06, -0.04, 0.03, -0.06, 0.08, -0.02, 0.05];
          const offset = offsets[i % offsets.length];
          // HSL 변환 없이 간단한 RGB 명도 조정
          const base = themeConfig.land;
          const r = parseInt(base.slice(1, 3), 16);
          const g = parseInt(base.slice(3, 5), 16);
          const b = parseInt(base.slice(5, 7), 16);
          const clamp = (v: number) => Math.max(0, Math.min(255, Math.round(v)));
          const adj = 255 * offset;
          const fill = `rgb(${clamp(r + adj)}, ${clamp(g + adj)}, ${clamp(b + adj)})`;
          return (
            <path
              key={`country-${i}`}
              d={pathGen(feature) || ""}
              fill={fill}
              stroke={themeConfig.landStroke}
              strokeWidth={themeConfig.landStrokeWidth}
            />
          );
        })}

        {/* 호수 — 육지 위, 경계선 아래 */}
        {lakeData?.features.map((feature, i) => (
          <path
            key={`lake-${i}`}
            d={pathGen(feature) || ""}
            fill={themeConfig.lakeFill ?? themeConfig.ocean}
            stroke={themeConfig.lakeStroke ?? themeConfig.landStroke}
            strokeWidth={themeConfig.lakeStrokeWidth ?? 0.3}
            strokeOpacity={0.6}
          />
        ))}

        {/* 강 — 호수 위, 경계선 아래 */}
        {riverData?.features.map((feature, i) => (
          <path
            key={`river-${i}`}
            d={pathGen(feature) || ""}
            fill="none"
            stroke={themeConfig.riverStroke ?? themeConfig.landStroke}
            strokeWidth={themeConfig.riverStrokeWidth ?? 0.5}
            strokeOpacity={themeConfig.riverOpacity ?? 0.4}
            strokeLinecap="round"
          />
        ))}

        {/* 도/시 경계선 (admin-1) — 국경선보다 아래 */}
        {adminData?.features.map((feature, i) => (
          <path
            key={`admin-${i}`}
            d={pathGen(feature) || ""}
            fill="none"
            stroke={themeConfig.adminStroke ?? themeConfig.borderStroke}
            strokeWidth={themeConfig.adminStrokeWidth ?? 0.3}
            strokeOpacity={0.6}
          />
        ))}

        {/* 국경선 */}
        {borderData?.features.map((feature, i) => (
          <path
            key={`border-${i}`}
            d={pathGen(feature) || ""}
            fill="none"
            stroke={themeConfig.borderStroke}
            strokeWidth={themeConfig.borderStrokeWidth}
            strokeDasharray={themeConfig.borderDash}
          />
        ))}

        {/* 국가명 라벨 — 뷰포트 내 국가만 표시 */}
        {countriesData?.features.map((feature, i) => {
          const props = feature.properties as Record<string, unknown>;
          const labelX = props.LABEL_X as number | undefined;
          const labelY = props.LABEL_Y as number | undefined;
          const name = (props.NAME_KO as string) || (props.NAME as string) || "";
          if (!labelX || !labelY || !name) return null;
          const projected = projection([labelX, labelY]);
          if (!projected) return null;
          const [px, py] = projected;
          // 뷰포트 밖이면 스킵 (여유 50px)
          if (px < -50 || px > width + 50 || py < -50 || py > height + 50) return null;
          return (
            <text
              key={`cname-${i}`}
              x={px}
              y={py}
              textAnchor="middle"
              dominantBaseline="central"
              style={{
                fontFamily: "'Pretendard', sans-serif",
                fontSize: 14,
                fontWeight: 500,
                fill: themeConfig.landStroke,
                opacity: 0.6,
                letterSpacing: "0.05em",
                pointerEvents: "none",
              }}
            >
              {name}
            </text>
          );
        })}

        {/* 해안선 — 국경선 위, 선명한 해안선 강조 */}
        {coastlineData?.features.map((feature, i) => (
          <path
            key={`coast-${i}`}
            d={pathGen(feature) || ""}
            fill="none"
            stroke={themeConfig.coastlineStroke ?? themeConfig.landStroke}
            strokeWidth={themeConfig.coastlineStrokeWidth ?? 0.6}
            strokeOpacity={0.7}
            strokeLinecap="round"
          />
        ))}

        {/* 영역 오버레이 */}
        {territories?.map((t, i) => {
          const geo = t.data.geojsonInline as GeoJSON.Feature | undefined;
          if (!geo) return null;
          return (
            <path
              key={`territory-${i}`}
              d={pathGen(geo) || ""}
              fill={t.data.fillColor}
              fillOpacity={t.data.fillOpacity * t.opacity}
              stroke={t.data.strokeColor || "none"}
              strokeWidth={1}
            />
          );
        })}

        {/* 경로 — stroke-dashoffset 트림으로 깔끔한 reveal */}
        {routeRender && <RoutePathSVG routeRender={routeRender} route={route!} />}

      </svg>

      {/* HTML 오버레이 (마커, 라벨 등) — SVG 위에 확실히 렌더 */}
      {children && (
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width,
            height,
            pointerEvents: "none",
            zIndex: 10,
          }}
        >
          {children}
        </div>
      )}
    </div>
  );
};
