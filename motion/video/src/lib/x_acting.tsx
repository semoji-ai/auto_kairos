// 도감 x_acting — 캐릭터 연기 · 감정/효과 FX (레퍼런스 ref1·ref2·ref4 프레임 대조 구현)
// 모든 좌표는 화면(1920×1080) 절대 px. 결정론(remotion random) 전용. 방사형 광선 금지 → 원형 글로우·링.
import { SemojiWalker, SemojiRigParams, SemojiRigP, RigPose } from "./semoji_rig";
import { CAST, CastId, RigJson, prop, propSize, propH } from "./kit";
import React from "react";
import { AbsoluteFill, Img, Easing, random, useCurrentFrame, staticFile } from "remotion";
import { z } from "zod";
import { W, H, lerp, kf, EXPO_OUT, hz, src } from "../fx";
import { num, col, flag, choice, def } from "../params/p";
import { talkOpenRandom } from "./semoji_rig";

type RN = React.ReactNode;
type Pt = [number, number];
const TAU = Math.PI * 2;
const D2R = Math.PI / 180;
const EASY = Easing.bezier(0.33, 0, 0.67, 1);
/** 0→1→0 사인 한 번 */
const bump = (t: number) => (t <= 0 || t >= 1 ? 0 : Math.sin(t * Math.PI));
/** 핑퐁 이지이지(0..1) */
const pp01 = (f: number, period: number, phase = 0) => {
  const k = Math.max(0, f + phase), seg = Math.floor(k / period), t = (k % period) / period, e = EASY(t);
  return seg % 2 === 0 ? e : 1 - e;
};
const Full: React.FC<{ children: RN; style?: React.CSSProperties }> = ({ children, style }) => (
  <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ position: "absolute", left: 0, top: 0, overflow: "visible", pointerEvents: "none", ...style }}>{children}</svg>
);
/** 블러 팝 (scale from→1, blur→0, 불투명 0→1) */
const blurPop = (f: number, at: number, len: number, from = 1.3, blur = 10) => ({
  s: kf(f, at, [0, len], [from, 1], EXPO_OUT),
  blur: kf(f, at, [0, len], [blur, 0], EXPO_OUT),
  op: kf(f, at, [0, Math.max(1, len * 0.5)], [0, 1]),
});

// ══ 0. 퍼펫 리그: 플랫 2D 세모지 인물(외곽선 없음) ═══════════════════════════════
// 로컬 좌표 400×700, 발바닥 중앙 (200,700). 팔은 2관절(어깨 a1, 팔꿈치 a2 상대), 0°=아래, 90°=바깥 수평, 180°=위.
export type Eyes = "dot" | "closed" | "squint" | "sparkle" | "sleepy" | "angry" | "wide";
export type Mouth = "smile" | "open" | "closed" | "grit" | "o" | "frown" | "none";
export type Hand = "fist" | "palm" | "glove" | "none";
export type Arm = { a1: number; a2?: number; hand?: Hand; color?: string; item?: RN; itemRot?: number };
export type PuppetLook = { skin?: string; shirt?: string; pants?: string; hair?: string; hairStyle?: "short" | "bob" | "bald" | "long" | "none"; tie?: string; collar?: string; blush?: boolean };
export type PuppetProps = PuppetLook & {
  /** 발바닥 중앙(화면 px) */ x: number; y: number;
  /** 전신(로컬 700) 화면 높이 */ h: number;
  eyes?: Eyes; mouth?: Mouth; brows?: "none" | "angry" | "worried";
  armL?: Arm; armR?: Arm; legs?: boolean; legL?: number; legR?: number;
  headTilt?: number; bodyTilt?: number; flip?: boolean; bob?: number;
  /** 로컬 좌표 오버레이(머리 앞) / 몸 뒤 */ extra?: RN; under?: RN; face?: RN;
  style?: React.CSSProperties; opacity?: number;
};
const SH_L: Pt = [112, 290], SH_R: Pt = [288, 290], UA = 108, FA = 100, ARMW = 44;
const dirOf = (side: -1 | 1, a: number): Pt => [side * Math.sin(a * D2R), Math.cos(a * D2R)];
/** 팔 관절 좌표(로컬) */
export const armPts = (side: -1 | 1, arm: Arm) => {
  const s = side < 0 ? SH_L : SH_R, d1 = dirOf(side, arm.a1), d2 = dirOf(side, arm.a1 + (arm.a2 ?? 0));
  const e: Pt = [s[0] + d1[0] * UA, s[1] + d1[1] * UA];
  const hnd: Pt = [e[0] + d2[0] * FA, e[1] + d2[1] * FA];
  return { s, e, h: hnd, ang: (Math.atan2(d2[1], d2[0]) * 180) / Math.PI - 90 };
};
/** 로컬 → 화면 좌표 (tilt·flip 무시한 근사) */
export const puppetToScreen = (p: { x: number; y: number; h: number; flip?: boolean }, lp: Pt): Pt => {
  const k = p.h / 700;
  return [p.x + (p.flip ? -1 : 1) * (lp[0] - 200) * k, p.y + (lp[1] - 700) * k];
};
const HandShape: React.FC<{ kind: Hand; skin: string; color?: string }> = ({ kind, skin, color }) => {
  if (kind === "none") return null;
  if (kind === "fist") return <><circle cx={0} cy={6} r={27} fill={skin} /><rect x={-20} y={-6} width={40} height={10} rx={5} fill="rgba(0,0,0,0.08)" /></>;
  if (kind === "glove") return (
    <g>
      <rect x={-26} y={-18} width={52} height={30} rx={8} fill="#f4f1ea" />
      <ellipse cx={0} cy={40} rx={50} ry={46} fill={color || "#d83a3a"} />
      <ellipse cx={-30} cy={30} rx={20} ry={24} fill={color || "#d83a3a"} />
      <ellipse cx={14} cy={30} rx={22} ry={14} fill="rgba(255,255,255,0.22)" />
    </g>
  );
  // palm: 손바닥 정면(손가락 +y 방향)
  return (
    <g fill={skin}>
      <rect x={-30} y={-6} width={60} height={56} rx={22} />
      {[-22, -7.5, 7.5, 22].map((fx, i) => <rect key={i} x={fx - 7} y={30} width={14} height={i === 0 || i === 3 ? 42 : 52} rx={7} />)}
      <rect x={-50} y={0} width={14} height={40} rx={7} transform="rotate(-40 -40 10)" />
    </g>
  );
};
const ArmG: React.FC<{ side: -1 | 1; arm: Arm; sleeve: string; skin: string }> = ({ side, arm, sleeve, skin }) => {
  const { s, e, h, ang } = armPts(side, arm);
  return (
    <g>
      <path d={`M${s[0]},${s[1]} L${e[0]},${e[1]} L${h[0]},${h[1]}`} stroke={sleeve} strokeWidth={ARMW} strokeLinecap="round" strokeLinejoin="round" fill="none" />
      <g transform={`translate(${h[0]},${h[1]}) rotate(${ang}) ${side < 0 ? "scale(-1,1)" : ""}`}>
        {arm.item && <g transform={`rotate(${arm.itemRot ?? 0})`}>{arm.item}</g>}
        <HandShape kind={arm.hand ?? "fist"} skin={skin} color={arm.color} />
      </g>
    </g>
  );
};
const EyeG: React.FC<{ kind: Eyes; x: number; side: -1 | 1 }> = ({ kind, x, side }) => {
  const y = 150, ink = "#2a1d1a";
  switch (kind) {
    case "closed": return <path d={`M${x - 14},${y} Q${x},${y + 12} ${x + 14},${y}`} stroke={ink} strokeWidth={5} fill="none" strokeLinecap="round" />;
    case "sleepy": return <path d={`M${x - 16},${y + 2} Q${x},${y - 10} ${x + 16},${y + 2}`} stroke={ink} strokeWidth={5} fill="none" strokeLinecap="round" />;
    case "squint": return <path d={side < 0 ? `M${x - 12},${y - 12} L${x + 10},${y} L${x - 12},${y + 12}` : `M${x + 12},${y - 12} L${x - 10},${y} L${x + 12},${y + 12}`} stroke={ink} strokeWidth={6} fill="none" strokeLinecap="round" strokeLinejoin="round" />;
    case "sparkle": return <g><circle cx={x} cy={y} r={17} fill="#fff" /><circle cx={x} cy={y} r={17} fill="none" stroke={ink} strokeWidth={4} /><circle cx={x} cy={y + 2} r={7} fill="#3b7f5a" /><circle cx={x + 5} cy={y - 5} r={4} fill="#fff" /></g>;
    case "wide": return <g><ellipse cx={x} cy={y} rx={13} ry={16} fill="#fff" /><circle cx={x} cy={y} r={7} fill={ink} /></g>;
    case "angry": return <ellipse cx={x} cy={y + 2} rx={8} ry={10} fill={ink} />;
    default: return <g><ellipse cx={x} cy={y} rx={9} ry={12} fill={ink} /><circle cx={x + 3} cy={y - 4} r={3} fill="#fff" /></g>;
  }
};
const MouthG: React.FC<{ kind: Mouth }> = ({ kind }) => {
  const x = 200, y = 208, ink = "#6b2323";
  switch (kind) {
    case "open": return <g><path d={`M${x - 24},${y - 6} Q${x},${y - 12} ${x + 24},${y - 6} Q${x + 20},${y + 26} ${x},${y + 28} Q${x - 20},${y + 26} ${x - 24},${y - 6}Z`} fill={ink} /><ellipse cx={x} cy={y + 18} rx={12} ry={7} fill="#e46d6d" /></g>;
    case "closed": return <path d={`M${x - 16},${y + 2} L${x + 16},${y + 2}`} stroke={ink} strokeWidth={5} strokeLinecap="round" />;
    case "grit": return <g><rect x={x - 28} y={y - 10} width={56} height={24} rx={8} fill="#fff" /><path d={`M${x - 28},${y + 2} L${x + 28},${y + 2} M${x - 10},${y - 10} L${x - 10},${y + 14} M${x + 10},${y - 10} L${x + 10},${y + 14}`} stroke="#b9a9a0" strokeWidth={2.5} /></g>;
    case "o": return <ellipse cx={x} cy={y + 6} rx={11} ry={14} fill={ink} />;
    case "frown": return <path d={`M${x - 18},${y + 10} Q${x},${y - 6} ${x + 18},${y + 10}`} stroke={ink} strokeWidth={5} fill="none" strokeLinecap="round" />;
    case "none": return null;
    default: return <path d={`M${x - 22},${y - 2} Q${x},${y + 22} ${x + 22},${y - 2}Z`} fill={ink} />;
  }
};
const HairG: React.FC<{ style: PuppetLook["hairStyle"]; c: string }> = ({ style, c }) => {
  if (style === "bald" || style === "none") return null;
  if (style === "bob" || style === "long") return (
    <g fill={c}>
      <path d="M104,170 C92,70 150,48 200,48 C252,48 310,70 296,170 L300,250 L270,250 L276,130 C240,112 170,112 124,130 L130,250 L100,250Z" />
      {style === "long" && <path d="M100,240 L96,330 L150,330 L130,240Z M300,240 L304,330 L250,330 L270,240Z" />}
    </g>
  );
  return <path d="M110,150 C100,72 150,50 200,50 C255,50 300,70 292,150 C282,118 250,104 206,112 C170,100 128,112 110,150Z" fill={c} />;
};
export const Puppet: React.FC<PuppetProps> = (p) => {
  const skin = p.skin ?? "#F7D0B5", shirt = p.shirt ?? "#6F86B8", pants = p.pants ?? "#2D2F3A", hairC = p.hair ?? "#2B2320";
  const k = p.h / 700, legs = p.legs ?? true;
  const armL: Arm = p.armL ?? { a1: 12, a2: 0 }, armR: Arm = p.armR ?? { a1: 12, a2: 0 };
  const leg = (x0: number, a: number, side: number) => {
    const d = dirOf(1, a), e: Pt = [x0 + d[0] * 200, 470 + d[1] * 200];
    return (
      <g key={x0}>
        <path d={`M${x0},460 L${e[0]},${e[1]}`} stroke={pants} strokeWidth={50} strokeLinecap="round" />
        <ellipse cx={e[0] + 8} cy={e[1] + 18} rx={36} ry={16} fill="#222" />
      </g>
    );
  };
  return (
    <svg width={400 * k} height={700 * k} viewBox="0 0 400 700" style={{
      position: "absolute", left: p.x - 200 * k, top: p.y - 700 * k - (p.bob ?? 0), overflow: "visible", opacity: p.opacity,
      transformOrigin: "50% 100%", transform: `${p.flip ? "scaleX(-1)" : ""} rotate(${p.bodyTilt ?? 0}deg)`, ...p.style,
    }}>
      {p.under}
      {legs && <>{leg(168, p.legL ?? 0, -1)}{leg(232, p.legR ?? 0, 1)}<rect x={112} y={430} width={176} height={70} rx={20} fill={pants} /></>}
      <path d="M96,300 C96,262 130,248 170,246 L230,246 C270,248 304,262 304,300 L292,470 C292,482 280,490 268,490 L132,490 C120,490 108,482 108,470Z" fill={shirt} />
      <path d="M176,246 L200,300 L224,246Z" fill={p.collar ?? "#fff"} />
      {p.tie && <path d="M193,262 L207,262 L214,360 L200,378 L186,360Z" fill={p.tie} />}
      <g transform={`rotate(${p.headTilt ?? 0} 200 250)`}>
        <rect x={178} y={214} width={44} height={44} fill={skin} />
        <circle cx={112} cy={162} r={17} fill={skin} /><circle cx={288} cy={162} r={17} fill={skin} />
        <ellipse cx={200} cy={150} rx={90} ry={96} fill={skin} />
        <HairG style={p.hairStyle ?? "short"} c={hairC} />
        {(p.blush ?? true) && <><circle cx={146} cy={188} r={17} fill="#F29C9C" opacity={0.55} /><circle cx={254} cy={188} r={17} fill="#F29C9C" opacity={0.55} /></>}
        {p.brows === "angry" && <path d="M145,118 L182,132 M255,118 L218,132" stroke="#2a1d1a" strokeWidth={7} strokeLinecap="round" />}
        {p.brows === "worried" && <path d="M148,128 L182,118 M252,128 L218,118" stroke="#2a1d1a" strokeWidth={6} strokeLinecap="round" />}
        <EyeG kind={p.eyes ?? "dot"} x={165} side={-1} /><EyeG kind={p.eyes ?? "dot"} x={235} side={1} />
        <MouthG kind={p.mouth ?? "smile"} />
        {p.face}
      </g>
      <ArmG side={-1} arm={armL} sleeve={shirt} skin={skin} />
      <ArmG side={1} arm={armR} sleeve={shirt} skin={skin} />
      {p.extra}
    </svg>
  );
};

/** 팔 그림 알파 극점(캔버스 좌표): [top.x, top.y, left.x, left.y, right.x, right.y, bottom.x, bottom.y] — 손 위치 추정용(자동 측정) */
const ARM_EXT: Record<string, number[]> = {
  "walker1/arm_guard_fist_l": [586,482,453,548,725,635,644,769], "walker1/arm_guard_fist_r": [430,482,292,635,564,548,372,769], "walker1/arm_hold_l": [619,476,516,792,728,679,566,846], "walker1/arm_hold_r": [397,476,289,679,501,792,450,846], "walker1/arm_l": [620,478,602,562,731,779,693,961], "walker1/arm_palm_stop_l": [889,378,361,606,961,508,447,692], "walker1/arm_palm_stop_r": [127,378,56,508,656,606,569,692], "walker1/arm_r": [396,478,286,779,415,562,323,961], "walker1/arm_raise_fist_l": [696,140,575,547,750,210,636,648], "walker1/arm_raise_fist_r": [320,140,267,210,442,547,380,648], "walker1/arm_up_hang_l": [707,168,569,617,761,268,621,685], "walker1/arm_up_hang_r": [309,168,256,268,448,617,395,685],
  "c2_boss/arm_guard_fist_l": [631,458,459,545,734,671,675,787], "c2_boss/arm_guard_fist_r": [373,458,271,671,546,545,329,787], "c2_boss/arm_hand_chest_l": [611,444,390,587,746,695,679,795], "c2_boss/arm_hand_chest_r": [393,444,259,695,615,587,325,795], "c2_boss/arm_hold_l": [614,452,463,789,753,712,558,865], "c2_boss/arm_hold_r": [390,452,252,712,542,789,446,865], "c2_boss/arm_l": [614,440,578,549,764,866,698,1112], "c2_boss/arm_out_side_l": [857,324,483,548,933,357,628,648], "c2_boss/arm_out_side_r": [147,324,72,357,522,548,376,648], "c2_boss/arm_r": [390,440,241,866,427,549,306,1112], "c2_boss/arm_reach_l": [347,504,266,625,910,557,434,678], "c2_boss/arm_reach_r": [657,504,95,557,739,625,570,678], "c2_boss/arm_up_hang_l": [615,72,568,120,725,388,665,555], "c2_boss/arm_up_hang_r": [389,72,280,388,437,120,339,555],
  "c3_woman/arm_hand_chin_l": [470,329,416,437,664,609,571,817], "c3_woman/arm_hand_chin_r": [538,329,345,609,593,437,437,817], "c3_woman/arm_hold_l": [684,425,394,745,735,557,462,805], "c3_woman/arm_hold_r": [324,425,274,557,615,745,546,805], "c3_woman/arm_l": [606,451,576,544,703,785,671,928], "c3_woman/arm_point_l": [895,402,421,498,973,411,594,592], "c3_woman/arm_point_r": [113,402,36,411,588,498,414,592], "c3_woman/arm_r": [402,451,306,785,433,544,337,928], "c3_woman/arm_raise_fist_l": [652,116,528,570,703,284,595,675], "c3_woman/arm_raise_fist_r": [356,116,306,284,481,570,413,675], "c3_woman/arm_up_hang_l": [651,72,531,491,697,239,580,578], "c3_woman/arm_up_hang_r": [357,72,312,239,478,491,428,578],
  "c4_elder/arm_l": [605,431,570,555,804,902,704,1137], "c4_elder/arm_r": [405,431,207,902,441,555,306,1137], "c4_elder/arm_raise_fist_l": [693,91,539,536,754,242,618,628], "c4_elder/arm_raise_fist_r": [317,91,257,242,472,536,392,628],
  "c5_chef/arm_guard_fist_l": [548,415,486,480,741,617,674,751], "c5_chef/arm_guard_fist_r": [458,415,266,617,521,480,332,751], "c5_chef/arm_hold_l": [670,465,493,844,804,747,573,925], "c5_chef/arm_hold_r": [336,465,203,747,514,844,433,925], "c5_chef/arm_l": [639,467,597,565,768,824,713,995], "c5_chef/arm_r": [367,467,239,824,410,565,293,995], "c5_chef/arm_raise_fist_l": [653,88,541,521,722,273,616,654], "c5_chef/arm_raise_fist_r": [353,88,285,273,466,521,390,654],
};

// ══ 0b. 세모지 그림체 리그(로컬 확장) ═══════════════════════════════════════════════
// public/kit/<cast> 부위 PNG(1024×1536 같은 좌표)를 겹친다 — SemojiRig 와 같은 규약(포즈=그림 교체, 팔=어깨 축 회전, 표정=얼굴 패치, 10f 까딱).
// x_acting 전용 확장: ① 몸 앞을 지나는 팔(가드·들기·가슴·턱) 그림은 몸통 위에 그린다 ② 팔 레이어 안에 소품(itemR/itemL, 캔버스 좌표)을 넣어 팔 회전을 따라가게 한다
// ③ 흉상(bust)은 아래만 잘라 팔·소품이 캔버스 밖으로 나가도 보인다 ④ tilt(몸 기울임) ⑤ under/over(캔버스 좌표 레이어).
const FRONT_ARMS = new Set(["arm_guard_fist", "arm_hold", "arm_hand_chest", "arm_hand_chin"]);
export type XPose = RigPose & { mouth?: boolean; eyesClosed?: boolean };
export type XRigProps = {
  cast: CastId; x: number; y: number; h: number; pose?: XPose; bust?: boolean; flip?: boolean; at?: number; seed?: string;
  itemR?: RN; itemL?: RN; under?: RN; over?: RN; tilt?: number; style?: React.CSSProperties; p?: Partial<SemojiRigP>;
};
const RJ = (c: CastId): RigJson => CAST[c];
/** 캔버스 px → 화면 px 배율 */
export const rigS = (c: CastId, h: number) => h / (RJ(c).feet[1] - RJ(c).top);
const anchorY = (R: RigJson, bust?: boolean) => (bust ? R.torsoBottom + 10 : R.feet[1]);
/** 캔버스 점 → 화면 점 (까딱·tilt 무시) */
export const rigToScreen = (c: CastId, o: { x: number; y: number; h: number; bust?: boolean; flip?: boolean }, pt: Pt): Pt => {
  const R = RJ(c), s = rigS(c, o.h);
  return [o.x + (o.flip ? -1 : 1) * (pt[0] - R.feet[0]) * s, o.y + (pt[1] - anchorY(R, o.bust)) * s];
};
/** 캔버스 점 pt 를 pv 기준 deg(시계+) 회전 */
export const rotAbout = (pt: Pt, pv: Pt, deg: number): Pt => {
  const a = deg * D2R, dx = pt[0] - pv[0], dy = pt[1] - pv[1];
  return [pv[0] + dx * Math.cos(a) - dy * Math.sin(a), pv[1] + dx * Math.sin(a) + dy * Math.cos(a)];
};
export const shoulder = (c: CastId, side: "r" | "l"): Pt => { const R = RJ(c), v = side === "r" ? R.shoulderR : R.shoulderL; return [v[0], v[1]]; };
/** 팔 그림의 손(주먹·손바닥) 위치(캔버스, 회전 전) — ARM_EXT 극점에서 포즈별로 고른다 */
export const handPt = (c: CastId, arm: string | undefined, side: "r" | "l"): Pt => {
  const n = !arm || arm === "arm" ? `arm_${side}` : `${arm}_${side}`, e = ARM_EXT[`${c}/${n}`];
  if (!e) return [RJ(c).feet[0], RJ(c).torsoBottom];
  const [tx, ty, lx, ly, rx, ry, bx, by] = e, out = side === "r" ? [lx, ly] : [rx, ry], inn = side === "r" ? [rx, ry] : [lx, ly], o = side === "r" ? 1 : -1;
  const k = arm ?? "arm";
  if (k === "arm_raise_fist" || k === "arm_up_hang") return [tx, ty + 45];
  if (k === "arm_hand_chin") return [tx, ty + 40];
  if (k === "arm_palm_stop" || k === "arm_out_side") return [out[0] + o * 70, out[1] - 10];
  if (k === "arm_reach" || k === "arm_point") return [out[0] + o * 10, out[1]];
  if (FRONT_ARMS.has(k)) return [inn[0] - o * 40, inn[1] + 5];
  return [bx, by - 45];
};
/** 회전까지 반영한 손의 화면 좌표 */
export const handScreen = (c: CastId, o: { x: number; y: number; h: number; bust?: boolean; flip?: boolean }, arm: string | undefined, side: "r" | "l", rot = 0): Pt =>
  rigToScreen(c, o, rotAbout(handPt(c, arm, side), shoulder(c, side), rot));
