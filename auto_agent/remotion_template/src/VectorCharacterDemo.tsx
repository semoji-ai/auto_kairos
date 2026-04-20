/**
 * VectorCharacterDemo v2 — 벡터 캐릭터 심화 (리디자인)
 *
 * 디자인 원칙 (Duolingo / 웹툰 스타일 참고):
 *  - 눈이 얼굴의 주인공: 전체 얼굴 대비 매우 크게
 *  - 15개 이하의 클린한 쉐이프
 *  - 큐빅 베지어 헤어 (椭圆 금지)
 *  - 아이리스 레이어: 흰자 → 채색 홍채 → 검은 동공 → 하이라이트
 *  - 파라메트릭: joy/surprise/anger/think/blink 수치로 표정 제어
 *
 * Scene 1: Expression Grid  — 8가지 표정 샷
 * Scene 2: Announcer        — 캐릭터가 통계 소개
 * Scene 3: Reaction         — 충격→생각→해결 3단 스토리
 * Scene 4: Two Characters   — 두 캐릭터 대화
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

/* ─── math helpers ───────────────────────────────── */
const lerp = (a: number, b: number, t: number) =>
  a + (b - a) * Math.max(0, Math.min(1, t));
const clamp = (v: number, lo: number, hi: number) =>
  Math.max(lo, Math.min(hi, v));
function sp(
  frame: number, fps: number, from: number, to: number,
  damping = 14, stiffness = 200,
) {
  return spring({ frame, fps, config: { damping, stiffness, mass: 0.6 }, from, to });
}

/* ─── design tokens ──────────────────────────────── */
const FONT   = "'Noto Sans KR','Apple SD Gothic Neo',sans-serif";
const AMBER  = "#F59E0B";
const GREEN  = "#10B981";
const RED    = "#EF4444";
const BLUE   = "#3B82F6";
const PURPLE = "#8B5CF6";
const WHITE  = "#FFFFFF";
const DIM    = "#52525B";
const BG     = "#0A0A0A";
const CARD   = "#141414";

/* ─── skin palette (세모지 엔진 기준) ─────────────── */
const S = {
  skin:    "#F5CABC",
  shadow:  "#D4896E",
  shadow2: "#C77050",
  blush:   "#E88789",
  hair:    "#3D2A1A",
  hairHL:  "#5A3D25",
  lip:     "#C97060",
  white:   "#FFFFFF",
  pupil:   "#1A0A05",
};

/* ================================================================
   FACE — 완전 재설계
   viewBox "0 0 200 240"  →  cx=100, cy=122

   Layers (bottom → top):
   1. 헤어 (뒤)
   2. 귀
   3. 얼굴 (피부)
   4. 얼굴 그림자
   5. 눈 (흰자→홍채→동공→하이라이트)
   6. 눈썹
   7. 코
   8. 입
   9. 볼터치
   10. 헤어 (앞 뱅)
   11. 이펙트 (땀방울/별)
   ================================================================ */

interface FaceProps {
  /* expression params 0–1 */
  joy?: number;
  surprise?: number;
  anger?: number;
  think?: number;
  /* anim params */
  blink?: number;   // 0=open 1=closed
  lookX?: number;   // -1~+1
  headTilt?: number;
  sweat?: boolean;
  /* style */
  skin?: string;
  hairColor?: string;
  irisColor?: string;
  tieColor?: string;
  /* transform */
  x?: number; y?: number; scale?: number;
}

