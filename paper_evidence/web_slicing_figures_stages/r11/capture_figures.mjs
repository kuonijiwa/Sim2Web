import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { openBrowser, paint, writeJson } from '../../../benchmark/figures_r7/capture_common.mjs';
import { staticServer } from '../../../benchmark/web_slicing/serve.mjs';
import { bandedNodes } from '../../../viewer/src/lib/colormaps.js';

const [stateFile, stagesSite, pitSite, workbench, output, selection = '2347'] = process.argv.slice(2);
const states = JSON.parse(await fs.readFile(stateFile, 'utf8'));
const previous = '../r10';
const stages = JSON.parse(await fs.readFile(new URL(previous + '/stage_states.json', import.meta.url), 'utf8'));
const pit = JSON.parse(await fs.readFile(new URL('../r9/print_check.json', import.meta.url), 'utf8'));
const css = '.panel, .right { display: none !important; }';
const workbenchCss = [
  '.steps .step { min-height: 32px !important; padding-block: 4px !important; }',
  '.diagnostics li { padding-block: 3px !important; margin-block: 2px !important; }',
].join('\n');
const sourceHook = 'this.axesWidget.setEnabled(!0)';
const captureHook = '(window.__paperScene=this,this.axesWidget.setEnabled(!1))';
const browser = await openBrowser();

function camera(base, azimuth, elevation, roll = 0) {
  const [a, e, r] = [azimuth, elevation, roll].map(x => x * Math.PI / 180);
  const sight = [Math.cos(e) * Math.cos(a), Math.cos(e) * Math.sin(a), Math.sin(e)];
  const up = [-Math.sin(e) * Math.cos(a), -Math.sin(e) * Math.sin(a), Math.cos(e)];
  const right = [-Math.sin(a), Math.cos(a), 0];
  const focal = base.slice(3, 6);
  const distance = Math.hypot(...base.slice(0, 3).map((v, i) => v - focal[i]));
  return [...sight.map((v, i) => focal[i] + v * distance), ...focal,
    ...up.map((v, i) => v * Math.cos(r) + right[i] * Math.sin(r)), base[9]];
}

async function siteServer(site) {
  const html = await fs.readFile(path.join(site, 'index.html'), 'utf8');
  const script = html.match(/src="\.\/(assets\/[^"]+\.js)"/)[1];
  const original = await fs.readFile(path.join(site, script), 'utf8');
  assert.equal(original.split(sourceHook).length, 2, script);
  return staticServer(site, { gzip: false, overlays: { ['/' + script]: original.replace(sourceHook, captureHook) } });
}

async function open(page, server, params) {
  await page.goto(server.url + '/index.html?prefetch=0#' + new URLSearchParams(params));
  await page.waitForFunction(() => window.__SIM2WEB__?.summary()?.events.firstRender, null, { timeout: 120000 });
  const maps = await page.locator('label:has-text("Colour map") option').allTextContents();
  assert(maps.includes('turbo'));
  const actual = await page.evaluate(() => window.__SIM2WEB__.activeColoring());
  assert.equal(actual.name, params.field);
  assert.equal(actual.colormap, 'turbo');
  assert.equal(actual.bands, 8);
  assert.equal(await page.locator('.status.error').count(), 0);
}

