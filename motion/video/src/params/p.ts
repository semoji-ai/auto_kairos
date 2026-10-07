// 기법 변수(파라미터) 규약 ─────────────────────────────────────────────────
// 각 기법 컴포넌트는 움직임·길이·크기·색처럼 "바꾸면 연출이 달라지는 수치"를 zod 스키마로 내보낸다.
//   export const StampParams = z.object({ dur: num(5, 1, 30, 1, "슬램 길이(f)", "timing"), ... })
//   컴포넌트는 p?: Partial<...> 를 받아 def(StampParams, p) 로 기본값과 합친다.
// 기본값 = 레퍼런스 실측/현재 구현값(바꾸지 않으면 결과가 이전과 완전히 같아야 한다).
// Remotion Studio 에서 Param-<id> 컴포지션을 열면 오른쪽 패널에 슬라이더로 나온다.
import { z } from "zod";
import { zColor } from "@remotion/zod-types";

/** 변수 그룹: timing(길이·지연·스태거) / motion(거리·각도·오버슈트·세기) / size(크기·두께) / look(색·불투명도·블러) */
export type PGroup = "timing" | "motion" | "size" | "look";
const tag = (label: string, group: PGroup, unit?: string) => JSON.stringify({ label, group, unit });

export const num = (d: number, min: number, max: number, step: number, label: string, group: PGroup, unit?: string) =>
  z.number().min(min).max(max).step(step).default(d).describe(tag(label, group, unit));
export const col = (d: string, label: string) => zColor().default(d).describe(tag(label, "look"));
export const flag = (d: boolean, label: string, group: PGroup = "motion") => z.boolean().default(d).describe(tag(label, group));
export const choice = <T extends string>(d: T, opts: readonly [T, ...T[]], label: string, group: PGroup = "motion") =>
  z.enum(opts).default(d).describe(tag(label, group));

/** 스키마 기본값 + 부분 덮어쓰기 */
export const def = <S extends z.ZodObject<any>>(schema: S, p?: Partial<z.infer<S>>): z.infer<S> =>
  ({ ...(schema.parse({}) as object), ...(p || {}) }) as z.infer<S>;

/** 도감 내보내기용: 스키마 → [{key, default, min, max, step, label, group, unit, type}] */
export const describeSchema = (schema: z.ZodObject<any>) =>
  Object.entries(schema.shape).map(([key, t]: [string, any]) => {
    let meta: any = {};
    try { meta = JSON.parse(t.description || "{}"); } catch (e) { meta = { label: t.description }; }
    const d = (schema.parse({}) as any)[key];
    const j: any = z.toJSONSchema ? (z.toJSONSchema as any)(t, { unrepresentable: "any" }) : {};
    return { key, default: d, min: j.minimum, max: j.maximum, step: j.multipleOf, options: j.enum, type: typeof d === "string" && /^#/.test(d) ? "color" : typeof d, ...meta };
  });
