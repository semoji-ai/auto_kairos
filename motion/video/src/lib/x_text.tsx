// 텍스트·타이포 + HUD·자막·포맷 기법(도감 "분석만" → 구현) — ref1·ref2·ref4 프레임 대조 실측.
// 전부 결정론적(remotion random(seed)). 방사형 광선 패턴 없음. 한자는 hz() 로 감싼다.
import React from "react";
import { AbsoluteFill, Img, random, useCurrentFrame, Easing, staticFile } from "remotion";
import { z } from "zod";
import { W, H, lerp, kf, hz, src, EXPO_OUT, QUART_OUT } from "../fx";
import type { Sub } from "../fx";
import { num, col, flag, def } from "../params/p";
import { HBlur } from "./callouts";
import { prop } from "./kit";
import { SmokeSwap } from "./characters";

type RN = React.ReactNode;
const given = <T extends object>(o: T): Partial<T> => Object.fromEntries(Object.entries(o).filter(([, v]) => v !== undefined)) as Partial<T>;
const pos = (v: number, m = 0.001) => Math.max(m, v);
const hexA = (hex: string, a: number) => {
  const h = hex.replace("#", "");
  const n = h.length === 3 ? h.split("").map((c) => c + c).join("") : h.slice(0, 6);
  const v = parseInt(n, 16);
  return `rgba(${(v >> 16) & 255},${(v >> 8) & 255},${v & 255},${a})`;
};
/** 종이 그레인(얇은 노이즈) */
const GrainX: React.FC<{ op?: number; seed?: number }> = ({ op = 0.08, seed = 3 }) => {
  const id = "xg" + React.useId().replace(/[^a-zA-Z0-9]/g, "");
  return (
    <svg width={W} height={H} style={{ position: "absolute", left: 0, top: 0, opacity: op, mixBlendMode: "multiply", pointerEvents: "none" }}>
      <filter id={id}><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves={2} seed={seed} /><feColorMatrix values="0 0 0 0 0.45  0 0 0 0 0.43  0 0 0 0 0.4  0 0 0 -1.6 1.5" /></filter>
      <rect width="100%" height="100%" filter={`url(#${id})`} />
    </svg>
  );
};