async function setup(page, context, fit, aspect, ground) {
  return page.evaluate(({ context, fit, aspect, ground }) => {
    const scene = window.__paperScene;
    const api = window.__SIM2WEB__;
    const [position, focal, viewUp] = [0, 3, 6].map(i => scene.getCamera().slice(i, i + 3));
    const direction = position.map((v, i) => v - focal[i]);
    const length = Math.hypot(...direction);
    const sight = direction.map(v => v / length);
    const [a, b, c] = sight;
    const [x, y, z] = viewUp;
    const right = [y*c - z*b, z*a - x*c, x*b - y*a];
    const dot = (v, w) => v[0]*w[0] + v[1]*w[1] + v[2]*w[2];
    const geometry = {};
    const visible = Object.keys(api.describeActors());
    let xmin = Infinity, xmax = -Infinity, ymin = Infinity, ymax = -Infinity;
    for (const id of visible) {
      const { actor, mapper, data } = scene.actors.get(id);
      const prop = actor.getProperty();
      prop.setLighting(false);
      if (context.includes(id)) {
        mapper.setScalarVisibility(false);
        prop.setColor(217/255, 217/255, 217/255);
        prop.setOpacity(.2);
        if (ground !== null) {
          // Keep the original ground-level polygons in the screenshot client.
          const polygons = data.getPolys();
          const cells = polygons.getData();
          const points = data.getPoints().getData();
          const selected = [];
          for (let i = 0; i < cells.length; i += cells[i]+1) {
            const cell = cells.subarray(i+1, i+1+cells[i]);
            if (cell.every(id => Math.abs(points[3*id+2] - ground) < .0001)) {
              selected.push(cell.length, ...cell);
            }
          }
          if (!selected.length) throw Error('No ground-level polygons');
          polygons.setData(new cells.constructor(selected));
          data.modified();
        }
      }
      geometry[id] = {
        opacity: prop.getOpacity(), color: mapper.getScalarVisibility() ? 'turbo' : '#D9D9D9',
        cells: data.getNumberOfCells(),
      };
      if (!fit || context.includes(id)) continue;
      const points = data.getPoints().getData();
      for (let i = 0; i < points.length; i += 3) {
        const p = points.subarray(i, i+3);
        const dx = dot(p, right), dy = dot(p, viewUp);
        xmin = Math.min(xmin, dx); xmax = Math.max(xmax, dx);
        ymin = Math.min(ymin, dy); ymax = Math.max(ymax, dy);
      }
    }
    if (fit && Number.isFinite(xmax)) {
      const scale = Math.max((xmax-xmin)/(2*aspect*fit.width), (ymax-ymin)/(2*fit.height));
      const dx = (xmin+xmax)/2 - dot(focal, right) - (fit.x ?? 0)*2*scale*aspect;
      const dy = (ymin+ymax)/2 - dot(focal, viewUp) - (fit.y ?? 0)*2*scale;
      const shift = right.map((v, i) => v*dx + viewUp[i]*dy);
      scene.setCamera([...position.map((v, i) => v+shift[i]), ...focal.map((v, i) => v+shift[i]), ...viewUp, scale]);
    }
    scene.render();
    return { geometry, camera: scene.getCamera(), actors: api.describeActors(), coloring: api.activeColoring() };
  }, { context, fit, aspect, ground });
}

function params(field, cam, layers, section = null, options = {}) {
  const result = { field, cam: cam.join(','), layers, section: section ? '1' : '0',
    parallel: '1', cmap: 'turbo', bands: '8', range: 'p5_p95', ...options };
  if (section) Object.assign(result, { axis: section.axis, pos: String(section.pos) });
  return result;
}

