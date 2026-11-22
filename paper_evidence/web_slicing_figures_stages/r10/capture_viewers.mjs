import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { openBrowser, paint, writeJson } from '../../../benchmark/figures_r7/capture_common.mjs';
import { staticServer } from '../../../benchmark/web_slicing/serve.mjs';
import { bandedNodes } from '../../../viewer/src/lib/colormaps.js';

const [statesPath, stagesSite, stageSettingsPath, out, selection = '347'] = process.argv.slice(2);
const states = JSON.parse(await fs.readFile(statesPath, 'utf8'));
const stageSettings = JSON.parse(await fs.readFile(stageSettingsPath, 'utf8'));
await fs.mkdir(out, { recursive: true });
const cleanCss = '.panel, .right { display: none !important; }';
const browser = await openBrowser();

async function open(page, server, params) {
  await page.goto(server.url + '/index.html?prefetch=0#' + new URLSearchParams(params));
  await page.waitForFunction(() => window.__SIM2WEB__?.summary()?.events.firstRender, null, { timeout: 180000 });
  const state = await page.evaluate(() => ({
    coloring: window.__SIM2WEB__.activeColoring(), actors: window.__SIM2WEB__.describeActors(),
  }));
  assert.equal(state.coloring.name, params.field);
  await paint(page);
  return state;
}

function validate(state, params) {
  const expected = params.layers.split(',').filter(layer => layer.split(':')[1] === '1')
    .map(layer => 'layer:' + layer.split(':')[0]);
  if (params.section === '1') expected.push('section');
  assert.deepEqual(Object.keys(state.actors).sort(), expected.sort());
  const { min, max, bands, colormap } = state.coloring;
  return bandedNodes(min, max, bands, colormap).legend;
}

async function rawCapture(site, viewport, file, params, unit, angle, probe = null) {
  const page = await browser.newPage({ viewport, deviceScaleFactor: 3 });
  const server = await staticServer(site, { gzip: false });
  try {
    const state = await open(page, server, params);
    const legend = validate(state, params);
    let probeInfo;
    if (probe) {
      const excavation = page.locator('.panel .layer input[type=checkbox]');
      await excavation.uncheck();
      probeInfo = await selectProbe(page, probe);
      await excavation.check();
    }
    await page.addStyleTag({ content: cleanCss });
    await paint(page);
    await page.screenshot({ path: path.join(out, file), scale: 'device' });
    console.log(file, JSON.stringify(state.coloring), Object.keys(state.actors));
    return { file, dsf: 3, viewport, params, unit, angle, state, legend, probe: probeInfo, css: cleanCss };
  } finally {
    await page.close();
    server.close();
  }
}

async function selectProbe(page, spec) {
  const pick = ([x, y]) => page.evaluate(([fx, fy]) => window.__SIM2WEB__.pickAt(fx, 1 - fy), [x, y]);
  const target = spec.probe_targets[0];
  const { right, up, px_per_m: scale } = spec.probe_projection;
  const dot = (a, b) => a.reduce((sum, value, i) => sum + value * b[i], 0);
  let position = target.canvas;
  for (let attempt = 0; attempt < 3; attempt++) {
    const hit = await pick(position);
    if (hit?.sourceCell === spec.probe_cell_id) return { hit, position };
    if (!hit?.position) break;
    const delta = target.world.map((value, i) => value - hit.position[i]);
    position = [position[0] + dot(delta, right) * scale / 960, position[1] - dot(delta, up) * scale / 600];
  }
  const candidates = [position];
  for (const radius of [1 / 3, 2 / 3, 1, 1.5, 2, 3, 6]) {
    const [x, y] = position;
    for (const [dx, dy] of [[-1, 0], [1, 0], [0, -1], [0, 1], [-1, -1], [1, 1]]) {
      candidates.push([x + dx * radius / 960, y + dy * radius / 600]);
    }
  }
  for (const [x, y] of candidates) {
    const hit = await pick([x, y]);
    if (hit?.sourceCell === spec.probe_cell_id) return { hit, position: [x, y] };
  }
  throw Error('Unable to pick the documented source cell ' + spec.probe_cell_id);
}

