/**
 * BuildingBlocks — 공유 디자인 토큰, 애니메이션 훅, UI 컴포넌트, 유틸리티
 *
 * SimpleScene / CreativeScene 양쪽에서 import하는 공통 빌딩 블록.
 * 아이콘: lucide-react (UI), @icons-pack/react-simple-icons (브랜드), country-flag-icons (국기)
 */
import React from "react";
import {
  useCurrentFrame,
  interpolate,
  Easing,
  staticFile,
  spring,
  useVideoConfig,
} from "remotion";

/* ================================================================
   아이콘 패키지
   ================================================================ */
import type { LucideIcon } from "lucide-react";
import {
  Shield, Lock, ShieldCheck,
  Brain, Cpu, Code, Database, Terminal,
  TrendingUp, Rocket, ArrowUpRight,
  MessageSquare, Mail, Globe,
  DollarSign, BarChart3, Target,
  Users, User, Building,
  Clock, Calendar, History,
  Wrench, Settings, Hammer,
  Search, Eye, Compass,
  CheckCircle, Award, Star,
  AlertTriangle, AlertCircle,
  BookOpen, GraduationCap, Lightbulb,
  HardDrive, Layers,
  Network, Link, GitBranch,
  Swords, Crosshair,
  Crown, Castle, Landmark,
  Heart, Zap, Flame, Bomb,
  Flag, Map, MapPin,
  Plane, Ship, Truck,
  FileText, Newspaper, Mic,
  Camera, Video, Music,
  Phone, Wifi, Radio,
} from "lucide-react";

import * as SimpleIcons from "@icons-pack/react-simple-icons";

import { useDesignPreset, usePresetColors, usePresetTypo, usePresetLayout, resolvePreset } from "../design";
import { usePresetVariants } from "../design/DesignPresetContext";
import type { PresetColors } from "../design/types";
import { DEFAULT_PRESET } from "../design";

/* ================================================================
   Design Tokens — DesignPreset Context 기반
   ================================================================ */

export const FONT = "var(--font-body, 'Pretendard', sans-serif)";

export type VideoThemeName = "dark" | "white";

/** @deprecated — PresetColors 사용 권장 */
export type { PresetColors as ColorTokens } from "../design/types";

/** @deprecated — usePresetColors() 또는 useC() 사용 권장. 하위호환용 전역 상수. */
export const C: PresetColors = DEFAULT_PRESET.colors;

/** @deprecated — resolvePreset() 사용 */
export function resolveVideoTheme(name?: string, artStyle?: string): PresetColors {
  const { colors } = resolvePreset({ videoTheme: name, artStyle });
  return { ...colors, divider: colors.divider } as any;
}

/* ── 비디오 테마 컨텍스트 ── */

// 하위호환: VideoThemeProvider → DesignPresetProvider 브릿지
// 새 시스템이 적용되면 SimpleVideo에서 직접 DesignPresetProvider를 사용하므로
// 이 컴포넌트는 점진적으로 제거됨
export const VideoThemeProvider: React.FC<{
  theme: string;
  artStyle?: string;
  children: React.ReactNode;
}> = ({ children }) => <>{children}</>;

/** @deprecated — usePresetColors() 사용 권장 */
export const useC = (): PresetColors => usePresetColors();

export const ease = Easing.out(Easing.cubic);
export const ease8020 = Easing.bezier(0.8, 0, 0.2, 1);
export const clamp = {
  extrapolateLeft: "clamp" as const,
  extrapolateRight: "clamp" as const,
};

/** variant에 따른 borderRadius 계산 */
function variantRadius(variant: string, size: number): number {
  switch (variant) {
    case "circle": return size / 2;
    case "rounded-square": return size * 0.2;
    case "square": return 0;
    case "card": return 8;
    case "pill": return size;
    case "shield": return size * 0.15;
    case "diamond": return 0; // diamond uses transform
    default: return size / 2;
  }
}

/* ================================================================
   Animation Hooks — 기존 6개
   ================================================================ */

export function useFadeRise(delay: number, dur = 20, rise = 25) {
  const frame = useCurrentFrame();
  const f = frame - delay;
  const d = Math.max(dur, 1);
  return {
    opacity: interpolate(f, [0, d], [0, 1], { ...clamp, easing: ease }),
    transform: `translateY(${interpolate(f, [0, d], [rise, 0], { ...clamp, easing: ease })}px)`,
  };
}

export function useFadeSlide(delay: number, dur = 15, slide = 20) {
  const frame = useCurrentFrame();
  const f = frame - delay;
  const d = Math.max(dur, 1);
  return {
    opacity: interpolate(f, [0, d], [0, 1], { ...clamp, easing: ease }),
    transform: `translateX(${interpolate(f, [0, d], [slide, 0], { ...clamp, easing: ease })}px)`,
  };
}

export function useFade(delay: number, dur = 15, to = 1) {
  const frame = useCurrentFrame();
  const d = Math.max(dur, 1);
  return interpolate(frame, [delay, delay + d], [0, to], clamp);
}

export function useScale(delay: number, dur = 20) {
  const frame = useCurrentFrame();
  const f = frame - delay;
  const d = Math.max(dur, 1);
  return {
    opacity: interpolate(f, [0, d], [0, 1], { ...clamp, easing: ease }),
    transform: `scale(${interpolate(f, [0, d], [0.85, 1], { ...clamp, easing: ease })})`,
  };
}

export function useLineExpand(delay: number, dur = 25, target = 120) {
  const frame = useCurrentFrame();
  const d = Math.max(dur, 1);
  return interpolate(frame, [delay, delay + d], [0, target], {
    ...clamp,
    easing: ease,
  });
}

