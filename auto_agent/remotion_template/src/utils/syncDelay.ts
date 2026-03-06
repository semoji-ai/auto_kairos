import type { VizAnimationConfig } from "../types/manifest";

/**
 * 시각화 아이템의 등장 프레임을 계산한다.
 *
 * itemSyncPoints가 있으면 나레이션 타이밍에 동기화하고,
 * 없으면 stagger 기반 폴백을 사용한다.
 *
 * stagger/itemDuration 단위: 밀리초(ms) — 프레임으로 변환하여 반환.
 */
export function calcItemDelay(
  itemIndex: number,
  fps: number,
  vizAnimation: VizAnimationConfig | undefined,
  fallbackBaseDelay: number,
  fallbackStagger: number,
  /** 아이템 라벨 배열 (label 기반 syncPoints 매칭용) */
  items?: string[],
): number {
  const syncPoints = vizAnimation?.itemSyncPoints;
  if (syncPoints && syncPoints.length > 0) {
    // itemIndex 직접 매칭
    const byIndex = syncPoints.find((sp) => sp.itemIndex === itemIndex);
    if (byIndex) {
      const sec = byIndex.startSec ?? byIndex.timeSec ?? 0;
      return Math.floor(sec * fps);
    }
    // label 기반 매칭 (Editor가 {label, timeSec} 형식으로 생성)
    if (items && items[itemIndex]) {
      const byLabel = syncPoints.find(
        (sp) => sp.label === items[itemIndex],
      );
      if (byLabel) {
        const sec = byLabel.startSec ?? byLabel.timeSec ?? 0;
        return Math.floor(sec * fps);
      }
    }
  }
  // 폴백: stagger 기반 (ms → frames)
  const staggerMs = vizAnimation?.stagger ?? 0;
  if (staggerMs > 0) {
    const staggerFrames = Math.floor((staggerMs / 1000) * fps);
    return fallbackBaseDelay + itemIndex * staggerFrames;
  }
  return fallbackBaseDelay + itemIndex * fallbackStagger;
}

/** ms 단위 값을 프레임으로 변환 (0이면 fallback 반환, 최소 1프레임 보장) */
export function msToFrames(ms: number | undefined, fps: number, fallback: number): number {
  if (ms && ms > 0) {
    return Math.max(1, Math.floor((ms / 1000) * fps));
  }
  return fallback;
}
