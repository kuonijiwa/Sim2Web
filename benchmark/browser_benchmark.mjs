#!/usr/bin/env node
// Browser-side benchmark and browser-level verification for a built package.
//
//   node benchmark/browser_benchmark.mjs --site examples/flac3d_slope_exac23/site \
//        [--browser /path/to/chrome] [--runs 3] [--sections 10] [--frames 120] \
//        [--gzip] [--headless false] [--out results.json]
//
// For every run a fresh browser profile is used and the HTTP cache is disabled,
// so "initial load" means a cold start.  The script records:
//   * time from navigation to the first rendered image and the bytes requested
//     before it (startup transfer), split by file;
//   * section-switching latency for evenly spaced, not previously loaded sections;
//   * frame rate while the camera rotates;
//   * JS heap (Chromium) after startup and after the section sweep;
//   * for every section shown, which array/association each visible actor is
//     coloured by and whether it matches the index (browser-level verification).
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import os from 'node:os';
import { chromium } from 'playwright-core';

const args = Object.fromEntries(process.argv.slice(2).reduce((acc, a, i, all) => {
  if (a.startsWith('--')) acc.push([a.slice(2), all[i + 1] && !all[i + 1].startsWith('--') ? all[i + 1] : 'true']);
  return acc;
}, []));
const site = path.resolve(args.site || '.');
const runs = Number(args.runs || 3);
const perAxis = Number(args.sections || 10);
const frames = Number(args.frames || 120);
const gzip = args.gzip === 'true';
const headless = args.headless !== 'false';
const browserPath = args.browser || process.env.CHROME_PATH || undefined;

