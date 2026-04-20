/**
 * ImageSelector — 씬 이미지 후보 목록에서 선택
 */
import React, { useState, useEffect } from "react";

interface ImageCandidate {
  id: string;
  url: string;
  file_name: string;
  type: "search" | "generated" | "viz_bg" | "final" | "none";
  selected?: boolean;
  metadata?: Record<string, any>;
}

interface Props {
  slug: string;
  sceneNum: number;
  currentUrl: string;
  accent: string;
  onSelect: (url: string) => void;
  forceExpanded?: boolean;
}

const TYPE_LABELS: Record<string, string> = {
  search: "검색",
  generated: "생성",
  viz_bg: "배경",
  final: "최종",
  none: "없음",
};

export const ImageSelector: React.FC<Props> = ({
  slug,
  sceneNum,
  currentUrl,
  accent,
  onSelect,
  forceExpanded,
}) => {
  const [candidates, setCandidates] = useState<ImageCandidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);
  const [saving, setSaving] = useState(false);

  // 서버에서 받은 selected 기준으로 currentUrl 보정
  const serverSelected = candidates.find((c) => c.selected);
  const effectiveUrl = serverSelected ? serverSelected.url : currentUrl;

  // forceExpanded가 true로 바뀌면 자동 펼치기
  useEffect(() => {
    if (forceExpanded) setExpanded(true);
  }, [forceExpanded]);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/p/${slug}/editor/scenes/${sceneNum}/images`)
      .then((r) => r.json())
      .then((data) => {
        setCandidates(data.candidates || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [slug, sceneNum]);

  if (loading) {
    return (
      <div style={{ fontSize: 11, color: "#71717A" }}>이미지 로딩...</div>
    );
  }

  const handleSelect = async (url: string) => {
    onSelect(url);
    setSaving(true);
    try {
      await fetch(`/api/p/${slug}/editor/scenes/${sceneNum}/select-image`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_url: url }),
      });
    } catch {
      // 에러 무시 — 로컬 상태는 이미 반영됨
    } finally {
      setSaving(false);
    }
  };

  const imgCandidates = candidates.filter((c) => c.type !== "none");
  const isNoneSelected = effectiveUrl === "" && (serverSelected?.id === "__none__" || (!serverSelected && !currentUrl));

  return (
    <div>
      <label
        style={{
          fontSize: 11,
          color: "#71717A",
          marginBottom: 3,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          cursor: "pointer",
        }}
        onClick={() => setExpanded(!expanded)}
      >
        <span>
          이미지 ({imgCandidates.length}개)
          {saving && <span style={{ color: accent, marginLeft: 4 }}>저장중...</span>}
        </span>
        <span style={{ fontSize: 10 }}>{expanded ? "▲" : "▼"}</span>
      </label>

      {/* 현재 이미지 미니 프리뷰 */}
      {effectiveUrl && !isNoneSelected && !expanded && (
        <div
          onClick={() => setExpanded(true)}
          style={{
            width: "100%",
            height: 48,
            borderRadius: 4,
            overflow: "hidden",
            cursor: "pointer",
            border: `1px solid rgba(255,255,255,0.1)`,
          }}
        >
          <img src={effectiveUrl} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        </div>
      )}
      {isNoneSelected && !expanded && (
        <div
          onClick={() => setExpanded(true)}
          style={{ fontSize: 10, color: "#EF4444", padding: "4px 0", cursor: "pointer" }}
        >
          🚫 이미지 없음 (클릭하여 변경)
        </div>
      )}

      {/* 후보 그리드 */}
      {expanded && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: 4,
            maxHeight: 220,
            overflowY: "auto",
          }}
        >
          {/* 이미지 없음 카드 */}
          {(() => {
            const noneSelected = candidates.find((c) => c.id === "__none__")?.selected || isNoneSelected;
            return (
              <div
                onClick={() => handleSelect("")}
                style={{
                  position: "relative",
                  aspectRatio: "16/9",
                  borderRadius: 4,
                  overflow: "hidden",
                  cursor: "pointer",
                  border: noneSelected ? `2px solid #EF4444` : "2px solid rgba(255,255,255,0.1)",
                  background: "rgba(239,68,68,0.08)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexDirection: "column",
                  gap: 2,
                }}
                title="이미지 없음 (source: none)"
              >
                <span style={{ fontSize: 14 }}>🚫</span>
                <span style={{ fontSize: 8, color: noneSelected ? "#EF4444" : "#71717A" }}>없음{noneSelected ? " ✓" : ""}</span>
              </div>
            );
          })()}

          {/* 이미지 후보 */}
          {imgCandidates.map((c) => {
            const isSelected = c.url === effectiveUrl || c.selected;
            return (
              <div
                key={c.id}
                onClick={() => handleSelect(c.url)}
                style={{
                  position: "relative",
                  aspectRatio: "16/9",
                  borderRadius: 4,
                  overflow: "hidden",
                  cursor: "pointer",
                  border: isSelected ? `2px solid ${accent}` : "2px solid transparent",
                  opacity: isSelected ? 1 : 0.7,
                  transition: "all 0.15s",
                }}
                title={`${c.file_name} (${TYPE_LABELS[c.type] || c.type})`}
              >
                <img src={c.url} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                <div
                  style={{
                    position: "absolute",
                    bottom: 0,
                    left: 0,
                    right: 0,
                    padding: "1px 3px",
                    background: "rgba(0,0,0,0.7)",
                    fontSize: 9,
                    color: isSelected ? accent : "#aaa",
                    textAlign: "center",
                  }}
                >
                  {TYPE_LABELS[c.type] || c.type}
                  {isSelected && " ✓"}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
