// Colour maps and banded / categorical lookup-table construction.
// Pure functions: no vtk.js imports, so they can be unit-tested with node --test.

// Control points: [t, r, g, b] with t in [0, 1].
export const COLORMAPS = {
  jet: [[0, 0, 0, 0.5], [0.11, 0, 0, 1], [0.34, 0, 1, 1], [0.65, 1, 1, 0], [0.89, 1, 0, 0], [1, 0.5, 0, 0]],
  viridis: [[0, 0.267, 0.005, 0.329], [0.125, 0.283, 0.141, 0.458], [0.25, 0.254, 0.265, 0.53],
    [0.375, 0.207, 0.372, 0.553], [0.5, 0.164, 0.471, 0.558], [0.625, 0.128, 0.567, 0.551],
    [0.75, 0.267, 0.679, 0.481], [0.875, 0.578, 0.788, 0.286], [1, 0.993, 0.906, 0.144]],
  turbo: [[0, 0.19, 0.072, 0.232], [0.125, 0.275, 0.408, 0.873], [0.25, 0.157, 0.733, 0.925],
    [0.375, 0.178, 0.937, 0.628], [0.5, 0.643, 0.988, 0.235], [0.625, 0.937, 0.812, 0.227],
    [0.75, 0.984, 0.502, 0.141], [0.875, 0.82, 0.2, 0.04], [1, 0.48, 0.016, 0.01]],
  coolwarm: [[0, 0.23, 0.299, 0.754], [0.25, 0.552, 0.69, 0.996], [0.5, 0.865, 0.865, 0.865],
    [0.75, 0.958, 0.604, 0.482], [1, 0.706, 0.016, 0.15]],
  grayscale: [[0, 0.1, 0.1, 0.1], [1, 0.95, 0.95, 0.95]],
};

// Okabe-Ito palette: distinguishable for common colour-vision deficiencies.
export const CATEGORY_COLORS = [
  [0.0, 0.447, 0.698], [0.902, 0.624, 0.0], [0.0, 0.62, 0.451], [0.8, 0.475, 0.655],
  [0.835, 0.369, 0.0], [0.337, 0.706, 0.914], [0.941, 0.894, 0.259], [0.3, 0.3, 0.3],
];

export function sampleColormap(name, t) {
  const pts = COLORMAPS[name] || COLORMAPS.jet;
  const x = Math.min(1, Math.max(0, t));
  for (let i = 1; i < pts.length; i += 1) {
    if (x <= pts[i][0]) {
      const [t0, r0, g0, b0] = pts[i - 1];
      const [t1, r1, g1, b1] = pts[i];
      const f = t1 > t0 ? (x - t0) / (t1 - t0) : 0;
      return [r0 + f * (r1 - r0), g0 + f * (g1 - g0), b0 + f * (b1 - b0)];
    }
  }
  return pts[pts.length - 1].slice(1);
}

// Piecewise-constant transfer-function nodes for `bands` equal intervals.
// Values outside [min, max] are clamped to the end colours by vtk.js.
export function bandedNodes(min, max, bands, colormap) {
  const span = max - min;
  if (!(span > 0)) return { nodes: [[min, ...sampleColormap(colormap, 0.5)]], legend: [{ from: min, to: max, color: sampleColormap(colormap, 0.5) }] };
  const n = Math.max(1, Math.round(bands));
  const step = span / n;
  const eps = span * 1e-9;
  const nodes = [];
  const legend = [];
  for (let i = 0; i < n; i += 1) {
    const from = min + i * step;
    const to = min + (i + 1) * step;
    const color = sampleColormap(colormap, n === 1 ? 0.5 : i / (n - 1));
    nodes.push([from, ...color], [to - eps, ...color]);
    legend.push({ from, to, color });
  }
  return { nodes, legend };
}

export function categoryNodes(categories) {
  const nodes = [];
  const legend = [];
  categories.forEach((cat, i) => {
    const color = CATEGORY_COLORS[i % CATEGORY_COLORS.length];
    nodes.push([cat.code - 0.5, ...color], [cat.code + 0.5 - 1e-6, ...color]);
    legend.push({ code: cat.code, label: cat.label, color });
  });
  return { nodes, legend };
}

export function formatValue(v, span = Math.abs(v)) {
  if (!Number.isFinite(v)) return String(v);
  const a = Math.abs(v);
  if (v === 0) return '0';
  if (a >= 1e5 || a < 1e-3) return v.toExponential(3);
  const digits = Math.max(0, Math.min(6, 3 - Math.floor(Math.log10(Math.max(span, 1e-12)))));
  return v.toFixed(digits);
}

export function cssColor([r, g, b]) {
  return `rgb(${Math.round(r * 255)}, ${Math.round(g * 255)}, ${Math.round(b * 255)})`;
}
