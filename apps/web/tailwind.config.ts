import type { Config } from "tailwindcss";
import defaultTheme from "tailwindcss/defaultTheme";

// Bảng màu theo UI_NCKH.html — tone xanh dương + trắng "Trọ CTU".
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: "#06305c",
        primary: {
          DEFAULT: "#0b4d8f",
          bright: "#1069bd",
          soft: "#e3effb",
          ring: "#c7ddf5",
        },
        ink: {
          DEFAULT: "#10243a",
          soft: "#3d5871",
          muted: "#5b7189",
          faint: "#8b9cb0",
        },
        line: {
          DEFAULT: "#dde5ee",
          soft: "#eef2f7",
        },
        paper: "#f6f8fb",
        tint: "#f0f4f9",
      },
      fontFamily: {
        sans: ["Segoe UI", "Arial", ...defaultTheme.fontFamily.sans],
      },
    },
  },
  plugins: [],
};

export default config;
