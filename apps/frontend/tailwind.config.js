/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        terminal: {
          bg: '#0a0a0a',
          text: '#10b981',
          'text-dim': '#047857',
          border: '#15803d',
          'border-bright': '#22c55e',
        },
        service: {
          slack: '#a855f7',
          hr: '#3b82f6',
          google: '#ef4444',
          github: '#6b7280',
          jira: '#22c55e',
        },
        status: {
          pending: '#6b7280',
          running: '#eab308',
          success: '#22c55e',
          failed: '#ef4444',
          skipped: '#9ca3af',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Courier New', 'monospace'],
      },
    },
  },
  plugins: [],
}
