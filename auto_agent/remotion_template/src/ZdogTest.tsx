import React, { useRef, useEffect } from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import Zdog from "zdog";

const TAU = Zdog.TAU;

// ── Kurzgesagt-inspired color palette ──
const COLORS = {
  bg: "#0B1428",
  bgGlow: "#162040",
  skin: "#F5C890",
  skinShadow: "#D4A06A",
  hair: "#3D2B1F",
  eyeWhite: "#FFFFFF",
  pupil: "#1A1A2E",
  mouth: "#C07A5C",
  shirt: "#2E86AB",
  shirtShadow: "#1B6B8A",
  pants: "#2C3E50",
  shoes: "#E8563A",
  bookCover: "#E8563A",
  bookPages: "#F5F0E6",
  deskTop: "#8B6F4E",
  deskLeg: "#6B5740",
  lampPost: "#555555",
  lampHead: "#F9C846",
  lampGlow: "rgba(249, 200, 70, 0.08)",
  scrollPaper: "#F0E6D0",
  scrollHandle: "#8B6F4E",
  glasses: "#C0C0C0",
  glassFill: "rgba(200, 220, 255, 0.3)",
  accent1: "#F9C846",
  accent2: "#0ABAB5",
  accent3: "#E85D75",
  particle: "#FFFFFF",
};