try {
  if (selection.includes('3')) {
    const viewport = { width: 1440, height: 900 };
    const page = await browser.newPage({ viewport, deviceScaleFactor: 3 });
    const server = await staticServer(stagesSite, { gzip: false });
    try {
      const a = states.A;
      const params = { stage: 'IV-2', field: 'Stress_Min_Principal', axis: 'x', pos: '38', section: '1',
        parallel: '1', cmap: 'jet', bands: '8', cam: a.camera.join(','), range: 'p5_p95', layers: 'excavation:1:0.35' };
      const state = await open(page, server, params);
      const legend = validate(state, params);
      assert.match(await page.locator('.panel section:has(h2:text-is("Stage")) select option:checked').innerText(), /IV-2$/);
      const { hit, position: [x, y] } = await selectProbe(page, a);
      const probeValue = hit.rows.find(row => row.name === params.field);
      assert.match(probeValue.text, /MPa$/);
      await page.mouse.click(x * viewport.width, y * viewport.height);
      await page.locator('.probe').waitFor();
      const probeText = await page.locator('.probe').innerText();
      assert(probeText.includes('Source_Cell_ID') && probeText.includes(String(hit.sourceCell)));
      const sections = '.panel section:has(h2:text-is("Section"))';
      const locators = [
        '.panel section:has(h2:text-is("Stage")) select',
        '.panel section:has(h2:text-is("Field")) select',
        '.panel section:has(h2:text-is("Layers")) .layer label',
        sections + ' .tabs',
        '.probe-head',
        '.legend-title',
      ];
      const slider = await page.locator(sections + ' input[type=range]').boundingBox();
      const body = await page.locator('.panel .body').boundingBox();
      assert(slider.y + slider.height <= body.y + body.height, 'Section slider must be visible');
      const boxes = [];
      for (const selector of locators) {
        const box = await page.locator(selector).first().boundingBox();
        assert(box && box.y >= 0 && box.y + box.height <= viewport.height, selector);
        boxes.push(box);
      }
      const legendBox = await page.locator('.legend').boundingBox();
      assert(legendBox.width <= viewport.width * .2 && legendBox.y >= 0);
      const font = await page.locator('.panel h2, .panel label, .panel select, .probe td, .legend .tick')
        .evaluateAll(nodes => [...new Set(nodes.map(n => parseFloat(getComputedStyle(n).fontSize)))].sort((a, b) => a-b));
      await paint(page);
      const file = 'viewer_full.png';
      await page.screenshot({ path: path.join(out, file), scale: 'device' });
      await writeJson(path.join(out, 'fig3.json'), { file, viewport, dsf: 3, params, unit: 'MPa', boxes,
        font, state, legend, hit, probeText, slider, legendBox, css: '' });
      console.log(file, hit.sourceCell, probeValue.text);
    } finally {
      await page.close();
      server.close();
    }
  }

  if (selection.includes('4')) {
    const records = {};
    for (const key of 'ABCDEF') {
      const { site, field, axis, position_m: pos, camera, range, layers, angles_deg } = states[key];
      const params = { field, section: axis ? '1' : '0', parallel: '1', cmap: 'jet', bands: '8',
        cam: camera.join(','), range, layers: layers.join(',') };
      if (axis) Object.assign(params, { axis, pos: String(pos) });
      const index = JSON.parse(await fs.readFile(path.join(site, 'model_cache', 'index.json'), 'utf8'));
      const unit = index.fields[field].unit;
      records[key] = await rawCapture(site, { width: 960, height: 600 }, 'case_' + key + '.png', params, unit, angles_deg,
        key === 'A' ? states.A : null);
      await writeJson(path.join(out, 'fig4.json'), records);
    }
  }

  if (selection.includes('7')) {
    const records = {};
    const { stages, camera, limits, limits_method, viewport, field } = stageSettings;
    for (const stage of stages) {
      const params = { stage, field, parallel: '1', cmap: 'jet', bands: '8', cam: camera.join(','),
        range: 'custom', rmin: limits[0], rmax: limits[1], section: '0', layers: 'excavation:1:1' };
      records[stage] = await rawCapture(stagesSite, viewport, 'stage_' + stage + '.png', params, 'MPa', null);
      assert.deepEqual([records[stage].state.coloring.min, records[stage].state.coloring.max], limits);
    }
    await writeJson(path.join(out, 'fig7.json'), { limits_method, stages: records });
  }
} finally {
  await browser.close();
}