// ══ 1. 붓글씨 대형 타이틀 슬램 [ref1 5:26.4 '딤섬의 여왕 정지선 셰프'] ═══════════════
// 약 200%·불투명 30% 에서 5f 만에 100% 로 떨어져 박힘. 검정 붓글씨 + 흐린 흰 외곽(헤일로).
// 퇴장 = 역슬램: 확대 + 페이드, 고스트 이중상 ~6f.
export const CalligraphySlamParams = z.object({
  inLen: num(5, 1, 20, 1, "슬램 길이", "timing", "f"),
  outLen: num(6, 1, 30, 1, "역슬램 퇴장 길이", "timing", "f"),
  fromScale: num(2, 1, 4, 0.05, "시작 크기(배)", "motion", "배"),
  fromOp: num(0.3, 0, 1, 0.05, "시작 불투명도", "look"),
  outScale: num(1.35, 1, 3, 0.05, "퇴장 확대(배)", "motion", "배"),
  ghosts: num(2, 0, 4, 1, "퇴장 고스트 수", "motion"),
  ghostSpread: num(0.12, 0, 0.5, 0.01, "고스트 간 크기차(배)", "motion", "배"),
  size: num(150, 40, 300, 2, "큰 줄 글자 크기", "size", "px"),
  subRatio: num(0.6, 0.3, 1, 0.05, "윗줄 크기 비율", "size"),
  halo: num(10, 0, 40, 1, "흰 외곽 번짐", "look", "px"),
  color: col("#161616", "글자 색"),
  haloColor: col("#ffffff", "외곽 색"),
});
export type CalligraphySlamP = z.infer<typeof CalligraphySlamParams>;
export const CalligraphySlam: React.FC<{ lines: string[]; x?: number; y?: number; at: number; out?: number; p?: Partial<CalligraphySlamP> }> = ({ lines, x = W / 2, y = H / 2, at, out, p }) => {
  const P = def(CalligraphySlamParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const sIn = kf(f, at, [0, pos(P.inLen)], [P.fromScale, 1], Easing.in(Easing.quad));
  const opIn = kf(f, at, [0, pos(P.inLen)], [P.fromOp, 1]);
  const ko = out !== undefined && f >= out ? kf(f, out, [0, pos(P.outLen)], [0, 1], Easing.in(Easing.quad)) : 0;
  if (out !== undefined && f > out + P.outLen) return null;
  const hs = `drop-shadow(0 0 ${P.halo * 0.4}px ${P.haloColor}) drop-shadow(0 0 ${P.halo}px ${P.haloColor})`;
  const block = (s: number, op: number, key: string) => (
    <div key={key} style={{ position: "absolute", left: x, top: y, transform: `translate(-50%,-50%) scale(${s})`, opacity: op, filter: hs, textAlign: "center", whiteSpace: "nowrap", fontFamily: "Yeonsung", color: P.color, lineHeight: 1.05 }}>
      {lines.map((l, i) => <div key={i} style={{ fontSize: i < lines.length - 1 ? P.size * P.subRatio : P.size }}>{hz(l)}</div>)}
    </div>
  );
  const main = 1 + (P.outScale - 1) * ko;
  return (
    <>
      {ko > 0 && Array.from({ length: Math.round(P.ghosts) }).map((_, g) => block(main + P.ghostSpread * (g + 1) * ko * 2, (1 - ko) * 0.45, `g${g}`))}
      {block(sIn * main, opIn * (1 - ko), "m")}
    </>
  );
};

// ══ 2. 흰 글로우 구름 텍스트 [ref2 0:00–39:00 기타] ═════════════════════════════
// 흑백 사진 위 텍스트 뒤에 흰 소프트 블롭(블러 원 뭉치)을 깔아 가독성 확보.
export const GlowCloudTextParams = z.object({
  fadeLen: num(8, 1, 30, 1, "블롭 번짐 길이", "timing", "f"),
  textDelay: num(3, 0, 20, 1, "글자 지연", "timing", "f"),
  textLen: num(6, 1, 20, 1, "글자 페이드 길이", "timing", "f"),
  blobBlur: num(34, 0, 90, 1, "블롭 블러", "look", "px"),
  blobOp: num(0.92, 0, 1, 0.02, "블롭 불투명도", "look"),
  padX: num(90, 0, 300, 5, "블롭 가로 여유", "size", "px"),
  padY: num(60, 0, 200, 5, "블롭 세로 여유", "size", "px"),
  size: num(72, 24, 160, 2, "글자 크기", "size", "px"),
  textColor: col("#161616", "글자 색"),
  blobColor: col("#ffffff", "블롭 색"),
});
export type GlowCloudTextP = z.infer<typeof GlowCloudTextParams>;
export const GlowCloudText: React.FC<{ lines: string[]; x: number; y: number; at: number; seed?: string; p?: Partial<GlowCloudTextP> }> = ({ lines, x, y, at, seed = "gc", p }) => {
  const P = def(GlowCloudTextParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const k = lerp(f, at, at + P.fadeLen, 0, 1);
  const tk = lerp(f, at + P.textDelay, at + P.textDelay + P.textLen, 0, 1);
  const longest = Math.max(...lines.map((l) => l.length));
  const bw = longest * P.size * 0.95 + P.padX * 2, bh = lines.length * P.size * 1.2 + P.padY * 2;
  const blobs = Array.from({ length: 7 }).map((_, i) => ({
    cx: (random(`${seed}x${i}`) - 0.5) * bw * 0.7, cy: (random(`${seed}y${i}`) - 0.5) * bh * 0.45,
    rx: bw * (0.28 + 0.14 * random(`${seed}r${i}`)), ry: bh * (0.38 + 0.12 * random(`${seed}q${i}`)),
  }));
  return (
    <div style={{ position: "absolute", left: x, top: y }}>
      <div style={{ position: "absolute", left: 0, top: 0, filter: `blur(${P.blobBlur}px)`, opacity: P.blobOp * k, transform: `scale(${0.85 + 0.15 * k})` }}>
        {blobs.map((b, i) => <div key={i} style={{ position: "absolute", left: b.cx - b.rx, top: b.cy - b.ry, width: b.rx * 2, height: b.ry * 2, borderRadius: "50%", background: P.blobColor }} />)}
      </div>
      <div style={{ position: "absolute", left: 0, top: 0, transform: "translate(-50%,-50%)", opacity: tk, filter: `blur(${(1 - tk) * 6}px)`, fontFamily: "NeoHv", fontSize: P.size, color: P.textColor, textAlign: "center", whiteSpace: "nowrap", lineHeight: 1.2 }}>
        {lines.map((l, i) => <div key={i}>{hz(l)}</div>)}
      </div>
    </div>
  );
};

// ══ 3. 그라데이션 밴드 스펙 라벨 [ref4-apple 31:43 'MOS 6502 프로세서 내장'] ══════════
// 가운데 #2e292b(α≈0.85) → 좌우 끝 투명 가로 띠 ~620×185, 흰 굵은 ~64px 2줄. 블러 해제 + 알파 ~5f(스케일 변화 없음).
// 뒤 배경은 흰 워시로 ~40% 흐리게. 두 번째 라벨은 ~1.2s 뒤 아래 줄에 같은 방식.
export const SpecBandLabelParams = z.object({
  inLen: num(5, 1, 20, 1, "등장 길이", "timing", "f"),
  blur: num(12, 0, 40, 1, "등장 블러", "look", "px"),
  w: num(620, 200, 1400, 10, "띠 너비", "size", "px"),
  h: num(185, 60, 400, 5, "띠 높이", "size", "px"),
  edge: num(120, 0, 400, 5, "좌우 페이드 폭", "size", "px"),
  gap: num(10, -40, 120, 2, "띠 사이 간격", "size", "px"),
  size: num(64, 24, 120, 2, "글자 크기", "size", "px"),
  alpha: num(0.85, 0, 1, 0.05, "띠 중앙 불투명도", "look"),
  washOp: num(0.4, 0, 1, 0.05, "배경 흰 워시", "look"),
  washLen: num(5, 1, 20, 1, "워시 길이", "timing", "f"),
  color: col("#2e292b", "띠 색"),
  textColor: col("#ffffff", "글자 색"),
});
export type SpecBandLabelP = z.infer<typeof SpecBandLabelParams>;
export const SpecBandLabel: React.FC<{ items: { lines: string[]; at: number }[]; x?: number; y?: number; wash?: boolean; p?: Partial<SpecBandLabelP> }> = ({ items, x = 1490, y = 240, wash = true, p }) => {
  const P = def(SpecBandLabelParams, p);
  const f = useCurrentFrame();
  const at0 = items[0]?.at ?? 0;
  const e = Math.min(49, (P.edge / P.w) * 100);
  return (
    <>
      {wash && f >= at0 && <AbsoluteFill style={{ background: "#fff", opacity: lerp(f, at0, at0 + P.washLen, 0, P.washOp) }} />}
      {items.map((it, i) => {
        if (f < it.at) return null;
        const k = lerp(f, it.at, it.at + P.inLen, 0, 1, Easing.out(Easing.quad));
        const c = hexA(P.color, P.alpha);
        return (
          <div key={i} style={{ position: "absolute", left: x - P.w / 2, top: y + i * (P.h + P.gap), width: P.w, height: P.h, opacity: k, filter: k < 1 ? `blur(${(1 - k) * P.blur}px)` : undefined,
            background: `linear-gradient(90deg, ${hexA(P.color, 0)} 0%, ${c} ${e}%, ${c} ${100 - e}%, ${hexA(P.color, 0)} 100%)`, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
            {it.lines.map((l, j) => <div key={j} style={{ fontFamily: "NeoHv", fontSize: P.size, color: P.textColor, lineHeight: 1.15, whiteSpace: "nowrap" }}>{hz(l)}</div>)}
          </div>
        );
      })}
    </>
  );
};

// ══ 4. 직함 떼어 날리기 [ref4-apple 59:02] ═══════════════════════════════════════
// 흰 종이 포스터(찢긴 가장자리, 1080p 실측 ~680×760): 제목 + 흑백 원형 인물 + 이름 + 직함 줄.
// 직함 줄 ~20f: 제자리에서 +15° 기울며 처짐 → 원본 대조 시 세로로 선 뒤 뒤집히며 오른쪽 위로 날아감(총 ≈+200°, ~420px 오른쪽·380px 위),
// 마지막 6f 페이드+블러. (분석문 '+70°' 보다 실제 회전이 큼)
// 포스터 본체는 고정. 이후 새 직함이 빈 자리에 팝.
export const TitleStripFlyoffParams = z.object({
  tiltLen: num(5, 1, 20, 1, "기울며 처지는 시간", "timing", "f"),
  flyLen: num(20, 4, 60, 1, "전체 날아가는 시간", "timing", "f"),
  fadeLen: num(6, 1, 20, 1, "끝 페이드 길이", "timing", "f"),
  tilt: num(15, 0, 60, 1, "처음 기울기", "motion", "°"),
  sag: num(14, 0, 80, 1, "처짐 거리", "motion", "px"),
  rotTotal: num(200, 0, 540, 5, "총 회전", "motion", "°"),
  dx: num(420, 0, 1200, 10, "가로 이동", "motion", "px"),
  dy: num(-380, -900, 400, 10, "세로 이동(위=-)", "motion", "px"),
  arc: num(60, 0, 400, 5, "호 불룩함", "motion", "px"),
  blur: num(6, 0, 30, 1, "끝 블러", "look", "px"),
  newPopLen: num(6, 1, 20, 1, "새 직함 팝 길이", "timing", "f"),
  posterW: num(680, 200, 1000, 10, "포스터 너비", "size", "px"),
  posterH: num(760, 250, 1000, 10, "포스터 높이", "size", "px"),
  titleSize: num(40, 12, 80, 1, "직함 글자 크기", "size", "px"),
  paper: col("#FAF8F3", "종이 색"),
});
export type TitleStripFlyoffP = z.infer<typeof TitleStripFlyoffParams>;
const tornPoly = (seed: string, n = 26, amp = 1.3) => {
  const pts: string[] = [];
  const j = (k: string) => (random(seed + k) - 0.5) * 2 * amp;
  for (let i = 0; i <= n; i++) pts.push(`${(i / n) * 100}% ${Math.abs(j(`t${i}`))}%`);
  for (let i = 0; i <= n; i++) pts.push(`${100 - Math.abs(j(`r${i}`))}% ${(i / n) * 100}%`);
  for (let i = n; i >= 0; i--) pts.push(`${(i / n) * 100}% ${100 - Math.abs(j(`b${i}`))}%`);
  for (let i = n; i >= 0; i--) pts.push(`${Math.abs(j(`l${i}`))}% ${(i / n) * 100}%`);
  return `polygon(${pts.join(",")})`;
};
export const TitleStripFlyoff: React.FC<{ img: string; heading: string; name: string; title: string; newTitle?: string; x?: number; y?: number; at: number; newAt?: number; imgPos?: string; p?: Partial<TitleStripFlyoffP> }> = ({ img, heading, name, title, newTitle, x = 760, y = 180, at, newAt, imgPos = "50% 30%", p }) => {
  const P = def(TitleStripFlyoffParams, p);
  const f = useCurrentFrame();
  const pw = P.posterW, ph = P.posterH, d = pw * 0.46;
  const g = f - at;
  const TL = Math.min(P.tiltLen, P.flyLen - 1);
  let rot = 0, tx = 0, ty = 0, op = 1, bl = 0;
  if (g >= 0) {
    if (g <= TL) { const k = Easing.out(Easing.quad)(g / pos(TL)); rot = P.tilt * k; ty = P.sag * k; }
    else {
      const k = Easing.in(Easing.quad)(Math.min(1, (g - TL) / pos(P.flyLen - TL)));
      rot = P.tilt + (P.rotTotal - P.tilt) * k; tx = P.dx * k; ty = P.sag + P.dy * k - P.arc * Math.sin(Math.PI * k);
    }
    op = kf(f, at, [P.flyLen - P.fadeLen, P.flyLen], [1, 0]);
    bl = kf(f, at, [P.flyLen - P.fadeLen, P.flyLen], [0, P.blur]);
  }
  const ty0 = ph * 0.84;
  const nk = newAt !== undefined && f >= newAt ? kf(f, newAt, [0, P.newPopLen * 0.6, P.newPopLen], [0.4, 1.08, 1], Easing.out(Easing.quad)) : 0;
  const strip = (t: string, style: React.CSSProperties) => (
    <div style={{ position: "absolute", left: 0, width: pw, top: ty0, textAlign: "center", fontFamily: "NeoHv", fontSize: P.titleSize, color: "#1c1c1c", whiteSpace: "nowrap", ...style }}>[{t}]</div>
  );
  return (
    <div style={{ position: "absolute", left: x, top: y, width: pw, height: ph }}>
      <div style={{ position: "absolute", inset: 0, background: P.paper, clipPath: tornPoly("tp"), filter: "drop-shadow(0 4px 6px rgba(0,0,0,0.25))" }} />
      <div style={{ position: "absolute", left: 0, width: pw, top: ph * 0.07, textAlign: "center", fontFamily: "NeoHv", fontSize: pw * 0.11, color: "#111" }}>{heading}</div>
      <div style={{ position: "absolute", left: (pw - d) / 2, top: ph * 0.22, width: d, height: d, borderRadius: "50%", overflow: "hidden", background: "#bbb" }}>
        <Img src={src(img)} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: imgPos, filter: "grayscale(1) contrast(1.05)" }} />
      </div>
      <div style={{ position: "absolute", left: 0, width: pw, top: ph * 0.68, textAlign: "center", fontFamily: "NeoHv", fontSize: pw * 0.1, color: "#111" }}>{name}</div>
      {op > 0.01 && strip(title, { transformOrigin: "50% 50%", transform: `translate(${tx}px,${ty}px) rotate(${rot}deg)`, opacity: op, filter: bl > 0.2 ? `blur(${bl}px)` : undefined })}
      {newTitle && nk > 0 && strip(newTitle, { transform: `scale(${nk})`, opacity: Math.min(1, nk * 1.5) })}
    </div>
  );
};

// ══ 5. 네 모서리 빨간 글자 타일 [ref4-apple 1:16:50 '비싼 가격', 1:10:40 '비전실현'] ═══════════
// 1080p 실측: 타일 ~245×245(좌 x225·우 x1440, 위 y160·아래 y620), 주황→빨강 그라데이션 + 크림 안쪽 선,
// 크림 글자 ~190px. 좌상→우상→좌하→우하 순서로 반투명 대형(~1.8배) 고스트가 5f 에 줄어들며 박힘, 간격 ~8f.
export const CornerCharTilesParams = z.object({
  stagger: num(8, 0, 30, 1, "타일 간격", "timing", "f"),
  slamLen: num(5, 1, 20, 1, "박히는 시간", "timing", "f"),
  fromScale: num(1.8, 1, 4, 0.05, "시작 크기(배)", "motion", "배"),
  fromOp: num(0.25, 0, 1, 0.05, "시작 불투명도", "look"),
  tile: num(245, 80, 400, 5, "타일 크기", "size", "px"),
  left: num(225, 0, 800, 5, "왼쪽 열 x", "size", "px"),
  right: num(1440, 900, 1800, 5, "오른쪽 열 x", "size", "px"),
  top: num(160, 0, 600, 5, "윗줄 y", "size", "px"),
  bottom: num(620, 300, 900, 5, "아랫줄 y", "size", "px"),
  size: num(190, 40, 300, 2, "글자 크기", "size", "px"),
  fillA: col("#EC7A45", "타일 위 색"),
  fillB: col("#C4303A", "타일 아래 색"),
  rim: col("#F6E9DC", "안쪽 선·글자 색"),
});
export type CornerCharTilesP = z.infer<typeof CornerCharTilesParams>;
export const CornerCharTiles: React.FC<{ chars: string[]; at: number; p?: Partial<CornerCharTilesP> }> = ({ chars, at, p }) => {
  const P = def(CornerCharTilesParams, p);
  const f = useCurrentFrame();
  const cs: [number, number][] = [[P.left, P.top], [P.right, P.top], [P.left, P.bottom], [P.right, P.bottom]];
  return (
    <>
      {chars.slice(0, 4).map((c, i) => {
        const a = at + i * P.stagger;
        if (f < a) return null;
        const s = kf(f, a, [0, pos(P.slamLen)], [P.fromScale, 1], Easing.in(Easing.quad));
        const op = kf(f, a, [0, pos(P.slamLen)], [P.fromOp, 1]);
        const T = P.tile;
        return (
          <div key={i} style={{ position: "absolute", left: cs[i][0], top: cs[i][1], width: T, height: T, transform: `scale(${s})`, opacity: op, borderRadius: T * 0.05,
            background: `linear-gradient(160deg, ${P.fillA}, ${P.fillB})`, boxShadow: "0 6px 14px rgba(0,0,0,0.35)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <div style={{ position: "absolute", inset: T * 0.045, borderRadius: T * 0.04, border: `${Math.max(2, T * 0.02)}px solid ${P.rim}` }} />
            <div style={{ fontFamily: "Jalnan", fontSize: P.size * (T / 245), color: P.rim, lineHeight: 1, marginTop: T * 0.04, textShadow: "0 3px 0 rgba(90,20,20,0.35)" }}>{hz(c)}</div>
          </div>
        );
      })}
    </>
  );
};

// ══ 6. 반복 단어 월페이퍼 [ref4-apple 1:45:16 'PROJECT' 150개] ═════════════════════
// 노랑-크림 보케 위 흰 박스 타일(검정 굵은 대문자 단어) 격자가 화면 밖까지 채우고, 전체가 천천히 아래로 흐름(≈200px/s).
// 등장 = 틴트 플리커 후 정지. compressAt 에서 2행×5개 "압축 결과" 로 하드 교체.
export const WordWallpaperParams = z.object({
  flickerLen: num(8, 0, 30, 1, "틴트 플리커 길이", "timing", "f"),
  speed: num(200, -600, 600, 10, "흐름 속도(+아래)", "motion", "px/s"),
  colPitch: num(420, 150, 800, 5, "가로 간격", "size", "px"),
  rowPitch: num(165, 60, 400, 5, "세로 간격", "size", "px"),
  rowShift: num(0, 0, 400, 5, "행마다 x 엇갈림", "size", "px"),
  size: num(72, 20, 160, 2, "글자 크기", "size", "px"),
  boxAlpha: num(0.7, 0, 1, 0.05, "박스 불투명도", "look"),
  bg: col("#F7E7A8", "배경(보케) 색"),
  bokeh: col("#FFF6D6", "보케 빛 색"),
  textColor: col("#111111", "글자 색"),
});
export type WordWallpaperP = z.infer<typeof WordWallpaperParams>;
export const WordWallpaper: React.FC<{ word: string; at?: number; compressAt?: number; compressN?: number; p?: Partial<WordWallpaperP> }> = ({ word, at = 0, compressAt, compressN = 10, p }) => {
  const P = def(WordWallpaperParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const g = f - at;
  const flick = g < P.flickerLen ? (Math.floor(g / 2) % 2 === 0 ? 0.55 : 1) : 1;
  const compressed = compressAt !== undefined && f >= compressAt;
  const off = ((g / 30) * P.speed) % P.rowPitch;
  const rows = Math.ceil(H / P.rowPitch) + 2, cols = Math.ceil(W / P.colPitch) + 2;
  const box = (key: string, l: number, t: number, sz = P.size) => (
    <div key={key} style={{ position: "absolute", left: l, top: t, height: sz * 1.25, padding: `0 ${sz * 0.22}px`, background: `rgba(255,255,255,${P.boxAlpha})`, display: "flex", alignItems: "center", fontFamily: "NeoHv", fontSize: sz, color: P.textColor, letterSpacing: 1, whiteSpace: "nowrap" }}>{word}</div>
  );
  const bok = Array.from({ length: 14 }).map((_, i) => ({ x: random(`wb${i}`) * W, y: random(`wy${i}`) * H, r: 80 + random(`wr${i}`) * 160 }));
  return (
    <AbsoluteFill style={{ background: P.bg, opacity: flick }}>
      {bok.map((b, i) => <div key={i} style={{ position: "absolute", left: b.x - b.r, top: b.y - b.r, width: b.r * 2, height: b.r * 2, borderRadius: "50%", background: P.bokeh, opacity: 0.55, filter: "blur(30px)" }} />)}
      {!compressed && Array.from({ length: rows }).map((_, r) => Array.from({ length: cols }).map((_, c) => box(`${r}-${c}`, -P.colPitch * 0.35 + c * P.colPitch + (r % 2) * P.rowShift, -P.rowPitch + r * P.rowPitch + off)))}
      {compressed && Array.from({ length: compressN }).map((_, i) => {
        const perRow = Math.ceil(compressN / 2), r = Math.floor(i / perRow), c = i % perRow;
        const pitch = Math.min(P.colPitch, (W - 120) / perRow);
        const estW = P.size * 0.7 * word.length + P.size * 0.44, sz = P.size * Math.min(1, (pitch * 0.9) / estW);
        return box(`c${i}`, (W - pitch * perRow) / 2 + c * pitch + (pitch - estW * (sz / P.size)) / 2, H / 2 - (P.rowPitch + sz * 1.25) / 2 + r * P.rowPitch, sz);
      })}
    </AbsoluteFill>
  );
};

// ══ 7. 정의문 줄단위 블러 상승 리빌 [ref4-apple 1:32:29 '중앙처리장치 CPU'] ═════════════
// 딥 인디고 #1E1650, 좌측 아이소메트릭 칩(청록 발광 + 위로 흐르는 입자 기둥 루프), 우측 검정 리본 배너 제목,
// 설명 줄(흰 굵은, **키워드** = 노랑 #F5B82E)이 VO 에 맞춰 한 줄씩: y+15→0, 블러 8→0, α0→1, ≈12f ease-out.
export const DefinitionRevealParams = z.object({
  lineLen: num(12, 1, 40, 1, "줄 등장 길이", "timing", "f"),
  lineGap: num(36, 4, 90, 1, "줄 간격(VO 싱크)", "timing", "f"),
  titleLen: num(8, 1, 30, 1, "제목 배너 등장", "timing", "f"),
  rise: num(15, 0, 80, 1, "떠오르는 거리", "motion", "px"),
  blur: num(8, 0, 30, 1, "줄 블러", "look", "px"),
  size: num(54, 20, 100, 2, "설명 글자 크기", "size", "px"),
  titleSize: num(44, 16, 90, 2, "제목 글자 크기", "size", "px"),
  lineH: num(72, 30, 140, 2, "줄 높이", "size", "px"),
  chipSize: num(420, 150, 700, 10, "칩 크기", "size", "px"),
  bg: col("#1E1650", "배경 색"),
  key: col("#F5B82E", "키워드 색"),
  glow: col("#2FE0C8", "칩 발광 색"),
});
export type DefinitionRevealP = z.infer<typeof DefinitionRevealParams>;
const IsoChip: React.FC<{ s: number; glow: string; f: number }> = ({ s, glow, f }) => {
  return (
    <svg width={s} height={s * 1.3} viewBox={`${-s / 2} ${-s * 0.85} ${s} ${s * 1.3}`} style={{ overflow: "visible" }}>
      <defs><linearGradient id="xcol" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stopColor={glow} stopOpacity={0.45} /><stop offset="1" stopColor={glow} stopOpacity={0} /></linearGradient></defs>
      <polygon points={`${-s * 0.22},${-s * 0.02} ${s * 0.22},${-s * 0.02} ${s * 0.22},${-s * 0.8} ${-s * 0.22},${-s * 0.8}`} fill="url(#xcol)" />
      {/* 세모지 그림체 아이소 칩(isochip_base + isochip_core, 같은 크롭 박스라 겹쳐 정렬) */}
      <image href={prop("isochip_base")} x={-s * 0.46} y={s * 0.03 - s * 0.726 * 0.45} width={s * 0.92} height={s * 0.726} />
      <image href={prop("isochip_core")} x={-s * 0.46} y={s * 0.03 - s * 0.726 * 0.45} width={s * 0.92} height={s * 0.726} />
      {Array.from({ length: 14 }).map((_, i) => {
        const ph = random(`cp${i}`), per = 40 + random(`cq${i}`) * 30;
        const t = ((f / per + ph) % 1);
        const x = (random(`cx${i}`) - 0.5) * s * 0.4, y = -s * 0.05 - t * s * 0.75;
        return <circle key={i} cx={x} cy={y} r={3 + random(`cr${i}`) * 3} fill="#BFFFF6" opacity={Math.sin(Math.PI * t)} />;
      })}
    </svg>
  );
};
const keyed = (t: string, key: string) => t.split(/(\*\*[^*]+\*\*)/).map((s, i) => s.startsWith("**") ? <span key={i} style={{ color: key }}>{hz(s.slice(2, -2))}</span> : <React.Fragment key={i}>{hz(s)}</React.Fragment>);
export const DefinitionReveal: React.FC<{ title: string; lines: string[]; at: number; lineAts?: number[]; x?: number; y?: number; bgOn?: boolean; p?: Partial<DefinitionRevealP> }> = ({ title, lines, at, lineAts, x = 1260, y = 190, bgOn = true, p }) => {
  const P = def(DefinitionRevealParams, p);
  const f = useCurrentFrame();
  const tk = lerp(f, at, at + P.titleLen, 0, 1, EXPO_OUT);
  return (
    <AbsoluteFill style={{ background: bgOn ? P.bg : undefined }}>
      <div style={{ position: "absolute", left: 520 - P.chipSize / 2, top: 520 - P.chipSize * 0.85 }}><IsoChip s={P.chipSize} glow={P.glow} f={f} /></div>
      {f >= at && (
        <div style={{ position: "absolute", left: x, top: y, transform: "translateX(-50%)", clipPath: `inset(0 ${50 * (1 - tk)}% 0 ${50 * (1 - tk)}%)` }}>
          <div style={{ position: "relative", background: "#111", padding: `10px ${P.titleSize * 1.2}px`, fontFamily: "NeoHv", fontSize: P.titleSize, color: "#fff", whiteSpace: "nowrap",
            clipPath: `polygon(0 0, 100% 0, calc(100% - ${P.titleSize * 0.5}px) 50%, 100% 100%, 0 100%, ${P.titleSize * 0.5}px 50%)` }}>{hz(title)}</div>
        </div>
      )}
      {lines.map((l, i) => {
        const a = lineAts?.[i] ?? at + P.titleLen + i * P.lineGap;
        if (f < a) return null;
        const k = lerp(f, a, a + P.lineLen, 0, 1, Easing.out(Easing.cubic));
        return (
          <div key={i} style={{ position: "absolute", left: x, top: y + P.titleSize * 2.4 + i * P.lineH, transform: `translate(-50%, ${(1 - k) * P.rise}px)`, opacity: k, filter: k < 1 ? `blur(${(1 - k) * P.blur}px)` : undefined,
            fontFamily: "NeoHv", fontSize: P.size, color: "#fff", whiteSpace: "nowrap" }}>{keyed(l, P.key)}</div>
        );
      })}
    </AbsoluteFill>
  );
};

// ══ 8. 연도 칩 고속 롤 + 라인업 몽타주 [ref4-cocacola 30:36 1958→1974] ════════════════
// 좌측 벽에 붙은 네이비 칩 #18308a(x0–311, y212–365), 흰 볼드 '1974년'. 구간이 바뀌면 숫자가 한 프레임에 한 단계씩
// 하드스텝으로 굴러 목표 연도에 멈추고(≈10f), 같은 프레임에 중앙 라인업이 하드컷 교체. 제품 아래 색 라벨 캡슐.
export const YearChipRollParams = z.object({
  rollMax: num(10, 1, 40, 1, "롤 최대 길이", "timing", "f"),
  framesPerStep: num(1, 1, 6, 1, "한 단계당 프레임", "timing", "f"),
  chipW: num(311, 120, 600, 1, "칩 너비", "size", "px"),
  chipH: num(153, 60, 300, 1, "칩 높이", "size", "px"),
  chipTop: num(212, 0, 800, 1, "칩 y", "size", "px"),
  chipSize: num(60, 20, 120, 2, "칩 글자 크기", "size", "px"),
  itemH: num(480, 150, 800, 10, "제품 높이", "size", "px"),
  labelSize: num(34, 14, 70, 1, "라벨 글자 크기", "size", "px"),
  chip: col("#18308a", "칩 색"),
  bg: col("#c0cac1", "배경 색"),
});
export type YearChipRollP = z.infer<typeof YearChipRollParams>;
export type LineupItem = { img: string; label: string; color?: string };
export const YearChipRoll: React.FC<{ segs: { year: number; at: number; items: LineupItem[] }[]; startYear?: number; suffix?: string; bgOn?: boolean; p?: Partial<YearChipRollP> }> = ({ segs, startYear, suffix = "년", bgOn = true, p }) => {
  const P = def(YearChipRollParams, p);
  const f = useCurrentFrame();
  let idx = -1;
  segs.forEach((s, i) => { if (f >= s.at) idx = i; });
  const cur = idx >= 0 ? segs[idx] : undefined;
  let year = cur?.year ?? startYear ?? segs[0]?.year ?? 0;
  if (cur) {
    const prev = idx > 0 ? segs[idx - 1].year : startYear ?? cur.year;
    const n = cur.year - prev, steps = Math.min(Math.abs(n), Math.round(P.rollMax));
    const k = Math.floor((f - cur.at) / P.framesPerStep) + 1;
    if (steps > 0 && k < steps) year = prev + Math.round((n * k) / steps);
  }
  const items = cur?.items ?? [];
  const slot = Math.min(440, (W - 500) / Math.max(1, items.length));
  return (
    <AbsoluteFill style={{ background: bgOn ? P.bg : undefined }}>
      {items.map((it, i) => {
        const cx = W / 2 + (i - (items.length - 1) / 2) * slot;
        return (
          <React.Fragment key={`${idx}-${i}`}>
            <Img src={src(it.img)} style={{ position: "absolute", left: cx - slot * 0.45, top: 610 - P.itemH, width: slot * 0.9, height: P.itemH, objectFit: "contain", objectPosition: "50% 100%" }} />
            <div style={{ position: "absolute", left: cx, top: 650, transform: "translateX(-50%)", background: it.color || "#C9C27A", padding: `4px ${P.labelSize * 0.8}px`, borderRadius: 6, fontFamily: "NeoHv", fontSize: P.labelSize, color: "#1c1c1c", whiteSpace: "nowrap" }}>{it.label}</div>
          </React.Fragment>
        );
      })}
      {cur && (
        <div style={{ position: "absolute", left: 0, top: P.chipTop, width: P.chipW, height: P.chipH, background: P.chip, borderRadius: `0 8px 8px 0`, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "NeoHv", fontSize: P.chipSize, color: "#fff" }}>
          {year}{suffix}
        </div>
      )}
    </AbsoluteFill>
  );
};

// ══ 9. 세이지 연월 타이핑 카드 [ref4-hyundai 12:58 '1942년 5월', 8:20 '그런'] ═════════════
// 하드컷 → 세이지 #C2CCC3 단색(그레인) 카드. 최종 가운데 위치에 미리 배치한 채 왼쪽부터 글자 드러냄(공백은 건너뜀).
// 컷 후 2f 빈 카드 → 글리프당 ≈2.5f, 커서 없음. 완성 후 홀드 → 하드컷.  (1080p 실측 글자 ~110px)
export const SageDateCardParams = z.object({
  blank: num(2, 0, 20, 1, "빈 카드 프레임", "timing", "f"),
  perGlyph: num(2.5, 0.5, 10, 0.5, "글자당 프레임", "timing", "f"),
  size: num(110, 30, 220, 2, "글자 크기", "size", "px"),
  y: num(540, 200, 900, 5, "글자 중심 y", "size", "px"),
  grain: num(0.08, 0, 0.4, 0.01, "그레인 세기", "look"),
  bg: col("#C2CCC3", "배경 색"),
  color: col("#111111", "글자 색"),
});
export type SageDateCardP = z.infer<typeof SageDateCardParams>;
export const SageDateCard: React.FC<{ text: string; at?: number; p?: Partial<SageDateCardP> }> = ({ text, at = 0, p }) => {
  const P = def(SageDateCardParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const g = f - at - P.blank;
  const chars = Array.from(text);
  let shown = g < 0 ? 0 : Math.floor(g / P.perGlyph) + 1, cnt = 0;
  const vis = chars.map((c) => { if (c === " ") return shown > cnt; cnt++; return cnt <= shown; });
  return (
    <AbsoluteFill style={{ background: P.bg }}>
      <GrainX op={P.grain} />
      <div style={{ position: "absolute", left: 0, right: 0, top: P.y, transform: "translateY(-50%)", textAlign: "center", fontFamily: "NeoHv", fontSize: P.size, color: P.color, whiteSpace: "pre" }}>
        {chars.map((c, i) => <span key={i} style={{ opacity: vis[i] ? 1 : 0 }}>{c}</span>)}
      </div>
    </AbsoluteFill>
  );
};

// ══ 10. 붓글씨 헤드라인 블러 인 [ref4-hyundai 13:01 '기업정비령 공포!'] ═══════════════════
// 흰 거친 붓글씨 대형 문구가 장면 중앙을 가로지름. 블러 ≈20px→0 + 불투명 0→1 ≈12f(easeOut), 스케일 변화 없음.
// 배경 장면은 명도 -40% 암부. 약한 드롭섀도.
export const BrushHeadlineParams = z.object({
  len: num(12, 1, 40, 1, "블러 해제 길이", "timing", "f"),
  blur: num(20, 0, 60, 1, "시작 블러", "look", "px"),
  dim: num(0.4, 0, 0.9, 0.05, "배경 어둡게", "look"),
  dimLen: num(6, 0, 30, 1, "암부 전환 길이", "timing", "f"),
  size: num(230, 40, 360, 2, "글자 크기", "size", "px"),
  weight: num(4, 0, 12, 0.5, "획 두께 보강", "size", "px"),
  y: num(480, 100, 900, 5, "글자 중심 y", "size", "px"),
  shadow: num(0.5, 0, 1, 0.05, "드롭섀도 세기", "look"),
  color: col("#ffffff", "글자 색"),
});
export type BrushHeadlineP = z.infer<typeof BrushHeadlineParams>;
export const BrushHeadline: React.FC<{ text: string; at: number; children?: RN; p?: Partial<BrushHeadlineP> }> = ({ text, at, children, p }) => {
  const P = def(BrushHeadlineParams, p);
  const f = useCurrentFrame();
  const k = lerp(f, at, at + P.len, 0, 1, Easing.out(Easing.cubic));
  const dk = P.dimLen > 0 ? lerp(f, at, at + P.dimLen, 0, 1) : f >= at ? 1 : 0;
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ filter: `brightness(${1 - P.dim * dk})` }}>{children}</AbsoluteFill>
      {f >= at && (
        <div style={{ position: "absolute", left: 0, right: 0, top: P.y, transform: "translateY(-50%)", textAlign: "center", fontFamily: "Yeonsung", fontSize: P.size, color: P.color, WebkitTextStroke: P.weight > 0 ? `${P.weight}px ${P.color}` : undefined, whiteSpace: "nowrap", opacity: k,
          filter: `${k < 1 ? `blur(${(1 - k) * P.blur}px) ` : ""}drop-shadow(0 4px 6px rgba(0,0,0,${P.shadow}))` }}>{hz(text)}</div>
      )}
    </AbsoluteFill>
  );
};

// ══ 11. 네이비 팩트 필 스택 [ref4-hyundai 1:12:25 조선소 4줄 누적] ═══════════════════════
// 필 1128×166, 중앙정렬, 세로 피치 196, #1D1951~#261F69, 흰 볼드. 새 필은 blur ~15→0 + α0→1 ~12f, 스케일·이동 없음.
export const FactPillStackParams = z.object({
  len: num(12, 1, 40, 1, "등장 길이", "timing", "f"),
  blur: num(15, 0, 50, 1, "등장 블러", "look", "px"),
  w: num(1128, 300, 1800, 4, "필 너비", "size", "px"),
  h: num(166, 50, 300, 2, "필 높이", "size", "px"),
  pitch: num(196, 50, 400, 2, "세로 피치", "size", "px"),
  top: num(130, 0, 800, 5, "첫 필 y", "size", "px"),
  size: num(70, 20, 140, 2, "글자 크기", "size", "px"),
  colorA: col("#1D1951", "필 위 색"),
  colorB: col("#261F69", "필 아래 색"),
  textColor: col("#ffffff", "글자 색"),
});
export type FactPillStackP = z.infer<typeof FactPillStackParams>;
export const FactPillStack: React.FC<{ items: { text: string; at: number }[]; x?: number; p?: Partial<FactPillStackP> }> = ({ items, x = W / 2, p }) => {
  const P = def(FactPillStackParams, p);
  const f = useCurrentFrame();
  return (
    <>
      {items.map((it, i) => {
        if (f < it.at) return null;
        const k = lerp(f, it.at, it.at + P.len, 0, 1, Easing.out(Easing.quad));
        return (
          <div key={i} style={{ position: "absolute", left: x - P.w / 2, top: P.top + i * P.pitch, width: P.w, height: P.h, borderRadius: P.h / 2, background: `linear-gradient(180deg, ${P.colorA}, ${P.colorB})`,
            opacity: k, filter: k < 1 ? `blur(${(1 - k) * P.blur}px)` : undefined, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "NeoHv", fontSize: P.size, color: P.textColor, whiteSpace: "nowrap" }}>{hz(it.text)}</div>
        );
      })}
    </>
  );
};

// ══ 12. 헤드라인 밴드 슬램 [ref4-hyundai 1:56:52 '해운 단가 폭락!'] ═════════════════════
// 30fps 원본 대조: 배경 전체 블러 + 어두운 반투명 가로 띠(y≈243–811) 먼저 → 1f 뒤 텍스트가 "가운데서 가로로 늘어나며" 등장
// (scaleX 0.3→0.75→1.12→1.04→1.0, 가로 모션블러 60→0, 4f). 분석문의 "좌측 슬라이드" 가 아님. 이후 미세 좌측 드리프트.
export const HeadlineBandSlamParams = z.object({
  bandLen: num(3, 0, 20, 1, "띠·블러 등장 길이", "timing", "f"),
  textDelay: num(1, 0, 20, 1, "텍스트 지연", "timing", "f"),
  stretchLen: num(4, 1, 20, 1, "가로 늘어남 길이", "timing", "f"),
  fromScaleX: num(0.3, 0, 1, 0.05, "시작 가로 비율", "motion"),
  over: num(1.12, 1, 1.6, 0.01, "오버슈트(배)", "motion", "배"),
  hblur: num(60, 0, 200, 2, "가로 모션블러", "look", "px"),
  drift: num(0.6, 0, 5, 0.1, "좌측 드리프트", "motion", "px/f"),
  bgBlur: num(20, 0, 60, 1, "배경 블러", "look", "px"),
  bandTop: num(243, 0, 800, 1, "띠 위 y", "size", "px"),
  bandBottom: num(811, 200, 1080, 1, "띠 아래 y", "size", "px"),
  bandAlpha: num(0.5, 0, 1, 0.05, "띠 불투명도", "look"),
  size: num(250, 60, 400, 2, "글자 크기", "size", "px"),
  bandColor: col("#1a1208", "띠 색"),
  color: col("#FBF6F1", "글자 색"),
});
export type HeadlineBandSlamP = z.infer<typeof HeadlineBandSlamParams>;
export const HeadlineBandSlam: React.FC<{ text: string; at: number; children?: RN; p?: Partial<HeadlineBandSlamP> }> = ({ text, at, children, p }) => {
  const P = def(HeadlineBandSlamParams, p);
  const f = useCurrentFrame();
  const bk = P.bandLen > 0 ? lerp(f, at, at + P.bandLen, 0, 1) : f >= at ? 1 : 0;
  const ta = at + P.textDelay, L = pos(P.stretchLen);
  const sx = kf(f, ta, [0, L * 0.25, L * 0.5, L * 0.75, L], [P.fromScaleX, (P.fromScaleX + 1) / 2 + 0.1, P.over, 1 + (P.over - 1) * 0.35, 1]);
  const hb = kf(f, ta, [0, L], [P.hblur, 0], Easing.out(Easing.quad));
  const dx = f > ta + L ? -(f - ta - L) * P.drift : 0;
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ filter: bk > 0 ? `blur(${P.bgBlur * bk}px)` : undefined, transform: bk > 0 ? "scale(1.03)" : undefined }}>{children}</AbsoluteFill>
      {f >= at && <div style={{ position: "absolute", left: 0, right: 0, top: P.bandTop, height: P.bandBottom - P.bandTop, background: hexA(P.bandColor, P.bandAlpha), opacity: bk }} />}
      {f >= ta && (
        <HBlur amt={hb} style={{ position: "absolute", left: 0, right: 0, top: (P.bandTop + P.bandBottom) / 2, transform: `translate(${dx}px,-50%) scaleX(${sx})`, textAlign: "center" }}>
          <div style={{ fontFamily: "Jua", fontSize: P.size, color: P.color, whiteSpace: "nowrap", lineHeight: 1 }}>{hz(text)}</div>
        </HBlur>
      )}
    </AbsoluteFill>
  );
};

