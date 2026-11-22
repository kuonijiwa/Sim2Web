<template>
  <div class="overlay" @click.self="$emit('close')">
    <div class="dialog" role="dialog" aria-label="Choose model files">
      <div class="head">
        <h2>Choose model files</h2>
        <button @click="$emit('close')" aria-label="Close">✕</button>
      </div>
      <div class="inline path">
        <button :disabled="!listing?.parent" @click="open(listing.parent)">Up</button>
        <select v-if="listing?.drives?.length" @change="open($event.target.value)">
          <option value="">Drive</option>
          <option v-for="d in listing.drives" :key="d" :value="d">{{ d }}</option>
        </select>
        <input v-model="typed" @keydown.enter="open(typed)" />
        <button @click="open(typed)">Go</button>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
      <ul class="entries">
        <li v-for="e in listing?.entries ?? []" :key="e.path" :class="{ dir: e.dir, picked: picked.has(e.path) }"
            @click="e.dir ? open(e.path) : toggle(e.path)">
          <span class="icon">{{ e.dir ? '▸' : (picked.has(e.path) ? '☑' : '☐') }}</span>
          <span class="name">{{ e.name }}</span>
          <span class="muted" v-if="!e.dir">{{ size(e.bytes) }}{{ e.convert ? ' · convert' : '' }}</span>
        </li>
        <li v-if="listing && !listing.entries.length" class="muted">No folders or model files here.</li>
      </ul>
      <p class="hint">Several files of one model become its stages, in the order chosen.
        VTU files are read directly; Exodus, MED, XDMF and Gmsh files are converted first.</p>
      <div class="inline foot">
        <span class="muted">{{ picked.size }} selected</span>
        <button class="primary" :disabled="!picked.size" @click="$emit('choose', [...picked])">Add</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import { api } from '../lib/api.js';

const props = defineProps({ start: String });
defineEmits(['close', 'choose']);
const listing = ref(null);
const typed = ref('');
const error = ref('');
const picked = ref(new Set());

async function open(path) {
  error.value = '';
  try {
    listing.value = await api.browse(path);
    typed.value = listing.value.path;
  } catch (err) {
    error.value = err.message;
  }
}
function toggle(path) {
  const next = new Set(picked.value);
  if (next.has(path)) next.delete(path); else next.add(path);
  picked.value = next;
}
const size = (b) => (b > 1e9 ? `${(b / 1e9).toFixed(1)} GB` : b > 1e6 ? `${(b / 1e6).toFixed(1)} MB` : `${Math.ceil(b / 1e3)} kB`);
onMounted(() => open(props.start));
</script>

<style scoped>
.overlay { position: fixed; inset: 0; background: rgba(20, 24, 31, 0.35); display: flex; align-items: center; justify-content: center; z-index: 10; }
.dialog { background: #fff; border-radius: 8px; width: min(720px, 92vw); max-height: 82vh; display: flex; flex-direction: column; padding: 16px; gap: 8px; }
.head { display: flex; justify-content: space-between; align-items: center; }
.path input { flex: 1; min-width: 200px; }
.entries { list-style: none; margin: 0; padding: 0; overflow: auto; border: 1px solid var(--line); border-radius: var(--radius); min-height: 220px; }
.entries li { display: flex; gap: 10px; padding: 6px 10px; cursor: pointer; border-bottom: 1px solid #f0f2f4; }
.entries li:hover { background: #f6f8fa; }
.entries li.picked { background: var(--accent-bg); }
.entries .name { flex: 1; overflow-wrap: anywhere; }
.entries .icon { width: 1.2em; color: var(--muted); }
.foot { justify-content: flex-end; }
</style>
