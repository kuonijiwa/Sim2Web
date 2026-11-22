<template>
  <div class="legend" v-if="legend.length">
    <div class="legend-title">{{ title }}</div>
    <div class="legend-sub" v-if="subtitle">{{ subtitle }}</div>
    <ul v-if="kind === 'categorical'" class="cats">
      <li v-for="item in legend" :key="item.code">
        <span class="swatch" :style="{ background: css(item.color) }"></span>
        <span>{{ item.label }}</span>
      </li>
    </ul>
    <div v-else class="bands">
      <div class="band-row" v-for="(item, i) in reversed" :key="i">
        <span class="swatch tall" :style="{ background: css(item.color) }"></span>
        <span class="tick">{{ fmt(item.to) }}</span>
      </div>
      <div class="band-row last"><span class="swatch spacer"></span><span class="tick">{{ fmt(legend[0].from) }}</span></div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { cssColor, formatValue } from '../lib/colormaps.js';

const props = defineProps({ legend: Array, kind: String, title: String, subtitle: String });
const reversed = computed(() => [...props.legend].reverse());
const span = computed(() => (props.legend.length ? props.legend[props.legend.length - 1].to - props.legend[0].from : 1));
const css = cssColor;
const fmt = (v) => formatValue(v, span.value);
</script>

<style scoped>
.legend { background: rgba(255,255,255,.95); border: 1px solid #dfe3ea; border-radius: 10px; padding: 10px 12px; min-width: 150px; box-shadow: 0 6px 20px rgba(0,0,0,.08); }
.legend-title { font-weight: 700; font-size: 12px; color: #1f2d3d; margin-bottom: 2px; }
.legend-sub { font-size: 10.5px; color: #6b7785; margin-bottom: 8px; }
.cats { list-style: none; margin: 0; padding: 0; font-size: 12px; }
.cats li { display: flex; align-items: center; gap: 8px; margin: 3px 0; }
.swatch { display: inline-block; width: 14px; height: 14px; border-radius: 2px; border: 1px solid rgba(0,0,0,.15); }
.bands { display: flex; flex-direction: column; font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 11px; }
.band-row { display: flex; align-items: flex-start; gap: 8px; height: 22px; }
.band-row .tick { transform: translateY(-7px); color: #34495e; }
.band-row.last { height: 0; }
.swatch.tall { height: 22px; border-radius: 0; border-top: none; }
.swatch.spacer { border: none; height: 0; }
</style>
