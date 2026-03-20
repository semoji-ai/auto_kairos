import { z } from "zod";

/**
 * Remotion Studio Props Editor용 Zod 스키마
 */

export const subtitleConfigSchema = z.object({
  visible: z.boolean(),
  fontFamily: z.string(),
  fontSize: z.number(),
  fontWeight: z.number(),
  color: z.string(),
  strokeColor: z.string(),
  strokeWidth: z.number(),
  keywordColor: z.string(),
  keywordStrokeColor: z.string(),
  bottomOffset: z.number(),
  maxWidth: z.string(),
  lineHeight: z.number(),
});

export const kairosVideoSchema = z.object({
  manifest: z.any(),
  subtitleConfig: subtitleConfigSchema,
});

export const sceneEditorSchema = z.object({
  manifest: z.any(),
  sceneNumber: z.number().min(1).max(80).describe("씬 번호"),
  subtitleConfig: subtitleConfigSchema,
});

export const vizOnlySchema = z.object({
  manifest: z.any(),
  sceneNumber: z.number().min(1).max(80),
});

export const vizStillSchema = z.object({
  vizData: z.any(),
  designTokens: z.any().optional(),
});
