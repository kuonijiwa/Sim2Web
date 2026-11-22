<template>
  <div>
    <h2>2 · Fields and units</h2>
    <p v-if="!state.inspection" class="notice info">Read the model first (step 1); the lists below are filled from the file.</p>

    <h3>Displacement</h3>
    <div class="row"><label>Array</label>
      <div><select :value="get('fields.displacement.name')" @change="set('fields.displacement.name', $event.target.value)">
        <option value="">none</option>
        <option v-for="a in c.displacement" :key="a.name" :value="a.name">{{ a.name }}</option>
      </select><div class="hint">Nodal vector with three components.</div></div></div>
    <div class="row"><label>Unit</label>
      <div><select :value="get('fields.displacement.unit')" @change="set('fields.displacement.unit', $event.target.value)">
        <option value="">not set</option>
        <option v-for="u in choices.length_units" :key="u" :value="u">{{ u }}</option>
      </select></div></div>

    <h3>Stress</h3>
    <div class="row"><label>Array</label>
      <div><select :value="get('fields.stress.name')" @change="set('fields.stress.name', $event.target.value)">
        <option value="">none</option>
        <option v-for="a in c.stress" :key="a.name" :value="a.name">{{ a.name }} ({{ a.association }} data)</option>
      </select><div class="hint">Symmetric tensor with six components, per cell or per node.</div></div></div>
    <div class="row"><label>Component order</label>
      <div><select :value="get('fields.stress.order')" @change="set('fields.stress.order', $event.target.value)">
        <option v-for="o in orders" :key="o.value" :value="o.value" :disabled="o.disabled">{{ o.label }}</option>
      </select>
      <div v-if="stressArray && !stressArray.component_names" class="notice warn">
        This file does not name its stress components. The order decides which values become the shear
        stresses and the principal stresses: take it from the solver's export documentation.</div>
      <div v-else-if="stressArray" class="hint">The order written in the file is used and checked at every build.</div>
      </div></div>
    <div class="row"><label>Unit</label>
      <div><select :value="get('fields.stress.unit')" @change="set('fields.stress.unit', $event.target.value)">
        <option value="">not set</option>
        <option v-for="u in choices.stress_units" :key="u" :value="u">{{ u }}</option>
      </select>
      <div v-if="advice" class="notice" :class="advice.level">
        <template v-if="advice.level === 'ok'">The vertical stress gradient fits {{ get('fields.stress.unit') }}
          (unit weight {{ advice.weights[get('fields.stress.unit')].toFixed(1) }} kN/m³).</template>
        <template v-else-if="advice.level === 'warn'">With {{ get('fields.stress.unit') }} the vertical gradient implies
          {{ fmtW(advice.weights[get('fields.stress.unit')]) }} kN/m³. It fits {{ advice.consistent.join(' or ') }}.
          <button v-if="advice.suggested" @click="set('fields.stress.unit', advice.suggested)">Use {{ advice.suggested }}</button></template>
        <template v-else>Implied unit weights: {{ Object.entries(advice.weights).map(([u, w]) => `${u} ${fmtW(w)}`).join(', ') }} kN/m³.</template>
      </div></div></div>
    <div class="row"><label>Sign convention</label>
      <div><select :value="get('fields.stress.sign_convention')" @change="set('fields.stress.sign_convention', $event.target.value)">
        <option value="tension positive">tension positive (Itasca, Abaqus, most FE codes)</option>
        <option value="compression positive">compression positive (soil mechanics convention)</option>
        <option value="">not stated</option>
      </select><div class="hint">Recorded in the package; values are not changed.</div></div></div>

    <h3>Categories</h3>
    <p class="hint">Integer or text cell arrays such as zone groups, materials or element blocks.</p>
    <table class="data" v-if="c.categories.length">
      <thead><tr><th>Use</th><th>Array</th><th>Label in the viewer</th><th>Values</th></tr></thead>
      <tbody>
        <tr v-for="a in c.categories" :key="a.name">
          <td><input type="checkbox" :checked="!!category(a.name)" @change="toggleCategory(a.name, $event.target.checked)" /></td>
          <td><code>{{ a.name }}</code></td>
          <td><input :disabled="!category(a.name)" :value="category(a.name)?.label ?? a.name" @change="labelCategory(a.name, $event.target.value)" /></td>
          <td class="muted">{{ a.unique_values }}: {{ a.examples.slice(0, 4).join(', ') }}{{ a.unique_values > 4 ? ', …' : '' }}</td>
        </tr>
      </tbody>
    </table>
    <p v-else class="muted">No category arrays found.</p>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { candidates, getPath, orderOptions, unitAdvice } from '../lib/model.js';

const props = defineProps({ state: Object, cfg: Object, busy: String, run: Function });
const emit = defineEmits(['update', 'set-config']);
const get = (p) => getPath(props.cfg, p, '');
const set = (p, v) => emit('update', p, v);
const choices = computed(() => props.state.choices ?? {});
const c = computed(() => candidates(props.state.inspection));
const stressArray = computed(() => c.value.stress.find((a) => a.name === get('fields.stress.name')));
const orders = computed(() => orderOptions(stressArray.value, choices.value.stress_orders));
const advice = computed(() => (stressArray.value ? unitAdvice(props.state.inspection, get('fields.stress.unit'), get('fields.stress.name')) : null));
const fmtW = (w) => (Number.isFinite(w) ? w.toPrecision(3) : '?');

const categories = () => getPath(props.cfg, 'fields.categories', []) ?? [];
const category = (name) => categories().find((x) => x.name === name);
function toggleCategory(name, on) {
  const list = categories().filter((x) => x.name !== name);
  if (on) list.push({ name, label: name });
  set('fields.categories', list);
  if (!on && get('geometry.groups.field') === name) set('geometry.groups.field', '');
}
function labelCategory(name, label) {
  set('fields.categories', categories().map((x) => (x.name === name ? { ...x, label } : x)));
}
</script>
