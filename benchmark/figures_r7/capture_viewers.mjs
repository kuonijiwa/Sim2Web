import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { staticServer } from '../web_slicing/serve.mjs';
import { deviceScaleFactor, measureText, openBrowser, paint, writeJson } from './capture_common.mjs';

const [statePath, output, selected = 'ABCDEF'] = process.argv.slice(2);
const states = JSON.parse(await fs.readFile(statePath, 'utf8'));
const viewerCss = `.panel.collapsed { display: none !important; }
.right { top: 8px !important; right: 8px !important; bottom: auto !important; gap: 0 !important; }
.legend { width: 232px; min-width: 0 !important; padding: 10px; box-shadow: none !important; background: #fff !important; }
.legend-title { font: 700 38px/1.06 'Arial Narrow', Arial, sans-serif !important; color: #1f2d3d; margin-bottom: 14px !important; }
.legend-sub { display: none !important; }
.bands { font: 400 36px/1 Arial, sans-serif !important; font-variant-numeric: tabular-nums; }
.band-row { height: 39px !important; gap: 7px !important; }
.band-row .tick { transform: translateY(-5px) !important; white-space: nowrap; }
.band-row .swatch { flex: 0 0 16px; }
.band-row .swatch.tall { height: 39px !important; }
.band-row.last { height: 30px !important; }
`;
const probeCss = `.probe { position: fixed; left: 8px; top: 8px; width: 706px !important; max-height: none !important;
  padding: 7px 11px; box-shadow: none !important; background: #fff !important; }
.probe-head { font-size: 27px !important; }
.probe-head .link { display: none; }
.probe .kv { font-size: 26px !important; margin-top: 2px !important; }
.probe .kv td { padding: 2px 4px !important; }
.probe .kv tr:not(:nth-child(2)):not(.active) { display: none; }
`;

async function pickOriginalCell(page, state) {
  // The viewer probe API uses the WebGL bottom-left origin.
  const pick = coords => page.evaluate(([x,y]) => (window.__SIM2WEB__ || window.__SIMWEBVIEW__).pickAt(x,1-y), coords);
  const {right, up, px_per_m: scale} = state.probe_projection;
  const dot = (a, b) => a.reduce((sum, component, i) => sum + component*b[i], 0);
  for (const target of state.probe_targets) {
    let p = target.canvas;
    for (let correction = 0; correction < 3; correction++) {
      const hit = await pick(p);
      if (hit?.sourceCell === state.probe_cell_id) return hit;
      if (!hit?.position) break;
      const delta = target.world.map((coord, i) => coord-hit.position[i]);
      p = [p[0]+dot(delta, right)*scale/960, p[1]-dot(delta, up)*scale/600];
    }
    // A small cut polygon can occupy only a few device pixels.
    for (const radius of [0, 1/3, 2/3, 1, 1.5, 2, 3]) {
      for (const [dx,dy] of [[0,0],[-1,0],[1,0],[0,-1],[0,1],[-1,-1],[-1,1],[1,-1],[1,1]]) {
        const hit = await pick([p[0]+dx*radius/960,p[1]+dy*radius/600]);
        if (hit?.sourceCell === state.probe_cell_id) return hit;
      }
    }
  }
  throw Error('Could not select the original source cell');
}

const browser = await openBrowser();
try {
  const records = {};
  for (const caseId of selected) {
    const state = states[caseId];
    const server = await staticServer(state.site, { gzip: false });
    const page = await browser.newPage({ viewport: { width: 960, height: 600 }, deviceScaleFactor });
    page.on('pageerror', error => console.error(error.message));
    try {
      const hash = new URLSearchParams({ field: state.field, range: state.range, section: state.axis ? '1' : '0',
        parallel: '1', cmap: 'jet', bands: '8', cam: state.camera.join(','), layers: state.layers.join(',') });
      if (state.axis) {
        hash.set('axis', state.axis);
        hash.set('pos', String(state.position_m));
      }
      await page.goto(`${server.url}/index.html?prefetch=0#${hash}`);
      await page.waitForFunction(() => (window.__SIM2WEB__ || window.__SIMWEBVIEW__)?.summary()?.events.firstRender,
        null, { timeout: 240000 });
      const coloring = await page.evaluate(() => (window.__SIM2WEB__ || window.__SIMWEBVIEW__).activeColoring());
      assert.equal(coloring.name, state.field);
      const visible = await page.evaluate(() => Object.keys((window.__SIM2WEB__ || window.__SIMWEBVIEW__).describeActors()));
      const expected = state.layers.filter(layer => layer.split(':')[1] === '1').map(layer => `layer:${layer.split(':')[0]}`);
      if (state.axis) expected.push('section');
      assert.deepEqual(visible.sort(), expected.sort());
      if (state.axis) assert.match(await page.locator('.panel section:has(.tabs) p.hint').innerText(),
        new RegExp(`^${state.axis.toUpperCase()} = ${state.position_m}(?:\\.0+)? m`));

      let probe;
      if (caseId === 'A') {
        const excavation = page.locator('.panel .layer input[type=checkbox]');
        await excavation.uncheck();
        probe = await pickOriginalCell(page, state);
        await excavation.check();
        assert.equal(probe?.sourceCell, state.probe_cell_id, 'Original source cell was not picked');
        assert.equal(probe.rows.find(row => row.name === state.field)?.text, '-6.857 MPa');
      }
      await page.locator('.panel .collapse').click();
      await page.locator('.panel.collapsed').waitFor();
      const css = viewerCss+(caseId === 'A' ? probeCss : '');
      await page.addStyleTag({ content: css });
      await paint(page);
      const legend = await page.locator('.legend').boundingBox();
      const legendItems = await page.locator('.legend-title, .tick').evaluateAll(nodes => nodes.map(node => {
        const range = document.createRange();
        range.selectNodeContents(node);
        return Array.from(range.getClientRects(), box => ({ left: box.left, right: box.right, top: box.top, bottom: box.bottom }));
      }).flat());
      assert(legendItems.length >= 10, `Missing legend labels for ${caseId}`);
      assert(legendItems.every(rect => rect.left >= legend.x && rect.right <= 959 && rect.top >= 0 && rect.bottom <= 600),
        `Legend overflows in ${caseId}: ${JSON.stringify(legendItems.filter(r => r.right > 959 || r.bottom > 600))}`);
      const probeCard = caseId === 'A' ? await page.locator('.probe').boundingBox() : null;
      if (probeCard) assert(probeCard.y + probeCard.height < 146, 'The probe intrudes into the model framing region');
      const text = await measureText(page, {
        legend_title: '.legend-title', legend_tick: '.tick', ...(caseId === 'A' ? { probe: '.probe-head b, .probe tr td' } : {}),
      });
      await page.screenshot({ path: path.join(output, `fig4_${caseId.toLowerCase()}.png`), scale: 'device' });
      const record = { deviceScaleFactor, viewport: { width: 960, height: 600 },
        field: state.field, axis: state.axis, position_m: state.position_m, range: state.range,
        injectedCss: css, legend, text };
      if (probeCard) record.probe = { cell: probe.sourceCell,
        minimum_stress: probe.rows.find(row => row.name === state.field).text, card: probeCard };
      records[caseId] = record;
      console.log(`Figure 4 ${caseId}: ready, legend ${Math.round(legend.width)} × ${Math.round(legend.height)} CSS px`);
    } finally {
      await page.close();
      server.close();
    }
  }
  await writeJson(path.join(output, 'viewer_capture.json'), records);
} finally {
  await browser.close();
}