// ══ 13. 인물 뒤 대형 수치 + 불꽃 [ref4-samsung 14:47 '20억' → 불타는 20억] ═══════════════════
// 리그: 텍스트(진갈색 브러시체 ≈820×280)를 캐릭터 "뒤" 레이어에. 블러 12→0 + α ≈30f, 캐릭터 동시 1.0→0.85 풀백.
// fireAt: 회색 연기 퍼프가 덮고(SmokeSwap) 걷히면 글자 가장자리에 불꽃 6개, 각 8~10f 흔들림 루프. 캐릭터는 연기 앞.
export const TextBehindCharacterParams = z.object({
  inLen: num(30, 1, 90, 1, "블러 해제 길이", "timing", "f"),
  blur: num(12, 0, 40, 1, "시작 블러", "look", "px"),
  pullTo: num(0.85, 0.5, 1.2, 0.01, "캐릭터 풀백 크기", "motion", "배"),
  flameN: num(6, 0, 12, 1, "불꽃 개수", "size"),
  flameSize: num(110, 20, 240, 2, "불꽃 크기", "size", "px"),
  flameLoop: num(9, 3, 30, 1, "불꽃 흔들림 주기", "timing", "f"),
  size: num(400, 80, 600, 5, "글자 크기", "size", "px"),
  weight: num(6, 0, 16, 0.5, "획 두께 보강", "size", "px"),
  color: col("#3A230B", "글자 색"),
});
export type TextBehindCharacterP = z.infer<typeof TextBehindCharacterParams>;
const Flame: React.FC<{ x: number; y: number; s: number; f: number; loop: number; seed: string }> = ({ x, y, s, f, loop, seed }) => {
  const ph = random(seed) * loop;
  const t = ((f + ph) % loop) / loop;
  const sy = 1 + 0.14 * Math.sin(t * Math.PI * 2), sk = 8 * Math.sin(t * Math.PI * 2 + 1.3);
  const tip = (random(seed + "t") - 0.5) * 16;
  return (
    <svg width={s} height={s * 1.4} viewBox="-50 -120 100 140" style={{ position: "absolute", left: x - s / 2, top: y - s * 1.2, overflow: "visible", transformOrigin: "50% 90%", transform: `scaleY(${sy}) skewX(${sk}deg)` }}>
      <path d={`M0,18 C-38,18 -44,-18 -26,-44 C-20,-54 -16,-40 -12,-36 C-12,-66 ${tip - 4},-86 ${tip},-112 C12,-80 34,-62 30,-30 C38,-40 40,-48 38,-56 C54,-26 44,18 0,18Z`} fill="#F26A0F" />
      <path d={`M0,16 C-22,16 -26,-8 -14,-26 C-10,-18 -6,-16 -4,-18 C-4,-42 ${tip * 0.6},-58 ${tip * 0.6 + 4},-70 C12,-50 26,-34 20,-6 C18,10 10,16 0,16Z`} fill="#F7C21A" />
    </svg>
  );
};
export const TextBehindCharacter: React.FC<{ text: string; img: string; at: number; fireAt?: number; x?: number; textY?: number; charW?: number; charTop?: number; p?: Partial<TextBehindCharacterP> }> = ({ text, img, at, fireAt, x = W / 2, textY = 380, charW = 520, charTop = 300, p }) => {
  const P = def(TextBehindCharacterParams, p);
  const f = useCurrentFrame();
  const k = lerp(f, at, at + P.inLen, 0, 1, Easing.out(Easing.cubic));
  const cs = lerp(f, at, at + P.inLen, 1, P.pullTo, Easing.inOut(Easing.cubic));
  const tw = Array.from(text).length * P.size * 0.6;
  const word = (fire: boolean) => (
    <div style={{ position: "absolute", left: x, top: textY, transform: "translate(-50%,-50%)" }}>
      <div style={{ fontFamily: "Yeonsung", fontSize: P.size, color: P.color, WebkitTextStroke: P.weight > 0 ? `${P.weight}px ${P.color}` : undefined, whiteSpace: "nowrap", lineHeight: 1, opacity: k, filter: k < 1 ? `blur(${(1 - k) * P.blur}px)` : undefined }}>{hz(text)}</div>
      {fire && Array.from({ length: Math.round(P.flameN) }).map((_, i) => {
        const n = Math.max(1, Math.round(P.flameN)), u = (i + 0.5) / n + (random(`fl${i}`) - 0.5) * (0.5 / n), top = i % 2 === 0;
        return <Flame key={i} x={tw * u} y={top ? P.size * 0.12 : P.size * 0.85 - random(`fy${i}`) * P.size * 0.3} s={P.flameSize * (0.75 + 0.5 * random(`fs${i}`))} f={f} loop={P.flameLoop} seed={`fl${i}`} />;
      })}
    </div>
  );
  const plain = <div style={{ position: "absolute", inset: 0 }}>{f >= at && word(false)}</div>;
  const burning = <div style={{ position: "absolute", inset: 0 }}>{word(true)}</div>;
  return (
    <AbsoluteFill>
      {fireAt === undefined ? plain : <SmokeSwap x={x} y={textY} w={tw * 1.4} h={P.size * 2.2} at={fireAt} a={plain} b={burning} seed="tbc" />}
      <Img src={src(img)} style={{ position: "absolute", left: x - charW / 2, top: charTop, width: charW, transformOrigin: "50% 100%", transform: `scale(${cs})` }} />
    </AbsoluteFill>
  );
};

