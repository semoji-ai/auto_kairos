import { staticFile } from "remotion";

/**
 * 에셋 경로를 Remotion staticFile()로 변환
 *
 * 매니페스트의 모든 경로는 public/ 기준 상대경로여야 함.
 * (예: "project/scenes/scene_001.png")
 *
 * ProjectPaths.prepare_remotion()이 절대경로→상대경로 변환과
 * 에셋 심링크를 처리하므로, 여기서는 staticFile()만 호출.
 */
export function resolveAsset(path: string): string {
  if (!path) return "";
  if (path.startsWith("http") || path.startsWith("blob:")) return path;
  return staticFile(path);
}