/** 어깨→손 방향이 화면 목표점 target 을 향하도록 하는 팔 회전(°) */
export const aimRot = (c: CastId, o: { x: number; y: number; h: number; bust?: boolean; flip?: boolean }, arm: string | undefined, side: "r" | "l", target: Pt) => {
  const sp = rigToScreen(c, o, shoulder(c, side)), hp = rigToScreen(c, o, handPt(c, arm, side));
  const a0 = Math.atan2(hp[1] - sp[1], hp[0] - sp[0]), a1 = Math.atan2(target[1] - sp[1], target[0] - sp[0]);
  let d = ((a1 - a0) * 180) / Math.PI; d = ((d + 540) % 360) - 180;
  return o.flip ? -d : d;
};
export const XRig: React.FC<XRigProps> = ({ cast, x, y, h, pose = {}, bust = false, flip = false, at = 0, seed = "rig", itemR, itemL, under, over, tilt = 0, style, p }) => {
  const R = RJ(cast);
  const P = def(SemojiRigParams, p);
  const f = useCurrentFrame();
  const t = Math.max(0, f - at);
  const s = rigS(cast, h);
  const ph = Math.floor(random(seed) * 10);
  const kk = P.bobEvery > 0 ? ((t + ph) % (2 * P.bobEvery)) / P.bobEvery : 0;
  const e = kk < 1 ? kk : 2 - kk, sy = 1 + (P.bobAmp / 100) * e * e * (3 - 2 * e);
  const blinkOn = P.blinkEvery > 0 && (t + Math.floor(random(seed + "b") * P.blinkEvery)) % P.blinkEvery < 4;
  const talkOn = P.talkMode === "random" ? talkOpenRandom(t, seed, P.talkMin, P.talkMax) : P.talkEvery > 0 && Math.floor(t / P.talkEvery) % 2 === 1;
  const img = (name: string, extra?: React.CSSProperties) => <Img key={name} src={staticFile(`${R.dir}/${name}.png`)} style={{ position: "absolute", left: 0, top: 0, width: R.w, height: R.h, ...extra }} />;
  const arm = (n: string | undefined, side: "r" | "l", rot = 0, item?: RN) => {
    const pv = side === "r" ? R.shoulderR : R.shoulderL;
    return (
      <div key={`arm${side}`} style={{ position: "absolute", left: 0, top: 0, width: R.w, height: R.h, transformOrigin: `${pv[0]}px ${pv[1]}px`, transform: `rotate(${rot}deg)` }}>
        {img(!n || n === "arm" ? `arm_${side}` : `${n}_${side}`)}
        {item}
      </div>
    );
  };
  const ay = anchorY(R, bust);
  const frontR = FRONT_ARMS.has(pose.armR ?? ""), frontL = FRONT_ARMS.has(pose.armL ?? "");
  const face = pose.face ? img(pose.face) : pose.eyesClosed || blinkOn ? img("eyes_closed") : null;
  return (
    <div style={{
      position: "absolute", left: x - R.feet[0], top: y - ay, width: R.w, height: R.h, transformOrigin: `${R.feet[0]}px ${ay}px`,
      transform: `scale(${flip ? -s : s},${s * sy}) rotate(${flip ? -tilt : tilt}deg)`, clipPath: bust ? `inset(-4000px -4000px ${R.h - ay}px -4000px)` : undefined, ...style,
    }}>
      {under}
      {!bust && img(pose.legs ?? "legs_stand")}
      {!pose.armFold && !frontR && arm(pose.armR, "r", pose.rotR, itemR)}
      {!pose.armFold && !frontL && arm(pose.armL, "l", pose.rotL, itemL)}
      {img("torso")}
      {face}
      {(pose.mouth || (!pose.face && talkOn)) && img("mouth_open")}
      {pose.armFold && img("arms_folded")}
      {!pose.armFold && frontR && arm(pose.armR, "r", pose.rotR, itemR)}
      {!pose.armFold && frontL && arm(pose.armL, "l", pose.rotL, itemL)}
      {over}
    </div>
  );
};
/** 소품 PNG 한 장 — 이미지 안의 기준점 (ax,ay)(0..1 비율)을 (x,y)에 두고 그 점을 축으로 rot 회전. h 생략 시 원본 비율 */
export const PropImg: React.FC<{ id: string; x: number; y: number; w: number; h?: number; ax?: number; ay?: number; rot?: number; flipX?: boolean; op?: number; style?: React.CSSProperties; children?: RN }> = ({ id, x, y, w, h, ax = 0.5, ay = 0.5, rot = 0, flipX, op, style, children }) => {
  const hh = h ?? propH(id, w);
  return (
    <div style={{ position: "absolute", left: x - ax * w, top: y - ay * hh, width: w, height: hh, transformOrigin: `${ax * w}px ${ay * hh}px`, transform: `rotate(${rot}deg)${flipX ? " scaleX(-1)" : ""}`, opacity: op, ...style }}>
      <Img src={prop(id)} style={{ position: "absolute", left: 0, top: 0, width: w, height: hh }} />
      {children}
    </div>
  );
};
/** 소품 원본 픽셀 좌표(px,py) → (ax,ay) 비율 */
export const pa = (id: string, px: number, py: number): [number, number] => { const [a, b] = propSize(id); return [px / a, py / b]; };

// ── 공용 소품 SVG ─────────────────────────────────────────────────────────
/** 왕관(밑변 중앙 0,0 · 폭 w) */
export const CrownSvg: React.FC<{ w: number; text?: string; color?: string }> = ({ w, text, color = "#F2B620" }) => {
  const h = w * 0.62;
  return (
    <g>
      <path d={`M${-w / 2},0 L${-w / 2},${-h * 0.72} L${-w / 4},${-h * 0.4} L0,${-h} L${w / 4},${-h * 0.4} L${w / 2},${-h * 0.72} L${w / 2},0Z`} fill={color} />
      <rect x={-w / 2} y={-h * 0.26} width={w} height={h * 0.26} fill="#E09A12" />
      {[-w / 2, 0, w / 2].map((x, i) => <circle key={i} cx={x} cy={i === 1 ? -h : -h * 0.72} r={w * 0.06} fill="#FFE27A" />)}
      {text ? <text x={0} y={-h * 0.3} textAnchor="middle" fontFamily="Jua" fontSize={w * 0.2} fill="#fff">{text}</text>
        : <circle cx={0} cy={-h * 0.45} r={w * 0.08} fill="#D8423A" />}
    </g>
  );
};
/** 8각 별 스파크(중심 0,0 · 반지름 r) — 방사 줄무늬 아님, 단일 폴리곤 */
export const StarSpark: React.FC<{ r: number; color?: string; core?: string; n?: number }> = ({ r, color = "#FFB21E", core = "#FFF1A0", n = 8 }) => {
  const pts = (rr: number, ir: number) => Array.from({ length: n * 2 }, (_, i) => { const a = (i / (n * 2)) * TAU - Math.PI / 2, q = i % 2 ? ir : rr; return `${Math.cos(a) * q},${Math.sin(a) * q}`; }).join(" ");
  return <g><polygon points={pts(r, r * 0.45)} fill={color} /><polygon points={pts(r * 0.55, r * 0.25)} fill={core} /></g>;
};
/** 소프트 원형 글로우 (광선 없음) */
const Glow: React.FC<{ x: number; y: number; r: number; color: string; op?: number; blend?: React.CSSProperties["mixBlendMode"] }> = ({ x, y, r, color, op = 1, blend }) => (
  <div style={{ position: "absolute", left: x - r, top: y - r, width: r * 2, height: r * 2, borderRadius: "50%", opacity: op, mixBlendMode: blend, background: `radial-gradient(circle, ${color} 0%, ${color} 18%, transparent 70%)` }} />
);
/** 손글씨 라벨 */
const Label: React.FC<{ text: string; x: number; y: number; size?: number; color?: string; rot?: number; op?: number; s?: number; blur?: number }> = ({ text, x, y, size = 54, color = "#1a1a1a", rot = -4, op = 1, s = 1, blur = 0 }) => (
  <div style={{ position: "absolute", left: x, top: y, transform: `translate(-50%,-50%) rotate(${rot}deg) scale(${s})`, opacity: op, filter: blur > 0.3 ? `blur(${blur}px)` : undefined, fontFamily: "Yeonsung", fontSize: size, color, whiteSpace: "pre", textAlign: "center", lineHeight: 1.05, textShadow: "0 0 6px rgba(255,255,255,0.9), 0 0 2px #fff" }}>{hz(text)}</div>
);
/** 결정론 보케 원들 */
const Bokeh: React.FC<{ n: number; seed: string; colors: string[]; rMin: number; rMax: number; y0?: number; y1?: number; op?: number; drift?: number }> = ({ n, seed, colors, rMin, rMax, y0 = 0, y1 = H, op = 0.5, drift = 0 }) => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill>
      {Array.from({ length: n }, (_, i) => {
        const r = rMin + (rMax - rMin) * random(`${seed}r${i}`), x = W * random(`${seed}x${i}`) + Math.sin(f / 40 + i) * drift, y = y0 + (y1 - y0) * random(`${seed}y${i}`) - f * drift * 0.1 * random(`${seed}v${i}`);
        return <div key={i} style={{ position: "absolute", left: x - r, top: y - r, width: r * 2, height: r * 2, borderRadius: "50%", background: colors[i % colors.length], opacity: op * (0.5 + 0.5 * random(`${seed}o${i}`)), filter: `blur(${r * 0.18}px)` }} />;
      })}
    </AbsoluteFill>
  );
};

// ══ 1. 말하는 입 교체 [ref1 13:22 · 8:05] — 두 입 모양을 4~6f 불규칙 교대 ═══════════════
export const MouthSwapParams = z.object({
  gapMin: num(4, 1, 30, 1, "교체 최소 간격", "timing", "f"),
  gapMax: num(6, 1, 30, 1, "교체 최대 간격", "timing", "f"),
  holdOpen: flag(false, "교체 없이 벌린 입 유지(0–5분 구간)", "motion"),
  talkMode: choice("fixed", ["fixed", "random"] as const, "입 교체 방식(fixed=gapMin~gapMax 기존 · random=talkMin~talkMax 시드 랜덤)"),
  talkMin: num(4, 1, 30, 1, "random: 최소 간격", "timing", "f"),
  talkMax: num(8, 1, 30, 1, "random: 최대 간격", "timing", "f"),
});
export type MouthSwapP = z.infer<typeof MouthSwapParams>;
/** f 에서 입이 벌어져 있는가 (at 부터 out 까지 교대, seed 로 간격 결정) */
export const mouthOpenAt = (f: number, at: number, P: MouthSwapP, seed = "mouth", out = Infinity) => {
  if (f < at || f >= out) return false;
  if (P.holdOpen) return true;
  if (P.talkMode === "random") return talkOpenRandom(f - at, seed, P.talkMin, P.talkMax);
  const lo = Math.max(1, Math.min(P.gapMin, P.gapMax)), hi = Math.max(lo, Math.max(P.gapMin, P.gapMax));
  let t = at, i = 0;
  while (i < 999) { const len = lo + Math.floor(random(`${seed}${i}`) * (hi - lo + 1)); if (f < t + len) return i % 2 === 0; t += len; i++; }
  return false;
};
export const MouthSwap: React.FC<{ at: number; out?: number; seed?: string; render: (open: boolean) => RN; p?: Partial<MouthSwapP> }> = ({ at, out, seed, render, p }) => {
  const P = def(MouthSwapParams, p);
  const f = useCurrentFrame();
  return <>{render(mouthOpenAt(f, at, P, seed, out))}</>;
};

