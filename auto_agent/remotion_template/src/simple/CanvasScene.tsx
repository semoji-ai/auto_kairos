/**
 * CanvasScene — 의회식 크론의 자유 캔버스 JSON을 Remotion으로 렌더링
 *
 * council_decisions.json의 background + layers를 실제 프레임으로 변환
 */
import React from "react";
import {
  AbsoluteFill,
  Img,
  staticFile,
  useCurrentFrame,
  interpolate,
  Easing,
} from "remotion";

/* ── Types ── */
interface CanvasData {
  background?: any;
  layers?: CanvasLayer[];
  imageAssets?: any[];
  audioDirection?: string;
}

interface CanvasLayer {
  type: string;
  props?: Record<string, any>;
  position?: { x: string | number; y: string | number; anchor?: string };
  size?: { width: string | number; height: string | number };
  animation?: {
    enter?: AnimConfig;
    exit?: AnimConfig;
    emphasis?: AnimConfig;
    effect?: AnimConfig;
  };
  /** 레이어 표시 시작 프레임 (기본: enter.delay ?? 0) */
  showFrom?: number;
  /** 레이어 표시 종료 프레임 (기본: 씬 끝까지) — exit 애니메이션은 이 시점 전에 시작 */
  showUntil?: number;
  zIndex?: number;
  opacity?: number;
}

interface AnimConfig {
  type: string;
  duration?: number;
  delay?: number;
  easing?: string;
  from?: number;
  to?: number;
  /** exit의 시작 프레임 (showUntil 대신 직접 지정) */
  startFrame?: number;
}

/* ── Main Component ── */
interface Props {
  canvas: CanvasData;
  durationInFrames: number;
}

export const CanvasScene: React.FC<Props> = ({ canvas, durationInFrames }) => {
  if (!canvas) return null;

  return (
    <AbsoluteFill>
      {/* Background */}
      <CanvasBackground bg={canvas.background} durationInFrames={durationInFrames} />

      {/* Layers */}
      {(canvas.layers || []).map((layer, i) => (
        <CanvasLayerRenderer key={i} layer={layer} index={i} durationInFrames={durationInFrames} />
      ))}
    </AbsoluteFill>
  );
};

/* ── Background Renderer ── */
const CanvasBackground: React.FC<{ bg: any; durationInFrames: number }> = ({ bg, durationInFrames }) => {
  const frame = useCurrentFrame();
  if (!bg) return <AbsoluteFill style={{ backgroundColor: "#0a0a0a" }} />;

  const type = bg.type || "solid";

  if (type === "solid") {
    return <AbsoluteFill style={{ backgroundColor: bg.color || "#000000" }} />;
  }

  if (type === "gradient") {
    const angle = bg.gradientAngle ?? 180;
    const from = bg.gradientFrom || "#000";
    const to = bg.gradientTo || "#111";
    return (
      <AbsoluteFill
        style={{ background: `linear-gradient(${angle}deg, ${from}, ${to})` }}
      />
    );
  }

  if (type === "image" || type === "blur_image") {
    // 이미지 배경 — src가 있으면 실제 이미지 렌더링
    const opacity = bg.opacity ?? 0.4;
    const blur = type === "blur_image" ? (bg.blurAmount ?? bg.blur ?? 10) : 0;
    const overlayColor = bg.overlayColor;
    const overlayOpacity = bg.overlayOpacity ?? 0.5;

    // src 경로 해석: 절대경로면 그대로, 상대경로면 staticFile
    const imgSrc = bg.src
      ? (bg.src.startsWith("/") || bg.src.startsWith("http") ? bg.src : staticFile(bg.src))
      : null;

    return (
      <AbsoluteFill style={{ backgroundColor: "#0a0a0a" }}>
        {imgSrc && (
          <AbsoluteFill style={{ opacity }}>
            <Img
              src={imgSrc}
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
                filter: blur > 0 ? `blur(${blur}px)` : undefined,
              }}
            />
          </AbsoluteFill>
        )}
        {overlayColor && (
          <AbsoluteFill
            style={{
              backgroundColor: overlayColor,
              opacity: overlayOpacity,
            }}
          />
        )}
      </AbsoluteFill>
    );
  }

  return <AbsoluteFill style={{ backgroundColor: "#0a0a0a" }} />;
};

