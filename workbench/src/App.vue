<template>
  <div class="app" :class="{ viewing: mode === 'view' }">
    <header class="top">
      <div class="brand">Sim2Web <span class="muted">workbench</span></div>
      <div class="project" :title="state?.dir">{{ state?.config?.title || 'New project' }}
        <span class="muted">· {{ state?.dir }}</span></div>
      <div class="modes" role="tablist">
        <button :class="{ on: mode === 'process' }" @click="mode = 'process'">Process</button>
        <button :class="{ on: mode === 'view' }" :disabled="!viewerUrl" @click="mode = 'view'">View</button>
      </div>
    </header>

    <nav class="steps" v-if="mode === 'process'">
      <button v-for="(s, i) in STEPS" :key="s.id" class="step" :class="[status[s.id], { active: i === stepIndex }]"
              @click="stepIndex = i">
        <span class="badge">{{ status[s.id] === 'done' ? '✓' : status[s.id] === 'attention' ? '!' : i + 1 }}</span>
        {{ s.label }}
      </button>
      <div class="saved muted">Settings are saved to<br><code>case.yaml</code> as you edit</div>
    </nav>

    <main class="centre">
      <section class="form" v-if="mode === 'process'">
        <p v-if="loadError" class="error">{{ loadError }}</p>
        <component v-else-if="state" :is="stepComponent" :state="state" :cfg="cfg" :busy="busy" :run="run"
                   @update="update" @set-config="replaceConfig" />
        <div class="nav-buttons" v-if="state">
          <button :disabled="stepIndex === 0" @click="stepIndex -= 1">Back</button>
          <button class="primary" :disabled="stepIndex === STEPS.length - 1" @click="stepIndex += 1">Next</button>
        </div>
      </section>
      <section class="viewer">
        <iframe v-if="viewerUrl" :key="viewerUrl" :src="viewerUrl" title="Package viewer"></iframe>
        <div v-else class="placeholder">
          <p><strong>No package yet</strong></p>
          <p class="muted">Open a model, then use Preview (step 3) or Build (step 5).
            The package is shown here in the viewer that is published.</p>
        </div>
        <div class="viewer-label" v-if="viewerUrl">{{ viewerKind === 'preview' ? 'Preview: surfaces only' : 'Built package' }}</div>
      </section>
    </main>

    <aside class="diagnostics" v-if="mode === 'process'">
      <h2>Diagnostics</h2>
      <p v-if="!findings.length" class="muted">Findings appear here after the model is read.</p>
      <ul>
        <li v-for="(f, k) in findings" :key="k" :class="f.level">
          <div class="title">{{ f.title }}</div>
          <div class="detail">{{ f.detail }}</div>
        </li>
      </ul>
    </aside>

    <footer class="log" :class="{ open: logOpen }">
      <button class="log-toggle" @click="logOpen = !logOpen">
        {{ logOpen ? '▾' : '▸' }} Log <span class="muted" v-if="busy">· {{ busy }} running…</span>
        <span class="muted" v-else-if="lastLine">· {{ lastLine }}</span>
      </button>
      <pre v-if="logOpen" ref="logBox">{{ log.join('\n') }}</pre>
    </footer>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { api, runJob } from './lib/api.js';
import { STEPS, clone, diagnostics, setPath, stepStatus } from './lib/model.js';
import StepModel from './components/StepModel.vue';
import StepFields from './components/StepFields.vue';
import StepGeometry from './components/StepGeometry.vue';
import StepSections from './components/StepSections.vue';
import StepBuild from './components/StepBuild.vue';
import StepPublish from './components/StepPublish.vue';

const state = ref(null);
const cfg = ref(null);
const stepIndex = ref(0);
const mode = ref('process');
const busy = ref('');
const log = ref([]);
const logOpen = ref(false);
const logBox = ref(null);
const loadError = ref('');
const viewerKind = ref('');
const viewerStamp = ref(0);

