<template>
  <div class="fullscreen-viewport">
    <div ref="vtkContainer" class="absolute-full-canvas"></div>

    <!-- Camera controls -->
    <div class="floating-camera-nav">
      <div class="nav-title">Camera and axis views</div>
      <button class="reset-view-btn" @click="resetCameraView">
        ⟲ Reset view
      </button>
      <div class="axis-align-container">
        <button class="axis-btn btn-x" @click="alignToAxis('x')">X view</button>
        <button class="axis-btn btn-y" @click="alignToAxis('y')">Y view</button>
        <button class="axis-btn btn-z" @click="alignToAxis('z')">Z view</button>
      </div>
    </div>

    <!-- Scalar legend -->
    <div class="html-legend-card" v-if="availableScalars.length > 0 && legendTicks.length > 0">
      <div class="legend-card-title">{{ formatFieldName(activeScalar) }}</div>
      <div class="legend-card-body">
        <div class="legend-color-blocks-container">
          <div 
            v-for="(colorStr, cIdx) in legendColors" 
            :key="cIdx" 
            class="legend-color-block"
            :style="{ backgroundColor: colorStr }"
          ></div>
        </div>
        <div class="legend-ticks-axis">
          <span v-for="(tick, idx) in legendTicks" :key="idx" class="legend-tick-label">
            {{ tick }}
          </span>
        </div>
      </div>
    </div>

    <!-- Floating control panel -->
    <div class="glass-dock-panel">
      <div class="scroll-body">
        <!-- 1. Excavation stage selection -->
        <div class="panel-section" v-if="stageList.length > 0">
          <label class="section-title" style="color: #e6a23c;">Excavation stage</label>
          <div class="stage-control-box">
            <div class="stage-action-bar">
              <button @click="prevStage" :disabled="currentStageIndex <= 0" class="step-arrow-btn">◀ Previous</button>
              <button @click="nextStage" :disabled="currentStageIndex >= stageList.length - 1" class="step-arrow-btn">Next ▶</button>
            </div>
            <div style="margin-top: 10px;">
              <select v-model.number="currentStageIndex" @change="onStageIndexChange" class="dark-select stage-select">
                <option v-for="(name, index) in stageList" :key="name" :value="index">
                  Stage {{ index + 1 }}: {{ name }}
                </option>
              </select>
            </div>
            <div class="stage-name-display">Current stage: <span>Stage {{ currentStageIndex + 1 }}: {{ activeStageName }}</span></div>
          </div>
        </div>

        <!-- 2. Field selection in a two-column grid -->
        <div class="panel-section border-top" v-if="availableScalars.length > 0">
          <label class="section-title" style="color: #409eff;">Select field</label>
          <div class="scalar-grid-box">
            <button
              v-for="field in availableScalars"
              :key="field"
              :title="formatFieldName(field)"
              :class="['scalar-grid-btn', { active: activeScalar === field }]"
              @click="changeScalar(field)"
            >
              {{ formatFieldName(field) }}
            </button>
          </div>
        </div>

        <!-- 3. Layer and section controls -->
        <div class="panel-section border-top">
          <label class="section-title">Model layers</label>
          <div class="switch-row">
            <label class="inner-label">Solid-group surfaces</label>
            <input type="checkbox" v-model="showFullModel" @change="updateVisibility" class="ios-checkbox" />
          </div>
          <div class="slider-group" v-if="showFullModel">
            <label class="sub-label">Surface opacity: {{ (fullModelOpacity * 100).toFixed(0) }}%</label>
            <input type="range" v-model.number="fullModelOpacity" max="1.0" min="0.0" step="0.05" @input="updateOpacity"/>
          </div>

          <div class="switch-row" style="margin-top: 12px;" v-if="hasCavityData">
            <label class="inner-label" style="color: #4db8ff;">Excavation interface</label>
            <input type="checkbox" v-model="showCavityModel" @change="updateVisibility" class="ios-checkbox" />
          </div>
        </div>

        <div class="panel-section border-top">
          <div class="switch-row">
            <label class="section-title">Show section</label>
            <input type="checkbox" v-model="sliceMode" @change="toggleSliceMode" class="ios-checkbox">
          </div>
          
          <div v-if="sliceMode" class="slice-inner-box">
            <label class="sub-label">Section axis:</label>
            <div class="tab-button-group">
              <button :class="{ active: currentAxis === 'x' }" @click="setAxis('x')">X section</button>
              <button :class="{ active: currentAxis === 'y' }" @click="setAxis('y')">Y section</button>
              <button :class="{ active: currentAxis === 'z' }" @click="setAxis('z')">Z section</button>
            </div>
            <div style="margin-top:12px;">
              <label class="sub-label">Section position (m): <span class="highlight-val">{{ currentSliceValue }}</span></label>
              <input type="range" v-model.number="currentSliceIndex" :max="maxIndex" min="0" step="1" @input="onSliceSliderInput"/>
            </div>
          </div>
        </div>

        <div class="panel-section border-top">
          <div class="switch-row">
            <label class="inner-label">Show mesh edges</label>
            <input type="checkbox" v-model="showEdges" @change="updateEdges" class="ios-checkbox">
          </div>
        </div>
      </div>

      <div class="panel-footer">
        <div class="status-badge">Status: {{ statusMsg }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, nextTick } from 'vue';
