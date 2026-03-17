/**
 * ItemsEditor — HTML5 드래그 리오더 + 인라인 편집
 */
import React, { useCallback, useRef, useState } from "react";

interface Props {
  items: string[];
  values: number[];
  descriptions?: string[];
  unit?: string;
  onChange: (items: string[], values: number[], descriptions?: string[]) => void;
  maxItems?: number;
  minItems?: number;
  accent?: string;
}

export const ItemsEditor: React.FC<Props> = ({
  items,
  values,
  descriptions = [],
  unit = "",
  onChange,
  maxItems = 10,
  minItems = 0,
  accent = "#F59E0B",
}) => {
  const [dragIdx, setDragIdx] = useState<number | null>(null);
  const [overIdx, setOverIdx] = useState<number | null>(null);

  const handleDragStart = (e: React.DragEvent, i: number) => {
    setDragIdx(i);
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDragOver = (e: React.DragEvent, i: number) => {
    e.preventDefault();
    setOverIdx(i);
  };

  const handleDrop = (e: React.DragEvent, dropIdx: number) => {
    e.preventDefault();
    if (dragIdx === null || dragIdx === dropIdx) return;

    const newItems = [...items];
    const newVals = [...values];
    const newDescs = [...descriptions];

    const [movedItem] = newItems.splice(dragIdx, 1);
    newItems.splice(dropIdx, 0, movedItem);

    if (newVals.length > 0) {
      const [movedVal] = newVals.splice(dragIdx, 1);
      newVals.splice(dropIdx, 0, movedVal);
    }

    if (newDescs.length > 0) {
      const [movedDesc] = newDescs.splice(dragIdx, 1);
      newDescs.splice(dropIdx, 0, movedDesc);
    }

    onChange(newItems, newVals, newDescs.length > 0 ? newDescs : undefined);
    setDragIdx(null);
    setOverIdx(null);
  };

  const updateItem = (i: number, text: string) => {
    const newItems = [...items];
    newItems[i] = text;
    onChange(newItems, values, descriptions.length > 0 ? descriptions : undefined);
  };

  const updateValue = (i: number, val: string) => {
    const newVals = [...values];
    newVals[i] = parseFloat(val) || 0;
    onChange(items, newVals, descriptions.length > 0 ? descriptions : undefined);
  };

  const removeItem = (i: number) => {
    if (items.length <= minItems) return;
    const newItems = items.filter((_, idx) => idx !== i);
    const newVals = values.filter((_, idx) => idx !== i);
    const newDescs = descriptions.filter((_, idx) => idx !== i);
    onChange(newItems, newVals, newDescs.length > 0 ? newDescs : undefined);
  };

  const addItem = () => {
    if (items.length >= maxItems) return;
    onChange([...items, "새 항목"], [...values, 0], descriptions.length > 0 ? [...descriptions, ""] : undefined);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <div style={{ fontSize: 11, color: "#999", marginBottom: 2 }}>
        Items ({items.length}{maxItems < 10 ? `/${maxItems}` : ""}) — 드래그로 순서 변경
      </div>
      {items.map((item, i) => (
        <div
          key={i}
          draggable
          onDragStart={(e) => handleDragStart(e, i)}
          onDragOver={(e) => handleDragOver(e, i)}
          onDrop={(e) => handleDrop(e, i)}
          onDragEnd={() => { setDragIdx(null); setOverIdx(null); }}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            padding: "4px 6px",
            background: overIdx === i ? "rgba(255,255,255,0.08)" : "rgba(255,255,255,0.03)",
            borderRadius: 4,
            border: dragIdx === i ? `1px solid ${accent}` : "1px solid transparent",
            cursor: "grab",
            transition: "background 0.15s",
          }}
        >
          <span style={{ color: "#666", fontSize: 10, cursor: "grab", userSelect: "none" }}>⠿</span>
          <span style={{ color: accent, fontSize: 11, fontWeight: 700, minWidth: 16 }}>{i + 1}</span>
          <input
            type="text"
            value={item}
            onChange={(e) => updateItem(i, e.target.value)}
            style={{
              flex: 1,
              background: "transparent",
              border: "none",
              borderBottom: "1px solid rgba(255,255,255,0.1)",
              color: "#E4E4E7",
              fontSize: 12,
              padding: "2px 4px",
              outline: "none",
            }}
          />
          {values.length > 0 && (
            <input
              type="text"
              value={values[i] ?? ""}
              onChange={(e) => updateValue(i, e.target.value)}
              style={{
                width: 50,
                background: "transparent",
                border: "none",
                borderBottom: "1px solid rgba(255,255,255,0.1)",
                color: accent,
                fontSize: 12,
                fontWeight: 700,
                textAlign: "right",
                padding: "2px 4px",
                outline: "none",
              }}
            />
          )}
          {items.length > minItems && (
            <button
              onClick={() => removeItem(i)}
              style={{
                background: "transparent",
                border: "none",
                color: "#666",
                cursor: "pointer",
                fontSize: 14,
                padding: "0 2px",
                lineHeight: 1,
              }}
            >
              ×
            </button>
          )}
        </div>
      ))}
      {items.length < maxItems && (
        <button
          onClick={addItem}
          style={{
            background: "transparent",
            border: "1px dashed rgba(255,255,255,0.15)",
            borderRadius: 4,
            color: "#999",
            cursor: "pointer",
            fontSize: 11,
            padding: "4px 8px",
            textAlign: "center",
          }}
        >
          + 항목 추가
        </button>
      )}
    </div>
  );
};
