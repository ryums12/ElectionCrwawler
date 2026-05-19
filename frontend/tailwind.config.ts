import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/hooks/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#080914",
        panel: "#111326",
        line: "#262943",
      },
      boxShadow: {
        glow: "0 20px 70px rgba(91, 88, 255, 0.16)",
      },
    },
  },
  plugins: [],
};

export default config;
