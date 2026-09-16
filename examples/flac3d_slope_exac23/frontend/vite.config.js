import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { fileURLToPath, URL } from 'node:url';

const frontendRoot = fileURLToPath(new URL('.', import.meta.url));

export default defineConfig({
  root: frontendRoot,
  base: './',
  publicDir: fileURLToPath(new URL('../output', import.meta.url)),
  plugins: [vue()],
  build: { outDir: 'dist', emptyOutDir: true },
});
