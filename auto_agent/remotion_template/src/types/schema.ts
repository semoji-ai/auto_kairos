import { z } from "zod";

/**
 * Remotion Studio Props Editor용 Zod 스키마
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

/** CreativeScene 데이터 편집 스키마 */
export const sceneOverrideSchema = z.object({
  // ── Creative 필드 ──
  headline: z.string().describe("헤드라인 텍스트 ({{키워드}}로 강조, \\n으로 줄바꿈)"),
  layout: z.enum([
    "", "items_list", "items_grid", "split", "headline_only",
    "cinematic", "bar", "bar_horizontal", "line", "pie", "donut",
    "flow", "timeline", "metric_spotlight", "metric_wall",
    "rank_list", "comparison_table", "before_after", "icon_stat",
    "stacked_progress", "card_carousel", "hero_with_context",
    "quote_portrait", "person_card",
  ]).describe("레이아웃 (빈값=자동)"),
  reveal: z.enum([
    "fade_in", "stagger", "stagger_then_flash", "cascade",
    "count_up", "typewriter", "spotlight", "split_reveal",
    "zoom_in", "build_up", "dramatic_pause", "parallel",
  ]).describe("등장 애니메이션"),
  emphasis: z.enum([
    "none", "number", "keyword", "count", "contrast",
    "sequence", "person", "quote",
  ]).describe("텍스트 강조 방식"),
  mood: z.enum([
    "dramatic", "contemplative", "urgent", "triumphant",
    "somber", "informative", "suspense",
  ]).describe("분위기"),

  // ── Visualization 필드 ──
  title: z.string().describe("씬 제목 (차트 제목으로 사용)"),
  items: z.string().describe("아이템 목록 (쉼표 구분)"),
  values: z.string().describe("아이템 값 (쉼표 구분, 숫자)"),
  unit: z.string().describe("값 단위 (%, 원, 억 달러 등)"),
  source: z.string().describe("데이터 출처"),

  // ── 폰트 사이즈 ──
  headlineFontSize: z.number().min(24).max(200).step(2).describe("헤드라인 폰트 크기"),
  itemFontSize: z.number().min(16).max(100).step(2).describe("아이템 폰트 크기"),
  chartTitleFontSize: z.number().min(16).max(100).step(2).describe("차트 제목 폰트 크기"),

  // ── 위치 조절 ──
  contentX: z.number().min(-960).max(960).step(10).describe("콘텐츠 X 오프셋 (좌← →우)"),
  contentY: z.number().min(-540).max(540).step(10).describe("콘텐츠 Y 오프셋 (상← →하)"),
});

export const kairosVideoSchema = z.object({
  manifest: z.any().describe("씬 데이터 (자동 로드)"),
  subtitleConfig: subtitleConfigSchema,
});

export const sceneEditorSchema = z.object({
  manifest: z.any().describe("씬 데이터 (자동 로드)"),
  sceneNumber: z.number().min(1).max(80).describe("씬 번호"),
  subtitleConfig: subtitleConfigSchema,
  override: sceneOverrideSchema,
});

export const vizOnlySchema = z.object({
  manifest: z.any().describe("씬 데이터 (자동 로드)"),
  sceneNumber: z.number().min(1).max(80).describe("씬 번호"),
});

export const vizStillSchema = z.object({
  vizData: z.any().describe("시각화 데이터 (VisualizationData)"),
  designTokens: z.any().optional().describe("디자인 토큰 오버라이드"),
});
