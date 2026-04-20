# Layout Taxonomy and Hierarchy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rework the Remotion layout system so base layouts own the taxonomy, variants become explicit options, quote variants are unified, logo/flag visuals render reliably, and title/items/value hierarchy matches the actual meaning of each layout.

**Architecture:** Keep the existing flat scene schema and renderer structure, but normalize legacy layout names into base-layout + options before rendering. Drive hierarchy changes inside `CreativeScene` and `SceneEditorPanel`, while extending manifest types for explicit options and updating typography defaults so items/value-led layouts stop being dominated by title-like text.

**Tech Stack:** TypeScript, React, Remotion, project-local SceneEditor/manifest pipeline

---

## File Map

### Modify
- `auto_agent/remotion_template/src/types/manifest.ts` — add flat option fields and type-safe layout option shapes for existing scenes and SceneEditor
- `auto_agent/remotion_template/src/components/SceneRenderer.tsx` — pass new flat option fields through visualization resolution
- `auto_agent/remotion_template/src/simple/CreativeScene.tsx` — normalize legacy layouts, apply hierarchy rules, unify quote rendering, and improve logo/flag slot usage
- `auto_agent/remotion_template/src/editor/SceneEditorPanel.tsx` — replace legacy variant layout names in the UI with base layout + options controls
- `auto_agent/remotion_template/src/design/defaults.ts` — retune typography/layout defaults so item/value-led layouts have stronger visual weight
- `remotion/src/types/manifest.ts` — mirror manifest type updates
- `remotion/src/components/SceneRenderer.tsx` — mirror visualization resolution updates
- `remotion/src/simple/CreativeScene.tsx` — mirror renderer logic updates
- `remotion/src/editor/SceneEditorPanel.tsx` — mirror editor updates
- `remotion/src/design/defaults.ts` — mirror typography updates

### Test / Verify
- `auto_agent/remotion_template/src/editor/SceneEditorPanel.tsx` manual option verification in editor
- `auto_agent/remotion_template/src/simple/CreativeScene.tsx` manual scene rendering verification via Remotion/Studio views
- project build commands from `docs/rules/remotion-rules.md`

---

### Task 1: Extend manifest/layout option types

**Files:**
- Modify: `auto_agent/remotion_template/src/types/manifest.ts`
- Modify: `remotion/src/types/manifest.ts`

- [ ] **Step 1: Write the failing type expectation as an inline plan target**

```ts
const scene: VisualizationData = {
  title: "열효율 비교",
  items: ["증기 엔진", "내연기관"],
  values: [10, 30],
  unit: "%",
  source: "",
  creative: {
    concept: "comparison",
    layout: "bar",
    reveal: "fade_in",
    emphasis: "contrast",
    headline: "",
    mood: "informative",
  },
  chartStyle: "donut",
  orientation: "horizontal",
  withPortrait: true,
  portraitPlacement: "left",
};
```

- [ ] **Step 2: Run TypeScript check mentally against current types**

Run: `npm --prefix "/Users/jleavens_macmini/Projects/auto_kairos_v3/remotion" run typecheck`
Expected: FAIL because `chartStyle`, `orientation`, `withPortrait`, and `portraitPlacement` are not declared on `VisualizationData`.

- [ ] **Step 3: Add the minimal type fields**

```ts
export interface VisualizationData {
  title: string;
  items: string[];
  values: number[];
  unit: string;
  source: string;
  chartStyle?: "pie" | "donut";
  orientation?: "vertical" | "horizontal";
  withPortrait?: boolean;
  portraitPlacement?: "left" | "right";
  itemIcons?: string[];
  itemFlags?: string[];
  logoMap?: Record<string, string>;
  creative?: CreativeDirection;
}
```

- [ ] **Step 4: Mirror the same type changes in both src trees**

```ts
// Apply the same VisualizationData additions in:
// - auto_agent/remotion_template/src/types/manifest.ts
// - remotion/src/types/manifest.ts
```

- [ ] **Step 5: Run the typecheck again**

Run: `npm --prefix "/Users/jleavens_macmini/Projects/auto_kairos_v3/remotion" run typecheck`
Expected: PASS for the new option field declarations.

- [ ] **Step 6: Commit**