// ══ 2. 거대 블러 줌아웃 등장 [ref1 3:12] — 약 250% + 블러, 오른쪽 아래에서 → 100% 8f ══════
export const GiantBlurEntryParams = z.object({
  len: num(8, 1, 40, 1, "등장 길이", "timing", "f"),
  from: num(2.5, 1, 6, 0.05, "시작 크기(배)", "motion"),
  blur: num(28, 0, 80, 1, "시작 블러", "look", "px"),
  dx: num(260, -1200, 1200, 10, "시작 x 어긋남", "motion", "px"),
  dy: num(420, -1200, 1200, 10, "시작 y 어긋남", "motion", "px"),
});
export type GiantBlurEntryP = z.infer<typeof GiantBlurEntryParams>;
export const GiantBlurEntry: React.FC<{ at: number; anchor: Pt; children: RN; p?: Partial<GiantBlurEntryP> }> = ({ at, anchor, children, p }) => {
  const P = def(GiantBlurEntryParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const k = lerp(f, at, at + P.len, 0, 1, EXPO_OUT);
  const s = P.from + (1 - P.from) * k, b = P.blur * (1 - k);
  return (
    <AbsoluteFill style={{ transformOrigin: `${anchor[0]}px ${anchor[1]}px`, transform: `translate(${P.dx * (1 - k)}px,${P.dy * (1 - k)}px) scale(${s})`, filter: b > 0.3 ? `blur(${b}px)` : undefined }}>
      {children}
    </AbsoluteFill>
  );
};

// ══ 3. 알파 페이드 등장 · 겹쳤다 분리 [ref1 13:59] — 한 명씩 알파 0→1 9f + 옆으로 60px 벌어짐 ══
export const FadeAccumulateParams = z.object({
  stagger: num(30, 1, 120, 1, "다음 인물까지 간격", "timing", "f"),
  fadeLen: num(9, 1, 40, 1, "페이드 길이", "timing", "f"),
  spread: num(60, 0, 300, 2, "벌어짐 거리", "motion", "px"),
});
export type FadeAccumulateP = z.infer<typeof FadeAccumulateParams>;
export const FadeAccumulate: React.FC<{ at: number; items: RN[]; p?: Partial<FadeAccumulateP> }> = ({ at, items, p }) => {
  const P = def(FadeAccumulateParams, p);
  const f = useCurrentFrame();
  return (
    <AbsoluteFill>
      {items.map((it, i) => {
        const a = at + i * P.stagger;
        if (f < a) return null;
        const k = lerp(f, a, a + P.fadeLen, 0, 1, Easing.out(Easing.quad));
        // 첫 인물은 제자리 페이드, 이후 인물은 앞 사람 쪽(-x)에서 겹쳐 나타나 벌어진다
        return <AbsoluteFill key={i} style={{ opacity: lerp(f, a, a + P.fadeLen, 0, 1, Easing.linear), transform: `translateX(${i === 0 ? 0 : -P.spread * (1 - k)}px)` }}>{it}</AbsoluteFill>;
      })}
    </AbsoluteFill>
  );
};

// ══ 4. 표정 스왑 [ref1 9:28] — 눈을 '> <' 찡그림으로 하드 스왑 ════════════════════
export const ExpressionSwapParams = z.object({
  hold: num(0, 0, 120, 1, "스왑 유지 후 복귀(0=유지)", "timing", "f"),
  pop: num(0, 0, 0.2, 0.01, "스왑 순간 튐(배)", "motion"),
  popLen: num(3, 1, 12, 1, "튐 길이", "timing", "f"),
});
export type ExpressionSwapP = z.infer<typeof ExpressionSwapParams>;
export const ExpressionSwap: React.FC<{ at: number; before: RN; after: RN; origin?: Pt; p?: Partial<ExpressionSwapP> }> = ({ at, before, after, origin = [W / 2, H], p }) => {
  const P = def(ExpressionSwapParams, p);
  const f = useCurrentFrame();
  const on = f >= at && (P.hold <= 0 || f < at + P.hold);
  const s = on ? 1 + P.pop * bump((f - at) / P.popLen) : 1;
  return <AbsoluteFill style={{ transformOrigin: `${origin[0]}px ${origin[1]}px`, transform: `scale(${s})` }}>{on ? after : before}</AbsoluteFill>;
};

// ══ 5. 반복 팔 동작 [ref1 5:10] — 7f 사인(0→+18px→0) + 12f 정지 = 19f 주기, 두 인물 9.5f 엇갈림 ══
export const RepeatGestureParams = z.object({
  moveLen: num(7, 1, 30, 1, "동작 길이", "timing", "f"),
  rest: num(12, 0, 60, 1, "정지 길이", "timing", "f"),
  amp: num(18, 0, 120, 1, "흔들 거리", "motion", "px"),
  rot: num(0, -30, 30, 1, "흔들 때 회전", "motion", "°"),
  phaseB: num(9.5, 0, 40, 0.5, "두 번째 인물 엇갈림", "timing", "f"),
});
export type RepeatGestureP = z.infer<typeof RepeatGestureParams>;
/** 0..1 동작 곡선 (phase 만큼 늦게) */
export const gestureK = (f: number, at: number, P: RepeatGestureP, phase = 0) => {
  const g = f - at - phase, L = Math.max(1, P.moveLen), T = L + Math.max(0, P.rest);
  if (g < 0) return 0;
  const t = g % T;
  return t < L ? Math.sin((t / L) * Math.PI) : 0;
};
/** children 을 주기적으로 흔든다(render 가 있으면 k·P 를 넘겨 직접 그리게 한다). second=true 면 phaseB 만큼 늦음 */
export const RepeatGesture: React.FC<{ at: number; second?: boolean; pivot?: Pt; children?: RN; render?: (k: number, P: RepeatGestureP) => RN; p?: Partial<RepeatGestureP> }> = ({ at, second, pivot = [0, 0], children, render, p }) => {
  const P = def(RepeatGestureParams, p);
  const f = useCurrentFrame();
  const k = gestureK(f, at, P, second ? P.phaseB : 0);
  if (render) return <>{render(k, P)}</>;
  return <AbsoluteFill style={{ transformOrigin: `${pivot[0]}px ${pivot[1]}px`, transform: `translateY(${-P.amp * k}px) rotate(${P.rot * k}deg)` }}>{children}</AbsoluteFill>;
};

// ══ 6. 팔 1축 트윈 + 스윙 [ref1 13:30 뚜껑 들기 · 2:06 웍 팔] — 15f 120px ease-out → ±3° 1.5s 스윙 ══
export const ArmTweenParams = z.object({
  liftLen: num(15, 1, 60, 1, "들어올림 길이", "timing", "f"),
  liftDist: num(120, 0, 600, 5, "들어올림 거리", "motion", "px"),
  swingDeg: num(3, 0, 30, 0.5, "스윙 각도(±)", "motion", "°"),
  swingPeriod: num(45, 4, 180, 1, "스윙 주기", "timing", "f"),
});
export type ArmTweenP = z.infer<typeof ArmTweenParams>;
export const armTweenAt = (f: number, at: number, P: ArmTweenP) => {
  const k = lerp(f, at, at + P.liftLen, 0, 1, Easing.out(Easing.cubic));
  const g = f - at - P.liftLen;
  return { k, lift: P.liftDist * k, swing: g > 0 ? P.swingDeg * Math.sin((g / P.swingPeriod) * TAU) : 0 };
};
export const ArmTween: React.FC<{ at: number; pivot: Pt; children?: RN; render?: (s: { k: number; lift: number; swing: number }, P: ArmTweenP) => RN; p?: Partial<ArmTweenP> }> = ({ at, pivot, children, render, p }) => {
  const P = def(ArmTweenParams, p);
  const f = useCurrentFrame();
  const s = armTweenAt(f, at, P);
  if (render) return <>{render(s, P)}</>;
  return <AbsoluteFill style={{ transformOrigin: `${pivot[0]}px ${pivot[1] - s.lift}px`, transform: `translateY(${-s.lift}px) rotate(${s.swing}deg)` }}>{children}</AbsoluteFill>;
};

// ══ 7. 의상·소품 추가 [ref1 9:51 '딤섬의 여왕'] — 왕관·망토 0→100 15f(왕관 -10px 내려앉음) + 네임태그 4f 블러 슬라이드 ══
export const CostumeAddParams = z.object({
  fadeLen: num(15, 1, 60, 1, "소품 페이드 길이", "timing", "f"),
  crownDrop: num(10, 0, 120, 1, "왕관 내려앉는 거리", "motion", "px"),
  tagLead: num(-6, -30, 30, 1, "태그 시작(소품 대비)", "timing", "f"),
  tagLen: num(4, 1, 20, 1, "태그 슬라이드 길이", "timing", "f"),
  tagDist: num(140, 0, 600, 5, "태그 슬라이드 거리", "motion", "px"),
  tagBlur: num(24, 0, 80, 1, "태그 모션블러", "look", "px"),
});
export type CostumeAddP = z.infer<typeof CostumeAddParams>;
/** 세모지 왕관 PNG(밑변 중앙 x,y · 폭 w). text 는 금 띠 위에 코드로 올린다(가운데 보석은 띠색 패치로 가림) */
export const CrownImg: React.FC<{ x: number; y: number; w: number; text?: string; style?: React.CSSProperties }> = ({ x, y, w, text, style }) => {
  const h = propH("crown", w);
  return (
    <div style={{ position: "absolute", left: x - w / 2, top: y - h, width: w, height: h, ...style }}>
      <Img src={prop("crown")} style={{ position: "absolute", left: 0, top: 0, width: w, height: h }} />
      {text && <div style={{ position: "absolute", left: w * 0.1, width: w * 0.8, top: h * 0.805, height: h * 0.17, transform: "translateY(-50%)", borderRadius: h * 0.04, background: "#B97F1C", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "Jua", fontSize: w * 0.15, color: "#FFF4C8", whiteSpace: "nowrap" }}>{text}</div>}
    </div>
  );
};
/** 왕관·망토 PNG(royal_cape_back 인물 뒤 / royal_cape_collar 인물 앞, 같은 크롭 박스). cape.(x,y) = 털 칼라 윗변 중앙, w = 망토 폭 */
export const CostumeAdd: React.FC<{
  at: number; children: RN; crown?: { x: number; y: number; w: number; text?: string };
  cape?: { x: number; y: number; w: number; h?: number }; tag?: { text: string; x: number; y: number; from?: Pt }; p?: Partial<CostumeAddP>;
}> = ({ at, children, crown, cape, tag, p }) => {
  const P = def(CostumeAddParams, p);
  const f = useCurrentFrame();
  const op = lerp(f, at, at + P.fadeLen, 0, 1, Easing.linear);
  const ta = at + P.tagLead, tk = lerp(f, ta, ta + P.tagLen, 0, 1, Easing.out(Easing.quad));
  const [cax, cay] = pa("royal_cape_back", 582, 3);
  const capeImg = (id: string) => cape && <PropImg id={id} x={cape.x} y={cape.y} w={cape.w} h={cape.h} ax={cax} ay={cay} op={op} />;
  return (
    <AbsoluteFill>
      {f >= at && capeImg("royal_cape_back")}
      {children}
      {f >= at && capeImg("royal_cape_collar")}
      {crown && f >= at && <CrownImg x={crown.x} y={crown.y - P.crownDrop * (1 - op)} w={crown.w} text={crown.text} style={{ opacity: op }} />}
      {tag && f >= ta && (() => {
        const fr = tag.from ?? [tag.x - 160, tag.y + 40];
        return (
          <>
            <svg width={W} height={H} style={{ position: "absolute", left: 0, top: 0, opacity: tk }}>
              <path d={`M${fr[0]},${fr[1]} q20,-30 40,0 t40,-10 T${tag.x - 10},${tag.y + 6}`} stroke="#222" strokeWidth={4} fill="none" strokeLinecap="round" />
            </svg>
            <div style={{ position: "absolute", left: tag.x, top: tag.y, transform: `translate(${P.tagDist * (1 - tk)}px,-50%)`, filter: tk < 0.99 ? `blur(${P.tagBlur * (1 - tk)}px)` : undefined, opacity: Math.min(1, tk * 2), background: "#2b2b2b", color: "#fff", fontFamily: "NeoHv", fontSize: 44, padding: "8px 26px 10px", borderRadius: 16, whiteSpace: "nowrap" }}>{tag.text}</div>
          </>
        );
      })()}
    </AbsoluteFill>
  );
};

// ══ 8. 의사봉 내리치기 [ref2 87:35] — 들어올린 채 11f 정지 → 3f 내리침, 바운스 없음 ══════════
export const MalletStrikeParams = z.object({
  hold: num(11, 0, 60, 1, "들어올린 정지", "timing", "f"),
  strikeLen: num(3, 1, 20, 1, "내리침 길이", "timing", "f"),
  recover: num(6, 1, 40, 1, "다시 들기", "timing", "f"),
  raise: num(24, 0, 80, 1, "들어올린 각도", "motion", "°"),
  repeat: num(3, 1, 12, 1, "내리침 횟수", "motion"),
  shake: num(6, 0, 40, 1, "타격 순간 받침 흔들림", "motion", "px"),
  size: num(1, 0.3, 3, 0.05, "크기(배)", "size"),
});
export type MalletStrikeP = z.infer<typeof MalletStrikeParams>;
/** 의사봉 각도(0=내려침, +raise=들림) + 타격 후 경과 */
export const malletAt = (f: number, at: number, P: MalletStrikeP) => {
  const g = f - at, T = P.hold + P.strikeLen + P.recover, n = Math.max(1, Math.round(P.repeat));
  if (g < 0) return { ang: P.raise, hit: -1 };
  const i = Math.floor(g / T), c = g - i * T;
  if (i >= n || (i === n - 1 && c >= P.hold + P.strikeLen)) return { ang: 0, hit: g - ((n - 1) * T + P.hold + P.strikeLen) };
  if (c < P.hold) return { ang: P.raise, hit: -1 };
  if (c < P.hold + P.strikeLen) return { ang: P.raise * (1 - Easing.in(Easing.quad)((c - P.hold) / P.strikeLen)), hit: -1 };
  return { ang: P.raise * EASY((c - P.hold - P.strikeLen) / P.recover), hit: c - P.hold - P.strikeLen };
};
export const GavelSvg: React.FC = () => (
  <g>
    <rect x={0} y={-17} width={330} height={34} rx={17} fill="#6B3A1E" />
    <rect x={150} y={-20} width={40} height={40} rx={10} fill="#5A2F17" />
    <rect x={300} y={-100} width={120} height={200} rx={26} fill="#7A4424" />
    <rect x={300} y={-60} width={120} height={22} fill="#C99A2E" /><rect x={300} y={38} width={120} height={22} fill="#C99A2E" />
    <rect x={292} y={-104} width={136} height={24} rx={10} fill="#8A5230" /><rect x={292} y={80} width={136} height={24} rx={10} fill="#8A5230" />
  </g>
);
/** 의사봉 세트 PNG(gavel_hammer / gavel_block 같은 크롭 1356×811): 받침 윗면 중앙 ≈ (347,580), 자루 끝 피벗 ≈ (1322,578), 이미지 원래 각도에서 -1.6° 돌면 머리가 받침에 닿음 */
const GAVEL_PIVOT: Pt = [1322, 578], GAVEL_BLOCK: Pt = [347, 580], GAVEL_HIT = -1.6;
export const MalletStrike: React.FC<{ at: number; x: number; y: number; p?: Partial<MalletStrikeP> }> = ({ at, x, y, p }) => {
  const P = def(MalletStrikeParams, p);
  const f = useCurrentFrame();
  const { ang, hit } = malletAt(f, at, P);
  const sh = hit >= 0 && hit < 5 ? P.shake * Math.exp(-hit / 1.5) * (hit % 2 ? -1 : 1) : 0;
  // (x,y) = 받침대 중앙 윗면. 받침 폭 ≈ 400px × size
  const w = (1356 * 400 * P.size) / 694, sc = w / 1356;
  const left = x - GAVEL_BLOCK[0] * sc, top = y - GAVEL_BLOCK[1] * sc;
  return (
    <AbsoluteFill>
      <PropImg id="gavel_block" x={left} y={top + sh * 0.3} w={w} ax={0} ay={0} />
      <PropImg id="gavel_hammer" x={left + GAVEL_PIVOT[0] * sc} y={top + GAVEL_PIVOT[1] * sc} w={w} ax={GAVEL_PIVOT[0] / 1356} ay={GAVEL_PIVOT[1] / 811} rot={GAVEL_HIT + ang} />
    </AbsoluteFill>
  );
};

// ══ 9. 비핵심 인물 얼굴 블러 [ref4-apple 1:15:00 · 1:21:56] — 얼굴 원(≈160px)만 가우시안 12~16px ══
export const FaceBlurParams = z.object({
  r: num(84, 20, 300, 2, "블러 원 반지름", "size", "px"),
  blur: num(14, 0, 60, 1, "블러 세기", "look", "px"),
  feather: num(0.28, 0, 0.9, 0.02, "가장자리 부드러움", "look"),
  desat: num(0.15, 0, 1, 0.05, "블러 부분 채도 감소", "look"),
});
export type FaceBlurP = z.infer<typeof FaceBlurParams>;
/** children(장면)을 그리고, faces 위치만 블러된 사본을 원형 마스크로 덮는다. 카메라 변환은 바깥에서 감싸면 함께 따라간다 */
export const FaceBlur: React.FC<{ faces: { x: number; y: number; r?: number }[]; children: RN; p?: Partial<FaceBlurP> }> = ({ faces, children, p }) => {
  const P = def(FaceBlurParams, p);
  return (
    <AbsoluteFill>
      {children}
      {faces.map((fc, i) => {
        const r = fc.r ?? P.r, m = `radial-gradient(circle ${r}px at ${fc.x}px ${fc.y}px, #000 ${Math.round((1 - P.feather) * 100)}%, transparent 100%)`;
        return <AbsoluteFill key={i} style={{ WebkitMaskImage: m, maskImage: m, filter: `blur(${P.blur}px) saturate(${1 - P.desat})` }}>{children}</AbsoluteFill>;
      })}
    </AbsoluteFill>
  );
};

// ══ 10. 복싱 링 라이벌 + ROUND 표기 [ref4-apple 0:45:41] ═══════════════════════════════
export const BoxingRoundParams = z.object({
  roundAt: num(10, 0, 120, 1, "ROUND 표기 시작", "timing", "f"),
  roundPop: num(6, 1, 30, 1, "ROUND 블러 팝 길이", "timing", "f"),
  roundSize: num(76, 30, 200, 2, "ROUND 글자 크기", "size", "px"),
  roundX: num(1500, 0, 1920, 10, "ROUND 위치 x", "size", "px"),
  roundY: num(96, 0, 1080, 2, "ROUND 위치 y", "size", "px"),
  bobAmp: num(5, 0, 40, 1, "들썩임 높이", "motion", "px"),
  bobPeriod: num(14, 4, 60, 1, "들썩임 반주기", "timing", "f"),
  labelAt: num(26, 0, 150, 1, "주장 라벨 시작", "timing", "f"),
  labelStagger: num(14, 0, 60, 1, "라벨 간격", "timing", "f"),
  streaks: num(10, 0, 40, 1, "가장자리 속도선 개수", "size"),
  roundColor: col("#D8322E", "ROUND 색"),
});
export type BoxingRoundP = z.infer<typeof BoxingRoundParams>;
export const BoxingRound: React.FC<{ at: number; left: RN; right: RN; round?: string; labels?: { text: string; x: number; y: number }[]; p?: Partial<BoxingRoundP> }> = ({ at, left, right, round = "ROUND2", labels = [], p }) => {
  const P = def(BoxingRoundParams, p);
  const f = useCurrentFrame();
  const bl = P.bobAmp * pp01(f, P.bobPeriod), br = P.bobAmp * pp01(f, P.bobPeriod, P.bobPeriod * 0.6);
  const rp = blurPop(f, at + P.roundAt, P.roundPop, 1.35, 12);
  const sk = Math.floor(f / 2);
  return (
    <AbsoluteFill style={{ background: "linear-gradient(180deg,#24514f 0%,#173536 55%,#0f2527 100%)" }}>
      <Bokeh n={46} seed="arena" colors={["#9fd6c8", "#f5f0d0", "#6fa7a0"]} rMin={6} rMax={20} y0={60} y1={520} op={0.55} />
      <Glow x={380} y={-40} r={520} color="rgba(220,255,240,0.22)" /><Glow x={1540} y={-40} r={520} color="rgba(220,255,240,0.22)" />
      <Full>
        {[0, 1, 2].map((i) => <line key={i} x1={0} y1={560 + i * 62} x2={W} y2={548 + i * 62} stroke={["#c9453f", "#f1f1f1", "#3d6fb3"][i]} strokeWidth={14} />)}
        <rect x={120} y={500} width={30} height={600} fill="#bbb" /><rect x={1770} y={500} width={30} height={600} fill="#bbb" />
        {Array.from({ length: Math.round(P.streaks) }, (_, i) => {
          const side = i % 2 ? 1 : -1, y = 80 + 900 * random(`bs${i}${sk}`), len = 90 + 120 * random(`bl${i}${sk}`), x = side < 0 ? 20 + 60 * random(`bx${i}${sk}`) : W - 20 - 60 * random(`bx${i}${sk}`);
          return <line key={i} x1={x} y1={y} x2={x - side * len} y2={y + len * 0.35} stroke="#fff" strokeWidth={4} strokeLinecap="round" opacity={0.85} />;
        })}
      </Full>
      <AbsoluteFill style={{ transform: `translateY(${-bl}px)` }}>{left}</AbsoluteFill>
      <AbsoluteFill style={{ transform: `translateY(${-br}px)` }}>{right}</AbsoluteFill>
      {f >= at + P.roundAt && (
        <div style={{ position: "absolute", left: P.roundX, top: P.roundY, transform: `translate(-50%,-50%) scale(${rp.s})`, opacity: rp.op, filter: rp.blur > 0.3 ? `blur(${rp.blur}px)` : undefined, fontFamily: "Jalnan", fontSize: P.roundSize, color: P.roundColor, WebkitTextStroke: `${P.roundSize * 0.05}px #7a1512`, letterSpacing: 2 }}>{round}</div>
      )}
      {labels.map((l, i) => {
        const a = at + P.labelAt + i * P.labelStagger;
        if (f < a) return null;
        const b = blurPop(f, a, 6, 1.3, 8);
        return <Label key={i} text={l.text} x={l.x} y={l.y} s={b.s} op={b.op} blur={b.blur} size={52} />;
      })}
    </AbsoluteFill>
  );
};

// ══ 11. 두더지 게임 뿅망치 [ref4-apple 1:14:57] — 구멍 속 상반신 + 머리 위 대각 뿅망치 흔들림 ══
export const WhackAMoleParams = z.object({
  riseLen: num(8, 1, 40, 1, "구멍에서 솟는 길이", "timing", "f"),
  hammerDelay: num(4, 0, 60, 1, "망치 등장 지연", "timing", "f"),
  hammerIn: num(10, 1, 40, 1, "망치 진입 길이", "timing", "f"),
  swing: num(4, 0, 30, 0.5, "망치 흔들림(±)", "motion", "°"),
  swingPeriod: num(18, 4, 80, 1, "흔들림 반주기", "timing", "f"),
  bubbleAt: num(16, 0, 120, 1, "말풍선 시작", "timing", "f"),
  holeW: num(760, 300, 1400, 10, "구멍 폭", "size", "px"),
});
export type WhackAMoleP = z.infer<typeof WhackAMoleParams>;
export const WhackAMole: React.FC<{ at: number; char: RN; text?: string; bubble?: (at: number) => RN; p?: Partial<WhackAMoleP> }> = ({ at, char, bubble, p }) => {
  const P = def(WhackAMoleParams, p);
  const f = useCurrentFrame();
  const hy = 1000, hw = P.holeW, rise = lerp(f, at, at + P.riseLen, 520, 0, EXPO_OUT);
  const ha = at + P.hammerDelay, hin = lerp(f, ha, ha + P.hammerIn, 42, 0, Easing.out(Easing.back(1.4)));
  const rot = 154 + hin + (f > ha + P.hammerIn ? P.swing * (pp01(f - ha - P.hammerIn, P.swingPeriod) * 2 - 1) : 0);
  return (
    <AbsoluteFill style={{ background: "linear-gradient(180deg,#26307a 0%,#3552b8 45%,#3f66c9 70%)" }}>
      <Bokeh n={40} seed="whk" colors={["#ffffff", "#9ec5ff", "#dbe8ff"]} rMin={8} rMax={26} y0={120} y1={560} op={0.7} />
      {[260, 560, 1360, 1660].map((x, i) => <Glow key={i} x={x} y={200} r={130} color="rgba(255,255,255,0.8)" />)}
      <div style={{ position: "absolute", left: 0, right: 0, top: 860, bottom: 0, background: "linear-gradient(180deg,#6fcf6a,#3f9e45)" }} />
      <Full><ellipse cx={W / 2} cy={hy} rx={hw / 2 + 30} ry={120} fill="#8a5a33" /><ellipse cx={W / 2} cy={hy} rx={hw / 2} ry={96} fill="#3a2414" /></Full>
      <div style={{ position: "absolute", left: 0, top: 0, width: W, height: hy, overflow: "hidden" }}>
        <AbsoluteFill style={{ transform: `translateY(${rise}px)` }}>{char}</AbsoluteFill>
      </div>
      <Full><path d={`M${W / 2 - hw / 2 - 30},${hy} A${hw / 2 + 30},120 0 0 0 ${W / 2 + hw / 2 + 30},${hy} L${W / 2 + hw / 2},${hy} A${hw / 2},96 0 0 1 ${W / 2 - hw / 2},${hy}Z`} fill="#9b6a3d" /></Full>
      {f >= ha && <PropImg id="toy_hammer" x={1830 + 960 * Math.cos(rot * D2R)} y={-260 + 960 * Math.sin(rot * D2R)} w={440} ax={408 / 810} ay={208 / 1290} rot={rot + 89} />}
      {bubble && bubble(at + P.bubbleAt)}
    </AbsoluteFill>
  );
};

// ══ 12. 권투 글러브 펀치 교체 [ref4-apple 1:41:49] — 글러브 7f 진입 → 폭발 스타 → 회전하며 튕겨나감 → 빈자리 → 새 인물 ══
export const GlovePunchSwapParams = z.object({
  gloveIn: num(7, 1, 30, 1, "글러브 진입 길이", "timing", "f"),
  gloveSize: num(240, 80, 600, 5, "글러브 크기", "size", "px"),
  burst: num(130, 20, 400, 5, "폭발 스타 크기", "size", "px"),
  flyLen: num(14, 2, 60, 1, "튕겨나가는 길이", "timing", "f"),
  spin: num(-12, -60, 60, 1, "프레임당 회전", "motion", "°"),
  flyDx: num(760, -2000, 2000, 10, "튕김 x 거리", "motion", "px"),
  flyDy: num(-900, -2000, 2000, 10, "튕김 y 거리", "motion", "px"),
  emptyHold: num(30, 0, 120, 1, "빈자리 유지", "timing", "f"),
  dropLen: num(8, 0, 40, 1, "새 인물 낙하(0=하드 등장)", "timing", "f"),
});
export type GlovePunchSwapP = z.infer<typeof GlovePunchSwapParams>;
export const BoxingGloveSvg: React.FC<{ s: number; color: string }> = ({ s, color }) => (
  <g transform={`scale(${s / 240})`}>
    <rect x={-330} y={-50} width={200} height={100} rx={20} fill="#f2efe8" />
    <rect x={-150} y={-62} width={50} height={124} rx={14} fill="#e9e4da" />
    <path d="M-110,-90 C-60,-130 60,-130 110,-70 C150,-20 140,70 80,100 C20,125 -80,110 -110,70Z" fill={color} />
    <ellipse cx={-40} cy={70} rx={70} ry={42} fill={color} /><ellipse cx={20} cy={-60} rx={60} ry={26} fill="rgba(255,255,255,0.25)" />
  </g>
);
export const GlovePunchSwap: React.FC<{ at: number; x: number; y: number; oldNode: RN; newNode: RN; p?: Partial<GlovePunchSwapP> }> = ({ at, x, y, oldNode, newNode, p }) => {
  const P = def(GlovePunchSwapParams, p);
  const f = useCurrentFrame();
  const hit = at + P.gloveIn, hx = x - 150;
  const gx = f < hit ? lerp(f, at, hit, -P.gloveSize * 1.5, hx - P.gloveSize * 0.45, Easing.linear) : lerp(f, hit, hit + 3, hx - P.gloveSize * 0.45, hx - P.gloveSize * 0.2) - lerp(f, hit + 6, hit + 16, 0, hx + P.gloveSize * 2, Easing.in(Easing.quad));
  const t = (f - hit) / P.flyLen, back = hit + P.flyLen + P.emptyHold;
  const dk = P.dropLen > 0 ? lerp(f, back, back + P.dropLen, 1, 0, Easing.in(Easing.quad)) : 0;
  const land = f - back - P.dropLen;
  const sq = land >= 0 && land < 6 ? 1 - 0.06 * Math.sin((land / 6) * Math.PI) : 1;
  return (
    <AbsoluteFill>
      {f < hit && oldNode}
      {f >= hit && t < 1.05 && (
        <AbsoluteFill style={{ transformOrigin: `${x}px ${y}px`, transform: `translate(${P.flyDx * Easing.out(Easing.quad)(Math.min(1, t))}px,${P.flyDy * Math.min(1, t)}px) rotate(${P.spin * (f - hit)}deg)` }}>{oldNode}</AbsoluteFill>
      )}
      {f >= back && <AbsoluteFill style={{ transformOrigin: `${x}px ${y + 300}px`, transform: `translateY(${-1100 * dk}px) scale(${1 / sq},${sq})` }}>{newNode}</AbsoluteFill>}
      <Full>
        {f >= hit && f < hit + 14 && Array.from({ length: 10 }, (_, i) => {
          const g = f - hit, a = -1.2 + (i / 10) * 2.2 + random(`gd${i}`) * 0.3, d = 30 + g * (14 + 10 * random(`gv${i}`));
          return <rect key={i} x={hx + 40 + Math.cos(a) * d} y={y - 30 + Math.sin(a) * d} width={16} height={10} fill={i % 2 ? "#F28C28" : "#3a2a20"} opacity={1 - g / 14} transform={`rotate(${g * 30 + i * 40} ${hx + 40 + Math.cos(a) * d} ${y - 30 + Math.sin(a) * d})`} />;
        })}
        {f >= hit && t < 1 && Array.from({ length: 6 }, (_, i) => {
          const tt = Math.max(0, t - 0.08 * (i + 1)), px = x + P.flyDx * Easing.out(Easing.quad)(tt), py = y + P.flyDy * tt;
          return <circle key={`t${i}`} cx={px} cy={py} r={14 - i * 2} fill="#F28C28" opacity={0.8 - i * 0.12} />;
        })}
        {f >= hit && f < hit + 7 && (
          <g transform={`translate(${hx + 40},${y - 30}) scale(${kf(f, hit, [0, 2, 7], [0.2, 1.3, 0])})`}><StarSpark r={P.burst / 2} color="#FFB21E" /></g>
        )}
      </Full>
      {f >= at && gx > -P.gloveSize * 2 && gx < W && <PropImg id="boxing_glove_red" x={gx + (140 * P.gloveSize) / 240} y={y - 30} w={(488 * P.gloveSize) / 240} ax={1209 / 1210} ay={0.58} />}
    </AbsoluteFill>
  );
};
/** 세모지 왕좌 PNG(throne, 좌판 윗면 중앙 x,y · 폭 w) */
export const ThroneImg: React.FC<{ x: number; y: number; w: number }> = ({ x, y, w }) => <PropImg id="throne" x={x} y={y} w={w} ax={0.5} ay={820 / 1292} />;
/** 금색 왕좌(좌판 중앙 x,y · 폭 w) */
export const ThroneSvg: React.FC<{ x: number; y: number; w: number }> = ({ x, y, w }) => (
  <svg width={w} height={w * 1.5} viewBox="0 0 400 600" style={{ position: "absolute", left: x - w / 2, top: y - w * 1.0, overflow: "visible" }}>
    <path d="M60,420 L40,60 C40,10 110,0 200,0 C290,0 360,10 360,60 L340,420Z" fill="#E9A92A" />
    <path d="M100,400 L90,90 C90,55 140,50 200,50 C260,50 310,55 310,90 L300,400Z" fill="#C7302C" />
    {[70, 130, 200, 270, 330].map((cx, i) => <circle key={i} cx={cx} cy={i === 2 ? 14 : 30} r={18} fill="#F6CD52" />)}
    <rect x={20} y={380} width={70} height={210} rx={20} fill="#E9A92A" /><rect x={310} y={380} width={70} height={210} rx={20} fill="#E9A92A" />
    <rect x={60} y={400} width={280} height={60} rx={20} fill="#B82622" />
  </svg>
);

// ══ 13. 배경 블러·딤 인터럽트 [ref4-apple 1:32:23] — 장면 블러 12px + 밝기 -40% (8f) → 해설 인물 슬라이드업 + STOP 손 → 말풍선 팝 ══
export const BlurDimInterruptParams = z.object({
  dimLen: num(8, 1, 40, 1, "블러·딤 길이", "timing", "f"),
  blur: num(12, 0, 40, 1, "배경 블러", "look", "px"),
  dim: num(0.4, 0, 0.9, 0.05, "밝기 감소", "look"),
  slideDelay: num(4, 0, 60, 1, "인물 등장 지연", "timing", "f"),
  slideLen: num(10, 1, 40, 1, "슬라이드업 길이", "timing", "f"),
  slideDist: num(720, 0, 1400, 10, "슬라이드 거리", "motion", "px"),
  bubbleDelay: num(20, 0, 90, 1, "말풍선 지연", "timing", "f"),
  bubblePop: num(6, 1, 30, 1, "말풍선 블러 팝", "timing", "f"),
  reveal: choice("pop", ["pop", "wipe"] as const, "말풍선 등장(pop=블러 팝 · wipe=좌→우 폭 펼침)"),
  wipeLen: num(12, 1, 40, 1, "wipe: 펼침 길이", "timing", "f"),
  exit: choice("none", ["none", "drop"] as const, "퇴장(none · drop=아래로 낙하 + 딤 해제)"),
  exitAt: num(60, 0, 300, 1, "drop: 퇴장 시작(at 기준)", "timing", "f"),
  dropLen: num(8, 1, 30, 1, "drop: 낙하 길이", "timing", "f"),
  dropDist: num(1100, 100, 1600, 10, "drop: 낙하 거리", "motion", "px"),
  dropBlur: num(10, 0, 40, 1, "drop: 세로 모션블러", "look", "px"),
  undimLen: num(10, 1, 40, 1, "drop: 딤 해제 길이", "timing", "f"),
});
export type BlurDimInterruptP = z.infer<typeof BlurDimInterruptParams>;
// 말풍선 등장 옵션 — pop(기본) = 정적(호출측이 팝을 건다, 기존과 동일) / wipe = 좌→우 폭 펼침 + 글자 같은 방향 노출, 퇴장 축소·페이드 [설명형 레퍼런스 #14]
export const SpeechBubbleParams = z.object({
  reveal: choice("pop", ["pop", "wipe"] as const, "등장 방식(pop=정적·호출측 팝 · wipe=좌→우 폭 펼침)"),
  wipeLen: num(12, 1, 40, 1, "wipe: 펼침 길이", "timing", "f"),
  outLen: num(3, 1, 20, 1, "wipe: 퇴장 축소·페이드", "timing", "f"),
  outScale: num(0.85, 0.3, 1, 0.01, "wipe: 퇴장 끝 크기(배)", "motion"),
});
export type SpeechBubbleP = z.infer<typeof SpeechBubbleParams>;
const SpeechBubbleBody: React.FC<{ x: number; y: number; w: number; h: number; text: string; tail?: "left" | "right"; size?: number; style?: React.CSSProperties }> = ({ x, y, w, h, text, tail = "left", size = 44, style }) => (
  <div style={{ position: "absolute", left: x - w / 2, top: y - h / 2, width: w, height: h, ...style }}>
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} style={{ position: "absolute", overflow: "visible" }}>
      <path d={tail === "left" ? `M${w * 0.2},${h * 0.8} L${-w * 0.08},${h * 1.02} L${w * 0.34},${h * 0.9}Z` : `M${w * 0.8},${h * 0.8} L${w * 1.08},${h * 1.02} L${w * 0.66},${h * 0.9}Z`} fill="#fff" />
      <ellipse cx={w / 2} cy={h / 2} rx={w / 2} ry={h / 2} fill="#fff" />
    </svg>
    <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", textAlign: "center", fontFamily: "Yeonsung", fontSize: size, color: "#1a1a1a", lineHeight: 1.1, whiteSpace: "pre-line" }}>{hz(text)}</div>
  </div>
);
/** 세모지 흰 타원 말풍선. reveal="wipe" 면 at 부터 스스로 펼쳐지고 out 에서 축소·페이드 */
export const SpeechBubble: React.FC<{ x: number; y: number; w: number; h: number; text: string; tail?: "left" | "right"; size?: number; at?: number; out?: number; p?: Partial<SpeechBubbleP> }> = ({ x, y, w, h, text, tail = "left", size = 44, at = 0, out, p }) => {
  const P = def(SpeechBubbleParams, p);
  const f = useCurrentFrame();
  if (P.reveal !== "wipe") return <SpeechBubbleBody x={x} y={y} w={w} h={h} text={text} tail={tail} size={size} />;
  if (f < at || (out !== undefined && f >= out + P.outLen)) return null;
  const k = lerp(f, at, at + P.wipeLen, 0, 1, Easing.out(Easing.cubic));
  const ko = out !== undefined ? lerp(f, out, out + P.outLen, 1, 0, Easing.linear) : 1;
  // 꼬리가 박스 밖(−8%~108%)으로 나가므로 여유 폭을 두고 왼쪽부터 오른쪽으로 열린다
  const x0 = -0.1 * w, x1 = 1.1 * w, edge = x0 + (x1 - x0) * k;
  const ox = tail === "left" ? x - w / 2 - 0.08 * w : x + w / 2 + 0.08 * w, oy = y + h * 0.52;
  return (
    <div style={{ position: "absolute", inset: 0, transformOrigin: `${ox}px ${oy}px`, transform: ko < 1 ? `scale(${P.outScale + (1 - P.outScale) * ko})` : undefined, opacity: ko }}>
      <SpeechBubbleBody x={x} y={y} w={w} h={h} text={text} tail={tail} size={size} style={{ clipPath: `inset(-20% ${Math.max(0, w - edge)}px -20% -20%)` }} />
    </div>
  );
};
export const BlurDimInterrupt: React.FC<{ at: number; bg: RN; narrator: RN; bubble?: { x: number; y: number; w: number; h: number; text: string }; p?: Partial<BlurDimInterruptP> }> = ({ at, bg, narrator, bubble, p }) => {
  const P = def(BlurDimInterruptParams, p);
  const f = useCurrentFrame();
  const k = lerp(f, at, at + P.dimLen, 0, 1, Easing.out(Easing.quad));
  const sa = at + P.slideDelay, sk = lerp(f, sa, sa + P.slideLen, 1, 0, EXPO_OUT);
  const ba = at + P.bubbleDelay, bp = blurPop(f, ba, P.bubblePop, 1.25, 10);
  const wipe = P.reveal === "wipe";
  const bubbleNode = bubble && f >= ba && (wipe
    ? <SpeechBubble {...bubble} at={ba} p={{ reveal: "wipe", wipeLen: P.wipeLen }} />
    : <div style={{ position: "absolute", inset: 0, transformOrigin: `${bubble.x}px ${bubble.y}px`, transform: `scale(${bp.s})`, opacity: bp.op, filter: bp.blur > 0.3 ? `blur(${bp.blur}px)` : undefined }}><SpeechBubble {...bubble} /></div>);
  if (P.exit === "drop" && f >= at + P.exitAt) {
    // 낙하 퇴장: 인물·말풍선이 아래로 ease-in 낙하(세로 모션블러) + 배경 딤·블러 해제
    const e0 = at + P.exitAt, u = lerp(f, e0, e0 + P.dropLen, 0, 1, Easing.in(Easing.quad));
    const kd = k * lerp(f, e0, e0 + P.undimLen, 1, 0, Easing.out(Easing.quad));
    const vb = P.dropBlur * Math.sin(Math.PI * Math.min(1, u)) + (u > 0 ? 1 : 0), fid = `bdiDrop${at}`;
    return (
      <AbsoluteFill>
        <AbsoluteFill style={{ filter: kd > 0 ? `blur(${P.blur * kd}px) brightness(${1 - P.dim * kd})` : undefined, transform: `scale(${1 + 0.02 * kd})` }}>{bg}</AbsoluteFill>
        {u < 1 && (
          <AbsoluteFill style={{ transform: `translateY(${P.dropDist * u}px)`, filter: vb > 0.3 ? `url(#${fid})` : undefined }}>
            <svg width={0} height={0} style={{ position: "absolute" }}><filter id={fid} x="-5%" y="-30%" width="110%" height="160%"><feGaussianBlur stdDeviation={`0 ${vb.toFixed(2)}`} /></filter></svg>
            {f >= sa && <AbsoluteFill style={{ transform: `translateY(${P.slideDist * sk}px)` }}>{narrator}</AbsoluteFill>}
            {bubbleNode}
          </AbsoluteFill>
        )}
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ filter: k > 0 ? `blur(${P.blur * k}px) brightness(${1 - P.dim * k})` : undefined, transform: `scale(${1 + 0.02 * k})` }}>{bg}</AbsoluteFill>
      {f >= sa && <AbsoluteFill style={{ transform: `translateY(${P.slideDist * sk}px)` }}>{narrator}</AbsoluteFill>}
      {bubbleNode}
    </AbsoluteFill>
  );
};

