/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        brand: {
          DEFAULT: "#80CFAE",
          hover: "#6FC29F",
          ink: "#0B1A14",
        },
        primary: {
          DEFAULT: "#80CFAE",
          foreground: "#0B1A14",
        },
        secondary: {
          DEFAULT: "#1e1b4b",
          foreground: "#c7d2fe",
        },
        card: {
          DEFAULT: "#0f172a",
          foreground: "#f8fafc",
        },
      },
    },
  },
  plugins: [],
};