const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.vtp': 'application/octet-stream' };
let served = [];
const server = http.createServer((req, res) => {
  const url = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  const file = path.join(site, url === '/' ? 'index.html' : url);
  if (!file.startsWith(site) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); res.end(); return; }
  let body = fs.readFileSync(file);
  const headers = { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream', 'Cache-Control': 'no-store' };
  if (gzip && /gzip/.test(req.headers['accept-encoding'] || '')) { body = zlib.gzipSync(body, { level: 6 }); headers['Content-Encoding'] = 'gzip'; }
  headers['Content-Length'] = body.length;
  served.push({ url, bytes: body.length });
  res.writeHead(200, headers);
  res.end(body);
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const base = `http://127.0.0.1:${server.address().port}/`;
const index = JSON.parse(fs.readFileSync(path.join(site, 'model_cache/index.json'), 'utf8'));

const results = { site: path.relative(process.cwd(), site), gzip, host: { platform: `${os.platform()} ${os.release()}`, cpus: os.cpus()[0]?.model, cores: os.cpus().length, memoryGiB: +(os.totalmem() / 2 ** 30).toFixed(1) }, runs: [] };

for (let run = 0; run < runs; run += 1) {
  served = [];
  const browser = await chromium.launch({ executablePath: browserPath, headless,
    args: ['--enable-precise-memory-info', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
  const context = await browser.newContext({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1 });
  const page = await context.newPage();
  const cdp = await context.newCDPSession(page);
  await cdp.send('Network.enable');
  await cdp.send('Network.setCacheDisabled', { cacheDisabled: true });
  await cdp.send('Performance.enable');
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  const t0 = Date.now();
  // Packages built before the rename expose window.__SIMWEBVIEW__; read either name.
await page.addInitScript(() => {
  Object.defineProperty(window, '__SIM2WEB__', {
    configurable: true,
    get() { return this.__sim2webApi || this.__SIMWEBVIEW__; },
    set(v) { this.__sim2webApi = v; },
  });
});
await page.goto(`${base}index.html?prefetch=0`);
  await page.waitForFunction(() => window.__SIM2WEB__ && window.__SIM2WEB__.summary().events.firstRender, null, { timeout: 600000 });
  const wall = Date.now() - t0;
  const summary = await page.evaluate(() => window.__SIM2WEB__.summary());
  const gl = await page.evaluate(() => {
    const c = document.createElement('canvas').getContext('webgl2');
    const ext = c && c.getExtension('WEBGL_debug_renderer_info');
    return ext ? c.getParameter(ext.UNMASKED_RENDERER_WEBGL) : (c ? c.getParameter(c.RENDERER) : 'no WebGL2');
  });
  const heapStart = await heap(cdp);
  const record = {
    run: run + 1, browser: browser.version(), renderer: gl,
    navigationToFirstImageMs: summary.events.firstRender, indexToFirstImageMs: summary.events.firstRender - summary.events.index,
    wallClockMs: wall, startupBytes: summary.startupBytes,
    startupFiles: summary.startupFiles.map((f) => ({ file: f.url.replace(base, ''), bytes: f.bytes, fetchMs: +f.fetchMs.toFixed(1), parseMs: +f.parseMs.toFixed(1) })),
    serverBytesAtStartup: served.reduce((s, f) => s + f.bytes, 0),
    heapAfterStartupMiB: heapStart, sectionSwitches: [], verification: [], errors,
  };
  // section sweep
  const stage = index.stages[0];
  const field = index.viewer.default_field;
  for (const axis of ['x', 'y', 'z']) {
    const n = stage.sections[axis]?.length || 0;
    if (!n) continue;
    const picks = [...new Set(Array.from({ length: Math.min(perAxis, n) }, (_, i) => Math.round((i * (n - 1)) / Math.max(1, Math.min(perAxis, n) - 1))))];
    for (const k of picks) {
      const sw = await page.evaluate(([a, i]) => window.__SIM2WEB__.setSection(a, i), [axis, k]);
      record.sectionSwitches.push({ axis, value: sw.value, ms: +sw.ms.toFixed(1), cached: sw.cached, bytes: sw.bytes });
      const actors = await page.evaluate(() => window.__SIM2WEB__.describeActors());
      const meta = index.fields[field];
      for (const [id, a] of Object.entries(actors)) {
        const ok = !a.scalarVisibility || (a.array === field && a.association === meta.association && a.arrayFound);
        const inRange = !a.dataRange || (a.dataRange[0] >= stage.fields[field].min - 1e-6 * Math.abs(stage.fields[field].min) - 1e-12
          && a.dataRange[1] <= stage.fields[field].max + 1e-6 * Math.abs(stage.fields[field].max) + 1e-12);
        record.verification.push({ axis, index: k, actor: id, ...a, matchesIndex: ok, dataWithinIndexedRange: inRange });
      }
    }
  }
  record.heapAfterSweepMiB = await heap(cdp);
  await page.evaluate(() => window.__SIM2WEB__.resetCamera());
  record.frameRate = await page.evaluate((f) => window.__SIM2WEB__.measureFrameRate(f, 3), frames);
  if (run === 0 && args.screenshot) await page.screenshot({ path: args.screenshot });
  const sw = record.sectionSwitches.map((s) => s.ms).sort((a, b) => a - b);
  record.sectionSwitchMedianMs = sw[Math.floor(sw.length / 2)];
  record.sectionSwitchMaxMs = sw[sw.length - 1];
  record.verificationPassed = record.verification.every((v) => v.matchesIndex && v.dataWithinIndexedRange);
  results.runs.push(record);
  console.log(`run ${run + 1}: first image ${record.navigationToFirstImageMs.toFixed(0)} ms, startup ${(record.startupBytes / 1e6).toFixed(2)} MB, `
    + `section switch median ${record.sectionSwitchMedianMs} ms (max ${record.sectionSwitchMaxMs}), `
    + `${record.frameRate.fps.toFixed(1)} fps, heap ${record.heapAfterStartupMiB}→${record.heapAfterSweepMiB} MiB, `
    + `verification ${record.verificationPassed ? 'passed' : 'FAILED'}${errors.length ? `, ${errors.length} page error(s)` : ''}`);
  await browser.close();
}
server.close();
if (args.out) fs.writeFileSync(args.out, `${JSON.stringify(results, null, 2)}\n`);

async function heap(cdp) {
  const { metrics } = await cdp.send('Performance.getMetrics');
  const used = metrics.find((m) => m.name === 'JSHeapUsedSize')?.value;
  return used ? +(used / 2 ** 20).toFixed(1) : null;
}