function buildCharacter(illo: Zdog.Illustration, breathe: number) {
  const character = new Zdog.Anchor({
    addTo: illo,
    translate: { x: 0, y: 30 },
  });

  // ═══ HEAD ═══
  const headGroup = new Zdog.Group({
    addTo: character,
    translate: { y: -155 + breathe * 0.4 },
  });

  // Head base
  new Zdog.Shape({
    addTo: headGroup,
    stroke: 100,
    color: COLORS.skin,
  });

  // Head shadow (chin area)
  new Zdog.Ellipse({
    addTo: headGroup,
    diameter: 60,
    stroke: 12,
    color: COLORS.skinShadow,
    translate: { y: 20, z: -2 },
    fill: true,
  });

  // Hair - main volume
  new Zdog.Hemisphere({
    addTo: headGroup,
    diameter: 108,
    stroke: false,
    color: COLORS.hair,
    translate: { y: -18 },
    rotate: { x: -TAU / 4 },
  });

  // Hair - side left
  new Zdog.Shape({
    addTo: headGroup,
    path: [
      { x: -48, y: -30 },
      { arc: [
        { x: -56, y: -5 },
        { x: -50, y: 8 },
      ]},
    ],
    stroke: 18,
    color: COLORS.hair,
  });

  // Hair - side right
  new Zdog.Shape({
    addTo: headGroup,
    path: [
      { x: 48, y: -30 },
      { arc: [
        { x: 56, y: -5 },
        { x: 50, y: 8 },
      ]},
    ],
    stroke: 18,
    color: COLORS.hair,
  });

  // ── Glasses ──
  // Left frame
  new Zdog.Ellipse({
    addTo: headGroup,
    diameter: 30,
    stroke: 3,
    color: COLORS.glasses,
    translate: { x: -18, y: -4, z: 46 },
  });
  // Right frame
  new Zdog.Ellipse({
    addTo: headGroup,
    diameter: 30,
    stroke: 3,
    color: COLORS.glasses,
    translate: { x: 18, y: -4, z: 46 },
  });
  // Bridge
  new Zdog.Shape({
    addTo: headGroup,
    path: [
      { x: -3, y: -4, z: 48 },
      { x: 3, y: -4, z: 48 },
    ],
    stroke: 3,
    color: COLORS.glasses,
  });
  // Temple left
  new Zdog.Shape({
    addTo: headGroup,
    path: [
      { x: -33, y: -4, z: 46 },
      { x: -46, y: -6, z: 20 },
    ],
    stroke: 2.5,
    color: COLORS.glasses,
  });
  // Temple right
  new Zdog.Shape({
    addTo: headGroup,
    path: [
      { x: 33, y: -4, z: 46 },
      { x: 46, y: -6, z: 20 },
    ],
    stroke: 2.5,
    color: COLORS.glasses,
  });

  // ── Eyes ──
  // Left eye white
  new Zdog.Shape({
    addTo: headGroup,
    stroke: 18,
    color: COLORS.eyeWhite,
    translate: { x: -18, y: -4, z: 44 },
  });
  // Left pupil
  new Zdog.Shape({
    addTo: headGroup,
    stroke: 9,
    color: COLORS.pupil,
    translate: { x: -16, y: -3, z: 48 },
  });
  // Left pupil highlight
  new Zdog.Shape({
    addTo: headGroup,
    stroke: 3,
    color: "#FFFFFF",
    translate: { x: -14, y: -6, z: 50 },
  });
  // Right eye white
  new Zdog.Shape({
    addTo: headGroup,
    stroke: 18,
    color: COLORS.eyeWhite,
    translate: { x: 18, y: -4, z: 44 },
  });
  // Right pupil
  new Zdog.Shape({
    addTo: headGroup,
    stroke: 9,
    color: COLORS.pupil,
    translate: { x: 20, y: -3, z: 48 },
  });
  // Right pupil highlight
  new Zdog.Shape({
    addTo: headGroup,
    stroke: 3,
    color: "#FFFFFF",
    translate: { x: 22, y: -6, z: 50 },
  });

  // ── Nose ──
  new Zdog.Shape({
    addTo: headGroup,
    stroke: 8,
    color: COLORS.skinShadow,
    translate: { y: 6, z: 48 },
  });

  // ── Mouth (gentle smile) ──
  new Zdog.Ellipse({
    addTo: headGroup,
    diameter: 14,
    quarters: 2,
    stroke: 3.5,
    color: COLORS.mouth,
    translate: { y: 18, z: 44 },
    rotate: { z: TAU / 4 },
  });

  // ── Ears ──
  new Zdog.Shape({
    addTo: headGroup,
    stroke: 20,
    color: COLORS.skin,
    translate: { x: -48, y: 0, z: 0 },
  });
  new Zdog.Shape({
    addTo: headGroup,
    stroke: 10,
    color: COLORS.skinShadow,
    translate: { x: -48, y: 0, z: 0 },
  });
  new Zdog.Shape({
    addTo: headGroup,
    stroke: 20,
    color: COLORS.skin,
    translate: { x: 48, y: 0, z: 0 },
  });
  new Zdog.Shape({
    addTo: headGroup,
    stroke: 10,
    color: COLORS.skinShadow,
    translate: { x: 48, y: 0, z: 0 },
  });

  // ═══ NECK ═══
  new Zdog.Shape({
    addTo: character,
    path: [
      { y: -110 },
      { y: -95 },
    ],
    stroke: 24,
    color: COLORS.skin,
  });

  // ═══ BODY ═══
  const bodyGroup = new Zdog.Group({
    addTo: character,
    translate: { y: -55 + breathe * 0.2 },
  });

  // Torso
  new Zdog.RoundedRect({
    addTo: bodyGroup,
    width: 80,
    height: 90,
    cornerRadius: 18,
    stroke: 30,
    color: COLORS.shirt,
    fill: true,
  });

  // Collar
  new Zdog.Shape({
    addTo: bodyGroup,
    path: [
      { x: -12, y: -42, z: 14 },
      { x: 0, y: -28, z: 16 },
      { x: 12, y: -42, z: 14 },
    ],
    stroke: 4,
    color: COLORS.shirtShadow,
    closed: false,
  });

  // Pocket
  new Zdog.RoundedRect({
    addTo: bodyGroup,
    width: 18,
    height: 16,
    cornerRadius: 3,
    stroke: 2,
    color: COLORS.shirtShadow,
    translate: { x: -20, y: -8, z: 16 },
  });

  // Pocket pen
  new Zdog.Shape({
    addTo: bodyGroup,
    path: [
      { x: -18, y: -18, z: 17 },
      { x: -16, y: -8, z: 17 },
    ],
    stroke: 3,
    color: COLORS.accent1,
  });

  // ═══ ARMS ═══
  // Left arm - raised, holding a book
  const leftArmGroup = new Zdog.Anchor({
    addTo: bodyGroup,
    translate: { x: -55, y: -25 },
  });
  new Zdog.Shape({
    addTo: leftArmGroup,
    path: [
      { x: 0, y: 0 },
      { arc: [
        { x: -15, y: 30 },
        { x: -25, y: 50 },
      ]},
    ],
    stroke: 26,
    color: COLORS.shirt,
  });
  // Left hand
  new Zdog.Shape({
    addTo: leftArmGroup,
    stroke: 22,
    color: COLORS.skin,
    translate: { x: -25, y: 52 },
  });

  // Book in left hand
  const bookGroup = new Zdog.Anchor({
    addTo: leftArmGroup,
    translate: { x: -28, y: 44 },
    rotate: { z: 0.2 },
  });
  new Zdog.Box({
    addTo: bookGroup,
    width: 36,
    height: 48,
    depth: 8,
    color: COLORS.bookCover,
    frontFace: COLORS.bookCover,
    rearFace: COLORS.bookCover,
    leftFace: COLORS.bookPages,
    rightFace: COLORS.bookPages,
    topFace: COLORS.bookPages,
    bottomFace: COLORS.bookPages,
    stroke: false,
  });
  // Book title line 1
  new Zdog.Shape({
    addTo: bookGroup,
    path: [
      { x: -10, y: -12, z: 5 },
      { x: 10, y: -12, z: 5 },
    ],
    stroke: 2,
    color: COLORS.accent1,
  });
  // Book title line 2
  new Zdog.Shape({
    addTo: bookGroup,
    path: [
      { x: -8, y: -6, z: 5 },
      { x: 8, y: -6, z: 5 },
    ],
    stroke: 2,
    color: COLORS.accent1,
  });

  // Right arm - relaxed
  new Zdog.Shape({
    addTo: bodyGroup,
    path: [
      { x: 55, y: -25 },
      { arc: [
        { x: 78, y: 10 },
        { x: 72, y: 45 },
      ]},
    ],
    stroke: 26,
    color: COLORS.shirt,
  });
  // Right hand
  new Zdog.Shape({
    addTo: bodyGroup,
    stroke: 22,
    color: COLORS.skin,
    translate: { x: 72, y: 47 },
  });

  // ═══ LEGS ═══
  // Left leg
  new Zdog.Shape({
    addTo: character,
    path: [
      { x: -20, y: -8 },
      { x: -24, y: 55 },
    ],
    stroke: 28,
    color: COLORS.pants,
  });
  // Left shoe
  new Zdog.RoundedRect({
    addTo: character,
    width: 34,
    height: 14,
    cornerRadius: 7,
    stroke: 14,
    color: COLORS.shoes,
    fill: true,
    translate: { x: -24, y: 62, z: 8 },
  });
  // Shoe sole
  new Zdog.RoundedRect({
    addTo: character,
    width: 36,
    height: 15,
    cornerRadius: 7,
    stroke: 4,
    color: "#333",
    fill: true,
    translate: { x: -24, y: 68, z: 8 },
  });

  // Right leg
  new Zdog.Shape({
    addTo: character,
    path: [
      { x: 20, y: -8 },
      { x: 24, y: 55 },
    ],
    stroke: 28,
    color: COLORS.pants,
  });
  // Right shoe
  new Zdog.RoundedRect({
    addTo: character,
    width: 34,
    height: 14,
    cornerRadius: 7,
    stroke: 14,
    color: COLORS.shoes,
    fill: true,
    translate: { x: 24, y: 62, z: 8 },
  });
  // Shoe sole
  new Zdog.RoundedRect({
    addTo: character,
    width: 36,
    height: 15,
    cornerRadius: 7,
    stroke: 4,
    color: "#333",
    fill: true,
    translate: { x: 24, y: 68, z: 8 },
  });

  return character;
}

