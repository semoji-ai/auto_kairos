/**
 * SvgMotionTest — SVG 모션 그래픽 테스트 컴포지션
 *
 * 3가지 효과를 시연:
 * 1. Decorative Overlay — 반투명 기하학 도형이 떠다니는 배경
 * 2. Line Drawing — evolvePath()로 선이 그려지는 애니메이션
 * 3. Emphasis Motion — 숫자/텍스트 주변 반짝이는 효과
 */
import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Easing,
  spring,
  Sequence,
} from "remotion";
import { evolvePath } from "@remotion/paths";
import { makeCircle, makeRect, makeTriangle } from "@remotion/shapes";

const ACCENT = "#F59E0B";
const BG = "#0A0A0A";
const TEXT = "#FFFFFF";
const FONT = "'Pretendard', sans-serif";

const ease = Easing.out(Easing.cubic);
const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

/* ================================================================
   Section 1: Decorative Overlay — 떠다니는 기하학 도형
   ================================================================ */

interface FloatingShape {
  type: "circle" | "triangle" | "rect" | "ring" | "line";
  x: number;
  y: number;
  size: number;
  rotation: number;
  speed: number;
  delay: number;
  opacity: number;
}

const SHAPES: FloatingShape[] = [
  { type: "circle", x: 150, y: 200, size: 40, rotation: 0, speed: 0.3, delay: 0, opacity: 0.15 },
  { type: "triangle", x: 1700, y: 150, size: 50, rotation: 15, speed: 0.5, delay: 5, opacity: 0.12 },
  { type: "rect", x: 300, y: 800, size: 35, rotation: 45, speed: 0.4, delay: 10, opacity: 0.1 },
  { type: "ring", x: 1600, y: 700, size: 60, rotation: 0, speed: 0.25, delay: 3, opacity: 0.12 },
  { type: "line", x: 900, y: 100, size: 80, rotation: -20, speed: 0.6, delay: 8, opacity: 0.15 },
  { type: "circle", x: 1200, y: 850, size: 25, rotation: 0, speed: 0.35, delay: 15, opacity: 0.1 },
  { type: "triangle", x: 500, y: 150, size: 30, rotation: 60, speed: 0.45, delay: 12, opacity: 0.08 },
  { type: "rect", x: 1400, y: 400, size: 20, rotation: 30, speed: 0.55, delay: 7, opacity: 0.1 },
  { type: "ring", x: 200, y: 600, size: 45, rotation: 0, speed: 0.3, delay: 20, opacity: 0.12 },
  { type: "line", x: 1750, y: 500, size: 60, rotation: 70, speed: 0.4, delay: 2, opacity: 0.1 },
];

const FloatingShapeElement: React.FC<{ shape: FloatingShape }> = ({ shape }) => {
  const frame = useCurrentFrame();
  const f = frame - shape.delay;

  const fadeIn = interpolate(f, [0, 20], [0, shape.opacity], clamp);
  const yOffset = Math.sin((f * shape.speed * Math.PI) / 60) * 20;
  const xOffset = Math.cos((f * shape.speed * Math.PI) / 90) * 10;
  const rot = shape.rotation + f * shape.speed * 0.5;

  const renderShape = () => {
    switch (shape.type) {
      case "circle": {
        const { path } = makeCircle({ radius: shape.size / 2 });
        return <path d={path} fill={ACCENT} />;
      }
      case "triangle": {
        const { path } = makeTriangle({ length: shape.size, direction: "up" });
        return <path d={path} fill="none" stroke={ACCENT} strokeWidth={2} />;
      }
      case "rect": {
        const { path } = makeRect({ width: shape.size, height: shape.size });
        return <path d={path} fill="none" stroke={ACCENT} strokeWidth={1.5} />;
      }
      case "ring": {
        const { path: outer } = makeCircle({ radius: shape.size / 2 });
        const { path: inner } = makeCircle({ radius: shape.size / 2 - 3 });
        return (
          <>
            <path d={outer} fill="none" stroke={ACCENT} strokeWidth={2} />
            <path d={inner} fill="none" stroke={ACCENT} strokeWidth={1} opacity={0.5} />
          </>
        );
      }
      case "line":
        return (
          <line
            x1={0} y1={0}
            x2={shape.size} y2={0}
            stroke={ACCENT}
            strokeWidth={2}
            strokeLinecap="round"
          />
        );
    }
  };

  return (
    <svg
      style={{
        position: "absolute",
        left: shape.x + xOffset,
        top: shape.y + yOffset,
        opacity: fadeIn,
        overflow: "visible",
      }}
      width={shape.size + 10}
      height={shape.size + 10}
      viewBox={`-5 -5 ${shape.size + 10} ${shape.size + 10}`}
    >
      <g transform={`rotate(${rot} ${shape.size / 2} ${shape.size / 2})`}>
        {renderShape()}
      </g>
    </svg>
  );
};

