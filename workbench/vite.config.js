// The processing workbench served by `sim2web gui`.  `npm run build:workbench`
// writes the static build into the Python package (src/sim2web/workbench_dist).
//
// Development: run `sim2web gui <project> --no-browser` and `npm run dev:workbench`;
// API and package requests are forwarded to the Python server on port 8765.
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { fileURLToPath, URL } from 'node:url';

const backend = process.env.SIM2WEB_GUI ?? 'http://127.0.0.1:8765';

export default defineConfig({
  root: fileURLToPath(new URL('.', import.meta.url)),
  base: './',
  plugins: [vue()],
  server: { proxy: { '/api': backend, '/site': backend, '/preview': backend } },
  build: {
    outDir: fileURLToPath(new URL('../src/sim2web/workbench_dist', import.meta.url)),
    emptyOutDir: true,
  },
});
