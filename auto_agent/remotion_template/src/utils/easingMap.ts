import { Easing } from "remotion";

type EasingFn = (t: number) => number;

const EASING_MAP: Record<string, EasingFn> = {
  linear: (t) => t,
  easeInQuad: Easing.in(Easing.quad),
  easeOutQuad: Easing.out(Easing.quad),
  easeInOutQuad: Easing.inOut(Easing.quad),
  easeInCubic: Easing.in(Easing.cubic),
  easeOutCubic: Easing.out(Easing.cubic),
  easeInOutCubic: Easing.inOut(Easing.cubic),
  easeInQuart: Easing.in(Easing.poly(4)),
  easeOutQuart: Easing.out(Easing.poly(4)),
  easeInOutQuart: Easing.inOut(Easing.poly(4)),
  easeOutBack: Easing.out(Easing.back(1.5)),
  easeOutElastic: Easing.out(Easing.elastic(1)),
  easeOutBounce: Easing.out(Easing.bounce),
  easeInExpo: Easing.in(Easing.exp),
  easeOutExpo: Easing.out(Easing.exp),
  easeInOutExpo: Easing.inOut(Easing.exp),
};

/**
 * 이징 문자열 이름 → Remotion Easing 함수 변환
 * unknown 이름은 linear (identity) 반환
 */
export function resolveEasing(name?: string): EasingFn {
  if (!name || name === "linear") return (t) => t;
  return EASING_MAP[name] ?? ((t) => t);
}
