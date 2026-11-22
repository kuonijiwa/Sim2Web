// Shareable view state in the URL hash, e.g.
//   #stage=IV-2&field=Stress_Min_Principal&axis=x&pos=54&range=p5_p95&cmap=jet&bands=8
//    &layers=excavation:1:1&section=1&cam=px,py,pz,fx,fy,fz,ux,uy,uz,scale
// Pure functions.

const NUMERIC = new Set(['pos', 'bands', 'rmin', 'rmax']);

export function encodeState(state) {
  const parts = [];
  for (const [key, value] of Object.entries(state)) {
    if (value === undefined || value === null || value === '') continue;
    let text;
    if (key === 'layers') text = Object.entries(value).map(([id, v]) => `${id}:${v.visible ? 1 : 0}:${round(v.opacity, 3)}`).join(',');
    else if (key === 'cam') text = value.map((x) => round(x, 4)).join(',');
    else if (typeof value === 'boolean') text = value ? '1' : '0';
    else text = String(value);
    parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(text)}`);
  }
  return parts.length ? `#${parts.join('&')}` : '';
}

export function decodeState(hash) {
  const out = {};
  const text = (hash || '').replace(/^#/, '');
  if (!text) return out;
  for (const part of text.split('&')) {
    const [k, v = ''] = part.split('=');
    const key = decodeURIComponent(k);
    const value = decodeURIComponent(v);
    if (key === 'layers') {
      out.layers = {};
      for (const item of value.split(',').filter(Boolean)) {
        const [id, vis, op] = item.split(':');
        out.layers[id] = { visible: vis === '1', opacity: Number(op ?? 1) };
      }
    } else if (key === 'cam') {
      const nums = value.split(',').map(Number);
      if (nums.length === 10 && nums.every(Number.isFinite)) out.cam = nums;
    } else if (key === 'section' || key === 'edges' || key === 'parallel') {
      out[key] = value === '1';
    } else if (NUMERIC.has(key)) {
      const n = Number(value);
      if (Number.isFinite(n)) out[key] = n;
    } else {
      out[key] = value;
    }
  }
  return out;
}

function round(x, digits) {
  const f = 10 ** digits;
  return Math.round(x * f) / f;
}
