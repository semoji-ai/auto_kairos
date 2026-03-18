import React, { createContext, useContext, useMemo } from "react";
import { STYLE, TYPO, LAYOUT, VIZ_FONT, VIZ_TITLE_FONT } from "../visualizations/vizStyles";
import type { DesignTokens } from "../types/manifest";

/**
 * 컴포넌트에서 사용하는 디자인 토큰 형태
 * vizStyles.ts의 기본값과 동일한 구조
 */
export interface ResolvedTokens {
  STYLE: typeof STYLE;
  TYPO: typeof TYPO;
  LAYOUT: typeof LAYOUT;
  VIZ_FONT: string;
  VIZ_TITLE_FONT: string;
}

const DEFAULTS: ResolvedTokens = {
  STYLE,
  TYPO,
  LAYOUT,
  VIZ_FONT,
  VIZ_TITLE_FONT,
};

const DesignTokenContext = createContext<ResolvedTokens>(DEFAULTS);

/** 재귀 깊은 병합: override 값이 있으면 대체, 없으면 base 유지 */
function deepMerge<T extends Record<string, any>>(base: T, override: Record<string, any>): T {
  const result = { ...base } as any;
  for (const key of Object.keys(override)) {
    const val = override[key];
    if (val !== undefined && val !== null) {
      if (
        typeof val === "object" &&
        !Array.isArray(val) &&
        typeof result[key] === "object" &&
        !Array.isArray(result[key])
      ) {
        result[key] = deepMerge(result[key], val);
      } else {
        result[key] = val;
      }
    }
  }
  return result;
}

interface ProviderProps {
  tokens?: DesignTokens;
  children: React.ReactNode;
}

export const DesignTokenProvider: React.FC<ProviderProps> = ({
  tokens,
  children,
}) => {
  const merged = useMemo<ResolvedTokens>(() => {
    if (!tokens) return DEFAULTS;
    return {
      STYLE: deepMerge(STYLE as any, tokens.style ?? {}) as typeof STYLE,
      TYPO: deepMerge(TYPO as any, tokens.typo ?? {}) as typeof TYPO,
      LAYOUT: deepMerge(LAYOUT as any, tokens.layout ?? {}) as typeof LAYOUT,
      VIZ_FONT: tokens.vizFont ?? VIZ_FONT,
      VIZ_TITLE_FONT: tokens.vizTitleFont ?? VIZ_TITLE_FONT,
    };
  }, [tokens]);

  const cssVars = useMemo(
    () =>
      ({
        "--viz-bg": merged.STYLE.background,
        "--viz-text": merged.STYLE.text,
        "--viz-subtitle": merged.STYLE.subtitle,
        "--viz-source": merged.STYLE.source,
        "--viz-grid": merged.STYLE.grid,
        "--viz-card-bg": merged.STYLE.cardBg,
        "--viz-border": merged.STYLE.border,
        "--viz-card-radius": `${merged.STYLE.cardRadius}px`,
        "--viz-card-shadow": merged.STYLE.cardShadow,
        "--viz-positive": merged.STYLE.semantic.positive,
        "--viz-positive-bg": merged.STYLE.semantic.positiveBg,
        "--viz-negative": merged.STYLE.semantic.negative,
        "--viz-negative-bg": merged.STYLE.semantic.negativeBg,
        ...merged.STYLE.colors.reduce(
          (acc, c, i) => ({ ...acc, [`--viz-color-${i}`]: c }),
          {} as Record<string, string>,
        ),
        "--viz-title-size": `${merged.TYPO.title.size}px`,
        "--viz-title-weight": String(merged.TYPO.title.weight),
        "--viz-title-tracking": merged.TYPO.title.letterSpacing,
        "--viz-hero-size": `${merged.TYPO.hero.size}px`,
        "--viz-hero-weight": String(merged.TYPO.hero.weight),
        "--viz-hero-tracking": merged.TYPO.hero.letterSpacing,
        "--viz-subtitle-size": `${merged.TYPO.subtitle.size}px`,
        "--viz-subtitle-weight": String(merged.TYPO.subtitle.weight),
        "--viz-label-size": `${merged.TYPO.label.size}px`,
        "--viz-label-weight": String(merged.TYPO.label.weight),
        "--viz-value-size": `${merged.TYPO.value.size}px`,
        "--viz-value-weight": String(merged.TYPO.value.weight),
        "--viz-caption-size": `${merged.TYPO.caption.size}px`,
        "--viz-caption-weight": String(merged.TYPO.caption.weight),
        "--viz-top-margin": `${merged.LAYOUT.topMargin}%`,
        "--viz-side-padding": `${merged.LAYOUT.sidePadding}%`,
        "--viz-safe-zone": `${merged.LAYOUT.safeZoneHeight}%`,
        "--viz-font": merged.VIZ_FONT,
        "--viz-title-font": merged.VIZ_TITLE_FONT,
      }) as React.CSSProperties,
    [merged],
  );

  return (
    <DesignTokenContext.Provider value={merged}>
      <div style={cssVars}>{children}</div>
    </DesignTokenContext.Provider>
  );
};

export const useDesignTokens = (): ResolvedTokens =>
  useContext(DesignTokenContext);
