/**
 * 씬 렌더러 v4 — Creative Direction 기반
 *
 * 모든 시각화는 creative 필드 + 데이터 구조로 CreativeScene이 자동 결정.
 * vizType 레거시 코드 완전 제거됨.
 *
 * 라우팅 흐름:
 * 1. 데이터 없음 → Bridge (안전 폴백)
 * 2. chapter 필드 → TitleCard
 * 3. normalizeCreative(): creative 필드 보완 (불완전 시 데이터에서 추론)
 * 4. inferChartType(): timeline/compare/table/diagram 전용 렌더러
 * 5. 나머지 → CreativeScene (자동 레이아웃 감지)
 */
import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  Easing,
  staticFile,
} from "remotion";
import { CreativeScene } from "./CreativeScene";

/* ---------- BuildingBlocks re-export (하위 호환성) ---------- */
export {
  C, FONT, ease, clamp,
  useFadeRise, useFadeSlide, useFade, useScale, useLineExpand, useCountUp,
  useOvershootScale, useBounceIn, useShake, usePulse, useGlitch, useTypewriter, useFadeOut, useSpringValue,
  staggerDelay,
  AccentText, Card, Pill, CircleBadge, ImageBadge,
  Icon, IconBadge, FlagBadge, LogoBadge, ProgressBar, Tag, Divider, StatusDot,
  extractNumber, formatWithTemplate, resolveIcon, resolveLogo,
} from "./BuildingBlocks";

import {
  C, FONT, ease, clamp,
  useFadeRise, useFadeSlide, useFade, useScale, useLineExpand, useCountUp,
  AccentText, Card, Pill, CircleBadge, ImageBadge,
  extractNumber, formatWithTemplate,
} from "./BuildingBlocks";

/* ---------- Chart inference: creative 필드 + 데이터 구조 기반 ---------- */

/**
 * creative 필드 + 데이터 구조로 차트 타입 추론.
 * creative 필드 + 데이터 구조로 자연스럽게 차트 컴포넌트 선택.
 */
function inferChartType(data: any, creative: any): string | null {
  if (!creative || !data) return null;
  const emphasis: string = creative.emphasis || "none";
  const reveal: string = creative.reveal || "fade_in";
  const items: string[] = data.items || [];
  const descriptions: string[] = data.descriptions || [];

  // 0. chartConfig.type 명시적 지정 — CreativeScene 내부에서 처리하므로 null 반환
  if (creative.chartConfig?.type === "pie" || creative.chartConfig?.type === "line") return null;

  // 0.5. displayMode 명시적 지정 — CreativeScene 내부에서 처리
  if (creative.displayMode) return null;

  // 1. Timeline: 순서/과정 강조 + 설명 데이터
  if (emphasis === "sequence" && descriptions.length > 0) return "timeline";

  // 2. Compare: 대비 강조 + 좌우 데이터
  if ((emphasis === "contrast" || reveal === "split_reveal") &&
      (data.left || data.right)) return "compare";

  // 3. Table: 파이프 구분 데이터
  if (items.length > 1 && items.some((i: string) => i.includes("|"))) return "table";

  // 4. Diagram: 관계/프로세스 데이터
  if (items.length > 1 && data.relations?.length > 0) return "diagram";

  // 차트 아님 → CreativeScene이 처리
  return null;
}

/* ---------- Creative 보완 (normalizeCreative) ---------- */

/**
 * creative 필드가 없거나 불완전할 때, 데이터 구조에서 합리적 기본값을 자동 생성.
 * visual-composer가 제대로 분석하지 못한 씬도 CreativeScene에서 렌더링 가능하도록 보완.
 */
function normalizeCreative(data: any): any {
  const viz = data || {};
  const creative = { ...(viz.creative || {}) };

  // headline 보완: creative.headline 없으면 title에서
  if (!creative.headline) {
    creative.headline = viz.title || "";
  }

  // emphasis 보완: 데이터 패턴에서 추론
  if (!creative.emphasis) {
    if (viz.values?.length >= 1 && (viz.items?.length || 0) <= 2) {
      creative.emphasis = "number";
    } else {
      creative.emphasis = "none";
    }
  }

  // reveal 보완: items 수 기반
  if (!creative.reveal) {
    creative.reveal = (viz.items?.length || 0) >= 3 ? "stagger" : "fade_in";
  }

  // mood 보완
  if (!creative.mood) {
    creative.mood = "informative";
  }

  return { ...viz, creative };
}

/* ---------- Router ---------- */

interface SubtitleEntry {
  text: string;
  startSec: number;
  endSec: number;
}

interface Props {
  data: any;
  sceneNumber: number;
  durationInFrames: number;
  subtitles?: SubtitleEntry[];
  hasImageBackground?: boolean;
  imageAssetPlacement?: "background" | "left" | "right";
}

export const SimpleScene: React.FC<Props> = ({ data, sceneNumber, durationInFrames, subtitles, hasImageBackground, imageAssetPlacement }) => {
  const scene = (() => {
    // 데이터 없음 → 안전 폴백
    if (!data || (!data.creative && !data.title && !data.items?.length)) {
      return <Bridge text={data?.title || ""} />;
    }

    // TitleCard: chapter 필드가 있으면 타이틀 카드
    if (data.chapter) {
      return <TitleCard data={data} />;
    }

    // creative 보완: 불완전한 creative 필드를 데이터 구조에서 자동 생성
    const normalized = normalizeCreative(data);
    const creative = normalized.creative;

    // 차트 타입 추론 (timeline/compare/table/diagram)
    const chartType = inferChartType(normalized, creative);
    if (chartType) {
      switch (chartType) {
        case "timeline":  return <TimelineScene data={normalized} />;
        case "compare":   return <CompareScene data={normalized} />;
        case "table":     return <TableScene data={normalized} />;
        case "diagram":   return <DiagramScene data={normalized} />;
      }
    }

    // 나머지 모든 씬 → CreativeScene (자동 레이아웃 감지)
    return <CreativeScene data={normalized} subtitles={subtitles} fps={30} hasImageBackground={hasImageBackground} imageAssetPlacement={imageAssetPlacement} />;
  })();

  // 이미지 배경이 있을 때: 배경 투명 + 전체 폭 사용
  // 이미지 배경이 없을 때: 기존 방식 (검정 배경 + 78% 폭)
  const useFullWidth = hasImageBackground && !!data?.creative;

  // 이미지 에셋 배치에 따른 컨텐츠 영역 조정
  // left/right 에셋: SideImageLayout이 flex row를 잡아주므로 여기서는 100% 사용
  const hasAssetSide = imageAssetPlacement === "left" || imageAssetPlacement === "right";
  const contentStyle: React.CSSProperties = hasAssetSide
    ? {
        width: "100%",
        height: "100%",
        position: "relative" as const,
      }
    : {
        width: useFullWidth ? "100%" : "78%",
        height: "100%",
        margin: "0 auto",
        position: "relative" as const,
      };

  return (
    <AbsoluteFill style={{ backgroundColor: hasImageBackground ? "transparent" : C.bg, fontFamily: FONT }}>
      <div style={contentStyle}>
        {scene}
      </div>
    </AbsoluteFill>
  );
};