// ══ 14. 칼싸움 + 스파크 클래시 [ref4-hyundai 0:55:37] — 불꽃 배경, 1.3배 좌→우 팬 20f → 1.0 풀백, 칼 ±4°, 8각 별 스파크 ══
export const SwordDuelParams = z.object({
  camScale: num(1.3, 1, 2.5, 0.05, "카메라 시작 배율", "motion"),
  panLen: num(20, 1, 90, 1, "좌→우 팬 길이", "timing", "f"),
  panX: num(260, 0, 900, 10, "팬 거리(±)", "motion", "px"),
  pullAt: num(34, 0, 150, 1, "풀백 시작", "timing", "f"),
  pullLen: num(16, 1, 60, 1, "풀백 길이", "timing", "f"),
  wobble: num(4, 0, 20, 0.5, "칼 흔들림(±)", "motion", "°"),
  wobblePeriod: num(8, 2, 40, 1, "칼 흔들림 반주기", "timing", "f"),
  sparkEvery: num(30, 4, 120, 1, "스파크 간격", "timing", "f"),
  sparkLen: num(6, 2, 30, 1, "스파크 길이", "timing", "f"),
  sparkSize: num(80, 20, 300, 2, "스파크 크기", "size", "px"),
  flameSpeed: num(3, 0, 20, 0.5, "불꽃 흐름 속도", "motion", "px/f"),
  bg: col("#F08A24", "배경 주황"),
  flame: col("#E4381F", "불꽃 빨강"),
});
export type SwordDuelP = z.infer<typeof SwordDuelParams>;
/** 흐르는 불꽃 모양 레이어 */
export const FlameField: React.FC<{ color: string; speed: number; seed?: string; n?: number; op?: number }> = ({ color, speed, seed = "ff", n = 26, op = 1 }) => {
  const f = useCurrentFrame();
  return (
    <Full style={{ opacity: op }}>
      {Array.from({ length: n }, (_, i) => {
        const x = (i % 7) * 300 + 150 * (Math.floor(i / 7) % 2) + 60 * random(`${seed}x${i}`) - 60;
        const span = H + 500, y0 = Math.floor(i / 7) * 330 + 100 * random(`${seed}y${i}`);
        const y = ((((y0 - f * speed * (0.8 + 0.4 * random(`${seed}v${i}`))) % span) + span) % span) - 200;
        const s = 0.9 + 0.7 * random(`${seed}s${i}`), sw = Math.sin(f / 9 + i) * 10;
        return <path key={i} transform={`translate(${x},${y}) scale(${s}) rotate(${sw})`} d="M0,160 C-90,150 -110,60 -60,0 C-40,40 -20,40 -10,20 C-20,-40 20,-100 60,-140 C40,-60 110,-20 90,70 C80,130 40,160 0,160Z" fill={color} />;
      })}
    </Full>
  );
};
export const SwordSvg: React.FC<{ len?: number }> = ({ len = 520 }) => (
  <g>
    <path d={`M-10,0 L-10,${-len} L0,${-len - 40} L10,${-len} L10,0Z`} fill="#7c8088" />
    <path d={`M0,0 L0,${-len - 36}`} stroke="#b9bdc4" strokeWidth={4} />
    <path d="M-50,-4 C-40,20 40,20 50,-4 C40,6 -40,6 -50,-4Z" fill="#555a62" />
    <rect x={-8} y={0} width={16} height={60} rx={6} fill="#3a3a40" /><circle cx={0} cy={66} r={12} fill="#555a62" />
  </g>
);
export const SwordDuel: React.FC<{ at: number; clash: Pt; render: (wobbleL: number, wobbleR: number) => RN; p?: Partial<SwordDuelP> }> = ({ at, clash, render, p }) => {
  const P = def(SwordDuelParams, p);
  const f = useCurrentFrame();
  const g = f - at;
  const pan = lerp(f, at, at + P.panLen, P.panX, -P.panX, Easing.inOut(Easing.cubic));
  const pk = lerp(f, at + P.pullAt, at + P.pullAt + P.pullLen, 0, 1, Easing.inOut(Easing.cubic));
  const s = P.camScale + (1 - P.camScale) * pk, tx = pan * (1 - pk);
  const wl = P.wobble * (pp01(f, P.wobblePeriod) * 2 - 1), wr = P.wobble * (pp01(f, P.wobblePeriod, P.wobblePeriod * 0.5) * 2 - 1);
  const sg = g < 0 ? -1 : (g - P.sparkEvery * 0.5) % P.sparkEvery;
  const sp = g >= P.sparkEvery * 0.5 && sg >= 0 && sg < P.sparkLen ? kf(sg, 0, [0, P.sparkLen * 0.4, P.sparkLen], [0, 1.2, 0]) : 0;
  return (
    <AbsoluteFill style={{ background: P.bg }}>
      <AbsoluteFill style={{ transform: `translateX(${tx}px) scale(${s})`, transformOrigin: "50% 45%" }}>
        <FlameField color={P.flame} speed={P.flameSpeed} />
        <FlameField color="#F9B233" speed={P.flameSpeed * 0.7} seed="ff2" n={14} op={0.6} />
        {render(wl, wr)}
        {sp > 0 && <Full><g transform={`translate(${clash[0]},${clash[1]}) scale(${sp}) rotate(${sg * 12})`}><StarSpark r={P.sparkSize / 2} color="#FFD23F" core="#FFF6C8" /></g>
          {Array.from({ length: 8 }, (_, i) => { const a = (i / 8) * TAU + 0.4, d = 20 + sg * 16; return <circle key={i} cx={clash[0] + Math.cos(a) * d} cy={clash[1] + Math.sin(a) * d} r={5} fill="#FFB21E" opacity={1 - sg / P.sparkLen} />; })}</Full>}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ══ 15. '천지창조' 손 패러디 [ref4-hyundai 1:00:24] — 금색 보케, 인물 좌하단 8f 슬라이드인, 명화 팔 좌상단 대각 12f + 손끝 떨림 ══
export const CreationHandParams = z.object({
  charIn: num(8, 1, 40, 1, "인물 슬라이드인 길이", "timing", "f"),
  charDist: num(320, 0, 1000, 10, "인물 슬라이드 거리", "motion", "px"),
  armDelay: num(4, 0, 60, 1, "팔 진입 지연", "timing", "f"),
  armIn: num(12, 1, 60, 1, "팔 진입 길이", "timing", "f"),
  armDist: num(760, 0, 1600, 10, "팔 진입 거리", "motion", "px"),
  tremble: num(2.5, 0, 12, 0.5, "손끝 떨림(±)", "motion", "°"),
  tremblePeriod: num(5, 2, 30, 1, "떨림 반주기", "timing", "f"),
  bokeh: num(28, 0, 80, 1, "보케 개수", "size"),
});
export type CreationHandP = z.infer<typeof CreationHandParams>;
/** 명화 풍 뻗은 팔(손끝 = 로컬 0,0, 팔은 왼쪽 위로 뻗어 나감) */
export const ReachArmSvg: React.FC<{ fing?: number }> = ({ fing = 0 }) => (
  <g>
    <defs>
      <linearGradient id="armG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#F0C9A4" /><stop offset="0.55" stopColor="#D9A07A" /><stop offset="1" stopColor="#A8704F" /></linearGradient>
      <linearGradient id="armH" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stopColor="#D69C74" /><stop offset="1" stopColor="#EBC19C" /></linearGradient>
    </defs>
    <path d="M-900,-520 C-700,-420 -520,-330 -330,-250 C-250,-220 -200,-170 -170,-150 L-150,-60 C-260,-100 -420,-140 -600,-200 C-760,-250 -880,-320 -960,-380Z" fill="url(#armG)" />
    <path d="M-330,-250 C-300,-240 -240,-205 -175,-160" stroke="rgba(120,70,40,0.35)" strokeWidth={10} fill="none" />
    <g transform={`rotate(${fing} -170 -110)`}>
      <path d="M-200,-160 C-150,-175 -90,-150 -60,-120 C-40,-100 -20,-80 0,-60 C8,-50 -2,-40 -14,-46 C-40,-62 -60,-72 -80,-80 C-90,-60 -110,-30 -140,-30 C-170,-30 -190,-60 -200,-80Z" fill="url(#armH)" />
      <path d="M-120,-60 C-100,-40 -70,-20 -50,-12 C-40,-8 -44,4 -56,2 C-80,-6 -110,-22 -130,-40Z" fill="#DDA985" />
      <path d="M-150,-40 C-140,-10 -120,14 -104,24 C-96,30 -104,40 -114,36 C-132,28 -150,4 -162,-24Z" fill="#D59C78" />
      <path d="M-80,-80 C-60,-70 -30,-58 -8,-50" stroke="rgba(120,70,40,0.3)" strokeWidth={4} fill="none" />
    </g>
  </g>
);
export const CreationHand: React.FC<{ at: number; char: RN; other?: RN; tip: Pt; p?: Partial<CreationHandP> }> = ({ at, char, other, tip, p }) => {
  const P = def(CreationHandParams, p);
  const f = useCurrentFrame();
  const ck = lerp(f, at, at + P.charIn, 1, 0, EXPO_OUT);
  const aa = at + P.armDelay, ak = lerp(f, aa, aa + P.armIn, 1, 0, Easing.out(Easing.cubic));
  const tr = f > aa + P.armIn ? P.tremble * (pp01(f, P.tremblePeriod) * 2 - 1) : 0;
  return (
    <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 40%, #FBE7A6 0%, #F2C766 45%, #D9A441 100%)" }}>
      <Bokeh n={Math.round(P.bokeh)} seed="cr" colors={["#FFF7DA", "#FFD0E0", "#FFFFFF"]} rMin={10} rMax={40} op={0.55} drift={6} />
      {other}
      {f >= at && <AbsoluteFill style={{ transform: `translate(${-P.charDist * ck}px,${P.charDist * 0.6 * ck}px)` }}>{char}</AbsoluteFill>}
      {f >= aa && (() => {
        // creation_forearm / creation_hand PNG(같은 크롭 1359×810): 손끝 (1352,630), 손목 (795,496). 폭 1000px
        const w = 1000, sc = w / 1359, tx = tip[0] - P.armDist * 0.8 * ak, ty = tip[1] - P.armDist * 0.6 * ak, l = tx - 1352 * sc, t = ty - 630 * sc;
        return <><PropImg id="creation_forearm" x={l} y={t} w={w} ax={0} ay={0} /><PropImg id="creation_hand" x={l + 795 * sc} y={t + 496 * sc} w={w} ax={795 / 1359} ay={496 / 810} rot={tr} /></>;
      })()}
    </AbsoluteFill>
  );
};

// ══ 16. 밧줄 건너뛰기(카메라 추적) [ref4-hyundai 1:02:42] — 진자 ±8°/40f, 포물선 12f 도약, 잡을 때 별 버스트, 카메라 우측 팬 30f ══
export const RopeSwingParams = z.object({
  swingDeg: num(8, 0, 40, 0.5, "밧줄 흔들림(±)", "motion", "°"),
  swingPeriod: num(40, 8, 160, 1, "진자 주기", "timing", "f"),
  hold: num(30, 4, 120, 1, "한 밧줄에 매달리는 시간", "timing", "f"),
  jumpLen: num(12, 2, 40, 1, "도약 길이", "timing", "f"),
  jumpH: num(140, 0, 500, 5, "도약 높이", "motion", "px"),
  bodyRot: num(15, 0, 60, 1, "도약 중 몸 회전", "motion", "°"),
  burstLen: num(6, 2, 20, 1, "잡기 별 버스트 길이", "timing", "f"),
  panLen: num(30, 1, 90, 1, "카메라 팬 길이", "timing", "f"),
  panDist: num(400, 0, 1200, 10, "도약당 카메라 이동", "motion", "px"),
  gap: num(520, 200, 1000, 10, "밧줄 간격", "size", "px"),
  grip: num(560, 200, 900, 10, "잡는 지점(매단 곳에서 아래로)", "size", "px"),
});
export type RopeSwingP = z.infer<typeof RopeSwingParams>;
export const UnionFlagSvg: React.FC<{ w: number }> = ({ w }) => {
  const h = w * 0.6;
  return (
    <g>
      <rect x={0} y={0} width={w} height={h} fill="#1f3f8c" />
      <path d={`M0,0 L${w},${h} M${w},0 L0,${h}`} stroke="#fff" strokeWidth={h * 0.2} />
      <path d={`M0,0 L${w},${h} M${w},0 L0,${h}`} stroke="#c8202f" strokeWidth={h * 0.07} />
      <path d={`M${w / 2},0 L${w / 2},${h} M0,${h / 2} L${w},${h / 2}`} stroke="#fff" strokeWidth={h * 0.32} />
      <path d={`M${w / 2},0 L${w / 2},${h} M0,${h / 2} L${w},${h / 2}`} stroke="#c8202f" strokeWidth={h * 0.18} />
    </g>
  );
};
/** char 는 손 잡는 점(0,0) 기준 로컬 좌표로 그린다 */
export const RopeSwing: React.FC<{ at: number; char: RN; ropes?: number; x0?: number; flag?: boolean; p?: Partial<RopeSwingP> }> = ({ at, char, ropes = 4, x0 = 420, flag = true, p }) => {
  const P = def(RopeSwingParams, p);
  const f = useCurrentFrame();
  const L = 900, top = -40;
  const ang = (i: number, fr: number) => P.swingDeg * Math.sin(((fr + i * 11) / P.swingPeriod) * TAU);
  const grip = (i: number, fr: number): Pt => { const a = ang(i, fr) * D2R, r = P.grip; return [x0 + i * P.gap + Math.sin(a) * r, top + Math.cos(a) * r]; };
  const seg = P.hold + P.jumpLen, g = Math.max(0, f - at);
  const i = Math.min(ropes - 1, Math.floor(g / seg)), c = g - i * seg;
  let pos: Pt, rot: number, jumping = false;
  if (i >= ropes - 1 || c < P.hold) { pos = grip(i, f); rot = ang(i, f); }
  else {
    jumping = true;
    const t = (c - P.hold) / P.jumpLen, a = grip(i, f), b = grip(i + 1, f), e = Easing.inOut(Easing.quad)(t);
    pos = [a[0] + (b[0] - a[0]) * e, a[1] + (b[1] - a[1]) * e - P.jumpH * 4 * t * (1 - t)];
    rot = ang(i, f) + P.bodyRot * Math.sin(t * Math.PI);
  }
  // 카메라: 도약 시작마다 panDist 만큼 easeInOut
  let cam = 0;
  for (let j = 0; j < ropes - 1; j++) cam += P.panDist * lerp(f, at + j * seg + P.hold, at + j * seg + P.hold + P.panLen, 0, 1, Easing.inOut(Easing.cubic));
  const bg = i > 0 && !jumping ? f - (at + i * seg) : -1;
  const gp = grip(i, f);
  return (
    <AbsoluteFill style={{ background: "linear-gradient(180deg,#3b2a63 0%,#6a4f93 50%,#8a6bb0 100%)" }}>
      <AbsoluteFill style={{ transform: `translateX(${-cam * 0.4}px)` }}>
        <Full>
          {Array.from({ length: 9 }, (_, k) => <ellipse key={k} cx={k * 420 + 120} cy={560 + 80 * Math.sin(k * 1.7)} rx={300} ry={220} fill="#9d84c4" opacity={0.35} />)}
          {Array.from({ length: 22 }, (_, k) => { const x = k * 190 + 60 * random(`st${k}`), l = 120 + 200 * random(`sl${k}`); return <path key={`s${k}`} d={`M${x - 50},0 L${x + 50},0 L${x + 6},${l} L${x - 4},${l}Z`} fill="#2b1d47" opacity={0.85} />; })}
          {Array.from({ length: 20 }, (_, k) => { const x = k * 200 + 80 * random(`bt${k}`), l = 80 + 160 * random(`bl${k}`); return <path key={`b${k}`} d={`M${x - 60},${H} L${x + 60},${H} L${x + 5},${H - l}Z`} fill="#2b1d47" opacity={0.8} />; })}
        </Full>
      </AbsoluteFill>
      <AbsoluteFill style={{ transform: `translateX(${-cam}px)` }}>
        <Full>
          {Array.from({ length: ropes }, (_, k) => {
            const a = ang(k, f), px = x0 + k * P.gap;
            return (
              <g key={k} transform={`rotate(${-a} ${px} ${top})`}>
                <line x1={px} y1={top} x2={px} y2={top + L} stroke="#C8894A" strokeWidth={18} strokeLinecap="round" />
                <line x1={px} y1={top} x2={px} y2={top + L} stroke="#8F5A2B" strokeWidth={18} strokeDasharray="6 14" />
                {flag && k === ropes - 1 && <g transform={`translate(${px + 8},${top + 120})`}><UnionFlagSvg w={170} /></g>}
              </g>
            );
          })}
        </Full>
        <div style={{ position: "absolute", left: pos[0], top: pos[1], transform: `rotate(${-rot}deg)`, transformOrigin: "0 0" }}>{char}</div>
        {bg >= 0 && bg < P.burstLen && <Full><g transform={`translate(${gp[0]},${gp[1]}) scale(${kf(bg, 0, [0, P.burstLen * 0.35, P.burstLen], [0.2, 1.1, 0])})`}><StarSpark r={70} color="#FF8A1E" /></g></Full>}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ══ 17. 화분 성장 은유 [ref4-hyundai 1:16:32] — 화분 3개, 물뿌리개 물줄기 루프, 건물이 흙에서 솟아 자람 + 반짝임 ══
export const GrowthPotParams = z.object({
  canIn: num(8, 1, 40, 1, "물뿌리개 기울임 길이", "timing", "f"),
  canTilt: num(28, 0, 80, 1, "물뿌리개 기울기", "motion", "°"),
  riseDelay: num(10, 0, 90, 1, "건물 성장 지연", "timing", "f"),
  riseLen: num(40, 4, 150, 1, "건물 성장 길이", "timing", "f"),
  riseFrom: num(0, 0, 0.95, 0.05, "성장 시작 높이 비율", "motion"),
  sparkleDelay: num(4, 0, 60, 1, "반짝임 지연(성장 후)", "timing", "f"),
  dropSpeed: num(14, 1, 60, 1, "물방울 속도", "motion", "px/f"),
  gap: num(420, 200, 700, 10, "화분 간격", "size", "px"),
});
export type GrowthPotP = z.infer<typeof GrowthPotParams>;
const Building: React.FC<{ w: number; h: number; label: string }> = ({ w, h, label }) => (
  <g>
    <rect x={-w / 2} y={-h} width={w} height={h} fill="#8A96A8" />
    {Array.from({ length: Math.floor((h - 70) / 44) }, (_, r) => Array.from({ length: 4 }, (_, c) => <rect key={`${r}-${c}`} x={-w / 2 + 14 + c * ((w - 28) / 4)} y={-h + 66 + r * 44} width={(w - 28) / 4 - 10} height={30} fill={(r + c) % 3 ? "#9BD3EC" : "#E9F6FB"} />))}
    <rect x={-w / 2 - 6} y={-h - 4} width={w + 12} height={46} fill="#F4F4F4" />
    <text x={0} y={-h + 28} textAnchor="middle" fontFamily="NeoHv" fontSize={22} fill="#333">{label}</text>
  </g>
);
export const GrowthPot: React.FC<{ at: number; label?: string; target?: number; p?: Partial<GrowthPotP> }> = ({ at, label = "(주)현대양행", target = 2, p }) => {
  const P = def(GrowthPotParams, p);
  const f = useCurrentFrame();
  const cx = W / 2, potY = 860, pots = [cx - P.gap, cx, cx + P.gap];
  const tilt = lerp(f, at, at + P.canIn, 0, P.canTilt, EXPO_OUT);
  const ra = at + P.riseDelay, rk = lerp(f, ra, ra + P.riseLen, P.riseFrom, 1, Easing.out(Easing.cubic));
  const bw = 200, bh = propH("office_building_small", 200);
  // 화분 PNG(pot_leaves 뒤 / pot_body 앞, 같은 크롭 1048×1165): 화분 몸통 중앙 x≈498, 테두리 윗면 y≈504, 흙면 y≈540
  const PS = 0.48, soil = potY - 50 + (540 - 504) * PS;
  const potBox = (x: number): Pt => [x - 498 * PS, potY - 50 - 504 * PS];
  // 물뿌리개 PNG(watering_can 1418×809): 몸통 축 (1000,470), 물뿌리개 꽃 (116,145). 폭 460
  const CW = 460, cs = CW / 1418, piv: Pt = [pots[target] + 380, 250];
  const rose = rotAbout([piv[0] + (116 - 1000) * cs, piv[1] + (145 - 470) * cs], piv, -10 - tilt);
  const sa = ra + P.riseLen + P.sparkleDelay;
  return (
    <AbsoluteFill style={{ background: "#D9C3A5" }}>
      {pots.map((x, i) => {
        const [l, t] = potBox(x), by = potY - 10 + bh * (1 - (i === target ? rk : 1));
        return (
          <React.Fragment key={i}>
            <PropImg id="pot_leaves" x={l} y={t} w={1048 * PS} ax={0} ay={0} />
            <div style={{ position: "absolute", left: x - 300, top: -200, width: 600, height: soil + 200, overflow: "hidden" }}>
              <PropImg id="office_building_small" x={300} y={by + 200} w={bw} ax={0.5} ay={1}>
                <div style={{ position: "absolute", left: 0, right: 0, top: bh * 0.035, height: bh * 0.06, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "NeoHv", fontSize: 20, color: "#333", whiteSpace: "nowrap" }}>{label}</div>
              </PropImg>
            </div>
            <PropImg id="pot_body" x={l} y={t} w={1048 * PS} ax={0} ay={0} />
          </React.Fragment>
        );
      })}
      <Full>
        {f >= at && Array.from({ length: 14 }, (_, k) => {
          const tt = ((f - at) * P.dropSpeed + k * 50) % 700;
          return <ellipse key={k} cx={rose[0] - 20 - tt * 0.34 + 8 * Math.sin(k)} cy={rose[1] + 30 + tt} rx={7} ry={12} fill="#7BC6F0" opacity={tilt / Math.max(1, P.canTilt)} />;
        })}
      </Full>
      <PropImg id="watering_can" x={piv[0]} y={piv[1]} w={CW} ax={1000 / 1418} ay={470 / 809} rot={-10 - tilt} />
      <Full>
        {f >= sa && [[pots[target] - 80, potY - bh - 60, 70], [pots[target] + 110, potY - bh + 40, 50]].map(([sx, sy, sz], k) => {
          const g = f - sa - k * 4;
          if (g < 0) return null;
          const s = kf(g, 0, [0, 4], [0, 1], Easing.out(Easing.quad)) * (0.35 + 0.65 * Math.abs(Math.cos((g / 20) * Math.PI)));
          return <path key={k} transform={`translate(${sx},${sy}) scale(${(sz / 100) * s})`} d="M0,-50 C6,-8 8,-6 50,0 C8,6 6,8 0,50 C-6,8 -8,6 -50,0 C-8,-6 -6,-8 0,-50Z" fill="#FFF3B0" />;
        })}
      </Full>
    </AbsoluteFill>
  );
};

// ══ 18. 왕관 날아감 [ref4-hyundai 1:45:18] — ±6° 3f×2 흔들 → 우상향 튀어올라 포물선 낙하 18f, +110° 회전, 모션블러 ══
export const CrownKnockoffParams = z.object({
  wobbleDeg: num(6, 0, 30, 0.5, "흔들림 각도(±)", "motion", "°"),
  wobbleLen: num(3, 1, 12, 1, "흔들림 한 번 길이", "timing", "f"),
  wobbleN: num(2, 0, 6, 1, "흔들림 왕복 수", "motion"),
  flyLen: num(18, 4, 60, 1, "날아가는 길이", "timing", "f"),
  flyDx: num(560, -1500, 1500, 10, "가로 이동", "motion", "px"),
  flyUp: num(160, 0, 600, 5, "튀어오르는 높이", "motion", "px"),
  fall: num(900, 0, 1600, 10, "낙하 거리", "motion", "px"),
  spin: num(110, -360, 360, 5, "누적 회전", "motion", "°"),
  blur: num(8, 0, 30, 1, "모션블러", "look", "px"),
});
export type CrownKnockoffP = z.infer<typeof CrownKnockoffParams>;
export const CrownKnockoff: React.FC<{ at: number; x: number; y: number; w: number; text?: string; children?: RN; p?: Partial<CrownKnockoffP> }> = ({ at, x, y, w, text, children, p }) => {
  const P = def(CrownKnockoffParams, p);
  const f = useCurrentFrame();
  const g = f - at, WL = P.wobbleLen * 2 * Math.round(P.wobbleN);
  let dx = 0, dy = 0, rot = 0, b = 0;
  if (g >= 0 && g < WL) rot = P.wobbleDeg * (Math.floor(g / P.wobbleLen) % 2 ? 1 : -1);
  else if (g >= WL) {
    const t = Math.min(1.2, (g - WL) / P.flyLen);
    dx = P.flyDx * t; dy = -4 * P.flyUp * t * (1 - t) + P.fall * t * t * t; rot = P.spin * t; b = t < 1.2 ? P.blur * Math.min(1, t * 3) : 0;
  }
  return (
    <AbsoluteFill>
      {children}
      <CrownImg x={x + dx} y={y + dy} w={w} text={text} style={{ transformOrigin: "50% 60%", transform: `rotate(${rot}deg)`, filter: b > 0.3 ? `blur(${b}px)` : undefined }} />
    </AbsoluteFill>
  );
};
/** 흑색 붓질 텍스처 배경 */
export const BrushDarkBg: React.FC<{ seed?: string }> = ({ seed = "brush" }) => (
  <AbsoluteFill style={{ background: "#161616" }}>
    <Full>
      {Array.from({ length: 70 }, (_, i) => {
        const y = H * random(`${seed}y${i}`), x = -200 + W * random(`${seed}x${i}`), l = 500 + 900 * random(`${seed}l${i}`), sw = 6 + 30 * random(`${seed}w${i}`);
        return <path key={i} d={`M${x},${y} q${l / 2},${-40 * random(`${seed}q${i}`)} ${l},${-20}`} stroke={`rgba(255,255,255,${0.04 + 0.08 * random(`${seed}o${i}`)})`} strokeWidth={sw} fill="none" strokeLinecap="round" />;
      })}
    </Full>
  </AbsoluteFill>
);

// ══ 19. 은유 괴물 + 라벨 [ref4-hyundai 1:11:20 '인플레이션'] — 보라 문어 촉수 루프(20f) + 배 흔들림 '질질' + 이름표 ══
export const OctopusMonsterParams = z.object({
  tentPeriod: num(20, 4, 80, 1, "촉수 흔들림 주기", "timing", "f"),
  tentAmp: num(14, 0, 60, 1, "촉수 흔들림 세기", "motion", "px"),
  shipRock: num(3, 0, 20, 0.5, "배 흔들림(±)", "motion", "°"),
  shipPeriod: num(16, 4, 80, 1, "배 흔들림 반주기", "timing", "f"),
  labelAt: num(6, 0, 90, 1, "라벨 등장", "timing", "f"),
  labelPop: num(6, 1, 30, 1, "라벨 블러 팝", "timing", "f"),
  size: num(1, 0.4, 2.5, 0.05, "크기(배)", "size"),
});
export type OctopusMonsterP = z.infer<typeof OctopusMonsterParams>;
export const OctopusMonster: React.FC<{ at: number; x: number; y: number; label?: string; ship?: boolean; p?: Partial<OctopusMonsterP> }> = ({ at, x, y, label = "인플레이션", ship = true, p }) => {
  const P = def(OctopusMonsterParams, p);
  const f = useCurrentFrame();
  const s = P.size;
  const wv = (i: number, k: number) => P.tentAmp * Math.sin(((f + i * 5) / P.tentPeriod) * TAU + k);
  // octopus_body / octopus_tentacle / cargo_ship PNG. 촉수 = 밑동(이미지 위 (300,20))을 축으로 회전 + 흔들림
  const tent = (i: number, bx: number, by: number, rot: number, len: number) => (
    <PropImg key={`t${i}`} id="octopus_tentacle" x={x + bx * s} y={y + by * s} w={(533 * len * s) / 1462} ax={300 / 533} ay={20 / 1462} rot={rot + wv(i, 0) * 0.5} flipX={rot < 0} />
  );
  const rock = P.shipRock * (pp01(f, P.shipPeriod) * 2 - 1);
  const lp = blurPop(f, at + P.labelAt, P.labelPop, 1.3, 10);
  return (
    <AbsoluteFill>
      {tent(0, -130, 40, 75, 380)}{tent(1, -70, 70, 55, 300)}
      <PropImg id="octopus_body" x={x} y={y - 10 * s} w={480 * s} />
      {tent(2, 80, 70, -60, 320)}{tent(3, 150, 30, -80, 400)}
      {ship && <PropImg id="cargo_ship" x={x + 600 * s} y={y + 50 * s} w={480 * s} ax={0.5} ay={0.85} rot={rock} />}
      <Full>
        {ship && <text x={x + 790 * s} y={y - 70 * s} fontFamily="Yeonsung" fontSize={44 * s} fill="#fff" transform={`rotate(-8 ${x + 790 * s} ${y - 70 * s})`}>질질</text>}
      </Full>
      {f >= at + P.labelAt && (
        <div style={{ position: "absolute", left: x - 120 * s, top: y - 300 * s, transform: `translate(-50%,-50%) scale(${lp.s})`, opacity: lp.op, filter: lp.blur > 0.3 ? `blur(${lp.blur}px)` : undefined }}>
          <div style={{ background: "#232323", color: "#fff", fontFamily: "NeoHv", fontSize: 46 * s, padding: "8px 26px", borderRadius: 10, whiteSpace: "nowrap" }}>{label}</div>
          <div style={{ width: 0, height: 0, margin: "0 auto", borderLeft: "14px solid transparent", borderRight: "14px solid transparent", borderTop: "18px solid #232323" }} />
        </div>
      )}
    </AbsoluteFill>
  );
};

// ══ 20. 꼭두각시 조종자 [ref4-samsung 1:34:28] — 받침대 인물 슬라이드인 5f + '권력' 구슬 5개 2f 스태거 + 줄 진자 ±6°/24f ══
export const MarionetteParams = z.object({
  slideLen: num(5, 1, 30, 1, "슬라이드인 길이", "timing", "f"),
  slideDist: num(520, 0, 1200, 10, "슬라이드 거리", "motion", "px"),
  slideBlur: num(18, 0, 60, 1, "슬라이드 모션블러", "look", "px"),
  beadAt: num(6, 0, 60, 1, "구슬 팝 시작", "timing", "f"),
  beadStagger: num(2, 0, 20, 1, "구슬 스태거", "timing", "f"),
  beadPop: num(5, 1, 20, 1, "구슬 팝 길이", "timing", "f"),
  beadR: num(30, 10, 80, 1, "구슬 반지름", "size", "px"),
  swingDeg: num(6, 0, 30, 0.5, "줄 흔들림(±)", "motion", "°"),
  swingPeriod: num(24, 4, 90, 1, "줄 흔들림 주기", "timing", "f"),
  bgBlur: num(20, 0, 60, 1, "배경 사진 블러", "look", "px"),
  pedestal: col("#C8553D", "받침대 색"),
  bead: col("#E94E83", "구슬 색"),
});
export type MarionetteP = z.infer<typeof MarionetteParams>;
/** 세모지 리그 인물(cast, 기본 c2_boss)이 받침대 위에서 양팔(arm_out_side)을 수평으로 벌리고, 손에서 구슬 줄이 늘어진다 */
export const Marionette: React.FC<{ at: number; bg?: string; x: number; y: number; h?: number; bead?: string; cast?: CastId; p?: Partial<MarionetteP> }> = ({ at, bg, x, y, h = 560, bead = "권력", cast = "c2_boss", p }) => {
  const P = def(MarionetteParams, p);
  const f = useCurrentFrame();
  const sk = lerp(f, at, at + P.slideLen, 1, 0, Easing.out(Easing.quad));
  const g = f - at - P.beadAt;
  const sw = g > 0 ? P.swingDeg * Math.sin((g / P.swingPeriod) * TAU) : 0;
  const o = { x, y: y + 4, h };
  const rR = -30 + sw * 0.6, rL = 30 + sw * 0.6;                     // arm_out_side 손(≈30° 위)을 수평으로
  const hL = handScreen(cast, o, "arm_out_side", "r", rR), hR = handScreen(cast, o, "arm_out_side", "l", rL);
  const beads: { hand: Pt; len: number; dx: number }[] = [
    { hand: hL, len: 150, dx: -30 }, { hand: hL, len: 250, dx: 20 }, { hand: hR, len: 130, dx: 26 }, { hand: hR, len: 230, dx: -18 }, { hand: hR, len: 320, dx: 44 },
  ];
  return (
    <AbsoluteFill>
      {bg && <Img src={src(bg)} style={{ position: "absolute", inset: -40, width: W + 80, height: H + 80, objectFit: "cover", filter: `blur(${P.bgBlur}px)` }} />}
      {f >= at && (
        <AbsoluteFill style={{ transform: `translateY(${P.slideDist * sk}px)`, filter: sk > 0.02 ? `blur(${P.slideBlur * sk}px)` : undefined }}>
          <Full>
            <path d={`M${x - 150},${y} L${x + 150},${y} L${x + 180},${H + 40} L${x - 180},${H + 40}Z`} fill={P.pedestal} />
            <rect x={x - 170} y={y - 10} width={340} height={30} fill="#B24832" />
          </Full>
          <XRig cast={cast} {...o} seed="mario" pose={{ armR: "arm_out_side", armL: "arm_out_side", rotR: rR, rotL: rL }} />
          <Full>
            {beads.map((b, i) => {
              const ba = at + P.beadAt + i * P.beadStagger, bs = kf(f, ba, [0, P.beadPop * 0.6, P.beadPop], [0, 1.15, 1], Easing.out(Easing.quad));
              const a = (sw * (i % 2 ? 1 : -1) * 0.8) * D2R, ex = b.hand[0] + Math.sin(a) * b.len + b.dx, ey = b.hand[1] + Math.cos(a) * b.len;
              return (
                <g key={i}>
                  <line x1={b.hand[0]} y1={b.hand[1]} x2={ex} y2={ey} stroke="#5a2a1a" strokeWidth={2.5} />
                  {f >= ba && <g transform={`translate(${ex},${ey}) scale(${bs})`}><circle r={P.beadR} fill={P.bead} /><circle r={P.beadR} fill="none" stroke="#fff" strokeWidth={3} opacity={0.6} /><text y={P.beadR * 0.32} textAnchor="middle" fontFamily="NeoHv" fontSize={P.beadR * 0.8} fill="#fff">{bead}</text></g>}
                </g>
              );
            })}
          </Full>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};

// ══ 21. 먹덩이 얼굴 의인화 [ref4-samsung 0:42:22 우진조선] — 검은 불규칙 원 ≈420px + 분홍 졸린 선 얼굴, 0→1.35(f2)→1.0(f8) + 호흡 ══
export const BlobHeadParams = z.object({
  peak: num(1.35, 1, 2, 0.05, "팝 최고 크기(배)", "motion"),
  peakF: num(2, 1, 20, 1, "최고점 프레임", "timing", "f"),
  settleF: num(8, 2, 40, 1, "안착 프레임", "timing", "f"),
  rise: num(160, 0, 600, 10, "아래에서 올라오는 거리", "motion", "px"),
  breath: num(0.025, 0, 0.1, 0.005, "호흡 크기", "motion"),
  breathPeriod: num(40, 8, 120, 1, "호흡 반주기", "timing", "f"),
  size: num(420, 150, 800, 10, "머리 지름", "size", "px"),
  gray: flag(true, "배경 흑백 처리", "look"),
});
export type BlobHeadP = z.infer<typeof BlobHeadParams>;
export const BlobHead: React.FC<{ at: number; x: number; y: number; text?: string; bg?: string; cast?: CastId; p?: Partial<BlobHeadP> }> = ({ at, x, y, text = "우진조선", bg, cast = "c2_boss", p }) => {
  const P = def(BlobHeadParams, p);
  const f = useCurrentFrame();
  const g = f - at;
  const pop = kf(g, 0, [0, P.peakF, Math.max(P.peakF + 1, P.settleF)], [0, P.peak, 1], Easing.out(Easing.quad));
  const br = g > P.settleF ? 1 + P.breath * pp01(g - P.settleF, P.breathPeriod) : 1;
  const ry = lerp(f, at, at + P.settleF, P.rise, 0, EXPO_OUT);
  // 세모지 캐스트 흉상(cast) 위에 inkblob_head PNG(1035×1210, 머리 중심 (634,402)·폭 797)를 머리 대신 씌운다. 캔버스에서 머리 폭 480px = size
  const R = CAST[cast], s = P.size / 480, rh = s * (R.feet[1] - R.top), fw = (1035 * 480) / 797;
  return (
    <AbsoluteFill>
      {bg && <Img src={src(bg)} style={{ position: "absolute", inset: 0, width: W, height: H, objectFit: "cover", filter: P.gray ? "grayscale(1) contrast(1.05)" : undefined }} />}
      {g >= 0 && (
        <AbsoluteFill style={{ transformOrigin: `${x}px ${y}px`, transform: `translateY(${ry}px) scale(${pop}) scale(1,${br})` }}>
          <XRig cast={cast} x={x} y={y} h={rh} bust seed="blob" p={{ blinkEvery: 0, bobEvery: 0 }}
            over={<>
              <PropImg id="inkblob_head" x={R.feet[0]} y={250} w={fw} ax={634 / 1035} ay={402 / 1210} />
              <div style={{ position: "absolute", left: R.feet[0], top: R.torsoBottom - 170, transform: "translate(-50%,-50%)", fontFamily: "Jua", fontSize: 96, color: "#fff", whiteSpace: "nowrap", textShadow: "0 0 8px rgba(0,0,0,0.5)" }}>{text}</div>
            </>} />
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};

// ══ 22. 제자리 걷기 + 이정표 트랙 [ref4-samsung 0:03:40] — 걷기 16f(다리 교대+bob 4px), 초록 트랙, 발자국 누적, 깃발 이정표 ══
export const TreadmillWalkParams = z.object({
  cycle: num(16, 4, 60, 1, "걷기 사이클(다리 4포즈)", "timing", "f"),
  blinkEvery: num(80, 0, 300, 1, "눈 깜빡임 간격(0=없음)", "timing", "f"),
  bob: num(4, 0, 30, 1, "몸 들썩임", "motion", "px"),
  armSwing: num(5, 0, 25, 0.5, "팔 흔들림", "motion", "°"),
  speed: num(160, 0, 600, 5, "인물 전진 속도", "motion", "px/s"),
  scroll: num(0, 0, 600, 5, "트랙 스크롤 속도", "motion", "px/s"),
  trackH: num(170, 60, 400, 5, "트랙 높이", "size", "px"),
  footGap: num(64, 20, 200, 2, "발자국 간격", "size", "px"),
  track: col("#1E7A45", "트랙 색"),
});
export type TreadmillWalkP = z.infer<typeof TreadmillWalkParams>;
export const TreadmillWalk: React.FC<{ at: number; x0: number; h?: number; look?: PuppetLook; milestones?: { x: number; label: string; flag?: string }[]; p?: Partial<TreadmillWalkP> }> = ({ at, x0, h = 660, look, milestones = [], p }) => {
  const P = def(TreadmillWalkParams, p);
  const f = useCurrentFrame();
  const t = Math.max(0, f - at), ty = H - P.trackH;
  const cx = x0 + (P.speed * t) / 30, sc = (P.scroll * t) / 30;
  const prints: RN[] = [];
  for (let k = 0; ; k++) { const px = x0 - 40 + k * P.footGap - sc; if (px > cx - 60 || k > 200) break; prints.push(<g key={k} transform={`translate(${px},${ty + 40 + (k % 2) * 26}) rotate(90)`}><ellipse rx={9} ry={15} fill="#101010" /><ellipse cy={-22} rx={7} ry={7} fill="#101010" /></g>); }
  return (
    <AbsoluteFill style={{ background: "#C4CFC6" }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: ty, bottom: 0, background: P.track }} />
      <Full>
        {prints}
        {milestones.map((m, i) => (
          <g key={i} transform={`translate(${m.x - sc},${ty})`}>
            <line x1={0} y1={0} x2={0} y2={-110} stroke="#555" strokeWidth={5} />
            <path d="M0,-110 L70,-92 L0,-70Z" fill={m.flag ?? "#D8322E"} />
          </g>
        ))}
      </Full>
      {milestones.map((m, i) => (
        <div key={i} style={{ position: "absolute", left: m.x - sc - 20, top: ty + 40, transform: "translateX(-100%)", background: "rgba(0,60,30,0.55)", color: "#fff", fontFamily: "NeoHv", fontSize: 34, padding: "6px 16px", borderRadius: 8, whiteSpace: "pre", lineHeight: 1.2 }}>{m.label}</div>
      ))}
      {/* 세모지 그림체 리그(부위별 PNG): 다리 포즈 교대 + 들썩임 + 팔 흔들림 */}
      <SemojiWalker x={cx} y={ty + 30} h={h} at={at} p={{ cycle: P.cycle, bob: P.bob, armSwing: P.armSwing, blinkEvery: P.blinkEvery }} />
    </AbsoluteFill>
  );
};

// ══ 23. 불꽃 스프라이트 루프 [ref1 2:06 웍 · 5:32 VS · 3:09 불꽃 눈] — 3~4f 간격 스프라이트 교체 + 불씨 ══
export const FlameSpriteParams = z.object({
  swapEvery: num(3, 1, 12, 1, "스프라이트 교체 간격", "timing", "f"),
  tongues: num(7, 1, 20, 1, "불꽃 혀 개수", "size"),
  heightVar: num(0.35, 0, 0.8, 0.05, "높이 편차", "motion"),
  embers: num(10, 0, 40, 1, "불씨 개수", "size"),
  emberRise: num(9, 0, 40, 1, "불씨 상승 속도", "motion", "px/f"),
  outer: col("#F2541B", "바깥 불꽃 색"),
  mid: col("#FF9A1F", "중간 불꽃 색"),
  inner: col("#FFE14D", "속 불꽃 색"),
});
export type FlameSpriteP = z.infer<typeof FlameSpriteParams>;
const tonguePath = (bx: number, wd: number, hg: number, lean: number) =>
  `M${bx - wd / 2},0 C${bx - wd / 2},${-hg * 0.45} ${bx - wd * 0.15 + lean * 0.5},${-hg * 0.62} ${bx + lean},${-hg} C${bx + wd * 0.3 + lean * 0.3},${-hg * 0.55} ${bx + wd / 2},${-hg * 0.4} ${bx + wd / 2},0 Q${bx},${wd * 0.25} ${bx - wd / 2},0Z`;
/** (x,y)=불꽃 밑변 중앙, w×h 영역에 스프라이트 불꽃 */
export const FlameSprite: React.FC<{ at?: number; x: number; y: number; w: number; h: number; seed?: string; p?: Partial<FlameSpriteP> }> = ({ at = 0, x, y, w, h, seed = "fl", p }) => {
  const P = def(FlameSpriteParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const sp = Math.floor((f - at) / P.swapEvery), n = Math.max(1, Math.round(P.tongues));
  const layer = (c: string, sc: number, key: string) => (
    <g key={key}>
      {Array.from({ length: n }, (_, i) => {
        const r = (k: string) => random(`${seed}${key}${i}${k}${sp}`);
        const bx = (-0.5 + (i + 0.5) / n) * w * 0.85 + (r("x") - 0.5) * w * 0.06;
        const env = 1 - Math.pow(Math.abs(bx) / (w * 0.5), 2) * 0.6;
        const hg = h * sc * env * (1 - P.heightVar + P.heightVar * r("h")), wd = (w / n) * 1.7 * sc;
        return <path key={i} d={tonguePath(bx, wd, hg, (r("l") - 0.5) * wd * 0.8)} fill={c} />;
      })}
    </g>
  );
  return (
    <svg width={W} height={H} style={{ position: "absolute", left: 0, top: 0, overflow: "visible", pointerEvents: "none" }}>
      <g transform={`translate(${x},${y})`}>
        {layer(P.outer, 1, "o")}{layer(P.mid, 0.72, "m")}{layer(P.inner, 0.42, "i")}
        {Array.from({ length: Math.round(P.embers) }, (_, i) => {
          const life = 24, g = (f - at + i * 7) % life, ex = (random(`${seed}e${i}`) - 0.5) * w * 1.1 + Math.sin((f + i * 5) / 6) * 8;
          return <circle key={`e${i}`} cx={ex} cy={-h * 0.4 - g * P.emberRise} r={3 + 3 * random(`${seed}er${i}`)} fill={i % 2 ? P.mid : P.inner} opacity={1 - g / life} />;
        })}
      </g>
    </svg>
  );
};

// ══ 24. 바람선 스크리블 [ref1 3:09 겨울 씬] — 흰 스크리블 3개가 약 1초 동안 순차로 닦이듯 지나감 ══
export const WindLinesParams = z.object({
  count: num(3, 1, 10, 1, "바람선 개수", "size"),
  stagger: num(10, 0, 40, 1, "순차 간격", "timing", "f"),
  drawLen: num(8, 1, 30, 1, "그려지는 길이", "timing", "f"),
  life: num(18, 4, 60, 1, "한 줄 수명", "timing", "f"),
  travel: num(260, 0, 900, 10, "흘러가는 거리", "motion", "px"),
  len: num(240, 60, 700, 10, "스크리블 길이", "size", "px"),
  stroke: num(5, 1, 20, 0.5, "선 두께", "size", "px"),
  color: col("#FFFFFF", "선 색"),
});
export type WindLinesP = z.infer<typeof WindLinesParams>;
export const WindLines: React.FC<{ at: number; pts?: Pt[]; seed?: string; p?: Partial<WindLinesP> }> = ({ at, pts = [[380, 480], [900, 560], [1380, 470]], seed = "wind", p }) => {
  const P = def(WindLinesParams, p);
  const f = useCurrentFrame();
  const n = Math.round(P.count);
  return (
    <Full>
      {Array.from({ length: n }, (_, i) => {
        const a = at + i * P.stagger, g = f - a;
        if (g < 0 || g > P.life) return null;
        const [x, y] = pts[i % pts.length], L = P.len, segs = 22;
        // 촘촘한 사선 해칭이 오른쪽 위로 번지는 스크리블(2겹)
        const d = [0, 1].map((layer) => Array.from({ length: segs + 1 }, (_, k) => `${k ? "L" : "M"}${(k / segs) * L + (k % 2 ? 18 : -18) + (random(`${seed}${i}x${k}${layer}`) - 0.5) * 12},${(k % 2 ? -1 : 1) * (16 + 12 * random(`${seed}${i}y${k}${layer}`)) - (k / segs) * 50 + layer * 16}`).join(" ")).join(" ");
        const draw = lerp(f, a, a + P.drawLen, 0, 1, Easing.out(Easing.quad)), erase = lerp(f, a + P.drawLen, a + P.life, 0, 1, Easing.in(Easing.quad));
        const mv = P.travel * (g / P.life);
        return <path key={i} d={d} transform={`translate(${x + mv},${y})`} pathLength={1} strokeDasharray={`${Math.max(0.001, draw - erase)} 2`} strokeDashoffset={-erase} stroke={P.color} strokeWidth={P.stroke} fill="none" strokeLinecap="round" strokeLinejoin="round" />;
      })}
    </Full>
  );
};

// ══ 25. 소스 붓기 [ref1 4:18] — 뚜껑이 튀어 나가고 병이 기울며(6f) 소스 줄기 path trim(10f) ══
export const SaucePourParams = z.object({
  lidLen: num(10, 1, 40, 1, "뚜껑 날아가는 길이", "timing", "f"),
  tiltDelay: num(14, 0, 90, 1, "기울임 시작(뚜껑 후)", "timing", "f"),
  tiltLen: num(6, 1, 30, 1, "기울임 길이", "timing", "f"),
  tilt: num(65, -120, 120, 1, "기울기(시계방향 +)", "motion", "°"),
  streamLen: num(10, 1, 40, 1, "소스 줄기 늘어나는 길이", "timing", "f"),
  streamW: num(46, 6, 120, 1, "소스 줄기 두께", "size", "px"),
  jar: col("#C9161E", "병/소스 색"),
});
export type SaucePourP = z.infer<typeof SaucePourParams>;
export const SaucePour: React.FC<{ at: number; x: number; y: number; label?: string; p?: Partial<SaucePourP> }> = ({ at, x, y, label = "두반장", p }) => {
  const P = def(SaucePourParams, p);
  const f = useCurrentFrame();
  const lk = lerp(f, at, at + P.lidLen, 0, 1, Easing.out(Easing.quad));
  const ta = at + P.tiltDelay, tk = lerp(f, ta, ta + P.tiltLen, 0, 1, Easing.inOut(Easing.quad));
  const sk = lerp(f, ta + P.tiltLen * 0.6, ta + P.tiltLen * 0.6 + P.streamLen, 0, 1, Easing.out(Easing.quad));
  const ang = P.tilt * tk, wob = f > ta + P.tiltLen ? Math.sin((f - ta) / 4) * 1.5 : 0;
  // sauce_jar PNG(506×1344, 폭 260): 뚜껑 = 위 150px(클립해서 따로 날림), 병 입구 = 중심에서 위로 268px. 손 = hand_press_nozzle(반전)으로 병 어깨를 쥔 근사
  const JW = 260, js = JW / 506, JH = 1344 * js, CAP = 150 * js, MOUTH = 268;
  const a = (ang + wob) * D2R, mx = x + Math.sin(a) * MOUTH + 20 * tk, my = y - Math.cos(a) * MOUTH + 60 * tk;
  const jar = (clip: string, extra?: React.CSSProperties) => <Img src={prop("sauce_jar")} style={{ position: "absolute", left: 0, top: 0, width: JW, height: JH, clipPath: clip, ...extra }} />;
  return (
    <AbsoluteFill>
      <Full>{sk > 0 && <path d={`M${mx},${my} C${mx + 40},${my + 40} ${mx + 60},${my + 200} ${mx + 50},${H + 60}`} pathLength={1} strokeDasharray={`${sk} 2`} stroke={P.jar} strokeWidth={P.streamW} strokeLinecap="round" fill="none" />}</Full>
      <div style={{ position: "absolute", left: x + 20 * tk - JW / 2, top: y + 60 * tk - JH / 2, width: JW, height: JH, transformOrigin: "50% 50%", transform: `rotate(${ang + wob}deg)` }}>
        {jar(`inset(${CAP}px 0 0 0)`)}
        <div style={{ position: "absolute", left: 253 * js, top: 790 * js, transform: "translate(-50%,-50%)", fontFamily: "NeoHv", fontSize: 40, color: "#222", whiteSpace: "nowrap" }}>{label}</div>
        <PropImg id="hand_press_nozzle" x={JW * 0.18} y={JH * 0.3} w={330} ax={0.62} ay={0.62} flipX rot={-15} />
      </div>
      {f < at + P.lidLen + 2 && (
        <div style={{ position: "absolute", left: x - JW / 2 + 320 * lk, top: y - JH / 2 - 300 * lk + 260 * lk * lk, width: JW, height: JH, transformOrigin: `50% ${CAP / 2}px`, transform: `rotate(${160 * lk}deg)`, opacity: 1 - lerp(f, at + P.lidLen - 3, at + P.lidLen + 2, 0, 1) }}>{jar(`inset(0 0 ${JH - CAP}px 0)`)}</div>
      )}
    </AbsoluteFill>
  );
};

// ══ 26. 꽃 파티클 팝 [ref1 8:16] — 머리 위 핑크 꽃이 12f 팝했다가 사라짐 ══
export const FlowerParticlesParams = z.object({
  life: num(12, 4, 60, 1, "팝-페이드 길이", "timing", "f"),
  count: num(4, 1, 12, 1, "머리당 꽃 수", "size"),
  size: num(34, 10, 100, 1, "꽃 크기", "size", "px"),
  spread: num(80, 0, 300, 2, "좌우 퍼짐", "size", "px"),
  rise: num(18, 0, 120, 1, "떠오름", "motion", "px"),
  stagger: num(1, 0, 10, 1, "꽃 사이 지연", "timing", "f"),
  color: col("#F7A0C4", "꽃잎 색"),
});
export type FlowerParticlesP = z.infer<typeof FlowerParticlesParams>;
export const FlowerParticles: React.FC<{ at: number; heads: Pt[]; seed?: string; p?: Partial<FlowerParticlesP> }> = ({ at, heads, seed = "flw", p }) => {
  const P = def(FlowerParticlesParams, p);
  const f = useCurrentFrame();
  const n = Math.round(P.count);
  return (
    <Full>
      {heads.map(([hx, hy], j) => Array.from({ length: n }, (_, i) => {
        const a = at + i * P.stagger + j, g = f - a;
        if (g < 0 || g > P.life) return null;
        const u = n > 1 ? i / (n - 1) - 0.5 : 0, px = hx + u * P.spread * 2 + (random(`${seed}${j}${i}`) - 0.5) * 20, py = hy - 30 - Math.cos(u * Math.PI) * 40 - P.rise * (g / P.life);
        const s = kf(g, 0, [0, P.life * 0.3, P.life], [0, 1.15, 0.85], Easing.out(Easing.quad)), op = kf(g, 0, [0, P.life * 0.6, P.life], [1, 1, 0]);
        const r = P.size / 2;
        return (
          <g key={`${j}-${i}`} transform={`translate(${px},${py}) scale(${s}) rotate(${g * 6 + i * 30})`} opacity={op}>
            {Array.from({ length: 5 }, (_, k) => <circle key={k} cx={Math.cos((k / 5) * TAU) * r * 0.55} cy={Math.sin((k / 5) * TAU) * r * 0.55} r={r * 0.48} fill={P.color} />)}
            <circle r={r * 0.34} fill="#FFE27A" />
          </g>
        );
      }))}
    </Full>
  );
};

// ══ 27. 홀로그램 테크 오라 [ref2 154:21] — 손 위 물체가 회전 팝, 청백 에너지 링이 돌며 반짝임 ══
export const TechAuraParams = z.object({
  popLen: num(8, 1, 30, 1, "물체 등장 길이", "timing", "f"),
  spinFrom: num(-40, -360, 360, 5, "등장 회전", "motion", "°"),
  rings: num(3, 1, 6, 1, "링 개수", "size"),
  ringR: num(250, 60, 600, 5, "링 반지름", "size", "px"),
  rotSpeed: num(3, 0, 20, 0.5, "링 회전 속도", "motion", "°/f"),
  floatAmp: num(8, 0, 40, 1, "부유 높이", "motion", "px"),
  floatPeriod: num(40, 8, 120, 1, "부유 반주기", "timing", "f"),
  color: col("#6FE3FF", "오라 색"),
});
export type TechAuraP = z.infer<typeof TechAuraParams>;
export const TechAura: React.FC<{ at: number; x: number; y: number; object: RN; p?: Partial<TechAuraP> }> = ({ at, x, y, object, p }) => {
  const P = def(TechAuraParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const g = f - at, k = lerp(f, at, at + P.popLen, 0, 1, Easing.out(Easing.back(1.6)));
  const fl = P.floatAmp * (pp01(g, P.floatPeriod) * 2 - 1), R = P.ringR, c = P.color;
  return (
    <AbsoluteFill>
      <Glow x={x} y={y} r={R * 1.3 * Math.min(1, k)} color="rgba(111,227,255,0.35)" blend="screen" />
      <Full>
        {Array.from({ length: Math.round(P.rings) }, (_, i) => {
          const r = R * (0.72 + i * 0.16) * Math.min(1, k), dir = i % 2 ? -1 : 1;
          return (
            <g key={i} transform={`translate(${x},${y}) rotate(${dir * g * P.rotSpeed * (1 + i * 0.3) + i * 40})`} opacity={0.9 - i * 0.15}>
              <circle r={r} fill="none" stroke={c} strokeWidth={10 - i * 2} strokeDasharray={`${r * 1.2} ${r * 0.35} ${r * 0.4} ${r * 0.3}`} style={{ filter: `drop-shadow(0 0 12px ${c})` }} />
              <circle r={r * 0.94} fill="none" stroke="#E8FBFF" strokeWidth={2} opacity={0.7} />
            </g>
          );
        })}
        {Array.from({ length: 10 }, (_, i) => {
          const a = (i / 10) * TAU + g * 0.05, r = R * (0.8 + 0.3 * random(`ta${i}`)), tw = Math.abs(Math.sin((g + i * 7) / 6));
          return <path key={`s${i}`} transform={`translate(${x + Math.cos(a) * r},${y + Math.sin(a) * r * 0.9}) scale(${0.12 * tw * Math.min(1, k)})`} d="M0,-50 C6,-8 8,-6 50,0 C8,6 6,8 0,50 C-6,8 -8,6 -50,0 C-8,-6 -6,-8 0,-50Z" fill="#fff" />;
        })}
      </Full>
      <AbsoluteFill style={{ transformOrigin: `${x}px ${y}px`, transform: `translateY(${fl}px) scale(${k}) rotate(${P.spinFrom * (1 - Math.min(1, k))}deg)` }}>{object}</AbsoluteFill>
    </AbsoluteFill>
  );
};
/** 세모지 노트북 PNG(laptop 1165×1074, 화면 중앙 (486,346)) — 화면 글자는 코드 */
export const LaptopImg: React.FC<{ x: number; y: number; w: number; text?: string }> = ({ x, y, w, text = "?" }) => (
  <PropImg id="laptop" x={x} y={y} w={w}>
    <div style={{ position: "absolute", left: (486 / 1165) * w, top: (346 / 1074) * propH("laptop", w), transform: "translate(-50%,-50%) skewY(-8deg)", fontFamily: "Jalnan", fontSize: w * 0.3, color: "#fff" }}>{text}</div>
  </PropImg>
);
export const LaptopSvg: React.FC<{ x: number; y: number; w: number; screen?: string }> = ({ x, y, w, screen = "#27D3C3" }) => (
  <svg width={w} height={w} viewBox="-200 -200 400 400" style={{ position: "absolute", left: x - w / 2, top: y - w / 2, overflow: "visible" }}>
    <g transform="skewY(-12)">
      <rect x={-150} y={-150} width={300} height={200} rx={14} fill="#8C8FC9" /><rect x={-134} y={-136} width={268} height={172} rx={6} fill={screen} />
      <text x={0} y={-10} textAnchor="middle" fontFamily="Jalnan" fontSize={120} fill="#fff">?</text>
      <path d="M-150,50 L150,50 L200,130 L-100,130Z" fill="#A9ACE0" />
      {Array.from({ length: 4 }, (_, r) => <rect key={r} x={-110 + r * 10} y={62 + r * 14} width={250} height={8} rx={3} fill="#7F82B8" />)}
    </g>
  </svg>
);

// ══ 28. 전경 박수 손 루프 [ref4-apple 1:24:32] — 화면 아래 40% 살구색 손 3~4쌍, 8~10f 핑퐁, 쌍마다 위상차 ══
export const ClappingHandsParams = z.object({
  pairs: num(4, 1, 8, 1, "손 쌍 개수", "size"),
  period: num(5, 2, 20, 1, "박수 반주기", "timing", "f"),
  phaseStep: num(2, 0, 10, 0.5, "쌍 사이 위상차", "timing", "f"),
  size: num(380, 120, 700, 5, "손 크기", "size", "px"),
  open: num(24, 0, 60, 1, "벌어지는 각도", "motion", "°"),
  opacity: num(0.97, 0.3, 1, 0.01, "불투명도", "look"),
});
export type ClappingHandsP = z.infer<typeof ClappingHandsParams>;
/** 옆에서 본 손바닥(손가락 모음) — 손목(0,0), 손끝 (0,-250) */
const PalmSvg: React.FC<{ c: string }> = ({ c }) => (
  <g>
    <path d="M-52,60 L-52,-60 C-56,-150 -40,-230 -6,-252 C22,-262 44,-236 48,-190 L56,-60 L56,60Z" fill={c} />
    <path d="M-50,-40 C-110,-70 -128,-120 -110,-140 C-92,-156 -62,-120 -44,-100Z" fill={c} />
    {[-150, -110, -70].map((y, i) => <path key={i} d={`M-40,${y} Q-4,${y - 10} 40,${y}`} stroke="rgba(150,70,60,0.22)" strokeWidth={5} fill="none" strokeLinecap="round" />)}
    <rect x={-60} y={40} width={124} height={80} rx={10} fill="#E9E4DA" />
  </g>
);
/** 세모지 박수 손 PNG(clapping_palm 724×1111): 손목 (221,751) → 손끝 (590,32) 가 위를 향하도록 -27° 회전. SVG 좌표(손목 0,0 · 손끝 0,-250) */
const PalmImg: React.FC = () => {
  const k = 250 / 810;   // 손목→손끝 ≈ 810px 를 250 으로
  return <g transform="rotate(-27)"><image href={prop("clapping_palm")} x={-221 * k} y={-751 * k} width={724 * k} height={1111 * k} /></g>;
};
export const ClappingHands: React.FC<{ at?: number; y?: number; p?: Partial<ClappingHandsP> }> = ({ at = 0, y = H + 40, p }) => {
  const P = def(ClappingHandsParams, p);
  const f = useCurrentFrame();
  const n = Math.round(P.pairs), s = P.size / 400;
  return (
    <Full style={{ opacity: P.opacity }}>
      {Array.from({ length: n }, (_, i) => {
        const cx = ((i + 0.5) / n) * W + (i % 2 ? 40 : -40), k = f < at ? 0 : pp01(f - at, P.period, i * P.phaseStep), op = P.open * k, lean = (cx - W / 2) * 0.012;
        const yy = y - (i % 2 ? 40 : 0);
        return (
          <g key={i} transform={`translate(${cx},${yy}) scale(${s}) rotate(${lean})`}>
            <g transform={`translate(-120,0) rotate(${26 - op}) scale(-1,1)`}><PalmImg /></g>
            <g transform={`translate(120,0) rotate(${-26 + op})`}><PalmImg /></g>
          </g>
        );
      })}
    </Full>
  );
};

// ══ 29. 유리 깨짐 크랙 [ref4-apple 1:36:10] — 검정 크랙 1f 하드 등장(≈360px) → +15f 작은 2차 크랙(≈150px) ══
export const GlassCrackParams = z.object({
  size: num(360, 80, 900, 10, "1차 크랙 크기", "size", "px"),
  size2: num(150, 0, 600, 5, "2차 크랙 크기(0=없음)", "size", "px"),
  delay2: num(15, 0, 90, 1, "2차 크랙 지연", "timing", "f"),
  cracks: num(12, 4, 30, 1, "균열 가닥 수", "size"),
  thick: num(7, 1, 20, 0.5, "균열 두께", "size", "px"),
  color: col("#111111", "균열 색"),
});
export type GlassCrackP = z.infer<typeof GlassCrackParams>;
const CrackG: React.FC<{ x: number; y: number; size: number; n: number; thick: number; c: string; seed: string }> = ({ x, y, size, n, thick, c, seed }) => {
  const R = size / 2, rnd = (k: string) => random(`${seed}${k}`);
  const arms = Array.from({ length: n }, (_, i) => {
    const a0 = (i / n) * TAU + (rnd(`a${i}`) - 0.5) * 0.5, len = R * (0.55 + 0.6 * rnd(`l${i}`));
    const pts: Pt[] = [[0, 0]];
    for (let k = 1; k <= 5; k++) { const t = k / 5, a = a0 + (rnd(`j${i}${k}`) - 0.5) * 0.45; pts.push([Math.cos(a) * len * t, Math.sin(a) * len * t]); }
    return pts;
  });
  const hole = Array.from({ length: 10 }, (_, i) => { const a = (i / 10) * TAU, r = R * (0.1 + 0.08 * rnd(`h${i}`)); return `${i ? "L" : "M"}${Math.cos(a) * r},${Math.sin(a) * r}`; }).join(" ") + "Z";
  return (
    <g transform={`translate(${x},${y})`}>
      {arms.map((pts, i) => pts.slice(1).map((pt, k) => <line key={`${i}-${k}`} x1={pts[k][0]} y1={pts[k][1]} x2={pt[0]} y2={pt[1]} stroke={c} strokeWidth={Math.max(1, thick * (1 - k / 5))} strokeLinecap="round" />))}
      {[0.35, 0.62].map((t, ri) => arms.map((pts, i) => { if (rnd(`w${ri}${i}`) < 0.35) return null; const j = Math.round(t * 5), a = pts[j], b = arms[(i + 1) % n][j]; return <path key={`w${ri}${i}`} d={`M${a[0]},${a[1]} Q${(a[0] + b[0]) * 0.55},${(a[1] + b[1]) * 0.55} ${b[0]},${b[1]}`} stroke={c} strokeWidth={Math.max(1, thick * 0.4)} fill="none" />; }))}
      <path d={hole} fill={c} />
      {Array.from({ length: 6 }, (_, i) => { const a = rnd(`s${i}`) * TAU, r = R * 0.18 + R * 0.12 * rnd(`sr${i}`); return <path key={`s${i}`} d={`M${Math.cos(a) * r},${Math.sin(a) * r} l${12 * Math.cos(a + 1)},${12 * Math.sin(a + 1)} l${10 * Math.cos(a - 1)},${10 * Math.sin(a - 1)}Z`} fill={c} />; })}
    </g>
  );
};
export const GlassCrack: React.FC<{ at: number; x: number; y: number; x2?: number; y2?: number; seed?: string; p?: Partial<GlassCrackP> }> = ({ at, x, y, x2, y2, seed = "gc", p }) => {
  const P = def(GlassCrackParams, p);
  const f = useCurrentFrame();
  const n = Math.round(P.cracks);
  return (
    <Full>
      {f >= at && <CrackG x={x} y={y} size={P.size} n={n} thick={P.thick} c={P.color} seed={seed} />}
      {P.size2 > 0 && f >= at + P.delay2 && <CrackG x={x2 ?? x + P.size * 0.7} y={y2 ?? y + P.size * 0.5} size={P.size2} n={Math.max(5, Math.round(n * 0.7))} thick={P.thick * 0.8} c={P.color} seed={`${seed}2`} />}
    </Full>
  );
};

// ══ 30. 깨달음 웜 블룸 [ref4-apple 1:27:49] — 주황-노랑 소프트 글로우(반경≈500) 6~8f 램프업 + 노출 +30% → 피크에서 하드컷 ══
export const IdeaWarmBloomParams = z.object({
  rampLen: num(8, 1, 40, 1, "램프업 길이", "timing", "f"),
  hold: num(3, 0, 30, 1, "피크 유지 후 컷", "timing", "f"),
  radius: num(500, 100, 1600, 10, "글로우 반경", "size", "px"),
  exposure: num(0.3, 0, 1.5, 0.05, "인물 노출 증가", "look"),
  whiteout: num(0.55, 0, 1, 0.05, "피크 화이트아웃", "look"),
  color: col("#FFB347", "글로우 색"),
});
export type IdeaWarmBloomP = z.infer<typeof IdeaWarmBloomParams>;
export const IdeaWarmBloom: React.FC<{ at: number; x: number; y: number; children: RN; next?: RN; p?: Partial<IdeaWarmBloomP> }> = ({ at, x, y, children, next, p }) => {
  const P = def(IdeaWarmBloomParams, p);
  const f = useCurrentFrame();
  const k = lerp(f, at, at + P.rampLen, 0, 1, Easing.in(Easing.quad)), cut = at + P.rampLen + P.hold;
  if (next !== undefined && f >= cut) return <>{next}</>;
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ filter: k > 0 ? `brightness(${1 + P.exposure * k}) saturate(${1 + 0.2 * k})` : undefined }}>{children}</AbsoluteFill>
      {k > 0 && <>
        <Glow x={x} y={y} r={P.radius * (0.6 + 0.8 * k)} color={P.color} op={0.85 * k} blend="screen" />
        <Glow x={x} y={y} r={P.radius * 0.5 * (0.6 + 0.8 * k)} color="#FFF3C8" op={0.9 * k} blend="screen" />
        <AbsoluteFill style={{ background: "#FFE9B8", opacity: P.whiteout * k * k, mixBlendMode: "screen" }} />
      </>}
    </AbsoluteFill>
  );
};

// ══ 31. 전기 소용돌이 등장 [ref4-samsung 0:47:22] (= 에너지 포탈 링 ref4-apple 2:01:31) ══════════
// f0 점 → f3 링 최대(1.1 오버슈트) → f5~10 수축 + 물체 페이드인 → f10~24 호 조각 12~16개로 분해·회전(90°)·알파 0
export const ElectricVortexParams = z.object({
  growLen: num(3, 1, 20, 1, "링 커지는 길이", "timing", "f"),
  over: num(1.1, 1, 1.6, 0.01, "오버슈트(배)", "motion"),
  shrinkEnd: num(10, 2, 40, 1, "수축 끝 프레임", "timing", "f"),
  breakEnd: num(24, 4, 80, 1, "분해 끝 프레임", "timing", "f"),
  frags: num(14, 4, 30, 1, "호 조각 수", "size"),
  fragRot: num(90, 0, 360, 5, "조각 회전", "motion", "°"),
  hold: flag(false, "분해 없이 링 유지(포탈 루프)", "motion"),
  core: col("#7FD8FF", "코어 색"),
  glow: col("#2E7BFF", "글로우 색"),
});
export type ElectricVortexP = z.infer<typeof ElectricVortexParams>;
export const ElectricVortexSpawn: React.FC<{ at: number; x: number; y: number; r?: number; object?: RN; seed?: string; p?: Partial<ElectricVortexP> }> = ({ at, x, y, r = 130, object, seed = "ev", p }) => {
  const P = def(ElectricVortexParams, p);
  const f = useCurrentFrame();
  const g = f - at;
  if (g < 0) return null;
  const sc = P.hold ? (g < P.growLen ? kf(g, 0, [0, P.growLen], [0, P.over], Easing.out(Easing.quad)) : 1 + (P.over - 1) * Math.exp(-(g - P.growLen) / 3))
    : kf(g, 0, [0, P.growLen, P.shrinkEnd], [0, P.over, 0.7], Easing.out(Easing.quad));
  const bk = P.hold ? 0 : lerp(g, P.shrinkEnd, P.breakEnd, 0, 1, Easing.out(Easing.quad));
  const objOp = lerp(g, Math.min(5, P.shrinkEnd - 1), P.shrinkEnd, 0, 1, Easing.linear);
  const R = r * sc, th = r * 0.36, jit = Math.floor(g / 2);
  const jag = (rr: number, k: string) => Array.from({ length: 40 }, (_, i) => { const a = (i / 40) * TAU, q = rr * (1 + 0.07 * (random(`${seed}${k}${i}${jit}`) - 0.5)); return `${i ? "L" : "M"}${Math.cos(a) * q},${Math.sin(a) * q}`; }).join(" ") + "Z";
  const n = Math.round(P.frags);
  return (
    <AbsoluteFill>
      {object && <AbsoluteFill style={{ opacity: objOp }}>{object}</AbsoluteFill>}
      <Full>
        <g transform={`translate(${x},${y})`} style={{ filter: `drop-shadow(0 0 10px ${P.glow}) drop-shadow(0 0 4px ${P.glow})` }}>
          {bk <= 0 ? (
            <g transform={P.hold ? `rotate(${g * 4})` : undefined}>
              <path d={jag(R, "o")} fill="none" stroke={P.core} strokeWidth={th * Math.min(1, sc)} strokeLinejoin="round" />
              <path d={jag(R * 1.01, "i")} fill="none" stroke="#E6FAFF" strokeWidth={th * 0.25 * Math.min(1, sc)} opacity={0.8} />
              {P.hold && Array.from({ length: 8 }, (_, i) => { const a = (i / 8) * TAU + random(`${seed}ha${i}${jit}`), rr = R + th * 0.7; return <path key={i} d={`M${Math.cos(a) * rr},${Math.sin(a) * rr} l${16 * Math.cos(a + 1.2)},${16 * Math.sin(a + 1.2)} l${14 * Math.cos(a - 0.4)},${14 * Math.sin(a - 0.4)}`} stroke="#E6FAFF" strokeWidth={3} fill="none" />; })}
            </g>
          ) : (
            Array.from({ length: n }, (_, i) => {
              const a0 = (i / n) * TAU + P.fragRot * D2R * bk * (i % 2 ? 1.2 : 0.8), span = (TAU / n) * (0.55 - 0.25 * bk), rr = R * (1 + (0.5 + 0.4 * random(`${seed}fr${i}`)) * bk);
              return <path key={i} d={`M${Math.cos(a0) * rr},${Math.sin(a0) * rr} A${rr},${rr} 0 0 1 ${Math.cos(a0 + span) * rr},${Math.sin(a0 + span) * rr}`} stroke={i % 3 ? P.core : "#E6FAFF"} strokeWidth={th * 0.5 * (1 - bk) + 2} strokeLinecap="round" fill="none" opacity={1 - bk} />;
            })
          )}
        </g>
      </Full>
    </AbsoluteFill>
  );
};

// ══ 32. 동심원 암흑 펄스 [ref4-cocacola 0:03:30] — #784646 중앙에서 소프트 원이 8~9f 간격 생성, 각 25f 확장 ══
export const ConcentricDarkPulseParams = z.object({
  every: num(8.5, 2, 40, 0.5, "원 생성 간격", "timing", "f"),
  life: num(25, 4, 90, 1, "원 확장 길이", "timing", "f"),
  maxR: num(1250, 300, 2400, 10, "최대 반지름", "size", "px"),
  alpha: num(0.32, 0.05, 1, 0.01, "원 진하기", "look"),
  edge: num(0.22, 0, 0.8, 0.01, "가장자리 부드러움", "look"),
  bg: col("#784646", "배경 색"),
  ring: col("#2A2424", "원 색"),
});
export type ConcentricDarkPulseP = z.infer<typeof ConcentricDarkPulseParams>;
export const ConcentricDarkPulse: React.FC<{ at: number; x?: number; y?: number; p?: Partial<ConcentricDarkPulseP> }> = ({ at, x = W / 2, y = H / 2, p }) => {
  const P = def(ConcentricDarkPulseParams, p);
  const f = useCurrentFrame();
  const g = f - at, circles: RN[] = [];
  if (g >= 0) {
    const last = Math.floor(g / P.every);
    for (let k = 0; k <= last; k++) {
      const t = (g - k * P.every) / P.life;
      if (t > 1) continue;
      const r = P.maxR * Easing.out(Easing.quad)(t);
      circles.push(<div key={k} style={{ position: "absolute", left: x - r, top: y - r, width: 2 * r, height: 2 * r, borderRadius: "50%", opacity: P.alpha * Math.min(1, (1 - t) / 0.3), background: `radial-gradient(circle, ${P.ring} 0%, ${P.ring} ${Math.round((1 - P.edge) * 100)}%, transparent 100%)` }} />);
    }
  }
  return <AbsoluteFill style={{ background: P.bg, overflow: "hidden" }}>{circles}</AbsoluteFill>;
};

// ══ 33. 홍수 수위 상승 + 줌아웃 [ref4-hyundai 0:47:26 · 0:47:32] — 2.2→1.0 6f 줌아웃 + 수면 상승(y≈540), 물결 루프, 머리 bob, 실루엣화 ══
export const FloodRiseParams = z.object({
  zoomLen: num(6, 1, 40, 1, "줌아웃 길이", "timing", "f"),
  zoomFrom: num(2.2, 1, 4, 0.05, "클로즈업 배율", "motion"),
  riseLen: num(10, 1, 60, 1, "수면 상승 길이", "timing", "f"),
  waterY: num(540, 200, 1000, 5, "수면 높이 y", "size", "px"),
  waveAmp: num(12, 0, 60, 1, "물결 높이", "motion", "px"),
  wavePeriod: num(40, 8, 160, 1, "물결 주기", "timing", "f"),
  bobAmp: num(6, 0, 30, 1, "머리 들썩임", "motion", "px"),
  silAt: num(0, 0, 200, 1, "실루엣화 시작(0=안 함)", "timing", "f"),
  silLen: num(10, 1, 60, 1, "실루엣 크로스페이드", "timing", "f"),
  water: col("#4A8EA3", "물 색"),
});
export type FloodRiseP = z.infer<typeof FloodRiseParams>;
export const FloodRise: React.FC<{ at: number; focus: Pt; bg?: RN; render: (bob: number, sil: number, zoomed: boolean) => RN; p?: Partial<FloodRiseP> }> = ({ at, focus, bg, render, p }) => {
  const P = def(FloodRiseParams, p);
  const f = useCurrentFrame();
  const zk = lerp(f, at, at + P.zoomLen, 0, 1, Easing.out(Easing.cubic)), s = P.zoomFrom + (1 - P.zoomFrom) * zk;
  const wy = lerp(f, at, at + P.riseLen, H + 80, P.waterY, Easing.out(Easing.cubic));
  const bob = f >= at ? P.bobAmp * Math.sin((f / (P.wavePeriod / 2)) * Math.PI) : 0;
  const sil = P.silAt > 0 ? lerp(f, at + P.silAt, at + P.silAt + P.silLen, 0, 1, Easing.linear) : 0;
  const wave = (y0: number, ph: number, amp: number) => {
    const pts = Array.from({ length: 25 }, (_, i) => { const x = (i / 24) * (W + 200) - 100; return `${x},${y0 + amp * Math.sin((x / 180) + ((f + ph) / P.wavePeriod) * TAU)}`; });
    return `M-100,${H + 100} L${pts.join(" L")} L${W + 100},${H + 100}Z`;
  };
  return (
    <AbsoluteFill style={{ transformOrigin: `${focus[0]}px ${focus[1]}px`, transform: `scale(${s})` }}>
      {bg}
      {render(bob, sil, f >= at)}
      <Full>
        <path d={wave(wy - 6, 10, P.waveAmp)} fill="#E8F4F6" opacity={0.85} />
        <path d={wave(wy, 0, P.waveAmp)} fill={P.water} />
        <path d={wave(wy + 60, 20, P.waveAmp * 0.6)} fill="rgba(255,255,255,0.08)" />
      </Full>
    </AbsoluteFill>
  );
};

// ══ 34. 떠오른 이미지 블러 물질화 [ref4-hyundai 1:04:38] — 머리 사이 허공, 블러 40→0 + 불투명 0→1 동시 18f(선형), 위치·크기 고정 ══
export const ThoughtMaterializeParams = z.object({
  len: num(18, 1, 60, 1, "물질화 길이", "timing", "f"),
  blur: num(40, 0, 120, 1, "시작 블러", "look", "px"),
  op0: num(0, 0, 1, 0.05, "시작 불투명도", "look"),
});
export type ThoughtMaterializeP = z.infer<typeof ThoughtMaterializeParams>;
export const ThoughtMaterialize: React.FC<{ at: number; children: RN; p?: Partial<ThoughtMaterializeP> }> = ({ at, children, p }) => {
  const P = def(ThoughtMaterializeParams, p);
  const f = useCurrentFrame();
  if (f < at) return null;
  const k = lerp(f, at, at + P.len, 0, 1, Easing.linear);
  return <AbsoluteFill style={{ opacity: P.op0 + (1 - P.op0) * k, filter: k < 1 ? `blur(${P.blur * (1 - k)}px)` : undefined }}>{children}</AbsoluteFill>;
};
export const BanknoteSvg: React.FC<{ x: number; y: number; w: number }> = ({ x, y, w }) => (
  <svg width={w} height={w * 0.48} viewBox="0 0 420 200" style={{ position: "absolute", left: x - w / 2, top: y - w * 0.24 }}>
    <rect width={420} height={200} rx={10} fill="#DCE3D4" /><rect x={10} y={10} width={400} height={180} rx={6} fill="none" stroke="#8B9A86" strokeWidth={4} />
    <circle cx={120} cy={100} r={58} fill="#B7C2B0" /><path d="M80,120 Q120,60 160,120Z" fill="#7F8E7A" />
    <text x={300} y={80} textAnchor="middle" fontFamily="MyeongjoEB" fontSize={34} fill="#5E6D5A">오백원</text>
    <text x={300} y={140} textAnchor="middle" fontFamily="NeoHv" fontSize={44} fill="#6E7D69">500</text>
    <text x={40} y={50} fontFamily="NeoHv" fontSize={22} fill="#6E7D69">500</text>
  </svg>
);
/** 보라 소용돌이 배경 */
export const SwirlBg: React.FC<{ c1?: string; c2?: string; cx?: number; cy?: number; speed?: number }> = ({ c1 = "#6F5FD8", c2 = "#9A8CF0", cx = W * 0.62, cy = H * 0.4, speed = 0.4 }) => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: c1 }}>
      <Full>
        <g transform={`translate(${cx},${cy}) rotate(${f * speed})`}>
          {Array.from({ length: 10 }, (_, i) => {
            const pts = Array.from({ length: 60 }, (_, k) => { const t = k / 59, a = t * TAU * 1.6 + (i / 10) * TAU, r = 60 + t * 1600; return `${Math.cos(a) * r},${Math.sin(a) * r}`; });
            return <polyline key={i} points={pts.join(" ")} fill="none" stroke={c2} strokeWidth={70} strokeLinecap="round" />;
          })}
        </g>
      </Full>
    </AbsoluteFill>
  );
};

// ══ 35. 컬러 드레인(점진 흑백화) [ref4-hyundai 1:28:06] — 한 샷 안에서 채도 100%→10% 25f 선형 + 회청 톤다운 ══
export const ColorDrainParams = z.object({
  len: num(25, 1, 120, 1, "드레인 길이", "timing", "f"),
  to: num(0.1, 0, 1, 0.05, "최종 채도", "look"),
  tint: num(0.22, 0, 1, 0.02, "회청 톤 오버레이", "look"),
  dim: num(0.08, 0, 0.6, 0.01, "밝기 감소", "look"),
  tintColor: col("#8A9CA3", "톤 색"),
});
export type ColorDrainP = z.infer<typeof ColorDrainParams>;
export const ColorDrain: React.FC<{ at: number; children: RN; p?: Partial<ColorDrainP> }> = ({ at, children, p }) => {
  const P = def(ColorDrainParams, p);
  const f = useCurrentFrame();
  const k = lerp(f, at, at + P.len, 0, 1, Easing.linear);
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ filter: k > 0 ? `saturate(${1 - (1 - P.to) * k}) brightness(${1 - P.dim * k})` : undefined }}>{children}</AbsoluteFill>
      {k > 0 && <AbsoluteFill style={{ background: P.tintColor, opacity: P.tint * k, mixBlendMode: "multiply" }} />}
    </AbsoluteFill>
  );
};

// ══ 36. 족쇄 쇳덩이 슬램 [ref4-hyundai 1:28:42 '자금 압박'] — 돈자루 좌측 15f 슬라이드 + 배경 블러 0→8(6f), 쇳덩이 우측 휩 인 3f → 진자 오버슈트 2회 8f ══
export const BurdenBallChainParams = z.object({
  sackLen: num(15, 1, 60, 1, "돈자루 슬라이드 길이", "timing", "f"),
  sackX: num(350, 0, 960, 10, "돈자루 최종 x", "size", "px"),
  defocus: num(8, 0, 40, 1, "배경 디포커스", "look", "px"),
  defocusLen: num(6, 1, 30, 1, "디포커스 길이", "timing", "f"),
  ballDelay: num(5, 0, 60, 1, "쇳덩이 지연", "timing", "f"),
  whipLen: num(3, 1, 20, 1, "쇳덩이 휩 인", "timing", "f"),
  swing: num(12, 0, 40, 1, "진자 오버슈트 각도", "motion", "°"),
  swingLen: num(8, 2, 40, 1, "진자 감쇠 길이", "timing", "f"),
  ballR: num(150, 50, 300, 5, "쇳덩이 반지름", "size", "px"),
});
export type BurdenBallChainP = z.infer<typeof BurdenBallChainParams>;
export const MoneySacksSvg: React.FC = () => (
  <g>
    {[[-150, 30, 1], [120, 40, 0.95], [-10, -20, 1.1]].map(([x, y, s], i) => (
      <g key={i} transform={`translate(${x},${y}) scale(${s})`}>
        <rect x={-120} y={-40} width={240} height={60} rx={6} fill="#6FBF55" /><rect x={-110} y={-32} width={220} height={44} rx={4} fill="#9BD67F" />
        <path d="M-150,160 C-190,60 -120,-20 -40,-40 L40,-40 C120,-20 190,60 150,160 C100,200 -100,200 -150,160Z" fill="#F4EBCF" />
        <path d="M-60,-40 L60,-40 L40,-80 C20,-100 -20,-100 -40,-80Z" fill="#EFE3C0" />
        <path d="M-70,-44 C-30,-30 30,-30 70,-44" stroke="#D9A72C" strokeWidth={12} fill="none" />
      </g>
    ))}
  </g>
);
export const BurdenBallChain: React.FC<{ at: number; bg: RN; text?: string; ball?: Pt; p?: Partial<BurdenBallChainP> }> = ({ at, bg, text = "자금\n압박", ball = [1480, 560], p }) => {
  const P = def(BurdenBallChainParams, p);
  const f = useCurrentFrame();
  const sk = lerp(f, at, at + P.sackLen, 0, 1, Easing.out(Easing.cubic));
  const dk = lerp(f, at, at + P.defocusLen, 0, 1, Easing.out(Easing.quad));
  const ba = at + P.ballDelay, wk = lerp(f, ba, ba + P.whipLen, 0, 1, Easing.out(Easing.quad)), gs = f - ba - P.whipLen;
  const sw = gs >= 0 ? P.swing * Math.exp(-gs / (P.swingLen / 3)) * Math.cos((gs / (P.swingLen / 2)) * TAU * 0.5) : 0;
  const R = P.ballR, bx = ball[0] + 700 * (1 - wk), sackCx = -400 + (P.sackX + 400) * sk, sackY = 820;
  const pivot: Pt = [bx - R * 0.3, ball[1] - R - 220];
  const ang = (f >= ba ? sw : 0) * D2R, bcx = pivot[0] + (bx - pivot[0]) * Math.cos(ang) - (ball[1] - pivot[1]) * Math.sin(ang), bcy = pivot[1] + (bx - pivot[0]) * Math.sin(ang) + (ball[1] - pivot[1]) * Math.cos(ang);
  // iron_ball PNG(882×1123): 공 몸통 중심 (440,680)·반지름≈440, 고리 중심 (440,150). chain_link PNG 로 사슬, money_sack PNG 3개
  const bs = R / 440, ringP: Pt = rotAbout([bcx, bcy - 530 * bs], [bcx, bcy], sw), sackP: Pt = [sackCx + 150, sackY - 40];
  const links = 16, la = (Math.atan2(ringP[1] - sackP[1], ringP[0] - sackP[0]) * 180) / Math.PI;
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ filter: dk > 0 ? `blur(${P.defocus * dk}px)` : undefined }}>{bg}</AbsoluteFill>
      {f >= ba && Array.from({ length: links }, (_, i) => {
        const t = (i + 0.5) / links, sag = Math.sin(t * Math.PI) * 60, lx = sackP[0] + (ringP[0] - sackP[0]) * t, ly = sackP[1] + (ringP[1] - sackP[1]) * t + sag;
        return <PropImg key={i} id="chain_link" x={lx} y={ly} w={i % 2 ? 22 : 36} h={62} rot={la + 90} op={wk} />;
      })}
      {[[-150, 30, 1], [120, 40, 0.95], [-10, -20, 1.1]].map(([dx, dy, k], i) => <PropImg key={i} id="money_sack" x={sackCx + dx} y={sackY + dy} w={300 * k} ax={0.5} ay={0.45} />)}
      {f >= ba && (
        <div style={{ position: "absolute", inset: 0, filter: wk < 1 ? `blur(${10 * (1 - wk)}px)` : undefined }}>
          <PropImg id="iron_ball" x={bcx} y={bcy} w={882 * bs} ax={440 / 882} ay={680 / 1123} rot={sw} />
          {text.split("\n").map((ln, i, arr) => <div key={i} style={{ position: "absolute", left: bcx, top: bcy + (i - (arr.length - 1) / 2) * R * 0.5, transform: "translate(-50%,-50%)", fontFamily: "Jalnan", fontSize: R * 0.44, color: "#fff", whiteSpace: "nowrap" }}>{ln}</div>)}
        </div>
      )}
    </AbsoluteFill>
  );
};

