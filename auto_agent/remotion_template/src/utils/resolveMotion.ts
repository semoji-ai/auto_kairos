/**
 * resolveMotion — motion preset 이름을 구체적 애니메이션 파라미터로 변환
 *
 * script-director가 씬 작성 시 `motion: "stagger_wave"` 같은 프리셋 이름을 지정하면,
 * 이 함수가 Remotion 렌더러에서 사용할 구체적 애니메이션 설정으로 변환합니다.
 *
 * 모든 프리셋은 BuildingBlocks.tsx의 기존 훅(useFadeRise, useShake 등)으로 구현 가능합니다.
 */

/* ── 타입 정의 ── */

export type MotionPreset =
  | "fade_rise"
  | "stagger_wave"
  | "cascade_rank"
  | "count_and_grow"
  | "number_spotlight"
  | "pie_spin"
  | "dramatic_shake"
  | "glitch_alert"
  | "bounce_celebrate"
  | "calm_float"
  | "type_and_draw"
  | "split_compare"
  | "map_reveal"
  | "cinematic_fade"
  | "build_sequence";

export type EntranceType =
  | "fade"
  | "fadeRise"
  | "fadeSlide"
  | "scale"
  | "spring"
  | "overshoot"
  | "bounce"
  | "typewriter";

export type EmphasisType =
  | "countUp"
  | "shake"
  | "glitch"
  | "pulse"
  | "glow"
  | "bounce"
  | "lineExpand"
  | "none";

export type StaggerPattern = "sequential" | "wave" | "cascade";

export interface MotionConfig {
  /** 프리셋 이름 (디버그/로깅용) */
  preset: MotionPreset;

  /** 진입 애니메이션 */
  entrance: {
    type: EntranceType;
    duration: number;
    easing: string;
    direction?: "up" | "down" | "left" | "right";
    rise?: number;
    springConfig?: { damping: number; stiffness: number };
  };

  /** 스태거 설정 (items가 여러 개일 때) */
  stagger?: {
    gap: number;
    pattern: StaggerPattern;
  };

  /** 강조 효과 (entrance 이후) */
  emphasis?: {
    type: EmphasisType;
    delay: number;
    duration: number;
    intensity?: number;
  };

  /** SVG 효과 */
  svg?: {
    type: "line_draw" | "path_morph";
    duration: number;
  };

  /** 배경 효과 */
  background?: {
    spotlight: boolean;
    vignette: boolean;
    grain: boolean;
  };

  /** 전체 씬 속도 계수 (1.0 = 기본, 0.7 = 느림, 1.3 = 빠름) */
  speedFactor: number;
}

/* ── 프리셋 정의 ── */

const PRESETS: Record<MotionPreset, MotionConfig> = {
  /* ─── 기본 등장 계열 ─── */

  fade_rise: {
    preset: "fade_rise",
    entrance: { type: "fadeRise", duration: 20, easing: "easeOutCubic", rise: 25 },
    speedFactor: 1.0,
  },

  stagger_wave: {
    preset: "stagger_wave",
    entrance: { type: "fadeRise", duration: 20, easing: "easeOutCubic", rise: 25 },
    stagger: { gap: 8, pattern: "wave" },
    speedFactor: 1.0,
  },

  cascade_rank: {
    preset: "cascade_rank",
    entrance: { type: "overshoot", duration: 22, easing: "easeOutBack", direction: "down" },
    stagger: { gap: 10, pattern: "cascade" },
    speedFactor: 1.0,
  },

  /* ─── 숫자/데이터 강조 계열 ─── */

  count_and_grow: {
    preset: "count_and_grow",
    entrance: { type: "fadeRise", duration: 15, easing: "easeOutCubic", rise: 15 },
    stagger: { gap: 6, pattern: "sequential" },
    emphasis: { type: "countUp", delay: 5, duration: 40 },
    speedFactor: 1.0,
  },

  number_spotlight: {
    preset: "number_spotlight",
    entrance: {
      type: "spring",
      duration: 25,
      easing: "easeOutCubic",
      springConfig: { damping: 150, stiffness: 100 },
    },
    emphasis: { type: "glow", delay: 20, duration: 30 },
    background: { spotlight: true, vignette: false, grain: false },
    speedFactor: 1.0,
  },

  pie_spin: {
    preset: "pie_spin",
    entrance: { type: "fade", duration: 10, easing: "easeOutCubic" },
    stagger: { gap: 12, pattern: "sequential" },
    emphasis: { type: "countUp", delay: 10, duration: 45 },
    speedFactor: 1.0,
  },

  /* ─── 감정/드라마 계열 ─── */

  dramatic_shake: {
    preset: "dramatic_shake",
    entrance: { type: "fadeRise", duration: 12, easing: "easeOutQuart", rise: 15 },
    stagger: { gap: 4, pattern: "wave" },
    emphasis: { type: "shake", delay: 0, duration: 18, intensity: 6 },
    speedFactor: 1.3,
  },

  glitch_alert: {
    preset: "glitch_alert",
    entrance: { type: "fade", duration: 8, easing: "easeOutExpo" },
    emphasis: { type: "glitch", delay: 0, duration: 15, intensity: 4 },
    background: { spotlight: false, vignette: true, grain: true },
    speedFactor: 1.2,
  },

  bounce_celebrate: {
    preset: "bounce_celebrate",
    entrance: { type: "bounce", duration: 25, easing: "easeOutBounce" },
    stagger: { gap: 8, pattern: "wave" },
    emphasis: { type: "pulse", delay: 25, duration: 40 },
    speedFactor: 1.0,
  },

  calm_float: {
    preset: "calm_float",
    entrance: { type: "fade", duration: 30, easing: "easeOutCubic" },
    emphasis: { type: "pulse", delay: 30, duration: 60 },
    speedFactor: 0.7,
  },

  /* ─── 특수 효과 계열 ─── */

  type_and_draw: {
    preset: "type_and_draw",
    entrance: { type: "typewriter", duration: 40, easing: "linear" },
    svg: { type: "line_draw", duration: 30 },
    speedFactor: 0.9,
  },

  split_compare: {
    preset: "split_compare",
    entrance: { type: "fadeSlide", duration: 20, easing: "easeOutCubic" },
    stagger: { gap: 0, pattern: "sequential" },
    speedFactor: 1.0,
  },

  map_reveal: {
    preset: "map_reveal",
    entrance: { type: "fade", duration: 15, easing: "easeOutCubic" },
    stagger: { gap: 10, pattern: "sequential" },
    speedFactor: 0.9,
  },

  cinematic_fade: {
    preset: "cinematic_fade",
    entrance: { type: "fade", duration: 45, easing: "easeOutCubic" },
    background: { spotlight: false, vignette: true, grain: true },
    speedFactor: 0.6,
  },

  build_sequence: {
    preset: "build_sequence",
    entrance: { type: "fadeRise", duration: 18, easing: "easeOutCubic", rise: 20 },
    stagger: { gap: 12, pattern: "sequential" },
    svg: { type: "line_draw", duration: 20 },
    emphasis: { type: "pulse", delay: 0, duration: 30 },
    speedFactor: 1.0,
  },
};