/** 카운팅 애니메이션: startFrom → target 숫자까지 증가 */
export function useCountUp(
  delay: number,
  dur = 35,
  target: number,
  startFrom = 1,
) {
  const frame = useCurrentFrame();
  const d = Math.max(dur, 1);
  if (frame >= delay + d) return target;
  if (frame <= delay) return startFrom;
  const value = interpolate(frame, [delay, delay + d], [startFrom, target], {
    ...clamp,
    easing: Easing.out(Easing.exp),
  });
  return Math.round(value);
}

/* ================================================================
   Animation Hooks — 신규 9개
   ================================================================ */

/** 오버슈트 스케일 등장 — 숫자/뱃지 주목 */
export function useOvershootScale(delay: number, dur = 20) {
  const frame = useCurrentFrame();
  const f = frame - delay;
  const d = Math.max(dur, 1);
  const overshoot = Easing.out(Easing.back(1.7));
  return {
    opacity: interpolate(f, [0, d * 0.4 || 1], [0, 1], { ...clamp, easing: ease }),
    transform: `scale(${interpolate(f, [0, d], [0.5, 1], { ...clamp, easing: overshoot })})`,
  };
}

/** 바운스 등장 — 성취/축하 */
export function useBounceIn(delay: number, dur = 25) {
  const frame = useCurrentFrame();
  const f = frame - delay;
  const d = Math.max(dur, 1);
  const bounce = Easing.out(Easing.bounce);
  return {
    opacity: interpolate(f, [0, d * 0.3 || 1], [0, 1], { ...clamp, easing: ease }),
    transform: `scale(${interpolate(f, [0, d], [0.3, 1], { ...clamp, easing: bounce })})`,
  };
}

/** 좌우 진동 — 경고/위험 */
export function useShake(delay: number, dur = 20, intensity = 6) {
  const frame = useCurrentFrame();
  const f = frame - delay;
  const d = Math.max(dur, 1);
  const opacity = interpolate(f, [0, 8], [0, 1], { ...clamp, easing: ease });
  const decay = interpolate(f, [0, d], [1, 0], clamp);
  const x = f > 0 ? Math.sin(f * 1.8) * intensity * decay : 0;
  return { opacity, transform: `translateX(${x}px)` };
}

/** 지속 펄스 — 주의 유지 */
export function usePulse(delay: number, period = 60) {
  const frame = useCurrentFrame();
  const f = frame - delay;
  const opacity = interpolate(f, [0, 10], [0, 1], { ...clamp, easing: ease });
  const scale = f > 0 ? 1 + Math.sin((f / period) * Math.PI * 2) * 0.05 : 1;
  return { opacity, transform: `scale(${scale})` };
}

/** 글리치 — 기술/해킹 */
export function useGlitch(delay: number, dur = 15) {
  const frame = useCurrentFrame();
  const f = frame - delay;
  const opacity = interpolate(f, [0, 5], [0, 1], { ...clamp, easing: ease });
  const active = f > 0 && f < dur;
  const x = active ? Math.sin(f * 3.7) * 3 : 0;
  const y = active ? Math.cos(f * 2.3) * 2 : 0;
  const hue = active ? Math.sin(f * 5) * 30 : 0;
  return {
    opacity,
    transform: `translate(${x}px, ${y}px)`,
    filter: active ? `hue-rotate(${hue}deg)` : "none",
  };
}

/** 타자기 효과 — 표시할 글자수 반환 */
export function useTypewriter(delay: number, length: number, speed = 0.5) {
  const frame = useCurrentFrame();
  const f = frame - delay;
  if (f <= 0) return 0;
  return Math.min(Math.floor(f * speed), length);
}

/** 퇴장 애니메이션 */
export function useFadeOut(startFrame: number, dur = 15) {
  const frame = useCurrentFrame();
  const f = frame - startFrame;
  return {
    opacity: interpolate(f, [0, dur], [1, 0], { ...clamp, easing: ease }),
    transform: `translateY(${interpolate(f, [0, dur], [0, -15], { ...clamp, easing: ease })}px)`,
  };
}

/** Remotion spring() 래퍼 — 0→1 spring 값 */
export function useSpringValue(delay: number, config?: { damping?: number; stiffness?: number }) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = frame - delay;
  if (f <= 0) return 0;
  return spring({
    frame: f,
    fps,
    config: { damping: config?.damping ?? 200, stiffness: config?.stiffness ?? 100 },
  });
}

/** 스태거 딜레이 계산 유틸 */
export function staggerDelay(index: number, gap = 8, base = 0) {
  return base + index * gap;
}

/* ================================================================
   순수 함수 애니메이션 유틸 — .map() 안이나 조건 블록에서 사용
   (useCurrentFrame 없이 frame을 직접 인자로 받음)
   ================================================================ */

export function fadeRise(frame: number, delay: number, dur = 20, rise = 25) {
  const f = frame - delay;
  const d = Math.max(dur, 1);
  return {
    opacity: interpolate(f, [0, d], [0, 1], { ...clamp, easing: ease }),
    transform: `translateY(${interpolate(f, [0, d], [rise, 0], { ...clamp, easing: ease })}px)`,
  };
}

export function fadeSlide(frame: number, delay: number, dur = 15, slide = 20) {
  const f = frame - delay;
  const d = Math.max(dur, 1);
  return {
    opacity: interpolate(f, [0, d], [0, 1], { ...clamp, easing: ease }),
    transform: `translateX(${interpolate(f, [0, d], [slide, 0], { ...clamp, easing: ease })}px)`,
  };
}

export function fadeVal(frame: number, delay: number, dur = 15, to = 1) {
  const d = Math.max(dur, 1);
  return interpolate(frame, [delay, delay + d], [0, to], clamp);
}

