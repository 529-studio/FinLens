import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        background: '#020617', // slate-950
      },
    },
  },
  plugins: [],
} satisfies Config;
