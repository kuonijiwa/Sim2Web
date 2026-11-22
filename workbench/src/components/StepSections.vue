<template>
  <div>
    <h2>4 · Sections</h2>
    <div class="row"><label>Sections</label>
      <label class="inline"><input type="checkbox" :checked="get('sections.enabled') !== false"
             @change="set('sections.enabled', $event.target.checked)" /> pre-compute plane sections through the model</label></div>
    <template v-if="get('sections.enabled') !== false">
      <div class="row"><label>Normal directions</label>
        <div class="inline">
          <label v-for="a in ['x', 'y', 'z']" :key="a"><input type="checkbox" :checked="axes.includes(a)" @change="toggleAxis(a, $event.target.checked)" /> {{ a }}</label>
        </div></div>
      <div class="row"><label>Positions</label>
        <div><select :value="get('sections.placement')" @change="set('sections.placement', $event.target.value)">
          <option value="integer_grid">regular spacing from a whole number</option>
          <option value="interior">regular spacing inside the model</option>
          <option value="explicit">only the positions listed below</option>
        </select></div></div>
      <div class="row" v-if="get('sections.placement') !== 'explicit'"><label>Spacing</label>
        <div><input type="number" step="any" min="0" :value="get('sections.spacing')" @change="set('sections.spacing', Number($event.target.value))" />
          <span class="muted"> {{ get('viewer.length_unit') || 'm' }}</span>
          <div class="hint" v-if="estimate">About {{ estimate }} sections per stage.</div></div></div>
      <div class="row" v-for="a in axes" :key="'p' + a"><label>{{ get('sections.placement') === 'explicit' ? 'Positions' : 'Extra positions' }} ({{ a }})</label>
        <div><input :value="(get(`sections.positions.${a}`) || []).join(', ')" placeholder="12.5, 40"
                    @change="setPositions(a, $event.target.value)" /></div></div>
      <div class="row"><label>Discontinuities</label>
        <div><label class="inline"><input type="checkbox" :checked="!!get('sections.preserve_discontinuities')"
                    @change="set('sections.preserve_discontinuities', $event.target.checked)" /> keep jumps across block joints</label>
          <div class="hint">For block (DEM) models: displacement on two sides of a joint is not averaged on sections.</div></div></div>
      <div class="row"><label>Displacement magnitude</label>
        <div><select :value="get('sections.magnitude') || 'vector_norm'" @change="set('sections.magnitude', $event.target.value)">
          <option value="vector_norm">norm of the interpolated vector (recommended)</option>
          <option value="interpolated">interpolated nodal magnitude (v0.1)</option>
        </select></div></div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { getPath } from '../lib/model.js';

const props = defineProps({ state: Object, cfg: Object, busy: String, run: Function });
const emit = defineEmits(['update', 'set-config']);
const get = (p) => getPath(props.cfg, p, '');
const set = (p, v) => emit('update', p, v);
const axes = computed(() => getPath(props.cfg, 'sections.axes', ['x', 'y', 'z']) ?? []);

function toggleAxis(a, on) {
  const next = ['x', 'y', 'z'].filter((x) => (x === a ? on : axes.value.includes(x)));
  set('sections.axes', next);
}
function setPositions(a, text) {
  const values = text.split(',').map((s) => s.trim()).filter((s) => s !== '').map(Number).filter(Number.isFinite);
  const positions = { ...(getPath(props.cfg, 'sections.positions', {}) ?? {}) };
  if (values.length) positions[a] = values; else delete positions[a];
  set('sections.positions', positions);
}
const estimate = computed(() => {
  const b = props.state.inspection?.bounds;
  const s = Number(get('sections.spacing'));
  if (!b || !(s > 0)) return '';
  const span = { x: b[1] - b[0], y: b[3] - b[2], z: b[5] - b[4] };
  return axes.value.reduce((n, a) => n + Math.max(0, Math.floor(span[a] / s)), 0).toLocaleString('en-US');
});
</script>