/* ====================================================================
   1. Title Card — title_card
   챕터/섹션 시작. 큰 챕터 번호 + 타이틀 + 서브타이틀
   ==================================================================== */

const TitleCard: React.FC<{ data: any }> = ({ data }) => {
  const chapter = data.chapter || "";
  const title = data.title || "";
  const subtitle = data.items?.[0] || "";
  const line = useLineExpand(5, 30, 160);
  const chapFade = useFadeRise(3, 15, 10);
  const titleFade = useFadeRise(12, 25, 30);
  const subFade = useFadeRise(28, 20, 15);
  const dotScale = useScale(0, 15);

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: "80px 0",
      }}
    >
      {/* 챕터가 있을 때만 장식 도트 + 라인 표시 */}
      {chapter && (
        <>
          <div
            style={{
              ...dotScale,
              width: 10,
              height: 10,
              borderRadius: 5,
              backgroundColor: C.accent,
              marginBottom: 28,
            }}
          />
          <div
            style={{
              ...chapFade,
              fontSize: 36,
              fontWeight: 600,
              color: C.accent,
              letterSpacing: "0.15em",
              textTransform: "uppercase",
              marginBottom: 16,
            }}
          >
            {chapter}
          </div>
          <div
            style={{
              width: line,
              height: 3,
              backgroundColor: C.accent,
              marginBottom: 32,
            }}
          />
        </>
      )}

      {/* 메인 타이틀 */}
      <div
        style={{
          ...titleFade,
          fontSize: 124,
          fontWeight: 800,
          color: C.text,
          textAlign: "center",
          lineHeight: 1.2,
          letterSpacing: "-0.02em",
        }}
      >
        {title}
      </div>

      {/* 서브타이틀 */}
      {subtitle && (
        <div
          style={{
            ...subFade,
            fontSize: 48,
            fontWeight: 400,
            color: C.textMuted,
            textAlign: "center",
            marginTop: 24,
            lineHeight: 1.4,
          }}
        >
          {subtitle}
        </div>
      )}
    </div>
  );
};

/* ====================================================================
   2. Center Impact — slide_highlight
   컨텍스트(뮤트) 위 → 히어로 텍스트(볼드) → 원형 장식
   ==================================================================== */

const Highlight: React.FC<{ data: any }> = ({ data }) => {
  const heroText: string = data.items?.[0] || data.title || "";
  const contextText: string | null = data.items?.[0] ? (data.title || null) : null;
  const line = useLineExpand(8, 25, 80);
  const ctx = useFadeRise(5, 18, 15);
  const hero = useFadeRise(16, 22, 30);
  const src = useFade(50, 15, 0.8);

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: "80px 0",
      }}
    >
      {contextText && (
        <div
          style={{
            ...ctx,
            fontSize: 44,
            fontWeight: 400,
            color: C.textMuted,
            marginBottom: 20,
            letterSpacing: "0.02em",
          }}
        >
          {contextText}
        </div>
      )}

      <div
        style={{
          width: line,
          height: 3,
          backgroundColor: C.accent,
          marginBottom: 32,
        }}
      />

      {/* 히어로 텍스트 — {{}} 마크업으로 강조 컬러 적용 */}
      <div
        style={{
          ...hero,
          fontSize: 116,
          fontWeight: 800,
          textAlign: "center",
          lineHeight: 1.3,
          letterSpacing: "-0.02em",
        }}
      >
        <AccentText text={heroText} />
      </div>

      {data.source && (
        <div
          style={{
            position: "absolute",
            bottom: 80,
            right: 0,
            fontSize: 36,
            fontWeight: 400,
            color: C.textDim,
            opacity: src,
          }}
        >
          {data.source}
        </div>
      )}
    </div>
  );
};

/* ====================================================================
   3. Big Number — slide_bignum
   카운팅 애니메이션 + 큰 숫자 강조 + 라벨
   ==================================================================== */

const BigNumber: React.FC<{ data: any }> = ({ data }) => {
  const frame = useCurrentFrame();
  const rawValue = data.value || data.items?.[0] || "0";
  const numericTarget = extractNumber(String(rawValue));
  const label = data.title || "";
  const sublabel = data.items?.[1] || data.source || "";
  const unit = data.unit || "";

  const countedValue = useCountUp(12, 40, numericTarget);
  const formatted = formatWithTemplate(String(rawValue), countedValue);

  const labelFade = useFadeRise(0, 18, 15);
  const numFade = useFadeRise(8, 25, 40);
  const subFade = useFadeRise(40, 20, 15);
  const line = useLineExpand(5, 25, 60);

  // 숫자 글로우 효과
  const glowOpacity = interpolate(frame, [20, 50], [0, 0.4], clamp);

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: "80px 0",
      }}
    >
      {/* 라벨 (위) */}
      {label && (
        <div
          style={{
            ...labelFade,
            fontSize: 44,
            fontWeight: 400,
            color: C.textMuted,
            marginBottom: 20,
            letterSpacing: "0.02em",
            textAlign: "center",
          }}
        >
          {label}
        </div>
      )}

      {/* 라인 */}
      <div
        style={{
          width: line,
          height: 3,
          backgroundColor: C.accent,
          marginBottom: 36,
        }}
      />

      {/* 큰 숫자 + 카운팅 */}
      <div
        style={{
          ...numFade,
          fontSize: 165,
          fontWeight: 800,
          color: C.accent,
          textAlign: "center",
          lineHeight: 1.0,
          letterSpacing: "-0.03em",
          textShadow: `0 0 60px rgba(245,158,11,${glowOpacity})`,
        }}
      >
        {formatted}
        {unit && (
          <span style={{ fontSize: 88, fontWeight: 600, marginLeft: 8 }}>
            {unit}
          </span>
        )}
      </div>

      {/* 서브 라벨 (아래) */}
      {sublabel && (
        <div
          style={{
            ...subFade,
            fontSize: 48,
            fontWeight: 500,
            color: C.textMuted,
            marginTop: 28,
            textAlign: "center",
            lineHeight: 1.4,
          }}
        >
          {sublabel}
        </div>
      )}
    </div>
  );
};

/* ====================================================================
   4. Quote — 인용문 레이아웃
   좌측 액센트 보더 카드 안에 인용문
   ==================================================================== */

const Quote: React.FC<{ data: any }> = ({ data }) => {
  const text = data.items?.[0] || data.title;
  const cardFade = useFade(5, 20);
  const quote = useFadeRise(12, 25, 20);
  const src = useFade(45, 15, 0.8);

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        padding: "80px 0",
      }}
    >
      <div
        style={{
          opacity: cardFade,
          borderLeft: `4px solid ${C.accent}`,
          backgroundColor: C.cardBg,
          borderRadius: "0 12px 12px 0",
          padding: "48px 44px",
        }}
      >
        <div
          style={{
            fontSize: 120,
            fontWeight: 800,
            color: C.accent,
            lineHeight: 0.8,
            marginBottom: 20,
          }}
        >
          &ldquo;
        </div>

        <div
          style={{
            ...quote,
            fontSize: 88,
            fontWeight: 700,
            color: C.text,
            lineHeight: 1.35,
            letterSpacing: "-0.01em",
          }}
        >
          {text}
        </div>

        {data.source && (
          <div
            style={{
              opacity: src,
              fontSize: 40,
              fontWeight: 400,
              color: C.textMuted,
              marginTop: 32,
            }}
          >
            — {data.source}
          </div>
        )}
      </div>
    </div>
  );
};