function buildDesk(illo: Zdog.Illustration) {
  const desk = new Zdog.Anchor({
    addTo: illo,
    translate: { x: 180, y: 40 },
  });

  // Desktop surface
  new Zdog.Box({
    addTo: desk,
    width: 120,
    height: 8,
    depth: 60,
    color: COLORS.deskTop,
    frontFace: COLORS.deskTop,
    topFace: "#9B7F5E",
    stroke: false,
  });

  // Desk legs
  [-40, 40].forEach((x) => {
    new Zdog.Shape({
      addTo: desk,
      path: [
        { x, y: 4 },
        { x, y: 60 },
      ],
      stroke: 10,
      color: COLORS.deskLeg,
    });
  });

  // Lamp on desk
  const lamp = new Zdog.Anchor({
    addTo: desk,
    translate: { x: 30, y: -8 },
  });
  // Lamp base
  new Zdog.Ellipse({
    addTo: lamp,
    diameter: 20,
    stroke: 4,
    color: COLORS.lampPost,
    fill: true,
    rotate: { x: TAU / 4 },
  });
  // Lamp post
  new Zdog.Shape({
    addTo: lamp,
    path: [
      { y: 0 },
      { y: -45 },
      { arc: [
        { x: 0, y: -55 },
        { x: -15, y: -55 },
      ]},
    ],
    stroke: 5,
    color: COLORS.lampPost,
  });
  // Lamp head
  new Zdog.Cone({
    addTo: lamp,
    diameter: 30,
    length: 18,
    stroke: false,
    color: COLORS.lampHead,
    translate: { x: -15, y: -55 },
    rotate: { x: TAU / 4 },
  });

  // Scroll on desk
  const scroll = new Zdog.Anchor({
    addTo: desk,
    translate: { x: -15, y: -6, z: 5 },
    rotate: { y: 0.3 },
  });
  new Zdog.Rect({
    addTo: scroll,
    width: 40,
    height: 50,
    stroke: 3,
    color: COLORS.scrollPaper,
    fill: true,
    rotate: { x: TAU / 4 },
  });
  // Scroll text lines
  for (let i = 0; i < 4; i++) {
    new Zdog.Shape({
      addTo: scroll,
      path: [
        { x: -14, z: -18 + i * 10 },
        { x: 14, z: -18 + i * 10 },
      ],
      stroke: 2,
      color: "#AAA099",
      translate: { y: -4 },
      rotate: { x: TAU / 4 },
    });
  }

  return desk;
}

