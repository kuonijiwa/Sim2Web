<template>
  <div>
    <h2>3 · Geometry and excavation</h2>

    <div class="row"><label>Main object in the viewer</label>
      <div class="inline">
        <label><input type="radio" value="exterior" :checked="get('geometry.primary') !== 'excavation'"
                      @change="setPrimary('exterior')" /> Exterior surface (slopes, pits, foundations)</label>
        <label><input type="radio" value="excavation" :checked="get('geometry.primary') === 'excavation'"
                      @change="setPrimary('excavation')" /> Excavation surface (caverns, tunnels)</label>
      </div></div>

    <h3>Exterior surface</h3>
    <div class="row"><label>Internal faces</label>
      <div><select :value="get('geometry.exterior.internal_faces') || 'auto'" @change="set('geometry.exterior.internal_faces', $event.target.value)">
        <option v-for="o in INTERNAL_FACES" :key="o.value" :value="o.value">{{ o.label }}</option>
      </select>
      <div class="hint">Block models (3DEC) and zones generated without merged gridpoints expose faces that have
        rock on both sides. Removing them keeps the surface small without changing what is visible.</div></div></div>
    <div class="row"><label>Group boundaries</label>
      <label class="inline"><input type="checkbox" :checked="get('geometry.exterior.split_by_group') !== false"
             @change="set('geometry.exterior.split_by_group', $event.target.checked)" /> keep the boundaries between groups visible</label></div>
    <div class="row"><label>Group array</label>
      <div><select :value="get('geometry.groups.field')" @change="set('geometry.groups.field', $event.target.value)">
        <option value="">none</option>
        <option v-for="cat in declared" :key="cat.name" :value="cat.name">{{ cat.label || cat.name }}</option>
      </select><div class="hint">Smoothed display values are not averaged across groups. Only declared categories (step 2) can be used.</div></div></div>

    <h3>Excavation</h3>
    <div class="row"><label>Excavated region</label>
      <label class="inline"><input type="checkbox" :checked="!!get('geometry.excavation.enabled')"
             @change="setExcavation($event.target.checked)" /> the model contains excavated zones</label></div>
    <template v-if="get('geometry.excavation.enabled')">
      <div class="row"><label>How they are recognised</label>
        <div><select :value="get('geometry.excavation.strategy')" @change="set('geometry.excavation.strategy', $event.target.value)">
          <option v-for="o in EXCAVATION_STRATEGIES" :key="o.value" :value="o.value">{{ o.label }}</option>
        </select></div></div>
      <div class="row" v-if="usesLabels"><label>Label tokens</label>
        <div><input :value="(get('geometry.excavation.label_tokens') || []).join(', ')"
                    @change="set('geometry.excavation.label_tokens', list($event.target.value))" />
          <div class="hint">A cell is excavated when a category label contains one of these words.</div></div></div>
      <div class="row" v-if="usesStress"><label>Zero-stress threshold</label>
        <div><input type="number" step="any" :value="get('geometry.excavation.null_threshold')"
                    @change="set('geometry.excavation.null_threshold', Number($event.target.value))" />
          <span class="muted"> {{ get('fields.stress.unit') }}</span>
          <div class="hint">Null zones carry exactly zero stress; the build reports how well the two populations separate.</div></div></div>
      <div class="row" v-if="get('geometry.excavation.strategy') === 'field'"><label>Excavation array</label>
        <div><select :value="get('geometry.excavation.void_field')" @change="set('geometry.excavation.void_field', $event.target.value)">
          <option value="">choose</option>
          <option v-for="a in c.categories" :key="a.name" :value="a.name">{{ a.name }}</option>
        </select></div></div>
      <div class="row"><label>Contact tolerance</label>
        <div><input type="number" step="any" :value="get('geometry.excavation.contact_tolerance')"
                    @change="set('geometry.excavation.contact_tolerance', Number($event.target.value))" />
          <span class="muted"> {{ get('viewer.length_unit') || 'm' }}</span>
          <div class="hint" v-if="get('geometry.excavation.strategy') === 'removed_zones'">Faces within this distance of the model's outer planes are treated as outer boundary.</div>
          <div class="hint" v-else>Solid faces within this distance of excavated cells form the excavation surface.</div></div></div>
    </template>

    <div class="inline" style="margin-top: 14px">
      <button class="primary" :disabled="!!busy || !!state.errors.length" @click="run('preview')">Preview surfaces</button>
      <span class="muted">Builds the surfaces only (no sections) and shows them below.</span>
    </div>
    <p v-if="state.errors.length" class="notice error">{{ state.errors[0] }}</p>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { EXCAVATION_STRATEGIES, INTERNAL_FACES, candidates, getPath } from '../lib/model.js';

const props = defineProps({ state: Object, cfg: Object, busy: String, run: Function });
const emit = defineEmits(['update', 'set-config']);
const get = (p) => getPath(props.cfg, p, '');
const set = (p, v) => emit('update', p, v);
const c = computed(() => candidates(props.state.inspection));
const declared = computed(() => getPath(props.cfg, 'fields.categories', []) ?? []);
const strategy = computed(() => get('geometry.excavation.strategy'));
const usesLabels = computed(() => ['labels', 'labels_then_stress'].includes(strategy.value));
const usesStress = computed(() => ['stress', 'labels_then_stress'].includes(strategy.value));
const list = (text) => text.split(',').map((s) => s.trim()).filter(Boolean);

function setPrimary(value) {
  set('geometry.primary', value);
  if (value === 'excavation') set('geometry.excavation.enabled', true);
}
function setExcavation(on) {
  set('geometry.excavation.enabled', on);
  if (!on && get('geometry.primary') === 'excavation') set('geometry.primary', 'exterior');
}
</script>