const components = [StepModel, StepFields, StepGeometry, StepSections, StepBuild, StepPublish];
const stepComponent = computed(() => components[stepIndex.value]);
const status = computed(() => stepStatus(state.value));
const findings = computed(() => diagnostics(state.value));
const lastLine = computed(() => log.value.at(-1)?.split('\n')[0]?.slice(0, 120));
const viewerUrl = computed(() => {
  if (viewerKind.value === 'preview') return `/preview/index.html?v=${viewerStamp.value}`;
  if (state.value?.built) return `/site/index.html?v=${viewerStamp.value}`;
  return '';
});

async function refresh() {
  state.value = await api.project();
  cfg.value = clone(state.value.config);
}

let saveTimer = null;
function update(path, value) {
  if (!cfg.value) return; // nothing loaded yet: never save a partial configuration
  cfg.value = setPath(cfg.value, path, value);
  clearTimeout(saveTimer);
  saveTimer = setTimeout(save, 350);
}
async function replaceConfig(next) {
  cfg.value = clone(next);
  await save();
}
async function save() {
  clearTimeout(saveTimer);
  saveTimer = null;
  if (!cfg.value) return;
  const next = await api.saveConfig(cfg.value);
  state.value = { ...next, inspection: next.inspection ?? state.value?.inspection };
}

async function run(kind, params = {}) {
  if (busy.value) return null;
  if (saveTimer) await save();
  busy.value = kind;
  log.value.push(`— ${kind} —`);
  try {
    const view = await runJob(kind, params, (lines) => {
      log.value.push(...lines);
      if (logOpen.value) nextTick(() => { if (logBox.value) logBox.value.scrollTop = logBox.value.scrollHeight; });
    });
    if (kind === 'inspect') await refresh();
    else state.value = await api.project();
    if (kind === 'preview') { viewerKind.value = 'preview'; viewerStamp.value += 1; }
    if (kind === 'build') { viewerKind.value = 'site'; viewerStamp.value += 1; }
    return view.result;
  } catch (err) {
    log.value.push(`ERROR: ${err.message}`);
    logOpen.value = true;
    return null;
  } finally {
    busy.value = '';
  }
}

watch(logOpen, (open) => open && nextTick(() => { if (logBox.value) logBox.value.scrollTop = logBox.value.scrollHeight; }));

onMounted(async () => {
  try {
    await refresh();
    if (state.value.built) viewerKind.value = 'site';
    // a reopened project: read the model again so that the forms can offer its arrays
    if (state.value.config && !state.value.inspection) {
      const files = (state.value.config.input?.stages ?? []).map((s) => s.file);
      if (files.length) await run('inspect', { files, keep_settings: true });
    }
  } catch (err) {
    loadError.value = `Cannot reach the workbench server: ${err.message}`;
  }
});
</script>

