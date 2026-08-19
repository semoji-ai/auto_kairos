/**
 * InfographicScene — 배경 없는 요소들을 화면에 배치해 인포그래픽 씬을 만든다.
 *
 * 재연 씬은 한 장을 그려 얹지만 인포그래픽은 요소를 따로 그려 두고 여기서
 * 조립한다. 그림을 굽지 않는 이유는 둘이다.
 *   · 라벨을 나중에 고치거나 번역할 수 있다 (글자는 이미지에 넣지 않는다)
 *   · 요소가 하나씩 등장하는 리듬을 여기서 준다
 *
 * **자리는 여기서 정하지 않는다.** compose 단계(scripts/compose_infographics.py)가
 * `composition.form`을 보고 백분율로 적어 두면 그대로 놓는다. 스토리보드
 * 미리보기도 같은 숫자를 읽는다 — 두 곳에서 따로 배치하면 반드시 어긋난다.
 */
import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

export type InfoAsset = {
  id: string;
  src: string;               // public/ 기준 경로
  label?: string;
};

/** 요소 하나 — 자리(백분율)는 compose 단계가 이미 정해서 넣어 준다. */
export type InfoItem = InfoAsset & { left: number; top: number; size: number };

export type InfographicSceneProps = {
  items: InfoItem[];
  headline?: string;
  background?: string;       // 그리드 배경 등
  accent?: string;
};

export const InfographicScene: React.FC<InfographicSceneProps> = ({
  items, headline, background, accent = "#E8C4B0",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // 하나씩 들어온다. 한꺼번에 뜨면 어디를 봐야 할지 모른다.
  const STEP = Math.round(fps * 0.45);
  const IN = Math.round(fps * 0.5);

  return (
    <AbsoluteFill style={{ backgroundColor: "#F2F2F0" }}>
      {background && (
        <Img src={staticFile(background)}
             style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover" }} />
      )}

      {items.map((a, i) => {
        const t0 = i * STEP;
        const p = interpolate(frame - t0, [0, IN], [0, 1], {
          extrapolateLeft: "clamp", extrapolateRight: "clamp",
        });
        return (
          <div key={a.id + i}
               style={{
                 position: "absolute",
                 left: `${a.left}%`, top: `${a.top}%`,
                 width: `${a.size}%`,
                 transform: `translate(-50%, -50%) translateY(${(1 - p) * 18}px) scale(${0.94 + p * 0.06})`,
                 opacity: p,
                 textAlign: "center",
               }}>
            <Img src={staticFile(a.src)}
                 style={{
                   width: "100%", display: "block",
                   // 밝은 배경에서 요소가 묻히지 않게 띄운다
                   filter: "drop-shadow(0 14px 30px rgba(0,0,0,.28))",
                 }} />
            {a.label && (
              <div style={{
                marginTop: 10, fontFamily: "BMYeonsung, sans-serif",
                fontSize: 26, color: "#2F3E52", lineHeight: 1.2,
              }}>{a.label}</div>
            )}
          </div>
        );
      })}

      {headline && (
        <div style={{
          position: "absolute", left: 0, right: 0, top: "7%",
          textAlign: "center", fontFamily: "BMYeonsung, sans-serif",
          fontSize: 58, color: "#2F3E52",
          textShadow: `0 2px 0 ${accent}`,
        }}>{headline}</div>
      )}
    </AbsoluteFill>
  );
};