import '@kitware/vtk.js/Rendering/Profiles/Geometry';
import vtkFullScreenRenderWindow from '@kitware/vtk.js/Rendering/Misc/FullScreenRenderWindow';
import vtkXMLPolyDataReader from '@kitware/vtk.js/IO/XML/XMLPolyDataReader';
import vtkActor from '@kitware/vtk.js/Rendering/Core/Actor';
import vtkMapper from '@kitware/vtk.js/Rendering/Core/Mapper';
import vtkColorTransferFunction from '@kitware/vtk.js/Rendering/Core/ColorTransferFunction';
import vtkAxesActor from '@kitware/vtk.js/Rendering/Core/AxesActor';
import vtkOrientationMarkerWidget from '@kitware/vtk.js/Interaction/Widgets/OrientationMarkerWidget';

const JET_PRESET = { "ColorSpace": "RGB", "Name": "Jet", "RGBPoints": [0.0,0,0,0.5, 0.11,0,0,1, 0.34,0,1,1, 0.65,1,1,0, 0.89,1,0,0, 1.0,0.5,0,0] };

const vtkContainer = ref(null);
const indexData = ref({});
const modelNames = ref([]);
const selectedModel = ref('');

const currentStageIndex = ref(0);
const stageList = ref([]);
const availableScalars = ref([]);
const activeScalar = ref('');
const colorBands = ref(8); 
const showEdges = ref(false);

const showFullModel = ref(true);
const fullModelOpacity = ref(0.65);
const showCavityModel = ref(true);

const sliceMode = ref(true);
const currentAxis = ref('y');
const currentSliceIndex = ref(0);
const statusMsg = ref('Initializing...');

const legendTicks = ref([]);
const legendColors = ref([]);

let context = null;
let lut = null;
let axesWidget = null;

const fullModel = { reader: null, mapper: null, actor: null };
const cavityModel = { reader: null, mapper: null, actor: null };
const sliceModelObj = { reader: null, mapper: null, actor: null };

const activeStageConfig = computed(() => {
  if (!selectedModel.value || !indexData.value[selectedModel.value]) return null;
  const cfg = indexData.value[selectedModel.value];
  if (cfg.stages) {
    const currentStageName = stageList.value[currentStageIndex.value];
    return cfg.stages[currentStageName] || null;
  }
  return cfg;
});

const activeStageName = computed(() => stageList.value[currentStageIndex.value] || 'N/A');
const hasCavityData = computed(() => !!activeStageConfig.value?.cavity);

// Identify categorical fields
const isCategoricalField = computed(() => {
  if (!activeScalar.value) return false;
  const name = activeScalar.value.toLowerCase();
  
  if (name.includes('stress') || name.includes('disp')) return false;

  return name.includes('group') || 
         name.includes('material') || 
         name.includes('mat') ||
         name.includes('state') || 
         name.includes('plastic') || 
         name.includes('block');
});

const currentFileList = computed(() => activeStageConfig.value?.slices?.[currentAxis.value] || []);
const maxIndex = computed(() => Math.max(0, currentFileList.value.length - 1));
const currentSliceValue = computed(() => {
  if (!currentFileList.value.length) return 'N/A';
  return currentFileList.value[currentSliceIndex.value]?.split('_').pop().replace('.vtp', '') || 'N/A';
});

