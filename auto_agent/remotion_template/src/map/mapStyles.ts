/**
 * 맵 스타일 프리셋 — MapLibre 전용
 *
 * 모든 테마가 MapLibre 벡터 타일 기반으로 렌더링되며,
 * layerOverrides로 레이어별 색상/선/가시성을 완전 제어한다.
 */

/* ── 레이어 오버라이드 ────────────────────────── */

export interface LayerOverride {
  /** 레이어 ID 매칭 패턴 (정확 매칭 또는 prefix*) */
  match: string;
  /** paint 프로퍼티 오버라이드 */
  paint?: Record<string, unknown>;
  /** layout 프로퍼티 오버라이드 */
  layout?: Record<string, unknown>;
}

/* ── 통합 스타일 설정 ────────────────────────── */

export interface MapStyleConfig {
  /** MapLibre: 타일 스타일 URL */
  url?: string;
  /** MapLibre: CSS 필터 (전체 톤 조정) */
  cssFilter?: string;
  /** MapLibre: 레이어별 paint/layout 오버라이드 */
  layerOverrides?: LayerOverride[];
  /** 설명 (에이전트/UI 참조용) */
  description: string;
  /** 권장 용도 */
  recommended: string;
}

/**
 * 레이어 오버라이드를 MapLibre 맵에 적용한다.
 * map.on("load") 콜백 안에서 호출.
 */
export function applyLayerOverrides(
  map: { getStyle: () => { layers?: { id: string; type: string }[] } | undefined; setPaintProperty: (id: string, prop: string, val: unknown) => void; setLayoutProperty: (id: string, prop: string, val: unknown) => void },
  overrides: LayerOverride[],
): void {
  const style = map.getStyle();
  if (!style?.layers) return;

  for (const override of overrides) {
    const isPrefix = override.match.endsWith("*");
    const prefix = isPrefix ? override.match.slice(0, -1) : "";

    for (const layer of style.layers) {
      const matched = isPrefix
        ? layer.id.startsWith(prefix)
        : layer.id === override.match;
      if (!matched) continue;

      if (override.paint) {
        for (const [prop, val] of Object.entries(override.paint)) {
          try { map.setPaintProperty(layer.id, prop, val); } catch { /* skip */ }
        }
      }
      if (override.layout) {
        for (const [prop, val] of Object.entries(override.layout)) {
          try { map.setLayoutProperty(layer.id, prop, val); } catch { /* skip */ }
        }
      }
    }
  }
}

/* ══════════════════════════════════════════════
   테마별 레이어 오버라이드 정의

   OpenFreeMap (OpenMapTiles 스키마) 주요 레이어:
   - background: 배경색
   - water: 바다/호수 채우기
   - waterway*: 강/수로
   - landcover*: 녹지/숲/관개
   - landuse*: 토지용도
   - park*: 공원
   - boundary*: 행정경계 (admin)
   - road*, transportation*: 도로
   - building*: 건물
   - place*, poi*: 라벨 (symbol)
   ══════════════════════════════════════════════ */

/** vintage_parchment — 양피지/고지도 (bright 타일 기반) */
const VINTAGE_PARCHMENT_OVERRIDES: LayerOverride[] = [
  { match: "background", paint: { "background-color": "#F5E6C8" } },
  { match: "water", paint: { "fill-color": "#C4B08A" } },
  { match: "waterway*", paint: { "line-color": "#B0996E" } },
  { match: "landcover*", paint: { "fill-color": "#E8D8B8", "fill-opacity": 0.5 } },
  { match: "landuse*", paint: { "fill-color": "#E8D8B8", "fill-opacity": 0.3 } },
  { match: "park*", paint: { "fill-color": "#D8CCA8", "fill-opacity": 0.4 } },
  { match: "boundary*", paint: { "line-color": "#7A5C38", "line-width": 1.8, "line-opacity": 0.9 } },
  { match: "road*", paint: { "line-color": "#C0A878", "line-opacity": 0.7 } },
  { match: "building*", paint: { "fill-color": "#E0D0B4", "fill-opacity": 0.4 } },
];

/** minimal_light — 밝고 깔끔한 미니멀 (bright 타일 기반) */
const MINIMAL_LIGHT_OVERRIDES: LayerOverride[] = [
  { match: "background", paint: { "background-color": "#F8F8FA" } },
  { match: "water", paint: { "fill-color": "#C8D8EC" } },
  { match: "waterway*", paint: { "line-color": "#A8C0DA" } },
  { match: "landcover*", paint: { "fill-color": "#EEF2EE", "fill-opacity": 0.4 } },
  { match: "landuse*", paint: { "fill-color": "#F2F2F4", "fill-opacity": 0.3 } },
  { match: "park*", paint: { "fill-color": "#E0EAE0", "fill-opacity": 0.4 } },
  { match: "boundary*", paint: { "line-color": "#8890A0", "line-width": 1.4, "line-opacity": 0.8 } },
  { match: "road*", paint: { "line-color": "#C8CCD2", "line-opacity": 0.8 } },
  { match: "building*", paint: { "fill-color": "#E8E8EA", "fill-opacity": 0.4 } },
];

