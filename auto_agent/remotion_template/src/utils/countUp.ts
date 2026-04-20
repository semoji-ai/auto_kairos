import { interpolate } from "remotion";

/**
 * 0에서 목표값까지 카운트업 애니메이션
 */
export function countUpValue(
  frame: number,
  startFrame: number,
  duration: number,
  targetValue: number,
  easingFn?: (t: number) => number,
): number {
  const progress = interpolate(
    frame,
    [startFrame, startFrame + duration],
    [0, 1],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: easingFn,
    },
  );
  return Math.round(targetValue * progress);
}