```bash
git -C "/Users/jleavens_macmini/Projects/auto_kairos_v3/.worktrees/layout-design" add \
  auto_agent/remotion_template/src/types/manifest.ts \
  remotion/src/types/manifest.ts
git -C "/Users/jleavens_macmini/Projects/auto_kairos_v3/.worktrees/layout-design" commit -m "feat(remotion): add layout option fields to manifest"
```

### Task 2: Pass flat option fields through SceneRenderer

**Files:**
- Modify: `auto_agent/remotion_template/src/components/SceneRenderer.tsx`
- Modify: `remotion/src/components/SceneRenderer.tsx`

- [ ] **Step 1: Write the failing behavior target**

```ts
const viz = resolveVisualization({
  layout: "bar",
  title: "열효율 비교",
  items: ["증기 엔진", "내연기관"],
  values: [10, 30],
  orientation: "horizontal",
  chartStyle: "donut",
  withPortrait: true,
  portraitPlacement: "right",
});

expect(viz.orientation).toBe("horizontal");
expect(viz.chartStyle).toBe("donut");
expect(viz.withPortrait).toBe(true);
expect(viz.portraitPlacement).toBe("right");
```

- [ ] **Step 2: Run the current resolver path mentally**

Run: `npm --prefix "/Users/jleavens_macmini/Projects/auto_kairos_v3/remotion" run typecheck`
Expected: FAIL in behavior terms because `resolveVisualization()` does not copy the new fields.

- [ ] **Step 3: Update `resolveVisualization()` to include option fields**

```ts
for (const k of [
  "layout",
  "headline",
  "items",
  "values",
  "unit",
  "source",
  "icons",
  "flags",
  "chartConfig",
  "title",
  "chartStyle",
  "orientation",
  "withPortrait",
  "portraitPlacement",
  "itemIcons",
  "itemFlags",
  "logoMap",
]) {
  if (scene[k] != null) viz[k] = scene[k];
}
```

- [ ] **Step 4: Mirror the change in both src trees**

```ts
// Apply the same `resolveVisualization()` field list in:
// - auto_agent/remotion_template/src/components/SceneRenderer.tsx
// - remotion/src/components/SceneRenderer.tsx
```

- [ ] **Step 5: Run the typecheck again**

Run: `npm --prefix "/Users/jleavens_macmini/Projects/auto_kairos_v3/remotion" run typecheck`
Expected: PASS with the new resolver fields recognized.

- [ ] **Step 6: Commit**

```bash
git -C "/Users/jleavens_macmini/Projects/auto_kairos_v3/.worktrees/layout-design" add \
  auto_agent/remotion_template/src/components/SceneRenderer.tsx \
  remotion/src/components/SceneRenderer.tsx
git -C "/Users/jleavens_macmini/Projects/auto_kairos_v3/.worktrees/layout-design" commit -m "feat(remotion): pass layout options through scene renderer"
```

### Task 3: Normalize legacy layout names into base-layout options

**Files:**
- Modify: `auto_agent/remotion_template/src/simple/CreativeScene.tsx`
- Modify: `remotion/src/simple/CreativeScene.tsx`

- [ ] **Step 1: Write the failing normalization cases**

```ts
expect(normalizeLayoutOptions({ layout: "donut" })).toEqual({
  layout: "pie",
  chartStyle: "donut",
});

expect(normalizeLayoutOptions({ layout: "bar_horizontal" })).toEqual({
  layout: "bar",
  orientation: "horizontal",
});

expect(normalizeLayoutOptions({ layout: "quote_portrait" })).toEqual({
  layout: "quote",
  withPortrait: true,
});
```

- [ ] **Step 2: Run a targeted typecheck mentally**

Run: `npm --prefix "/Users/jleavens_macmini/Projects/auto_kairos_v3/remotion" run typecheck`
Expected: FAIL because `normalizeLayoutOptions` does not exist.

- [ ] **Step 3: Add a small normalization helper near `resolveLayout()`**

