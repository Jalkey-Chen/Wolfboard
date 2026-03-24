import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#111827",
        mist: "#f8fafc",
        accent: "#b91c1c",
        gold: "#d97706",
      },
    },
  },
  plugins: [],
};

export default config;
