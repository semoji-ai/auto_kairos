import React, { useState, useEffect } from "react";
import { PreviewComposition } from "./PreviewComposition";
import type { DesignPresetOverride } from "../design/types";

export const PreviewApp: React.FC = () => {
  const [preset, setPreset] = useState<DesignPresetOverride>({});

  useEffect(() => {
    const handler = (e: MessageEvent) => {
      if (e.data?.type === "preset-update" && e.data.preset) {
        setPreset(e.data.preset);
      }
    };
    window.addEventListener("message", handler);
    return () => window.removeEventListener("message", handler);
  }, []);

  return (
    <div style={{
      width: "100%",
      minHeight: "100vh",
      backgroundColor: "#0A0A0A",
      overflowY: "auto",
    }}>
      <PreviewComposition designPreset={preset} />
    </div>
  );
};
