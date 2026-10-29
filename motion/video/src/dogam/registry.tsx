// 기법 도감 레지스트리: 모든 갤러리 데모를 id 로 모은다. 미리보기는 Dogam 컴포지션에 id 를 넘겨 한 편씩 렌더.
import React from "react";
import * as GCore from "../gallery/core";
import * as GCharts from "../gallery/charts";
import * as GTrans from "../gallery/transitions";
import * as GCall from "../gallery/callouts";
import * as GChar from "../gallery/characters";
import * as GBg from "../gallery/backgrounds";
import * as X0 from "../gallery/x_transitions";
import * as X1 from "../gallery/x_text";
import * as X2 from "../gallery/x_callouts";
import * as X3 from "../gallery/x_charts";
import * as X4 from "../gallery/x_media";
import * as X5 from "../gallery/x_acting";
import * as X6 from "../gallery/x_explainer";
import * as GKit from "../gallery/kit";


import type { Demo } from "../gallery/runner";
const GROUPS: [string, Demo[]][] = [
  ["core", GCore.DEMOS], ["charts", GCharts.DEMOS], ["transitions", GTrans.DEMOS],
  ["callouts", GCall.DEMOS], ["characters", GChar.DEMOS], ["backgrounds", GBg.DEMOS],
  ["x_transitions", X0.DEMOS], ["x_text", X1.DEMOS], ["x_callouts", X2.DEMOS], ["x_charts", X3.DEMOS], ["x_media", X4.DEMOS], ["x_acting", X5.DEMOS], ["kit", GKit.DEMOS], ["x_explainer", X6.DEMOS],
];
export const ENTRIES: ({ id: string; group: string; idx: number } & Demo)[] =
  GROUPS.flatMap(([g, ds]) => ds.map((d, i) => ({ ...d, id: d.id ?? `${g}-${String(i + 1).padStart(2, "0")}`, group: g, idx: i + 1 })));
export const byId = (id: string) => ENTRIES.find((e) => e.id === id) ?? ENTRIES[0];