```ts
type LayoutOptions = {
  layout: LayoutType;
  chartStyle?: "pie" | "donut";
  orientation?: "vertical" | "horizontal";
  withPortrait?: boolean;
  portraitPlacement?: "left" | "right";
};

function normalizeLayoutOptions(data: any, creative: any): LayoutOptions {
  const explicit = data.layout || creative.layout || "";
  const chartStyle = data.chartStyle || creative.chartStyle;
  const orientation = data.orientation || creative.orientation;
  const withPortrait = data.withPortrait || creative.withPortrait;
  const portraitPlacement = data.portraitPlacement || creative.portraitPlacement || data.imageAsset?.placement;

  if (explicit === "donut") return { layout: "pie", chartStyle: "donut" };
  if (explicit === "bar_horizontal") return { layout: "bar", orientation: "horizontal" };
  if (explicit === "quote_portrait") return { layout: "quote", withPortrait: true, portraitPlacement };

  return {
    layout: resolveLayout(data, creative),
    chartStyle,
    orientation,
    withPortrait,
    portraitPlacement,
  };
}
```

- [ ] **Step 4: Replace direct `resolveLayout()` usage with normalized options**

```ts
const layoutOptions = normalizeLayoutOptions(data, creative);
const layout = layoutOptions.layout;
const chartStyle = layoutOptions.chartStyle || "pie";
const orientation = layoutOptions.orientation || "vertical";
const withPortrait = layoutOptions.withPortrait || false;
const portraitPlacement = layoutOptions.portraitPlacement || "right";
```

- [ ] **Step 5: Mirror the helper and variable replacements in both src trees**

```ts
// Apply the same helper and normalized option variables in:
// - auto_agent/remotion_template/src/simple/CreativeScene.tsx
// - remotion/src/simple/CreativeScene.tsx
```

- [ ] **Step 6: Run typecheck**

Run: `npm --prefix "/Users/jleavens_macmini/Projects/auto_kairos_v3/remotion" run typecheck`
Expected: PASS with no unresolved legacy-only layout handling.

- [ ] **Step 7: Commit**

```bash
git -C "/Users/jleavens_macmini/Projects/auto_kairos_v3/.worktrees/layout-design" add \
  auto_agent/remotion_template/src/simple/CreativeScene.tsx \
  remotion/src/simple/CreativeScene.tsx
git -C "/Users/jleavens_macmini/Projects/auto_kairos_v3/.worktrees/layout-design" commit -m "refactor(remotion): normalize legacy layouts into options"
```

### Task 4: Unify quote rendering and option-driven portrait behavior

**Files:**
- Modify: `auto_agent/remotion_template/src/simple/CreativeScene.tsx`
- Modify: `remotion/src/simple/CreativeScene.tsx`

- [ ] **Step 1: Write the failing behavior target**

```ts
// quote + withPortrait should render the portrait-aware presentation
const scene = {
  title: "",
  items: ["혁신은 느리게 시작된다"],
  withPortrait: true,
  portraitPlacement: "left",
  imageAsset: { placement: "left", opacity: 1 },
};
```

- [ ] **Step 2: Run the current renderer mentally**

Run: `npm --prefix "/Users/jleavens_macmini/Projects/auto_kairos_v3/remotion" run typecheck`
Expected: FAIL in behavior terms because portrait quote is still tied to `quote_portrait` branches.

- [ ] **Step 3: Remove `quote_portrait`-specific routing and gate on options instead**

```ts
const isQuotePortrait = layout === "quote" && withPortrait;

if (layout === "quote") {
  const quoteText = items[0] || data.quote || title || "";
  return (
    <QuoteDisplay
      items={[quoteText]}
      source={data.source || source}
      moodCfg={moodCfg}
      reveal={reveal}
      speed={moodCfg.speed}
      mood={mood}
      hasImageBg={hasImageBackground}
      portrait={isQuotePortrait ? data.images?.[0] : undefined}
    />
  );
}
```

- [ ] **Step 4: Replace `layout === "quote_portrait"` checks with `isQuotePortrait`**

```ts
const isQuotePortrait = layout === "quote" && withPortrait;

{!isQuotePortrait && tags.length > 0 && <TagRow ... />}
style={isQuotePortrait ? portraitStyle : defaultStyle}
```

- [ ] **Step 5: Mirror the quote unification in both src trees**

```ts
// Apply the same quote unification logic in:
// - auto_agent/remotion_template/src/simple/CreativeScene.tsx
// - remotion/src/simple/CreativeScene.tsx
```

- [ ] **Step 6: Run typecheck**

Run: `npm --prefix "/Users/jleavens_macmini/Projects/auto_kairos_v3/remotion" run typecheck`
Expected: PASS with quote portrait behavior driven by options rather than a separate layout name.

- [ ] **Step 7: Commit**

