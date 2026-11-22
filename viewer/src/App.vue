<template>
  <div class="shell">
    <div ref="viewport" class="viewport" @pointerdown="onPointerDown" @pointerup="onPointerUp"></div>

    <!-- Control panel -->
    <aside class="panel" :class="{ collapsed }">
      <header>
        <button class="collapse" @click="collapsed = !collapsed" :title="collapsed ? 'Show panel' : 'Hide panel'">{{ collapsed ? '›' : '‹' }}</button>
        <div v-if="!collapsed">
          <h1>{{ index?.viewer?.title || 'Sim2Web' }}</h1>
          <p class="subtitle" v-if="index?.viewer?.subtitle">{{ index.viewer.subtitle }}</p>
        </div>
      </header>

      <div class="body" v-if="index && !collapsed">
        <!-- Stage -->
        <section v-if="index.stages.length > 1">
          <h2>Stage</h2>
          <div class="row">
            <button @click="setStage(stageIndex - 1)" :disabled="stageIndex === 0">◀</button>
            <select v-model.number="stageIndex" @change="setStage(stageIndex)">
              <option v-for="(s, i) in index.stages" :key="s.id" :value="i">{{ i + 1 }}. {{ s.label }}</option>
            </select>
            <button @click="setStage(stageIndex + 1)" :disabled="stageIndex === index.stages.length - 1">▶</button>
          </div>
          <label class="check"><input type="checkbox" v-model="rangeScopeAll" @change="recolor" /> Same colour scale for all stages</label>
        </section>

        <!-- Field -->
        <section>
          <h2>Field</h2>
          <select v-model="fieldName" @change="recolor">
            <optgroup v-for="g in fieldGroups" :key="g.label" :label="g.label">
              <option v-for="f in g.fields" :key="f.name" :value="f.name">{{ f.label }}{{ f.unit ? ` (${f.unit})` : '' }}</option>
            </optgroup>
          </select>
          <p class="hint" v-if="fieldMeta">
            <span class="badge" :class="fieldMeta.association">{{ fieldMeta.association === 'cell' ? 'cell value (exact)' : 'nodal value' }}</span>
            <span v-if="fieldMeta.sign_convention"> {{ fieldMeta.sign_convention }}.</span>
            <span v-if="fieldMeta.component_order"> Source order {{ fieldMeta.component_order }}.</span>
          </p>
          <template v-if="fieldMeta && fieldMeta.kind !== 'categorical'">
            <div class="grid2">
              <label>Colour map
                <select v-model="colormap" @change="recolor">
                  <option v-for="c in colormaps" :key="c" :value="c">{{ c }}</option>
                </select>
              </label>
              <label>Bands
                <input type="number" min="1" max="32" v-model.number="bands" @change="recolor" />
              </label>
            </div>
            <label>Range
              <select v-model="rangeMode" @change="recolor">
                <option value="full">Full range</option>
                <option value="p5_p95">P5–P95 (outliers clamped)</option>
                <option value="custom">Custom</option>
              </select>
            </label>
            <div class="grid2" v-if="rangeMode === 'custom'">
              <label>Min <input type="number" step="any" v-model.number="customMin" @change="recolor" /></label>
              <label>Max <input type="number" step="any" v-model.number="customMax" @change="recolor" /></label>
            </div>
          </template>
        </section>

        <!-- Layers -->
        <section>
          <h2>Layers</h2>
          <div v-for="layer in stage.layers" :key="layer.id" class="layer">
            <label class="check"><input type="checkbox" v-model="layerState[layer.id].visible" @change="applyLayers" />
              {{ layer.label }} <span class="muted" v-if="layer.role === 'supplementary'">(supplementary)</span></label>
            <input type="range" min="0" max="1" step="0.05" v-model.number="layerState[layer.id].opacity" @input="applyLayers"
                   :disabled="!layerState[layer.id].visible" :title="`Opacity ${Math.round(layerState[layer.id].opacity * 100)}%`" />
          </div>
          <label class="check"><input type="checkbox" v-model="edges" @change="applyEdges" /> Mesh edges</label>
        </section>

        <!-- Sections -->
        <section v-if="axes.length">
          <h2>Section</h2>
          <label class="check"><input type="checkbox" v-model="sectionOn" @change="onSectionToggle" /> Show section</label>
          <template v-if="sectionOn">
            <div class="tabs">
              <button v-for="a in axes" :key="a" :class="{ active: axis === a }" @click="setAxis(a)">{{ a.toUpperCase() }}</button>
            </div>
            <div class="row">
              <button @click="stepSection(-1)" :disabled="sectionIndex <= 0">−</button>
              <input type="range" min="0" :max="sections.length - 1" v-model.number="sectionIndex" @input="loadSection()" />
              <button @click="stepSection(1)" :disabled="sectionIndex >= sections.length - 1">+</button>
            </div>
            <p class="hint">{{ axis.toUpperCase() }} = <b>{{ fmtPos(sections[sectionIndex]?.value) }}</b> {{ lengthUnit }}
              · {{ sectionIndex + 1 }} / {{ sections.length }} · {{ kib(sections[sectionIndex]?.bytes) }}</p>
            <button class="wide" @click="viewSectionFaceOn">View section face-on</button>
          </template>
        </section>

        <!-- Tools -->
        <section>
          <h2>View</h2>
          <div class="row">
            <button @click="scene.resetCamera()">Reset</button>
            <button @click="scene.viewAxis('x')">X</button>
            <button @click="scene.viewAxis('y')">Y</button>
            <button @click="scene.viewAxis('z')">Z</button>
          </div>
          <label class="check"><input type="checkbox" v-model="parallel" @change="scene.setParallel(parallel)" /> Parallel projection</label>
          <div class="row">
            <button @click="saveScreenshot">Save image</button>
            <button @click="copyLink">{{ copied ? 'Link copied' : 'Copy view link' }}</button>
          </div>
          <p class="hint">Click a surface or section to read exact values and source identifiers.</p>
        </section>

        <!-- Diagnostics -->
        <section>
          <details>
            <summary>Package and performance</summary>
            <table class="kv">
              <tr><td>Source</td><td>{{ stage.source.file }} · {{ stage.source.cells.toLocaleString() }} cells</td></tr>
              <tr><td>Startup transfer</td><td>{{ mib(perf.startupBytes) }} in {{ perf.startupFiles }} file(s)</td></tr>
              <tr><td>Index → first image</td><td>{{ ms(perf.firstRender) }}</td></tr>
              <tr><td>Last section switch</td><td>{{ ms(perf.lastSwitch) }} <span class="muted">{{ perf.lastSwitchCached ? '(cached)' : '' }}</span></td></tr>
              <tr><td>Frame rate</td><td>{{ perf.fps ? perf.fps.toFixed(1) + ' fps' : '—' }} <button class="link" @click="measureFps">measure</button></td></tr>
              <tr v-if="perf.heap"><td>JS heap</td><td>{{ mib(perf.heap) }}</td></tr>
              <tr><td>Generator</td><td>{{ index.generator.name }} {{ index.generator.version }}</td></tr>
            </table>
          </details>
        </section>
      </div>
      <footer class="status" :class="{ error: !!error }">{{ error || status }}</footer>
    </aside>

    <!-- Right column: probe and legend -->
    <div class="right">
      <div class="probe" v-if="probe">
        <div class="probe-head"><b>{{ probe.layer }}</b><button class="link" @click="clearProbe">×</button></div>
        <table class="kv">
          <tr v-if="probe.position"><td>x, y, z</td><td>{{ probe.position.map(fmtPos).join(', ') }}</td></tr>
          <tr><td>Source_Cell_ID</td><td>{{ probe.sourceCell }}</td></tr>
          <tr v-if="probe.sourcePoint !== null"><td>Source_Point_ID</td><td>{{ probe.sourcePoint }} <span class="muted">(nearest node)</span></td></tr>
          <tr v-else-if="probe.isSection"><td>Vertex</td><td class="muted">interpolated (no source node)</td></tr>
          <tr v-for="row in probe.rows" :key="row.name" :class="{ active: row.name === fieldName }">
            <td>{{ row.label }}</td><td>{{ row.text }}</td>
          </tr>
        </table>
      </div>
      <LegendCard :legend="legend" :kind="fieldMeta?.kind" :title="legendTitle" :subtitle="legendSubtitle" />
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue';
import LegendCard from './components/LegendCard.vue';
import { COLORMAPS, formatValue } from './lib/colormaps.js';
import { checkIndex, displayRange, groupedFields, nearestSectionIndex, sectionAxes } from './lib/indexModel.js';
import { ProductLoader } from './lib/loader.js';
import { Metrics, afterPaint } from './lib/metrics.js';
import { Scene } from './lib/scene.js';
import { decodeState, encodeState } from './lib/urlState.js';