/* ====================================================================
   5. List — slide_list
   카드 기반 리스트, 이미지 배지 or 번호 배지 + 텍스트
   ==================================================================== */

const ListScene: React.FC<{ data: any }> = ({ data }) => {
  const items: string[] = data.items || [];
  const images: (string | null)[] = data.images || [];
  const title = useFadeRise(0, 20, 15);
  const STAGGER = 8;

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        padding: "80px 0",
      }}
    >
      <div
        style={{
          ...title,
          fontSize: 88,
          fontWeight: 800,
          color: C.text,
          letterSpacing: "-0.01em",
          marginBottom: 40,
        }}
      >
        {data.title}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {items.map((item, i) => {
          const delay = 18 + i * STAGGER;
          const s = useFadeSlide(delay, 15, 25);
          const hasImage = images[i];
          return (
            <div key={i} style={{ ...s }}>
              <Card style={{ display: "flex", alignItems: "center", gap: 20 }}>
                {hasImage ? (
                  <ImageBadge imageUrl={images[i]!} size={42} />
                ) : (
                  <CircleBadge text={String(i + 1)} size={36} filled />
                )}
                <div style={{ fontSize: 48, fontWeight: 500, color: C.text, lineHeight: 1.4 }}>
                  {item}
                </div>
              </Card>
            </div>
          );
        })}
      </div>
    </div>
  );
};

/* ====================================================================
   6. Numbered List — slide_numbered
   스텝 카드 (번호 배지 + 제목 + 설명)
   ==================================================================== */

const NumberedListScene: React.FC<{ data: any }> = ({ data }) => {
  const items: string[] = data.items || [];
  const descs: string[] = data.descriptions || [];
  const title = useFadeRise(0, 20, 15);
  const STAGGER = 10;

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        padding: "80px 0",
      }}
    >
      <div
        style={{
          ...title,
          fontSize: 88,
          fontWeight: 800,
          color: C.text,
          marginBottom: 40,
        }}
      >
        {data.title}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {items.map((item, i) => {
          const s = useFadeSlide(16 + i * STAGGER, 15, 25);
          return (
            <div key={i} style={{ ...s }}>
              <Card style={{ display: "flex", alignItems: "flex-start", gap: 20 }}>
                <CircleBadge
                  text={String(i + 1)}
                  size={40}
                  filled
                  style={{ marginTop: 2 }}
                />
                <div>
                  <div style={{ fontSize: 48, fontWeight: 600, color: C.text, lineHeight: 1.4 }}>
                    {item}
                  </div>
                  {descs[i] && (
                    <div style={{ fontSize: 36, fontWeight: 400, color: C.textMuted, marginTop: 6 }}>
                      {descs[i]}
                    </div>
                  )}
                </div>
              </Card>
            </div>
          );
        })}
      </div>
    </div>
  );
};

/* ====================================================================
   7. Bar Chart — 두꺼운 바 + 카운팅 숫자
   ==================================================================== */

