import lottieData from "../../public/overlays/lottie/manifest.json";

export interface LottieAsset {
  id: string;
  file: string;
  tags: string[];
  size: { width: number; height: number };
}

export const lottieManifest: LottieAsset[] = lottieData.assets as LottieAsset[];