export function scaleAnim(frame: number, delay: number, dur = 20) {
  const f = frame - delay;
  const d = Math.max(dur, 1);
  return {
    opacity: interpolate(f, [0, d], [0, 1], { ...clamp, easing: ease }),
    transform: `scale(${interpolate(f, [0, d], [0.85, 1], { ...clamp, easing: ease })})`,
  };
}

/* ================================================================
   Accent Text Parser
   ================================================================ */

/**
 * {{text}} 마크업을 파싱하여 강조 텍스트를 액센트 컬러로 렌더링
 * 줄바꿈(\n)도 처리
 */
export const AccentText: React.FC<{
  text: string;
  baseColor?: string;
  style?: React.CSSProperties;
}> = ({ text, baseColor, style }) => {
  const C = useC();
  const resolvedBaseColor = baseColor ?? C.text;
  const lines = text.split("\n");
  return (
    <span style={style}>
      {lines.map((line, li) => (
        <React.Fragment key={li}>
          {li > 0 && <br />}
          {line.split(/(\{\{[^}]+\}\})/g).map((part, pi) => {
            if (part.startsWith("{{") && part.endsWith("}}")) {
              return (
                <span key={pi} style={{ color: C.accent }}>
                  {part.slice(2, -2)}
                </span>
              );
            }
            return (
              <span key={pi} style={{ color: resolvedBaseColor }}>
                {part}
              </span>
            );
          })}
        </React.Fragment>
      ))}
    </span>
  );
};

/** 텍스트 내 \n을 <br/>로 변환 — AccentText와 동일한 방식 */
export const TextWithBreaks: React.FC<{
  text: string;
  style?: React.CSSProperties;
}> = ({ text, style }) => {
  if (!text) return null;
  const parts = text.split("\n");
  if (parts.length === 1) return <span style={style}>{text}</span>;
  return (
    <span style={{ display: "inline-block", ...style }}>
      {parts.map((line, i) => (
        <React.Fragment key={i}>
          {i > 0 && <br />}
          {line}
        </React.Fragment>
      ))}
    </span>
  );
};

/* ================================================================
   UI Components — 기존 5개
   ================================================================ */

export const Card: React.FC<{
  children: React.ReactNode;
  style?: React.CSSProperties;
}> = ({ children, style }) => {
  const C = useC();
  const V = usePresetVariants();
  const cardStyles: Record<string, React.CSSProperties> = {
    bordered: { backgroundColor: C.cardBg, border: `1px solid ${C.cardBorder}` },
    filled: { backgroundColor: C.accentSoft, border: "none" },
    glass: { backgroundColor: "rgba(255,255,255,0.05)", border: `1px solid rgba(255,255,255,0.1)`, backdropFilter: "blur(10px)" },
    minimal: { backgroundColor: "transparent", border: "none", padding: "12px 0" },
  };
  const vs = cardStyles[V.card] || cardStyles.bordered;
  return (
    <div
      style={{
        backgroundColor: C.cardBg,
        border: `1px solid ${C.cardBorder}`,
        borderRadius: 12,
        padding: "24px 28px",
        ...vs,
        ...style,
      }}
    >
      {children}
    </div>
  );
};

export const Pill: React.FC<{
  text: string;
  active?: boolean;
  style?: React.CSSProperties;
}> = ({ text, active, style }) => {
  const C = useC();
  const V = usePresetVariants();
  const pillRadius = V.pill === "pill" ? 20 : V.pill === "square" ? 0 : 8;
  return (
    <div
      style={{
        padding: "8px 20px",
        borderRadius: pillRadius,
        border: `1px solid ${active ? C.accent : C.cardBorder}`,
        backgroundColor: active ? C.accentSoft : "transparent",
        fontSize: 20,
        fontWeight: 600,
        color: active ? C.accent : C.textMuted,
        ...style,
      }}
    >
      {text}
    </div>
  );
};

export const CircleBadge: React.FC<{
  text: string;
  size?: number;
  filled?: boolean;
  style?: React.CSSProperties;
}> = ({ text, size = 48, filled, style }) => {
  const C = useC();
  const V = usePresetVariants();
  const radius = variantRadius(V.circleBadge, size);
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: radius,
        border: `2px solid ${C.accent}`,
        backgroundColor: filled ? C.accent : "transparent",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: size * 0.4,
        fontWeight: 700,
        color: filled ? C.bg : C.accent,
        flexShrink: 0,
        ...style,
      }}
    >
      {text}
    </div>
  );
};

/** 이미지 원형 배지 — imageUrl이 있으면 이미지, 없으면 인물 실루엣 */
export const ImageBadge: React.FC<{
  imageUrl?: string;
  size?: number;
  style?: React.CSSProperties;
}> = ({ imageUrl, size = 56, style }) => {
  const C = useC();
  const V = usePresetVariants();
  const radius = variantRadius(V.imageBadge, size);
  const resolvedUrl = imageUrl
    ? imageUrl.startsWith("http")
      ? imageUrl
      : staticFile(imageUrl)
    : null;

  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: radius,
        border: `2px solid ${C.accentBorder}`,
        backgroundColor: C.accentBg,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        overflow: "hidden",
        flexShrink: 0,
        ...style,
      }}
    >
      {resolvedUrl ? (
        <img
          src={resolvedUrl}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      ) : (
        <svg
          width={size * 0.5}
          height={size * 0.5}
          viewBox="0 0 24 24"
          fill="none"
        >
          <circle cx="12" cy="8" r="4" fill="rgba(255,255,255,0.3)" />
          <path
            d="M4 21c0-4.4 3.6-8 8-8s8 3.6 8 8"
            fill="rgba(255,255,255,0.2)"
          />
        </svg>
      )}
    </div>
  );
};

