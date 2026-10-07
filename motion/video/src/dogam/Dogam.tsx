import React from "react";
import { AbsoluteFill } from "remotion";
import { byId } from "./registry";
/** 도감 미리보기 한 편. p 가 오면 그 기법의 변수로 넘긴다 */
export const Dogam: React.FC<{ id: string; p?: Record<string, unknown> }> = ({ id, p }) => { const e = byId(id); return <AbsoluteFill style={{ background: "#1c1c1c", overflow: "hidden" }}><e.C p={p} /></AbsoluteFill>; };
/** Studio 조절용: 변수 스키마가 있는 기법마다 Param-<id> 컴포지션 */
export const makeParamComp = (id: string) => { const e = byId(id); const C: React.FC<any> = (props) => <AbsoluteFill style={{ background: "#1c1c1c", overflow: "hidden" }}><e.C p={props} /></AbsoluteFill>; return C; };