async function raw(site, settings, file, { viewport, context = [], fit = null, full = false, angles, ground = null }) {
  const dsf = 3;
  const page = await browser.newPage({ viewport, deviceScaleFactor: dsf });
  const server = await siteServer(site);
  try {
    await open(page, server, settings);
    const state = await setup(page, context, fit, viewport.width / viewport.height, ground);
    const { min, max, bands, colormap } = state.coloring;
    const legend = bandedNodes(min, max, bands, colormap).legend;
    const index = JSON.parse(await fs.readFile(path.join(site, 'model_cache/index.json'), 'utf8'));
    const unit = index.fields[settings.field].unit;
    const intended = Object.keys(state.actors).sort();
    const expected = settings.layers.split(',').map(layer => 'layer:' + layer.split(':')[0]);
    if (settings.section === '1') expected.push('section');
    assert.deepEqual(intended, expected.sort(), file);
    let probe = null, uiFontCss = null, slider = null;
    if (full) {
      assert.match(await page.locator('.panel section:has(h2:text-is("Stage")) select option:checked').innerText(), /IV-2$/);
      const points = [[.50,.47],[.47,.47],[.53,.47],[.50,.51],[.55,.51],[.45,.51]];
      for (const y of [.42,.50,.58,.64,.70]) {
        for (const x of [.48,.54,.44,.59,.38,.64]) points.push([x,y]);
      }
      for (const point of points) {
        const hit = await page.evaluate(([x, y]) => window.__SIM2WEB__.pickAt(x, 1-y), point);
        if (!hit?.isSection || !Number.isInteger(hit.sourceCell)) continue;
        await page.mouse.click(point[0] * viewport.width, point[1] * viewport.height);
        const probeText = await page.locator('.probe').innerText();
        assert(probeText.includes(String(hit.sourceCell)));
        probe = { ...hit, pixel: point.map((v, i) => Math.round(v*(i ? viewport.height : viewport.width))), text: probeText };
        break;
      }
      assert(probe, 'A physical section cell must be clicked');
      slider = await page.locator('.panel section:has(h2:text-is("Section")) .hint').innerText();
      const extent = await page.locator('.panel section:has(h2:text-is("Section")) input[type=range]').boundingBox();
      assert(extent.y + extent.height < viewport.height);
      uiFontCss = await page.locator('.panel h2, .panel label, .panel select, .probe td, .legend .tick')
        .evaluateAll(nodes => [...new Set(nodes.map(n => parseFloat(getComputedStyle(n).fontSize)))].sort((a,b) => a-b));
    } else {
      await page.addStyleTag({ content: css });
    }
    await paint(page);
    await page.screenshot({ path: path.join(output, file), scale: 'device' });
    console.log(file, settings.field, colormap, bands, [min, max], state.geometry, probe?.sourceCell);
    return { file, viewport, dsf, settings, state, legend, unit, ground, css: full ? '' : css, angles, probe, uiFontCss, slider };
  } finally {
    await page.close();
    server.close();
  }
}

async function leftPanels() {
  const viewport = { width: 880, height: 820 };
  const dsf = 4;
  const page = await browser.newPage({ viewport, deviceScaleFactor: dsf });
  try {
    await page.goto(new URL('/workbench/', workbench).href);
    await page.locator('.diagnostics .ok').filter({ hasText: 'Every published value matches the source model' }).waitFor({ timeout: 15000 });
    await page.locator('.steps button').filter({ hasText: 'Geometry and excavation' }).click();
    const meta = await (await page.request.get(new URL('/api/project', workbench).href)).json();
    assert.equal(meta.build_report.sim2web, '0.2.0');
    assert.equal(meta.validation.passed, true);
    assert.equal(await page.locator('.steps .step:visible').count(), 6);
    assert.equal(await page.locator('.diagnostics .warn,.diagnostics .error').count(), 0);
    await page.addStyleTag({ content: workbenchCss });
    await paint(page);
    const groups = [
      ['steps', '.steps', '.steps .step', '.steps .step'],
      ['diagnostics', '.diagnostics', '.diagnostics h2', '.diagnostics li'],
    ];
    const crops = {};
    for (const [key, frame, top, bottom] of groups) {
      const box = await page.locator(frame).boundingBox();
      const first = await page.locator(top).first().boundingBox();
      const last = await page.locator(bottom).last().boundingBox();
      const y = Math.floor(first.y) - 2;
      const clip = { x: Math.floor(box.x), y, width: Math.floor(box.width),
        height: Math.ceil(last.y + last.height + 3 - y) };
      await page.screenshot({ path: path.join(output, key+'.png'), clip, scale: 'device' });
      crops[key] = clip;
    }
    const diagnostic = await page.locator('.diagnostics li').evaluateAll(items => items.map(li => ({
      title: li.querySelector('.title').innerText, value: li.querySelector('.detail').innerText,
    })));
    const font = {};
    for (const [key, selector] of [['steps', '.steps .step'], ['diagnostics', '.diagnostics .detail']]) {
      font[key] = await page.locator(selector).evaluateAll(items => Math.min(...items.map(el => parseFloat(getComputedStyle(el).fontSize))));
    }
    return { viewport, dsf, crops, font, diagnostic, css: workbenchCss,
      build: meta.build_report, validation: meta.validation };
  } finally {
    await page.close();
  }
}

