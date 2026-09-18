/** Reproducible smoke render: red 0-2s, green 2-4s source, two 2s scenes.
 * Generate public/track-smoke.mp4 with ffmpeg before rendering.
 * At frame 75 the pixel must be green (not restarted red).
 */
import React from "react";
import {Composition, registerRoot} from "remotion";
import {SimpleVideo} from "../src/SimpleVideo";
import {VideoTrackLayer} from "../src/components/VideoTrackLayer";
import {SceneRendererInner} from "../src/components/SceneRenderer";
import {DesignPresetProvider} from "../src/design";

const clip = {clipId: "two-scenes", sourcePath: "track-smoke.mp4", sceneIds: ["s1", "s2"],
  timelineStartFrame: 0, timelineDurationFrames: 120, sourceIn: 0, sourceOut: 4, muted: true};
const manifest: any = {meta: {topic: "track smoke", fps: 30, resolution: {width: 320, height: 180},
  subtitleFont: "sans-serif", vizFont: "sans-serif"}, bgm: null, videoClips: [clip],
  scenes: [1, 2].map(n => ({sceneNumber: n, sceneId: "s" + n, durationFrames: 60,
    audioDurationSec: 2, imagePath: "", audioPath: "", subtitles: [],
    transition: {type: "none", durationFrames: 0}, kenBurns: {type: "none"}}))};
const Full = () => <SimpleVideo manifest={manifest} subtitleConfig={{visible: false} as any} />;
const Slice = () => <DesignPresetProvider meta={manifest.meta}>
  <SceneRendererInner scene={{...manifest.scenes[1], videoTrackSlices: [
    {...clip, timelineStartFrame: 0, timelineDurationFrames: 60, sourceIn: 2, sourceOut: 4}
  ]}} />
</DesignPresetProvider>;
const Track = () => <VideoTrackLayer clips={[clip]} />;
registerRoot(() => <>
  <Composition id="FullTrackSmoke" component={Full} durationInFrames={120} fps={30} width={320} height={180} />
  <Composition id="SliceTrackSmoke" component={Slice} durationInFrames={60} fps={30} width={320} height={180} />
  <Composition id="TrackSmoke" component={Track} durationInFrames={120} fps={30} width={320} height={180} />
</>);
