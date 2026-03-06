import { interpolate } from "remotion";
import type { CameraKeyframe } from "../types/manifest";
import { resolveEasing } from "../utils/easingMap";

export interface CameraState {
  center: [number, number]; // [lng, lat]
  zoom: number;
  bearing: number;
  pitch: number;
}

/**
 * Mercator 투영 보정: 줌이 높아질수록 같은 경도/위도 변화가 더 큰 픽셀 이동을 만듦.
 * center(팬)가 zoom보다 약간 먼저 도달하도록 프레임 범위를 압축.
 * 이렇게 하면 줌인 시 "줌은 끝났는데 팬이 아직 남아 있는" 느낌을 방지.
 */
const PAN_LEAD_RATIO = 0.88; // center 보간이 전체 구간의 88%에서 완료

/**
 * 키프레임 프레임 배열의 마지막 구간을 ratio만큼 압축.
 * [0, 30, 60] + ratio 0.88 → [0, 30, 56.4]  (마지막 구간만 압축)
 */
function compressLastSegment(frames: number[], ratio: number): number[] {
  if (frames.length < 2) return frames;
  const result = [...frames];
  const lastIdx = result.length - 1;
  const secondLast = result[lastIdx - 1];
  const lastSpan = result[lastIdx] - secondLast;
  result[lastIdx] = secondLast + lastSpan * ratio;
  return result;
}

/**
 * 프레임 번호에 따라 카메라 키프레임 배열을 보간하여 현재 카메라 상태를 반환.
 * MapLibre의 jumpTo()에 직접 전달 가능한 형태.
 *
 * center(팬)는 zoom보다 PAN_LEAD_RATIO 비율만큼 먼저 완료되어
 * Mercator 투영에서의 시각적 동기화를 보정.
 */
export function interpolateCamera(
  frame: number,
  keyframes: CameraKeyframe[],
  easingName?: string,
): CameraState {
  if (keyframes.length === 0) {
    return { center: [126.977, 37.566], zoom: 10, bearing: 0, pitch: 0 };
  }

  if (keyframes.length === 1) {
    const kf = keyframes[0];
    return {
      center: kf.center,
      zoom: kf.zoom,
      bearing: kf.bearing ?? 0,
      pitch: kf.pitch ?? 0,
    };
  }

  const easingFn = resolveEasing(easingName);

  // 키프레임 프레임 번호 배열
  const frames = keyframes.map((kf) => kf.frame);

  // 줌 변화가 있는지 확인 — 줌 변화가 있을 때만 pan lead 적용
  const hasZoomChange = keyframes.some((kf, i) =>
    i > 0 && Math.abs(kf.zoom - keyframes[i - 1].zoom) > 0.5,
  );
  const panFrames = hasZoomChange ? compressLastSegment(frames, PAN_LEAD_RATIO) : frames;

  // center(팬)는 압축된 프레임 범위 사용 → zoom보다 먼저 도달
  const lng = interpolate(frame, panFrames, keyframes.map((kf) => kf.center[0]), {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: easingFn,
  });

  const lat = interpolate(frame, panFrames, keyframes.map((kf) => kf.center[1]), {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: easingFn,
  });

  // zoom/bearing/pitch는 원래 프레임 범위 그대로
  const zoom = interpolate(frame, frames, keyframes.map((kf) => kf.zoom), {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: easingFn,
  });

  const bearing = interpolate(
    frame,
    frames,
    keyframes.map((kf) => kf.bearing ?? 0),
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easingFn },
  );

  const pitch = interpolate(
    frame,
    frames,
    keyframes.map((kf) => kf.pitch ?? 0),
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easingFn },
  );

  return { center: [lng, lat], zoom, bearing, pitch };
}
