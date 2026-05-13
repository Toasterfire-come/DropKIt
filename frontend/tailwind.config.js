/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    container: {
      center: true,
      padding: "1.5rem",
      screens: { "2xl": "1280px" },
    },
    extend: {
      colors: {
        // DropKit design tokens
        circuit: "#E8510A",      // Primary — Circuit Orange
        solder: "#A8B2B8",       // Secondary — Solder Tin
        pcb: "#0D1117",          // Background dark
        carbon: "#161B22",       // Background mid
        graphite: "#21262D",     // Background light
        warm: "#F0F0EE",         // Text primary
        cool: "#8B949E",         // Text secondary
        flux: "#39D353",         // Success green
        trace: "#58A6FF",        // Info blue
        short: "#FF4444",        // Danger
        border: "#30363D",
        // shadcn aliases
        background: "#0D1117",
        foreground: "#F0F0EE",
      },
      fontFamily: {
        display: ['"Space Grotesk"', "system-ui", "sans-serif"],
        sans: ['"Inter"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      borderRadius: {
        sm: "2px",
        DEFAULT: "2px",
        md: "4px",
        lg: "6px",
      },
      boxShadow: {
        glow: "0 0 16px rgba(232, 81, 10, 0.5)",
        "glow-lg": "0 0 28px rgba(232, 81, 10, 0.6)",
      },
      transitionDuration: {
        150: "150ms",
        300: "300ms",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
