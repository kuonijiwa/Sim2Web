import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';
const here = fileURLToPath(new URL('.', import.meta.url));
export default defineConfig({
  root: here,
  build: {target:"esnext", outDir: process.env.SIM2WEB_R6_BROWSER_BUILD, emptyOutDir: true, chunkSizeWarningLimit: 1500},
});
