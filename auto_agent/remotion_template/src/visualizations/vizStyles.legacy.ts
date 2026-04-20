/**
 * 시각화 디자인 시스템
 * - STYLE: 색상, 그래디언트, 카드 스타일
 * - TYPO: 타이포그래피 스케일
 * - LAYOUT: 레이아웃 비율
 */

export const STYLE = {
  background: "#FFFEF8",
  border: "#3D3B2F",
  text: "#3D3B2F",
  subtitle: "#5D5B4F",
  source: "#8D8B7F",
  grid: "#E8E5DC",
  colors: [
    "#F7D94C", "#FF8A5C", "#5BA8A0", "#FF6B8A",
    "#9B8FD9", "#6BCB77", "#FFB347", "#87CEEB",
    "#DDA0DD", "#98D8C8",
  ],
  gradients: [
    ["#F7D94C", "#FFE88A"],
    ["#FF8A5C", "#FFB899"],
    ["#5BA8A0", "#8CCCC5"],
    ["#FF6B8A", "#FF9EB2"],
    ["#9B8FD9", "#C2B9EC"],
    ["#6BCB77", "#9EE0A5"],
  ],
  cardBg: "#FFFFFF",
  cardShadow: "0 4px 20px rgba(61,59,47,0.08)",
  cardRadius: 16,
  accentIndex: 0,
  semantic: {
    positive: "#2E7D32",
    positiveBg: "#E8F5E9",
    negative: "#C62828",
    negativeBg: "#FFEBEE",
  },
} as const;

export const TYPO = {
  title: { size: 52, weight: 700, letterSpacing: "-0.01em" },
  hero: { size: 64, weight: 800, letterSpacing: "-0.02em" },
  subtitle: { size: 34, weight: 500 },
  label: { size: 26, weight: 600 },
  value: { size: 24, weight: 700 },
  caption: { size: 18, weight: 400 },
} as const;

export const LAYOUT = {
  topMargin: 3,
  sourceHeight: 2,
  titleHeight: 8,
  subtitleHeight: 4,
  chartHeight: 65,
  safeZoneHeight: 18,
  sidePadding: 6,
} as const;

/** 본문/레이블용 폰트 (Pretendard) */
export const VIZ_FONT = "'Pretendard', 'Apple SD Gothic Neo', sans-serif";

/** 제목 전용 폰트 (GriunPolFairness) */
export const VIZ_TITLE_FONT = "'GriunPolFairness', 'Pretendard', 'Apple SD Gothic Neo', sans-serif";

/**
 * 폰트 정의 목록 — VisualizationRenderer에서 FontFace API로 로드
 * (CSS @font-face url()은 Remotion 렌더 서버에서 404이므로 JS 로딩 사용)
 */
export const FONT_DEFS = [
  { family: "GriunPolFairness", file: "fonts/Griun_PolFairness-Rg.ttf", weight: "normal" },
  { family: "Pretendard", file: "fonts/Pretendard-Regular.otf", weight: "400" },
  { family: "Pretendard", file: "fonts/Pretendard-Bold.otf", weight: "700" },
  { family: "SBAggroB", file: "fonts/SBAggroB.otf", weight: "700" },
  { family: "SBAggroL", file: "fonts/SBAggroL.otf", weight: "300" },
] as const;
