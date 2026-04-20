/**
 * MotionShowcase — 기존 CreativeScene에 없는 표현들 레퍼런스
 *
 * Scene 1: Kinetic Typography  — 단어별 타격감 있는 등장
 * Scene 2: 3D Space Cards      — CSS perspective 3D 공간
 * Scene 3: SVG Path Draw       — 선이 실시간으로 그려지는 느낌
 * Scene 4: Vector Face Story   — 인라인 SVG 캐릭터가 데이터에 반응
 */
import React from "react";
import {
  AbsoluteFill,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Easing,
} from "remotion";

/* ===== helpers ===================================================== */
const clamp = (v: number, lo: number, hi: number) =>
  Math.max(lo, Math.min(hi, v));

function useSpring(
  frame: number,
  fps: number,
  opts: { from: number; to: number; damping?: number; stiffness?: number; mass?: number }
) {
  return spring({
    frame,
    fps,
    config: {
      damping: opts.damping ?? 14,
      stiffness: opts.stiffness ?? 200,
      mass: opts.mass ?? 0.6,
    },
    from: opts.from,
    to: opts.to,
  });
}

const FONT = "'Noto Sans KR', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif";
const AMBER = "#F59E0B";
const WHITE = "#FFFFFF";
const DIM = "#71717A";
const BG_DARK = "#0A0A0A";
const BG_CARD = "#1A1A1A";

/* ===================================================================
   Scene 1 — KINETIC TYPOGRAPHY
   단어가 한 번에 하나씩 화면을 꽉 채우며 타격감 있게 등장.
   마지막엔 전체 문장이 남는다.
   =================================================================== */
const KINETIC_WORDS = [
  { text: "진실은", color: WHITE, size: 160 },
  { text: "숫자가", color: AMBER, size: 180 },
  { text: "말한다", color: WHITE, size: 160 },
];

const KineticTypoScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const PER = 52; // frames per word (1.73s at 30fps)
  const HOLD = 48; // final word hold frames

  const phase = Math.floor(frame / PER);
  const localF = frame % PER;

  // Full sentence reveal after all words shown
  const sentenceStart = KINETIC_WORDS.length * PER;
  const sentenceProgress = clamp((frame - sentenceStart) / 20, 0, 1);
  const showSentence = frame >= sentenceStart;

  return (
    <AbsoluteFill
      style={{
        background: BG_DARK,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        overflow: "hidden",
      }}
    >
      {/* 플래시 효과 */}
      {KINETIC_WORDS.map((w, i) => {
        const wordStart = i * PER;
        const flash = interpolate(frame - wordStart, [0, 3, 8], [0.25, 0, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        return (
          <AbsoluteFill
            key={`flash-${i}`}
            style={{ background: `rgba(255,255,255,${flash})`, pointerEvents: "none" }}
          />
        );
      })}

      {/* 단어별 단독 표시 */}
      {!showSentence &&
        KINETIC_WORDS.map((w, i) => {
          if (i !== phase) return null;
          const sc = useSpring(localF, fps, {
            from: 2.8,
            to: 1,
            damping: 7,
            stiffness: 350,
            mass: 0.5,
          });
          const opa = interpolate(localF, [0, 6], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          const yShift = interpolate(localF, [0, 8], [60, 0], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.out(Easing.cubic),
          });
          return (
            <div
              key={i}
              style={{
                position: "absolute",
                fontSize: w.size,
                fontWeight: 900,
                fontFamily: FONT,
                color: w.color,
                transform: `scale(${sc}) translateY(${yShift}px)`,
                opacity: opa,
                letterSpacing: "-0.03em",
                textShadow: `0 0 60px ${w.color}66, 0 0 120px ${w.color}33`,
                whiteSpace: "nowrap",
              }}
            >
              {w.text}
            </div>
          );
        })}

      {/* 문장 전체 */}
      {showSentence && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 4,
            opacity: sentenceProgress,
            transform: `scale(${0.4 + sentenceProgress * 0.6})`,
          }}
        >
          {KINETIC_WORDS.map((w, i) => (
            <div
              key={i}
              style={{
                fontSize: 88,
                fontWeight: 900,
                fontFamily: FONT,
                color: w.color,
                letterSpacing: "-0.03em",
                lineHeight: 1.1,
                textAlign: "center",
              }}
            >
              {w.text}
            </div>
          ))}
          <div
            style={{
              marginTop: 24,
              width: 80,
              height: 4,
              background: AMBER,
              borderRadius: 2,
              opacity: sentenceProgress,
            }}
          />
        </div>
      )}

      {/* 장면 라벨 */}
      <div
        style={{
          position: "absolute",
          bottom: 40,
          right: 50,
          fontSize: 18,
          color: DIM,
          fontFamily: FONT,
          letterSpacing: "0.1em",
          textTransform: "uppercase",
        }}
      >
        01 · Kinetic Typography
      </div>
    </AbsoluteFill>
  );
};

