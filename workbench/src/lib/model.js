// Pure helpers of the workbench: reading and editing the case configuration,
// candidate arrays from the inspection, step status and diagnostics.
// No DOM, no network: tested with `node --test workbench/tests`.

export const STEPS = [
  { id: 'model', label: 'Open model' },
  { id: 'fields', label: 'Fields and units' },
  { id: 'geometry', label: 'Geometry and excavation' },
  { id: 'sections', label: 'Sections' },
  { id: 'build', label: 'Build and validate' },
  { id: 'publish', label: 'Publish and export' },
];

export function getPath(obj, path, fallback = undefined) {
  let node = obj;
  for (const key of path.split('.')) {
    if (node == null || typeof node !== 'object' || !(key in node)) return fallback;
    node = node[key];
  }
  return node === undefined ? fallback : node;
}

// Deep copy of plain JSON data.  Works on Vue reactive proxies, which
// structuredClone refuses.
export function clone(value) {
  return value == null ? value : JSON.parse(JSON.stringify(value));
}

// Returns a new object; the input is not modified.
export function setPath(obj, path, value) {
  const out = clone(obj ?? {});
  const keys = path.split('.');
  let node = out;
  for (const key of keys.slice(0, -1)) {
    if (node[key] == null || typeof node[key] !== 'object') node[key] = {};
    node = node[key];
  }
  node[keys.at(-1)] = value;
  return out;
}

// Arrays of the inspected file that can serve each role.
export function candidates(inspection) {
  if (!inspection) return { displacement: [], stress: [], categories: [] };
  const list = [];
  for (const [assoc, key] of [['point', 'point_arrays'], ['cell', 'cell_arrays']]) {
    for (const [name, e] of Object.entries(inspection[key] ?? {})) list.push({ name, association: assoc, ...e });
  }
  const strain = (n) => /^(eps|strain)/i.test(n);
  return {
    displacement: list.filter((a) => a.association === 'point' && a.components === 3),
    stress: list.filter((a) => a.components === 6 && !strain(a.name)),
    categories: list.filter((a) => a.association === 'cell' && a.components === 1 && 'unique_values' in a),
  };
}

// The component order offered for a stress array: from the file when named.
export function orderOptions(stressArray, stressOrders) {
  const options = [];
  if (stressArray?.component_names?.length === 6) {
    options.push({ value: 'from_file', label: `Read from file (${stressArray.component_names.join(', ')})` });
  } else {
    options.push({ value: 'from_file', label: 'Choose the order (the file does not name its components)', disabled: true });
  }
  for (const [order, note] of Object.entries(stressOrders ?? {})) options.push({ value: order, label: `${order} — ${note}` });
  return options;
}

// Unit check of the inspection, summarised for the forms.
export function unitAdvice(inspection, declared, arrayName = null) {
  const check = inspection?.stress_unit_check;
  if (!check || !check.consistent_units) return null;
  if (arrayName && check.array && check.array !== arrayName) return null; // checked another array
  const units = check.consistent_units;
  const weights = {};
  for (const u of ['Pa', 'kPa', 'MPa']) {
    const w = check[`implied_unit_weight_kN_m3_if_${u}`];
    if (Number.isFinite(w)) weights[u] = w;
  }
  const suggested = units.length === 1 ? units[0] : null;
  const level = !declared ? 'info' : (units.includes(declared) ? 'ok' : (units.length ? 'warn' : 'info'));
  return { suggested, consistent: units, weights, level };
}

const EXCAVATION = {
  labels: 'Cells whose category label contains a token (e.g. "null")',
  stress: 'Cells whose six stress components are all near zero',
  labels_then_stress: 'Labels if any match, otherwise near-zero stress',
  field: 'A cell array that is non-zero for excavated cells',
  removed_zones: 'Excavated zones were deleted before export',
};
export const EXCAVATION_STRATEGIES = Object.entries(EXCAVATION).map(([value, label]) => ({ value, label }));

export const INTERNAL_FACES = [
  { value: 'auto', label: 'Automatic: remove when the mesh has several connected regions' },
  { value: 'drop', label: 'Remove faces with solid on both sides' },
  { value: 'layer', label: 'Remove, and keep them as a separate hidden layer' },
  { value: 'keep', label: 'Keep every face (v0.1 behaviour)' },
];