const DecorativeOverlay: React.FC = () => (
  <AbsoluteFill style={{ pointerEvents: "none" }}>
    {SHAPES.map((s, i) => (
      <FloatingShapeElement key={i} shape={s} />
    ))}
  </AbsoluteFill>
);

/* ================================================================
   Section 2: Line Drawing Animation — evolvePath
   ================================================================ */

const LineDrawingDemo: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // 헤드라인 밑줄 path
  const underlinePath = "M 0,0 C 100,20 300,-15 500,0 C 600,8 700,2 800,0";

  // 장식 곡선
  const decorCurve = "M 0,0 Q 150,-80 300,0 T 600,0 T 900,0";

  // 원형 path
  const { path: circlePath } = makeCircle({ radius: 60 });

  // 삼각형 path
  const { path: triPath } = makeTriangle({ length: 100, direction: "up" });

  // 진행도 (0 → 1)
  const progress1 = interpolate(frame, [0, 40], [0, 1], clamp);
  const progress2 = interpolate(frame, [15, 55], [0, 1], clamp);
  const progress3 = interpolate(frame, [30, 60], [0, 1], clamp);
  const progress4 = interpolate(frame, [10, 50], [0, 1], clamp);

  const underlineEv = evolvePath(progress1, underlinePath);
  const decorEv = evolvePath(progress2, decorCurve);
  const circleEv = evolvePath(progress3, circlePath);
  const triEv = evolvePath(progress4, triPath);

  const textOpacity = interpolate(frame, [5, 20], [0, 1], clamp);
  const labelOpacity = interpolate(frame, [45, 60], [0, 1], clamp);

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      {/* 헤드라인 + 밑줄 */}
      <div style={{ position: "relative", marginBottom: 80 }}>
        <div
          style={{
            fontFamily: FONT,
            fontSize: 72,
            fontWeight: 800,
            color: TEXT,
            opacity: textOpacity,
          }}
        >
          Line Drawing Animation
        </div>
        <svg
          width={800}
          height={30}
          viewBox="0 -15 800 30"
          style={{ position: "absolute", bottom: -15, left: "50%", transform: "translateX(-50%)" }}
        >
          <path
            d={underlinePath}
            fill="none"
            stroke={ACCENT}
            strokeWidth={4}
            strokeLinecap="round"
            strokeDasharray={underlineEv.strokeDasharray}
            strokeDashoffset={underlineEv.strokeDashoffset}
          />
        </svg>
      </div>

      {/* 도형 line-draw 데모 */}
      <div style={{ display: "flex", gap: 120, alignItems: "center" }}>
        {/* 원 */}
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 20 }}>
          <svg width={140} height={140} viewBox="-70 -70 140 140">
            <path
              d={circlePath}
              fill="none"
              stroke={ACCENT}
              strokeWidth={3}
              strokeLinecap="round"
              strokeDasharray={circleEv.strokeDasharray}
              strokeDashoffset={circleEv.strokeDashoffset}
              transform="translate(-60,-60)"
            />
          </svg>
          <span style={{ fontFamily: FONT, fontSize: 28, color: TEXT, opacity: labelOpacity }}>
            Circle
          </span>
        </div>

        {/* 삼각형 */}
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 20 }}>
          <svg width={140} height={140} viewBox="-20 -20 140 140">
            <path
              d={triPath}
              fill="none"
              stroke={ACCENT}
              strokeWidth={3}
              strokeLinecap="round"
              strokeDasharray={triEv.strokeDasharray}
              strokeDashoffset={triEv.strokeDashoffset}
            />
          </svg>
          <span style={{ fontFamily: FONT, fontSize: 28, color: TEXT, opacity: labelOpacity }}>
            Triangle
          </span>
        </div>

        {/* 장식 곡선 */}
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 20 }}>
          <svg width={200} height={100} viewBox="-10 -90 920 180">
            <path
              d={decorCurve}
              fill="none"
              stroke={ACCENT}
              strokeWidth={3}
              strokeLinecap="round"
              strokeDasharray={decorEv.strokeDasharray}
              strokeDashoffset={decorEv.strokeDashoffset}
            />
          </svg>
          <span style={{ fontFamily: FONT, fontSize: 28, color: TEXT, opacity: labelOpacity }}>
            Wave Curve
          </span>
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* ================================================================
   Section 3: Emphasis Motion — 반짝이/하이라이트 효과
   ================================================================ */