/* ===================================================================
   Scene 2 — 3D SPACE CARDS
   3개의 카드가 원근감 있는 3D 공간에서 회전하며 떠 있다.
   =================================================================== */
interface Card3DData {
  label: string;
  value: string;
  sub: string;
  color: string;
}

const CARDS_3D: Card3DData[] = [
  { label: "ChatGPT 월간 사용자", value: "1.8억", sub: "출시 40일 만에 달성", color: "#F59E0B" },
  { label: "글로벌 AI 투자", value: "$91B", sub: "2023년 기준", color: "#3B82F6" },
  { label: "AI 대체 위험 직군", value: "3억", sub: "전 세계 일자리 수", color: "#EF4444" },
];

const Card3DScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const totalRotation = interpolate(frame, [0, 180], [0, 360], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });

  const globalScale = useSpring(frame, fps, { from: 0.3, to: 1, damping: 20, stiffness: 120 });
  const globalOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: "radial-gradient(ellipse 80% 60% at 50% 40%, #0d0d1a 0%, #0A0A0A 70%)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        overflow: "hidden",
        opacity: globalOpacity,
      }}
    >
      {/* 그리드 바닥 (원근감) */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: 300,
          background:
            "repeating-linear-gradient(90deg, rgba(59,130,246,0.08) 0px, rgba(59,130,246,0.08) 1px, transparent 1px, transparent 80px), " +
            "repeating-linear-gradient(0deg, rgba(59,130,246,0.08) 0px, rgba(59,130,246,0.08) 1px, transparent 1px, transparent 80px)",
          transform: "perspective(600px) rotateX(65deg) scaleX(3)",
          transformOrigin: "bottom center",
          opacity: 0.6,
        }}
      />

      {/* 3D 카드 컨테이너 */}
      <div
        style={{
          position: "relative",
          width: 900,
          height: 400,
          transform: `scale(${globalScale})`,
          perspective: 1200,
        }}
      >
        {CARDS_3D.map((card, i) => {
          const baseAngle = (i / CARDS_3D.length) * 360;
          const angle = ((baseAngle + totalRotation) % 360) * (Math.PI / 180);
          const RADIUS = 320;
          const x = Math.sin(angle) * RADIUS;
          const z = Math.cos(angle) * RADIUS;

          // 앞에 있을수록 크고 밝음
          const depthFactor = (z + RADIUS) / (2 * RADIUS); // 0~1
          const cardScale = 0.65 + depthFactor * 0.5;
          const cardOpacity = 0.3 + depthFactor * 0.7;
          const zIndex = Math.round(depthFactor * 100);

          // 카드 입장 타이밍
          const entryDelay = i * 15;
          const entryScale = useSpring(frame - entryDelay, fps, {
            from: 0,
            to: 1,
            damping: 18,
            stiffness: 150,
          });

          return (
            <div
              key={i}
              style={{
                position: "absolute",
                left: "50%",
                top: "50%",
                width: 260,
                height: 160,
                marginLeft: -130,
                marginTop: -80,
                transform: `translateX(${x}px) scale(${cardScale * entryScale})`,
                opacity: cardOpacity,
                zIndex,
                background: BG_CARD,
                border: `1px solid ${card.color}44`,
                borderRadius: 16,
                padding: "20px 24px",
                boxShadow: `0 0 40px ${card.color}22, 0 0 80px ${card.color}11`,
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
              }}
            >
              <div
                style={{
                  fontSize: 13,
                  color: card.color,
                  fontFamily: FONT,
                  fontWeight: 600,
                  letterSpacing: "0.05em",
                  textTransform: "uppercase",
                }}
              >
                {card.label}
              </div>
              <div
                style={{
                  fontSize: 52,
                  fontWeight: 900,
                  fontFamily: FONT,
                  color: WHITE,
                  lineHeight: 1,
                }}
              >
                {card.value}
              </div>
              <div style={{ fontSize: 13, color: DIM, fontFamily: FONT }}>
                {card.sub}
              </div>
              <div
                style={{
                  position: "absolute",
                  bottom: 0,
                  left: 0,
                  right: 0,
                  height: 3,
                  background: card.color,
                  borderRadius: "0 0 16px 16px",
                  opacity: 0.8,
                }}
              />
            </div>
          );
        })}
      </div>

      <div
        style={{
          position: "absolute",
          bottom: 40,
          right: 50,
          fontSize: 18,
          color: DIM,
          fontFamily: FONT,
          letterSpacing: "0.1em",
        }}
      >
        02 · 3D Space Cards
      </div>
    </AbsoluteFill>
  );
};

