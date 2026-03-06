import { z } from "zod";

/**
 * Remotion Studio Props Editor용 Zod 스키마
 *
 * manifest는 JSON blob이라 그대로 passthrough하고,
 * subtitleConfig만 인터랙티브 편집 가능하게 정의한다.
 */

export const subtitleConfigSchema = z.object({
  visible: z.boolean().describe("자막 표시/숨김"),
  fontFamily: z.string().describe("자막 폰트"),
  fontSize: z.number().min(12).max(120).describe("글자 크기 (px)"),
  fontWeight: z.number().min(100).max(900).step(100).describe("글자 굵기"),
  color: z.string().describe("텍스트 색상"),
  strokeColor: z.string().describe("외곽선 색상"),
  strokeWidth: z.number().min(0).max(10).describe("외곽선 두께 (px)"),
  keywordColor: z.string().describe("키워드 하이라이트 색상"),
  keywordStrokeColor: z.string().describe("키워드 외곽선 색상"),
  bottomOffset: z.number().min(0).max(300).describe("하단 오프셋 px (기본 30)"),
  maxWidth: z.string().describe("최대 너비 (예: 85%)"),
  lineHeight: z.number().min(1).max(3).step(0.1).describe("줄간격"),
});

export const kairosVideoSchema = z.object({
  manifest: z.any().describe("씬 데이터 (자동 로드)"),
  subtitleConfig: subtitleConfigSchema,
});

export const sceneEditorSchema = z.object({
  manifest: z.any().describe("씬 데이터 (자동 로드)"),
  sceneNumber: z.number().min(1).max(50).describe("씬 번호"),
  subtitleConfig: subtitleConfigSchema,
});

export const vizOnlySchema = z.object({
  manifest: z.any().describe("씬 데이터 (자동 로드)"),
  sceneNumber: z.number().min(1).max(80).describe("씬 번호"),
});

export const vizStillSchema = z.object({
  vizData: z.any().describe("시각화 데이터 (VisualizationData)"),
  designTokens: z.any().optional().describe("디자인 토큰 오버라이드"),
});