function buildBackgroundElements(illo: Zdog.Illustration, frame: number) {
  // Floating geometric elements (Kurzgesagt-style)

  // Floating hexagon
  const hex1 = new Zdog.Anchor({
    addTo: illo,
    translate: { x: -280, y: -120 },
    rotate: { z: frame * 0.002 },
  });
  new Zdog.Polygon({
    addTo: hex1,
    radius: 25,
    sides: 6,
    stroke: 3,
    color: COLORS.accent2,
    fill: false,
  });

  // Floating triangle
  const tri1 = new Zdog.Anchor({
    addTo: illo,
    translate: { x: 300, y: -140 },
    rotate: { z: -frame * 0.003 },
  });
  new Zdog.Polygon({
    addTo: tri1,
    radius: 18,
    sides: 3,
    stroke: 3,
    color: COLORS.accent1,
    fill: false,
  });

  // Floating circle
  new Zdog.Ellipse({
    addTo: illo,
    diameter: 30,
    stroke: 2.5,
    color: COLORS.accent3,
    translate: { x: -320, y: 80 },
  });

  // Small dots cluster
  const dots = [
    { x: 260, y: -60 },
    { x: 275, y: -50 },
    { x: 250, y: -45 },
    { x: 270, y: -70 },
    { x: -250, y: 140 },
    { x: -265, y: 130 },
    { x: -240, y: 150 },
  ];
  dots.forEach((pos, i) => {
    new Zdog.Shape({
      addTo: illo,
      stroke: 4 + (i % 4) * 1.5,
      color: COLORS.accent2,
      translate: { ...pos, z: -20 },
    });
  });

  // Diamond shape
  const diamond = new Zdog.Anchor({
    addTo: illo,
    translate: { x: -200, y: -180 },
    rotate: { z: TAU / 8 + frame * 0.001 },
  });
  new Zdog.Rect({
    addTo: diamond,
    width: 16,
    height: 16,
    stroke: 2.5,
    color: COLORS.accent1,
  });

  // Plus sign
  const plus = new Zdog.Anchor({
    addTo: illo,
    translate: { x: 220, y: 100 },
  });
  new Zdog.Shape({
    addTo: plus,
    path: [{ x: -8, y: 0 }, { x: 8, y: 0 }],
    stroke: 3,
    color: COLORS.accent3,
  });
  new Zdog.Shape({
    addTo: plus,
    path: [{ x: 0, y: -8 }, { x: 0, y: 8 }],
    stroke: 3,
    color: COLORS.accent3,
  });
}

