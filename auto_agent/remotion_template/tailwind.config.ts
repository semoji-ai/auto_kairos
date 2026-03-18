import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        theme: {
          bg: "var(--viz-bg)",
          text: "var(--viz-text)",
          subtitle: "var(--viz-subtitle)",
          source: "var(--viz-source)",
          grid: "var(--viz-grid)",
          card: "var(--viz-card-bg)",
          border: "var(--viz-border)",
          accent: "var(--viz-color-0)",
          "color-0": "var(--viz-color-0)",
          "color-1": "var(--viz-color-1)",
          "color-2": "var(--viz-color-2)",
          "color-3": "var(--viz-color-3)",
          "color-4": "var(--viz-color-4)",
          "color-5": "var(--viz-color-5)",
          "color-6": "var(--viz-color-6)",
          "color-7": "var(--viz-color-7)",
          "color-8": "var(--viz-color-8)",
          "color-9": "var(--viz-color-9)",
          positive: "var(--viz-positive)",
          "positive-bg": "var(--viz-positive-bg)",
          negative: "var(--viz-negative)",
          "negative-bg": "var(--viz-negative-bg)",
        },
      },
      fontFamily: {
        viz: ["var(--viz-font)"],
        "viz-title": ["var(--viz-title-font)"],
      },
      fontSize: {
        "viz-title": "var(--viz-title-size)",
        "viz-hero": "var(--viz-hero-size)",
        "viz-subtitle": "var(--viz-subtitle-size)",
        "viz-label": "var(--viz-label-size)",
        "viz-value": "var(--viz-value-size)",
        "viz-caption": "var(--viz-caption-size)",
      },
      fontWeight: {
        "viz-title": "var(--viz-title-weight)",
        "viz-hero": "var(--viz-hero-weight)",
        "viz-subtitle": "var(--viz-subtitle-weight)",
        "viz-label": "var(--viz-label-weight)",
        "viz-value": "var(--viz-value-weight)",
        "viz-caption": "var(--viz-caption-weight)",
      },
      letterSpacing: {
        "viz-title": "var(--viz-title-tracking)",
        "viz-hero": "var(--viz-hero-tracking)",
      },
      borderRadius: {
        "viz-card": "var(--viz-card-radius)",
      },
      boxShadow: {
        "viz-card": "var(--viz-card-shadow)",
      },
    },
  },
  plugins: [],
};

export default config;
