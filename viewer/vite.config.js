// One data-driven viewer for every package.  `npm run build:viewer` writes the
// static build into the Python package (src/sim2web/viewer_dist), from where
// `sim2web build` copies it next to the data products.
//
// For development against a built package:
//   SIM2WEB_SITE=examples/flac3d_slope_exac23/site npm run dev:viewer
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { fileURLToPath, URL } from 'node:url';
import { resolve } from 'node:path';

const root = fileURLToPath(new URL('.', import.meta.url));
const site = process.env.SIM2WEB_SITE ? resolve(process.cwd(), process.env.SIM2WEB_SITE) : false;

export default defineConfig({
  root,
  base: './',
  publicDir: site,
  plugins: [vue()],
  build: {
    outDir: fileURLToPath(new URL('../src/sim2web/viewer_dist', import.meta.url)),
    emptyOutDir: true,
    chunkSizeWarningLimit: 2000,
  },
});
