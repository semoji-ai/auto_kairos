/**
 * SceneEditorPanel — Player(좌) + 편집 폼(우)
 *
 * 폼에서 씬 속성을 수정하면 Player가 실시간으로 결과를 보여줌 (WYSIWYG)
 * layout, headline, items, mood, reveal, emphasis, placement 등
 * 실제 시스템 속성을 직접 편집 → 렌더 결과가 그대로 반영
 */
import React, { useState, useCallback, useRef, useMemo } from "react";
import { Player, type PlayerRef } from "@remotion/player";
import { SingleScenePlayer } from "./SingleScenePlayer";
import { ItemsEditor } from "./ItemsEditor";
import { ImageSelector } from "./ImageSelector";
import type { SceneEntry, SceneManifest, VisualizationData, CreativeDirection } from "../types/manifest";

const LAYOUT_OPTIONS = [
  "headline_only", "items_grid", "items_list", "person_card", "counter",
  "quote", "split", "bar", "logo_grid", "pie", "line",
  "flow", "timeline", "metric_spotlight", "metric_wall", "rank_list",
  "comparison_table", "before_after", "icon_stat", "stacked_progress",
  "card_carousel", "hero_with_context", "quote_portrait", "annotated_chart",
] as const;

const MOOD_OPTIONS = [
  "dramatic", "contemplative", "urgent", "triumphant",
  "somber", "informative", "suspense",
] as const;

const REVEAL_OPTIONS = [
  "fade_in", "stagger", "stagger_then_flash", "cascade", "count_up",
  "typewriter", "spotlight", "split_reveal", "zoom_in", "build_up",
  "dramatic_pause", "parallel",
] as const;

const EMPHASIS_OPTIONS = [
  "number", "keyword", "count", "contrast", "sequence",
  "person", "quote", "none",
] as const;

const PLACEMENT_OPTIONS = [
  "background", "fullscreen", "center", "left", "right", "inline",
] as const;

interface Props {
  scene: SceneEntry;
  meta: SceneManifest["meta"];
  slug: string;
  onSaved?: () => void;
}

/* ── 스타일 상수 ── */
import { resolvePreset } from "../design/resolvePreset";

const PANEL_BG = "#18181B";
const FORM_BG = "#1E1E22";
const INPUT_BG = "rgba(255,255,255,0.05)";
const BORDER = "rgba(255,255,255,0.1)";
const TEXT = "#E4E4E7";
const MUTED = "#71717A";
const DEFAULT_ACCENT = "#F59E0B";

const labelStyle: React.CSSProperties = {
  fontSize: 11, color: MUTED, marginBottom: 3, display: "block",
};

const selectStyle: React.CSSProperties = {
  width: "100%", background: INPUT_BG, border: `1px solid ${BORDER}`,
  borderRadius: 4, color: TEXT, fontSize: 12, padding: "5px 8px",
  outline: "none", cursor: "pointer",
};

const inputStyle: React.CSSProperties = {
  width: "100%", background: INPUT_BG, border: `1px solid ${BORDER}`,
  borderRadius: 4, color: TEXT, fontSize: 12, padding: "5px 8px",
  outline: "none", boxSizing: "border-box",
};