// ══ 14. 배경 디포커스 + 한자 메달리온 [ref4-samsung 9:35 三星 상호 유래] ═══════════════════
// 배경 블러 0→≈18px ≈10f. 흰 원판(1080p 실측 지름 ≈470)에 굵은 붓 한자 + 음(석 삼), 0→1.1→1.0 ≈5f.
// 보라 리본 #5A4FB0 왼→오 펼침 ≈4f(설명). 다음 원판 +≈2.8s. out 에서 크로스페이드 ≈8f + 줌 풀백.
export const HanjaMedallionParams = z.object({
  bgBlurLen: num(10, 0, 40, 1, "배경 블러 길이", "timing", "f"),
  bgBlur: num(18, 0, 50, 1, "배경 블러", "look", "px"),
  popLen: num(5, 1, 20, 1, "원판 팝 길이", "timing", "f"),
  over: num(1.1, 1, 1.5, 0.01, "오버슈트(배)", "motion", "배"),
  ribbonLen: num(4, 1, 20, 1, "리본 펼침 길이", "timing", "f"),
  ribbonDelay: num(3, 0, 30, 1, "리본 지연", "timing", "f"),
  outLen: num(8, 1, 30, 1, "퇴장 크로스페이드", "timing", "f"),
  d: num(470, 150, 800, 5, "원판 지름", "size", "px"),
  hanjaSize: num(300, 60, 500, 5, "한자 크기", "size", "px"),
  ribbonSize: num(56, 16, 100, 1, "리본 글자 크기", "size", "px"),
  ribbon: col("#5A4FB0", "리본 색"),
  disc: col("#FBFAF7", "원판 색"),
});
export type HanjaMedallionP = z.infer<typeof HanjaMedallionParams>;
export const HanjaMedallion: React.FC<{ items: { hanja: string; reading: [string, string]; x: number; y: number; at: number }[]; ribbon?: { text: string; x: number; y: number; at: number }; at: number; out?: number; children?: RN; p?: Partial<HanjaMedallionP> }> = ({ items, ribbon, at, out, children, p }) => {
  const P = def(HanjaMedallionParams, p);
  const f = useCurrentFrame();
  const bb = P.bgBlurLen > 0 ? lerp(f, at, at + P.bgBlurLen, 0, P.bgBlur) : f >= at ? P.bgBlur : 0;
  const ok = out !== undefined ? lerp(f, out, out + P.outLen, 1, 0) : 1;
  const zm = out !== undefined ? lerp(f, out, out + P.outLen, 1, 1.3, Easing.in(Easing.quad)) : 1;
  const ra = ribbon ? ribbon.at + P.ribbonDelay : 0;
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ filter: bb > 0.2 ? `blur(${bb}px)` : undefined, transform: bb > 0.2 ? "scale(1.04)" : undefined }}>{children}</AbsoluteFill>
      <AbsoluteFill style={{ opacity: ok, transform: `scale(${zm})` }}>
        {items.map((it, i) => {
          if (f < it.at) return null;
          const s = kf(f, it.at, [0, P.popLen * 0.6, P.popLen], [0, P.over, 1], Easing.out(Easing.quad));
          const mb = kf(f, it.at, [0, P.popLen], [8, 0]);
          return (
            <div key={i} style={{ position: "absolute", left: it.x - P.d / 2, top: it.y - P.d / 2, width: P.d, height: P.d, borderRadius: "50%", background: P.disc, boxShadow: "0 0 30px rgba(255,255,255,0.6)",
              transform: `scale(${s})`, filter: mb > 0.3 ? `blur(${mb}px)` : undefined, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
              <div style={{ fontSize: P.hanjaSize, lineHeight: 0.9, color: "#111", marginTop: -P.d * 0.08 }}>{hz(it.hanja)}</div>
              <div style={{ position: "absolute", bottom: P.d * 0.1, fontFamily: "Yeonsung", color: "#222", whiteSpace: "nowrap" }}>
                <span style={{ fontSize: P.d * 0.07, marginRight: 8 }}>{it.reading[0]}</span><span style={{ fontSize: P.d * 0.12 }}>{it.reading[1]}</span>
              </div>
            </div>
          );
        })}
        {ribbon && f >= ra && (
          <div style={{ position: "absolute", left: ribbon.x, top: ribbon.y, transform: "translate(-50%,-50%)", clipPath: `inset(0 ${100 - lerp(f, ra, ra + P.ribbonLen, 0, 100, QUART_OUT)}% 0 0)` }}>
            <div style={{ background: P.ribbon, padding: `8px ${P.ribbonSize * 1.3}px`, fontFamily: "Yeonsung", fontSize: P.ribbonSize, color: "#fff", whiteSpace: "nowrap",
              clipPath: `polygon(0 0, 100% 0, calc(100% - ${P.ribbonSize * 0.6}px) 50%, 100% 100%, 0 100%, ${P.ribbonSize * 0.6}px 50%)` }}>{hz(ribbon.text)}</div>
          </div>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ══ 15. 사선 구호 배너 [ref4-samsung 22:40 '무너진 경제를 재건하자'] ═══════════════════════
// 빨간 사각 배너 #E0303C ~620×260, -8° 회전, 흰 브러시체 2줄 ≈70px, 캐릭터 옆(뒤)에 붙음. ≈6f 스케일 팝 + 모서리 반짝이.
export const SloganBannerParams = z.object({
  popLen: num(6, 1, 20, 1, "팝 길이", "timing", "f"),
  from: num(0.3, 0, 1, 0.05, "시작 크기(배)", "motion", "배"),
  over: num(1.08, 1, 1.5, 0.01, "오버슈트(배)", "motion", "배"),
  rot: num(-8, -30, 30, 0.5, "기울기", "motion", "°"),
  w: num(620, 200, 1200, 10, "배너 너비", "size", "px"),
  h: num(260, 80, 600, 10, "배너 높이", "size", "px"),
  size: num(70, 24, 140, 2, "글자 크기", "size", "px"),
  sparkle: flag(true, "모서리 반짝이", "look"),
  color: col("#E0303C", "배너 색"),
  textColor: col("#ffffff", "글자 색"),
});
export type SloganBannerP = z.infer<typeof SloganBannerParams>;
export const SloganBanner: React.FC<{ lines: string[]; x: number; y: number; at: number; p?: Partial<SloganBannerP> }> = ({ lines, x, y, at, p }) => {
  const P = def(SloganBannerParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const s = kf(f, at, [0, P.popLen * 0.65, P.popLen], [P.from, P.over, 1], Easing.out(Easing.quad));
  const g = f - at - P.popLen;
  const tw = g > 0 ? Math.max(0, Math.sin((g / 14) * Math.PI)) * (g < 42 ? 1 : 0) : 0;
  return (
    <div style={{ position: "absolute", left: x, top: y, width: P.w, height: P.h, transform: `translate(-50%,-50%) rotate(${P.rot}deg) scale(${s})` }}>
      <div style={{ position: "absolute", inset: 0, background: P.color, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", fontFamily: "Yeonsung", fontSize: P.size, color: P.textColor, lineHeight: 1.15 }}>
        {lines.map((l, i) => <div key={i} style={{ whiteSpace: "nowrap" }}>{hz(l)}</div>)}
      </div>
      {P.sparkle && tw > 0.02 && (
        <svg width={80} height={80} viewBox="-50 -50 100 100" style={{ position: "absolute", right: -30, top: -34, transform: `scale(${0.4 + tw * 0.6})`, opacity: tw }}>
          <path d="M0,-50 C6,-8 8,-6 50,0 C8,6 6,8 0,50 C-6,8 -8,6 -50,0 C-8,-6 -6,-8 0,-50Z" fill="#fff" />
        </svg>
      )}
    </div>
  );
};

// ══ 16. 반투명 자막 띠(구 포맷) [ref1 0:45–14:28] ═════════════════════════════════════
// 하단 전폭 밝은 회색 반투명 띠 y 936–1020(≈84px) 위 검정 굵은 고딕 ≈44px. 등장·퇴장 애니 없이 하드 교체.
export const LegacySubtitleBandParams = z.object({
  top: num(936, 700, 1060, 1, "띠 위 y", "size", "px"),
  h: num(84, 30, 160, 1, "띠 높이", "size", "px"),
  size: num(44, 16, 80, 1, "글자 크기", "size", "px"),
  alpha: num(0.78, 0, 1, 0.02, "띠 불투명도", "look"),
  bg: col("#D2D2D2", "띠 색"),
  color: col("#111111", "글자 색"),
});
export type LegacySubtitleBandP = z.infer<typeof LegacySubtitleBandParams>;
export const LegacySubtitleBand: React.FC<{ subs: Sub[]; p?: Partial<LegacySubtitleBandP> }> = ({ subs, p }) => {
  const P = def(LegacySubtitleBandParams, p);
  const f = useCurrentFrame();
  const t = f / 30;
  const cur = subs.find((s) => t >= s.t0 && t < s.t1);
  if (!cur) return null;
  return (
    <div style={{ position: "absolute", left: 0, right: 0, top: P.top, height: P.h, background: hexA(P.bg, P.alpha), display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "NeoHv", fontSize: P.size, color: P.color, whiteSpace: "nowrap" }}>{hz(cur.text)}</div>
  );
};

// ══ 17. 출처 칩 드로우온 [ref4-apple 1:07:12 'GettyImages'] ═══════════════════════════════
// 흰 윤곽 삼각 화살표(왼쪽 향함, ~70×90) + 흰 2px 테두리 상자 ~385×78(반투명 검정). 화살표 선 ~3f →
// 상자 너비 0→100% 오른쪽 확장 ~6f ease-out → 약 8f 뒤 글자 알파 ~3f. 위치 x1405–1865, y838–918.
export const SourceChipDrawOnParams = z.object({
  arrowLen: num(3, 1, 20, 1, "화살표 그리는 시간", "timing", "f"),
  boxLen: num(6, 1, 30, 1, "상자 확장 시간", "timing", "f"),
  textDelay: num(8, 0, 30, 1, "글자 지연(상자 뒤)", "timing", "f"),
  textLen: num(3, 1, 20, 1, "글자 페이드", "timing", "f"),
  x: num(1405, 0, 1900, 1, "왼쪽 x", "size", "px"),
  y: num(838, 0, 1060, 1, "위 y", "size", "px"),
  arrowW: num(70, 20, 160, 1, "화살표 너비", "size", "px"),
  boxW: num(385, 100, 900, 5, "상자 너비", "size", "px"),
  h: num(78, 30, 160, 1, "높이", "size", "px"),
  size: num(36, 14, 70, 1, "글자 크기", "size", "px"),
  stroke: num(2, 1, 8, 0.5, "선 두께", "size", "px"),
  fillAlpha: num(0.45, 0, 1, 0.05, "상자 채움 불투명도", "look"),
  color: col("#ffffff", "선·글자 색"),
});
export type SourceChipDrawOnP = z.infer<typeof SourceChipDrawOnParams>;
export const SourceChipDrawOn: React.FC<{ text: string; at: number; p?: Partial<SourceChipDrawOnP> }> = ({ text, at, p }) => {
  const P = def(SourceChipDrawOnParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const ak = lerp(f, at, at + P.arrowLen, 0, 1, Easing.linear);
  const b0 = at + P.arrowLen, bk = lerp(f, b0, b0 + P.boxLen, 0, 1, Easing.out(Easing.cubic));
  const t0 = b0 + P.boxLen + P.textDelay, tk = lerp(f, t0, t0 + P.textLen, 0, 1);
  const aw = P.arrowW, h = P.h, ah = h * 1.15, per = aw + 2 * Math.hypot(aw, ah / 2);
  return (
    <div style={{ position: "absolute", left: P.x, top: P.y }}>
      <svg width={aw + 4} height={ah + 4} style={{ position: "absolute", left: -2, top: (h - ah) / 2 - 2, overflow: "visible" }}>
        <polygon points={`${aw + 2},2 2,${ah / 2 + 2} ${aw + 2},${ah + 2}`} fill="none" stroke={P.color} strokeWidth={P.stroke} strokeLinejoin="round"
          strokeDasharray={per} strokeDashoffset={per * (1 - ak)} />
      </svg>
      <div style={{ position: "absolute", left: aw + 6, top: 0, width: P.boxW * bk, height: h, boxSizing: "border-box", border: bk > 0 ? `${P.stroke}px solid ${P.color}` : undefined, background: `rgba(0,0,0,${P.fillAlpha})`, overflow: "hidden" }}>
        <div style={{ position: "absolute", left: 0, width: P.boxW, top: 0, height: h - 2 * P.stroke, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "NeoEb", fontSize: P.size, color: P.color, opacity: tk, whiteSpace: "nowrap" }}>{text}</div>
      </div>
    </div>
  );
};

// ══ 18. 탭형 챕터 바 HUD(사각 스케치 로고) [ref4-hyundai 28:20 / 1:00 / 48:10] ═══════════════
// 로고 사각 x28–220,y25–137. 바 x250–1828, y45–112(외곽선 ~3px #9A9696). 칸 수 = 챕터 수(에피소드마다 리셋).
// 활성 칸 ≈#A09A9A 채움 + 흰 볼드 ~30px, 비활성 회색 레귤러. 활성 교체는 하드(이동 애니 없음). dark = 다크 반전 모드.
export const TabbedChapterHUDParams = z.object({
  barX0: num(250, 0, 800, 1, "바 왼쪽 x", "size", "px"),
  barX1: num(1828, 1000, 1920, 1, "바 오른쪽 x", "size", "px"),
  barTop: num(45, 0, 200, 1, "바 위 y", "size", "px"),
  barH: num(67, 30, 140, 1, "바 높이", "size", "px"),
  strokeW: num(3, 1, 10, 0.5, "외곽선 두께", "size", "px"),
  activeSize: num(30, 12, 60, 1, "활성 글자 크기", "size", "px"),
  idleSize: num(28, 12, 60, 1, "비활성 글자 크기", "size", "px"),
  switchLen: num(0, 0, 20, 1, "활성 교체 페이드(0=하드)", "timing", "f"),
  stroke: col("#9A9696", "외곽선 색"),
  fill: col("#A09A9A", "활성 칸 채움"),
  idleColor: col("#B4B0AD", "비활성 글자 색"),
  darkFill: col("#000000", "다크: 바 채움"),
  darkIdle: col("#E6E6E6", "다크: 비활성 글자"),
});
export type TabbedChapterHUDP = z.infer<typeof TabbedChapterHUDParams>;
export const TabbedChapterHUD: React.FC<{ chapters: string[]; active?: number; activeAt?: [number, number][]; dark?: boolean; logo?: boolean; p?: Partial<TabbedChapterHUDP> }> = ({ chapters, active = 0, activeAt, dark = false, logo = true, p }) => {
  const P = def(TabbedChapterHUDParams, p);
  const f = useCurrentFrame();
  let act = active, since = -999;
  (activeAt || []).forEach(([fr, i]) => { if (f >= fr) { act = i; since = fr; } });
  const n = Math.max(1, chapters.length), bw = P.barX1 - P.barX0, cw = bw / n;
  const fk = P.switchLen > 0 ? lerp(f, since, since + P.switchLen, 0, 1) : 1;
  const r = P.barH * 0.3;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {logo && <Img src={staticFile("ui/logo.png")} style={{ position: "absolute", left: 28, top: 25, width: 192, height: 112 }} />}
      <div style={{ position: "absolute", left: P.barX0, top: P.barTop, width: bw, height: P.barH, borderRadius: r, boxSizing: "border-box", border: `${P.strokeW}px solid ${dark ? "#C8C6C4" : P.stroke}`, background: dark ? P.darkFill : "transparent", overflow: "hidden" }}>
        <div style={{ position: "absolute", left: act * cw - P.strokeW, top: -P.strokeW, width: cw + (act === 0 || act === n - 1 ? P.strokeW : 0), height: P.barH, borderRadius: r * 0.8, background: P.fill, opacity: fk }} />
        {chapters.map((c, i) => (
          <div key={i} style={{ position: "absolute", left: i * cw - P.strokeW, width: cw, top: -P.strokeW, height: P.barH, display: "flex", alignItems: "center", justifyContent: "center", whiteSpace: "nowrap",
            fontFamily: i === act ? "NeoHv" : "NeoEb", fontWeight: i === act ? 900 : 400, fontSize: i === act ? P.activeSize : P.idleSize, color: i === act ? "#fff" : dark ? P.darkIdle : P.idleColor, opacity: i === act ? 1 : 0.95 }}>{hz(c)}</div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

// ══ 19. HUD 다크 반전 [ref4-hyundai 1:53:40] ═══════════════════════════════════════════
// 어두운 씬(컷 단위)에서 상단 챕터 탭 바를 흑색 채움 + 흰 글씨로 반전, 밝은 씬은 투명 + 회색 스트로크. 로고 배지는 고정.
export const HUDDarkInvertParams = z.object({
  fadeLen: num(0, 0, 12, 1, "반전 전환(0=컷 단위 하드)", "timing", "f"),
  topBand: flag(true, "다크 씬 상단 검정 띠", "look"),
  bandH: num(160, 0, 300, 2, "상단 검정 띠 높이", "size", "px"),
  darkFill: col("#000000", "바 채움 색"),
  darkIdle: col("#E6E6E6", "비활성 글자 색"),
  activeFill: col("#A8A4A0", "활성 칸 채움"),
});
export type HUDDarkInvertP = z.infer<typeof HUDDarkInvertParams>;
export const HUDDarkInvert: React.FC<{ chapters: string[]; active: number; darkCuts: [number, number][]; p?: Partial<HUDDarkInvertP> }> = ({ chapters, active, darkCuts, p }) => {
  const P = def(HUDDarkInvertParams, p);
  const f = useCurrentFrame();
  const cut = darkCuts.find(([a, b]) => f >= a && f < b);
  const k = cut ? (P.fadeLen > 0 ? lerp(f, cut[0], cut[0] + P.fadeLen, 0, 1) : 1) : 0;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {P.topBand && k > 0 && <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: P.bandH, background: "#000", opacity: k }} />}
      <AbsoluteFill style={{ opacity: 1 - k }}><TabbedChapterHUD chapters={chapters} active={active} p={{ fill: P.activeFill }} /></AbsoluteFill>
      {k > 0 && <AbsoluteFill style={{ opacity: k }}><TabbedChapterHUD chapters={chapters} active={active} dark p={{ fill: P.activeFill, darkFill: P.darkFill, darkIdle: P.darkIdle }} /></AbsoluteFill>}
    </AbsoluteFill>
  );
};

// ══ 20. 초기 포맷 v1 [ref4-cocacola 0:34 '1. 존 펨버턴' / '1831년'] ═════════════════════════
// 채널 초기 포맷 한 벌: 사각 스케치 로고 + 탭형 챕터바(활성 채움 하드 이동) + 흰 배경 챕터카드('N. 챕터명', 검정 볼드)
// + 세이지 연도 인터스티셜(음절 단위 타자 ~5f) + 하단 전폭 반투명 흰 자막띠(검정 볼드). segs 를 순서대로 하드컷.
export const LegacyFormatParams = z.object({
  typePer: num(5, 1, 15, 0.5, "연도 타자 글자당", "timing", "f"),
  cardSize: num(60, 24, 120, 2, "챕터카드 글자 크기", "size", "px"),
  yearSize: num(110, 40, 200, 2, "연도 글자 크기", "size", "px"),
  subH: num(66, 30, 120, 1, "자막띠 높이", "size", "px"),
  subSize: num(34, 14, 60, 1, "자막 글자 크기", "size", "px"),
  subAlpha: num(0.72, 0, 1, 0.02, "자막띠 불투명도", "look"),
  cardBg: col("#FBF6F3", "챕터카드 배경"),
  sage: col("#C2CCC3", "연도 카드 배경"),
});
export type LegacyFormatP = z.infer<typeof LegacyFormatParams>;
export type LegacySeg = { kind: "card" | "year" | "scene"; dur: number; text?: string; chapter?: number; sub?: string; content?: RN };
export const LegacyFormat: React.FC<{ chapters: string[]; segs: LegacySeg[]; p?: Partial<LegacyFormatP> }> = ({ chapters, segs, p }) => {
  const P = def(LegacyFormatParams, p);
  const f = useCurrentFrame();
  let t = 0, cur: LegacySeg | undefined, from = 0, chap = 0;
  for (const s of segs) { if (s.chapter !== undefined && f >= t) chap = s.chapter; if (f >= t && f < t + s.dur) { cur = s; from = t; } t += s.dur; }
  if (!cur) cur = segs[segs.length - 1];
  const g = f - from;
  return (
    <AbsoluteFill style={{ background: "#fff" }}>
      {cur?.kind === "card" && (
        <AbsoluteFill style={{ background: P.cardBg, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <GrainX op={0.05} /><div style={{ fontFamily: "NeoHv", fontSize: P.cardSize, color: "#141414" }}>{hz(cur.text || "")}</div>
        </AbsoluteFill>
      )}
      {cur?.kind === "year" && (
        <AbsoluteFill style={{ opacity: 1 }}>
          <SageDateCard text={cur.text || ""} at={from} p={{ perGlyph: P.typePer, size: P.yearSize, bg: P.sage, blank: 0 }} />
        </AbsoluteFill>
      )}
      {cur?.kind === "scene" && <AbsoluteFill>{cur.content}</AbsoluteFill>}
      <TabbedChapterHUD chapters={chapters} active={chap} p={{ activeSize: 24, idleSize: 22, fill: "#9a9a9a", idleColor: "#C4C0BD" }} />
      {cur?.sub && g >= 0 && (
        <div style={{ position: "absolute", left: 0, right: 0, top: 1000 - P.subH, height: P.subH, background: `rgba(255,255,255,${P.subAlpha})`, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "NeoHv", fontSize: P.subSize, color: "#111" }}>{hz(cur.sub)}</div>
      )}
    </AbsoluteFill>
  );
};

// ══ 21. 시대별 배경 팔레트 전환 [ref4-samsung 0:40 / 1:05:00 / 1:30:50] ═══════════════════════
// 통합편 안에서 배경 기본색이 파트마다 바뀜: 세이지 → 크림 → 블루그레이, 감정 장면은 단색 풀필드(진홍·코발트·노랑).
// HUD·자막띠는 전 구간 동일. eras 의 color 에 팔레트 이름 또는 HEX. 전환은 컷 단위(fadeLen 0).
export const EraPaletteParams = z.object({
  fadeLen: num(0, 0, 30, 1, "전환 길이(0=하드컷)", "timing", "f"),
  grain: num(0.07, 0, 0.4, 0.01, "종이 그레인", "look"),
  sage: col("#C2CCC3", "세이지(1~4편)"),
  cream: col("#FEF9F6", "크림(제품사 파트)"),
  bluegray: col("#9DA5B3", "블루그레이(후반)"),
  crimson: col("#93403F", "감정: 진홍"),
  cobalt: col("#2F4FA8", "감정: 코발트"),
  yellow: col("#FBD27D", "감정: 노랑(VS)"),
});
export type EraPaletteP = z.infer<typeof EraPaletteParams>;
export type EraKey = "sage" | "cream" | "bluegray" | "crimson" | "cobalt" | "yellow";
export const EraPalette: React.FC<{ eras: { at: number; color: EraKey | string }[]; children?: RN; overlay?: RN; p?: Partial<EraPaletteP> }> = ({ eras, children, overlay, p }) => {
  const P = def(EraPaletteParams, p);
  const f = useCurrentFrame();
  const res = (c: string) => (c.startsWith("#") ? c : (P as any)[c] ?? c);
  let i = 0;
  eras.forEach((e, j) => { if (f >= e.at) i = j; });
  const cur = res(eras[i]?.color ?? "sage"), prev = i > 0 ? res(eras[i - 1].color) : cur;
  const k = P.fadeLen > 0 && i > 0 ? lerp(f, eras[i].at, eras[i].at + P.fadeLen, 0, 1, Easing.linear) : 1;
  return (
    <AbsoluteFill style={{ background: prev }}>
      <AbsoluteFill style={{ background: cur, opacity: k }} />
      <GrainX op={P.grain} seed={7} />
      <AbsoluteFill>{children}</AbsoluteFill>
      {overlay}
    </AbsoluteFill>
  );
};

// ══ 22. 채널 로고 스탬프 인트로(구포맷) [ref4-samsung 0:26] ═════════════════════════════════
// 크림 배경 중앙에 선화 인물 + '세상의 모든 지식' 스탬프 로고가 점에서 커짐(0→1.05→1.0 ≈7f, 1080p 실측 ≈980×570),
// +≈20f '구독' 체크박스 팝, +≈15f '좋아요' 팝. 전체 ≈2.3s 후 하드컷(현행 HUD 로고 스팅과 다른 구포맷).
export const LegacyLogoIntroParams = z.object({
  logoLen: num(7, 1, 30, 1, "로고 커지는 길이", "timing", "f"),
  over: num(1.05, 1, 1.4, 0.01, "로고 오버슈트(배)", "motion", "배"),
  subDelay: num(20, 0, 60, 1, "구독 지연(로고 뒤)", "timing", "f"),
  likeDelay: num(15, 0, 60, 1, "좋아요 지연(구독 뒤)", "timing", "f"),
  popLen: num(5, 1, 20, 1, "아이콘 팝 길이", "timing", "f"),
  logoW: num(980, 300, 1400, 10, "로고 너비", "size", "px"),
  logoY: num(404, 200, 700, 2, "로고 중심 y", "size", "px"),
  bg: col("#FBF7F2", "배경 색"),
});
export type LegacyLogoIntroP = z.infer<typeof LegacyLogoIntroParams>;
export const LegacyLogoIntro: React.FC<{ at?: number; p?: Partial<LegacyLogoIntroP> }> = ({ at = 0, p }) => {
  const P = def(LegacyLogoIntroParams, p);
  const f = useCurrentFrame();
  const L = pos(P.logoLen);
  const s = f < at ? 0 : kf(f, at, [0, L * 6 / 7, L], [0.02, P.over, 1], Easing.out(Easing.quad));
  const sa = at + L + P.subDelay, la = sa + P.likeDelay;
  const pop = (a: number) => (f < a ? 0 : kf(f, a, [0, P.popLen * 0.6, P.popLen], [0.3, 1.1, 1], Easing.out(Easing.quad)));
  const lw = P.logoW, lh = lw * (588 / 1005);
  return (
    <AbsoluteFill style={{ background: P.bg }}>
      <GrainX op={0.05} />
      {s > 0 && <Img src={staticFile("ui/sting_logo.png")} style={{ position: "absolute", left: W / 2 - lw / 2, top: P.logoY - lh / 2, width: lw, height: lh, transform: `scale(${s})` }} />}
      {pop(sa) > 0 && <Img src={staticFile("ui/sting_sub.png")} style={{ position: "absolute", left: 395, top: 832, width: 440, height: 173, transform: `scale(${pop(sa)})` }} />}
      {pop(la) > 0 && <Img src={staticFile("ui/sting_like.png")} style={{ position: "absolute", left: 1040, top: 820, width: 520, height: 190, transform: `scale(${pop(la)})`, mixBlendMode: "multiply" }} />}
    </AbsoluteFill>
  );
};
