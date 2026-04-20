import gifData from "../../public/overlays/gif/manifest.json";

export interface GifAsset {
  id: string;
  file: string;
  tags: string[];
  duration_sec: number;
  size: { width: number; height: number };
  loop: boolean;
}

export const gifManifest: GifAsset[] = gifData.assets as GifAsset[];