```bash
git -C "/Users/jleavens_macmini/Projects/auto_kairos_v3/.worktrees/layout-design" add \
  auto_agent/remotion_template/src/simple/CreativeScene.tsx \
  remotion/src/simple/CreativeScene.tsx
git -C "/Users/jleavens_macmini/Projects/auto_kairos_v3/.worktrees/layout-design" commit -m "refactor(remotion): unify quote layout variants"
```

### Task 5: Make pie/donut and bar orientation option-driven in rendering

**Files:**
- Modify: `auto_agent/remotion_template/src/simple/CreativeScene.tsx`
- Modify: `remotion/src/simple/CreativeScene.tsx`

- [ ] **Step 1: Write the failing render targets**

```ts
// pie + donut style
const pieScene = { layout: "pie", chartStyle: "donut", items: ["A", "B"], values: [1, 2] };

// bar + horizontal orientation
const barScene = { layout: "bar", orientation: "horizontal", items: ["A", "B"], values: [1, 2] };
```

- [ ] **Step 2: Run typecheck/build mentally**

Run: `npm --prefix "/Users/jleavens_macmini/Projects/auto_kairos_v3/remotion" run typecheck`
Expected: FAIL in behavior terms because rendering is still split on `layout === "donut"` and `layout === "bar_horizontal"`.

- [ ] **Step 3: Update pie rendering to use `chartStyle`**

```ts
if (layout === "pie") {
  return (
    <PieChartDisplay
      items={items}
      values={values}
      unit={unit}
      headline={title}
      moodCfg={moodCfg}
      source={source}
      mood={mood}
      hasImageBg={hasImageBackground}
      chartConfig={{
        ...creative.chartConfig,
        showTotal: chartStyle === "donut" ? true : creative.chartConfig?.showTotal,
      }}
    />
  );
}
```

- [ ] **Step 4: Update bar rendering to use `orientation`**

```ts
if (layout === "bar" && orientation === "horizontal") {
  return <HorizontalBarLayout ... />;
}

if (layout === "bar") {
  return <BarDisplay ... />;
}
```

- [ ] **Step 5: Mirror the option-driven rendering in both src trees**

```ts
// Apply the same pie/bar option-driven rendering in:
// - auto_agent/remotion_template/src/simple/CreativeScene.tsx
// - remotion/src/simple/CreativeScene.tsx
```

- [ ] **Step 6: Run typecheck**

Run: `npm --prefix "/Users/jleavens_macmini/Projects/auto_kairos_v3/remotion" run typecheck`
Expected: PASS with pie/bar variants driven by options instead of separate layout names.

- [ ] **Step 7: Commit**

```bash
git -C "/Users/jleavens_macmini/Projects/auto_kairos_v3/.worktrees/layout-design" add \
  auto_agent/remotion_template/src/simple/CreativeScene.tsx \
  remotion/src/simple/CreativeScene.tsx
git -C "/Users/jleavens_macmini/Projects/auto_kairos_v3/.worktrees/layout-design" commit -m "feat(remotion): drive pie and bar variants from options"
```

### Task 6: Rebuild hierarchy so title supports items/value instead of overpowering them

**Files:**
- Modify: `auto_agent/remotion_template/src/simple/CreativeScene.tsx`
- Modify: `remotion/src/simple/CreativeScene.tsx`
- Modify: `auto_agent/remotion_template/src/design/defaults.ts`
- Modify: `remotion/src/design/defaults.ts`

- [ ] **Step 1: Write the failing layout expectations**

```ts
// before_after
// title = "열효율 비교" should be smaller than engine labels and values

// metric_spotlight
// title = "하루 물가 상승률" should not dominate value 41% and label "독일 초인플레이션(1923)"

// items_list
// title = "전기차가 사라진 이유" should behave like a section title while the reasons stay primary
```

- [ ] **Step 2: Inspect current behavior in the browser/player**

Run: `npm --prefix "/Users/jleavens_macmini/Projects/auto_kairos_v3/remotion" run dev`
Expected: Current scenes still show title/headline-style text too large relative to items/value.

- [ ] **Step 3: Introduce hierarchy helpers in `CreativeScene.tsx`**

