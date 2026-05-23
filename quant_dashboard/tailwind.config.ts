import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
    "./signal_monitoring/**/*.{js,ts,jsx,tsx,mdx}",
    "./model_intelligence/**/*.{js,ts,jsx,tsx,mdx}",
    "./calibration_intelligence/**/*.{js,ts,jsx,tsx,mdx}",
    "./regime_analytics/**/*.{js,ts,jsx,tsx,mdx}",
    "./replay_visualization/**/*.{js,ts,jsx,tsx,mdx}",
    "./risk_intelligence/**/*.{js,ts,jsx,tsx,mdx}",
    "./notification_analytics/**/*.{js,ts,jsx,tsx,mdx}",
    "./drift_visualization/**/*.{js,ts,jsx,tsx,mdx}",
    "./infra_observability/**/*.{js,ts,jsx,tsx,mdx}",
    "./audit_center/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: "#0b0f14",
          raised: "#121820",
          border: "#1e2a38",
        },
        accent: {
          cyan: "#22d3ee",
          green: "#34d399",
          amber: "#fbbf24",
          red: "#f87171",
        },
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      animation: {
        "pulse-soft": "pulse-soft 2s ease-in-out infinite",
      },
      keyframes: {
        "pulse-soft": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.6" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
