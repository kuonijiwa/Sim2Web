<template>
  <div>
    <h2>6 · Publish and export</h2>

    <h3>Viewer</h3>
    <div class="row"><label>Title</label><input :value="get('title')" @change="set('title', $event.target.value)" /></div>
    <div class="row"><label>Subtitle</label><input :value="get('viewer.subtitle')" @change="set('viewer.subtitle', $event.target.value)" /></div>
    <div class="row"><label>Solver</label><input :value="get('solver')" placeholder="FLAC3D 9.0" @change="set('solver', $event.target.value)" /></div>
    <div class="row"><label>Description</label><textarea rows="2" :value="get('description')" @change="set('description', $event.target.value)"></textarea></div>
    <div class="row"><label>Colour map</label>
      <div class="inline"><select :value="get('viewer.colormap') || 'jet'" @change="set('viewer.colormap', $event.target.value)">
        <option v-for="m in state.choices?.colormaps ?? []" :key="m" :value="m">{{ m }}</option></select>
        <label class="inline muted">bands <input type="number" min="1" max="64" :value="get('viewer.bands') || 8"
               @change="set('viewer.bands', Number($event.target.value))" /></label></div></div>
    <div class="row"><label>Colour range</label>
      <select :value="get('viewer.range_mode') || 'full'" @change="set('viewer.range_mode', $event.target.value)">
        <option value="full">full range</option><option value="p5_p95">5th to 95th percentile</option></select></div>
    <div class="row"><label>Length unit</label>
      <select :value="get('viewer.length_unit') || 'm'" @change="set('viewer.length_unit', $event.target.value)">
        <option v-for="u in state.choices?.length_units ?? []" :key="u" :value="u">{{ u }}</option></select></div>
    <p class="hint">Viewer settings take effect at the next build.</p>

    <h3>Export</h3>
    <div class="inline">
      <a v-if="state.built" class="button primary" href="/api/export" download>Download package (ZIP)</a>
      <span v-else class="muted">Build the package first (step 5).</span>
      <span class="muted" v-if="state.built && !state.validation?.passed">Not validated yet.</span>
    </div>
    <p class="hint">The ZIP holds the static package (<code>site/</code>) and <code>case.yaml</code>. Any static web
      server can host <code>site/</code>; it needs no Python and no Sim2Web installation.</p>

    <h3>Reproduce without the workbench</h3>
    <pre class="box">{{ state.commands.join('\n') }}</pre>
    <h3>Configuration (<code>case.yaml</code>)</h3>
    <pre class="box">{{ state.yaml }}</pre>
  </div>
</template>

<script setup>
import { getPath } from '../lib/model.js';

const props = defineProps({ state: Object, cfg: Object, busy: String, run: Function });
const emit = defineEmits(['update', 'set-config']);
const get = (p) => getPath(props.cfg, p, '');
const set = (p, v) => emit('update', p, v);
</script>

<style scoped>
.box { background: #f6f8fa; border: 1px solid var(--line); border-radius: var(--radius); padding: 10px; max-height: 260px; overflow: auto; }
a.button { text-decoration: none; padding: 6px 12px; border-radius: var(--radius); }
a.button.primary { background: var(--accent); color: #fff; }
textarea { width: 100%; }
</style>
