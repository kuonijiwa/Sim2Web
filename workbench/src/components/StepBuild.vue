<template>
  <div>
    <h2>5 · Build and validate</h2>
    <p class="muted">Build writes the complete package (surfaces, sections and the viewer) to
      <code>{{ outDir }}</code>. Validation recomputes every published value from the source model independently.</p>

    <div class="inline">
      <button class="primary" :disabled="!!busy || !!state.errors.length" @click="run('build')">Build package</button>
      <button :disabled="!!busy || !state.built" @click="run('validate', { sections: sample })">Validate</button>
      <label class="inline muted">sections checked
        <select v-model="sample">
          <option value="all">all</option><option :value="5">every 5th</option><option :value="20">every 20th</option>
        </select></label>
    </div>
    <p v-if="state.errors.length" class="notice error">{{ state.errors[0] }}</p>

    <template v-if="report">
      <h3>Package</h3>
      <table class="data">
        <thead><tr><th>Stage</th><th>Main surface</th><th>Sections</th><th>Stage size</th><th>Time</th></tr></thead>
        <tbody>
          <tr v-for="s in report.stages" :key="s.stage">
            <td>{{ s.stage }}</td><td>{{ mb(s.primary_bytes) }}</td><td>{{ s.section_count }}</td>
            <td>{{ mb(s.output_bytes) }}</td><td>{{ sec(sum(s.seconds)) }}</td>
          </tr>
        </tbody>
      </table>
      <p class="hint">Built with Sim2Web {{ report.sim2web }} in {{ sec(report.seconds_total) }} on {{ report.platform }}.</p>
    </template>

    <template v-if="state.validation">
      <h3>Validation</h3>
      <p class="notice" :class="state.validation.passed ? 'ok' : 'error'">
        {{ state.validation.passed ? 'Passed: every checked value matches the source model.'
          : `${state.validation.failures.length} failure(s)` }}</p>
      <ul v-if="!state.validation.passed" class="error">
        <li v-for="f in state.validation.failures.slice(0, 20)" :key="f">{{ f }}</li>
      </ul>
      <table class="data" v-if="rows.length">
        <thead><tr><th>Stage</th><th>Check</th><th>Value</th></tr></thead>
        <tbody><tr v-for="r in rows" :key="r.stage + r.key"><td>{{ r.stage }}</td><td>{{ r.key }}</td><td>{{ r.value }}</td></tr></tbody>
      </table>
    </template>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import { getPath } from '../lib/model.js';

const props = defineProps({ state: Object, cfg: Object, busy: String, run: Function });
defineEmits(['update', 'set-config']);
const sample = ref('all');
const report = computed(() => props.state.build_report);
const outDir = computed(() => getPath(props.cfg, 'output.dir', 'site') || 'site');
const mb = (b) => (b == null ? '–' : b > 1e6 ? `${(b / 1e6).toFixed(2)} MB` : `${Math.ceil(b / 1e3)} kB`);
const sec = (s) => (s > 90 ? `${(s / 60).toFixed(1)} min` : `${s.toFixed(1)} s`);
const sum = (o) => Object.values(o ?? {}).reduce((a, b) => a + (Number(b) || 0), 0);
const rows = computed(() => {
  const out = [];
  for (const [stage, v] of Object.entries(props.state.validation?.stages ?? {})) {
    for (const [key, value] of Object.entries(v)) {
      if (typeof value === 'number' || typeof value === 'boolean') {
        out.push({ stage, key: key.replaceAll('_', ' '), value: typeof value === 'number' ? Number(value.toPrecision(4)) : String(value) });
      }
    }
  }
  return out;
});
</script>