onMounted(async () => {
  try {
    const res = await fetch('model_cache/index.json');
    const rawData = await res.json();
    
    const firstKey = Object.keys(rawData)[0];
    if (firstKey && rawData[firstKey] && !rawData[firstKey].stages && rawData[firstKey].full) {
      const stageOrder = Object.keys(rawData).sort((a, b) => {
        const numA = parseInt(a.match(/\d+$/)?.[0] || 0);
        const numB = parseInt(b.match(/\d+$/)?.[0] || 0);
        return numA - numB;
      });
      indexData.value = {
        "DefaultModel": {
          stages: rawData,
          stage_order: stageOrder
        }
      };
    } else {
      indexData.value = rawData;
    }
    
    modelNames.value = Object.keys(indexData.value);
    if (modelNames.value.length > 0) {
      selectedModel.value = modelNames.value[0];
    }
  } catch (e) {
    statusMsg.value = "Failed to load model index";
    return;
  }

  const fullScreen = vtkFullScreenRenderWindow.newInstance({
    container: vtkContainer.value,
    rootContainer: vtkContainer.value,
    background: [1.0, 1.0, 1.0], 
  });
  
  const renderer = fullScreen.getRenderer();
  const renderWindow = fullScreen.getRenderWindow();

  const axesActor = vtkAxesActor.newInstance();
  axesWidget = vtkOrientationMarkerWidget.newInstance({
    actor: axesActor,
    interactor: renderWindow.getInteractor(),
  });
  axesWidget.setViewportCorner(vtkOrientationMarkerWidget.Corners.BOTTOM_LEFT);
  axesWidget.setViewportSize(0.12);

  lut = vtkColorTransferFunction.newInstance();

  [fullModel, cavityModel, sliceModelObj].forEach(obj => {
    obj.reader = vtkXMLPolyDataReader.newInstance();
    obj.mapper = vtkMapper.newInstance({ lookupTable: lut, useLookupTableScalarRange: true });
    obj.actor = vtkActor.newInstance({ mapper: obj.mapper });
    obj.mapper.setInputConnection(obj.reader.getOutputPort());
    renderer.addActor(obj.actor);
  });

  context = { renderer, renderWindow, fullScreen };

  window.addEventListener('resize', () => context.fullScreen.resize());
  onModelChange(true); 
});

// Display labels for scalar, material and group fields
function formatFieldName(name) {
  if (!name) return '';
  const dict = {
    'TotalDisplacement': 'Displacement (m)',
    'X_Disp': 'X displacement (m)',
    'Y_Disp': 'Y displacement (m)',
    'Z_Disp': 'Z displacement (m)',
    'Stress_XX': 'Stress σxx (Pa)',
    'Stress_YY': 'Stress σyy (Pa)',
    'Stress_ZZ': 'Stress σzz (Pa)',
    'Stress_Max_Principal': 'Principal σ1 (Pa)',
    'Stress_Mid_Principal': 'Principal σ2 (Pa)',
    'Stress_Min_Principal': 'Principal σ3 (Pa)',
  };
  if (dict[name]) return name.toLowerCase().includes('stress') ? `${dict[name]} · cell data` : dict[name];

  const lower = name.toLowerCase();
  
  // Identify material fields
  if (lower.includes('material') || lower.includes('mat')) {
    return 'Material';
  }
  
  // Recognize supported group field names
  if (lower.includes('group') || lower.includes('block') || lower.includes('zone') || lower.includes('slot')) {
    return 'Model group';
  }
  
  if (lower.includes('state') || lower.includes('plastic')) {
    return 'Plastic state';
  }
  return name;
}

