import React, { useEffect, useState } from "react";
import { AbsoluteFill, staticFile, delayRender, continueRender } from "remotion";
import { BarChart } from "../visualizations/BarChart";
import { LineChart } from "../visualizations/LineChart";
import { PieChart } from "../visualizations/PieChart";
import { TableView } from "../visualizations/TableView";
import { Timeline } from "../visualizations/Timeline";
import { Compare } from "../visualizations/Compare";
import { SlideQuote } from "../visualizations/SlideQuote";
import { SlideList } from "../visualizations/SlideList";
import { SlideNumbered } from "../visualizations/SlideNumbered";
import { SlideHighlight } from "../visualizations/SlideHighlight";
import { TechTree } from "../visualizations/TechTree";
import { SlideStatistic } from "../visualizations/SlideStatistic";
import { SlideProscons } from "../visualizations/SlideProscons";
import { SlideDefinition } from "../visualizations/SlideDefinition";
import { SlideSummary } from "../visualizations/SlideSummary";
import { SlideProfile } from "../visualizations/SlideProfile";
import { SlideRanking } from "../visualizations/SlideRanking";
import { SlideProcess } from "../visualizations/SlideProcess";
import { SlideChecklist } from "../visualizations/SlideChecklist";
import { SlideQna } from "../visualizations/SlideQna";
import { SlideCountdown } from "../visualizations/SlideCountdown";
import { FONT_DEFS } from "../visualizations/vizStyles";
import { VizBackgroundProvider } from "../contexts/VizBackgroundContext";
import type { VisualizationData, VizAnimationConfig } from "../types/manifest";

interface Props {
  data: VisualizationData;
  durationInFrames: number;
  fps: number;
  vizAnimation?: VizAnimationConfig;
  vizBackgroundPath?: string;
}

/**
 * JavaScript FontFace API로 폰트 로드 — delayRender로 완료 보장
 * CSS @font-face url()은 Remotion 렌더 서버에서 404 발생하므로,
 * staticFile()을 통한 JS 로딩 사용.
 */
const useFonts = () => {
  const [handle] = useState(() => delayRender("Loading custom fonts"));

  useEffect(() => {
    const loadAll = async () => {
      const promises = FONT_DEFS.map(async (f) => {
        const url = staticFile(f.file);
        const descriptors: FontFaceDescriptors = {
          weight: f.weight,
          style: "normal",
        };
        const face = new FontFace(f.family, `url('${url}')`, descriptors);
        const loaded = await face.load();
        document.fonts.add(loaded);
      });
      await Promise.all(promises);
      continueRender(handle);
    };
    loadAll().catch((err) => {
      console.error("Font loading failed:", err);
      continueRender(handle);
    });
  }, [handle]);
};

export const VisualizationRenderer: React.FC<Props> = ({
  data,
  durationInFrames,
  fps,
  vizAnimation,
  vizBackgroundPath,
}) => {
  useFonts();
  const commonProps = { data, durationInFrames, fps, vizAnimation };

  return (
    <AbsoluteFill>
      <VizBackgroundProvider value={vizBackgroundPath || ""}>
        {(() => {
          switch (data.vizType) {
            case "bar_chart":
            case "graph":        // 하위호환
              return <BarChart {...commonProps} />;
            case "line_chart":
              return <LineChart {...commonProps} />;
            case "pie_chart":
              return <PieChart {...commonProps} />;
            case "tech_tree":
              return <TechTree {...commonProps} />;
            case "timeline":
              return <Timeline {...commonProps} />;
            case "table":
              return <TableView {...commonProps} />;
            case "compare":
            case "diagram":        // 하위호환 → Compare
            case "slide_compare":  // 하위호환 → Compare
              return <Compare {...commonProps} />;
            case "slide_quote":
              return <SlideQuote {...commonProps} />;
            case "slide_list":
              return <SlideList {...commonProps} />;
            case "slide_numbered":
              return <SlideNumbered {...commonProps} />;
            case "slide_highlight":
              return <SlideHighlight {...commonProps} />;
            case "slide_statistic":
              return <SlideStatistic {...commonProps} />;
            case "slide_proscons":
              return <SlideProscons {...commonProps} />;
            case "slide_definition":
              return <SlideDefinition {...commonProps} />;
            case "slide_summary":
              return <SlideSummary {...commonProps} />;
            case "slide_profile":
              return <SlideProfile {...commonProps} />;
            case "slide_ranking":
              return <SlideRanking {...commonProps} />;
            case "slide_process":
              return <SlideProcess {...commonProps} />;
            case "slide_checklist":
              return <SlideChecklist {...commonProps} />;
            case "slide_qna":
              return <SlideQna {...commonProps} />;
            case "slide_countdown":
              return <SlideCountdown {...commonProps} />;
            // Creative Direction v4.0 타입 → 가장 가까운 기존 컴포넌트로 폴백
            case "impact_count":
            case "dramatic_number":
            case "counter_wall":
            case "icon_stat":
            case "slide_bignum":
              return <SlideStatistic {...commonProps} />;
            case "reveal_sequence":
              return <SlideNumbered {...commonProps} />;
            case "split_contrast":
              return <Compare {...commonProps} />;
            case "spotlight_reveal":
            case "title_card":
              return <SlideHighlight {...commonProps} />;
            case "narrative_build":
            case "word_cascade":
            case "icon_grid":
              return <SlideList {...commonProps} />;
            default:
              return <BarChart {...commonProps} />;
          }
        })()}
      </VizBackgroundProvider>
    </AbsoluteFill>
  );
};
