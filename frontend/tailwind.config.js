/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        saffron: {
          50:  '#fff7ed',
          100: '#ffedd5',
          400: '#fb923c',
          500: '#f97316',
          600: '#ea580c',
          700: '#c2410c',
        },
        brand: {
          bg:      '#0f172a',
          card:    '#1e293b',
          border:  '#334155',
          muted:   '#64748b',
          text:    '#f1f5f9',
          accent:  '#f97316',
        },
      },
    },
  },
  plugins: [],
}