const query = new URLSearchParams(window.location.search);
const INDEX_URL = query.get('index') || 'model_cache/index.json';
const PREFETCH = query.get('prefetch') !== '0';
const BASE = new URL('.', new URL(INDEX_URL, window.location.href)).href.replace(/model_cache\/$/, '');

const viewport = ref(null);
const index = ref(null);
const status = ref('Loading index…');
const error = ref('');
const collapsed = ref(false);
const stageIndex = ref(0);
const fieldName = ref('');
const colormap = ref('jet');
const bands = ref(8);
const rangeMode = ref('full');
const rangeScopeAll = ref(false);
const customMin = ref(null);
const customMax = ref(null);
const layerState = reactive({});
const edges = ref(false);
const parallel = ref(false);
const sectionOn = ref(true);
const axis = ref('x');
const sectionIndex = ref(0);
const legend = ref([]);
const probe = ref(null);
const copied = ref(false);
const perf = reactive({ startupBytes: 0, startupFiles: 0, firstRender: null, lastSwitch: null, lastSwitchCached: false, fps: null, heap: null });
const colormaps = Object.keys(COLORMAPS);

const metrics = new Metrics();
const loader = new ProductLoader({ metrics });
let scene = null;
let sectionToken = 0;

const stage = computed(() => index.value?.stages[stageIndex.value]);
const fieldGroups = computed(() => (index.value && stage.value ? groupedFields(index.value, stage.value) : []));
const fieldMeta = computed(() => (index.value && fieldName.value ? { ...index.value.fields[fieldName.value], name: fieldName.value } : null));
const axes = computed(() => (stage.value ? sectionAxes(stage.value) : []));
const sections = computed(() => stage.value?.sections?.[axis.value] ?? []);
const lengthUnit = computed(() => index.value?.viewer?.length_unit || 'm');
const currentRange = computed(() => (index.value && fieldName.value
  ? displayRange(index.value, stageIndex.value, fieldName.value, rangeMode.value, rangeScopeAll.value ? 'all' : 'stage', [customMin.value, customMax.value])
  : null));