/* ===================================================================
   Scene 3 — SVG PATH DRAW
   라인이 왼쪽에서 오른쪽으로 실시간 그려지며
   각 마일스톤에서 원과 숫자가 팝업.
   =================================================================== */
const LINE_DATA = [
  { year: "2020", value: 12, label: "$12B" },
  { year: "2021", value: 28, label: "$28B" },
  { year: "2022", value: 51, label: "$51B" },
  { year: "2023", value: 91, label: "$91B" },
];

const SVGDrawScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const W = 1000, H = 380;
  const PAD = { l: 80, r: 60, t: 60, b: 80 };

  const drawProgress = interpolate(frame, [10, 140], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });
  const fadeIn = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const maxV = Math.max(...LINE_DATA.map((d) => d.value));
  const xScale = (i: number) =>
    PAD.l + (i / (LINE_DATA.length - 1)) * (W - PAD.l - PAD.r);
  const yScale = (v: number) =>
    H - PAD.b - (v / maxV) * (H - PAD.t - PAD.b);

  // SVG path
  const points = LINE_DATA.map((d, i) => ({ x: xScale(i), y: yScale(d.value) }));
  const pathD = points
    .map((p, i) => (i === 0 ? `M ${p.x} ${p.y}` : `L ${p.x} ${p.y}`))
    .join(" ");

  // 전체 경로 길이 (근사값)
  const totalLen = 1200;
  const dashOffset = totalLen * (1 - drawProgress);

  // 그라디언트 아래 채우기
  const fillPathD =
    pathD +
    ` L ${points[points.length - 1].x} ${H - PAD.b} L ${points[0].x} ${H - PAD.b} Z`;

  return (
    <AbsoluteFill
      style={{
        background: BG_DARK,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        opacity: fadeIn,
      }}
    >
      {/* 제목 */}
      <div
        style={{
          fontSize: 38,
          fontWeight: 700,
          fontFamily: FONT,
          color: WHITE,
          marginBottom: 8,
          textAlign: "center",
        }}
      >
        글로벌 AI 투자 규모
      </div>
      <div
        style={{
          fontSize: 20,
          color: DIM,
          fontFamily: FONT,
          marginBottom: 30,
          textAlign: "center",
        }}
      >
        2020–2023 (단위: 십억 달러)
      </div>

      {/* SVG 차트 */}
      <svg
        width={W}
        height={H}
        viewBox={`0 0 ${W} ${H}`}
        style={{ overflow: "visible" }}
      >
        {/* 그리드 라인 */}
        {[0, 0.25, 0.5, 0.75, 1].map((t) => {
          const y = PAD.t + t * (H - PAD.t - PAD.b);
          const v = Math.round(maxV * (1 - t));
          return (
            <g key={t}>
              <line
                x1={PAD.l}
                y1={y}
                x2={W - PAD.r}
                y2={y}
                stroke="rgba(255,255,255,0.06)"
                strokeWidth={1}
              />
              <text
                x={PAD.l - 12}
                y={y + 5}
                textAnchor="end"
                fill={DIM}
                fontSize={16}
                fontFamily={FONT}
              >
                {v}
              </text>
            </g>
          );
        })}

        {/* 채우기 그라디언트 */}
        <defs>
          <linearGradient id="fillGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={AMBER} stopOpacity={0.2} />
            <stop offset="100%" stopColor={AMBER} stopOpacity={0} />
          </linearGradient>
          <clipPath id="drawClip">
            <rect
              x={0}
              y={0}
              width={PAD.l + (W - PAD.l - PAD.r) * drawProgress + 2}
              height={H}
            />
          </clipPath>
        </defs>

        {/* 채우기 경로 */}
        <path d={fillPathD} fill="url(#fillGrad)" clipPath="url(#drawClip)" />

        {/* 메인 라인 */}
        <path
          d={pathD}
          fill="none"
          stroke={AMBER}
          strokeWidth={4}
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeDasharray={totalLen}
          strokeDashoffset={dashOffset}
        />

        {/* 마일스톤 점 + 라벨 */}
        {points.map((p, i) => {
          const pointProgress = (i + 1) / LINE_DATA.length;
          const appears = drawProgress >= pointProgress - 0.05;
          const dotScale = appears
            ? useSpring(
                Math.max(
                  0,
                  frame -
                    Math.round(
                      10 + 130 * (pointProgress - 0.05)
                    )
                ),
                fps,
                { from: 0, to: 1, damping: 10, stiffness: 250 }
              )
            : 0;

          return (
            <g key={i} style={{ opacity: dotScale }}>
              {/* 외부 원 글로우 */}
              <circle cx={p.x} cy={p.y} r={18} fill={AMBER} opacity={0.15} />
              {/* 메인 원 */}
              <circle cx={p.x} cy={p.y} r={10} fill={BG_DARK} stroke={AMBER} strokeWidth={3} />
              {/* 중심 점 */}
              <circle cx={p.x} cy={p.y} r={3} fill={AMBER} />

              {/* 값 라벨 */}
              <text
                x={p.x}
                y={p.y - 28}
                textAnchor="middle"
                fill={WHITE}
                fontSize={22}
                fontFamily={FONT}
                fontWeight={700}
              >
                {LINE_DATA[i].label}
              </text>

              {/* 연도 라벨 */}
              <text
                x={p.x}
                y={H - PAD.b + 30}
                textAnchor="middle"
                fill={DIM}
                fontSize={18}
                fontFamily={FONT}
              >
                {LINE_DATA[i].year}
              </text>
            </g>
          );
        })}
      </svg>

      <div
        style={{
          position: "absolute",
          bottom: 40,
          right: 50,
          fontSize: 18,
          color: DIM,
          fontFamily: FONT,
          letterSpacing: "0.1em",
        }}
      >
        03 · SVG Path Draw
      </div>
    </AbsoluteFill>
  );
};

