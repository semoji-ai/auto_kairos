/**
 * 데이터 양에 따른 적응형 사이징 유틸리티
 */

/** 항목 수에 따라 바 높이 자동 조절 (16~56px) */
export function adaptiveBarSize(itemCount: number, canvasHeight: number): number {
  const maxBar = 56;
  const minBar = 16;
  const available = canvasHeight * 0.7;
  const raw = available / Math.max(itemCount, 1);
  return Math.round(Math.min(maxBar, Math.max(minBar, raw * 0.6)));
}

/** 레이블 길이에 따라 YAxis 너비 자동 조절 (80~300px) */
export function adaptiveYAxisWidth(items: string[], baseFontSize: number): number {
  const longestLen = Math.max(
    ...items.map((s) => {
      const koreanChars = (s.match(/[\u3131-\uD79D]/g) || []).length;
      const latinChars = s.length - koreanChars;
      return koreanChars * 0.85 + latinChars * 0.5;
    }),
    3,
  );
  return Math.min(360, Math.max(100, Math.ceil(longestLen * baseFontSize) + 24));
}

/** 항목 많을수록 폰트 축소 (최소 minScale 비율) */
export function adaptiveFontSize(
  baseSize: number,
  itemCount: number,
  thresholds: { shrinkAt: number; minScale: number },
): number {
  if (itemCount <= thresholds.shrinkAt) return baseSize;
  const scale = Math.max(
    thresholds.minScale,
    1 - (itemCount - thresholds.shrinkAt) * 0.06,
  );
  return Math.round(baseSize * scale);
}

/** 타임라인 항목 간격 자동 조절 */
export function adaptiveTimelineGap(
  itemCount: number,
  canvasHeight: number,
): number {
  const available = canvasHeight * 0.7;
  const perItem = available / Math.max(itemCount, 1);
  return Math.min(40, Math.max(8, perItem * 0.15));
}