const BarChartScene: React.FC<{ data: any }> = ({ data }) => {
  const frame = useCurrentFrame();
  const labels: string[] = data.items || [];
  const values: number[] = (data.values || []).map(Number);
  const maxVal = Math.max(...values, 1);
  const title = useFadeRise(0, 20, 15);
  const src = useFade(50, 15, 0.8);

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        padding: "80px 0",
      }}
    >
      <div style={{ ...title, fontSize: 88, fontWeight: 800, color: C.text, marginBottom: 44 }}>
        {data.title}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
        {labels.map((label, i) => {
          const delay = 15 + i * 10;
          const barProgress = interpolate(frame, [delay, delay + 35], [0, 1], {
            ...clamp,
            easing: Easing.out(Easing.exp),
          });
          const pct = (values[i] / maxVal) * 100;
          const labelFade = useFade(delay, 12);

          // 카운팅 애니메이션 (바 차트는 0부터)
          const countVal = useCountUp(delay, 35, values[i], 0);
          const formatted = values[i] >= 1000
            ? countVal.toLocaleString()
            : String(countVal);

          return (
            <div key={i} style={{ opacity: labelFade }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
                <span style={{ fontSize: 44, fontWeight: 500, color: C.text }}>{label}</span>
                <span style={{ fontSize: 56, fontWeight: 800, color: C.accent }}>
                  {formatted}{data.unit ? ` ${data.unit}` : ""}
                </span>
              </div>
              <div
                style={{
                  height: 24,
                  backgroundColor: C.cardBg,
                  borderRadius: 12,
                  overflow: "hidden",
                  border: `1px solid ${C.divider}`,
                }}
              >
                <div
                  style={{
                    height: "100%",
                    width: `${pct * barProgress}%`,
                    backgroundColor: C.accent,
                    borderRadius: 12,
                    boxShadow: `0 0 20px rgba(245,158,11,0.3)`,
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {data.source && (
        <div style={{ position: "absolute", bottom: 80, right: 0, fontSize: 36, color: C.textDim, opacity: src }}>
          {data.source}
        </div>
      )}
    </div>
  );
};

/* ====================================================================
   8. Timeline
   세로 라인 + 액센트 원형 노드 + 카드
   ==================================================================== */

const TimelineScene: React.FC<{ data: any }> = ({ data }) => {
  const frame = useCurrentFrame();
  const items: string[] = data.items || [];
  const descs: string[] = data.descriptions || [];
  const title = useFadeRise(0, 20, 15);
  const STAGGER = 8;

  const lineH = interpolate(frame, [10, 10 + items.length * STAGGER + 20], [0, 100], {
    ...clamp,
    easing: ease,
  });

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        padding: "80px 0",
      }}
    >
      <div style={{ ...title, fontSize: 88, fontWeight: 800, color: C.text, marginBottom: 40 }}>
        {data.title}
      </div>

      <div style={{ position: "relative", paddingLeft: 56 }}>
        <div
          style={{
            position: "absolute",
            left: 11,
            top: 0,
            width: 2,
            height: `${lineH}%`,
            backgroundColor: C.accentBorder,
          }}
        />

        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {items.map((item, i) => {
            const delay = 14 + i * STAGGER;
            const s = useFadeSlide(delay, 15, 20);
            return (
              <div key={i} style={{ ...s, position: "relative" }}>
                <div
                  style={{
                    position: "absolute",
                    left: -50,
                    top: 14,
                    width: 12,
                    height: 12,
                    borderRadius: 6,
                    backgroundColor: C.accent,
                    border: `2px solid ${C.bg}`,
                    boxShadow: `0 0 0 2px ${C.accent}`,
                  }}
                />
                <Card>
                  {descs[i] && (
                    <div style={{ fontSize: 34, fontWeight: 700, color: C.accent, marginBottom: 6, letterSpacing: "0.02em" }}>
                      {descs[i]}
                    </div>
                  )}
                  <div style={{ fontSize: 44, fontWeight: 500, color: C.text, lineHeight: 1.4 }}>
                    {item}
                  </div>
                </Card>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

/* ====================================================================
   9. Compare — Split (이미지 배지 지원)
   X/체크 or 이미지 원형 아이콘 + 좌우 카드 + 세로 구분선
   ==================================================================== */

const CompareScene: React.FC<{ data: any }> = ({ data }) => {
  const left = data.left || { label: "", items: [] };
  const right = data.right || { label: "", items: [] };
  const leftImage = data.leftImage || null;
  const rightImage = data.rightImage || null;
  const title = useFadeRise(0, 20, 15);
  const leftScale = useScale(10, 20);
  const rightScale = useScale(18, 20);

  // 양쪽 대칭: 명시적 icon이 없으면 라벨 첫 글자 사용 (중립)
  const leftIcon = left.icon || (left.label ? left.label[0] : "A");
  const rightIcon = right.icon || (right.label ? right.label[0] : "B");

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        padding: "80px 0",
      }}
    >
      <div style={{ ...title, fontSize: 88, fontWeight: 800, color: C.text, marginBottom: 40, textAlign: "center" }}>
        {data.title}
      </div>

      <div style={{ display: "flex", gap: 24 }}>
        {/* 좌측 */}
        <div style={{ flex: 1, ...leftScale }}>
          <Card style={{ height: "100%", textAlign: "center" }}>
            {leftImage ? (
              <ImageBadge imageUrl={leftImage} size={56} style={{ margin: "0 auto 16px" }} />
            ) : (
              <div
                style={{
                  width: 52,
                  height: 52,
                  borderRadius: 26,
                  border: `2px solid ${C.accent}66`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  margin: "0 auto 16px",
                  fontSize: 40,
                  fontWeight: 700,
                  color: C.accent,
                }}
              >
                {leftIcon}
              </div>
            )}
            <div style={{ fontSize: 44, fontWeight: 700, color: C.text, marginBottom: 16 }}>
              {left.label}
            </div>
            {(left.items || []).map((item: string, i: number) => {
              const s = useFadeRise(22 + i * 6, 12, 10);
              return (
                <div key={i} style={{ ...s, fontSize: 40, fontWeight: 400, color: C.textMuted, lineHeight: 1.6, marginBottom: 4 }}>
                  {item}
                </div>
              );
            })}
          </Card>
        </div>

        {/* 세로 구분선 */}
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
          <div style={{ width: 1, flex: 1, backgroundColor: C.divider }} />
        </div>

        {/* 우측 */}
        <div style={{ flex: 1, ...rightScale }}>
          <Card style={{ height: "100%", textAlign: "center" }}>
            {rightImage ? (
              <ImageBadge imageUrl={rightImage} size={56} style={{ margin: "0 auto 16px" }} />
            ) : (
              <div
                style={{
                  width: 52,
                  height: 52,
                  borderRadius: 26,
                  border: `2px solid ${C.accent}66`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  margin: "0 auto 16px",
                  fontSize: 40,
                  fontWeight: 700,
                  color: C.accent,
                }}
              >
                {rightIcon}
              </div>
            )}
            <div style={{ fontSize: 44, fontWeight: 700, color: C.text, marginBottom: 16 }}>
              {right.label}
            </div>
            {(right.items || []).map((item: string, i: number) => {
              const s = useFadeRise(28 + i * 6, 12, 10);
              return (
                <div key={i} style={{ ...s, fontSize: 40, fontWeight: 400, color: C.textMuted, lineHeight: 1.6, marginBottom: 4 }}>
                  {item}
                </div>
              );
            })}
          </Card>
        </div>
      </div>
    </div>
  );
};

/* ====================================================================
   10. Table
   카드 행 스타일, 첫 열 accent
   ==================================================================== */

const TableScene: React.FC<{ data: any }> = ({ data }) => {
  const items: string[] = data.items || [];
  const rows = items.map((row: string) => row.split("|").map((c: string) => c.trim()));
  const title = useFadeRise(0, 20, 15);
  const STAGGER = 8;

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        padding: "80px 0",
      }}
    >
      <div style={{ ...title, fontSize: 88, fontWeight: 800, color: C.text, marginBottom: 36 }}>
        {data.title}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {rows.map((cells: string[], ri: number) => {
          const s = useFadeSlide(14 + ri * STAGGER, 15, 20);
          return (
            <div key={ri} style={{ ...s }}>
              <Card
                style={{
                  display: "flex",
                  padding: "16px 24px",
                  borderColor: ri === 0 ? C.accent : C.cardBorder,
                }}
              >
                {cells.map((cell: string, ci: number) => (
                  <div
                    key={ci}
                    style={{
                      flex: 1,
                      fontSize: 40,
                      fontWeight: ci === 0 ? 700 : 400,
                      color: ci === 0 ? C.accent : C.text,
                      lineHeight: 1.5,
                    }}
                  >
                    {cell}
                  </div>
                ))}
              </Card>
            </div>
          );
        })}
      </div>
    </div>
  );
};

/* ====================================================================
   11. Statistic — 이미지/실루엣 배지 + 카운팅 숫자
   인물/통계 카드 (이미지 원형 배지 + 이름 + 값)
   ==================================================================== */

const StatisticScene: React.FC<{ data: any }> = ({ data }) => {
  const frame = useCurrentFrame();
  const items: string[] = data.items || [];
  const values: string[] = (data.values || []).map(String);
  const images: (string | null)[] = data.images || [];
  const title = useFadeRise(0, 20, 15);
  const STAGGER = 10;

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: "80px 0",
      }}
    >
      <div style={{ ...title, fontSize: 88, fontWeight: 800, color: C.text, marginBottom: 48, textAlign: "center" }}>
        {data.title}
      </div>

      <div style={{ display: "flex", gap: 24, justifyContent: "center", flexWrap: "wrap" }}>
        {items.map((item, i) => {
          const s = useScale(14 + i * STAGGER, 20);
          const hasImage = images[i];
          return (
            <div key={i} style={{ ...s }}>
              <Card style={{ textAlign: "center", minWidth: 160, borderColor: i === 0 ? C.accent : C.cardBorder }}>
                {hasImage ? (
                  <ImageBadge imageUrl={images[i]!} size={56} style={{ margin: "0 auto 16px" }} />
                ) : (
                  <CircleBadge
                    text={item.charAt(0)}
                    size={56}
                    filled={i === 0}
                    style={{ margin: "0 auto 16px" }}
                  />
                )}
                <div
                  style={{
                    fontSize: 56,
                    fontWeight: 800,
                    color: i === 0 ? C.accent : C.text,
                    letterSpacing: "-0.01em",
                    marginBottom: 8,
                  }}
                >
                  {item}
                </div>
                {values[i] && (
                  <div style={{ fontSize: 34, fontWeight: 400, color: C.textMuted }}>
                    {values[i]}
                  </div>
                )}
              </Card>
            </div>
          );
        })}
      </div>
    </div>
  );
};

/* ====================================================================
   12. Process — 수평 플로우
   번호 원형 배지 + 카드 + 화살표 연결
   ==================================================================== */

