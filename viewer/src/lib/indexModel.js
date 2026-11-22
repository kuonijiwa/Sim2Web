// Reading and interpreting sim2web-index/2 documents.  Pure functions.

export const SUPPORTED_SCHEMA = 'sim2web-index/2';
// Packages built before the rename (SimWebView 0.2.0.dev0) carry the old name.
export const LEGACY_SCHEMAS = ['simwebview-index/2'];

export function checkIndex(index) {
  if (!index || (index.schema !== SUPPORTED_SCHEMA && !LEGACY_SCHEMAS.includes(index.schema))) {
    throw new Error(`Unsupported index schema "${index?.schema}"; this viewer reads ${SUPPORTED_SCHEMA}. `
      + 'Rebuild the package with sim2web >= 0.2.');
  }
  if (!Array.isArray(index.stages) || !index.stages.length) throw new Error('The index lists no stages.');
  return index;
}

// Quantitative and categorical fields available in a stage, in index order.
export function stageFields(index, stage) {
  return Object.keys(index.fields).filter((name) => stage.fields[name]);
}

export function fieldGroup(meta) {
  if (meta.kind === 'categorical') return 'Categories';
  if (/^(TotalDisplacement|[XYZ]_Disp)$/.test(meta.name ?? '')) return 'Displacement';
  if ((meta.source ?? '') && meta.component_order) return 'Stress';
  return 'Other';
}

export function groupedFields(index, stage) {
  const groups = new Map();
  for (const name of stageFields(index, stage)) {
    const meta = { ...index.fields[name], name };
    const g = fieldGroup(meta);
    if (!groups.has(g)) groups.set(g, []);
    groups.get(g).push(meta);
  }
  return [...groups.entries()].map(([label, fields]) => ({ label, fields }));
}

// Display range for a continuous field.
//   mode:  'full' | 'p5_p95' | 'custom'
//   scope: 'stage' | 'all'   (all stages share one scale)
export function displayRange(index, stageIndex, name, mode, scope, custom) {
  if (mode === 'custom' && custom && Number.isFinite(custom[0]) && Number.isFinite(custom[1]) && custom[1] > custom[0]) {
    return { min: custom[0], max: custom[1], label: 'custom' };
  }
  const stages = scope === 'all' ? index.stages : [index.stages[stageIndex]];
  const entries = stages.map((s) => s.fields[name]).filter(Boolean);
  if (!entries.length) return { min: 0, max: 1, label: 'n/a' };
  if (mode === 'p5_p95' && entries.every((e) => Number.isFinite(e.p5))) {
    return { min: Math.min(...entries.map((e) => e.p5)), max: Math.max(...entries.map((e) => e.p95)),
      label: scope === 'all' && entries.length > 1 ? 'P5–P95 (envelope of stages)' : 'P5–P95' };
  }
  return { min: Math.min(...entries.map((e) => e.min)), max: Math.max(...entries.map((e) => e.max)), label: 'full range' };
}

export function sectionAxes(stage) {
  return ['x', 'y', 'z'].filter((a) => (stage.sections?.[a] ?? []).length);
}

export function nearestSectionIndex(entries, value) {
  let best = 0;
  let dist = Infinity;
  entries.forEach((e, i) => {
    const d = Math.abs(e.value - value);
    if (d < dist) { dist = d; best = i; }
  });
  return best;
}

export function unitSuffix(meta) {
  return meta?.unit ? ` (${meta.unit})` : '';
}