// Filter internal indices while retaining group fields
function processFields(fields) {
  if (!fields || !Array.isArray(fields)) return [];

  const order = ['TotalDisplacement', 'X_Disp', 'Y_Disp', 'Z_Disp', 'Stress_Max_Principal', 'Stress_Mid_Principal', 'Stress_Min_Principal'];
  
  const sorted = [];
  order.forEach(k => { if (fields.includes(k)) sorted.push(k); });
  fields.forEach(k => { if (!order.includes(k)) sorted.push(k); });

  const result = [];
  const seenDisplayNames = new Set();

  for (const rawField of sorted) {
    const rawLower = rawField.toLowerCase();
    
    // Exclude VTK-generated cell and point indices
    if (rawLower.includes('vtkoriginal') || rawLower.includes('cellids') || rawLower.includes('pointids')) {
      continue;
    }

    const displayName = formatFieldName(rawField);

    // Avoid duplicate display labels
    if (seenDisplayNames.has(displayName)) {
      continue;
    }

    seenDisplayNames.add(displayName);
    result.push(rawField);
  }

  return result;
}

async function onModelChange(forceResetCamera = true) {
  const cfg = indexData.value[selectedModel.value];
  if (!cfg) return;

  if (cfg.stages) {
    stageList.value = cfg.stage_order || Object.keys(cfg.stages);
  } else {
    stageList.value = ['Stage 1'];
  }
  currentStageIndex.value = 0; 

  await nextTick();
  if (currentFileList.value.length > 0) {
    currentSliceIndex.value = Math.floor(maxIndex.value / 2);
  }
  await loadStageFluidData(forceResetCamera);
}

function prevStage() { if (currentStageIndex.value > 0) { currentStageIndex.value--; onStageIndexChange(); } }
function nextStage() { if (currentStageIndex.value < stageList.value.length - 1) { currentStageIndex.value++; onStageIndexChange(); } }
async function onStageIndexChange() { await loadStageFluidData(false); }

async function loadStageFluidData(resetCamera = false) {
  const cfg = activeStageConfig.value;
  if (!cfg) return;

  availableScalars.value = processFields(cfg.fields);
  if (!activeScalar.value || !availableScalars.value.includes(activeScalar.value)) {
    activeScalar.value = availableScalars.value[0] || '';
  }

  statusMsg.value = `Loading model...`;
  
  const requests = [
    fullModel.reader.setUrl(cfg.full, { loadData: true })
  ];
  if (cfg.cavity) {
    requests.push(cavityModel.reader.setUrl(cfg.cavity, { loadData: true }));
  }
  if (sliceMode.value && currentFileList.value.length) {
    requests.push(sliceModelObj.reader.setUrl(currentFileList.value[currentSliceIndex.value], { loadData: true }));
  }
  
  await Promise.all(requests);
  
  [fullModel, cavityModel, sliceModelObj].forEach((obj) => {
    const data = obj.reader.getOutputData(0);
    if (data) {
      data.buildLinks();
      data.modified();
    }
    obj.reader.modified();
    obj.mapper.update();
  });
  
  updateVisibility();
  updateOpacity();
  updateMapperArraysOnly();
  updateEdges();
  updateScalars();

  if (resetCamera) {
    await nextTick();
    resetCameraView(); 
  } else {
    context.renderWindow.render();
  }

  if (axesWidget && !axesWidget.getEnabled()) {
    axesWidget.setEnabled(true);
    context.renderWindow.render();
  }
  statusMsg.value = "Ready";
}

function changeScalar(field) {
  activeScalar.value = field;
  updateScalars();
}

async function onSliceSliderInput() {
  await loadSliceFile();
}

async function loadSliceFile() {
  if (!sliceMode.value || !currentFileList.value.length) return;
  if (currentSliceIndex.value > maxIndex.value) currentSliceIndex.value = Math.floor(maxIndex.value / 2);
  
  await sliceModelObj.reader.setUrl(currentFileList.value[currentSliceIndex.value], { loadData: true });
  sliceModelObj.reader.modified();
  sliceModelObj.mapper.update();
  
  updateMapperArraysOnly();
  if (context && context.renderWindow) {
    context.renderWindow.render();
  }
}