/** dark_elegant — 어두운 배경 + 골드 (dark 타일 기반) */
const DARK_ELEGANT_OVERRIDES: LayerOverride[] = [
  { match: "background", paint: { "background-color": "#1A1A2E" } },
  { match: "water", paint: { "fill-color": "#14142A" } },
  { match: "waterway*", paint: { "line-color": "#20203A" } },
  { match: "landcover*", paint: { "fill-color": "#252540", "fill-opacity": 0.3 } },
  { match: "landuse*", paint: { "fill-color": "#222238", "fill-opacity": 0.2 } },
  { match: "park*", paint: { "fill-color": "#202038", "fill-opacity": 0.3 } },
  { match: "boundary*", paint: { "line-color": "#9999CC", "line-width": 1.2, "line-opacity": 0.7 } },
  { match: "road*", paint: { "line-color": "#3A3A5A", "line-opacity": 0.5 } },
  { match: "building*", paint: { "fill-color": "#2A2A44", "fill-opacity": 0.3 } },
];

/** blueprint — 청사진/설계도 (dark 타일 기반) */
const BLUEPRINT_OVERRIDES: LayerOverride[] = [
  { match: "background", paint: { "background-color": "#0F2942" } },
  { match: "water", paint: { "fill-color": "#081828" } },
  { match: "waterway*", paint: { "line-color": "#1A3E60" } },
  { match: "landcover*", paint: { "fill-color": "#163050", "fill-opacity": 0.4 } },
  { match: "landuse*", paint: { "fill-color": "#143050", "fill-opacity": 0.3 } },
  { match: "park*", paint: { "fill-color": "#123048", "fill-opacity": 0.3 } },
  { match: "boundary*", paint: { "line-color": "#68A0D0", "line-width": 1.4, "line-opacity": 0.9 } },
  { match: "road*", paint: { "line-color": "#2E6090", "line-opacity": 0.6 } },
  { match: "building*", paint: { "fill-color": "#1A3A5C", "fill-opacity": 0.3 } },
];

/** warm_earth — 따뜻한 대지색 (bright 타일 기반) */
const WARM_EARTH_OVERRIDES: LayerOverride[] = [
  { match: "background", paint: { "background-color": "#F0E8DE" } },
  { match: "water", paint: { "fill-color": "#C8BAA0" } },
  { match: "waterway*", paint: { "line-color": "#B8A888" } },
  { match: "landcover*", paint: { "fill-color": "#E4DCC8", "fill-opacity": 0.5 } },
  { match: "landuse*", paint: { "fill-color": "#E8DDCC", "fill-opacity": 0.3 } },
  { match: "park*", paint: { "fill-color": "#D4CCB8", "fill-opacity": 0.5 } },
  { match: "boundary*", paint: { "line-color": "#8A6E48", "line-width": 1.6, "line-opacity": 0.9 } },
  { match: "road*", paint: { "line-color": "#C8B498", "line-opacity": 0.7 } },
  { match: "building*", paint: { "fill-color": "#E0D6C8", "fill-opacity": 0.4 } },
];

/** matte_slate — 뉴트럴 다크 (dark 타일 기반) */
const MATTE_SLATE_OVERRIDES: LayerOverride[] = [
  { match: "background", paint: { "background-color": "#1A1C22" } },
  { match: "water", paint: { "fill-color": "#0E1018" } },
  { match: "waterway*", paint: { "line-color": "#1E2030" } },
  { match: "landcover*", paint: { "fill-color": "#22242E", "fill-opacity": 0.4 } },
  { match: "landuse*", paint: { "fill-color": "#20222C", "fill-opacity": 0.3 } },
  { match: "park*", paint: { "fill-color": "#1E2028", "fill-opacity": 0.3 } },
  { match: "boundary*", paint: { "line-color": "#6A6E7C", "line-width": 1.4, "line-opacity": 0.8 } },
  { match: "road*", paint: { "line-color": "#383C48", "line-opacity": 0.6 } },
  { match: "building*", paint: { "fill-color": "#24262E", "fill-opacity": 0.3 } },
];

/** historical — 세피아 고전 (bright 타일 기반, CSS 필터 보완) */
const HISTORICAL_OVERRIDES: LayerOverride[] = [
  { match: "boundary*", paint: { "line-color": "#8B7355", "line-width": 1.6, "line-opacity": 0.9 } },
  { match: "water", paint: { "fill-color": "#B8CCD8" } },
  { match: "waterway*", paint: { "line-color": "#9AB0C0" } },
];