const ProcessScene: React.FC<{ data: any }> = ({ data }) => {
  const items: string[] = data.items || [];
  const descs: string[] = data.descriptions || [];
  const title = useFadeRise(0, 20, 15);
  const STAGGER = 8;

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        padding: "80px 0",
      }}
    >
      <div style={{ ...title, fontSize: 88, fontWeight: 800, color: C.text, marginBottom: 40 }}>
        {data.title}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {items.map((item, i) => {
          const delay = 16 + i * STAGGER;
          const s = useFadeSlide(delay, 15, 25);
          const isLast = i === items.length - 1;
          const arrowFade = useFade(delay + 10, 8, 0.8);

          return (
            <React.Fragment key={i}>
              <div style={{ ...s }}>
                <Card style={{ display: "flex", alignItems: "flex-start", gap: 20 }}>
                  <CircleBadge
                    text={String(i + 1)}
                    size={36}
                    filled
                    style={{ marginTop: 2 }}
                  />
                  <div>
                    <div style={{ fontSize: 44, fontWeight: 600, color: C.text, lineHeight: 1.4 }}>
                      {item}
                    </div>
                    {descs[i] && (
                      <div style={{ fontSize: 34, fontWeight: 400, color: C.textMuted, marginTop: 4 }}>
                        {descs[i]}
                      </div>
                    )}
                  </div>
                </Card>
              </div>
              {!isLast && (
                <div style={{ marginLeft: 28, fontSize: 36, color: C.accent, opacity: arrowFade }}>
                  ↓
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};

/* ====================================================================
   13. Icon Grid — icon_grid
   2x2 or 3x2 개념 그리드, 각 셀은 이미지/실루엣 + 라벨
   ==================================================================== */

const IconGrid: React.FC<{ data: any }> = ({ data }) => {
  const items: string[] = data.items || [];
  const descs: string[] = data.descriptions || [];
  const images: (string | null)[] = data.images || [];
  const title = useFadeRise(0, 20, 15);
  const STAGGER = 8;
  const cols = items.length <= 4 ? 2 : 3;

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        padding: "80px 0",
      }}
    >
      <div style={{ ...title, fontSize: 88, fontWeight: 800, color: C.text, marginBottom: 40 }}>
        {data.title}
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${cols}, 1fr)`,
          gap: 16,
        }}
      >
        {items.map((item, i) => {
          const delay = 14 + i * STAGGER;
          const s = useScale(delay, 18);
          return (
            <div key={i} style={{ ...s }}>
              <Card
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  textAlign: "center",
                  padding: "28px 20px",
                  borderColor: i === 0 ? C.accent : C.cardBorder,
                }}
              >
                {images[i] ? (
                  <ImageBadge imageUrl={images[i]!} size={52} style={{ marginBottom: 16 }} />
                ) : (
                  <CircleBadge
                    text={item.charAt(0)}
                    size={48}
                    filled={i === 0}
                    style={{ marginBottom: 16 }}
                  />
                )}
                <div style={{ fontSize: 40, fontWeight: 700, color: C.text, lineHeight: 1.3, marginBottom: 4 }}>
                  {item}
                </div>
                {descs[i] && (
                  <div style={{ fontSize: 32, fontWeight: 400, color: C.textMuted, lineHeight: 1.4 }}>
                    {descs[i]}
                  </div>
                )}
              </Card>
            </div>
          );
        })}
      </div>
    </div>
  );
};

/* ====================================================================
   14. Icon Stat — icon_stat
   단일 큰 숫자 KPI + 아이콘 + 트렌드
   ==================================================================== */

const IconStat: React.FC<{ data: any }> = ({ data }) => {
  const frame = useCurrentFrame();
  const value = data.value || data.items?.[0] || "0";
  const numTarget = extractNumber(String(value));
  const label = data.title || "";
  const desc = data.items?.[1] || data.source || "";
  const trend = data.trend; // "up" | "down" | undefined

  const counted = useCountUp(10, 40, numTarget);
  const formatted = formatWithTemplate(String(value), counted);

  const iconFade = useScale(0, 20);
  const numFade = useFadeRise(8, 25, 30);
  const labelFade = useFadeRise(18, 20, 15);
  const descFade = useFadeRise(35, 18, 12);
  const glowOpacity = interpolate(frame, [15, 50], [0, 0.3], clamp);

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: "80px 0",
      }}
    >
      {/* 큰 원형 배경 */}
      <div
        style={{
          ...iconFade,
          width: 120,
          height: 120,
          borderRadius: 60,
          border: `3px solid ${C.accentBorder}`,
          backgroundColor: C.accentBg,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          marginBottom: 32,
        }}
      >
        {trend === "up" && (
          <span style={{ fontSize: 96, color: C.accent }}>↑</span>
        )}
        {trend === "down" && (
          <span style={{ fontSize: 96, color: "#EF4444" }}>↓</span>
        )}
        {!trend && (
          <span style={{ fontSize: 72, fontWeight: 800, color: C.accent }}>
            {label.charAt(0) || "#"}
          </span>
        )}
      </div>

      {/* 라벨 */}
      <div
        style={{
          ...labelFade,
          fontSize: 44,
          fontWeight: 500,
          color: C.textMuted,
          marginBottom: 16,
          letterSpacing: "0.02em",
        }}
      >
        {label}
      </div>

      {/* 큰 숫자 */}
      <div
        style={{
          ...numFade,
          fontSize: 132,
          fontWeight: 800,
          color: C.accent,
          lineHeight: 1.0,
          letterSpacing: "-0.02em",
          textShadow: `0 0 50px rgba(245,158,11,${glowOpacity})`,
        }}
      >
        {formatted}
      </div>

      {/* 설명 */}
      {desc && (
        <div
          style={{
            ...descFade,
            fontSize: 44,
            fontWeight: 400,
            color: C.textMuted,
            marginTop: 24,
            textAlign: "center",
            lineHeight: 1.4,
          }}
        >
          {desc}
        </div>
      )}
    </div>
  );
};

/* ====================================================================
   15. Impact Count — impact_count
   아이템이 하나씩 등장 후 동시 플래시 → 큰 숫자 오버레이
   "9개 도시 동시 타격" 같은 동시성 강조에 사용
   ==================================================================== */

const ImpactCount: React.FC<{ data: any }> = ({ data }) => {
  const frame = useCurrentFrame();
  const items: string[] = data.items || [];
  const rawValue = data.value || String(items.length);
  const numTarget = extractNumber(String(rawValue));
  const title = data.title || "";
  const subtitle = data.subtitle || data.source || "";
  const unit = data.unit || "";

  const titleFade = useFadeRise(0, 20, 15);
  const ITEM_STAGGER = 5;
  const ALL_DONE = 18 + items.length * ITEM_STAGGER;
  const FLASH_AT = ALL_DONE + 5;
  const NUM_AT = FLASH_AT + 12;

  // 동시 플래시: 모든 아이템이 한꺼번에 빛남
  const flashPeak = interpolate(
    frame,
    [FLASH_AT, FLASH_AT + 6, FLASH_AT + 25],
    [0, 1, 0.2],
    clamp,
  );
  const isFlashing = frame >= FLASH_AT;

  // 큰 숫자
  const counted = useCountUp(NUM_AT, 25, numTarget);
  const numOpacity = useFade(NUM_AT, 15);
  const numScale = interpolate(
    frame,
    [NUM_AT, NUM_AT + 20],
    [1.4, 1],
    { ...clamp, easing: ease },
  );
  const numGlow = interpolate(frame, [NUM_AT, NUM_AT + 30], [0, 0.5], clamp);

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: "80px 0",
      }}
    >
      {/* 타이틀 */}
      <div
        style={{
          ...titleFade,
          fontSize: 88,
          fontWeight: 800,
          color: C.text,
          marginBottom: 40,
        }}
      >
        {title}
      </div>

      {/* 아이템 그리드 */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 12,
          justifyContent: "center",
          marginBottom: 48,
        }}
      >
        {items.map((item, i) => {
          const delay = 18 + i * ITEM_STAGGER;
          const itemOpacity = useFade(delay, 10);

          return (
            <div
              key={i}
              style={{
                opacity: itemOpacity,
                padding: "14px 28px",
                borderRadius: 10,
                border: `2px solid ${isFlashing ? C.accent : C.cardBorder}`,
                backgroundColor: isFlashing
                  ? `rgba(245,158,11,${flashPeak * 0.15})`
                  : C.cardBg,
                boxShadow: isFlashing
                  ? `0 0 ${24 * flashPeak}px rgba(245,158,11,${flashPeak * 0.5})`
                  : "none",
                fontSize: 48,
                fontWeight: 600,
                color: isFlashing ? C.accent : C.text,
              }}
            >
              {item}
            </div>
          );
        })}
      </div>

      {/* 큰 숫자 — 플래시 후 등장 */}
      <div
        style={{
          opacity: numOpacity,
          transform: `scale(${numScale})`,
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontSize: 150,
            fontWeight: 800,
            color: C.accent,
            lineHeight: 1,
            textShadow: `0 0 60px rgba(245,158,11,${numGlow})`,
          }}
        >
          {counted}
          {unit && (
            <span style={{ fontSize: 72, fontWeight: 600, marginLeft: 4 }}>
              {unit}
            </span>
          )}
        </div>
        {subtitle && (
          <div
            style={{
              fontSize: 44,
              fontWeight: 400,
              color: C.textMuted,
              marginTop: 12,
            }}
          >
            {subtitle}
          </div>
        )}
      </div>
    </div>
  );
};

/* ====================================================================
   16. Diagram — 흐름도/인과관계
   A → B → C 구조, 카드 + 화살표
   ==================================================================== */

const DiagramScene: React.FC<{ data: any }> = ({ data }) => {
  const items: string[] = data.items || [];
  const descs: string[] = data.descriptions || [];
  const title = useFadeRise(0, 20, 15);
  const STAGGER = 12;

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        padding: "80px 0",
      }}
    >
      <div style={{ ...title, fontSize: 88, fontWeight: 800, color: C.text, marginBottom: 40 }}>
        {data.title}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 0, alignItems: "center" }}>
        {items.map((item, i) => {
          const delay = 14 + i * STAGGER;
          const cardFade = useScale(delay, 20);
          const arrowFade = useFade(delay + 8, 10, 0.8);
          const isLast = i === items.length - 1;

          return (
            <React.Fragment key={i}>
              <div style={{ ...cardFade, width: "80%" }}>
                <Card
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 20,
                    borderColor: i === 0 ? C.accent : i === items.length - 1 ? C.accent : C.cardBorder,
                    borderWidth: i === 0 || i === items.length - 1 ? 2 : 1,
                  }}
                >
                  <div
                    style={{
                      width: 40,
                      height: 40,
                      borderRadius: 8,
                      backgroundColor: i === 0 ? C.accent : C.accentBg,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 36,
                      fontWeight: 700,
                      color: i === 0 ? C.bg : C.accent,
                      flexShrink: 0,
                    }}
                  >
                    {i + 1}
                  </div>
                  <div>
                    <div style={{ fontSize: 44, fontWeight: 600, color: C.text, lineHeight: 1.4 }}>
                      {item}
                    </div>
                    {descs[i] && (
                      <div style={{ fontSize: 32, fontWeight: 400, color: C.textMuted, marginTop: 4 }}>
                        {descs[i]}
                      </div>
                    )}
                  </div>
                </Card>
              </div>
              {!isLast && (
                <div
                  style={{
                    opacity: arrowFade,
                    fontSize: 56,
                    color: C.accent,
                    padding: "8px 0",
                    lineHeight: 1,
                  }}
                >
                  ▼
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};

/* ====================================================================
   17. DramaticNumber — 극적 정지 후 큰 숫자 공개
   맥락 텍스트 → 잠시 정지 → 큰 숫자 줌인
   ==================================================================== */

const DramaticNumber: React.FC<{ data: any }> = ({ data }) => {
  const frame = useCurrentFrame();
  const headline = data.creative?.headline || data.title || "";
  const source = data.source || "";

  // headline 안의 {{...}}에서 숫자 추출 → 카운트업 애니메이션용
  const accentMatch = headline.match(/\{\{([^}]+)\}\}/);
  const accentContent = accentMatch ? accentMatch[1] : "";
  const rawValue = data.values?.[0] || data.value || "0";
  const numTarget = extractNumber(accentContent || String(rawValue));

  // Phase 1: 전체 텍스트 페이드인 (5-23)
  const textFade = useFadeRise(5, 18, 20);

  // Phase 2: 숫자 카운트업 + 글로우 (15+)
  const counted = useCountUp(15, 35, numTarget);
  const numGlow = interpolate(frame, [15, 60], [0, 0.6], clamp);
  const sourceFade = useFade(50, 15, 0.8);

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: "80px 60px",
      }}
    >
      {/* headline 인라인 — {{숫자}}는 큰 악센트로, 나머지는 맥락 텍스트 */}
      <div
        style={{
          ...textFade,
          fontSize: 72,
          fontWeight: 600,
          textAlign: "center",
          lineHeight: 2.4,
          maxWidth: "85%",
        }}
      >
        {headline.split("\n").map((line: string, li: number) => (
          <React.Fragment key={li}>
            {li > 0 && <br />}
            {line.split(/(\{\{[^}]+\}\})/g).map((part: string, pi: number) => {
              if (part.startsWith("{{") && part.endsWith("}}")) {
                const content = part.slice(2, -2);
                const num = extractNumber(content);
                const isNum = !isNaN(num) && num > 0;
                const displayText = isNum
                  ? formatWithTemplate(content, counted)
                  : content;
                return (
                  <span
                    key={pi}
                    style={{
                      fontSize: 132,
                      fontWeight: 800,
                      color: C.accent,
                      display: "inline-block",
                      textShadow: `0 0 60px rgba(245,158,11,${numGlow})`,
                      verticalAlign: "middle",
                      lineHeight: 1.1,
                      margin: "0 4px",
                    }}
                  >
                    {displayText}
                  </span>
                );
              }
              return (
                <span key={pi} style={{ color: C.textMuted }}>
                  {part}
                </span>
              );
            })}
          </React.Fragment>
        ))}
      </div>

      {source && (
        <div
          style={{
            opacity: sourceFade,
            fontSize: 32,
            color: C.textDim,
            marginTop: 32,
          }}
        >
          {source}
        </div>
      )}
    </div>
  );
};

/* ====================================================================
   18. RevealSequence — 단계별 공개 스토리
   각 단계가 하나씩 드러남, 마지막에 전체 하이라이트
   ==================================================================== */

const RevealSequence: React.FC<{ data: any }> = ({ data }) => {
  const frame = useCurrentFrame();
  const items: string[] = data.items || [];
  const title = data.title || "";
  const headline = data.creative?.headline || "";
  const STEP_DUR = 18;

  const titleFade = useFadeRise(0, 18, 15);
  const totalSteps = items.length;
  const ALL_DONE = 20 + totalSteps * STEP_DUR;

  // 마지막 전체 조망: 모든 아이템이 accent로 빛남
  const finalGlow = interpolate(
    frame,
    [ALL_DONE, ALL_DONE + 15],
    [0, 1],
    clamp,
  );

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        padding: "80px 0",
      }}
    >
      <div
        style={{
          ...titleFade,
          fontSize: 80,
          fontWeight: 800,
          color: C.text,
          marginBottom: 40,
          textAlign: "center",
        }}
      >
        <AccentText text={headline || title} />
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 8, alignItems: "center" }}>
        {items.map((item, i) => {
          const delay = 20 + i * STEP_DUR;
          const stepFade = useFadeSlide(delay, 15, 30);
          const isRevealed = frame >= delay + 15;
          const isFinal = finalGlow > 0;
          const stepNum = i + 1;

          return (
            <div
              key={i}
              style={{
                ...stepFade,
                width: "75%",
                display: "flex",
                alignItems: "center",
                gap: 16,
                padding: "16px 24px",
                borderRadius: 10,
                border: `1px solid ${isFinal ? C.accent : isRevealed ? C.cardBorder : "transparent"}`,
                backgroundColor: isFinal
                  ? `rgba(245,158,11,${finalGlow * 0.08})`
                  : C.cardBg,
              }}
            >
              <div
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 18,
                  backgroundColor: isFinal ? C.accent : C.accentBg,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 32,
                  fontWeight: 700,
                  color: isFinal ? C.bg : C.accent,
                  flexShrink: 0,
                }}
              >
                {stepNum}
              </div>
              <div style={{ fontSize: 44, fontWeight: 600, color: isFinal ? C.accent : C.text }}>
                <AccentText text={item} baseColor={isFinal ? C.accent : C.text} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

/* ====================================================================
   19. SplitContrast — 화면 분할 대비
   좌우 분할로 두 가지 대비되는 정보 표시
   ==================================================================== */

const SplitContrast: React.FC<{ data: any }> = ({ data }) => {
  const frame = useCurrentFrame();
  const items: string[] = data.items || [];
  const title = data.title || "";
  const headline = data.creative?.headline || "";

  const leftItem = items[0] || "";
  const rightItem = items[1] || "";

  const titleFade = useFadeRise(0, 18, 15);

  // 분할선 애니메이션
  const dividerHeight = interpolate(
    frame,
    [15, 40],
    [0, 100],
    { ...clamp, easing: ease },
  );

  // 좌우 슬라이드 인
  const leftSlide = useFadeSlide(25, 18, -40);
  const rightSlide = {
    opacity: interpolate(frame - 25, [0, 18], [0, 1], { ...clamp, easing: ease }),
    transform: `translateX(${interpolate(frame - 25, [0, 18], [40, 0], { ...clamp, easing: ease })}px)`,
  };

  // "vs" 텍스트
  const vsFade = useScale(35, 15);

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: "80px 0",
      }}
    >
      {/* 타이틀 */}
      <div
        style={{
          ...titleFade,
          fontSize: 72,
          fontWeight: 800,
          color: C.text,
          marginBottom: 48,
          textAlign: "center",
        }}
      >
        <AccentText text={headline || title} />
      </div>

      {/* 분할 영역 */}
      <div
        style={{
          display: "flex",
          width: "85%",
          gap: 0,
          alignItems: "stretch",
          position: "relative",
        }}
      >
        {/* 왼쪽 */}
        <div
          style={{
            ...leftSlide,
            flex: 1,
            padding: "40px 36px",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <div
            style={{
              fontSize: 56,
              fontWeight: 700,
              color: C.text,
              textAlign: "center",
              lineHeight: 1.5,
            }}
          >
            <AccentText text={leftItem} />
          </div>
        </div>

        {/* 중앙 분할선 + VS */}
        <div
          style={{
            position: "relative",
            width: 60,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <div
            style={{
              position: "absolute",
              width: 2,
              height: `${dividerHeight}%`,
              backgroundColor: C.accent,
              opacity: 0.5,
            }}
          />
          <div
            style={{
              ...vsFade,
              position: "relative",
              zIndex: 1,
              fontSize: 36,
              fontWeight: 800,
              color: C.accent,
              backgroundColor: C.bg,
              padding: "8px 12px",
              borderRadius: 8,
              border: `1px solid ${C.accentBorder}`,
            }}
          >
            VS
          </div>
        </div>

        {/* 오른쪽 */}
        <div
          style={{
            ...rightSlide,
            flex: 1,
            padding: "40px 36px",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <div
            style={{
              fontSize: 56,
              fontWeight: 700,
              color: C.text,
              textAlign: "center",
              lineHeight: 1.5,
            }}
          >
            <AccentText text={rightItem} />
          </div>
        </div>
      </div>
    </div>
  );
};

/* ====================================================================
   20. SpotlightReveal — 스포트라이트 공개
   어두운 화면에서 핵심만 밝아짐
   ==================================================================== */

const SpotlightReveal: React.FC<{ data: any }> = ({ data }) => {
  const frame = useCurrentFrame();
  const items: string[] = data.items || [];
  const title = data.title || "";
  const headline = data.creative?.headline || "";

  // 오버레이 어둡기 (점점 밝아짐)
  const overlayOpacity = interpolate(
    frame,
    [0, 30, 50],
    [0.95, 0.7, 0.3],
    clamp,
  );

  const spotlightSize = interpolate(
    frame,
    [10, 45],
    [100, 600],
    { ...clamp, easing: ease },
  );

  const titleFade = useFadeRise(25, 20, 20);
  const contentFade = useFadeRise(40, 20, 15);

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        position: "relative",
      }}
    >
      {/* 스포트라이트 그라데이션 오버레이 */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: `radial-gradient(circle ${spotlightSize}px at 50% 45%, transparent 0%, rgba(0,0,0,${overlayOpacity}) 100%)`,
          pointerEvents: "none",
          zIndex: 1,
        }}
      />

      {/* 컨텐츠 */}
      <div
        style={{
          position: "relative",
          zIndex: 2,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          padding: "80px 0",
        }}
      >
        <div
          style={{
            ...titleFade,
            fontSize: 96,
            fontWeight: 800,
            color: C.text,
            textAlign: "center",
            marginBottom: 32,
            lineHeight: 1.3,
          }}
        >
          <AccentText text={headline || title} />
        </div>

        {items.length > 0 && (
          <div
            style={{
              ...contentFade,
              display: "flex",
              flexDirection: "column",
              gap: 12,
              alignItems: "center",
            }}
          >
            {items.map((item, i) => {
              const itemDelay = 50 + i * 8;
              const itemFade = useFadeRise(itemDelay, 15, 12);
              return (
                <div
                  key={i}
                  style={{
                    ...itemFade,
                    fontSize: 48,
                    fontWeight: 600,
                    color: C.textMuted,
                    textAlign: "center",
                  }}
                >
                  <AccentText text={item} baseColor={C.textMuted} />
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

/* ====================================================================
   21. CounterWall — 다수 통계 동시 카운팅
   여러 숫자가 동시에 카운팅되며 벽처럼 채움
   ==================================================================== */

const CounterWall: React.FC<{ data: any }> = ({ data }) => {
  const items: string[] = data.items || [];
  const values: number[] = (data.values || []).map(Number);
  const unit = data.unit || "";
  const title = data.title || "";
  const headline = data.creative?.headline || "";

  const titleFade = useFadeRise(0, 18, 15);
  const COUNT_START = 20;
  const STAGGER = 6;

  const cols = items.length <= 2 ? items.length : items.length <= 4 ? 2 : 3;

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: "80px 0",
      }}
    >
      <div
        style={{
          ...titleFade,
          fontSize: 80,
          fontWeight: 800,
          color: C.text,
          marginBottom: 48,
          textAlign: "center",
        }}
      >
        <AccentText text={headline || title} />
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${cols}, 1fr)`,
          gap: 24,
          width: "80%",
        }}
      >
        {items.map((item, i) => {
          const delay = COUNT_START + i * STAGGER;
          const cardFade = useFadeRise(delay, 15, 20);
          const counted = useCountUp(delay + 5, 35, values[i] || 0, 0);

          return (
            <div
              key={i}
              style={{
                ...cardFade,
              }}
            >
              <Card style={{ textAlign: "center", padding: "32px 24px" }}>
                <div
                  style={{
                    fontSize: 104,
                    fontWeight: 800,
                    color: C.accent,
                    lineHeight: 1,
                    marginBottom: 12,
                  }}
                >
                  {counted.toLocaleString()}
                  {unit && (
                    <span style={{ fontSize: 40, fontWeight: 500, marginLeft: 4 }}>
                      {unit}
                    </span>
                  )}
                </div>
                <div
                  style={{
                    fontSize: 36,
                    fontWeight: 600,
                    color: C.textMuted,
                  }}
                >
                  {item}
                </div>
              </Card>
            </div>
          );
        })}
      </div>
    </div>
  );
};

