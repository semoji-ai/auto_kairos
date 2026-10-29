// 세모지 에셋 키트 색인 — 캐릭터 리그(public/kit/<id>/rig.json)와 소품(public/kit/props/props.json)
import walker1 from "../../public/kit/walker1/rig.json";
import c2_boss from "../../public/kit/c2_boss/rig.json";
import c3_woman from "../../public/kit/c3_woman/rig.json";
import c4_elder from "../../public/kit/c4_elder/rig.json";
import c5_chef from "../../public/kit/c5_chef/rig.json";
import PROPS_META from "../../public/kit/props/props.json";
import { staticFile } from "remotion";

export type RigJson = { dir: string; w: number; h: number; feet: number[]; top: number; shoulderR: number[]; shoulderL: number[]; torsoBottom: number; extras: string[] };
/** 캐스트: walker1 1930년대 청년 · c2_boss 50대 정장 기업가 · c3_woman 20대 여성 회사원 · c4_elder 한복 노인 · c5_chef 중식 요리사 */
export const CAST = { walker1, c2_boss, c3_woman, c4_elder, c5_chef } as Record<string, RigJson>;
export type CastId = keyof typeof CAST;

type PropMeta = { size: number[] };
const PM = PROPS_META as unknown as Record<string, PropMeta>;
/** 소품 PNG 경로(staticFile). id 는 public/kit/props/*.png 이름 */
export const prop = (id: string) => staticFile(`kit/props/${id}.png`);
/** 소품 원본 크기(px) — 가로세로비 계산용 */
export const propSize = (id: string): [number, number] => { const m = PM[id]; return m ? [m.size[0], m.size[1]] : [512, 512]; };
/** 폭 w 로 맞춘 높이 */
export const propH = (id: string, w: number) => { const [a, b] = propSize(id); return (w * b) / a; };
