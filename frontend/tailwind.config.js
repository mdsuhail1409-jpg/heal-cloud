/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        hc: {
          bg: "#0B0F19",
          card: "#111827",
          cardHover: "#161F32",
          border: "#1F2937",
          borderHover: "#374151",
          text: "#F9FAFB",
          muted: "#9CA3AF",
          dim: "#6B7280",
          accent: "#3B82F6",
          accentHover: "#2563EB",
          critical: "#EF4444",
          warning: "#F59E0B",
          healthy: "#10B981",
          info: "#3B82F6",
        },
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      boxShadow: {
        card: "0 4px 20px -2px rgba(0, 0, 0, 0.5)",
        modal: "0 20px 50px -10px rgba(0, 0, 0, 0.7)",
      },
    },
  },
  plugins: [],
}

