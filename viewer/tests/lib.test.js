// node --test viewer/tests/   (pure-function tests; no browser needed)
import test from 'node:test';
import assert from 'node:assert/strict';
import { bandedNodes, categoryNodes, sampleColormap, formatValue } from '../src/lib/colormaps.js';
import { checkIndex, displayRange, nearestSectionIndex, sectionAxes } from '../src/lib/indexModel.js';
import { decodeState, encodeState } from '../src/lib/urlState.js';

const index = {
  schema: 'sim2web-index/2',
  fields: { U: { association: 'point', kind: 'continuous' }, S: { association: 'cell', kind: 'continuous' } },
  stages: [
    { id: 'a', fields: { U: { min: 0, max: 1, p5: 0.1, p95: 0.8 }, S: { min: -5, max: 2, p5: -4, p95: 1 } },
      sections: { x: [{ value: 0 }, { value: 10 }, { value: 20 }], y: [] } },
    { id: 'b', fields: { U: { min: 0, max: 3, p5: 0.2, p95: 2 } }, sections: {} },
  ],
};

test('banded nodes cover the range with equal bands', () => {
  const { nodes, legend } = bandedNodes(0, 8, 4, 'viridis');
  assert.equal(legend.length, 4);
  assert.equal(nodes.length, 8);
  assert.deepEqual(legend.map((b) => [b.from, b.to]), [[0, 2], [2, 4], [4, 6], [6, 8]]);
  assert.deepEqual(nodes[0].slice(1), nodes[1].slice(1)); // constant colour inside a band
});

test('degenerate range does not throw', () => {
  const { legend } = bandedNodes(3, 3, 8, 'jet');
  assert.equal(legend.length, 1);
});

test('categories get distinct colours centred on integer codes', () => {
  const { nodes, legend } = categoryNodes([{ code: 0, label: 'rock' }, { code: 1, label: 'fill' }]);
  assert.equal(nodes[0][0], -0.5);
  assert.notDeepEqual(legend[0].color, legend[1].color);
});

test('colormap endpoints', () => {
  assert.deepEqual(sampleColormap('grayscale', 0), [0.1, 0.1, 0.1]);
  assert.deepEqual(sampleColormap('grayscale', 2), [0.95, 0.95, 0.95]);
});

test('display ranges: full, percentile, all stages and custom', () => {
  assert.deepEqual(displayRange(index, 0, 'U', 'full', 'stage').min, 0);
  assert.equal(displayRange(index, 0, 'U', 'p5_p95', 'stage').max, 0.8);
  assert.equal(displayRange(index, 0, 'U', 'full', 'all').max, 3);
  assert.equal(displayRange(index, 0, 'U', 'custom', 'stage', [0.2, 0.4]).max, 0.4);
  assert.equal(displayRange(index, 0, 'U', 'custom', 'stage', [0.4, 0.2]).label, 'full range'); // invalid custom
});

test('schema check and section helpers', () => {
  assert.throws(() => checkIndex({ schema: 'old' }), /Unsupported/);
  assert.deepEqual(sectionAxes(index.stages[0]), ['x']);
  assert.equal(nearestSectionIndex(index.stages[0].sections.x, 12), 1);
});

test('URL state round trip', () => {
  const state = { stage: 'IV-2', field: 'Stress_XX', pos: 54, bands: 8, section: true,
    layers: { exterior: { visible: true, opacity: 0.35 } }, cam: [1, 2, 3, 4, 5, 6, 0, 0, 1, 10] };
  const back = decodeState(encodeState(state));
  assert.deepEqual(back, state);
});

test('value formatting', () => {
  assert.equal(formatValue(0), '0');
  assert.match(formatValue(1.23e-6), /e-6$/);
});
