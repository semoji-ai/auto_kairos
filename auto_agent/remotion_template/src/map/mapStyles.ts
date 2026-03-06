/**
 * 맵 스타일 프리셋 — MapLibre(타일) + D3(SVG) 하이브리드
 *
 * renderer 필드로 구분:
 * - "maplibre": OpenFreeMap 벡터 타일 기반, 현실적 지도
 * - "d3": Natural Earth GeoJSON + SVG 기반, 완전한 스타일 제어
 *
 * 사용 기준:
 * - 실제 도로/건물 디테일이 필요 → MapLibre (modern_clean, historical 등)
 * - 스타일리시/미니멀/역사 다큐 느낌 → D3 (vintage_parchment, dark_elegant 등)
 */

import type { D3ThemeName } from "./D3MapRenderer";

/* ── 통합 스타일 설정 ────────────────────────── */

export interface MapStyleConfig {
  renderer: "maplibre" | "d3";
  /** MapLibre: 타일 스타일 URL */
  url?: string;
  /** MapLibre: CSS 필터 (세피아 등) */
  cssFilter?: string;
  /** D3: 테마명 */
  d3Theme?: D3ThemeName;
  /** 설명 (에이전트/UI 참조용) */
  description: string;
  /** 권장 용도 */
  recommended: string;
}

export const MAP_STYLES: Record<string, MapStyleConfig> = {
  /* ── MapLibre 기반 (타일) ── */
  modern_clean: {
    renderer: "maplibre",
    url: "https://tiles.openfreemap.org/styles/bright",
    description: "깔끔한 현대풍 지도",
    recommended: "현대 도시, 정보 콘텐츠, 뉴스",
  },
  historical: {
    renderer: "maplibre",
    url: "https://tiles.openfreemap.org/styles/bright",
    cssFilter: "sepia(0.25) saturate(0.8) brightness(0.95)",
    description: "세피아 빈티지 지도 (타일 기반)",
    recommended: "역사 콘텐츠 (도로/지형 디테일 필요 시)",
  },
  dark_cyber: {
    renderer: "maplibre",
    url: "https://tiles.openfreemap.org/styles/dark",
    description: "어두운 사이버 톤 지도",
    recommended: "테크, 사이버, 미래",
  },

  /* ── D3 기반 (SVG) ── */
  vintage_parchment: {
    renderer: "d3",
    d3Theme: "vintage_parchment",
    description: "양피지/고지도 느낌, 따뜻한 톤",
    recommended: "역사 다큐, 고전, 탐험",
  },
  minimal_light: {
    renderer: "d3",
    d3Theme: "minimal_light",
    description: "밝고 깔끔한 미니멀 지도",
    recommended: "교육, 설명, 인포그래픽",
  },
  dark_elegant: {
    renderer: "d3",
    d3Theme: "dark_elegant",
    description: "어두운 배경 + 우아한 선",
    recommended: "고급스러운 다큐, 밤 분위기",
  },
  blueprint: {
    renderer: "d3",
    d3Theme: "blueprint",
    description: "청사진/설계도 느낌",
    recommended: "군사, 전략, 건축",
  },
  warm_earth: {
    renderer: "d3",
    d3Theme: "warm_earth",
    description: "따뜻한 대지색 톤",
    recommended: "자연, 여행, 지리",
  },
} as const;

export type MapStylePreset = keyof typeof MAP_STYLES;

/**
 * 스타일 프리셋명을 해석.
 * MapLibre용 URL이나 D3 테마를 포함한 전체 설정을 반환.
 */
export function resolveMapStyle(styleOrUrl?: string): MapStyleConfig {
  if (!styleOrUrl) return MAP_STYLES.modern_clean;
  if (styleOrUrl in MAP_STYLES) {
    return MAP_STYLES[styleOrUrl as MapStylePreset];
  }
  // 프리셋에 없으면 URL로 간주 → MapLibre
  return {
    renderer: "maplibre",
    url: styleOrUrl,
    description: "커스텀 URL",
    recommended: "",
  };
}