function updateMapperArraysOnly() {
  let globalMin;
  let globalMax;
  const cfg = activeStageConfig.value; 
  
  if (cfg && cfg.global_ranges && cfg.global_ranges[activeScalar.value]) {
    const r = cfg.global_ranges[activeScalar.value];
    globalMin = r[0]; 
    globalMax = r[1];
  }
  if (!Number.isFinite(globalMin) || !Number.isFinite(globalMax)) throw new Error('Missing validated scalar range: ' + activeScalar.value);

  [fullModel, cavityModel, sliceModelObj].forEach((obj) => {
    const polydata = obj.reader.getOutputData(0);
    if (!polydata) return;
    obj.mapper.setColorByArrayName(activeScalar.value);
    if (isCategoricalField.value || activeScalar.value.toLowerCase().includes('stress')) {
      obj.mapper.setScalarModeToUseCellFieldData();
      obj.mapper.setInterpolateScalarsBeforeMapping(false); 
    } else {
      obj.mapper.setScalarModeToUsePointFieldData();
      obj.mapper.setInterpolateScalarsBeforeMapping(true);  
    }
  });
  buildDiscreteLUT([globalMin, globalMax], isCategoricalField.value ? Math.max(1, Math.round(globalMax - globalMin + 1)) : colorBands.value);
}

function updateScalars() {
  updateMapperArraysOnly();

  let globalMin;
  let globalMax;
  const cfg = activeStageConfig.value; 
  if (cfg && cfg.global_ranges && cfg.global_ranges[activeScalar.value]) {
    const r = cfg.global_ranges[activeScalar.value];
    globalMin = r[0]; 
    globalMax = r[1];
  }
  if (!Number.isFinite(globalMin) || !Number.isFinite(globalMax)) throw new Error('Missing validated scalar range: ' + activeScalar.value);

  const ticks = [];
  const colors = [];
  const span = globalMax - globalMin;
  const bands = isCategoricalField.value ? Math.max(1, Math.round(globalMax - globalMin + 1)) : colorBands.value;

  const stepSize = span / bands;
  for (let i = bands - 1; i >= 0; i--) {
    const midVal = globalMin + (i + 0.5) * stepSize;
    if (isCategoricalField.value) {
      ticks.push(Math.round(midVal));
    } else {
      ticks.push(Math.abs(midVal) > 1e4 || (Math.abs(midVal) < 1e-2 && midVal !== 0) ? midVal.toExponential(3) : midVal.toFixed(3));
    }
    const rgb = [];
    lut.getColor(midVal, rgb);
    colors.push(`rgb(${Math.round(rgb[0]*255)}, ${Math.round(rgb[1]*255)}, ${Math.round(rgb[2]*255)})`);
  }

  legendTicks.value = ticks;
  legendColors.value = colors;
  context.renderWindow.render();
}

function buildDiscreteLUT(range, numBands) {
  lut.removeAllPoints();
  const [min, max] = range;
  const span = max - min;
  if (span <= 0) { lut.addRGBPoint(min, 0.2, 0.5, 0.8); return; }
  const tempLut = vtkColorTransferFunction.newInstance();
  tempLut.applyColorMap(JET_PRESET);
  tempLut.setMappingRange(min, max);
  const stepSize = span / numBands;
  for (let i = 0; i < numBands; i++) {
    const valStart = min + i * stepSize;
    const valEnd = min + (i + 1) * stepSize;
    const color = [];
    tempLut.getColor(min + (i + 0.5) * stepSize, color);
    lut.addRGBPoint(valStart, color[0], color[1], color[2]);
    lut.addRGBPoint(valEnd - (span * 1e-6), color[0], color[1], color[2]);
  }
}

function updateVisibility() {
  fullModel.actor.setVisibility(showFullModel.value);
  cavityModel.actor.setVisibility(hasCavityData.value && showFullModel.value);
  sliceModelObj.actor.setVisibility(sliceMode.value);
  context.renderWindow.render();
}

function resetCameraView() {
  if (!context) return;
  const camera = context.renderer.getActiveCamera();
  camera.setParallelProjection(true); 

  camera.setPosition(-246.63, 456.82, 1055.37); 
  camera.setFocalPoint(479.16, -134.53, 516.97);
  camera.setParallelScale(403.46 );
  camera.setViewUp(0, 0, 1);    

  context.renderer.resetCameraClippingRange();
  context.renderWindow.render();
}

