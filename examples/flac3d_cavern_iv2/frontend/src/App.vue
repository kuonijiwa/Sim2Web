<template>
  <main class="app-shell">
    <div ref="vtkContainer" class="vtk-view"></div>

    <section class="control-panel">
      <h1>Open cavern-surface example</h1>
      <p class="role">INNER EXCAVATION SURFACE · IV-2</p>

      <label>Field</label>
      <select v-model="activeScalar" @change="applyScalar">
        <option v-for="field in fields" :key="field" :value="field">
          {{ fieldLabel(field) }}
        </option>
      </select>

      <div class="row">
        <label><input v-model="showSection" type="checkbox" @change="loadSection" /> SECTION</label>
      </div>

      <div class="axis-row">
        <button v-for="axis in ['x', 'y', 'z']" :key="axis" @click="setAxis(axis)">
          {{ axis.toUpperCase() }} section
        </button>
      </div>

      <input
        v-model.number="sliceIndex"
        type="range"
        min="0"
        :max="Math.max(0, currentSlices.length - 1)"
        @input="loadSection"
      />

      <div class="axis-row">
        <button @click="align('x')">X view</button>
        <button @click="align('y')">Y view</button>
        <button @click="align('z')">Z view</button>
      </div>
      <button class="wide" @click="resetCamera">Reset camera</button>
      <p class="status">{{ status }}</p>
      <p class="status">{{ rangeLabel }}</p>
    </section>
  </main>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue';
import '@kitware/vtk.js/Rendering/Profiles/Geometry';
import vtkFullScreenRenderWindow from '@kitware/vtk.js/Rendering/Misc/FullScreenRenderWindow';
import vtkXMLPolyDataReader from '@kitware/vtk.js/IO/XML/XMLPolyDataReader';
import vtkActor from '@kitware/vtk.js/Rendering/Core/Actor';
import vtkMapper from '@kitware/vtk.js/Rendering/Core/Mapper';
import vtkColorTransferFunction from '@kitware/vtk.js/Rendering/Core/ColorTransferFunction';
import vtkScalarBarActor from '@kitware/vtk.js/Rendering/Core/ScalarBarActor';

const vtkContainer = ref(null);
const indexData = ref(null);
const fields = ref([]);
const activeScalar = ref('');
const activeAxis = ref('x');
const sliceIndex = ref(0);
const showSection = ref(true);
const status = ref('Loading…');
const rangeLabel = ref('');

let renderer;
let renderWindow;
let fullScreen;
let scalarBar;
const lut = vtkColorTransferFunction.newInstance();
const surface = makePipeline();
const section = makePipeline();

const stageConfig = computed(() => indexData.value?.['IV-2'] ?? null);
const currentSlices = computed(() => stageConfig.value?.slices?.[activeAxis.value] ?? []);

function makePipeline() {
  const reader = vtkXMLPolyDataReader.newInstance();
  const mapper = vtkMapper.newInstance({ lookupTable: lut, useLookupTableScalarRange: true });
  const actor = vtkActor.newInstance({ mapper });
  actor.setVisibility(false);
  return { reader, mapper, actor };
}

function isStress(name) {
  return name.toLowerCase().includes('stress');
}

function isCategorical(name) {
  const lower = name.toLowerCase();
  return ['group', 'material', 'state', 'plastic', '_id'].some((token) => lower.includes(token));
}

function fieldLabel(name) {
  const labels = {
    TotalDisplacement: 'Displacement magnitude (m)',
    X_Disp: 'X displacement (m)',
    Y_Disp: 'Y displacement (m)',
    Z_Disp: 'Z displacement (m)',
    Stress_XX: 'σxx (MPa)',
    Stress_YY: 'σyy (MPa)',
    Stress_ZZ: 'σzz (MPa)',
    Stress_Max_Principal: 'Maximum principal stress (MPa)',
    Stress_Mid_Principal: 'Intermediate principal stress (MPa)',
    Stress_Min_Principal: 'Minimum principal stress (MPa)',
  };
  const label = labels[name] ?? name;
  return isStress(name) ? `${label} · exact cell` : label;
}

function availableAssociation(polydata, name) {
  if (isStress(name) || isCategorical(name)) {
    if (polydata.getCellData().getArrayByName(name)) return 'cell';
  }
  if (polydata.getPointData().getArrayByName(name)) return 'point';
  if (polydata.getCellData().getArrayByName(name)) return 'cell';
  return null;
}

function applyPipelineScalar(pipeline) {
  const data = pipeline.reader.getOutputData(0);
  if (!data || !activeScalar.value) return null;
  const association = availableAssociation(data, activeScalar.value);
  if (!association) return null;
  pipeline.mapper.setColorByArrayName(activeScalar.value);
  if (association === 'cell') {
    pipeline.mapper.setScalarModeToUseCellFieldData();
    pipeline.mapper.setInterpolateScalarsBeforeMapping(false);
  } else {
    pipeline.mapper.setScalarModeToUsePointFieldData();
    pipeline.mapper.setInterpolateScalarsBeforeMapping(true);
  }
  const array = association === 'cell'
    ? data.getCellData().getArrayByName(activeScalar.value)
    : data.getPointData().getArrayByName(activeScalar.value);
  return array?.getRange?.() ?? null;
}