/* ================================================================
   UI Components — 신규 8개
   ================================================================ */

/** Lucide 아이콘 래퍼 — 일관된 크기/색상 */
export const Icon: React.FC<{
  icon: LucideIcon;
  size?: number;
  color?: string;
  style?: React.CSSProperties;
}> = ({ icon: LucideComp, size = 24, color, style }) => {
  const C = useC();
  return <LucideComp size={size} color={color ?? C.accent} strokeWidth={1.5} style={style} />;
};

/** 아이콘 + 원형 배지 (CircleBadge의 아이콘 버전) */
export const IconBadge: React.FC<{
  icon: LucideIcon;
  size?: number;
  filled?: boolean;
  style?: React.CSSProperties;
}> = ({ icon: LucideComp, size = 48, filled, style }) => {
  const C = useC();
  const V = usePresetVariants();
  const radius = variantRadius(V.iconBadge, size);
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: radius,
        border: `2px solid ${C.accent}`,
        backgroundColor: filled ? C.accent : "transparent",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
        ...style,
      }}
    >
      <LucideComp
        size={size * 0.5}
        color={filled ? C.bg : C.accent}
        strokeWidth={1.5}
      />
    </div>
  );
};

/** 국기 원형 배지 (ISO alpha-2 코드) */
export const FlagBadge: React.FC<{
  countryCode: string;
  size?: number;
  style?: React.CSSProperties;
}> = ({ countryCode, size = 48, style }) => {
  const C = useC();
  const V = usePresetVariants();
  const isCard = V.flagBadge === "card";
  const radius = isCard ? 8 : variantRadius(V.flagBadge, size);
  const w = isCard ? size * 1.5 : size;
  const h = size;
  // country-flag-icons provides SVG URLs via the package
  let FlagUrl: string | null = null;
  try {
    // country-flag-icons/3x2/{CODE}.svg
    FlagUrl = `https://purecatamphetamine.github.io/country-flag-icons/3x2/${countryCode.toUpperCase()}.svg`;
  } catch {
    FlagUrl = null;
  }
  return (
    <div
      style={{
        width: w,
        height: h,
        borderRadius: radius,
        border: `2px solid ${C.accentBorder}`,
        backgroundColor: C.accentBg,
        overflow: "hidden",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
        ...style,
      }}
    >
      {FlagUrl ? (
        <img
          src={FlagUrl}
          style={{ width: isCard ? "100%" : "120%", height: isCard ? "100%" : "120%", objectFit: "cover" }}
        />
      ) : (
        <span style={{ fontSize: size * 0.4, color: C.textMuted }}>
          {countryCode.toUpperCase()}
        </span>
      )}
    </div>
  );
};

/** 국기 카드 — 직사각형 원본 비율, 국기가 주인공인 씬용 */
export const FlagCard: React.FC<{
  countryCode: string;
  label?: string;
  width?: number;
  style?: React.CSSProperties;
}> = ({ countryCode, label, width = 120, style }) => {
  const C = useC();
  const h = Math.round(width * 2 / 3); // 3:2 비율
  const FlagUrl = `https://purecatamphetamine.github.io/country-flag-icons/3x2/${countryCode.toUpperCase()}.svg`;
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10, flexShrink: 0, ...style }}>
      <div style={{
        width, height: h, borderRadius: 8, overflow: "hidden",
        border: `2px solid ${C.cardBorder}`,
        boxShadow: "0 2px 12px rgba(0,0,0,0.2)",
      }}>
        <img
          src={FlagUrl}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      </div>
      {label && (
        <span style={{ fontSize: 24, fontWeight: 600, color: C.text, textAlign: "center" }}>
          {label}
        </span>
      )}
    </div>
  );
};

/** 브랜드 로고 배지 (Simple Icons) */
export const LogoBadge: React.FC<{
  logo: string;
  size?: number;
  color?: string;
  style?: React.CSSProperties;
}> = ({ logo, size = 48, color, style }) => {
  const C = useC();
  const V = usePresetVariants();
  const radius = variantRadius(V.logoBadge, size);
  const LogoComp = resolveLogo(logo);
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: radius,
        border: `2px solid ${C.accentBorder}`,
        backgroundColor: C.accentBg,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
        ...style,
      }}
    >
      {LogoComp ? (
        <LogoComp size={size * 0.5} color={color ?? C.accent} />
      ) : (
        <span
          style={{
            fontSize: size * 0.35,
            fontWeight: 700,
            color: color ?? C.accent,
          }}
        >
          {logo.slice(0, 2).toUpperCase()}
        </span>
      )}
    </div>
  );
};