await fs.mkdir(output, { recursive: true });
const view = { width: 1120, height: 700 };
const site = key => states[key].site;
const common = { width: .89, height: .90 };
try {
  if (selection.includes('2')) {
    const left = await leftPanels();
    const angles = [228, 35, -48];
    const settings = params('TotalDisplacement', pit.right.camera, 'exterior:1:0.2,excavation:1:1');
    const right = await raw(pitSite, settings, 'pit.png', { viewport: { width: 1360, height: 1250 },
      context: ['layer:exterior'], angles, ground: 11 });
    await writeJson(path.join(output, 'fig2.json'), { left, right, browser: browser.version() });
  }
  if (selection.includes('3')) {
    const angles = [211, 31, 0];
    const settings = params('Stress_Min_Principal', camera(states.A.camera, ...angles), 'excavation:1:1',
      { axis: 'x', pos: 38 }, { stage: 'IV-2' });
    const shot = await raw(stagesSite, settings, 'viewer_full.png', { viewport: { width: 1600, height: 900 },
      full: true, fit: { width: .57, height: .78, x: -.02, y: .015 }, angles });
    await writeJson(path.join(output, 'fig3.json'), shot);
  }
  if (selection.includes('4')) {
    const presentations = {
      A: { angles: [216,30,0], layers: 'excavation:1:1', section: true },
      B: { angles: [225,32,-5], layers: 'exterior:1:0.2,excavation:1:1', grey: true, section: true },
      C: { angles: [298,33,-26], layers: 'exterior:1:1', range: 'p5_p95' },
      D: { angles: [228,43,-58], layers: 'exterior:1:0.2,excavation:1:1', grey: true },
      E: { angles: [240,32,5], layers: 'exterior:1:1' },
      F: { angles: [275,32,-26], layers: 'exterior:1:0.2', grey: true, section: true },
    };
    const results = {};
    for (const [key, spec] of Object.entries(presentations)) {
      const base = states[key];
      const cam = camera(key === 'D' ? pit.right.camera : base.camera, ...spec.angles);
      const settings = params(base.field, cam, spec.layers,
        spec.section ? { axis: base.axis, pos: base.position_m } : null, { range: spec.range ?? base.range });
      results[key] = await raw(site(key), settings, 'case_'+key+'.png', {
        viewport: view, context: spec.grey ? ['layer:exterior'] : [],
        fit: common, angles: spec.angles, ground: key === 'D' ? 11 : null,
      });
    }
    await writeJson(path.join(output, 'fig4.json'), results);
  }
  if (selection.includes('7')) {
    const results = {};
    const angles = [239, 30, 0];
    const cam = camera(stages.camera, ...angles);
    cam[9] *= 1.20;
    for (const [i, stage] of stages.stages.entries()) {
      const settings = params(stages.field, cam, 'excavation:1:1', null,
        { stage, range: 'custom', rmin: stages.limits[0], rmax: stages.limits[1] });
      const shot = await raw(stagesSite, settings, 'stage_'+stage+'.png', {
        viewport: { width: 950, height: 650 }, angles,
      });
      assert.deepEqual([shot.state.coloring.min, shot.state.coloring.max], stages.limits);
      assert.equal(shot.state.geometry['layer:excavation'].cells, [20142,27837,49677][i]);
      results[stage] = shot;
    }
    await writeJson(path.join(output, 'fig7.json'), { results, range_method: stages.limits_method });
  }
} finally {
  await browser.close();
}