function alignToAxis(axis) {
  if (!context) return;
  const camera = context.renderer.getActiveCamera();
  
  const activeActor = sliceMode.value ? sliceModelObj.actor : fullModel.actor;
  const bounds = activeActor.getBounds();
  
  const cx = (bounds[0] + bounds[1]) / 2;
  const cy = (bounds[2] + bounds[3]) / 2;
  const cz = (bounds[4] + bounds[5]) / 2;
  
  camera.setFocalPoint(cx, cy, cz);
  camera.setParallelProjection(true);

  const maxSpan = Math.max(bounds[1]-bounds[0], bounds[3]-bounds[2], bounds[4]-bounds[5]) || 1000;
  const distance = maxSpan * 2; 

  if (axis === 'x') {
    camera.setPosition(cx + distance, cy, cz);
    camera.setViewUp(0, 0, 1);
  } else if (axis === 'y') {
    camera.setPosition(cx, cy + distance, cz);
    camera.setViewUp(0, 0, 1);
  } else if (axis === 'z') {
    camera.setPosition(cx, cy, cz + distance);
    camera.setViewUp(0, 1, 0);
  }

  context.renderer.resetCameraClippingRange();
  context.renderWindow.render();
}

function updateOpacity() {
  fullModel.actor.getProperty().setOpacity(fullModelOpacity.value);
  cavityModel.actor.getProperty().setOpacity(1.0); 
  sliceModelObj.actor.getProperty().setOpacity(1.0);
  context.renderWindow.render();
}

function updateEdges() {
  [fullModel, cavityModel, sliceModelObj].forEach((obj) => {
    obj.actor.getProperty().setEdgeVisibility(showEdges.value);
    obj.actor.getProperty().setEdgeColor(0.2, 0.2, 0.2);
  });
  context.renderWindow.render();
}

function toggleSliceMode() {
  if (sliceMode.value) {
    currentSliceIndex.value = Math.floor(maxIndex.value / 2);
    fullModelOpacity.value = 0.15; 
  } else {
    fullModelOpacity.value = 1.0;
  }
  updateOpacity();
  loadSliceFile().then(() => updateVisibility());
}

function setAxis(ax) {
  currentAxis.value = ax;
  currentSliceIndex.value = Math.floor(maxIndex.value / 2);
  loadSliceFile();
}
</script>

<style scoped>
.fullscreen-viewport { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; margin: 0; padding: 0; overflow: hidden; background-color: #f0f2f5; }
.absolute-full-canvas { width: 100%; height: 100%; position: absolute; top: 0; left: 0; z-index: 1; }

/* Left control panel */
.glass-dock-panel { 
  position: absolute; 
  top: 16px; 
  left: 20px; 
  width: 320px; 
  max-height: calc(100vh - 32px); 
  background: rgba(255, 255, 255, 0.92); 
  backdrop-filter: blur(12px); 
  border: 1px solid rgba(220, 223, 230, 0.8); 
  border-radius: 14px; 
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.12); 
  z-index: 10; 
  display: flex; 
  flex-direction: column; 
  color: #2c3e50; 
}

