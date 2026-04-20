import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import { resolveEasing } from "../utils/easingMap";

interface Props {
  type:
    | "crossfade"
    | "cut"
    | "fade"
    | "slide"
    | "slide_left"
    | "slide_right"
    | "wipe"
    | "wipe_left"
    | "wipe_right";
  durationFrames: number;
  totalFrames: number;
  easing?: string;
  children: React.ReactNode;
}

export const TransitionEffect: React.FC<Props> = ({
  type,
  durationFrames,
  totalFrames,
  easing,
  children,
}) => {
  const frame = useCurrentFrame();
  const dur = Math.max(durationFrames, 1);
  const easingFn = resolveEasing(easing);

  if (type === "cut" || durationFrames <= 0) {
    return <AbsoluteFill>{children}</AbsoluteFill>;
  }

  // Slide transitions ("slide" → defaults to slide_left)
  if (type === "slide" || type === "slide_left" || type === "slide_right") {
    const direction = type === "slide_right" ? 1 : -1;
    const enterX = interpolate(frame, [0, dur], [direction * -100, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: easingFn,
    });
    const exitX = interpolate(
      frame,
      [totalFrames - dur, totalFrames],
      [0, direction * 100],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easingFn },
    );
    const translateX =
      frame < dur ? enterX : frame > totalFrames - dur ? exitX : 0;
    return (
      <AbsoluteFill style={{ transform: `translateX(${translateX}%)` }}>
        {children}
      </AbsoluteFill>
    );
  }

  // Wipe transitions (clip-path) ("wipe" → defaults to wipe_left)
  if (type === "wipe" || type === "wipe_left" || type === "wipe_right") {
    const enterProgress = interpolate(frame, [0, dur], [0, 100], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: easingFn,
    });
    const exitProgress = interpolate(
      frame,
      [totalFrames - dur, totalFrames],
      [100, 0],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easingFn },
    );
    const progress =
      frame < dur
        ? enterProgress
        : frame > totalFrames - dur
          ? exitProgress
          : 100;
    const clipPath =
      type === "wipe_right"
        ? `inset(0 0 0 ${100 - progress}%)`
        : `inset(0 ${100 - progress}% 0 0)`;
    return (
      <AbsoluteFill style={{ clipPath }}>
        {children}
      </AbsoluteFill>
    );
  }

  // Fade / Crossfade
  const fadeIn = interpolate(frame, [0, dur], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: easingFn,
  });
  const fadeOut = interpolate(
    frame,
    [totalFrames - dur, totalFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easingFn },
  );
  const opacity = Math.min(fadeIn, fadeOut);

  return (
    <AbsoluteFill style={{ opacity }}>
      {children}
    </AbsoluteFill>
  );
};