/** 수평 진행 바 */
export const ProgressBar: React.FC<{
  progress: number;
  height?: number;
  color?: string;
  label?: string;
  style?: React.CSSProperties;
}> = ({ progress, height = 16, color, label, style }) => {
  const C = useC();
  const V = usePresetVariants();
  const barRadius = V.progressBar === "flat" ? 0 : height / 2;
  const barHeight = V.progressBar === "thick" ? height * 1.5 : height;
  const resolvedColor = color ?? C.accent;
  return (
    <div style={{ width: "100%", ...style }}>
      {label && (
        <div
          style={{
            fontSize: 36,
            color: C.textMuted,
            marginBottom: 6,
            display: "flex",
            justifyContent: "space-between",
          }}
        >
          <span>{label}</span>
          <span style={{ color: C.accent }}>{Math.round(progress * 100)}%</span>
        </div>
      )}
      <div
        style={{
          width: "100%",
          height: barHeight,
          backgroundColor: C.divider,
          borderRadius: barRadius,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${Math.min(progress * 100, 100)}%`,
            height: "100%",
            backgroundColor: resolvedColor,
            borderRadius: barRadius,
          }}
        />
      </div>
    </div>
  );
};

/** 키워드 태그/칩 (Pill 개선) */
export const Tag: React.FC<{
  text: string;
  active?: boolean;
  size?: "sm" | "md" | "lg";
  style?: React.CSSProperties;
}> = ({ text, active, size = "md", style }) => {
  const C = useC();
  const V = usePresetVariants();
  const tagRadius = V.tag === "pill" ? 20 : V.tag === "square" ? 0 : 6;
  const sizes = { sm: { px: 18, py: 8, fs: 20 }, md: { px: 28, py: 12, fs: 26 }, lg: { px: 36, py: 16, fs: 36 } };
  const s = sizes[size];
  return (
    <span
      style={{
        padding: `${s.py}px ${s.px}px`,
        borderRadius: tagRadius,
        border: `1px solid ${active ? C.accent : C.cardBorder}`,
        backgroundColor: active ? C.accentSoft : C.cardBg,
        fontSize: s.fs,
        fontWeight: 600,
        color: active ? C.accent : C.textMuted,
        whiteSpace: "nowrap",
        ...style,
      }}
    >
      {text}
    </span>
  );
};

/** 구분선 */
export const Divider: React.FC<{
  width?: number | string;
  color?: string;
  thickness?: number;
  style?: React.CSSProperties;
}> = ({ width = "100%", color, thickness = 1, style }) => {
  const C = useC();
  const V = usePresetVariants();
  const resolvedColor = color ?? C.divider;
  const divStyle = V.divider === "dashed" ? "dashed" : V.divider === "dotted" ? "dotted" : "solid";
  const isGradient = V.divider === "gradient";
  return (
    <div
      style={{
        width,
        height: isGradient ? thickness : 0,
        flexShrink: 0,
        ...(isGradient
          ? { background: `linear-gradient(to right, transparent, ${resolvedColor}, transparent)` }
          : { borderTop: `${thickness}px ${divStyle} ${resolvedColor}` }),
        ...style,
      }}
    />
  );
};

/** 상태 표시 도트 */
export const StatusDot: React.FC<{
  status: "positive" | "negative" | "neutral" | "warning";
  label?: string;
  style?: React.CSSProperties;
}> = ({ status, label, style }) => {
  const C = useC();
  const V = usePresetVariants();
  const colors = {
    positive: C.positive,
    negative: C.negative,
    neutral: C.textDim,
    warning: C.warning,
  };
  const statusColor = colors[status];
  const isBadge = V.statusDot === "badge";
  const isIcon = V.statusDot === "icon";
  if (isBadge) {
    return (
      <div style={{ display: "flex", alignItems: "center", gap: 12, ...style }}>
        <span style={{
          padding: "2px 10px", borderRadius: 6, fontSize: 20, fontWeight: 700,
          backgroundColor: `${statusColor}22`, color: statusColor,
        }}>
          {status === "positive" ? "OK" : status === "negative" ? "NG" : status === "warning" ? "!" : "-"}
        </span>
        {label && <span style={{ fontSize: 36, color: C.textMuted }}>{label}</span>}
      </div>
    );
  }
  if (isIcon) {
    const icon = status === "positive" ? "\u2713" : status === "negative" ? "\u2717" : status === "warning" ? "!" : "\u2014";
    return (
      <div style={{ display: "flex", alignItems: "center", gap: 12, ...style }}>
        <span style={{ fontSize: 20, fontWeight: 700, color: statusColor, flexShrink: 0 }}>{icon}</span>
        {label && <span style={{ fontSize: 36, color: C.textMuted }}>{label}</span>}
      </div>
    );
  }
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, ...style }}>
      <div
        style={{
          width: 16,
          height: 16,
          borderRadius: 8,
          backgroundColor: statusColor,
          flexShrink: 0,
        }}
      />
      {label && (
        <span style={{ fontSize: 36, color: C.textMuted }}>{label}</span>
      )}
    </div>
  );
};

/* ================================================================
   UI Components — 확장 12개 (의도 기반 크리에이티브 컴포지션용)
   ================================================================ */

/** 노드 간 연결선/화살표 — 프로세스 흐름, 인과관계 */
export const Connector: React.FC<{
  direction?: "down" | "right" | "left";
  length?: number;
  arrow?: boolean;
  color?: string;
  style?: React.CSSProperties;
}> = ({ direction = "down", length = 40, arrow = true, color, style }) => {
  const C = useC();
  const V = usePresetVariants();
  const isDashed = V.connector === "dashed";
  const showArrow = V.connector !== "line";
  const resolvedColor = color ?? C.accent;
  const isVertical = direction === "down";
  const w = isVertical ? 3 : length;
  const h = isVertical ? length : 3;
  const arrowSize = 10;
  const lineStyle: React.CSSProperties = isDashed
    ? isVertical
      ? { width: 0, height: h, borderLeft: `3px dashed ${resolvedColor}`, flexShrink: 0 }
      : { width: w, height: 0, borderTop: `3px dashed ${resolvedColor}`, flexShrink: 0 }
    : { width: w, height: h, backgroundColor: resolvedColor, flexShrink: 0 };
  return (
    <div style={{ display: "flex", flexDirection: isVertical ? "column" : "row", alignItems: "center", overflow: "visible", ...style }}>
      <div style={lineStyle} />
      {arrow && showArrow && (
        <div style={{
          width: 0, height: 0, flexShrink: 0,
          borderLeft: isVertical ? `${arrowSize}px solid transparent` : `${arrowSize + 2}px solid ${resolvedColor}`,
          borderRight: isVertical ? `${arrowSize}px solid transparent` : "none",
          borderTop: isVertical ? `${arrowSize + 2}px solid ${resolvedColor}` : `${arrowSize}px solid transparent`,
          borderBottom: isVertical ? "none" : `${arrowSize}px solid transparent`,
          ...(direction === "left" ? { transform: "rotate(180deg)" } : {}),
        }} />
      )}
    </div>
  );
};

/** 타임라인 이벤트 마커 — 연대기, 역사 사건 */
export const TimelineDot: React.FC<{
  label: string;
  active?: boolean;
  size?: number;
  style?: React.CSSProperties;
}> = ({ label, active, size = 32, style }) => {
  const C = useC();
  const V = usePresetVariants();
  const dotRadius = V.timelineDot === "circle" ? size / 2 : V.timelineDot === "square" ? 2 : size / 2;
  const isDiamond = V.timelineDot === "diamond";
  const dotSize = isDiamond ? size * 0.7 : size;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 16, ...style }}>
      <div style={{
        width: dotSize, height: dotSize, borderRadius: dotRadius,
        backgroundColor: active ? C.accent : "transparent",
        border: `2px solid ${active ? C.accent : C.cardBorder}`,
        flexShrink: 0,
        ...(isDiamond ? { transform: "rotate(45deg)" } : {}),
      }} />
      <span style={{ fontSize: 28, fontWeight: active ? 700 : 400, color: active ? C.accent : C.text }}>
        {label}
      </span>
    </div>
  );
};

/** KPI 카드 — 라벨 + 큰 숫자 + 변화율 */
export const MetricCard: React.FC<{
  label: string;
  value: string;
  change?: string;
  trend?: "up" | "down" | "neutral";
  style?: React.CSSProperties;
}> = ({ label, value, change, trend, style }) => {
  const C = useC();
  const V = usePresetVariants();
  const metricStyles: Record<string, React.CSSProperties> = {
    bordered: { backgroundColor: "rgba(0,0,0,0.4)", border: `2px solid ${C.accent}BB` },
    filled: { backgroundColor: "rgba(0,0,0,0.4)", border: `2px solid ${C.accent}BB` },
    glass: { backgroundColor: "rgba(0,0,0,0.4)", border: `2px solid ${C.accent}BB`, backdropFilter: "blur(10px)" },
    minimal: { backgroundColor: "transparent", border: "none", padding: "12px 0" },
  };
  const ms = metricStyles[V.metricCard] || metricStyles.bordered;
  const trendColor = trend === "up" ? C.positive : trend === "down" ? C.negative : C.textMuted;
  const trendArrow = trend === "up" ? "↑" : trend === "down" ? "↓" : "";
  return (
    <div style={{
      backgroundColor: C.cardBg, border: `1px solid ${C.cardBorder}`,
      borderRadius: 12, padding: "24px 32px", minWidth: 180, textAlign: "center", ...ms, ...style,
    }}>
      <div style={{ fontSize: 40, color: C.textMuted, marginBottom: 10 }}><TextWithBreaks text={label} /></div>
      <div style={{ fontSize: 100, fontWeight: 800, color: C.accent, lineHeight: 1.05 }}><TextWithBreaks text={value} /></div>
      {change && (
        <div style={{ fontSize: 28, color: trendColor, marginTop: 10, fontWeight: 600 }}>
          {trendArrow} {change}
        </div>
      )}
    </div>
  );
};

/** 인라인 미니 차트 — 트렌드를 컴팩트하게 표시 */
export const Sparkline: React.FC<{
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  style?: React.CSSProperties;
}> = ({ data, width = 280, height = 72, color, style }) => {
  const C = useC();
  const V = usePresetVariants();
  const isArea = V.sparkline === "area";
  if (!data.length) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((v - min) / range) * height;
    return { x, y };
  });
  const points = pts.map(p => `${p.x},${p.y}`).join(" ");
  const resolvedColor = color ?? C.accent;
  const areaPoints = isArea
    ? `0,${height} ${points} ${width},${height}`
    : undefined;
  return (
    <svg width={width} height={height} style={style}>
      {isArea && areaPoints && (
        <polygon points={areaPoints} fill={`${resolvedColor}22`} />
      )}
      <polyline points={points} fill="none" stroke={resolvedColor} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
};

/** 말풍선/주석 박스 — 부연 설명, 인용 강조 */
export const Callout: React.FC<{
  children: React.ReactNode;
  variant?: "info" | "warning" | "accent";
  style?: React.CSSProperties;
}> = ({ children, variant = "accent", style }) => {
  const C = useC();
  const V = usePresetVariants();
  const borderColor = variant === "warning" ? C.negative : variant === "info" ? C.accent : C.accent;
  const calloutStyle: React.CSSProperties = V.callout === "full-border"
    ? { border: `2px solid ${borderColor}`, borderRadius: 8, paddingLeft: 24, paddingRight: 24, paddingTop: 16, paddingBottom: 16, borderLeft: undefined }
    : V.callout === "highlight"
    ? { backgroundColor: `${borderColor}22`, borderRadius: 8, padding: "16px 24px", borderLeft: "none" }
    : { borderLeft: `5px solid ${borderColor}`, paddingLeft: 24, paddingTop: 16, paddingBottom: 16, backgroundColor: `${borderColor}11`, borderRadius: "0 8px 8px 0" };
  return (
    <div style={{
      fontSize: 28, color: C.text, lineHeight: 1.5,
      ...calloutStyle,
      ...style,
    }}>
      {children}
    </div>
  );
};

/** 번호 스텝 배지 — 프로세스 단계 표시 */
export const StepBadge: React.FC<{
  step: number;
  label?: string;
  active?: boolean;
  size?: number;
  style?: React.CSSProperties;
}> = ({ step, label, active, size, style }) => {
  const C = useC();
  const V = usePresetVariants();
  const L = usePresetLayout();
  const T = usePresetTypo();
  const resolvedSize = size ?? L.stepBadgeSize;
  const radius = variantRadius(V.stepBadge, resolvedSize);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 16, ...style }}>
      <div style={{
        width: resolvedSize, height: resolvedSize, borderRadius: radius,
        backgroundColor: active ? C.accent : "transparent",
        border: `2px solid ${C.accent}`,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: resolvedSize * 0.45, fontWeight: 800,
        color: active ? C.bg : C.accent, flexShrink: 0,
      }}>
        {step}
      </div>
      {label && (
        <span style={{ fontSize: T.itemText, fontWeight: 600, color: active ? C.text : C.textMuted }}>
          {label}
        </span>
      )}
    </div>
  );
};

/** 비교 셀 — before/after, 변화 전후 대비 */
export const ComparisonCell: React.FC<{
  label: string;
  value: string;
  sublabel?: string;
  variant?: "before" | "after" | "neutral";
  size?: "md" | "lg";
  style?: React.CSSProperties;
}> = ({ label, value, sublabel, variant = "neutral", size = "md", style }) => {
  const C = useC();
  const V = usePresetVariants();
  const valueColor = variant === "after" ? C.positive : variant === "before" ? C.textMuted : C.accent;
  const isLg = size === "lg";
  const lgBg = "rgba(0,0,0,0.4)";
  const lgBorder = `2px solid ${valueColor}`;
  const cellStyle: React.CSSProperties = V.comparisonCell === "filled"
    ? { backgroundColor: isLg ? lgBg : C.accentSoft, border: isLg ? lgBorder : "none" }
    : V.comparisonCell === "accent-top"
    ? { backgroundColor: isLg ? lgBg : C.cardBg, border: isLg ? lgBorder : `1px solid ${C.cardBorder}`, ...(!isLg ? { borderTop: `3px solid ${valueColor}` } : {}) }
    : V.comparisonCell === "none"
    ? { backgroundColor: "transparent", border: "none" }
    : { backgroundColor: isLg ? lgBg : C.cardBg, border: isLg ? lgBorder : `1px solid ${C.cardBorder}` };
  return (
    <div style={{
      borderRadius: isLg ? 20 : 12,
      padding: isLg ? "28px 40px" : "16px 20px",
      textAlign: "center", ...cellStyle, ...style,
    }}>
      <div style={{ fontSize: isLg ? 36 : 24, color: C.textMuted, marginBottom: isLg ? 12 : 6 }}><TextWithBreaks text={label} /></div>
      <div style={{ fontSize: isLg ? 64 : 48, fontWeight: 700, color: valueColor, lineHeight: 1.2 }}><TextWithBreaks text={value} /></div>
      {sublabel && <div style={{ fontSize: isLg ? 120 : 48, fontWeight: 800, color: valueColor, lineHeight: 1.05, marginTop: isLg ? 8 : 4 }}><TextWithBreaks text={sublabel} /></div>}
    </div>
  );
};

/** 순위 배지 — 1st/2nd/3rd 색상 구분 */
export const RankBadge: React.FC<{
  rank: number;
  size?: number;
  style?: React.CSSProperties;
}> = ({ rank, size = 72, style }) => {
  const C = useC();
  const V = usePresetVariants();
  const radius = variantRadius(V.rankBadge, size);
  const isShield = V.rankBadge === "shield";
  const preset = useDesignPreset();
  const rankColors = preset.colors.rank;
  const colors: Record<number, string> = { 1: rankColors[0], 2: rankColors[1], 3: rankColors[2] };
  const bg = colors[rank] || C.accent;
  return (
    <div style={{
      width: size, height: size, borderRadius: radius,
      backgroundColor: bg, display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: size * 0.45, fontWeight: 800, color: "#0A0A0A", flexShrink: 0,
      ...(isShield ? { transform: "rotate(0deg)" } : {}),
      ...style,
    }}>
      {rank}
    </div>
  );
};

/** 독립 인용부호 장식 */
export const QuoteMark: React.FC<{
  size?: number;
  color?: string;
  style?: React.CSSProperties;
}> = ({ size = 64, color, style }) => {
  const C = useC();
  const V = usePresetVariants();
  if (V.quoteMark === "none") return null;
  const qSize = V.quoteMark === "small" ? (size || 64) * 0.5 : size || 64;
  return (
    <span style={{
      fontSize: qSize, fontWeight: 900, color: color ?? C.accent, opacity: 0.3, lineHeight: 0.8,
      fontFamily: "var(--font-mono, 'Georgia', serif)", userSelect: "none", ...style,
    }}>
      &ldquo;
    </span>
  );
};

/** 발광 도트 — 펄스 애니메이션으로 주의 환기, 라이브 표시 */
export const GlowDot: React.FC<{
  color?: string;
  size?: number;
  style?: React.CSSProperties;
}> = ({ color, size = 24, style }) => {
  const C = useC();
  const V = usePresetVariants();
  const resolvedColor = color ?? C.accent;
  const isGlow = V.glowDot === "glow";
  const isRing = V.glowDot === "ring";
  return (
    <div style={{
      width: size, height: size, borderRadius: size / 2,
      backgroundColor: isRing ? "transparent" : resolvedColor,
      ...(isRing
        ? { border: `2px solid ${resolvedColor}` }
        : isGlow || V.glowDot === undefined
          ? { boxShadow: `0 0 ${size}px ${size / 2}px ${resolvedColor}66` }
          : {}),
      flexShrink: 0, ...style,
    }} />
  );
};

/** 지시선 + 주석 — 차트/도표의 특정 부분 가리키기 */
export const AnnotationLine: React.FC<{
  text: string;
  width?: number;
  direction?: "left" | "right";
  color?: string;
  style?: React.CSSProperties;
}> = ({ text, width = 100, direction = "right", color, style }) => {
  const C = useC();
  const V = usePresetVariants();
  const isDashed = V.annotationLine === "dashed";
  const resolvedColor = color ?? C.accent;
  const lineStyle: React.CSSProperties = isDashed
    ? { width, height: 0, borderTop: `1px dashed ${resolvedColor}`, flexShrink: 0 }
    : { width, height: 1, backgroundColor: resolvedColor, flexShrink: 0 };
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 8,
      flexDirection: direction === "left" ? "row-reverse" : "row",
      ...style,
    }}>
      <div style={lineStyle} />
      <span style={{ fontSize: 36, color: resolvedColor, whiteSpace: "nowrap", fontWeight: 600 }}>{text}</span>
    </div>
  );
};

/** 인라인 소형 막대 — 카드 내 비교 수치 */
export const MiniBar: React.FC<{
  value: number;
  maxValue: number;
  label?: string;
  color?: string;
  height?: number;
  style?: React.CSSProperties;
}> = ({ value, maxValue, label, color, height = 12, style }) => {
  const C = useC();
  const V = usePresetVariants();
  const barRadius = V.miniBar === "flat" ? 0 : height / 2;
  const resolvedColor = color ?? C.accent;
  const pct = maxValue > 0 ? Math.min((value / maxValue) * 100, 100) : 0;
  return (
    <div style={{ width: "100%", ...style }}>
      {label && (
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 30, marginBottom: 4 }}>
          <span style={{ color: C.textMuted }}>{label}</span>
          <span style={{ color: resolvedColor }}>{value}</span>
        </div>
      )}
      <div style={{ width: "100%", height, backgroundColor: C.divider, borderRadius: barRadius, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", backgroundColor: resolvedColor, borderRadius: barRadius }} />
      </div>
    </div>
  );
};

/* ================================================================
   숫자 포맷팅 유틸
   ================================================================ */

/** 숫자 문자열에서 순수 숫자를 추출 (예: "$100" → 100, "2,000회" → 2000) */
export function extractNumber(s: string): number {
  const dateMarkers = (s.match(/[년월일]/g) || []).length;
  if (dateMarkers >= 2) return 0;
  if (/→|->|~/.test(s)) return 0;
  const cleaned = s.replace(/[^0-9.-]/g, "").replace(/,/g, "");
  return parseFloat(cleaned) || 0;
}

/** 숫자에 원래 형식 적용 (접두사, 접미사, 쉼표) */
export function formatWithTemplate(template: string, value: number): string {
  const prefixMatch = template.match(/^([^0-9]*)/);
  const prefix = prefixMatch ? prefixMatch[1] : "";
  const suffixMatch = template.match(/[0-9][^0-9]*$/);
  const suffix = suffixMatch
    ? suffixMatch[0].replace(/[0-9.,]/g, "")
    : "";
  const hasComma = template.includes(",");
  const formatted = hasComma ? value.toLocaleString() : String(value);
  return `${prefix}${formatted}${suffix}`;
}

/* ================================================================
   아이콘/로고 해석 유틸
   ================================================================ */

/** Lucide 아이콘 이름 → 컴포넌트 매핑 (design-system.md Section 2 기반) */
const ICON_MAP: Record<string, LucideIcon> = {
  // AI/기술
  Brain, Cpu, Code, Database, Terminal,
  // 성장/트렌드
  TrendingUp, Rocket, ArrowUpRight,
  // 보안/안전
  Shield, Lock, ShieldCheck,
  // 통신/소통
  MessageSquare, Mail, Globe,
  // 비즈니스
  DollarSign, BarChart3, Target,
  // 사람/조직
  Users, User, Building,
  // 시간
  Clock, Calendar, History,
  // 도구
  Wrench, Settings, Hammer,
  // 검색/탐구
  Search, Eye, Compass,
  // 성공/달성
  CheckCircle, Award, Star,
  // 경고/주의
  AlertTriangle, AlertCircle,
  // 학습/지식
  BookOpen, GraduationCap, Lightbulb,
  // 데이터
  HardDrive, Layers,
  // 연결/네트워크
  Network, Link, GitBranch,
  // 전쟁/군사
  Swords, Crosshair,
  // 왕관/권력
  Crown, Castle, Landmark,
  // 감정/에너지
  Heart, Zap, Flame, Bomb,
  // 위치
  Flag, Map, MapPin,
  // 운송
  Plane, Ship, Truck,
  // 미디어
  FileText, Newspaper, Mic, Camera, Video, Music,
  // 통신
  Phone, Wifi, Radio,
};

/** 문자열 → Lucide 아이콘 컴포넌트 */
export function resolveIcon(name?: string): LucideIcon | null {
  if (!name) return null;
  return ICON_MAP[name] ?? null;
}

/** 문자열 → Simple Icons 브랜드 로고 컴포넌트 */
export function resolveLogo(name?: string): React.ComponentType<any> | null {
  if (!name) return null;
  // Simple Icons uses "Si" prefix: "Nato" → "SiNato"
  const key = `Si${name.charAt(0).toUpperCase()}${name.slice(1)}`;
  const comp = (SimpleIcons as any)[key];
  return comp ?? null;
}