const Face: React.FC<FaceProps> = ({
  joy = 0, surprise = 0, anger = 0, think = 0,
  blink = 0, lookX = 0, headTilt = 0, sweat = false,
  skin = S.skin, hairColor = S.hair, irisColor = "#5B9BD5",
  tieColor = AMBER,
  x = 0, y = 0, scale = 1,
}) => {
  /* ── derived values ── */
  const eyeScaleY  = clamp(1 + surprise * 0.35 - joy * 0.28 - anger * 0.25 - blink * 0.95, 0.05, 1.35);
  const pupilScale = clamp(1 + surprise * 0.2 - anger * 0.1, 0.7, 1.2);
  const blushOpa   = clamp(joy * 0.65 + surprise * 0.15, 0, 0.65);

  /* Eyebrow: y offset + inner-corner dip for anger / raise for surprise */
  const browBaseY  = 80;
  const browLift   = -surprise * 14 + anger * 4;
  /* inner corner delta Y: anger dips inner brows toward nose */
  const browInnerDip = anger * 18;
  /* think: one brow raised */
  const browLiftL  = browLift + think * -10;
  const browLiftR  = browLift;

  /* Mouth */
  const mouthOpenY = surprise * 18;               // lower jaw drops
  const mouthCurve = joy * 30 - anger * 16;       // positive=smile, negative=frown
  const mouthWidth = lerp(28, 40, joy + surprise * 0.5);

  /* Pupil position */
  const px = lookX * 8;
  const py = think * 5 + surprise * -2;

  /* Shadow skin color */
  const shadow = S.shadow;
  const shadow2 = S.shadow2;

  return (
    <g transform={`translate(${x},${y}) scale(${scale}) rotate(${headTilt},100,122)`}>

      {/* ── 1. 헤어 (뒤) ── */}
      <path
        d={`
          M 100,22
          C 50,16 10,50 12,108
          C 22,70 50,44 100,42
          C 150,44 178,70 188,108
          C 190,50 150,16 100,22 Z
        `}
        fill={hairColor}
      />
      {/* 사이드 헤어 */}
      <path
        d="M 12,108 C 4,140 6,190 22,210 C 14,188 10,155 12,108 Z"
        fill={hairColor}
      />
      <path
        d="M 188,108 C 196,140 194,190 178,210 C 186,188 190,155 188,108 Z"
        fill={hairColor}
      />

      {/* ── 2. 귀 ── */}
      <path d="M 16,122 C 8,110 8,140 16,152 C 22,148 24,130 16,122 Z" fill={skin} />
      <path d="M 184,122 C 192,110 192,140 184,152 C 178,148 176,130 184,122 Z" fill={skin} />
      {/* 귀 안쪽 음영 */}
      <path d="M 16,126 C 11,117 11,137 16,148 C 20,144 21,132 16,126 Z" fill={shadow} opacity={0.35} />
      <path d="M 184,126 C 189,117 189,137 184,148 C 180,144 179,132 184,126 Z" fill={shadow} opacity={0.35} />

      {/* ── 3. 얼굴 ── */}
      <path
        d={`
          M 100,24
          C 44,24 14,64 14,118
          C 14,176 52,218 100,218
          C 148,218 186,176 186,118
          C 186,64 156,24 100,24 Z
        `}
        fill={skin}
      />

      {/* ── 4. 얼굴 음영 (아래턱/코옆) ── */}
      <path
        d="M 55,160 C 55,196 145,196 145,160 C 145,178 100,188 55,160 Z"
        fill={shadow}
        opacity={0.12}
      />

      {/* ── 5. 눈 ── */}
      {/* === 왼쪽 눈 === */}
      <g transform={`translate(68,114)`}>
        {/* 흰자 */}
        <ellipse cx={0} cy={0} rx={26} ry={23 * eyeScaleY} fill={WHITE} />
        {/* 홍채 */}
        <ellipse cx={px} cy={py} rx={19} ry={20 * eyeScaleY * pupilScale}
          fill={irisColor} clipPath="url(#eyeClipL)" />
        {/* 홍채 그라디언트 (밝은 위쪽) */}
        <ellipse cx={px} cy={py - 6 * eyeScaleY} rx={17} ry={12 * eyeScaleY}
          fill="rgba(255,255,255,0.18)" clipPath="url(#eyeClipL)" />
        {/* 동공 */}
        <circle cx={px} cy={py} r={12 * eyeScaleY * pupilScale}
          fill={S.pupil} clipPath="url(#eyeClipL)" />
        {/* 눈 하이라이트 대 */}
        <circle cx={px + 7} cy={py - 7 * eyeScaleY} r={6}
          fill={WHITE} opacity={eyeScaleY > 0.2 ? 0.96 : 0} />
        {/* 눈 하이라이트 소 */}
        <circle cx={px - 5} cy={py + 6 * eyeScaleY} r={3}
          fill={WHITE} opacity={eyeScaleY > 0.2 ? 0.55 : 0} />
        {/* 눈꺼풀 위선 */}
        <path
          d={`M -26,${-2 * eyeScaleY} Q 0,${-26 * eyeScaleY} 26,${-2 * eyeScaleY}`}
          fill="none" stroke={hairColor} strokeWidth={3.5} strokeLinecap="round"
        />
        {/* blink 커버 */}
        {blink > 0.1 && (
          <ellipse cx={0} cy={0} rx={27} ry={23 * blink} fill={skin} />
        )}
        <clipPath id="eyeClipL">
          <ellipse cx={0} cy={0} rx={26} ry={23 * eyeScaleY} />
        </clipPath>
      </g>

      {/* === 오른쪽 눈 === */}
      <g transform={`translate(132,114)`}>
        <ellipse cx={0} cy={0} rx={26} ry={23 * eyeScaleY} fill={WHITE} />
        <ellipse cx={px} cy={py} rx={19} ry={20 * eyeScaleY * pupilScale}
          fill={irisColor} clipPath="url(#eyeClipR)" />
        <ellipse cx={px} cy={py - 6 * eyeScaleY} rx={17} ry={12 * eyeScaleY}
          fill="rgba(255,255,255,0.18)" clipPath="url(#eyeClipR)" />
        <circle cx={px} cy={py} r={12 * eyeScaleY * pupilScale}
          fill={S.pupil} clipPath="url(#eyeClipR)" />
        <circle cx={px + 7} cy={py - 7 * eyeScaleY} r={6}
          fill={WHITE} opacity={eyeScaleY > 0.2 ? 0.96 : 0} />
        <circle cx={px - 5} cy={py + 6 * eyeScaleY} r={3}
          fill={WHITE} opacity={eyeScaleY > 0.2 ? 0.55 : 0} />
        <path
          d={`M -26,${-2 * eyeScaleY} Q 0,${-26 * eyeScaleY} 26,${-2 * eyeScaleY}`}
          fill="none" stroke={hairColor} strokeWidth={3.5} strokeLinecap="round"
        />
        {blink > 0.1 && (
          <ellipse cx={0} cy={0} rx={27} ry={23 * blink} fill={skin} />
        )}
        <clipPath id="eyeClipR">
          <ellipse cx={0} cy={0} rx={26} ry={23 * eyeScaleY} />
        </clipPath>
      </g>

      {/* ── 6. 눈썹 ── */}
      {/* 왼쪽 눈썹 */}
      <path
        d={`M ${48},${browBaseY + browLiftL + browInnerDip}
            C ${62},${browBaseY + browLiftL + browInnerDip - 14}
              ${78},${browBaseY + browLiftL - 16}
              ${90},${browBaseY + browLiftL - 10}`}
        fill="none" stroke={hairColor} strokeWidth={7}
        strokeLinecap="round" strokeLinejoin="round"
      />
      {/* 오른쪽 눈썹 */}
      <path
        d={`M ${110},${browBaseY + browLiftR - 10}
            C ${122},${browBaseY + browLiftR - 16}
              ${138},${browBaseY + browLiftR + browInnerDip - 14}
              ${152},${browBaseY + browLiftR + browInnerDip}`}
        fill="none" stroke={hairColor} strokeWidth={7}
        strokeLinecap="round" strokeLinejoin="round"
      />

      {/* ── 7. 코 (미니멀) ── */}
      <path
        d="M 94,152 C 91,156 91,160 96,162 C 100,163 104,163 108,162 C 113,160 113,156 110,152"
        fill="none" stroke={shadow} strokeWidth={2.5} strokeLinecap="round"
      />

      {/* ── 8. 입 ── */}
      {surprise > 0.5 ? (
        /* O자 입 */
        <ellipse cx={100} cy={183 + mouthOpenY * 0.5}
          rx={mouthWidth * 0.6} ry={8 + mouthOpenY * 0.6}
          fill={S.pupil}
        />
      ) : (
        /* 미소/찡그림 */
        <>
          <path
            d={`M ${100 - mouthWidth},${180} Q ${100},${180 + mouthCurve} ${100 + mouthWidth},${180}`}
            fill="none" stroke={S.lip} strokeWidth={4.5} strokeLinecap="round"
          />
          {/* 이 (기쁨 크면) */}
          {joy > 0.5 && (
            <path
              d={`M ${100 - mouthWidth + 4},${182}
                  Q ${100},${182 + mouthCurve * 0.75}
                  ${100 + mouthWidth - 4},${182}`}
              fill={WHITE}
              opacity={(joy - 0.5) * 1.8}
            />
          )}
        </>
      )}

      {/* ── 9. 볼터치 ── */}
      <ellipse cx={50} cy={158} rx={24} ry={14}
        fill={S.blush} opacity={blushOpa} />
      <ellipse cx={150} cy={158} rx={24} ry={14}
        fill={S.blush} opacity={blushOpa} />

      {/* ── 10. 헤어 앞 뱅 ── */}
      <path
        d={`
          M 14,105
          C 18,62 46,28 100,26
          C 154,28 182,62 186,105
          C 165,72 140,56 100,54
          C 60,56 35,72 14,105 Z
        `}
        fill={hairColor}
      />
      {/* 헤어 하이라이트 */}
      <path
        d="M 62,34 C 78,26 122,26 138,34 C 120,28 80,28 62,34 Z"
        fill={S.hairHL}
        opacity={0.6}
      />

      {/* ── 11. 이펙트 ── */}
      {sweat && (
        <g transform="translate(156, 64)">
          {/* 땀방울 큰 것 */}
          <path d="M 0,-14 C -8,-8 -10,0 0,6 C 10,0 8,-8 0,-14 Z"
            fill={BLUE} opacity={0.85} />
          {/* 땀방울 작은 것 */}
          <path d="M 14,-6 C 10,-2 9,2 14,5 C 19,2 18,-2 14,-6 Z"
            fill={BLUE} opacity={0.65} />
        </g>
      )}
    </g>
  );
};

