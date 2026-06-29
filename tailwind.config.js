/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./templates/**/*.html"],
  theme: {
    extend: {
      colors: {
        gray: {
          50: "#f7f6f2",
          100: "#efeee8",
          200: "#deddd5",
          300: "#c3c8c7",
          400: "#819097",
          500: "#60717a",
          600: "#435b66",
          700: "#294a56",
          800: "#163846",
          900: "#112e3b",
        },
        indigo: {
          50: "#fff3f1",
          100: "#ffe1dd",
          300: "#f5a09a",
          400: "#ee685f",
          500: "#e93b32",
          600: "#e32219",
          700: "#bd1d16",
        },
      },
    },
  },
  plugins: [],
};
