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

/* ================================================================
   Design Tokens
   ================================================================ */

export const FONT = "'Pretendard', sans-serif";

export const C = {
  bg: "#0A0A0A",
  text: "#FFFFFF",
  textMuted: "#FFFFFF",
  textDim: "#FFFFFF",
  accent: "#F59E0B",
  accentBg: "rgba(245,158,11,0.08)",
  accentBorder: "rgba(245,158,11,0.3)",
  accentSoft: "rgba(245,158,11,0.15)",
  cardBg: "rgba(245,158,11,0.06)",
  cardBorder: "rgba(245,158,11,0.25)",
  divider: "rgba(255,255,255,0.08)",
} as const;

export const ease = Easing.out(Easing.cubic);
export const ease8020 = Easing.bezier(0.8, 0, 0.2, 1);
export const clamp = {
  extrapolateLeft: "clamp" as const,
  extrapolateRight: "clamp" as const,
};

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
}> = ({ text, baseColor = C.text, style }) => {
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
              <span key={pi} style={{ color: baseColor }}>
                {part}
              </span>
            );
          })}
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
}> = ({ children, style }) => (
  <div
    style={{
      backgroundColor: C.cardBg,
      border: `1px solid ${C.cardBorder}`,
      borderRadius: 12,
      padding: "24px 28px",
      ...style,
    }}
  >
    {children}
  </div>
);

export const Pill: React.FC<{
  text: string;
  active?: boolean;
  style?: React.CSSProperties;
}> = ({ text, active, style }) => (
  <div
    style={{
      padding: "8px 20px",
      borderRadius: 20,
      border: `1px solid ${active ? C.accent : C.cardBorder}`,
      backgroundColor: active ? C.accentSoft : "transparent",
      fontSize: 18,
      fontWeight: 600,
      color: active ? C.accent : C.textMuted,
      ...style,
    }}
  >
    {text}
  </div>
);

export const CircleBadge: React.FC<{
  text: string;
  size?: number;
  filled?: boolean;
  style?: React.CSSProperties;
}> = ({ text, size = 48, filled, style }) => (
  <div
    style={{
      width: size,
      height: size,
      borderRadius: size / 2,
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

/** 이미지 원형 배지 — imageUrl이 있으면 이미지, 없으면 인물 실루엣 */
export const ImageBadge: React.FC<{
  imageUrl?: string;
  size?: number;
  style?: React.CSSProperties;
}> = ({ imageUrl, size = 56, style }) => {
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
        borderRadius: size / 2,
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
}> = ({ icon: LucideComp, size = 24, color = C.accent, style }) => (
  <LucideComp size={size} color={color} strokeWidth={1.5} style={style} />
);

/** 아이콘 + 원형 배지 (CircleBadge의 아이콘 버전) */
export const IconBadge: React.FC<{
  icon: LucideIcon;
  size?: number;
  filled?: boolean;
  style?: React.CSSProperties;
}> = ({ icon: LucideComp, size = 48, filled, style }) => (
  <div
    style={{
      width: size,
      height: size,
      borderRadius: size / 2,
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

/** 국기 원형 배지 (ISO alpha-2 코드) */
export const FlagBadge: React.FC<{
  countryCode: string;
  size?: number;
  style?: React.CSSProperties;
}> = ({ countryCode, size = 48, style }) => {
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
        width: size,
        height: size,
        borderRadius: size / 2,
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
          style={{ width: "120%", height: "120%", objectFit: "cover" }}
        />
      ) : (
        <span style={{ fontSize: size * 0.4, color: C.textMuted }}>
          {countryCode.toUpperCase()}
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
}> = ({ logo, size = 48, color = C.accent, style }) => {
  const LogoComp = resolveLogo(logo);
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: size / 2,
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
        <LogoComp size={size * 0.5} color={color} />
      ) : (
        <span
          style={{
            fontSize: size * 0.35,
            fontWeight: 700,
            color: C.accent,
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
}> = ({ progress, height = 8, color = C.accent, label, style }) => (
  <div style={{ width: "100%", ...style }}>
    {label && (
      <div
        style={{
          fontSize: 14,
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
        height,
        backgroundColor: C.divider,
        borderRadius: height / 2,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          width: `${Math.min(progress * 100, 100)}%`,
          height: "100%",
          backgroundColor: color,
          borderRadius: height / 2,
        }}
      />
    </div>
  </div>
);

/** 키워드 태그/칩 (Pill 개선) */
export const Tag: React.FC<{
  text: string;
  active?: boolean;
  size?: "sm" | "md" | "lg";
  style?: React.CSSProperties;
}> = ({ text, active, size = "md", style }) => {
  const sizes = { sm: { px: 10, py: 4, fs: 13 }, md: { px: 16, py: 6, fs: 15 }, lg: { px: 20, py: 8, fs: 18 } };
  const s = sizes[size];
  return (
    <span
      style={{
        padding: `${s.py}px ${s.px}px`,
        borderRadius: 6,
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
}> = ({ width = "100%", color = C.divider, thickness = 1, style }) => (
  <div
    style={{
      width,
      height: thickness,
      backgroundColor: color,
      flexShrink: 0,
      ...style,
    }}
  />
);

/** 상태 표시 도트 */
export const StatusDot: React.FC<{
  status: "positive" | "negative" | "neutral" | "warning";
  label?: string;
  style?: React.CSSProperties;
}> = ({ status, label, style }) => {
  const colors = {
    positive: "#22C55E",
    negative: "#EF4444",
    neutral: "rgba(255,255,255,0.4)",
    warning: "#F59E0B",
  };
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, ...style }}>
      <div
        style={{
          width: 8,
          height: 8,
          borderRadius: 4,
          backgroundColor: colors[status],
          flexShrink: 0,
        }}
      />
      {label && (
        <span style={{ fontSize: 15, color: C.textMuted }}>{label}</span>
      )}
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