/* ── 목 + 몸통 + 팔 ──────────────────────────────── */
interface BodyProps {
  armAngleL?: number;
  armAngleR?: number;
  tieColor?: string;
  suitColor?: string;
  bounce?: number;
  x?: number; y?: number; scale?: number;
}

const Body: React.FC<BodyProps> = ({
  armAngleL = Math.PI * 0.38,
  armAngleR = -Math.PI * 0.38,
  tieColor = AMBER,
  suitColor = "#1E1E2E",
  bounce = 0,
  x = 0, y = 0, scale = 1,
}) => {
  const bx = 100, by = 18 + bounce;
  const ARM = 78;

  /* hand positions */
  const lhx = bx - 52 + Math.cos(Math.PI - armAngleL) * ARM;
  const lhy = by + 16 + Math.sin(Math.PI - armAngleL) * ARM;
  const rhx = bx + 52 + Math.cos(armAngleR) * ARM;
  const rhy = by + 16 + Math.sin(armAngleR) * ARM;

  return (
    <g transform={`translate(${x},${y}) scale(${scale})`}>
      {/* 목 */}
      <path
        d={`M 85,${by - 8} C 82,${by + 14} 82,${by + 26} 85,${by + 32}
            L 115,${by + 32} C 118,${by + 26} 118,${by + 14} 115,${by - 8} Z`}
        fill={S.skin}
      />

      {/* 팔 (몸통 아래 레이어) */}
      {/* 왼팔 */}
      <line x1={bx - 46} y1={by + 22} x2={lhx} y2={lhy}
        stroke={suitColor} strokeWidth={28} strokeLinecap="round" />
      <line x1={bx - 46} y1={by + 22} x2={lhx} y2={lhy}
        stroke={"#2A2A3E"} strokeWidth={22} strokeLinecap="round" />
      {/* 오른팔 */}
      <line x1={bx + 46} y1={by + 22} x2={rhx} y2={rhy}
        stroke={suitColor} strokeWidth={28} strokeLinecap="round" />
      <line x1={bx + 46} y1={by + 22} x2={rhx} y2={rhy}
        stroke={"#2A2A3E"} strokeWidth={22} strokeLinecap="round" />

      {/* 손 */}
      <circle cx={lhx} cy={lhy} r={14} fill={S.skin} />
      <circle cx={lhx} cy={lhy} r={14} fill={S.shadow} opacity={0.15} />
      <circle cx={rhx} cy={rhy} r={14} fill={S.skin} />
      <circle cx={rhx} cy={rhy} r={14} fill={S.shadow} opacity={0.15} />

      {/* 몸통 */}
      <path
        d={`M ${bx - 56},${by + 16}
            C ${bx - 58},${by + 32} ${bx - 58},${by + 100} ${bx - 50},${by + 120}
            L ${bx + 50},${by + 120}
            C ${bx + 58},${by + 100} ${bx + 58},${by + 32} ${bx + 56},${by + 16} Z`}
        fill={suitColor}
      />
      {/* 몸통 하이라이트 */}
      <path
        d={`M ${bx - 30},${by + 18}
            C ${bx - 28},${by + 40} ${bx - 28},${by + 70} ${bx - 32},${by + 90}
            L ${bx - 24},${by + 90}
            C ${bx - 20},${by + 70} ${bx - 20},${by + 40} ${bx - 22},${by + 18} Z`}
        fill={WHITE} opacity={0.04}
      />

      {/* 셔츠 칼라 */}
      <path
        d={`M ${bx - 22},${by + 16} L ${bx},${by + 38} L ${bx + 22},${by + 16}`}
        fill={WHITE} opacity={0.12}
      />

      {/* 넥타이 */}
      <path
        d={`M ${bx - 11},${by + 18}
            L ${bx + 11},${by + 18}
            L ${bx + 9},${by + 68}
            L ${bx},${by + 90}
            L ${bx - 9},${by + 68} Z`}
        fill={tieColor}
      />
      {/* 넥타이 매듭 */}
      <path
        d={`M ${bx - 11},${by + 18} C ${bx - 4},${by + 26} ${bx + 4},${by + 26} ${bx + 11},${by + 18}
            C ${bx + 6},${by + 28} ${bx - 6},${by + 28} ${bx - 11},${by + 18} Z`}
        fill={tieColor} filter="brightness(0.8)"
      />
    </g>
  );
};