function applyScalar() {
  const ranges = [applyPipelineScalar(surface), applyPipelineScalar(section)].filter(Boolean);
  if (!ranges.length) return;
  const min = Math.min(...ranges.map((range) => range[0]));
  const max = Math.max(...ranges.map((range) => range[1]));
  lut.removeAllPoints();
  if (isCategorical(activeScalar.value)) {
    const colors = [[0, 0.45, 0.70], [0.90, 0.62, 0], [0, 0.62, 0.45], [0.80, 0.47, 0.65], [0.84, 0.37, 0]];
    for (let code = Math.round(min); code <= Math.round(max); code += 1) {
      const color = colors[(code - Math.round(min)) % colors.length];
      lut.addRGBPoint(code - 0.5, ...color);
      lut.addRGBPoint(code + 0.5 - 1e-6, ...color);
    }
    rangeLabel.value = 'Category codes: ' + Array.from({ length: Math.round(max - min) + 1 }, (_, i) => Math.round(min) + i).join(', ');
  } else {
    lut.addRGBPoint(min, 0.05, 0.1, 0.75);
    lut.addRGBPoint((min + max) / 2, 0.1, 0.85, 0.65);
    lut.addRGBPoint(max, 0.8, 0.05, 0.02);
    rangeLabel.value = 'Range: ' + min.toExponential(4) + ' to ' + max.toExponential(4);
  }
  lut.setMappingRange(min, max);
  scalarBar.setAxisLabel(fieldLabel(activeScalar.value));
  renderWindow.render();
}

async function loadSection() {
  if (!showSection.value || !currentSlices.value.length) {
    section.actor.setVisibility(false);
    renderWindow.render();
    return;
  }
  if (sliceIndex.value >= currentSlices.value.length) sliceIndex.value = 0;
  await section.reader.setUrl(currentSlices.value[sliceIndex.value], { loadData: true });
  section.mapper.setInputConnection(section.reader.getOutputPort());
  section.actor.setVisibility(true);
  applyScalar();
}

async function setAxis(axis) {
  activeAxis.value = axis;
  sliceIndex.value = Math.floor(currentSlices.value.length / 2);
  await loadSection();
}

function resetCamera() {
  renderer.resetCamera();
  renderer.resetCameraClippingRange();
  renderWindow.render();
}

function align(axis) {
  const bounds = renderer.computeVisiblePropBounds();
  const center = [(bounds[0] + bounds[1]) / 2, (bounds[2] + bounds[3]) / 2, (bounds[4] + bounds[5]) / 2];
  const distance = Math.max(bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4]) * 3;
  const camera = renderer.getActiveCamera();
  camera.setParallelProjection(true);
  camera.setFocalPoint(...center);
  if (axis === 'x') { camera.setPosition(center[0] + distance, center[1], center[2]); camera.setViewUp(0, 0, 1); }
  if (axis === 'y') { camera.setPosition(center[0], center[1] + distance, center[2]); camera.setViewUp(0, 0, 1); }
  if (axis === 'z') { camera.setPosition(center[0], center[1], center[2] + distance); camera.setViewUp(0, 1, 0); }
  renderer.resetCameraClippingRange();
  renderWindow.render();
}

onMounted(async () => {
  fullScreen = vtkFullScreenRenderWindow.newInstance({ rootContainer: vtkContainer.value, background: [1, 1, 1] });
  renderer = fullScreen.getRenderer();
  renderWindow = fullScreen.getRenderWindow();
  renderer.addActor(surface.actor);
  renderer.addActor(section.actor);
  scalarBar = vtkScalarBarActor.newInstance({ boxPosition: [0.88, 0.12], boxSize: [0.09, 0.72] });
  scalarBar.setScalarsToColors(lut);
  scalarBar.setAxisTextStyle({ fontColor: 'black' });
  scalarBar.setTickTextStyle({ fontColor: 'black' });
  renderer.addActor(scalarBar);

  const response = await fetch('model_cache/index.json');
  if (!response.ok) throw new Error(`index.json HTTP ${response.status}`);
  indexData.value = await response.json();
  fields.value = (stageConfig.value?.fields ?? []).filter((name) => !isCategorical(name) || name.endsWith('_ID'));
  activeScalar.value = fields.value.includes('TotalDisplacement') ? 'TotalDisplacement' : fields.value[0];
  await surface.reader.setUrl(stageConfig.value.cavity, { loadData: true });
  surface.mapper.setInputConnection(surface.reader.getOutputPort());
  surface.actor.setVisibility(true);
  sliceIndex.value = Math.floor(currentSlices.value.length / 2);
  await loadSection();
  applyScalar();
  await nextTick();
  resetCamera();
  requestAnimationFrame(() => requestAnimationFrame(() => renderWindow.render()));
  status.value = 'Ready · exact associations preserved';
});
</script>

<style>
html, body, #app, .app-shell { width: 100%; height: 100%; margin: 0; overflow: hidden; font-family: Arial, sans-serif; }
.vtk-view { position: absolute; inset: 0; }
.control-panel { position: absolute; top: 20px; left: 20px; width: 285px; padding: 18px; background: rgba(255,255,255,.94); border-radius: 10px; box-shadow: 0 5px 20px rgba(0,0,0,.16); }
h1 { margin: 0 0 5px; font-size: 18px; }
.role, .status { color: #53616d; font-size: 12px; }
select, input[type='range'], .wide { width: 100%; margin: 7px 0 12px; }
.row { margin: 8px 0; }
.axis-row { display: flex; gap: 6px; margin: 7px 0; }
button { flex: 1; padding: 7px; border: 1px solid #aab4bc; border-radius: 5px; background: #f6f8fa; cursor: pointer; }
</style>