const legendTitle = computed(() => (fieldMeta.value ? `${fieldMeta.value.label}${fieldMeta.value.unit ? ` (${fieldMeta.value.unit})` : ''}` : ''));
const legendSubtitle = computed(() => {
  if (!fieldMeta.value || fieldMeta.value.kind === 'categorical') return fieldMeta.value ? 'cell categories' : '';
  const r = currentRange.value;
  return `${fieldMeta.value.association === 'cell' ? 'cell data' : 'point data'} · ${r.label}${rangeScopeAll.value ? ', all stages' : ''}`;
});

const url = (rel) => new URL(rel, BASE).href;
const fmtPos = (v) => (Number.isFinite(v) ? formatValue(v, 100) : '—');
const kib = (b) => (b ? `${(b / 1024).toFixed(0)} KiB` : '');
const mib = (b) => (b ? `${(b / 1048576).toFixed(2)} MiB` : '—');
const ms = (v) => (Number.isFinite(v) ? `${v.toFixed(0)} ms` : '—');

// ------------------------------------------------------------------ startup
onMounted(async () => {
  metrics.mark('start');
  try {
    const response = await fetch(url(INDEX_URL.replace(/^.*model_cache\//, 'model_cache/')));
    if (!response.ok) throw new Error(`Cannot read ${INDEX_URL} (HTTP ${response.status})`);
    index.value = checkIndex(await response.json());
    metrics.mark('index');
    document.title = index.value.viewer?.title || 'Sim2Web';
    const v = index.value.viewer || {};
    colormap.value = COLORMAPS[v.colormap] ? v.colormap : 'jet';
    bands.value = v.bands || 8;
    rangeMode.value = v.range_mode || 'full';
    const saved = decodeState(window.location.hash);
    const si = index.value.stages.findIndex((s) => s.id === saved.stage);
    stageIndex.value = si >= 0 ? si : 0;
    initLayerState(saved.layers);
    fieldName.value = pickField(saved.field || v.default_field);
    if (saved.cmap && COLORMAPS[saved.cmap]) colormap.value = saved.cmap;
    if (saved.bands) bands.value = saved.bands;
    if (saved.range) rangeMode.value = saved.range;
    if (saved.rmin !== undefined) customMin.value = saved.rmin;
    if (saved.rmax !== undefined) customMax.value = saved.rmax;
    if (saved.section !== undefined) sectionOn.value = saved.section;
    edges.value = Boolean(saved.edges);
    parallel.value = Boolean(saved.parallel);
    axis.value = axes.value.includes(saved.axis) ? saved.axis : (axes.value.includes(v.default_axis) ? v.default_axis : axes.value[0] || 'x');
    sectionIndex.value = saved.pos !== undefined ? nearestSectionIndex(sections.value, saved.pos) : Math.floor((sections.value.length - 1) / 2);

    await nextTick();
    scene = new Scene(viewport.value, { background: v.background || [1, 1, 1] });
    await loadStage();
    if (saved.cam) scene.setCamera(saved.cam); else scene.resetCamera();
    scene.setParallel(parallel.value);
    await afterPaint();
    metrics.mark('firstRender');
    const s = metrics.summary();
    perf.startupBytes = s.startupBytes;
    perf.startupFiles = s.startupFiles.length;
    perf.firstRender = metrics.events.firstRender - metrics.events.index;
    perf.heap = s.heap?.usedJSHeapSize ?? null;
    status.value = 'Ready';
    exposeApi();
    watchState();
  } catch (e) {
    error.value = e.message || String(e);
    console.error(e);
  }
});

function pickField(preferred) {
  const names = fieldGroups.value.flatMap((g) => g.fields.map((f) => f.name));
  return names.includes(preferred) ? preferred : names[0] || '';
}

function initLayerState(saved = {}) {
  for (const layer of stage.value.layers) {
    if (!layerState[layer.id]) {
      layerState[layer.id] = saved[layer.id] || {
        visible: layer.default_visible !== false,
        // with a section shown, a semi-transparent primary surface keeps the section visible
        opacity: layer.role === 'primary' ? (sectionOn.value && axes.value.length ? 0.35 : 1) : 0.6,
      };
    }
  }
}

async function loadStage() {
  status.value = 'Loading surfaces…';
  initLayerState();
  const st = stage.value;
  const tasks = st.layers.map(async (layer) => {
    const data = await loader.load(url(layer.file), { role: `layer:${layer.id}` });
    scene.setData(`layer:${layer.id}`, data);
  });
  if (sectionOn.value && sections.value.length) tasks.push(loadSection({ silent: true }));
  await Promise.all(tasks);
  for (const id of [...scene.actors.keys()]) {
    if (id.startsWith('layer:') && !st.layers.some((l) => `layer:${l.id}` === id)) scene.setVisible(id, false);
  }
  applyLayers();
  applyEdges();
  recolor();
  status.value = 'Ready';
}

async function setStage(i) {
  if (i < 0 || i >= index.value.stages.length) return;
  stageIndex.value = i;
  const pos = sections.value[sectionIndex.value]?.value;
  if (!axes.value.includes(axis.value)) axis.value = axes.value[0] || 'x';
  sectionIndex.value = pos !== undefined ? nearestSectionIndex(sections.value, pos) : 0;
  if (!fieldGroups.value.some((g) => g.fields.some((f) => f.name === fieldName.value))) fieldName.value = pickField('');
  clearProbe();
  await loadStage();
}

// ---------------------------------------------------------------- sections
async function loadSection({ silent = false } = {}) {
  const entry = sections.value[sectionIndex.value];
  if (!sectionOn.value || !entry) { scene?.setVisible('section', false); scene?.render(); return; }
  const token = ++sectionToken;
  const target = url(entry.file);
  const cached = loader.has(target);
  const t0 = performance.now();
  const data = await loader.load(target, { role: 'section' });
  if (token !== sectionToken) return; // a newer request superseded this one
  scene.setData('section', data);
  scene.setVisible('section', true);
  scene.setOpacity('section', 1);
  if (!silent) {
    scene.render();
    await afterPaint();
    const dt = performance.now() - t0;
    metrics.sectionSwitches.push({ axis: axis.value, value: entry.value, ms: dt, cached, bytes: entry.bytes });
    perf.lastSwitch = dt;
    perf.lastSwitchCached = cached;
  }
  if (PREFETCH) prefetchNeighbours();
}

function prefetchNeighbours() {
  const list = sections.value;
  for (const k of [sectionIndex.value + 1, sectionIndex.value - 1]) {
    if (list[k]) {
      const run = () => loader.load(url(list[k].file), { role: 'section', prefetch: true }).catch(() => {});
      (window.requestIdleCallback || setTimeout)(run);
    }
  }
}

function stepSection(d) {
  const k = sectionIndex.value + d;
  if (k >= 0 && k < sections.value.length) { sectionIndex.value = k; loadSection(); }
}

function setAxis(a) {
  const keep = sections.value[sectionIndex.value]?.value;
  axis.value = a;
  sectionIndex.value = Math.floor((sections.value.length - 1) / 2);
  if (keep === undefined) sectionIndex.value = 0;
  loadSection();
}

function onSectionToggle() {
  if (sectionOn.value) {
    for (const l of stage.value.layers) if (l.role === 'primary' && layerState[l.id].opacity > 0.3) layerState[l.id].opacity = 0.25;
  } else {
    for (const l of stage.value.layers) if (l.role === 'primary') layerState[l.id].opacity = 1;
  }
  applyLayers();
  loadSection();
}

function viewSectionFaceOn() {
  const data = scene.actors.get('section')?.data;
  if (data) scene.viewAxis(axis.value, data.getBounds());
}

// ----------------------------------------------------------------- styling
function applyLayers() {
  for (const layer of stage.value.layers) {
    const s = layerState[layer.id];
    scene.setVisible(`layer:${layer.id}`, s.visible);
    scene.setOpacity(`layer:${layer.id}`, s.opacity);
  }
  scene.render();
}

function applyEdges() {
  scene.setEdges(edges.value);
  scene.render();
}

function recolor() {
  const meta = fieldMeta.value;
  if (!meta || !scene) return;
  const r = currentRange.value;
  legend.value = scene.applyColoring({
    name: meta.name, association: meta.association, kind: meta.kind, min: r.min, max: r.max,
    bands: bands.value, colormap: colormap.value, categories: meta.categories || [],
  });
  if (probe.value) refreshProbe();
  scene.render();
}

// ------------------------------------------------------------------ probing
let down = null;
function onPointerDown(e) { down = [e.clientX, e.clientY]; }
async function onPointerUp(e) {
  if (!down || Math.hypot(e.clientX - down[0], e.clientY - down[1]) > 4 || !scene) return;
  const rect = viewport.value.getBoundingClientRect();
  const [w, h] = scene.canvasSize();
  const x = ((e.clientX - rect.left) / rect.width) * w;
  const y = h - ((e.clientY - rect.top) / rect.height) * h;
  const hit = await scene.pick(x, y);
  if (!hit) { clearProbe(); return; }
  lastHit = hit;
  refreshProbe();
}

let lastHit = null;
function refreshProbe() {
  const hit = lastHit;
  if (!hit) return;
  const data = hit.data;
  const cd = data.getCellData();
  const pd = data.getPointData();
  const cellIds = cd.getArrayByName('Source_Cell_ID');
  const isSection = hit.id === 'section';
  let nearest = null;
  try {
    const { cellPointIds } = data.getCellPoints(hit.cellId);
    const pts = data.getPoints().getData();
    const target = hit.position || [pts[3 * cellPointIds[0]], pts[3 * cellPointIds[0] + 1], pts[3 * cellPointIds[0] + 2]];
    let best = Infinity;
    for (const pid of cellPointIds) {
      const d = (pts[3 * pid] - target[0]) ** 2 + (pts[3 * pid + 1] - target[1]) ** 2 + (pts[3 * pid + 2] - target[2]) ** 2;
      if (d < best) { best = d; nearest = pid; }
    }
  } catch (err) { nearest = null; }
  const rows = [];
  for (const [name, meta] of Object.entries(index.value.fields)) {
    let value = null;
    if (meta.association === 'cell') value = cd.getArrayByName(name)?.getData()[hit.cellId];
    else if (nearest !== null) value = pd.getArrayByName(name)?.getData()[nearest];
    if (value === undefined || value === null) continue;
    let text = formatValue(Number(value));
    if (meta.kind === 'categorical') text = meta.categories?.find((c) => c.code === Number(value))?.label ?? String(value);
    else if (meta.unit) text += ` ${meta.unit}`;
    rows.push({ name, label: meta.label, text });
  }
  const spid = pd.getArrayByName('Source_Point_ID');
  const st = stage.value;
  const layer = isSection ? `Section ${axis.value.toUpperCase()} = ${fmtPos(sections.value[sectionIndex.value]?.value)} ${lengthUnit.value}`
    : st.layers.find((l) => `layer:${l.id}` === hit.id)?.label || hit.id;
  probe.value = {
    layer, isSection, position: hit.position ? Array.from(hit.position) : null,
    sourceCell: cellIds ? cellIds.getData()[hit.cellId] : '—',
    sourcePoint: spid && nearest !== null ? spid.getData()[nearest] : null,
    rows,
  };
  const b = scene.visibleBounds();
  scene.showMarker(hit.position, Math.max(b[1] - b[0], b[3] - b[2], b[5] - b[4]) * 0.004);
}

function clearProbe() {
  probe.value = null;
  lastHit = null;
  scene?.showMarker(null);
}

// ------------------------------------------------------------ export/share
async function saveScreenshot() {
  const image = await scene.screenshot();
  const a = document.createElement('a');
  a.href = image;
  a.download = `${stage.value.id}_${fieldName.value}${sectionOn.value ? `_${axis.value}${fmtPos(sections.value[sectionIndex.value]?.value)}` : ''}.png`;
  a.click();
}

function currentState() {
  return {
    stage: stage.value.id, field: fieldName.value, cmap: colormap.value, bands: bands.value, range: rangeMode.value,
    rmin: rangeMode.value === 'custom' ? customMin.value : undefined, rmax: rangeMode.value === 'custom' ? customMax.value : undefined,
    section: sectionOn.value, axis: axis.value, pos: sections.value[sectionIndex.value]?.value,
    layers: Object.fromEntries(stage.value.layers.map((l) => [l.id, layerState[l.id]])),
    edges: edges.value, parallel: parallel.value, cam: scene.getCamera(),
  };
}

async function copyLink() {
  const link = `${window.location.href.split('#')[0]}${encodeState(currentState())}`;
  try { await navigator.clipboard.writeText(link); } catch { window.prompt('Copy this link', link); }
  copied.value = true;
  setTimeout(() => { copied.value = false; }, 1500);
}

function watchState() {
  let timer = null;
  const update = () => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      const st = currentState();
      delete st.cam; // the camera is shared only through "Copy view link"
      history.replaceState(null, '', encodeState(st) || ' ');
    }, 250);
  };
  watch([stageIndex, fieldName, colormap, bands, rangeMode, customMin, customMax, sectionOn, axis, sectionIndex, edges, parallel, () => JSON.stringify(layerState)], update);
}

