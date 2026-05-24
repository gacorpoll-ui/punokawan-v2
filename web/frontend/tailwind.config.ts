import type { Config } from "tailwindcss"

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: "#090d1a",
          800: "#0f1425",
          700: "#1a1f35",
          600: "#252a45",
        },
        gold: { DEFAULT: "#f0b90b", 500: "#c99a08" },
        profit: "#00c853",
        loss: "#ff1744",
        card: "#111827",
        surface: "#1a1f35",
        muted: "#64748b",
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      animation: {
        "pulse-gold": "pulse-gold 2s infinite",
        "slide-up": "slide-up 0.5s ease-out",
        "glow": "glow 2s ease-in-out infinite alternate",
        "ticker": "ticker 20s linear infinite",
      },
      keyframes: {
        "pulse-gold": {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(240, 185, 11, 0.4)" },
          "50%": { boxShadow: "0 0 0 15px rgba(240, 185, 11, 0)" },
        },
        "slide-up": {
          "0%": { transform: "translateY(20px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        "glow": {
          "0%": { boxShadow: "0 0 5px rgba(240, 185, 11, 0.2)" },
          "100%": { boxShadow: "0 0 20px rgba(240, 185, 11, 0.6)" },
        },
        "ticker": {
          "0%": { transform: "translateX(0)" },
          "100%": { transform: "translateX(-50%)" },
        },
      },
    },
  },
  plugins: [],
}
export default config