/* ===================================================================
   Scene 4 — VECTOR FACE STORY
   인라인 SVG 캐릭터가 데이터에 반응.
   처음: 걱정 표정 → 좋은 데이터 등장 → 웃는 표정으로 변화.
   =================================================================== */
const VectorFaceScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const PHASE_1 = 40;   // 걱정 표정
  const PHASE_2 = 90;   // 데이터 등장
  const PHASE_3 = 140;  // 미소 변화

  const smileProgress = interpolate(frame, [PHASE_3, PHASE_3 + 30], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.back(1.5)),
  });

  const fadeIn = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const dataScale = useSpring(Math.max(0, frame - PHASE_2), fps, {
    from: 0,
    to: 1,
    damping: 12,
    stiffness: 200,
  });

  // 머리 흔들기 (걱정 단계)
  const headShake =
    frame < PHASE_2
      ? Math.sin(frame * 0.4) * interpolate(frame, [0, PHASE_1, PHASE_2], [0, 8, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        })
      : 0;

  // 눈: 걱정(= > <) → 웃음(^ ^)
  const eyeOpenness = 1 - smileProgress * 0.5; // 웃으면 눈이 반쯤 감김

  // 입 커브: -1(찡그림) → 0 → +1(웃음)
  const mouthCurve = interpolate(smileProgress, [0, 1], [-0.4, 1]);

  // 볼터치 opacity
  const blushOpacity = smileProgress;

  // 별/파티클
  const starScale = useSpring(Math.max(0, frame - PHASE_3 - 10), fps, {
    from: 0,
    to: 1,
    damping: 10,
    stiffness: 180,
  });

  const bgColor = interpolate(smileProgress, [0, 1], [0, 1]);

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(ellipse 80% 60% at 50% 40%, ${
          smileProgress > 0.5 ? "#0d1a0d" : "#1a0d0d"
        } 0%, #0A0A0A 70%)`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        opacity: fadeIn,
      }}
    >
      {/* 데이터 카드 — 캐릭터 옆 */}
      <div
        style={{
          position: "absolute",
          left: "54%",
          top: "50%",
          transform: `translate(80px, -50%) scale(${dataScale})`,
          transformOrigin: "left center",
          background: BG_CARD,
          border: `1px solid #10B98144`,
          borderRadius: 20,
          padding: "28px 36px",
          width: 340,
          boxShadow: "0 0 40px rgba(16,185,129,0.15)",
        }}
      >
        <div
          style={{ fontSize: 14, color: "#10B981", fontFamily: FONT, fontWeight: 600, letterSpacing: "0.08em", marginBottom: 10 }}
        >
          🎉 좋은 소식
        </div>
        <div style={{ fontSize: 56, fontWeight: 900, fontFamily: FONT, color: WHITE, lineHeight: 1 }}>
          +340%
        </div>
        <div style={{ fontSize: 18, color: DIM, fontFamily: FONT, marginTop: 8 }}>
          AI 도입 후 생산성 향상
        </div>
        <div
          style={{
            marginTop: 16,
            height: 4,
            background: "linear-gradient(90deg, #10B981, #3B82F6)",
            borderRadius: 2,
          }}
        />
      </div>

      {/* 벡터 캐릭터 (인라인 SVG) */}
      <svg
        width={280}
        height={340}
        viewBox="0 0 280 340"
        style={{
          position: "absolute",
          left: "50%",
          top: "50%",
          transform: `translate(calc(-50% - 220px), -50%) translateX(${headShake}px)`,
          overflow: "visible",
        }}
      >
        {/* 몸통 */}
        <rect
          x={80}
          y={230}
          width={120}
          height={90}
          rx={20}
          fill="#2A2A3A"
          stroke="#3A3A4A"
          strokeWidth={2}
        />
        {/* 넥타이 */}
        <polygon
          points="130,230 150,230 148,290 140,310 132,290"
          fill={smileProgress > 0.3 ? "#10B981" : "#EF4444"}
          opacity={0.9}
        />

        {/* 목 */}
        <rect x={120} y={210} width={40} height={30} rx={10} fill="#F5CABC" />

        {/* 머리 */}
        <ellipse cx={140} cy={165} rx={80} ry={85} fill="#F5CABC" />

        {/* 귀 */}
        <ellipse cx={62} cy={170} rx={16} ry={20} fill="#F5CABC" />
        <ellipse cx={218} cy={170} rx={16} ry={20} fill="#F5CABC" />
        <ellipse cx={62} cy={170} rx={8} ry={12} fill="#E8A090" opacity={0.5} />
        <ellipse cx={218} cy={170} rx={8} ry={12} fill="#E8A090" opacity={0.5} />

        {/* 머리카락 */}
        <ellipse cx={140} cy={88} rx={82} ry={42} fill="#3D2A1A" />
        <ellipse cx={80} cy={100} rx={30} ry={40} fill="#3D2A1A" />
        <ellipse cx={200} cy={100} rx={30} ry={40} fill="#3D2A1A" />

        {/* 눈썹 (걱정 → 편안) */}
        <path
          d={`M 100,138 Q 120,${130 + smileProgress * 6} 130,138`}
          stroke="#3D2A1A"
          strokeWidth={5}
          fill="none"
          strokeLinecap="round"
        />
        <path
          d={`M 150,138 Q 160,${130 + smileProgress * 6} 180,138`}
          stroke="#3D2A1A"
          strokeWidth={5}
          fill="none"
          strokeLinecap="round"
        />

        {/* 눈 흰자 */}
        <ellipse cx={115} cy={162} rx={20} ry={20 * eyeOpenness} fill={WHITE} />
        <ellipse cx={165} cy={162} rx={20} ry={20 * eyeOpenness} fill={WHITE} />

        {/* 눈동자 */}
        <circle cx={117} cy={164} r={10 * eyeOpenness} fill="#2A1A0A" />
        <circle cx={167} cy={164} r={10 * eyeOpenness} fill="#2A1A0A" />
        {/* 눈 하이라이트 */}
        <circle cx={120} cy={160} r={4 * eyeOpenness} fill={WHITE} opacity={0.9} />
        <circle cx={170} cy={160} r={4 * eyeOpenness} fill={WHITE} opacity={0.9} />

        {/* 코 */}
        <ellipse cx={140} cy={180} rx={8} ry={5} fill="#E8A090" opacity={0.6} />

        {/* 입: 찡그림 → 미소 */}
        <path
          d={`M 115,200 Q 140,${200 + mouthCurve * 25} 165,200`}
          stroke="#CD816F"
          strokeWidth={4}
          fill="none"
          strokeLinecap="round"
        />
        {/* 이가 보임 (웃을 때) */}
        {smileProgress > 0.5 && (
          <path
            d="M 118,202 Q 140,218 162,202"
            fill={WHITE}
            opacity={(smileProgress - 0.5) * 2}
          />
        )}

        {/* 볼터치 */}
        <ellipse cx={92} cy={190} rx={22} ry={14} fill="#E88789" opacity={blushOpacity * 0.55} />
        <ellipse cx={188} cy={190} rx={22} ry={14} fill="#E88789" opacity={blushOpacity * 0.55} />

        {/* 별 파티클 (웃음 후) */}
        {["★", "✦", "★", "✦"].map((star, i) => {
          const angle = (i / 4) * Math.PI * 2 - Math.PI / 4;
          const r = 110 + Math.sin(frame * 0.05 + i) * 8;
          const sx = 140 + Math.cos(angle) * r;
          const sy = 165 + Math.sin(angle) * r * 0.6;
          return (
            <text
              key={i}
              x={sx}
              y={sy}
              textAnchor="middle"
              fontSize={i % 2 === 0 ? 20 : 14}
              fill={AMBER}
              opacity={starScale * (0.6 + Math.sin(frame * 0.1 + i) * 0.3)}
              style={{ transform: `rotate(${frame * 0.5 + i * 90}deg)`, transformOrigin: `${sx}px ${sy}px` }}
            >
              {star}
            </text>
          );
        })}
      </svg>

      {/* 말풍선 텍스트 */}
      {frame >= PHASE_3 + 20 && (
        <div
          style={{
            position: "absolute",
            bottom: 100,
            left: "50%",
            transform: `translateX(-50%) scale(${useSpring(frame - PHASE_3 - 20, fps, { from: 0, to: 1, damping: 14 })})`,
            fontSize: 32,
            fontWeight: 700,
            fontFamily: FONT,
            color: "#10B981",
            textAlign: "center",
            whiteSpace: "nowrap",
          }}
        >
          이거... 나쁘지 않은데? 😌
        </div>
      )}

      <div
        style={{
          position: "absolute",
          bottom: 40,
          right: 50,
          fontSize: 18,
          color: DIM,
          fontFamily: FONT,
          letterSpacing: "0.1em",
        }}
      >
        04 · Vector Face Story
      </div>
    </AbsoluteFill>
  );
};

/* ===================================================================
   Main Composition
   =================================================================== */
const SCENE_DUR = 210; // 7s per scene at 30fps

export const MotionShowcase: React.FC = () => {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ background: BG_DARK }}>
      <Sequence from={0} durationInFrames={SCENE_DUR} layout="none">
        <KineticTypoScene />
      </Sequence>
      <Sequence from={SCENE_DUR} durationInFrames={SCENE_DUR} layout="none">
        <Card3DScene />
      </Sequence>
      <Sequence from={SCENE_DUR * 2} durationInFrames={SCENE_DUR} layout="none">
        <SVGDrawScene />
      </Sequence>
      <Sequence from={SCENE_DUR * 3} durationInFrames={SCENE_DUR} layout="none">
        <VectorFaceScene />
      </Sequence>
    </AbsoluteFill>
  );
};