/* ─── 말풍선 ─────────────────────────────────────── */
const Bubble: React.FC<{
  lines: string[];
  x: number; y: number;
  tailDir?: "left" | "right";
  accent?: string;
  scale?: number;
  width?: number;
}> = ({ lines, x, y, tailDir = "left", accent = WHITE, scale = 1, width = 300 }) => {
  const h = 44 + lines.length * 28;
  const tailX = tailDir === "left" ? 32 : width - 32;
  return (
    <g transform={`translate(${x},${y}) scale(${scale})`}
      style={{ transformOrigin: `${tailDir === "left" ? "0" : `${width}px`} 100%` }}>
      {/* 그림자 */}
      <rect x={2} y={2} width={width} height={h} rx={18}
        fill="black" opacity={0.18} />
      {/* 본체 */}
      <rect x={0} y={0} width={width} height={h} rx={18}
        fill={CARD} stroke={accent} strokeWidth={1.5} />
      {/* 꼬리 */}
      <polygon points={`${tailX - 10},${h} ${tailX + 10},${h} ${tailX},${h + 14}`}
        fill={CARD} />
      <line x1={tailX - 10} y1={h} x2={tailX} y2={h + 14}
        stroke={accent} strokeWidth={1.5} />
      <line x1={tailX} y1={h + 14} x2={tailX + 10} y2={h}
        stroke={accent} strokeWidth={1.5} />
      {/* 텍스트 */}
      {lines.map((line, i) => (
        <text key={i} x={width / 2} y={32 + i * 28}
          textAnchor="middle" fill={WHITE}
          fontSize={i === 0 && lines.length > 1 ? 15 : 19}
          fontFamily={FONT}
          fontWeight={i === 0 && lines.length > 1 ? 400 : 600}
          opacity={i === 0 && lines.length > 1 ? 0.55 : 1}>
          {line}
        </text>
      ))}
    </g>
  );
};