<style>
:root {
  --bg: #f6f7f9; --panel: #fff; --line: #dde1e6; --text: #1d2329; --muted: #667080;
  --accent: #1f6feb; --accent-bg: #e8f0fe; --ok: #1a7f37; --ok-bg: #e6f4ea; --warn: #9a6700;
  --warn-bg: #fff4d6; --err: #b42318; --err-bg: #fdecea; --radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; font-size: 14px; color: var(--text);
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); }
button { font: inherit; padding: 6px 12px; border: 1px solid var(--line); border-radius: var(--radius); background: var(--panel); cursor: pointer; color: var(--text); }
button:hover:not(:disabled) { border-color: #b8bfc8; }
button:disabled { opacity: 0.5; cursor: default; }
button.primary { background: var(--accent); border-color: var(--accent); color: #fff; }
input, select, textarea { font: inherit; padding: 5px 8px; border: 1px solid var(--line); border-radius: var(--radius); background: #fff; color: var(--text); }
input[type=number] { width: 9em; }
code, pre { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 12.5px; }
.muted { color: var(--muted); }
.error { color: var(--err); }
h2 { font-size: 15px; font-weight: 600; margin: 0 0 10px; }
h3 { font-size: 14px; font-weight: 600; margin: 18px 0 8px; }

.app { display: grid; height: 100vh; grid-template-columns: 230px minmax(0, 1fr) 300px;
  grid-template-rows: 48px minmax(0, 1fr) auto; grid-template-areas: "top top top" "steps centre diag" "log log log"; }
.app.viewing { grid-template-columns: minmax(0, 1fr); grid-template-areas: "top" "centre" "log"; }
.top { grid-area: top; display: flex; align-items: center; gap: 16px; padding: 0 16px; background: var(--panel); border-bottom: 1px solid var(--line); }
.brand { font-weight: 700; }
.project { flex: 1; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.modes { display: flex; }
.modes button { border-radius: 0; }
.modes button:first-child { border-radius: var(--radius) 0 0 var(--radius); }
.modes button:last-child { border-radius: 0 var(--radius) var(--radius) 0; border-left: none; }
.modes button.on { background: var(--accent-bg); border-color: var(--accent); color: var(--accent); }

.steps { grid-area: steps; display: flex; flex-direction: column; gap: 4px; padding: 12px 10px; background: var(--panel); border-right: 1px solid var(--line); }
.step { display: flex; align-items: center; gap: 10px; text-align: left; border: none; background: transparent; padding: 8px 10px; }
.step.active { background: var(--accent-bg); color: var(--accent); }
.step .badge { width: 22px; height: 22px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 12px; background: #eef0f3; flex: none; }
.step.done .badge { background: var(--ok-bg); color: var(--ok); }
.step.attention .badge { background: var(--warn-bg); color: var(--warn); }
.saved { margin-top: auto; font-size: 12px; padding: 8px; }

.centre { grid-area: centre; display: grid; grid-template-rows: minmax(0, 1fr) minmax(0, 1fr); min-height: 0; }
.app.viewing .centre { grid-template-rows: minmax(0, 1fr); }
.form { overflow: auto; padding: 16px 20px; border-bottom: 1px solid var(--line); background: var(--panel); }
.nav-buttons { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
.viewer { position: relative; min-height: 0; background: #fff; }
.viewer iframe { width: 100%; height: 100%; border: 0; display: block; }
.viewer-label { position: absolute; top: 8px; right: 8px; font-size: 12px; padding: 2px 8px; border-radius: var(--radius); background: rgba(255,255,255,0.9); border: 1px solid var(--line); }
.placeholder { height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 24px; max-width: 460px; margin: 0 auto; }

.diagnostics { grid-area: diag; overflow: auto; padding: 14px; background: var(--panel); border-left: 1px solid var(--line); }
.diagnostics ul { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 8px; }
.diagnostics li { padding: 8px 10px; border-radius: var(--radius); background: #f1f3f5; }
.diagnostics li.ok { background: var(--ok-bg); }
.diagnostics li.warn { background: var(--warn-bg); }
.diagnostics li.error { background: var(--err-bg); }
.diagnostics .title { font-weight: 600; font-size: 13px; }
.diagnostics li.ok .title { color: var(--ok); }
.diagnostics li.warn .title { color: var(--warn); }
.diagnostics li.error .title { color: var(--err); }
.diagnostics .detail { font-size: 12.5px; margin-top: 2px; overflow-wrap: anywhere; }

.log { grid-area: log; background: var(--panel); border-top: 1px solid var(--line); }
.log-toggle { border: none; width: 100%; text-align: left; padding: 6px 16px; background: transparent; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.log pre { margin: 0; padding: 8px 16px; height: 180px; overflow: auto; background: #fafbfc; border-top: 1px solid var(--line); white-space: pre-wrap; }

/* shared form layout used by the step components */
.row { display: grid; grid-template-columns: 210px minmax(0, 1fr); gap: 12px; align-items: start; padding: 6px 0; }
.row > label { padding-top: 6px; color: #3a434d; }
.hint { font-size: 12px; color: var(--muted); margin-top: 3px; }
.notice { padding: 8px 10px; border-radius: var(--radius); margin: 8px 0; font-size: 13px; }
.notice.ok { background: var(--ok-bg); color: var(--ok); }
.notice.warn { background: var(--warn-bg); color: var(--warn); }
.notice.error { background: var(--err-bg); color: var(--err); }
.notice.info { background: #f1f3f5; }
table.data { border-collapse: collapse; width: 100%; font-size: 13px; }
table.data th, table.data td { text-align: left; padding: 4px 8px; border-bottom: 1px solid var(--line); }
table.data th { color: var(--muted); font-weight: 500; }
.inline { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
</style>
