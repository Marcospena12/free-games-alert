/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/renderer/index.html', './src/renderer/src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#F7F7F5',
        surface: '#FFFFFF',
        border: '#E7E5E4',
        ink: {
          DEFAULT: '#18181B',
          muted: '#71717A',
          faint: '#A1A1AA',
        },
        accent: {
          DEFAULT: '#4F46E5',
          soft: '#EEF2FF',
        },
        free: '#16A34A',
        warn: '#D97706',
        danger: '#DC2626',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      borderRadius: {
        card: '12px',
        cover: '8px',
      },
      boxShadow: {
        card: '0 1px 2px rgba(24,24,27,0.04)',
        pop: '0 8px 24px rgba(24,24,27,0.10)',
      },
      transitionDuration: {
        fast: '150ms',
        base: '200ms',
      },
    },
  },
  plugins: [],
}
