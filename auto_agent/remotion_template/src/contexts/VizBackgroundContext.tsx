/**
 * 시각화 배경 이미지 Context
 *
 * 하이브리드 viz: 아트스타일 배경 이미지 경로를
 * VisualizationRenderer → VizShell로 전달.
 * 개별 viz 컴포넌트(BarChart, Timeline 등)를 수정하지 않기 위해
 * Context 패턴 사용.
 */
import { createContext, useContext } from "react";

const VizBackgroundContext = createContext<string>("");

export const VizBackgroundProvider = VizBackgroundContext.Provider;
export const useVizBackground = () => useContext(VizBackgroundContext);
