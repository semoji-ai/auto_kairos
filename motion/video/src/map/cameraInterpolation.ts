/** 지도 카메라 상태(MapLibre jumpTo 인자) */
export type CameraState = { center: [number, number]; zoom: number; bearing: number; pitch: number };

/** 경위도 → 화면 픽셀(MapLibre tileSize 512 웹 메르카토르). 오버레이·AE 좌표 변환 공용 */
export function lngLatToPixel(lngLat: [number, number], cam: CameraState, width = 1920, height = 1080) {
  const scale = Math.pow(2, cam.zoom) * 512;
  const merc = (lng: number, lat: number) => {
    const r = (lat * Math.PI) / 180;
    return { x: ((lng + 180) / 360) * scale, y: ((1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2) * scale };
  };
  const c = merc(cam.center[0], cam.center[1]), p = merc(lngLat[0], lngLat[1]);
  return { x: width / 2 + (p.x - c.x), y: height / 2 + (p.y - c.y) };
}