```ts
const title = data.title || "";
const showsHeadlineOnly = layout === "headline_only";
const itemPrimaryLayouts = new Set([
  "items_grid", "items_list", "before_after", "comparison_table",
  "metric_wall", "rank_list", "card_carousel", "hero_with_context",
  "timeline", "flow",
]);
const valuePrimaryLayouts = new Set(["counter", "metric_spotlight", "icon_stat"]);

const showHeroHeadline = showsHeadlineOnly;
const showSupportTitle = !showsHeadlineOnly && !!title;
```

- [ ] **Step 4: Replace the common headline block with title-aware rendering**

```tsx
{showHeroHeadline && (
  <div style={{ textAlign: "center", maxWidth: "95%" }}>
    {lines.map((line, i) => (
      <LineReveal key={i} line={line} ... />
    ))}
  </div>
)}

{showSupportTitle && (
  <div style={{
    fontSize: itemPrimaryLayouts.has(layout) ? T.chartTitle * 0.65 : T.chartTitle * 0.8,
    fontWeight: 700,
    color: C.textMuted,
    marginBottom: itemPrimaryLayouts.has(layout) ? 24 : 16,
    textAlign: "center",
  }}>
    <TextWithBreaks text={title} />
  </div>
)}
```

- [ ] **Step 5: Increase primary item/value prominence in the affected layouts**

```tsx
// before_after
<ComparisonCell
  label="BEFORE"
  value={items[0]}
  sublabel={values[0] != null ? `${fmtNum(values[0])}${data.unit || ""}` : undefined}
  style={{ minWidth: 260 }}
/>

// metric_spotlight
<MetricCard
  label={items[0] || ""}
  value={values.length > 0 ? `${fmtNum(values[0])}${data.unit || ""}` : ""}
  style={{ transform: "scale(1.18)" }}
/>
```

- [ ] **Step 6: Adjust default typography values to match the hierarchy**

```ts
typography: {
  headlineAccent: 144,
  headlineBase: 84,
  metricValue: 72,
  itemText: 44,
  descText: 24,
  labelText: 24,
  sourceText: 20,
  chartTitle: 36,
  comparisonLabel: 24,
  comparisonValue: 64,
  metricCardLabel: 28,
}
```

- [ ] **Step 7: Mirror the hierarchy and typography changes in both src trees**

```ts
// Apply the same hierarchy helpers and default typography adjustments in:
// - auto_agent/remotion_template/src/simple/CreativeScene.tsx
// - remotion/src/simple/CreativeScene.tsx
// - auto_agent/remotion_template/src/design/defaults.ts
// - remotion/src/design/defaults.ts
```

- [ ] **Step 8: Run typecheck and visual verification**

Run: `npm --prefix "/Users/jleavens_macmini/Projects/auto_kairos_v3/remotion" run typecheck`
Expected: PASS

Run: `npm --prefix "/Users/jleavens_macmini/Projects/auto_kairos_v3/remotion" run dev`
Expected: `before_after`, `items_list`, and `metric_spotlight` scenes now show title as support text and items/value as primary content.

- [ ] **Step 9: Commit**

```bash
git -C "/Users/jleavens_macmini/Projects/auto_kairos_v3/.worktrees/layout-design" add \
  auto_agent/remotion_template/src/simple/CreativeScene.tsx \
  auto_agent/remotion_template/src/design/defaults.ts \
  remotion/src/simple/CreativeScene.tsx \
  remotion/src/design/defaults.ts
git -C "/Users/jleavens_macmini/Projects/auto_kairos_v3/.worktrees/layout-design" commit -m "feat(remotion): rebalance layout text hierarchy"
```

### Task 7: Restore reliable logo/flag rendering in item-led layouts

**Files:**
- Modify: `auto_agent/remotion_template/src/simple/CreativeScene.tsx`
- Modify: `remotion/src/simple/CreativeScene.tsx`

- [ ] **Step 1: Write the failing behavior target**

```ts
const scene = {
  layout: "before_after",
  title: "열효율 비교",
  items: ["증기 엔진", "내연기관"],
  values: [10, 30],
  itemFlags: ["gb", "de"],
};
```

- [ ] **Step 2: Run visual verification mentally against current code**

Run: `npm --prefix "/Users/jleavens_macmini/Projects/auto_kairos_v3/remotion" run dev`
Expected: FAIL because `before_after`, `comparison_table`, and related layouts do not consistently surface flags/logos.

- [ ] **Step 3: Add a small shared resolver for item-leading visuals**

