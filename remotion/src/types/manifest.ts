/**
 * Scene Manifest - Python 파이프라인과 Remotion 사이의 인터페이스 계약
 *
 * Python의 RemotionBridge가 이 스키마의 JSON을 생성하고,
 * Remotion의 KairosVideo 컴포지션이 이를 소비합니다.
 */

import type { DesignPresetOverride } from "../design/types";

export interface DesignTokens {
  style?: {
    background?: string;
    border?: string;
    text?: string;
    subtitle?: string;
    source?: string;
    grid?: string;
    colors?: string[];
    gradients?: [string, string][];
    cardBg?: string;
    cardShadow?: string;
    cardRadius?: number;
    accentIndex?: number;
    semantic?: {
      positive?: string;
      positiveBg?: string;
      negative?: string;
      negativeBg?: string;
    };
  };
  typo?: {
    title?: { size?: number; weight?: number; letterSpacing?: string };
    hero?: { size?: number; weight?: number; letterSpacing?: string };
    subtitle?: { size?: number; weight?: number };
    label?: { size?: number; weight?: number };
    value?: { size?: number; weight?: number };
    caption?: { size?: number; weight?: number };
  };
  layout?: {
    topMargin?: number;
    sourceHeight?: number;
    titleHeight?: number;
    subtitleHeight?: number;
    chartHeight?: number;
    safeZoneHeight?: number;
    sidePadding?: number;
  };
  vizFont?: string;
  vizTitleFont?: string;
}

export interface SceneManifest {
  meta: {
    topic: string;
    resolution: { width: number; height: number };
    fps: number;
    subtitleFont: string;
    vizFont: string;
    designTokens?: DesignTokens;
    /** 비디오 테마 ("dark" = 다크 기본, "white" = 화이트 라이트) */
    videoTheme?: "dark" | "white";
    /** 아트스타일 (accent 색상 결정) */
    artStyle?: string;
    /** 디자인 프리셋 오버라이드 (아트스타일 기본값 위에 덮어씀) */
    designPreset?: DesignPresetOverride;
  };
  scenes: SceneEntry[];
  bgm: BGMConfig | null;
}

/** 캔버스 에디터 오버라이드 — 프리미어 스타일 직접 조작용 */
export interface CanvasOverrides {
  headline?: {
    x: number;      // 0~1920 (캔버스 좌표)
    y: number;      // 0~1080
    fontSize: number; // px
    width?: number;   // px (텍스트 박스 폭)
  };
  image?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
}

export interface SceneEntry {
  sceneNumber: number;
  imagePath: string;
  audioPath: string;
  audioDurationSec: number;

  subtitles: SubtitleEntry[];

  visualization: VisualizationData | null;

  kenBurns: KenBurnsConfig;
  transition: TransitionConfig;
  vizAnimation?: VizAnimationConfig;

  /** "contain" → 원본 비율 유지 + 그리드 배경 (레퍼런스 씬용) */
  imageMode?: "cover" | "contain";

  /** 이미지 에셋 배치 정보 (placement + opacity) */
  imageAsset?: {
    placement: "fullscreen" | "background" | "center" | "left" | "right" | "inline";
    opacity: number;
    itemImages?: boolean;
  };

  /** 캔버스 에디터 오버라이드 (프리미어 스타일 직접 조작) */
  overrides?: CanvasOverrides;

  /** 시각화 씬의 아트스타일 배경 이미지 경로 (하이브리드 viz) */
  vizBackgroundPath?: string;

  /** 예고편/영상 클립 경로 (mp4) */
  trailerVideoPath?: string;
  /** 예고편 구간 지정 */
  trailerClip?: { startSec: number; endSec: number };

  /** 지도 씬 데이터 (위치/경로/영역/플라이스루) */
  mapScene?: MapSceneData | null;

  /** GIF/Lottie 오버레이 목록 */
  overlays?: OverlayItem[];
}

export interface SubtitleEntry {
  text: string;
  startSec: number;
  endSec: number;
  keywords?: string[];
  words?: { word: string; start: number; end: number }[];
}

export interface CreativeDirection {
  concept: string;
  layout?: string;
  reveal: "fade_in" | "stagger" | "stagger_then_flash" | "cascade" | "count_up"
    | "typewriter" | "spotlight" | "split_reveal" | "zoom_in" | "build_up"
    | "dramatic_pause" | "parallel";
  emphasis: "number" | "keyword" | "count" | "contrast" | "sequence"
    | "person" | "quote" | "none";
  headline: string;
  mood: "dramatic" | "contemplative" | "urgent" | "triumphant"
    | "somber" | "informative" | "suspense";
}

export interface CinematicOverlay {
  type: "speech_bubble" | "emotion" | "caption";
  text: string;
  position: "top_left" | "top_right" | "bottom_left" | "bottom_right" | "center";
}

