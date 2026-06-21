/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        'next-level': '#6366f1',
        'outgrow': '#f59e0b',
        'be-rolling': '#10b981',
        'admin': '#64748b',
        'personal': '#f43f5e',
        'unknown': '#94a3b8',
      },
    },
  },
  plugins: [],
}
