import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: "#ff6a00", dark: "#cc5500" },
      },
    },
  },
  plugins: [],
} satisfies Config;