/* ====================================================================
   22. NarrativeBuild — 서사적 구축
   요소가 하나씩 쌓여 전체 그림 완성
   ==================================================================== */

const NarrativeBuild: React.FC<{ data: any }> = ({ data }) => {
  const frame = useCurrentFrame();
  const items: string[] = data.items || [];
  const title = data.title || "";
  const headline = data.creative?.headline || "";
  const STAGGER = 14;
  const ALL_DONE = 15 + items.length * STAGGER;

  const titleFade = useFadeRise(0, 18, 15);

  // 마지막에 전체 연결선 등장
  const connectorOpacity = interpolate(
    frame,
    [ALL_DONE, ALL_DONE + 20],
    [0, 0.6],
    clamp,
  );

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: "80px 0",
      }}
    >
      <div
        style={{
          ...titleFade,
          fontSize: 80,
          fontWeight: 800,
          color: C.text,
          marginBottom: 48,
          textAlign: "center",
        }}
      >
        <AccentText text={headline || title} />
      </div>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 0,
          position: "relative",
        }}
      >
        {/* 연결선 (전체 완성 후) */}
        <div
          style={{
            position: "absolute",
            left: "50%",
            top: 0,
            bottom: 0,
            width: 2,
            backgroundColor: C.accent,
            opacity: connectorOpacity,
            transform: "translateX(-50%)",
          }}
        />

        {items.map((item, i) => {
          const delay = 15 + i * STAGGER;
          const blockFade = useScale(delay, 18);
          const isLeft = i % 2 === 0;

          return (
            <div
              key={i}
              style={{
                ...blockFade,
                display: "flex",
                width: "80%",
                justifyContent: isLeft ? "flex-start" : "flex-end",
                padding: "8px 0",
              }}
            >
              <div
                style={{
                  maxWidth: "45%",
                  minWidth: 200,
                  padding: "16px 24px",
                  borderRadius: 10,
                  border: `1px solid ${C.cardBorder}`,
                  backgroundColor: C.cardBg,
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  whiteSpace: "nowrap" as const,
                }}
              >
                <div
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: 14,
                    backgroundColor: C.accentBg,
                    border: `2px solid ${C.accent}`,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 26,
                    fontWeight: 700,
                    color: C.accent,
                    flexShrink: 0,
                  }}
                >
                  {i + 1}
                </div>
                <div style={{ fontSize: 40, fontWeight: 600, color: C.text, lineHeight: 1.4 }}>
                  <AccentText text={item} />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

/* ====================================================================
   23. WordCascade — 키워드 폭포
   단어들이 위에서 떨어지며 화면을 채움
   ==================================================================== */

const WordCascade: React.FC<{ data: any }> = ({ data }) => {
  const items: string[] = data.items || [];
  const title = data.title || "";
  const headline = data.creative?.headline || "";
  const STAGGER = 6;

  const titleFade = useFadeRise(0, 18, 15);

  // 무작위하지 않은 고정 패턴 위치
  const positions = [
    { x: 20, size: 28 }, { x: 55, size: 32 }, { x: 35, size: 26 },
    { x: 70, size: 30 }, { x: 15, size: 24 }, { x: 50, size: 34 },
    { x: 80, size: 28 }, { x: 30, size: 26 }, { x: 60, size: 30 },
    { x: 45, size: 28 }, { x: 25, size: 32 }, { x: 65, size: 26 },
  ];

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: "80px 0",
      }}
    >
      <div
        style={{
          ...titleFade,
          fontSize: 80,
          fontWeight: 800,
          color: C.text,
          marginBottom: 48,
          textAlign: "center",
          zIndex: 2,
          position: "relative",
        }}
      >
        <AccentText text={headline || title} />
      </div>

      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 16,
          justifyContent: "center",
          maxWidth: "85%",
        }}
      >
        {items.map((item, i) => {
          const delay = 15 + i * STAGGER;
          const pos = positions[i % positions.length];
          const dropFade = useFadeRise(delay, 12, 30);
          const isAccent = i % 3 === 0;

          return (
            <div
              key={i}
              style={{
                ...dropFade,
                padding: "12px 24px",
                borderRadius: 8,
                border: `1px solid ${isAccent ? C.accent : C.cardBorder}`,
                backgroundColor: isAccent ? C.accentSoft : C.cardBg,
                fontSize: pos.size,
                fontWeight: isAccent ? 700 : 500,
                color: isAccent ? C.accent : C.text,
              }}
            >
              {item}
            </div>
          );
        })}
      </div>
    </div>
  );
};

/* ====================================================================
   Bridge — narration-only
   최소한의 시각 요소, 원형 장식
   ==================================================================== */

const Bridge: React.FC<{ text: string }> = ({ text }) => {
  const line = useLineExpand(10, 30, 60);
  const dotScale = useScale(5, 20);

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <div
        style={{
          ...dotScale,
          width: 8,
          height: 8,
          borderRadius: 4,
          backgroundColor: C.accent,
          marginBottom: 24,
          opacity: 0.5,
        }}
      />
      <div style={{ width: line, height: 2, backgroundColor: C.accent, opacity: 0.3 }} />
      {text && (
        <div
          style={{
            fontSize: 56,
            fontWeight: 600,
            color: C.textMuted,
            textAlign: "center",
            marginTop: 24,
            lineHeight: 1.5,
          }}
        >
          {text}
        </div>
      )}
    </div>
  );
};
