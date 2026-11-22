import { test } from 'node:test';
import assert from 'node:assert/strict';
import { candidates, clone, diagnostics, getPath, orderOptions, setPath, stageFor, stepStatus, unitAdvice } from '../src/lib/model.js';

const inspection = {
  cells: 1000, points: 1331, bounds: [0, 10, 0, 10, 0, 10],
  point_arrays: { Displacement: { components: 3, min: 0, max: 1 }, Temp: { components: 1, min: 0, max: 1 } },
  cell_arrays: {
    Stress: { components: 6, component_names: ['XX', 'YY', 'ZZ', 'XY', 'XZ', 'YZ'] },
    Strain: { components: 6 },
    Group: { components: 1, unique_values: 3, examples: ['1', '2', '3'] },
  },
  stress_unit_check: { array: 'Stress', status: 'ok', consistent_units: ['MPa'],
    implied_unit_weight_kN_m3_if_Pa: 0.0000208, implied_unit_weight_kN_m3_if_kPa: 0.0208, implied_unit_weight_kN_m3_if_MPa: 20.8 },
};
const orders = { 'XX,YY,ZZ,XY,XZ,YZ': 'Itasca', 'XX,YY,ZZ,XY,YZ,XZ': 'Voigt' };

test('paths are read and written without mutating the input', () => {
  const a = { fields: { stress: { unit: 'Pa' } } };
  const b = setPath(a, 'fields.stress.unit', 'MPa');
  assert.equal(a.fields.stress.unit, 'Pa');
  assert.equal(getPath(b, 'fields.stress.unit'), 'MPa');
  assert.equal(getPath(b, 'geometry.primary', 'exterior'), 'exterior');
  assert.equal(getPath(setPath(null, 'a.b', 1), 'a.b'), 1);
});

test('candidate arrays per role', () => {
  const c = candidates(inspection);
  assert.deepEqual(c.displacement.map((a) => a.name), ['Displacement']);
  assert.deepEqual(c.stress.map((a) => a.name), ['Stress']);          // strain excluded
  assert.deepEqual(c.categories.map((a) => a.name), ['Group']);
});

test('the file order is offered only when the file names its components', () => {
  const named = orderOptions(candidates(inspection).stress[0], orders);
  assert.equal(named[0].value, 'from_file');
  assert.ok(!named[0].disabled);
  const unnamed = orderOptions({ name: 'S', components: 6 }, orders);
  assert.ok(unnamed[0].disabled);
  assert.equal(unnamed.length, 3);
});

test('unit advice follows the gravity check of the same array', () => {
  assert.equal(unitAdvice(inspection, 'MPa', 'Stress').level, 'ok');
  const wrong = unitAdvice(inspection, 'Pa', 'Stress');
  assert.equal(wrong.level, 'warn');
  assert.equal(wrong.suggested, 'MPa');
  assert.equal(unitAdvice(inspection, 'Pa', 'OtherStress'), null);
});

test('step status and diagnostics', () => {
  const state = { config: { input: { stages: [{ file: 'a.vtu', name: 'a' }] }, fields: { stress: { name: 'Stress', unit: 'Pa', order: 'from_file' } } },
    errors: [], inspection, built: true, validation: { passed: false, failures: ['s1: x'] },
    build_report: { stages: [{ stage: 's1', excavation_boundary: { faces: 10, area: 80, internal_faces_removed: 5 } }] } };
  const s = stepStatus(state);
  assert.equal(s.model, 'done');
  assert.equal(s.build, 'attention');
  const d = diagnostics(state);
  assert.ok(d.some((x) => x.level === 'warn' && x.title === 'Stress unit'));
  assert.ok(d.some((x) => x.title.startsWith('Mesh interfaces')));
  assert.ok(d.some((x) => x.level === 'error' && x.title === 'Validation'));
  assert.equal(stepStatus({ config: null }).fields, 'todo');
});

test('stage names stay unique', () => {
  const first = stageFor('C:\\models\\EXC12.vtu');
  assert.deepEqual(first, { file: 'C:\\models\\EXC12.vtu', name: 'EXC12' });
  assert.equal(stageFor('/x/EXC12.vtu', [first]).name, 'EXC12_2');
});

test('clone copies proxies of plain data', () => {
  const target = { a: { b: [1, 2] } };
  const proxy = new Proxy(target, {});
  const copy = clone(proxy);
  copy.a.b.push(3);
  assert.deepEqual(target.a.b, [1, 2]);
  assert.equal(getPath(setPath(proxy, 'a.c', 1), 'a.c'), 1);
});