/** 반짝이 파티클 */
const Sparkle: React.FC<{
  cx: number;
  cy: number;
  delay: number;
  size?: number;
}> = ({ cx, cy, delay, size = 8 }) => {
  const frame = useCurrentFrame();
  const f = frame - delay;

  const scale = interpolate(f, [0, 8, 16], [0, 1.2, 0], clamp);
  const opacity = interpolate(f, [0, 6, 16], [0, 1, 0], clamp);
  const rotation = interpolate(f, [0, 16], [0, 45], clamp);

  return (
    <g transform={`translate(${cx}, ${cy}) rotate(${rotation}) scale(${scale})`} opacity={opacity}>
      {/* 4-point star */}
      <path
        d={`M 0,${-size} L ${size * 0.3},${-size * 0.3} L ${size},0 L ${size * 0.3},${size * 0.3} L 0,${size} L ${-size * 0.3},${size * 0.3} L ${-size},0 L ${-size * 0.3},${-size * 0.3} Z`}
        fill={ACCENT}
      />
    </g>
  );
};

/** 확장 원형 pulse */
const PulseRing: React.FC<{
  cx: number;
  cy: number;
  delay: number;
  radius?: number;
}> = ({ cx, cy, delay, radius = 50 }) => {
  const frame = useCurrentFrame();
  const f = frame - delay;

  const scale = interpolate(f, [0, 25], [0.3, 1.5], clamp);
  const opacity = interpolate(f, [0, 10, 25], [0, 0.6, 0], clamp);

  return (
    <circle
      cx={cx}
      cy={cy}
      r={radius * scale}
      fill="none"
      stroke={ACCENT}
      strokeWidth={2}
      opacity={opacity}
    />
  );
};

