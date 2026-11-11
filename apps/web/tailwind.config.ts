import type { Config } from "tailwindcss";

export default {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: { extend: { colors: { una: { 50: "#f0f5fa", 700: "#123d6a", 900: "#0a2342" }, oro: "#d6a84b" } } },
  plugins: [],
} satisfies Config;