// ══ 37. 회로 배경 부품 발광 [ref4-hyundai 2:02:33 전륜→후륜] — #0E3A45 회로 트레이스+노드 펄스, 부품 네온 그린 6f + 연기 글로우 깜빡임, 라벨 블러 팝 + 핀선 ══
export const TechCircuitGlowParams = z.object({
  glowIn: num(6, 1, 30, 1, "부품 발광 페이드", "timing", "f"),
  labelPop: num(6, 1, 30, 1, "라벨 블러 팝", "timing", "f"),
  flicker: num(8, 2, 30, 1, "연기 글로우 깜빡임 주기", "timing", "f"),
  pulsePeriod: num(30, 6, 120, 1, "노드 펄스 주기", "timing", "f"),
  switchAt: num(60, 0, 300, 1, "다음 부품으로 이동(0=안 함)", "timing", "f"),
  pinLen: num(90, 20, 300, 5, "핀선 길이", "size", "px"),
  bg: col("#0E3A45", "배경 색"),
  neon: col("#3EE04A", "발광 색"),
  label: col("#3C7BD9", "라벨 색"),
});
export type TechCircuitGlowP = z.infer<typeof TechCircuitGlowParams>;
export const CircuitBg: React.FC<{ bg: string; period: number; seed?: string }> = ({ bg, period, seed = "cb" }) => {
  const f = useCurrentFrame();
  const traces = Array.from({ length: 26 }, (_, i) => {
    const y = 60 + (i * 41) % 980, x0 = random(`${seed}x${i}`) * W * 0.8, l1 = 120 + 300 * random(`${seed}l${i}`), dy = (random(`${seed}d${i}`) - 0.5) * 200, l2 = 80 + 200 * random(`${seed}m${i}`);
    return { d: `M${x0},${y} L${x0 + l1},${y} L${x0 + l1 + Math.abs(dy)},${y + dy} L${x0 + l1 + Math.abs(dy) + l2},${y + dy}`, end: [x0 + l1 + Math.abs(dy) + l2, y + dy] as Pt, start: [x0, y] as Pt };
  });
  return (
    <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 50%, #145567 0%, ${bg} 70%)` }}>
      <Full>
        {traces.map((t, i) => {
          const pu = 0.35 + 0.65 * Math.pow(Math.abs(Math.sin(((f + i * 9) / period) * Math.PI)), 3);
          return (
            <g key={i}>
              <path d={t.d} stroke="#3FB6D6" strokeWidth={3} fill="none" opacity={0.45} />
              <circle cx={t.end[0]} cy={t.end[1]} r={7} fill="#8FF0FF" opacity={pu} style={{ filter: "drop-shadow(0 0 8px #3FD0FF)" }} />
              <circle cx={t.start[0]} cy={t.start[1]} r={5} fill="#3FB6D6" opacity={0.6} />
            </g>
          );
        })}
      </Full>
    </AbsoluteFill>
  );
};
/** 세모지 세단 옆모습 PNG(car_sedan_side 1430×511, 왼쪽이 앞). 바퀴 중심(원본 px) = 앞 (252,392) · 뒤 (1144,392), 반지름 ≈121 */
export const CAR_WHEELS: Pt[] = [[252, 392], [1144, 392]];
export const CarSideImg: React.FC<{ x: number; y: number; w: number }> = ({ x, y, w }) => <PropImg id="car_sedan_side" x={x} y={y} w={w} ax={0} ay={0} />;
/** 옆모습 세단(로컬 1000×360, 바퀴 중심 (230,290)·(790,290) r=78) */
export const CarSideSvg: React.FC<{ x: number; y: number; w: number }> = ({ x, y, w }) => (
  <svg width={w} height={w * 0.36} viewBox="0 0 1000 360" style={{ position: "absolute", left: x, top: y, overflow: "visible" }}>
    <defs><linearGradient id="carB" x1="0" x2="1"><stop offset="0" stopColor="#BFEFE6" /><stop offset="1" stopColor="#D7D4E6" /></linearGradient></defs>
    <path d="M40,250 C30,200 60,170 140,160 L290,150 C360,90 440,60 560,60 C650,60 720,100 790,150 L900,170 C960,180 985,210 980,250 L975,290 L40,290Z" fill="url(#carB)" />
    <path d="M320,150 C380,100 450,80 540,78 L560,150Z" fill="#6F8C99" /><path d="M580,78 C660,82 710,110 760,150 L580,150Z" fill="#6F8C99" />
    <path d="M60,220 L960,220" stroke="rgba(0,0,0,0.12)" strokeWidth={4} />
    {[230, 790].map((cx) => <g key={cx}><circle cx={cx} cy={290} r={86} fill="#2c3a40" /><circle cx={cx} cy={290} r={62} fill="#DCE6EA" /><circle cx={cx} cy={290} r={16} fill="#9AA8AE" />{Array.from({ length: 10 }, (_, k) => <line key={k} x1={cx} y1={290} x2={cx + Math.cos((k / 10) * TAU) * 58} y2={290 + Math.sin((k / 10) * TAU) * 58} stroke="#9AA8AE" strokeWidth={5} />)}</g>)}
    <path d="M960,200 L985,210 L980,235 L955,230Z" fill="#E0505A" />
  </svg>
);
export const TechCircuitGlow: React.FC<{ at: number; parts: { x: number; y: number; r: number; label: string }[]; product?: RN; p?: Partial<TechCircuitGlowP> }> = ({ at, parts, product, p }) => {
  const P = def(TechCircuitGlowParams, p);
  const f = useCurrentFrame();
  const idx = P.switchAt > 0 && f >= at + P.switchAt && parts.length > 1 ? 1 : 0;
  const a0 = idx ? at + P.switchAt : at, pt = parts[idx];
  const gk = lerp(f, a0, a0 + P.glowIn, 0, 1, Easing.linear), lp = blurPop(f, a0, P.labelPop, 1.3, 10);
  const fl = 0.75 + 0.25 * Math.abs(Math.sin(((f - a0) / P.flicker) * Math.PI));
  return (
    <AbsoluteFill>
      <CircuitBg bg={P.bg} period={P.pulsePeriod} />
      {product}
      {f >= a0 && pt && (
        <>
          <Full>
            <g opacity={gk} style={{ filter: `drop-shadow(0 0 16px ${P.neon})` }}>
              <circle cx={pt.x} cy={pt.y} r={pt.r * 1.08} fill={P.neon} opacity={0.82 * fl} />
              <circle cx={pt.x} cy={pt.y} r={pt.r * 0.7} fill="none" stroke="#B8FFB0" strokeWidth={6} opacity={0.8} />
              {Array.from({ length: 9 }, (_, k) => { const life = 24, g = (f - a0 + k * 5) % life, a = random(`sm${k}`) * TAU; return <circle key={k} cx={pt.x + Math.cos(a) * pt.r * 0.8 - g * 1.5} cy={pt.y + Math.sin(a) * pt.r * 0.6 - g * 2.5} r={pt.r * (0.18 + 0.2 * (g / life))} fill={P.neon} opacity={0.6 * (1 - g / life) * fl} />; })}
            </g>
            <line x1={pt.x} y1={pt.y - pt.r * 0.2} x2={pt.x} y2={pt.y - pt.r - P.pinLen} stroke="#fff" strokeWidth={4} opacity={lp.op} />
            <circle cx={pt.x} cy={pt.y - pt.r * 0.2} r={7} fill="#fff" opacity={lp.op} />
          </Full>
          <div style={{ position: "absolute", left: pt.x, top: pt.y - pt.r - P.pinLen, transform: `translate(-50%,-100%) scale(${lp.s})`, transformOrigin: "50% 100%", opacity: lp.op, filter: lp.blur > 0.3 ? `blur(${lp.blur}px)` : undefined, background: P.label, color: "#fff", fontFamily: "NeoHv", fontSize: 40, padding: "6px 22px", borderRadius: 8, border: "3px solid #fff", whiteSpace: "nowrap" }}>{pt.label}</div>
        </>
      )}
    </AbsoluteFill>
  );
};

