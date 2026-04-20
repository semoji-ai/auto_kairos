import { staticFile } from "remotion";
import { gifManifest } from "./gifManifest";
import { lottieManifest } from "./lottieManifest";

export function resolveOverlayPath(
  type: "gif" | "lottie",
  assetId: string,
): string | null {
  if (type === "gif") {
    const asset = gifManifest.find((a) => a.id === assetId);
    return asset ? staticFile(`overlays/gif/${asset.file}`) : null;
  }
  const asset = lottieManifest.find((a) => a.id === assetId);
  return asset ? staticFile(`overlays/lottie/${asset.file}`) : null;
}