```ts
const getItemLeadVisual = (index: number) => {
  if (data.itemFlags?.[index]) return { type: "flag", value: data.itemFlags[index] };
  if (data.itemIcons?.[index] && resolveIcon(data.itemIcons[index])) return { type: "icon", value: data.itemIcons[index] };
  if (data.logoMap?.[items[index]] || resolveLogo(items[index])) return { type: "logo", value: data.logoMap?.[items[index]] || items[index] };
  return null;
};
```

- [ ] **Step 4: Render the lead visual in `before_after` and `comparison_table` cells**

```tsx
const lead = getItemLeadVisual(i);

{lead?.type === "flag" && <FlagCard countryCode={lead.value} width={88} />}
{lead?.type === "icon" && <IconBadge icon={resolveIcon(lead.value)!} size={52} />}
{lead?.type === "logo" && resolveLogo(lead.value) && <LogoBadge logo={lead.value} size={52} />}
```

- [ ] **Step 5: Use the same lead visual helper in `metric_wall` / `card_carousel` where appropriate**

```tsx
// Inject the same `getItemLeadVisual(i)` rendering block above the label/value text
// in `metric_wall` and `card_carousel` cards when data exists.
```

- [ ] **Step 6: Mirror the lead-visual logic in both src trees**

```ts
// Apply the same helper and cell/card rendering in:
// - auto_agent/remotion_template/src/simple/CreativeScene.tsx
// - remotion/src/simple/CreativeScene.tsx
```

- [ ] **Step 7: Run visual verification**

Run: `npm --prefix "/Users/jleavens_macmini/Projects/auto_kairos_v3/remotion" run dev`
Expected: scenes with `itemFlags`, `itemIcons`, or `logoMap` now render a visible leading visual instead of silently dropping it.

- [ ] **Step 8: Commit**

```bash
git -C "/Users/jleavens_macmini/Projects/auto_kairos_v3/.worktrees/layout-design" add \
  auto_agent/remotion_template/src/simple/CreativeScene.tsx \
  remotion/src/simple/CreativeScene.tsx
git -C "/Users/jleavens_macmini/Projects/auto_kairos_v3/.worktrees/layout-design" commit -m "feat(remotion): restore logo and flag rendering"
```

### Task 8: Replace legacy variant names in SceneEditor with base layout + options

**Important:** This task is not just UI sync. The SceneEditor must load, edit, save, and reload the same schema that the renderer now expects, so work-in-progress manual edits stay stable.

**Files:**
- Modify: `auto_agent/remotion_template/src/editor/SceneEditorPanel.tsx`
- Modify: `remotion/src/editor/SceneEditorPanel.tsx`

- [ ] **Step 1: Write the failing editor expectation**

```ts
// Existing scene with layout="quote_portrait"
// Editor should show layout="quote" and option withPortrait=true
```

- [ ] **Step 2: Run the editor mentally**

Run: `npm --prefix "/Users/jleavens_macmini/Projects/auto_kairos_v3/remotion" run dev`
Expected: FAIL because the layout select still exposes `quote_portrait` directly and has no option controls.

- [ ] **Step 3: Reduce `LAYOUT_OPTIONS` to base layouts**

```ts
const LAYOUT_OPTIONS = [
  "headline_only", "items_grid", "items_list", "person_card", "counter",
  "quote", "split", "bar", "logo_grid", "pie", "line",
  "flow", "timeline", "metric_spotlight", "metric_wall", "rank_list",
  "comparison_table", "before_after", "icon_stat", "stacked_progress",
  "card_carousel", "hero_with_context", "annotated_chart", "cinematic",
] as const;
```

- [ ] **Step 4: Add normalization for initial editor state**

```ts
const legacyLayout = s.layout || s.sceneType || v.layout || "";
const normalizedLayout = legacyLayout === "quote_portrait"
  ? "quote"
  : legacyLayout === "donut"
    ? "pie"
    : legacyLayout === "bar_horizontal"
      ? "bar"
      : legacyLayout;

const chartStyle = legacyLayout === "donut" ? "donut" : (s.chartStyle || v.chartStyle || "pie");
const orientation = legacyLayout === "bar_horizontal" ? "horizontal" : (s.orientation || v.orientation || "vertical");
const withPortrait = legacyLayout === "quote_portrait" ? true : !!(s.withPortrait || v.withPortrait);
```