/** clean_white — 순백 깔끔한 현대풍 (bright 타일 기반) */
const CLEAN_WHITE_OVERRIDES: LayerOverride[] = [
  { match: "background", paint: { "background-color": "#FFFFFF" } },
  { match: "water", paint: { "fill-color": "#D6E6F5" } },
  { match: "waterway*", paint: { "line-color": "#B0D0F0" } },
  { match: "landcover*", paint: { "fill-color": "#F0F4F0", "fill-opacity": 0.3 } },
  { match: "landuse*", paint: { "fill-color": "#F8F8FA", "fill-opacity": 0.2 } },
  { match: "park*", paint: { "fill-color": "#E8F2E8", "fill-opacity": 0.3 } },
  { match: "boundary*", paint: { "line-color": "#A0AAB8", "line-width": 1.2, "line-opacity": 0.8 } },
  { match: "road*", paint: { "line-color": "#D8DCE4", "line-opacity": 0.7 } },
  { match: "building*", paint: { "fill-color": "#F0F0F4", "fill-opacity": 0.3 } },
];

/** dark_cyber — 사이버 다크 (dark 타일 기반) */
const DARK_CYBER_OVERRIDES: LayerOverride[] = [
  { match: "boundary*", paint: { "line-color": "#4A8080", "line-width": 1.2, "line-opacity": 0.8 } },
  { match: "water", paint: { "fill-color": "#18202A" } },
  { match: "road*", paint: { "line-color": "#2A3540", "line-opacity": 0.6 } },
];

/* ══════════════════════════════════════════════
   테마 레지스트리
   ══════════════════════════════════════════════ */

const BRIGHT_URL = "https://tiles.openfreemap.org/styles/bright";
const DARK_URL = "https://tiles.openfreemap.org/styles/dark";

export const MAP_STYLES: Record<string, MapStyleConfig> = {
  /* ── 기존 MapLibre 테마 (변경 없음) ── */
  modern_clean: {

    url: BRIGHT_URL,
    description: "깔끔한 현대풍 지도",
    recommended: "현대 도시, 정보 콘텐츠, 뉴스",
  },
  historical: {

    url: BRIGHT_URL,
    cssFilter: "sepia(0.2) saturate(0.85) brightness(0.95)",
    layerOverrides: HISTORICAL_OVERRIDES,
    description: "세피아 빈티지 지도 (타일 기반)",
    recommended: "역사 콘텐츠 (도로/지형 디테일 필요 시)",
  },
  dark_cyber: {

    url: DARK_URL,
    layerOverrides: DARK_CYBER_OVERRIDES,
    description: "어두운 사이버 톤 지도",
    recommended: "테크, 사이버, 미래",
  },

  /* ── 레이어 오버라이드 테마 ── */
  vintage_parchment: {

    url: BRIGHT_URL,
    layerOverrides: VINTAGE_PARCHMENT_OVERRIDES,

    description: "양피지/고지도 느낌, 따뜻한 톤",
    recommended: "역사 다큐, 고전, 탐험",
  },
  minimal_light: {

    url: BRIGHT_URL,
    layerOverrides: MINIMAL_LIGHT_OVERRIDES,

    description: "밝고 깔끔한 미니멀 지도",
    recommended: "교육, 설명, 인포그래픽",
  },
  dark_elegant: {

    url: DARK_URL,
    layerOverrides: DARK_ELEGANT_OVERRIDES,

    description: "어두운 배경 + 우아한 골드 라인",
    recommended: "고급스러운 다큐, 밤 분위기",
  },
  blueprint: {

    url: DARK_URL,
    layerOverrides: BLUEPRINT_OVERRIDES,

    description: "청사진/설계도 느낌",
    recommended: "군사, 전략, 건축",
  },
  warm_earth: {

    url: BRIGHT_URL,
    layerOverrides: WARM_EARTH_OVERRIDES,

    description: "따뜻한 대지색 톤",
    recommended: "자연, 여행, 지리",
  },
  matte_slate: {

    url: DARK_URL,
    layerOverrides: MATTE_SLATE_OVERRIDES,

    description: "뉴트럴 다크 — 데이터 시각화 중립 캔버스",
    recommended: "뉴스, 선거, 인포그래픽, 코로플레스",
  },
  clean_white: {

    url: BRIGHT_URL,
    layerOverrides: CLEAN_WHITE_OVERRIDES,

    description: "순백 깔끔한 현대풍 지도",
    recommended: "금융, 교육, 비즈니스, 라이트 모드 콘텐츠",
  },
} as const;

export type MapStylePreset = keyof typeof MAP_STYLES;

/**
 * 스타일 프리셋명을 해석.
 * MapLibre용 URL과 레이어 오버라이드를 포함한 전체 설정을 반환.
 */
export function resolveMapStyle(styleOrUrl?: string): MapStyleConfig {
  if (!styleOrUrl) return MAP_STYLES.modern_clean;
  if (styleOrUrl in MAP_STYLES) {
    return MAP_STYLES[styleOrUrl as MapStylePreset];
  }
  // 프리셋에 없으면 URL로 간주 → MapLibre
  return {

    url: styleOrUrl,
    description: "커스텀 URL",
    recommended: "",
  };
}