// Completion of each step: 'done', 'attention' or 'todo'.
export function stepStatus(state) {
  const cfg = state?.config;
  const errors = state?.errors ?? [];
  const has = (p) => !!getPath(cfg, p);
  const out = {};
  out.model = cfg && getPath(cfg, 'input.stages', []).length ? 'done' : 'todo';
  if (!cfg) return { ...out, fields: 'todo', geometry: 'todo', sections: 'todo', build: 'todo', publish: 'todo' };
  const fieldError = errors.some((e) => /fields\./.test(e) || /stress/.test(e));
  out.fields = fieldError ? 'attention' : (has('fields.stress.unit') || has('fields.displacement.name') ? 'done' : 'todo');
  out.geometry = errors.some((e) => /geometry\./.test(e)) ? 'attention' : 'done';
  out.sections = errors.some((e) => /sections\./.test(e)) ? 'attention' : 'done';
  const v = state.validation;
  out.build = !state.built ? 'todo' : (v ? (v.passed ? 'done' : 'attention') : 'attention');
  out.publish = state.built && v?.passed ? 'done' : 'todo';
  return out;
}

const fmt = (n) => (Number.isFinite(n) ? n.toLocaleString('en-US') : String(n));

// Findings shown in the diagnostics panel: { level, title, detail }.
export function diagnostics(state) {
  const items = [];
  const info = state?.inspection;
  const cfg = state?.config;
  for (const e of state?.errors ?? []) items.push({ level: 'error', title: 'Configuration', detail: e });
  if (info) {
    items.push({ level: 'info', title: 'Model', detail: `${fmt(info.cells)} cells, ${fmt(info.points)} points` });
  }
  const stressName = getPath(cfg, 'fields.stress.name');
  if (stressName && info) {
    const arr = candidates(info).stress.find((a) => a.name === stressName);
    const order = getPath(cfg, 'fields.stress.order');
    if (arr?.component_names) {
      items.push({ level: 'ok', title: 'Stress component order', detail: `Read from the file: ${arr.component_names.join(', ')}` });
    } else if (order && order !== 'from_file') {
      items.push({ level: 'warn', title: 'Stress component order', detail: `Declared as ${order}; the file does not name its components. Check against the solver manual.` });
    }
    const advice = unitAdvice(info, getPath(cfg, 'fields.stress.unit'), stressName);
    if (advice) {
      const unit = getPath(cfg, 'fields.stress.unit');
      const w = advice.weights[unit];
      if (advice.level === 'ok') {
        items.push({ level: 'ok', title: 'Stress unit', detail: `${unit}: implied unit weight ${w.toFixed(1)} kN/m³` });
      } else if (advice.level === 'warn') {
        items.push({ level: 'warn', title: 'Stress unit', detail: `${unit} implies ${Number.isFinite(w) ? w.toFixed(1) : '?'} kN/m³; the vertical gradient fits ${advice.consistent.join(' or ')}` });
      }
    }
  }
  const stages = state?.build_report?.stages ?? [];
  for (const s of stages) {
    const b = s.excavation_boundary ?? {};
    if (b.faces) items.push({ level: 'info', title: `Excavation surface (${s.stage})`, detail: `${fmt(b.faces)} faces, ${fmt(Math.round(b.area))} m²` });
    if (b.internal_faces_removed) items.push({ level: 'ok', title: `Mesh interfaces (${s.stage})`, detail: `${fmt(b.internal_faces_removed)} faces with rock on both sides left out of the excavation surface` });
    if (b.internal_contact_faces) items.push({ level: 'ok', title: `Internal faces (${s.stage})`, detail: `${fmt(b.internal_contact_faces)} block-contact faces removed from the exterior` });
    const u = s.stress_unit_check;
    if (u && u.declared_consistent === false) items.push({ level: 'warn', title: `Stress unit (${s.stage})`, detail: 'The declared unit disagrees with the vertical stress gradient.' });
    if (s.void_diagnostics?.near_null_retained_cells > 0) items.push({ level: 'warn', title: `Void classification (${s.stage})`, detail: `${fmt(s.void_diagnostics.near_null_retained_cells)} retained cells carry almost no stress` });
  }
  const v = state?.validation;
  if (v) {
    items.push(v.passed
      ? { level: 'ok', title: 'Validation', detail: 'Every published value matches the source model' }
      : { level: 'error', title: 'Validation', detail: `${v.failures.length} failure(s): ${v.failures[0] ?? ''}` });
  }
  return items;
}

// A stage entry for a model file, with a name unique within the list.
export function stageFor(file, existing = []) {
  const base = file.split(/[\\/]/).pop().replace(/\.[^.]+$/, '') || 'stage';
  const names = new Set(existing.map((s) => s.name));
  let name = base;
  for (let k = 2; names.has(name); k += 1) name = `${base}_${k}`;
  return { file, name };
}