/* ================================================================
   Scene 1 — Expression Grid (2×4)
   ================================================================ */
const EXPR_DATA = [
  { label: "기쁨",    joy: 1,       blink: 0,   headTilt: -6,  iris: "#5B9BD5" },
  { label: "놀람",    surprise: 1,  lookX: 0.3, headTilt:  5,  iris: "#7C3AED" },
  { label: "화남",    anger: 1,     headTilt:   4,             iris: "#DC2626" },
  { label: "생각중",  think: 1,     lookX: -0.55, headTilt: -4, iris: "#0EA5E9" },
  { label: "윙크",    blink: 0.95,  joy: 0.5,   headTilt: -8,  iris: "#10B981" },
  { label: "당황",    surprise: 0.6, sweat: true, headTilt:3,  iris: "#F59E0B" },
  { label: "찡그림",  anger: 0.6,   joy: -0.2,  headTilt: 6,   iris: "#6B7280" },
  { label: "감동",    joy: 0.8,     blink: 0.2, headTilt: -4,  iris: "#EC4899" },
];

const ExpressionGridScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill style={{ background: BG, fontFamily: FONT }}>
      {/* 헤더 */}
      <div style={{
        position: "absolute", top: 36, width: "100%", textAlign: "center",
      }}>
        <div style={{ fontSize: 30, fontWeight: 800, color: WHITE, letterSpacing: 1 }}>
          Expression Sheet
        </div>
        <div style={{ fontSize: 16, color: DIM, marginTop: 6 }}>
          joy · surprise · anger · think · blink — 파라메트릭 제어
        </div>
      </div>

      {/* 2×4 그리드 */}
      {EXPR_DATA.map((expr, i) => {
        const col = i % 4;
        const row = Math.floor(i / 4);
        const px = 80 + col * 292;
        const py = 110 + row * 270;
        const delay = i * 8;
        const esc = sp(Math.max(0, frame - delay), fps, 0, 1, 10, 200);

        // 아이리스 색: 눈 색은 표정 고유 색으로
        const irisColor = expr.iris || "#5B9BD5";

        // 넥타이 색을 표정마다 다르게
        const tieColors = [GREEN, PURPLE, RED, BLUE, GREEN, AMBER, DIM, "#EC4899"];

        return (
          <g key={i} style={{ position: "absolute", left: 0, top: 0 }}>
            <svg
              style={{
                position: "absolute", left: px - 100, top: py - 160,
                width: 200, height: 250,
                transform: `scale(${esc})`,
                transformOrigin: "50% 80%",
                filter: `drop-shadow(0 8px 24px rgba(0,0,0,0.7))`,
              }}
              viewBox="0 0 200 240"
            >
              <Face
                {...(expr as any)}
                irisColor={irisColor}
                x={0} y={0} scale={1}
              />
              <Body tieColor={tieColors[i]} x={-5} y={218} scale={0.82} />
            </svg>

            {/* 라벨 */}
            <div style={{
              position: "absolute",
              left: px - 46,
              top: py + 105,
              width: 92,
              textAlign: "center",
              fontSize: 17,
              fontWeight: 700,
              color: tieColors[i],
              fontFamily: FONT,
            }}>
              {expr.label}
            </div>
          </g>
        );
      })}

      <div style={{ position: "absolute", bottom: 28, right: 48, fontSize: 15, color: DIM, letterSpacing: "0.08em" }}>
        01 · Expression Sheet
      </div>
    </AbsoluteFill>
  );
};

/* ================================================================
   Scene 2 — Data Announcer
   ================================================================ */
const STATS = [
  { val: "28억", sub: "유튜브 월간 사용자", color: RED,   delay: 28 },
  { val: "$91B", sub: "글로벌 AI 투자 규모", color: BLUE, delay: 68 },
  { val: "+340%", sub: "AI 도입 생산성 향상", color: GREEN, delay: 108 },
];

const AnnouncerScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const charX = sp(Math.max(0, frame - 4), fps, -380, 0, 16, 130);
  const charSc = sp(Math.max(0, frame - 4), fps, 0.6, 1, 12, 150);
  const joy = clamp((frame - 28) / 55, 0, 0.85);
  const pointing = frame > 22;
  const armR = pointing
    ? sp(Math.max(0, frame - 22), fps, -Math.PI * 0.3, -Math.PI * 0.52, 10, 180)
    : -Math.PI * 0.3;
  const bounce = Math.sin(frame * 0.16) * 3.5;
  const bubbleSc = sp(Math.max(0, frame - 38), fps, 0, 1, 9, 260);
  const blink = (frame % 80 < 3) ? 1 : 0;

  return (
    <AbsoluteFill style={{
      background: "radial-gradient(ellipse 75% 55% at 28% 50%, #081a0d 0%, #0A0A0A 65%)",
      fontFamily: FONT,
    }}>
      {/* 캐릭터 */}
      <svg style={{
        position: "absolute",
        left: charX + 30,
        bottom: 30,
        width: 320, height: 580,
        transform: `scale(${charSc})`,
        transformOrigin: "50% 100%",
        filter: "drop-shadow(0 16px 40px rgba(0,0,0,0.7))",
      }} viewBox="0 0 320 580">
        <Face joy={joy} blink={blink} lookX={0.65}
          headTilt={-4 + Math.sin(frame * 0.08) * 2}
          x={60} y={0} scale={1.15}
          tieColor={GREEN} irisColor="#22C55E"
        />
        <Body
          tieColor={GREEN} suitColor="#1A2A1A"
          armAngleL={Math.PI * 0.28}
          armAngleR={armR}
          bounce={bounce}
          x={60} y={240} scale={1.15}
        />
      </svg>

      {/* 말풍선 */}
      <div style={{
        position: "absolute", left: 310, bottom: 460,
        transform: `scale(${bubbleSc})`, transformOrigin: "left bottom",
      }}>
        <Bubble
          lines={["오늘의 AI 핵심 통계 📊", "같이 볼게요!"]}
          x={0} y={0} tailDir="left" accent={GREEN} width={280}
        />
      </div>

      {/* 통계 카드들 */}
      <div style={{
        position: "absolute", right: 60, top: "50%",
        transform: "translateY(-50%)",
        display: "flex", flexDirection: "column", gap: 22,
      }}>
        {STATS.map((s, i) => {
          const sc = sp(Math.max(0, frame - s.delay), fps, 0, 1, 9, 220);
          return (
            <div key={i} style={{
              width: 360, padding: "18px 28px",
              background: CARD,
              border: `1px solid ${s.color}44`,
              borderLeft: `4px solid ${s.color}`,
              borderRadius: "0 14px 14px 0",
              boxShadow: `0 4px 30px ${s.color}18`,
              transform: `scale(${sc})`,
              transformOrigin: "right center",
              display: "flex", alignItems: "center", gap: 18,
            }}>
              <div>
                <div style={{ fontSize: 48, fontWeight: 900, color: s.color, lineHeight: 1 }}>
                  {s.val}
                </div>
                <div style={{ fontSize: 15, color: DIM, marginTop: 4 }}>{s.sub}</div>
              </div>
            </div>
          );
        })}
      </div>

      <div style={{ position: "absolute", bottom: 28, right: 48, fontSize: 15, color: DIM, letterSpacing: "0.08em" }}>
        02 · Data Announcer
      </div>
    </AbsoluteFill>
  );
};

/* ================================================================
   Scene 3 — Reaction Story (충격→생각→해결)
   ================================================================ */
const ReactionScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const phase = frame < 68 ? 0 : frame < 138 ? 1 : 2;
  const pf    = phase === 0 ? frame : phase === 1 ? frame - 68 : frame - 138;
  const pt    = sp(Math.min(pf, 28), fps, 0, 1, 11, 180);

  const phases = [
    { label: "😱 충격",   color: RED,    bgHue: "#1a0808",
      face: { surprise: 1, sweat: true,  headTilt: 7  },
      tie:  RED,   speech: ["AI가…", "내 직업을?!"] },
    { label: "🤔 생각중", color: BLUE,   bgHue: "#08101a",
      face: { think: 1,   lookX: -0.6,  headTilt: -6 },
      tie:  BLUE,  speech: ["음…", "어떻게 대비하지?"] },
    { label: "💡 해결!",  color: GREEN,  bgHue: "#081a0d",
      face: { joy: 1,                   headTilt: -4 },
      tie:  GREEN, speech: ["AI를 도구로", "쓰면 돼!"] },
  ];
  const cur = phases[phase];
  const blink = frame % 72 < 3 ? 1 : 0;
  const bounce = phase === 2 ? Math.sin(frame * 0.22) * 5 : 0;
  const shakeX = phase === 0 ? Math.sin(frame * 1.1) * Math.max(0, 5 - pf * 0.07) : 0;

  const bubbleSc = sp(Math.min(pf, 22), fps, 0, 1, 8, 280);

  // 해결: 카드
  const cardSc = phase === 2 ? sp(Math.max(0, pf - 18), fps, 0, 1, 9, 220) : 0;

  return (
    <AbsoluteFill style={{
      background: `radial-gradient(ellipse 70% 55% at 44% 50%, ${cur.bgHue} 0%, #0A0A0A 65%)`,
      fontFamily: FONT,
    }}>
      {/* 단계 태그 */}
      <div style={{
        position: "absolute", top: 44, left: sp(Math.min(pf, 22), fps, -300, 56, 14, 170),
        background: cur.color + "1A",
        border: `1px solid ${cur.color}44`,
        borderRadius: 30, padding: "10px 28px",
        display: "flex", alignItems: "center", gap: 10,
      }}>
        <div style={{ width: 9, height: 9, borderRadius: "50%",
          background: cur.color, boxShadow: `0 0 8px ${cur.color}` }} />
        <span style={{ fontSize: 21, fontWeight: 700, color: WHITE }}>{cur.label}</span>
      </div>

      {/* 캐릭터 */}
      <svg style={{
        position: "absolute",
        left: 280 + shakeX, bottom: 24,
        width: 340, height: 580,
        filter: "drop-shadow(0 16px 40px rgba(0,0,0,0.7))",
      }} viewBox="0 0 340 580">
        <Face
          {...(cur.face as any)}
          blink={blink}
          irisColor={phase === 0 ? "#EF4444" : phase === 1 ? "#3B82F6" : "#10B981"}
          tieColor={cur.tie}
          x={70} y={0} scale={1.15}
        />
        <Body
          tieColor={cur.tie}
          suitColor={phase === 0 ? "#1a1a22" : phase === 1 ? "#0d1422" : "#0d1a14"}
          armAngleL={phase === 1 ? Math.PI * 0.55 : Math.PI * 0.32}
          armAngleR={phase === 2 ? -Math.PI * 0.6 : -Math.PI * 0.32}
          bounce={bounce}
          x={70} y={240} scale={1.15}
        />
      </svg>

      {/* 말풍선 */}
      <div style={{
        position: "absolute", left: 500, bottom: 440,
        transform: `scale(${bubbleSc})`, transformOrigin: "left bottom",
      }}>
        <Bubble lines={cur.speech} x={0} y={0} tailDir="left"
          accent={cur.color} width={240} />
      </div>

      {/* 해결: 전략 카드 */}
      {phase === 2 && (
        <div style={{
          position: "absolute", right: 60, top: "50%",
          transform: `translateY(-50%) scale(${cardSc})`,
          transformOrigin: "right center",
          width: 350, padding: "28px 32px",
          background: CARD,
          border: `1px solid ${GREEN}44`,
          borderRadius: 20,
          boxShadow: `0 0 50px ${GREEN}1A`,
        }}>
          <div style={{ fontSize: 13, color: GREEN, fontWeight: 700, letterSpacing: "0.1em", marginBottom: 20 }}>
            💡 AI 시대 생존 전략
          </div>
          {["프롬프트 엔지니어링", "데이터 리터러시", "AI + 인간 협업"].map((item, i) => (
            <div key={i} style={{
              display: "flex", alignItems: "center", gap: 14, padding: "10px 0",
              borderBottom: i < 2 ? "1px solid rgba(255,255,255,0.07)" : "none",
            }}>
              <div style={{
                width: 28, height: 28, borderRadius: "50%",
                background: GREEN + "1A", border: `1px solid ${GREEN}44`,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 13, color: GREEN, fontWeight: 800,
              }}>{i + 1}</div>
              <span style={{ fontSize: 18, color: WHITE }}>{item}</span>
            </div>
          ))}
        </div>
      )}

      {/* 생각: 생각 말풍선 */}
      {phase === 1 && (
        <div style={{
          position: "absolute", left: 510, top: 110,
          transform: `scale(${sp(Math.max(0, pf - 12), fps, 0, 1, 9, 200)})`,
          transformOrigin: "left bottom",
        }}>
          <svg width={280} height={160} viewBox="0 0 280 160">
            <circle cx={40} cy={152} r={5.5} fill={CARD} stroke={DIM} strokeWidth={1.5} />
            <circle cx={58} cy={136} r={10} fill={CARD} stroke={DIM} strokeWidth={1.5} />
            <circle cx={80} cy={115} r={16} fill={CARD} stroke={DIM} strokeWidth={1.5} />
            <rect x={96} y={0} width={178} height={100} rx={18}
              fill={CARD} stroke={DIM} strokeWidth={1.5} />
            <text x={185} y={36} textAnchor="middle" fill={DIM} fontSize={13} fontFamily={FONT}>선택지는...</text>
            <text x={185} y={62} textAnchor="middle" fill={WHITE} fontSize={19} fontFamily={FONT} fontWeight={700}>① 배운다</text>
            <text x={185} y={88} textAnchor="middle" fill={WHITE} fontSize={19} fontFamily={FONT} fontWeight={700}>② AI에게 진다</text>
          </svg>
        </div>
      )}

      <div style={{ position: "absolute", bottom: 28, right: 48, fontSize: 15, color: DIM, letterSpacing: "0.08em" }}>
        03 · Reaction Story
      </div>
    </AbsoluteFill>
  );
};

/* ================================================================
   Scene 4 — Two Characters
   ================================================================ */
const DIALOG = [
  { start: 20,  side: "L", text: ["AI가 내 직업을", "대체한다고!"],   color: RED   },
  { start: 68,  side: "R", text: ["아니, 협력하면", "이길 수 있어!"], color: GREEN },
  { start: 116, side: "L", text: ["증거 있어?"],                       color: AMBER },
  { start: 152, side: "R", text: ["있지! 생산성", "+340% 달성!"],      color: GREEN },
];

const TwoScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const lSc = sp(Math.max(0, frame -  0), fps, 0, 1, 13, 140);
  const rSc = sp(Math.max(0, frame - 16), fps, 0, 1, 13, 140);
  const active = DIALOG.filter(d => frame >= d.start).slice(-1)[0];

  const lTalk = active?.side === "L";
  const rTalk = active?.side === "R";

  const lBounce = lTalk ? Math.sin(frame * 0.28) * 4.5 : 0;
  const rBounce = rTalk ? Math.sin(frame * 0.28) * 4.5 : 0;

  const lBlink = frame % 85 < 3 ? 1 : 0;
  const rBlink = frame % 70 < 3 ? 1 : 0;

  const bubSc = active ? sp(frame - active.start, fps, 0, 1, 8, 280) : 0;

  return (
    <AbsoluteFill style={{
      background: "radial-gradient(ellipse 80% 55% at 50% 50%, #0d0d1e 0%, #0A0A0A 65%)",
      fontFamily: FONT,
    }}>
      {/* VS 배경 */}
      <div style={{
        position: "absolute", left: "50%", top: "50%",
        transform: "translate(-50%,-50%)",
        fontSize: 96, fontWeight: 900, color: "#FFFFFF09", letterSpacing: "0.1em",
        userSelect: "none",
      }}>VS</div>

      {/* 구분선 */}
      <div style={{
        position: "absolute", left: "50%", top: 60, bottom: 60,
        width: 1,
        background: `linear-gradient(to bottom, transparent, ${DIM}33 30%, ${DIM}33 70%, transparent)`,
      }} />

      {/* 왼쪽 — 비관론 */}
      <svg style={{
        position: "absolute", left: 30, bottom: 24,
        width: 300, height: 530,
        transform: `scale(${lSc})`, transformOrigin: "50% 100%",
        filter: "drop-shadow(0 12px 32px rgba(0,0,0,0.7))",
      }} viewBox="0 0 300 530">
        <Face
          anger={lTalk ? 0.45 : 0.15}
          blink={lBlink}
          lookX={0.85}
          headTilt={3}
          irisColor={"#EF4444"}
          tieColor={RED}
          x={50} y={0} scale={1.05}
        />
        <Body
          tieColor={RED} suitColor="#1e1414"
          armAngleL={Math.PI * 0.32}
          armAngleR={-Math.PI * 0.36 + lBounce * 0.015}
          bounce={lBounce}
          x={50} y={218} scale={1.05}
        />
      </svg>

      {/* 왼쪽 네임태그 */}
      <div style={{
        position: "absolute", left: 90, bottom: 22,
        background: RED + "18", border: `1px solid ${RED}44`,
        borderRadius: 20, padding: "7px 20px",
        fontSize: 17, fontWeight: 700, color: RED,
      }}>😰 비관론</div>

      {/* 오른쪽 — 낙관론 */}
      <svg style={{
        position: "absolute", right: 30, bottom: 24,
        width: 300, height: 530,
        transform: `scaleX(-1) scale(${rSc})`, transformOrigin: "50% 100%",
        filter: "drop-shadow(0 12px 32px rgba(0,0,0,0.7))",
      }} viewBox="0 0 300 530">
        <Face
          joy={rTalk ? 0.8 : 0.4}
          blink={rBlink}
          lookX={0.85}
          headTilt={-4}
          irisColor={"#10B981"}
          tieColor={GREEN}
          x={50} y={0} scale={1.05}
        />
        <Body
          tieColor={GREEN} suitColor="#14201a"
          armAngleL={Math.PI * 0.28}
          armAngleR={-Math.PI * 0.44 + rBounce * 0.015}
          bounce={rBounce}
          x={50} y={218} scale={1.05}
        />
      </svg>

      {/* 오른쪽 네임태그 */}
      <div style={{
        position: "absolute", right: 90, bottom: 22,
        background: GREEN + "18", border: `1px solid ${GREEN}44`,
        borderRadius: 20, padding: "7px 20px",
        fontSize: 17, fontWeight: 700, color: GREEN,
      }}>😊 낙관론</div>

      {/* 말풍선 */}
      {active && (
        <div style={{
          position: "absolute",
          bottom: 360,
          ...(active.side === "L"
            ? { left: 280, transformOrigin: "left bottom" }
            : { right: 280, transformOrigin: "right bottom" }),
          transform: `scale(${bubSc})`,
        }}>
          <Bubble
            lines={active.text}
            x={0} y={0}
            tailDir={active.side === "L" ? "left" : "right"}
            accent={active.color}
            width={260}
          />
        </div>
      )}

      <div style={{ position: "absolute", bottom: 28, right: 48, fontSize: 15, color: DIM, letterSpacing: "0.08em" }}>
        04 · Two Characters
      </div>
    </AbsoluteFill>
  );
};

/* ================================================================
   Main
   ================================================================ */
const SCENE_DUR = 210;

export const VectorCharacterDemo: React.FC = () => (
  <AbsoluteFill style={{ background: BG }}>
    <Sequence from={0}             durationInFrames={SCENE_DUR} layout="none"><ExpressionGridScene /></Sequence>
    <Sequence from={SCENE_DUR}     durationInFrames={SCENE_DUR} layout="none"><AnnouncerScene /></Sequence>
    <Sequence from={SCENE_DUR * 2} durationInFrames={SCENE_DUR} layout="none"><ReactionScene /></Sequence>
    <Sequence from={SCENE_DUR * 3} durationInFrames={SCENE_DUR} layout="none"><TwoScene /></Sequence>
  </AbsoluteFill>
);
