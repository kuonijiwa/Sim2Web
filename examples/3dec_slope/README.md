# Case C — 3DEC slope

This cross-solver example retains one `slopemodel` input.  The displayed object
is the **OUTER EXPOSED SURFACE**, with axis-aligned **SECTION** meshes.  Separate
blocks and disconnected surface components are physically valid for this case.

```bash
python processing/process.py
npm run build:3dec-slope
```

Input is `input/slopemodel.vtu`; products are written beneath
`output/model_cache/slopemodel/`.  The editable frontend entry component is
`frontend/src/App.vue`.  Full-model opacity defaults to 100% for the clearest
validated display.

Stress uses exact CellData, material identifiers are categorical CellData, and
displacement fields are continuous PointData.
