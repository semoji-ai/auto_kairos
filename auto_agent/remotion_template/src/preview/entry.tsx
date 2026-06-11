import React from "react";
import { createRoot } from "react-dom/client";
import { PreviewApp } from "./PreviewApp";

const root = createRoot(document.getElementById("root")!);
root.render(<PreviewApp />);
