import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate } from "remotion";

export const SvgCharacterTest: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Animations
  const breathe = Math.sin((frame / fps) * Math.PI * 2) * 1.5;
  const blink = (() => {
    // Blink every ~3 seconds, blink lasts 6 frames
    const blinkCycle = frame % (fps * 3);
    if (blinkCycle < 3) return interpolate(blinkCycle, [0, 3], [1, 0.05]);
    if (blinkCycle < 6) return interpolate(blinkCycle, [3, 6], [0.05, 1]);
    return 1;
  })();

  // Floating elements gentle bob
  const float1 = Math.sin((frame / fps) * Math.PI * 0.8) * 6;
  const float2 = Math.sin((frame / fps) * Math.PI * 0.6 + 1) * 8;
  const float3 = Math.sin((frame / fps) * Math.PI * 1.0 + 2) * 5;

  // Title fade in
  const titleOpacity = interpolate(frame, [0, 40], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: "#0B1428" }}>
      {/* Background glow */}
      <div
        style={{
          position: "absolute",
          width: "100%",
          height: "100%",
          background: "radial-gradient(ellipse at 50% 45%, rgba(22,32,64,0.8) 0%, transparent 65%)",
        }}
      />

      <svg
        viewBox="0 0 1920 1080"
        width="1920"
        height="1080"
        style={{ width: "100%", height: "100%" }}
      >
        <defs>
          {/* Skin gradient */}
          <linearGradient id="skinGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#F5D0A9" />
            <stop offset="100%" stopColor="#E8B88A" />
          </linearGradient>

          {/* Hair gradient */}
          <linearGradient id="hairGrad" x1="0" y1="0" x2="0.3" y2="1">
            <stop offset="0%" stopColor="#3D2B1F" />
            <stop offset="100%" stopColor="#2A1B10" />
          </linearGradient>

          {/* Coat gradient */}
          <linearGradient id="coatGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#F0EDE8" />
            <stop offset="100%" stopColor="#D8D3CB" />
          </linearGradient>

          {/* Shirt gradient */}
          <linearGradient id="shirtGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#2E86AB" />
            <stop offset="100%" stopColor="#1E6A8A" />
          </linearGradient>

          {/* Pants gradient */}
          <linearGradient id="pantsGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#2C3E50" />
            <stop offset="100%" stopColor="#1A2530" />
          </linearGradient>

          {/* Shoe gradient */}
          <linearGradient id="shoeGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#8B4513" />
            <stop offset="100%" stopColor="#6B3410" />
          </linearGradient>

          {/* Book gradient */}
          <linearGradient id="bookGrad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#C0392B" />
            <stop offset="100%" stopColor="#962D22" />
          </linearGradient>

          {/* Glasses lens */}
          <radialGradient id="lensGrad" cx="0.3" cy="0.3" r="0.7">
            <stop offset="0%" stopColor="rgba(200,220,255,0.25)" />
            <stop offset="100%" stopColor="rgba(150,180,220,0.08)" />
          </radialGradient>

          {/* Drop shadow */}
          <filter id="softShadow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur in="SourceAlpha" stdDeviation="8" />
            <feOffset dx="4" dy="6" result="offsetblur" />
            <feComponentTransfer>
              <feFuncA type="linear" slope="0.25" />
            </feComponentTransfer>
            <feMerge>
              <feMergeNode />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          {/* Glow filter */}
          <filter id="glow">
            <feGaussianBlur stdDeviation="4" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          {/* Background star glow */}
          <radialGradient id="starGlow" cx="0.5" cy="0.5" r="0.5">
            <stop offset="0%" stopColor="rgba(255,255,255,0.6)" />
            <stop offset="100%" stopColor="rgba(255,255,255,0)" />
          </radialGradient>
        </defs>

        {/* ═══════ BACKGROUND ELEMENTS ═══════ */}

        {/* Stars */}
        {[
          { cx: 150, cy: 120, r: 2 }, { cx: 350, cy: 80, r: 1.5 },
          { cx: 520, cy: 200, r: 1 }, { cx: 680, cy: 60, r: 2.5 },
          { cx: 850, cy: 150, r: 1 }, { cx: 1050, cy: 90, r: 1.8 },
          { cx: 1250, cy: 180, r: 1.2 }, { cx: 1400, cy: 70, r: 2 },
          { cx: 1600, cy: 130, r: 1.5 }, { cx: 1750, cy: 200, r: 1 },
          { cx: 200, cy: 350, r: 1 }, { cx: 1700, cy: 380, r: 1.5 },
          { cx: 100, cy: 600, r: 1.2 }, { cx: 1800, cy: 550, r: 1.8 },
          { cx: 300, cy: 900, r: 1 }, { cx: 1650, cy: 920, r: 1.3 },
        ].map((s, i) => (
          <circle
            key={i}
            cx={s.cx}
            cy={s.cy}
            r={s.r}
            fill="white"
            opacity={0.3 + (i % 4) * 0.15}
          />
        ))}

        {/* Floating hexagon */}
        <g transform={`translate(280, ${220 + float1})`} opacity="0.6">
          <polygon
            points="0,-30 26,-15 26,15 0,30 -26,15 -26,-15"
            fill="none"
            stroke="#0ABAB5"
            strokeWidth="2.5"
          />
        </g>

        {/* Floating triangle */}
        <g transform={`translate(1640, ${180 + float2})`} opacity="0.5">
          <polygon
            points="0,-22 19,11 -19,11"
            fill="none"
            stroke="#F9C846"
            strokeWidth="2.5"
          />
        </g>

        {/* Floating circle */}
        <g transform={`translate(200, ${680 + float3})`} opacity="0.4">
          <circle r="18" fill="none" stroke="#E85D75" strokeWidth="2.5" />
        </g>

        {/* Floating diamond */}
        <g transform={`translate(1700, ${520 + float1})`} opacity="0.45">
          <rect
            x="-12" y="-12" width="24" height="24"
            fill="none" stroke="#F9C846" strokeWidth="2"
            transform="rotate(45)"
          />
        </g>

        {/* Dot clusters */}
        {[
          { x: 1520, y: 280 }, { x: 1540, y: 295 }, { x: 1510, y: 305 },
          { x: 1535, y: 265 }, { x: 1555, y: 310 },
        ].map((d, i) => (
          <circle key={`dot-${i}`} cx={d.x} cy={d.y} r={2 + i * 0.5} fill="#0ABAB5" opacity="0.5" />
        ))}

        {/* ═══════ GROUND SHADOW ═══════ */}
        <ellipse cx="960" cy="880" rx="220" ry="18" fill="rgba(0,0,0,0.3)" />

        {/* ═══════ DESK ═══════ */}
        <g transform="translate(1180, 580)">
          {/* Desk legs */}
          <rect x="-80" y="55" width="12" height="240" rx="3" fill="#6B5740" />
          <rect x="80" y="55" width="12" height="240" rx="3" fill="#6B5740" />
          {/* Cross bar */}
          <rect x="-70" y="200" width="152" height="8" rx="3" fill="#5A4835" />
          {/* Desktop surface */}
          <rect x="-100" y="40" width="212" height="18" rx="5" fill="#9B7F5E" />
          <rect x="-100" y="40" width="212" height="10" rx="5" fill="#A88B68" />

          {/* Items on desk */}
          {/* Stack of papers */}
          <g transform="translate(-40, 20)">
            <rect x="-25" y="0" width="50" height="3" rx="1" fill="#F0EDE8" transform="rotate(-2)" />
            <rect x="-25" y="-4" width="50" height="3" rx="1" fill="#F5F2EE" transform="rotate(1)" />
            <rect x="-25" y="-8" width="50" height="3" rx="1" fill="#FAF8F5" transform="rotate(-1)" />
          </g>

          {/* Coffee mug */}
          <g transform="translate(50, -5)">
            <rect x="-12" y="10" width="24" height="32" rx="4" fill="#E8563A" />
            <rect x="-12" y="10" width="24" height="8" rx="4" fill="#F06A4D" />
            <ellipse cx="0" cy="10" rx="12" ry="4" fill="#D04A30" />
            {/* Handle */}
            <path d="M12,18 C22,18 22,35 12,35" fill="none" stroke="#E8563A" strokeWidth="4" />
            {/* Steam */}
            <path
              d={`M-3,${6 + float1 * 0.3} C-6,${-2 + float1 * 0.2} 2,${-6 + float1 * 0.3} -1,${-14 + float1 * 0.2}`}
              fill="none" stroke="rgba(255,255,255,0.15)" strokeWidth="2" strokeLinecap="round"
            />
            <path
              d={`M4,${7 + float2 * 0.2} C7,${-1 + float2 * 0.2} -1,${-5 + float2 * 0.2} 3,${-12 + float2 * 0.2}`}
              fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="1.5" strokeLinecap="round"
            />
          </g>

          {/* Desk lamp */}
          <g transform="translate(-70, -10)">
            <ellipse cx="0" cy="45" rx="16" ry="5" fill="#555" />
            <rect x="-3" y="-20" width="6" height="65" rx="3" fill="#666" />
            <path d="M-3,-20 C-3,-30 -25,-35 -30,-25" fill="none" stroke="#666" strokeWidth="5" strokeLinecap="round" />
            {/* Lamp head */}
            <ellipse cx="-35" cy="-22" rx="18" ry="10" fill="#F9C846" transform="rotate(-15, -35, -22)" />
            {/* Light cone */}
            <path d="M-48,-15 L-70,40 L-10,40 L-22,-15" fill="rgba(249,200,70,0.06)" />
          </g>
        </g>

        {/* ═══════ CHARACTER ═══════ */}
        <g transform={`translate(880, ${280 + breathe * 0.3})`} filter="url(#softShadow)">

          {/* ── LEGS ── */}
          <g transform={`translate(0, ${-breathe * 0.15})`}>
            {/* Left leg */}
            <path
              d="M-35,310 L-40,460 C-40,465 -38,468 -35,468 L-20,468 C-15,468 -12,465 -12,460 L-12,445 L-30,445 L-25,310 Z"
              fill="url(#pantsGrad)"
            />
            {/* Right leg */}
            <path
              d="M35,310 L40,460 C40,465 38,468 35,468 L20,468 C15,468 12,465 12,460 L12,445 L30,445 L25,310 Z"
              fill="url(#pantsGrad)"
            />
            {/* Left shoe */}
            <path
              d="M-45,458 C-48,458 -52,462 -52,468 C-52,478 -45,482 -30,482 L-8,482 C-2,482 0,478 0,474 C0,468 -5,462 -12,460 L-40,460 Z"
              fill="url(#shoeGrad)"
            />
            {/* Left shoe detail */}
            <path d="M-48,472 L-5,472" stroke="#7A3C11" strokeWidth="1.5" opacity="0.4" />
            {/* Right shoe */}
            <path
              d="M45,458 C48,458 52,462 52,468 C52,478 45,482 30,482 L8,482 C2,482 0,478 0,474 C0,468 5,462 12,460 L40,460 Z"
              fill="url(#shoeGrad)"
            />
            <path d="M48,472 L5,472" stroke="#7A3C11" strokeWidth="1.5" opacity="0.4" />
          </g>

          {/* ── BODY ── */}
          {/* Lab coat back shadow */}
          <path
            d="M-75,140 C-78,180 -80,250 -75,320 L75,320 C80,250 78,180 75,140 Z"
            fill="#C8C3BB"
          />

          {/* Shirt (under coat) */}
          <path
            d="M-50,135 C-52,170 -52,230 -50,280 L50,280 C52,230 52,170 50,135 Z"
            fill="url(#shirtGrad)"
          />

          {/* Lab coat - main body */}
          <path
            d="M-70,140 C-72,180 -78,280 -72,330 L-15,330 L-15,140 Z"
            fill="url(#coatGrad)"
          />
          <path
            d="M70,140 C72,180 78,280 72,330 L15,330 L15,140 Z"
            fill="url(#coatGrad)"
          />

          {/* Coat lapels */}
          <path
            d="M-15,135 L-35,175 L-15,165 Z"
            fill="#E8E4DD"
          />
          <path
            d="M15,135 L35,175 L15,165 Z"
            fill="#E8E4DD"
          />

          {/* Coat buttons */}
          <circle cx="-18" cy="200" r="3.5" fill="#D0CBC3" />
          <circle cx="-18" cy="230" r="3.5" fill="#D0CBC3" />
          <circle cx="-18" cy="260" r="3.5" fill="#D0CBC3" />

          {/* Coat pocket left */}
          <path
            d="M-55,245 L-55,275 C-55,278 -53,280 -50,280 L-30,280 C-27,280 -25,278 -25,275 L-25,245"
            fill="none" stroke="#C0BAB2" strokeWidth="2"
          />
          {/* Pen in pocket */}
          <rect x="-45" y="230" width="4" height="20" rx="2" fill="#2E86AB" />
          <circle cx="-43" cy="230" r="2.5" fill="#F9C846" />

          {/* Coat pocket right */}
          <path
            d="M55,245 L55,275 C55,278 53,280 50,280 L30,280 C27,280 25,278 25,275 L25,245"
            fill="none" stroke="#C0BAB2" strokeWidth="2"
          />

          {/* Tie */}
          <path
            d="M0,138 L-8,155 L0,280 L8,155 Z"
            fill="#C0392B"
          />
          <path d="M-8,155 L0,165 L8,155" fill="#A82E22" />

          {/* ── ARMS ── */}
          {/* Left arm (holding book) */}
          <g transform={`translate(0, ${breathe * 0.2})`}>
            {/* Upper arm */}
            <path
              d="M-65,145 C-85,165 -105,200 -110,240"
              fill="none" stroke="url(#coatGrad)" strokeWidth="38" strokeLinecap="round"
            />
            {/* Forearm */}
            <path
              d="M-110,240 C-108,260 -100,280 -90,290"
              fill="none" stroke="url(#coatGrad)" strokeWidth="34" strokeLinecap="round"
            />
            {/* Hand */}
            <g transform="translate(-88, 292)">
              <ellipse cx="0" cy="0" rx="16" ry="14" fill="url(#skinGrad)" />
              {/* Fingers */}
              <ellipse cx="-10" cy="10" rx="5" ry="7" fill="#F5D0A9" transform="rotate(15)" />
              <ellipse cx="0" cy="13" rx="5" ry="7" fill="#F5D0A9" />
              <ellipse cx="10" cy="10" rx="5" ry="7" fill="#F5D0A9" transform="rotate(-15)" />
              {/* Thumb */}
              <ellipse cx="14" cy="-3" rx="6" ry="5" fill="#F5D0A9" transform="rotate(-30)" />
            </g>

            {/* Book in hand */}
            <g transform="translate(-95, 255) rotate(12)">
              <rect x="-22" y="-32" width="44" height="58" rx="3" fill="url(#bookGrad)" />
              <rect x="-18" y="-32" width="4" height="58" fill="#962D22" />
              {/* Book pages side */}
              <rect x="-14" y="-29" width="32" height="52" rx="1" fill="#F5F0E6" />
              {/* Title lines */}
              <rect x="-8" y="-20" width="22" height="2.5" rx="1" fill="#FFD700" opacity="0.8" />
              <rect x="-4" y="-14" width="16" height="2" rx="1" fill="#FFD700" opacity="0.5" />
              {/* Cover decoration */}
              <circle cx="5" cy="5" r="8" fill="none" stroke="#FFD700" strokeWidth="1.5" opacity="0.6" />
            </g>
          </g>

          {/* Right arm (relaxed) */}
          <g transform={`translate(0, ${breathe * 0.15})`}>
            <path
              d="M65,145 C85,170 95,220 90,270"
              fill="none" stroke="url(#coatGrad)" strokeWidth="38" strokeLinecap="round"
            />
            <path
              d="M90,270 C88,290 82,305 78,315"
              fill="none" stroke="url(#coatGrad)" strokeWidth="34" strokeLinecap="round"
            />
            {/* Hand */}
            <g transform="translate(76, 318)">
              <ellipse cx="0" cy="0" rx="15" ry="13" fill="url(#skinGrad)" />
              <ellipse cx="-8" cy="10" rx="4.5" ry="6" fill="#F5D0A9" transform="rotate(10)" />
              <ellipse cx="0" cy="12" rx="4.5" ry="6" fill="#F5D0A9" />
              <ellipse cx="8" cy="10" rx="4.5" ry="6" fill="#F5D0A9" transform="rotate(-10)" />
              <ellipse cx="13" cy="-2" rx="5.5" ry="4.5" fill="#F5D0A9" transform="rotate(-25)" />
            </g>
          </g>

          {/* ── NECK ── */}
          <rect x="-14" y="110" width="28" height="32" rx="8" fill="url(#skinGrad)" />

          {/* ── HEAD ── */}
          <g transform={`translate(0, ${breathe * 0.5})`}>
            {/* Head shape */}
            <ellipse cx="0" cy="55" rx="62" ry="68" fill="url(#skinGrad)" />

            {/* Ears */}
            <ellipse cx="-60" cy="60" rx="12" ry="16" fill="#E8B88A" />
            <ellipse cx="-60" cy="60" rx="7" ry="10" fill="#D4A06A" />
            <ellipse cx="60" cy="60" rx="12" ry="16" fill="#E8B88A" />
            <ellipse cx="60" cy="60" rx="7" ry="10" fill="#D4A06A" />

            {/* Hair - back volume */}
            <path
              d="M-58,30 C-60,5 -45,-18 -20,-28 C-5,-33 5,-33 20,-28 C45,-18 60,5 58,30 C60,15 50,-5 30,-18 C10,-28 -10,-28 -30,-18 C-50,-5 -60,15 -58,30 Z"
              fill="url(#hairGrad)"
            />

            {/* Hair - top */}
            <path
              d="M-50,25 C-52,0 -38,-22 -10,-32 C5,-36 15,-35 30,-28 C50,-18 58,5 55,30 L55,15 C55,0 48,-12 30,-22 C15,-30 -5,-30 -20,-25 C-40,-16 -48,0 -50,25 Z"
              fill="#3D2B1F"
            />

            {/* Hair highlights */}
            <path
              d="M-30,-22 C-15,-28 5,-28 20,-22"
              fill="none" stroke="#5A4030" strokeWidth="3" opacity="0.5"
            />
            <path
              d="M-20,-18 C-5,-24 10,-23 25,-16"
              fill="none" stroke="#5A4030" strokeWidth="2" opacity="0.3"
            />

            {/* Hair side strands */}
            <path d="M-55,25 C-62,35 -65,50 -60,55" fill="none" stroke="#3D2B1F" strokeWidth="8" strokeLinecap="round" />
            <path d="M55,25 C62,35 65,50 60,55" fill="none" stroke="#3D2B1F" strokeWidth="8" strokeLinecap="round" />

            {/* Eyebrows */}
            <path d="M-34,38 C-28,33 -18,33 -12,36" fill="none" stroke="#3D2B1F" strokeWidth="3.5" strokeLinecap="round" />
            <path d="M34,38 C28,33 18,33 12,36" fill="none" stroke="#3D2B1F" strokeWidth="3.5" strokeLinecap="round" />

            {/* Glasses */}
            {/* Left lens */}
            <circle cx="-23" cy="52" r="20" fill="url(#lensGrad)" stroke="#888" strokeWidth="2.5" />
            {/* Right lens */}
            <circle cx="23" cy="52" r="20" fill="url(#lensGrad)" stroke="#888" strokeWidth="2.5" />
            {/* Bridge */}
            <path d="M-3,52 C-1,48 1,48 3,52" fill="none" stroke="#888" strokeWidth="2.5" />
            {/* Temples */}
            <path d="M-43,50 L-60,48" stroke="#888" strokeWidth="2.5" strokeLinecap="round" />
            <path d="M43,50 L60,48" stroke="#888" strokeWidth="2.5" strokeLinecap="round" />
            {/* Lens reflection */}
            <path d="M-30,43 C-28,40 -24,40 -22,42" fill="none" stroke="rgba(255,255,255,0.3)" strokeWidth="1.5" />
            <path d="M16,43 C18,40 22,40 24,42" fill="none" stroke="rgba(255,255,255,0.3)" strokeWidth="1.5" />

            {/* Eyes */}
            {/* Left eye */}
            <g transform={`translate(-23, 52) scale(1, ${blink})`}>
              <ellipse cx="0" cy="0" rx="10" ry="11" fill="white" />
              <circle cx="2" cy="1" r="6.5" fill="#2C1810" />
              <circle cx="2" cy="1" r="4" fill="#1A0E08" />
              <circle cx="4" cy="-2" r="2.5" fill="white" opacity="0.9" />
              <circle cx="0" cy="3" r="1.2" fill="white" opacity="0.4" />
            </g>
            {/* Right eye */}
            <g transform={`translate(23, 52) scale(1, ${blink})`}>
              <ellipse cx="0" cy="0" rx="10" ry="11" fill="white" />
              <circle cx="2" cy="1" r="6.5" fill="#2C1810" />
              <circle cx="2" cy="1" r="4" fill="#1A0E08" />
              <circle cx="4" cy="-2" r="2.5" fill="white" opacity="0.9" />
              <circle cx="0" cy="3" r="1.2" fill="white" opacity="0.4" />
            </g>

            {/* Nose */}
            <path
              d="M0,62 C-3,68 -8,72 -6,74 C-4,76 4,76 6,74 C8,72 3,68 0,62 Z"
              fill="#D4A06A" opacity="0.7"
            />

            {/* Mouth */}
            <g transform="translate(0, 84)">
              {/* Upper lip */}
              <path
                d="M-12,0 C-8,-4 -3,-3 0,-1 C3,-3 8,-4 12,0"
                fill="none" stroke="#C07A5C" strokeWidth="2.5" strokeLinecap="round"
              />
              {/* Smile */}
              <path
                d="M-10,1 C-6,6 6,6 10,1"
                fill="#B86B50" stroke="#C07A5C" strokeWidth="1.5"
              />
              {/* Teeth hint */}
              <path d="M-6,1 L6,1" stroke="white" strokeWidth="2" opacity="0.5" />
            </g>

            {/* Cheek blush */}
            <ellipse cx="-35" cy="72" rx="10" ry="6" fill="#E8A090" opacity="0.25" />
            <ellipse cx="35" cy="72" rx="10" ry="6" fill="#E8A090" opacity="0.25" />
          </g>
        </g>

        {/* ═══════ FLOOR LINE ═══════ */}
        <line x1="400" y1="880" x2="1500" y2="880" stroke="rgba(255,255,255,0.05)" strokeWidth="1" />

        {/* ═══════ TITLE ═══════ */}
        <g opacity={titleOpacity}>
          <text
            x="960" y="1010"
            textAnchor="middle"
            fontFamily="'Noto Sans KR', sans-serif"
            fontSize="28"
            fontWeight="700"
            fill="#F9C846"
            letterSpacing="4"
          >
            SVG CHARACTER TEST
          </text>
        </g>
      </svg>
    </AbsoluteFill>
  );
};