async function measureFps() {
  status.value = 'Measuring frame rate…';
  const r = await scene.measureFrameRate();
  perf.fps = r.fps;
  metrics.frameRates.push(r);
  status.value = 'Ready';
}

// Programmatic control for automated benchmarks and embedding.
function exposeApi() {
  window.__SIM2WEB__ = {
    metrics,
    summary: () => metrics.summary(),
    stages: () => index.value.stages.map((s) => s.id),
    async setStage(i) { await setStage(i); await afterPaint(); },
    async setField(name) { fieldName.value = name; recolor(); await afterPaint(); },
    async setSection(a, k) {
      axis.value = a; sectionIndex.value = k; sectionOn.value = true; await loadSection(); return metrics.sectionSwitches.at(-1);
    },
    sectionCount: (a) => stage.value.sections[a]?.length ?? 0,
    measureFrameRate: (frames, degrees) => scene.measureFrameRate(frames, degrees).then((r) => { metrics.frameRates.push(r); return r; }),
    activeColoring: () => ({ ...scene.coloring }),
    describeActors: () => scene.describeActors(),
    pickAt: async (fx, fy) => {
      const [w, h] = scene.canvasSize();
      const hit = await scene.pick(fx * w, fy * h);
      if (!hit) return null;
      lastHit = hit; refreshProbe();
      return JSON.parse(JSON.stringify(probe.value));
    },
    resetCamera: () => scene.resetCamera(),
  };
  window.__SIMWEBVIEW__ = window.__SIM2WEB__; // name used before 0.2
  window.dispatchEvent(new Event('sim2web-ready'));
}