export const ZdogTest: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const frame = useCurrentFrame();
  const { durationInFrames, fps } = useVideoConfig();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Subtle breathing
    const breathe = Math.sin((frame / fps) * Math.PI * 2) * 1.2;

    // Fixed camera, no rotation
    const illo = new Zdog.Illustration({
      element: canvas,
      zoom: 3,
      centered: true,
    });

    buildCharacter(illo, breathe);
    buildDesk(illo);
    buildBackgroundElements(illo, 0);

    illo.updateRenderGraph();
  }, [frame, fps]);

  // Star particles (CSS-based for background depth)
  const stars = React.useMemo(() => {
    return Array.from({ length: 60 }).map((_, i) => ({
      x: (i * 137.508) % 100,
      y: (i * 97.31) % 100,
      size: 1 + (i % 4) * 1.2,
      opacity: 0.08 + (i % 5) * 0.06,
      delay: i * 0.3,
    }));
  }, []);

  const bgGlowOpacity = interpolate(frame, [0, durationInFrames / 2, durationInFrames], [0.3, 0.5, 0.3], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: COLORS.bg,
        overflow: "hidden",
      }}
    >
      {/* Background radial glow */}
      <div
        style={{
          position: "absolute",
          width: "120%",
          height: "120%",
          left: "-10%",
          top: "-10%",
          background: `radial-gradient(ellipse at 50% 45%, ${COLORS.bgGlow} 0%, transparent 70%)`,
          opacity: bgGlowOpacity,
        }}
      />

      {/* Star particles */}
      {stars.map((star, i) => {
        const twinkle = interpolate(
          frame,
          [0, 15 + (i % 20) * 3, 30 + (i % 20) * 3],
          [star.opacity, star.opacity * 1.8, star.opacity],
          { extrapolateRight: "clamp" },
        );
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: `${star.x}%`,
              top: `${star.y}%`,
              width: star.size,
              height: star.size,
              borderRadius: "50%",
              backgroundColor: COLORS.particle,
              opacity: twinkle,
            }}
          />
        );
      })}

      {/* Ground gradient */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          width: "100%",
          height: "25%",
          background: "linear-gradient(to top, rgba(15,25,50,0.9) 0%, transparent 100%)",
        }}
      />

      {/* Zdog canvas */}
      <canvas
        ref={canvasRef}
        width={1920}
        height={1080}
        style={{
          width: "100%",
          height: "100%",
        }}
      />

      {/* Title overlay */}
      <div
        style={{
          position: "absolute",
          bottom: 60,
          left: 0,
          right: 0,
          textAlign: "center",
          fontFamily: "'Noto Sans KR', sans-serif",
          fontSize: 28,
          fontWeight: 700,
          color: COLORS.accent1,
          letterSpacing: 4,
          opacity: interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" }),
        }}
      >
        ZDOG CHARACTER TEST
      </div>
    </AbsoluteFill>
  );
};