// ══ 38. 실사 사진 불꽃 눈 [ref4-samsung 0:52:03] — 눈 위치에 불꽃 스티커 2개(≈110×140, 얼굴 폭 25%), scaleY 0.95↔1.05 8f 비동기 ══
export const PhotoFlameEyesParams = z.object({
  attach: num(4, 0, 30, 1, "붙는 팝 길이", "timing", "f"),
  w: num(110, 30, 300, 2, "불꽃 폭", "size", "px"),
  h: num(140, 40, 400, 2, "불꽃 높이", "size", "px"),
  wobble: num(0.05, 0, 0.3, 0.01, "흔들림(scaleY ±)", "motion"),
  period: num(8, 2, 30, 1, "흔들림 주기", "timing", "f"),
  lift: num(0.3, 0, 1, 0.05, "불꽃을 눈 위로 올림(높이 비율)", "size"),
});
export type PhotoFlameEyesP = z.infer<typeof PhotoFlameEyesParams>;
export const FlameSticker: React.FC<{ w: number; h: number; id: string }> = ({ w, h, id }) => (
  <svg width={w} height={h} viewBox="-50 -130 100 140" style={{ overflow: "visible", display: "block" }}>
    <defs><linearGradient id={id} x1="0" y1="1" x2="0" y2="0"><stop offset="0" stopColor="#FFD83A" /><stop offset="0.55" stopColor="#FF8A1E" /><stop offset="1" stopColor="#F2401B" /></linearGradient></defs>
    <path d="M0,8 C-40,8 -52,-30 -36,-62 C-30,-48 -20,-44 -16,-50 C-24,-80 -6,-108 8,-128 C8,-100 30,-88 38,-62 C42,-72 40,-84 36,-92 C56,-66 58,-24 40,-6 C30,4 16,8 0,8Z" fill={`url(#${id})`} />
    <path d="M0,4 C-20,4 -26,-16 -16,-36 C-10,-26 -4,-26 -2,-34 C-4,-50 6,-62 12,-70 C14,-54 26,-44 24,-24 C22,-6 12,4 0,4Z" fill="#FFE97A" />
  </svg>
);
export const PhotoFlameEyes: React.FC<{ at: number; eyes: Pt[]; children?: RN; p?: Partial<PhotoFlameEyesP> }> = ({ at, eyes, children, p }) => {
  const P = def(PhotoFlameEyesParams, p);
  const f = useCurrentFrame();
  return (
    <AbsoluteFill>
      {children}
      {f >= at && eyes.map(([ex, ey], i) => {
        const g = f - at, s = kf(g, 0, [0, P.attach * 0.6, P.attach], [0, 1.15, 1], Easing.out(Easing.quad));
        const sy = 1 + P.wobble * Math.sin(((g + i * P.period * 0.37) / P.period) * TAU);
        return (
          <div key={i} style={{ position: "absolute", left: ex - P.w / 2, top: ey - P.h * (1 - P.lift) - P.h * 0.0, width: P.w, height: P.h, transformOrigin: "50% 90%", transform: `scale(${s},${s * sy})`, filter: "drop-shadow(0 0 8px rgba(255,120,0,0.6))" }}>
            <FlameSticker w={P.w} h={P.h} id={`fs${i}`} />
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// ══ 39. 심전도 배경 + 가슴 통증 글로우 [ref4-samsung 1:31:00] — #93403F, ECG 스크롤, 30f 지연 후 가슴 붉은 글로우 10f 성장 + 0.7↔1 펄스 12f, 번개 하트, 스파이크 버블 ══
export const EcgChestGlowParams = z.object({
  ecgSpeed: num(12, 0, 60, 1, "ECG 스크롤 속도", "motion", "px/f"),
  ecgW: num(3, 1, 10, 0.5, "ECG 선 두께", "size", "px"),
  glowDelay: num(30, 0, 120, 1, "글로우 지연", "timing", "f"),
  glowLen: num(10, 1, 40, 1, "글로우 성장", "timing", "f"),
  glowD: num(260, 60, 700, 10, "글로우 지름", "size", "px"),
  pulseLo: num(0.7, 0, 1, 0.05, "펄스 최저 알파", "look"),
  pulsePeriod: num(12, 2, 40, 1, "펄스 주기", "timing", "f"),
  heart: num(420, 100, 800, 10, "번개 하트 크기", "size", "px"),
  bg: col("#93403F", "배경 색"),
  ecg: col("#D09996", "ECG 색"),
});
export type EcgChestGlowP = z.infer<typeof EcgChestGlowParams>;
export const EcgLine: React.FC<{ y: number; speed: number; w: number; color: string; period?: number; amp?: number }> = ({ y, speed, w, color, period = 300, amp = 120 }) => {
  const f = useCurrentFrame();
  const off = (f * speed) % period, beats = Math.ceil(W / period) + 2;
  const beat = (x: number) => `L${x + 60},${y} q15,-18 30,0 L${x + 130},${y} l10,16 l14,${-amp} l14,${amp * 1.25} l10,${-amp * 0.25 - 16} L${x + 220},${y} q20,-30 40,0 L${x + period},${y}`;
  const d = `M${-period - off},${y} ` + Array.from({ length: beats + 1 }, (_, i) => beat(-period - off + i * period)).join(" ");
  const d2 = `M${-period - off * 0.7},${y + 220} ` + Array.from({ length: beats + 1 }, (_, i) => beat(-period - off * 0.7 + i * period).replace(new RegExp(`,${y}`, "g"), `,${y + 220}`)).join(" ");
  return <Full><path d={d} stroke={color} strokeWidth={w} fill="none" strokeLinejoin="round" /><path d={d2} stroke={color} strokeWidth={w * 0.7} fill="none" opacity={0.5} /></Full>;
};
export const LightningHeartSvg: React.FC<{ x: number; y: number; s: number }> = ({ x, y, s }) => (
  <svg width={s} height={s} viewBox="-110 -100 220 200" style={{ position: "absolute", left: x - s / 2, top: y - s / 2, overflow: "visible" }}>
    <path d="M0,90 C-60,50 -105,10 -100,-40 C-95,-85 -40,-95 0,-50 C40,-95 95,-85 100,-40 C105,10 60,50 0,90Z" fill="#E4454A" stroke="#B72A30" strokeWidth={8} />
    <path d="M-40,-50 C-30,-70 -10,-72 -2,-60" stroke="rgba(255,255,255,0.35)" strokeWidth={8} fill="none" strokeLinecap="round" />
    <path d="M10,-60 L-24,4 L4,4 L-12,56 L30,-10 L4,-10 L22,-60Z" fill="#fff" />
  </svg>
);
export const EcgChestGlow: React.FC<{ at: number; chest: Pt; char: RN; heart?: Pt; bubble?: (at: number) => RN; p?: Partial<EcgChestGlowP> }> = ({ at, chest, char, heart = [1240, 460], bubble, p }) => {
  const P = def(EcgChestGlowParams, p);
  const f = useCurrentFrame();
  const ga = at + P.glowDelay, gk = lerp(f, ga, ga + P.glowLen, 0, 1, Easing.out(Easing.quad));
  const pu = f > ga + P.glowLen ? P.pulseLo + (1 - P.pulseLo) * (0.5 + 0.5 * Math.cos(((f - ga - P.glowLen) / P.pulsePeriod) * TAU)) : 1;
  const r = (P.glowD / 2) * gk;
  return (
    <AbsoluteFill style={{ background: P.bg }}>
      <EcgLine y={500} speed={P.ecgSpeed} w={P.ecgW} color={P.ecg} />
      <PropImg id="lightning_heart" x={heart[0]} y={heart[1]} w={P.heart} />
      {char}
      {gk > 0 && <div style={{ position: "absolute", left: chest[0] - r, top: chest[1] - r, width: 2 * r, height: 2 * r, borderRadius: "50%", opacity: pu, background: "radial-gradient(circle, #FF2A2A 0%, rgba(255,40,40,0.85) 22%, rgba(230,30,30,0.35) 55%, transparent 72%)" }} />}
      {gk > 0 && <div style={{ position: "absolute", left: chest[0] - r * 0.3, top: chest[1] - r * 0.3, width: r * 0.6, height: r * 0.6, borderRadius: "50%", opacity: pu, border: `${Math.max(2, r * 0.03)}px solid rgba(255,90,90,0.7)` }} />}
      {bubble && bubble(ga + 6)}
    </AbsoluteFill>
  );
};

// ── 리그 헬퍼: 2관절 IK — 퍼펫 로컬 좌표 target 에 손이 닿도록 a1·a2 계산 (bend: 팔꿈치 굽는 방향 1/-1) ──
export const reachArm = (side: -1 | 1, target: Pt, bend: 1 | -1 = 1, extra: Partial<Arm> = {}): Arm => {
  const s = side < 0 ? SH_L : SH_R, dx = (target[0] - s[0]) * side, dy = target[1] - s[1];
  const d = Math.min(UA + FA - 0.01, Math.max(Math.abs(UA - FA) + 0.01, Math.hypot(dx, dy)));
  const th = (Math.atan2(dx, dy) * 180) / Math.PI;
  const al = (Math.acos((UA * UA + d * d - FA * FA) / (2 * UA * d)) * 180) / Math.PI;
  const be = (Math.acos((UA * UA + FA * FA - d * d) / (2 * UA * FA)) * 180) / Math.PI;
  return { a1: th + bend * al, a2: -bend * (180 - be), ...extra };
};
/** 화면 좌표 → 퍼펫 로컬 좌표 (puppetToScreen 역변환) */
export const screenToPuppet = (p: { x: number; y: number; h: number; flip?: boolean }, sp: Pt): Pt => {
  const k = p.h / 700;
  return [200 + ((sp[0] - p.x) / k) * (p.flip ? -1 : 1), 700 + (sp[1] - p.y) / k];
};