window.addEventListener('keydown', (e) => {
  if (e.target?.tagName === 'INPUT' || e.target?.tagName === 'SELECT') return;
  if (e.key === 'ArrowRight' || e.key === ']') stepSection(1);
  if (e.key === 'ArrowLeft' || e.key === '[') stepSection(-1);
});
</script>

<style>
html, body, #app { margin: 0; height: 100%; font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; color: #24303c; }
* { box-sizing: border-box; }
</style>

<style scoped>
.shell { position: fixed; inset: 0; background: #f3f5f8; }
.viewport { position: absolute; inset: 0; }
.panel { position: absolute; top: 12px; left: 12px; bottom: 12px; width: 318px; display: flex; flex-direction: column;
  background: rgba(255,255,255,.96); border: 1px solid #dfe3ea; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,.10); z-index: 5; }
.panel.collapsed { width: 44px; bottom: auto; }
header { display: flex; gap: 8px; padding: 12px 14px 8px; border-bottom: 1px solid #eef1f5; }
.collapse { border: 1px solid #dfe3ea; background: #fff; border-radius: 6px; width: 26px; height: 26px; cursor: pointer; flex: none; }
h1 { font-size: 14px; margin: 2px 0 2px; line-height: 1.3; }
.subtitle { font-size: 11.5px; color: #6b7785; margin: 0; }
.body { overflow-y: auto; padding: 4px 14px 8px; flex: 1; }
section { padding: 10px 0; border-bottom: 1px solid #f0f2f6; }
h2 { font-size: 10.5px; text-transform: uppercase; letter-spacing: .06em; color: #6b7785; margin: 0 0 8px; }
select, input[type=number] { width: 100%; padding: 6px 8px; border: 1px solid #d5dae2; border-radius: 6px; font-size: 12.5px; background: #fff; }
label { display: block; font-size: 12px; color: #4a5866; margin-top: 6px; }
label.check { display: flex; align-items: center; gap: 6px; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.row { display: flex; gap: 6px; align-items: center; margin-top: 6px; }
.row select, .row input[type=range] { flex: 1; }
button { padding: 6px 10px; font-size: 12px; border: 1px solid #d5dae2; background: #fff; border-radius: 6px; cursor: pointer; }
button:hover:not(:disabled) { border-color: #3d7ae6; color: #2f66c8; }
button:disabled { opacity: .45; cursor: default; }
button.wide { width: 100%; margin-top: 8px; }
button.link { border: none; background: none; color: #2f66c8; padding: 0 4px; }
.tabs { display: flex; gap: 4px; background: #eef1f5; padding: 3px; border-radius: 7px; margin-top: 8px; }
.tabs button { flex: 1; border: none; background: transparent; }
.tabs button.active { background: #fff; color: #2f66c8; font-weight: 700; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.layer { margin-bottom: 4px; }
.layer input[type=range] { width: 100%; }
.hint { font-size: 11.5px; color: #5d6a77; margin: 6px 0 0; line-height: 1.45; }
.muted { color: #8a95a1; }
.badge { display: inline-block; padding: 1px 6px; border-radius: 9px; font-size: 10.5px; font-weight: 600; }
.badge.cell { background: #e7f0ff; color: #2b5fb8; }
.badge.point { background: #e9f7ee; color: #23804a; }
.status { padding: 8px 14px; font-size: 11px; color: #7b8794; border-top: 1px solid #eef1f5; }
.status.error { color: #b42318; background: #fff4f2; }
details summary { font-size: 10.5px; text-transform: uppercase; letter-spacing: .06em; color: #6b7785; cursor: pointer; }
.kv { width: 100%; border-collapse: collapse; font-size: 11.5px; margin-top: 6px; }
.kv td { padding: 3px 4px; vertical-align: top; border-bottom: 1px solid #f2f4f7; }
.kv td:first-child { color: #6b7785; white-space: nowrap; }
.kv tr.active td { font-weight: 700; color: #1f2d3d; }
.right { position: absolute; right: 12px; bottom: 12px; display: flex; flex-direction: column; gap: 10px; align-items: flex-end; z-index: 5; }
.probe { background: rgba(255,255,255,.97); border: 1px solid #dfe3ea; border-radius: 10px; padding: 8px 10px; width: 330px;
  max-height: 50vh; overflow: auto; box-shadow: 0 6px 20px rgba(0,0,0,.08); }
.probe-head { display: flex; justify-content: space-between; font-size: 12px; }
@media (max-width: 720px) {
  .panel { width: calc(100% - 24px); bottom: auto; max-height: 55vh; }
  .probe { width: calc(100vw - 24px); }
}
</style>
