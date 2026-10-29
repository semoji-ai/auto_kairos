import React from "react";
import { Composition, Folder } from "remotion";
import { MapBg } from "./map/MapBg";
import { Main } from "./Main";
import TL from "./timeline.json";
import { FPS } from "./fx";
import * as GCharts from "./gallery/charts";
import * as GTrans from "./gallery/transitions";
import * as GCall from "./gallery/callouts";
import * as GChar from "./gallery/characters";
import * as GBg from "./gallery/backgrounds";
import * as GCore from "./gallery/core";
import { Dogam, makeParamComp } from "./dogam/Dogam";
import { byId, ENTRIES } from "./dogam/registry";
import { ExplainerDemo, EXPLAINER_DEMO_DUR } from "./explainer_demo/ExplainerDemo";

const galleries = [["Gallery-core", GCore], ["Gallery-charts", GCharts], ["Gallery-transitions", GTrans], ["Gallery-callouts", GCall], ["Gallery-characters", GChar], ["Gallery-backgrounds", GBg]] as const;

export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="ExplainerDemo" component={ExplainerDemo} durationInFrames={EXPLAINER_DEMO_DUR} fps={FPS} width={1920} height={1080} />
    <Composition id="Jjajang" component={Main} durationInFrames={Math.ceil(TL.total * FPS)} fps={FPS} width={1920} height={1080} />
    {galleries.map(([id, g]) => (
      <Composition key={id} id={id} component={g.Gallery} durationInFrames={g.GALLERY_DUR} fps={FPS} width={1920} height={1080} />
    ))}
    {/* 지도 배경 프리렌더(AE 가이드 레이어용): props 로 카메라·크기 지정 */}
    <Composition id="MapBg" component={MapBg} durationInFrames={1} fps={FPS} width={2364} height={1330} defaultProps={{ lng: 123.4, lat: 37.4, zoom: 6.2 }} />
    <Composition id="Dogam" component={Dogam} fps={FPS} width={1920} height={1080} durationInFrames={120}
      defaultProps={{ id: ENTRIES[0]?.id ?? "charts-01" }}
      calculateMetadata={({ props }) => ({ durationInFrames: byId(props.id).dur })} />
    {/* 기법 변수 조절: Studio 오른쪽 패널에 슬라이더 */}
    <Folder name="params">
      {ENTRIES.filter((e) => e.schema).map((e) => (
        <Composition key={e.id} id={`Param-${e.id.replace(/_/g, "-")}`} component={makeParamComp(e.id)} schema={e.schema!} defaultProps={e.schema!.parse({})}
          fps={FPS} width={1920} height={1080} durationInFrames={e.dur} />
      ))}
    </Folder>
  </>
);