- [ ] **Step 5: Add option controls under layout select**

```tsx
{creative.layout === "pie" && (
  <select value={viz.chartStyle || "pie"} onChange={e => updateViz({ chartStyle: e.target.value })}>
    <option value="pie">pie</option>
    <option value="donut">donut</option>
  </select>
)}

{creative.layout === "bar" && (
  <select value={viz.orientation || "vertical"} onChange={e => updateViz({ orientation: e.target.value })}>
    <option value="vertical">vertical</option>
    <option value="horizontal">horizontal</option>
  </select>
)}

{creative.layout === "quote" && (
  <label>
    <input type="checkbox" checked={!!viz.withPortrait} onChange={e => updateViz({ withPortrait: e.target.checked })} />
    portrait
  </label>
)}
```

- [ ] **Step 6: Mirror the editor changes in both src trees**

```ts
// Apply the same base-layout list, normalization, and option controls in:
// - auto_agent/remotion_template/src/editor/SceneEditorPanel.tsx
// - remotion/src/editor/SceneEditorPanel.tsx
```

- [ ] **Step 7: Verify SceneEditor save/load schema sync**

Run: `npm --prefix "/Users/jleavens_macmini/Projects/auto_kairos_v3/remotion" run dev`
Expected:
- SceneEditor shows only base layouts and exposes pie/bar/quote options separately.
- Changing pie ↔ donut, bar orientation, and quote portrait options updates the preview immediately.
- Saving and reloading preserves `chartStyle`, `orientation`, `withPortrait`, and `portraitPlacement` in the edited scene.

- [ ] **Step 8: Commit**

```bash
git -C "/Users/jleavens_macmini/Projects/auto_kairos_v3/.worktrees/layout-design" add \
  auto_agent/remotion_template/src/editor/SceneEditorPanel.tsx \
  remotion/src/editor/SceneEditorPanel.tsx
git -C "/Users/jleavens_macmini/Projects/auto_kairos_v3/.worktrees/layout-design" commit -m "feat(editor): expose layout variants as options"
```

### Task 9: Verify Remotion synchronization and final behavior

**Files:**
- Modify: `auto_agent/remotion_template/src/...`
- Modify: `remotion/src/...`

- [ ] **Step 1: Run the required Remotion builds**

Run: `cd "/Users/jleavens_macmini/Projects/auto_kairos_v3/remotion" && npx vite build --config vite.thumb.config.ts && npx vite build --config vite.editor.config.ts`
Expected: Both builds succeed.

- [ ] **Step 2: Run the main typecheck one last time**

Run: `npm --prefix "/Users/jleavens_macmini/Projects/auto_kairos_v3/remotion" run typecheck`
Expected: PASS

- [ ] **Step 3: Manually verify representative scenes**

Run: `npm --prefix "/Users/jleavens_macmini/Projects/auto_kairos_v3/remotion" run dev`
Expected:
- quote portrait scenes render through `quote + withPortrait`
- pie scenes can switch pie/donut
- bar scenes can switch vertical/horizontal
- before_after shows items/value as primary and title as support
- metric_spotlight shows value as primary and title as support
- logo/flag visuals appear when data exists

- [ ] **Step 4: Check worktree diff**

Run: `git -C "/Users/jleavens_macmini/Projects/auto_kairos_v3/.worktrees/layout-design" status --short`
Expected: Only the planned remotion/template files are modified.

- [ ] **Step 5: Commit**

```bash
git -C "/Users/jleavens_macmini/Projects/auto_kairos_v3/.worktrees/layout-design" add \
  auto_agent/remotion_template/src/types/manifest.ts \
  auto_agent/remotion_template/src/components/SceneRenderer.tsx \
  auto_agent/remotion_template/src/simple/CreativeScene.tsx \
  auto_agent/remotion_template/src/editor/SceneEditorPanel.tsx \
  auto_agent/remotion_template/src/design/defaults.ts \
  remotion/src/types/manifest.ts \
  remotion/src/components/SceneRenderer.tsx \
  remotion/src/simple/CreativeScene.tsx \
  remotion/src/editor/SceneEditorPanel.tsx \
  remotion/src/design/defaults.ts
git -C "/Users/jleavens_macmini/Projects/auto_kairos_v3/.worktrees/layout-design" commit -m "feat(remotion): redesign layout taxonomy and hierarchy"
```
