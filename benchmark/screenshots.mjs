// Capture a default-view screenshot of a built package (and optionally a probe click).
//   node benchmark/screenshots.mjs --site examples/flac3d_cavern_iv2/site --out shot.png [--field F] [--axis x --index 10] [--probe 0.55,0.5]
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path';
import { chromium } from 'playwright-core';
const a = Object.fromEntries(process.argv.slice(2).reduce((acc, x, i, all) => (x.startsWith('--') ? [...acc, [x.slice(2), all[i + 1]]] : acc), []));
const site = path.resolve(a.site);
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json' };
const srv = http.createServer((q, r) => {
  const f = path.join(site, decodeURIComponent(new URL(q.url, 'http://x').pathname));
  if (!f.startsWith(site) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { r.writeHead(404); r.end(); return; }
  r.writeHead(200, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream' }); r.end(fs.readFileSync(f));
});
await new Promise((r) => srv.listen(0, '127.0.0.1', r));
const browser = await chromium.launch({ executablePath: a.browser || process.env.CHROME_PATH, args: ['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
// Packages built before the rename expose window.__SIMWEBVIEW__; read either name.
await page.addInitScript(() => {
  Object.defineProperty(window, '__SIM2WEB__', {
    configurable: true,
    get() { return this.__sim2webApi || this.__SIMWEBVIEW__; },
    set(v) { this.__sim2webApi = v; },
  });
});
await page.goto(`http://127.0.0.1:${srv.address().port}/index.html${a.hash ? `#${a.hash}` : ''}`);
await page.waitForFunction(() => window.__SIM2WEB__, null, { timeout: 300000 });
if (a.field) await page.evaluate((f) => window.__SIM2WEB__.setField(f), a.field);
if (a.axis) await page.evaluate(([ax, i]) => window.__SIM2WEB__.setSection(ax, Number(i)), [a.axis, a.index ?? 0]);
if (a.probe) {
  const [fx, fy] = a.probe.split(',').map(Number);
  const probe = await page.evaluate(([x, y]) => window.__SIM2WEB__.pickAt(x, y), [fx, fy]);
  console.log(JSON.stringify(probe));
}
await page.waitForTimeout(300);
await page.screenshot({ path: a.out });
await browser.close(); srv.close();
