<template>
  <div>
    <h2>1 · Open model</h2>
    <p class="muted">Choose the result files of one model. Each file is a stage (for example one excavation step).</p>

    <table class="data" v-if="files.length">
      <thead><tr><th>Stage</th><th>File</th><th></th></tr></thead>
      <tbody>
        <tr v-for="(f, i) in files" :key="f.file">
          <td><input v-model="f.name" size="14" /></td>
          <td><code>{{ f.file }}</code>
            <div v-if="needsConversion(f.file)" class="inline hint">
              Not a VTU file.
              <select v-model="f.time" aria-label="Time step">
                <option value="last">last time step</option><option value="first">first time step</option>
              </select>
              <button :disabled="!!busy" @click="convert(i)">Convert</button>
            </div>
          </td>
          <td class="inline">
            <button :disabled="i === 0" @click="move(i, -1)" aria-label="Move up">↑</button>
            <button :disabled="i === files.length - 1" @click="move(i, 1)" aria-label="Move down">↓</button>
            <button @click="files.splice(i, 1)" aria-label="Remove">✕</button>
          </td>
        </tr>
      </tbody>
    </table>

    <div class="inline" style="margin-top: 10px">
      <button @click="dialog = true">Add model files…</button>
      <button class="primary" :disabled="!files.length || !!busy || files.some((f) => needsConversion(f.file))" @click="inspect">
        {{ state.config ? 'Read model again' : 'Read model and draft settings' }}
      </button>
      <label v-if="state.config" class="inline muted"><input type="checkbox" v-model="keep" /> keep current settings</label>
    </div>

    <template v-if="info">
      <h3>Model summary</h3>
      <div class="row"><label>Size</label><div>{{ fmt(info.cells) }} cells, {{ fmt(info.points) }} points</div></div>
      <div class="row"><label>Cell types</label><div>{{ Object.entries(info.cell_types).map(([k, v]) => `${k} ${fmt(v)}`).join(', ') }}</div></div>
      <div class="row"><label>Extent</label><div>{{ extent }}</div></div>
      <h3>Arrays in the file</h3>
      <table class="data">
        <thead><tr><th>Name</th><th>On</th><th>Components</th><th>Range / values</th></tr></thead>
        <tbody>
          <tr v-for="a in arrays" :key="a.assoc + a.name">
            <td><code>{{ a.name }}</code></td><td>{{ a.assoc }}</td>
            <td>{{ a.components }}<span class="muted" v-if="a.component_names"> ({{ a.component_names.join(', ') }})</span></td>
            <td class="muted">{{ a.range }}</td>
          </tr>
        </tbody>
      </table>
    </template>

    <FileDialog v-if="dialog" :start="state.dir" @close="dialog = false" @choose="add" />
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import FileDialog from './FileDialog.vue';
import { stageFor } from '../lib/model.js';

const props = defineProps({ state: Object, cfg: Object, busy: String, run: Function });
defineEmits(['update', 'set-config']);
const dialog = ref(false);
const keep = ref(true);
const CONVERT = /\.(e|exo|ex2|med|xdmf|xmf|msh|inp|vtk)$/i;
const needsConversion = (f) => CONVERT.test(f);

const files = ref([]);
watch(() => props.state.config?.input?.stages, (stages) => {
  files.value = (stages ?? []).map((s) => ({ file: s.file, name: s.name, time: 'last' }));
}, { immediate: true });

function add(paths) {
  dialog.value = false;
  for (const p of paths) {
    if (!files.value.some((f) => f.file === p)) files.value.push({ ...stageFor(p, files.value), time: 'last' });
  }
}
function move(i, d) {
  const [f] = files.value.splice(i, 1);
  files.value.splice(i + d, 0, f);
}
async function convert(i) {
  const f = files.value[i];
  const result = await props.run('convert', { file: f.file, time: f.time });
  if (result?.file) files.value[i] = { ...f, file: result.file };
}
function inspect() {
  return props.run('inspect', { files: files.value.map((f) => f.file), names: files.value.map((f) => f.name),
    keep_settings: keep.value && !!props.state.config });
}

const info = computed(() => props.state.inspection);
const fmt = (n) => Number(n).toLocaleString('en-US');
const extent = computed(() => {
  const b = info.value?.bounds;
  if (!b) return '';
  const span = [b[1] - b[0], b[3] - b[2], b[5] - b[4]].map((v) => v.toFixed(1));
  return `x ${b[0].toFixed(1)} … ${b[1].toFixed(1)}, y ${b[2].toFixed(1)} … ${b[3].toFixed(1)}, z ${b[4].toFixed(1)} … ${b[5].toFixed(1)} (${span.join(' × ')})`;
});
const arrays = computed(() => {
  const out = [];
  for (const [assoc, key] of [['point', 'point_arrays'], ['cell', 'cell_arrays']]) {
    for (const [name, e] of Object.entries(info.value?.[key] ?? {})) {
      const range = 'min' in e ? `${Number(e.min).toPrecision(4)} … ${Number(e.max).toPrecision(4)}`
        : e.examples ? `${e.unique_values} values: ${e.examples.slice(0, 4).join(', ')}${e.unique_values > 4 ? ', …' : ''}` : '';
      out.push({ name, assoc, components: e.components, component_names: e.component_names, range });
    }
  }
  return out;
});
</script>