export const SceneEditorPanel: React.FC<Props> = ({ scene: initialScene, meta, slug, onSaved }) => {
  const [scene, setScene] = useState<SceneEntry>(() => structuredClone(initialScene));
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<string>("");
  const playerRef = useRef<PlayerRef>(null);
  const [showImagePicker, setShowImagePicker] = useState(false);

  // 디자인 프리셋에서 accent 추출
  const _preset = useMemo(() => resolvePreset(meta || {}), [meta?.artStyle, meta?.videoTheme]);
  const ACCENT = _preset.colors?.accent || DEFAULT_ACCENT;

  // 플랫 스키마 + visualization 블록 fallback
  const s = scene as any;
  const v = s.visualization || {};
  const viz = {
    items: s.items || v.items || [],
    values: s.values || v.values || [],
    unit: s.unit ?? v.unit ?? "",
    source: s.source ?? v.source ?? "",
    title: s.title || v.title || "",
    itemIcons: s.icons || v.itemIcons || [],
    itemFlags: s.flags || v.itemFlags || [],
  } as any;
  const _layout = s.layout || s.sceneType || v.layout || "";
  const _headline = s.headline || v.headline || "";
  const creative = {
    layout: _layout,
    headline: _layout === "quote_portrait" ? "" : (_headline || s.title || v.title || ""),
    mood: s.mood || v.mood || "informative",
    motion: s.motion || s.motionPreset || v.motionPreset || "",
    reveal: "fade_in",
    emphasis: "none",
    headlineOffsetX: 0,
    headlineOffsetY: 0,
    itemsOffsetX: 0,
    itemsOffsetY: 0,
    sourceOffsetX: 0,
    sourceOffsetY: 0,
  } as any;

  const fps = meta?.fps || 30;
  const canvasW = meta?.resolution?.width || 1920;
  const canvasH = meta?.resolution?.height || 1080;
  const rawDuration = scene.audioDurationSec
    ? Math.ceil(scene.audioDurationSec * fps)
    : (scene as any).durationFrames || fps * 5;
  const durationInFrames = Math.max(1, rawDuration);

  /* ── 업데이트 헬퍼 (플랫 + visualization 양쪽 동기화) ── */
  const updateField = useCallback((patch: Record<string, any>) => {
    setScene(prev => {
      const next = { ...prev, ...patch };
      // visualization 블록에도 동기화 (SceneRendererInner가 resolveVisualization에서 읽음)
      const oldViz = prev.visualization || {};
      next.visualization = { ...oldViz, ...patch };
      return next;
    });
  }, []);
  const updateViz = updateField;
  const updateCreative = updateField;

  const updateImageAsset = useCallback((patch: Partial<NonNullable<SceneEntry["imageAsset"]>>) => {
    setScene(prev => ({
      ...prev,
      imageAsset: { ...(prev.imageAsset || { placement: "background", opacity: 0.4 }), ...patch },
    }));
  }, []);

  /* ── 저장 ── */
  const handleSave = async () => {
    setSaving(true);
    setStatus("");
    try {
      const resp = await fetch(`/api/p/${slug}/editor/scenes/${scene.sceneNumber}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scene_data: scene, mode: "save" }),
      });
      const result = await resp.json();
      if (result.ok) {
        setStatus("저장 완료");
        fetch(`/api/p/${slug}/rebuild-manifest`, { method: "POST" }).catch(() => {});
        onSaved?.();
      } else {
        setStatus(`오류: ${result.error || "저장 실패"}`);
      }
    } catch (e: any) {
      setStatus(`오류: ${e.message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ display: "flex", gap: 0, height: "100%", background: PANEL_BG, color: TEXT, fontFamily: "'Inter', sans-serif" }}>
      {/* ── 좌: Player ── */}
      <div style={{ flex: "1 1 55%", display: "flex", flexDirection: "column", padding: 12, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: ACCENT }}>
            Scene {scene.sceneNumber}
            {scene.title && <span style={{ color: MUTED, fontWeight: 400, marginLeft: 8, fontSize: 12 }}>{scene.title}</span>}
          </div>
        </div>
        <div style={{
          flex: 1, borderRadius: 8, overflow: "hidden", background: "#000",
          position: "relative", aspectRatio: `${canvasW}/${canvasH}`, maxHeight: "70vh",
        }}>
          <Player
            ref={playerRef}
            component={SingleScenePlayer}
            inputProps={{ scene, meta }}
            durationInFrames={durationInFrames}
            compositionWidth={canvasW}
            compositionHeight={canvasH}
            fps={fps}
            style={{ width: "100%", height: "100%" }}
            controls
            loop
            autoPlay
            initialFrame={Math.min(Math.floor(durationInFrames * 0.4), durationInFrames - 1)}
            acknowledgeRemotionLicense
          />
        </div>
        <div style={{ fontSize: 10, color: MUTED, marginTop: 6, textAlign: "center" }}>
          우측 폼에서 속성을 변경하면 실시간 반영됩니다
        </div>
      </div>

      {/* ── 우: 편집 폼 ── */}
      <div style={{
        flex: "0 0 320px", background: FORM_BG, borderLeft: `1px solid ${BORDER}`,
        overflowY: "auto", padding: "12px 14px", display: "flex", flexDirection: "column", gap: 14,
      }}>
        {/* Layout */}
        <div>
          <label style={labelStyle}>Layout</label>
          <select
            style={selectStyle}
            value={creative.layout || ""}
            onChange={e => updateCreative({ layout: e.target.value })}
          >
            <option value="">자동 (데이터 기반)</option>
            {LAYOUT_OPTIONS.map(l => <option key={l} value={l}>{l}</option>)}
          </select>
        </div>

        {/* Headline */}
        <div>
          <label style={labelStyle}>Headline</label>
          <textarea
            style={{ ...inputStyle, minHeight: 56, resize: "vertical", lineHeight: 1.4 }}
            value={creative.headline || ""}
            onChange={e => updateCreative({ headline: e.target.value })}
            placeholder={"헤드라인 입력... ({{강조}} 가능)\nEnter로 줄바꿈"}
            rows={2}
          />
          <div style={{ fontSize: 9, color: MUTED, marginTop: 2 }}>
            {"{{텍스트}}"} 강조 색상 &nbsp;|&nbsp; Enter 줄바꿈
          </div>
        </div>

        {/* Title */}
        <div>
          <label style={labelStyle}>Title</label>
          <input
            type="text"
            style={inputStyle}
            value={viz.title || ""}
            onChange={e => updateViz({ title: e.target.value })}
            placeholder="시각화 타이틀..."
          />
        </div>

        {/* Items — headline_only 등 items 불필요 레이아웃에서만 숨김 */}
        {!["headline_only", "counter", "quote", "icon_stat", "quote_portrait"].includes(creative.layout || "") && (
          <div>
            <label style={labelStyle}>Items ({(viz.items || []).length})</label>
            <ItemsEditor
              items={viz.items || []}
              values={viz.values || []}
              descriptions={viz.descriptions}
              unit={viz.unit}
              accent={ACCENT}
              onChange={(items, values, descriptions) => updateViz({ items, values, descriptions })}
            />
          </div>
        )}

        {/* Item Icons */}
        {(viz.items || []).length > 0 && (
          <div>
            <label style={labelStyle}>
              Item Icons
              <span style={{ fontSize: 9, color: MUTED, marginLeft: 6 }}>
                모두 지정하거나 모두 비워야 통일됨
              </span>
            </label>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
              {(viz.items || []).map((item: string, i: number) => (
                <select
                  key={i}
                  style={{ ...selectStyle, width: "auto", minWidth: 80, fontSize: 10, padding: "3px 4px" }}
                  value={(viz.itemIcons || [])[i] || ""}
                  onChange={e => {
                    const icons = [...(viz.itemIcons || [])];
                    while (icons.length < (viz.items || []).length) icons.push("");
                    icons[i] = e.target.value;
                    updateViz({ itemIcons: icons });
                  }}
                >
                  <option value="">없음</option>
                  <optgroup label="전쟁/군사">
                    <option value="Swords">Swords</option><option value="Crosshair">Crosshair</option>
                    <option value="Shield">Shield</option><option value="Bomb">Bomb</option><option value="Flag">Flag</option>
                  </optgroup>
                  <optgroup label="비즈니스">
                    <option value="DollarSign">DollarSign</option><option value="BarChart3">BarChart3</option>
                    <option value="Target">Target</option><option value="TrendingUp">TrendingUp</option>
                  </optgroup>
                  <optgroup label="사람/조직">
                    <option value="Users">Users</option><option value="User">User</option>
                    <option value="Building">Building</option><option value="Crown">Crown</option>
                    <option value="Landmark">Landmark</option>
                  </optgroup>
                  <optgroup label="기술">
                    <option value="Brain">Brain</option><option value="Cpu">Cpu</option>
                    <option value="Globe">Globe</option><option value="Network">Network</option>
                  </optgroup>
                  <optgroup label="시간">
                    <option value="Clock">Clock</option><option value="Calendar">Calendar</option>
                    <option value="History">History</option>
                  </optgroup>
                  <optgroup label="감정/에너지">
                    <option value="Zap">Zap</option><option value="Flame">Flame</option>
                    <option value="Heart">Heart</option><option value="Rocket">Rocket</option>
                  </optgroup>
                  <optgroup label="기타">
                    <option value="Star">Star</option><option value="Award">Award</option>
                    <option value="CheckCircle">CheckCircle</option><option value="AlertTriangle">AlertTriangle</option>
                    <option value="Lightbulb">Lightbulb</option><option value="BookOpen">BookOpen</option>
                    <option value="Map">Map</option><option value="MapPin">MapPin</option>
                    <option value="Plane">Plane</option><option value="Ship">Ship</option>
                  </optgroup>
                </select>
              ))}
            </div>
          </div>
        )}

        {/* Mood */}
        <div>
          <label style={labelStyle}>Mood</label>
          <select
            style={selectStyle}
            value={creative.mood || "informative"}
            onChange={e => updateCreative({ mood: e.target.value as any })}
          >
            {MOOD_OPTIONS.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>

        {/* Reveal */}
        <div>
          <label style={labelStyle}>Reveal</label>
          <select
            style={selectStyle}
            value={creative.reveal || "fade_in"}
            onChange={e => updateCreative({ reveal: e.target.value as any })}
          >
            {REVEAL_OPTIONS.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>

        {/* Emphasis */}
        <div>
          <label style={labelStyle}>Emphasis</label>
          <select
            style={selectStyle}
            value={creative.emphasis || "none"}
            onChange={e => updateCreative({ emphasis: e.target.value as any })}
          >
            {EMPHASIS_OPTIONS.map(em => <option key={em} value={em}>{em}</option>)}
          </select>
        </div>

        {/* Image Selector */}
        <ImageSelector
          slug={slug}
          sceneNum={scene.sceneNumber}
          currentUrl={scene.imagePath || scene.vizBackgroundPath || ""}
          accent={ACCENT}
          forceExpanded={showImagePicker}
          onSelect={(url) => {
            setScene(prev => ({
              ...prev,
              imagePath: url,
              vizBackgroundPath: prev.visualization ? url : prev.vizBackgroundPath,
            }));
            setShowImagePicker(false);
          }}
        />

        {/* Image Placement */}
        {scene.imageAsset && (
          <>
            <div>
              <label style={labelStyle}>Image Placement</label>
              <select
                style={selectStyle}
                value={scene.imageAsset?.placement || "background"}
                onChange={e => updateImageAsset({ placement: e.target.value as any })}
              >
                {PLACEMENT_OPTIONS.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label style={labelStyle}>Image Opacity ({((scene.imageAsset?.opacity ?? 0.4) * 100).toFixed(0)}%)</label>
              <input
                type="range"
                min="0" max="1" step="0.05"
                value={scene.imageAsset?.opacity ?? 0.4}
                onChange={e => updateImageAsset({ opacity: parseFloat(e.target.value) })}
                style={{ width: "100%", accentColor: ACCENT }}
              />
            </div>
          </>
        )}

        {/* Ken Burns */}
        {scene.kenBurns && (
          <div>
            <label style={{ ...labelStyle, display: "flex", alignItems: "center", gap: 6 }}>
              <input
                type="checkbox"
                checked={scene.kenBurns.enabled}
                onChange={e => setScene(prev => ({
                  ...prev,
                  kenBurns: { ...prev.kenBurns, enabled: e.target.checked },
                }))}
                style={{ accentColor: ACCENT }}
              />
              Ken Burns
            </label>
            {scene.kenBurns.enabled && (
              <div style={{ marginTop: 4 }}>
                <label style={labelStyle}>Zoom Factor ({scene.kenBurns.zoomFactor.toFixed(2)})</label>
                <input
                  type="range"
                  min="1" max="1.5" step="0.01"
                  value={scene.kenBurns.zoomFactor}
                  onChange={e => setScene(prev => ({
                    ...prev,
                    kenBurns: { ...prev.kenBurns, zoomFactor: parseFloat(e.target.value) },
                  }))}
                  style={{ width: "100%", accentColor: ACCENT }}
                />
              </div>
            )}
          </div>
        )}

        {/* Source */}
        <div>
          <label style={labelStyle}>Source</label>
          <input
            type="text"
            style={inputStyle}
            value={viz.source || ""}
            onChange={e => updateViz({ source: e.target.value })}
            placeholder="출처..."
          />
        </div>

        {/* Position Controls */}
        <div>
          <label style={{ ...labelStyle, fontSize: 12, fontWeight: 600, marginBottom: 8 }}>위치 조절</label>

          {/* Headline 위치 */}
          <div style={{ marginBottom: 10 }}>
            <label style={labelStyle}>Headline</label>
            <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <span style={{ fontSize: 9, color: MUTED, width: 12 }}>X</span>
              <input type="range" min={-960} max={960} step={10}
                value={creative.headlineOffsetX || 0}
                onChange={e => updateCreative({ headlineOffsetX: parseInt(e.target.value) } as any)}
                style={{ flex: 1, accentColor: ACCENT }} />
              <span style={{ fontSize: 9, color: TEXT, width: 32, textAlign: "right" }}>{creative.headlineOffsetX || 0}</span>
            </div>
            <div style={{ display: "flex", gap: 6, alignItems: "center", marginTop: 2 }}>
              <span style={{ fontSize: 9, color: MUTED, width: 12 }}>Y</span>
              <input type="range" min={-540} max={540} step={10}
                value={creative.headlineOffsetY || 0}
                onChange={e => updateCreative({ headlineOffsetY: parseInt(e.target.value) } as any)}
                style={{ flex: 1, accentColor: ACCENT }} />
              <span style={{ fontSize: 9, color: TEXT, width: 32, textAlign: "right" }}>{creative.headlineOffsetY || 0}</span>
            </div>
          </div>

          {/* Items 위치 */}
          <div style={{ marginBottom: 10 }}>
            <label style={labelStyle}>Items</label>
            <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <span style={{ fontSize: 9, color: MUTED, width: 12 }}>X</span>
              <input type="range" min={-960} max={960} step={10}
                value={creative.itemsOffsetX || 0}
                onChange={e => updateCreative({ itemsOffsetX: parseInt(e.target.value) } as any)}
                style={{ flex: 1, accentColor: ACCENT }} />
              <span style={{ fontSize: 9, color: TEXT, width: 32, textAlign: "right" }}>{creative.itemsOffsetX || 0}</span>
            </div>
            <div style={{ display: "flex", gap: 6, alignItems: "center", marginTop: 2 }}>
              <span style={{ fontSize: 9, color: MUTED, width: 12 }}>Y</span>
              <input type="range" min={-540} max={540} step={10}
                value={creative.itemsOffsetY || 0}
                onChange={e => updateCreative({ itemsOffsetY: parseInt(e.target.value) } as any)}
                style={{ flex: 1, accentColor: ACCENT }} />
              <span style={{ fontSize: 9, color: TEXT, width: 32, textAlign: "right" }}>{creative.itemsOffsetY || 0}</span>
            </div>
          </div>

          {/* Source 위치 */}
          <div style={{ marginBottom: 6 }}>
            <label style={labelStyle}>출처</label>
            <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <span style={{ fontSize: 9, color: MUTED, width: 12 }}>X</span>
              <input type="range" min={-960} max={960} step={10}
                value={creative.sourceOffsetX || 0}
                onChange={e => updateCreative({ sourceOffsetX: parseInt(e.target.value) } as any)}
                style={{ flex: 1, accentColor: ACCENT }} />
              <span style={{ fontSize: 9, color: TEXT, width: 32, textAlign: "right" }}>{creative.sourceOffsetX || 0}</span>
            </div>
            <div style={{ display: "flex", gap: 6, alignItems: "center", marginTop: 2 }}>
              <span style={{ fontSize: 9, color: MUTED, width: 12 }}>Y</span>
              <input type="range" min={-540} max={540} step={10}
                value={creative.sourceOffsetY || 0}
                onChange={e => updateCreative({ sourceOffsetY: parseInt(e.target.value) } as any)}
                style={{ flex: 1, accentColor: ACCENT }} />
              <span style={{ fontSize: 9, color: TEXT, width: 32, textAlign: "right" }}>{creative.sourceOffsetY || 0}</span>
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button
              onClick={() => updateCreative({ headlineOffsetX: 0, headlineOffsetY: 0, itemsOffsetX: 0, itemsOffsetY: 0, sourceOffsetX: 0, sourceOffsetY: 0 } as any)}
              style={{ fontSize: 9, color: MUTED, background: "none", border: `1px solid ${BORDER}`, borderRadius: 3, padding: "2px 8px", cursor: "pointer" }}
            >
              전체 리셋
            </button>
          </div>
        </div>

        {/* Save */}
        <div style={{ marginTop: "auto", paddingTop: 12, borderTop: `1px solid ${BORDER}` }}>
          <button
            onClick={handleSave}
            disabled={saving}
            style={{
              width: "100%", padding: "8px 16px", background: ACCENT, color: "#000",
              border: "none", borderRadius: 6, fontWeight: 700, fontSize: 13,
              cursor: saving ? "wait" : "pointer", opacity: saving ? 0.6 : 1,
            }}
          >
            {saving ? "저장 중..." : "저장"}
          </button>
          {status && (
            <div style={{ fontSize: 11, color: status.startsWith("오류") ? "#EF4444" : "#22C55E", marginTop: 6, textAlign: "center" }}>
              {status}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