.scroll-body { padding: 16px 20px; overflow-y: auto; flex: 1; }
.panel-section { padding-bottom: 12px; margin-bottom: 12px; }
.border-top { border-top: 1px solid #f2f4f8; padding-top: 12px; }
.section-title { display: block; font-size: 11px; font-weight: 800; color: #34495e; margin-bottom: 8px; }

/* Stage selector styles */
.stage-control-box { background: #fffbf0; border: 1px solid #fadead; padding: 12px; border-radius: 8px; }
.stage-action-bar { display: flex; gap: 8px; }
.step-arrow-btn { flex: 1; padding: 8px; font-size: 11px; font-weight: bold; background: #fff; border: 1px solid #dcdfe6; color: #606266; border-radius: 6px; cursor: pointer; transition: all 0.15s; }
.step-arrow-btn:hover:not(:disabled) { background: #fdf6ec; border-color: #f5dab1; color: #e6a23c; }
.step-arrow-btn:disabled { background: #f5f7fa; color: #c0c4cc; cursor: not-allowed; border-color: #e4e7ed; }
.stage-select { border-color: #f5dab1 !important; font-weight: bold; }
.stage-name-display { font-size: 12px; font-weight: bold; margin-top: 8px; color: #c27803; }
.stage-name-display span { color: #e6a23c; }

/* Two-column field selector */
.scalar-grid-box {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  background: #f8f9fb;
  border: 1px solid #e4e7ed;
  padding: 10px;
  border-radius: 8px;
}

.scalar-grid-btn {
  padding: 8px 4px;
  font-size: 11px;
  font-weight: 600;
  color: #606266;
  background: #ffffff;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  cursor: pointer;
  text-align: center;
  transition: all 0.15s ease;
  white-space: normal;
  overflow-wrap: anywhere;
  line-height: 1.3;
  min-height: 44px;
}

.scalar-grid-btn:hover {
  background: #ecf5ff;
  border-color: #c6e2ff;
  color: #409eff;
}

.scalar-grid-btn.active {
  background: #409eff;
  border-color: #409eff;
  color: #ffffff;
  font-weight: bold;
  box-shadow: 0 2px 6px rgba(64, 158, 255, 0.3);
}

.floating-camera-nav {
  position: absolute;
  top: 16px;
  right: 20px;
  z-index: 100;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(220, 223, 230, 0.9);
  border-radius: 12px;
  padding: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  width: 200px;
}

.nav-title { font-size: 11px; font-weight: 800; color: #34495e; margin-bottom: 8px; text-align: center; }
.reset-view-btn { width: 100%; background: #409eff; color: white; border: none; padding: 7px; font-size: 11px; font-weight: bold; border-radius: 6px; cursor: pointer; transition: background 0.2s; }
.reset-view-btn:hover { background: #66b1ff; }

.axis-align-container { display: flex; gap: 6px; margin-top: 8px; }
.axis-btn { flex: 1; padding: 6px 0; font-size: 11px; font-weight: bold; color: #ffffff; border: none; border-radius: 4px; cursor: pointer; transition: all 0.15s ease; box-shadow: 0 2px 6px rgba(0,0,0,0.1); }
.btn-x { background: #e6a23c; } .btn-x:hover { background: #ebb563; }
.btn-y { background: #409eff; } .btn-y:hover { background: #66b1ff; }
.btn-z { background: #67c23a; } .btn-z:hover { background: #85ce61; }

.inner-label { font-size: 12px; font-weight: bold; color: #5a6a7a; }
.sub-label { font-size: 11px; color: #909399; display: block; margin-bottom: 4px; }
.switch-row { display: flex; justify-content: space-between; align-items: center; }
.dark-select { width: 100%; padding: 8px; background: #ffffff; border: 1px solid #dcdfe6; color: #303133; border-radius: 6px; font-size: 12px; outline: none; }
.tab-button-group { display: flex; gap: 4px; background: #f0f2f5; padding: 3px; border-radius: 6px; }
.tab-button-group button { flex: 1; padding: 6px; background: transparent; border: none; font-size: 11px; color: #606266; cursor: pointer; border-radius: 4px; }
.tab-button-group button.active { background: #ffffff; color: #409eff; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
.slice-inner-box { margin-top: 10px; padding: 10px; background: #f8f9fb; border-radius: 8px; border: 1px solid #ebeef5; }
.highlight-val { color: #e6a23c; font-weight: bold; }

.panel-footer { padding: 10px 16px; background: #ffffff; border-top: 1px solid #f2f4f8; border-bottom-left-radius: 13px; border-bottom-right-radius: 13px; }
.status-badge { font-size: 10px; color: #909399; text-align: right; }

.html-legend-card { position: absolute; bottom: 20px; right: 20px; width: 135px; background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(8px); border: 1px solid rgba(220, 223, 230, 0.9); border-radius: 10px; padding: 12px 10px; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1); z-index: 100; font-family: sans-serif; }
.legend-card-title { font-size: 12px; font-weight: 800; color: #1f2d3d; text-align: center; margin-bottom: 10px; border-bottom: 1px solid #ebedf0; padding-bottom: 6px; }
.legend-card-body { display: flex; height: 240px; gap: 6px; padding: 0 2px; }
.legend-color-blocks-container { width: 13px; height: 100%; display: flex; flex-direction: column; border: 1px solid rgba(0,0,0,0.12); border-radius: 3px; overflow: hidden; }
.legend-color-block { flex: 1; width: 100%; }
.legend-ticks-axis { flex: 1; display: flex; flex-direction: column; height: 100%; }
.legend-tick-label { flex: 1; display: flex; align-items: center; font-size: 11px; font-weight: 700; color: #34495e; line-height: 1; font-family: "Courier New", Courier, monospace; padding-left: 2px; }

input[type=range] { width: 100%; margin: 4px 0; }
</style>
