/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // One brand ramp, used everywhere. Defining it here rather than
        // sprinkling hex values through components is what keeps the UI
        // looking like one product.
        brand: {
          50: "#effcf8",
          100: "#d8f7ef",
          200: "#b3eee0",
          300: "#7cddca",
          400: "#42c6ad",
          500: "#18a890",
          600: "#0f8a78",
          700: "#0c7064",
          800: "#0d594f",
          900: "#0e4942",
        },
      },
      fontFamily: {
        sans: [
          "Manrope",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "sans-serif",
        ],
        display: ["Space Grotesk", "Manrope", "sans-serif"],
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0", transform: "translateY(4px)" },
          to: { opacity: "1", transform: "none" },
        },
      },
      animation: { "fade-in": "fade-in 0.2s ease-out" },
    },
  },
  plugins: [],
};
