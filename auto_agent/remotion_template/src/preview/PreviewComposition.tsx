/**
 * PreviewComposition — 25개 BuildingBlocks + 차트/레이아웃 샘플 시각 프리뷰
 *
 * 모든 디자인 토큰(컬러, 타이포, 레이아웃, 변형)을 실시간 반영.
 */
import React from "react";
import { DesignPresetProvider, useDesignPreset } from "../design";
import type { DesignPresetOverride } from "../design/types";
import {
  AccentText, Card, CircleBadge, ImageBadge, Icon, IconBadge,
  FlagBadge, FlagCard, LogoBadge, ProgressBar, Tag, Divider,
  StatusDot, Pill, Connector, TimelineDot, MetricCard, Sparkline,
  Callout, StepBadge, ComparisonCell, RankBadge, QuoteMark,
  GlowDot, AnnotationLine, MiniBar, useC,
} from "../simple/BuildingBlocks";
import { Brain, Shield, TrendingUp, Star } from "lucide-react";

interface Props {
  designPreset?: DesignPresetOverride;
}

const PreviewContent: React.FC = () => {
  const C = useC();
  const preset = useDesignPreset();
  const T = preset.typography;
  const L = preset.layout;

  const section: React.CSSProperties = {
    marginBottom: L.sectionMarginTop + 8,
    padding: `0 ${L.scenePadding[1]}px`,
  };
  const title: React.CSSProperties = {
    fontSize: 14, fontWeight: 700, color: C.accent,
    marginBottom: 12, textTransform: "uppercase", letterSpacing: 1,
    borderBottom: `1px solid ${C.divider}`, paddingBottom: 8,
  };
  const row: React.CSSProperties = {
    display: "flex", alignItems: "center", gap: L.gap, flexWrap: "wrap",
  };

  // 바 차트 샘플 데이터
  const barData = [
    { label: "항목 A", value: 85 },
    { label: "항목 B", value: 62 },
    { label: "항목 C", value: 45 },
    { label: "항목 D", value: 30 },
  ];
  const barMax = Math.max(...barData.map(d => d.value));

  return (
    <div style={{
      backgroundColor: C.bg,
      fontFamily: `'${preset.fonts.body.family}', ${preset.fonts.body.fallback || "sans-serif"}`,
      minHeight: "100vh",
      padding: `${L.scenePadding[0]}px 0`,
      color: C.text,
    }}>

      {/* ── 1. Headline & Typography ── */}
      <div style={section}>
        <div style={title}>Headline & Typography</div>
        <div style={{ fontSize: T.headlineAccent, fontWeight: 800, marginBottom: 8 }}>
          <AccentText text="{{Design}} Preset" />
        </div>
        <div style={{ fontSize: T.headlineBase, fontWeight: 600, color: C.text, marginBottom: 6 }}>
          헤드라인 베이스 텍스트
        </div>
        <div style={{ fontSize: T.itemText, color: C.text, marginBottom: 4 }}>
          아이템 텍스트 ({T.itemText}px)
        </div>
        <div style={{ fontSize: T.descText, color: C.textMuted, marginBottom: 4 }}>
          설명 텍스트 ({T.descText}px)
        </div>
        <div style={{ fontSize: T.labelText, color: C.textDim, marginBottom: 4 }}>
          라벨 텍스트 ({T.labelText}px)
        </div>
        <div style={{ fontSize: T.sourceText, color: C.textDim }}>
          출처 텍스트 ({T.sourceText}px)
        </div>
      </div>

      {/* ── 2. Badges & Icons ── */}
      <div style={section}>
        <div style={title}>Badges & Icons (size: {L.badgeSize}px)</div>
        <div style={row}>
          <CircleBadge text="1" filled size={L.badgeSize} />
          <CircleBadge text="A" size={L.badgeSize} />
          <IconBadge icon={Brain} filled size={L.badgeSize} />
          <IconBadge icon={Shield} size={L.badgeSize} />
          <Icon icon={TrendingUp} size={L.badgeSize * 0.5} />
          <Icon icon={Star} size={L.badgeSize * 0.5} />
          <ImageBadge size={L.imageBadgeSize} />
          <FlagBadge countryCode="KR" size={L.badgeSize} />
          <FlagBadge countryCode="US" size={L.badgeSize} />
          <LogoBadge logo="Google" size={L.badgeSize} />
        </div>
        <div style={{ ...row, marginTop: L.itemsGap }}>
          <RankBadge rank={1} size={L.rankBadgeSize} />
          <RankBadge rank={2} size={L.rankBadgeSize} />
          <RankBadge rank={3} size={L.rankBadgeSize} />
          <GlowDot size={L.statusDotSize * 1.5} />
        </div>
      </div>

      {/* ── 3. Cards (radius: {L.cardRadius}px, padding: {L.cardPadding}) ── */}
      <div style={section}>
        <div style={title}>Cards (radius: {L.cardRadius}px)</div>
        <div style={{ ...row, alignItems: "stretch" }}>
          <Card style={{ flex: 1 }}>
            <div style={{ fontSize: T.itemText, fontWeight: 600 }}>기본 카드</div>
            <div style={{ fontSize: T.descText, color: C.textMuted, marginTop: 8 }}>카드 설명</div>
          </Card>
          <MetricCard label="성장률" value="127%" change="+23%" trend="up" style={{ flex: 1 }} />
          <ComparisonCell label="Before" value="$100" variant="before" style={{ flex: 1 }} />
          <ComparisonCell label="After" value="$250" variant="after" style={{ flex: 1 }} />
        </div>
        <div style={{ marginTop: L.itemsGap }}>
          <Callout variant="accent">Accent 콜아웃 — 주요 정보 강조</Callout>
        </div>
        <div style={{ marginTop: 8 }}>
          <Callout variant="warning">Warning 콜아웃 — 주의 필요</Callout>
        </div>
      </div>

      {/* ── 4. Tags & Pills ── */}
      <div style={section}>
        <div style={title}>Tags & Pills</div>
        <div style={row}>
          <Tag text="Small" size="sm" />
          <Tag text="Medium" size="md" />
          <Tag text="Large" size="lg" />
          <Tag text="Active" size="md" active />
          <Pill text="Pill A" />
          <Pill text="Pill B" active />
        </div>
        <div style={{ ...row, marginTop: L.itemsGap }}>
          <StatusDot status="positive" label="정상" />
          <StatusDot status="negative" label="오류" />
          <StatusDot status="warning" label="경고" />
          <StatusDot status="neutral" label="대기" />
        </div>
      </div>

      {/* ── 5. Bar Chart Sample (height: {L.barHeight}px, maxWidth: {L.maxContentWidth}px) ── */}
      <div style={section}>
        <div style={title}>Bar Chart (height: {L.barHeight}px, width: {L.maxContentWidth}px)</div>
        <div style={{ fontSize: T.chartTitle, fontWeight: 700, marginBottom: L.itemsGap }}>
          <AccentText text="{{샘플}} 바 차트" />
        </div>
        <div style={{ maxWidth: L.maxContentWidth, display: "flex", flexDirection: "column", gap: L.itemsGap }}>
          {barData.map((d, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: L.itemsGap }}>
              <div style={{ width: L.barLabelWidth, fontSize: T.labelText, color: C.text, textAlign: "right" }}>
                {d.label}
              </div>
              <div style={{
                flex: 1, height: L.barHeight,
                backgroundColor: C.divider, borderRadius: L.barHeight / 2, overflow: "hidden",
              }}>
                <div style={{
                  width: `${(d.value / barMax) * 100}%`, height: "100%",
                  backgroundColor: C.accent, borderRadius: L.barHeight / 2,
                }} />
              </div>
              <div style={{ width: L.barValueWidth, fontSize: T.chartValue, fontWeight: 700, color: C.accent }}>
                {d.value}%
              </div>
            </div>
          ))}
        </div>
        <div style={{ fontSize: T.sourceText, color: C.textDim, marginTop: 12 }}>
          출처: 샘플 데이터
        </div>
      </div>

      {/* ── 6. Progress & MiniBar ── */}
      <div style={section}>
        <div style={title}>Progress (height: {L.progressBarHeight}px) & MiniBar ({L.miniBarHeight}px)</div>
        <div style={{ display: "flex", flexDirection: "column", gap: L.itemsGap, maxWidth: 500 }}>
          <ProgressBar progress={0.75} label="달성률" height={L.progressBarHeight} />
          <MiniBar value={85} maxValue={100} label="점수" height={L.miniBarHeight} />
          <MiniBar value={42} maxValue={100} label="진행" height={L.miniBarHeight} />
          <Sparkline data={[10, 25, 18, 35, 28, 45, 40, 55, 48, 65]} width={L.sparklineSize[0]} height={L.sparklineSize[1]} />
        </div>
      </div>

      {/* ── 7. Process & Timeline ── */}
      <div style={section}>
        <div style={title}>Process</div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <StepBadge step={1} label="기획" active size={L.stepBadgeSize} />
          <Connector direction="right" length={L.connectorLength} />
          <StepBadge step={2} label="개발" size={L.stepBadgeSize} />
          <Connector direction="right" length={L.connectorLength} />
          <StepBadge step={3} label="배포" size={L.stepBadgeSize} />
        </div>
      </div>

      {/* ── 7b. Timeline (가로형) ── */}
      {(() => {
        const tlItems = [
          { label: "2024.01", desc: "프로젝트 시작", active: true },
          { label: "2024.06", desc: "베타 출시", active: false },
          { label: "2024.12", desc: "정식 런칭", active: false },
        ];
        const dotS = L.timelineDotSize;
        return (
          <div style={section}>
            <div style={title}>Timeline (가로)</div>
            <div style={{ position: "relative", display: "flex", justifyContent: "space-between", alignItems: "flex-start", padding: `0 ${dotS}px` }}>
              {/* 연결선: 첫 도트 중앙 ~ 마지막 도트 중앙 */}
              <div style={{
                position: "absolute",
                top: dotS / 2 - L.timelineConnectorWidth / 2,
                left: dotS + dotS / 2,
                right: dotS + dotS / 2,
                height: L.timelineConnectorWidth,
                backgroundColor: C.cardBorder,
              }} />
              {/* 도트 + 라벨 */}
              {tlItems.map((item, i) => (
                <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8, position: "relative", zIndex: 1 }}>
                  <div style={{
                    width: dotS, height: dotS,
                    borderRadius: dotS / 2,
                    backgroundColor: item.active ? C.accent : C.bg,
                    border: `${L.timelineConnectorWidth}px solid ${item.active ? C.accent : C.cardBorder}`,
                    flexShrink: 0,
                  }} />
                  <div style={{ fontSize: T.labelText, fontWeight: item.active ? 700 : 400, color: item.active ? C.accent : C.text, textAlign: "center" }}>
                    {item.label}
                  </div>
                  <div style={{ fontSize: T.descText, color: C.textMuted, textAlign: "center" }}>
                    {item.desc}
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })()}

      {/* ── 8. Misc ── */}
      <div style={section}>
        <div style={title}>Misc</div>
        <div style={row}>
          <QuoteMark />
          <Divider width={200} thickness={L.dividerThickness} />
          <AnnotationLine text="주석" width={L.annotationLineLength} />
        </div>
        <div style={{ marginTop: L.itemsGap }}>
          <FlagCard countryCode="JP" label="일본" />
        </div>
      </div>

      {/* ── 9. Quote ── */}
      <div style={section}>
        <div style={title}>Quote</div>
        <div style={{ display: "flex", gap: L.gap, alignItems: "flex-start" }}>
          <QuoteMark size={T.quoteMarkSize * 0.5} />
          <div>
            <div style={{ fontSize: T.quoteText, color: C.text, fontStyle: "italic", lineHeight: 1.6 }}>
              디자인은 어떻게 작동하는가이다.
            </div>
            <div style={{ fontSize: T.sourceText, color: C.textMuted, marginTop: 8 }}>— Steve Jobs</div>
          </div>
        </div>
      </div>

      {/* ── 10. Subtitle ── */}
      <div style={section}>
        <div style={title}>Subtitle</div>
        <div style={{
          backgroundColor: "rgba(0,0,0,0.6)", padding: "12px 24px",
          borderRadius: 8, display: "inline-block",
        }}>
          <span style={{
            fontSize: preset.subtitle.fontSize,
            fontWeight: preset.subtitle.fontWeight,
            color: preset.subtitle.color,
            WebkitTextStroke: `${preset.subtitle.strokeWidth}px ${preset.subtitle.strokeColor}`,
          }}>
            자막 텍스트 <span style={{ color: preset.subtitle.keywordColor }}>키워드</span> 강조
          </span>
        </div>
      </div>

      {/* ── 11. Mood Gradients ── */}
      <div style={section}>
        <div style={title}>Mood Gradients</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: L.itemsGap }}>
          {Object.entries(preset.moods).map(([name, m]) => (
            <div key={name} style={{
              background: m.gradient || C.bg, borderRadius: L.cardRadius,
              padding: "14px 10px", textAlign: "center", border: `1px solid ${C.divider}`,
            }}>
              <div style={{
                width: 10, height: 10, borderRadius: 5,
                backgroundColor: m.accent || C.accent, margin: "0 auto 6px",
              }} />
              <div style={{ fontSize: 11, fontWeight: 600, color: C.text }}>{name}</div>
              <div style={{ fontSize: 9, color: C.textMuted }}>
                speed: {m.speed ?? "1.0"} · glow: {m.glow ?? "0.3"}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── 12. Layout Tokens Summary ── */}
      <div style={section}>
        <div style={title}>Layout Tokens</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8, fontSize: 11 }}>
          {[
            ["scenePadding", `${L.scenePadding[0]}, ${L.scenePadding[1]}`],
            ["contentWidth", L.contentWidth],
            ["maxContentWidth", L.maxContentWidth],
            ["gap", L.gap],
            ["itemsGap", L.itemsGap],
            ["cardRadius", L.cardRadius],
            ["cardPadding", `${L.cardPadding[0]}, ${L.cardPadding[1]}`],
            ["badgeSize", L.badgeSize],
            ["barHeight", L.barHeight],
            ["barLabelWidth", L.barLabelWidth],
            ["progressBarHeight", L.progressBarHeight],
            ["miniBarHeight", L.miniBarHeight],
          ].map(([k, v]) => (
            <div key={k as string} style={{
              backgroundColor: C.cardBg, border: `1px solid ${C.cardBorder}`,
              borderRadius: 4, padding: "6px 8px",
            }}>
              <div style={{ color: C.textMuted, fontSize: 9 }}>{k}</div>
              <div style={{ color: C.accent, fontWeight: 700 }}>{v}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export const PreviewComposition: React.FC<Props> = ({ designPreset }) => (
  <DesignPresetProvider meta={{ designPreset }}>
    <PreviewContent />
  </DesignPresetProvider>
);