/* ── 공개 API ── */

/**
 * motion 프리셋 이름을 구체적 MotionConfig로 변환.
 * 알 수 없는 프리셋이면 fade_rise로 폴백.
 */
export function resolveMotion(preset?: string | null): MotionConfig {
  if (!preset || !(preset in PRESETS)) {
    return PRESETS.fade_rise;
  }
  return PRESETS[preset as MotionPreset];
}

/**
 * mood에 따라 MotionConfig의 속도/강도를 미세 조절.
 * resolveMotion() 결과를 받아 mood 보정을 적용합니다.
 */
export function applyMoodModifier(
  config: MotionConfig,
  mood?: string | null,
): MotionConfig {
  if (!mood) return config;

  const result = { ...config, entrance: { ...config.entrance } };

  switch (mood) {
    case "dramatic":
    case "urgent":
      result.speedFactor *= 1.15;
      if (result.entrance.duration > 10) {
        result.entrance.duration = Math.round(result.entrance.duration * 0.85);
      }
      break;

    case "contemplative":
    case "somber":
      result.speedFactor *= 0.8;
      result.entrance.duration = Math.round(result.entrance.duration * 1.3);
      break;

    case "triumphant":
      result.speedFactor *= 1.1;
      break;

    case "suspense":
      result.speedFactor *= 0.75;
      result.entrance.duration = Math.round(result.entrance.duration * 1.4);
      break;

    // informative: 기본값 유지
  }

  return result;
}

/**
 * items 개수에 따라 stagger gap을 자동 조정.
 * 아이템이 많으면 gap을 좁혀서 전체 등장 시간이 너무 길어지지 않게 합니다.
 */
export function adjustStaggerForItemCount(
  config: MotionConfig,
  itemCount: number,
): MotionConfig {
  if (!config.stagger || itemCount <= 1) return config;

  const result = { ...config, stagger: { ...config.stagger } };

  if (itemCount >= 8) {
    result.stagger.gap = Math.max(3, Math.round(config.stagger.gap * 0.5));
  } else if (itemCount >= 5) {
    result.stagger.gap = Math.max(4, Math.round(config.stagger.gap * 0.75));
  }

  return result;
}

/**
 * 편의 함수: preset + mood + itemCount를 한 번에 처리.
 */
export function resolveSceneMotion(
  preset?: string | null,
  mood?: string | null,
  itemCount?: number,
): MotionConfig {
  let config = resolveMotion(preset);
  config = applyMoodModifier(config, mood);
  if (itemCount != null && itemCount > 0) {
    config = adjustStaggerForItemCount(config, itemCount);
  }
  return config;
}

/** 모든 프리셋 이름 목록 */
export const MOTION_PRESET_NAMES = Object.keys(PRESETS) as MotionPreset[];
