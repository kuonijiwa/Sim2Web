# Viewer

The viewer is a single Vue 3 / vtk.js application (`viewer/`). It is built once
(`npm run build:viewer`) and copied by `sim2web build` into every package. It
reads `model_cache/index.json` and creates all controls from it, so it needs no
per-model code.

## Features

| Area | What it does |
|---|---|
| Stages | previous/next/select; optional common colour scale for all stages |
| Fields | grouped list (displacement, stress, categories, other) with units; badge shows cell (exact) or point (nodal) association; sign convention and source component order shown |
| Colour | five colour maps, 1–32 bands, full range, P5–P95 (outliers clamped, values unchanged) or custom range; categorical legend with labels |
| Layers | every layer in the index with visibility and opacity; mesh edges |
| Sections | axis tabs, slider and ± buttons (also ← / → keys), position and file size, "view face-on" |
| Probe | click any surface or section: exact cell values, `Source_Cell_ID`, nearest `Source_Point_ID` (surfaces) or "interpolated vertex" (sections) |
| View | reset, X/Y/Z views, parallel projection, PNG export |
| Sharing | the URL hash keeps stage, field, colour settings, section and layers; "Copy view link" adds the camera |
| Diagnostics | startup transfer, time to first image, last section-switch latency, frame-rate measurement, JS heap |

Only the primary surface(s) and the selected section are fetched at start-up;
other sections are fetched when selected. The two neighbouring sections are
prefetched in idle time (disable with `?prefetch=0`). A small cache keeps
recently used products.

## Customising

Most changes need only the configuration (`viewer:` block): title, subtitle,
default field and axis, colour map, bands, range mode, background, length
unit. Category labels come from `fields.categories[].labels`.

For deeper changes, edit the viewer source and rebuild:

| File | Responsibility |
|---|---|
| `viewer/src/App.vue` | panel layout and interaction |
| `viewer/src/lib/scene.js` | vtk.js scene: actors, colouring, camera, picking, screenshots |
| `viewer/src/lib/indexModel.js` | interpretation of `index.json` (fields, ranges, sections) |
| `viewer/src/lib/colormaps.js` | colour maps, banded and categorical lookup tables |
| `viewer/src/lib/loader.js` | fetching, parsing, caching, timing of VTP files |
| `viewer/src/lib/urlState.js` | shareable state in the URL |
| `viewer/src/components/LegendCard.vue` | legend |

```bash
npm install
npm run build:viewer                       # into src/sim2web/viewer_dist
sim2web install-viewer path/to/site     # or rebuild the package
# live development against a built package:
SIM2WEB_SITE=examples/flac3d_slope_exac23/site npm run dev:viewer
```

A custom build can be installed into any package with
`sim2web install-viewer site --source my_viewer_dist`.

## Embedding and automation

After start-up the viewer exposes `window.__SIM2WEB__`:

```js
const v = window.__SIM2WEB__;
await v.setField('Stress_Min_Principal');
await v.setSection('x', 12);          // returns {axis, value, ms, cached, bytes}
v.describeActors();                   // array, association, ranges of every visible actor
await v.measureFrameRate(120, 3);     // frames, seconds, fps
v.summary();                          // timings, transferred files, heap
```

`benchmark/browser_benchmark.mjs` uses this interface. Query parameters:
`?index=<url>` reads another index, `?prefetch=0` disables prefetching.

## Index schema (`sim2web-index/2`)

```text
schema, generator{name, version}, title, description, solver, config_sha256
viewer{title, subtitle, default_field, default_axis, colormap, bands, background, range_mode, length_unit}
fields{<name>: {label, unit, association, kind, source, component_order?, sign_convention?, categories?}}
ranges{<name>: {min, max}}                                   # over all stages
stages[]{id, label, source{file, sha256, bytes, points, cells}, void{method, cells}, mesh_regions,
         layers[]{id, label, kind, role, default_visible?, file, bytes, sha256, points, cells, point_arrays, cell_arrays},
         sections{x|y|z: [{value, file, bytes, sha256, points, cells, ...}]},
         section_rules{placement, spacing, displacement_magnitude, preserve_discontinuities, display_averaging},
         fields{<name>: {min, max, p5, p95}}}
```