/* ── Layer Renderer ── */
const CanvasLayerRenderer: React.FC<{
  layer: CanvasLayer;
  index: number;
  durationInFrames: number;
}> = ({ layer, index, durationInFrames }) => {
  const frame = useCurrentFrame();
  const enter = layer.animation?.enter;
  const delay = enter?.delay ?? (index * 8);
  const duration = enter?.duration ?? 20;
  const animType = enter?.type ?? "fade_in";

  // Visible 구간 — showFrom/showUntil 또는 enter.delay + exit로 결정
  const showFrom = layer.showFrom ?? delay;
  const exit = layer.animation?.exit;
  const exitDur = exit?.duration ?? 15;
  const exitStartFrame = exit?.startFrame;
  const showUntil = layer.showUntil ?? (exitStartFrame != null ? exitStartFrame + exitDur : durationInFrames);

  // 범위 밖이면 렌더링 안 함
  if (frame < showFrom || frame > showUntil + 5) return null;

  // Position
  const pos = layer.position || { x: "50%", y: "50%" };
  const anchor = pos.anchor || "top-left";
  const size = layer.size || {};

  // Enter animation: opacity
  const enterEnd = delay + Math.min(duration, 15);
  const enterOpacity = interpolate(
    frame,
    [delay, enterEnd],
    [0, layer.opacity ?? 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  // Exit animation: opacity
  let exitOpacity = 1;
  if (exit) {
    const exitStart = exitStartFrame ?? (showUntil - exitDur);
    if (exit.type === "fade_out" || !exit.type) {
      exitOpacity = interpolate(frame, [exitStart, exitStart + exitDur], [1, 0], {
        extrapolateLeft: "clamp", extrapolateRight: "clamp",
      });
    } else if (exit.type === "scale_down") {
      exitOpacity = interpolate(frame, [exitStart, exitStart + exitDur], [1, 0], {
        extrapolateLeft: "clamp", extrapolateRight: "clamp",
      });
    }
  }

  const opacity = enterOpacity * exitOpacity;

  // Animation transforms
  let transform = "";
  let blurValue = 0;

  if (animType === "fade_in") {
    // just opacity
  } else if (animType === "slide_up") {
    const y = interpolate(frame, [delay, delay + duration], [40, 0], {
      extrapolateLeft: "clamp", extrapolateRight: "clamp",
      easing: Easing.out(Easing.cubic),
    });
    transform = `translateY(${y}px)`;
  } else if (animType === "slide_down") {
    const y = interpolate(frame, [delay, delay + duration], [-40, 0], {
      extrapolateLeft: "clamp", extrapolateRight: "clamp",
      easing: Easing.out(Easing.cubic),
    });
    transform = `translateY(${y}px)`;
  } else if (animType === "slide_left") {
    const x = interpolate(frame, [delay, delay + duration], [60, 0], {
      extrapolateLeft: "clamp", extrapolateRight: "clamp",
      easing: Easing.out(Easing.cubic),
    });
    transform = `translateX(${x}px)`;
  } else if (animType === "slide_right") {
    const x = interpolate(frame, [delay, delay + duration], [-60, 0], {
      extrapolateLeft: "clamp", extrapolateRight: "clamp",
      easing: Easing.out(Easing.cubic),
    });
    transform = `translateX(${x}px)`;
  } else if (animType === "scale_up" || animType === "pop") {
    const s = interpolate(frame, [delay, delay + duration], [0.3, 1], {
      extrapolateLeft: "clamp", extrapolateRight: "clamp",
      easing: Easing.out(Easing.back(1.5)),
    });
    transform = `scale(${s})`;
  } else if (animType === "blur_in") {
    blurValue = interpolate(frame, [delay, delay + duration], [20, 0], {
      extrapolateLeft: "clamp", extrapolateRight: "clamp",
    });
  } else if (animType === "ken_burns") {
    const s = interpolate(frame, [0, durationInFrames], [1, 1.15], {
      extrapolateLeft: "clamp", extrapolateRight: "clamp",
    });
    transform = `scale(${s})`;
  }

  // Exit transform (scale down 등)
  if (exit?.type === "scale_down") {
    const exitStart = exitStartFrame ?? (showUntil - exitDur);
    const s = interpolate(frame, [exitStart, exitStart + exitDur], [1, 0.5], {
      extrapolateLeft: "clamp", extrapolateRight: "clamp",
    });
    transform += ` scale(${s})`;
  }

  // Position style
  const posStyle: React.CSSProperties = {
    position: "absolute",
    zIndex: layer.zIndex ?? (10 + index),
  };

  // Handle anchor point
  if (anchor === "center") {
    posStyle.left = typeof pos.x === "string" ? pos.x : `${pos.x}px`;
    posStyle.top = typeof pos.y === "string" ? pos.y : `${pos.y}px`;
    posStyle.transform = `translate(-50%, -50%) ${transform}`;
  } else {
    posStyle.left = typeof pos.x === "string" ? pos.x : `${pos.x}px`;
    posStyle.top = typeof pos.y === "string" ? pos.y : `${pos.y}px`;
    if (transform) posStyle.transform = transform;
  }

  if (size.width) posStyle.width = typeof size.width === "string" ? size.width : `${size.width}px`;
  if (size.height) posStyle.height = typeof size.height === "string" ? size.height : `${size.height}px`;

  posStyle.opacity = opacity;
  if (blurValue > 0) posStyle.filter = `blur(${blurValue}px)`;

  return (
    <div style={posStyle}>
      <LayerContent layer={layer} frame={frame} delay={delay} duration={duration} />
    </div>
  );
};

/* ── Layer Content by Type ── */
const LayerContent: React.FC<{
  layer: CanvasLayer;
  frame: number;
  delay: number;
  duration: number;
}> = ({ layer, frame, delay, duration }) => {
  const p = layer.props || {};
  const animType = layer.animation?.enter?.type;

  switch (layer.type) {
    case "text":
    case "quote": {
      const text = p.text || "";
      const fontSize = p.fontSize || 40;
      const color = p.color || "#ffffff";
      const fontWeight = p.fontWeight || "normal";
      const lineHeight = p.lineHeight || 1.4;
      const textShadow = p.textShadow || undefined;
      const letterSpacing = p.letterSpacing ? `${p.letterSpacing}px` : undefined;

      // Typewriter animation
      let displayText = text;
      if (animType === "typewriter") {
        const progress = interpolate(frame, [delay, delay + duration], [0, 1], {
          extrapolateLeft: "clamp", extrapolateRight: "clamp",
        });
        const chars = Math.floor(progress * text.length);
        displayText = text.substring(0, chars);
      }

      // Attribution for quotes
      const attribution = p.attribution;

      return (
        <div style={{ fontSize, color, fontWeight: fontWeight as any, lineHeight, textShadow, letterSpacing, whiteSpace: "pre-wrap" }}>
          {displayText}
          {attribution && (
            <div style={{ fontSize: fontSize * 0.5, color: "rgba(255,255,255,0.5)", marginTop: 12 }}>
              {attribution}
            </div>
          )}
        </div>
      );
    }

    case "number": {
      const targetValue = parseFloat(String(p.value || "0").replace(/,/g, ""));
      const suffix = p.suffix || "";
      const fontSize = p.fontSize || 80;
      const color = p.color || "#ffffff";
      const fontWeight = p.fontWeight || "bold";

      // Count up animation
      let displayValue: string;
      if (animType === "count_up") {
        const progress = interpolate(frame, [delay, delay + duration], [0, 1], {
          extrapolateLeft: "clamp", extrapolateRight: "clamp",
          easing: Easing.out(Easing.cubic),
        });
        const current = Math.round(targetValue * progress);
        displayValue = current.toLocaleString();
      } else {
        displayValue = targetValue.toLocaleString();
      }

      const suffixFontSize = p.suffixFontSize ?? fontSize * 0.5;

      return (
        <div style={{
          fontSize, color, fontWeight: fontWeight as any,
          fontVariantNumeric: "tabular-nums",
          whiteSpace: "nowrap",
        }}>
          {displayValue}<span style={{ fontSize: suffixFontSize }}>{suffix}</span>
        </div>
      );
    }

    case "image": {
      const src = p.src || "";
      const objectFit = p.objectFit || "cover";
      const borderRadius = p.borderRadius ?? 0;
      const overlayColor = p.overlayColor;
      const overlayOpacity = p.overlayOpacity ?? 0.3;

      // src 경로 해석: 절대경로면 그대로, 상대경로면 staticFile
      const imgSrc = src
        ? (src.startsWith("/") || src.startsWith("http") ? src : staticFile(src))
        : null;

      if (!imgSrc) {
        return (
          <div style={{
            width: "100%", height: "100%",
            display: "flex", alignItems: "center", justifyContent: "center",
            backgroundColor: "rgba(255,255,255,0.05)",
            border: "1px dashed rgba(255,255,255,0.15)",
            borderRadius: 8,
          }}>
            <span style={{ color: "rgba(255,255,255,0.3)", fontSize: 14 }}>no image</span>
          </div>
        );
      }

      return (
        <div style={{ width: "100%", height: "100%", borderRadius, overflow: "hidden", position: "relative" }}>
          <Img
            src={imgSrc}
            style={{ width: "100%", height: "100%", objectFit: objectFit as any }}
          />
          {overlayColor && (
            <div style={{
              position: "absolute", inset: 0,
              backgroundColor: overlayColor,
              opacity: overlayOpacity,
            }} />
          )}
        </div>
      );
    }

    case "icon": {
      const icon = p.icon || "Circle";
      const size = p.size || 32;
      const color = p.color || "#00d4ff";
      const glow = p.glow;

      return (
        <div style={{
          width: size * 2, height: size * 2,
          borderRadius: "50%",
          backgroundColor: `${color}22`,
          display: "flex", alignItems: "center", justifyContent: "center",
          boxShadow: glow ? `0 0 ${glow.radius || 12}px ${glow.color || color}` : undefined,
        }}>
          <span style={{ fontSize: size, color }}>
            {icon === "Pill" ? "💊" : icon === "Lock" ? "🔒" : icon === "CloudSun" ? "🌤️" : "●"}
          </span>
        </div>
      );
    }

    case "shape": {
      const shapeType = p.shape || "circle";
      const color = p.color || "rgba(0,229,255,0.2)";
      const w = p.width || 200;
      const h = p.height || 200;

      return (
        <div style={{
          width: w, height: h,
          borderRadius: shapeType === "circle" ? "50%" : 0,
          background: `radial-gradient(circle, ${color}, transparent)`,
        }} />
      );
    }

    default:
      return (
        <div style={{ color: "rgba(255,255,255,0.3)", fontSize: 12, padding: 8 }}>
          [{layer.type}]
        </div>
      );
  }
};