const EmphasisDemo: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // 숫자 카운트업
  const number = Math.round(interpolate(frame, [10, 50], [0, 2847], clamp));
  const numberScale = spring({ frame: frame - 8, fps, config: { damping: 12, stiffness: 100 } });
  const numberOpacity = interpolate(frame, [8, 18], [0, 1], clamp);

  // 텍스트 fade
  const labelOpacity = interpolate(frame, [0, 15], [0, 1], clamp);
  const subOpacity = interpolate(frame, [50, 60], [0, 1], clamp);

  // 밑줄 (line draw)
  const ulPath = "M 0,0 Q 80,8 160,0 Q 240,-8 320,0";
  const ulProgress = interpolate(frame, [55, 75], [0, 1], clamp);
  const ulEv = evolvePath(ulProgress, ulPath);

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      {/* 큰 숫자 */}
      <div style={{ position: "relative" }}>
        <div
          style={{
            fontFamily: FONT,
            fontSize: 200,
            fontWeight: 900,
            color: TEXT,
            opacity: numberOpacity,
            transform: `scale(${numberScale})`,
            letterSpacing: -4,
          }}
        >
          {number.toLocaleString()}
        </div>

        {/* 반짝이 효과 — 숫자 주변 */}
        <svg
          style={{ position: "absolute", inset: -80, overflow: "visible", pointerEvents: "none" }}
          viewBox="-80 -80 760 360"
        >
          <Sparkle cx={-40} cy={30} delay={20} size={12} />
          <Sparkle cx={650} cy={-20} delay={25} size={10} />
          <Sparkle cx={700} cy={150} delay={22} size={14} />
          <Sparkle cx={-60} cy={180} delay={28} size={9} />
          <Sparkle cx={300} cy={-50} delay={30} size={11} />
          <Sparkle cx={500} cy={220} delay={26} size={13} />

          {/* Pulse rings */}
          <PulseRing cx={300} cy={100} delay={15} radius={180} />
          <PulseRing cx={300} cy={100} delay={25} radius={150} />
          <PulseRing cx={300} cy={100} delay={35} radius={120} />
        </svg>
      </div>

      {/* 라벨 */}
      <div
        style={{
          fontFamily: FONT,
          fontSize: 36,
          fontWeight: 600,
          color: ACCENT,
          opacity: labelOpacity,
          marginTop: -20,
          letterSpacing: 4,
        }}
      >
        ACTIVE USERS
      </div>

      {/* 서브텍스트 + 밑줄 */}
      <div style={{ position: "relative", marginTop: 40 }}>
        <div
          style={{
            fontFamily: FONT,
            fontSize: 32,
            color: `${TEXT}99`,
            opacity: subOpacity,
          }}
        >
          Growth rate is accelerating
        </div>
        <svg
          width={320}
          height={20}
          viewBox="0 -10 320 20"
          style={{ position: "absolute", bottom: -10, left: "50%", transform: "translateX(-50%)" }}
        >
          <path
            d={ulPath}
            fill="none"
            stroke={ACCENT}
            strokeWidth={3}
            strokeLinecap="round"
            strokeDasharray={ulEv.strokeDasharray}
            strokeDashoffset={ulEv.strokeDashoffset}
          />
        </svg>
      </div>
    </AbsoluteFill>
  );
};

/* ================================================================
   Section Label — 섹션 타이틀 카드
   ================================================================ */

const SectionTitle: React.FC<{ title: string; subtitle: string }> = ({ title, subtitle }) => {
  const frame = useCurrentFrame();
  const titleOpacity = interpolate(frame, [0, 15], [0, 1], clamp);
  const titleY = interpolate(frame, [0, 15], [30, 0], { ...clamp, easing: ease });
  const subOpacity = interpolate(frame, [10, 25], [0, 1], clamp);
  const lineWidth = interpolate(frame, [5, 30], [0, 200], { ...clamp, easing: ease });

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <div
        style={{
          fontFamily: FONT,
          fontSize: 64,
          fontWeight: 800,
          color: ACCENT,
          opacity: titleOpacity,
          transform: `translateY(${titleY}px)`,
        }}
      >
        {title}
      </div>
      <div
        style={{
          width: lineWidth,
          height: 3,
          background: ACCENT,
          marginTop: 20,
          marginBottom: 20,
          borderRadius: 2,
        }}
      />
      <div
        style={{
          fontFamily: FONT,
          fontSize: 32,
          color: `${TEXT}88`,
          opacity: subOpacity,
        }}
      >
        {subtitle}
      </div>
    </AbsoluteFill>
  );
};

/* ================================================================
   Main Composition — 3 섹션을 시퀀스로 구성
   ================================================================ */

export const SvgMotionTest: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: BG }}>
      {/* 항상 떠다니는 장식 도형 (전체 재생 시간) */}
      <DecorativeOverlay />

      {/* Section 1: 타이틀 (0~2s) */}
      <Sequence from={0} durationInFrames={60}>
        <SectionTitle
          title="SVG Motion Graphics"
          subtitle="@remotion/paths + @remotion/shapes"
        />
      </Sequence>

      {/* Section 2: Line Drawing (2~5s) */}
      <Sequence from={60} durationInFrames={90}>
        <LineDrawingDemo />
      </Sequence>

      {/* Section 3: Emphasis / Sparkle (5~8s) */}
      <Sequence from={150} durationInFrames={90}>
        <EmphasisDemo />
      </Sequence>

      {/* Section 4: Ending label (8~10s) */}
      <Sequence from={240} durationInFrames={60}>
        <SectionTitle
          title="Ready to Integrate"
          subtitle="기존 컴포지션에 레이어로 추가 가능"
        />
      </Sequence>
    </AbsoluteFill>
  );
};