export interface VisualizationData {
  /** 시각화 타입 힌트 (optional — 렌더링은 creative 필드 기반) */
  vizType?: string;
  title: string;
  items: string[];
  values: number[];
  unit: string;
  source: string;
  imagePath?: string | { left: string; right: string };
  left?: { label: string; items: string[] };
  right?: { label: string; items: string[] };
  relations?: string[];       // tech_tree: 각 노드와 부모의 관계
  descriptions?: string[];    // tech_tree/slide_profile/slide_definition 등: 부가 설명
  profileName?: string;       // slide_profile: 인물/개체 이름
  profileSubtitle?: string;   // slide_profile: 직함/부제
  /** Creative Direction v4.0 — 씬별 창의적 연출 */
  creative?: CreativeDirection;
  /** 시네마틱 씬 오버레이 (말풍선/감탄부호/캡션) */
  cinematicOverlay?: CinematicOverlay;
  /** 챕터 번호/라벨 (title_card 등) */
  chapter?: string;
  /** 단일 값 (slide_bignum, icon_stat 등) */
  value?: string | number;
  /** 부제 (impact_count 등) */
  subtitle?: string;
}

/* ── 지도 씬 타입 ───────────────────────────────── */

export interface CameraKeyframe {
  frame: number;
  center: [number, number];  // [lng, lat]
  zoom: number;
  bearing?: number;           // 회전 (기본 0)
  pitch?: number;             // 기울기 (기본 0)
}

export interface MapMarker {
  coordinates: [number, number];
  label: string;
  style?: "pin" | "dot" | "pulse";
  appearAtFrame?: number;
  labelPosition?: "top" | "bottom" | "left" | "right";
}

export interface RouteData {
  coordinates: [number, number][];
  color?: string;
  width?: number;
  drawDurationFrames?: number;
  style?: "solid" | "dashed";
}

export interface TerritoryData {
  geojsonPath?: string;
  geojsonInline?: Record<string, unknown>;
  fillColor: string;
  fillOpacity: number;
  strokeColor?: string;
  label?: string;
  appearAtFrame?: number;
  fadeInFrames?: number;
}

export interface MapLabel {
  coordinates: [number, number];
  text: string;
  fontSize?: number;
  color?: string;
  appearAtFrame?: number;
}

export interface MapSceneData {
  mapType: "location_reveal" | "route_animation" | "territory_overlay" | "fly_through";
  mapStyle?: "modern_clean" | "historical" | "dark_cyber" | "satellite"
    | "vintage_parchment" | "minimal_light" | "dark_elegant" | "blueprint"
    | "warm_earth" | "matte_slate" | "clean_white";
  title?: string;
  source?: string;

  camera: {
    keyframes: CameraKeyframe[];
    easing?: string;
  };

  markers?: MapMarker[];
  route?: RouteData;
  territories?: TerritoryData[];
  labels?: MapLabel[];

  /** 프리렌더 프레임 디렉토리 (예: "map_frames/scene_5") — staticFile 기준 상대경로 (레거시) */
  prerenderedFramesDir?: string;

  /** 프리렌더 배경 이미지 (씬당 1장 고해상도 스크린샷) */
  prerenderedBg?: {
    /** 배경 이미지 경로 (staticFile 기준 상대경로, 예: "map_frames/scene_5/bg.png") */
    imagePath: string;
    /** 스크린샷 캡처 시점의 카메라 상태 */
    cameraState: {
      center: [number, number];
      zoom: number;
      bearing: number;
      pitch: number;
    };
  };
}

export interface KenBurnsConfig {
  enabled: boolean;
  zoomFactor: number;
  zoomDirection?: "in" | "out";
  panDirection?: "none" | "left" | "right" | "up" | "down";
  panX?: number;
  panY?: number;
  easing?: string;
}

export interface TransitionConfig {
  type: "crossfade" | "cut" | "fade" | "slide" | "wipe"
    | "slide_left" | "slide_right" | "wipe_left" | "wipe_right";
  durationFrames: number;
  easing?: string;
}

export interface VizAnimationConfig {
  stagger?: number;
  itemDuration?: number;
  easing?: string;
  titleFadeIn?: number;
  titleSlideUp?: number;
  itemSyncPoints?: {
    itemIndex?: number;
    label?: string;
    startSec?: number;
    timeSec?: number;
  }[];
  exitFadeOut?: number;
  exitDirection?: "down" | "up" | "scale";
}

export interface SubtitleConfig {
  visible: boolean;
  fontFamily: string;
  fontSize: number;           // px (기본 44)
  fontWeight: number;         // 기본 700
  color: string;              // 텍스트 색상 (기본 white)
  strokeColor: string;        // 외곽선 색상 (기본 #3D3B2F)
  strokeWidth: number;        // 외곽선 두께 px (기본 2)
  keywordColor: string;       // 키워드 하이라이트 색상 (기본 #F7D94C)
  keywordStrokeColor: string; // 키워드 외곽선 색상 (기본 #5A4B00)
  bottomOffset: number;       // 하단 오프셋 px (기본 30)
  maxWidth: string;           // 최대 너비 (기본 "85%")
  lineHeight: number;         // 줄간격 (기본 1.5)
}

export interface OverlayItem {
  type: "gif" | "lottie";
  assetId: string;
  position:
    | "top-left"
    | "top-right"
    | "bottom-left"
    | "bottom-right"
    | "bottom-center"
    | "center"
    | "custom";
  x?: number;
  y?: number;
  scale?: number;
  opacity?: number;
  enterFrame?: number;
  exitFrame?: number;
  loop?: boolean;
}

export interface BGMConfig {
  path: string;
  volume: number;
  loop: boolean;
}
