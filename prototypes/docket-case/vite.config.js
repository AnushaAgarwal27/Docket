import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Same-origin path for the live IRS Publication 519 check during local dev.
      '/api/p519': {
        target: 'https://www.irs.gov',
        changeOrigin: true,
        rewrite: () => '/publications/p519',
      },
    },
  },
});
