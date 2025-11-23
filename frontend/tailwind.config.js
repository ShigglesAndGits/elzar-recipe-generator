/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'elzar-red': '#e63946',
        'elzar-orange': '#f77f00',
        'elzar-yellow': '#fcbf49',
      },
    },
  },
  plugins: [],
}

